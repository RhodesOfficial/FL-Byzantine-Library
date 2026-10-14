"""Train-only P preparation arithmetic; no dataset loader or encoder path."""

import math

import numpy as np
import torch
import torch.nn.functional as F

SPLIT_SEED = 20261014
PERMUTATION_SEEDS = list(range(2026101401, 2026101406))
STEPS = 200
ADAM = dict(lr=0.01, betas=(0.9, 0.999), eps=1e-8, weight_decay=0)


def split_train(indices, labels, classes, budget):
    """Sort within each class before consuming one dataset-local PCG64 stream."""
    indices, labels = np.asarray(indices, np.int64), np.asarray(labels, np.int64)
    budget.scan()
    if len(indices) != len(labels) or len(np.unique(indices)) != len(indices):
        raise RuntimeError("duplicate or mismatched train indices")
    if labels.min() < 0 or labels.max() >= classes:
        raise RuntimeError("train label outside class universe")
    rng, fit, calibration, denominators = np.random.default_rng(SPLIT_SEED), [], [], []
    for c in range(classes):
        budget.scan()
        shuffled = rng.permutation(np.sort(indices[labels == c]))
        k = max(1, int(math.floor(0.2 * len(shuffled))))
        if len(shuffled) - k < 2:
            raise RuntimeError(f"class {c} cannot support train-internal isolation")
        calibration.extend(shuffled[:k].tolist())
        fit.extend(shuffled[k:].tolist())
        denominators.append(dict(class_id=c, train=len(shuffled), fit=len(shuffled)-k, calibration=k))
    fit, calibration = sorted(fit), sorted(calibration)
    if set(fit) & set(calibration) or set(fit) | set(calibration) != set(indices.tolist()):
        raise RuntimeError("internal partition not an exact disjoint train cover")
    return dict(fit_global_indices=fit, calibration_global_indices=calibration,
                denominators=denominators, seed=SPLIT_SEED, ratio=0.2)


def permute_labels(labels, classes, seed, budget):
    budget.scan()
    result = np.random.default_rng(seed).permutation(labels)
    if not np.array_equal(np.bincount(result, minlength=classes), np.bincount(labels, minlength=classes)):
        raise RuntimeError("global label permutation changed frequencies")
    return result


def balanced_loss(logits, labels, counts):
    # Each class contributes exactly its mean CE / C, regardless of its count.
    return (F.cross_entropy(logits, labels, reduction="none") / counts[labels]).sum() / len(counts)


def finite(values, budget):
    budget.scan()
    if not bool(torch.stack([torch.isfinite(v).all() for v in values]).all().item()):
        raise RuntimeError("non-finite probe loss/parameters/gradients")


def summarize(logits, labels, groups, budget):
    """Percent recalls with all classes retained, including exact zeroes."""
    budget.scan()
    C = logits.shape[1]
    finite([logits], budget)
    ce = F.cross_entropy(logits, labels, reduction="none").double()
    n = torch.bincount(labels, minlength=C)
    k = torch.bincount(labels[logits.argmax(1) == labels], minlength=C)
    ce_sum = torch.zeros(C, dtype=torch.float64, device=labels.device).scatter_add_(0, labels, ce)
    if bool((n == 0).any().item()):
        raise RuntimeError("internal calibration missing a class")
    n, k, ce_sum = n.cpu().numpy(), k.cpu().numpy(), ce_sum.cpu().numpy()
    recalls, class_ce = 100. * k / n, ce_sum / n
    all_groups = {"all": list(range(C)), **groups}
    return dict(per_class=[dict(class_id=c, sample_denominator=int(n[c]), correct=int(k[c]),
                               CE=float(class_ce[c]), recall_percent=float(recalls[c])) for c in range(C)],
                groups={name: dict(macro_recall_percent=float(recalls[ids].mean()),
                                   macro_CE=float(class_ce[ids].mean()), class_denominator=len(ids),
                                   sample_denominator=int(n[ids].sum()), class_ids=ids)
                        for name, ids in all_groups.items()},
                sample_denominator=int(n.sum()), sample_CE=float(ce_sum.sum()/n.sum()),
                units={"CE": "natural-log nats", "recall": "percent", "difference": "percentage points"})


def uniform_control(classes, denominators, groups):
    all_groups = {"all": list(range(classes)), **groups}
    return dict(analytic=True, tie_argmax_used=False, CE=math.log(classes),
                expected_recall_percent=100./classes,
                per_class=[dict(class_id=c, sample_denominator=int(denominators[c]),
                                CE=math.log(classes), expected_recall_percent=100./classes) for c in range(classes)],
                groups={name: dict(macro_recall_percent=100./classes, macro_CE=math.log(classes),
                                   class_denominator=len(ids), sample_denominator=sum(denominators[c] for c in ids))
                        for name, ids in all_groups.items()})


def differences(real, controls):
    return {name: {g: real["groups"][g]["macro_recall_percent"] - value["groups"][g]["macro_recall_percent"]
                   for g in real["groups"]} for name, value in controls.items()}


def fit_head(features, labels, calibration, true_labels, classes, groups, budget):
    """Exactly 200 full-population steps; selfchecks never call this function."""
    budget.consume("fits")
    weight = torch.zeros((classes, features.shape[1]), dtype=torch.float32,
                         device=features.device, requires_grad=True)
    bias = torch.zeros(classes, dtype=torch.float32, device=features.device, requires_grad=True)
    budget.scan()
    counts = torch.bincount(labels, minlength=classes).to(torch.float32)
    if bool((counts < 2).any().item()):
        raise RuntimeError("fit missing class support")
    optimizer = torch.optim.Adam([weight, bias], **ADAM)
    objectives = {}
    for step in range(STEPS):
        optimizer.zero_grad(set_to_none=True)
        budget.consume("forwards")
        objective = balanced_loss(F.linear(features, weight, bias), labels, counts)
        if step in (0, 50, 100):
            objectives[str(step)] = float(objective.detach().item())
        finite([objective, weight, bias], budget)
        budget.consume("backwards")
        objective.backward()
        budget.consume("optimizer_steps")
        optimizer.step()
    with torch.no_grad():
        budget.consume("forwards")
        objective = balanced_loss(F.linear(features, weight, bias), labels, counts)
        finite([objective, weight, bias], budget)
        objectives["200"] = float(objective.item())
        budget.consume("forwards")
        metrics = summarize(F.linear(calibration, weight, bias), true_labels, groups, budget)
    return dict(weight=weight.detach().cpu(), bias=bias.detach().cpu()), objectives, metrics
