"""Gate 0.4 fixed-tensor acceptance, with independent scalar/model-budget oracles."""
from dataclasses import asdict, replace
from collections import deque
import hashlib
import json
import math
from pathlib import Path
import statistics
import subprocess
import sys
import unittest
from unittest.mock import patch

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import torch
from d2_prime.budget import BudgetConfig, Receipt, RollingBudget, audit_history
from d2_prime.protocol import Reply, ProtocolConfig, TaskProtocol
from d2_prime.reference import FeatureMap, ReferenceConfig, ReferenceState

D, CHECKS, INPUTS, RUNS = 33, [], [], []


def clean(value):
    if isinstance(value, torch.Tensor):
        return clean(value.tolist())
    if hasattr(value, "__dataclass_fields__"):
        return clean(asdict(value))
    if isinstance(value, float) and not math.isfinite(value):
        return str(value)
    if isinstance(value, dict):
        return {str(k): clean(v) for k, v in value.items()}
    if isinstance(value, (tuple, list, set, frozenset, deque)):
        return [clean(v) for v in (sorted(value) if isinstance(value, (set, frozenset)) else value)]
    return value


def state(p):
    return clean({k: v for k, v in vars(p).items() if k != "_in_commit"})


def direction(x, mu, sigma, evidence, bound=1.):
    # Scalar implementation of the definition; no production reference helpers.
    scale = [min(1., max(.05, abs(a-b))) for a, b in zip(x, mu)]
    raw = [(a-b)/math.sqrt(D) for a, b in zip(x, mu)]
    raw += [(a-b)/math.sqrt(D) for a, b in zip(scale, sigma)]
    raw += [1-evidence]
    norm = math.sqrt(sum(v*v for v in raw))
    t = min(1., bound/norm) if norm else 1.
    return [v*t for v in raw]


class ModelOnlyOracle:
    """Independent Python scalar workflow: charge ONLY a, retain b=rho*a.

    Explicit event inputs, hand maintained task/source states and a-only window.
    It does not call production scoring, feature mapping, clipping or budgets.
    """
    def __init__(self, beta, rho, window=2.):
        self.beta, self.rho, self.window = beta/(1+rho), rho, window
        self.model, self.mu, self.sigma, self.e = [10., 20.], [0.]*D, [.25]*D, 0.
        self.version, self.next_task, self.tasks, self.history = 0, 0, {}, []
        self.sources = {0: (self.model[:], self.mu[:], self.sigma[:], self.e)}

    def issue(self, identity, now, delta):
        source = self.sources[self.version]
        local = [w-v for w, v in zip(source[0], delta)]
        task = {"identity": identity, "source": self.version, "expires": now+8., "local": local, "state": "arrived"}
        i = self.next_task
        self.next_task += 1
        self.tasks[i] = task
        return i, local

    def commit(self, now):
        rows, waiting = [], []
        for i, task in self.tasks.items():
            if task["state"] != "arrived":
                continue
            if now >= task["expires"]:
                task["state"] = "expired"
                continue
            spent = math.fsum(row["a"] for row in self.history
                if row["identity"] == task["identity"] and now-self.window < row["at"] <= now)
            remaining = max(0., self.beta-spent)
            if remaining == 0:
                waiting.append((i, "budget"))
                continue
            source = self.sources[task["source"]]
            raw = [w-l for w, l in zip(source[0], task["local"])]
            norm = math.sqrt(sum(v*v for v in raw))
            delta = [v*min(1., 1/norm) for v in raw] if norm else raw
            x = [max(-1., min(1., math.sqrt(32)*delta[0])),
                 max(-1., min(1., -math.sqrt(32)*delta[1]))]+[0.]*30+[math.sqrt(sum(v*v for v in delta))]
            rows.append((i, task, source, remaining, delta, x))
        # Test scenario has K=2, n_boot=1. Median implementation is independent.
        center = [statistics.median([row[5][j] for row in rows]) for j in range(D)] if rows else None
        mad = [min(1., max(.05, statistics.median([abs(row[5][j]-center[j]) for row in rows])))
               for j in range(D)] if rows else None
        receipts, changes = [], []
        for i, task, source, remaining, delta, x in rows:
            if source[3] >= .5:
                z2 = sum((x[j]-source[1][j])**2/(source[2][j]**2+(.1*(1-source[3]))**2)
                         for j in range(D))/D
            else:
                z2 = sum(((x[j]-center[j])/mad[j])**2 for j in range(D))/D
            g = (1-z2/9)**2 if z2 < 9 else 0.
            if g == 0:
                task["state"] = "rejected"
                continue
            h = 1/(1+self.version-task["source"])
            a0 = h*g/2
            # Independent algebraic cancellation: model-only lambda*a0 is
            # min(a0, L_M). No zero-balance tolerance or shared-budget helper.
            a = min(a0, remaining)
            b = self.rho*a
            v = direction(x, self.mu, self.sigma, self.e)
            receipts.append({"task_id": i, "identity": task["identity"], "at": now, "a": a, "b": b})
            changes.append((a, b, delta, v))
            task["state"] = "consumed"
        if changes:
            self.model = [self.model[j]-sum(a*delta[j] for a, _, delta, _ in changes) for j in range(2)]
            self.mu = [self.mu[j]+math.sqrt(D)*sum(b*v[j] for _, b, _, v in changes) for j in range(D)]
            self.sigma = [self.sigma[j]+math.sqrt(D)*sum(b*v[D+j] for _, b, _, v in changes) for j in range(D)]
            self.e += sum(b*v[-1] for _, b, _, v in changes)
            self.history.extend(receipts)
            self.version += 1
            self.sources[self.version] = (self.model[:], self.mu[:], self.sigma[:], self.e)
        return receipts, tuple(waiting)


class CommitAcceptance(unittest.TestCase):
    def record(self, **inputs):
        INPUTS.append({"case": self._testMethodName, **clean(inputs)})

    def check(self, label, actual, expected):
        CHECKS.append({"case": self._testMethodName, "label": label,
                       "actual": clean(actual), "expected": clean(expected), "kind": "exact"})
        self.assertEqual(clean(actual), clean(expected))

    def numeric(self, label, actual, expected):
        a, e = torch.as_tensor(actual, dtype=torch.float64), torch.as_tensor(expected, dtype=torch.float64)
        CHECKS.append({"case": self._testMethodName, "label": label,
            "actual": clean(a), "expected": clean(e), "kind": "numeric",
            "max_abs_error": (a-e).abs().max().item() if a.numel() else 0.})
        torch.testing.assert_close(a, e, atol=1e-10, rtol=1e-8)

    def make(self, capacity=1, n_boot=1, beta=.375, window=2., lifetime=5., eta_r=.5, eta_m=1.):
        pc = ProtocolConfig(identities=8, max_outstanding=8, capacity=capacity,
                            lifetime=lifetime, clip_norm=1., max_staleness=32, eta_model=eta_m)
        rc = ReferenceConfig(n_boot=n_boot, eta_reference=eta_r)
        bc, fm = BudgetConfig(window, beta), FeatureMap((0, 1), (1, -1), 32)
        p = TaskProtocol([10., 20.], pc, rc, fm, bc)
        self.record(protocol_config=pc, reference_config=rc, budget_config=bc, feature_map=fm, config_id=p.config_id)
        RUNS.append((self._testMethodName, p))
        return p

    def arrive(self, p, identity, delta=(0., 0.), at=None):
        task = p.issue(identity)
        # Fixed input generator, not an expected output; scalar oracle inputs are
        # separately declared for numerical assertions.
        source = p.snapshot(task.source_version).model
        local = tuple(w-v for w, v in zip(source, delta))
        packet = Reply(task.task_id, identity, task.source_version, local)
        at = p.now if at is None else at
        self.record(task=task, packet=packet, arrival=at)
        p.schedule_reply(packet, identity, at)
        p.advance(at)
        return task, packet

    def commit(self, p):
        deltas = {c["task_id"]: c["clipped_delta"] for c in p.candidates()}
        result = p.commit_event()
        self.record(at=p.now, result=result)
        self.assertTrue(p.audit_budget())
        # Direct influence check independently uses the recorded full source
        # delta and per-client direction, not the production clipping helper.
        by_id = {s.task_id: s for s in result.event.proposals}
        for receipt in result.receipts:
            proposal = by_id[receipt.task_id]
            norm_model = receipt.a*math.sqrt(sum(v*v for v in deltas[receipt.task_id]))
            norm_ref = math.sqrt(sum((receipt.b*v)**2 for v in proposal.direction))
            self.assertLessEqual(norm_ref, receipt.b*p.reference_config.clip_reference+1e-10)
            self.assertLessEqual(norm_model/p.config.clip_norm+norm_ref/p.reference_config.clip_reference,
                                 receipt.a+receipt.b+1e-10)
            self.record(direct_influence={"task_id": receipt.task_id, "model_norm": norm_model,
                "reference_norm": norm_ref, "normalized_sum": norm_model/p.config.clip_norm+norm_ref/p.reference_config.clip_reference,
                "coefficient_sum": receipt.a+receipt.b, "B_M": p.config.clip_norm,
                "B_R": p.reference_config.clip_reference})
        return result

    def test_budget_validation_and_window_endpoints(self):
        config = BudgetConfig(1., .5)
        receipt = Receipt(0, 0, .75, .4, .1, .5)
        self.record(config=config, receipt=receipt, probes=[1.25, 1.749, 1.75])
        budget = RollingBudget(config).record([receipt], .75)
        self.numeric("integer boundary does not reset", budget.remaining(0, 1.25), 0.)
        self.numeric("just inside left endpoint", budget.remaining(0, 1.749), 0.)
        self.numeric("left endpoint releases", budget.remaining(0, 1.75), .5)
        released = budget.prune(1.75)
        self.check("old entries removed, consumed retained", (released.entries, released.consumed), ((), frozenset({0})))
        with self.assertRaises(ValueError):
            released.record([replace(receipt, at=1.75)], 1.75)
        for window, beta in ((0., 1.), (1., 0.), (float("inf"), 1.), (1., float("nan"))):
            self.record(invalid_config=[window, beta])
            with self.assertRaises(ValueError):
                BudgetConfig(window, beta)
        with self.assertRaises(ValueError):
            budget.remaining(0, .5)

    def test_joint_model_reference_and_partial_scaling(self):
        p = self.make(capacity=3, n_boot=3, beta=.25)
        for i in range(3):
            self.arrive(p, i, (.125, 0.))
        result = self.commit(p)
        self.numeric("model scalar write", p.model, [9.9375, 20.])
        self.numeric("both channel coefficients", [[r.a, r.b, r.q] for r in result.receipts], [[1/6, 1/12, .25]]*3)
        self.numeric("same lambda both channels", [row[2] for row in result.scales], [.5]*3)
        x = [.125*math.sqrt(32)]+[0.]*31+[.125]
        v = direction(x, [0.]*D, [.25]*D, 0.)
        total = [.25*z for z in v]
        self.numeric("reference direct reconstruction", result.reference_displacement, total)
        self.numeric("reference center scalar write", p.reference.mu, [math.sqrt(D)*z for z in total[:D]])
        self.numeric("reference scale scalar write", p.reference.sigma, [.25+math.sqrt(D)*z for z in total[D:2*D]])
        self.numeric("reference evidence scalar write", p.reference.evidence, total[-1])
        self.numeric("snapshot committed model", p.snapshot(1).model, [9.9375, 20.])
        self.numeric("snapshot committed evidence", p.snapshot(1).evidence, total[-1])
        self.check("snapshot committed version", p.snapshot(1).version, 1)
        self.check("one successful version and three receipts", (p.version, len(p.ledger), p.outstanding), (1, 3, 0))
        for receipt in result.receipts:
            impact = receipt.a*.125+receipt.b*math.sqrt(sum(z*z for z in v))
            self.assertLessEqual(impact, .25+1e-10)

    def test_exact_exhaustion_and_zero_balance_wait(self):
        p = self.make()
        self.arrive(p, 0)
        result = self.commit(p)
        self.numeric("exact scaled coefficients", [result.receipts[0].a, result.receipts[0].b, result.receipts[0].q], [.25, .125, .375])
        self.numeric("balance exhausted", p.budget_remaining(0), 0.)
        self.numeric("paid reference evidence", p.reference.evidence, .125/math.sqrt(1.04))
        task, _ = self.arrive(p, 0)
        before = (p.model, p.reference, list(p.ledger), p.version)
        result = self.commit(p)
        self.check("zero balance waits", result.waiting, ((task.task_id, "budget"),))
        self.check("no future/current cold statistics", result.event.cold, None)
        self.check("waiting no new fees/reference/version", (p.reference, p.ledger, p.version), (before[1], before[2], before[3]))
        self.numeric("waiting no model write", p.model, [10., 20.])
        self.check("waiting slot retained", (p.outstanding, p.tasks[task.task_id].state), (1, "arrived"))

    def test_all_cold_waiting_without_reservations(self):
        p = self.make(capacity=3, n_boot=3, beta=.25)
        for i in (0, 1):
            self.arrive(p, i)
        result = self.commit(p)
        self.check("cold waits", result.waiting, ((0, "cold"), (1, "cold")))
        self.check("no reserved charges", (p.ledger, p.budget.entries, p.budget.consumed, p.version), ([], (), frozenset(), 0))
        self.numeric("full balances while waiting", [p.budget_remaining(i) for i in (0, 1)], [.25, .25])
        self.arrive(p, 2)
        self.check("new arrival permits commit", len(self.commit(p).receipts), 3)

    def test_budget_waiters_excluded_before_cold_stats(self):
        p = self.make(capacity=3, n_boot=3, beta=.25)
        for i in (0, 1, 2):
            self.arrive(p, i)
        self.commit(p)
        for i in (0, 3, 4):
            self.arrive(p, i)
        result = self.commit(p)
        self.check("only positive-balance candidates reach scorer", [x.identity for x in result.event.proposals], [3, 4])
        self.check("insufficient eligible samples", result.event.cold, None)
        self.check("budget and cold waiting reasons", result.waiting, ((3, "budget"), (4, "cold"), (5, "cold")))
        self.check("no second commit/fees", (p.version, len(p.ledger)), (1, 3))

    def test_waiting_retry_recomputes_reference_staleness_and_balance(self):
        p = self.make(capacity=2, window=3.)
        self.arrive(p, 0)
        self.commit(p)
        waiting, _ = self.arrive(p, 0)
        self.arrive(p, 1)
        result = self.commit(p)
        self.check("old identity waits while another writes", result.waiting, ((waiting.task_id, "budget"),))
        e1 = .125/math.sqrt(1.04)
        e2 = e1+.125*(1-e1)
        self.numeric("other identity changed current reference", p.reference.evidence, e2)
        p.advance(3.)
        result = self.commit(p)
        self.check("retry uses same original source", result.event.proposals[0].source_version, 1)
        self.numeric("recomputed staleness/coefficients", [result.event.proposals[0].h,
            result.event.proposals[0].a0, result.event.proposals[0].b0], [.5, .25, .125])
        self.numeric("retry current direction", result.event.proposals[0].direction[-1], 1-e2)
        self.numeric("retry reference scalar recurrence", p.reference.evidence, e2+.125*(1-e2))
        self.numeric("retry refreshed full budget", result.scales[0][1], .375)
        self.check("expiry remains original", p.tasks[waiting.task_id].expires_at, 5.)

    def test_expired_waiter_drops_without_refund_or_consumption(self):
        p = self.make(lifetime=1.)
        self.arrive(p, 0)
        self.commit(p)
        waiting, packet = self.arrive(p, 0)
        reference = p.reference
        p.advance(1.)
        self.commit(p)
        self.check("expired waiting task", (p.tasks[waiting.task_id].state, p.outstanding), ("expired", 0))
        self.check("expiry no extra fees/reference/version", (len(p.ledger), p.reference, p.version), (1, reference, 1))
        self.numeric("no early refund of committed task", p.budget_remaining(0), 0.)
        self.assertFalse(p.receive(packet, 0))
        p.advance(2.)
        self.commit(p)
        self.numeric("committed fee releases on window only", p.budget_remaining(0), .375)

    def test_cross_boundary_burst_is_not_periodic_reset(self):
        p = self.make(window=1.)
        p.advance(.75)
        self.arrive(p, 0)
        self.commit(p)
        p.advance(1.25)
        task, _ = self.arrive(p, 0)
        self.check("cross integer boundary still exhausted", self.commit(p).waiting, ((task.task_id, "budget"),))
        p.advance(1.75)
        self.check("left endpoint allows retry", len(self.commit(p).receipts), 1)
        self.numeric("record actual commit times", [r["at"] for r in p.ledger], [.75, 1.75])

    def test_actual_commit_time_not_issue_or_arrival(self):
        p = self.make(window=2.)
        task, packet = self.arrive(p, 0, at=1.)
        p.advance(1.5)
        self.commit(p)
        self.check("issued/arrived/charged are different", (task.issued_at, p.ledger[0]["at"]), (0., 1.5))
        p.advance(3.499)
        self.numeric("fee remains since commit", p.budget_remaining(0), 0.)
        p.advance(3.5)
        self.numeric("commit-based endpoint frees", p.budget_remaining(0), .375)

    def test_replay_never_charges_again_even_after_window_release(self):
        p = self.make()
        _, packet = self.arrive(p, 0)
        self.assertFalse(p.receive(packet, 0))  # Already arrived, before commit.
        self.commit(p)
        for at in (0., 2., 4.):
            p.advance(at)
            self.assertFalse(p.receive(packet, 0))
            self.commit(p)
        self.check("durable consumed marker survives release", (len(p.ledger), p.version, p.budget.consumed), (1, 1, frozenset({0})))
        self.check("active charges expired", p.budget.entries, ())

    def test_cancelling_model_vectors_do_not_refund(self):
        p = self.make(capacity=2, beta=2.)
        self.arrive(p, 0, (.125, 0.))
        self.arrive(p, 1, (-.125, 0.))
        result = self.commit(p)
        g = (296/297)**2
        self.numeric("independent cold weight", [x.g for x in result.event.proposals], [g, g])
        self.numeric("zero net model displacement", result.model_displacement, [0., 0.])
        self.numeric("nonzero per-identity fee despite cancellation", [r.q for r in result.receipts], [.75*g, .75*g])
        self.numeric("balances keep per-client fees", [p.budget_remaining(i) for i in (0, 1)], [2-.75*g]*2)
        self.check("cancelling positive write advances version", (p.version, len(p.ledger)), (1, 2))

    def test_zero_reference_direction_still_pays(self):
        p = self.make()
        # Literal committed-state boundary fixture; not an initialization change.
        p._reference = ReferenceState((0.,)*D, (.05,)*D, 1.)
        p._freeze()
        self.record(reference_fixture=p.reference)
        self.arrive(p, 0)
        result = self.commit(p)
        self.numeric("both net displacements zero", result.model_displacement+result.reference_displacement, [0.]*(2+2*D+1))
        self.numeric("zero innovation still charged", [result.receipts[0].a, result.receipts[0].b, result.receipts[0].q], [.25, .125, .375])
        self.check("zero displacement positive commit version", p.version, 1)

    def test_actual_score_rejection_finishes_without_either_write(self):
        p = self.make()
        p._reference = ReferenceState((0.,)*D, (.05,)*D, 1.)
        p._freeze()
        self.record(reference_fixture=p.reference)
        task, _ = self.arrive(p, 0, (.5, 0.))
        before = p.reference
        result = self.commit(p)
        self.numeric("reject residual scalar oracle", result.event.proposals[0].z, math.sqrt(500/33))
        self.check("g=0 terminates task", (result.rejected, p.tasks[task.task_id].state), ((0,), "rejected"))
        self.check("reject zero cost/reference/version", (p.ledger, p.reference, p.version), ([], before, 0))
        self.numeric("reject no model write", p.model, [10., 20.])

    def test_general_eta_ratio_and_binding_budget(self):
        p = self.make(beta=.625, eta_m=2., eta_r=.5)
        self.arrive(p, 0, (.125, 0.))
        result = self.commit(p)
        self.numeric("nonunit eta model coefficients", [result.receipts[0].a, result.receipts[0].b,
            result.receipts[0].q], [.5, .125, .625])
        self.numeric("nonunit eta common scale", result.scales[0][2], .25)
        self.numeric("nonunit eta model write", p.model, [9.9375, 20.])
        self.numeric("nonunit eta full exhaustion", p.budget_remaining(0), 0.)

    def test_direct_combined_influence_reaches_declared_bound(self):
        p = self.make()
        self.arrive(p, 0, (3., 4.))
        result = self.commit(p)
        # Hand oracle: source delta [3,4] has norm 5 -> [.6,.8].
        # Both full-model and joint-reference directions saturate their bounds.
        self.numeric("full-clipped joint model write", p.model, [9.85, 19.8])
        x = [1., -1.]+[0.]*30+[1.]
        v = direction(x, [0.]*D, [.25]*D, 0.)
        self.numeric("independent saturated reference direction", result.event.proposals[0].direction, v)
        ref_norm = math.sqrt(sum((.125*z)**2 for z in result.event.proposals[0].direction))
        self.numeric("combined direct bound attained", .25*math.sqrt(.6**2+.8**2)+ref_norm, .375)

    def test_reference_and_ledger_failures_leave_all_state_unchanged(self):
        for failure_site in ("d2_prime.protocol.write_reference", "d2_prime.budget.RollingBudget.record"):
            p = self.make()
            self.arrive(p, 0, (.125, 0.))
            before = state(p)
            self.record(failure_site=failure_site, before=before)
            def fail(*args, **kwargs):
                self.assertFalse(p.at_safe_event_boundary)
                self.numeric("no early model publication", p.model, [10., 20.])
                self.check("no early reference publication", p.reference.evidence, 0.)
                self.check("no early ledger publication", p.ledger, [])
                with self.assertRaises(RuntimeError):
                    p.commit_event()
                raise ValueError("injected prepublication failure")
            with patch(failure_site, side_effect=fail):
                with self.assertRaisesRegex(ValueError, "injected"):
                    p.commit_event()
            self.check("failed commit full state unchanged", state(p), before)
            self.check("failure returns safe boundary", p.at_safe_event_boundary, True)
            self.check("retry consumes exactly once", len(self.commit(p).receipts), 1)

    def test_missing_fee_receipt_and_duplicate_negative_controls(self):
        p = self.make()
        self.arrive(p, 0)
        self.commit(p)
        original = [dict(row) for row in p.ledger]
        cases = ("omitted_reference_fee", "omitted_entire_receipt", "duplicate_consumption")
        for case in cases:
            p.ledger = [dict(row) for row in original]
            if case == "omitted_reference_fee":
                p.ledger[0]["q"] = p.ledger[0]["a"]
            elif case == "omitted_entire_receipt":
                p.ledger.clear()
            else:
                p.ledger.append(dict(p.ledger[0]))
            self.record(negative_control=case, forged_ledger=p.ledger)
            with self.assertRaises(ValueError):
                p.audit_budget()
            self.check("negative detected", case in cases, True)
        p.ledger = original
        self.assertTrue(p.audit_budget())
        with self.assertRaises(ValueError):
            audit_history([Receipt(0, 0, 0., .25, .125, .375), Receipt(1, 0, 0., .25, .125, .375)], BudgetConfig(2., .375))

    def test_budget_mode_prevents_model_only_bypass_and_invalid_bindings(self):
        p = self.make()
        _, packet = self.arrive(p, 0)
        before = state(p)
        with self.assertRaises(RuntimeError):
            p.commit_model({0: 1.})
        self.check("bypass rejected without changes", state(p), before)
        for bad in (replace(packet, task_id=99), replace(packet, identity=1), replace(packet, source_version=1)):
            self.record(invalid_packet=bad)
            self.assertFalse(p.receive(bad, bad.identity))
        self.check("bad packets do not add charges", p.ledger, [])
        self.commit(p)
        other = self.make(beta=.5)
        self.assertNotEqual(p.config_id, other.config_id)

    def test_shared_vs_model_only_budget_full_state_trajectory(self):
        for rho, beta in ((.5, .375), (.1, .55)):
            p = self.make(capacity=2, beta=beta, eta_r=rho, lifetime=8.)
            oracle = ModelOnlyOracle(beta, rho)
            # Alternating valid identities, small fixed tensors; retry at release
            # after another identity advances the reference and commit version.
            for cycle in range(18):
                now = 4.*cycle
                p.advance(now)
                delta = (.03125 if cycle % 2 == 0 else 0., 0.)
                task, packet = self.arrive(p, 0, delta)
                expected_id, expected_local = oracle.issue(0, now, delta)
                self.check("oracle task id", task.task_id, expected_id)
                self.numeric("independently generated local input", packet.local_model, expected_local)
                actual = self.commit(p)
                expected, wait = oracle.commit(now)
                self.compare_oracle(p, actual, oracle, expected, wait)
                # This second task of the same identity waits without reserving.
                task, packet = self.arrive(p, 0, delta)
                oracle.issue(0, now, delta)
                actual = self.commit(p)
                expected, wait = oracle.commit(now)
                self.compare_oracle(p, actual, oracle, expected, wait)
                # A second identity writes while the first one waits.
                task, packet = self.arrive(p, 1, delta)
                oracle.issue(1, now, delta)
                actual = self.commit(p)
                expected, wait = oracle.commit(now)
                self.compare_oracle(p, actual, oracle, expected, wait)
                # Release window, use same source tasks and recompute proposals.
                p.advance(now+2.)
                actual = self.commit(p)
                expected, wait = oracle.commit(now+2.)
                self.compare_oracle(p, actual, oracle, expected, wait)
            self.record(rho=rho, shared_beta=beta, model_only_beta=oracle.beta,
                        oracle_final_model=oracle.model, oracle_final_reference=[oracle.mu, oracle.sigma, oracle.e],
                        oracle_history=oracle.history, oracle_tasks=oracle.tasks)

    def compare_oracle(self, p, actual, oracle, expected, wait):
        self.record(equivalence_actual=actual, model_only_expected_receipts=expected,
                    model_only_waiting=wait, model_only_history=oracle.history,
                    shared_history=p.ledger, shared_beta=p.budget.config.limit,
                    model_only_beta=oracle.beta, rho=oracle.rho)
        self.check("equivalent receipts ids", [r.task_id for r in actual.receipts], [r["task_id"] for r in expected])
        self.check("equivalent waiting", actual.waiting, wait)
        self.check("equivalent version", p.version, oracle.version)
        self.numeric("equivalent model", p.model, oracle.model)
        self.numeric("equivalent center", p.reference.mu, oracle.mu)
        self.numeric("equivalent scale", p.reference.sigma, oracle.sigma)
        self.numeric("equivalent evidence", p.reference.evidence, oracle.e)
        self.numeric("equivalent channel coefficients", [[r.a, r.b] for r in actual.receipts],
                     [[r["a"], r["b"]] for r in expected])
        self.check("equivalent task terminals", [t.state for t in p.tasks.values()],
                   [t["state"] for t in oracle.tasks.values()])


if __name__ == "__main__":
    assert Path(sys.executable).resolve() == Path(r"E:\anaconda3\python.exe").resolve()
    torch.set_num_threads(1)
    loader = unittest.defaultTestLoader
    current = loader.loadTestsFromTestCase(CommitAcceptance)
    regression = loader.discover(str(ROOT/"tests"), pattern="test_d2_prime_protocol.py")
    reference_regression = loader.discover(str(ROOT/"tests"), pattern="test_d2_prime_reference.py")
    counts = {"new": current.countTestCases(), "protocol": regression.countTestCases(), "reference": reference_regression.countTestCases()}
    result = unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite([current, regression, reference_regression]))
    failures = [(c._testMethodName, detail) for c, detail in result.failures+result.errors]
    failed_names = {c for c, _ in failures}
    files = ["docs/D2_PRIME_CHECKPOINTS_TRIMMED.md", "docs/D2_PRIME_CHECKPOINTS.md", "docs/D2_PRIME_DESIGN.md",
        "docs/D2_PRIME_DECISIONS.md", "docs/D2_PRIME_PHASE01_02_MANIFEST.json", "docs/D2_PRIME_PHASE03_MANIFEST.json",
        "d2_prime/protocol.py", "d2_prime/reference.py", "d2_prime/budget.py", "tests/test_d2_prime_commit.py",
        "tests/test_d2_prime_protocol.py", "tests/test_d2_prime_reference.py"]
    runs = [{"case": case, "final_state": state(p), "config_id": p.config_id} for case, p in RUNS]
    for row in runs:
        row["trajectory_sha256"] = hashlib.sha256(json.dumps(row["final_state"], sort_keys=True).encode()).hexdigest()
    for row in INPUTS:
        row["input_sha256"] = hashlib.sha256(json.dumps(row, sort_keys=True).encode()).hexdigest()
    manifest_path = ROOT/"docs/D2_PRIME_PHASE04_MANIFEST.json"
    previous = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
    prior_failures = previous.get("prior_failures", [])
    if previous.get("status") == "FAIL":
        prior_failures.append({k: previous[k] for k in ("input_sha256", "failed_cases", "failed_inputs", "max_abs_error")})
    manifest = {"gate_id": "0.4", "status": "PASS" if result.wasSuccessful() else "FAIL",
        "next_gate": "0.5+0.6+0.7" if result.wasSuccessful() else "0.4",
        "source_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "input_sha256": {f: hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in files},
        "execution": {"python": sys.executable, "torch": torch.__version__, "device": "cpu", "dtype": "float64",
            "counts": counts, "tests_run": result.testsRun, "failures": len(result.failures), "errors": len(result.errors),
            "real_training_tasks": 0, "atol": 1e-10, "rtol": 1e-8},
        "checks": CHECKS, "inputs": INPUTS, "runs": runs, "failed_cases": failures,
        "prior_failures": prior_failures,
        "failed_inputs": [r for r in INPUTS if r["case"] in failed_names],
        "max_abs_error": max((c["max_abs_error"] for c in CHECKS if c["kind"] == "numeric"), default=0.),
        "scope": "single event staged commit; no mid-event save API; no crash recovery or real training"}
    # Compact arrays keep the raw evidence reviewable without tens of thousands
    # of repeated coordinate lines. The whole file is one JSON result manifest.
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False,
        separators=(",", ":"), allow_nan=False)+"\n", encoding="utf-8")
    raise SystemExit(0 if result.wasSuccessful() else 1)
