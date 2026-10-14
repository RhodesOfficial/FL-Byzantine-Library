"""Frozen v5 arithmetic. Synthetic checks never fit, backpropagate, or encode."""
import math
import numpy as np
import torch
import torch.nn.functional as F
from scipy.stats import beta
from direction_a.probe_preparation import ADAM, finite, permute_labels, summarize, uniform_control, differences

TRAIN_SEEDS = list(range(2026101501, 2026101600))
VAL_SEEDS = {"CIFAR10": 2026101701, "CIFAR100": 2026101702}
THRESHOLDS = {"CIFAR10": (30.1, 5.6), "CIFAR100": (7.9, 5.9)}


def validate_loss_inputs(logits, labels, counts):
    C = len(counts)
    if (logits.ndim != 2 or logits.shape != (len(labels), C) or labels.dtype != torch.int64 or
            not len(labels) or bool((counts <= 0).any()) or not bool(torch.isfinite(counts).all()) or
            int(labels.min()) < 0 or int(labels.max()) >= C or
            not torch.equal(torch.bincount(labels, minlength=C).to(counts), counts)):
        raise RuntimeError("complete class universe / positive exact loss denominators required")


def class_loss(logits, labels, counts):
    return (F.cross_entropy(logits, labels, reduction="none") / counts[labels]).sum() / len(counts)


def train_control(real, nulls):
    if len(nulls) != 99 or not np.isfinite([real, *nulls]).all():
        raise RuntimeError("exactly 99 finite empirical controls required")
    b = int(np.count_nonzero(np.asarray(nulls) >= real))
    return dict(tail_scores_percent=list(nulls), minimum_percent=min(nulls), maximum_percent=max(nulls),
                exceedances_ge_including_ties=b, plus_one_rank=(1+b)/100,
                exceedance_probability=b/99,
                clopper_pearson_95=[0. if b == 0 else float(beta.ppf(.025, b, 100-b)),
                                   1. if b == 99 else float(beta.ppf(.975, b+1, 99-b))],
                interpretation="empirical trained controls; rank is NOT a representation-no-information p value")


def tail_count(prediction, labels, tail):
    return int(np.count_nonzero((prediction == labels) & np.isin(labels, tail)))


def paired_permutation(predictions, labels, tail, seed, budget, repeats=9999):
    rng = np.random.default_rng(seed)
    denom = int(np.isin(labels, tail).sum())
    if denom == 0 or len({int(x) for x in np.bincount(labels)}) != 1:
        raise RuntimeError("fixed equal positive validation class denominators required")
    observed = [tail_count(p, labels, tail) for p in predictions]
    values = [[] for _ in predictions]
    for _ in range(repeats):
        shuffled = rng.permutation(labels)
        for j, pred in enumerate(predictions):
            budget.scan()
            values[j].append(tail_count(pred, shuffled, tail))
    result = []
    for obs, stats in zip(observed, values):
        b = sum(s >= obs for s in stats)
        p = (1+b)/(repeats+1)
        result.append(dict(seed=seed, observed_tail_correct=obs, tail_denominator=denom,
                           permuted_tail_correct=stats, exceedances_ge_including_ties=b,
                           p=p, p_adj=min(1., 4*p), multiplicity=4,
                           tail_recall_percent=[100*s/denom for s in stats]))
    return result


def paired_bootstrap(pairs, labels, tail, budget, repeats=2000, seed=20261016):
    rng = np.random.default_rng(seed)
    C = int(labels.max())+1
    positions = [np.flatnonzero(labels == c) for c in range(C)]
    if any(not len(p) for p in positions):
        raise RuntimeError("bootstrap missing a class")
    denom = sum(len(positions[c]) for c in tail)
    values = [[] for _ in pairs]
    for _ in range(repeats):
        # Sample ALL classes in ascending order, even when only tail is reported.
        sampled = [rng.choice(p, len(p), replace=True) for p in positions]
        selected = np.concatenate([sampled[c] for c in tail])
        y = labels[selected]
        for j, (original, real) in enumerate(pairs):
            budget.scan()
            R = 100*int(np.count_nonzero(real[selected] == y))/denom
            R0 = 100*int(np.count_nonzero(original[selected] == y))/denom
            values[j].append([R, R-R0])
    result = []
    for rows in values:
        array = np.asarray(rows)
        result.append(dict(seed=seed, repeats=repeats, quantile_method="linear", fixed_tail_denominator=denom,
                           R_delta_replicates_percent_pp=rows,
                           R_95=np.quantile(array[:, 0], [.025, .975], method="linear").tolist(),
                           delta_95=np.quantile(array[:, 1], [.025, .975], method="linear").tolist(),
                           delta_decision=np.quantile(array[:, 1], [.0125, .9875], method="linear").tolist()))
    return result


def science(dataset, R, R0, nulls, perm, interval, qualified):
    tau, delta = THRESHOLDS[dataset]
    conditions = dict(engineering_qualification=bool(qualified), R_ge_tau=R >= tau,
                      R_gt_chance=R > (10. if dataset == "CIFAR10" else 1.),
                      R_gt_all_99_train_controls=R > max(nulls), p_adj_le_05=perm["p_adj"] <= .05)
    sep = all(conditions.values())
    cal = dict(separability_PASS=sep, delta_ge_minimum=R-R0 >= delta,
               delta_q0125_gt_zero=interval["delta_decision"][0] > 0)
    return dict(R_percent=R, original_R_percent=R0, delta_pp=R-R0, tau_percent=tau, minimum_delta_pp=delta,
                separability_conditions=conditions, calibration_conditions=cal,
                separability="PASS" if sep else "FAIL", calibration_space="PASS" if all(cal.values()) else "FAIL")


def fit(features, labels, validation, true_labels, C, groups, budget):
    if features.dtype != torch.float32 or features.shape != (len(labels), 128):
        raise RuntimeError("unaltered float32 N by 128 features required")
    counts = torch.bincount(labels, minlength=C).float()
    validate_loss_inputs(torch.empty(len(labels), C, device=features.device), labels, counts)
    budget.scan(); budget.consume("fits")
    weight = torch.zeros(C, 128, device=features.device, requires_grad=True)
    bias = torch.zeros(C, device=features.device, requires_grad=True)
    optimizer = torch.optim.Adam([weight, bias], **ADAM)
    objectives = {}
    for step in range(1000):
        optimizer.zero_grad(set_to_none=True)
        budget.consume("forwards")
        objective = class_loss(F.linear(features, weight, bias), labels, counts)
        if step in (0, 100, 500):
            objectives[str(step)] = float(objective.detach())
        finite([objective, weight, bias], budget)
        budget.consume("backwards"); objective.backward()
        budget.consume("optimizer_steps"); optimizer.step()
    with torch.no_grad():
        budget.consume("forwards")
        objective = class_loss(F.linear(features, weight, bias), labels, counts)
        finite([objective, weight, bias], budget)
        objectives["1000"] = float(objective)
        budget.consume("forwards")
        logits = F.linear(validation, weight, bias)
        metrics = summarize(logits, true_labels, groups, budget)
        prediction = logits.argmax(1).cpu().numpy().astype(np.int16)
        ce = F.cross_entropy(logits, true_labels, reduction="none").cpu().numpy()
    d = (objectives["500"]-objectives["1000"])/max(abs(objectives["500"]), 1e-12)
    return dict(weight=weight.detach().cpu(), bias=bias.detach().cpu()), objectives, metrics, prediction, ce, dict(
        L1000_le_L0=objectives["1000"] <= objectives["0"], relative_change_500_1000=d,
        final_segment_still_changing=abs(d) > .01, convergence_certified=False)
