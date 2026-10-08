"""Regression checks for interrupted FLGo task generation."""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "easyFL"))

from flgo_byzantine.d1_full_experiment import _clear_empty_task_scaffold


class TaskRecoveryTests(unittest.TestCase):
    def test_empty_flgo_scaffold_is_recoverable(self):
        with tempfile.TemporaryDirectory() as directory:
            task = Path(directory) / "task"
            (task / "log").mkdir(parents=True)
            (task / "record").mkdir()

            _clear_empty_task_scaffold(task)

            self.assertFalse(task.exists())

    def test_existing_task_artifacts_are_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            task = Path(directory) / "task"
            (task / "log").mkdir(parents=True)
            artifact = task / "log" / "previous_run.txt"
            artifact.write_text("keep", encoding="utf-8")

            with self.assertRaisesRegex(RuntimeError, "Existing files were preserved"):
                _clear_empty_task_scaffold(task)

            self.assertEqual(artifact.read_text(encoding="utf-8"), "keep")


if __name__ == "__main__":
    unittest.main()
