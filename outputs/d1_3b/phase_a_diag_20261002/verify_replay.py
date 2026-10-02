"""Read-only post-run validation; does not import torch or invoke an evaluator."""
import json
import math
from execute_diag import OUT, BASELINE, SEEDS, validate_task, trajectory_observations


manifest = json.loads((OUT / "manifest.json").read_text(encoding="utf-8"))
execution = json.loads((OUT / "execution.json").read_text(encoding="utf-8"))
assert all(execution["processes"][str(s)]["returncode"] == 0 for s in SEEDS)
for seed in SEEDS:
    directory = OUT / f"seed_{seed}"
    result = json.loads((directory / "result.json").read_text(encoding="utf-8"))
    old_result = json.loads((BASELINE / f"seed_{seed}/result.json").read_text(encoding="utf-8"))
    curves = json.loads((directory / "class_curves.json").read_text(encoding="utf-8"))
    record_paths = list((directory / "record").glob("*.json"))
    old_paths = list((BASELINE / f"seed_{seed}/record").glob("*.json"))
    assert len(record_paths) == len(old_paths) == 1
    record = json.loads(record_paths[0].read_text(encoding="utf-8"))
    old_record = json.loads(old_paths[0].read_text(encoding="utf-8"))
    assert set(record) == set(old_record) == {"option", "client_datavol", "time", "test_accuracy", "test_loss"}
    assert record["option"] == old_record["option"]
    assert result["participants"] == old_result["participants"]
    assert len(result["participants"]) == 200
    assert all(len(ids) == len(set(ids)) == 40 for ids in result["participants"])
    assert set(curves) == {"class_total", "round", "learning_rate_used", "class_correct", "class_loss_mean", "trajectory_flags"}
    assert curves["round"] == record["time"] == old_record["time"] == list(range(0, 201, 10))
    assert curves["class_total"] == [1000] * 10
    assert curves["learning_rate_used"] == [0.1] * 21
    assert len(curves["class_correct"]) == len(curves["class_loss_mean"]) == 21
    assert len(record["test_accuracy"]) == len(record["test_loss"]) == 21
    loss_errors = []
    expected_flags, previous = [], {}
    for i in range(21):
        correct, losses = curves["class_correct"][i], curves["class_loss_mean"][i]
        accuracy, loss = record["test_accuracy"][i], record["test_loss"][i]
        assert math.isfinite(accuracy) and 0 <= accuracy <= 1
        assert math.isfinite(loss) and loss >= 0
        assert len(correct) == len(losses) == 10
        assert all(isinstance(c, int) and 0 <= c <= 1000 for c in correct)
        assert all(math.isfinite(v) and v >= 0 for v in losses)
        assert sum(correct) / 10000 == record["test_accuracy"][i]
        weighted_loss = sum(n * v for n, v in zip(curves["class_total"], losses)) / 10000
        loss_errors.append(abs(weighted_loss - record["test_loss"][i]))
        assert math.isclose(weighted_loss, record["test_loss"][i], rel_tol=1e-5, abs_tol=1e-6)
        flags, previous = trajectory_observations(
            curves["round"][i], accuracy, loss,
            old_record["test_accuracy"][i], old_record["test_loss"][i], previous)
        expected_flags.extend(flags)
        print(f"HISTORY_DIFF seed={seed} round={curves['round'][i]} "
              f"accuracy_difference_pp={100*(accuracy-old_record['test_accuracy'][i]):.9g} "
              f"loss_difference={loss-old_record['test_loss'][i]:.12g}")
    accuracy_delta = max(abs(a-b) for a, b in zip(record["test_accuracy"], old_record["test_accuracy"]))
    loss_delta = max(abs(a-b) for a, b in zip(record["test_loss"], old_record["test_loss"]))
    assert curves["trajectory_flags"] == expected_flags
    assert result["class_correct"] == curves["class_correct"][-1]
    validate_task(seed, manifest["tasks"][str(seed)])
    print(f"seed={seed} all_21_summaries_pass=True max_weighted_loss_error={max(loss_errors):.12g}")
    print(f"seed={seed} participants_equal=True rounds=200 selections_per_round=40 options_equal=True task_hashes_unchanged=True")
    print(f"seed={seed} aligned_points=21 max_accuracy_delta={accuracy_delta:.12g} max_loss_delta={loss_delta:.12g}")
    print(f"seed={seed} per_class_accuracy={result['per_class_accuracy']} overall_accuracy={result['overall_accuracy']}")
    print(f"seed={seed} class8={result['per_class_accuracy'][8]} baseline_class8={old_result['per_class_accuracy'][8]} "
          f"class9={result['per_class_accuracy'][9]} baseline_class9={old_result['per_class_accuracy'][9]}")
    print(f"seed={seed} subprocess_wall_seconds={execution['processes'][str(seed)]['subprocess_wall_seconds']:.6f}")
    print(f"seed={seed} info_sha256={manifest['tasks'][str(seed)]['info_sha256']} data_sha256={manifest['tasks'][str(seed)]['data_sha256']}")
print(f"total_wall_seconds={execution['total_wall_seconds']:.6f}")
print(f"training_group_wall_seconds={execution['training_group_wall_seconds']:.6f}")
print("ALL_INTERNAL_CHECKS_PASSED; historical differences are observations only")
