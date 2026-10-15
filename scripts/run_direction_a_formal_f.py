"""One precommitted, metadata-only F entry and bounded evidence sealing.

prepare performs the only initial syntax/CPU suite. run is exclusive and cannot
resume. finalize only audits sealed bytes, adds tail costs, and writes handoff.
"""
import time
START = time.perf_counter()
import argparse
import ast
import io
import json
import subprocess
import sys
import traceback
import tracemalloc
import unittest
from decimal import Decimal
from fractions import Fraction as F
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.dont_write_bytecode = True
from direction_a.cost_m import normalized, sha, windows_peak, exact_b
from direction_a.formal_f import N, DELTA, IDS, SCENARIOS, ceil, probability, outcome, charge, classify
from direction_a.formal_f_policy import canonical, digest, invite, Consumer

OUT = ROOT/'artifacts/direction_a/phaseG1_1_formal_F_v1'
A = 'artifacts/direction_a/'
M = A+'phaseG1_1_cost_M_v1/'
OLD = A+'phaseG1_2_full_v1/'
BACK = A+'backbone_preparation_v1/'
SMOKE = A+'phaseG1_1_v1/'
BASE = '22c7418d40f62c81f2639e86d1b7a166a6898920'
AUTH = 'bbe939a2d8cf6ea14c7dfd18f96e24821a52ed3d'
UPSTREAM = 'd3a3bd712d6bb28283b59faff16e17e099debcb4'
ZERO = 'e3c3528722cd4c4f55f96b37182255a4ade961b8'
SMOKE_COMMIT = '54eb6e02f4630df82cfdeb1c352fd5e4520ea5be'
SOURCE = ['direction_a/formal_f.py','direction_a/formal_f_policy.py',
          'scripts/run_direction_a_formal_f.py','tests/test_direction_a_formal_f.py']
LIMITS = dict(seconds=300, writes=32*1024**2, metadata=8*1024**2,
              simulated_bytes=32*1024**3, scans=2048, attempts=800,
              windows=2*1024**3, cpu_proxy=512*1024**2,
              revisions=2, syntax_checks=2, CPU_suites=2, real_entries=1)
EXPECTED = ['input_checks.json','binding.json','mechanism.json','support.json',
            'plans.json','events.jsonl','replay_checks.json','coverage.json',
            'diagnostic_channel_audit.json','run_record.json','artifact_hashes.json',
            'seal_receipt.json']


def git(*args):
    return subprocess.check_output(['git',*args],cwd=ROOT)


class Ledger:
    def __init__(self, prior=None):
        # Discovery includes all shell reads, failed schema inspection, and listing.
        # Conservative upper envelopes (not traffic measurements) retain that cost.
        self.d = prior or dict(seconds=15.,writes=sum((ROOT/p).stat().st_size for p in SOURCE),
                               metadata=4*1024**2, scans=120,attempts=0,simulated_bytes=0,
                               windows=0,cpu_proxy=0, actions=[],phases={},
                               implementation_revisions=1,syntax_checks=1,CPU_suites=1,
                               discovery_accounting='15 s / 4 MiB / 120 scans upper envelopes, includes three full old-measurement schema reads and unsuccessful reads')
        self.started = time.perf_counter()

    def elapsed(self):
        return self.d['seconds'] + time.perf_counter()-self.started

    def guard(self, action, seconds=0, writes=0, metadata=0, scans=0, attempts=0, simulated_bytes=0, seal=False):
        proposed = dict(seconds=self.elapsed()+seconds+(0 if seal else 20),
                        writes=self.d['writes']+writes+(0 if seal else 2*1024**2),
                        metadata=self.d['metadata']+metadata,scans=self.d['scans']+scans,
                        attempts=self.d['attempts']+attempts,
                        simulated_bytes=self.d['simulated_bytes']+simulated_bytes)
        for k,v in proposed.items():
            if v > LIMITS[k]:
                raise RuntimeError('resource gate '+k+': '+str(v))
        self.d['windows'] = max(self.d['windows'],windows_peak())
        self.d['cpu_proxy'] = max(self.d['cpu_proxy'],tracemalloc.get_traced_memory()[1])
        for k in ('windows','cpu_proxy'):
            if self.d[k] > LIMITS[k]:
                raise RuntimeError('memory gate '+k)
        # Compact audit: action, elapsed, estimates seconds/write/metadata/scans/attempts/simulated,
        # then whether the fixed 20s/2MiB failure reserve is still held.
        self.d['actions'].append([action,round(self.elapsed(),6),seconds,writes,metadata,scans,
                                  attempts,simulated_bytes,not seal])

    def snapshot(self):
        return dict(self.d, seconds=self.elapsed())

    def save(self,name,obj):
        raw=canonical(obj)+b'\n'
        self.guard('write:'+name,writes=len(raw),seal=True)
        self.d['writes']+=len(raw)
        (OUT/name).write_bytes(raw)
        return dict(bytes=len(raw),sha256=sha(raw))

    def readback(self,path):
        self.guard('readback:'+path.name,metadata=path.stat().st_size,scans=1,seal=True)
        raw=path.read_bytes()
        self.d['metadata']+=len(raw)
        self.d['scans']+=1
        return raw


def prepare():
    tracemalloc.start()
    prior=None
    if OUT.exists():
        if (OUT/'entry.json').exists() or (OUT/'preparation_history_v1.json').exists():
            raise RuntimeError('preparation/entry limit; no overwriting')
        prior=json.loads((OUT/'preparation_ledger.json').read_bytes())
        prior['writes']+=(OUT/'preparation_ledger.json').stat().st_size+sum((ROOT/p).stat().st_size for p in SOURCE)
        prior['seconds']+=2  # previous preparation exit and subsequent bounded source edit commands
        prior['implementation_revisions']+=1;prior['syntax_checks']+=1;prior['CPU_suites']+=1
    l=Ledger(prior)
    if prior:
        history={}
        for name in ('preregistration.json','selfchecks.json','preparation_ledger.json'):
            raw=l.readback(OUT/name);history[name]=json.loads(raw)
        l.save('preparation_history_v1.json',history)
    for p in SOURCE:
        ast.parse((ROOT/p).read_text(encoding='utf-8'),filename=p)
    stream=io.StringIO()
    result=unittest.TextTestRunner(stream=stream,verbosity=2).run(
        unittest.defaultTestLoader.discover(str(ROOT/'tests'),pattern='test_direction_a_formal_f.py'))
    OUT.mkdir(parents=True,exist_ok=True)
    l.save('selfchecks.json',dict(passed=result.wasSuccessful(),tests=result.testsRun,log=stream.getvalue(),
         syntax_checks=l.d['syntax_checks'],CPU_suites=l.d['CPU_suites'],implementation_revisions=l.d['implementation_revisions'],torch_imported='torch' in sys.modules,
         real_samples=0,CUDA_initializations=0))
    if not result.wasSuccessful() or 'torch' in sys.modules:
        l.save('preparation_ledger.json',l.snapshot())
        raise RuntimeError(stream.getvalue())
    if git('rev-parse','HEAD').decode().strip()!=AUTH:
        raise RuntimeError('authorization mismatch')
    git('merge-base','--is-ancestor',BASE,AUTH)
    l.save('preregistration.json',dict(identity='G1.1-formal-F-v1',baseline=BASE,authorization_commit=AUTH,
        created_unix_ns=time.time_ns(),source_commit='HEAD at exclusive entry; verified tracked hashes below',
        sources={p:sha(normalized((ROOT/p).read_bytes())) for p in SOURCE},
        limits=LIMITS,entry_limit=1,retries=0,S1=2026102300,S2_registered_only=2026102400,
        S3_registered_only=2026102500,streams='PCG64(S1+1/+2/+3/+4): invitation/online/dropout/jitter',
        draw_order='32 attempts, sorted client_000..019, all20 draws each stream; shared across all12 trajectories',
        mechanism=dict(q='2/5',delta='16/5',grid=N,online='10*k<9*N',dropout='20*k<N',
                       D='s*(b/B)*(1/4+3*k/(2*N))',deadline='D<=delta',B='3938361000089474953/2500000000000000000'),
        order=['input_git_bindings','bootstrap40','exact_support4068','plans32',
               'four references manifest order / random,tail_slow,tail_fast / generate32 then replay32',
               'coverage_generate4','coverage_replay4','boundary2','isolation','seal','finalize_readonly_audit'],
        planned_attempts=778,main=384,replay=384,coverage=8,boundaries=2,
        estimates=dict(program_seconds=100,seal_seconds=20,writes=12*1024**2,
                       additional_metadata=4*1024**2,simulated_bytes_envelope=28536009765,
                       scans=900,windows=512*1024**2,cpu_proxy=128*1024**2),
        zero_operations=['training','model_forward','model_backward','encoding','class_gradient',
                         'validation_samples','test_samples','CUDA_initialization','model_updates'],
        original_packages={ZERO:A+'phase0_2_v1',SMOKE_COMMIT:SMOKE,UPSTREAM:[BACK,OLD],BASE:M},
        history='M delivery_audit only; P f4dd9f3 joint ledger; old G1.1/G1.2/P retained once, no borrowing',
        budgets_include='discovery, source/test/doc writes, checks, failures, replay, archive, readback and sealing tail'))
    l.save('preparation_ledger.json',l.snapshot())
    print(json.dumps(dict(status='prepared',tests=result.testsRun,seconds=l.elapsed())))


def run():
    tracemalloc.start()
    # Exclusive marker exists even if the run stops during initial validation.
    with (OUT/'entry.json').open('xb') as f:
        f.write(canonical(dict(entry=1,unix_ns=time.time_ns(),commit=git('rev-parse','HEAD').decode().strip()))+b'\n')
    prior=json.loads((OUT/'preparation_ledger.json').read_bytes())
    l=Ledger(prior)
    l.d['writes']+=(OUT/'preparation_ledger.json').stat().st_size+(OUT/'entry.json').stat().st_size
    inventory={f'{r}/{s}/{mode}/{a}':{} for r in range(4) for s in SCENARIOS
               for mode in ('generate','replay') for a in range(32)}
    inventory.update({f'coverage/{mode}/{a}':{} for mode in ('generate','replay') for a in range(4)})
    inventory.update({f'boundary/{a}':{} for a in range(2)})
    hashes={}; checks=[]; event_rows=[]; progress='input'; error=None; status='stopped'
    costs={k:0 for k in ('registration','reference_downlink','ordinary_state_return_preparation',
                        'gradient_preparation','effective_upload','W01_calls','W01_steps','W02_scans','W02_positions')}
    service=F(0); stage_started=time.perf_counter()

    def save(name,obj):
        hashes[name]=l.save(name,obj)

    def verified(path,commit,historical=None,decimal=False):
        size=(ROOT/path).stat().st_size
        l.guard('input:'+path,seconds=.3,metadata=size+4096,scans=3)
        # Git objects are the canonical source. Equality of tracked working content
        # is verified by Git, avoiding a second in-memory metadata copy.
        git('diff','--exit-code',commit,'--',path)
        actual=git('show',commit+':'+path);expected=actual
        l.d['metadata']+=len(actual);l.d['scans']+=3
        witness=None
        if historical:
            lf=normalized(expected)
            witness=next((label for label,raw in [('git',expected),('working',actual),('LF',lf),
                 ('CRLF',lf.replace(b'\n',b'\r\n')),('CR',lf.replace(b'\n',b'\r'))] if sha(raw)==historical),None)
            if witness is None:
                raise RuntimeError('historical hash has no newline-only witness '+path)
        checks.append(dict(path=path,commit=commit,read_origin='Git object; working Git content equal',normalized_sha256=sha(normalized(actual)),
                           historical_sha256=historical,newline_witness=witness))
        return json.loads(actual,parse_float=Decimal if decimal else float)

    def phase(name):
        nonlocal progress,stage_started
        now=time.perf_counter();l.d['phases'][progress]=l.d['phases'].get(progress,0)+now-stage_started
        progress=name;stage_started=now

    try:
        # Retain every pre-entry check and preregistration, including revision 1.
        for name in ('preregistration.json','selfchecks.json','preparation_ledger.json',
                     'preparation_history_v1.json','entry.json'):
            p=OUT/name
            if p.exists():
                raw=l.readback(p);hashes[name]=dict(bytes=len(raw),sha256=sha(raw))
        entry=json.loads((OUT/'entry.json').read_bytes());head=entry['commit']
        for ancestor in (BASE,AUTH):
            git('merge-base','--is-ancestor',ancestor,head)
        pre=verified((OUT/'preregistration.json').relative_to(ROOT).as_posix(),head)
        if pre['created_unix_ns']>=entry['unix_ns']:
            raise RuntimeError('preregistration must precede entry')
        for p,h in pre['sources'].items():
            raw=(ROOT/p).read_bytes();l.d['metadata']+=len(raw);l.d['scans']+=2
            if sha(normalized(raw))!=h or normalized(raw)!=normalized(git('show',head+':'+p)):
                raise RuntimeError('uncommitted source '+p)
        for commit,paths in [(ZERO,[A+'phase0_2_v1']), (SMOKE_COMMIT,[SMOKE]),
                             (UPSTREAM,[BACK,OLD]),(BASE,[M])]:
            l.guard('package_git_objects',seconds=2,scans=1)
            git('diff','--exit-code',commit,'--',*paths);l.d['scans']+=1
            checks.append(dict(package_paths=paths,git_content_comparison=commit,status='unchanged'))
        for p in ('docs/workflow/TO_EXECUTOR.md','docs/DIRECTION_A_G1_1_ADJUDICATION_v3.md',
                  'docs/DIRECTION_A_PROTOCOL_FREEZE_v1.md'):
            # Git object comparison includes CRLF conversion, and doesn't load unrelated document data.
            git('diff','--exit-code',AUTH,'--',p);l.d['scans']+=1
        manifest=verified(BACK+'manifest.json',UPSTREAM)
        config=verified(BACK+'generation_config.json',UPSTREAM,manifest['generation_config_sha256'])
        binding=verified(BACK+'task_binding.json',UPSTREAM,manifest['task_binding_sha256'])
        old=verified(OLD+'measurements.json',UPSTREAM,decimal=True)
        m=verified(M+'measurements.json',BASE)
        m_delivery=verified(M+'delivery_audit.json',BASE)
        reference_acceptance=verified(OLD+'reference_acceptance.json',UPSTREAM)
        speeds=verified(SMOKE+'speed_assignments.json',SMOKE_COMMIT)
        refs=manifest['references'];rows={};registrations={};tasks={};sources=[]
        if len(refs)!=4 or len(m['rows'])!=80 or len(old['references'])!=4:
            raise RuntimeError('reference/message cardinality')
        B=max(exact_b(row) for row in m['rows'])
        if str(B)!=m['B_seconds'] or str(B)!=pre['mechanism']['B']:
            raise RuntimeError('B mismatch')
        for ds in ('CIFAR10','CIFAR100'):
            cpath=binding[ds]['source_files']['counts.json']
            counts=verified(cpath['path'],ZERO,cpath['sha256'])
            reg=verified(SMOKE+'registration_'+ds+'.json',SMOKE_COMMIT)
            if reg['registered_ids']!=list(IDS) or not reg['all_registered']:
                raise RuntimeError('registration incomplete')
            if reg['task_identity']!=speeds[ds]['task_identity']:
                raise RuntimeError('task mismatch')
            task_bind=[]
            for c,msg in enumerate(reg['messages']):
                upload=msg['upload_utf8'].encode();ack=msg['ack_utf8'].encode()
                u=json.loads(upload);v=json.loads(ack)
                if not (sha(upload)==msg['upload_sha256']==v['received_upload_sha256']
                    and sha(ack)==msg['ack_sha256'] and v['registration_ok']
                    and u['client_id']==v['client_id']==msg['client_id']==IDS[c]
                    and u['task_identity']==reg['task_identity']
                    and u['n_ic']==counts['n_ic'][c] and u['N_c']==counts['N_c']
                    and u['a_ic']==counts['a_ic'][c]
                    and len(upload)==msg['upload_bytes'] and len(ack)==msg['ack_bytes']):
                    raise RuntimeError('ACK/count binding mismatch')
                # The original split hash is authenticated by the sealed upload.
                # Package Git equality proves unchanged index provenance, without copying data.json.
                task_bind.append(dict(client=IDS[c],task=u['task_identity'],split=u['train_split_hash'],
                    upload_sha256=sha(upload),ACK_sha256=sha(ack),count_row=c,source_files=u['source_task_sha256']))
            for name,value in binding[ds]['source_files'].items():
                if reg['source_file_sha256'][name]!=value['sha256']:
                    raise RuntimeError('split/count source identity')
            for s,assign in speeds[ds]['assignments'].items():
                if set(assign)!=set(IDS) or sorted(assign.values())!=[1]*10+[4]*10:
                    raise RuntimeError('speed map mismatch')
            registrations[ds]=task_bind;tasks[ds]=counts
            costs['registration']+=reg['registration_uplink_encoded_bytes']+reg['registration_downlink_encoded_bytes']
        if costs['registration']!=70757:
            raise RuntimeError('registration total')
        l.d['simulated_bytes']+=costs['registration']
        for ri,ref in enumerate(refs):
            rid=ref['reference_id'];ds=ref['dataset'];oldref=old['references'][ri]
            if oldref['reference_id']!=rid or oldref['state_before']!=ref['state_sha256'] or oldref['state_after']!=ref['state_sha256']:
                raise RuntimeError('reference state mismatch')
            for c in range(20):
                row=m['rows'][ri*20+c];oc=oldref['clients'][c]
                if not (row['status']=='complete' and row['task']==ref['task_identity']
                    and row['reference']==rid and row['client']==c==oc['client_id']
                    and row['old_message']==oc['message'] and row['steps']==5
                    and row['message_bytes']==oc['message']['bytes']
                    and all(F(row['old_W02_decimal_seconds'][k])==F(oc['cost_seconds'][k]) for k in ('encode','main_head','statistics'))
                    and F(row['b_seconds'])==exact_b(row) and F(row['L'])==exact_b(row)/B):
                    raise RuntimeError('M80 binding mismatch')
                row=dict(row,sample_count=oc['sample_count'],reference_bytes=oc['theoretical_reference_downlink_bytes'])
                if (ri,c) in rows:
                    raise RuntimeError('duplicate message')
                rows[ri,c]=row
            positive={(c,k,n) for c,ns in enumerate(tasks[ds]['n_ic']) for k,n in enumerate(ns) if n>0}
            from_old={(v['client_id'],int(k),v['n_ic']) for k,cl in oldref['provenance'].items() for v in cl['sources']}
            if positive!=from_old or len(positive)!=(85 if ds=='CIFAR10' else 593):
                raise RuntimeError('positive source mismatch')
        save('input_checks.json',dict(baseline=BASE,authorization=AUTH,source_commit=head,
            preregistration_precedes_entry=True,checks=checks,reference_acceptance_locator=OLD+'reference_acceptance.json',
            sample_accesses=0,CUDA_initializations=0,large_packages_loaded=0))
        save('binding.json',dict(bootstrap_order=0,attempts_start_order=1,registrations=registrations,
            references=refs,BN=config['BN'],transforms=config['transforms'],model=config['model'],
            reference_acceptance=reference_acceptance['references'],rows=[rows[k] for k in sorted(rows)],
            B=str(B),speed_assignments=speeds,split_proof='sealed upload hash + ACK + source_files + unchanged original Git package',
            history=dict(M_final=m_delivery,P_commit='f4dd9f3',P_key='joint_formal_accounting',
                         old_ledgers_retained=True,prior_costs_recharged=False)))
        phase('support')
        probs=[]
        for ri,ref in enumerate(refs):
            ds=ref['dataset']
            for s in SCENARIOS:
                for c in range(20):
                    p=probability(rows[ri,c]['L'],speeds[ds]['assignments'][s][IDS[c]])
                    pi=len(probs);probs.append(dict(reference=ri,scenario=s,client=c,**p))
                    for k,n in enumerate(tasks[ds]['n_ic'][c]):
                        if n>0:
                            sources.append([ri,s,c,k,n,pi])
        if len(sources)!=4068:
            raise RuntimeError('source scenarios not 4068')
        save('mechanism.json',dict(identity=pre['identity'],mechanism=pre['mechanism'],B=str(B),
            probability_formula='A=ceil(9N/10);H=N-ceil(N/20);K=clip(floor(N*x)+1,0,N);r=A*H*K/N^3;p=2*r/5',
            x='(delta/(s*L)-1/4)/(3/2)',lower_r=str(F(627,2000)-F(3,N)),
            lower_p=str(F(627,5000)-F(6,5*N)),continuous_error_r_bound=str(F(3,N)),
            continuous_error_p_bound=str(F(6,5*N)),finite_zero='observational insufficiency; never permanent absence'))
        save('support.json',dict(probabilities=probs,source_fields=['reference','scenario','client','class','n_ic','probability_index'],
            sources=sources,count=4068,reference_ids=[r['reference_id'] for r in refs],
            original_count_locator='binding.json#registrations and original counts n_ic[client][class]'))
        phase('plans')
        import numpy as np
        streams=[np.random.Generator(np.random.PCG64(2026102300+i)) for i in range(1,5)]
        plans=[]
        for a in range(32):
            plans.append(dict(attempt=a,invited=sorted(int(c) for c in streams[0].choice(20,8,replace=False)),
                U=[[int(k) for k in stream.integers(0,N,size=20,dtype=np.int64)] for stream in streams[1:]]))
        save('plans.json',dict(seed=2026102300,streams=[2026102301,2026102302,2026102303,2026102304],
            client_order=list(IDS),shared_across='all tasks/references/scenarios, no replay draws',attempts=plans,
            numpy_version=np.__version__,known_numpy_array_bytes=20*8*3))
        phase('events')
        replay=[];coverage=[];rejections=[]

        def step(ri,scenario,mode,a,round_id,plan,key,rational=False,L_override=None):
            nonlocal service
            # Bound eight worst-case dispatched clients before each action.
            ref=refs[ri];ds=ref['dataset'];mapping=speeds[ds]['assignments'][scenario]
            envelope=8*sum(max(rows[ri,c][f] for c in range(20)) for f in ('reference_bytes','return_bytes','message_bytes'))
            envelope+=8*(max(rows[ri,c]['return_bytes'] for c in range(20))+max(rows[ri,c]['message_bytes'] for c in range(20)))
            l.guard(key,seconds=.08,writes=9000,attempts=1,simulated_bytes=envelope)
            l.d['attempts']+=1;inventory[key]={'started':True}
            identity=dict(task=ref['task_identity'],mechanism='G1.1-formal-F-v1',seed=2026102300,
                          channel='coverage' if key.startswith('coverage/') else 'main',
                          reference=ref['reference_id'],scenario=scenario,attempt=a,round=round_id)
            chosen=invite([IDS[c] for c in plan['invited']],IDS)
            expected={};details=[];returned=[]
            for cid in chosen:
                c=IDS.index(cid);row=rows[ri,c]
                draws=[plan['U'][stream][c] for stream in range(3)]
                reason,duration=outcome(L_override or row['L'],mapping[cid],draws,rational=rational)
                token=digest(dict(identity,client=cid))[:24]
                if reason!='offline':
                    expected[cid]=(token,row['old_message']['sha256'])
                    charged=charge(row,row['reference_bytes'],reason=='returned')
                    for name,value in charged.items():
                        if name=='service_seconds':service+=F(value)
                        else:costs[name]+=value
                    l.d['simulated_bytes']+=sum(charged[k] for k in ('reference_downlink',
                        'ordinary_state_return_preparation','gradient_preparation','effective_upload'))
                details.append([c,reason,str(duration),token])
            consumer=Consumer(identity,IDS,expected)
            for c,reason,duration,token in details:
                if reason=='returned':
                    msg=dict(identity,client=IDS[c],token=token,payload=rows[ri,c]['old_message']['sha256'])
                    if consumer.accept(msg,F(duration)<=DELTA)!='accepted':
                        raise RuntimeError('valid return rejected')
                    returned.append(c)
            record=dict(key=key,reference=ri,scenario=scenario,mode=mode,attempt=a,round=round_id,
                channel=identity['channel'],
                round_after=round_id+int(bool(returned)),empty=not bool(returned),plan_attempt=plan['attempt'],
                plan_sha256=digest(plan),client_fields=['client','terminal','duration_fraction','token'],
                clients=details,returned=returned,terminal=True,simulated_time=str(DELTA),actual_updates=0)
            inventory[key]=dict(terminal=True,sha256=digest(record));event_rows.append(record)
            return record,consumer,identity

        for ri in range(4):
            for s in SCENARIOS:
                generated=[]
                for mode in ('generate','replay'):
                    rnd=0
                    for a,plan in enumerate(plans):
                        record,_,_=step(ri,s,mode,a,rnd,plan,f'{ri}/{s}/{mode}/{a}')
                        rnd=record['round_after']
                        neutral={k:v for k,v in record.items() if k not in ('key','mode')}
                        if mode=='generate':generated.append(digest(neutral))
                        elif generated[a]!=digest(neutral):raise RuntimeError('replay mismatch')
                    replay.append(dict(reference=ri,scenario=s,mode=mode,attempts=32,
                        final_round=rnd,simulated_time=str(32*DELTA),actual_updates=0,
                        trajectory_sha256=digest(generated),replay_equal=True))
        # Coverage is synthetic and separate from every main trajectory.
        fixture_plans=[]
        for a in range(4):
            u=[[0]*20,[N-1]*20,[0]*20]
            if a==0:
                u[0][1]=N-1;u[1][2]=0;u[2][3]=N-1
            elif a==1:u[0]=[N-1]*20
            elif a==2:u[1]=[0]*20
            fixture_plans.append(dict(attempt=a,invited=list(range(8)),U=u))
        # Use an original slow client in the L=1 synthetic workload fixture;
        # never mislabel this override as an observed M workload.
        slow=next(c for c in range(20) if speeds[refs[0]['dataset']]['assignments']['random'][IDS[c]]==4)
        fixture_plans[0]['U'][2][slow]=N-1
        fixture_plans[0]['invited']=sorted(set([slow]+list(range(7))))
        if len(fixture_plans[0]['invited'])<8:fixture_plans[0]['invited']=list(range(8))
        originals=[]
        for mode in ('generate','replay'):
            rnd=0
            for a,p in enumerate(fixture_plans):
                rec,consumer,identity=step(0,'random',mode,a,rnd,p,f'coverage/{mode}/{a}',L_override='1')
                rnd=rec['round_after'];neutral={k:v for k,v in rec.items() if k not in ('key','mode')}
                if mode=='generate':originals.append(digest(neutral))
                elif originals[a]!=digest(neutral):raise RuntimeError('coverage replay mismatch')
                coverage.append(dict(key=rec['key'],round=rec['round'],round_after=rnd,
                    empty=rec['empty'],terminals=[v[1] for v in rec['clients']]))
                if a==0 and mode=='generate':
                    c=rec['returned'][0];cid=IDS[c];token,payload=consumer.dispatched[cid]
                    msg=dict(identity,client=cid,token=token,payload=payload)
                    probes=[('wrong_reference',dict(msg,reference='wrong'),True,'identity'),
                            ('unregistered',dict(msg,client='unknown'),True,'unregistered'),
                            ('duplicate_token',msg,True,'duplicate_token'),
                            ('tampered',dict(msg,payload='bad'),True,'tampered'),
                            ('diagnostic_leak',dict(msg,p='1/2'),True,'schema')]
                    unused=next(cid for cid in IDS if cid not in consumer.dispatched)
                    probes.append(('undispatched',dict(msg,client=unused),True,'undispatched'))
                    fresh=Consumer(identity,IDS,consumer.dispatched)
                    probes.append(('late',msg,False,'late'))
                    for label,message,on_time,wanted in probes:
                        reason=(fresh if label=='late' else consumer).accept(message,on_time)
                        if reason!=wanted:raise RuntimeError('illegal return protection '+label)
                        rejections.append(dict(probe=label,reason=reason,message=message,accepted=False))
        boundary=[]
        for b in range(2):
            key=f'boundary/{b}';l.guard(key,seconds=.1,attempts=1,simulated_bytes=80000000)
            l.d['attempts']+=1;inventory[key]={'started':True}
            p=probability('1',4);K=p['K']
            tests=[dict(name='grid_before',u=[0,N-1,K-1],want='returned'),
                   dict(name='grid_after',u=[0,N-1,K],want='timeout'),
                   dict(name='online_before',u=[p['A']-1,N-1,0],want='returned'),
                   dict(name='online_after',u=[p['A'],N-1,0],want='offline'),
                   dict(name='drop_before',u=[0,N-p['H']-1,0],want='dropout'),
                   dict(name='drop_after',u=[0,N-p['H'],0],want='returned')] if b==0 else [
                   dict(name='rational_equality',u=['0','1/20','11/30'],want='returned'),
                   dict(name='rational_strict_online',u=['9/10','1/2','0'],want='offline')]
            results=[]
            for t in tests:
                result,d=outcome('1',4,t['u'],rational=b==1)
                if result!=t['want']:raise RuntimeError('boundary mismatch')
                if t['name']=='rational_equality' and d!=DELTA:raise RuntimeError('deadline equality')
                c=slow;row=rows[0,c]
                if result!='offline':
                    ch=charge(row,row['reference_bytes'],result=='returned')
                    for k,v in ch.items():
                        if k=='service_seconds':service+=F(v)
                        else:costs[k]+=v
                    l.d['simulated_bytes']+=sum(ch[k] for k in ('reference_downlink','ordinary_state_return_preparation','gradient_preparation','effective_upload'))
                results.append(dict(**t,result=result,D=str(d)))
            boundary.append(dict(key=key,synthetic=True,L='1',speed=4,grid=(N if b==0 else None),
                                 off_grid_rational_fixture=b==1,does_not_assert_grid_equality=True,checks=results))
            inventory[key]={'terminal':True,'sha256':digest(boundary[-1])}
        if l.d['attempts']!=778 or len(event_rows)!=776:raise RuntimeError('attempt cardinality')
        if not coverage[1]['empty'] or not coverage[2]['empty'] or coverage[1]['round']!=coverage[2]['round']:
            raise RuntimeError('empty round coverage')
        phase('archive')
        raw=b''.join(canonical(row)+b'\n' for row in event_rows)
        l.guard('events.jsonl',writes=len(raw),seconds=1)
        (OUT/'events.jsonl').write_bytes(raw);l.d['writes']+=len(raw)
        hashes['events.jsonl']=dict(bytes=len(raw),sha256=sha(raw))
        save('replay_checks.json',dict(trajectories=replay,main_generated=384,main_replayed=384,
             all_identical=True,actual_updates=0))
        save('coverage.json',dict(synthetic_only=True,L_override='1',reference=0,scenario='random',
            plans=fixture_plans,coverage=coverage,boundaries=boundary,rejections=rejections,
            attempts=10,all_rejected=True,replay_identical=True))
        tree=ast.parse((ROOT/'direction_a/formal_f_policy.py').read_text())
        imports=[n.module for n in ast.walk(tree) if isinstance(n,ast.ImportFrom)]
        if any('formal_f' in str(n) for n in imports):raise RuntimeError('policy diagnostic import')
        for n in ast.walk(tree):
            if isinstance(n,ast.Constant) and isinstance(n.value,str) and n.value in ('r','p','U','future_U'):
                raise RuntimeError('diagnostic consumption')
        save('diagnostic_channel_audit.json',dict(status='passed',policy='direction_a/formal_f_policy.py',
            policy_source_sha256=pre['sources']['direction_a/formal_f_policy.py'],imports=imports,
            invitation_inputs='planned eight IDs + immutable registered IDs only',
            return_inputs='identity,client,token,payload SHA,observed on_time only',
            diagnostic_inputs='support r/p, latent whole-client U, costs and durations retained only by simulator',
            prohibited_fields_rejected=True,actual_updates=0,physical_network=None))
        status='completed'
    except Exception:
        error=traceback.format_exc()
    finally:
        phase('seal')
        # Save all previously complete attempt records even on the first failure.
        if event_rows and 'events.jsonl' not in hashes:
            raw=b''.join(canonical(row)+b'\n' for row in event_rows)
            (OUT/'events.jsonl').write_bytes(raw);l.d['writes']+=len(raw)
            hashes['events.jsonl']=dict(bytes=len(raw),sha256=sha(raw))
        if error:
            save('failure.json',dict(error=error,stage=progress,input_checks=checks,
                 retained_records=len(event_rows),retry_permitted=False))
        counts=classify(inventory,('terminal','sha256'))
        if status=='completed' and (len(counts['complete'])!=778 or counts['partial'] or counts['not_started']):
            status='stopped';error='incomplete inventory'
        l.guard('seal readback and final snapshot',seconds=10,writes=200000,scans=40,seal=True)
        # Content readback is charged as logical metadata, including event archives.
        readback=[]
        for name,value in hashes.items():
            raw=l.readback(OUT/name)
            if len(raw)!=value['bytes'] or sha(raw)!=value['sha256']:
                status='stopped';error='seal readback mismatch '+name;break
            readback.append(name)
        run_record=dict(status=status,error=error,source_commit=git('rev-parse','HEAD').decode().strip(),
            counts=counts,inventory=inventory,simulated_costs=dict(costs,service_seconds=str(service)),
            actual_operations=dict(CUDA_initializations=0,training=0,forward=0,backward=0,encoding=0,
                class_gradients=0,validation_samples=0,test_samples=0,model_updates=0,physical_network=None),
            resources=l.snapshot(),numpy_array_proxy_bytes=480,torch_imported='torch' in sys.modules,
            stop_reason='all scheduled work completed' if status=='completed' else error,
            next_action='finalize sealed-byte receipt and delivery only; no simulation or retry',
            expected_evidence=EXPECTED)
        save('run_record.json',run_record)
        l.save('artifact_hashes.json',dict(algorithm='SHA256 exact binary bytes',artifacts=hashes,
            self_exclusion='hash index and seal/delivery receipts are outside their own hash domain'))
        l.save('seal_receipt.json',dict(status=status,readback=readback,readback_passed=error is None,
            artifact_index_sha256=sha((OUT/'artifact_hashes.json').read_bytes()),
            final_snapshot_tail_pending=True,resources=l.snapshot()))
        print(json.dumps(dict(status=status,error=error,attempts=l.d['attempts'],
            resources={k:v for k,v in l.snapshot().items() if k not in ('actions',)}),ensure_ascii=False))


def finalize():
    # No entry, input loading, plan generation or event evaluation is permitted here.
    tracemalloc.start()
    receipt=json.loads((OUT/'seal_receipt.json').read_bytes())
    l=Ledger(receipt['resources'])
    l.d['writes']+=(OUT/'seal_receipt.json').stat().st_size
    l.d['seconds']+=2  # conservative prior snapshot->process exit plus commit preparation tail
    run_record=json.loads((OUT/'run_record.json').read_bytes())
    l.d['metadata']+=(OUT/'seal_receipt.json').stat().st_size+(OUT/'run_record.json').stat().st_size
    l.d['scans']+=2
    index=json.loads((OUT/'artifact_hashes.json').read_bytes())
    l.d['metadata']+=(OUT/'artifact_hashes.json').stat().st_size;l.d['scans']+=1
    # Only final snapshots are reread; large sealed evidence already verified in run.
    run_hash=index['artifacts']['run_record.json']['sha256']
    if sha((OUT/'run_record.json').read_bytes())!=run_hash:
        raise RuntimeError('final run record altered')
    l.d['metadata']+=(OUT/'run_record.json').stat().st_size;l.d['scans']+=1
    l.guard('delivery handoff + final readback + Git commit tail',seconds=10,writes=100000,metadata=100000,scans=10,seal=True)
    fail=0 if run_record['status']=='completed' and receipt['readback_passed'] else 8
    handoff='''# 交付单：G1.1 正式事件F v1

- 对应任务单的基准 commit：`BASE_VALUE`
- 本次授权提交：`AUTH_VALUE`；源码预登记提交：`SOURCE_VALUE`；交付：见本提交。

## 做了什么（≤5条）
- 精确有理数机制、原ACK/计数/split/四参考与80条M工作量绑定。
- 主生成384/回放384、覆盖8/边界2，源码和预登记先提交后唯一入口。
- 仅元数据；本交付只申请G1.1裁决。

## 产出文件
- `artifacts/direction_a/phaseG1_1_formal_F_v1/`：input_checks、binding、mechanism、support、plans、events、replay_checks、coverage、diagnostic_channel_audit。
- 同目录selfchecks、run_record、artifact_hashes、seal_receipt、delivery_audit：检查、完整性、分账及最终尾耗。
- `scripts/run_direction_a_formal_f.py`、`direction_a/formal_f*.py`及相关CPU合成套件。

## 判据自评
|判据编号|结果 PASS/FAIL|证据位置 / 关键数字|
|---|---|---|
CRITERIA

## 实际资源消耗
- FINAL_RESOURCES
- 新训练/前反向/编码/梯度/validation/test/CUDA/模型更新均0；模拟与实耗独立，物理网络null。
- M只引用delivery_audit；P定位f4dd9f3联合账，旧账不重计；12轨迹不视作3研究重复。

## 阻塞
BLOCKER
## 异议
无。
## 需要审查者裁决的问题（≤3条）
- 仅申请正式G1.1结构验收；冷启动及多数端无超时事实保留，不宣称偏差或收益成立。
'''
    evidence=['input_checks / preregistration / entry / selfchecks','binding / support：4068正来源场景',
              'mechanism / plans / coverage：整数格点及单列有理数等号','events / replay_checks：384+384，逐条一致',
              'coverage：4+4+2，合计778 attempts','run_record.simulated_costs / diagnostic_channel_audit',
              'delivery_audit.resources：累计及封存尾耗','run_record：完整778、部分0、未开始0，completed']
    criteria='\n'.join(f'|{i}|'+('PASS' if fail==0 else 'FAIL')+f'|{e}|' for i,e in enumerate(evidence,1))
    tail=dict(seconds=10,writes=16384,metadata=100000,scans=10,
              note='conservative upper envelope for final snapshot/write/readback/git handoff tail; not added twice')
    totals=l.snapshot()
    for k in ('seconds','writes','metadata','scans'):totals[k]+=tail[k]
    for k in ('seconds','writes','metadata','scans','attempts','simulated_bytes','windows','cpu_proxy'):
        if totals[k]>LIMITS[k]:raise RuntimeError('final terminal bound '+k)
    resources=f"累计程序≤{totals['seconds']:.6f}秒 / 写入≤{totals['writes']} B / 元数据复制≤{totals['metadata']} B / 扫描≤{totals['scans']} / Windows峰{totals['windows']} B / CPU代理峰{totals['cpu_proxy']} B；模拟逻辑载荷{totals['simulated_bytes']} B。"
    handoff=handoff.replace('BASE_VALUE',BASE).replace('AUTH_VALUE',AUTH).replace('SOURCE_VALUE',run_record['source_commit']).replace('CRITERIA',criteria).replace('FINAL_RESOURCES',resources).replace('BLOCKER','无。' if fail==0 else str(run_record['error']))
    raw=handoff.encode('utf-8');path=ROOT/'docs/workflow/TO_REVIEWER.md';path.write_bytes(raw);l.d['writes']+=len(raw)
    l.save('delivery_audit.json',dict(status=run_record['status'],FAIL=fail,blocked=bool(fail),
        resources=totals,tail_upper_envelope=tail,run_record_sha256=run_hash,
        seal_receipt_sha256=sha((OUT/'seal_receipt.json').read_bytes()),
        handoff_sha256=sha(raw),handoff_lines=len(handoff.splitlines()),
        terminal_limits_passed=True,prior_costs_recounted=False,new_entries=0,
        seal_readback_passed=receipt['readback_passed'],final_snapshot_includes_tail=True))
    print(json.dumps(dict(status=run_record['status'],FAIL=fail,resources=resources),ensure_ascii=False))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['prepare','run','finalize'])
    action=parser.parse_args().action
    {'prepare':prepare,'run':run,'finalize':finalize}[action]()
