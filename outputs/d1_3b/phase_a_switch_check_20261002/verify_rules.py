"""Pure rule checks; no training, model forward, or data loading."""
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "outputs/d1_3b/phase_a_diag_20261002"))
from execute_diag import trajectory_observations

flags, previous = trajectory_observations(0, 0.4, 2.0, 0.3, 1.0, {})
assert len(flags) == 2 and not any(f["persistent"] for f in flags)
assert flags[0]["threshold"] == 0.005 and flags[1]["threshold"] == 0.005
flags, previous = trajectory_observations(10, 0.4, 2.0, 0.3, 1.0, previous)
assert len(flags) == 2 and all(f["persistent"] for f in flags)
flags, previous = trajectory_observations(20, 0.3, 1.0, 0.3, 1.0, previous)
assert not flags and not any(previous.values())
flags, previous = trajectory_observations(30, 0.4, 1.0, 0.3, 1.0, previous)
assert len(flags) == 1 and flags[0]["metric"] == "accuracy" and not flags[0]["persistent"]
flags, _ = trajectory_observations(0, 0.005, 2.01, 0, 2.0, {})
assert not flags
flags, _ = trajectory_observations(0, 0.0, 0.002, 0, 0, {})
assert len(flags) == 1 and flags[0]["threshold"] == 1e-3
print("RULE_CHECKS_PASSED: thresholds, per-metric consecutive flags, reset, boundary, loss floor")
print("Historical exceedances returned observations without raising")
