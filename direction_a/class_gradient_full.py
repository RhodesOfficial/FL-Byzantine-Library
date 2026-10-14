"""Frozen G1.2 full measurement arithmetic and cumulative budget guards."""

import time

import numpy as np
import torch

from direction_a.backbone_preparation import PreparationBudget, windows_memory
from direction_a.class_gradient_smoke import flatten

EPSILON = 2e-6


class FullBudget(PreparationBudget):
    def __init__(self, path, limits, started):
        super().__init__(path, limits)
        self.started = self.phase_started = started
        self.counts.update(feature_samples=0, client_scans=0, class_gradient_requests=0,
                           formal_runs=0, implementation_revisions=1, searches=0,
                           extra_encoded_positions=0)
        self.resources = {"gpu_allocated_peak_bytes": 0, "windows_working_set_peak_bytes": 0,
                          "cpu_known_arrays_tensor_proxy_peak_bytes": 0}
        self.save()

    def consume(self, field, amount=1, run_id=None):
        self.check()
        proposed = self.counts[field] + amount
        if proposed > self.limits[field]:
            self.stop(field, proposed)
        self.counts[field] = proposed

    def check(self):
        super().check()
        if not hasattr(self, "resources"):
            return
        gpu = torch.cuda.max_memory_allocated() if torch.cuda.is_initialized() else 0
        working = windows_memory()["peak_working_set_bytes"]
        self.resources["gpu_allocated_peak_bytes"] = max(gpu, self.resources["gpu_allocated_peak_bytes"])
        self.resources["windows_working_set_peak_bytes"] = max(working, self.resources["windows_working_set_peak_bytes"])
        for field, actual in (("gpu_allocated_bytes", gpu), ("windows_peak_working_set_bytes", working)):
            if actual >= self.limits[field]:
                self.stop(field, actual)

    def cpu_proxy(self, amount):
        self.resources["cpu_known_arrays_tensor_proxy_peak_bytes"] = max(
            amount, self.resources["cpu_known_arrays_tensor_proxy_peak_bytes"])
        if amount >= self.limits["cpu_tensor_proxy_bytes"]:
            self.stop("cpu_tensor_proxy_bytes", amount)

    def snapshot(self, now=None):
        value = super().snapshot(now)
        value["resources"] = getattr(self, "resources", {})
        return value


def compare(actual, reference, name, budget):
    budget.scan()
    if len(actual) != len(reference) or any(a.shape != b.shape for a, b in zip(actual, reference)):
        raise RuntimeError("complete-head shape mismatch: " + name)
    a, r = flatten(actual), flatten(reference)
    if not np.isfinite(a).all() or not np.isfinite(r).all():
        raise RuntimeError("non-finite gradient: " + name)
    delta = a - r
    absolute = float(np.abs(delta).max())
    scale = max(1., float(np.abs(r).max()))
    row = {"comparison": name, "absolute_Linf": absolute, "scale": scale,
           "normalized_Linf": absolute / scale, "difference_L2_Frobenius": float(np.linalg.norm(delta)),
           "epsilon": EPSILON}
    if row["normalized_Linf"] > EPSILON:
        budget.progress["failed_comparison"] = row
        raise RuntimeError("frozen 2e-6 tolerance exceeded: " + name)
    return row


def direct_class_sum(z, c, weight, bias, budget, batch=128):
    """Independent per-example NumPy float64 sums, never a per-client mean."""
    budget.scan()
    sums = [np.zeros(weight.shape, np.float64), np.zeros(bias.shape, np.float64)]
    for start in range(0, len(z), batch):
        budget.check()
        features = np.asarray(z[start:start + batch], np.float64)
        logits = features @ np.asarray(weight, np.float64).T + np.asarray(bias, np.float64)
        logits -= logits.max(axis=1, keepdims=True)
        residual = np.exp(logits)
        residual /= residual.sum(axis=1, keepdims=True)
        residual[:, c] -= 1.
        # Sum individual outer products, independently of class-mean matrix multiplication.
        for feature, error in zip(features, residual):
            sums[0] += error[:, None] * feature[None, :]
            sums[1] += error
    return sums


def aggregate(sources, counts, totals, C, budget):
    budget.scan()
    targets, provenance = {}, {}
    for c in range(C):
        parts = [np.zeros((C, 128), np.float64), np.zeros(C, np.float64)]
        rows = []
        for i in range(20):
            n = counts[i][c]
            if n:
                if c not in sources[i] or totals[c] <= 0:
                    raise RuntimeError("positive source missing")
                a = n / totals[c]
                for j in range(2):
                    parts[j] += a * sources[i][c][j].astype(np.float64)
                rows.append({"client_id": i, "n_ic": n, "a_ic": a})
            elif c in sources[i]:
                raise RuntimeError("missing class produced a message")
        error = abs(sum(row["a_ic"] for row in rows) - 1.)
        if sum(row["n_ic"] for row in rows) != totals[c] or error > 20 * np.finfo(np.float64).eps:
            raise RuntimeError("population count/weight mismatch")
        provenance[c] = {"N_c": totals[c], "sources": rows, "weight_sum_error": error}
        targets[c] = tuple(parts)
    return targets, provenance
