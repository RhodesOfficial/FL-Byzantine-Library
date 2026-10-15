"""Synthetic tests: no torch, CUDA, real samples, or network training."""
import io
import unittest
from direction_a.cost_m import Gate, Ledger, exact_b, normalized, record_state, serialize_once


class CostMTests(unittest.TestCase):
    def test_pure_prepare_timing_boundary(self):
        events = []
        ticks = iter((100, 125))
        ns, size = serialize_once(b'abc', lambda v, f: (events.append('save'), f.write(v)),
                                   clock=lambda: next(ticks), synchronize=lambda: events.append('sync'))
        self.assertEqual((ns, size, events), (25, 3, ['sync', 'save', 'sync']))

    def test_cumulative_limits_and_reserves(self):
        ledger = Ledger()
        ledger.phases['input'] = 29
        with self.assertRaises(Gate): ledger.guard('input', seconds=2)
        ledger.add(steps=400)
        with self.assertRaises(Gate): ledger.guard('W01', steps=1)
        ledger.copy('reference_downlink', 512*1024**2)
        with self.assertRaises(Gate): ledger.guard('storage', logical=1)
        ledger.counts['writes'] = 15*1024**2
        with self.assertRaises(Gate): ledger.guard('storage', writes=1)

    def test_exception_charges_elapsed_and_retains_partial(self):
        ticks = iter((2., 5.))
        ledger = Ledger(clock=lambda: next(ticks))
        row = {'task': 'synthetic', 'W01_started': True, 'steps': 2}
        with self.assertRaises(ValueError):
            ledger.timed('W01', lambda: (_ for _ in ()).throw(ValueError('fixture')))
        self.assertEqual(ledger.phases['W01'], 3.)
        self.assertEqual(record_state(row), 'partial')
        self.assertEqual(record_state({'task': 'synthetic'}), 'not_started')
        self.assertEqual(row['steps'], 2)

    def test_exact_components_and_complete_fields(self):
        row = dict(W01_ns=10, message_prepare_ns=20, return_bytes=2, message_bytes=3,
                   steps=5, preserved=True, resolution_seconds='1e-9',
                   old_W02_decimal_seconds=dict(encode='0.1', main_head='0.2', statistics='0.03',
                                                message_save_read='999'))
        self.assertEqual(str(exact_b(row)), '33000003/100000000')
        self.assertEqual(record_state(row), 'complete')
        del row['return_bytes']
        self.assertEqual(record_state(row), 'partial')
        self.assertEqual(normalized(b'a\r\nb\rc\n'), b'a\nb\nc\n')


if __name__ == '__main__':
    unittest.main()
