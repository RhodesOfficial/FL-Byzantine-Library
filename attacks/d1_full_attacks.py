"""Predeclared trigger and root-constrained attacker for the D1 full study."""

from __future__ import annotations

import copy

import torch
from torch.utils.data import Dataset, DataLoader, Subset


class FixedTriggerDataset(Dataset):
    """3x3 white bottom-right patch, target class zero, fixed 20% poisoning."""

    def __init__(self, source, *, target=0, poison_fraction=0.2, force=False):
        self.source = source
        self.target = target
        self.poison_fraction = poison_fraction
        self.force = force

    def __len__(self):
        return len(self.source)

    def __getitem__(self, index):
        image, label = self.source[index]
        if self.force or ((index * 2654435761 + 17) % 1000) < int(self.poison_fraction * 1000):
            image = image.clone()
            mean = (0.4914, 0.4822, 0.4465)
            std = (0.247, 0.243, 0.262)
            for channel in range(3):
                image[channel, -3:, -3:] = (1.0 - mean[channel]) / std[channel]
            return image, self.target
        return image, label


def _mean_gradient(context, indices, batch_size):
    model = context.model
    params = tuple(model.parameters())
    total = torch.zeros_like(torch.nn.utils.parameters_to_vector(params))
    count = 0
    loader = DataLoader(Subset(context.root_data, indices), batch_size=batch_size,
                        shuffle=False, collate_fn=getattr(context.calculator, "collate_fn", None))
    was_training = model.training
    model.eval()
    try:
        for batch in loader:
            loss = context.calculator.compute_loss(model, batch)
            loss = loss["loss"] if isinstance(loss, dict) else loss
            gradients = torch.autograd.grad(loss, params, allow_unused=True)
            n = len(batch[-1])
            total += torch.cat([torch.zeros_like(p).flatten() if g is None
                                else g.detach().flatten() for p, g in zip(params, gradients)]) * n
            count += n
    finally:
        model.train(was_training)
    return total / count


def root_constrained_update(benign, context, attacker_samples, train_indices,
                            *, batch_size=64, tolerance=0.02):
    """Maximize attacker-owned tail loss while preserving root-train loss.

    The attacker observes benign updates and its own tail samples. It never
    reads D1's held-out audit half. Candidate vectors have a bounded norm and
    are checked against the trusted train half before being returned.
    """
    if not benign:
        return torch.zeros_like(torch.nn.utils.parameters_to_vector(
            context.model.parameters()).detach())
    anchor = torch.stack(benign).mean(0)
    if not attacker_samples:
        return torch.zeros_like(anchor)
    model = context.model
    params = tuple(model.parameters())
    batch = next(iter(DataLoader(attacker_samples, batch_size=batch_size)))
    was_training = model.training
    model.eval()
    try:
        loss = context.calculator.compute_loss(model, batch)
        loss = loss["loss"] if isinstance(loss, dict) else loss
        parts = torch.autograd.grad(loss, params, allow_unused=True)
        tail_grad = torch.cat([torch.zeros_like(p).flatten() if g is None
                               else g.detach().flatten() for p, g in zip(params, parts)])
    finally:
        model.train(was_training)
    root_grad = _mean_gradient(context, train_indices, batch_size)
    root_unit = root_grad / root_grad.norm().clamp_min(1e-12)
    harmful = tail_grad - torch.dot(tail_grad, root_unit) * root_unit
    if harmful.norm() <= 1e-12:
        return torch.zeros_like(anchor)
    harmful = harmful / harmful.norm()
    limit = max(torch.stack([x.norm() for x in benign]).median().item(), 1e-12)
    base = torch.nn.utils.parameters_to_vector(params).detach().clone()
    probe = copy.deepcopy(model)
    probe_params = tuple(probe.parameters())

    def root_loss():
        loader = DataLoader(Subset(context.root_data, train_indices), batch_size=batch_size,
                            shuffle=False, collate_fn=getattr(context.calculator, "collate_fn", None))
        total, count = 0.0, 0
        probe.eval()
        with torch.no_grad():
            for root_batch in loader:
                value = context.calculator.compute_loss(probe, root_batch)
                value = value["loss"] if isinstance(value, dict) else value
                n = len(root_batch[-1])
                total += float(value) * n
                count += n
        return total / count

    baseline = root_loss()
    for scale in (2.0, 1.0, 0.5, 0.25, 0.125):
        candidate = anchor - scale * limit * harmful
        candidate = candidate * min(1.0, limit / candidate.norm().clamp_min(1e-12).item())
        with torch.no_grad():
            torch.nn.utils.vector_to_parameters(base - candidate, probe_params)
        if root_loss() <= baseline + tolerance:
            return candidate
    return torch.zeros_like(anchor)
