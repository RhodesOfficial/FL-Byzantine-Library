"""Gate logic: same-metric direction and pooled malicious upload counts."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.validate_phase_b_attack import judge, pooled_activity


class AttackValidationTests(unittest.TestCase):
    def test_direction_must_match_endpoint_metric(self):
        baseline = {"M_last5": .48198, "T_last5": .1626}
        activity = {"151-200": {"fraction": 1.0}, "201-250": {"fraction": .8}, "251-300": {"fraction": 1.0}}
        attack = {"M_final": .451, "T_final": .15, "M_last5": .49, "T_last5": .10}
        self.assertFalse(judge(attack, baseline, activity)["passed"])
        attack["M_last5"] = .48
        self.assertTrue(judge(attack, baseline, activity)["passed"])
        activity["251-300"]["fraction"] = .7999
        self.assertFalse(judge(attack, baseline, activity)["passed"])

    def test_pooled_counts_and_null(self):
        result = pooled_activity([{"malicious": 1, "malicious_nonzero_fraction": 1.0},
                                  {"malicious": 9, "malicious_nonzero_fraction": 0.0},
                                  {"malicious": 0, "malicious_nonzero_fraction": None}])
        self.assertEqual(result, {"nonzero_uploads": 1, "malicious_uploads": 10, "fraction": .1})
        self.assertIsNone(pooled_activity([])["fraction"])
        with self.assertRaises(AssertionError):
            pooled_activity([{"malicious": 1, "malicious_nonzero_fraction": float("nan")}])


if __name__ == "__main__":
    unittest.main(verbosity=2)
