"""CPU-only synthetic independent boundary and integrity oracles."""
import itertools
import unittest
from unittest.mock import patch
from fractions import Fraction as F

from direction_a.formal_f import N, IDS, DELTA, probability, outcome, charge, classify
from direction_a.formal_f_policy import Consumer, invite


class FormalFChecks(unittest.TestCase):
    def test_probabilities_and_grid_boundaries(self):
        self.assertEqual(sum(0 in c for c in itertools.combinations(range(5), 2)), 4)
        p = probability('1', 4)
        self.assertEqual((p['A'], p['H'], p['K']),
                         (8106479329266893, 8556839292003942, 3302639726738364))
        self.assertEqual(F(p['continuous_r']), F(627, 2000))
        for grid in (4, 9, 20):
            count = sum(outcome('1', 4, (o, d, j), grid)[0] == 'returned'
                        for o, d, j in itertools.product(range(grid), repeat=3))
            self.assertEqual(F(count, grid**3), F(probability('1', 4, grid)['r']))
        K = p['K']
        self.assertEqual(outcome('1', 4, (0, N-1, K-1))[0], 'returned')
        self.assertEqual(outcome('1', 4, (0, N-1, K))[0], 'timeout')
        self.assertEqual(outcome('1', 4, (F(9,10), F(1,2), 0), rational=True)[0], 'offline')
        self.assertEqual(outcome('1', 4, (0, F(1,20), F(11,30)), rational=True), ('returned', DELTA))

    def test_observable_consumer(self):
        self.assertEqual(invite(IDS[:8], IDS), IDS[:8])
        with self.assertRaises(ValueError):
            invite([IDS[0]]*8, IDS)
        c = Consumer({'reference':'r', 'attempt':0}, IDS, {IDS[0]:('t','h')})
        m = dict(reference='r', attempt=0, client=IDS[0], token='t', payload='h')
        self.assertEqual(c.accept(dict(m, reference='wrong'), True), 'identity')
        self.assertEqual(c.accept(dict(m, client='unknown'), True), 'unregistered')
        self.assertEqual(c.accept(dict(m, client=IDS[1]), True), 'undispatched')
        self.assertEqual(c.accept(dict(m, token='bad'), True), 'tampered')
        self.assertEqual(c.accept(dict(m, r='0.5'), True), 'schema')
        self.assertEqual(c.accept(m, False), 'late')
        self.assertEqual(c.accept(m, True), 'accepted')
        self.assertEqual(c.accept(m, True), 'duplicate_token')

    def test_costs_and_exception_sealing(self):
        row = dict(return_bytes=11,message_bytes=7,sample_count=13,b_seconds='3/2')
        failed, good = charge(row, 17, False), charge(row, 17, True)
        self.assertEqual(failed['effective_upload'], 0)
        self.assertEqual(good['effective_upload'], 18)
        self.assertEqual(failed['W01_steps'], 5)
        self.assertEqual(failed['W02_positions'], 13)
        self.assertEqual(failed['gradient_preparation'], 7)
        items = {'a':{'terminal':True}, 'b':{'started':True}, 'c':{}}
        try:
            raise RuntimeError('synthetic failure after one complete and one partial')
        except RuntimeError:
            inventory = classify(items, ('terminal',))
        self.assertEqual(inventory,dict(complete=['a'],partial=['b'],not_started=['c']))

    def test_resource_gate_prevents_action(self):
        from scripts.run_direction_a_formal_f import Ledger, LIMITS
        prior=dict(seconds=0,writes=0,metadata=0,scans=0,attempts=799,
                   simulated_bytes=0,windows=0,cpu_proxy=0,actions=[],phases={})
        with patch('scripts.run_direction_a_formal_f.windows_peak',return_value=1):
            ledger=Ledger(prior)
            ledger.guard('last permitted',attempts=1)
            self.assertEqual(ledger.d['attempts'],799)
            with self.assertRaisesRegex(RuntimeError,'attempts'):
                ledger.guard('over limit',attempts=2)
            with self.assertRaisesRegex(RuntimeError,'writes'):
                ledger.guard('no failure reserve',writes=LIMITS['writes'])
            with self.assertRaisesRegex(RuntimeError,'seconds'):
                ledger.guard('time envelope',seconds=LIMITS['seconds'])
