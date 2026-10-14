"""Bounded G1.2 smoke measurements; no formal qualification or Server policy."""

import io
import math
import pickle
import time
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F

from direction_a.backbone_preparation import PreparationBudget, sha, windows_memory
from direction_a.model import transform_images


class SmokeBudget(PreparationBudget):
    def __init__(self, path, limits):
        super().__init__(path, limits)
        self.counts.update(feature_samples=0, class_gradient_requests=0)
        self.save()

    def check(self):
        super().check()
        peak = windows_memory()["peak_working_set_bytes"]
        if peak >= self.limits["windows_peak_working_set_bytes"]:
            self.stop("windows_peak_working_set_bytes", peak)


def head_gradient(z, labels, weight, bias, budget, reduction="mean"):
    """Differentiate cloned complete head, leaving the frozen model untouched."""
    if len(z) == 0:
        raise ValueError("missing class: no gradient request")
    budget.consume("class_gradient_requests")
    budget.consume("forwards")
    budget.consume("backwards")
    w = weight.detach().clone().requires_grad_(True)
    b = None if bias is None else bias.detach().clone().requires_grad_(True)
    loss = F.cross_entropy(F.linear(z.detach(), w, b), labels, reduction=reduction)
    if not torch.isfinite(loss):
        raise RuntimeError("non-finite CE")
    grads = torch.autograd.grad(loss, (w,) if b is None else (w, b))
    if not all(torch.isfinite(g).all() for g in grads):
        raise RuntimeError("non-finite head gradient")
    return tuple(g.detach().cpu().numpy().copy() for g in grads)


def analytic_gradient(z, labels, weight, bias, budget):
    """Independent NumPy float64 softmax CE formula; no PyTorch loss/autograd."""
    if len(z) == 0:
        raise ValueError("missing class: no analytic gradient")
    budget.scan()
    z, weight = np.asarray(z, np.float64), np.asarray(weight, np.float64)
    logits = z @ weight.T
    if bias is not None:
        logits += np.asarray(bias, np.float64)
    shifted = logits - logits.max(axis=1, keepdims=True)
    probabilities = np.exp(shifted)
    probabilities /= probabilities.sum(axis=1, keepdims=True)
    probabilities[np.arange(len(z)), np.asarray(labels, np.int64)] -= 1
    gw = probabilities.T @ z / len(z)
    return (gw,) if bias is None else (gw, probabilities.mean(axis=0))


def full_class_gradient(z, labels, weight, bias, budget, batch=128):
    sums = [np.zeros(tuple(weight.shape), np.float64), np.zeros(tuple(bias.shape), np.float64)]
    for start in range(0, len(z), batch):
        grads = head_gradient(z[start:start + batch], labels[start:start + batch], weight, bias, budget, "sum")
        for j, g in enumerate(grads):
            sums[j] += g.astype(np.float64)
    return tuple((value / len(z)).astype(np.float32) for value in sums)


def flatten(parts):
    return np.concatenate([np.asarray(g, np.float64).reshape(-1) for g in parts])


def compare_gradient(actual, reference, name, budget):
    budget.scan()
    if len(actual) != len(reference) or any(a.shape != b.shape for a, b in zip(actual, reference)):
        raise RuntimeError("complete-head shape mismatch")
    a, r = flatten(actual), flatten(reference)
    if not np.isfinite(a).all() or not np.isfinite(r).all():
        raise RuntimeError("non-finite comparison")
    delta, reference_linf = a - r, float(np.abs(r).max())
    scale = max(1.0, reference_linf)
    value = {"comparison": name, "absolute_Linf": float(np.abs(delta).max()),
             "difference_L2_Frobenius": float(np.linalg.norm(delta)), "reference_Linf": reference_linf,
             "scale": scale, "normalized_Linf": float(np.abs(delta).max()) / scale,
             "blocks": [{"shape": list(g.shape), "absolute_Linf": float(np.abs(np.asarray(g, np.float64) - h).max())}
                        for g, h in zip(actual, reference)]}
    if value["normalized_Linf"] >= 1e-4:
        raise RuntimeError("smoke debugging bound reached; do not enlarge epsilon: " + name)
    return value


def weighted_partial(class_gradients, n_ic, N_c, C, d):
    """Selected sources only; never label this partial contribution full G_c."""
    out = {}
    for c in range(C):
        w, b = np.zeros((C, d), np.float64), np.zeros(C, np.float64)
        contributors = []
        for i, by_class in class_gradients.items():
            if c in by_class:
                n = n_ic[i][c]
                if n <= 0 or N_c[c] <= 0:
                    raise RuntimeError("sealed count/source mismatch")
                w += n / N_c[c] * by_class[c][0]
                b += n / N_c[c] * by_class[c][1]
                contributors.append(i)
        out[c] = {"weight": w, "bias": b, "selected_source_ids": contributors,
                  "scope": "selected-client partial contribution, NOT full-population G_c"}
    return out


def selected_images(task, selected, budget):
    budget.scan()
    dataset = task["info"]["spec"]["dataset"]
    sources = task["info"]["source_file_sha256"]
    paths = sorted([Path(p) for p in sources if
                    (Path(p).name.startswith("data_batch_") if dataset == "CIFAR10" else Path(p).name == "train")],
                   key=lambda p: p.name)
    arrays, labels, verified = [], [], {}
    for path in paths:
        budget.check()
        raw = path.read_bytes()
        if sha(raw) != sources[str(path)]:
            raise RuntimeError("official train source changed: " + str(path))
        data = pickle.loads(raw, encoding="bytes")
        arrays.append(data[b"data"])
        labels.extend(data[b"labels"] if dataset == "CIFAR10" else data[b"fine_labels"])
        verified[str(path)] = sources[str(path)]
    images = np.concatenate(arrays).reshape(-1, 3, 32, 32)
    labels = np.asarray(labels, np.int64)
    clients = {}
    proxy = images.nbytes + labels.nbytes + sum(a.nbytes for a in arrays)
    for i in selected:
        row = task["data"]["clients"][i]
        indices = row["train"]
        expected = task["acceptance"]["client_train_totals"][i]
        if len(indices) != expected or row["id"] != f"client_{i:03d}":
            raise RuntimeError("sealed index/client identity mismatch")
        x = transform_images(images[indices], dataset)
        clients[i] = {"x": x, "y": torch.tensor(labels[indices], dtype=torch.long),
                      "indices": indices, "sealed_sample_count": expected}
        proxy += x.numel() * x.element_size() + len(indices) * 8
    if proxy >= budget.limits["cpu_tensor_proxy_bytes"]:
        budget.stop("cpu_tensor_proxy_bytes", proxy)
    return clients, {"verified_original_train_sha256": verified,
                     "cpu_resident_known_arrays_tensor_proxy_bytes": proxy,
                     "test_images_loaded": False, "validation_indices_used": False}


def encode_client(model, client, budget, batch=128):
    budget.scan()
    budget.consume("feature_samples", len(client["y"]))
    result = []
    with torch.no_grad():
        for start in range(0, len(client["y"]), batch):
            budget.consume("forwards")
            result.append(model.encode(client["x"][start:start + batch].to("cuda")))
    z = torch.cat(result).detach()
    if z.shape != (len(client["y"]), 128) or not torch.isfinite(z).all():
        raise RuntimeError("feature identity/dimension mismatch")
    return z


def feature_statistics(z, budget):
    budget.scan()
    norms = np.linalg.norm(z.detach().cpu().numpy().astype(np.float64), axis=1)
    return {"sample_denominator": len(norms), "feature_dim": z.shape[1], "norm": "Euclidean L2",
            "min": float(norms.min()), "max": float(norms.max()), "mean": float(norms.mean()),
            "rms": float(np.sqrt(np.mean(norms ** 2))), "median": float(np.median(norms)),
            "p95": float(np.quantile(norms, .95)), "quantile_rule": "NumPy linear interpolation",
            "use": "W02 diagnostic statistics only; no A3 radius/feature synthesis"}


def save_tensors(path, value, budget):
    stream = io.BytesIO()
    torch.save(value, stream)
    raw = stream.getvalue()
    digest = budget.write(path, raw, raw=True)
    return {"path": str(path), "sha256": digest, "bytes": len(raw)}


def to_tensors(value):
    if isinstance(value, np.ndarray):
        return torch.from_numpy(value.copy())
    if isinstance(value, dict):
        return {key: to_tensors(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [to_tensors(item) for item in value]
    return value


def timed(function):
    torch.cuda.synchronize()
    start = time.perf_counter()
    result = function()
    torch.cuda.synchronize()
    return result, time.perf_counter() - start


def epsilon_candidate(comparisons):
    maximum = max(row["normalized_Linf"] for row in comparisons)
    base = max(8 * np.finfo(np.float32).eps, 4 * maximum)
    decade = 10.0 ** math.floor(math.log10(base))
    candidate = math.ceil(base / decade) * decade
    return {"status": "candidate_only_NOT_frozen", "value": candidate,
            "machine_epsilon_float32": float(np.finfo(np.float32).eps),
            "observed_max_normalized_Linf": maximum, "unrounded_rule_value": float(base),
            "rule": "ceil to one decimal significant digit of max(8*float32_machine_epsilon, 4*max_observed)",
            "norm": "Linf on concatenated complete weight+bias; scale=max(1,Linf(reference))",
            "other_reported_norm": "L2/Frobenius difference, not a separate tolerance",
            "scope": "this CUDA float32 head CE on these four eval float32 feature references; NumPy float64 head oracle on same features",
            "excludes": ["encoder/feature gradients", "training mode", "other platforms/precisions", "estimator", "recovery", "formal acceptance"]}
