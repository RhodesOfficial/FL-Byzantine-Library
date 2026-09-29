"""Fixed 100-unit D1 full experiment plan and FLGo execution."""

from __future__ import annotations

import json
import math
import time
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path

import flgo
import flgo.benchmark.partition as partition
import torch
from torch.utils.data import DataLoader, Subset

from attacks.d1_full_attacks import FixedTriggerDataset
from run_flgo_byzantine import ByzantineLogger
from . import d1_cifar10_lt, d1_cifar100_lt, d1_full_algorithm
from .d1_cifar10_lt import core as cifar10_core
from .d1_cifar100_lt import core as cifar100_core


SEEDS = (1, 2, 3, 4)
SCENES = (
    ("full_clean", 0.0, "none"),
    ("missing_clean", 0.2, "none"),
    ("full_flip", 0.0, "label_flip"),
    ("full_adaptive", 0.0, "adaptive_root"),
    ("missing_adaptive", 0.2, "adaptive_root"),
    ("missing_backdoor", 0.2, "backdoor"),
)
CONTROLS = ("avg", "fltrust", "brdrag", "flest", "balanced_brdrag")
ABLATIONS = ("single_root", "no_residual", "global_audit", "balanced_splice")
D1_ALGORITHM_VERSION = "root-backtracking-v1"


@dataclass(frozen=True)
class Unit:
    family: str
    dataset: str
    scene: str
    seed: int
    missing: float
    attack: str
    method: str
    malicious_fraction: float = 0.3
    mode: str = "majority"
    ablation: str = "none"


def plan():
    units = []
    for dataset in ("CIFAR10", "CIFAR100"):
        for scene, missing, attack in SCENES:
            for seed in SEEDS:
                units.append(Unit("main", dataset, scene, seed, missing,
                                  attack, "d1",
                                  malicious_fraction=0.0 if attack == "none" else 0.3))
    for dataset in ("CIFAR10", "CIFAR100"):
        for method in CONTROLS:
            for seed in SEEDS:
                units.append(Unit("control", dataset, "missing_adaptive", seed,
                                  0.2, "adaptive_root", method))
    for ablation in ABLATIONS:
        for seed in (1, 2):
            method = "balanced_splice" if ablation == "balanced_splice" else "d1"
            units.append(Unit("ablation", "CIFAR10", "missing_adaptive",
                              seed, 0.2, "adaptive_root", method,
                              ablation=ablation))
    units.extend((
        Unit("ratio", "CIFAR10", "full_adaptive", 1, 0, "adaptive_root", "d1", 0.1),
        Unit("ratio", "CIFAR10", "full_adaptive", 1, 0, "adaptive_root", "avg", 0.1),
        Unit("ratio", "CIFAR10", "full_adaptive", 1, 0, "adaptive_root", "d1", 0.6,
             mode="conservative"),
        Unit("ratio", "CIFAR10", "missing_adaptive", 1, 0.2, "adaptive_root", "d1", 0.6,
             mode="conservative"),
    ))
    assert len(units) == 100
    return units


def _clear_empty_task_scaffold(task):
    """Recover a task directory abandoned before FLGo wrote its metadata."""
    if not task.exists():
        return
    if (task / "info").is_file() and (task / "data.json").is_file():
        return
    if not task.is_dir():
        raise RuntimeError(f"incomplete FLGo task path is not a directory: {task}")
    children = list(task.iterdir())
    if (all(child.name in {"log", "record"} and child.is_dir()
            and not any(child.iterdir()) for child in children)):
        for child in children:
            child.rmdir()
        task.rmdir()
        return
    raise RuntimeError(
        f"incomplete FLGo task at {task}; expected info and data.json. "
        "Existing files were preserved for inspection")


def _task_for(unit, output_dir):
    benchmark, core = ((d1_cifar10_lt, cifar10_core) if unit.dataset == "CIFAR10"
                       else (d1_cifar100_lt, cifar100_core))
    core.MISSING_FRACTION = unit.missing
    core.ROOT_SEED = unit.seed
    task = output_dir / "tasks" / unit.dataset.lower() / (
        f"s{unit.seed}_m{int(unit.missing * 100)}_a0p1_ir50_v2")
    _clear_empty_task_scaffold(task)
    if not task.exists():
        task.parent.mkdir(parents=True, exist_ok=True)
        labels = core.TaskGenerator().train_data.targets
        # FLGo's stock Dirichlet partitioner expects a per-subset indexer.
        index_func = lambda pool: [int(labels[i]) for i in pool.indices]
        part = partition.DirichletPartitioner(num_clients=100, alpha=0.1,
                                               index_func=index_func)
        created = flgo.gen_task_by_(benchmark, part, str(task), seed=unit.seed)
        if created is None:
            raise RuntimeError("FLGo task generation failed")
    info = json.loads((task / "info").read_text(encoding="utf-8"))
    fed = json.loads((task / "data.json").read_text(encoding="utf-8"))
    root = info["root_data"]
    n_classes = 10 if unit.dataset == "CIFAR10" else 100
    if (info["benchmark"] != benchmark.__name__ or info["num_clients"] != 100
            or "dir0.10" not in info["partitioner"]
            or root["seed"] != unit.seed + 12001
            or root["missing_fraction"] != unit.missing
            or root["imbalance_ratio"] != 50
            or root["root_scheme"] != "lt_proportional_minimum_v2"
            or len(root["root_indices"]) != 2000
            or len(fed["client_names"]) != 100):
        raise ValueError("cached task does not match the 3B scientific design")
    labels = core.TaskPipe(str(task)).train_data.targets
    counts = Counter(int(labels[i]) for i in root["root_indices"])
    missing = int(n_classes * unit.missing)
    if any(counts[c] != root["root_counts"][c]
           for c in range(n_classes)):
        raise ValueError("root class counts differ from plan")
    if (any(counts[c] < (20 if n_classes == 10 else 10)
            for c in range(n_classes - missing))
            or any(counts[c] != 0 for c in range(n_classes - missing, n_classes))):
        raise ValueError("root coverage differs from plan")
    pool = root["client_pool_indices"]
    if (Counter(int(labels[i]) for i in pool) != Counter(dict(enumerate(root["lt_counts"])))
            or sum(len(fed[name]["data"]) for name in fed["client_names"]) != len(pool)):
        raise ValueError("LT pool or client partition differs from plan")
    return task, core


def _options(unit, gpu):
    n_classes = 10 if unit.dataset == "CIFAR10" else 100
    batch = 64 if n_classes == 10 else 32
    return {
        "gpu": [gpu], "num_rounds": 200, "num_epochs": 1,
        "batch_size": batch, "test_batch_size": 128,
        "proportion": 0.2, "sample": "uniform", "aggregate": "uniform",
        "learning_rate": 0.1 if n_classes == 10 else 0.01,
        "seed": unit.seed, "byz_seed": unit.seed,
        "no_tqdm": True, "eval_interval": 10,
        "test_holdout": 0, "train_holdout": 0, "num_workers": 0,
        "byz_aggregator": unit.method, "byz_attack": unit.attack,
        "byz_malicious_fraction": unit.malicious_fraction,
        "byz_assumed_count": 0,
        "byz_label_flip_num_classes": n_classes,
        "byz_d1_num_classes": n_classes,
        "byz_d1_mode": unit.mode,
        "byz_d1_root_step": 0.1 if n_classes == 10 else 0.01,
        "byz_d1_batch_size": batch,
        "byz_d1_ablation": (unit.ablation if unit.method == "d1" else "none"),
    }


def _evaluate(model, dataset, device, tail_classes, batch_size=128):
    confusion_correct = [0] * (max(tail_classes) + 1 if tail_classes else 0)
    confusion_total = [0] * len(confusion_correct)
    model.eval()
    with torch.no_grad():
        for image, target in DataLoader(dataset, batch_size=batch_size):
            pred = model(image.to(device)).argmax(1).cpu()
            for label in target.unique().tolist():
                label = int(label)
                mask = target == label
                confusion_total[label] += int(mask.sum())
                confusion_correct[label] += int((pred[mask] == label).sum())
    per_class = [correct / total if total else math.nan
                 for correct, total in zip(confusion_correct, confusion_total)]
    return per_class, sum(confusion_correct) / sum(confusion_total)


def _validate_report(report, index, unit):
    if report.get("index") != index or report.get("unit") != asdict(unit):
        raise ValueError(f"report {index} does not match the fixed 3B plan")
    if (unit.method == "d1"
            and report.get("d1_algorithm_version") != D1_ALGORITHM_VERSION):
        raise ValueError(
            f"report {index} uses an older D1 algorithm; rerun this unit with --rerun")


def run_unit(index, unit, output_dir, gpu, *, rerun=False):
    report_file = output_dir / "reports" / f"unit_{index:03d}.json"
    if report_file.exists() and not rerun:
        existing = json.loads(report_file.read_text(encoding="utf-8"))
        _validate_report(existing, index, unit)
        return existing
    task, core = _task_for(unit, output_dir)
    # Initialize the selected CUDA allocator before resetting its peak stats.
    # PyTorch 2.5.1 rejects this reset when no allocation has occurred yet.
    torch.empty(1, device=torch.device("cuda", gpu))
    torch.cuda.reset_peak_memory_stats(gpu)
    runner = flgo.init(str(task), d1_full_algorithm, _options(unit, gpu),
                       Logger=ByzantineLogger)
    start = time.perf_counter()
    runner.run()
    elapsed = time.perf_counter() - start
    if len(runner.full_round_stats) != 200:
        raise AssertionError("full run did not complete 200 rounds")
    if not all(torch.isfinite(p).all().item() for p in runner.model.parameters()):
        raise AssertionError("final model contains non-finite parameters")
    dataset = core.TaskPipe(str(task)).test_data
    n_classes = 10 if unit.dataset == "CIFAR10" else 100
    tail = runner.full_tail_classes
    per_class, overall = _evaluate(runner.model, dataset, runner.device,
                                   list(range(n_classes)))
    if len(per_class) != n_classes or not all(math.isfinite(x) for x in per_class):
        raise AssertionError("invalid per-class test metric")
    asr_dataset = FixedTriggerDataset(
        Subset(dataset, [i for i, label in enumerate(dataset.targets) if int(label) != 0]),
        force=True)
    attack_success = 0
    runner.model.eval()
    with torch.no_grad():
        for image, _ in DataLoader(asr_dataset, batch_size=128):
            attack_success += int((runner.model(image.to(runner.device)).argmax(1) == 0).sum())
    curve = [float(x) for x in runner.gv.logger.output["test_accuracy"]]
    if not curve or not all(math.isfinite(x) for x in curve):
        raise AssertionError("invalid training curve")
    rounds = runner.full_round_stats

    def mean_available(key):
        values = [float(r[key]) for r in rounds if r.get(key) is not None]
        return sum(values) / len(values) if values else None

    report = {
        "index": index, "unit": asdict(unit), "task": str(task),
        "d1_algorithm_version": D1_ALGORITHM_VERSION if unit.method == "d1" else None,
        "overall_accuracy": overall,
        "macro_accuracy": sum(per_class) / n_classes,
        "tail_accuracy": sum(per_class[c] for c in tail) / len(tail),
        "tail_classes": tail, "per_class_accuracy": per_class,
        "backdoor_asr": attack_success / len(asr_dataset),
        "accuracy_curve": curve,
        "round_stats": rounds,
        "rounds": 200, "elapsed_seconds": elapsed,
        "seconds_per_round": elapsed / 200,
        "gpu_peak_allocated_gib": torch.cuda.max_memory_allocated(gpu) / 2**30,
        "gpu_peak_reserved_gib": torch.cuda.max_memory_reserved(gpu) / 2**30,
        "actual_malicious_fraction_mean": mean_available("malicious_fraction"),
        "malicious_majority_rounds": sum(r["malicious_fraction"] >= 0.5 for r in rounds),
        "adaptive_zero_fraction": sum(r["adaptive_zero_update"] for r in rounds) / 200,
        "tail_benign_mean_weight": mean_available("tail_benign_mean_weight"),
        "other_benign_mean_weight": mean_available("other_benign_mean_weight"),
        "tail_benign_weight_loss": mean_available("tail_benign_weight_loss"),
        "weight_kind": rounds[-1]["weight_kind"],
        "tail_client_definition": runner.full_tail_client_definition,
        "fallback_fraction": sum(r.get("aggregator_stats", {}).get("fallback", "none") != "none"
                                 for r in rounds) / 200,
        "root_compute_seconds_per_round": mean_available("root_compute_seconds"),
    }
    report_file.parent.mkdir(parents=True, exist_ok=True)
    report_file.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def summarize(output_dir):
    """Collect complete and incomplete matrices without inventing missing scores."""
    rows = []
    missing = []
    for index, unit in enumerate(plan()):
        path = output_dir / "reports" / f"unit_{index:03d}.json"
        if path.exists():
            row = json.loads(path.read_text(encoding="utf-8"))
            _validate_report(row, index, unit)
            rows.append(row)
        else:
            missing.append(index)
    groups = {}
    metrics = ("overall_accuracy", "macro_accuracy", "tail_accuracy",
               "backdoor_asr", "fallback_fraction", "adaptive_zero_fraction",
               "root_compute_seconds_per_round",
               "tail_benign_mean_weight", "other_benign_mean_weight",
               "tail_benign_weight_loss", "seconds_per_round", "gpu_peak_reserved_gib")
    for row in rows:
        unit = row["unit"]
        key = (unit["family"], unit["dataset"], unit["scene"], unit["method"],
               unit["mode"], unit["ablation"], unit["malicious_fraction"])
        groups.setdefault(key, []).append(row)
    summary = []
    for key, group in sorted(groups.items()):
        item = {"family": key[0], "dataset": key[1], "scene": key[2],
                "method": key[3], "mode": key[4], "ablation": key[5],
                "malicious_fraction": key[6],
                "seeds": sorted(row["unit"]["seed"] for row in group),
                "n": len(group)}
        for metric in metrics:
            values = [row[metric] for row in group if row.get(metric) is not None]
            item[metric + "_mean"] = sum(values) / len(values) if values else None
        summary.append(item)
    result = {"completed": len(rows), "total": 100, "missing_indices": missing,
              "groups": summary}
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "summary.json"
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return path, result
