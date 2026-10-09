"""Trimmed 2.1: one normal bounded-delay condition, two independent clean units."""
import argparse
from collections import Counter
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys
import time
import traceback
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'outputs/d2_prime_phase2_1_async_20261009'
sys.path[:0] = [str(ROOT),str(ROOT/'easyFL')]
PYTHON = Path(r'E:\anaconda3\python.exe')


def read(path):return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def save(path,value):
    Path(path).write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')


def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def object_digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,allow_nan=False).encode()).hexdigest()


def prepare():
    import numpy as np
    previous=read(ROOT/'docs/D2_PRIME_PHASE1_MANIFEST.json')
    assert previous['status']=='PASS' and previous['frozen']['B']=='rfa'
    old=previous['configuration']
    assert (old['IR'],old['alpha'],old['num_clients'])==(5,1.,100)
    task=Path(old['task'])
    for p,h in old['task_sha256'].items():assert digest(task/p)==h
    slow=sorted(np.random.RandomState(1801).choice(100,50,replace=False).tolist())
    paths=['docs/D2_PRIME_PHASE2_1_RULING.md','docs/D2_PRIME_CHECKPOINTS_TRIMMED.md',
        'docs/D2_PRIME_CHECKPOINTS.md','docs/D2_PRIME_DESIGN.md','docs/D2_PRIME_PHASE1_REPORT.md',
        'docs/D2_PRIME_PHASE1_MANIFEST.json','docs/D2_PRIME_PHASE05_07_REPORT.md',
        'flgo_byzantine/d2_prime_algorithm.py','d2_prime/protocol.py','d2_prime/budget.py','d2_prime/reference.py',
        'flgo_byzantine/algorithm.py','aggregators/rfa.py','aggregators/rfa_contributions.py',
        'aggregators/contribution_diagnostics.py','easyFL/flgo/algorithm/fedbuff.py',
        'easyFL/flgo/algorithm/fedbase.py','easyFL/flgo/algorithm/asyncbase.py','easyFL/flgo/simulator/base.py',
        'aggregators/async_rfa_contributions.py','flgo_byzantine/async_baseline_state.py',
        'flgo_byzantine/async_baseline_algorithm.py','scripts/run_d2_prime_async_baseline.py',
        'scripts/summarize_d2_prime_async_baseline.py','tests/test_d2_prime_async_baseline.py']
    config={k:old[k] for k in ('task','task_sha256','IR','alpha','num_clients','num_epochs','batch_size',
        'learning_rate','lr_scheduler','optimizer','momentum','weight_decay','seed','dataseed',
        'development_indices','final_evaluation_indices','train_labels_sha256','test_labels_sha256')}
    config.update(source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        registered_at=datetime.now(timezone.utc).isoformat(), device='cuda:0',dtype='float32',amp=False,
        model='original CIFAR10 CNN, 797962 parameters, no buffers', K=20,eta_model=1.,
        task_limit=12000,evaluation_points=[10400,10800,11200,11600,12000],max_outstanding=40,
        one_unterminated_per_identity=True,clock='integer simulation tick, start0, step1',
        buffer_wait=8,lifetime=32,max_staleness=64,staleness_weight='1/(1+version_before-source_version)',
        dispatch_seed=801,slow_seed=1801,delay_seeds=[2801+c for c in range(100)],
        slow_ids=slow,slow_ids_sha256=object_digest(slow),fast_ids=sorted(set(range(100))-set(slow)),
        delays_fast=[1,2,3],delays_slow=[6,7,8],malicious_fraction=0.,
        B='rfa',rfa_T=5,rfa_nu=1e-6,rfa_semantics='rfa_final_mix_v1',
        async_rfa_semantics='async_rfa_post_staleness_v1',B_M=previous['frozen']['B_M'],
        B_M_used_for_baseline_clipping=False,H=None,beta=None,
        nominal_fee='0.055/(1+staleness_commit); no actual reference writes',
        H_rule='linear p95 of positive same-identity consecutive effective commit tick gaps',
        beta_rule='linear p95 of all 100 identity maximum nominal costs in (t-H,t]',
        transport='native FLGo with_clock / with_latency / ElemClock; sorted compute order',
        tail='after budget, no unterminated issued tasks: consume remainder immediately; drain late packets',
        recovery='unsupported: interrupted unit restarts from original registration; final_model is not checkpoint',
        smoke_task_limit=200,source_sha256={p:digest(ROOT/p) for p in paths})
    config['configuration_hash']=object_digest(config)
    OUT.mkdir(exist_ok=True)
    if (OUT/'preregister.json').exists():
        raise RuntimeError('registration already exists; preserve it before an explicit source repair')
    save(OUT/'preregister.json',config)
    print('REGISTERED '+json.dumps({k:config[k] for k in ('configuration_hash','slow_ids','H','beta')}),flush=True)


def run_unit(method,smoke):
    import numpy as np
    import torch
    import flgo
    import flgo_byzantine.algorithm as synchronous_bridge
    import flgo_byzantine.async_baseline_algorithm as algorithm
    from attacks.flgo_label_flip import LabelFlippedDataset
    from flgo.experiment.logger.simple_logger import SimpleLogger
    from scripts.summarize_d2_prime_async_baseline import calibrate,diagnose
    config=read(OUT/'preregister.json')
    for p,h in config['source_sha256'].items():assert digest(ROOT/p)==h,p
    task=Path(config['task'])
    for p,h in config['task_sha256'].items():assert digest(task/p)==h,p
    if not smoke:
        for m in ('avg','rfa'):
            assert read(OUT/f'smoke_{m}/result.json')['engineering_ok']
    directory=OUT/f'{"smoke" if smoke else "full"}_{method}'
    directory.mkdir()
    for p in ('record','log'):(directory/p).mkdir()
    limit=200 if smoke else 12000
    points=[200] if smoke else [10400,10800,11200,11600,12000]
    options=dict(gpu=[0],num_rounds=12000,num_epochs=1,num_steps=-1,batch_size=64,
        learning_rate=.1,lr_scheduler='-1',optimizer='SGD',momentum=0.,weight_decay=0.,
        seed=101,dataseed=0,num_workers=0,num_parallels=1,torch_num_threads=1,
        train_holdout=0.,test_holdout=0.,test_batch_size=128,no_tqdm=True,
        no_log_console=True,log_file=True,eval_interval=0,async_method=method,
        async_task_limit=limit,async_eval_points=points,async_config_id=config['configuration_hash'])
    class UnitLogger(SimpleLogger):
        def get_output_path(self):return str(directory/'record')
        def get_log_path(self):return str(directory/'log')
        def get_output_name(self,suffix='.json'):return directory.name+suffix
    with patch.object(synchronous_bridge,'load_root_data',side_effect=AssertionError('root use forbidden')) as roots:
        runner=flgo.init(str(task),algorithm,options,Logger=UnitLogger)
        assert len(runner.clients)==100 and runner.baseline.capacity==20
        assert runner.baseline.limit==40 and not list(runner.model.buffers())
        assert sum(p.numel() for p in runner.model.parameters())==797962
        assert runner.learning_rate==.1 and runner.lr_scheduler_type=='-1'
        assert sorted(runner.slow_ids)==config['slow_ids']
        assert not any(k in vars(runner.baseline) for k in ('reference','budget','clip_norm'))
        initial=algorithm.parameter_vector(runner.model)
        initial_hash=hashlib.sha256(initial.cpu().numpy().tobytes()).hexdigest()
        assert initial_hash=='f266aa56cc0cfc3947bb2b83966b309c3a14cce26801d47854a5655c53af5d0b'
        data=read(task/'data.json')
        names=data['client_names']
        pool=set()
        for c in runner.clients:
            assert not isinstance(c.train_data,LabelFlippedDataset) and c.val_data is None and c.test_data is None
            assert list(c.train_data.indices)==data[names[c.id]]['data']
            assert not pool.intersection(c.train_data.indices)
            pool.update(c.train_data.indices)
            assert c.num_steps==math.ceil(c.datavol/64) and c.learning_rate==.1
        info=read(task/'info')['root_data']
        assert pool==set(info['client_pool_indices']) and not pool.intersection(info['root_indices'])
        assert len(pool)==20342 and len(info['root_indices'])==2000
        raw_train=runner.clients[0].train_data.dataset.targets
        raw_test=runner.test_data.dataset.targets if hasattr(runner.test_data,'dataset') else runner.test_data.targets
        for values,key in ((raw_train,'train_labels_sha256'),(raw_test,'test_labels_sha256')):
            assert hashlib.sha256(np.asarray(values,dtype='<i8').tobytes()).hexdigest()==config[key]
        assert len(runner.test_data)==10000
        runner.test_data=torch.utils.data.Subset(runner.test_data,config['development_indices'])
        runner.calculator.collect_class_stats=True
        curves={"terminated_tasks":[],"issued_tasks":[],"training_samples":[],"minibatches":[],
                "simulated_time":[],"model_version":[],"class_total":[500]*10,
                "class_correct":[],"class_loss_mean":[],"macro_accuracy":[]}
        def evaluate(progress):
            result=runner.test()
            stats=runner.calculator.last_class_statistics
            assert stats['class_total']==[500]*10
            assert sum(stats['class_correct'])/5000==result['accuracy']
            work={k:sum(c.work[k] for c in runner.clients) for k in ('tasks','minibatches','examples')}
            for key,value in [('terminated_tasks',progress),('issued_tasks',len(runner.baseline.tasks)),
                ('training_samples',work['examples']),('minibatches',work['minibatches']),
                ('simulated_time',runner.baseline.now),('model_version',runner.baseline.version),
                ('class_correct',stats['class_correct']),('class_loss_mean',stats['class_loss_mean']),
                ('macro_accuracy',sum(stats['class_correct'])/5000)]:curves[key].append(value)
            print('EVALUATE '+json.dumps({'unit':directory.name,'tasks':progress,'M':curves['macro_accuracy'][-1],
                                         'time':runner.baseline.now,'version':runner.baseline.version}),flush=True)
        runner.on_evaluate=evaluate
        with (directory/'batches.jsonl').open('w',encoding='utf-8') as output:
            def on_batch(record):
                output.write(json.dumps(record,allow_nan=False)+'\n');output.flush()
                if runner.baseline.terminated%600==0:
                    print(f'PROGRESS {directory.name} terminal={runner.baseline.terminated} issued={len(runner.baseline.tasks)} tick={runner.baseline.now}',flush=True)
            runner.on_batch=on_batch
            start=time.perf_counter()
            try:
                runner.run()
            except Exception:
                save(directory/'failure.json',{'exception':traceback.format_exc(),
                    'issued':len(runner.baseline.tasks),'terminated':runner.baseline.terminated,
                    'tick':runner.baseline.now,'version':runner.baseline.version})
                if hasattr(runner.baseline,'failed_batch'):
                    torch.save(runner.baseline.failed_batch,directory/'failed_batch_inputs.pt')
                raise
            elapsed=time.perf_counter()-start
        state=runner.baseline
        state.audit()
        rows=list(state.tasks.values())
        assert len(rows)==state.terminated==limit and not state.live and not state.fifo and runner.gv.clock.empty()
        assert runner.executed_order==list(range(limit))
        work={k:sum(c.work[k] for c in runner.clients) for k in ('tasks','minibatches','examples')}
        assert work['tasks']==limit
        assert work['examples']==sum(len(data[names[r['identity']]]['data']) for r in rows)
        assert work['minibatches']==sum(math.ceil(len(data[names[r['identity']]]['data'])/64) for r in rows)
        assert all(r['first_packet_at'] is not None and r['raw_norm'] is not None for r in rows)
        assert roots.call_count==0
        assert curves['terminated_tasks']==[0]+points
        save(directory/'tasks.json',rows)
        save(directory/'events.json',state.journal)
        save(directory/'dispatch_delays.json',runner.delay_sequence)
        save(directory/'class_curves.json',curves)
        result=dict(method=method,configuration_hash=config['configuration_hash'],effective_options=runner.option,
            engineering_ok=True,task_limit=limit,work=work,simulated_time=state.now,model_version=state.version,
            initial_model_sha256=initial_hash,dispatch_delays_sha256=object_digest(runner.delay_sequence),
            terminal_counts=dict(Counter(r['state'] for r in rows)),batch_sizes=dict(Counter(r['batch_size'] for r in state.batches)),
            batch_reasons=dict(Counter(r['reason'] for r in state.batches)),
            maximum_outstanding=state.maximum_outstanding,maximum_arrived=state.maximum_arrived,
            root_loader_calls=roots.call_count,final_evaluation_forward_count=0,
            M=sum(curves['macro_accuracy'][-5:])/5 if not smoke else None,
            endpoint=curves['macro_accuracy'][-1],tail8_last5=sum(r[8]/500 for r in curves['class_correct'][-5:])/5 if not smoke else None,
            tail9_last5=sum(r[9]/500 for r in curves['class_correct'][-5:])/5 if not smoke else None,
            maximum_E_alg=max(r['checks']['E_alg'] for r in state.batches),
            maximum_E_model=max(r['checks']['E_model'] for r in state.batches),
            all_actual_writebacks_exact=all(r['checks']['writeback_exact'] for r in state.batches),
            elapsed_seconds=elapsed,peak_cuda_memory_allocated=torch.cuda.max_memory_allocated(),
            diagnostics=diagnose(rows,runner.slow_ids,config['B_M']),recovery_supported=False)
        save(directory/'result.json',result)
        torch.save(runner.model.state_dict(),directory/'final_model_only.pt')
        if not smoke and method=='avg':save(directory/'offline_H_beta.json',calibrate(rows))
        for p,h in config['task_sha256'].items():assert digest(task/p)==h
        print('UNIT_COMPLETE '+json.dumps({k:result[k] for k in ('method','M','endpoint','work','model_version','simulated_time','elapsed_seconds')}),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('action',choices=['prepare','smoke','unit'])
    p.add_argument('--method',choices=['avg','rfa'])
    args=p.parse_args()
    assert Path(sys.executable).resolve()==PYTHON.resolve()
    try:
        prepare() if args.action=='prepare' else run_unit(args.method,args.action=='smoke')
    except Exception:
        traceback.print_exc()
        # No automatic resume or result-dependent retry.
        sys.exit(1)
