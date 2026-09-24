"""Suite protocol checks that run without PyTorch or FLGo."""

import json
import tempfile
import unittest
from pathlib import Path

from research_suite import _command, _conditions, _percentile, summarize


class ResearchSuiteTests(unittest.TestCase):
    def test_conditions_keep_timing_vector_comparison(self):
        conditions = _conditions({2}, [], 0)
        names = {name for _, name, _ in conditions}
        self.assertIn("baseline_joint_random", names)
        self.assertIn("baseline_joint_timing", names)

    def test_phase_three_reserves_root(self):
        with self.assertRaises(ValueError):
            _conditions({3}, [], 0)

    def test_server_rate_is_sent_to_runner(self):
        case = {"id": "example", "seed": 3, "phase": 1,
                "settings": {"mode": "baseline", "attack": "ipm"}}
        common = {"rounds": 5, "proportion": 0.3, "malicious_fraction": 0.2,
                  "delay_min": 0, "delay_max": 3, "max_staleness": 8,
                  "attack_max_delay": 6, "server_rate": 0.2,
                  "root_ids": [], "gpu": None}
        command = _command(Path("task"), case, common)
        self.assertEqual(command[command.index("--server-rate") + 1], "0.2")

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

    def test_failed_run_keeps_last_logged_round_and_hides_survivor_mean(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            record = output / "success.json"
            record.write_text(json.dumps({"test_accuracy": [0.8], "test_loss": [2.0]}),
                              encoding="utf-8")
            (output / "failed.log").write_text(
                "INFO --------------Round 7--------------\n"
                "INFO test_accuracy                 0.1\n"
                "INFO test_loss                     123.0\n"
                "RuntimeError: aggregate would diverge\n", encoding="utf-8")
            manifest = {"cases": [
                {"id": "success", "phase": 1, "condition": "example", "seed": 0,
                 "status": "complete", "record": str(record)},
                {"id": "failed", "phase": 1, "condition": "example", "seed": 1,
                 "status": "failed", "record": None},
            ]}
            summarize(manifest, output)
            summary = (output / "summary.md").read_text(encoding="utf-8")
            self.assertIn("| 1 | example | 1/2 | 1 | — |", summary)
            import csv
            with (output / "summary.csv").open(encoding="utf-8-sig", newline="") as stream:
                rows = list(csv.DictReader(stream))
            self.assertEqual(rows[1]["last_logged_round"], "7")
            self.assertEqual(rows[1]["last_logged_loss"], "123.0")


if __name__ == "__main__":
    unittest.main()
