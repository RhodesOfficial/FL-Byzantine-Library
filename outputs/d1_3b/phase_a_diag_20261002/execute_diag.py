"""Replay unchanged p40 units, collecting statistics in the existing evaluation."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
SOURCE = ROOT / "outputs/d1_3b/phase_a_ir5_20261002"
BASELINE = ROOT / "outputs/d1_3b/phase_a_ir5_p40_20261002"
PYTHON = Path(r"E:\anaconda3\python.exe")
SEEDS = (101, 102, 103)
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "easyFL"))


def now():
    return datetime.now(timezone.utc).isoformat()


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False),
                    encoding="utf-8")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_task(seed, record):
    task = Path(record["task"])
    assert task == SOURCE / f"seed_{seed}" / "task" and task.is_dir()
    for filename, key in (("info", "info_sha256"), ("data.json", "data_sha256")):
        assert digest(task / filename) == record[key]
    info = json.loads((task / "info").read_text(encoding="utf-8"))
    assert info["root_data"]["imbalance_ratio"] == 5 and "dir1.00" in info["partitioner"]
    assert info["num_clients"] == 100
    return task


def trajectory_observations(round_number, accuracy, loss, old_accuracy, old_loss, previous):
    """Historical observations only; never decide whether training should stop."""
    flags, exceeded = [], {}
    for metric, current, historical, threshold in (
            ("accuracy", accuracy, old_accuracy, 0.005),
            ("loss", loss, old_loss, max(1e-3, 0.005 * abs(old_loss)))):
        difference = current - historical
        exceeded[metric] = abs(difference) > threshold
        if exceeded[metric]:
            flags.append({"round": round_number, "metric": metric,
                          "difference": difference, "threshold": threshold,
                          "persistent": bool(previous.get(metric, False))})
    return flags, exceeded


def assert_model_finite(model):
    import torch
    assert all(torch.isfinite(value).all().item() for value in model.state_dict().values())


def make_logger(directory, baseline_record=None, collect_class_stats=True):
    from flgo.experiment.logger.simple_logger import SimpleLogger

    class OutputLogger(SimpleLogger):
        def get_output_path(self):
            return str(directory / "record")

        def get_log_path(self):
            return str(directory / "log")

        def initialize(self):
            super().initialize()
            self.class_curves = {"class_total": None, "round": [],
                                 "learning_rate_used": [], "class_correct": [],
                                 "class_loss_mean": [], "trajectory_flags": []}
            self._trajectory_exceeded = {}

        def log_once(self, *args, **kwargs):
            super().log_once(*args, **kwargs)
            accuracy = self.output["test_accuracy"][-1]
            loss = self.output["test_loss"][-1]
            assert math.isfinite(accuracy) and 0 <= accuracy <= 1
            assert math.isfinite(loss) and loss >= 0
            assert_model_finite(self.coordinator.model)
            if not collect_class_stats:
                assert not getattr(self.coordinator.calculator, "collect_class_stats", False)
                return
            stats = self.coordinator.calculator.last_class_statistics
            curves = self.class_curves
            index = len(curves["round"])
            round_number = 0 if index == 0 else self.coordinator.current_round
            assert round_number == index * 10
            total = stats["class_total"]
            assert len(total) == len(stats["class_correct"]) == len(stats["class_loss_mean"]) == 10
            assert all(isinstance(n, int) and n > 0 for n in total)
            assert sum(total) == len(self.coordinator.test_data)
            assert all(isinstance(c, int) and 0 <= c <= n for c, n in zip(stats["class_correct"], total))
            assert all(math.isfinite(v) and v >= 0 for v in stats["class_loss_mean"])
            if curves["class_total"] is None:
                curves["class_total"] = total
            assert total == curves["class_total"]
            assert sum(stats["class_correct"]) / sum(total) == accuracy
            weighted_loss = sum(n * v for n, v in zip(total, stats["class_loss_mean"])) / sum(total)
            assert math.isclose(weighted_loss, loss, rel_tol=1e-5, abs_tol=1e-6)
            rate = float(self.coordinator.learning_rate)
            assert math.isfinite(rate) and rate == 0.1
            assert all(float(c.learning_rate) == rate for c in self.coordinator.clients)
            curves["round"].append(round_number)
            curves["learning_rate_used"].append(rate)
            curves["class_correct"].append(stats["class_correct"])
            curves["class_loss_mean"].append(stats["class_loss_mean"])
            if baseline_record is not None:
                old_accuracy = baseline_record["test_accuracy"][index]
                old_loss = baseline_record["test_loss"][index]
                flags, self._trajectory_exceeded = trajectory_observations(
                    round_number, accuracy, loss, old_accuracy, old_loss,
                    self._trajectory_exceeded)
                curves["trajectory_flags"].extend(flags)
            save(directory / "class_curves.json", curves)

    return OutputLogger


def prepare():
    if (OUT / "manifest.json").exists() or any(OUT.glob("seed_*")):
        raise RuntimeError("Refusing to reuse existing training results")
    begin = time.perf_counter()
    original = json.loads((BASELINE / "manifest.json").read_text(encoding="utf-8"))
    tasks, options = {}, {}
    for seed in SEEDS:
        record = original["tasks"][str(seed)]
        validate_task(seed, record)
        value = dict(original["options"][str(seed)])
        assert value["proportion"] == 0.4 and value["num_rounds"] == 200
        assert value["num_epochs"] == 1 and value["learning_rate"] == 0.1
        assert value["batch_size"] == 64 and value["eval_interval"] == 10
        assert value["sample"] == "uniform" and value["num_parallels"] == 1
        tasks[str(seed)], options[str(seed)] = record, value
        (OUT / f"seed_{seed}").mkdir()
        print(f"TASK_REUSE_VERIFIED seed={seed}", flush=True)
    save(OUT / "manifest.json", {"prepared_at": now(), "python": str(PYTHON),
         "IR": 5, "alpha": 1.0, "num_clients": 100, "tasks_generated": False,
         "preparation_seconds": time.perf_counter() - begin,
         "tasks": tasks, "options": options})


def unit(seed):
    begin = time.perf_counter()
    import torch
    import flgo
    from flgo.algorithm import fedavg

    directory = OUT / f"seed_{seed}"
    manifest = json.loads((OUT / "manifest.json").read_text(encoding="utf-8"))
    record = manifest["tasks"][str(seed)]
    task = validate_task(seed, record)
    baseline_result = json.loads((BASELINE / f"seed_{seed}/result.json").read_text(encoding="utf-8"))
    baseline_files = list((BASELINE / f"seed_{seed}/record").glob("*.json"))
    assert len(baseline_files) == 1
    baseline_record = json.loads(baseline_files[0].read_text(encoding="utf-8"))
    for child_dir in ("record", "log"):
        (directory / child_dir).mkdir()
    assert torch.cuda.is_available() and torch.__version__.startswith("2.5.1")
    # This run must retain the original p40 environment, not switch-check settings.
    assert os.environ.get("CUBLAS_WORKSPACE_CONFIG") is None
    assert not torch.backends.cudnn.deterministic
    assert not torch.backends.cudnn.benchmark
    assert not torch.are_deterministic_algorithms_enabled()
    runner = flgo.init(str(task), fedavg, manifest["options"][str(seed)],
                       Logger=make_logger(directory, baseline_record))
    assert not torch.backends.cudnn.deterministic
    assert not torch.are_deterministic_algorithms_enabled()
    assert runner.num_clients == len(runner.clients) == 100 and runner.proportion == 0.4
    assert type(runner.model).__module__ == "flgo.benchmark.cifar10_classification.model.cnn"
    assert runner.option == baseline_record["option"]
    runner.calculator.collect_class_stats = True
    participants, timings = [], []
    iterate = runner.iterate

    def monitored_iterate():
        started = time.perf_counter()
        assert runner.learning_rate == 0.1
        assert all(c.learning_rate == 0.1 for c in runner.clients)
        value = iterate()
        assert_model_finite(runner.model)
        selected = [int(cid) for cid in runner.selected_clients]
        received = [int(cid) for cid in runner.received_clients]
        assert len(selected) == len(set(selected)) == 40 and selected == received
        if selected != baseline_result["participants"][len(participants)]:
            raise RuntimeError(f"PARTICIPANT_SEQUENCE_CHANGED round={runner.current_round}")
        participants.append(selected)
        timings.append(time.perf_counter() - started)
        return value

    runner.iterate = monitored_iterate
    started = time.perf_counter()
    runner.run()
    training_seconds = time.perf_counter() - started
    assert runner.current_round == 201 and len(participants) == 200
    assert participants == baseline_result["participants"]
    assert_model_finite(runner.model)
    curves = runner.gv.logger.class_curves
    assert curves["round"] == list(range(0, 201, 10))
    assert curves["class_total"] == [1000] * 10
    assert curves["learning_rate_used"] == [0.1] * 21
    correct, totals = curves["class_correct"][-1], curves["class_total"]
    per_class = [c / n for c, n in zip(correct, totals)]
    overall = sum(correct) / sum(totals)
    assert set(runner.gv.logger.output) == {"option", "client_datavol", "time", "test_accuracy", "test_loss"}
    validate_task(seed, record)
    torch.save(runner.model.state_dict(), directory / "final_model.pt")
    save(directory / "result.json", {"seed": seed, "method": "FedAvg", "attack": "none",
         "task": str(task), "rounds": 200, "per_class_accuracy": per_class,
         "overall_accuracy": overall, "class_correct": correct, "class_total": totals,
         "participants": participants, "elapsed_seconds": training_seconds,
         "wall_seconds": time.perf_counter() - begin, "round_seconds": timings,
         "torch_version": torch.__version__, "gpu_name": torch.cuda.get_device_name(0),
         "passed": per_class[8] >= 0.1 and per_class[9] >= 0.1})
    print(f"UNIT_COMPLETE seed={seed} class8={per_class[8]:.4f} class9={per_class[9]:.4f}", flush=True)


def run():
    started, stamp = time.perf_counter(), now()
    prepare()
    launch_started = time.perf_counter()
    children, streams, records = {}, {}, {}
    for seed in SEEDS:
        stream = (OUT / f"seed_{seed}" / "console.log").open("w", encoding="utf-8")
        streams[seed] = stream
        child_start = time.perf_counter()
        child = subprocess.Popen([str(PYTHON), "-B", "-u", str(Path(__file__).resolve()),
                                  "unit", "--seed", str(seed)], cwd=ROOT,
                                 stdout=stream, stderr=subprocess.STDOUT)
        children[seed] = (child, child_start)
        records[str(seed)] = {"pid": child.pid, "started_at": now()}
    save(OUT / "launch.json", {"started_at": now(), "processes": records})
    pending = set(SEEDS)
    while pending:
        for seed in tuple(pending):
            child, child_start = children[seed]
            code = child.poll()
            if code is not None:
                records[str(seed)].update(returncode=code, ended_at=now(),
                                         subprocess_wall_seconds=time.perf_counter() - child_start)
                streams[seed].close()
                pending.remove(seed)
                print(f"PROCESS_FINISHED seed={seed} returncode={code}", flush=True)
        if pending:
            time.sleep(1)
    save(OUT / "execution.json", {"started_at": stamp, "ended_at": now(),
          "total_wall_seconds": time.perf_counter() - started,
          "training_group_wall_seconds": time.perf_counter() - launch_started,
          "processes": records})
    return int(any(item["returncode"] for item in records.values()))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("run", "unit"))
    parser.add_argument("--seed", type=int, choices=SEEDS)
    args = parser.parse_args()
    assert Path(sys.executable).resolve() == PYTHON.resolve()
    try:
        sys.exit((run() if args.action == "run" else unit(args.seed)) or 0)
    except Exception:
        traceback.print_exc()
        sys.exit(1)
