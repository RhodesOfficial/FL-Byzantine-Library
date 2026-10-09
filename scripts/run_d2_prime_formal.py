"""Trimmed 2.2+2.3: migration gate, preregistered smoke, one full clean unit."""
import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import sys
import time
import traceback
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'easyFL')]
from scripts.run_d2_prime_async_baseline import read,save,digest,object_digest
OUT=ROOT/'outputs/d2_prime_phase2_2_3_20261009'


def prepare():
    import torch
    from d2_prime.reference import ReferenceConfig,ReferenceState,FeatureMap
    from flgo.benchmark.cifar10_classification.model.cnn import Model
    config=read(ROOT/'outputs/d2_prime_phase2_1_async_20261009/preregister.json')
    config.update(registered_at=datetime.now(timezone.utc).isoformat(),
        source_commit='a3cda3f6c33a4ebf1d49fac4731673bf2177e2d8',
        method='D2_prime',H=33.,beta=.4125,B_M_used_for_baseline_clipping=True,
        model_carrier='GPU/float32 committed state; no hidden evolving double model',
        canonical_candidate='exact float32 source/local values subtracted and full-norm clipped once in CPU double',
        model_write='round temporary double displacement to float32 then GPU float32 addition',
        reference_config=asdict(ReferenceConfig()),sigma_0=.25,
        initial_reference=asdict(ReferenceState.initial(ReferenceConfig())),initial_U=1.,initial_ready=False,
        progress='trained terminal order: event sequence then sorted task_id',
        evaluation_boundary='first full expiry/commit boundary >= target; offset <=39',
        M_minimum=.48876,R_slow_minimum=.8,segment_P_minimum=.1,
        ready_before_terminal=2400,latter_source_fraction_minimum=.8,
        nominal_fee='actual D2 shared a+b; a=h*g/20, b=.1*a, shared lambda',
        rfa_used_in_D2=False)
    model=Model()
    order=[dict(name=n,shape=list(p.shape),numel=p.numel()) for n,p in model.named_parameters()]
    mapping=FeatureMap.generate(797962,ReferenceConfig())
    OUT.mkdir(exist_ok=True)
    assert not (OUT/'preregister.json').exists(),'do not overwrite registration'
    torch.save(dict(buckets=torch.tensor(mapping.buckets),signs=torch.tensor(mapping.signs),
                    bucket_count=32,parameter_order=order),OUT/'actual_feature_map.pt')
    config.update(feature_map=dict(seed=0,buckets=32,dimension=33,file='actual_feature_map.pt',
        sha256=digest(OUT/'actual_feature_map.pt'),parameter_order=order,
        buckets_sha256=hashlib.sha256(torch.tensor(mapping.buckets).numpy().tobytes()).hexdigest(),
        signs_sha256=hashlib.sha256(torch.tensor(mapping.signs).numpy().tobytes()).hexdigest()))
    paths=list(config['source_sha256'])+['docs/D2_PRIME_PHASE2_2_RULING.md',
        'd2_prime/float32_protocol.py','flgo_byzantine/formal_d2_prime_algorithm.py',
        'scripts/run_d2_prime_formal.py','scripts/summarize_d2_prime_formal.py','tests/test_d2_prime_formal.py']
    config['source_sha256']={p:digest(ROOT/p) for p in paths}
    config.pop('configuration_hash',None)
    config['configuration_hash']=object_digest(config)
    save(OUT/'preregister.json',config)
    print('REGISTERED '+config['configuration_hash'],flush=True)


def run(smoke):
    import numpy as np
    import torch
    import flgo
    import flgo_byzantine.algorithm as sync_bridge
    import flgo_byzantine.formal_d2_prime_algorithm as algorithm
    from attacks.flgo_label_flip import LabelFlippedDataset
    from flgo.experiment.logger.simple_logger import SimpleLogger
    from scripts.summarize_d2_prime_formal import summarize
    config=read(OUT/'preregister.json')
    for p,h in config['source_sha256'].items():assert digest(ROOT/p)==h,p
    assert read(OUT/'migration.json')['passed']
    if not smoke:assert read(OUT/'smoke/result.json')['engineering_ok']
    directory=OUT/('smoke' if smoke else 'full')
    directory.mkdir()
    for name in ('record','log'):(directory/name).mkdir()
    limit=200 if smoke else 12000
    points=[200] if smoke else [10400,10800,11200,11600,12000]
    options=dict(gpu=[0],num_rounds=12000,num_epochs=1,num_steps=-1,batch_size=64,
        learning_rate=.1,lr_scheduler='-1',optimizer='SGD',momentum=0.,weight_decay=0.,
        seed=101,dataseed=0,num_workers=0,num_parallels=1,torch_num_threads=1,
        train_holdout=0.,test_holdout=0.,test_batch_size=128,no_tqdm=True,
        no_log_console=True,log_file=True,eval_interval=0,async_task_limit=limit,async_eval_points=points)
    options['d2_z_cut']=config['reference_config']['z_cut']
    class Logger(SimpleLogger):
        def get_output_path(self):return str(directory/'record')
        def get_log_path(self):return str(directory/'log')
        def get_output_name(self,suffix='.json'):return directory.name+suffix
    with patch.object(sync_bridge,'load_root_data',side_effect=AssertionError('root forbidden')) as roots:
        task=Path(config['task'])
        for p,h in config['task_sha256'].items():assert digest(task/p)==h
        runner=flgo.init(str(task),algorithm,options,Logger=Logger)
        p=runner.protocol
        assert asdict(p.reference_config)==config['reference_config']
        assert sum(v.numel() for v in runner.model.parameters())==797962
        assert not list(runner.model.buffers()) and sorted(runner.slow_ids)==config['slow_ids']
        assert asdict(p.reference)==config['initial_reference'] or json.loads(json.dumps(asdict(p.reference)))==config['initial_reference']
        initial_hash=hashlib.sha256(p.model.cpu().numpy().tobytes()).hexdigest()
        assert initial_hash=='f266aa56cc0cfc3947bb2b83966b309c3a14cce26801d47854a5655c53af5d0b'
        saved=torch.load(OUT/'actual_feature_map.pt',weights_only=True)
        assert torch.equal(saved['buckets'],torch.tensor(p.feature_map.buckets))
        assert torch.equal(saved['signs'],torch.tensor(p.feature_map.signs))
        data=read(task/'data.json');names=data['client_names'];pool=set()
        for c in runner.clients:
            assert not isinstance(c.train_data,LabelFlippedDataset) and c.val_data is None and c.test_data is None
            assert list(c.train_data.indices)==data[names[c.id]]['data']
            assert not pool.intersection(c.train_data.indices)
            pool.update(c.train_data.indices)
            assert c.num_steps==math.ceil(c.datavol/64) and c.learning_rate==.1
        info=read(task/'info')['root_data']
        assert pool==set(info['client_pool_indices']) and not pool.intersection(info['root_indices'])
        assert len(pool)==20342 and len(info['root_indices'])==2000
        train=runner.clients[0].train_data.dataset.targets
        test=runner.test_data.dataset.targets if hasattr(runner.test_data,'dataset') else runner.test_data.targets
        for values,key in ((train,'train_labels_sha256'),(test,'test_labels_sha256')):
            assert hashlib.sha256(np.asarray(values,dtype='<i8').tobytes()).hexdigest()==config[key]
        runner.test_data=torch.utils.data.Subset(runner.test_data,config['development_indices'])
        runner.calculator.collect_class_stats=True
        curves=[]
        def evaluate(target,actual):
            runner.test();stats=runner.calculator.last_class_statistics
            assert stats['class_total']==[500]*10
            row=dict(target=target,actual=actual,offset=actual-target,at=p.now,version=p.version,
                     class_correct=stats['class_correct'],M=sum(stats['class_correct'])/5000)
            curves.append(row)
            print('EVALUATE '+json.dumps(row),flush=True)
        runner.on_evaluate=evaluate
        with (directory/'events.jsonl').open('w',encoding='utf-8') as output:
            def record(row):
                output.write(json.dumps(row,allow_nan=False)+'\n');output.flush()
                if row['terminated_after']//600>row['terminated_before']//600:
                    print(f'PROGRESS terminal={runner.terminated} issued={len(p.tasks)} tick={p.now} version={p.version}',flush=True)
            runner.on_event=record
            start=time.perf_counter()
            try:runner.run()
            except Exception:
                save(directory/'failure.json',dict(exception=traceback.format_exc(),issued=len(p.tasks),
                    terminal=runner.terminated,at=p.now,version=p.version));raise
            elapsed=time.perf_counter()-start
        p.audit_budget();runner.audit_tick()
        rows=list(p.observations.values())
        assert len(rows)==runner.terminated==limit and not p.outstanding and not p.buffer_ids and runner.gv.clock.empty()
        assert runner.executed_order==list(range(limit)) and roots.call_count==0
        work={k:sum(c.work[k] for c in runner.clients) for k in ('tasks','minibatches','examples')}
        assert work['tasks']==limit
        assert work['examples']==sum(len(data[names[r['identity']]]['data']) for r in rows)
        assert work['minibatches']==sum(math.ceil(len(data[names[r['identity']]]['data'])/64) for r in rows)
        baseline=[json.loads(line) for line in (ROOT/'outputs/d2_prime_phase2_1_async_20261009/full_avg/batches.jsonl').read_text().splitlines()]
        diagnosis=summarize(rows,runner.terminal_order,runner.journal,runner.slow_ids,baseline)
        save(directory/'tasks.json',rows);save(directory/'terminal_order.json',runner.terminal_order)
        save(directory/'ledger.json',p.ledger);save(directory/'class_curves.json',curves)
        save(directory/'dispatch_delays.json',runner.delay_sequence)
        checks=[e['checks'] for e in runner.journal if e['kind']=='commit']
        result=dict(engineering_ok=True,configuration_hash=config['configuration_hash'],initial_hash=initial_hash,
            work=work,attempts=runner.attempts,consumed=len(p.ledger),version=p.version,at=p.now,
            M=sum(r['M'] for r in curves[-5:])/5 if not smoke else None,endpoint=curves[-1]['M'],
            evaluation_points=curves,diagnostics=diagnosis,elapsed_seconds=elapsed,
            E_alg_max=max(c['E_alg'] for c in checks),E_model_max=max(c['E_model'] for c in checks),
            reference_error_max=max(c['reference_max_abs_error'] for c in checks),
            all_exact=all(c['writeback_exact'] for c in checks),root_reads=roots.call_count,
            peak_cuda_allocated=torch.cuda.max_memory_allocated(),recovery_supported=False)
        save(directory/'result.json',result)
        torch.save(runner.model.state_dict(),directory/'final_model_only.pt')
        print('COMPLETE '+json.dumps({k:result[k] for k in ('M','endpoint','attempts','consumed','version','at','elapsed_seconds')}),flush=True)


if __name__=='__main__':
    assert Path(sys.executable).resolve()==Path(r'E:\anaconda3\python.exe').resolve()
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['prepare','smoke','full'])
    args=parser.parse_args()
    prepare() if args.action=='prepare' else run(args.action=='smoke')
