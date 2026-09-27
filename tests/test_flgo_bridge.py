"""Offline integration checks for FLGo and the Byzantine library."""

import json
import copy
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np


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
    import flgo_byzantine.algorithm as bridge
    from flgo_byzantine.root_data import load_root_data
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
        self.assertIsNone(bridge._byz_root_data)

    def test_root_indices_are_isolated_and_reproducible(self):
        with (Path(self.tempdir.name) / "toy" / "info").open(encoding="utf-8") as stream:
            root = json.load(stream)["root_data"]
        saved = json.loads((Path(self.task) / "data.json").read_text(encoding="utf-8"))
        clients = [i for name in saved["client_names"] for i in saved[name]["data"]]
        self.assertEqual(len(root["root_indices"]), 32)
        self.assertEqual(set(root["root_indices"]) & set(clients), set())
        self.assertEqual(set(root["client_pool_indices"]), set(clients))
        data, identity = load_root_data(self.task, toy.core.TaskPipe)
        self.assertEqual(len(data), 32)
        self.assertTrue(torch.equal(data[0][0], toy.core.TRAIN_DATA[root["root_indices"][0]][0]))
        other = str(Path(self.tempdir.name) / "toy_again")
        flgo.gen_task_by_(toy, partition.IIDPartitioner(num_clients=10), other, seed=11)
        repeated = json.loads((Path(other) / "info").read_text(encoding="utf-8"))
        self.assertEqual(root, repeated["root_data"])
        self.assertEqual(identity, load_root_data(other, toy.core.TaskPipe)[1])

    def test_context_refresh_and_cache_identity(self):
        seen = []

        class Probe:
            def __init__(self, context):
                self.context = context

            def __call__(self, updates):
                seen.append(self.context.model)
                return torch.stack(updates).mean(dim=0)

        requirements = bridge.AggregatorRequirements(
            root_data=True, runtime_context=True, option_keys=("byz_probe_setting",))
        with patch.object(bridge, "AGGREGATORS", bridge.AGGREGATORS | {"probe"}), \
             patch.dict(bridge.AGGREGATOR_REQUIREMENTS, {"probe": requirements}), \
             patch.object(bridge, "_build_aggregator", side_effect=lambda *a, **kw: Probe(kw["context"])) as factory:
            runner = flgo.init(self.task, flgo_byzantine,
                               self.options(byz_aggregator="probe", byz_probe_setting=1))
            runner.received_clients = [0, 1]
            first = runner.model
            models = [copy.deepcopy(first) for _ in range(2)]
            with torch.no_grad():
                for parameter in models[0].parameters():
                    parameter.sub_(0.1)
            runner.model = runner.aggregate(models)
            old_vector = torch.nn.utils.parameters_to_vector(first.parameters())
            new_vector = torch.nn.utils.parameters_to_vector(runner.model.parameters())
            self.assertTrue(torch.allclose(new_vector, old_vector - 0.05, atol=1e-6))
            instance = runner._byz_aggregator_instance
            self.assertEqual(len(runner._byz_root_data), 32)
            self.assertIs(seen[0], first)
            self.assertIs(instance.context.model, first)
            self.assertIs(instance.context.calculator, runner.calculator)
            self.assertEqual(instance.context.device, runner.device)
            second = runner.model
            runner.received_clients = [0]
            runner.model = runner.aggregate([copy.deepcopy(second)])
            self.assertIs(runner._byz_aggregator_instance, instance)
            self.assertIs(seen[1], second)
            self.assertEqual(factory.call_count, 1)
            runner.option["byz_probe_setting"] = 2
            runner.model = runner.aggregate([copy.deepcopy(runner.model)])
            self.assertEqual(factory.call_count, 2)

    def test_existing_cache_rules(self):
        cc = flgo.init(self.task, flgo_byzantine,
                       self.options(byz_aggregator="cc"))
        cc.received_clients = list(range(10))
        cc.model = cc.aggregate([copy.deepcopy(cc.model) for _ in range(10)])
        instance = cc._byz_aggregator_instance
        center = instance.momentum.clone()
        cc.received_clients = list(range(9))
        cc.model = cc.aggregate([copy.deepcopy(cc.model) for _ in range(9)])
        self.assertIs(cc._byz_aggregator_instance, instance)
        self.assertTrue(torch.equal(instance.momentum, center))

        krum = flgo.init(self.task, flgo_byzantine,
                         self.options(byz_aggregator="krum", byz_assumed_count=1))
        krum.received_clients = list(range(10))
        krum.model = krum.aggregate([copy.deepcopy(krum.model) for _ in range(10)])
        instance = krum._byz_aggregator_instance
        krum.received_clients = list(range(9))
        krum.model = krum.aggregate([copy.deepcopy(krum.model) for _ in range(9)])
        self.assertIsNot(krum._byz_aggregator_instance, instance)

    def test_stats_are_json_safe_and_namespaced(self):
        class Stats:
            def get_attack_stats(self):
                return {"received": np.int64(3), "score": torch.tensor(0.5),
                        "invalid": float("nan"), "empty": None,
                        "vector": torch.tensor([1.0, 2.0])}

        result = bridge._aggregator_stats(Stats())
        self.assertEqual(result, {"received": 3, "score": 0.5, "empty": None})
        self.assertEqual(json.loads(json.dumps(result)), result)

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
        self.assertIn("Krum-Bypassed", record["byz_aggregator_stats"][-1])


if __name__ == "__main__":
    unittest.main()
