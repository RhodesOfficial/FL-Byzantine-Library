"""One v9 continuation. v5 fitting/statistical arithmetic is imported unchanged.

--check (synthetic only), commit sources/registration, --run once, --seal.
The old formal package is read-only; inherited complete heads never enter fit.
"""
import time
ENTRY_STARTED = time.monotonic()
import os
os.environ['CUBLAS_WORKSPACE_CONFIG'] = ':4096:8'
import gc
import io
import json
import subprocess
import sys
import traceback
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.dont_write_bytecode = True
import scripts.run_direction_a_probe_formal as original
from direction_a.probe_startup import RecoveryBudget, execute_attempt
from direction_a.backbone_preparation import windows_memory, tensor_state_sha

OUT = ROOT/'artifacts/direction_a/phaseP_formal_resume_v4'
OLD = ROOT/'artifacts/direction_a/phaseP_formal_v1'
BASE = '56b3ac4a6466b9086fd28152002804c4bde84c7b'
OLD_COMMIT = 'ea6a10001998a6062b6365f5e5f3f0df862bca7e'
FAILED = ROOT/'artifacts/direction_a/phaseP_formal_resume_v1'
FAILED2 = ROOT/'artifacts/direction_a/phaseP_formal_resume_v2'
FAILED3 = ROOT/'artifacts/direction_a/phaseP_formal_resume_v3'
FORMAL_SECONDS = 7200
INHERITED_SECONDS = 2138.421
INHERITED_BYTES = 13834446
INHERITED_SCANS = 174822
IMPLEMENTATION_UPPER_SECONDS = 600
RUN_ID = 'FedPCC-P-formal-resume-v4'
encode, sha, git = original.encode, original.sha, original.git
SOURCES = ['scripts/resume_direction_a_probe_formal.py', 'tests/test_direction_a_probe_formal_resume.py', *original.SOURCES]
LIMITS = {**original.LIMITS, 'wall_seconds':FORMAL_SECONDS-INHERITED_SECONDS, 'evidence_bytes':134217728-INHERITED_BYTES,
          'scans':500000-INHERITED_SCANS, 'fits':240, 'backwards':240000, 'optimizer_steps':240000,
          'forwards':240864, 'encoder_forwards':24, 'feature_samples':3000,
          'windows_peak_working_set_bytes':16*1024**3, 'implementation_revisions':1}


def reference_ids():
    return [f'A-backbone-{ds}-s{s}-r{r:04d}-v1' for ds,s in
            [('CIFAR10',2026101321),('CIFAR100',2026101322)] for r in (40,80)]


def queue():
    refs=reference_ids()
    return [(refs[1],s) for s in range(2026101560,2026101600)]+[
        (r,s) for r in refs[2:] for s in [None,*range(2026101501,2026101600)]]


def expected_old():
    refs=reference_ids()
    return [(refs[0],s) for s in [None,*range(2026101501,2026101600)]]+[
        (refs[1],s) for s in [None,*range(2026101501,2026101560)]]


def head_name(seed): return 'real' if seed is None else f'permuted_s{seed}'


def assert_new_head(rid,seed):
    if (rid,seed) not in queue(): raise RuntimeError('complete old head cannot be retrained')


def assert_new_path(path):
    p=Path(path).resolve()
    if any(p==old.resolve() or old.resolve() in p.parents for old in (OLD,FAILED,FAILED2,FAILED3)):
        raise PermissionError('old formal package is immutable')
    local=ROOT/'artifacts_local'/OUT.relative_to(ROOT)
    if not (OUT.resolve() in p.parents or local.resolve() in p.parents):
        raise PermissionError('resume writes must remain in new package')


class ResumeBudget(RecoveryBudget):
    def write(self,path,value,raw=False):
        assert_new_path(path)
        return super().write(path,value,raw)

    def snapshot(self,now=None):
        value=super().snapshot(now)
        if self.context.get('formal_history'): value['formal_history']=self.context['formal_history']
        return value

    def consume(self,field,amount=1,run_id=None):
        super().consume(field,amount,run_id)
        inherited=self.context.get('old_counts',{})
        bounds=dict(fits=401,backwards=400461,optimizer_steps=400461,forwards=401666,
                    encoder_forwards=40,feature_samples=5000,scans=500000)
        if field in bounds and inherited.get(field,0)+self.counts[field]>bounds[field]:
            self.stop('joint_'+field,inherited.get(field,0)+self.counts[field])


def run_once(context,namespace_factory=None):
    namespace={}
    def factory():
        namespace.update(namespace_factory(context) if namespace_factory else
                         dict(LIMITS=LIMITS,main=lambda b:experiment(context,b)))
        context['limits']=namespace['LIMITS']
        b=ResumeBudget(context)
        for name,value in context.get('precheck_resource_peaks',{}).items():
            b.resources[name]=max(value,b.resources[name])
        if context.get('synthetic_head_forwards'): b.consume('forwards',context['synthetic_head_forwards'])
        return b
    def archive(b):
        if namespace.get('archive_callback'): namespace['archive_callback'](b)
    return execute_attempt(context,factory,lambda b:namespace['main'](b),archive)


def registration(fingerprints):
    p=original.registration(fingerprints)
    p.update(run_id=RUN_ID,baseline_commit=BASE,limits=LIMITS,
             protocol_v7_path='docs/DIRECTION_A_P_ADJUDICATION_v7.md',
             protocol_v7_sha256=sha((ROOT/'docs/DIRECTION_A_P_ADJUDICATION_v7.md').read_bytes()),
             protocol_v9_path='docs/DIRECTION_A_P_ADJUDICATION_v9.md',
             protocol_v9_sha256=sha((ROOT/'docs/DIRECTION_A_P_ADJUDICATION_v9.md').read_bytes()),
             formal_total_seconds=FORMAL_SECONDS,
             protocol_v8_path='docs/DIRECTION_A_P_ADJUDICATION_v8.md',
             protocol_v8_sha256=sha((ROOT/'docs/DIRECTION_A_P_ADJUDICATION_v8.md').read_bytes()),
             protocol_v6_path='docs/DIRECTION_A_P_ADJUDICATION_v6.md',
             protocol_v6_sha256=sha((ROOT/'docs/DIRECTION_A_P_ADJUDICATION_v6.md').read_bytes()),
             old_source_commit='a12905c9ffdfe65270feb83e587bffa4b90f612a',
             actual_command=[r'E:\anaconda3\python.exe','-B','scripts/resume_direction_a_probe_formal.py','--run'],
             resume=dict(old_directory=OLD.relative_to(ROOT).as_posix(),old_input_commit=OLD_COMMIT,
                         immutable_old_heads=160,new_heads=240,queue=[dict(reference_id=r,seed=s) for r,s in queue()],
                         head_161='seed 2026101560 starts at zero; no step-462/Adam checkpoint exists',
                         repeated_validation=dict(CIFAR10_r80=dict(samples=1000,encoder=8)),
                         inherited_floor=dict(seconds=INHERITED_SECONDS,bytes=INHERITED_BYTES,scans=INHERITED_SCANS),
                         implementation_program_upper_seconds=IMPLEMENTATION_UPPER_SECONDS,verification_program_reserve_seconds=20,
                         implementation_accounting_basis='600 second conservative implementation bound; historical reserves retained independently; 20 seconds delivery verification precharged',
                         remaining_fit_estimate='max(0, original 2090.6519772480947 seconds minus sum of 160 stored fit_save_seconds), times frozen 1.8 safety factor',
                         no_automatic_retry=True))
    return p


def check():
    import torch
    if OUT.exists(): raise FileExistsError('one resume implementation/check only; directory already exists')
    OUT.mkdir(parents=True)
    counts=dict(write_bytes=0,scans=0); forbidden=[]; peak=0
    read,write=Path.read_bytes,Path.write_bytes
    def tracked_read(path):
        nonlocal peak
        p=path.resolve().as_posix()
        if any(x in p for x in ['/RAW_DATA/','/checkpoints/','/phaseG1_2_', '/phase0_2_v1/tasks/', '/phaseP_formal_v1/', '/phaseP_formal_resume_v1/', '/phaseP_formal_resume_v2/', '/phaseP_formal_resume_v3/']):
            forbidden.append(p); raise AssertionError('synthetic real input forbidden')
        raw=read(path); counts['scans']+=1; peak=max(peak,len(raw)); return raw
    def tracked_write(path,raw):
        nonlocal peak
        assert_new_path(path)
        counts['write_bytes']+=len(raw); peak=max(peak,len(raw))
        if counts['write_bytes']>8*1024**2: raise RuntimeError('synthetic write limit')
        return write(path,raw)
    def deny(name):
        def blocked(*a,**k): forbidden.append(name); raise AssertionError(name+' forbidden')
        return blocked
    class Results(unittest.TestResult):
        def __init__(self): super().__init__(); self.cases=[]
        def addSuccess(self,t): super().addSuccess(t); self.cases.append(dict(case=t.id(),status='PASS'))
        def addError(self,t,e): super().addError(t,e); self.cases.append(dict(case=t.id(),status='FAIL',error=self._exc_info_to_string(e,t)))
        def addFailure(self,t,e): super().addFailure(t,e); self.cases.append(dict(case=t.id(),status='FAIL',error=self._exc_info_to_string(e,t)))
    result=Results(); fingerprints={}; syntax=[]
    with patch.object(Path,'read_bytes',tracked_read),patch.object(Path,'write_bytes',tracked_write):
        for name in SOURCES:
            raw=(ROOT/name).read_bytes(); fingerprints[name]=sha(raw)
            try: compile(raw,name,'exec'); syntax.append(dict(path=name,status='PASS',sha256=sha(raw)))
            except SyntaxError: syntax.append(dict(path=name,status='FAIL',error=traceback.format_exc()))
        with patch.object(torch,'load',deny('torch.load')),patch.object(torch.cuda,'init',deny('CUDA init')),patch.object(torch.cuda,'_lazy_init',deny('CUDA lazy init')),patch.object(torch.Tensor,'cuda',deny('tensor CUDA')),patch.object(torch.Tensor,'backward',deny('backward')),patch.object(torch.optim.Adam,'step',deny('Adam')):
            tests=original.module('resume_checks','tests/test_direction_a_probe_formal_resume.py')
            if all(x['status']=='PASS' for x in syntax): tests.suite().run(result)
        passed=result.wasSuccessful() and result.testsRun>0 and not forbidden and not torch.cuda.is_initialized() and all(x['status']=='PASS' for x in syntax)
        for name,value in [('syntax_check.json',dict(status='PASS' if all(x['status']=='PASS' for x in syntax) else 'FAIL',invocations=1,files=syntax)),
                           ('selfchecks.json',dict(status='PASS' if passed else 'FAIL',invocations=1,tests_run=result.testsRun,cases=result.cases,large_archive_actual_bytes=getattr(tests,'LARGE_ARCHIVE_BYTES',None),
                            isolation=dict(real_input_reads=0,CUDA_initialized=torch.cuda.is_initialized(),backwards=0,optimizer_steps=0,forbidden_attempts=forbidden))),
                           ('preregistration.json',registration(fingerprints))]:
            (OUT/name).write_bytes(encode(value))
        source_bytes=sum((ROOT/n).stat().st_size for n in SOURCES[:2])
        cost=dict(status='PASS' if passed else 'FAIL',fingerprints=fingerprints,program_seconds=time.monotonic()-ENTRY_STARTED+.5,
                  implementation_revisions=1,CPU_suites=1,syntax_checks=1,
                  source_write_events=[dict(path=n,bytes=(ROOT/n).stat().st_size,sha256=fingerprints[n],revision=1) for n in SOURCES[:2]],
                  implementation_write_reserve_bytes=524288,
                  counts=dict(write_bytes=counts['write_bytes']+source_bytes+524288,scans=counts['scans']+tests.arithmetic.SYNTHETIC_SCANS+100),
                  synthetic_head_forwards=tests.arithmetic.SYNTHETIC_FORWARDS,
                  resources=dict(windows_peak_bytes=windows_memory()['peak_working_set_bytes'],cpu_proxy_bytes=8*peak+8*source_bytes))
        before=cost['counts']['write_bytes']
        for _ in range(12): cost['counts']['write_bytes']=before+len(encode(cost))
        (OUT/'check_cost.json').write_bytes(encode(cost))
    print(json.dumps(dict(status=cost['status'],cases=result.testsRun,seconds=cost['program_seconds'],failures=[x for x in result.cases if x['status']=='FAIL'])))
    return 0 if passed else 1


def read_json(path,b): b.scan(); return json.loads(Path(path).read_bytes())


def validate_locator(locator,b,root=ROOT):
    p=root/locator['path']; b.scan(); raw=p.read_bytes()
    if len(raw)!=locator['bytes'] or sha(raw)!=locator['sha256']: raise RuntimeError('artifact hash mismatch: '+str(p))
    return p


def normalized_text(raw):
    return raw.replace(b'\r\n',b'\n').replace(b'\r',b'\n')


def historical_text_relation(raw,locator):
    # Establish the old RAW hash's relationship to its own Git object first.
    lf=normalized_text(raw)
    variants={'git_blob':raw,'LF':lf,'CRLF':lf.replace(b'\n',b'\r\n'),'CR':lf.replace(b'\n',b'\r')}
    matches=[name for name,value in variants.items()
             if len(value)==locator['bytes'] and sha(value)==locator['sha256']]
    if not matches: raise RuntimeError('historical artifact mismatch: '+locator['path'])
    return dict(historical_raw_sha256=locator['sha256'],git_blob_sha256=sha(raw),
                normalized_sha256=sha(lf),historical_raw_newline_forms=matches)


def historical_locator(locator,b,commit,package):
    path=ROOT/locator['path']
    if path.resolve().is_relative_to(package.resolve()):
        return validate_locator(locator,b)
    b.scan()
    raw=subprocess.check_output(['git','show',f"{commit}:{locator['path']}"],cwd=ROOT)
    if Path(locator['path']).suffix.lower() in ('.py','.md','.json','.txt'):
        relation=historical_text_relation(raw,locator)
        if locator['path']=='models/ResNet.py':
            b.scan(); current=path.read_bytes()
            if normalized_text(current)!=normalized_text(raw):
                raise RuntimeError('current frozen source content changed: '+locator['path'])
            relation['current_normalized_equal']=True
        return dict(path=locator['path'],commit=commit,bytes=len(raw),sha256=sha(raw),text_relation=relation)
    if len(raw)!=locator['bytes'] or sha(raw)!=locator['sha256']:
        raise RuntimeError('historical artifact mismatch: '+locator['path'])
    return dict(path=locator['path'],commit=commit,bytes=len(raw),sha256=sha(raw))


FACT_FIELDS=['fits','backwards','optimizer_steps','forwards','encoder_forwards','feature_samples','scans']


def inherited_records():
    # Frozen adjudication facts are usable even if the CPU gate prevents input reads.
    return [dict(commit=OLD_COMMIT,path=(OLD/'run_record.json').relative_to(ROOT).as_posix(),
                 seconds=562.063,bytes=8259455,status='failed_terminal_limit',
                 counts=dict(fits=161,backwards=160461,optimizer_steps=160461,forwards=160793,
                             encoder_forwards=16,feature_samples=2000,scans=166480),
                 resources=dict(windows_working_set_peak_bytes=6447243264),unknown_resource_fields=['gpu_allocated_peak_bytes','cpu_known_arrays_tensor_proxy_peak_bytes']),
            dict(commit='10e0b657d616983d41de081863a97bf8332534d5',path=(FAILED/'run_record.json').relative_to(ROOT).as_posix(),
                 seconds=220.562,bytes=1537791,status='failed_before_real_input',counts=dict(scans=1407),
                 synthetic_head_forwards=3,resources={},unknown_resource_fields=['windows_working_set_peak_bytes','gpu_allocated_peak_bytes','cpu_known_arrays_tensor_proxy_peak_bytes']),
            dict(commit='6e977f897e95a0b715fbff0c5075fde7ffdc3194',path=(FAILED2/'run_record.json').relative_to(ROOT).as_posix(),
                 seconds=661.719,bytes=1681119,status='failed_no_retry',
                 counts=dict(fits=0,backwards=0,optimizer_steps=0,forwards=3,encoder_forwards=0,feature_samples=0,scans=2350),
                 resources={},unknown_resource_fields=['windows_working_set_peak_bytes','gpu_allocated_peak_bytes','cpu_known_arrays_tensor_proxy_peak_bytes']),
            dict(commit=BASE,path=(FAILED3/'run_record.json').relative_to(ROOT).as_posix(),
                 seconds=694.077,bytes=2356081,status='failed_no_retry',
                 counts=dict(fits=0,backwards=0,optimizer_steps=0,forwards=3,encoder_forwards=0,feature_samples=0,scans=4585),
                 resources={},unknown_resource_fields=['windows_working_set_peak_bytes','gpu_allocated_peak_bytes','cpu_known_arrays_tensor_proxy_peak_bytes'])]


def combine_history(records):
    expected={(r['commit'],r['path']) for r in inherited_records()}
    if len(records)!=4 or {(r['commit'],r['path']) for r in records}!=expected:
        raise RuntimeError('four distinct formal ledgers must be inherited exactly once')
    facts={}; unknown=[]
    for field in FACT_FIELDS:
        total=0
        for row in records:
            value=row['counts'].get(field)
            if value is None:
                unknown.append(dict(path=row['path'],field=field))
                # A failed synthetic gate has no real operations; retain raw missing fields.
                if row['status']=='failed_before_real_input' and field!='scans':
                    value=row.get('synthetic_head_forwards') if field=='forwards' else 0
                else: value=None
            if value is None: total=None; break
            total+=value
        facts[field]=total if total is not None else 'unknown'
    peaks={}
    for field in ['windows_working_set_peak_bytes','gpu_allocated_peak_bytes','cpu_known_arrays_tensor_proxy_peak_bytes']:
        values=[r['resources'].get(field) for r in records]
        known=[v for v in values if isinstance(v,(int,float))]
        peaks[field]=dict(known_max=max(known) if known else None,unknown_sources=[r['path'] for r,v in zip(records,values) if v is None])
    return dict(records=records,seconds=sum(r['seconds'] for r in records),bytes=sum(r['bytes'] for r in records),
                fact_counts=facts,missing_fields_retained=unknown,resource_peaks=peaks,inherited_once=True,
                missing_failed_gate_real_operations_basis='v1 CPU gate prevented real operations; only known unexecuted operations infer zero; missing raw fields retained; v1/v2/v3 synthetic forwards each inherited once')


def read_history(b):
    rows=inherited_records()
    for row in rows:
        path=ROOT/row['path']; b.scan()
        if git('hash-object',str(path))!=git('rev-parse',f"{row['commit']}:{row['path']}"):
            raise RuntimeError('historical ledger changed')
        raw=read_json(path,b)
        if raw['status']!=row['status'] or abs(raw['new_stage_elapsed_seconds']-row['seconds'])>1e-6 or raw['counts']['evidence_bytes']!=row['bytes']:
            raise RuntimeError('historical ledger differs from frozen adjudication')
        for field,value in row['counts'].items():
            if raw['counts'].get(field)!=value: raise RuntimeError('historical fact differs: '+field)
        row.update(counts=raw['counts'],resources=raw['resources'],historical_unknowns=raw.get('historical_failure',{}))
        for field in row['unknown_resource_fields'].copy():
            if field in raw['resources']: row['unknown_resource_fields'].remove(field)
    return combine_history(rows)


def load_prediction(locator,b):
    import numpy as np
    path=validate_locator(locator,b); b.scan()
    with np.load(path) as x: pred=x['argmax'].copy(); ce=x['true_label_CE'].copy()
    if pred.shape!=(1000,) or ce.shape!=(1000,) or not np.isfinite(ce).all(): raise RuntimeError('prediction identity/finite/length failure')
    return pred,ce


def validate_head(metadata,rid,seed,C,objectives):
    if (metadata.get('run_id') not in [original.RUN_ID,RUN_ID] or metadata.get('reference_id')!=rid or metadata.get('seed')!=seed or
        metadata.get('steps')!=1000 or metadata.get('C')!=C or metadata.get('d')!=128 or
        not metadata.get('zero_initialization') or not metadata.get('bias_included') or metadata.get('objectives')!=objectives or
        sorted(objectives)!=['0','100','1000','500'] or metadata.get('optimizer')!=dict(name='Adam',lr=.01,betas=[.9,.999],eps=1e-8,weight_decay=0)):
        raise RuntimeError('head identity/protocol mismatch')


def metrics_from_prediction(pred,ce,labels,groups,b):
    import numpy as np
    b.scan(); C=int(labels.max())+1
    if pred.shape!=labels.shape or int(pred.min())<0 or int(pred.max())>=C or not np.isfinite(ce).all(): raise RuntimeError('invalid saved prediction')
    n=np.bincount(labels,minlength=C); k=np.bincount(labels[pred==labels],minlength=C)
    sums=np.bincount(labels,weights=ce.astype(np.float64),minlength=C)
    if (n<=0).any(): raise RuntimeError('missing validation class')
    recalls=100*k/n; means=sums/n
    return dict(per_class=[dict(class_id=c,sample_denominator=int(n[c]),correct=int(k[c]),CE=float(means[c]),recall_percent=float(recalls[c])) for c in range(C)],
                groups={name:dict(macro_recall_percent=float(recalls[ids].mean()),macro_CE=float(means[ids].mean()),class_denominator=len(ids),sample_denominator=int(n[ids].sum()),class_ids=ids) for name,ids in {'all':list(range(C)),**groups}.items()},
                sample_denominator=int(n.sum()),sample_CE=float(sums.sum()/n.sum()),units=dict(CE='natural-log nats',recall='percent',difference='percentage points'))


def verify_old(b):
    index=read_json(OLD/'artifact_hashes.json',b)
    relations=[]
    for name,row in index['files'].items():
        verified=historical_locator(dict(path=name,**row),b,OLD_COMMIT,OLD)
        if isinstance(verified,dict): relations.append(verified)
    index['verified_historical_shared_locators']=relations
    # Whole tracked old package identity is bound to the baseline commit as well.
    tracked=git('ls-tree','-r','--name-only',OLD_COMMIT,'artifacts/direction_a/phaseP_formal_v1').splitlines()
    for name in tracked:
        b.scan()
        if git('hash-object',name)!=git('rev-parse',f'{OLD_COMMIT}:{name}'): raise RuntimeError('old sealed bytes changed: '+name)
    saved=read_json(OLD/'results.json',b); inputs=read_json(OLD/'input_checks.json',b)
    mapping=read_json(OLD/'predictions/CIFAR10_mapping.json',b)
    from direction_a import probe_formal as f
    import numpy as np
    import torch
    heads=[]; found=[]
    for rid,seed in expected_old():
        name=head_name(seed); row=read_json(OLD/f'head_results/{rid}/{name}.json',b)
        path=validate_locator(row['head'],b); b.scan(); packet=torch.load(path,map_location='cpu',weights_only=True)
        validate_head(packet['metadata'],rid,seed,10,row['objectives'])
        if packet['weight'].shape!=(10,128) or packet['bias'].shape!=(10,) or any(v.dtype!=torch.float32 or not bool(torch.isfinite(v).all()) for v in [packet['weight'],packet['bias']]): raise RuntimeError('old head invalid')
        labels=np.asarray(mapping['train_labels'],np.int64)
        expected=labels if seed is None else f.permute_labels(labels,10,seed,b)
        if packet['metadata']['labels_sha256']!=sha(expected.tobytes()) or packet['metadata']['label_frequencies']!=np.bincount(expected,minlength=10).tolist(): raise RuntimeError('old train label identity mismatch')
        pred,ce=load_prediction(row['prediction'],b)
        recovered=metrics_from_prediction(pred,ce,np.asarray(mapping['validation_labels']),mapping['class_groups'],b)
        if encode(recovered)!=encode(row['metrics']): raise RuntimeError('old saved metrics differ from prediction/CE')
        heads.append(dict(reference_id=rid,seed=seed,name=name,head=row['head'],prediction=row['prediction'],objectives=row['objectives'],result_path=(OLD/f'head_results/{rid}/{name}.json').relative_to(ROOT).as_posix()))
        found.append((rid,seed))
    if found!=expected_old() or len(list((OLD/'heads').rglob('*.pt')))!=160: raise RuntimeError('old complete head set differs from exact 160')
    return index,saved,inputs,mapping,heads,tracked


def experiment(context,b):
    import numpy as np
    import torch
    import torch.nn.functional as F
    from direction_a import probe_formal as f
    helper=original.inherited_helpers(context)
    b.consume('formal_runs'); context['real_input_started']=True
    b.progress=dict(actual_run_commit=git('rev-parse','HEAD'),actual_command=[sys.executable,*sys.argv],real_input_started=True); b.save()
    results=dict(run_id=RUN_ID,references=[],engineering_criteria={str(i):'FAIL' for i in range(1,8)},scientific_status='not_completed')
    results['engineering_criteria']['1']='PASS'
    original.write_json(OUT/'uncertainty.json',dict(status='not_completed',validation_permutations=0,bootstrap=0),b)
    inputs=dict(status='partial',references=[],inherited_validation_points=2,new_validation_points=2,repeated_validation_points=1)
    old_index=None
    original.write_json(OUT/'input_checks.json',inputs,b)
    original.write_json(OUT/'resume_manifest.json',dict(status='planned_not_verified',new_queue=[dict(reference_id=r,seed=s) for r,s in queue()],old_expected_heads=160,head_161='from zero, full 1000 steps; no middle Adam checkpoint'),b)
    try:
        context['formal_history']=read_history(b)
        context['old_counts']=context['formal_history']['fact_counts'].copy()
        b.enter('read_only_old_qualification')
        old_index,saved,old_inputs,c10_mapping,joint,tracked=verify_old(b)
        old_ledger=read_json(OLD/'run_record.json',b)
        if old_ledger['status']!='failed_terminal_limit' or old_ledger['counts']['fits']!=161 or old_ledger['counts']['backwards']!=160461 or old_ledger['counts']['optimizer_steps']!=160461 or old_ledger['counts']['scans']!=166480 or old_ledger['counts']['evidence_bytes']!=8259455 or abs(old_ledger['new_stage_elapsed_seconds']-562.063)>1e-6:
            raise RuntimeError('old ledger differs from v6 inherited bounds')
        context['old_counts']=context['formal_history']['fact_counts'].copy()
        context['old_ledger']=old_ledger
        manifest=dict(old_commit=OLD_COMMIT,failed_resume_commits=[r['commit'] for r in inherited_records()[1:]],formal_history=context['formal_history'],old_ledger_path=(OLD/'run_record.json').relative_to(ROOT).as_posix(),old_status=old_ledger['status'],old_6GiB_qualification='FAIL',old_criterion_6='FAIL',
                      preserved_heads=joint.copy(),new_queue=[dict(reference_id=r,seed=s) for r,s in queue()],head_161='from zero, full 1000 steps; no middle optimizer checkpoint',old_bytes_verified=True,old_tracked_files=tracked,
                      old_source_commit='a12905c9ffdfe65270feb83e587bffa4b90f612a',G1_2_input_commit=original.G12_COMMIT)
        manifest['verified_historical_shared_locators']=old_index['verified_historical_shared_locators']
        original.write_json(OUT/'resume_manifest.json',manifest,b)
        for name in ('preregistration.json','reference_acceptance.json','measurements.json','artifact_hashes.json','run_record.json','decision.json'): helper.committed(helper.G12/name,original.G12_COMMIT,b)
        index=helper.read_json(helper.G12/'artifact_hashes.json',b)
        for name in ('preregistration.json','reference_acceptance.json','measurements.json','run_record.json','decision.json'):
            if helper.digest_file(helper.G12/name,b)!=index['files'][name]: raise RuntimeError('G1.2 package mismatch')
        accepted=helper.read_json(helper.G12/'reference_acceptance.json',b)['references']
        measurements=helper.read_json(helper.G12/'measurements.json',b)['references']
        decision=helper.read_json(helper.G12/'decision.json',b)
        if decision['fail_count'] or decision['blocked'] or [a['reference']['reference_id'] for a in accepted]!=reference_ids(): raise RuntimeError('fixed G1.2 qualification failed')
        prep=helper.read_json(ROOT/context['history']['ledger_path'],b)
        helper.committed(ROOT/context['history']['ledger_path'],original.PREP_COMMIT,b)
        if abs(prep['cumulative_conservative_elapsed_upper_seconds']-74.9171745)>1e-6 or prep['cumulative_accountable_write_bytes']!=11988355: raise RuntimeError('preparation inherited twice or changed')
        context['history']['historical_unknowns']=prep['historical_failure']['historical_unknowns']
        source=helper.UPSTREAM/'preregistration.md'; helper.committed(source,original.PREP_COMMIT,b)
        inputs['provenance']=dict(prior_validation_reported=True,all_four_preselected_references_delivered=True,selection_leakage_detected=False,preselected_rounds_sha256=helper.digest_file(source,b),basis='v5 fixed r40/r80, v6 all four mandatory')
        if not torch.cuda.is_available(): raise RuntimeError('CUDA unavailable')
        torch.set_num_threads(2); torch.use_deterministic_algorithms(True)
        torch.backends.cuda.matmul.allow_tf32=False; torch.backends.cudnn.allow_tf32=False; torch.cuda.reset_peak_memory_stats()
        p=read_json(OUT/'preregistration.json',b)
        original.write_json(OUT/'environment.json',dict(actual_run_commit=git('rev-parse','HEAD'),actual_command=p['actual_command'],python=sys.version,numpy=np.__version__,torch=torch.__version__,CUDA=torch.version.cuda,device=torch.cuda.get_device_name(),protocol_v5_sha256=p['protocol_sha256'],protocol_v6_sha256=p['protocol_v6_sha256'],protocol_v8_sha256=p['protocol_v8_sha256'],protocol_v9_sha256=p['protocol_v9_sha256']),b)
        old_fit=sum(h['fit_save_seconds'] for row in saved['references'] for h in row['heads'])
        remaining=max(0.,p['estimates']['fitting_seconds']-old_fit)*1.8+160+120
        prefit=dict(old_complete_fit_save_seconds=old_fit,remaining_operations_estimate_seconds=remaining,already_spent_resume_seconds=time.monotonic()-b.started,
                    inherited_seconds=INHERITED_SECONDS,already_written_resume_bytes=b.counts['evidence_bytes'],remaining_write_estimate_bytes=68*1024**2,terminal_reserve_seconds=120,terminal_reserve_bytes=8*1024**2)
        original.write_json(OUT/'prefit_budget.json',prefit,b)
        if remaining+time.monotonic()-b.started>=LIMITS['wall_seconds'] or 68*1024**2+b.counts['evidence_bytes']>=LIMITS['evidence_bytes']: raise RuntimeError('insufficient joint budget before fitting')
        datasets={'CIFAR10':c10_mapping}; predictions={}; new_completed=0
        b.planned_references=reference_ids()
        for a in accepted:
            ref=a['reference']; rid=ref['reference_id']; ds=ref['dataset']; b.enter(rid)
            point=next(x for x in measurements if x['reference_id']==rid)
            packet,before=helper.frozen_checkpoint(ref,a,b)
            oldrow=next((x for x in saved['references'] if x['reference_id']==rid),None)
            if rid==reference_ids()[0]:
                row=oldrow; check=next(x for x in old_inputs['references'] if x['reference_id']==rid).copy()
                check.update(qualification='inherited',validation_reencoded=0); inputs['references'].append(check)
                labels=np.asarray(c10_mapping['validation_labels']); mapping=c10_mapping; groups=mapping['class_groups']; C=10
                if row['state_before']!=before or row['state_after']!=before: raise RuntimeError('inherited reference changed')
            else:
                z,y,indices,C,groups,original_head,check=helper.load_train(ref,point,a,index,b)
                if len(y)!=p['train']['samples'][ds] or groups!=a['binding']['class_groups'] or sorted(sum(groups.values(),[]))!=list(range(C)): raise RuntimeError('train/group qualification failure')
                if not torch.equal(original_head['weight'],packet['state_dict']['linear.weight']) or not torch.equal(original_head['bias'],packet['state_dict']['linear.bias']): raise RuntimeError('cached original head mismatch')
                val,labels,val_indices,vcheck=original.validation_features(a,packet,indices,ds,C,b,helper)
                mapping=dict(train_indices=indices.tolist(),train_labels=y.tolist(),validation_indices=val_indices.tolist(),validation_labels=labels.tolist(),class_groups=groups,label_mapping=a['binding']['label_mapping'],index_namespace='official_train',test_samples=0)
                if ds in datasets and datasets[ds]!=mapping: raise RuntimeError('paired mapping identity mismatch')
                if ds not in datasets: datasets[ds]=mapping; original.write_json(OUT/f'predictions/{ds}_mapping.json',mapping,b)
                check.update(vcheck,qualification='repeated_validation' if ds=='CIFAR10' else 'new_validation',original_head_matches=True,train_frequencies=torch.bincount(y,minlength=C).tolist())
                inputs['references'].append(check)
                train=z.cuda(); true=torch.as_tensor(labels,device='cuda'); del z
                if oldrow:
                    row=oldrow
                    original_pred,original_ce=load_prediction(row['original_prediction'],b)
                    row['original_head']=metrics_from_prediction(original_pred,original_ce,labels,groups,b)
                    row['original_summary_recovered_from_saved_prediction_CE']=True
                else:
                    with torch.no_grad():
                        b.consume('forwards'); logits=F.linear(val,original_head['weight'].cuda(),original_head['bias'].cuda())
                        original_metrics=f.summarize(logits,true,groups,b)
                        original_pred=logits.argmax(1).cpu().numpy().astype(np.int16); original_ce=F.cross_entropy(logits,true,reduction='none').cpu().numpy()
                    loc=original.save_prediction(OUT/f'predictions/{rid}/original.npz',original_pred,original_ce,b)
                    row=dict(reference_id=rid,dataset=ds,class_groups=groups,original_head=original_metrics,original_prediction=loc,uniform_control=f.uniform_control(C,[1000//C]*C,groups),heads=[],state_before=before)
                for qrid,seed in queue():
                    if qrid!=rid: continue
                    assert_new_head(rid,seed); name=head_name(seed); start=time.monotonic()
                    label=y.numpy() if seed is None else f.permute_labels(y.numpy(),C,seed,b)
                    fitted,objectives,metrics,pred,ce,diagnostic=f.fit(train,torch.as_tensor(label,device='cuda'),val,true,C,groups,b)
                    meta=dict(run_id=RUN_ID,reference_id=rid,seed=seed,label_kind='real' if seed is None else 'permuted',steps=1000,labels_sha256=sha(label.tobytes()),label_frequencies=np.bincount(label,minlength=C).tolist(),objectives=objectives,optimizer=p['probe']['optimizer'],C=C,d=128,zero_initialization=True,bias_included=True)
                    loc=helper.save_head(OUT/f'heads/{rid}/{name}.pt',{**fitted,'metadata':meta},b)
                    predloc=original.save_prediction(OUT/f'predictions/{rid}/{name}.npz',pred,ce,b)
                    h=dict(name=name,seed=seed,head=loc,prediction=predloc,objectives=objectives,metrics=metrics,optimization=diagnostic,fit_save_seconds=time.monotonic()-start,train_labels_sha256=meta['labels_sha256'])
                    row['heads'].append(h); original.write_json(OUT/f'head_results/{rid}/{name}.json',h,b)
                    joint.append(dict(reference_id=rid,seed=seed,name=name,head=loc,prediction=predloc,objectives=objectives,result_path=(OUT/f'head_results/{rid}/{name}.json').relative_to(ROOT).as_posix()))
                    new_completed+=1; b.progress.update(completed_heads=160+new_completed,new_completed_heads=new_completed,reference=rid)
                    if new_completed%10==0: b.save(); print(json.dumps(b.progress),flush=True)
                _,after=helper.frozen_checkpoint(ref,a,b)
                if before!=after or tensor_state_sha(packet['state_dict'])!=before: raise RuntimeError('frozen state changed')
                row['state_after']=after
                del train,val,true,packet,fitted; gc.collect(); torch.cuda.empty_cache()
            results['references'].append(row)
            if len(row['heads'])!=100 or [h['seed'] for h in row['heads']]!=[None,*f.TRAIN_SEEDS]: raise RuntimeError('joint head order/count mismatch')
            row['differences_pp']=f.differences(row['heads'][0]['metrics'],{'original':row['original_head'],'uniform':row['uniform_control'],**{h['name']:h['metrics'] for h in row['heads'][1:]}})
            R=row['heads'][0]['metrics']['groups']['tail']['macro_recall_percent']
            row['train_empirical_controls']=f.train_control(R,[h['metrics']['groups']['tail']['macro_recall_percent'] for h in row['heads'][1:]])
            op,_=load_prediction(row['original_prediction'],b); real,_=load_prediction(row['heads'][0]['prediction'],b); predictions[rid]=(op,real)
            original.write_json(OUT/f'point_results/{rid}.json',row,b)
            b.delivered_references.append(rid); original.write_json(OUT/'input_checks.json',inputs,b)
        if any(b.counts[k]!=v for k,v in dict(fits=240,backwards=240000,optimizer_steps=240000,encoder_forwards=24,feature_samples=3000).items()): raise RuntimeError('resume operation count mismatch')
        keys=[(x['reference_id'],x['seed']) for x in joint]
        if len(keys)!=400 or len(set(keys))!=400 or set(keys)!=set(expected_old()+queue()): raise RuntimeError('400 unique head joint index incomplete')
        for item in joint:
            path=validate_locator(item['head'],b); b.scan(); value=torch.load(path,map_location='cpu',weights_only=True)
            validate_head(value['metadata'],item['reference_id'],item['seed'],10 if 'CIFAR10-' in item['reference_id'] else 100,item['objectives'])
            if not bool(torch.isfinite(value['weight']).all()) or not bool(torch.isfinite(value['bias']).all()): raise RuntimeError('joint nonfinite head')
            load_prediction(item['prediction'],b)
        original.write_json(OUT/'joint_index.json',dict(heads=joint,count=400,unique_heads=400,effective_updates=400000,readback='PASS',mapping_paths={'CIFAR10':(OLD/'predictions/CIFAR10_mapping.json').relative_to(ROOT).as_posix(),'CIFAR100':(OUT/'predictions/CIFAR100_mapping.json').relative_to(ROOT).as_posix()}),b)
        inputs.update(status='PASS',distinct_validation_points=4,distinct_validation_samples=4000,encoder_fact_cumulative=40,encoded_samples_fact_cumulative=5000,new_train_encoding=0)
        original.write_json(OUT/'input_checks.json',inputs,b)
        b.enter('fixed_prediction_statistics'); uncertainty=dict(run_id=RUN_ID,references={},interpretation='approximate validation sampling intervals; not training repeats',validation_permutation_assumptions=p['inference_assumptions'],prior_validation_disclosure=p['disclosure'])
        for ds,mapping in datasets.items():
            rows=[x for x in results['references'] if x['dataset']==ds]; labels=np.asarray(mapping['validation_labels']); tail=mapping['class_groups']['tail']
            perms=f.paired_permutation([predictions[x['reference_id']][1] for x in rows],labels,tail,f.VAL_SEEDS[ds],b)
            boots=f.paired_bootstrap([predictions[x['reference_id']] for x in rows],labels,tail,b)
            for row,perm,boot in zip(rows,perms,boots):
                uncertainty['references'][row['reference_id']]=dict(validation_permutation=perm,paired_bootstrap=boot)
                row['science']=f.science(ds,row['heads'][0]['metrics']['groups']['tail']['macro_recall_percent'],row['original_head']['groups']['tail']['macro_recall_percent'],row['train_empirical_controls']['tail_scores_percent'],perm,boot,True)
                if row['science']['calibration_space']=='FAIL' and row['heads'][0]['optimization']['final_segment_still_changing']: row['failure_interpretation']='求解未稳定，失败原因未定；不据此断言表征无信息'
        uncertainty.update(validation_permutations=39996,bootstrap=8000)
        original.write_json(OUT/'uncertainty.json',uncertainty,b)
        results['engineering_criteria']={str(i):'PASS' for i in range(1,8)}
        results['scientific_dataset_status']={ds:'PASS' if all(x['science']['calibration_space']=='PASS' for x in results['references'] if x['dataset']==ds) else 'FAIL' for ds in datasets}
        results['scientific_status']='PASS' if all(x=='PASS' for x in results['scientific_dataset_status'].values()) else 'FAIL'
        b.enter('archive')
    except Exception:
        results['blocked']=traceback.format_exc(); raise
    finally:
        original.write_json(OUT/'results.json',results,b)
        if old_index:
            for name,record in old_index['files'].items(): historical_locator(dict(path=name,**record),b,OLD_COMMIT,OLD)
            original.write_json(OUT/'old_preservation.json',dict(status='PASS',old_files=len(old_index['files']),baseline_commit=OLD_COMMIT,old_bytes_unchanged=True),b)


def launch():
    cost=json.loads((OUT/'check_cost.json').read_bytes())
    if cost['status']!='PASS': raise RuntimeError('one CPU gate failed; no real-input run')
    if subprocess.run(['git','merge-base','--is-ancestor',BASE,'HEAD'],cwd=ROOT).returncode: raise RuntimeError('baseline not ancestor')
    for name,digest in cost['fingerprints'].items():
        if sha((ROOT/name).read_bytes())!=digest or git('hash-object',name)!=git('rev-parse',f'HEAD:{name}'): raise RuntimeError('source changed or not committed before real inputs')
    name=(OUT/'preregistration.json').relative_to(ROOT).as_posix()
    if git('hash-object',name)!=git('rev-parse',f'HEAD:{name}'): raise RuntimeError('registration not committed')
    history=original.preparation_history()
    context=dict(output=OUT,run_id=RUN_ID,history=history,limits=LIMITS,started=ENTRY_STARTED-cost['program_seconds']-IMPLEMENTATION_UPPER_SECONDS-20,
                 preparation_initial_write_bytes=cost['counts']['write_bytes'],preparation_initial_scans=cost['counts']['scans'],source_write_events=cost['source_write_events'],implementation_revisions=1,
                 total_wall_seconds=LIMITS['wall_seconds']+history['upper_seconds'],total_write_bytes=LIMITS['evidence_bytes']+history['bytes'],cumulative_scan_limit=LIMITS['scans']+history['scan_upper_bound'],new_preparation_launches=0,new_failed_restarts=0,
                 cpu_proxy_upper_bytes=cost['resources']['cpu_proxy_bytes'],cpu_proxy_basis='eight times tracked synthetic buffers; accepted cache inventory envelope',emergency_closure_bytes=1024**2,synthetic_head_forwards=cost['synthetic_head_forwards'],
                 precheck_resource_peaks=dict(windows_working_set_peak_bytes=cost['resources']['windows_peak_bytes'],cpu_known_arrays_tensor_proxy_peak_bytes=cost['resources']['cpu_proxy_bytes']),archive_repo_paths=True,archive_extra_paths=[ROOT/n for n in SOURCES])
    ledger=run_once(context)
    print(json.dumps(dict(status=ledger['status'],seconds=ledger['new_stage_elapsed_seconds'],counts=ledger['counts'],error=ledger['error']),ensure_ascii=False))
    return 0 if ledger['status']=='completed' else 1


def review(ledger,results):
    criteria=results.get('engineering_criteria',{str(i):'FAIL' for i in range(1,8)}).copy()
    completed=ledger['status']=='completed'
    if not completed: criteria['7']='FAIL'
    science=results.get('scientific_status','FAIL') if completed else 'FAIL'
    fail=sum(x=='FAIL' for x in criteria.values())+int(science!='PASS')
    c=ledger['counts']; r=ledger.get('resources',{})
    seconds=INHERITED_SECONDS+ledger.get('new_stage_elapsed_seconds',0); written=INHERITED_BYTES+c.get('evidence_bytes',0)
    lines=['# 交付单：P 正式第5轮保留160头续跑','',f'- 对应任务单的基准 commit：{BASE}','- 本次交付 commit：见本提交','', '## 做了什么（≤5 条）',
           '- 最小v9恢复入口及一次合成CPU套件，v5科学算术完整复用；源码与预登记先提交。',
           f"- 旧160头只读复用；新完整头 {ledger.get('progress',{}).get('new_completed_heads',0)}/240，第161头从零重做。",
           '- 累计账本与实际检查结果已封存；四点联合推断是否完成见下表，旧6 GiB失败和未知保留。','', '## 产出文件',
           '- artifacts/direction_a/phaseP_formal_resume_v4/：预登记、语法/CPU/输入检查、manifest、results/uncertainty、run_record/artifact_hashes。',
           '- 完成运行时另产出 joint_index、heads/、head_results/、predictions/；本轮完成量见判据3。','', '## 判据自评',
           '|判据编号|结果 PASS/FAIL|证据位置 / 关键数字|','|---|---|---|']
    evidence={'1':'syntax_check.json / selfchecks.json；一次合成生产生命周期及保护检查',
              '2':f"input_checks.json；新encoder {c.get('encoder_forwards',0)}/24；新验证编码 {c.get('feature_samples',0)}/3000",
              '3':f"resume_manifest / joint_index；新拟合 {c.get('fits',0)}/240；新反向/Adam {c.get('backwards',0)}/{c.get('optimizer_steps',0)}",
              '4':'results / predictions；完整分母、机会、99训练置乱及CP',
              '5':'uncertainty；39996次全标签配对置乱、≥、加一p及四点调整',
              '6':'uncertainty / results；8000次类配对bootstrap、linear分位及目标诊断',
              '7':f"run_record / artifact_hashes / old_preservation；终态 {ledger['status']}；旧峰失败保留"}
    for k in map(str,range(1,8)): lines.append(f'|{k}|{criteria[k]}|{evidence[k]}|')
    lines += [f'|8|{science}|四点固定科学判据，逐点见下表|','','|参考|尾R %|Δ pp|可分性|校准空间|','|---|---:|---:|---|---|']
    for rid in reference_ids():
        row=next((x for x in results.get('references',[]) if x['reference_id']==rid),{})
        s=row.get('science',{})
        if s and completed: lines.append(f"|{rid}|{s['R_percent']:.6f}|{s['delta_pp']:.6f}|{s['separability']}|{s['calibration_space']}|")
        else: lines.append(f'|{rid}|未完成|未完成|FAIL|FAIL|')
    lines += ['', '## 实际资源消耗',
              f"- 旧正式562.063秒/8259455 B/166480扫描、失败v1 220.562秒/1537791 B/1407扫描、失败v2 661.719秒/1681119 B/2350扫描、失败v3 694.077秒/2356081 B/4585扫描；v4保守{ledger.get('new_stage_elapsed_seconds',0):.6f}秒/{c.get('evidence_bytes',0)} B/{c.get('scans',0)}扫描。",
              f'- 正式总账 {seconds:.6f}/{FORMAL_SECONDS}秒、{written}/134217728 B；余量 {FORMAL_SECONDS-seconds:.6f}秒、{134217728-written} B。',
              f"- 本轮CUDA峰{r.get('gpu_allocated_peak_bytes','unknown')} B、Windows峰{r.get('windows_working_set_peak_bytes','unknown')} B、CPU代理峰{r.get('cpu_known_arrays_tensor_proxy_peak_bytes','unknown')} B；跨阶段最大峰及缺项见run_record.joint_formal_accounting.resource_peaks。",
              f'- 准备74.9171745秒/11988355 B只继承一次；P累计 {74.9171745+seconds:.6f}秒/{11988355+written} B；旧未知及旧判据6 FAIL保留。',
              f"- 新有效更新{c.get('backwards',0)}，完整头{160+ledger.get('progress',{}).get('new_completed_heads',0)}/400；失败461次与CPU前向分列；重复编码及近似区间见证据。",
              f'- 自评FAIL {fail}条；完整性/工程资格与科学得分分开。','','## 阻塞（没有写“无”）',
              '无' if completed else '- '+(ledger.get('error') or results.get('blocked') or 'CPU/入口失败').splitlines()[-1],
              '', '## 异议（没有写“无”）','无','', '## 需要审查者裁决的问题（≤3 条，没有写“无”）',
              '- 按v6联合工程资格及v5四点科学门槛裁决；P交付后由审查者接续原G1.1文档任务。']
    if len(lines)>80: raise RuntimeError('review exceeds 80 lines')
    return ('\n'.join(lines)+'\n').encode(),fail,not completed


def seal_limit_exceeded(ledger):
    c=ledger['counts']
    return (c['evidence_bytes']>=LIMITS['evidence_bytes'] or
            ledger['joint_formal_accounting']['seconds']>=FORMAL_SECONDS or
            c['scans']>LIMITS['scans'] or
            ledger['resources']['windows_working_set_peak_bytes']>=LIMITS['windows_peak_working_set_bytes'])


def seal():
    import torch
    r={}
    cost=json.loads((OUT/'check_cost.json').read_bytes())
    if (OUT/'run_record.json').exists():
        ledger=json.loads((OUT/'run_record.json').read_bytes()); index=json.loads((OUT/'artifact_hashes.json').read_bytes())
        if ledger.get('delivery_verification'): raise FileExistsError('already sealed')
    else:
        ledger=dict(status='failed_before_real_input',error='CPU gate/launch failed; no retry authorized',counts=dict(evidence_bytes=cost['counts']['write_bytes']+1024**2,scans=cost['counts']['scans'],fits=0,backwards=0,optimizer_steps=0,forwards=cost['synthetic_head_forwards'],encoder_forwards=0,feature_samples=0,formal_runs=0),new_stage_elapsed_seconds=cost['program_seconds']+IMPLEMENTATION_UPPER_SECONDS+20,resources=dict(windows_working_set_peak_bytes=cost['resources']['windows_peak_bytes'],gpu_allocated_peak_bytes=0,cpu_known_arrays_tensor_proxy_peak_bytes=cost['resources']['cpu_proxy_bytes']))
        files={}
        for path in [*OUT.rglob('*'),*[ROOT/n for n in SOURCES]]:
            if path.is_file():
                raw=path.read_bytes(); files[path.relative_to(ROOT).as_posix()]=dict(bytes=len(raw),sha256=sha(raw))
        index=dict(files=files,excluded=['artifact_hashes.json (self)'])
    results=json.loads((OUT/'results.json').read_bytes()) if (OUT/'results.json').exists() else {}
    scans=0; error=None
    for name,row in index['files'].items():
        raw=(ROOT/name).read_bytes(); scans+=1
        if len(raw)!=row['bytes'] or sha(raw)!=row['sha256']: error='archive readback mismatch: '+name; break
    if ledger['status']=='completed':
        old_index=json.loads((OLD/'artifact_hashes.json').read_bytes()); scans+=1
        for name,row in old_index['files'].items():
            scans+=1
            try: historical_locator(dict(path=name,**row),type('Scan',(),{'scan':lambda self:None})(),OLD_COMMIT,OLD)
            except Exception: error='old sealed artifact changed: '+name; break
    elapsed=time.monotonic()-ENTRY_STARTED+.5
    if elapsed>20: error='verification exceeded precharged 20 second reserve'
    if error: ledger.update(status='failed_no_retry',error=error)
    ledger['counts']['scans']+=scans+10
    ledger['resources']['windows_working_set_peak_bytes']=max(ledger['resources'].get('windows_working_set_peak_bytes',0),windows_memory()['peak_working_set_bytes'])
    c=ledger['counts']; r=ledger['resources']
    history=ledger.get('formal_history') or combine_history(inherited_records())
    facts={k:(history['fact_counts'][k]+c.get(k,0) if isinstance(history['fact_counts'][k],int) else 'unknown') for k in FACT_FIELDS}
    peaks={k:dict(new_measured=r.get(k),historical=history['resource_peaks'][k],
                  known_max=max([v for v in [r.get(k),history['resource_peaks'][k]['known_max']] if isinstance(v,(int,float))],default=None)) for k in history['resource_peaks']}
    ledger['joint_formal_accounting']=dict(inherited=history,new_seconds=ledger['new_stage_elapsed_seconds'],
        fact_counts=facts,resource_peaks=peaks,old_terminal_status='failed_terminal_limit',failed_resume_status='failed_before_real_input',failed_resume_v2_status='failed_no_retry',failed_resume_v3_status='failed_no_retry',
        old_6GiB_qualification='FAIL',old_criterion_6='FAIL',effective_complete_heads=160+ledger.get('progress',{}).get('new_completed_heads',0),
        unknown_history_retained=True,implementation_revisions=7,syntax_checks=7,CPU_suites=7,
        formal_runs=3+c.get('formal_runs',0),duplicate_validation_encoder=min(8,c.get('encoder_forwards',0)))
    ledger['delivery_verification']=dict(program_seconds=elapsed,precharged_seconds=20,index_readback='PASS' if error is None else 'FAIL',checked_files=scans,source_commit=git('rev-parse','HEAD'),real_input_reads=0,experiment_runs_new=0)
    # These are mutually distinct: preparation, old formal, new recovery, P total.
    ledger['joint_formal_accounting']['seconds']=INHERITED_SECONDS+ledger['new_stage_elapsed_seconds']
    before=c['evidence_bytes']; records=index['files']; ledger_name=(OUT/'run_record.json').relative_to(ROOT).as_posix()
    for _ in range(16):
        reviewer,fail,blocked=review(ledger,results)
        records['docs/workflow/TO_REVIEWER.md']=dict(bytes=len(reviewer),sha256=sha(reviewer))
        records[ledger_name]=dict(bytes=len(encode(ledger)),sha256='0'*64)
        c['evidence_bytes']=before+len(reviewer)+len(encode(ledger))+len(encode(index))
        ledger['joint_formal_accounting']['bytes']=INHERITED_BYTES+c['evidence_bytes']
        ledger['P_cumulative']=dict(seconds=74.9171745+INHERITED_SECONDS+ledger['new_stage_elapsed_seconds'],bytes=11988355+INHERITED_BYTES+c['evidence_bytes'],preparation_inherited_once=True)
    if seal_limit_exceeded(ledger): ledger.update(status='failed_terminal_limit',error='seal cumulative resource limit')
    reviewer,fail,blocked=review(ledger,results); records['docs/workflow/TO_REVIEWER.md']=dict(bytes=len(reviewer),sha256=sha(reviewer))
    raw=encode(ledger); records[ledger_name]=dict(bytes=len(raw),sha256=sha(raw))
    (ROOT/'docs/workflow/TO_REVIEWER.md').write_bytes(reviewer); (OUT/'run_record.json').write_bytes(raw); (OUT/'artifact_hashes.json').write_bytes(encode(index))
    print(json.dumps(dict(status=ledger['status'],FAIL=fail,blocked=blocked,verified_files=scans),ensure_ascii=False))
    return 0


if __name__=='__main__':
    if Path(sys.executable).resolve()!=Path(r'E:\anaconda3\python.exe').resolve(): raise RuntimeError('required project interpreter mismatch')
    if sys.argv[1:]==['--check']: sys.exit(check())
    if sys.argv[1:]==['--run']: sys.exit(launch())
    if sys.argv[1:]==['--seal']: sys.exit(seal())
    raise RuntimeError('use --check, commit, --run once, then --seal')
