"""Run one asynchronous robust-FL research condition on a FLGo task."""

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

from flgo_byzantine import research_algorithm


def _ids(text):
    return [int(part) for part in text.split(",") if part.strip()]


class ResearchLogger(SimpleLogger):
    def initialize(self):
        super().initialize()
        self.output["research_config"].append({key: value for key, value in self.option.items()
                                                if key.startswith("byz_")})
        self.output["research_minority_ids"].append(
            sorted(self.coordinator.byz_minority_ids))
        root = self.coordinator.byz_root
        self.output["research_root_actual_samples"].append(len(root) if root is not None else 0)
        self.output["research_root_actual_classes"].append(
            sorted({int(root[i][1]) for i in range(len(root))}) if root is not None else [])

    def log_once(self, *args, **kwargs):
        super().log_once(*args, **kwargs)
        event = self.coordinator.byz_last_round
        self.output["research_received"].append(event.get("received", 0))
        self.output["research_used"].append(event.get("used", 0))
        self.output["research_malicious"].append(event.get("malicious", 0))
        self.output["research_staleness"].append(event.get("staleness", []))
        self.output["research_decisions"].append(event.get("decisions", {}))
        self.output["research_false_reject"].append(event.get("false_reject", 0))
        self.output["research_benign_deferred"].append(event.get("benign_deferred", 0))
        self.output["research_benign_decisions"].append(event.get("benign_decisions", 0))
        self.output["research_minority_false_reject"].append(
            event.get("minority_false_reject", 0))
        self.output["research_minority_deferred"].append(
            event.get("minority_deferred", 0))
        self.output["research_minority_decisions"].append(
            event.get("minority_decisions", 0))
        self.output["research_root_weight"].append(event.get("root_weight"))
        self.output["research_aggregation_ms"].append(event.get("aggregation_ms"))
        self.output["research_server_ms"].append(event.get("server_ms"))
        self.output["research_deadline_miss"].append(event.get("deadline_miss"))
        self.output["research_stage"].append(event.get("stage"))
        self.output["research_attack_without_benign"].append(
            self.coordinator.byz_attack_without_benign)
        self.output["research_raw_aggregate_norm"].append(event.get("raw_aggregate_norm"))
        self.output["research_median_update_norm"].append(event.get("median_update_norm"))
        self.output["research_model_max_abs"].append(event.get("model_max_abs"))
        self.output["research_backdoor_asr"].append(self.coordinator.backdoor_asr())

    def get_output_name(self, suffix=".json"):
        base = super().get_output_name(suffix="")
        config = {key: value for key, value in self.option.items()
                  if key.startswith("byz_")}
        digest = hashlib.sha1(json.dumps(config, sort_keys=True).encode()).hexdigest()[:10]
        return f"{base}_RESEARCH_{digest}{suffix}"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task", type=Path, required=True)
    parser.add_argument("--mode", choices=("baseline", "triage", "root_only",
                                           "root_fusion", "anytime"), default="baseline")
    parser.add_argument("--aggregator", choices=("avg", "cm", "tm", "krum", "cc", "rfa"),
                        default="avg", help="Used in baseline mode")
    parser.add_argument("--attack", choices=("none", "alie", "ipm", "timed_ipm",
                                       "joint_random", "joint_timing", "backdoor"), default="none")
    parser.add_argument("--malicious-fraction", type=float, default=0.2)
    parser.add_argument("--assumed-count", type=int, default=0)
    parser.add_argument("--rounds", type=int, default=100)
    parser.add_argument("--proportion", type=float, default=0.3)
    parser.add_argument("--epochs", type=int, default=1)
    parser.add_argument("--learning-rate", type=float, default=0.1)
    parser.add_argument("--server-rate", type=float, default=1.0,
                        help="Asynchronous interpolation rate applied to every aggregate")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--gpu", type=int)
    parser.add_argument("--delay-min", type=int, default=0)
    parser.add_argument("--delay-max", type=int, default=3)
    parser.add_argument("--max-staleness", type=int, default=4)
    parser.add_argument("--attack-max-delay", type=int, default=6)
    parser.add_argument("--attack-scale", type=float, default=1.0)
    parser.add_argument("--ipm-epsilon", type=float, default=1.0)
    parser.add_argument("--alie-z", type=float)
    parser.add_argument("--root-ids", type=_ids, default=[],
                        help="Comma-separated trusted client IDs reserved from training")
    parser.add_argument("--root-samples", type=int, default=50)
    parser.add_argument("--root-batch", type=int, default=32)
    parser.add_argument("--root-classes", type=_ids, default=[],
                        help="Restrict the trusted root to these class labels")
    parser.add_argument("--root-noise", type=float, default=0.0)
    parser.add_argument("--budget-ms", type=float, default=5.0)
    parser.add_argument("--target-label", type=int, default=0)
    parser.add_argument("--trigger-size", type=int, default=3)
    parser.add_argument("--run-id", default="single")
    args = parser.parse_args(argv)
    if not args.task.is_dir():
        parser.error(f"FLGo task does not exist: {args.task}")
    if args.rounds < 1 or not 0 < args.proportion <= 1:
        parser.error("rounds must be positive and proportion in (0, 1]")
    if args.delay_min < 0 or args.delay_max < args.delay_min:
        parser.error("invalid ordinary delay range")
    if args.attack_max_delay < 0 or args.max_staleness < 0:
        parser.error("delay bounds must be nonnegative")
    if not 0 <= args.root_noise <= 1:
        parser.error("root noise must be in [0, 1]")
    if args.root_samples < 1 or args.root_batch < 1 or args.budget_ms <= 0:
        parser.error("root sample count, root batch size and budget must be positive")
    if not 0 <= args.malicious_fraction < 1 or args.assumed_count < 0:
        parser.error("invalid malicious fraction or assumed count")
    if args.attack_scale < 0:
        parser.error("attack scale must be nonnegative")
    if not 0 < args.server_rate <= 1:
        parser.error("server rate must be in (0, 1]")
    if args.attack == "backdoor" and args.trigger_size < 1:
        parser.error("trigger size must be positive")
    option = {
        "gpu": [] if args.gpu is None else [args.gpu],
        "num_rounds": args.rounds,
        "num_epochs": args.epochs,
        "proportion": args.proportion,
        "sample": "uniform",
        "aggregate": "uniform",
        "learning_rate": args.learning_rate,
        "seed": args.seed,
        "no_tqdm": True,
        "eval_interval": 1,
        "byz_seed": args.seed,
        "byz_run_id": args.run_id,
        "byz_mode": args.mode,
        "byz_aggregator": args.aggregator,
        "byz_attack": args.attack,
        "byz_malicious_fraction": args.malicious_fraction,
        "byz_assumed_count": args.assumed_count,
        "byz_delay_min": args.delay_min,
        "byz_delay_max": args.delay_max,
        "byz_max_staleness": args.max_staleness,
        "byz_attack_max_delay": args.attack_max_delay,
        "byz_attack_scale": args.attack_scale,
        "byz_server_rate": args.server_rate,
        "byz_ipm_epsilon": args.ipm_epsilon,
        "byz_alie_z": args.alie_z,
        "byz_root_ids": args.root_ids,
        "byz_root_samples": args.root_samples,
        "byz_root_batch": args.root_batch,
        "byz_root_classes": args.root_classes,
        "byz_root_noise": args.root_noise,
        "byz_budget_ms": args.budget_ms,
        "byz_target_label": args.target_label,
        "byz_trigger_size": args.trigger_size,
    }
    runner = flgo.init(str(args.task), research_algorithm, option, Logger=ResearchLogger)
    runner.run()


if __name__ == "__main__":
    main()
