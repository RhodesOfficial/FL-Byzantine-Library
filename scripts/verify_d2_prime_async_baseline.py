"""Independent integer scheduler and scalar offline oracle; no model training.

Scheduler/calibration oracles do not import tested decision implementations.
Fixed-entry fixtures invoke the adapter with hand-written constant references.
"""
import hashlib
import json
from fractions import Fraction
from pathlib import Path
import sys
from types import SimpleNamespace

import numpy as np

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'outputs/d2_prime_phase2_1_async_20261009'


def read(path):return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def percentile(values,p):
    ordered=sorted(values)
    x=(len(ordered)-1)*p
    lo=int(x);hi=min(lo+1,len(ordered)-1)
    return ordered[lo]+(x-lo)*(ordered[hi]-ordered[lo])


def scheduler_oracle(limit,slow):
    dispatch=np.random.RandomState(801)
    delays=[np.random.RandomState(2801+c) for c in range(100)]
    tasks,live,queue,fifo,batches={},{},{},[],[]
    tick=version=0
    def expire():
        nonlocal fifo
        for tid in list(live.values()):
            r=tasks[tid]
            if tick>=r['expires_at'] or version-r['source_version']>64:
                r.update(state='expired',terminal_at=tick,terminal_version=version)
                del live[r['identity']]
                fifo=[x for x in fifo if x!=tid]
    while True:
        expire()
        for tid in sorted([i for i,at in queue.items() if at==tick]):
            del queue[tid]
            r=tasks[tid]
            if r['state']=='issued':
                r.update(state='arrived',arrived_at=tick,arrival_version=version,
                         staleness_arrival=version-r['source_version'])
                fifo.append(tid)
        while True:
            expire()
            full=len(fifo)>=20
            tail=len(tasks)==limit and all(r['state']!='issued' for r in tasks.values())
            if not fifo or (not full and not tail and tick-tasks[fifo[0]]['arrived_at']<8):break
            chunk=fifo[:20];fifo=fifo[20:]
            lags=[version-tasks[i]['source_version'] for i in chunk]
            batches.append(dict(at=tick,version_before=version,version_after=version+1,
                task_ids=chunk,client_ids=[tasks[i]['identity'] for i in chunk],
                source_versions=[tasks[i]['source_version'] for i in chunk],staleness_commit=lags,
                batch_size=len(chunk),reason='full' if full else 'tail' if tail else 'timeout'))
            version+=1
            for i,lag in zip(chunk,lags):
                r=tasks[i]
                r.update(state='consumed',terminal_at=tick,terminal_version=version,staleness_commit=lag)
                del live[r['identity']]
        count=min(limit-len(tasks),40-len(live))
        if count:
            free=sorted(set(range(100))-set(live))
            chosen=sorted(dispatch.choice(free,count,replace=False).tolist())
            for cid in chosen:
                tid=len(tasks)
                delay=int(delays[cid].choice([6,7,8] if cid in slow else [1,2,3]))
                tasks[tid]=dict(task_id=tid,identity=cid,source_version=version,issued_at=tick,
                    expires_at=tick+32,state='issued',expected_delay=delay)
                live[cid]=tid;queue[tid]=tick+delay
        if len(tasks)==limit and not live and not queue:break
        tick+=1
        assert tick<limit*32+32
    return tasks,batches,tick


def verify(name):
    config=read(OUT/'preregister.json');directory=OUT/name
    result=read(directory/'result.json');rows=read(directory/'tasks.json')
    observed_batches=[json.loads(line) for line in (directory/'batches.jsonl').read_text().splitlines()]
    expected,batches,tick=scheduler_oracle(result['task_limit'],set(config['slow_ids']))
    assert len(rows)==len(expected) and len(batches)==len(observed_batches)
    fields=['task_id','identity','source_version','issued_at','expires_at','state','arrived_at',
            'arrival_version','staleness_arrival','terminal_at','terminal_version','staleness_commit']
    for r in rows:
        e=expected[r['task_id']]
        assert r['config_id']==config['configuration_hash']
        for k in fields:assert r.get(k)==e.get(k),(name,r['task_id'],k,r.get(k),e.get(k))
        assert r['first_packet_at']==e['issued_at']+e['expected_delay']
        if r['state']=='consumed' and result['method']=='avg':
            assert abs(r['actual_coefficient']-1/(20*(1+e['staleness_commit'])))<1e-15
    for actual,expected_batch in zip(observed_batches,batches):
        for k,v in expected_batch.items():assert actual[k]==v,(name,k)
        assert all(actual['checks'][k] for k in ('layer1_pass','layer2_pass','writeback_exact'))
        assert any(a>0 for a in actual['actual_coefficients'])
        for i,tid in enumerate(actual['task_ids']):
            assert rows[tid]['actual_coefficient']==actual['actual_coefficients'][i]
        if result['method']=='rfa':
            binding=actual['rfa_layer']
            assert binding['semantics']=='rfa_final_mix_v1'
            assert binding['rfa_call_id']==actual['batch_id']+1
            for i,entry in enumerate(binding['clients']):
                assert entry['client_id']==actual['client_ids'][i]
                w=entry['weight'];beta=binding['final_betas'][i]
                assert abs(w-beta/binding['denominator'])<1e-6
                oracle_a=len(actual['task_ids'])/20*w/(1+actual['staleness_commit'][i])
                assert abs(oracle_a-actual['actual_coefficients'][i])<1e-15
    assert result['simulated_time']==tick and result['model_version']==len(batches)
    data=read(Path(config['task'])/'data.json');names=data['client_names']
    volumes=[len(data[names[r['identity']]]['data']) for r in rows]
    assert result['work']==dict(tasks=len(rows),minibatches=sum((n+63)//64 for n in volumes),examples=sum(volumes))
    curves=read(directory/'class_curves.json')
    assert curves['class_total']==[500]*10
    evidence=dict(unit=name,tasks=len(rows),independent_scheduler_matches=True,
                  versions=len(batches),ticks=tick,independent_work_matches=True)
    if name.startswith('full'):
        assert curves['terminated_tasks']==[0,10400,10800,11200,11600,12000]
        M=sum(Fraction(sum(c),5000) for c in curves['class_correct'][-5:])/5
        assert abs(float(M)-result['M'])<1e-12
        assert M>Fraction(3,20)
        evidence.update(M_exact=str(M),M=float(M),M_above_floor=True)
    return evidence


def verify_calibration():
    rows=read(OUT/'full_avg/tasks.json');observed=read(OUT/'full_avg/offline_H_beta.json')
    times=[[r['terminal_at'] for r in rows if r['identity']==cid and r['state']=='consumed']
           for cid in range(100)]
    gaps=[b-a for ts in times for a,b in zip(sorted(ts),sorted(ts)[1:]) if b>a]
    assert gaps,'evidence insufficient: no positive commit intervals'
    H=percentile(gaps,.95)
    maxima=[]
    for cid in range(100):
        group=[r for r in rows if r['identity']==cid and r['state']=='consumed']
        # Independent O(n^2) exact sums; no sliding-deque recurrence from production.
        maxima.append(max((sum(Fraction(11,200*(1+r['staleness_commit'])) for r in group
                               if at-H<r['terminal_at']<=at) for at in times[cid]),default=Fraction(0)))
    beta=percentile([float(v) for v in maxima],.95)
    assert abs(H-observed['H'])<1e-12 and abs(beta-observed['beta'])<1e-12
    assert observed['evidence_sufficient'] and len(observed['per_identity'])==100
    return dict(H=H,beta=beta,positive_intervals=len(gaps),all_100_identities=True,
                independent_sorted_quantile_and_rational_window_match=True)


def fixed_entry_checks():
    """Drive the actual new receive/drain/carrier seam using native timed packets.

    No dataset, forward, backward or optimizer. Hand-written scalar references.
    The full normal trajectory happened to have no two-batch ticks or short tails,
    so these cases are covered here at the formal K=20.
    """
    sys.path[:0]=[str(ROOT),str(ROOT/'easyFL')]
    import torch
    from flgo.simulator.base import ElemClock
    from flgo_byzantine.async_baseline_algorithm import Server
    from flgo_byzantine.async_baseline_state import BaselineState,DeliveredReply
    class Carrier(torch.nn.Module):
        def __init__(self,value):
            super().__init__();self.theta=torch.nn.Parameter(torch.tensor([value],device='cuda'))
    def server(method,value,limit):
        s=object.__new__(Server)
        s.model=Carrier(value);s.baseline=BaselineState(s.model.theta.detach(),method,'entry-fixed')
        s.task_limit=limit;s.eval_points=[];s.evaluated=[];s.current_round=0
        s.gv=SimpleNamespace(clock=ElemClock());s.records=[];s.on_batch=s.records.append
        return s
    def schedule(s,t,local,at):
        s.gv.clock.put({'reply':DeliveredReply(t.task_id,t.identity,t.source_version,torch.tensor([local])),
                        '__cid':t.identity,'__t':at},at)
    def harvest(s,at):
        s.gv.clock.step(at-s.gv.clock.current_time)
        s.baseline.expire(at)
        pkgs=s.gv.clock.get_sofar()
        values={k:[p[k] for p in pkgs] for k in ('reply','__cid','__t')}
        s._receive(values);s._drain()
    evidence=[]
    for method in ('avg','rfa'):
        s=server(method,100.,80)
        tickets=[s.baseline.issue(c) for c in range(40)]
        for t in reversed(tickets):schedule(s,t,80.,1)
        assert s.model.theta.item()==100. and all(r['raw_norm'] is None for r in s.baseline.tasks.values())
        harvest(s,1)
        assert s.model.theta.item()==70.  # First batch -20; second same-tick batch -10.
        assert [r['version_before'] for r in s.records]==[0,1]
        assert s.records[1]['staleness_commit']==[1]*20
        assert s.records[0]['task_ids']==list(range(20))
        assert s.records[1]['task_ids']==list(range(20,40))
        mixed=server(method,100.,50)
        old=[mixed.baseline.issue(c) for c in range(40)]
        for t in old[:20]:schedule(mixed,t,80.,1)
        harvest(mixed,1)
        new=[mixed.baseline.issue(c) for c in range(10)]
        for t in old[20:30]:schedule(mixed,t,80.,2)
        for t in new:schedule(mixed,t,70.,2)
        for t in old[30:]:schedule(mixed,t,80.,32)
        harvest(mixed,2)
        assert mixed.model.theta.item()==70.  # old10*.025*20 + new10*.05*10 = 10
        assert mixed.records[-1]['source_versions']==[0]*10+[1]*10
        harvest(mixed,32)
        assert mixed.model.theta.item()==70.
        assert all(mixed.baseline.tasks[t.task_id]['state']=='expired' for t in old[30:])
        assert all(mixed.baseline.tasks[t.task_id]['raw_norm']==20. for t in old[30:])
        tail=server(method,10.,3)
        for cid in range(3):schedule(tail,tail.baseline.issue(cid),6.,1)
        harvest(tail,1)
        assert torch.equal(tail.model.theta.detach(),torch.tensor([9.4],device='cuda'))
        assert tail.records[0]['reason']=='tail' and tail.records[0]['batch_size']==3
        timeout=server(method,10.,100)
        schedule(timeout,timeout.baseline.issue(0),6.,1)
        harvest(timeout,1);harvest(timeout,8)
        assert timeout.model.theta.item()==10. and not timeout.records
        harvest(timeout,9)
        assert torch.equal(timeout.model.theta.detach(),torch.tensor([9.8],device='cuda'))
        assert timeout.records[0]['reason']=='timeout'
        assert all(r['checks']['writeback_exact'] for x in (s,mixed,tail,timeout) for r in x.records)
        evidence.append(dict(method=method,K=20,two_batches_same_tick_model=70.,mixed_source_model=70.,
            expired_on_tick32=10,late_raw_norm=20.,tail3_model=float(tail.model.theta.item()),
            timeout_wait8_model=float(timeout.model.theta.item()),actual_GPU_float32_writeback=True,
            native_ElemClock_order_and_no_future_read=True,real_training_tasks=0))
    return evidence


if __name__=='__main__':
    config=read(OUT/'preregister.json')
    for p,h in config['source_sha256'].items():
        assert hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h,p
    result={'units':[verify(n) for n in ('smoke_avg','smoke_rfa','full_avg','full_rfa')],
            'calibration':verify_calibration(),'fixed_native_entry':fixed_entry_checks()}
    (OUT/'independent_verification.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,indent=2))
