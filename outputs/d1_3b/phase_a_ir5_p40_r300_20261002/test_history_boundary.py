"""Test actual logger history boundary with stub metrics; no forward or training."""
from collections import defaultdict
from pathlib import Path
import sys
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "easyFL"))
sys.path.insert(0, str(ROOT / "outputs/d1_3b/phase_a_diag_20261002"))
import torch
from execute_diag import make_logger
from flgo.experiment.logger.simple_logger import SimpleLogger

directory = Path(__file__).resolve().parent / "rule_check"
directory.mkdir(exist_ok=True)
history = {"time": list(range(0,201,10)), "test_accuracy": [0.0]*21, "test_loss": [2.0]*21}
Logger = make_logger(directory, history)
logger = Logger.__new__(Logger)
logger.output = defaultdict(list)
logger.class_curves = {"class_total": [1]*10, "round": list(range(0,200,10)),
                       "learning_rate_used": [0.1]*20, "class_correct": [[1]*10 for _ in range(20)],
                       "class_loss_mean": [[1.0]*10 for _ in range(20)], "trajectory_flags": []}
logger._trajectory_exceeded = {}
stats = {"class_total": [1]*10, "class_correct": [1]*10, "class_loss_mean": [1.0]*10}
logger.coordinator = SimpleNamespace(current_round=200, model=torch.nn.Linear(4,10),
    calculator=SimpleNamespace(last_class_statistics=stats), test_data=list(range(10)),
    learning_rate=0.1, clients=[])

def existing_metrics(self, *args, **kwargs):
    self.output["test_accuracy"].append(1.0)
    self.output["test_loss"].append(1.0)

with patch.object(SimpleLogger, "log_once", existing_metrics):
    logger.log_once()
    assert len(logger.class_curves["trajectory_flags"]) == 2
    assert all(f["round"] == 200 for f in logger.class_curves["trajectory_flags"])
    for round_number in range(210,301,10):
        logger.coordinator.current_round = round_number
        logger.log_once()
        assert len(logger.class_curves["trajectory_flags"]) == 2
assert logger.class_curves["round"] == list(range(0,301,10))
print("HISTORY_BOUNDARY_PASSED: round200 records flags without stopping; rounds210-300 skip history; 31 points")
print("No model forward, evaluator loop, or runner.run() invoked")
