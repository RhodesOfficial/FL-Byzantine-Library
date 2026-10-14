"""Small independent checks run inside the sole bounded measurement process."""

import numpy as np

from direction_a.class_gradient_full import aggregate, compare, direct_class_sum


def run_checks(budget):
    # Equal logits: one source [1,2], three source [3,0]; known n=[1,3] mean.
    C = 2
    w, b = np.zeros((C, 128)), np.zeros(C)
    z = np.zeros((4, 128)); z[:, :2] = [[1, 2], [3, 0], [3, 0], [3, 0]]
    sums = direct_class_sum(z, 0, w, b, budget)
    expected = np.zeros_like(w); expected[:, :2] = [[-5, -1], [5, 1]]
    assert np.array_equal(sums[0], expected)
    assert np.array_equal(sums[1], [-2, 2])
    sources = {i: {} for i in range(20)}
    counts = [[0, 0] for _ in range(20)]
    for i, rows in ((0, z[:1]), (1, z[1:])):
        sources[i][0] = tuple(x / len(rows) for x in direct_class_sum(rows, 0, w, b, budget))
        counts[i][0] = len(rows)
    sources[2][1] = tuple(x for x in direct_class_sum(z[:1], 1, w, b, budget))
    counts[2][1] = 1
    targets, provenance = aggregate(sources, counts, [4, 1], C, budget)
    assert np.array_equal(targets[0][0], expected / 4)
    assert provenance[0]["sources"] == [{"client_id": 0, "n_ic": 1, "a_ic": .25},
                                         {"client_id": 1, "n_ic": 3, "a_ic": .75}]
    compare((np.array([2e-6]),), (np.zeros(1),), "test-boundary", budget)
    try:
        compare((np.array([2.01e-6]),), (np.zeros(1),), "test-reject-old-debug-bound", budget)
    except RuntimeError:
        budget.progress.pop("failed_comparison", None)
    else:
        raise AssertionError("frozen tolerance was not enforced")
    return {"direct_outer_product_hand_constants": True, "unequal_source_weight_constants": True,
            "frozen_epsilon_boundary_and_rejection": True}
