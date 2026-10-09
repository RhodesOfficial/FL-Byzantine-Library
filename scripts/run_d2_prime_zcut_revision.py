"""One authorized z_cut=6 revision; original output is always read-only."""
import argparse
import copy
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import shutil
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'easyFL'),str(ROOT/'tests')]
from scripts.run_d2_prime_async_baseline import read,save,digest,object_digest
OLD=ROOT/'outputs/d2_prime_phase2_2_3_20261009'
OUT=ROOT/'outputs/d2_prime_phase2_2_3_zcut6_20261009'
AUTHORITY='docs/D2_PRIME_PHASE2_2_3_FAILURE_RULING.md'


def preserve_check():
    records=read(OUT/'preserved_original.json')
    for r in records:assert digest(ROOT/r['path'])==r['sha256'],r['path']
    actual={str(p.relative_to(ROOT)) for p in OLD.rglob('*') if p.is_file()}
    expected={r['path'] for r in records if Path(r['path']).is_relative_to(OLD.relative_to(ROOT))}
    assert actual==expected,'old evidence inventory changed'
    return len(actual)


def prepare():
    assert not (OUT/'preregister.json').exists()
    preserve_check()
    old=read(OLD/'preregister.json');config=copy.deepcopy(old)
    config['reference_config']['z_cut']=6.
    metadata=('registered_at','source_sha256','configuration_hash')
    effective=lambda c:{k:v for k,v in c.items() if k not in metadata}
    expected=effective(old);expected['reference_config']=dict(expected['reference_config'],z_cut=6.)
    assert effective(config)==expected
    changed=[p for p,h in old['source_sha256'].items() if digest(ROOT/p)!=h]
    assert set(changed)=={'flgo_byzantine/formal_d2_prime_algorithm.py','scripts/run_d2_prime_formal.py'}
    config['registered_at']=datetime.now(timezone.utc).isoformat()
    paths=list(old['source_sha256'])+[AUTHORITY,'scripts/verify_d2_prime_formal.py',
        'scripts/run_d2_prime_zcut_revision.py','tests/test_d2_prime_zcut_revision.py']
    config['source_sha256']={p:digest(ROOT/p) for p in paths}
    config.pop('configuration_hash')
    config['configuration_hash']=object_digest(config)
    shutil.copyfile(OLD/'actual_feature_map.pt',OUT/'actual_feature_map.pt')
    assert digest(OUT/'actual_feature_map.pt')==old['feature_map']['sha256']
    save(OUT/'preregister.json',config)
    save(OUT/'revision_registration.json',dict(authority=dict(path=AUTHORITY,sha256=digest(ROOT/AUTHORITY)),
        registered_at=config['registered_at'],old_configuration_hash=old['configuration_hash'],
        new_configuration_hash=config['configuration_hash'],old_effective_hash=object_digest(effective(old)),
        new_effective_hash=object_digest(effective(config)),metadata_excluded=list(metadata),
        effective_diff=[dict(path='reference_config.z_cut',old=3.,new=6.)],
        unchanged_effective_configuration={k:v for k,v in effective(old).items() if k!='reference_config'},
        unchanged_reference_parameters={k:v for k,v in old['reference_config'].items() if k!='z_cut'},
        affected_checks=['cold/source score boundaries','dual coefficients','reference invariants',
                         'shared budget/expiry','formal option wiring','old default regressions'],
        hard_gates=dict(M=.48876,R_slow=.8,S2_S5_P=.1,ready_by=2400,latter_source=.8,
                        engineering='all numerical/protocol/budget checks; no full-segment stall'),
        diagnostic_support=dict(latter_four_G_min=.85,latter_four_A_min=.85,not_a_hard_gate=True),
        diagnostic_unit='unique trained terminal task_id, ordered in five 2400-task segments',
        diagnostic_h_g='latest scored proposal h,g per terminal task; never scored: terminal h and g=0',
        diagnostic_A='sum actual once-only receipt a / sum(h/20), same unique terminal tasks',
        retries='earlier proposals excluded; unscored or expired tasks retained, never double-counted',
        mechanism_revision_limit=1,no_parameter_selection_from_smoke=True,
        initial_state='original seed101 initialization, never continue either prior model',
        old_evidence_preserved=preserve_check()))
    print('REGISTERED '+config['configuration_hash'],flush=True)


def check():
    config=read(OUT/'preregister.json')
    for p,h in config['source_sha256'].items():assert digest(ROOT/p)==h,p
    suite=unittest.defaultTestLoader.discover(str(ROOT/'tests'),pattern='test_d2_prime*.py')
    with (OUT/'migration_tests.txt').open('w',encoding='utf-8') as output:
        result=unittest.TextTestRunner(stream=output,verbosity=2).run(suite)
    import test_d2_prime_zcut_revision as anchors
    save(OUT/'migration.json',dict(passed=result.wasSuccessful(),tests=result.testsRun,
        failures=len(result.failures),errors=len(result.errors),anchors=anchors.EVIDENCE))
    print('ENTRY_CHECKS '+json.dumps(read(OUT/'migration.json')),flush=True)
    assert result.wasSuccessful(),'entry checks failed; stop before training'


def diagnostic(rows,order,events):
    latest={}
    for e in events:
        for p in e.get('event',{}).get('proposals',[]):
            if p['g'] is not None:latest[p['task_id']]=p
    by_id={r['task_id']:r for r in rows}
    def part(ids):
        terms=[]
        for tid in ids:
            row=by_id[tid];p=latest.get(tid)
            h=p['h'] if p else 1/(1+row['staleness_terminal'])
            g=p['g'] if p else 0.
            terms.append((h,g,row['a']))
        sh=math.fsum(h for h,g,a in terms);hg=math.fsum(h*g for h,g,a in terms)
        sa=math.fsum(a for h,g,a in terms)
        return dict(tasks=len(terms),sum_h=sh,sum_h_g=hg,sum_a=sa,nominal_commit=sh/20,
                    G=hg/sh,A=sa/(sh/20))
    return dict(segments=[dict(segment=j+1,**part(order[j*2400:(j+1)*2400])) for j in range(5)],
        latter_four=part(order[2400:]),all=part(order))


def verify(unit):
    from scripts.verify_d2_prime_formal import verify as reconstruct
    result=reconstruct(unit,OUT)
    result['preserved_original_files']=preserve_check()
    save(OUT/(unit+'_independent_verification.json'),result)
    print('INDEPENDENT '+json.dumps(result),flush=True)


if __name__=='__main__':
    assert Path(sys.executable).resolve()==Path(r'E:\anaconda3\python.exe').resolve()
    parser=argparse.ArgumentParser()
    parser.add_argument('action',choices=['prepare','check','smoke','full','verify_smoke','verify_full'])
    action=parser.parse_args().action
    if action=='prepare':prepare()
    elif action=='check':check()
    elif action.startswith('verify_'):verify(action[7:])
    else:
        import scripts.run_d2_prime_formal as runner
        runner.OUT=OUT
        if action=='full':assert read(OUT/'smoke_independent_verification.json')['independent_event_math']
        preserve_check();runner.run(action=='smoke');preserve_check()
