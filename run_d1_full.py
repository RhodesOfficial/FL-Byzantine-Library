"""D1 experiment entry point. Phase 3A currently provides only --profile smoke.

Smoke fixes the scientific conditions: MNIST, Dirichlet alpha 0.1, cyclic
label flip at 30%, one seed, D1 versus FedAvg, and 2,000 covered root samples.
It is a run-through check, not evidence for D1's proposed mechanism.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "easyFL"))

import flgo
import flgo.benchmark.partition as partition
import torch
from torch.utils.data import Subset

import flgo_byzantine
import flgo_byzantine.d1_mnist_benchmark as benchmark
import flgo_byzantine.d1_mnist_benchmark.core as benchmark_core
from attacks.flgo_label_flip import LabelFlippedDataset
from run_flgo_byzantine import ByzantineLogger


SEED = 1
CLIENTS = 10
ROUNDS = 5
BATCH_SIZE = 64
ALPHA = 0.1
MALICIOUS_FRACTION = 0.3
ROOT_COUNT = 2000
NUM_CLASSES = 10


def _task_path(output_dir):
    return output_dir / "mnist_dirichlet_0p1_root2000"


def _make_or_validate_task(output_dir):
    task = _task_path(output_dir)
    if not task.exists():
        if task.parent.exists() and task.parent.is_file():
            raise ValueError("output directory is a file")
        # The index function reads existing MNIST labels without decoding all
        # 58,000 client-pool images during FLGo's standard Dirichlet partition.
        index_func = lambda pool: [int(pool.dataset.targets[index]) for index in pool.indices]
        part = partition.DirichletPartitioner(
            num_clients=CLIENTS, alpha=ALPHA, index_func=index_func)
        generated = flgo.gen_task_by_(benchmark, part, str(task), seed=SEED)
        if generated is None:
            raise RuntimeError("FLGo did not generate the MNIST task")
    info = json.loads((task / "info").read_text(encoding="utf-8"))
    data = json.loads((task / "data.json").read_text(encoding="utf-8"))
    root = info.get("root_data", {})
    if info.get("benchmark") != "flgo_byzantine.d1_mnist_benchmark":
        raise ValueError("existing task uses a different benchmark")
    if info.get("num_clients") != CLIENTS or len(data["client_names"]) != CLIENTS:
        raise ValueError("existing task has a different client count")
    if "dir0.10" not in info.get("partitioner", ""):
        raise ValueError("existing task does not use Dirichlet alpha 0.1")
    indices = root.get("root_indices", [])
    if len(indices) != ROOT_COUNT or root.get("source_size") != 60000:
        raise ValueError("existing task has an incorrect root budget")
    if root.get("seed") != 12 + SEED:
        raise ValueError("existing task has a different root seed")
    labels = benchmark_core._mnist(True).targets
    counts = Counter(int(labels[index]) for index in indices)
    if any(counts[label] != 200 for label in range(NUM_CLASSES)):
        raise ValueError("root data lacks exact 200-per-class coverage")
    pool = root.get("client_pool_indices", [])
    if len(pool) != 58000 or set(indices) & set(pool):
        raise ValueError("root and client pool are not disjoint")
    client_indices = [index for name in data["client_names"] for index in data[name]["data"]]
    if len(client_indices) != len(pool) or set(client_indices) != set(pool):
        raise ValueError("client partitions do not match the root-excluded pool")
    pool_counts = Counter(int(labels[index]) for index in pool)
    # MNIST is almost balanced: this fixed rule makes the tail metric a
    # pipeline check, not a long-tail scientific claim.
    tail_classes = sorted(range(NUM_CLASSES), key=lambda label: (pool_counts[label], label))[:2]
    return task, tail_classes, dict(pool_counts)


def _options(aggregator, gpu):
    option = {
        "gpu": [gpu],
        "num_rounds": ROUNDS,
        "num_epochs": 1,
        "batch_size": BATCH_SIZE,
        "test_batch_size": 256,
        "proportion": 1.0,
        "sample": "uniform",
        "aggregate": "uniform",
        "learning_rate": 0.1,
        "seed": SEED,
        "byz_seed": SEED,
        "no_tqdm": True,
        "eval_interval": 1,
        "test_holdout": 0,
        "train_holdout": 0,
        "num_workers": 0,
        "byz_aggregator": aggregator,
        "byz_attack": "label_flip",
        "byz_label_flip_num_classes": NUM_CLASSES,
        "byz_malicious_fraction": MALICIOUS_FRACTION,
        "byz_assumed_count": 0,
    }
    if aggregator == "d1":
        option.update({
            "byz_d1_num_classes": NUM_CLASSES,
            "byz_d1_mode": "majority",
            "byz_d1_batch_size": BATCH_SIZE,
        })
    return option


def _run_one(task, aggregator, tail_classes, gpu):
    runner = flgo.init(str(task), flgo_byzantine, _options(aggregator, gpu),
                       Logger=ByzantineLogger)
    malicious = runner.byz_malicious_ids
    if len(malicious) != 3:
        raise AssertionError("label flip must affect exactly three of ten clients")
    for client in runner.clients:
        poisoned = isinstance(client.train_data, LabelFlippedDataset)
        if poisoned != (client.id in malicious):
            raise AssertionError("malicious-client labels were not assigned consistently")
        if poisoned:
            original_label = int(client.train_data.source[0][-1])
            flipped_label = int(client.train_data[0][-1])
            if flipped_label != (original_label + 1) % NUM_CLASSES:
                raise AssertionError("malicious-client labels were not cyclically flipped")
    round_seconds = []
    original_iterate = runner.iterate

    def timed_iterate():
        start = time.perf_counter()
        updated = original_iterate()
        round_seconds.append(time.perf_counter() - start)
        print(f"{aggregator} round {len(round_seconds)}/{ROUNDS}: "
              f"{round_seconds[-1]:.1f}s", flush=True)
        return updated

    runner.iterate = timed_iterate
    torch.cuda.reset_peak_memory_stats(gpu)
    start = time.perf_counter()
    runner.run()
    elapsed = time.perf_counter() - start
    if len(round_seconds) != ROUNDS:
        raise AssertionError("FLGo did not complete all five rounds")
    if runner.byz_last_round.get("malicious") != 3:
        raise AssertionError("the last round did not contain three malicious clients")
    if not all(torch.isfinite(parameter).all().item() for parameter in runner.model.parameters()):
        raise AssertionError("the final model contains non-finite parameters")
    test_data = benchmark_core._mnist(False)
    tail_indices = [index for index, label in enumerate(test_data.targets)
                    if int(label) in tail_classes]
    overall = runner.calculator.test(runner.model, test_data, batch_size=256)["accuracy"]
    tail = runner.calculator.test(runner.model, Subset(test_data, tail_indices),
                                  batch_size=256)["accuracy"]
    curve = [float(value) for value in runner.gv.logger.output["test_accuracy"]]
    if len(curve) != ROUNDS + 1 or not all(math.isfinite(value) for value in curve):
        raise AssertionError("overall-accuracy curve is incomplete or non-finite")
    stats = runner._byz_aggregator_instance.last_stats if aggregator == "d1" else None
    if aggregator == "d1" and (stats["covered_classes"] != NUM_CLASSES
                               or stats["root_train_count"] != 1000
                               or stats["root_audit_count"] != 1000):
        raise AssertionError("D1 did not use a covered 1000/1000 root split")
    return {
        "overall_accuracy": float(overall),
        "tail_accuracy": float(tail),
        "accuracy_curve": curve,
        "round_seconds": round_seconds,
        "total_seconds": elapsed,
        "gpu_peak_allocated_gib": torch.cuda.max_memory_allocated(gpu) / 2**30,
        "gpu_peak_reserved_gib": torch.cuda.max_memory_reserved(gpu) / 2**30,
        "malicious_client_ids": sorted(int(index) for index in malicious),
        "last_round": runner.byz_last_round,
        "d1_stats": stats,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", choices=("smoke",), required=True)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "outputs" / "d1_3a")
    parser.add_argument("--gpu", type=int, default=0)
    args = parser.parse_args(argv)
    if not torch.cuda.is_available() or args.gpu >= torch.cuda.device_count() or args.gpu < 0:
        parser.error("3A smoke requires an available CUDA GPU index")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    task, tail_classes, pool_counts = _make_or_validate_task(args.output_dir)
    print(f"3A task: {task}; tail classes by client-pool frequency: {tail_classes}", flush=True)
    results = {}
    for aggregator in ("avg", "d1"):
        results[aggregator] = _run_one(task, aggregator, tail_classes, args.gpu)
    report = {
        "profile": "smoke",
        "dataset": "MNIST",
        "three_a_only": True,
        "scientific_design": {
            "dirichlet_alpha": ALPHA,
            "label_flip_fraction": MALICIOUS_FRACTION,
            "label_flip_rule": "y -> (y + 1) % 10 on malicious training data",
            "seed": SEED,
            "comparators": ["FedAvg", "D1"],
            "root_samples": ROOT_COUNT,
            "root_train_samples": 1000,
            "root_audit_samples": 1000,
            "root_classes": NUM_CLASSES,
            "tail_definition": "two least frequent classes in the root-excluded client pool",
            "tail_classes": tail_classes,
            "client_pool_class_counts": pool_counts,
        },
        "execution": {
            "machine": torch.cuda.get_device_name(args.gpu),
            "clients": CLIENTS,
            "participants_per_round": CLIENTS,
            "rounds": ROUNDS,
            "local_epochs": 1,
            "batch_size": BATCH_SIZE,
            "gpu": args.gpu,
        },
        "results": results,
    }
    report_path = args.output_dir / "summary.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"D1_3A_OK FedAvg={results['avg']['overall_accuracy']:.4f}/"
          f"{results['avg']['tail_accuracy']:.4f} "
          f"D1={results['d1']['overall_accuracy']:.4f}/"
          f"{results['d1']['tail_accuracy']:.4f} "
          f"summary={report_path}", flush=True)


if __name__ == "__main__":
    main()
