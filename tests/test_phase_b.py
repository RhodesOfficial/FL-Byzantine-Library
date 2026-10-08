"""Independent Phase B integrity checks; no runner.run() here."""
import copy
from dataclasses import asdict
from pathlib import Path
import random
import sys
import tempfile
from types import SimpleNamespace
import unittest
import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "easyFL")]
from aggregators.d1_category_coverage import _preserve_global_rng
from aggregators.d1_reference_baselines import RootBaseline, B_BASELINE_VERSION
from flgo_byzantine.d1_full_algorithm import Server, malicious_nonzero_fraction
from flgo_byzantine.d1_full_experiment import Unit, _validate_report
from scripts.run_phase_b import build_manifest, upload_activity


def rng_state():
    return (random.getstate(), np.random.get_state(), torch.get_rng_state(),
            torch.cuda.get_rng_state_all() if torch.cuda.is_available() else [])


def same_rng(before, after):
    return (before[0] == after[0] and before[1][0] == after[1][0]
            and np.array_equal(before[1][1], after[1][1]) and before[1][2:] == after[1][2:]
            and torch.equal(before[2], after[2]) and len(before[3]) == len(after[3])
            and all(torch.equal(x, y) for x, y in zip(before[3], after[3])))


class RootData:
    def __init__(self):
        self.seen = []

    def __len__(self):
        return 2000

    def __getitem__(self, index):
        self.seen.append(index)
        random.random(); np.random.random(); torch.rand(1)
        if torch.cuda.is_available():
            torch.rand(1, device="cuda")
        return torch.tensor([index % 7 / 7, 1.0]), index % 8


class Calculator:
    collate_fn = None

    def compute_loss(self, model, batch):
        return {"loss": (model(batch[0]).flatten() - batch[1].float()).square().mean()}


class PhaseBTests(unittest.TestCase):
    def setUp(self):
        torch.set_num_threads(1)
        self.context = SimpleNamespace(model=torch.nn.Linear(2, 1), calculator=Calculator(),
                                       root_data=RootData())
        if torch.cuda.is_available():
            torch.cuda.get_rng_state_all()

    def test_budget_and_sampling(self):
        for method in ("brdrag", "balanced_brdrag"):
            baseline = RootBaseline(self.context, 10, method, version=B_BASELINE_VERSION, root_budget=2000)
            self.assertEqual(set(sum(baseline.train_indices.values(), [])), set(range(2000)))
            self.context.root_data.seen.clear()
            baseline._root()
            indices = self.context.root_data.seen
            self.assertEqual(len(indices), 2000)
            if method == "brdrag":
                self.assertEqual(set(indices), set(range(2000)))
            else:
                self.assertEqual([sum(i % 8 == c for i in indices) for c in range(8)], [250]*8)
        old = RootBaseline(self.context, 10, "brdrag")
        self.assertEqual(sum(map(len, old.train_indices.values())), 1000)
        self.assertFalse(old.protect_rng)
        self.assertIsNone(old._loader_generator)
        print("BUDGET_PASS pools=2000 ordinary_unique=2000 balanced_draws=2000 legacy=1000")

    def test_root_output_and_rng(self):
        for method in ("brdrag", "balanced_brdrag"):
            before = rng_state()
            baseline = RootBaseline(self.context, 10, method, version=B_BASELINE_VERSION, root_budget=2000)
            self.assertTrue(same_rng(before, rng_state()))
            initial = copy.deepcopy(baseline)
            before = rng_state()
            x = baseline._root()
            self.assertTrue(same_rng(before, rng_state()))
            y_baseline = copy.deepcopy(initial)
            y_baseline._loader_generator = None
            with _preserve_global_rng():
                y = y_baseline._root_unprotected()
            self.assertTrue(same_rng(before, rng_state()))
            original = copy.deepcopy(initial)
            original._loader_generator = None
            with _preserve_global_rng():
                unprotected = original._root_unprotected()
            self.assertTrue(torch.equal(x, y) and torch.equal(x, unprotected))
        print("RNG_PASS constructor+root Python/NumPy/CPU/CUDA restored; X=Y=unprotected bitwise")

    def test_nonzero_and_output_invariance(self):
        self.assertIsNone(malicious_nonzero_fraction([torch.zeros(2)], []))
        updates = [torch.zeros(2), torch.tensor([1e-13, 0.0], dtype=torch.float64),
                   torch.tensor([1e-12, 0.0], dtype=torch.float64), torch.tensor([2e-12, 0.0])]
        self.assertEqual(malicious_nonzero_fraction(updates, list(range(4))), 0.25)
        for invalid in (float("nan"), float("inf")):
            with self.assertRaises(ValueError):
                malicious_nonzero_fraction([torch.tensor([invalid])], [0])
        rows = [{"malicious": 1, "malicious_nonzero_fraction": 1.0},
                {"malicious": 3, "malicious_nonzero_fraction": 0.0},
                {"malicious": 0, "malicious_nonzero_fraction": None}]
        self.assertEqual(upload_activity(rows), 0.25)
        with tempfile.TemporaryDirectory() as directory:
            outputs = []
            for enabled in (False, True):
                server = Server.__new__(Server)
                server.model = copy.deepcopy(self.context.model)
                models = [copy.deepcopy(server.model), copy.deepcopy(server.model)]
                with torch.no_grad():
                    next(models[1].parameters()).add_(0.1)
                server.option = {"byz_seed": 101, "byz_collect_nonzero": enabled,
                                 "byz_diagnostic_output_dir": directory}
                server.received_clients = [0, 1]
                server.byz_malicious_ids = {1}
                server.byz_aggregator, server.byz_attack = "avg", "label_flip"
                server._tail_client_ids, server.full_round_stats = set(), []
                server._load_context = lambda: None
                server._aggregator = lambda: lambda values: torch.stack(values).mean(0)
                outputs.append(server.aggregate(models).state_dict())
                if enabled:
                    self.assertEqual(server.byz_last_round["malicious_nonzero_fraction"], 1.0)
            self.assertTrue(all(torch.equal(outputs[0][k], outputs[1][k]) for k in outputs[0]))
        print("NONZERO_PASS null/threshold/NaN/Inf/pooled-count/output-bitwise")

    def test_manifest_and_cache_version(self):
        manifest = build_manifest()
        self.assertFalse(manifest["tasks_generated"])
        self.assertEqual(manifest["root_budget"], 2000)
        unit = Unit("phase_b", "CIFAR10", "missing_flip", 101, 0.2, "label_flip", "brdrag")
        report = {"index": 101, "unit": asdict(unit), "baseline_version": B_BASELINE_VERSION,
                  "root_budget": 2000}
        _validate_report(report, 101, unit, baseline_version=B_BASELINE_VERSION, root_budget=2000)
        for key, value in (("baseline_version", "root1000-v1"), ("root_budget", 1000)):
            with self.assertRaises(ValueError):
                _validate_report(dict(report, **{key: value}), 101, unit,
                                 baseline_version=B_BASELINE_VERSION, root_budget=2000)
        print("MANIFEST_PASS hashes/options; CACHE_PASS rejects old version/budget")


if __name__ == "__main__":
    unittest.main(verbosity=2)
