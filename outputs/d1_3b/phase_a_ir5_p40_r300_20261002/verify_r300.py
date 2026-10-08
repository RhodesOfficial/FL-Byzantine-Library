"""Read-only internal checks for all 31 points and history observations for 0-200 only."""
import json
import math
from execute_r300 import OUT, BASELINE, SEEDS, validate_task
from execute_diag import trajectory_observations

manifest = json.loads((OUT / "manifest.json").read_text(encoding="utf-8"))
execution = json.loads((OUT / "execution.json").read_text(encoding="utf-8"))
assert all(execution["processes"][str(seed)]["returncode"] == 0 for seed in SEEDS)
for seed in SEEDS:
    directory = OUT / f"seed_{seed}"
    result = json.loads((directory / "result.json").read_text(encoding="utf-8"))
    old_result = json.loads((BASELINE / f"seed_{seed}/result.json").read_text(encoding="utf-8"))
    curves = json.loads((directory / "class_curves.json").read_text(encoding="utf-8"))
    paths = list((directory / "record").glob("*.json"))
    old_paths = list((BASELINE / f"seed_{seed}/record").glob("*.json"))
    assert len(paths) == len(old_paths) == 1
    record = json.loads(paths[0].read_text(encoding="utf-8"))
    historical = json.loads(old_paths[0].read_text(encoding="utf-8"))
    assert set(record) == set(historical) == {"option", "client_datavol", "time", "test_accuracy", "test_loss"}
    assert record["option"] == dict(historical["option"], num_rounds=300)
    assert record["option"]["lr_scheduler"] == "-1" and not record["option"]["load_checkpoint"]
    assert result["rounds"] == len(result["participants"]) == len(result["round_seconds"]) == 300
    assert result["participants"][:200] == old_result["participants"]
    assert all(len(ids) == len(set(ids)) == 40 and all(0 <= cid < 100 for cid in ids) for ids in result["participants"])
    assert set(curves) == {"round", "learning_rate_used", "class_correct", "class_loss_mean", "class_total", "trajectory_flags"}
    assert curves["round"] == record["time"] == list(range(0, 301, 10))
    assert historical["time"] == curves["round"][:21] == list(range(0, 201, 10))
    assert curves["class_total"] == [1000]*10 and curves["learning_rate_used"] == [0.1]*31
    assert len(curves["class_correct"]) == len(curves["class_loss_mean"]) == 31
    assert len(record["test_accuracy"]) == len(record["test_loss"]) == 31
    flags, previous, errors = [], {}, []
    for index, round_number in enumerate(curves["round"]):
        accuracy, loss = record["test_accuracy"][index], record["test_loss"][index]
        correct, losses = curves["class_correct"][index], curves["class_loss_mean"][index]
        assert math.isfinite(accuracy) and 0 <= accuracy <= 1
        assert math.isfinite(loss) and loss >= 0
        assert len(correct) == len(losses) == 10
        assert all(isinstance(c, int) and 0 <= c <= 1000 for c in correct)
        assert all(math.isfinite(v) and v >= 0 for v in losses)
        assert sum(correct)/10000 == accuracy
        weighted_loss = sum(n*v for n,v in zip(curves["class_total"], losses))/10000
        errors.append(abs(weighted_loss-loss))
        assert math.isclose(weighted_loss, loss, abs_tol=1e-6, rel_tol=1e-5)
        if round_number <= 200:
            observed, previous = trajectory_observations(
                round_number, accuracy, loss,
                historical["test_accuracy"][index], historical["test_loss"][index], previous)
            flags.extend(observed)
            print(f"HISTORY_DIFF seed={seed} round={round_number} "
                  f"accuracy_difference_pp={100*(accuracy-historical['test_accuracy'][index]):.9g} "
                  f"loss_difference={loss-historical['test_loss'][index]:.12g}")
    assert curves["trajectory_flags"] == flags and all(f["round"] <= 200 for f in flags)
    assert result["class_correct"] == curves["class_correct"][-1]
    assert result["class_total"] == curves["class_total"]
    assert result["per_class_accuracy"] == [c/1000 for c in curves["class_correct"][-1]]
    assert result["overall_accuracy"] == record["test_accuracy"][-1]
    validate_task(seed, manifest["tasks"][str(seed)])
    print(f"seed={seed} internal_checks_pass=True rounds=300 eval_points=31 max_weighted_loss_error={max(errors):.12g}")
    print(f"seed={seed} first_200_participant_rounds_equal=True all_300_rounds_valid=True options_only_change=num_rounds")
    print(f"seed={seed} per_class_accuracy={result['per_class_accuracy']} overall_accuracy={result['overall_accuracy']}")
    print(f"seed={seed} trajectory_flags={json.dumps(flags)}")
    for index in range(26,31):
        c = curves["class_correct"][index]
        print(f"TAIL_POINT seed={seed} round={curves['round'][index]} class8={c[8]/1000} class9={c[9]/1000}")
    print(f"seed={seed} subprocess_wall_seconds={execution['processes'][str(seed)]['subprocess_wall_seconds']:.6f}")
print(f"total_wall_seconds={execution['total_wall_seconds']:.6f}")
print("ALL_INTERNAL_CHECKS_PASSED; history limited to 0-200 and does not determine pass/fail")
