"""Independent durable-history windows and Q5 progress/coverage diagnostics."""
import math
from collections import Counter


def summarize(rows, order, events, slow_ids, baseline_batches):
    assert len(order)==len(rows)==len(set(order))
    by_id={r['task_id']:r for r in rows}
    assert set(by_id)==set(order)
    ledger=[r for e in events for r in e.get('receipts',[])]
    assert len(ledger)==len({r['task_id'] for r in ledger})
    assert {r['task_id'] for r in ledger}=={r['task_id'] for r in rows if r['state']=='consumed'}
    # Independent O(n^2) sums, no production RollingBudget/audit_history calls.
    maxima=[]
    for cid in range(100):
        group=[r for r in ledger if r['identity']==cid]
        maximum=max((math.fsum(r['q'] for r in group if t-33<r['at']<=t)
                     for t in {r['at'] for r in group}),default=0.)
        if maximum>.4125 and not math.isclose(maximum,.4125,rel_tol=1e-12,abs_tol=0.):
            raise ValueError('material historical overspend')
        maxima.append(maximum)
    for r in ledger:
        assert r['q']==r['a']+r['b'] and math.isclose(r['b'],.1*r['a'],rel_tol=1e-12,abs_tol=1e-15)
        row=by_id[r['task_id']]
        assert r['identity']==row['identity'] and r['a']==row['a'] and r['b']==row['b']

    def nominal(r):
        ell=r['staleness_arrival'] if r['first_arrival_at'] is not None else r['staleness_terminal']
        assert ell is not None and ell>=0
        return 1/(20*(1+ell))

    retention={}
    for name,slow in (('fast',False),('slow',True)):
        group=[r for r in rows if (r['identity'] in slow_ids)==slow]
        n=math.fsum(nominal(r) for r in group);a=math.fsum(r['a'] for r in group)
        retention[name]=dict(count=len(group),actual=a,nominal=n,r=a/n if n else None)
    fast=retention['fast']['r'];slow=retention['slow']['r']
    retention['R_slow']=slow/fast if fast and slow is not None else None
    segments=[]
    if len(rows)==12000:
        for j in range(5):
            lo,hi=j*2400,(j+1)*2400
            group=[by_id[i] for i in order[lo:hi]]
            a=math.fsum(r['a'] for r in group);n=math.fsum(nominal(r) for r in group)
            covered=[e for e in events if e['kind']=='commit' and e['terminated_after']>lo and e['terminated_before']<hi]
            v=math.fsum(e['checks']['delta_norm'] for e in covered)
            baseline_v=math.fsum(b['checks']['delta_norm'] for b in baseline_batches
                                if any(lo<t+1<=hi for t in b['task_ids']))
            segments.append(dict(segment=j+1,start=lo+1,end=hi,A=a,N=n,P=a/n,V=v,
                baseline_V=baseline_v,cross_boundary_events=[e['attempt'] for e in covered
                    if e['terminated_before']<lo or e['terminated_after']>hi]))
    ready=next((dict(at=e['at'],version=e['version'],terminated=e['terminated_after'])
                for e in events if e['ready']),None)
    latter=[by_id[i] for i in order[len(order)//2:]]
    scored=[r for r in latter if r['ever_scored']]
    source=[r for r in scored if r['source_scored']]
    coverage=len(source)/len(scored) if scored else None
    proposals=[p for e in events for p in e.get('event',{}).get('proposals',[])]
    waits=[w for e in events for w in e.get('waiting',[])]
    norms={}
    groups={'all':rows,'fast':[r for r in rows if r['identity'] not in slow_ids],
            'slow':[r for r in rows if r['identity'] in slow_ids]}
    for state in ('consumed','rejected','expired'):groups[state]=[r for r in rows if r['state']==state]
    for axis in ('staleness_arrival','staleness_commit'):
        for lo,hi in ((0,0),(1,1),(2,4),(5,8),(9,16),(17,64)):
            groups[f'{axis}_{lo}-{hi}']=[r for r in rows if r.get(axis) is not None and lo<=r[axis]<=hi]
    for name,group in groups.items():
        observed=[r for r in group if r['raw_norm'] is not None]
        norms[name]=dict(tasks=len(group),observed=len(observed),
            fraction_clipped=sum(r['raw_norm']>.9701598816245317 for r in observed)/len(observed) if observed else None,
            mean_clip_scale=math.fsum(r['clip_scale'] for r in observed)/len(observed) if observed else None)
    return dict(terminal_counts=dict(Counter(r['state'] for r in rows)),retention=retention,segments=segments,
        first_ready=ready,ready_sources_issued=sum(r['source_ready'] for r in rows),
        latter_unique_scored=len(scored),latter_unique_source=len(source),latter_source_fraction=coverage,
        latter_unscored=len(latter)-len(scored),proposal_paths=dict(Counter(p['path'] for p in proposals)),
        waiting_attempt_reasons=dict(Counter(w[1] for w in waits)),
        event_source_fraction=sum(any(p['path']=='source' for p in e.get('event',{}).get('proposals',[]))
                                  for e in events)/max(1,sum(e['kind']=='commit' for e in events)),
        minimum_g=min((p['g'] for p in proposals if p['g'] is not None),default=None),
        clip_groups=norms,per_identity_historical_max_fee=maxima,independent_history_ok=True)
