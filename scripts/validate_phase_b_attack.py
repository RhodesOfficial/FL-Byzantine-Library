"""One fresh paired FedAvg label-flip validation; no core units or retries."""
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "easyFL")]
from scripts.run_phase_b import (OUT, PYTHON, SOURCE, build_manifest, create_runner,
                                digest, read, save, validate_task)


def metrics(curves):
    assert curves["round"] == list(range(0, 301, 10))
    totals = curves["class_total"]
    assert totals == [1000] * 10
    assert len(curves["class_correct"]) == len(curves["class_loss_mean"]) == 31
    assert curves["learning_rate_used"] == [0.1] * 31
    overall = [sum(c) / sum(totals) for c in curves["class_correct"]]
    tail = [(c[8] / totals[8] + c[9] / totals[9]) / 2 for c in curves["class_correct"]]
    return {"M_final": overall[-1], "T_final": tail[-1],
            "M_last5": math.fsum(overall[-5:]) / 5,
            "T_last5": math.fsum(tail[-5:]) / 5}


def pooled_activity(rows):
    total = nonzero = 0
    for row in rows:
        n, fraction = row["malicious"], row["malicious_nonzero_fraction"]
        assert isinstance(n, int) and 0 <= n <= 40
        if n == 0:
            assert fraction is None
            continue
        assert math.isfinite(fraction) and 0 <= fraction <= 1
        count = round(fraction * n)
        assert math.isclose(count, fraction * n, abs_tol=1e-10)
        total += n
        nonzero += count
    return {"nonzero_uploads": nonzero, "malicious_uploads": total,
            "fraction": nonzero / total if total else None}


def judge(attack, baseline, intervals):
    conditions = {}
    for name, threshold in (("M", 0.451), ("T", 0.137)):
        endpoint = attack[name + "_final"] <= threshold
        direction = attack[name + "_last5"] < baseline[name + "_last5"]
        conditions[name] = {"endpoint_threshold": threshold, "endpoint_pass": endpoint,
                            "direction_pass": direction, "same_metric_pass": endpoint and direction}
    active = all(v["fraction"] is not None and v["fraction"] >= 0.8 for v in intervals.values())
    return {"metrics": conditions, "endpoint_pass": any(v["endpoint_pass"] for v in conditions.values()),
            "same_metric_direction_pass": any(v["same_metric_pass"] for v in conditions.values()),
            "activity_pass": active,
            "passed": active and any(v["same_metric_pass"] for v in conditions.values())}


def audit_labels(runner):
    import numpy as np
    import torch
    from aggregators.d1_category_coverage import _preserve_global_rng
    from attacks.flgo_label_flip import LabelFlippedDataset

    def original_label(dataset, index):
        while isinstance(dataset, torch.utils.data.Subset):
            index, dataset = int(dataset.indices[index]), dataset.dataset
        assert not isinstance(dataset, LabelFlippedDataset)
        return int(dataset.targets[index])

    expected = frozenset(int(i) for i in np.random.default_rng(101).choice(100, 30, replace=False))
    assert runner.byz_malicious_ids == expected
    counts = {"malicious_train_labels_checked": 0, "honest_train_labels_checked": 0,
              "root_labels_checked": 0, "test_labels_checked": 0}
    # Dataset inspection is protected and does not evaluate the model.
    with _preserve_global_rng():
        for client in runner.clients:
            malicious = client.id in expected
            dataset = client.train_data
            assert isinstance(dataset, LabelFlippedDataset) == malicious
            source = dataset.source if malicious else dataset
            if malicious:
                assert dataset.num_classes == 10
            for index in range(len(dataset)):
                original = original_label(source, index)
                assert int(dataset[index][-1]) == ((original + 1) % 10 if malicious else original)
            counts["malicious_train_labels_checked" if malicious else "honest_train_labels_checked"] += len(dataset)
        # Load a separate root view for inspection; do not initialize aggregation state early.
        from flgo_byzantine.root_data import load_root_data
        root, _ = load_root_data(runner.task, runner.gv.TaskPipe)
        for name, dataset in (("root", root), ("test", runner.test_data)):
            assert not isinstance(dataset, LabelFlippedDataset)
            for index in range(len(dataset)):
                assert int(dataset[index][-1]) == original_label(dataset, index)
            counts[name + "_labels_checked"] = len(dataset)
    return dict(counts, malicious_ids=sorted(expected), cyclic_mapping="(y+1)%10",
                applies_from_round=1, global_rng_protected=True)


def capture_existing_evaluations(runner, directory):
    import torch
    logger = runner.gv.logger
    original = logger.log_once
    curves = {"class_total": None, "round": [], "learning_rate_used": [],
              "class_correct": [], "class_loss_mean": []}
    runner.calculator.collect_class_stats = True

    def log_once(*args, **kwargs):
        original(*args, **kwargs)  # Exactly the original evaluation forward and loader.
        stats = runner.calculator.last_class_statistics
        accuracy, loss = logger.output["test_accuracy"][-1], logger.output["test_loss"][-1]
        assert math.isfinite(accuracy) and 0 <= accuracy <= 1
        assert math.isfinite(loss) and loss >= 0
        assert all(torch.isfinite(v).all().item() for v in runner.model.state_dict().values())
        total, correct, losses = (stats[k] for k in ("class_total", "class_correct", "class_loss_mean"))
        assert total == [1000] * 10 and len(correct) == len(losses) == 10
        assert all(isinstance(c, int) and 0 <= c <= n for c, n in zip(correct, total))
        assert all(math.isfinite(v) and v >= 0 for v in losses)
        assert sum(correct) / sum(total) == accuracy
        assert math.isclose(math.fsum(n * v for n, v in zip(total, losses)) / sum(total),
                            loss, abs_tol=1e-6, rel_tol=1e-5)
        round_number = 0 if not curves["round"] else int(runner.current_round)
        assert round_number == len(curves["round"]) * 10
        assert runner.learning_rate == 0.1
        curves["class_total"] = total
        curves["round"].append(round_number)
        curves["learning_rate_used"].append(float(runner.learning_rate))
        curves["class_correct"].append(correct)
        curves["class_loss_mean"].append(losses)
        save(directory / "class_curves.json", curves)
        print(f"CHECKPOINT round={round_number} accuracy={accuracy:.6f} loss={loss:.6f}", flush=True)

    logger.log_once = log_once
    return curves


def main():
    start = time.perf_counter()
    import torch
    assert Path(sys.executable).resolve() == PYTHON.resolve()
    assert torch.cuda.is_available() and torch.__version__.startswith("2.5.1")
    assert os.environ.get("CUBLAS_WORKSPACE_CONFIG") is None
    assert not torch.backends.cudnn.deterministic and not torch.backends.cudnn.benchmark
    assert not torch.are_deterministic_algorithms_enabled()
    assert not subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True).strip()
    manifest = read(OUT / "manifest.json")
    current = build_manifest()
    run_commit = current["source_commit"]
    current["source_commit"] = manifest["source_commit"]
    assert current == manifest  # Preserve setup provenance while recording this script's commit.
    record = manifest["tasks"]["101"]
    validate_task(record)
    baseline_path = SOURCE.parent / "seed_101/class_curves.json"
    baseline = metrics(read(baseline_path))
    for key, value in {"M_final": .501, "T_final": .187, "M_last5": .48198, "T_last5": .1626}.items():
        assert math.isclose(baseline[key], value, abs_tol=1e-12)
    directory = OUT / "attack_validation_seed_101"
    runner = create_runner(manifest, 101, "avg", directory)
    runtime = {"torch_version": torch.__version__, "cuda_version": torch.version.cuda,
               "gpu": torch.cuda.get_device_name(0), "cudnn_deterministic": torch.backends.cudnn.deterministic,
               "cudnn_benchmark": torch.backends.cudnn.benchmark,
               "deterministic_algorithms": torch.are_deterministic_algorithms_enabled(),
               "CUBLAS_WORKSPACE_CONFIG": os.environ.get("CUBLAS_WORKSPACE_CONFIG")}
    assert not runtime["cudnn_deterministic"] and not runtime["cudnn_benchmark"]
    assert not runtime["deterministic_algorithms"] and runtime["CUBLAS_WORKSPACE_CONFIG"] is None
    save(directory / "run_manifest.json", {"source_commit": run_commit,
         "b_manifest_sha256": digest(OUT / "manifest.json"), "b_setup_commit": manifest["source_commit"],
         "task": record, "baseline_curves": str(baseline_path), "baseline_sha256": digest(baseline_path),
         "options": runner.option, "runtime": runtime, "from_scratch": True})
    labels = audit_labels(runner)
    save(directory / "label_audit.json", labels)
    print("LABEL_AUDIT_PASS " + str(labels), flush=True)
    curves = capture_existing_evaluations(runner, directory)
    paired_iterate = runner.iterate

    def checked_iterate():
        value = paired_iterate()
        row = runner.full_round_stats[-1]
        assert row["received"] == 40 and row["aggregator"] == "avg" and row["attack"] == "label_flip"
        assert row["malicious"] == sum(cid in runner.byz_malicious_ids for cid in runner.received_clients)
        pooled_activity([row])
        if len(runner.phase_b_participants) == 10:
            assert row["malicious"] == 21
            print("ROUND10_PRESERVED malicious=21 received=40", flush=True)
        return value

    runner.iterate = checked_iterate
    training_start = time.perf_counter()
    runner.run()
    training_seconds = time.perf_counter() - training_start
    assert runner.current_round == 301
    assert len(runner.full_round_stats) == len(runner.phase_b_participants) == 300
    attack = metrics(curves)
    intervals = {f"{a}-{b}": pooled_activity(runner.full_round_stats[a-1:b])
                 for a, b in ((151, 200), (201, 250), (251, 300))}
    diagnostics = [json.loads(line) for line in
                   (directory / "diagnostic_log.jsonl").read_text(encoding="utf-8").splitlines()]
    assert len(diagnostics) == 300
    for i, row in enumerate(diagnostics):
        assert row["round"] == i + 1 and not row["nonfinite_fields"]
        assert row["received_client_ids"] == runner.phase_b_participants[i]
        assert row["malicious_nonzero_fraction"] == runner.full_round_stats[i]["malicious_nonzero_fraction"]
    validate_task(record)
    verdict = judge(attack, baseline, intervals)
    torch.save(runner.model.state_dict(), directory / "final_model.pt")
    save(directory / "result.json", {"seed": 101, "method": "FedAvg", "attack": "label_flip",
         "rounds": 300, "options": runner.option, "participants": runner.phase_b_participants,
         "round_stats": runner.full_round_stats, "per_class_accuracy": [v / 1000 for v in curves["class_correct"][-1]],
         "attack_metrics": attack, "baseline_metrics": baseline, "activity_intervals": intervals,
         "verdict": verdict, "integrity_passed": True, "participant_pairing_passed": True,
         "training_seconds": training_seconds, "wall_seconds": time.perf_counter() - start})
    print("VALIDATION_COMPLETE " + str(dict(attack=attack, intervals=intervals, verdict=verdict)), flush=True)


if __name__ == "__main__":
    main()
