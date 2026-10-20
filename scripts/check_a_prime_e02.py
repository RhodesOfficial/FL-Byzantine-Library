"""E02 fixed C100/r80 qualification. Use run_a_prime_e02.ps1 for outer limits.
No training image encoding, official test access, branching FL utility or score-driven retry.
"""
import time
START = time.perf_counter()
import argparse
import copy
import hashlib
import json
import os
import pickle
import platform
import subprocess
import sys
from pathlib import Path
for _name in ('OMP_NUM_THREADS','MKL_NUM_THREADS','OPENBLAS_NUM_THREADS','NUMEXPR_NUM_THREADS'):
    os.environ[_name]='4'
import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from direction_a.model import ResNet8Adapter, transform_images
from check_a_prime_e01 import memory
OUT = ROOT / 'artifacts/a_prime/e02'
LOCAL = ROOT / 'artifacts_local/a_prime/e02'
TASK = ROOT / 'artifacts/direction_a/phase0_2_v1/tasks/FedPCC-0.2-candidate-CIFAR100-N20-v1'
REF = 'A-backbone-CIFAR100-s2026101322-r0080-v1'
INPUT = 'a2284d267ec757418ba105ab3f1fe033490d7322'
DIAG = 'artifacts/direction_a/phaseG1_2_full_v1/diagnostics/' + REF + '.pt'
BACKBONE = 'artifacts/direction_a/backbone_preparation_v1/checkpoints/' + REF + '.pt'
DIAG_SHA = '52ec222afebd2e41c883974fa1e0b840293b5b17310834b79f5838ff10f4cb8d'
BACKBONE_SHA = '7b6faf5b0a4be006133c72140d60e9d5918d52f8aa953f800b87efab268dccae'
STATE_SHA = '5a84b86e6d66a21ea5ea2ebf2e72b41a37db86402e2063cdc5a9b2d34018597a'
POSITIONS = [0,1,2,3,5,8,12,16,24,32,40,50,75,100,150,200]
LAM = .001
K = 12900
TIMINGS = {}
STAGE_SECONDS = 300

def sha(path):
    with Path(path).open('rb') as f:
        h = hashlib.sha256()
        while b := f.read(1024*1024): h.update(b)
    return h.hexdigest()

def js(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))

def capacity():
    return sum(p.stat().st_size for root in (OUT, LOCAL) for p in root.rglob('*') if p.is_file())

def guard():
    current, peak = memory()
    if peak > 8*1024**3: raise RuntimeError('8 GiB OS process working set exceeded')
    if capacity() > 512*1024**2: raise RuntimeError('512 MiB new artifact capacity exceeded')
    if time.perf_counter()-START > STAGE_SECONDS-3: raise RuntimeError('Stage timeout reserve reached')

def intended(path):
    p = Path(path).resolve()
    assert any(base.resolve() in p.parents for base in (OUT,LOCAL)), str(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    return p

def save_json(path, data):
    p = intended(path); tmp = intended(str(p)+'.tmp')
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False, allow_nan=False)+'\n', encoding='utf-8')
    assert js(tmp) == data
    guard()
    os.replace(tmp,p)
    assert js(p) == data
    guard()

def save_torch(path, data):
    p=intended(path); tmp=intended(str(p)+'.tmp')
    torch.save(data,tmp); torch.load(tmp,weights_only=True); guard()
    os.replace(tmp,p); guard()

def git_text(*args):
    return subprocess.check_output(['git',*args],cwd=ROOT).decode().strip()

def extract(path, expected):
    local_name = 'trusted_training_diagnostic.pt' if path==DIAG else 'trusted_validation_backbone.pt'
    assert path in (DIAG,BACKBONE)
    dest = intended(LOCAL / local_name)
    if not dest.exists():
        # Direct binary file redirection, never terminal-text binary recovery.
        with dest.open('xb') as f:
            subprocess.run(['git','show','ba9b542:'+path],cwd=ROOT,stdout=f,check=True)
    assert sha(dest)==expected
    return dest

def task():
    info=js(TASK/'info.json')
    for name in ('counts.json','data.json'): assert sha(TASK/name)==info['artifact_sha256'][name]
    return info,js(TASK/'data.json'),js(TASK/'counts.json')

def load_inputs():
    manifest=js(OUT/'input_identity.json')
    assert manifest['input_commit']==INPUT
    assert manifest['protocol_sha256']==sha(ROOT/'docs/projects/a_prime/PROTOCOL.md')
    assert manifest['task_sheet_sha256']==sha(ROOT/'docs/projects/a_prime/TO_EXECUTOR.md')
    for name,value in manifest['local_hashes'].items(): assert sha(LOCAL/name)==value
    with np.load(LOCAL/'features.npz',allow_pickle=False) as f: data={k:f[k].copy() for k in f.files}
    return data,manifest

def initialize():
    t=time.perf_counter(); info,data,counts=task()
    diag=extract(DIAG,DIAG_SHA)
    # Unsafe pickle is narrowly allowed only after exact trusted local Git byte identity.
    d=torch.load(diag,weights_only=False,map_location='cpu')
    zs=[]; ys=[]; indices=[]; client=[]
    assert sorted(d['clients'])==list(range(20))
    for i in range(20):
        part=d['clients'][i]; z=np.asarray(part['features_float32']); y=np.asarray(part['labels']); ix=np.asarray(part['global_train_indices']).tolist()
        assert list(ix)==data['clients'][i]['train']
        assert z.shape==(len(ix),128) and z.dtype==np.float32 and np.isfinite(z).all()
        assert np.bincount(y,minlength=100).tolist()==counts['n_ic'][i]
        zs.append(z); ys.append(y); indices.extend(ix); client.extend([i]*len(ix))
    z=np.concatenate(zs); y=np.concatenate(ys).astype(np.int64)
    assert len(y)==9754 and np.bincount(y,minlength=100).tolist()==counts['N_c']
    perm=np.random.Generator(np.random.PCG64(2026102002)).permutation(9754)
    old=np.concatenate([np.asarray(d['weight_float32']).reshape(-1),np.asarray(d['bias_float32']).reshape(-1)]).astype(np.float64)
    del d,zs
    train_source=next(Path(p) for p in info['source_file_sha256'] if Path(p).name=='train')
    assert sha(train_source)==info['source_file_sha256'][str(train_source)]
    # Reading the trusted official train container is necessary; encode validation only.
    with train_source.open('rb') as f: source=pickle.load(f,encoding='bytes')
    validation=np.array(data['validation'],dtype=np.int64)
    vy=np.array(source[b'fine_labels'],dtype=np.int64)[validation]
    assert len(validation)==1000 and np.bincount(vy,minlength=100).tolist()==[10]*100
    assert np.array_equal(y,np.array(source[b'fine_labels'])[indices])
    checkpoint=extract(BACKBONE,BACKBONE_SHA)
    saved=torch.load(checkpoint,map_location='cpu',weights_only=True)
    # Historical checkpoint carries named model_state plus identity metadata.
    state=saved.get('model_state',saved.get('state_dict',saved.get('model_state_dict')))
    if state is None: raise RuntimeError('Unknown trusted checkpoint schema: '+str(list(saved)))
    model=ResNet8Adapter(100); model.load_state_dict(state); model.freeze_reference()
    assert model.state_identity()==STATE_SHA
    vt=time.perf_counter(); vz=[]
    with torch.no_grad():
        for start in range(0,1000,128):
            ix=validation[start:start+128]
            images=source[b'data'][ix].reshape(-1,3,32,32)
            vz.append(model.encode(transform_images(images,'CIFAR100')).numpy()); guard()
    vz=np.concatenate(vz)
    assert model.state_identity()==STATE_SHA and not model.training
    TIMINGS['validation_encode_seconds']=time.perf_counter()-vt
    del source,model,saved,state
    p=intended(LOCAL/'features.npz')
    with p.open('wb') as f:
        np.savez(f,z=z,y=y,client=np.array(client),indices=np.array(indices),permutation=perm,
                 validation_z=vz,validation_y=vy,validation_indices=validation,ordinary_theta=old,
                 n_ic=np.array(counts['n_ic']),N_c=np.array(counts['N_c']),tail=np.array(counts['class_groups']['tail']))
    manifest={'input_commit':INPUT,'implementation_commit':git_text('rev-parse','HEAD'),
              'protocol':'APRIME-EXP-v1','protocol_sha256':sha(ROOT/'docs/projects/a_prime/PROTOCOL.md'),
              'task_sheet_sha256':sha(ROOT/'docs/projects/a_prime/TO_EXECUTOR.md'),
              'reference':REF,'reference_state_sha256':STATE_SHA,'source_commit':'ba9b542',
              'diagnostic_path':DIAG,'checkpoint_path':BACKBONE,'train_source_sha256':sha(train_source),
              'local_hashes':{f.name:sha(f) for f in (diag,checkpoint,p)},
              'permutation_sha256':hashlib.sha256(perm.tobytes()).hexdigest(),
              'validation_indices_sha256':hashlib.sha256(validation.tobytes()).hexdigest(),
              'train_samples':9754,'validation_samples':1000,'tail_classes':34,
              'data_access':'Trusted official train container hash/decode; only 1000 previously exposed validation images encoded; no official test file/images/predictions read; training features reused',
              'environment':{'python':sys.version,'torch':torch.__version__,'numpy':np.__version__,
                             'platform':platform.platform(),'threads':torch.get_num_threads(),'device':'CPU'},
              'full_checkpoint_schema':list(saved) if 'saved' in locals() else 'model_state accepted'}
    save_json(OUT/'input_identity.json',manifest)
    TIMINGS['initialize_seconds']=time.perf_counter()-t
    return load_inputs()

def value_grad(theta,z,y,weights,lam=LAM):
    C=int(y.max().item())+1
    dim=z.shape[1]; W=theta[:C*dim].reshape(C,dim); b=theta[C*dim:]
    logits=z@W.T+b; logp=torch.log_softmax(logits,dim=1)
    rows=torch.arange(len(y)); loss=-(weights*logp[rows,y]).sum()+lam/2*theta.square().sum()
    e=logp.exp(); e[rows,y]-=1; e*=weights[:,None]
    grad=torch.cat([(e.T@z).reshape(-1),e.sum(0)])+lam*theta
    return float(loss),grad

class Head:
    def __init__(self,name,data):
        self.name=name
        arr=data['z'] if name=='real' else data['z'][data['permutation']]
        self.z=torch.from_numpy(arr.astype(np.float64)); self.y=torch.from_numpy(data['y'])
        self.weights=torch.from_numpy(1/(100*data['N_c'][data['y']]).astype(np.float64))
        self.theta=torch.nn.Parameter(torch.zeros(K,dtype=torch.float64))
        self.opt=torch.optim.LBFGS([self.theta],lr=1,max_iter=1,max_eval=600,history_size=10,
                                  tolerance_grad=0,tolerance_change=0,line_search_fn='strong_wolfe')
        self.iterations=0; self.calls=0; self.history=[]; self.nodes={}; self.evaluations={}; self.stop=None
        self.last_theta=None; self.last_value=None; self.last_grad=None; self.closure_seconds=[]
    def closure(self):
        guard()
        if self.calls>=getattr(self,'active_cap',600): raise RuntimeError('Head value/gradient budget reached')
        t=time.perf_counter(); self.calls+=1
        # Charge even a failed, unaccepted line-search evaluation across process recovery.
        journal=intended(LOCAL/(self.name+'_call_journal.json'))
        journal.write_text(json.dumps({'calls_started':self.calls})+'\n',encoding='utf-8')
        value,grad=value_grad(self.theta.detach(),self.z,self.y,self.weights)
        assert np.isfinite(value) and torch.isfinite(grad).all()
        self.theta.grad=grad.clone()
        self.last_theta=self.theta.detach().clone(); self.last_value=value; self.last_grad=grad.clone()
        self.closure_seconds.append(time.perf_counter()-t)
        return torch.tensor(value,dtype=torch.float64)
    def metrics(self):
        if self.last_theta is None or not torch.equal(self.last_theta,self.theta.detach()): self.closure()
        norm=float(torch.linalg.vector_norm(self.last_grad))
        return {'iteration':self.iterations,'value_gradient_calls':self.calls,'objective':self.last_value,
                'gradient_norm':norm,'strong_convex_gap_bound':norm**2/(2*LAM),
                'sufficient':norm**2/(2*LAM)<=1e-4}
    def snap(self):
        return {'theta':self.theta.detach().clone(),'optimizer':copy.deepcopy(self.opt.state_dict()),
                'iterations':self.iterations,'calls':self.calls,'history':copy.deepcopy(self.history),
                'nodes':self.nodes,'evaluations':self.evaluations,'stop':self.stop,
                'last_theta':self.last_theta,'last_value':self.last_value,'last_grad':self.last_grad,
                'closure_seconds':self.closure_seconds}
    def restore(self,s):
        with torch.no_grad(): self.theta.copy_(s['theta'])
        self.opt.load_state_dict(s['optimizer'])
        for name in ('iterations','calls','history','nodes','evaluations','stop','last_theta','last_value','last_grad','closure_seconds'): setattr(self,name,s[name])
    def run_to(self,target,call_cap=600):
        self.active_cap=call_cap
        if self.name=='real' and not self.nodes: self.nodes[0]=self.theta.detach().clone()
        while self.iterations<target and not self.stop:
            metric=self.metrics()
            if not self.history or self.history[-1]['iteration']!=self.iterations: self.history.append(metric)
            if metric['sufficient']: self.stop='training_gap_sufficient'; break
            if self.calls>=call_cap:
                if call_cap==600: self.stop='value_gradient_budget_exhausted'
                break
            before=self.theta.detach().clone()
            opt_before=copy.deepcopy(self.opt.state_dict())
            value_before=self.last_value; grad_before=self.last_grad.clone()
            try: self.opt.step(self.closure)
            except RuntimeError as exc:
                if 'budget reached' not in str(exc): raise
                # A line-search trial is not an accepted head: restore its pre-step state.
                # Its already spent closures remain charged; no completed iterate is retrained.
                with torch.no_grad(): self.theta.copy_(before)
                self.opt.load_state_dict(opt_before)
                self.last_theta=before; self.last_value=value_before; self.last_grad=grad_before
                if call_cap==600: self.stop='value_gradient_budget_exhausted'
                break
            if torch.equal(before,self.theta.detach()): self.stop='numerical_no_parameter_change'; break
            self.iterations+=1
            if self.name=='real' and self.iterations in POSITIONS: self.nodes[self.iterations]=self.theta.detach().clone()
            metric=self.metrics(); self.history.append(metric)
            if metric['sufficient']: self.stop='training_gap_sufficient'
            save_torch(LOCAL/(self.name+'_resume.pt'),self.snap())
            if self.stop: break
        save_torch(LOCAL/(self.name+'_resume.pt'),self.snap())
        return self.metrics()

def evaluate(theta,data):
    C=100; z=torch.from_numpy(data['validation_z'].astype(np.float64)); t=torch.as_tensor(theta)
    pred=(z@t[:12800].reshape(C,128).T+t[12800:]).argmax(1).numpy()
    y=data['validation_y']; correct=(pred==y)
    per=np.array([correct[y==c].mean() for c in range(C)])
    return {'all_macro_recall':float(per.mean()),'tail_macro_recall':float(per[data['tail']].mean()),
            'per_class_recall':per.tolist(),'predictions':pred.tolist(),'samples':1000,'all_classes':100,
            'tail_classes':34,'tail_samples':340,'purpose':'previously_exposed_validation_exploration'}

def paired_interval(real,other,mask):
    d=(np.asarray(real)==mask['y']).astype(float)-(np.asarray(other)==mask['y']).astype(float)
    d=d[mask['keep']]; m=float(d.mean()); se=float(d.std(ddof=1)/np.sqrt(len(d)))
    return {'difference_pp':100*m,'normal_approx_95_pp':[100*(m-1.96*se),100*(m+1.96*se)],
            'samples':len(d),'scope':'descriptive paired samples on exposed fixed validation, not independent confirmation'}

def node_gradient(theta,data):
    t=time.perf_counter(); z=torch.from_numpy(data['z'].astype(np.float64)); y=torch.from_numpy(data['y'])
    th=torch.as_tensor(theta); logp=torch.log_softmax(z@th[:12800].reshape(100,128).T+th[12800:],1)
    e=logp.exp(); e[torch.arange(len(y)),y]-=1
    weights=torch.from_numpy(1/(100*data['N_c'][data['y']]).astype(np.float64)); e*=weights[:,None]
    # Only one transient set of class quantities for the shared return-mean diagnostic.
    class_h=np.zeros((20,100,K),dtype=np.float64)
    for i in range(20):
        positions=np.flatnonzero(data['client']==i)
        for c in np.flatnonzero(data['n_ic'][i]):
            rows=positions[data['y'][positions]==c]
            es=e[rows]; zs=z[rows]
            class_h[i,c]=torch.cat([(es.T@zs).reshape(-1),es.sum(0)]).numpy()
    h=class_h.sum(1)
    full=torch.cat([(e.T@z).reshape(-1),e.sum(0)]).numpy()
    residual=float(np.max(np.abs(h.sum(0)-full)))
    assert residual<=1e-11
    TIMINGS.setdefault('node_seconds',[]).append(time.perf_counter()-t)
    return h,class_h,residual

def checks():
    z=torch.tensor([[-1.],[-2.],[1.],[2.]],dtype=torch.float64); y=torch.tensor([0,0,1,1])
    w=torch.full((4,),.25,dtype=torch.float64); th=torch.tensor([.1,-.1,.03,-.03],dtype=torch.float64,requires_grad=True)
    loss=(-(w*torch.log_softmax(z@th[:2].reshape(2,1).T+th[2:],1)[torch.arange(4),y]).sum()+LAM/2*th.square().sum())
    loss.backward(); val,grad=value_grad(th.detach(),z,y,w)
    residual=float(torch.max(torch.abs(grad-th.grad)))
    assert residual<1e-12 and abs(val-float(loss))<1e-12
    param=torch.nn.Parameter(torch.zeros(4,dtype=torch.float64))
    opt=torch.optim.LBFGS([param],max_iter=50,history_size=10,line_search_fn='strong_wolfe')
    def closure():
        v,g=value_grad(param.detach(),z,y,w); param.grad=g; return torch.tensor(v,dtype=torch.float64)
    initial=value_grad(param.detach(),z,y,w)[0]; opt.step(closure); final=value_grad(param.detach(),z,y,w)[0]
    assert final<initial and (z@param[:2].reshape(2,1).T+param[2:]).argmax(1).tolist()==y.tolist()
    from a_prime_e02_events import selfcheck
    return {'gradient_autograd_max_residual':residual,'separable_positive_initial':initial,
            'separable_positive_final':final,'separable_predictions_correct':True,'events':selfcheck()}

def save_heads(heads):
    for h in heads: save_torch(LOCAL/(h.name+'_resume.pt'),h.snap())

def restore_heads(data):
    heads=[]
    for name in ('real','shuffled'):
        h=Head(name,data); h.restore(torch.load(LOCAL/(name+'_resume.pt'),weights_only=True))
        journal=LOCAL/(name+'_call_journal.json')
        if journal.exists(): h.calls=max(h.calls,js(journal)['calls_started'])
        heads.append(h)
    return heads

def representative():
    OUT.mkdir(parents=True,exist_ok=True); LOCAL.mkdir(parents=True,exist_ok=True)
    assert not (OUT/'representative.json').exists()
    assert not (list(OUT.glob('failure_representative_*.json')) and list(LOCAL.glob('*_call_journal.json'))), 'Representative head work interrupted: deliver partial, do not reset heads or journals'
    if not (OUT/'implementation_checks.json').exists(): save_json(OUT/'implementation_checks.json',checks())
    data,identity=(load_inputs() if (OUT/'input_identity.json').exists() else initialize())
    heads=[Head(n,data) for n in ('real','shuffled')]
    t=time.perf_counter()
    for h in heads: h.run_to(3,call_cap=12)
    TIMINGS['two_head_partial_seconds']=time.perf_counter()-t
    t=time.perf_counter(); ordinary=evaluate(data['ordinary_theta'],data); TIMINGS['evaluation_seconds']=time.perf_counter()-t
    save_json(OUT/'ordinary_validation.json',ordinary)
    h,ch,res=node_gradient(heads[0].nodes[0],data)
    active=np.argwhere(data['n_ic']>0)
    sparse=ch[active[:,0],active[:,1]].copy(); del ch
    save_torch(LOCAL/'node_000.pt',{'iteration':0,'theta':heads[0].nodes[0],'h':torch.from_numpy(h),
        'active_class_indices':torch.from_numpy(active),'class_h_active':torch.from_numpy(sparse)})
    del sparse
    t=time.perf_counter(); save_heads(heads); restored=restore_heads(data)
    equality=[]
    for before,after in zip(heads,restored):
        assert torch.equal(before.theta,after.theta)
        assert before.calls==after.calls and before.iterations==after.iterations
        # Optimizer history tensors/step scale/gradient restored; not a new optimization step.
        assert recursive_equal(before.opt.state_dict(),after.opt.state_dict())
        equality.append({'head':before.name,'calls':after.calls,'iterations':after.iterations,'optimizer_exact':True})
    TIMINGS['save_readback_restore_seconds']=time.perf_counter()-t
    stable=[x for hd in heads for x in hd.closure_seconds[1:]]
    receipt={'status':'representative_complete_heads_partial','timings':TIMINGS,
             'stable_closure_proxy_seconds':float(np.mean(stable)),'head_status':[h.metrics() for h in heads],
             'completed_calls':sum(h.calls for h in heads),'completed_nodes':1,
             'node_aggregation_max_residual':res,'restore':equality,'artifacts_bytes':capacity(),
             'process_working_set':dict(zip(['current_bytes','os_peak_bytes'],memory())),
             'inner_seconds':time.perf_counter()-START,'inner_not_added_to_outer':True}
    save_json(OUT/'representative.json',receipt)
    print(json.dumps(receipt,ensure_ascii=False))

def recursive_equal(a,b):
    if isinstance(a,torch.Tensor): return isinstance(b,torch.Tensor) and torch.equal(a,b)
    if isinstance(a,dict): return a.keys()==b.keys() and all(recursive_equal(a[k],b[k]) for k in a)
    if isinstance(a,(list,tuple)): return len(a)==len(b) and all(recursive_equal(x,y) for x,y in zip(a,b))
    return a==b

def full():
    plan=js(OUT/'plan.json'); assert plan['decision']=='continue_complete_package'
    data,identity=load_inputs(); heads=restore_heads(data)
    for h in heads:
        if 'final' in h.evaluations: continue
        if not h.stop and h.iterations<50: h.run_to(50)
        if 'tier50_or_early_stop' not in h.evaluations:
            h.evaluations['tier50_or_early_stop']=evaluate(h.theta.detach(),data)
            save_json(OUT/(h.name+'_tier50_validation.json'),h.evaluations['tier50_or_early_stop'])
            save_heads([h])
        if not h.metrics()['sufficient'] and not h.stop: h.run_to(200)
        if not h.stop: h.stop='accepted_iteration_budget_exhausted'
        if h.name=='real' and h.iterations not in h.nodes: h.nodes[h.iterations]=h.theta.detach().clone()
        assert len(h.nodes)<=16
        h.evaluations['final']=(h.evaluations['tier50_or_early_stop'] if h.iterations<=50 else evaluate(h.theta.detach(),data))
        save_json(OUT/(h.name+'_final_validation.json'),h.evaluations['final']); save_heads([h])
    real,shuffled=heads
    # In recovery completed heads are not trained or evaluated again.
    positions=sorted(real.nodes)
    save_json(OUT/'head_results.json',{'heads':{h.name:{'metrics':h.metrics(),'stop':h.stop,
                 'history':h.history,'closure_seconds':h.closure_seconds,'evaluations':h.evaluations} for h in heads},
                 'node_positions':positions,'method_utility':'not_tested'})
    node_res=[]
    def callback(j):
        iteration=positions[j]; theta=real.nodes[iteration]
        path=LOCAL/('node_%03d.pt'%iteration)
        if iteration==0:
            saved=torch.load(path,weights_only=True); assert torch.equal(saved['theta'],theta)
            h=saved['h'].numpy(); ch=np.zeros((20,100,K),dtype=np.float64)
            active=saved['active_class_indices'].numpy()
            ch[active[:,0],active[:,1]]=saved['class_h_active'].numpy()
            node_res.append(float(np.max(np.abs(ch.sum(1)-h))))
            return h,ch
        if path.exists(): raise RuntimeError('Partial event stage has a completed gradient node; preserve it, do not silently recompute')
        h,ch,res=node_gradient(theta,data); node_res.append(res)
        save_torch(path,{'iteration':iteration,'theta':theta,'h':torch.from_numpy(h)})
        return h,ch
    from a_prime_e02_events import diagnose
    if (OUT/'event_results.json').exists():
        events=js(OUT/'event_results.json')
        node_res=js(OUT/'node_checks.json')['aggregation_residuals']
    else:
        events=diagnose(data['n_ic'],data['tail'].tolist(),positions,callback,check=guard)
        save_json(OUT/'node_checks.json',{'aggregation_residuals':node_res,'positions':positions})
        save_json(OUT/'event_results.json',events)
    r=real.evaluations['final']; s=shuffled.evaluations['final']
    sufficient=real.metrics()['sufficient'] and shuffled.metrics()['sufficient']
    differences={name:r[name]-s[name] for name in ('all_macro_recall','tail_macro_recall')}
    summary={'representation_qualification':bool(sufficient and min(differences.values())>=.02),
             'both_heads_sufficient':bool(sufficient),'real_final_all_recall':r['all_macro_recall'],
             'real_final_tail_recall':r['tail_macro_recall'],'shuffled_final_all_recall':s['all_macro_recall'],
             'shuffled_final_tail_recall':s['tail_macro_recall'],'differences':differences,
             'paired_validation_uncertainty':{name:paired_interval(r['predictions'],s['predictions'],
                {'y':data['validation_y'],'keep':np.ones(1000,dtype=bool) if name=='all' else np.isin(data['validation_y'],data['tail'])}) for name in ('all','tail')},
             'actual_estimator_qualification':events['qualification'], 'main_estimator_comparison':events['main_comparison'],
             'method_classification_utility':'not_tested','independent_confirmation':'not_tested',
             'node_positions':positions,'node_aggregation_max_residual':max(node_res),'timings':TIMINGS,
             'artifacts_bytes':capacity(),'process_working_set':dict(zip(['current_bytes','os_peak_bytes'],memory())),
             'inner_seconds':time.perf_counter()-START,'inner_not_added_to_outer':True}
    save_json(OUT/'summary.json',summary)
    save_json(OUT/'state.json',{'complete':['input_objects','validation_features','real_head_optimization',
        'shuffled_head_optimization','head_optimizer_states','dynamic_nodes_events','registered_evaluations','save_readback'],
        'partial':[],'not_started':['E03_method_utility','new_references','CIFAR10','independent_confirmation'],
        'input_commit':INPUT,'protocol_sha256':identity['protocol_sha256']})
    print(json.dumps(summary,ensure_ascii=False))

def verify():
    data,identity=load_inputs(); heads=restore_heads(data)
    entries={}
    for root in (OUT,LOCAL):
        for path in root.rglob('*'):
            if path.is_file() and path.name!='recovery_verification.json' and not path.name.endswith('.tmp'):
                entries[str(path.relative_to(ROOT)).replace('\\','/')]=sha(path)
    restored=[]
    for h in heads:
        metric=h.metrics(); assert metric==js(OUT/'head_results.json')['heads'][h.name]['metrics']
        assert h.stop and h.calls<=600 and h.iterations<=200
        for iteration,theta in h.nodes.items():
            n=torch.load(LOCAL/('node_%03d.pt'%iteration),weights_only=True)
            assert torch.equal(theta,n['theta'])
        restored.append({'name':h.name,'iterations':h.iterations,'calls':h.calls,
                         'stop':h.stop,'optimizer_state_restored':True,'completed_head_retrained':False})
    s=js(OUT/'summary.json'); e=js(OUT/'event_results.json')
    assert s['actual_estimator_qualification']==e['qualification']
    save_json(OUT/'recovery_verification.json',{'input_commit':INPUT,'protocol_sha256':identity['protocol_sha256'],
        'local_hashes_checked':True,'head_states':restored,'all_evidence_hashes':entries,
        'state':js(OUT/'state.json'),'verification':'independent process reload; optimizer and all input/evidence hashes; no retraining or resampling',
        'inner_seconds':time.perf_counter()-START,'inner_not_added_to_outer':True,
        'process_working_set':dict(zip(['current_bytes','os_peak_bytes'],memory()))})
    print('Independent readback/recovery verified; no completed objects retrained')

if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('mode',choices=['representative','full','verify']); parser.add_argument('--stage-seconds',type=float,required=True)
    args=parser.parse_args(); STAGE_SECONDS=args.stage_seconds
    torch.set_num_threads(4); torch.set_num_interop_threads(1)
    try: globals()[args.mode]()
    except Exception as exc:
        OUT.mkdir(parents=True,exist_ok=True)
        # Preserve failed attempt evidence without pretending an interrupted object completed.
        failure=OUT/('failure_%s_%d.json'%(args.mode,time.time_ns()))
        failure.write_text(json.dumps({'error':repr(exc),'mode':args.mode,'inner_seconds':time.perf_counter()-START,
                                      'process_working_set':dict(zip(['current_bytes','os_peak_bytes'],memory()))},indent=2)+'\n',encoding='utf-8')
        raise
