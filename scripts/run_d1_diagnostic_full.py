"""Serial task preparation followed by four independent diagnostic pipelines."""
from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
import traceback

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/d1_3b/diagnostic_full_20260930"
PYTHON = Path(r"E:\anaconda3\python.exe")
METHODS = {"fedavg": "avg", "brdrag": "brdrag",
           "class_bal_brdrag": "balanced_brdrag", "d1": "d1"}
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "easyFL"))


def now():
    return datetime.now(timezone.utc).isoformat()


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def make_unit(seed, method):
    from flgo_byzantine.d1_full_experiment import Unit
    return Unit("diagnostic_full", "CIFAR10", "missing_adaptive", seed,
                0.2, "adaptive_root", METHODS[method])


def prepare():
    import flgo_byzantine.d1_full_experiment as exp
    if OUT.exists():
        raise RuntimeError("The new output directory must not already exist")
    OUT.mkdir(parents=True)
    begin = time.perf_counter()
    tasks = {}
    previous = json.loads((ROOT / "outputs/d1_3b/smokeB_20260930/manifest.json").read_text(encoding="utf-8"))
    for seed in range(1, 6):
        task, _ = exp._task_for(make_unit(seed, "d1"), OUT / "shared")
        info = json.loads((task / "info").read_text(encoding="utf-8"))
        data = json.loads((task / "data.json").read_text(encoding="utf-8"))
        root = info["root_data"]
        assert root["root_counts"][8:] == [0, 0]
        root_ids, pool_ids = set(root["root_indices"]), set(root["client_pool_indices"])
        client_ids = [i for name in data["client_names"] for i in data[name]["data"]]
        assert len(root_ids) == 2000 and not root_ids & pool_ids
        assert len(data["client_names"]) == 100
        assert len(client_ids) == len(set(client_ids)) and set(client_ids) == pool_ids
        old_task = Path(previous["tasks"][str(seed)]["task"])
        old_info = json.loads((old_task / "info").read_text(encoding="utf-8"))
        old_data = json.loads((old_task / "data.json").read_text(encoding="utf-8"))
        assert root == old_info["root_data"], "root selection changed"
        assert data["client_names"] == old_data["client_names"]
        assert all(data[name]["data"] == old_data[name]["data"] for name in data["client_names"]), "client partition changed"
        tasks[str(seed)] = {"task": str(task), "info_sha256": digest(task / "info"),
                            "data_sha256": digest(task / "data.json"),
                            "root_counts": root["root_counts"], "lt_counts": root["lt_counts"],
                            "clients": 100, "matches_previous_partition": True}
        save(OUT / "preparation_progress.json", {"completed_seeds": list(tasks), "at": now()})
        print(f"TASK_READY seed={seed} root_counts={root['root_counts']}", flush=True)
    save(OUT / "manifest.json", {"prepared_at": now(), "preparation_seconds": time.perf_counter() - begin,
                                "git_head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
                                "python": str(PYTHON), "tasks": tasks,
                                "options": {str(seed): exp._options(make_unit(seed, "d1"), 0) for seed in range(1, 6)}})


def unit(seed, method):
    import torch
    import flgo_byzantine.d1_full_experiment as exp
    directory = OUT / f"seed_{seed}_{method}"
    directory.mkdir(exist_ok=False)
    start = time.perf_counter()
    manifest = json.loads((OUT / "manifest.json").read_text(encoding="utf-8"))
    record = manifest["tasks"][str(seed)]
    task = Path(record["task"])
    for filename, key in (("info", "info_sha256"), ("data.json", "data_sha256")):
        assert digest(task / filename) == record[key]

    class UnitLogger(exp.ByzantineLogger):
        def get_output_path(self):
            path = directory / "record"
            path.mkdir(exist_ok=True)
            return str(path)

        def get_log_path(self):
            path = directory / "log"
            path.mkdir(exist_ok=True)
            return str(path)

    exp.ByzantineLogger = UnitLogger
    exp._task_for = lambda requested, unused: (task, exp.cifar10_core)
    original_options = exp._options

    def options(requested, gpu):
        value = original_options(requested, gpu)
        value["byz_diagnostic_output_dir"] = str(directory)
        assert value["num_rounds"] == 200 and value["num_epochs"] == 1
        return value

    exp._options = options
    original_init = exp.flgo.init
    timings, participants = [], []

    def monitored_init(*args, **kwargs):
        runner = original_init(*args, **kwargs)
        assert runner.num_clients == 100 and len(runner.byz_malicious_ids) == 30
        iterate = runner.iterate

        def monitored_iterate():
            begin = time.perf_counter()
            value = iterate()
            timings.append(time.perf_counter() - begin)
            participants.append([int(cid) for cid in runner.received_clients])
            assert len(runner.received_clients) == 20 and len(timings) <= 200
            stats = runner.full_round_stats[-1]
            if method == "d1":
                assert stats["aggregator_stats"]["missing_classes"] == 2
            save(directory / "progress.json", {"seed": seed, "method": method,
                 "round": len(timings), "last_round_seconds": timings[-1], "at": now()})
            if len(timings) % 10 == 0:
                print(f"PROGRESS seed={seed} method={method} round={len(timings)}/200 seconds={timings[-1]:.3f}", flush=True)
            return value

        runner.iterate = monitored_iterate
        return runner

    exp.flgo.init = monitored_init
    index = (seed - 1) * 4 + list(METHODS).index(method)
    report = exp.run_unit(index, make_unit(seed, method), directory, 0)
    assert report["rounds"] == len(timings) == 200 and report["tail_classes"] == [8, 9]
    rows = [json.loads(line) for line in (directory / "diagnostic_log.jsonl").read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 200 and [r["round"] for r in rows] == list(range(1, 201))
    assert [r["received_client_ids"] for r in rows] == participants
    for filename, key in (("info", "info_sha256"), ("data.json", "data_sha256")):
        assert digest(task / filename) == record[key]
    sources = {"residual_pass": 0, "root_fallback": 0, "zero_update": 0,
               "client_direction_zero_residual": 0}
    if method == "d1":
        for item in report["round_stats"]:
            stats = item["aggregator_stats"]
            if stats.get("update_norm", 0.0) <= 1e-12:
                sources["zero_update"] += 1
            elif stats["fallback"] == "root":
                sources["root_fallback"] += 1
            elif stats["residual_norm"] > 1e-12:
                sources["residual_pass"] += 1
            else:
                sources["client_direction_zero_residual"] += 1
        assert sum(sources.values()) == 200
    report.update(smoke_b_method=method, wall_seconds=time.perf_counter() - start,
                  round_seconds=timings, participants=participants, task_hashes=record,
                  update_sources=sources if method == "d1" else None,
                  torch_version=torch.__version__, gpu_name=torch.cuda.get_device_name(0),
                  diagnostic_log_bytes=(directory / "diagnostic_log.jsonl").stat().st_size,
                  attack_invocation_rounds=sum(r["attack_called"] for r in rows))
    save(directory / "result.json", report)
    print(f"UNIT_COMPLETE seed={seed} method={method} zero_fraction={report['adaptive_zero_fraction']:.3f}", flush=True)


def group(method):
    begin = time.perf_counter()
    records = []
    for seed in range(1, 6):
        start, stamp = time.perf_counter(), now()
        log = OUT / f"seed_{seed}_{method}.console.log"
        with log.open("w", encoding="utf-8") as stream:
            child = subprocess.run([str(PYTHON), "-u", str(Path(__file__).resolve()),
                                    "unit", "--seed", str(seed), "--method", method],
                                   cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT)
        records.append({"seed": seed, "method": method, "started_at": stamp,
                        "ended_at": now(), "returncode": child.returncode,
                        "subprocess_wall_seconds": time.perf_counter() - start, "log": str(log)})
        save(OUT / f"process_{method}_progress.json", records)
        print(f"PIPELINE {method} seed={seed} exit={child.returncode}", flush=True)
    save(OUT / f"process_{method}.json", {"method": method, "wall_seconds": time.perf_counter() - begin,
                                        "ended_at": now(), "units": records})
    return int(any(r["returncode"] for r in records))


def run():
    prepare()
    start, stamp = time.perf_counter(), now()
    children, streams = {}, []
    for method in METHODS:
        stream = (OUT / f"process_{method}.console.log").open("w", encoding="utf-8")
        streams.append(stream)
        children[method] = subprocess.Popen([str(PYTHON), "-u", str(Path(__file__).resolve()),
                                             "group", "--method", method],
                                            cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT)
    save(OUT / "launch.json", {"started_at": stamp, "process_pids": {m: c.pid for m, c in children.items()}})
    # A failure never kills or prevents waiting for the other three pipelines.
    exits = {method: child.wait() for method, child in children.items()}
    for stream in streams:
        stream.close()
    save(OUT / "execution.json", {"started_at": stamp, "ended_at": now(),
                                  "total_wall_seconds": time.perf_counter() - start,
                                  "process_returncodes": exits})
    print("DIAGNOSTIC_FULL_ALL_PROCESSES_FINISHED", flush=True)
    return int(any(exits.values()))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("run", "group", "unit"))
    parser.add_argument("--method", choices=METHODS)
    parser.add_argument("--seed", type=int, choices=range(1, 6))
    args = parser.parse_args()
    assert Path(sys.executable).resolve() == PYTHON.resolve()
    try:
        code = run() if args.action == "run" else (group(args.method) if args.action == "group" else unit(args.seed, args.method))
        sys.exit(code or 0)
    except Exception:
        traceback.print_exc()
        sys.exit(1)
