"""Synthetic production continuation checks; no real input or optimization."""
import tempfile
import unittest
import types
import copy
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch
import scripts.resume_direction_a_probe_formal as wrapper
import direction_a.probe_startup as startup
arithmetic=wrapper.original.module('frozen_resume_arithmetic','tests/test_direction_a_probe_formal.py')
old=wrapper.original.module('frozen_resume_lifecycle','tests/test_direction_a_probe_startup.py')


class Resume(unittest.TestCase):
    def fixture(self,b):
        np=arithmetic.np
        labels=np.repeat(np.arange(10),100)
        groups=dict(head=[0,1,2],middle=[3,4,5],tail=[6,7,8,9])
        mapping=dict(train_indices=list(range(10)),train_labels=list(range(10)),validation_indices=list(range(1000)),
                     validation_labels=labels.tolist(),class_groups=groups,label_mapping=list(range(10)),index_namespace='official_train',test_samples=0)
        metrics=wrapper.metrics_from_prediction(labels,np.ones(1000),labels,groups,b)
        rows=[]; joint=[]; files={}; records={}
        for i,rid in enumerate(wrapper.reference_ids()):
            heads=[]
            for r,seed in wrapper.expected_old():
                if r!=rid: continue
                h=dict(seed=seed,name=wrapper.head_name(seed),metrics=metrics,prediction=dict(synthetic=True),fit_save_seconds=1.)
                path=wrapper.OUT/f'synthetic/{rid}/{wrapper.head_name(seed)}.json'
                records[path]=h; heads.append(h)
                joint.append(dict(reference_id=rid,seed=seed,result_path=path.relative_to(wrapper.ROOT).as_posix()))
            row=dict(reference_id=rid,heads=heads)
            if i<2:
                path=(wrapper.OLD/f'predictions/{rid}/original.npz').relative_to(wrapper.ROOT).as_posix()
                files[path]=dict(bytes=1,sha256='synthetic')
            if i==0: row.update(original_prediction=dict(path=path,**files[path]),original_head=metrics,state_before='frozen',state_after='frozen',dataset='CIFAR10')
            rows.append(row)
        return dict(references=rows),dict(files=files,verified_historical_shared_locators=[]),mapping,joint,records

    def test_recovery_missing_corrupt_and_partial_identity_rejected(self):
        b=arithmetic.SyntheticBudget(); saved,index,mapping,joint,records=self.fixture(b)
        pred=arithmetic.np.asarray(mapping['validation_labels']); ce=arithmetic.np.ones(1000)
        with patch.object(wrapper,'read_json',side_effect=lambda path,b:records[Path(path)]),patch.object(wrapper,'load_prediction',return_value=(pred,ce)):
            plans=wrapper.recovery_plan(saved,index,mapping,joint,b)
            self.assertEqual([p['preserved_heads'] for p in plans.values()],[100,60,0,0])
            for rid in wrapper.reference_ids()[:2]: self.assertIn('original_prediction',plans[rid]['row'])
            broken=copy.deepcopy(index); broken['files'].pop(next(iter(broken['files'])))
            with self.assertRaises(RuntimeError): wrapper.recovery_plan(saved,broken,mapping,joint,b)
            broken=copy.deepcopy(saved); broken['references'][1]['heads'][0]['seed']=123
            with self.assertRaises(RuntimeError): wrapper.recovery_plan(broken,index,mapping,joint,b)
        with patch.object(wrapper,'read_json',side_effect=lambda path,b:records[Path(path)]),patch.object(wrapper,'load_prediction',side_effect=RuntimeError('corrupt original archive')):
            with self.assertRaisesRegex(RuntimeError,'corrupt'): wrapper.recovery_plan(saved,index,mapping,joint,b)

    def test_synthetic_experiment_entry_complete_partial_and_both_empty_points(self):
        # Exercise experiment itself through the old KeyError and BOTH C100 original-forward branches.
        torch=arithmetic.torch; np=arithmetic.np
        from direction_a import probe_formal as f
        for target in range(4):
            with self.subTest(target=target),ExitStack() as stack:
                b=types.SimpleNamespace(counts=dict(evidence_bytes=0,fits=0,backwards=0,optimizer_steps=0,encoder_forwards=0,feature_samples=0),progress={},planned_references=[],delivered_references=[],
                    started=wrapper.time.monotonic(),save=lambda:None,enter=lambda name:None,
                    scan=lambda:None,consume=lambda name,amount=1:arithmetic.SyntheticBudget().consume(name,amount) if name=='forwards' else None)
                saved,index,mapping,joint,records=self.fixture(b)
                rid=wrapper.reference_ids()[target]; C=10 if target<2 else 100; ds='CIFAR10' if C==10 else 'CIFAR100'
                labels=np.repeat(np.arange(C,dtype=np.int64),1000//C); groups=mapping['class_groups'] if C==10 else dict(head=list(range(30)),middle=list(range(30,60)),tail=list(range(60,100)))
                y=torch.arange(C,dtype=torch.int64); weight=torch.zeros(C,128); bias=torch.zeros(C)
                packet=dict(state_dict={'linear.weight':weight,'linear.bias':bias})
                a=dict(reference=dict(reference_id=rid,dataset=ds),binding=dict(class_groups=groups,label_mapping=list(range(C))))
                acceptance=dict(references=[a]); measurements=dict(references=[dict(reference_id=rid)])
                prep=dict(cumulative_conservative_elapsed_upper_seconds=74.9171745,cumulative_accountable_write_bytes=11988355,historical_failure=dict(historical_unknowns={}))
                names=['preregistration.json','reference_acceptance.json','measurements.json','run_record.json','decision.json']
                helper=types.SimpleNamespace(G12=wrapper.OUT/'synthetic_g12',UPSTREAM=wrapper.OUT/'synthetic_upstream',
                    committed=lambda *args:None,digest_file=lambda *args:'hash',
                    frozen_checkpoint=lambda *args:(packet,'frozen'),
                    load_train=lambda *args:(torch.zeros(C,128),y,torch.arange(C),C,groups,dict(weight=weight,bias=bias),{}))
                def hread(path,b):
                    name=Path(path).name
                    return {'artifact_hashes.json':dict(files={n:'hash' for n in names}),'reference_acceptance.json':acceptance,
                        'measurements.json':measurements,'decision.json':dict(fail_count=0,blocked=False),'run_record.json':prep}.get(name,{})
                helper.read_json=hread
                oldledger=dict(status='failed_terminal_limit',counts=dict(fits=161,backwards=160461,optimizer_steps=160461,scans=166480,evidence_bytes=8259455),new_stage_elapsed_seconds=562.063)
                prereg=dict(train=dict(samples={ds:C}),estimates=dict(fitting_seconds=2000),actual_command=['synthetic'],protocol_sha256='x',protocol_v6_sha256='x',protocol_v8_sha256='x',protocol_v9_sha256='x')
                def read(path,b):
                    if Path(path) in records: return records[Path(path)]
                    return oldledger if Path(path)==wrapper.OLD/'run_record.json' else prereg
                written={}
                def put(path,value,b): written[Path(path).name]=copy.deepcopy(value)
                def pred(loc,b):
                    sizeC=10 if loc.get('path','').startswith('artifacts/direction_a/phaseP_formal_v1') else C
                    return np.repeat(np.arange(sizeC),1000//sizeC),np.ones(1000)
                overrides=[(wrapper.original,'inherited_helpers',lambda c:helper),(wrapper,'verify_old',lambda b:(index,saved,dict(references=[dict(reference_id=wrapper.reference_ids()[0])]),mapping,joint,[])),
                    (wrapper,'read_history',lambda b:wrapper.combine_history(wrapper.inherited_records())),(wrapper,'read_json',read),
                    (wrapper,'load_prediction',pred),(wrapper.original,'write_json',put),(wrapper,'accepted_references',lambda *a:None),
                    (wrapper,'historical_locator',lambda *a:None),(wrapper,'git',lambda *a:'synthetic_commit'),
                    (wrapper.original,'validation_features',lambda *a:(torch.zeros(1000,128),labels,np.arange(1000),{})),
                    (wrapper.original,'save_prediction',lambda *a:dict(synthetic=True)),
                    (torch.Tensor,'cuda',lambda tensor,*a,**k:tensor),(torch.cuda,'is_available',lambda:True),
                    (torch.cuda,'reset_peak_memory_stats',lambda:None),(torch.cuda,'get_device_name',lambda:'synthetic CPU'),
                    (f,'fit',lambda *a:(_ for _ in ()).throw(RuntimeError('synthetic stop before fitting')))]
                as_tensor=torch.as_tensor
                overrides.append((torch,'as_tensor',lambda value,*a,**k:as_tensor(value,*a,**{n:v for n,v in k.items() if n!='device'})))
                for obj,name,value in overrides: stack.enter_context(patch.object(obj,name,value))
                context=dict(history=dict(ledger_path='synthetic_prep/run_record.json'))
                with self.assertRaises(RuntimeError) as error: wrapper.experiment(context,b)
                if target==0:
                    self.assertEqual(str(error.exception),'resume operation count mismatch')
                    self.assertEqual(len(written['results.json']['references']),1)
                else:
                    self.assertEqual(str(error.exception),'synthetic stop before fitting')
                    self.assertIn(rid,written['resume_manifest.json']['recovery_points'])
                    if target>=2: self.assertEqual(b.progress['new_result_boundary']['kind'],'new_original_prediction_and_metrics')

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

    def test_four_history_missing_is_unknown_and_duplicate_rejected(self):
        rows=wrapper.inherited_records()
        self.assertEqual(wrapper.combine_history(rows)['fact_counts']['scans'],179423)
        self.assertEqual(wrapper.combine_history(rows)['fact_counts']['backwards'],160461)
        with self.assertRaises(RuntimeError): wrapper.combine_history(rows[:2])
        with self.assertRaises(RuntimeError): wrapper.combine_history([rows[0],rows[1],rows[1]])
        rows[2]['counts'].pop('encoder_forwards')
        self.assertEqual(wrapper.combine_history(rows)['fact_counts']['encoder_forwards'],'unknown')

    def test_9000_budget_runtime_and_seal_share_remaining_balance(self):
        self.assertEqual(wrapper.FORMAL_SECONDS,9000)
        self.assertAlmostEqual(wrapper.LIMITS['wall_seconds'],6174.063)
        self.assertEqual(wrapper.LIMITS['evidence_bytes'],116919378)
        self.assertEqual(wrapper.LIMITS['scans'],320577)
        self.assertEqual(wrapper.combine_history(wrapper.inherited_records())['fact_counts']['forwards'],160805)
        with tempfile.TemporaryDirectory(dir=wrapper.OUT) as folder:
            clock=old.Clock(); ctx=old.context(Path(folder)/'attempt',clock)
            ctx.update(limits={**wrapper.LIMITS,'evidence_bytes':8*1024**2},
                       total_wall_seconds=wrapper.LIMITS['wall_seconds']+1.25,
                       total_write_bytes=8*1024**2+1000,cumulative_scan_limit=500000,
                       emergency_closure_bytes=1024**2)
            ctx['formal_history']=wrapper.combine_history(wrapper.inherited_records())
            def namespace(context):
                def work(b):
                    self.assertAlmostEqual(b.limits['wall_seconds'],6174.063)
                    clock.now=b.started+4000
                    b.check()
                    clock.now=b.started+6174.063
                    b.check()
                return dict(LIMITS=ctx['limits'],main=work)
            with patch.object(startup.time,'monotonic',clock.monotonic):
                value=wrapper.run_once(ctx,namespace)
            self.assertEqual(value['status'],'failed_terminal_limit')
            self.assertAlmostEqual(value['formal_history']['seconds'],2825.937)
        ledger=dict(counts=dict(evidence_bytes=1,scans=1),
                    joint_formal_accounting=dict(seconds=6134.464),
                    resources=dict(windows_working_set_peak_bytes=1))
        self.assertFalse(wrapper.seal_limit_exceeded(ledger))
        ledger['joint_formal_accounting']['seconds']=9000
        self.assertTrue(wrapper.seal_limit_exceeded(ledger))
        ledger['joint_formal_accounting']['seconds']=8999.999
        self.assertFalse(wrapper.seal_limit_exceeded(ledger))
        ledger['counts']['evidence_bytes']=wrapper.LIMITS['evidence_bytes']
        self.assertTrue(wrapper.seal_limit_exceeded(ledger))

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

    def test_four_ledgers_once_missing_unknown_and_commit_locator(self):
        rows=wrapper.inherited_records(); joint=wrapper.combine_history(rows)
        self.assertAlmostEqual(joint['seconds'],2825.937)
        self.assertEqual(joint['bytes'],17298350)
        self.assertEqual(joint['fact_counts']['forwards'],160805)
        self.assertEqual(joint['fact_counts']['encoder_forwards'],24)
        self.assertEqual(joint['fact_counts']['feature_samples'],3000)
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

    def test_production_inherits_four_ledgers_and_queue_isolation(self):
        with tempfile.TemporaryDirectory(dir=wrapper.OUT) as folder:
            ctx=old.context(Path(folder)/'attempt')
            ctx['limits']={**wrapper.LIMITS,'evidence_bytes':8*1024**2}
            ctx['formal_history']=wrapper.combine_history(wrapper.inherited_records())
            ctx['old_counts']=ctx['formal_history']['fact_counts']
            ctx['cumulative_scan_limit']=500000
            def namespace(context):
                def work(b):
                    self.assertEqual(b.context['old_counts']['forwards'],160805)
                    self.assertEqual(len(set(wrapper.expected_old()+wrapper.queue())),400)
                    with self.assertRaises(RuntimeError): wrapper.assert_new_head(*wrapper.expected_old()[0])
                    with self.assertRaises(PermissionError): b.write(wrapper.OLD/'synthetic',{})
                    raise RuntimeError('synthetic immutable history exit')
                return dict(LIMITS=ctx['limits'],main=work)
            value=wrapper.run_once(ctx,namespace)
            self.assertNotEqual(value['status'],'completed')
            self.assertAlmostEqual(value['formal_history']['seconds'],2825.937)


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
        for path in [wrapper.OLD,wrapper.OLD/'heads/example.pt',wrapper.OLD/'predictions/example.npz',wrapper.FAILED,wrapper.FAILED/'run_record.json',wrapper.FAILED2,wrapper.FAILED2/'heads/x.pt',wrapper.FAILED3,wrapper.FAILED3/'heads/x.pt',wrapper.FAILED4,wrapper.FAILED4/'heads/x.pt']:
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
