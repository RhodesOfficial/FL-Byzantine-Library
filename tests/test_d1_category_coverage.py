"""Mock-data checks for D1's evidence, budget, fallback and sign contract."""

import random
import unittest
from types import SimpleNamespace

import numpy as np
import torch

from aggregators.d1_category_coverage import D1CategoryCoverage


class ToyCalculator:
    collate_fn = None

    def compute_loss(self, model, batch):
        features, labels = batch
        target = torch.ones_like(labels, dtype=features.dtype)
        prediction = model(features).squeeze(-1)
        return {"loss": ((prediction - target) ** 2).mean()}


class RandomizedCalculator(ToyCalculator):
    def compute_loss(self, model, batch):
        torch.rand(())
        np.random.rand()
        random.random()
        if torch.cuda.is_available():
            torch.rand((), device="cuda")
        return super().compute_loss(model, batch)


def fixture(include_second=True, **kwargs):
    model = torch.nn.Linear(2, 1, bias=False)
    with torch.no_grad():
        model.weight.zero_()
    root = [(torch.tensor([1.0, 0.0]), 0) for _ in range(8)]
    if include_second:
        root += [(torch.tensor([0.0, 1.0]), 1) for _ in range(8)]
    context = SimpleNamespace(model=model, calculator=ToyCalculator(),
                              root_data=root, device=torch.device("cpu"))
    return D1CategoryCoverage(context, num_classes=2, root_step=0.1,
                              clip_norm=2.0, **kwargs)


class D1CategoryCoverageTests(unittest.TestCase):
    def test_default_candidate_steps_include_extended_grid(self):
        self.assertEqual(
            fixture().candidate_steps,
            (1.0, 0.5, 0.25, 0.125, 0.0625, 0.03125, 0.015625))

    def test_call_preserves_global_rng_and_aggregation_output(self):
        aggregator = fixture(candidate_steps=(1.0, 0.5, 0.25, 0.125))
        aggregator.context.calculator = RandomizedCalculator()
        devices = list(range(torch.cuda.device_count())) if torch.cuda.is_available() else []
        numpy_state = np.random.get_state()
        python_state = random.getstate()
        try:
            with torch.random.fork_rng(devices=devices):
                torch.manual_seed(123)
                np.random.seed(123)
                random.seed(123)
                if devices:
                    torch.cuda.manual_seed_all(123)
                before_torch = torch.random.get_rng_state().clone()
                before_cuda = [state.clone() for state in torch.cuda.get_rng_state_all()] if devices else []
                before_numpy = np.random.get_state()
                before_python = random.getstate()

                result = aggregator([torch.tensor([-0.3, -0.3])])

                self.assertTrue(torch.equal(torch.random.get_rng_state(), before_torch))
                self.assertTrue(all(torch.equal(after, before) for after, before in
                                    zip(torch.cuda.get_rng_state_all(), before_cuda)))
                after_numpy = np.random.get_state()
                self.assertEqual(after_numpy[0], before_numpy[0])
                np.testing.assert_array_equal(after_numpy[1], before_numpy[1])
                self.assertEqual(after_numpy[2:], before_numpy[2:])
                self.assertEqual(random.getstate(), before_python)
                self.assertTrue(torch.allclose(
                    result, torch.tensor([-0.10000000894069672, -0.10000000894069672]),
                    rtol=0, atol=1e-7))
                self.assertEqual(aggregator.last_stats["fallback"], "none")
                self.assertEqual(aggregator.last_stats["selected_step"], 1.0)
        finally:
            np.random.set_state(numpy_state)
            random.setstate(python_state)

    def test_category_evidence_uses_disjoint_root_sets(self):
        aggregator = fixture(include_second=False)
        train = aggregator.train_indices[0]
        audit = aggregator.audit_indices[0]
        self.assertEqual(len(train), 4)
        self.assertEqual(len(audit), 4)
        self.assertFalse(set(train) & set(audit))
        self.assertEqual(aggregator.train_indices[1], [])
        result = aggregator([torch.tensor([-0.4, -0.4])])
        self.assertTrue(torch.isfinite(result).all())
        self.assertEqual(aggregator.last_stats["missing_classes"], 1)
        self.assertEqual(aggregator.last_stats["class_reliability"][1], 0.0)

    def test_missing_class_audit_rejects_harmful_client_and_falls_back(self):
        aggregator = fixture(include_second=False, drag_strength=0.0,
                             loss_tolerance=0.0, candidate_lambdas=(0.0,))
        # Positive bridge difference means a negative model displacement.
        result = aggregator([torch.tensor([0.4, 0.0])])
        self.assertEqual(aggregator.last_stats["fallback"], "root")
        self.assertEqual(aggregator.last_stats["missing_classes"], 1)
        self.assertLess(result[0].item(), 0.0)
        self.assertEqual(result[1].item(), 0.0)

    def test_residual_is_capped_even_with_large_uncovered_direction(self):
        aggregator = fixture(include_second=False, residual_budget_ratio=0.1,
                             candidate_lambdas=(1.0,), loss_tolerance=1.0)
        result = aggregator([torch.tensor([-0.3, -10.0])] * 3)
        self.assertEqual(aggregator.last_stats["fallback"], "none")
        self.assertLessEqual(aggregator.last_stats["residual_norm"], 0.2 + 1e-6)
        self.assertLessEqual(abs(result[1].item()), 0.2 + 1e-6)
        self.assertLessEqual(result.norm().item(), 2.0 + 1e-6)

    def test_return_sign_matches_bridge_model_update(self):
        aggregator = fixture(candidate_lambdas=(0.0,), loss_tolerance=1.0)
        base = torch.nn.utils.parameters_to_vector(aggregator.context.model.parameters()).detach().clone()
        result = aggregator([torch.tensor([-0.3, -0.3])])
        self.assertEqual(result.shape, base.shape)
        self.assertTrue(torch.isfinite(result).all())
        updated = base - result
        self.assertGreater(updated[0].item(), base[0].item())
        self.assertGreater(updated[1].item(), base[1].item())
        self.assertLess(result[0].item(), 0.0)

    def test_conservative_mode_disables_residual(self):
        aggregator = fixture(include_second=False, mode="conservative",
                             candidate_lambdas=(1.0,), loss_tolerance=1.0)
        result = aggregator([torch.tensor([-0.3, -10.0])])
        self.assertEqual(aggregator.last_stats["residual_norm"], 0.0)
        self.assertEqual(result[1].item(), 0.0)


if __name__ == "__main__":
    unittest.main()
