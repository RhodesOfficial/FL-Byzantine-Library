"""Independent scalar/reference assertions, called by the bounded 0.2 runner.

No test launches a model/scan without its supplied shared Budget.
"""

import math
from types import SimpleNamespace

import numpy as np

from direction_a.evaluation import summarize
from direction_a.task import TaskSpec, apportion, audit_task, build_task, class_groups, lt_counts


def run_data_oracles(budget):
    results = []
    budget.scan("oracle:hand_calculated_LT_and_apportionment")
    assert lt_counts(100, 3, 100) == [100, 10, 1]
    assert apportion(7, [0.5, 0.3, 0.2]).tolist() == [4, 2, 1]
    assert apportion(2, [0.25] * 4).tolist() == [1, 1, 0, 0]
    assert class_groups([9, 9, 6, 3, 2, 1]) == {"head": [0, 1], "middle": [2, 3], "tail": [4, 5]}
    results.append("LT constants, exact largest-remainder allocation and tie rules")

    budget.scan("oracle:hand_calculated_evaluation_denominators")
    matrix = [[2, 0, 0], [1, 1, 0], [0, 1, 1]]
    result = summarize(matrix, {"head": [0], "middle": [1], "tail": [2]},
                       [1, 1, 0, 2], [2, 1, 1, 2], [0, 2], [0, 2])
    assert result["sample_accuracy"] == 4 / 6
    assert result["macro_all_classes"]["value"] == 2 / 3
    assert result["macro_covered_classes"]["value"] == 3 / 4
    assert result["client_equal_mean"] == 5 / 8
    assert result["worst_10_percent_count"] == 1 and result["worst_10_percent_mean"] == 0
    assert result["minimum_client"] == 0 and result["tail_holder_mean"] == 1 / 4
    missing = summarize([[1, 0], [0, 0]], {"head": [0], "tail": [1]}, [0], [0], [], [0])
    assert missing["macro_all_classes"]["value"] is None
    assert missing["macro_all_classes"]["class_denominator"] == 2
    assert missing["macro_all_classes"]["missing_classes"] == [1]
    assert missing["client_equal_mean"] is None and missing["missing_test_clients"] == [0]
    results.append("scalar accuracy/recall/client/worst-decile/missing denominators")

    # A hand-authored fixture includes zero/single/multiple sources explicitly.
    source = SimpleNamespace(dataset="fixture", classes=3, file_hashes={},
                             train_labels=np.array([0] * 20 + [1] * 20 + [2] * 20),
                             test_labels=np.array([0] * 4 + [1] * 4 + [2] * 4))
    spec = TaskSpec("fixture", "oracle_smoke", 3, 2, 10, 2, 4)
    info, data, counts = build_task(source, spec, budget)
    result = audit_task(source, spec, data, counts, budget)
    assert result["training_class_counts"] == [10, 1, 1]
    assert result["train_total"] == 12 and result["validation_total"] == 6 and result["test_total"] == 12
    assert result["discarded_train_total"] == 42
    assert 1 in result["single_source_classes"] and 2 in result["single_source_classes"]
    # Detect corrupted conserved indices, independently of model tolerance.
    data["clients"][0]["train"].append(data["validation"][0])
    rejected = False
    try:
        audit_task(source, spec, data, counts, budget)
    except AssertionError:
        rejected = True
    assert rejected, "validation leakage must be rejected"
    results.append("hand-label fixture conservation and validation-leakage negative control")
    return results


def run_model_oracles(budget):
    import torch
    from direction_a.model import ResNet8Adapter, transform_images

    # Raw uint8=0 / 255 -> (0-mean)/std, and uint8=255 -> (1-mean)/std.
    pixels = np.zeros((2, 3, 32, 32), dtype=np.uint8)
    pixels[1] = 255
    for dataset, constants in (("CIFAR10", ((0.4914, 0.4822, 0.4465), (0.247, 0.243, 0.262))),
                               ("CIFAR100", ((0.5071, 0.4867, 0.4408), (0.2675, 0.2565, 0.2761)))):
        transformed = transform_images(pixels, dataset)
        mean, std = constants
        for c in range(3):
            assert abs(float(transformed[0, c, 0, 0]) - (-mean[c] / std[c])) < 3e-7
            assert abs(float(transformed[1, c, 0, 0]) - ((1 - mean[c]) / std[c])) < 3e-7

    torch.manual_seed(20261012)
    model = ResNet8Adapter(10).freeze_reference()
    # A hand-written head with only two nonzero feature coordinates.
    with torch.no_grad():
        model.head.weight.zero_()
        model.head.bias.zero_()
        model.head.weight[0, 0] = 2
        model.head.weight[0, 1] = -3
        model.head.bias[0] = 5
    features = torch.zeros(1, 128)
    features[0, 0], features[0, 1] = 4, -2
    logits = budget.forward("oracle:scalar_head_constant", lambda: model.head(features))
    assert logits.tolist() == [[19.0] + [0.0] * 9]  # 2*4 + (-3)*(-2) + 5
    # Uniform raw logits have CE=ln(10), from an independent scalar formula.
    loss = torch.nn.functional.cross_entropy(torch.zeros(1, 10), torch.tensor([7]))
    assert abs(float(loss) - math.log(10)) < 1e-7
    return ["uint8 transform scalar references", "head=19 hand calculation", "uniform-logits CE=ln(10)"]


def run_guard_oracles(budget):
    """Virtual limits/time only: no model, scan or file is launched by guards."""
    from unittest.mock import patch
    from direction_a.budget import Budget, LimitReached
    budget.scan("oracle:budget_guard_scalar_boundaries")
    limits = {"forwards": 3, "scans": 4, "artifact_bytes": 10, "retries": 1,
              "wall_seconds": 9, "phase_seconds": {"data": 4}}
    with patch.object(Budget, "save", lambda self: None), patch("direction_a.budget.time.monotonic", return_value=100):
        guard = Budget("virtual_guard_not_written.json", limits)
        guard.consume("forwards", "virtual1")
        guard.consume("forwards", "virtual2")
        rejected = False
        try:
            guard.consume("forwards", "virtual3")
        except LimitReached:
            rejected = True
        assert rejected and guard.hit == {"field": "forwards", "actual": 3}
        assert guard.counts["forwards"] == 2  # third action was never executed
        guard = Budget("virtual_guard_not_written.json", limits)
        guard.enter("data")
        guard.phase_started = 95
        rejected = False
        try:
            guard.check()
        except LimitReached:
            rejected = True
        assert rejected and guard.hit == {"field": "phase_seconds.data", "actual": 5}
        guard = Budget("virtual_guard_not_written.json", limits)
        guard.started = 91
        rejected = False
        try:
            guard.check()
        except LimitReached:
            rejected = True
        assert rejected and guard.hit == {"field": "wall_seconds", "actual": 9}
    return ["count bound stops before action", "phase-time bound", "total-time bound"]
