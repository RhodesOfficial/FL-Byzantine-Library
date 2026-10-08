"""Clipped 0.5: one composite boundary, literal/scalar independent anchors."""
import copy
from dataclasses import asdict, is_dataclass
import hashlib
import json
import math
from pathlib import Path
import random
import sys
import unittest

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np
import torch
from d2_prime.protocol import TaskProtocol, ProtocolConfig, Reply
from d2_prime.reference import ReferenceConfig, FeatureMap
from d2_prime.budget import BudgetConfig
from d2_prime.recovery import capture_checkpoint, restore_checkpoint, rng_state
from d2_prime.diagnostics import check_batch


def clean(value):
    if is_dataclass(value):
        return clean(asdict(value))
    if isinstance(value, (torch.Tensor, np.ndarray)):
        return clean(value.tolist())
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, dict):
        return {str(k): clean(v) for k, v in value.items()}
    if isinstance(value, (set, frozenset)):
        return clean(sorted(value))
    if isinstance(value, (list, tuple)) or type(value).__name__ == "deque":
        return [clean(v) for v in value]
    if hasattr(value, "__dict__"):
        return clean(vars(value))
    return value


def digest(value):
    return hashlib.sha256(json.dumps(clean(value), sort_keys=True, allow_nan=False).encode()).hexdigest()


def boundary():
    p = TaskProtocol([10., 20.], ProtocolConfig(identities=8, max_outstanding=8,
        capacity=1, lifetime=5., max_staleness=32), ReferenceConfig(n_boot=1, eta_reference=.5),
        FeatureMap((0, 1), (1, -1), 32), BudgetConfig(2., .375))
    def dispatch(identity, arrival):
        t = p.issue(identity)
        p.schedule_reply(Reply(t.task_id, identity, t.source_version,
                               p.snapshot(t.source_version).model), identity, arrival)
    dispatch(0, 0.)
    p.advance(0.)
    p.commit_event()
    dispatch(0, 0.)
    p.advance(0.)
    assert p.commit_event().waiting == ((1, "budget"),)
    dispatch(1, 1.)
    dispatch(2, 6.)
    return p


def finish(p, logging):
    trajectory, logs = [], []
    for now, commits in [(1., 1), (2., 2), (5., 1), (6., 1)]:
        p.advance(now)
        for _ in range(commits):
            p.commit_event()
            if logging:
                logs.append(json.dumps(clean(p.trace[-1:]), sort_keys=True))
            trajectory.append(digest(vars(p)))
    randoms = (random.random(), np.random.rand(), torch.rand(3).tolist())
    return trajectory, randoms, logs


class RecoveryAcceptance(unittest.TestCase):
    def test_independent_reconstruction_rejects_bad_model_and_reference(self):
        p = boundary()
        batch = p.batches[0]
        e = .125/math.sqrt(1.04)
        sigma = .25-.025/math.sqrt(1.04)
        normalized = [0.]*33+[sigma/math.sqrt(33)]*33+[e]
        inputs = dict(batch=batch, model_before=np.array([10., 20.]),
                      model_after=np.array([10., 20.]), carrier_after=np.array([10., 20.]),
                      reference_after=normalized, sources={}, protocol=p)
        self.assertEqual(check_batch(**inputs)["model"], 0.)
        with self.assertRaises(AssertionError):
            check_batch(**dict(inputs, carrier_after=np.array([10.001, 20.])))
        with self.assertRaises(AssertionError):
            check_batch(**dict(inputs, reference_after=[0.]*67))

    def test_independent_oracle_normal_frozen_source(self):
        p = TaskProtocol([10., 20.], ProtocolConfig(capacity=1),
                         ReferenceConfig(n_boot=1, eta_reference=.5, e_ready=.1),
                         budget_config=BudgetConfig(2., 1.5))
        for identity in (0, 1):
            task = p.issue(identity)
            source = p.snapshot(task.source_version)
            before = p.model.numpy()
            p.schedule_reply(Reply(task.task_id, identity, task.source_version, source.model), identity, p.now)
            p.advance(p.now)
            result = p.commit_event()
            self.assertEqual(result.event.proposals[0].path, "cold" if identity == 0 else "source")
            self.assertEqual(result.event.proposals[0].g, 1.)
            r = p.reference
            normalized = [v/math.sqrt(33) for v in r.mu+r.sigma]+[r.evidence]
            check_batch(p.batches[-1], before, p.model.numpy(), p.model.numpy(), normalized,
                        {task.source_version: source}, p)

    def test_composite_boundary_recovery_logging_and_literals(self):
        random.seed(101)
        np.random.seed(101)
        torch.manual_seed(101)
        p = boundary()
        self.assertEqual((p.version, p.buffer_ids, len(p.ledger), p.outstanding), (1, (1,), 1, 3))
        self.assertEqual(sum(e[1] == 1 for e in p._events), 2)
        self.assertEqual(p.budget_remaining(0), 0.)
        self.assertAlmostEqual(p.reference.evidence, .125/math.sqrt(1.04), places=14)
        # Historic 0.4 exhausted-case anchor: same registered source map/config,
        # model, receipt and R1 before adding the two pending tasks.
        old = json.loads((ROOT/"docs/D2_PRIME_PHASE04_MANIFEST.json").read_text())
        record = next(r for r in old["runs"] if r["case"] == "test_exact_exhaustion_and_zero_balance_wait")
        self.assertEqual(p.config_id, record["config_id"])
        self.assertEqual(clean(p.model), record["final_state"]["_model"])
        self.assertEqual(clean(p.ledger), record["final_state"]["ledger"])
        self.assertEqual(clean(p.reference), record["final_state"]["_reference"])
        payload = capture_checkpoint(p)
        expected = finish(p, False)
        recovered, _ = restore_checkpoint(payload, p.config_id)
        self.assertEqual(digest(vars(recovered)), digest(payload["protocol"]))
        actual = finish(recovered, True)
        self.assertEqual(actual[:2], expected[:2])
        self.assertGreater(len(actual[2]), 0)
        self.assertEqual(recovered.version, 3)
        self.assertEqual([r["task_id"] for r in recovered.ledger], [0, 1, 2])
        self.assertEqual([t.state for t in recovered.tasks.values()], ["consumed"]*3+["expired"])
        self.assertTrue(torch.equal(recovered.model, torch.tensor([10., 20.], dtype=torch.float64)))
        e1 = .125/math.sqrt(1.04)
        e2 = e1 + .125*(1-e1)
        self.assertAlmostEqual(recovered.reference.evidence, e2+.125*(1-e2), places=14)
        # Loading the same checkpoint again reproduces the suffix, not a doubled bill.
        again, _ = restore_checkpoint(payload, recovered.config_id)
        self.assertEqual(finish(again, False)[:2], expected[:2])
        self.assertEqual(len(again.ledger), 3)

    def test_mid_commit_and_wrong_config_rejected(self):
        p = boundary()
        p._in_commit = True
        with self.assertRaisesRegex(RuntimeError, "safe event"):
            capture_checkpoint(p)
        p._in_commit = False
        with self.assertRaisesRegex(ValueError, "mismatch"):
            restore_checkpoint(capture_checkpoint(p), "incorrect")
        with self.assertRaisesRegex(RuntimeError, "commit_event"):
            p.commit_model({})

    def test_future_queue_is_not_reference_or_score_input(self):
        p = boundary()
        q = copy.deepcopy(p)
        for i, event in enumerate(q._events):
            if event[1] == 1:
                reply, identity = event[-1]
                q._events[i] = (*event[:-1], (Reply(reply.task_id, identity,
                    reply.source_version, (999., -999.)), identity))
        self.assertEqual(p.prepare_reference_event(), q.prepare_reference_event())
        self.assertEqual(p.reference, q.reference)
        self.assertEqual(p.commit_event(), q.commit_event())
        self.assertEqual(p.ledger, q.ledger)


if __name__ == "__main__":
    unittest.main()
