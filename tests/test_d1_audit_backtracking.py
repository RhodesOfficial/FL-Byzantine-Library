"""Regression checks for the observed feasible root step below the old grid."""

import sys
import unittest
from dataclasses import asdict
from pathlib import Path
from types import MethodType

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "easyFL"))

import torch

from aggregators.d1_category_coverage import D1CategoryCoverage
from flgo_byzantine.d1_full_experiment import (
    D1_ALGORITHM_VERSION, _validate_report, plan,
)


class D1AuditBacktrackingTests(unittest.TestCase):
    def test_feasible_smaller_root_step_is_used(self):
        aggregator = object.__new__(D1CategoryCoverage)
        aggregator.clip_norm = 1.0
        aggregator.candidate_steps = (1.0, 0.5, 0.25, 0.125)
        checked = []

        def feasibility(_self, candidate, *_args):
            norm = candidate.norm().item()
            checked.append(norm)
            return 1.0 if norm <= 0.0625 else None

        aggregator._feasible = MethodType(feasibility, aggregator)
        candidate, step = aggregator._root_fallback(
            torch.tensor([1.0]), None, None, None, None, None, None)

        self.assertAlmostEqual(step, 0.0625)
        self.assertAlmostEqual(candidate.norm().item(), 0.0625)
        self.assertEqual(len(checked), 5)

    def test_infeasible_root_still_skips_after_bounded_search(self):
        aggregator = object.__new__(D1CategoryCoverage)
        aggregator.clip_norm = 1.0
        aggregator.candidate_steps = (1.0, 0.5, 0.25, 0.125)
        checked = []

        def feasibility(_self, candidate, *_args):
            checked.append(candidate.norm().item())
            return None

        aggregator._feasible = MethodType(feasibility, aggregator)
        candidate, step = aggregator._root_fallback(
            torch.tensor([1.0]), None, None, None, None, None, None)

        self.assertIsNone(candidate)
        self.assertEqual(step, 0.0)
        self.assertEqual(len(checked), 12)

    def test_old_d1_report_cannot_be_silently_reused(self):
        unit = plan()[0]
        report = {"index": 0, "unit": asdict(unit)}
        with self.assertRaisesRegex(ValueError, "--rerun"):
            _validate_report(report, 0, unit)
        report["d1_algorithm_version"] = D1_ALGORITHM_VERSION
        _validate_report(report, 0, unit)


if __name__ == "__main__":
    unittest.main()
