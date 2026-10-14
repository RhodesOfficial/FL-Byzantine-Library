"""Independent hand constants and scalar differences for the smoke path."""

import math

import numpy as np
import torch

from direction_a.class_gradient_smoke import analytic_gradient, head_gradient, weighted_partial


def run_oracles(budget):
    z = torch.tensor([[1., 2.]], dtype=torch.float64)
    w, b = torch.zeros(3, 2, dtype=torch.float64), torch.zeros(3, dtype=torch.float64)
    labels = torch.tensor([0])
    expected_w = np.array([[-2/3, -4/3], [1/3, 2/3], [1/3, 2/3]])
    expected_b = np.array([-2/3, 1/3, 1/3])
    for with_bias in (True, False):
        actual = head_gradient(z, labels, w, b if with_bias else None, budget)
        gold = analytic_gradient(z.numpy(), labels.numpy(), w.numpy(), b.numpy() if with_bias else None, budget)
        assert np.max(np.abs(actual[0] - expected_w)) < 1e-12
        assert np.max(np.abs(gold[0] - expected_w)) < 1e-12
        assert len(actual) == (2 if with_bias else 1)
        if with_bias:
            assert np.max(np.abs(actual[1] - expected_b)) < 1e-12
            assert np.max(np.abs(gold[1] - expected_b)) < 1e-12
    # One sample at source 0, three [3,0] samples at source 1: n=[1,3].
    second = (np.array([[-2., 0.], [1., 0.], [1., 0.]]), expected_b)
    partial = weighted_partial({0: {0: (expected_w, expected_b)}, 1: {0: second}},
                               [[1, 0, 0], [3, 0, 0]], [4, 1, 1], 3, 2)
    assert np.max(np.abs(partial[0]["weight"] - np.array([[-5/3, -1/3], [5/6, 1/6], [5/6, 1/6]]))) < 1e-12
    assert np.max(np.abs(partial[0]["bias"] - expected_b)) < 1e-12
    assert partial[1]["selected_source_ids"] == []  # arithmetic placeholder is NOT a gradient request
    before = dict(budget.counts)
    try:
        head_gradient(z[:0], labels[:0], w, b, budget)
        raise AssertionError("empty class accepted")
    except ValueError:
        pass
    assert budget.counts == before
    # Independent scalar log-sum-exp CE finite differences, nonzero logits.
    zz = np.array([[.2, -.4], [1., .5]])
    ww, bb = np.array([[.3, -.2], [-.1, .4], [.2, .1]]), np.array([.2, -.3, .1])
    yy = np.array([0, 2])
    analytical = analytic_gradient(zz, yy, ww, bb, budget)

    def scalar_loss(weight, bias):
        total = 0.
        for row, label in zip(zz, yy):
            scores = [sum(float(weight[c,j])*float(row[j]) for j in range(2)) + float(bias[c]) for c in range(3)]
            highest = max(scores)
            total += highest + math.log(sum(math.exp(v-highest) for v in scores)) - scores[label]
        return total / 2

    h, errors = 1e-5, []
    for idx in np.ndindex(ww.shape):
        plus, minus = ww.copy(), ww.copy()
        plus[idx] += h
        minus[idx] -= h
        errors.append(abs((scalar_loss(plus, bb)-scalar_loss(minus, bb))/(2*h)-analytical[0][idx]))
    for idx in range(3):
        plus, minus = bb.copy(), bb.copy()
        plus[idx] += h
        minus[idx] -= h
        errors.append(abs((scalar_loss(ww, plus)-scalar_loss(ww, minus))/(2*h)-analytical[1][idx]))
    assert max(errors) < 1e-8
    return {"hand_zero_logits_complete_output_bias_and_no_bias": True,
            "two_source_counts_1_3_weighted_Gc_hand_constants": True,
            "missing_class_rejected_without_query": True,
            "independent_scalar_finite_difference_step": h, "finite_difference_max_absolute_error": max(errors)}
