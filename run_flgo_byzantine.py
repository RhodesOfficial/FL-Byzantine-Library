"""Run a FLGo task with FL-Byzantine-Library aggregation and attacks.

Example: python run_flgo_byzantine.py --task ./mnist_20 --create-mnist \
    --clients 20 --aggregator krum --attack alie --malicious-fraction 0.2 \
    --assumed-count 4 --rounds 2 --proportion 1
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "easyFL"))

import flgo
from flgo.experiment.logger.simple_logger import SimpleLogger

import flgo_byzantine
from flgo_byzantine.algorithm import AGGREGATORS, ATTACKS


class ByzantineLogger(SimpleLogger):
    """Save attack participation beside FLGo's ordinary accuracy metrics."""

    def initialize(self):
        super().initialize()
        option = self.option
        for key in ("byz_aggregator", "byz_attack", "byz_malicious_fraction",
                    "byz_assumed_count", "byz_seed"):
            self.output[key].append(option.get(key, option["seed"]))

    def log_once(self, *args, **kwargs):
        super().log_once(*args, **kwargs)
        summary = self.coordinator.byz_last_round
        self.output["byz_received"].append(summary.get("received", 0))
        self.output["byz_malicious"].append(summary.get("malicious", 0))
        self.output["byz_benign_mean_error_norm"].append(
            summary.get("benign_mean_error_norm"))
        self.output["byz_aggregator_stats"].append(
            summary.get("aggregator_stats", {}))
        if self.coordinator.byz_aggregator == "rfa":
            # Dedicated contract: never embed full weights in legacy scalar stats.
            self.output["byz_rfa_contribution"].append(
                copy.deepcopy(summary.get("rfa_contribution")))

    def get_output_name(self, suffix=".json"):
        base = super().get_output_name(suffix="")
        option = self.option
        tag = (f"_DEF{option['byz_aggregator']}_ATK{option['byz_attack']}"
               f"_MR{option['byz_malicious_fraction']:.3f}"
               f"_F{option['byz_assumed_count']}")
        settings = {key: value for key, value in option.items()
                    if key.startswith("byz_")}
        digest = hashlib.sha1(json.dumps(settings, sort_keys=True).encode()).hexdigest()[:8]
        return base + tag + f"_CFG{digest}" + suffix


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task", type=Path, required=True,
                        help="Existing FLGo task directory")
    parser.add_argument("--create-mnist", action="store_true",
                        help="Create the task with IID MNIST if absent")
    parser.add_argument("--create-toy", action="store_true",
                        help="Create a small offline synthetic task if absent")
    parser.add_argument("--clients", type=int, default=20)
    parser.add_argument("--partition", choices=("iid", "dirichlet"), default="iid",
                        help="Partition used when creating an MNIST task")
    parser.add_argument("--alpha", type=float, default=0.5,
                        help="Dirichlet concentration when creating an MNIST task")
    parser.add_argument("--aggregator", choices=sorted(AGGREGATORS), default="avg")
    parser.add_argument("--attack", choices=sorted(ATTACKS), default="none")
    parser.add_argument("--malicious-fraction", type=float, default=0.0)
    parser.add_argument("--assumed-count", type=int, default=0,
                        help="Defense's assumed upper bound per received round")
    parser.add_argument("--rounds", type=int, default=5)
    parser.add_argument("--proportion", type=float, default=1.0)
    parser.add_argument("--epochs", type=int, default=1)
    parser.add_argument("--learning-rate", type=float, default=0.1)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--gpu", type=int, default=None)
    parser.add_argument("--clip-tau", type=float, default=1.0)
    parser.add_argument("--ipm-epsilon", type=float, default=1.0)
    parser.add_argument("--alie-z", type=float, default=None)
    parser.add_argument("--label-flip-num-classes", type=int, default=None,
                        help="Label universe for cyclic label_flip attack")
    parser.add_argument("--d1-num-classes", type=int, default=None,
                        help="D1 task label-universe size; required for --aggregator d1")
    parser.add_argument("--d1-mode", choices=("majority", "conservative"),
                        default="majority")
    parser.add_argument("--d1-clip-norm", type=float, default=1.0)
    parser.add_argument("--d1-residual-budget-ratio", type=float, default=0.25)
    parser.add_argument("--d1-root-step", type=float, default=0.1)
    parser.add_argument("--d1-drag-strength", type=float, default=0.5)
    parser.add_argument("--d1-loss-tolerance", type=float, default=0.02)
    parser.add_argument("--d1-min-class-count", type=int, default=2)
    parser.add_argument("--d1-reliability-floor", type=float, default=0.05)
    parser.add_argument("--d1-batch-size", type=int, default=64)
    args = parser.parse_args(argv)
    if args.clients < 1 or args.rounds < 1 or not 0 < args.proportion <= 1:
        parser.error("clients and rounds must be positive; proportion must be in (0, 1]")
    if args.partition == "dirichlet" and args.alpha <= 0:
        parser.error("alpha must be positive")
    if args.create_mnist and args.create_toy:
        parser.error("choose only one of --create-mnist and --create-toy")
    if args.aggregator == "d1" and (args.d1_num_classes is None or args.d1_num_classes < 1):
        parser.error("--aggregator d1 requires positive --d1-num-classes")
    if args.attack == "label_flip" and (args.label_flip_num_classes is None or args.label_flip_num_classes < 2):
        parser.error("--attack label_flip requires --label-flip-num-classes >= 2")
    if (args.create_mnist or args.create_toy) and not args.task.exists():
        import flgo.benchmark.partition as partition
        if args.create_mnist:
            import flgo.benchmark.mnist_classification as benchmark
            if args.partition == "dirichlet":
                task_partitioner = partition.DirichletPartitioner(
                    num_clients=args.clients, alpha=args.alpha)
            else:
                task_partitioner = partition.IIDPartitioner(num_clients=args.clients)
        else:
            import flgo_byzantine.toy_benchmark as benchmark
            task_partitioner = partition.IIDPartitioner(num_clients=args.clients)
        flgo.gen_task_by_(benchmark, task_partitioner,
                          str(args.task), seed=args.seed)
    if not args.task.is_dir():
        parser.error(f"task directory does not exist: {args.task}")
    option = {
        "gpu": [] if args.gpu is None else [args.gpu],
        "num_rounds": args.rounds,
        "num_epochs": args.epochs,
        "proportion": args.proportion,
        "sample": "uniform",
        "aggregate": "uniform",
        "learning_rate": args.learning_rate,
        "seed": args.seed,
        "byz_seed": args.seed,
        "byz_aggregator": args.aggregator,
        "byz_attack": args.attack,
        "byz_malicious_fraction": args.malicious_fraction,
        "byz_assumed_count": args.assumed_count,
        "byz_clip_tau": args.clip_tau,
        "byz_ipm_epsilon": args.ipm_epsilon,
        "byz_alie_z": args.alie_z,
    }
    if args.aggregator == "d1":
        option.update({
            "byz_d1_num_classes": args.d1_num_classes,
            "byz_d1_mode": args.d1_mode,
            "byz_d1_clip_norm": args.d1_clip_norm,
            "byz_d1_residual_budget_ratio": args.d1_residual_budget_ratio,
            "byz_d1_root_step": args.d1_root_step,
            "byz_d1_drag_strength": args.d1_drag_strength,
            "byz_d1_loss_tolerance": args.d1_loss_tolerance,
            "byz_d1_min_class_count": args.d1_min_class_count,
            "byz_d1_reliability_floor": args.d1_reliability_floor,
            "byz_d1_batch_size": args.d1_batch_size,
        })
    if args.attack == "label_flip":
        option["byz_label_flip_num_classes"] = args.label_flip_num_classes
    runner = flgo.init(str(args.task), flgo_byzantine, option,
                       Logger=ByzantineLogger)
    runner.run()


if __name__ == "__main__":
    main()
