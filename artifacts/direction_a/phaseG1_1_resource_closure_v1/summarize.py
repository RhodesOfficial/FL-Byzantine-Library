"""One frozen-metadata arithmetic pass; no experiment imports or scientific results.
Run with E:/anaconda3/python.exe. Never overwrite an existing accounting.json.
Final document hashes are sealed separately, within the reserved delivery tail.
"""
import ctypes
import hashlib
import json
from pathlib import Path
import subprocess
import time
import tracemalloc

START=time.perf_counter()
tracemalloc.start()
ROOT=Path(__file__).resolve().parents[3]
BASE='b37efe0f53f899131b76926d681132af7b90f6b2'
AUTH='9625da960957a5a69eda16ac5d08821f9fbc5dc7'
OLD='artifacts/direction_a/phaseG1_1_formal_F_resume_v1/'
OUT=Path(__file__).resolve().parent
assert not (OUT/'accounting.json').exists(), 'single pass; no overwrite'
reads=[]
def git(*args):
    return subprocess.check_output(['git',*args],cwd=ROOT)
assert git('rev-parse','HEAD').decode().strip()==AUTH
subprocess.run(['git','merge-base','--is-ancestor',BASE,AUTH],cwd=ROOT,check=True)
protected=[OLD,'artifacts/direction_a/phaseG1_1_formal_F_v1',
    'direction_a/formal_f.py','direction_a/formal_f_policy.py',
    'scripts/run_direction_a_formal_f.py','docs/DIRECTION_A_PROTOCOL_FREEZE_v1.md']
identity=[]
for p in protected:
    before=git('rev-parse',BASE+':'+p.rstrip('/')).decode().strip()
    now=git('rev-parse',AUTH+':'+p.rstrip('/')).decode().strip()
    assert before==now,p
    identity.append(dict(path=p,baseline_git_object=before,authorization_git_object=now))
def load(name):
    p=OLD+name
    raw=git('show',BASE+':'+p)
    reads.append(dict(path=p,origin=BASE,bytes=len(raw),purpose='frozen accounting input'))
    return json.loads(raw)
binding=load('binding.json')
audit=load('delivery_audit.json')
prior=audit['resources']
assert prior['seconds']==95.73515180000686
assert prior['writes']==2545091 and prior['metadata']==15150236
assert prior['scans']==523 and prior['simulated_bytes']==29642603849
assert len(binding['rows'])==80 and len(binding['references'])==4
per_reference=[]
for ri,ref in enumerate(binding['references']):
    rows=[r for r in binding['rows'] if r['reference']==ref['reference_id']]
    assert len(rows)==20 and sorted(r['client'] for r in rows)==list(range(20))
    charges=[dict(client=r['client'],reference=r['reference_bytes'],
        return_preparation=r['return_bytes'],gradient_preparation=r['message_bytes'],
        effective_upload_upper=r['return_bytes']+r['message_bytes'],
        total=r['reference_bytes']+2*r['return_bytes']+2*r['message_bytes']) for r in rows]
    top=sorted(charges,key=lambda r:(-r['total'],r['client']))[:8]
    coarse=8*(max(r['reference_bytes'] for r in rows)+2*max(r['return_bytes'] for r in rows)+2*max(r['message_bytes'] for r in rows))
    per_reference.append(dict(index=ri,reference=ref['reference_id'],attempts=192,
        row_locator=OLD+'binding.json#rows',client_charges=charges,
        top8_clients=[r['client'] for r in top],top8_sum=sum(r['total'] for r in top),
        main_upper=192*sum(r['total'] for r in top),coarse_main_upper=192*coarse,
        all20_message_bytes=sum(r['message_bytes'] for r in rows)))
main=sum(r['main_upper'] for r in per_reference)
coarse_main=sum(r['coarse_main_upper'] for r in per_reference)
coverage=8*per_reference[0]['top8_sum']
# Two boundary attempts have six and two static checks. Charge each as a full
# dispatch+return at the largest reference-0 endpoint; no observed state used.
boundary=8*max(r['total'] for r in per_reference[0]['client_charges'])
registration=70757 # frozen runner bootstrap assertion and formal plan W03
metadata=16*1024**2 # entire F metadata cap; conservative overlapping allowance
components=dict(main=main,coverage8=coverage,boundary2_eight_checks=boundary,
    registration=registration,preparation_metadata_full_cap=metadata)
full=sum(components.values()); limit=32*1024**3
coarse_full=coarse_main+8*(per_reference[0]['coarse_main_upper']//192)+boundary+registration+metadata
cost=dict(formula='C_ir=reference_ir+2*return_ir+2*message_ir',
    worst_case='all invited online and returned; top8 among all20 each reference; 3 scenarios*32*(generate+replay)=192',
    per_reference=per_reference,components=components,full_upper=full,
    coarse_main_only=coarse_main,coarse_full=coarse_full,hard_limit=limit,
    signed_excess=full-limit,within_hard_limit=full<=limit,
    actual_payload_reference_only=prior['simulated_bytes'],actual_payload_already_in_prior=True,
    new_payload_charged=0,historical_registered=28544398373,
    historical_resource_criterion_7='FAIL',
    metadata_overlap='full16MiB conservatively duplicates registration/event metadata; physical network null',
    preparation_scope='C contains state and gradient preparation for every dispatch including failures; metadata cap covers input/preparation/repeated copies/archive/seal/Git',
    boundary_scope='6+2 static checks from runner boundary loop; offline/failed savings not used',
    provenance={'charge':'direction_a/formal_f.py#charge',
        'workload':'scripts/run_direction_a_formal_f.py#run/step/main/fixtures/boundary',
        'registration':'runner bootstrap assertion=70757; formal plan section2 W03',
        'metadata':'frozen protocol section7 full F16MiB cap'})
delta=dict(seconds=60,writes=262144,metadata=1572864,scans=128,
    simulated_bytes=0,attempts=0,implementation_revisions=0,syntax_checks=0,
    CPU_suites=0,real_entries=0,events=0,model_operations=0,scientific_statistics=0)
keys=('seconds','writes','metadata','scans','simulated_bytes','attempts',
      'implementation_revisions','syntax_checks','CPU_suites','real_entries')
joint={k:prior[k]+delta[k] for k in keys}
limits=dict(seconds=300,writes=33554432,metadata=16777216,scans=2048,
    simulated_bytes=limit,attempts=800,implementation_revisions=3,
    syntax_checks=3,CPU_suites=3,real_entries=2)
assert all(joint[k]<=limits[k] for k in limits)
balances={k:limits[k]-joint[k] for k in limits}
class Memory(ctypes.Structure):
    _fields_=[('cb',ctypes.c_ulong),('PageFaultCount',ctypes.c_ulong)]+[(n,ctypes.c_size_t) for n in ('PeakWorkingSetSize','WorkingSetSize','QuotaPeakPagedPoolUsage','QuotaPagedPoolUsage','QuotaPeakNonPagedPoolUsage','QuotaNonPagedPoolUsage','PagefileUsage','PeakPagefileUsage')]
memory=Memory(); memory.cb=ctypes.sizeof(memory)
assert ctypes.windll.psapi.GetProcessMemoryInfo(ctypes.windll.kernel32.GetCurrentProcess(),ctypes.byref(memory),memory.cb)
proxy=tracemalloc.get_traced_memory()[1]
joint['windows']=max(prior['windows'],memory.PeakWorkingSetSize,256*1024**2)
joint['cpu_proxy']=max(prior['cpu_proxy'],proxy,256*1024**2)
assert joint['windows']<=2*1024**3 and joint['cpu_proxy']<=512*1024**2
discovery=[('docs/workflow/ROLE_EXECUTOR.md',5585),('docs/workflow/TO_EXECUTOR.md',7318),
    ('docs/workflow/STATE.md',12059),(OLD+'preregistration.json',3402),
    (OLD+'delivery_readback.json',3550),(OLD+'preparation_ledger.json',3612),
    (OLD+'mechanism.json',674),(OLD+'coverage.json',7498),
    ('direction_a/formal_f.py',4017),('direction_a/formal_f_policy.py',1702),
    ('docs/DIRECTION_A_G1_1_FORMAL_PLAN_v1.md',14663),
    ('scripts/run_direction_a_formal_f.py',45664),(OLD+'delivery_audit.json',60693),
    ('scripts/run_direction_a_formal_f.py',45664),
    ('docs/DIRECTION_A_PROTOCOL_FREEZE_v1.md',70665),
    ('scripts/run_direction_a_formal_f.py@offset14000',6000),
    ('docs/DIRECTION_A_PROTOCOL_FREEZE_v1.md@offset19000',14000)]
front=sum(n for p,n in discovery)+sum(r['bytes'] for r in reads)+(OUT/'summarize.py').stat().st_size
assert front<=524288
record=dict(baseline=BASE,authorization=AUTH,identity=identity,
    prior_once=dict(locator=BASE+':'+OLD+'delivery_audit.json#resources',
        resources={k:v for k,v in prior.items() if k not in ('actions','phases')},
        other_old_ledgers_added_again=False),operation_delta=delta,segment_upper=delta,
    joint_upper=joint,balances=balances,cost=cost,reads=reads,
    discovery_reads=[dict(path=p,bytes=n,origin='working tree at clean authorized HEAD') for p,n in discovery],
    metering=dict(front_cap=524288,front_used_upper=front,tail_cap=1048576,
        tail='1MiB reserved for final documents/JSON/hash readback, helper buffers, Git object identity/index/staging/commit and final verification; no full package scans',
        seconds='60s conservative all-program ceiling includes discovery, single arithmetic summary, document/hash/readback/Git tail and20s failure reserve; human reasoning excluded',
        scans='128 upper including17 discovery content reads,2 frozen inputs, identity queries/helper/readback/hash and Git tail',
        writes='256KiB cumulative ceiling includes discarded19558B helper draft, final helper/documents/JSON/hashes plus Git object/index tail; not final directory size',
        memory='256MiB conservative ceilings for shell/summary/Git; measured Python retained; inherited peaks use max'),
    measured=dict(summary_seconds_before_seal=time.perf_counter()-START,
        summary_windows_peak=memory.PeakWorkingSetSize,summary_cpu_proxy_peak=proxy),
    historical_references=dict(structural_complete=778,partial=0,not_started=0,
        cold_start_79_without_timeout=True,P_full_scope='FAIL',G1_1='not_closed',G1_3='formal_closed'),
    stopping_category='resource_plan_review_only',bias_results_computed=0,
    selfcheck_scope='bookkeeping identities/arithmetic only; no syntax check, CPU suite or event entry')
(OUT/'accounting.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
assert time.perf_counter()-START<20
print(json.dumps(dict(status='sealed_arithmetic',components=components,full_upper=full,coarse_full=coarse_full,coarse_main=coarse_main,signed_excess=full-limit,per_reference=[{k:r[k] for k in ('index','top8_sum','main_upper','coarse_main_upper','all20_message_bytes')} for r in per_reference],joint_upper=joint,balances=balances,
    messages=sum(r['all20_message_bytes'] for r in per_reference),front_used=front,
    summary_seconds=time.perf_counter()-START),ensure_ascii=False))
