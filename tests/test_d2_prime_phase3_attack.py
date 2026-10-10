"""Independent scalar/constant oracles for causal_joint_32_v1; fixed tensors only."""
from collections import deque
import math
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT/'easyFL')]
import torch

from attacks.causal_joint_32 import CausalJoint32Attacker, clip_to_cap, _unit
from flgo_byzantine.async_attack_state import AttackBaselineState
from flgo_byzantine.async_baseline_state import DeliveredReply


def attacker_with(labels, present):
    images = torch.zeros(len(labels), 3, 32, 32)
    model = torch.nn.Linear(4, 3)
    a = CausalJoint32Attacker(images, torch.tensor(labels), present, 0.97, model, torch.device('cpu'))
    return a


def logsumexp(values):
    m = max(values)
    return m+math.log(sum(math.exp(v-m) for v in values))


class CandidateMathTests(unittest.TestCase):
    def test_clip_to_cap_scales_only_above_bound(self):
        cap = 10*0.97
        small = torch.tensor([3., 4.])  # norm 5 < cap: unchanged
        self.assertTrue(torch.equal(clip_to_cap(small, cap), small))
        big = torch.tensor([30., 40.])  # norm 50 -> scaled to cap
        out = clip_to_cap(big, cap)
        self.assertAlmostEqual(out.norm().item(), cap, places=5)
        self.assertAlmostEqual((out[1]/out[0]).item(), 4/3, places=6)

    def test_vector_formula_against_hand_constant(self):
        a = attacker_with([0, 1, 2], [0, 1, 2])
        mu = torch.tensor([3., 0., 0., 0.])     # |mu|=3, v1=[1,0,0,0]
        grad = torch.tensor([0., 2., 0., 0.])   # v2=[0,1,0,0]
        resolved, info = a.resolve_directions(mu, _unit(grad)[0], torch.tensor([0., 0., 1., 0.]))
        self.assertAlmostEqual(info['mu_vis_norm'], 3.0, places=6)
        cands = a.build_candidates(mu, resolved)
        self.assertEqual(len(cands), 8)
        # d=2 (grad direction), gamma=1: u = clip(mu - 1*0.97*[0,1,0,0]) = [3,-0.97,0,0]
        c = next(c for c in cands if c['d'] == 2 and c['gamma'] == 1.0)
        self.assertTrue(torch.allclose(c['vector'], torch.tensor([3., -0.97, 0., 0.]), atol=1e-6))
        # gamma=0 ignores direction: both d give clip(mu)=mu (norm 3 < cap)
        for c0 in (c for c in cands if c['gamma'] == 0.0):
            self.assertTrue(torch.allclose(c0['vector'], mu, atol=1e-6))

    def test_direction_fallback_chain(self):
        a = attacker_with([0, 1], [0, 1])
        zero = torch.zeros(4)
        # mu_vis zero, grad zero -> both directions fall back to normal_diff
        resolved, _ = a.resolve_directions(zero, _unit(zero)[0], torch.tensor([0., 0., 0., 5.]))
        self.assertEqual(resolved[1][0], 'normal_diff')
        self.assertEqual(resolved[2][0], 'normal_diff')
        # all zero -> degenerate, candidate vector is zero (recorded deactivation)
        resolved2, _ = a.resolve_directions(zero, None, zero)
        self.assertIsNone(resolved2[1])
        cands = a.build_candidates(zero, resolved2)
        self.assertTrue(all(c['vector_norm'] == 0.0 for c in cands))


class ClassBalancedLossTests(unittest.TestCase):
    def test_class_balanced_ce_matches_independent_logsumexp(self):
        a = attacker_with([0, 0, 1, 2], [0, 1, 2])
        logits = torch.tensor([[0., 0., 0.], [10., 0., 0.], [0., 0., 0.], [0., 0., 0.]])
        got = a._class_balanced_ce(logits).item()
        rows = [[0., 0., 0.], [10., 0., 0.], [0., 0., 0.], [0., 0., 0.]]
        labels = [0, 0, 1, 2]
        ce = [logsumexp(r)-r[y] for r, y in zip(rows, labels)]
        class0 = (ce[0]+ce[1])/2
        expected = (class0+ce[2]+ce[3])/3
        self.assertAlmostEqual(got, expected, places=5)
        plain = sum(ce)/4
        self.assertNotAlmostEqual(expected, plain, places=4)  # class balancing differs from plain mean


class SelectionTests(unittest.TestCase):
    def test_tie_break_prefers_release_gamma_direction(self):
        scored = [
            {'d': 2, 'gamma': 4.0, 'effective_action': 'delay8', 'L_adv': 5.0},
            {'d': 1, 'gamma': 0.5, 'effective_action': 'immediate', 'L_adv': 5.0},
            {'d': 1, 'gamma': 0.0, 'effective_action': 'expire', 'L_adv': 9.0},
        ]
        # Highest L_adv wins outright.
        self.assertEqual(CausalJoint32Attacker.select(scored), 2)
        tie = scored[:2]
        # Tie on L_adv -> earlier release (immediate) wins.
        self.assertEqual(CausalJoint32Attacker.select(tie), 1)

    def test_nonfinite_scores_rank_last(self):
        scored = [{'d': 1, 'gamma': 0.0, 'effective_action': 'immediate', 'L_adv': float('inf')},
                  {'d': 1, 'gamma': 0.0, 'effective_action': 'expire', 'L_adv': 2.0}]
        self.assertEqual(CausalJoint32Attacker.select(scored), 1)


class ProxyRolloutTests(unittest.TestCase):
    def _state(self):
        return AttackBaselineState(torch.tensor([10.], dtype=torch.float32), 'avg', 't',
                                   capacity=1, outstanding_limit=10, lifetime=1000, wait=8)

    def test_proxy_average_matches_hand_scalar(self):
        s = self._state()
        a, x, c = s.issue(0), s.issue(1), s.issue(2)
        s.expire(1)
        s.receive(DeliveredReply(a.task_id, 0, 0, torch.tensor([8.])), 0, 1)  # u_A = 10-8 = 2
        clone = s.clone_for_proxy()
        # candidate X uploads u=4 immediately (tick1); colluding C uploads u=8 at tick3.
        model = clone.proxy_rollout([(3, c.task_id, torch.tensor([8.])),
                                     (1, x.task_id, torch.tensor([4.]))], 32, False)
        # tick1: A(lag0,1/1)->8; X(lag1,1/2)->6. tick3: C(lag2,1/3)->6-8/3.
        self.assertAlmostEqual(model.item(), 10-2-2-8/3, places=5)

    def test_timing_changes_release_tick_and_processing_path(self):
        u_A, u_X, u_C = torch.tensor([2.]), torch.tensor([4.]), torch.tensor([8.])
        releases = {}
        results = {}
        for release, label in ((1, 'immediate'), (9, 'delay8')):
            s = self._state()
            a, x, c = s.issue(0), s.issue(1), s.issue(2)
            s.expire(1)
            s.receive(DeliveredReply(a.task_id, 0, 0, torch.tensor([8.])), 0, 1)
            clone = s.clone_for_proxy()
            results[label] = clone.proxy_rollout(
                [(3, c.task_id, u_C), (release, x.task_id, u_X)], 32, False).item()
            releases[label] = release
        self.assertNotEqual(releases['immediate'], releases['delay8'])
        # immediate: X at lag1 (1/2), C at lag2 (1/3). delay8: C at lag1 (1/2), X at lag2 (1/3).
        self.assertAlmostEqual(results['immediate'], 10-2-0.5*4-8/3, places=5)
        self.assertAlmostEqual(results['delay8'], 10-2-0.5*8-4/3, places=5)
        self.assertNotAlmostEqual(results['immediate'], results['delay8'], places=4)

    def test_proxy_does_not_mutate_real_state(self):
        s = self._state()
        a, x, c = s.issue(0), s.issue(1), s.issue(2)
        s.expire(1)
        s.receive(DeliveredReply(a.task_id, 0, 0, torch.tensor([8.])), 0, 1)
        before_model = s.model.clone()
        before_states = {t: s.tasks[t]['state'] for t in s.tasks}
        before_version, before_fifo = s.version, list(s.fifo)
        clone = s.clone_for_proxy()
        clone.proxy_rollout([(3, c.task_id, torch.tensor([8.])),
                             (1, x.task_id, torch.tensor([4.]))], 32, False)
        self.assertTrue(torch.equal(s.model, before_model))
        self.assertEqual({t: s.tasks[t]['state'] for t in s.tasks}, before_states)
        self.assertEqual((s.version, list(s.fifo)), (before_version, before_fifo))


class SymbolTests(unittest.TestCase):
    def test_uploaded_reconstructs_crafted_u(self):
        source = torch.tensor([5., -3.])
        u = torch.tensor([2., 1.])            # crafted raw update
        uploaded = source - u                  # what the malicious client sends
        s = AttackBaselineState(source.clone(), 'avg', 't', capacity=1, outstanding_limit=2)
        t = s.issue(0)
        s.expire(1)
        s.receive(DeliveredReply(t.task_id, 0, 0, uploaded), 0, 1)
        # Server reconstructs u_raw = theta_source - theta_uploaded.
        self.assertTrue(torch.allclose(s.updates[t.task_id], u, atol=1e-6))
        self.assertAlmostEqual(s.tasks[t.task_id]['raw_norm'], math.sqrt(5), places=6)


if __name__ == '__main__':
    unittest.main()
