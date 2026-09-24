"""Focused algorithm checks and a FLGo virtual-clock integration smoke test."""

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
    import flgo.benchmark.partition as partition
    import flgo_byzantine.toy_benchmark as toy
    from flgo_byzantine import research_algorithm
    from flgo_byzantine.research_methods import (
        Triage, Update, project_conflict, reference_fusion,
    )
except ImportError as error:
    IMPORT_ERROR = error
else:
    IMPORT_ERROR = None


@unittest.skipIf(IMPORT_ERROR is not None, "FLGo/PyTorch dependencies unavailable")
class ResearchTests(unittest.TestCase):
    def test_projection_removes_opposing_component(self):
        reference = torch.tensor([1.0, 0.0])
        result = project_conflict(torch.tensor([-2.0, 3.0]), reference)
        self.assertTrue(torch.allclose(result, torch.tensor([0.0, 3.0])))

    def test_fusion_reduces_inconsistent_root_weight(self):
        root = torch.tensor([1.0, 0.0])
        aligned = reference_fusion(root, root, root)[1]
        opposed = reference_fusion(root, -root, -root)[1]
        self.assertLess(opposed, aligned)

    def test_triage_preserves_supported_minority_cluster(self):
        direction = torch.tensor([1.0, 0.0])
        arrivals = [Update(0, direction, 1, 2),
                    Update(1, -direction, 1, 2),
                    Update(2, -direction, 1, 2),
                    Update(3, -direction, 1, 2)]
        selected, decisions = Triage().process(arrivals, direction, 2)
        self.assertEqual(len(selected), 4)
        self.assertEqual(decisions[1], "accepted")

    def test_async_virtual_clock_and_root_mode(self):
        with tempfile.TemporaryDirectory() as directory:
            task = str(Path(directory) / "toy")
            flgo.gen_task_by_(toy, partition.IIDPartitioner(num_clients=8),
                              task, seed=7)
            option = {"gpu": [], "num_rounds": 2, "num_epochs": 1,
                      "proportion": 0.5, "sample": "uniform", "aggregate": "uniform",
                      "learning_rate": 0.1, "seed": 9, "eval_interval": 0,
                      "no_tqdm": True, "byz_seed": 9,
                      "byz_mode": "root_fusion", "byz_attack": "ipm",
                      "byz_malicious_fraction": 0.2, "byz_root_ids": [0],
                      "byz_root_samples": 8, "byz_delay_min": 1,
                      "byz_delay_max": 2, "byz_max_staleness": 5}
            runner = flgo.init(task, research_algorithm, option)
            runner.run()
            self.assertEqual(runner.current_round, 3)
            self.assertTrue(torch.isfinite(
                torch.nn.utils.parameters_to_vector(runner.model.parameters())).all())
            self.assertNotIn(0, runner.byz_malicious_ids)


if __name__ == "__main__":
    unittest.main()
