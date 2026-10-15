"""Synthetic production continuation checks; no real input or optimization."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import scripts.resume_direction_a_probe_formal as wrapper
import direction_a.probe_startup as startup
arithmetic=wrapper.original.module('frozen_resume_arithmetic','tests/test_direction_a_probe_formal.py')
old=wrapper.original.module('frozen_resume_lifecycle','tests/test_direction_a_probe_startup.py')


class Resume(unittest.TestCase):
    def test_newline_equivalence_and_historical_raw_relation(self):
        for blob in [b'a\nb\n',b'a\r\nb\r\n',b'a\rb\r']:
            for recorded in [b'a\nb\n',b'a\r\nb\r\n',b'a\rb\r']:
                loc=dict(path='synthetic.py',bytes=len(recorded),sha256=wrapper.sha(recorded))
                relation=wrapper.historical_text_relation(blob,loc)
                self.assertEqual(relation['normalized_sha256'],wrapper.sha(b'a\nb\n'))
                self.assertEqual(relation['historical_raw_sha256'],wrapper.sha(recorded))
                self.assertTrue(relation['historical_raw_newline_forms'])

    def test_substantive_text_and_false_raw_hash_rejected(self):
        recorded=b'a\r\nb\r\n'
        loc=dict(path='synthetic.py',bytes=len(recorded),sha256=wrapper.sha(recorded))
        for changed in [b'a \nb\n',b'a\nc\n',b'\xef\xbb\xbfa\nb\n']:
            with self.assertRaises(RuntimeError): wrapper.historical_text_relation(changed,loc)
        with self.assertRaises(RuntimeError):
            wrapper.historical_text_relation(b'a\nb\n',dict(loc,sha256='0'*64))
        with patch.object(wrapper.subprocess,'check_output',return_value=b'a\nb\n'),patch.object(Path,'read_bytes',return_value=b'a\nc\n'):
            with self.assertRaises(RuntimeError):
                wrapper.historical_locator(dict(loc,path='models/ResNet.py'),arithmetic.SyntheticBudget(),'synthetic',wrapper.OLD)

    def test_production_text_locator_and_binary_strictness(self):
        with tempfile.TemporaryDirectory(dir=wrapper.OUT) as folder:
            p=Path(folder)/'synthetic.py'; p.write_bytes(b'current authorized revision')
            raw=b'history\n'; recorded=b'history\r\n'
            loc=dict(path=p.relative_to(wrapper.ROOT).as_posix(),bytes=len(recorded),sha256=wrapper.sha(recorded))
            with patch.object(wrapper.subprocess,'check_output',return_value=raw):
                value=wrapper.historical_locator(loc,arithmetic.SyntheticBudget(),'synthetic',wrapper.OLD)
                self.assertEqual(value['text_relation']['historical_raw_newline_forms'],['CRLF'])
                with self.assertRaises(RuntimeError):
                    wrapper.historical_locator(dict(loc,path=loc['path']+'.pt'),arithmetic.SyntheticBudget(),'synthetic',wrapper.OLD)

    def test_three_history_missing_is_unknown_and_duplicate_rejected(self):
        rows=wrapper.inherited_records()
        self.assertEqual(wrapper.combine_history(rows)['fact_counts']['scans'],170237)
        self.assertEqual(wrapper.combine_history(rows)['fact_counts']['backwards'],160461)
        with self.assertRaises(RuntimeError): wrapper.combine_history(rows[:2])
        with self.assertRaises(RuntimeError): wrapper.combine_history([rows[0],rows[1],rows[1]])
        rows[2]['counts'].pop('encoder_forwards')
        self.assertEqual(wrapper.combine_history(rows)['fact_counts']['encoder_forwards'],'unknown')

    def test_large_emergency_archive_and_cross_process_peaks(self):
        with tempfile.TemporaryDirectory(dir=wrapper.OUT) as folder:
            ctx=old.context(Path(folder)/'attempt')
            ctx.update(emergency_closure_bytes=1024**2,total_write_bytes=8*1024**2,
                       cumulative_scan_limit=500000)
            ctx['limits']={**wrapper.LIMITS,'evidence_bytes':8*1024**2}
            def namespace(context):
                def work(b):
                    self.assertGreaterEqual(b.counts['evidence_bytes'],1024**2)
                    for i in range(1400): b.write(ctx['output']/f'partial-{i:04d}',b'nonzero',raw=True)
                    b.resources['windows_working_set_peak_bytes']=8*1024**3
                    raise RuntimeError('synthetic large partial archive')
                return dict(LIMITS=ctx['limits'],main=work)
            value=wrapper.run_once(ctx,namespace)
            self.assertEqual(value['status'],'failed_no_retry')
            self.assertEqual(value['resources']['windows_working_set_peak_bytes'],8*1024**3)
            global LARGE_ARCHIVE_BYTES
            LARGE_ARCHIVE_BYTES=(ctx['output']/'artifact_hashes.json').stat().st_size
            self.assertGreater(LARGE_ARCHIVE_BYTES,128*1024)

    def test_three_ledgers_once_missing_unknown_and_commit_locator(self):
        rows=wrapper.inherited_records(); joint=wrapper.combine_history(rows)
        self.assertAlmostEqual(joint['seconds'],1444.344)
        self.assertEqual(joint['bytes'],11478365)
        self.assertEqual(joint['fact_counts']['forwards'],160799)
        self.assertEqual(joint['fact_counts']['encoder_forwards'],16)
        self.assertEqual(joint['fact_counts']['feature_samples'],2000)
        self.assertTrue(joint['missing_fields_retained'])
        self.assertNotIn('forwards',rows[1]['counts'])
        with self.assertRaises(RuntimeError): wrapper.combine_history([rows[0],rows[0]])
        rows[0]['counts'].pop('forwards')
        self.assertEqual(wrapper.combine_history(rows)['fact_counts']['forwards'],'unknown')
        with tempfile.TemporaryDirectory(dir=wrapper.OUT) as folder:
            path=Path(folder)/'shared'; path.write_bytes(b'new')
            locator=dict(path=path.relative_to(wrapper.ROOT).as_posix(),bytes=3,sha256=wrapper.sha(b'old'))
            with patch.object(wrapper.subprocess,'check_output',return_value=b'old') as mock:
                value=wrapper.historical_locator(locator,arithmetic.SyntheticBudget(),'synthetic_commit',wrapper.OLD)
                self.assertEqual(value['commit'],'synthetic_commit')
                self.assertIn('synthetic_commit:',mock.call_args.args[0][2])
                locator['sha256']=wrapper.sha(b'bad')
                with self.assertRaises(RuntimeError): wrapper.historical_locator(locator,arithmetic.SyntheticBudget(),'synthetic_commit',wrapper.OLD)

    def test_production_inherits_three_ledgers_and_queue_isolation(self):
        with tempfile.TemporaryDirectory(dir=wrapper.OUT) as folder:
            ctx=old.context(Path(folder)/'attempt')
            ctx['limits']={**wrapper.LIMITS,'evidence_bytes':8*1024**2}
            ctx['formal_history']=wrapper.combine_history(wrapper.inherited_records())
            ctx['old_counts']=ctx['formal_history']['fact_counts']
            ctx['cumulative_scan_limit']=500000
            def namespace(context):
                def work(b):
                    self.assertEqual(b.context['old_counts']['forwards'],160799)
                    self.assertEqual(len(set(wrapper.expected_old()+wrapper.queue())),400)
                    with self.assertRaises(RuntimeError): wrapper.assert_new_head(*wrapper.expected_old()[0])
                    with self.assertRaises(PermissionError): b.write(wrapper.OLD/'synthetic',{})
                    raise RuntimeError('synthetic immutable history exit')
                return dict(LIMITS=ctx['limits'],main=work)
            value=wrapper.run_once(ctx,namespace)
            self.assertNotEqual(value['status'],'completed')
            self.assertAlmostEqual(value['formal_history']['seconds'],1444.344)


    def test_exact_queue_and_old_set(self):
        q=wrapper.queue(); prior=wrapper.expected_old()
        self.assertEqual(len(q),240); self.assertEqual(len(prior),160)
        self.assertEqual(len(set(q+prior)),400)
        self.assertEqual(q[0],(wrapper.reference_ids()[1],2026101560))
        self.assertEqual(q[39][1],2026101599)
        for rid,seed in prior:
            with self.assertRaises(RuntimeError): wrapper.assert_new_head(rid,seed)
        for rid,seed in q: wrapper.assert_new_head(rid,seed)

    def test_old_write_denied_without_access(self):
        for path in [wrapper.OLD,wrapper.OLD/'heads/example.pt',wrapper.OLD/'predictions/example.npz',wrapper.FAILED,wrapper.FAILED/'run_record.json',wrapper.FAILED2,wrapper.FAILED2/'heads/x.pt']:
            with self.assertRaises(PermissionError): wrapper.assert_new_path(path)
        wrapper.assert_new_path(wrapper.OUT/'heads/new.pt')

    def test_hash_missing_and_bad_identity_rejected(self):
        b=arithmetic.SyntheticBudget()
        with self.assertRaises(FileNotFoundError): wrapper.validate_locator(dict(path='absent-synthetic-file',bytes=1,sha256='0'*64),b)
        with self.assertRaises(RuntimeError): wrapper.validate_head({},wrapper.reference_ids()[0],None,10,{})
        with tempfile.TemporaryDirectory(dir=wrapper.OUT) as folder:
            p=Path(folder)/'x'; p.write_bytes(b'synthetic')
            with self.assertRaises(RuntimeError): wrapper.validate_locator(dict(path=p.relative_to(wrapper.ROOT).as_posix(),bytes=9,sha256='0'*64),b)

    def test_inherited_cost_and_distinct_resource_limits(self):
        with tempfile.TemporaryDirectory(dir=wrapper.OUT) as folder:
            ctx=old.context(Path(folder)/'attempt')
            ctx['limits']={**ctx['limits'],**wrapper.LIMITS,'scans':100}
            ctx['old_counts']=dict(fits=161,backwards=160461,optimizer_steps=160461,scans=166480)
            ctx['cumulative_scan_limit']=500000
            def namespace(context):
                def work(b):
                    self.assertGreaterEqual(b.counts['evidence_bytes'],ctx['preparation_initial_write_bytes'])
                    self.assertGreaterEqual(b.counts['scans'],7)
                    self.assertEqual(b.limits['windows_peak_working_set_bytes'],16*1024**3)
                    self.assertEqual(b.limits['gpu_allocated_bytes'],6*1024**3)
                    b.counts['fits']=240
                    with self.assertRaises(Exception): b.consume('fits')
                    raise RuntimeError('synthetic cumulative cap')
                return dict(LIMITS=ctx['limits'],main=work)
            value=wrapper.run_once(ctx,namespace)
            self.assertNotEqual(value['status'],'completed')
            self.assertGreater(value['cumulative_accountable_write_bytes'],value['counts']['evidence_bytes'])


class Production(old.StartupTests):
    def setUp(self):
        self.directory=tempfile.TemporaryDirectory(prefix='resume-synthetic-',dir=wrapper.OUT)
        self.addCleanup(self.directory.cleanup)
        self.output=Path(self.directory.name)/'attempt'


def suite():
    old.wrapper=wrapper
    # Reuse all frozen arithmetic except old-directory writing tests.
    names=[n for n in unittest.defaultTestLoader.getTestCaseNames(arithmetic.Arithmetic) if n!='test_formal_large_emergency_index_is_precharged_and_retained']
    production=['test_production_before_constructor','test_production_after_constructor_nonzero_work',
                'test_production_archive_error_nonzero_work','test_production_normal_preserves_peaks',
                'test_production_terminal_time_limit','test_production_terminal_write_limit','test_production_terminal_scan_limit',
                'test_real_parent_initialization_and_exact_write_inheritance','test_existing_marker_and_ledger_are_immutable']
    return unittest.TestSuite([unittest.defaultTestLoader.loadTestsFromTestCase(Resume),
                              *[arithmetic.Arithmetic(n) for n in names],*[Production(n) for n in production]])
