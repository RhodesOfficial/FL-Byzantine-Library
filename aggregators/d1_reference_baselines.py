"""Root-data controls for the D1 experiment, in bridge difference direction.

FLTrust follows the local implementation's positive-cosine trust rule;
BR-DRAG follows Xiao et al. 2026, IV.B-C; FLEST follows Geng et al.
2023, IV.2-3. All use the same disjoint 1,000-example root training split.
"""

from __future__ import annotations

import copy
from collections import defaultdict
from contextlib import nullcontext

import torch
from torch.utils.data import DataLoader, Subset

from .base import _BaseAggregator
from .d1_category_coverage import _preserve_global_rng

LEGACY_BASELINE_VERSION = "root1000-v1"
B_BASELINE_VERSION = "root2000-rng-v1"


class RootBaseline(_BaseAggregator):
    def __init__(self, context, num_classes, method, seed=0, root_step=0.1,
                 batch_size=64, drag_strength=0.5, splice_ratio=0.25,
                 version=LEGACY_BASELINE_VERSION, root_budget=1000):
        if method not in {"fltrust", "brdrag", "flest", "balanced_brdrag",
                          "balanced_splice"}:
            raise ValueError("unknown root baseline")
        self.context = context
        self.num_classes = num_classes
        self.method = method
        self.root_step = root_step
        self.batch_size = batch_size
        self.drag_strength = drag_strength
        self.splice_ratio = splice_ratio
        self.seed = seed
        self.round_index = 0
        self.version, self.root_budget = version, root_budget
        if version not in {LEGACY_BASELINE_VERSION, B_BASELINE_VERSION}:
            raise ValueError("unknown root baseline version")
        self.protect_rng = version == B_BASELINE_VERSION
        if root_budget != (2000 if self.protect_rng else 1000):
            raise ValueError("root budget differs from baseline version")
        if self.protect_rng and (method not in {"brdrag", "balanced_brdrag"}
                                 or len(context.root_data) != root_budget):
            raise ValueError("B baselines require the complete 2000-example root pool")
        self._loader_generator = (torch.Generator().manual_seed(seed)
                                  if self.protect_rng else None)
        with _preserve_global_rng() if self.protect_rng else nullcontext():
            self._initialize_indices(context, num_classes, seed)
        self.last_client_weights = []
        self.last_stats = {}

    def _initialize_indices(self, context, num_classes, seed):
        buckets = defaultdict(list)
        for index in range(len(context.root_data)):
            buckets[int(context.root_data[index][-1])].append(index)
        generator = torch.Generator().manual_seed(seed)
        self.train_indices = {}
        extra = ((len(context.root_data) + 1) // 2
                 - sum(len(indices) // 2 for indices in buckets.values()))
        for label in range(num_classes):
            indices = buckets[label]
            order = torch.randperm(len(indices), generator=generator).tolist()
            cut = len(indices) // 2
            if self.protect_rng:
                cut = len(indices)
            if not self.protect_rng and len(indices) % 2 and extra:
                cut += 1
                extra -= 1
            self.train_indices[label] = [indices[i] for i in order[:cut]]

    def _root(self):
        with _preserve_global_rng() if self.protect_rng else nullcontext():
            return self._root_unprotected()

    def _root_unprotected(self):
        all_indices = [i for indices in self.train_indices.values() for i in indices]
        if self.method in {"balanced_brdrag", "balanced_splice"}:
            labels = [label for label, indices in self.train_indices.items() if indices]
            base, remainder = divmod(self.root_budget, len(labels))
            generator = torch.Generator().manual_seed(self.seed + self.round_index + 919)
            all_indices = []
            for offset, label in enumerate(labels):
                indices = self.train_indices[label]
                count = base + (offset < remainder)
                choices = torch.randint(len(indices), (count,), generator=generator)
                all_indices.extend(indices[int(j)] for j in choices)
        generator = torch.Generator().manual_seed(self.seed + self.round_index + 313)
        all_indices = [all_indices[int(j)] for j in torch.randperm(
            len(all_indices), generator=generator)]
        self.round_index += 1
        model = copy.deepcopy(self.context.model)
        base_vector = torch.nn.utils.parameters_to_vector(
            self.context.model.parameters()).detach()
        optimizer = torch.optim.SGD(model.parameters(), lr=self.root_step)
        loader = DataLoader(Subset(self.context.root_data, all_indices),
                            batch_size=self.batch_size, shuffle=False,
                            collate_fn=getattr(self.context.calculator, "collate_fn", None),
                            generator=self._loader_generator)
        model.train()
        for batch in loader:
            optimizer.zero_grad(set_to_none=True)
            loss = self.context.calculator.compute_loss(model, batch)
            loss = loss["loss"] if isinstance(loss, dict) else loss
            loss.backward()
            optimizer.step()
        return base_vector - torch.nn.utils.parameters_to_vector(model.parameters()).detach()

    @staticmethod
    def _kmeans_largest(updates):
        # Exact Euclidean 2-means in the 20-by-20 Gram space; no 20xD copy.
        x = torch.stack(updates)
        gram = x @ x.T
        diagonal = gram.diag()
        distance = (diagonal[:, None] + diagonal[None, :] - 2 * gram).clamp_min(0)
        seeds = [0, int(distance[0].argmax())]
        assignment = None
        centre_distances = torch.stack([distance[:, seeds[0]],
                                        distance[:, seeds[1]]], dim=1)
        for _ in range(10):
            next_assignment = centre_distances.argmin(dim=1)
            if assignment is not None and torch.equal(next_assignment, assignment):
                break
            assignment = next_assignment
            columns = []
            for group in (0, 1):
                members = (assignment == group).nonzero().flatten()
                if not len(members):
                    columns.append(distance[:, seeds[group]])
                else:
                    columns.append((diagonal - 2 * gram[:, members].mean(1)
                                    + gram[members][:, members].mean()).clamp_min(0))
            centre_distances = torch.stack(columns, dim=1)
        members = (assignment == int((assignment == 1).sum() > (assignment == 0).sum())).nonzero().flatten()
        return x[members].mean(0)

    @staticmethod
    def _middle_half_mean(scores):
        ordered = scores.sort().values
        lo, hi = len(scores) // 4, len(scores) - len(scores) // 4
        return ordered[lo:hi].mean()

    def __call__(self, inputs):
        if not inputs or any(x.shape != inputs[0].shape or not torch.isfinite(x).all() for x in inputs):
            raise ValueError("invalid root baseline updates")
        root = self._root().to(inputs[0])
        root_norm = root.norm()
        if root_norm <= 1e-12:
            self.last_client_weights = [0.0] * len(inputs)
            return torch.zeros_like(inputs[0])
        norms = torch.stack([x.norm() for x in inputs]).clamp_min(1e-12)
        unit = torch.stack([x / norm for x, norm in zip(inputs, norms)])
        cosines = (unit @ (root / root_norm)).clamp(-1, 1)
        if self.method == "fltrust":
            scores = cosines.clamp_min(0)
            transformed = unit * root_norm
        elif self.method in {"brdrag", "balanced_brdrag", "balanced_splice"}:
            # B diagnostics can use this actual lam and clamped norms:
            # a_i=(1-lam_i)*root_norm/(len(inputs)*norms_i), b_i=0.
            # Both bridge vectors have opposite sign to model displacements.
            lam = (self.drag_strength * (1 - cosines)).clamp(0, 1)
            scores = torch.ones_like(cosines)
            transformed = (1 - lam[:, None]) * unit * root_norm + lam[:, None] * root
        else:
            cluster = self._kmeans_largest(inputs)
            cluster_unit = cluster / cluster.norm().clamp_min(1e-12)
            confidence = (unit @ cluster_unit).clamp_min(0)
            trust = cosines.clamp_min(0)
            trust_middle = self._middle_half_mean(trust)
            confidence_middle = self._middle_half_mean(confidence)
            gamma = trust_middle / (trust_middle + confidence_middle).clamp_min(1e-12)
            scores = gamma * trust + (1 - gamma) * confidence
            transformed = unit * root_norm
            self.last_stats = {"gamma": float(gamma)}
        weights = scores / scores.sum().clamp_min(1e-12)
        self.last_client_weights = weights.tolist()
        result = (weights[:, None] * transformed).sum(0)
        if self.method == "balanced_splice":
            residual = torch.stack([x - torch.dot(x, root) / (root_norm ** 2) * root
                                    for x in inputs]).mean(0)
            residual = residual * min(1.0, self.splice_ratio * root_norm.item()
                                      / (residual.norm().item() + 1e-12))
            result = result + residual
        if not torch.isfinite(result).all():
            raise ValueError("non-finite root baseline output")
        return result

    def get_attack_stats(self):
        return self.last_stats
