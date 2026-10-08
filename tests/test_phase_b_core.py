"""Core execution integrity rules, without training or generated tasks."""
import copy
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "easyFL")]
from scripts.run_phase_b_core import check_record


class CoreChecks(unittest.TestCase):
    def setUp(self):
        self.ids = list(range(40))
        self.row = {"round": 1, "received_client_ids": self.ids,
                    "client_parallel_coef": [1.] * 40, "client_residual_coef": [0.] * 40,
                    "client_contrib_norm": [1.] * 40, "client_contrib_along_final": [0.025] * 40,
                    "decomposition_error": 0.01, "residual_vector": None, "residual_group_cosine": None}
        self.checks = {"round": 1, "layer1_pass": True, "writeback_exact": True,
                       "layer2_pass": True, "delta_norm": 1.}
        self.diagnostic = {"round": 1, "received_client_ids": self.ids, "nonfinite_fields": []}

    def call(self):
        return check_record(self.row, self.checks, self.diagnostic, 1, self.ids, "brdrag", ROOT)

    def test_report_only_old_relative_error(self):
        self.assertIsNone(self.call())

    def test_strict_layer1_and_writeback(self):
        for key in ("layer1_pass", "writeback_exact", "layer2_pass"):
            self.checks[key] = False
            with self.assertRaises(ValueError):
                self.call()
            self.checks[key] = True

    def test_array_order_finite_and_length(self):
        original = copy.deepcopy(self.row)
        for key, value in (("received_client_ids", list(reversed(self.ids))),
                           ("client_parallel_coef", [1.] * 39),
                           ("client_contrib_norm", [float("nan")] * 40)):
            self.row[key] = value
            with self.assertRaises(AssertionError):
                self.call()
            self.row = copy.deepcopy(original)

    def test_zero_delta_direction_null(self):
        self.checks["delta_norm"] = 0
        with self.assertRaises(AssertionError):
            self.call()
        self.row["client_contrib_along_final"] = [None] * 40
        self.row["decomposition_error"] = None
        self.assertIsNone(self.call())

    def test_residual_file_and_zero_cosines(self):
        import numpy as np
        from scripts.run_phase_b import save
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as tmp:
            directory = Path(tmp)
            path = directory / "residual_vectors/round_020.f32"
            path.parent.mkdir()
            path.write_bytes(np.zeros(797962, dtype="<f4").tobytes())
            save(directory / "contribution_metadata.json", {"parameter_layout": [{"numel": 797962}]})
            self.row.update(round=20, residual_vector=str(path.relative_to(directory)),
                            residual_group_cosine={k: None for k in ("honest_tail_enriched", "other_honest", "malicious")})
            self.checks["round"] = self.diagnostic["round"] = 20
            result = check_record(self.row, self.checks, self.diagnostic, 20, self.ids, "d1", directory)
            self.assertEqual(result["norm"], 0)
            self.row["residual_group_cosine"]["malicious"] = 0.
            with self.assertRaises(AssertionError):
                check_record(self.row, self.checks, self.diagnostic, 20, self.ids, "d1", directory)


if __name__ == "__main__":
    unittest.main()
