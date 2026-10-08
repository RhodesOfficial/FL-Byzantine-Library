"""Gate 0.3: fixed tensors, literal fixtures and independent scalar oracles."""
from dataclasses import asdict, FrozenInstanceError, replace
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys
import unittest

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import torch
from d2_prime.protocol import ProtocolConfig, Reply, SourceSnapshot, TaskProtocol
from d2_prime.reference import (FeatureMap, ReferenceCandidate, ReferenceConfig,
    ReferenceState, clip_l2, cold_statistics, features, prepare_event,
    score_feature, validate_state, write_reference)

INPUTS, CHECKS = [], []
D = 33


def clean(value):
    if isinstance(value, torch.Tensor):
        return clean(value.tolist())
    if hasattr(value, "__dataclass_fields__"):
        return clean(asdict(value))
    if isinstance(value, float) and not math.isfinite(value):
        return str(value)
    if isinstance(value, dict):
        return {str(k): clean(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [clean(v) for v in value]
    return value


def f(projected=0., norm=0.):
    return (projected,) * 32 + (norm,)


def r(mu=0., sigma=.25, evidence=0.):
    return ReferenceState((mu,) * D, (sigma,) * D, evidence)


def scalar_direction(x, before, bound, sigma_min=.05):
    # Independent Python scalars; does not call a production normalizer/clipper.
    target_scale = [min(1., max(sigma_min, abs(a-b))) for a, b in zip(x, before.mu)]
    raw = [(a-b)/math.sqrt(D) for a, b in zip(x, before.mu)]
    raw += [(a-b)/math.sqrt(D) for a, b in zip(target_scale, before.sigma)]
    raw += [1-before.evidence]
    length = math.sqrt(sum(v*v for v in raw))
    t = min(1., bound/length) if length else 1.
    return target_scale, [t*v for v in raw], t


class ReferenceAcceptance(unittest.TestCase):
    def record(self, **inputs):
        INPUTS.append({"case": self._testMethodName, **clean(inputs)})

    def check(self, label, actual, expected):
        CHECKS.append({"case": self._testMethodName, "label": label,
                       "actual": clean(actual), "expected": clean(expected), "kind": "exact"})
        self.assertEqual(clean(actual), clean(expected))

    def numeric(self, label, actual, expected):
        a = torch.as_tensor(actual, dtype=torch.float64)
        e = torch.as_tensor(expected, dtype=torch.float64)
        CHECKS.append({"case": self._testMethodName, "label": label,
            "actual": clean(a), "expected": clean(e), "kind": "numeric",
            "max_abs_error": (a-e).abs().max().item() if a.numel() else 0.})
        torch.testing.assert_close(a, e, atol=1e-10, rtol=1e-8)

    def candidates(self, source, rows, version=0):
        return [ReferenceCandidate(i, i, version, source, x) for i, x in enumerate(rows)]

    def protocol(self, capacity=3, **options):
        config = ProtocolConfig(identities=8, max_outstanding=8, capacity=capacity,
                                lifetime=5., clip_norm=1.)
        rc = ReferenceConfig(**options)
        mapping = FeatureMap((0, 1), (1, -1), 32)
        p = TaskProtocol([10., 20.], config, rc, mapping)
        self.record(protocol_config=config, reference_config=rc, feature_map=mapping,
                    config_id=p.config_id, initial_model=[10., 20.])
        return p

    def reply(self, p, identity, local, arrival=0.):
        task = p.issue(identity)
        packet = Reply(task.task_id, task.identity, task.source_version, tuple(local))
        self.record(task=task, packet=packet, arrival=arrival)
        p.schedule_reply(packet, identity, arrival)
        return task

    def test_full_clip_and_fixed_features(self):
        mapping = FeatureMap((0, 1), (1, -1), 32)
        self.record(mapping=mapping, delta=[-3., -4.], model_bound=1.)
        clipped = clip_l2([-3., -4.], 1.)
        self.numeric("3-4-5 full clip", clipped, [-.6, -.8])
        self.numeric("saturation plus full norm", features(clipped, mapping, 1.),
                     [-1., 1.] + [0.]*30 + [1.])
        collisions = FeatureMap((0, 0, 1), (1, -1, 1), 32)
        self.record(mapping=collisions, clipped_delta=[.02, .01, .03])
        self.numeric("signed bucket sum", features([.02, .01, .03], collisions, 1.),
                     [.01*math.sqrt(32), .03*math.sqrt(32)] + [0.]*30 + [math.sqrt(.0014)])
        self.numeric("zero clip", clip_l2([0., 0.], 1.), [0., 0.])
        self.numeric("zero feature", features([0., 0.], mapping, 1.), [0.]*D)

    def test_public_map_is_repeatable_and_rng_isolated(self):
        config = ReferenceConfig()
        before = torch.random.get_rng_state().clone()
        first, second = FeatureMap.generate(12, config), FeatureMap.generate(12, config)
        self.record(config=config, first=first, second=second)
        # Recorded seed-0 arrays are literal, independently inspected fixed fixtures.
        self.check("seed-zero buckets", first.buckets, (12, 15, 21, 0, 3, 27, 3, 7, 9, 19, 21, 18))
        self.check("seed-zero signs", first.signs, (-1, 1, -1, -1, -1, -1, -1, 1, -1, 1, 1, -1))
        self.check("repeatability", first, second)
        self.assertTrue(torch.equal(before, torch.random.get_rng_state()))
        with self.assertRaises(FrozenInstanceError):
            first.signs = (1,)*12

    def test_initial_state_and_normalization(self):
        config = ReferenceConfig()
        initial = ReferenceState.initial(config)
        self.record(config=config, initial=initial)
        self.check("initial reference", initial, r())
        self.check("initial uncertainty/ready", (initial.uncertainty, initial.ready(config)), (1., False))
        self.numeric("fixed normalization", initial.normalized(),
                     [0.]*D + [.25/math.sqrt(D)]*D + [0.])
        with self.assertRaises(FrozenInstanceError):
            initial.evidence = .9

    def test_even_and_odd_cold_median_mad(self):
        config = ReferenceConfig()
        rows = [f(v) for v in (0., .2, .4, 1.)]
        self.record(config=config, rows=rows)
        cold = cold_statistics(rows, config)
        self.numeric("even median", cold.center, [.3]*32+[0.])
        self.numeric("even MAD without normal factor", cold.scale, [.2]*32+[.05])
        _, z, g = score_feature(f(.4), r(), cold, config)
        self.numeric("cold residual", z, math.sqrt(8/33))
        self.numeric("cold weight", g, (1-8/297)**2)
        odd_rows = [f(v) for v in (-.2, 0., .4)]
        self.record(odd_rows=odd_rows)
        odd = cold_statistics(odd_rows, config)
        self.numeric("odd median", odd.center, [0.]*D)
        self.numeric("odd MAD", odd.scale, [.2]*32+[.05])

    def test_cold_waits_for_arrivals_not_future_packets(self):
        p = self.protocol()
        old = p.snapshot(0)
        for i in (0, 1):
            self.reply(p, i, [10., 20.])
        self.reply(p, 2, [10., 20.], arrival=1.)
        p.advance(0.)
        event = p.prepare_reference_event()
        self.record(event=event)
        self.check("two arrived, future excluded", [s.path for s in event.proposals], ["waiting"]*2)
        self.check("no cold stats", event.cold, None)
        write = write_reference(event, {})
        self.check("wait has no reference increment", write.displacement, (0.,)*(2*D+1))
        self.numeric("wait keeps R0", write.after.normalized(), [0.]*D+[.25/math.sqrt(D)]*D+[0.])
        self.check("read-only protocol", (p.version, p.ledger, p.reference, p.model.tolist()),
                   (0, [], r(), [10., 20.]))
        p.advance(1.)
        event = p.prepare_reference_event()
        self.check("three arrived bootstrap", [s.path for s in event.proposals], ["cold"]*3)
        self.check("bootstrap g", [s.g for s in event.proposals], [1.]*3)
        self.check("never backfill S0", p.snapshot(0), old)
        self.check("no arrival/reference writes", p.reference, r())

    def test_cold_changes_only_with_this_event_set(self):
        config = ReferenceConfig()
        rows1, rows2 = [f(0.)]*3, [f(0.), f(.4), f(.8)]
        self.record(config=config, source=r(), event1=rows1, event2=rows2)
        first = prepare_event(self.candidates(r(), rows1), r(), config, 3, 1., 0)
        second = prepare_event(self.candidates(r(), rows2), r(.9, .8, .95), config, 3, 1., 0)
        self.numeric("event1 score", first.proposals[0].g, 1.)
        self.numeric("event2 score", second.proposals[0].g, (1-32/297)**2)
        self.numeric("event2 center", second.cold.center, [.4]*32+[0.])
        again = prepare_event(self.candidates(r(), rows1), r(.9, .8, .95), config, 3, 1., 0)
        self.check("current ready cannot replace cold source", [s.path for s in again.proposals], ["cold"]*3)
        self.numeric("unchanged set unchanged cold score", again.proposals[0].g, 1.)

    def test_ready_threshold_both_sides_and_uncertainty_term(self):
        config = ReferenceConfig()
        x = (.3, .0) + (0.,)*30 + (.4,)
        self.record(config=config, feature=x, evidence=[.5-1e-12, .5, 1.])
        self.check("below threshold waits", score_feature(x, r(evidence=.5-1e-12), None, config),
                   ("waiting", None, None))
        path, z, g = score_feature(x, r(evidence=.5), None, config)
        self.check("at threshold source path", path, "source")
        z2 = .25/(33*(.25**2+.05**2))
        self.numeric("uncertainty residual", z, math.sqrt(z2))
        self.numeric("uncertainty weight", g, (1-z2/9)**2)
        _, z1, _ = score_feature(x, r(evidence=1.), None, config)
        self.numeric("fully ready residual", z1, math.sqrt(.25/(33*.25**2)))

    def test_normal_and_cutoff_rejection(self):
        config = ReferenceConfig()
        source = r(evidence=1.)
        self.record(config=config, source=source, features=[f(0.), f(.75, .75), f(1., 1.)])
        self.check("normal zero", score_feature(f(), source, None, config), ("source", 0., 1.))
        self.check("exact cutoff", score_feature(f(.75, .75), source, None, config), ("source", 3., 0.))
        self.check("above cutoff", score_feature(f(1., 1.), source, None, config), ("source", 4., 0.))
        event = prepare_event(self.candidates(source, [f(1., 1.)]), r(), config, 3, 1., 0)
        self.check("rejected has no proposals", (event.proposals[0].a0, event.proposals[0].b0,
                   event.proposals[0].direction), (0., 0., ()))
        write = write_reference(event, {})
        self.check("rejected has no contributions", write.contributions, ())
        self.numeric("reject leaves reference", write.after.normalized(),
                     [0.]*D+[.25/math.sqrt(D)]*D+[0.])

    def test_cold_outlier_rejected_fixed_K_not_renormalized(self):
        config = ReferenceConfig()
        rows = [f(), f(), f(1., 1.)]
        self.record(config=config, source=r(), features=rows, capacity=3)
        event = prepare_event(self.candidates(r(), rows), r(), config, 3, 1., 0)
        self.check("cold rejection", [p.g for p in event.proposals], [1., 1., 0.])
        self.numeric("fixed denominator model", [p.a0 for p in event.proposals], [1/3, 1/3, 0.])
        self.numeric("fixed denominator reference", [p.b0 for p in event.proposals], [.1/3, .1/3, 0.])
        write = write_reference(event, {0: .1/3, 1: .1/3})
        self.numeric("two accepted evidence", write.after.evidence, (.2/3)/math.sqrt(1.04))

    def test_staleness_and_small_ready_batch(self):
        config = ReferenceConfig()
        source = r(evidence=1.)
        self.record(config=config, feature=f(), source=source, source_version=2, current_version=5, capacity=20)
        event = prepare_event(self.candidates(source, [f()], version=2), r(), config, 20, 1., 5)
        self.check("ready single sample allowed", event.proposals[0].path, "source")
        self.numeric("stale fixed-K coefficients", [event.proposals[0].h, event.proposals[0].a0,
                     event.proposals[0].b0], [1/4, 1/80, .1/80])

    def test_frozen_source_score_independent_of_current_and_future(self):
        config, source, x = ReferenceConfig(), r(.1, .2, .6), f(.2, .2)
        current_states = [r(), r(-.4, .7, .9), r(.8, .05, 1.)]
        self.record(config=config, frozen_source=source, feature=x, changed_current_states=current_states)
        expected_z2 = .1**2/(.2**2+(.1*.4)**2)
        directions = []
        for before in current_states:
            event = prepare_event(self.candidates(source, [x], version=2), before, config, 3, 1., 5)
            p = event.proposals[0]
            self.check("frozen normal path", p.path, "source")
            self.numeric("source residual invariant", p.z, math.sqrt(expected_z2))
            self.numeric("source weight invariant", p.g, (1-expected_z2/9)**2)
            _, expected, _ = scalar_direction(x, before, 1.)
            self.numeric("innovation depends on current prestate", p.direction, expected)
            directions.append(p.direction)
        self.assertEqual(len(set(directions)), 3)
        self.check("source remains immutable", source, r(.1, .2, .6))

    def test_joint_clip_per_client_and_reference_reconstruction(self):
        config, before = ReferenceConfig(), r()
        rows = [f()]*3
        self.record(config=config, before=before, source=r(), features=rows, coefficients={i: .1/3 for i in range(3)})
        event = prepare_event(self.candidates(r(), rows), before, config, 3, 1., 0)
        v = [0.]*D+[-.2/math.sqrt(D)/math.sqrt(1.04)]*D+[1/math.sqrt(1.04)]
        for p in event.proposals:
            self.numeric("joint clip includes paid evidence", p.direction, v)
            self.numeric("joint direction norm", math.sqrt(sum(x*x for x in p.direction)), 1.)
        write = write_reference(event, {i: .1/3 for i in range(3)})
        self.record(event=event, write=write)
        expected_total = [.1*x for x in v]
        self.numeric("total normalized displacement", write.displacement, expected_total)
        for task_id, contribution in write.contributions:
            self.numeric("direct client increment", contribution, [(.1/3)*x for x in v])
        self.numeric("contributions independently sum", [sum(c[j] for _, c in write.contributions)
                     for j in range(2*D+1)], expected_total)
        self.numeric("center after", write.after.mu, [0.]*D)
        self.numeric("scale after", write.after.sigma, [.25-.02/math.sqrt(1.04)]*D)
        self.numeric("evidence after", write.after.evidence, .1/math.sqrt(1.04))
        self.check("before not changed", before, r())

    def test_same_prestate_all_candidates_and_order_invariance(self):
        config, before, source = ReferenceConfig(clip_reference=.2), r(.1, .3, .4), r(0., 1., 1.)
        rows = [f(-.2, .1), f(.5, .4), f(.9, .8)]
        inputs = self.candidates(source, rows)
        self.record(config=config, before=before, source=source, rows=rows, order=[2, 0, 1])
        event = prepare_event([inputs[i] for i in (2, 0, 1)], before, config, 3, 1., 0)
        ordered = prepare_event(inputs, before, config, 3, 1., 0)
        self.check("deterministic preparation", event, ordered)
        expected_terms, coefficients = [], {}
        for i, x in enumerate(rows):
            scale, direction, _ = scalar_direction(x, before, .2)
            z2 = sum(v*v for v in x)/D
            b = .1/3*(1-z2/9)**2
            coefficients[i] = b
            expected_terms.append([b*v for v in direction])
            self.numeric("same prestate target", event.proposals[i].scale_target, scale)
            self.numeric("same prestate direction", event.proposals[i].direction, direction)
        write = write_reference(event, coefficients)
        expected_delta = [sum(t[j] for t in expected_terms) for j in range(2*D+1)]
        self.numeric("batch direct increment", write.displacement, expected_delta)
        self.numeric("batch center", write.after.mu, [.1+math.sqrt(D)*v for v in expected_delta[:D]])
        self.numeric("batch scale", write.after.sigma, [.3+math.sqrt(D)*v for v in expected_delta[D:2*D]])
        self.numeric("batch evidence", write.after.evidence, .4+expected_delta[-1])

    def test_reference_domains_convex_oracle_at_boundaries(self):
        # 36 fixed boundary/interior events; unrelated to the old 500 formula checks.
        config = ReferenceConfig(eta_reference=1., clip_reference=.35)
        for mu in (-1., 0., 1.):
            for sigma in (.05, .25, 1.):
                for evidence in (0., .49, .5, 1.):
                    before = r(mu, sigma, evidence)
                    rows = [f(-1., 0.), f(0., .5), f(1., 1.)]
                    # Each ready source equals its own feature: g=1 independently.
                    candidates = [ReferenceCandidate(i, i, 0, ReferenceState(x, (1.,)*D, 1.), x)
                                  for i, x in enumerate(rows)]
                    self.record(config=config, before=before, candidates=candidates, coefficients={i: 1/3 for i in range(3)})
                    event = prepare_event(candidates, before, config, 3, 1., 0)
                    write = write_reference(event, {i: 1/3 for i in range(3)})
                    weights, scales = [], []
                    for x in rows:
                        scale, _, t = scalar_direction(x, before, .35)
                        weights.append(t/3)
                        scales.append(scale)
                    retained = 1-sum(weights)
                    expected_mu = [retained*mu+sum(w*x[j] for w, x in zip(weights, rows)) for j in range(D)]
                    expected_sigma = [retained*sigma+sum(w*x[j] for w, x in zip(weights, scales)) for j in range(D)]
                    expected_e = retained*evidence+sum(weights)
                    self.numeric("convex center oracle", write.after.mu, expected_mu)
                    self.numeric("convex scale oracle", write.after.sigma, expected_sigma)
                    self.numeric("convex evidence oracle", write.after.evidence, expected_e)
                    self.assertTrue(all(-1-1e-10 <= v <= 1+1e-10 for v in write.after.mu))
                    self.assertTrue(all(.05-1e-10 <= v <= 1+1e-10 for v in write.after.sigma))
                    self.assertTrue(0-1e-10 <= write.after.evidence <= 1+1e-10)

    def test_paid_evidence_cold_to_ready_trajectory(self):
        config, state = ReferenceConfig(), r()
        expected_e, expected_sigma = 0., .25
        paths = []
        for k in range(30):
            self.record(config=config, version=k, source=state, rows=[f()]*3, coefficients={i: .1/3 for i in range(3)})
            event = prepare_event(self.candidates(state, [f()]*3, version=k), state, config, 3, 1., k)
            paths.append(event.proposals[0].path)
            expected_path = "source" if expected_e >= .5 else "cold"
            self.check("threshold-driven trajectory path", paths[-1], expected_path)
            norm = math.sqrt((.05-expected_sigma)**2+(1-expected_e)**2)
            t = min(1., 1/norm) if norm else 1.
            expected_e += .1*t*(1-expected_e)
            expected_sigma += .1*t*(.05-expected_sigma)
            state = write_reference(event, {i: .1/3 for i in range(3)}).after
            self.numeric("scalar evidence recurrence", state.evidence, expected_e)
            self.numeric("scalar scale recurrence", state.sigma, [expected_sigma]*D)
        self.check("cold-to-ready event counts", (paths.count("cold"), paths.count("source")), (7, 23))
        self.record(final_reference=state, paths=paths)

    def test_mixed_ready_and_cold_low_sample_event(self):
        config, before = ReferenceConfig(), r(.2, .5, .9)
        candidates = [ReferenceCandidate(0, 0, 0, r(), f()),
                      ReferenceCandidate(1, 1, 1, r(evidence=1.), f())]
        self.record(config=config, before=before, candidates=candidates)
        event = prepare_event(candidates, before, config, 3, 1., 2)
        self.check("old cold source still waits", [p.path for p in event.proposals], ["waiting", "source"])
        self.numeric("only ready nominal reference", [p.b0 for p in event.proposals], [0., .1/6])
        write = write_reference(event, {1: .1/6})
        _, direction, _ = scalar_direction(f(), before, 1.)
        self.numeric("only ready reference writes", write.displacement, [(.1/6)*v for v in direction])

    def test_protocol_snapshot_mapping_binding_and_read_only_events(self):
        p = self.protocol()
        snapshot = p.snapshot(0)
        # An old in-flight task keeps S0 alive after a model-only seam commit.
        old = p.issue(0)
        for i in (1, 2, 3):
            self.reply(p, i, [10., 20.])
        p.advance(0.)
        event = p.prepare_reference_event()
        write = write_reference(event, {i: .1/3 for i in (1, 2, 3)})
        self.check("pure writer cannot silently commit", (p.reference, p.snapshot(0)), (r(), snapshot))
        self.assertGreater(write.after.evidence, 0.)
        p.commit_model({i: 1/3 for i in (1, 2, 3)})
        self.check("old task source binding", old.source_version, 0)
        self.check("retained source snapshot", p.snapshot(0), snapshot)
        self.check("model-only seam preserves reference", p.snapshot(1).evidence, 0.)
        self.check("new task hash binding", p.issue(4).config_id, p.config_id)
        with self.assertRaises(FrozenInstanceError):
            snapshot.mu = (1.,)*D
        different = TaskProtocol([10., 20.], p.config, p.reference_config, FeatureMap((1, 0), (1, -1), 32))
        self.assertNotEqual(p.config_id, different.config_id)
        self.check("actual mapping is saved", asdict(p.feature_map),
                   {"buckets": (0, 1), "signs": (1, -1), "bucket_count": 32})
        self.record(snapshot=snapshot, event=event, pure_write=write, after_snapshot=p.snapshot(1))

    def test_protocol_freezes_noninitial_ready_reference(self):
        p = self.protocol()
        old_cold = p.issue(0)
        # Explicit committed-state fixtures exercise _freeze, not a gate 0.4
        # transaction. No production setter/reference-only commit is introduced.
        p._reference, p.version = r(.1, .2, .6), 1
        p._freeze()
        ready = p.issue(1)
        frozen = p.snapshot(1)
        self.record(fixture_reference=r(.1, .2, .6), fixture_version=1, task=ready)
        delta = 1/(2*math.sqrt(32))
        p.schedule_reply(Reply(ready.task_id, 1, 1, (10.-delta, 20.)), 1, 0.)
        p.schedule_reply(Reply(old_cold.task_id, 0, 0, (10., 20.)), 0, 0.)
        expected_x = [.5]+[0.]*31+[delta]
        z2 = sum((v-.1)**2 for v in expected_x)/(33*(.2**2+(.1*.4)**2))
        for version, current in ((2, r(.8, .5, .9)), (3, r(-.8, .05, 1.))):
            p._reference, p.version = current, version
            p._freeze()
            p.advance(0.)
            event = p.prepare_reference_event()
            by_id = {proposal.task_id: proposal for proposal in event.proposals}
            self.record(current_fixture=current, current_version=version, event=event)
            self.check("cold source never rebound to ready current", by_id[old_cold.task_id].path, "waiting")
            self.check("ready source reads frozen snapshot", by_id[ready.task_id].path, "source")
            self.numeric("protocol source residual", by_id[ready.task_id].z, math.sqrt(z2))
            self.numeric("protocol source weight", by_id[ready.task_id].g, (1-z2/9)**2)
            self.check("noninitial snapshot values remain frozen", p.snapshot(1),
                SourceSnapshot(1, (10., 20.), (.1,)*D, (.2,)*D, .6, p.config_id))
        self.check("original snapshot object unchanged", frozen.evidence, .6)
        self.check("no scoring side effects", (p.ledger, p.model.tolist()), ([], [10., 20.]))

    def test_zero_reference_direction_and_zero_coefficients(self):
        config = ReferenceConfig()
        before = r(0., .05, 1.)
        self.record(config=config, before=before, candidates=self.candidates(before, [f()]))
        event = prepare_event(self.candidates(before, [f()]), before, config, 3, 1., 0)
        self.numeric("zero joint innovation", event.proposals[0].direction, [0.]*(2*D+1))
        for b in (0., .1/3):
            write = write_reference(event, {0: b})
            self.numeric("zero direction reference unchanged", write.after.normalized(),
                         [0.]*D+[.05/math.sqrt(D)]*D+[1.])
        # No claim about actual budget charges: those are gate 0.4.

    def test_invalid_numbers_dimensions_domains_and_coefficients(self):
        config, mapping = ReferenceConfig(), FeatureMap((0, 1), (1, -1), 32)
        bad_vectors = [[float("nan"), 0.], [float("inf"), 0.], [1e308, 1e308]]
        for delta in bad_vectors:
            self.record(delta=delta, bound=1.)
            with self.assertRaises(ValueError):
                clip_l2(delta, 1.)
        for delta in ([0.], [2., 0.], [float("nan"), 0.]):
            self.record(feature_input=delta, mapping=mapping)
            with self.assertRaises(ValueError):
                features(delta, mapping, 1.)
        for state in (r(2.), r(sigma=.01), r(evidence=1.1)):
            self.record(bad_reference=state)
            with self.assertRaises(ValueError):
                validate_state(state, config)
        with self.assertRaises(ValueError):
            r(evidence=float("nan"))
        source = r(evidence=1.)
        for x in ((0.,)*32, f(2.), f(0., -1.), f(float("inf"))):
            self.record(bad_feature=x, source=source)
            with self.assertRaises(ValueError):
                score_feature(x, source, None, config)
        event = prepare_event(self.candidates(source, [f()]), r(), config, 3, 1., 0)
        for b in (-.1, .1, float("nan"), float("inf")):
            self.record(event=event, bad_coefficient=b)
            with self.assertRaises(ValueError):
                write_reference(event, {0: b})
        self.check("invalid inputs do not change before", event.before, r())

    def test_event_shape_and_configuration_guards(self):
        config = ReferenceConfig()
        good = self.candidates(r(evidence=1.), [f(), f(), f()])
        for rows, version in ((good+[replace(good[0], task_id=3, identity=3)], 0),
            ([good[0], replace(good[1], identity=0)], 0), ([good[0], good[0]], 0),
            ([replace(good[0], source_version=1)], 0)):
            self.record(config=config, invalid_candidates=rows, current_version=version)
            with self.assertRaises(ValueError):
                prepare_event(rows, r(), config, 3, 1., version)
        for option in ({"eta_reference": 1.1}, {"sigma_min": .3}, {"z_cut": float("nan")},
                       {"n_boot": 0}, {"projection_buckets": 0}):
            self.record(invalid_config=option)
            with self.assertRaises(ValueError):
                ReferenceConfig(**option)
        with self.assertRaises(ValueError):
            TaskProtocol([10.], ProtocolConfig(capacity=2), config)
        with self.assertRaises(RuntimeError):
            TaskProtocol([10.]).prepare_reference_event()


if __name__ == "__main__":
    assert Path(sys.executable).resolve() == Path(r"E:\anaconda3\python.exe").resolve()
    torch.set_num_threads(1)
    loader = unittest.defaultTestLoader
    current = loader.loadTestsFromTestCase(ReferenceAcceptance)
    regression = loader.discover(str(ROOT / "tests"), pattern="test_d2_prime_protocol.py")
    new_count, regression_count = current.countTestCases(), regression.countTestCases()
    result = unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite([current, regression]))
    failures = [(case._testMethodName, detail) for case, detail in result.failures+result.errors]
    failed_names = {name for name, _ in failures}
    files = ["docs/D2_PRIME_CHECKPOINTS_TRIMMED.md", "docs/D2_PRIME_CHECKPOINTS.md",
        "docs/D2_PRIME_DESIGN.md", "docs/D2_PRIME_PHASE01_02_MANIFEST.json",
        "d2_prime/protocol.py", "d2_prime/reference.py", "tests/test_d2_prime_protocol.py",
        "tests/test_d2_prime_reference.py"]
    manifest = {"gate_id": "0.3", "status": "PASS" if result.wasSuccessful() else "FAIL",
        "next_gate": "0.4" if result.wasSuccessful() else "0.3",
        "source_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "specification": "D2_PRIME_DESIGN:2.1/phase0.3-v1",
        "defaults": {"reference": asdict(ReferenceConfig()),
            "synthetic_protocol": asdict(ProtocolConfig(identities=8, max_outstanding=8,
                capacity=3, lifetime=5., clip_norm=1.)),
            "features": "d_p=32, d=33 throughout; explicit maps or seed-0 generated arrays in inputs",
            "pure_writer": "final b_i supplied explicitly; no budget, model or protocol writes"},
        "input_sha256": {f: hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in files},
        "execution": {"python": sys.executable, "torch": torch.__version__, "device": "cpu",
            "dtype": "float64", "new_tests": new_count, "regression_tests": regression_count,
            "tests_run": result.testsRun, "failures": len(result.failures), "errors": len(result.errors),
            "real_training_tasks": 0, "atol": 1e-10, "rtol": 1e-8},
        "oracle": "Literal vectors plus independent Python scalar residuals, norms, convex sums and recurrences. No production function generates expected numbers.",
        "checks": CHECKS, "inputs": INPUTS,
        "failed_cases": failures, "failed_inputs": [row for row in INPUTS if row["case"] in failed_names],
        "max_abs_error": max((c["max_abs_error"] for c in CHECKS if c["kind"] == "numeric"), default=0.),
        "not_covered": ["0.4 shared sliding budgets/eligibility and dual-channel commit",
            "0.5+ checkpoint recovery", "FLGo training integration", "real training or defense performance"]}
    contexts = {}
    for row in manifest["inputs"]:
        context = contexts.setdefault(row["case"], {
            "reference": manifest["defaults"]["reference"],
            "protocol": manifest["defaults"]["synthetic_protocol"], "feature_map": None})
        if "reference_config" in row or "config" in row:
            context["reference"] = row.get("reference_config", row.get("config"))
        if "protocol_config" in row:
            context["protocol"] = row["protocol_config"]
        if "capacity" in row:
            context["protocol"] = dict(context["protocol"], capacity=row["capacity"])
        if "feature_map" in row or "mapping" in row:
            context["feature_map"] = row.get("feature_map", row.get("mapping"))
        row["config_sha256"] = hashlib.sha256(json.dumps(context, sort_keys=True).encode()).hexdigest()
        row["input_sha256"] = hashlib.sha256(json.dumps(row, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    (ROOT/"docs/D2_PRIME_PHASE03_MANIFEST.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, allow_nan=False)+"\n", encoding="utf-8")
    raise SystemExit(0 if result.wasSuccessful() else 1)
