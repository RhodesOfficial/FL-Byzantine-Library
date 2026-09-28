"""D1: class-covered root trust with a capped, audited residual.

The public input uses the FLGo bridge's ``base - client`` convention.  All
internal displacements use ``client - base``; the result is negated on return.
The root set must have been isolated from client training by the caller.
"""

from __future__ import annotations

import copy
import math
from collections import defaultdict

import torch
from torch.utils.data import DataLoader, Subset

from .base import _BaseAggregator


class D1CategoryCoverage(_BaseAggregator):
    """Three-stage D1 aggregator, using only trusted root labels as evidence.

    ``context`` provides the current model, calculator, device and root_data.
    ``num_classes`` is the task's declared label universe, not a client claim.
    ``mode`` must be chosen before training, without using malicious identities.
    """

    def __init__(self, context, num_classes: int, *, mode: str = "majority",
                 clip_norm: float = 1.0, residual_budget_ratio: float = 0.25,
                 root_step: float = 0.1, drag_strength: float = 0.5,
                 loss_tolerance: float = 0.02, min_class_count: int = 2,
                 reliability_floor: float = 0.05, batch_size: int = 64,
                 seed: int = 0, median_steps: int = 20,
                 candidate_lambdas=(0.0, 0.25, 0.5, 1.0),
                 candidate_steps=(1.0, 0.5, 0.25, 0.125)):
        if context is None or context.root_data is None:
            raise ValueError("D1 requires an isolated trusted root dataset and runtime context")
        if type(num_classes) is not int or num_classes < 1:
            raise ValueError("num_classes must be a positive integer")
        if mode not in {"majority", "conservative"}:
            raise ValueError("mode must be 'majority' or 'conservative'")
        for name, value in (("clip_norm", clip_norm), ("root_step", root_step),
                            ("loss_tolerance", loss_tolerance)):
            if not math.isfinite(value) or (value <= 0 if name != "loss_tolerance" else value < 0):
                raise ValueError(f"{name} must be finite and nonnegative (positive for norms/steps)")
        for name, value in (("residual_budget_ratio", residual_budget_ratio),
                            ("drag_strength", drag_strength)):
            if not math.isfinite(value) or not 0 <= value <= 1:
                raise ValueError(f"{name} must lie in [0, 1]")
        if min_class_count < 2 or batch_size < 1 or median_steps < 1:
            raise ValueError("invalid class count, batch size, or median iteration count")
        if not math.isfinite(reliability_floor) or not 0 <= reliability_floor <= 1:
            raise ValueError("reliability_floor must lie in [0, 1]")
        if not candidate_lambdas or any(not math.isfinite(x) or not 0 <= x <= 1 for x in candidate_lambdas):
            raise ValueError("candidate_lambdas must be a nonempty subset of [0, 1]")
        if not candidate_steps or any(not math.isfinite(x) or not 0 < x <= 1 for x in candidate_steps):
            raise ValueError("candidate_steps must be a nonempty subset of (0, 1]")
        self.context = context
        self.num_classes = num_classes
        self.mode = mode
        self.clip_norm = float(clip_norm)
        self.residual_budget_ratio = float(residual_budget_ratio)
        self.root_step = float(root_step)
        self.drag_strength = float(drag_strength)
        self.loss_tolerance = float(loss_tolerance)
        self.min_class_count = int(min_class_count)
        self.reliability_floor = float(reliability_floor)
        self.batch_size = int(batch_size)
        self.median_steps = int(median_steps)
        self.candidate_lambdas = tuple(float(x) for x in candidate_lambdas)
        self.candidate_steps = tuple(float(x) for x in candidate_steps)
        self.train_indices, self.audit_indices = self._split_root(seed)
        self.last_stats = {}

    def _split_root(self, seed):
        """Fixed, stratified, disjoint split; no client metadata is consumed."""
        by_class = defaultdict(list)
        for index in range(len(self.context.root_data)):
            sample = self.context.root_data[index]
            if not isinstance(sample, (tuple, list)) or len(sample) < 2:
                raise ValueError("root samples must end with a class label")
            label = sample[-1]
            label = int(label.item()) if isinstance(label, torch.Tensor) else int(label)
            if not 0 <= label < self.num_classes:
                raise ValueError("root label lies outside the declared class universe")
            by_class[label].append(index)
        generator = torch.Generator().manual_seed(int(seed))
        train, audit = {}, {}
        for label in range(self.num_classes):
            indices = by_class[label]
            order = torch.randperm(len(indices), generator=generator).tolist()
            cut = (len(indices) + 1) // 2
            train[label] = [indices[j] for j in order[:cut]]
            audit[label] = [indices[j] for j in order[cut:]]
        return train, audit

    def _batches(self, indices):
        subset = Subset(self.context.root_data, indices)
        return DataLoader(subset, batch_size=self.batch_size, shuffle=False,
                          collate_fn=getattr(self.context.calculator, "collate_fn", None))

    def _loss(self, model, batch):
        result = self.context.calculator.compute_loss(model, batch)
        loss = result["loss"] if isinstance(result, dict) else result
        if not torch.isfinite(loss).all().item():
            raise ValueError("non-finite trusted root loss")
        return loss

    def _class_gradient(self, model, indices, parameters):
        """Two independent halves provide a cheap stability estimate."""
        midpoint = (len(indices) + 1) // 2
        halves = (indices[:midpoint], indices[midpoint:])
        gradients, losses = [], []
        for half in halves:
            total = None
            loss_total = 0.0
            count = 0
            for batch in self._batches(half):
                n = len(batch[-1])
                model.zero_grad(set_to_none=True)
                loss = self._loss(model, batch)
                parts = torch.autograd.grad(loss, parameters, allow_unused=True)
                vector = torch.cat([torch.zeros_like(p).reshape(-1) if g is None else g.detach().reshape(-1)
                                    for p, g in zip(parameters, parts)])
                total = vector * n if total is None else total + vector * n
                loss_total += float(loss.detach()) * n
                count += n
            gradients.append(total / count)
            losses.append(loss_total / count)
        return (gradients[0] * len(halves[0]) + gradients[1] * len(halves[1])) / len(indices), gradients, losses

    def _root_evidence(self, model):
        parameters = tuple(model.parameters())
        basis_vectors, coefficients, reliable, counts, quality = [], {}, [], {}, {}
        for label in range(self.num_classes):
            indices = self.train_indices[label]
            counts[label] = len(indices)
            quality[label] = 0.0
            if len(indices) < self.min_class_count or len(self.audit_indices[label]) < self.min_class_count:
                continue
            gradient, halves, losses = self._class_gradient(model, indices, parameters)
            norm_product = halves[0].norm() * halves[1].norm()
            stability = (torch.dot(halves[0], halves[1]) / norm_product).clamp(min=0).item() if norm_product > 0 else 0.0
            volatility = abs(losses[0] - losses[1]) / (abs(sum(losses) / 2) + 1e-12)
            q = len(indices) / (len(indices) + self.min_class_count) * stability / (1 + volatility)
            if not math.isfinite(q):
                raise ValueError("non-finite root reliability")
            quality[label] = q
            if q >= self.reliability_floor and torch.isfinite(gradient).all().item() and gradient.norm() > 0:
                components = []
                remainder = gradient.clone()
                for direction in basis_vectors:
                    component = torch.dot(remainder, direction)
                    components.append(component)
                    remainder -= component * direction
                norm = remainder.norm()
                if norm > 1e-8 * gradient.norm():
                    basis_vectors.append(remainder / norm)
                    components.append(norm)
                coefficients[label] = torch.stack(components)
                reliable.append(label)
        dimension = sum(p.numel() for p in parameters)
        basis = torch.stack(basis_vectors) if basis_vectors else parameters[0].new_empty((0, dimension))
        padded = {}
        for label, values in coefficients.items():
            padded[label] = torch.nn.functional.pad(values, (0, len(basis_vectors) - len(values)))
        return basis, padded, reliable, counts, quality

    @staticmethod
    def _project(vector, basis):
        return (vector @ basis.T) @ basis if basis.numel() else torch.zeros_like(vector)

    @staticmethod
    def _cap(vector, limit):
        norm = vector.norm()
        return vector * min(1.0, limit / (norm.item() + 1e-12))

    def _geometric_median(self, vectors):
        points = torch.stack(vectors)
        estimate = points.mean(dim=0)
        for _ in range(self.median_steps):
            distances = torch.linalg.vector_norm(points - estimate, dim=1)
            if distances.min().item() < 1e-8:
                return points[distances.argmin()].clone()
            weights = distances.clamp_min(1e-8).reciprocal()
            next_estimate = (points * weights[:, None]).sum(dim=0) / weights.sum()
            if torch.linalg.vector_norm(next_estimate - estimate).item() < 1e-6:
                return next_estimate
            estimate = next_estimate
        return estimate

    def _audit_losses(self, model, labels):
        result = {}
        model.eval()
        with torch.no_grad():
            for label in labels:
                total, count = 0.0, 0
                for batch in self._batches(self.audit_indices[label]):
                    n = len(batch[-1])
                    total += float(self._loss(model, batch)) * n
                    count += n
                result[label] = total / count
        return result

    def _set_displacement(self, model, base, displacement):
        with torch.no_grad():
            torch.nn.utils.vector_to_parameters(base + displacement, model.parameters())

    def _feasible(self, displacement, basis, coefficients, labels, audit_model, base, baseline):
        projected = basis @ displacement
        if any(torch.dot(coefficients[label], projected).item() > self.loss_tolerance + 1e-8
               for label in labels):
            return None
        self._set_displacement(audit_model, base, displacement)
        losses = self._audit_losses(audit_model, labels)
        if any(losses[label] - baseline[label] > self.loss_tolerance + 1e-8 for label in labels):
            return None
        return sum(losses.values()) / len(losses)

    def __call__(self, inputs):
        if not inputs:
            raise ValueError("D1 requires at least one client update")
        first = inputs[0]
        if first.ndim != 1 or not first.is_floating_point():
            raise ValueError("D1 requires flat floating-point vectors")
        if any(x.shape != first.shape or x.device != first.device or x.dtype != first.dtype
               or not torch.isfinite(x).all().item() for x in inputs):
            raise ValueError("D1 received an incompatible or non-finite update")
        model = self.context.model
        base = torch.nn.utils.parameters_to_vector(model.parameters()).detach()
        if base.shape != first.shape or base.device != first.device:
            raise ValueError("current model does not match client update layout")
        was_training = model.training
        model.eval()
        try:
            basis, coefficients, reliable, counts, quality = self._root_evidence(model)
        finally:
            model.train(was_training)
        stats = {"covered_classes": len(reliable), "total_classes": self.num_classes,
                 "missing_classes": sum(counts[c] == 0 for c in counts),
                 "root_train_count": sum(len(v) for v in self.train_indices.values()),
                 "root_audit_count": sum(len(v) for v in self.audit_indices.values()),
                 "mode": self.mode, "fallback": "none", "residual_norm": 0.0,
                 "class_reliability": quality}
        if not reliable:
            stats["fallback"] = "skip_no_reliable_class"
            self.last_stats = stats
            return torch.zeros_like(first)
        mean_coefficients = torch.stack([coefficients[c] for c in reliable]).mean(dim=0)
        root = self._cap(-self.root_step * (mean_coefficients @ basis), self.clip_norm)
        if root.norm().item() < 1e-12:
            stats["fallback"] = "skip_no_root_direction"
            self.last_stats = stats
            return torch.zeros_like(first)
        displacements = [self._cap(-x, self.clip_norm) for x in inputs]
        parallel = [self._project(x, basis) for x in displacements]
        residuals = [x - p for x, p in zip(displacements, parallel)]
        root_norm = root.norm()
        calibrated = []
        for vector in parallel:
            norm = vector.norm()
            cosine = (torch.dot(vector, root) / (norm * root_norm)).clamp(-1, 1).item() if norm > 0 and root_norm > 0 else 0.0
            weight = self.drag_strength * (1 - cosine)
            normalized = vector * (root_norm / norm) if norm > 0 else torch.zeros_like(root)
            calibrated.append((1 - weight) * normalized + weight * root)
        trusted = self._project(torch.stack(calibrated).mean(dim=0), basis)
        median = self._geometric_median(residuals) if self.mode == "majority" else torch.zeros_like(root)
        # Missing classes never increase this budget; the category audit below
        # protects only classes with actual independent evidence.
        budget = self.clip_norm * self.residual_budget_ratio
        baseline_model = copy.deepcopy(model)
        baseline = self._audit_losses(baseline_model, reliable)
        audit_model = copy.deepcopy(model)
        best, best_loss = None, float("inf")
        for step in self.candidate_steps:
            for lam in (self.candidate_lambdas if self.mode == "majority" else (0.0,)):
                residual = self._cap(lam * median, budget)
                candidate = self._cap(step * (trusted + residual), self.clip_norm)
                score = self._feasible(candidate, basis, coefficients, reliable, audit_model, base, baseline)
                if score is not None and score < best_loss:
                    best, best_loss = candidate, score
                    stats["residual_norm"] = float(self._cap(step * residual, budget).norm())
        if best is None:
            for step in self.candidate_steps:
                candidate = self._cap(step * root, self.clip_norm)
                score = self._feasible(candidate, basis, coefficients, reliable, audit_model, base, baseline)
                if score is not None:
                    best = candidate
                    stats["fallback"] = "root"
                    break
        if best is None:
            best = torch.zeros_like(first)
            stats["fallback"] = "skip_audit"
        if not torch.isfinite(best).all().item():
            raise ValueError("D1 produced a non-finite displacement")
        stats["update_norm"] = float(best.norm())
        self.last_stats = stats
        return -best

    def get_attack_stats(self):
        # Keep the bridge's scalar-only logger contract; detailed reliability
        # remains available on the instance for local diagnostics.
        return {key: value for key, value in self.last_stats.items()
                if key != "class_reliability"}
