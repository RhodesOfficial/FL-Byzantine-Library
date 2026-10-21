"""Fixed B-E01 producer/evaluator. Deployable replay never receives current truth.

Commands: probe, representative, restart, finish, verify. Every scientific Python
invocation is externally capped and receipted by scripts/b_e01_process.ps1.
"""
import hashlib
import json
import os
import pickle
import random
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'artifacts/b/e01'
LOCAL = ROOT / 'artifacts_local/b/e01'
TASK = ROOT / 'artifacts/direction_a/phase0_2_v1/tasks/FedPCC-0.2-candidate-CIFAR10-N20-v1'
CKPT_OBJECT = 'ba9b542:artifacts/direction_a/backbone_preparation_v1/checkpoints/A-backbone-CIFAR10-s2026101321-r0080-v1.pt'
CKPT_HASH = 'd8e137b9feeda74bb3bf401b64569e0075f3ec52914eb0ccf72d56040965a5ed'
STATE_HASH = 'c2a11303f977029a840946f1703047288365ec4b6bbb7136db3ad3eb65ad4b44'


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda: f.read(1024*1024), b''):
            h.update(chunk)
    return h.hexdigest()


def dump(path, obj):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(obj, indent=2, sort_keys=True, allow_nan=False) + '\n', encoding='utf-8')
    os.replace(temp, path)


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def save_pickle(path, obj):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + '.tmp')
    with temp.open('wb') as f:
        pickle.dump(obj, f, protocol=5)
    os.replace(temp, path)


def read_pickle(path):
    with Path(path).open('rb') as f:
        return pickle.load(f)


def storage():
    return sum(p.stat().st_size for base in (OUT, LOCAL) for p in base.rglob('*') if p.is_file())


def check_storage():
    n = storage()
    if n > 1073741824:
        raise RuntimeError(f'E01 storage cap: {n}')
    return n


def environment():
    import numpy as np
    import torch
    torch.set_num_threads(4); torch.set_num_interop_threads(1)
    torch.use_deterministic_algorithms(True)
    return {'python_executable':sys.executable, 'python':sys.version,
            'numpy':np.__version__, 'numpy_module':np.__file__,
            'torch':torch.__version__, 'torch_module':torch.__file__,
            'torch_compute_threads':torch.get_num_threads(), 'torch_interop_threads':torch.get_num_interop_threads(),
            'device':'cpu','cuda_used':False,'project_root':str(ROOT),
            'openblas_threads':os.environ.get('OPENBLAS_NUM_THREADS')}


def input_and_model():
    import numpy as np
    import torch
    from direction_a.model import ResNet8Adapter, transform_images
    start=time.perf_counter()
    info = load(TASK/'info.json'); data = load(TASK/'data.json'); counts=load(TASK/'counts.json')
    task_hashes = {name:sha(TASK/name) for name in ('info.json','data.json','counts.json','acceptance.json')}
    for name, expected in info['artifact_sha256'].items():
        assert task_hashes[name] == expected, ('task hash',name)
    assert info['spec']['dataset']=='CIFAR10' and info['spec']['clients']==20 and info['spec']['alpha']==0.1
    assert info['actual_training_if']==100.0
    selections=[]
    for i, client in enumerate(data['clients']):
        assert client['id']==f'client_{i:03d}'
        pool=client['train']
        assert len(pool)==sum(counts['n_ic'][i]) and len(pool)==len(set(pool))
        selected=sorted(random.Random(2026102100+i).sample(pool,min(32,len(pool))))
        assert set(selected)<=set(pool) and not set(selected).intersection(data['validation'])
        selections.append(selected)
    assert sum(map(len,selections))==583
    wanted=set(j for ss in selections for j in ss)
    sample_images={}; sample_labels={}; raw_hashes={}; read_sources=[]
    for path, expected in info['source_file_sha256'].items():
        if Path(path).name.startswith('data_batch_'):
            p=Path(path); raw=p.read_bytes(); digest=hashlib.sha256(raw).hexdigest()
            assert digest==expected, ('raw source hash',str(p))
            raw_hashes[str(p)]=digest
            batch=pickle.loads(raw,encoding='bytes')
            offset=(int(p.name.rsplit('_',1)[1])-1)*10000
            assert batch[b'data'].shape==(10000,3072) and len(batch[b'labels'])==10000
            # Only selected training images are transformed; no validation/test image decode or prediction.
            for j in sorted(wanted.intersection(range(offset,offset+10000))):
                sample_images[j]=batch[b'data'][j-offset].reshape(3,32,32).copy()
                sample_labels[j]=int(batch[b'labels'][j-offset])
            read_sources.append(str(p)); del raw, batch
    assert len(raw_hashes)==5 and len(sample_images)==583
    batches=[(transform_images(np.stack([sample_images[j] for j in ss]),'CIFAR10'),
              torch.tensor([sample_labels[j] for j in ss],dtype=torch.int64)) for ss in selections]
    checkpoint=LOCAL/'reference.pt'
    if not checkpoint.exists():
        with checkpoint.open('wb') as f:
            subprocess.run(['git','show',CKPT_OBJECT],cwd=ROOT,stdout=f,check=True)
    assert checkpoint.stat().st_size==1258030 and sha(checkpoint)==CKPT_HASH
    checkpoint_data=torch.load(checkpoint,map_location='cpu',weights_only=False)
    if 'state_dict' in checkpoint_data:
        key='state_dict'
    elif 'model_state_dict' in checkpoint_data:
        key='model_state_dict'
    elif 'model' in checkpoint_data and isinstance(checkpoint_data['model'],dict):
        key='model'
    else:
        key=None
    state=checkpoint_data if key is None else checkpoint_data[key]
    model=ResNet8Adapter(10); model.load_state_dict(state,strict=True)
    assert model.state_identity()==STATE_HASH, 'checkpoint state identity'
    model.eval(); model.requires_grad_(True)
    params=list(model.named_parameters())
    assert all(p.requires_grad for _,p in params)
    bn={n:v.detach().clone() for n,v in model.named_buffers()}
    bn_hash=hashlib.sha256(b''.join(n.encode()+v.numpy().tobytes() for n,v in bn.items())).hexdigest()
    bn_meta=json.dumps([{'name':n,'dtype':str(v.numpy().dtype),'shape':list(v.shape)} for n,v in bn.items()],sort_keys=True).encode('utf-8')
    bn_wire=len(bn_meta).to_bytes(4,'little')+bn_meta+b''.join(v.numpy().tobytes() for v in bn.values())
    bn_path=LOCAL/'fixed_BN_wire.bin'
    if bn_path.exists(): assert sha(bn_path)==hashlib.sha256(bn_wire).hexdigest()
    else: bn_path.write_bytes(bn_wire)
    identity={'task_hashes':task_hashes,'source_training_hashes':raw_hashes,'read_sources':read_sources,
              'sample_indices':selections,'client_sample_sizes':list(map(len,selections)), 'samples':583,
              'checkpoint_object':CKPT_OBJECT,'checkpoint_file_sha256':sha(checkpoint),
              'checkpoint_state_sha256':model.state_identity(),'checkpoint_container_key':key,
              'checkpoint_container_keys':list(checkpoint_data),
              'parameter_order':[{'name':n,'shape':list(p.shape),'dtype':str(p.dtype),'numel':p.numel()} for n,p in params],
              'D':sum(p.numel() for _,p in params),'BN_sha256':bn_hash,'fixed_BN_wire_bytes':len(bn_wire),
              'downlink_encoding':'actual persisted little-endian float32 parameter body theta_tXX.bin + <IIQII task header; fixed BN wire once per client at initialization',
              'all_parameters_trainable':True,'model_mode':'eval_fixed_BN',
              'data_exposure':'only five official training source files; 583 selected train images transformed; no validation/test prediction',
              'input_initialization_seconds':time.perf_counter()-start}
    if (OUT/'inputs.json').exists():
        prior=load(OUT/'inputs.json')
        for field in ('task_hashes','source_training_hashes','sample_indices','checkpoint_file_sha256','checkpoint_state_sha256','parameter_order','BN_sha256'):
            assert prior[field]==identity[field], ('input changed on restart',field)
    else:
        dump(OUT/'inputs.json',identity)
    return model,batches,bn,identity


def persist_model_wire(t,model):
    import numpy as np
    values=np.concatenate([p.detach().numpy().reshape(-1) for p in model.parameters()]).astype('<f4')
    raw=values.tobytes(); path=LOCAL/f'theta_t{t:02d}.bin'
    if path.exists():
        assert sha(path)==hashlib.sha256(raw).hexdigest(), 'source model wire changed'
    else:
        path.write_bytes(raw)
    return len(raw)


def produce(until):
    import numpy as np
    import torch
    start=time.perf_counter()
    model,batches,bn,identity=input_and_model()
    params=[p for p in model.parameters()]; D=identity['D']
    cursor_file=LOCAL/'path_cursor.pkl'
    cursor=read_pickle(cursor_file) if cursor_file.exists() else {'t':0,'i':0,'model':model.state_dict(),'evaluations':0,'points':[]}
    model.load_state_dict(cursor['model'],strict=True)
    persist_model_wire(cursor['t'],model) if cursor['t']<16 else None
    new=[]
    while cursor['t']<until:
        t=cursor['t']; point=LOCAL/f'gradient_t{t:02d}.npy'; begin=time.perf_counter()
        if point.exists():
            table=np.lib.format.open_memmap(point,mode='r+')
            assert table.shape==(20,D) and table.dtype==np.float32
        else:
            table=np.lib.format.open_memmap(point,mode='w+',dtype=np.float32,shape=(20,D))
        for i in range(cursor['i'],20):
            x,y=batches[i]
            model.zero_grad(set_to_none=True)
            loss=torch.nn.functional.cross_entropy(model(x),y,reduction='mean')
            loss.backward()
            assert all(p.grad is not None and torch.isfinite(p.grad).all() for p in params)
            gradient=torch.cat([p.grad.detach().reshape(-1) for p in params]).numpy()
            table[i]=gradient; table.flush()
            for n,v in model.named_buffers():
                assert torch.equal(v,bn[n]),('BN changed',n)
            cursor['i']=i+1; cursor['evaluations']+=1
            cursor['model']=model.state_dict()
            cursor.setdefault('losses',[]).append({'t':t,'client':i,'CE':float(loss.detach())})
            save_pickle(cursor_file,cursor)
        current=table.astype(np.float64).mean(axis=0)
        # Protocol updates all trainable tensors in float32 after float64 direction arithmetic.
        if t<15:
            offset=0
            with torch.no_grad():
                for p in params:
                    size=p.numel()
                    value=p.detach().numpy().astype(np.float64)-0.01*current[offset:offset+size].reshape(tuple(p.shape))
                    p.copy_(torch.from_numpy(value.astype(np.float32)))
                    offset+=size
            persist_model_wire(t+1,model)
        record={'t':t,'gradient_sha256':sha(point),'gradient_bytes':point.stat().st_size,
                'point_seconds':time.perf_counter()-begin,'target_squared_norm':float(current@current)}
        cursor['points'].append(record); cursor['t']=t+1; cursor['i']=0; cursor['model']=model.state_dict()
        save_pickle(cursor_file,cursor)
        dump(OUT/'path_progress.json',{'complete_points':cursor['t'],'partial_point':None,'unique_client_evaluations':cursor['evaluations'],
                                     'points':cursor['points'],'losses':cursor['losses'],'BN_unchanged':True})
        new.append(record); check_storage()
        print(json.dumps({'point_complete':t,'unique_evaluations':cursor['evaluations'],'seconds':record['point_seconds']}),flush=True)
        del table
    return {'new_points':new,'complete_points':cursor['t'],'unique_evaluations':cursor['evaluations'],
            'producer_seconds':time.perf_counter()-start,'D':D}


class GradientStore:
    def __init__(self):
        import numpy as np
        self.tables={}
        for p in sorted(LOCAL.glob('gradient_t*.npy')):
            self.tables[int(p.stem[-2:])]=np.load(p,mmap_mode='r')
    def returned(self,source,client):
        import numpy as np
        return np.asarray(self.tables[source][client],dtype=np.float64)
    def truth(self,t):
        return self.tables[t].astype('float64').mean(axis=0)


def measure_step(state,store):
    import numpy as np
    from direction_b.replay import step
    t=state['t']; begin=time.perf_counter()
    result=step(state,store.returned)
    truth=store.truth(t)
    errors={name:np.asarray(v)-truth for name,v in result['vectors'].items()}
    correction=result['vectors']['R']-result['vectors']['C']
    record=result['diagnostics']
    record.update({'t':t,'errors_squared':{n:float(e@e) for n,e in errors.items()},
                   'target_squared_norm':float(truth@truth),'correction_squared':float(correction@correction),
                   'step_seconds':time.perf_counter()-begin})
    assert all(np.isfinite(e).all() for e in errors.values())
    return record,errors


def representative():
    from direction_b.replay import new_state,boundary_tests
    start=time.perf_counter(); env=environment(); dump(OUT/'environment.json',env)
    tests=boundary_tests(); dump(OUT/'boundary_checks.json',tests)
    production=produce(2); store=GradientStore()
    state=new_state(store.tables[0].astype('float64'),2026102101,0.10,True,fixed_initialization_bytes=load(OUT/'inputs.json')['fixed_BN_wire_bytes'])
    record,errors=measure_step(state,store)
    # Persist only low-dimensional evaluated records; no diagnostic truth in deployment state.
    envelope={'deployment':state,'evaluation_records':[record],'error_sum':{n:e.copy() for n,e in errors.items()}}
    save_begin=time.perf_counter()
    save_pickle(LOCAL/'representative_state.pkl',envelope)
    state_digest=sha(LOCAL/'representative_state.pkl'); save_seconds=time.perf_counter()-save_begin
    dump(OUT/'representative.json',{'producer':production,'first_buffer':record,'state_save_and_hash_seconds':save_seconds,
                                  'state_sha256':state_digest,
                                  'state_bytes':(LOCAL/'representative_state.pkl').stat().st_size,
                                  'internal_seconds':time.perf_counter()-start,'artifact_bytes':check_storage(),
                                  'restart_status':'awaiting_separate_process'})


def restart():
    environment(); start=time.perf_counter(); store=GradientStore()
    assert sha(LOCAL/'representative_state.pkl')==load(OUT/'representative.json')['state_sha256']
    envelope=read_pickle(LOCAL/'representative_state.pkl'); state=envelope['deployment']
    assert state['t']==1
    before=load(OUT/'path_progress.json')['unique_client_evaluations']
    record,errors=measure_step(state,store)
    envelope['evaluation_records'].append(record)
    for n,e in errors.items(): envelope['error_sum'][n]+=e
    save_pickle(LOCAL/'rolling_state.pkl',envelope)
    dump(OUT/'rolling_resume.json',{'name':'hetero_k0.10_s2026102101','t':state['t'],
                                   'sha256':sha(LOCAL/'rolling_state.pkl')})
    assert load(OUT/'path_progress.json')['unique_client_evaluations']==before==40
    dump(OUT/'restart.json',{'readback_sha256_verified':True,'before_t':1,'after_t':state['t'],
                           'completed_gradients_recomputed':0,'before_unique_evaluations':before,
                           'source_versions_continued':record,'state_sha256':sha(LOCAL/'rolling_state.pkl'),
                           'state_bytes':(LOCAL/'rolling_state.pkl').stat().st_size,
                           'internal_seconds':time.perf_counter()-start,'artifact_bytes':check_storage()})


def trajectory(state,store,name,records=None,error_sum=None):
    import numpy as np
    records=[] if records is None else records
    error_sum={} if error_sum is None else error_sum
    while state['t']<16:
        record,errors=measure_step(state,store); records.append(record)
        for n,e in errors.items():
            if n not in error_sum: error_sum[n]=e.copy()
            else: error_sum[n]+=e
        # One rolling state serves every trajectory; completed records and costs
        # are committed with state, so recovery never consumes a buffer twice.
        save_pickle(LOCAL/'rolling_state.pkl',{'deployment':state,'evaluation_records':records,'error_sum':error_sum})
        dump(OUT/'rolling_resume.json',{'name':name,'t':state['t'],'sha256':sha(LOCAL/'rolling_state.pkl')})
        dump(OUT/'buffers'/f'{name}.json',records)
    assert len(records)==16
    energy=float(np.mean([r['target_squared_norm'] for r in records])); epsilon=1e-8*max(1,energy)
    methods=list(records[0]['errors_squared'])
    maximum_reference_difference=max(r['arithmetic_reference_difference_squared'] for r in records)
    assert maximum_reference_difference<=epsilon, 'measurement invalid: aggregate arithmetic reference'
    mse={m:float(np.mean([r['errors_squared'][m] for r in records])) for m in methods}
    summary={'name':name,'seed':state['seed'],'k':state['k'],'heterogeneous':state['hetero'],
             'buffers':16,'returns':64,'mean_target_energy':energy,'epsilon':epsilon,'MSE':mse,
             'maximum_arithmetic_reference_difference_squared':maximum_reference_difference,
             'relative_target_energy_MSE':{m:v/energy if energy!=0 else None for m,v in mse.items()},
             'squared_bias':{m:float((error_sum[m]/16)@(error_sum[m]/16)) for m in methods},
             'max_squared_error':{m:max(r['errors_squared'][m] for r in records) for m in methods},
             'nonzero_corrections':sum(r['correction_squared']>epsilon for r in records),
             'paired_differences':{m:mse[m]-mse['R'] for m in ('C','CACHE','ABS')},
             'state_final_t':state['t'],'state_pending_count':len(state.get('pending',[])),
             'communication':state.get('communication',state.get('bytes',{})),
             'all_records_path':str((OUT/'buffers'/f'{name}.json').relative_to(ROOT))}
    dump(OUT/'trajectories'/f'{name}.json',summary)
    return summary


def finish():
    from direction_b.replay import new_state
    environment()
    assert load(OUT/'frozen_plan.json')['launch_remaining_allowed'] is True
    production=produce(16); assert production['unique_evaluations']==320
    store=GradientStore(); summaries=[]
    for hetero,k in ((True,0.10),(True,1.00),(True,0.01),(False,0.10)):
        for seed in range(2026102101,2026102105):
            name=f"{'hetero' if hetero else 'equal'}_k{k:.2f}_s{seed}"
            summary_file=OUT/'trajectories'/f'{name}.json'
            if summary_file.exists():
                summaries.append(load(summary_file)); continue
            resume=load(OUT/'rolling_resume.json')
            if resume['name']==name:
                assert sha(LOCAL/'rolling_state.pkl')==resume['sha256']
                envelope=read_pickle(LOCAL/'rolling_state.pkl'); state=envelope['deployment']
                assert state['t']==resume['t'] and state['seed']==seed and state['k']==k and state['hetero']==hetero
                records=envelope['evaluation_records']; error_sum=envelope['error_sum']
            else:
                state=new_state(store.tables[0].astype('float64'),seed,k,hetero,fixed_initialization_bytes=load(OUT/'inputs.json')['fixed_BN_wire_bytes']); records=[]; error_sum={}
            result=trajectory(state,store,name,records,error_sum); summaries.append(result)
            print(json.dumps({'trajectory_complete':name,'MSE':result['MSE'],'nonzero':result['nonzero_corrections']}),flush=True)
            check_storage(); del state
    main=[s for s in summaries if s['heterogeneous'] and s['k']==0.10]
    comparisons={}
    for baseline in ('C','CACHE','ABS'):
        base=sum(s['MSE'][baseline] for s in main)/4; actual=sum(s['MSE']['R'] for s in main)/4
        gain=(base-actual)/base if base!=0 else None
        positive=sum(s['paired_differences'][baseline]>s['epsilon'] for s in main)
        comparisons[baseline]={'baseline_mean_MSE':base,'R_mean_MSE':actual,'relative_improvement':gain,
                               'positive_pairs':positive,'pass':gain is not None and gain>=0.05 and positive>=3}
    nonzero=sum(s['nonzero_corrections'] for s in main)
    scientific=all(c['pass'] for c in comparisons.values()) and nonzero>=13
    dump(OUT/'summary.json',{'protocol':'B-EXP-v1','task':'B-E01','main_comparisons':comparisons,
                           'main_nonzero_corrections':nonzero,'main_buffer_denominator':64,
                           'nonzero_condition_pass':nonzero>=13,'numerical_main_conditions_pass':scientific,
                           'trajectories':summaries,'complete_trajectories':len(summaries),'complete_buffers':256,
                           'effective_returns':1024,'unique_client_gradient_evaluations':320,
                           'interpretation':'fixed common full-model diagnostic path; event seeds not independent training repeats; Reviewer accepts/stops candidate',
                           'not_started':['B-E02','B-E03']})
    verify()


def verify():
    progress=load(OUT/'path_progress.json'); verified=[]
    for p in progress['points']:
        file=LOCAL/f"gradient_t{p['t']:02d}.npy"
        assert sha(file)==p['gradient_sha256']
        verified.append(p['t'])
    resume=load(OUT/'rolling_resume.json')
    assert sha(LOCAL/'rolling_state.pkl')==resume['sha256']
    restored=read_pickle(LOCAL/'rolling_state.pkl')['deployment']
    assert restored['t']==resume['t']
    if (OUT/'summary.json').exists():
        summary=load(OUT/'summary.json')
        assert len(summary['trajectories'])==16
        for s in summary['trajectories']:
            records=load(ROOT/s['all_records_path'])
            assert len(records)==16 and [r['t'] for r in records]==list(range(16))
            for record in records:
                assert len(record['errors_squared'])==9
    dump(OUT/'readback.json',{'all_gradient_hashes_match':True,'complete_points':len(verified),
                            'unique_client_evaluations':progress['unique_client_evaluations'],
                            'all_summary_and_buffer_JSON_readback':True,'artifact_bytes_at_check':check_storage(),
                            'final_state_readback':{'name':resume['name'],'t':restored['t'],'sha256':resume['sha256']},
                            'restoration':load(OUT/'restart.json')})
    files=[]
    for base in (OUT,LOCAL):
        for file in sorted(base.rglob('*')):
            if file.is_file() and file.name!='artifact_hashes.json' and 'processes' not in file.parts:
                files.append({'path':str(file.relative_to(ROOT)),'bytes':file.stat().st_size,'sha256':sha(file)})
    dump(OUT/'artifact_hashes.json',{'files':files,'mutable_process_receipts_excluded':True,'verified_complete_gradient_points':verified,
                                   'total_new_artifact_bytes_at_check':check_storage()})


def main():
    OUT.mkdir(parents=True,exist_ok=True); LOCAL.mkdir(parents=True,exist_ok=True)
    mode=sys.argv[1]
    if mode=='probe': dump(OUT/'environment_probe.json',environment())
    elif mode=='representative': representative()
    elif mode=='restart': restart()
    elif mode=='finish': finish()
    elif mode=='verify': environment(); verify()
    else: raise ValueError(mode)


if __name__=='__main__':
    main()
