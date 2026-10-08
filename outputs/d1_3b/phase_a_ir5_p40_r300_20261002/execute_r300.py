"""Fresh 300-round FedAvg units; only num_rounds differs from the completed 200-round run."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
BASELINE = ROOT / "outputs/d1_3b/phase_a_diag_20261002"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "easyFL"))
sys.path.insert(0, str(BASELINE))
from execute_diag import PYTHON, SEEDS, now, save, validate_task, make_logger, assert_model_finite


def prepare():
    if (OUT / "manifest.json").exists() or any(OUT.glob("seed_*")):
        raise RuntimeError("Refusing to reuse any existing run outputs")
    begin = time.perf_counter()
    original = json.loads((BASELINE / "manifest.json").read_text(encoding="utf-8"))
    tasks, options = {}, {}
    for seed in SEEDS:
        record = original["tasks"][str(seed)]
        validate_task(seed, record)
        value = dict(original["options"][str(seed)])
        assert value["num_rounds"] == 200
        value["num_rounds"] = 300
        assert [k for k in value if value[k] != original["options"][str(seed)][k]] == ["num_rounds"]
        assert value["seed"] == seed and value["num_epochs"] == 1
        assert value["learning_rate"] == 0.1 and value["batch_size"] == 64
        assert value["proportion"] == 0.4 and value["eval_interval"] == 10
        assert value["sample"] == "uniform" and value["num_parallels"] == 1
        tasks[str(seed)], options[str(seed)] = record, value
        (OUT / f"seed_{seed}").mkdir()
        print(f"TASK_HASHES_VERIFIED seed={seed} only_option_change=num_rounds:200->300", flush=True)
    save(OUT / "manifest.json", {"prepared_at": now(), "python": str(PYTHON),
         "IR": 5, "alpha": 1.0, "num_clients": 100, "tasks_generated": False,
         "preparation_seconds": time.perf_counter()-begin, "tasks": tasks, "options": options})


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
    baseline_paths = list((BASELINE / f"seed_{seed}/record").glob("*.json"))
    assert len(baseline_paths) == 1
    baseline_record = json.loads(baseline_paths[0].read_text(encoding="utf-8"))
    assert baseline_record["time"] == list(range(0, 201, 10))
    assert len(baseline_result["participants"]) == 200
    for child in ("record", "log"):
        (directory / child).mkdir()
    assert torch.cuda.is_available() and torch.__version__.startswith("2.5.1")
    assert os.environ.get("CUBLAS_WORKSPACE_CONFIG") is None
    assert not torch.backends.cudnn.deterministic and not torch.backends.cudnn.benchmark
    assert not torch.are_deterministic_algorithms_enabled()
    runner = flgo.init(str(task), fedavg, manifest["options"][str(seed)],
                       Logger=make_logger(directory, baseline_record))
    assert runner.option == dict(baseline_record["option"], num_rounds=300)
    assert runner.num_rounds == 300 and runner.num_clients == len(runner.clients) == 100
    assert runner.proportion == 0.4 and runner.sample_option == "uniform"
    assert runner.learning_rate == 0.1 and runner.lr_scheduler_type == "-1"
    assert not runner.option["load_checkpoint"]
    assert not torch.backends.cudnn.deterministic and not torch.are_deterministic_algorithms_enabled()
    assert type(runner.model).__module__ == "flgo.benchmark.cifar10_classification.model.cnn"
    runner.calculator.collect_class_stats = True
    participants, timings = [], []
    iterate = runner.iterate

    def monitored_iterate():
        started = time.perf_counter()
        assert runner.learning_rate == 0.1 and runner.lr_scheduler_type == "-1"
        assert all(c.learning_rate == 0.1 for c in runner.clients)
        value = iterate()
        assert_model_finite(runner.model)
        selected = [int(cid) for cid in runner.selected_clients]
        received = [int(cid) for cid in runner.received_clients]
        assert len(selected) == len(set(selected)) == 40 and selected == received
        assert all(0 <= cid < 100 for cid in selected)
        index = len(participants)
        if index < 200 and selected != baseline_result["participants"][index]:
            raise RuntimeError(f"PARTICIPANT_SEQUENCE_CHANGED round={runner.current_round}")
        participants.append(selected)
        timings.append(time.perf_counter()-started)
        return value

    runner.iterate = monitored_iterate
    started = time.perf_counter()
    runner.run()
    training_seconds = time.perf_counter()-started
    assert runner.current_round == 301 and len(participants) == 300
    assert participants[:200] == baseline_result["participants"]
    assert_model_finite(runner.model)
    curves = runner.gv.logger.class_curves
    assert curves["round"] == list(range(0, 301, 10))
    assert curves["class_total"] == [1000]*10 and curves["learning_rate_used"] == [0.1]*31
    assert len(curves["class_correct"]) == len(curves["class_loss_mean"]) == 31
    assert all(f["round"] <= 200 for f in curves["trajectory_flags"])
    correct, total = curves["class_correct"][-1], curves["class_total"]
    per_class = [c/n for c,n in zip(correct,total)]
    assert set(runner.gv.logger.output) == {"option", "client_datavol", "time", "test_accuracy", "test_loss"}
    validate_task(seed, record)
    torch.save(runner.model.state_dict(), directory / "final_model.pt")
    save(directory / "result.json", {"seed": seed, "method": "FedAvg", "attack": "none",
         "task": str(task), "rounds": 300, "per_class_accuracy": per_class,
         "overall_accuracy": sum(correct)/sum(total), "class_correct": correct, "class_total": total,
         "participants": participants, "elapsed_seconds": training_seconds,
         "wall_seconds": time.perf_counter()-begin, "round_seconds": timings,
         "torch_version": torch.__version__, "gpu_name": torch.cuda.get_device_name(0),
         "passed": per_class[8] >= 0.1 and per_class[9] >= 0.1})
    print(f"UNIT_COMPLETE seed={seed} rounds=300 class8={per_class[8]:.4f} class9={per_class[9]:.4f}", flush=True)


def run():
    started, stamp = time.perf_counter(), now()
    prepare()
    launch_started = time.perf_counter()
    children, streams, records = {}, {}, {}
    for seed in SEEDS:
        stream = (OUT / f"seed_{seed}/console.log").open("w", encoding="utf-8")
        streams[seed] = stream
        child_started = time.perf_counter()
        child = subprocess.Popen([str(PYTHON), "-B", "-u", str(Path(__file__).resolve()),
                                  "unit", "--seed", str(seed)], cwd=ROOT,
                                 stdout=stream, stderr=subprocess.STDOUT)
        children[seed] = (child, child_started)
        records[str(seed)] = {"pid": child.pid, "started_at": now()}
    save(OUT / "launch.json", {"started_at": now(), "processes": records})
    pending = set(SEEDS)
    while pending:
        for seed in tuple(pending):
            child, child_started = children[seed]
            code = child.poll()
            if code is not None:
                records[str(seed)].update(returncode=code, ended_at=now(),
                                         subprocess_wall_seconds=time.perf_counter()-child_started)
                streams[seed].close()
                pending.remove(seed)
                print(f"PROCESS_FINISHED seed={seed} returncode={code}", flush=True)
        if pending:
            time.sleep(1)
    save(OUT / "execution.json", {"started_at": stamp, "ended_at": now(),
         "total_wall_seconds": time.perf_counter()-started,
         "training_group_wall_seconds": time.perf_counter()-launch_started, "processes": records})
    return int(any(p["returncode"] for p in records.values()))


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
