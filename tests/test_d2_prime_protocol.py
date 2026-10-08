"""Phase 0.1+0.2 acceptance, using independent fixed-vector/scalar oracles."""
from dataclasses import asdict, FrozenInstanceError, replace
import hashlib
import json
import math
from pathlib import Path
import sys
import unittest

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import torch
from d2_prime.protocol import ProtocolConfig, Reply, TaskProtocol

RUNS, CHECKS = [], []


def clean(value):
    if isinstance(value, torch.Tensor):
        return clean(value.tolist())
    if isinstance(value, float) and not math.isfinite(value):
        return str(value)
    if isinstance(value, dict):
        return {str(k): clean(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [clean(v) for v in value]
    return value


class ProtocolAcceptance(unittest.TestCase):
    def make(self, **options):
        config = ProtocolConfig(**dict({"identities": 4, "max_outstanding": 4,
            "capacity": 2, "lifetime": 5., "clip_norm": 10.}, **options))
        p = TaskProtocol([10., 20.], config)
        RUNS.append({"case": self._testMethodName, "config": asdict(config),
            "config_id": config.config_id, "initial_model": [10., 20.],
            "replies": [], "protocol": p})
        return p

    def fake(self, p, task, local):
        reply = Reply(task.task_id, task.identity, task.source_version, tuple(local))
        next(r for r in RUNS if r["protocol"] is p)["replies"].append(asdict(reply))
        return reply

    def check(self, label, actual, expected):
        CHECKS.append({"case": self._testMethodName, "label": label,
                       "actual": clean(actual), "expected": clean(expected)})
        self.assertEqual(clean(actual), clean(expected))

    def numeric(self, label, actual, expected):
        CHECKS.append({"case": self._testMethodName, "label": label,
                       "actual": clean(actual), "expected": clean(expected)})
        torch.testing.assert_close(actual, torch.tensor(expected, dtype=torch.float64),
                                   atol=1e-10, rtol=1e-8)

    def test_zero_delay_and_arrival_passivity(self):
        p = self.make()
        tasks = [p.issue(i) for i in (0, 1)]
        for task, local in zip(tasks, ([11., 18.], [12., 16.])):
            p.schedule_reply(self.fake(p, task, local), task.identity, 0.)
        p.advance(0.)
        self.numeric("arrival leaves model unchanged", p.model, [10., 20.])
        self.check("arrival ledger", p.ledger, [])
        p.commit_model({0: .5, 1: .5})
        # Independent synchronous oracle: mean([11,18], [12,16]). No protocol helper.
        self.numeric("synchronous mean", p.model, [11.5, 17.])
        self.numeric("negative source delta", torch.tensor(p.batches[0]["candidates"][0]["delta"], dtype=torch.float64), [-1., 2.])
        self.check("consumed once", [p.tasks[i].state for i in (0, 1)], ["consumed", "consumed"])

    def test_source_model_is_server_owned_and_frozen(self):
        p = self.make(capacity=1, max_staleness=1)
        old, fast = p.issue(0), p.issue(1)
        snapshot = p.snapshot(0)
        exposed = p.model
        exposed.fill_(999.)
        with self.assertRaises(FrozenInstanceError):
            snapshot.evidence = 1.
        p.receive(self.fake(p, fast, [14., 20.]), 1)
        p.commit_model({fast.task_id: 1.})
        p.receive(self.fake(p, old, [11., 18.]), 0)
        self.check("old source delta", p.candidates()[0]["delta"], (-1., 2.))
        self.check("source binding", (old.source_version, snapshot.model), (0, (10., 20.)))
        self.check("reference metadata", (snapshot.mu[0], snapshot.sigma[0], snapshot.evidence), (0., .25, 0.))
        p.commit_model({old.task_id: .5})
        self.numeric("stale write against current model", p.model, [14.5, 19.])
        self.check("task metadata", (old.task_id, old.identity, old.issued_at, old.expires_at,
            old.config_id), (0, 0, 0., 5., p.config.config_id))

    def test_forty_arrivals_two_twenty_batches(self):
        p = self.make(identities=40, max_outstanding=40, capacity=20)
        tasks = [p.issue(i) for i in range(40)]
        for task in reversed(tasks):
            p.schedule_reply(self.fake(p, task, [11., 18.]), task.identity, 1.)
        p.advance(1.)
        self.check("first capacity/order", p.buffer_ids, tuple(range(20)))
        self.check("forty outstanding including waiting", p.outstanding, 40)
        p.commit_model({i: 1/20 for i in range(20)})
        self.numeric("first independent batch", p.model, [11., 18.])
        self.check("second capacity/order", p.buffer_ids, tuple(range(20, 40)))
        self.check("old model retained", p.snapshot(0).model, (10., 20.))
        p.commit_model({i: 1/40 for i in range(20, 40)})
        # Fixed denominator K=20 and h=1/(1+1), NOT a second normalized mean.
        self.numeric("two-batch scalar oracle", p.model, [11.5, 17.])
        self.check("batch versions", [(b["version_before"], b["version_after"]) for b in p.batches], [(0, 1), (1, 2)])
        self.check("source/staleness", [(c["source_version"], c["staleness"])
            for b in p.batches for c in b["candidates"]], [(0, 0)] * 20 + [(0, 1)] * 20)
        self.check("capacity and final slots", ([len(b["candidates"]) for b in p.batches], p.outstanding), ([20, 20], 0))

    def test_equal_time_order_independent_of_enqueue_order(self):
        traces = []
        for order in ([2, 0, 3, 1], [3, 2, 1, 0]):
            p = self.make(capacity=4)
            tasks = [p.issue(i) for i in range(4)]
            for i in order:
                p.schedule_reply(self.fake(p, tasks[i], [11.+i, 20.]), i, 1.)
            p.advance(1.)
            traces.append([event[2] for event in p.trace if event[0] == "arrive"])
            p.commit_model({i: .25 for i in range(4)})
            self.numeric("ordered batch arithmetic", p.model, [12.5, 20.])
        self.check("independent expected order", traces, [[0, 1, 2, 3], [0, 1, 2, 3]])

    def test_global_and_identity_limits(self):
        p = self.make(max_outstanding=2)
        p.issue(0)
        p.issue(1)
        for identity in (0, 2):
            with self.assertRaises(RuntimeError):
                p.issue(identity)
        self.check("no excess tasks", (p.outstanding, len(p.tasks)), (2, 2))
        p.cancel(0)
        self.check("monotone task id after failed issue", p.issue(2).task_id, 2)

    def test_invalid_packets_have_zero_extra_effect(self):
        p = self.make()
        task = p.issue(0)
        good = self.fake(p, task, [11., 18.])
        invalid = [(replace(good, task_id=999), 0), (replace(good, identity=1), 1),
            (good, 1), (replace(good, source_version=1), 0),
            (replace(good, source_version=-1), 0)]
        for packet, identity in invalid:
            self.check("invalid receive", p.receive(packet, identity), False)
            self.numeric("invalid model", p.model, [10., 20.])
            self.check("invalid ledger/version/slots", (p.ledger, p.version, p.outstanding), ([], 0, 1))
        self.check("valid task survives spoof", p.tasks[0].state, "issued")

    def test_duplicate_before_and_after_commit(self):
        p = self.make(capacity=1)
        task = p.issue(0)
        reply = self.fake(p, task, [11., 18.])
        self.assertTrue(p.receive(reply, 0))
        self.check("duplicate queued", p.receive(reply, 0), False)
        p.commit_model({0: 1.})
        self.check("duplicate consumed", p.receive(reply, 0), False)
        self.numeric("one write only", p.model, [11., 18.])
        self.check("one ledger receipt", (len(p.ledger), p.outstanding, p.version), (1, 0, 1))

    def test_loss_cancel_and_expiry_reclaim_slots(self):
        for terminal in ("lost", "cancelled", "expired"):
            p = self.make(max_outstanding=1, lifetime=1.)
            task = p.issue(0)
            reply = self.fake(p, task, [11., 18.])
            if terminal == "expired":
                p.advance(1.)
            else:
                p.cancel(task.task_id, lost=terminal == "lost")
            self.check("terminal state", (p.tasks[0].state, p.outstanding), (terminal, 0))
            new = p.issue(0)
            self.check("late old reply", p.receive(reply, 0), False)
            self.check("new task not released by old reply", (new.task_id, p.outstanding, p.tasks[1].state), (1, 1, "issued"))
            self.numeric("terminal model", p.model, [10., 20.])
            self.check("terminal ledger", p.ledger, [])

    def test_expiry_endpoint_and_buffered_expiry(self):
        p = self.make(lifetime=1.)
        task = p.issue(0)
        p.schedule_reply(self.fake(p, task, [11., 18.]), 0, 1.)
        p.advance(1.)
        self.check("expiry wins arrival tie", (p.tasks[0].state, p.buffer_ids, p.outstanding), ("expired", (), 0))
        p = self.make(lifetime=1.)
        task = p.issue(0)
        p.schedule_reply(self.fake(p, task, [11., 18.]), 0, .999)
        p.advance(.999)
        self.check("before endpoint", p.tasks[0].state, "arrived")
        p.advance(1.)
        p.commit_model({})
        self.check("buffered expiry", (p.buffer_ids, p.ledger, p.version, p.outstanding), ((), [], 0, 0))
        self.numeric("expired writeback", p.model, [10., 20.])

    def test_staleness_expiry_reclaims_unreturned_task(self):
        p = self.make(capacity=1, max_staleness=0)
        old, fast = p.issue(0), p.issue(1)
        p.receive(self.fake(p, fast, [11., 18.]), 1)
        p.commit_model({fast.task_id: 1.})
        self.check("stale in-flight task", (p.tasks[old.task_id].state, p.outstanding), ("expired", 0))
        self.check("reclaimed identity", p.issue(0).source_version, 1)

    def test_buffer_and_ingress_cancellation_reclaims_slots(self):
        p = self.make(capacity=1, lifetime=1.)
        for i in range(4):
            p.receive(self.fake(p, p.issue(i), [11., 18.]), i)
        p.cancel(0)
        self.check("fill after cancelling buffer", p.buffer_ids, (1,))
        p.cancel(2, lost=True)  # A queued arrival, rather than the current candidate.
        self.check("cancel ingress leaves candidate", p.buffer_ids, (1,))
        p.advance(1.)
        self.check("buffer/ingress terminal states", [p.tasks[i].state for i in range(4)],
                   ["cancelled", "expired", "lost", "expired"])
        self.check("all waiting slots reclaimed", (p.outstanding, p.buffer_ids, p.ledger), (0, (), []))
        self.numeric("waiting cancellation model", p.model, [10., 20.])

    def test_old_expiry_event_cannot_cancel_reissued_identity(self):
        p = self.make(lifetime=1.)
        old = p.issue(0)
        p.cancel(old.task_id)
        p.advance(.5)
        new = p.issue(0)
        p.advance(1.)  # The old task's expiry event fires while the new one is live.
        self.check("old timer isolation", (p.tasks[new.task_id].state, p.outstanding), ("issued", 1))

    def test_clipping_has_independent_norm_oracle(self):
        p = self.make(capacity=1, clip_norm=1.)
        task = p.issue(0)
        p.receive(self.fake(p, task, [13., 24.]), 0)
        # Source-local = [-3,-4], norm=5, clip=[-.6,-.8].
        p.commit_model({0: 1.})
        self.numeric("clipped writeback", p.model, [10.6, 20.8])

    def test_zero_score_rejects_without_version(self):
        p = self.make(capacity=1)
        task = p.issue(0)
        p.receive(self.fake(p, task, [11., 18.]), 0)
        p.commit_model({0: 0.})  # External test coefficient, not an implemented scorer.
        self.check("empty contribution", (p.version, p.ledger, p.outstanding, p.tasks[0].state), (0, [], 0, "rejected"))
        self.numeric("zero coefficient model", p.model, [10., 20.])

    def test_cancelling_vectors_still_advance_version(self):
        p = self.make()
        for i, local in enumerate(([11., 20.], [9., 20.])):
            p.receive(self.fake(p, p.issue(i), local), i)
        p.commit_model({0: .5, 1: .5})
        self.numeric("positive contributions cancel", p.model, [10., 20.])
        self.check("commit sequence despite zero displacement", (p.version, len(p.ledger), p.snapshot(1).version), (1, 2, 1))

    def test_invalid_vector_and_coefficient_leave_writeback_unchanged(self):
        p = self.make(capacity=1)
        task = p.issue(0)
        for local in ([1.], [float("nan"), 2.], [float("inf"), 2.], [1e308, 1e308]):
            self.check("invalid vector", p.receive(self.fake(p, task, local), 0), False)
        p.receive(self.fake(p, task, [11., 18.]), 0)
        for a in (-1., 1.1, float("nan"), float("inf")):
            with self.assertRaises(ValueError):
                p.commit_model({0: a})
            self.numeric("invalid coefficient model", p.model, [10., 20.])
            self.check("invalid coefficient receipt", (p.ledger, p.version, p.tasks[0].state), ([], 0, "arrived"))

    def test_old_snapshot_retention_and_collection(self):
        p = self.make(capacity=1)
        old, fast = p.issue(0), p.issue(1)
        p.receive(self.fake(p, fast, [11., 18.]), 1)
        p.commit_model({fast.task_id: 1.})
        self.check("active old snapshot", p.snapshot(0).model, (10., 20.))
        p.cancel(old.task_id)
        with self.assertRaises(KeyError):
            p.snapshot(0)
        self.check("current snapshot retained", p.snapshot(1).model, (11., 18.))

    def test_clock_and_configuration_guards(self):
        for options in ({"capacity": 0}, {"lifetime": 0.}, {"max_staleness": -1}, {"clip_norm": float("nan")}):
            with self.assertRaises(ValueError):
                ProtocolConfig(**options)
        p = self.make()
        p.advance(1.)
        with self.assertRaises(ValueError):
            p.advance(0.)
        self.check("clock unchanged", p.now, 1.)


if __name__ == "__main__":
    assert Path(sys.executable).resolve() == Path(r"E:\anaconda3\python.exe").resolve()
    torch.set_num_threads(1)
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(ProtocolAcceptance)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    manifest_path = ROOT / "docs/D2_PRIME_PHASE01_02_MANIFEST.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    runs = []
    for row in RUNS:
        p = row.pop("protocol")
        row.update(final_model=p.model, version=p.version, outstanding=p.outstanding,
            tasks=[asdict(t) for t in p.tasks.values()], trace=p.trace,
            model_ledger=p.ledger, batches=p.batches)
        row = clean(row)
        row["fixture_sha256"] = hashlib.sha256(json.dumps({"initial_model": row["initial_model"],
            "replies": row["replies"]}, sort_keys=True).encode()).hexdigest()
        row["trajectory_sha256"] = hashlib.sha256(json.dumps({k: row[k] for k in
            ("trace", "batches", "model_ledger", "tasks", "final_model", "version")},
            sort_keys=True).encode()).hexdigest()
        runs.append(row)
    files = ["d2_prime/__init__.py", "d2_prime/protocol.py", "tests/test_d2_prime_protocol.py",
        *manifest["input_files"]]
    manifest["file_sha256"] = {f: hashlib.sha256((ROOT / f).read_bytes()).hexdigest() for f in files}
    manifest["execution"] = {"python": sys.executable, "torch": torch.__version__,
        "device": "cpu", "dtype": "float64", "real_training_tasks": 0,
        "tests_run": result.testsRun, "failures": len(result.failures), "errors": len(result.errors),
        "status": "PASS" if result.wasSuccessful() else "FAIL",
        "failed_cases": [(str(case), error) for case, error in result.failures + result.errors]}
    manifest["status"] = manifest["execution"]["status"]
    manifest["runs"], manifest["checks"] = runs, CHECKS
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, allow_nan=False)+"\n", encoding="utf-8")
    raise SystemExit(0 if result.wasSuccessful() else 1)
