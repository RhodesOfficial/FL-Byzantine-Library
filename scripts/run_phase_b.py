"""Phase B from immutable Phase A tasks; no task generation or legacy options."""
import argparse
from dataclasses import asdict
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "outputs/d1_3b/phase_a_ir5_p40_r300_20261002/manifest.json"
OUT = ROOT / "outputs/d1_3b/phase_b_20261003"
PYTHON = Path(r"E:\anaconda3\python.exe")
METHODS = ("brdrag", "balanced_brdrag", "d1", "avg")
SEEDS = (101, 102, 103)
sys.path[:0] = [str(ROOT), str(ROOT / "easyFL")]


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def save(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False), encoding="utf-8")


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def validate_task(record):
    task = Path(record["task"])
    for filename, key in (("info", "info_sha256"), ("data.json", "data_sha256")):
        if not (task / filename).is_file() or digest(task / filename) != record[key]:
            raise ValueError(f"Missing or changed task: {task / filename}")
    info, data = read(task / "info"), read(task / "data.json")
    root = info["root_data"]
    assert root["imbalance_ratio"] == 5 and "dir1.00" in info["partitioner"]
    assert info["num_clients"] == len(data["client_names"]) == 100
    assert len(root["root_indices"]) == 2000 and root["root_counts"][8:] == [0, 0]
    clients = [i for name in data["client_names"] for i in data[name]["data"]]
    assert len(clients) == len(set(clients)) and set(clients) == set(root["client_pool_indices"])
    assert not set(root["root_indices"]) & set(clients)
    return task


def build_manifest():
    from aggregators.d1_reference_baselines import B_BASELINE_VERSION
    source = read(SOURCE)
    assert (source["IR"], source["alpha"], source["num_clients"]) == (5, 1.0, 100)
    options = {}
    for seed in SEEDS:
        validate_task(source["tasks"][str(seed)])
        value = dict(source["options"][str(seed)])
        required = {"num_rounds": 300, "proportion": 0.4, "num_epochs": 1,
                    "batch_size": 64, "learning_rate": 0.1, "seed": seed,
                    "sample": "uniform", "aggregate": "uniform", "eval_interval": 10,
                    "num_workers": 0, "num_parallels": 1, "torch_num_threads": 1}
        assert all(value[k] == v for k, v in required.items())
        records = list((SOURCE.parent / f"seed_{seed}/record").glob("*.json"))
        assert len(records) == 1
        effective = read(records[0])["option"]
        assert effective["lr_scheduler"] == "-1" and not effective["load_checkpoint"]
        for key in ("dataseed", "lr_scheduler", "optimizer", "momentum", "weight_decay"):
            value[key] = effective[key]
        value.update(byz_seed=seed, byz_attack="label_flip", byz_malicious_fraction=0.3,
                     byz_assumed_count=0, byz_label_flip_num_classes=10,
                     byz_d1_num_classes=10, byz_d1_mode="majority", byz_d1_ablation="none",
                     byz_d1_root_step=0.1, byz_d1_batch_size=64, byz_d1_drag_strength=0.5,
                     byz_collect_nonzero=True)
        options[str(seed)] = {}
        for method in METHODS:
            unit = dict(value, byz_aggregator=method)
            if method in {"brdrag", "balanced_brdrag"}:
                unit.update(byz_baseline_version=B_BASELINE_VERSION, byz_root_budget=2000)
            options[str(seed)][method] = unit
    return {"source_manifest": str(SOURCE), "source_manifest_sha256": digest(SOURCE),
            "source_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
            "baseline_version": B_BASELINE_VERSION, "root_budget": 2000,
            "baseline_behavior_change": "Full root pool and protected RNG; legacy trajectories may differ",
            "deterministic_settings_enabled": False, "tasks_generated": False,
            "tasks": source["tasks"], "options": options,
            "attack_validation": {"seed": 101, "method": "avg", "rounds": 300},
            "core_diagnostics_ready": False}


def prepare():
    manifest = build_manifest()
    if subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True).strip():
        raise RuntimeError("Commit retained source changes before preparing B manifest")
    if OUT.exists() and any(child.name != "verification" for child in OUT.iterdir()):
        raise RuntimeError("Refusing to reuse existing B outputs")
    OUT.mkdir(exist_ok=True)
    save(OUT / "manifest.json", manifest)
    print("B_MANIFEST_READY tasks_generated=false root_budget=2000")


def create_runner(manifest, seed, method, directory, verification_rounds=None):
    import torch
    import flgo
    from flgo_byzantine import d1_full_algorithm
    from run_flgo_byzantine import ByzantineLogger
    assert seed in SEEDS and method in METHODS
    task = validate_task(manifest["tasks"][str(seed)])
    options = dict(manifest["options"][str(seed)][method])
    if verification_rounds is not None:
        assert verification_rounds in (10, 20)
        options["num_rounds"] = verification_rounds
    options["byz_diagnostic_output_dir"] = str(directory)
    directory.mkdir(parents=True, exist_ok=False)
    for child in ("record", "log"):
        (directory / child).mkdir()

    class UnitLogger(ByzantineLogger):
        def get_output_path(self):
            return str(directory / "record")

        def get_log_path(self):
            return str(directory / "log")

    runner = flgo.init(str(task), d1_full_algorithm, options, Logger=UnitLogger)
    assert runner.num_clients == 100 and len(runner.byz_malicious_ids) == 30
    assert runner.learning_rate == 0.1 and runner.lr_scheduler_type == "-1"
    assert type(runner.model).__module__ == "flgo.benchmark.cifar10_classification.model.cnn"
    expected = read(SOURCE.parent / f"seed_{seed}/result.json")["participants"]
    iterate = runner.iterate
    participants = []

    def paired_iterate():
        assert runner.learning_rate == 0.1 and all(c.learning_rate == 0.1 for c in runner.clients)
        result = iterate()
        actual = [int(cid) for cid in runner.received_clients]
        assert actual == list(runner.selected_clients) == expected[len(participants)]
        assert len(actual) == len(set(actual)) == 40
        participants.append(actual)
        return result

    runner.iterate = paired_iterate
    runner.phase_b_participants = participants
    return runner


def upload_activity(rows):
    """Pooled upload frequency, never an unweighted mean of round fractions."""
    total = sum(row["malicious"] for row in rows)
    nonzero = sum(round(row["malicious_nonzero_fraction"] * row["malicious"])
                  for row in rows if row["malicious"])
    return nonzero / total if total else None


def validate_cached_report(report, seed, method, manifest):
    from flgo_byzantine.d1_full_experiment import Unit, _validate_report
    unit = Unit("phase_b", "CIFAR10", "missing_flip", seed, 0.2, "label_flip", method)
    kwargs = ({"baseline_version": manifest["baseline_version"], "root_budget": 2000}
              if method in {"brdrag", "balanced_brdrag"} else {})
    _validate_report(report, seed, unit, **kwargs)
    assert report["options"] == manifest["options"][str(seed)][method]
    assert report["source_commit"] == manifest["source_commit"]
    return asdict(unit)


def attack_validation():
    import torch
    assert os.environ.get("CUBLAS_WORKSPACE_CONFIG") is None
    assert not torch.backends.cudnn.deterministic and not torch.backends.cudnn.benchmark
    assert not torch.are_deterministic_algorithms_enabled()
    manifest = read(OUT / "manifest.json")
    assert manifest == build_manifest()
    directory = OUT / "attack_validation_seed_101"
    runner = create_runner(manifest, 101, "avg", directory)
    runner.run()
    assert len(runner.full_round_stats) == len(runner.phase_b_participants) == 300
    save(directory / "result.json", {"options": manifest["options"]["101"]["avg"],
         "participants": runner.phase_b_participants, "round_stats": runner.full_round_stats,
         "malicious_nonzero_fraction": upload_activity(runner.full_round_stats)})


if __name__ == "__main__":
    assert Path(sys.executable).resolve() == PYTHON.resolve()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "attack-validation"))
    args = parser.parse_args()
    (prepare if args.action == "prepare" else attack_validation)()
