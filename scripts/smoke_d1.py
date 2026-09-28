"""Five-round, ten-client FLGo D1 smoke run on the bundled synthetic task.

No external dataset is downloaded. CPU is the default; ``--gpu 0`` is
available for the local 8 GB logic-check machine.
"""

import argparse
import json
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "easyFL"))
sys.path.insert(0, str(ROOT))

import torch
import flgo
import flgo.benchmark.partition as partition

import flgo_byzantine
import flgo_byzantine.toy_benchmark as toy
from aggregators.d1_category_coverage import D1CategoryCoverage
from run_flgo_byzantine import ByzantineLogger


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gpu", type=int, default=None,
                        help="GPU index; omit to run this small smoke check on CPU")
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="flgo_d1_smoke_") as temporary:
        task = str(Path(temporary) / "toy_10_clients")
        flgo.gen_task_by_(toy, partition.IIDPartitioner(num_clients=10), task, seed=19)
        options = {
            "gpu": [] if args.gpu is None else [args.gpu],
            "num_rounds": 5,
            "num_epochs": 1,
            "batch_size": 16,
            "proportion": 1.0,
            "sample": "uniform",
            "aggregate": "uniform",
            "learning_rate": 0.1,
            "seed": 19,
            "byz_seed": 19,
            "no_tqdm": True,
            "eval_interval": 1,
            "byz_aggregator": "d1",
            "byz_attack": "none",
            "byz_malicious_fraction": 0.0,
            "byz_assumed_count": 0,
            "byz_d1_num_classes": 2,
            "byz_d1_batch_size": 16,
        }
        runner = flgo.init(task, flgo_byzantine, options, Logger=ByzantineLogger)
        runner.run()
        if not isinstance(runner._byz_aggregator_instance, D1CategoryCoverage):
            raise AssertionError("FLGo did not construct D1")
        if runner.byz_last_round.get("received") != 10:
            raise AssertionError("the final FLGo round did not receive ten clients")
        if not all(torch.isfinite(parameter).all().item() for parameter in runner.model.parameters()):
            raise AssertionError("D1 produced a non-finite model")
        records = list((Path(task) / "record").glob("*DEFd1_ATKnone*.json"))
        if len(records) != 1:
            raise AssertionError("expected exactly one D1 FLGo record")
        record = json.loads(records[0].read_text(encoding="utf-8"))
        calls = sum("covered_classes" in stats for stats in record["byz_aggregator_stats"])
        if calls != 5:
            raise AssertionError(f"D1 was logged in {calls} rounds, expected five")
        print(f"SMOKE_D1_OK rounds={calls} received=10 "
              f"covered={runner._byz_aggregator_instance.last_stats['covered_classes']}")


if __name__ == "__main__":
    main()
