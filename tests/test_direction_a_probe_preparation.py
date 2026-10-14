"""Independent analytic/forward checks within the one authorized preparation."""

import math

import numpy as np
import torch

from direction_a.probe_preparation import (balanced_loss, differences, finite, permute_labels,
                                          split_train, summarize, uniform_control)


def run_checks(budget):
    # Unequal frequencies deliberately separate class-balanced CE from sample CE.
    logits = torch.tensor([[math.log(3), 0.], [0., math.log(3)], [0., math.log(3)], [0., math.log(3)]])
    y = torch.tensor([0, 0, 0, 1])
    budget.consume("forwards")
    actual = float(balanced_loss(logits, y, torch.tensor([3., 1.])).item())
    expected = ((math.log(4/3) + 2*math.log(4))/3 + math.log(4/3))/2
    sample_ce = (2*math.log(4/3) + 2*math.log(4))/4
    assert abs(actual-expected) < 2e-7 and abs(actual-sample_ce) > .1
    budget.consume("forwards")
    assert abs(float(balanced_loss(torch.zeros(300, 100), torch.arange(100).repeat(3),
                                  torch.full((100,), 3.)).item())-math.log(100)) < 1e-6
    try:
        finite([torch.tensor(float("nan"))], budget)
    except RuntimeError:
        pass
    else:
        raise AssertionError("non-finite objective accepted")
    # Exact scalar predictions verify denominators, macro vs micro, and zeros.
    budget.consume("forwards")
    metrics = summarize(logits, y, {"head": [0], "middle": [1], "tail": [1]}, budget)
    assert metrics["per_class"][0]["correct"] == 1 and metrics["per_class"][0]["sample_denominator"] == 3
    assert abs(metrics["groups"]["all"]["macro_recall_percent"]-200/3) < 1e-10
    zero = summarize(torch.tensor([[1., 0.], [1., 0.]]), torch.tensor([0, 1]),
                     {"head": [0], "middle": [1], "tail": [1]}, budget)
    assert zero["groups"]["tail"]["macro_recall_percent"] == 0.
    u = uniform_control(2, [3, 1], {"head": [0], "middle": [1], "tail": [1]})
    assert u["expected_recall_percent"] == 50 and u["CE"] == math.log(2)
    assert abs(differences(metrics, {"uniform": u})["uniform"]["all"] - 50/3) < 1e-10
    indices, labels = np.arange(100, 115), np.array([0]*10 + [1]*5)
    split = split_train(indices[::-1], labels[::-1], 2, budget)
    # Independent PCG64 sequence, including the stream continuing into class 1.
    rng = np.random.default_rng(20261014)
    expected_cal = sorted(np.r_[rng.permutation(np.arange(100, 110))[:2],
                                rng.permutation(np.arange(110, 115))[:1]].tolist())
    assert split["calibration_global_indices"] == expected_cal
    assert split == split_train(indices, labels, 2, budget)
    assert set(split["fit_global_indices"]).isdisjoint(split["calibration_global_indices"])
    assert len(split["fit_global_indices"]) == 12
    for bad_indices, bad_labels in ((np.array([0, 0, 1, 2]), np.array([0, 0, 1, 1])),
                                   (np.arange(4), np.array([0, 0, 1, 1]))):
        try:
            split_train(bad_indices, bad_labels, 2, budget)
        except RuntimeError:
            pass
        else:
            raise AssertionError("invalid isolation was accepted")
    permuted = permute_labels(labels, 2, 2026101401, budget)
    assert np.array_equal(permuted, np.random.default_rng(2026101401).permutation(labels))
    assert not np.array_equal(permuted, labels) and np.array_equal(np.bincount(labels), np.bincount(permuted))
    return dict(class_balanced_loss_independent_constants=True, differs_from_sample_mean=True,
                metric_scalar_denominators_and_zero_retention=True, analytic_uniform_and_pp=True,
                dataset_local_PCG64_sorted_class_split=True, disjoint_exact_cover=True,
                duplicate_and_insufficient_support_rejected=True, exact_global_label_permutation=True,
                full_100_class_zero_logit_objective=True, nonfinite_rejected=True,
                optimizer_updates=0, backwards=0)
