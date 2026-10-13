"""Independent hand references for ordinary aggregation/metric bookkeeping."""

import math
from unittest.mock import patch

import torch

from direction_a.backbone_preparation import aggregate_states, summarize_validation, PreparationBudget, PreparationLimit


def run_oracles(budget):
    budget.scan()
    states = [
        {"linear.weight": torch.tensor([[1.0]]), "linear.bias": torch.tensor([2.0]),
         "bn.running_mean": torch.tensor([0.0]), "bn.running_var": torch.tensor([1.0]),
         "bn.num_batches_tracked": torch.tensor(2, dtype=torch.int64)},
        {"linear.weight": torch.tensor([[5.0]]), "linear.bias": torch.tensor([6.0]),
         "bn.running_mean": torch.tensor([4.0]), "bn.running_var": torch.tensor([9.0]),
         "bn.num_batches_tracked": torch.tensor(5, dtype=torch.int64)},
    ]
    result = aggregate_states(states, [1, 3])
    assert result["linear.weight"].item() == 4  # (1*1+3*5)/4
    assert result["linear.bias"].item() == 5
    assert result["bn.running_mean"].item() == 3
    assert result["bn.running_var"].item() == 7
    assert result["bn.num_batches_tracked"].item() == 5
    assert result["bn.num_batches_tracked"].dtype == torch.int64
    assert states[0]["linear.weight"].item() == 1  # aggregation does not overwrite input
    rejected = False
    try:
        aggregate_states(states, [0, 3])
    except ValueError:
        rejected = True
    assert rejected
    metrics = summarize_validation([[2, 0, 0], [1, 1, 0], [0, 1, 1]], 6 * math.log(3),
                                   {"head": [0], "middle": [1], "tail": [2]})
    assert metrics["sample_accuracy_fraction"] == 4 / 6
    assert metrics["macro_recall"]["value_fraction"] == 2 / 3
    assert metrics["sample_denominator"] == 6 and metrics["class_sample_denominators"] == [2, 2, 2]
    assert abs(metrics["mean_cross_entropy"] - math.log(3)) < 1e-15
    assert metrics["group_macro_recall"]["tail"]["value_fraction"] == 1 / 2
    missing = summarize_validation([[1, 0], [0, 0]], 0, {"head": [0], "tail": [1]})
    assert missing["macro_recall"]["value_fraction"] is None
    assert missing["macro_recall"]["class_denominator"] == 2
    assert missing["macro_recall"]["missing_classes"] == [1]
    # Scalar CE reference is independent of the model forward implementation.
    ce = torch.nn.functional.cross_entropy(torch.zeros(1, 10), torch.tensor([4]))
    assert abs(float(ce) - math.log(10)) < 1e-7
    return ["sample-weighted parameters/float BN buffers: manual constants; BN counter max=5",
            "independent confusion denominators/recall/CE; missing classes not removed",
            "uniform logits CE=ln(10); no model/gradient qualification test"]


def guard_oracles(budget):
    budget.scan()
    limits = {name: 10 for name in ("attempts", "optimizer_steps", "backwards", "forwards", "scans", "logical_copy_bytes", "retries")}
    limits.update(evidence_bytes=1000000, wall_seconds=9, phase_seconds={"training": 4},
                  per_run={"attempts": 3, "optimizer_steps": 3})
    with patch.object(PreparationBudget, "save", lambda self, reserved=False: None), patch("direction_a.backbone_preparation.time.monotonic", return_value=100):
        guard = PreparationBudget("virtual-not-written.json", limits)
        guard.consume("attempts", run_id="hand")
        guard.consume("attempts", run_id="hand")
        rejected = False
        try:
            guard.consume("attempts", run_id="hand")
        except PreparationLimit:
            rejected = True
        assert rejected and guard.run_counts["hand"]["attempts"] == 2
        guard = PreparationBudget("virtual-not-written.json", limits)
        guard.enter("training")
        guard.phase_started = 96
        rejected = False
        try:
            guard.check()
        except PreparationLimit:
            rejected = True
        assert rejected and guard.hit == {"field": "phase_seconds.training", "actual": 4}
        guard = PreparationBudget("virtual-not-written.json", limits)
        rejected = False
        try:
            guard.consume("logical_copy_bytes", 10)
        except PreparationLimit:
            rejected = True
        assert rejected and guard.counts["logical_copy_bytes"] == 0
    return ["per-run attempt, time and byte guards use hand boundary values; no real workload in guard fixtures"]
