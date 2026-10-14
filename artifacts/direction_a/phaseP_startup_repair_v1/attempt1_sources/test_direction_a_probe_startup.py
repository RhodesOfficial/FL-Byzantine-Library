"""CPU isolation tests of the real P class and exported wrapper lifecycle."""

import hashlib
import importlib.util
import json
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

import torch
import direction_a.backbone_preparation as parent
import direction_a.class_gradient_full as full
import direction_a.probe_startup as startup

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("probe_wrapper",ROOT/"scripts/recover_direction_a_probe.py")
wrapper=importlib.util.module_from_spec(spec); spec.loader.exec_module(wrapper)


class Clock:
    def __init__(self): self.now=100.
    def monotonic(self): return self.now


def context(output,clock=None):
    now=startup.time.monotonic() if clock is None else clock.monotonic()
    history=dict(elapsed_seconds=1.25,counts=dict(evidence_bytes=1000,archive_hash_scans=17),
                 implementation_revisions=4,preparation_launches=2,failed_retries=1)
    limits=dict(wall_seconds=20,evidence_bytes=1024*1024,scans=100,implementation_revisions=2,
                gpu_allocated_bytes=2*1024**3,windows_peak_working_set_bytes=2*1024**3,
                cpu_tensor_proxy_bytes=64*1024**2,phase_seconds={},per_run={})
    ctx=dict(output=Path(output),limits=limits,started=now,history=history,implementation_revisions=2,
             preparation_initial_write_bytes=321,preparation_initial_scans=7,
             source_write_events=[],run_id="synthetic_CPU_regression",total_wall_seconds=600,
             total_write_bytes=128*1024**2,new_preparation_launches=0,new_failed_restarts=0,
             cpu_proxy_upper_bytes=len(parent.encode(history))*8,
             cpu_proxy_basis="eight times serialized synthetic history byte buffer; no arrays/tensors")
    if clock is not None: ctx["clock"]=clock.monotonic
    return ctx


class StartupTests(unittest.TestCase):
    def setUp(self):
        self.directory=tempfile.TemporaryDirectory(prefix="P-startup-regression-")
        self.addCleanup(self.directory.cleanup)
        self.output=Path(self.directory.name)/"attempt"

    def fake_clock(self,clock):
        for module in (parent,full,startup):
            self.enterContext(patch.object(module,"time",types.SimpleNamespace(monotonic=clock.monotonic,
                                                                        monotonic_ns=lambda:123456)))

    def test_real_parent_initialization_and_exact_write_inheritance(self):
        clock=Clock(); self.fake_clock(clock); ctx=context(self.output,clock)
        snapshots=[]; writes=[]
        original_snapshot=startup.RecoveryBudget.snapshot
        original_write=Path.write_bytes
        def traced_snapshot(instance,now=None):
            snapshots.append(instance._initializing)
            return original_snapshot(instance,now)
        def traced_write(path,data):
            writes.append(len(data)); return original_write(path,data)
        with patch.object(startup.RecoveryBudget,"snapshot",traced_snapshot),patch.object(Path,"write_bytes",traced_write):
            budget=startup.RecoveryBudget(ctx)
            budget.save()
        self.assertIsInstance(budget,full.FullBudget)
        self.assertIsInstance(budget,parent.PreparationBudget)
        self.assertIn(True,snapshots); self.assertIn(False,snapshots)
        self.assertEqual(budget.counts["implementation_revisions"],2)
        self.assertEqual(budget.counts["scans"],7)
        self.assertEqual(budget.counts["evidence_bytes"],128*1024+321+sum(writes))
        saved=json.loads(budget.path.read_bytes())
        self.assertNotIn("P_initialization_pending",saved)
        self.assertEqual(saved["cumulative_implementation_revisions"],6)
        self.assertEqual(saved["cumulative_scans"],24)
        self.assertEqual(saved["cumulative_elapsed_seconds"],1.25)
        self.assertEqual(saved["cumulative_accountable_write_bytes"],1000+budget.counts["evidence_bytes"])

    def test_missing_inherited_cost_is_rejected_before_writing(self):
        ctx=context(self.output); del ctx["history"]["counts"]["evidence_bytes"]
        with self.assertRaises(KeyError): startup.RecoveryBudget(ctx)
        self.assertFalse(self.output.exists())

    def test_time_limit_saves_failure_and_preserves_history(self):
        clock=Clock(); self.fake_clock(clock); ctx=context(self.output,clock)
        budget=startup.RecoveryBudget(ctx)
        clock.now+=20
        with self.assertRaises(parent.PreparationLimit): budget.check()
        value=json.loads(budget.path.read_bytes())
        self.assertEqual(value["status"],"budget_exhausted")
        self.assertEqual(value["hit"]["field"],"wall_seconds")
        self.assertEqual(value["cumulative_elapsed_seconds"],21.25)

    def test_write_limit_rejects_payload_and_records_failed_state(self):
        budget=startup.RecoveryBudget(context(self.output))
        simulated_request=budget.limits["evidence_bytes"]-budget.counts["evidence_bytes"]+1
        with self.assertRaises(parent.PreparationLimit): budget.consume("evidence_bytes",simulated_request)
        saved=json.loads(budget.path.read_bytes())
        self.assertEqual(saved["status"],"budget_exhausted")
        self.assertEqual(saved["hit"]["field"],"evidence_bytes")
        self.assertLess(saved["counts"]["evidence_bytes"],budget.limits["evidence_bytes"])

    def test_cumulative_time_limit_includes_synthetic_history(self):
        clock=Clock(); self.fake_clock(clock); ctx=context(self.output,clock)
        ctx["total_wall_seconds"]=1.75
        budget=startup.RecoveryBudget(ctx); clock.now+=.5
        with self.assertRaises(parent.PreparationLimit): budget.check()
        saved=json.loads(budget.path.read_bytes())
        self.assertEqual(saved["hit"]["field"],"P_cumulative_wall_seconds")
        self.assertEqual(saved["cumulative_elapsed_seconds"],1.75)

    def test_cumulative_write_limit_includes_synthetic_history(self):
        ctx=context(self.output); budget=startup.RecoveryBudget(ctx)
        ctx["total_write_bytes"]=1000+budget.counts["evidence_bytes"]+10
        budget.consume("evidence_bytes",10)
        with self.assertRaises(parent.PreparationLimit): budget.check()
        saved=json.loads(budget.path.read_bytes())
        self.assertEqual(saved["hit"]["field"],"P_cumulative_write_bytes")
        self.assertEqual(saved["status"],"budget_exhausted")

    def test_existing_marker_and_ledger_are_immutable(self):
        self.output.mkdir()
        for name in ("run_record.json","startup_record.json"):
            path=self.output/name; path.write_bytes(b"sealed")
            before=path.read_bytes()
            with self.assertRaises(FileExistsError): startup.RecoveryBudget(context(self.output))
            with self.assertRaises(FileExistsError): startup.claim_startup(context(self.output))
            self.assertEqual(path.read_bytes(),before)
            path.unlink()

    def test_sealed_directories_rejected_without_access(self):
        for path in startup.PROTECTED:
            with self.assertRaises(PermissionError): startup.claim_startup(context(path))

    def check_attempt(self,when):
        clock=Clock(); self.fake_clock(clock); ctx=context(self.output,clock)
        calls=[]
        def factory():
            calls.append("factory")
            if when=="before": raise RuntimeError("injected-before-budget")
            return startup.RecoveryBudget(ctx)
        def work(budget):
            calls.append("work")
            if when=="after": raise RuntimeError("injected-after-budget")
            budget.scan()
        def archive(budget):
            calls.append("archive"); clock.now+=.5
        result=wrapper.execute_attempt(ctx,factory,work,archive)
        self.assertEqual(result["status"],"completed" if when=="normal" else "failed_no_retry")
        self.assertGreaterEqual(result["new_stage_elapsed_seconds"],.5)
        self.assertAlmostEqual(result["cumulative_elapsed_seconds"],1.25+result["new_stage_elapsed_seconds"])
        self.assertEqual(result["cumulative_preparation_launches"],2)
        self.assertEqual(result["cumulative_failed_restarts"],1)
        self.assertIn("archive",calls)
        marker=json.loads((self.output/"startup_record.json").read_bytes())
        self.assertEqual(marker["status"],result["status"])
        self.assertFalse(marker["retry_allowed"])
        if when!="normal": self.assertIn("injected-"+when,(self.output/"startup_failure.txt").read_text())
        index=json.loads((self.output/"artifact_hashes.json").read_bytes())
        for name,row in index["files"].items():
            raw=(self.output/name).read_bytes()
            self.assertEqual(len(raw),row["bytes"])
            self.assertEqual(hashlib.sha256(raw).hexdigest(),row["sha256"])
        before={p.name:p.read_bytes() for p in self.output.iterdir()}
        with self.assertRaises(FileExistsError): wrapper.execute_attempt(ctx,factory,work,archive)
        self.assertEqual(calls.count("factory"),1)
        self.assertEqual(before,{p.name:p.read_bytes() for p in self.output.iterdir()})

    def test_wrapper_exception_before_budget(self): self.check_attempt("before")
    def test_wrapper_exception_after_budget(self): self.check_attempt("after")
    def test_wrapper_normal_archive_and_no_retry(self): self.check_attempt("normal")

    def test_v2_cumulative_totals_are_not_double_counted(self):
        history=dict(cumulative_elapsed_seconds=4.9019854,cumulative_accountable_write_bytes=500678,
            preparation_launches=2,failed_restarts=1,historical_failure=dict(implementation_revisions=2,
                counts=dict(archive_hash_scans=16)),source_write_events=[dict(revision=1),dict(revision=2)])
        values=startup.history_totals(history)
        self.assertEqual(values["seconds"],4.9019854)
        self.assertEqual(values["bytes"],500678)
        self.assertEqual(values["revisions"],4)
        self.assertIsNone(values["scans"])
        self.assertEqual(values["scan_lower_bound"],16)
