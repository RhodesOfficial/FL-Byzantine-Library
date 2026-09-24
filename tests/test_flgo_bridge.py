"""Offline integration checks for FLGo and the Byzantine library."""

import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "easyFL"))
sys.path.insert(0, str(ROOT))

try:
    import torch
    import flgo
    import flgo.algorithm.fedavg as fedavg
    import flgo.benchmark.partition as partition
    import flgo_byzantine
    import flgo_byzantine.toy_benchmark as toy
    from run_flgo_byzantine import ByzantineLogger
except ImportError as error:
    IMPORT_ERROR = error
else:
    IMPORT_ERROR = None


@unittest.skipIf(IMPORT_ERROR is not None, "FLGo/PyTorch dependencies unavailable")
class FLGoBridgeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tempdir = tempfile.TemporaryDirectory()
        cls.task = str(Path(cls.tempdir.name) / "toy")
        flgo.gen_task_by_(toy, partition.IIDPartitioner(num_clients=10),
                          cls.task, seed=11)

    @classmethod
    def tearDownClass(cls):
        cls.tempdir.cleanup()

    def options(self, **overrides):
        values = {"gpu": [], "num_rounds": 1, "num_epochs": 1,
                  "proportion": 1.0, "sample": "uniform", "aggregate": "uniform",
                  "learning_rate": 0.1, "seed": 19, "no_tqdm": True,
                  "eval_interval": 0, "byz_aggregator": "avg",
                  "byz_attack": "none", "byz_malicious_fraction": 0.0,
                  "byz_assumed_count": 0}
        values.update(overrides)
        return values

    def test_average_matches_native_fedavg(self):
        option = self.options()
        native = flgo.init(self.task, fedavg, option)
        native.run()
        bridge = flgo.init(self.task, flgo_byzantine, option)
        bridge.run()
        native_vector = torch.nn.utils.parameters_to_vector(native.model.parameters())
        bridge_vector = torch.nn.utils.parameters_to_vector(bridge.model.parameters())
        self.assertTrue(torch.allclose(native_vector, bridge_vector,
                                       atol=1e-7, rtol=0))

    def test_attack_and_defense_run_and_record_counts(self):
        option = self.options(byz_aggregator="krum", byz_attack="alie",
                              byz_malicious_fraction=0.2,
                              byz_assumed_count=2, byz_alie_z=0.5,
                              eval_interval=1)
        runner = flgo.init(self.task, flgo_byzantine, option,
                           Logger=ByzantineLogger)
        runner.run()
        self.assertEqual(runner.byz_last_round["received"], 10)
        self.assertEqual(runner.byz_last_round["malicious"], 2)
        records = list((Path(self.task) / "record").glob("*DEFkrum_ATKalie*.json"))
        self.assertEqual(len(records), 1)
        record = json.loads(records[0].read_text(encoding="utf-8"))
        self.assertEqual(record["byz_malicious"][-1], 2)


if __name__ == "__main__":
    unittest.main()
