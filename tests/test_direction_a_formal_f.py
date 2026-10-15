"""CPU-only synthetic independent boundary and integrity oracles."""
import itertools
import copy
import json
import unittest
from unittest.mock import patch
from fractions import Fraction as F

from direction_a.formal_f import N, IDS, SCENARIOS, DELTA, probability, outcome, charge, classify, parse_speed_assignments
from direction_a.formal_f_policy import Consumer, invite


class FormalFChecks(unittest.TestCase):
    def test_production_speed_parser(self):
        original = {ds: {'assignments': {s: {cid: ('1' if c < 10 else '4')
                    for c, cid in enumerate(IDS)} for s in SCENARIOS}}
                    for ds in ('CIFAR10', 'CIFAR100')}
        raw = json.dumps(original)
        view = parse_speed_assignments(raw)
        self.assertEqual(json.loads(raw), original)
        for ds in original:
            for s in SCENARIOS:
                for c, cid in enumerate(IDS):
                    speed = view[ds]['assignments'][s][cid]
                    self.assertIs(type(speed), int)
                    expected = 1 if c < 10 else 4
                    self.assertEqual(probability('1', speed), probability('1', expected))
                    self.assertEqual(outcome('1', speed, (0, N-1, N-1)),
                                     outcome('1', expected, (0, N-1, N-1)))
        for bad in (True, False, 1, 4, 1.0, None, '01', '1.0', ' 1', '4 ', '2'):
            changed = copy.deepcopy(original)
            changed['CIFAR10']['assignments']['random'][IDS[0]] = bad
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                parse_speed_assignments(json.dumps(changed))
        for field in ('endpoint', 'scenario', 'task', 'multiset'):
            changed = copy.deepcopy(original)
            if field == 'endpoint': del changed['CIFAR10']['assignments']['random'][IDS[0]]
            elif field == 'scenario': del changed['CIFAR10']['assignments']['tail_fast']
            elif field == 'task': del changed['CIFAR100']
            else: changed['CIFAR10']['assignments']['random'][IDS[0]] = '4'
            with self.subTest(field=field), self.assertRaises(ValueError):
                parse_speed_assignments(json.dumps(changed))
        duplicate = raw.replace('"client_000": "1"', '"client_000": "1", "client_000": "4"', 1)
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            parse_speed_assignments(duplicate)

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
