"""Suite protocol checks that run without PyTorch or FLGo."""

import json
import tempfile
import unittest
from pathlib import Path

from research_suite import _conditions, _percentile, summarize


class ResearchSuiteTests(unittest.TestCase):
    def test_conditions_keep_timing_vector_comparison(self):
        conditions = _conditions({2}, [], 0)
        names = {name for _, name, _ in conditions}
        self.assertIn("baseline_joint_random", names)
        self.assertIn("baseline_joint_timing", names)

    def test_phase_three_reserves_root(self):
        with self.assertRaises(ValueError):
            _conditions({3}, [], 0)

    def test_summary_computes_rates_from_denominators(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            record = output / "record.json"
            record.write_text(json.dumps({
                "test_accuracy": [0.4, 0.6],
                "val_accuracy_dist": [[0.2, 0.8]],
                "research_backdoor_asr": [None, 0.3],
                "time": [0, 12],
                "research_false_reject": [1],
                "research_benign_decisions": [4],
                "research_minority_false_reject": [1],
                "research_minority_decisions": [2],
                "research_staleness": [[1, 2]],
                "research_server_ms": [2, 10],
                "research_deadline_miss": [False, True],
            }), encoding="utf-8")
            manifest = {"cases": [{"phase": 1, "condition": "example",
                                   "seed": 0, "status": "complete",
                                   "record": str(record)}]}
            summarize(manifest, output)
            summary = (output / "summary.csv").read_text(encoding="utf-8-sig")
            self.assertIn("0.25", summary)
            self.assertIn("0.5", summary)
            self.assertEqual(_percentile([2, 10], 0.95), 9.6)


if __name__ == "__main__":
    unittest.main()
