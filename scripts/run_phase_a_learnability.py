"""Phase A: serial new task generation, then three independent FedAvg runs."""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
import traceback

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/d1_3b/phase_a_learnability_20261001"
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


def options(seed):
    return {"gpu": [0], "num_rounds": 200, "num_epochs": 1,
            "batch_size": 64, "test_batch_size": 128,
            "proportion": 0.2, "sample": "uniform", "aggregate": "uniform",
            "learning_rate": 0.1, "seed": seed, "no_tqdm": True,
            "eval_interval": 10, "test_holdout": 0, "train_holdout": 0,
            "num_workers": 0, "num_parallels": 1, "torch_num_threads": 1}


def prepare():
    import flgo
    from flgo.benchmark.partition import DirichletPartitioner
    from flgo_byzantine import d1_cifar10_lt as benchmark
    from flgo_byzantine.d1_cifar10_lt import core
    from flgo_byzantine.d1_cifar_lt.common import LTGenerator

    if OUT.exists():
        raise RuntimeError("New output directory already exists; no tasks or reports reused")
    OUT.mkdir(parents=True)
    begin = time.perf_counter()
    LTGenerator.imbalance_ratio = 10
    core.MISSING_FRACTION = 0.2
    tasks = {}
    for seed in SEEDS:
        core.ROOT_SEED = seed
        directory = OUT / f"seed_{seed}"
        directory.mkdir()
        task = directory / "task"
        labels = core.TaskGenerator().train_data.targets
        part = DirichletPartitioner(num_clients=100, alpha=0.5,
                                   index_func=lambda pool: [int(labels[i]) for i in pool.indices])
        started = time.perf_counter()
        created = flgo.gen_task_by_(benchmark, part, str(task), seed=seed)
        if created is None:
            raise RuntimeError(f"Task generation failed for seed {seed}")
        generation_seconds = time.perf_counter() - started
        info = json.loads((task / "info").read_text(encoding="utf-8"))
        data = json.loads((task / "data.json").read_text(encoding="utf-8"))
        root = info["root_data"]
        assert root["imbalance_ratio"] == 10 and "dir0.50" in info["partitioner"]
        assert root["seed"] == seed + 12001 and root["missing_fraction"] == 0.2
        assert info["num_clients"] == len(data["client_names"]) == 100
        assert len(root["root_indices"]) == 2000 and root["root_counts"][8:] == [0, 0]
        root_ids, pool_ids = set(root["root_indices"]), set(root["client_pool_indices"])
        client_ids = [i for name in data["client_names"] for i in data[name]["data"]]
        assert not root_ids & pool_ids
        assert len(client_ids) == len(set(client_ids)) and set(client_ids) == pool_ids
        pool_counts = Counter(int(labels[i]) for i in pool_ids)
        assert [pool_counts[c] for c in range(10)] == root["lt_counts"]
        holders = {}
        anomalies = []
        for label in (8, 9):
            counts = {str(cid): sum(int(labels[i]) == label for i in data[name]["data"])
                      for cid, name in enumerate(data["client_names"])}
            counts = {cid: count for cid, count in counts.items() if count}
            holders[str(label)] = counts
            if len(counts) < 3:
                anomalies.append(f"class {label}: fewer than 3 holders ({len(counts)})")
            if max(counts.values(), default=0) > pool_counts[label] * 0.8:
                anomalies.append(f"class {label}: one client holds more than 80%")
            if pool_counts[label] < 100:
                anomalies.append(f"class {label}: pool smaller than 100 ({pool_counts[label]})")
        tasks[str(seed)] = {"task": str(task), "info_sha256": digest(task / "info"),
                            "data_sha256": digest(task / "data.json"),
                            "lt_counts": root["lt_counts"], "root_counts": root["root_counts"],
                            "tail_holders": holders, "anomalies": anomalies,
                            "generation_seconds": generation_seconds}
        print(f"TASK_READY seed={seed} pool8={pool_counts[8]} holders8={len(holders['8'])} "
              f"pool9={pool_counts[9]} holders9={len(holders['9'])} anomalies={anomalies}", flush=True)
    save(OUT / "manifest.json", {"prepared_at": now(), "python": str(PYTHON),
         "git_head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
         "preparation_seconds": time.perf_counter() - begin, "tasks": tasks,
         "options": {str(seed): options(seed) for seed in SEEDS}})


def unit(seed):
    begin = time.perf_counter()
    import torch
    import flgo
    from flgo.algorithm import fedavg
    from flgo.experiment.logger.simple_logger import SimpleLogger

    directory = OUT / f"seed_{seed}"
    manifest = json.loads((OUT / "manifest.json").read_text(encoding="utf-8"))
    record = manifest["tasks"][str(seed)]
    task = Path(record["task"])
    for filename, key in (("info", "info_sha256"), ("data.json", "data_sha256")):
        assert digest(task / filename) == record[key]
    assert torch.cuda.is_available() and torch.__version__.startswith("2.5.1")
    runner = flgo.init(str(task), fedavg, options(seed), Logger=SimpleLogger)
    assert runner.num_clients == 100 and len(runner.clients) == 100
    assert type(runner.model).__module__ == "flgo.benchmark.cifar10_classification.model.cnn"
    assert sum(c.datavol for c in runner.clients) == sum(record["lt_counts"])
    participants, timings = [], []
    iterate = runner.iterate

    def monitored_iterate():
        started = time.perf_counter()
        value = iterate()
        selected = [int(cid) for cid in runner.selected_clients]
        received = [int(cid) for cid in runner.received_clients]
        assert len(selected) == len(set(selected)) == 20 and selected == received
        participants.append(selected)
        timings.append(time.perf_counter() - started)
        return value

    runner.iterate = monitored_iterate
    started = time.perf_counter()
    runner.run()
    training_seconds = time.perf_counter() - started
    assert runner.current_round == 201 and len(participants) == 200
    assert all(torch.isfinite(p).all().item() for p in runner.model.parameters())
    correct = torch.zeros(10, dtype=torch.long)
    totals = torch.zeros(10, dtype=torch.long)
    runner.model.eval()
    with torch.no_grad():
        for image, target in torch.utils.data.DataLoader(runner.test_data, batch_size=128):
            pred = runner.model(image.to(runner.device)).argmax(1).cpu()
            totals += torch.bincount(target, minlength=10)
            correct += torch.bincount(target[pred == target], minlength=10)
    assert totals.tolist() == [1000] * 10
    per_class = (correct.double() / totals).tolist()
    overall = float(correct.sum() / totals.sum())
    assert abs(overall - runner.gv.logger.output["test_accuracy"][-1]) < 1e-7
    sampled = Counter(cid for row in participants for cid in row)
    holders = record["tail_holders"]
    union = sorted({int(cid) for counts in holders.values() for cid in counts})
    tail_sampling = {label: {"client_rounds": {cid: sampled[int(cid)] for cid in counts},
                           "mean_rounds": sum(sampled[int(cid)] for cid in counts) / len(counts)}
                     for label, counts in holders.items()}
    tail_sampling["union"] = {"client_rounds": {str(cid): sampled[cid] for cid in union},
                               "mean_rounds": sum(sampled[cid] for cid in union) / len(union)}
    for filename, key in (("info", "info_sha256"), ("data.json", "data_sha256")):
        assert digest(task / filename) == record[key]
    torch.save(runner.model.state_dict(), directory / "final_model.pt")
    save(directory / "result.json", {"seed": seed, "method": "FedAvg", "attack": "none",
         "task": str(task), "rounds": 200, "per_class_accuracy": per_class,
         "overall_accuracy": overall, "class_correct": correct.tolist(), "class_total": totals.tolist(),
         "participants": participants, "tail_sampling": tail_sampling,
         "elapsed_seconds": training_seconds, "wall_seconds": time.perf_counter() - begin,
         "round_seconds": timings, "torch_version": torch.__version__,
         "gpu_name": torch.cuda.get_device_name(0),
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
        child = subprocess.Popen([str(PYTHON), "-u", str(Path(__file__).resolve()),
                                  "unit", "--seed", str(seed)], cwd=ROOT,
                                 stdout=stream, stderr=subprocess.STDOUT)
        children[seed] = (child, child_start)
        records[str(seed)] = {"pid": child.pid, "started_at": now()}
    save(OUT / "launch.json", {"started_at": stamp, "processes": records})
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
    print("PHASE_A_ALL_PROCESSES_FINISHED", flush=True)
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
