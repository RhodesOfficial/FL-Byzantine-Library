"""Read-only independent scalar reconstruction of frozen D2' event evidence."""
from collections import defaultdict
import json
import math
import hashlib
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.run_d2_prime_async_baseline import read,save
OUT=ROOT/'outputs/d2_prime_phase2_2_3_20261009'


def verify(unit, output_directory=None):
    out=OUT if output_directory is None else Path(output_directory)
    config=read(out/'preregister.json');directory=out/unit
    rows=read(directory/'tasks.json');order=read(directory/'terminal_order.json')
    import torch
    mapping=torch.load(out/'actual_feature_map.pt',weights_only=True)
    contract=dict(protocol=dict(identities=100,max_outstanding=40,capacity=20,lifetime=32.,
        max_staleness=64,clip_norm=.9701598816245317,eta_model=1.,
        specification='D2_PRIME_DESIGN:2.1/phase0.1+0.2-v1'),
        reference=config['reference_config'],feature_map=dict(buckets=mapping['buckets'].tolist(),
        signs=mapping['signs'].tolist(),bucket_count=32),
        budget=dict(window=33.,limit=.4125,specification='D2_PRIME_DESIGN:2.1.5/phase0.4-v1'))
    protocol_id=hashlib.sha256(json.dumps(contract,sort_keys=True).encode()).hexdigest()
    assert all(r['config_id']==protocol_id for r in rows)
    events=[json.loads(line) for line in (directory/'events.jsonl').read_text().splitlines()]
    source={0:dict(mu=[0.]*33,sigma=[.25]*33,evidence=0.)}
    previous=source[0];version=0;history=[];maximum=0.;terminals=[]
    by_id={r['task_id']:r for r in rows}
    def compare(a,b):
        nonlocal maximum
        assert len(a)==len(b)
        errors=[abs(x-y) for x,y in zip(a,b)]
        maximum=max(maximum,max(errors,default=0.))
        assert all(e<=1e-10+1e-8*abs(y) for e,y in zip(errors,b))
    def normal(state):
        return [x/math.sqrt(33) for x in state['mu']+state['sigma']]+[state['evidence']]
    def median(values):
        a=sorted(values);return (a[(len(a)-1)//2]+a[len(a)//2])/2
    for event in events:
        assert event['terminal_task_ids']==sorted(event['terminal_task_ids'])
        assert not set(terminals).intersection(event['terminal_task_ids'])
        terminals+=event['terminal_task_ids']
        if event['kind']!='commit':continue
        state=event['event']['before'];compare(normal(state),normal(previous))
        proposals=event['event']['proposals'];cold=None
        if len(proposals)>=3:
            centers=[median([p['feature'][r] for p in proposals]) for r in range(33)]
            scales=[min(1.,max(.05,median([abs(p['feature'][r]-centers[r]) for p in proposals]))) for r in range(33)]
            cold=(centers,scales)
            compare(event['event']['cold']['center'],centers);compare(event['event']['cold']['scale'],scales)
        else:assert event['event']['cold'] is None
        receipts={r['task_id']:r for r in event['receipts']};disp=[0.]*67
        for p in proposals:
            src=source[p['source_version']];x=p['feature']
            if src['evidence']>=.5:
                z=math.sqrt(math.fsum((v-m)**2/(s*s+(.1*(1-src['evidence']))**2)
                    for v,m,s in zip(x,src['mu'],src['sigma']))/33);path='source'
            elif cold:
                z=math.sqrt(math.fsum(((v-m)/s)**2 for v,m,s in zip(x,*cold))/33);path='cold'
            else:
                assert p['g'] is None and p['path']=='waiting';continue
            cut=config['reference_config']['z_cut']
            g=(1-(z/cut)**2)**2 if z<cut else 0.
            compare([p['z'],p['g']],[z,g]);assert path==p['path']
            h=1/(1+version-p['source_version'])
            compare([p['h'],p['a0'],p['b0']],[h,h*g/20,.1*h*g/20] if g else [h,0.,0.])
            if g<=0:
                assert p['task_id'] not in receipts;continue
            scale=[min(1.,max(.05,abs(v-m))) for v,m in zip(x,state['mu'])]
            target=[v/math.sqrt(33) for v in x+scale]+[1.]
            d=[v-r for v,r in zip(target,normal(state))]
            norm=math.sqrt(math.fsum(v*v for v in d));v=[a*min(1.,1/norm) if norm else a for a in d]
            compare(p['scale_target'],scale);compare(p['direction'],v)
            r=receipts[p['task_id']]
            spent=math.fsum(s['q'] for s in history if s['identity']==p['identity'] and event['at']-33<s['at']<=event['at'])
            remaining=max(0.,.4125-spent);nom=.055*h*g
            a=min(h*g/20,remaining/1.1);b=.1*a
            compare([r['a'],r['b'],r['q']],[a,b,a+b])
            assert r['q']==r['a']+r['b'] and r['identity']==by_id[p['task_id']]['identity']
            disp=[total+r['b']*direction for total,direction in zip(disp,v)]
        compare(event['reference_displacement'],disp)
        after=[r+v for r,v in zip(normal(state),disp)]
        previous=dict(mu=[v*math.sqrt(33) for v in after[:33]],
                      sigma=[v*math.sqrt(33) for v in after[33:66]],evidence=after[-1])
        if receipts:
            version+=1;source[version]=previous
        assert event['version']==version
        compare([event['reference_evidence']],[previous['evidence']])
        history.extend(event['receipts'])
    assert terminals==order and len(set(terminals))==len(rows)
    assert history==[{k:r[k] for k in ('task_id','identity','at','a','b','q')} for r in read(directory/'ledger.json')]
    assert len(history)==sum(r['state']=='consumed' for r in rows)
    import numpy as np
    rngs=[np.random.RandomState(2801+c) for c in range(100)]
    for r in read(directory/'dispatch_delays.json'):
        expected=int(rngs[r['identity']].choice([6,7,8] if r['identity'] in config['slow_ids'] else [1,2,3]))
        assert r['delay']==expected
        row=by_id[r['task_id']]
        assert row['first_arrival_at']==row['issued_at']+expected
    # Independent integer scheduler/trigger replay using durable observations.
    # No formal Server, TaskProtocol or budget implementation is invoked.
    dispatch=np.random.RandomState(801);live={};fifo=[];paid=[];issued_count=0
    for tick in range(int(result_at(events))+1):
        tick_events=[e for e in events if e['at']==tick]
        expiry=tick_events[0]
        assert expiry['kind']=='expiry'
        for tid in expiry['terminal_task_ids']:
            live.pop(by_id[tid]['identity']);fifo=[i for i in fifo if i!=tid]
        arrived=sorted(r['task_id'] for r in rows if r['first_arrival_at']==tick)
        fifo.extend(tid for tid in arrived if by_id[tid]['identity'] in live)
        for e in tick_events[1:]:
            assert e['kind']=='commit'
            selected=fifo[:20]
            assert selected
            tail=issued_count==len(rows) and all(by_id[tid]['first_arrival_at']<=tick for tid in live.values())
            assert len(selected)==20 or tick-min(by_id[i]['first_arrival_at'] for i in selected)>=8 or tail
            eligible=[i for i in selected if math.fsum(r['q'] for r in paid
                if r['identity']==by_id[i]['identity'] and tick-33<r['at']<=tick)<.4125]
            assert sorted(eligible)==[p['task_id'] for p in e['event']['proposals']]
            paid.extend(e['receipts'])
            for tid in e['terminal_task_ids']:
                live.pop(by_id[tid]['identity']);fifo=[i for i in fifo if i!=tid]
        count=min(len(rows)-issued_count,40-len(live))
        expected=sorted(dispatch.choice([c for c in range(100) if c not in live],count,replace=False).tolist()) if count else []
        issued=sorted((r for r in rows if r['issued_at']==tick),key=lambda r:r['task_id'])
        assert [r['identity'] for r in issued]==expected
        current=tick_events[-1]['version']
        for row in issued:
            assert row['task_id']==issued_count and row['source_version']==current
            live[row['identity']]=row['task_id'];issued_count+=1
        assert len(live)<=40
    assert issued_count==len(rows) and not live and not fifo
    result=read(directory/'result.json');curves=read(directory/'class_curves.json')
    assert all(0<=c['offset']<=39 and c['actual']==c['target']+c['offset'] for c in curves)
    assert all(c['M']==sum(c['class_correct'])/5000 for c in curves)
    if unit=='full':assert abs(sum(c['M'] for c in curves[-5:])/5-result['M'])<1e-15
    return dict(unit=unit,independent_event_math=True,source_snapshots_reconstructed=version+1,
        protocol_config_id=protocol_id,
        terminal_order_exact=True,delay_rng_streams_exact=True,independent_dispatch_FIFO_gate=True,receipt_count=len(history),
        maximum_scalar_reference_error=maximum,evaluation_offsets=[c['offset'] for c in curves[1:]])


def result_at(events):
    return max(e['at'] for e in events)


if __name__=='__main__':
    result=[verify(unit) for unit in ('smoke','full')]
    save(OUT/'independent_verification.json',result)
    print(json.dumps(result,indent=2))
