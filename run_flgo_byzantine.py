"""Run a FLGo task with FL-Byzantine-Library aggregation and attacks.

Example: python run_flgo_byzantine.py --task ./mnist_20 --create-mnist \
    --clients 20 --aggregator krum --attack alie --malicious-fraction 0.2 \
    --assumed-count 4 --rounds 2 --proportion 1
"""

from __future__ import annotations

import argparse
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
    args = parser.parse_args(argv)
    if args.clients < 1 or args.rounds < 1 or not 0 < args.proportion <= 1:
        parser.error("clients and rounds must be positive; proportion must be in (0, 1]")
    if args.partition == "dirichlet" and args.alpha <= 0:
        parser.error("alpha must be positive")
    if args.create_mnist and args.create_toy:
        parser.error("choose only one of --create-mnist and --create-toy")
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
    runner = flgo.init(str(args.task), flgo_byzantine, option,
                       Logger=ByzantineLogger)
    runner.run()


if __name__ == "__main__":
    main()
