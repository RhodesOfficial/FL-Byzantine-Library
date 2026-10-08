"""Focused checks of the new full-study branches using mock data only."""

import unittest
from collections import Counter
from pathlib import Path
from types import SimpleNamespace
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "easyFL"))

import torch

from aggregators.d1_category_coverage import D1CategoryCoverage
from aggregators.d1_reference_baselines import RootBaseline
from attacks.d1_full_attacks import FixedTriggerDataset


class Calculator:
    collate_fn = None

    @staticmethod
    def compute_loss(model, batch):
        image, label = batch
        prediction = model(image).squeeze(-1)
        return {"loss": ((prediction - label.float()) ** 2).mean()}


class FullBackendTests(unittest.TestCase):
    def test_plan_has_only_declared_units(self):
        from flgo_byzantine.d1_full_experiment import plan
        units = plan()
        self.assertEqual(len(units), 100)
        self.assertEqual(Counter(unit.family for unit in units),
                         Counter(main=48, control=40, ablation=8, ratio=4))
        self.assertTrue(all(unit.dataset == "CIFAR10" for unit in units if unit.family == "ratio"))
        self.assertTrue(all(unit.mode == "conservative" for unit in units
                            if unit.malicious_fraction == 0.6))

    def test_missing_twenty_percent_root_still_splits_1000_1000(self):
        root = [(torch.tensor([1.0]), label) for label in range(80) for _ in range(25)]
        model = torch.nn.Linear(1, 1, bias=False)
        context = SimpleNamespace(model=model, calculator=Calculator(), root_data=root,
                                  device=torch.device("cpu"))
        d1 = D1CategoryCoverage(context, num_classes=100)
        baseline = RootBaseline(context, 100, "fltrust")
        self.assertEqual(sum(map(len, d1.train_indices.values())), 1000)
        self.assertEqual(sum(map(len, d1.audit_indices.values())), 1000)
        self.assertEqual(sum(map(len, baseline.train_indices.values())), 1000)
        self.assertEqual(sum(not d1.train_indices[c] for c in range(100)), 20)

    def test_five_root_controls_return_finite_bridge_vector(self):
        root = [(torch.tensor([1.0, 0.0]), 0) for _ in range(8)]
        root += [(torch.tensor([0.0, 1.0]), 1) for _ in range(8)]
        model = torch.nn.Linear(2, 1, bias=False)
        context = SimpleNamespace(model=model, calculator=Calculator(), root_data=root,
                                  device=torch.device("cpu"))
        inputs = [torch.tensor([0.2, 0.1]), torch.tensor([0.1, 0.2]),
                  torch.tensor([-0.1, -0.1])]
        for method in ("fltrust", "brdrag", "flest", "balanced_brdrag",
                       "balanced_splice"):
            with self.subTest(method=method):
                baseline = RootBaseline(context, 2, method)
                result = baseline(inputs)
                self.assertEqual(result.shape, inputs[0].shape)
                self.assertTrue(torch.isfinite(result).all())
                self.assertEqual(len(baseline.last_client_weights), len(inputs))

    def test_fixed_trigger_changes_only_selected_samples(self):
        source = [(torch.zeros(3, 32, 32), 4) for _ in range(10)]
        triggered = FixedTriggerDataset(source, force=True)
        image, label = triggered[3]
        self.assertEqual(label, 0)
        self.assertTrue((image[:, -3:, -3:] > 1).all())
        self.assertEqual(float(image[:, :-3, :].abs().sum()), 0.0)


if __name__ == "__main__":
    unittest.main()
