"""APRIME E02 event diagnostics, NumPy float64; no computations on import."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import time
import numpy as np
Q = np.float64(.4)
P_FLOOR = np.float64(.05)
SEEDS = tuple(2026102100+j for j in range(32))
DELTAS = (4,6)
HISTORIES = (0,64)
METHODS = ('mean','IPW','cache','actual_cached','oracle_cached','full')
ROOT = Path(__file__).resolve().parents[1]
def actual_predictions(past_A, past_R):
    """Freeze from past integer A/R logs ONLY; no true-p argument."""
    a, r = np.asarray(past_A, dtype=np.float64), np.asarray(past_R, dtype=np.float64)
    if a.shape != r.shape or not np.all(np.isfinite(a)) or not np.all(np.isfinite(r)):
        raise ValueError('past A/R must be finite equal-shaped counts')
    if np.any(r < 0) or np.any(a < r) or np.any(a != np.floor(a)) or np.any(r != np.floor(r)):
        raise ValueError('integer counts require 0 <= past_R <= past_A')
    rhat = (1+r)/(2+a)
    return rhat, np.maximum(Q*rhat, P_FLOOR)


def norm2(x):
    return np.einsum('...d,...d->...', x, x, optimize=True)


def _actual(h, old_M, residual, R, ptilde):
    """P-free actual estimation with frozen ptilde and OLD M."""
    w = R.astype(np.float64)/ptilde
    cache = np.sum(old_M, axis=1, dtype=np.float64)
    return {'IPW': w@h, 'cache': cache,
            'actual_cached': cache+np.einsum('si,sid->sd', w, residual, optimize=True)}


def actual_estimators(h, old_M, R, ptilde):
    """P-free helper, M[client,D] or [trajectory,client,D]; never updates M."""
    h, m = np.asarray(h, dtype=np.float64), np.asarray(old_M, dtype=np.float64)
    r, pt = np.asarray(R, dtype=np.bool_), np.asarray(ptilde, dtype=np.float64)
    single = m.ndim == 2
    if single:
        m, r, pt = m[None], r[None], pt[None]
    if h.ndim != 2 or m.ndim != 3 or m.shape[1:] != h.shape or r.shape != m.shape[:2] or pt.shape != r.shape:
        raise ValueError('incompatible estimator shapes')
    if np.any(pt <= 0) or not np.all(np.isfinite(pt)):
        raise ValueError('ptilde must be positive finite')
    result = _actual(h, m, h[None]-m, r, pt)
    return {k: v[0] if single else v for k,v in result.items()}


def _moments(h, m, residual, pt, true_p):
    """DIAGNOSTIC ONLY: merged-client (bias squared norm, variance, MSE)."""
    p = np.asarray(true_p, dtype=np.float64)
    if np.any(p <= 0) or np.any(p > 1):
        raise ValueError('complete-population oracle requires 0 < p <= 1')
    alpha = p[None]/pt-1
    ib = norm2(alpha@h)
    ab = norm2(np.einsum('si,sid->sd', alpha, residual, optimize=True))
    factor = p[None]*(1-p[None])/(pt*pt)
    iv = np.sum(factor*norm2(h)[None], axis=1)
    av = np.sum(factor*norm2(residual), axis=1)
    cb = norm2(np.sum(m,axis=1)-np.sum(h,axis=0)[None])
    ov = np.sum(((1-p)/p)[None]*norm2(residual), axis=1)
    zero = np.zeros(m.shape[0], dtype=np.float64)
    return {'IPW':(ib,iv,ib+iv), 'cache':(cb,zero,cb),
            'actual_cached':(ab,av,ab+av), 'oracle_cached':(zero,ov,ov), 'full':(zero,zero,zero)}


def make_event_arrays(service, rounds):
    """First draw (64+16,20,2) per PCG64 seed, THEN slice every group."""
    s = np.asarray(service, dtype=np.float64)
    if s.shape != (20,) or not np.all(np.isin(s,[1.,4.])) or not 1 <= rounds <= 16:
        raise ValueError('20 service scales 1/4 and 1..16 nodes required')
    u = np.empty((32,80,20,2), dtype=np.float64)
    for j,seed in enumerate(SEEDS):
        u[j] = np.random.Generator(np.random.PCG64(seed)).random((80,20,2),dtype=np.float64)
    a,jitter = u[...,0] < Q, .5+u[...,1]
    r = np.stack([a & (s[None,None]*jitter <= delta) for delta in DELTAS])
    rates = np.stack([np.clip(delta/s-.5,0,1) for delta in DELTAS])
    return {'seeds':np.asarray(SEEDS,dtype=np.int64), 'uniform':u, 'A_all':a, 'R_all':r,
            'future_A':a[:,64:64+rounds].copy(), 'future_R':r[:,:,64:64+rounds].copy(),
            'true_r':rates, 'true_p':Q*rates}


def exact_mean_coefficients(n_ic, true_p, chunk_size=4096):
    """Exact class subsets: E[R_i*N_c/sum_j R_j*n_jc], empty class zero.

    Multiply preweighted class_h by these coefficients. Marginal class
    expectations give final bias, NOT the shared-R cross-class variance.
    """
    n,p = np.asarray(n_ic,dtype=np.float64), np.asarray(true_p,dtype=np.float64)
    if n.ndim != 2 or p.shape != (n.shape[0],) or np.any(p <= 0) or np.any(p > 1) or chunk_size < 1:
        raise ValueError('invalid subset expectation inputs')
    coeff,mass_error = np.zeros(n.shape,dtype=np.float64), 0.
    for c in range(n.shape[1]):
        ii = np.flatnonzero(n[:,c] > 0)
        k = len(ii)
        if not k:
            continue
        shifts,counts,probs = np.arange(k,dtype=np.uint64), n[ii,c], p[ii]
        accum,mass = np.zeros(k,dtype=np.float64), 0.
        for first in range(0,1 << k,chunk_size):
            ids = np.arange(first,min(first+chunk_size,1 << k),dtype=np.uint64)
            bits = ((ids[:,None] >> shifts[None]) & np.uint64(1)).astype(np.bool_)
            ps = np.prod(np.where(bits,probs[None],1-probs[None]),axis=1,dtype=np.float64)
            bf = bits.astype(np.float64)
            den,scale = bf@counts, np.zeros(ids.size,dtype=np.float64)
            np.divide(np.sum(counts),den,out=scale,where=den > 0)
            accum += (ps*scale)@bf
            mass += float(np.sum(ps))
        coeff[ii,c] = accum
        mass_error = max(mass_error,abs(mass-1))
    return coeff,mass_error


def returned_mean(n_ic, class_h, returned):
    """Sum WITHIN class, count-normalize, THEN merge. NO second /100."""
    n,ch = np.asarray(n_ic,dtype=np.float64), np.asarray(class_h,dtype=np.float64)
    r = np.asarray(returned,dtype=np.bool_)
    single = r.ndim == 1
    if single:
        r = r[None]
    if ch.ndim != 3 or n.shape != ch.shape[:2] or r.shape[1:] != (n.shape[0],):
        raise ValueError('incompatible returned-mean shapes')
    merged = np.zeros((r.shape[0],ch.shape[2]),dtype=np.float64)
    for c in range(n.shape[1]):
        ii = np.flatnonzero(n[:,c] > 0)
        if not len(ii):
            continue
        rc = r[:,ii].astype(np.float64)
        numerator,den = rc@ch[ii,c], rc@n[ii,c]
        scale = np.zeros(den.shape,dtype=np.float64)
        np.divide(np.sum(n[:,c]),den,out=scale,where=den > 0)
        merged += numerator*scale[:,None]
    return merged[0] if single else merged


def _mean_expectation(ch, coeff):
    answer = np.zeros(ch.shape[2],dtype=np.float64)
    for c in range(ch.shape[1]):
        ii = np.flatnonzero(coeff[:,c])
        if len(ii):
            answer += coeff[ii,c]@ch[ii,c]
    return answer


def _paired(actual, baseline):
    x,y = np.asarray(actual),np.asarray(baseline)
    diff,am,bm = x-y,float(np.mean(x)),float(np.mean(y))
    md,sd = float(np.mean(diff)),float(np.std(diff,ddof=1))
    se = sd/float(np.sqrt(diff.size))
    reduction = None if bm == 0 else (bm-am)/bm
    return {'actual_mse':am,'baseline_mse':bm,'absolute_reduction':bm-am,
            'relative_reduction':reduction,'passes_10_percent':bool(reduction is not None and reduction >= .10),
            'paired_actual_minus_baseline':diff.tolist(),'paired_mean_difference':md,
            'paired_sample_sd':sd,'paired_standard_error':se,
            'paired_descriptive_95_interval':[md-1.96*se,md+1.96*se],
            'interval_method':'1.96 normal approximation to paired descriptive t interval; no scipy',
            'repeat_unit':'fixed-path event repetitions, NOT independent training seeds'}


def _ratio(num, den):
    return None if float(den) == 0 else float(num)/float(den)


def _groups(a, heads):
    groups,errors,targets = [],a['squared_error'],a['target_squared_norm']
    for d,delta in enumerate(DELTAS):
        for g,history in enumerate(HISTORIES):
            trajectory = np.mean(errors[d,g],axis=1)
            path = np.mean(trajectory,axis=0)
            nodes = []
            for k,position in enumerate(heads):
                methods = {}
                for m,name in enumerate(METHODS):
                    se = float(np.mean(errors[d,g,:,k,m]))
                    methods[name] = {'mean_actual_squared_error':se,
                        'mean_relative_actual_squared_error':_ratio(se,targets[k]),
                        'mean_conditional_bias_norm':float(np.mean(a['conditional_bias_norm'][d,g,:,k,m])),
                        'mean_conditional_bias_squared_norm':float(np.mean(a['conditional_bias_squared_norm'][d,g,:,k,m])),
                        'mean_conditional_variance':None if name == 'mean' else float(np.mean(a['conditional_variance'][d,g,:,k,m])),
                        'mean_conditional_mse':None if name == 'mean' else float(np.mean(a['conditional_mse'][d,g,:,k,m]))}
                covered = a['cache_covered_before'][d,g,:,k]
                age = a['cache_age_before'][d,g,:,k][covered]
                nodes.append({'position':position,'target_squared_norm':float(targets[k]),'methods':methods,
                    'probability_prediction_mse':float(np.mean(a['probability_error'][d,g,:,k]**2)),
                    'conditional_rate_prediction_mse':float(np.mean(a['conditional_rate_error'][d,g,:,k]**2)),
                    'probability_clipped_fraction':float(np.mean(a['probability_clipped'][d,g,:,k])),
                    'never_completed_before_fraction':float(np.mean(a['never_completed_before'][d,g,:,k])),
                    'never_completed_after_fraction':float(np.mean(a['never_completed_after'][d,g,:,k])),
                    'cache_covered_before_fraction':float(np.mean(covered)),
                    'cache_covered_after_fraction':float(np.mean(a['cache_covered_after'][d,g,:,k])),
                    'covered_age_before_mean':None if age.size == 0 else float(np.mean(age)),
                    'covered_age_before_max':None if age.size == 0 else int(np.max(age)),
                    'mean_sum_client_cache_residual_squared_norm':float(np.mean(np.sum(a['cache_residual_squared_norm'][d,g,:,k],axis=1))),
                    'mean_merged_cache_residual_squared_norm':float(np.mean(a['merged_cache_residual_squared_norm'][d,g,:,k])),
                    'empty_return_count':int(np.sum(a['empty_return'][d,:,k]))})
            groups.append({'delta':delta,'history_rounds':history,'nodes':nodes,
                'trajectory_mean_squared_error':{name:trajectory[:,m].tolist() for m,name in enumerate(METHODS)},
                'path_mean_squared_error':{name:float(path[m]) for m,name in enumerate(METHODS)},
                'path_mean_relative_squared_error':{name:None if np.any(targets == 0) else float(np.mean(errors[d,g,:,:,m]/targets[None])) for m,name in enumerate(METHODS)},
                'paired_actual_cached_vs_IPW':_paired(trajectory[:,3],trajectory[:,1]),
                'paired_actual_cached_vs_cache':_paired(trajectory[:,3],trajectory[:,2])})
    return groups

def run_diagnostics(n_ic, tail, heads, node, *, output_prefix=None, check=None):
    """Return (JSON dict, arrays); each node callback ONCE; no files by default.

    Callback returns preweighted h[20,12900], class_h[20,100,12900].
    Optional check() is a parent budget guard; output_prefix saves npz/json.
    """
    started = time.perf_counter()
    n = np.asarray(n_ic,dtype=np.float64)
    if n.shape != (20,100) or not np.all(np.isfinite(n)) or np.any(n < 0) or np.any(n != np.floor(n)):
        raise ValueError('nonnegative integer counts[20,100] required')
    if np.any(np.sum(n,axis=0) <= 0) or np.any(np.sum(n,axis=1) <= 0):
        raise ValueError('empty class/client: stop, no invented denominator')
    t = np.asarray(list(tail),dtype=np.float64)
    if t.ndim != 1 or t.size == 0 or not np.all(np.isfinite(t)) or np.any(t != np.floor(t)) or np.any(t < 0) or np.any(t >= 100):
        raise ValueError('nonempty integer tail indices required')
    t = t.astype(np.int64)
    if len(set(t.tolist())) != t.size:
        raise ValueError('duplicate tail indices')
    heads = list(heads)
    if not 1 <= len(heads) <= 16 or len({json.dumps(x,sort_keys=True,allow_nan=False) for x in heads}) != len(heads):
        raise ValueError('1..16 distinct JSON head positions required')
    z = np.sum(n[:,t],axis=1)/np.sum(n,axis=1)
    slow = np.lexsort((np.arange(20),-z))[:10]
    service = np.ones(20,dtype=np.float64); service[slow] = 4.
    rounds = len(heads)
    a = make_event_arrays(service,rounds)
    a.update(counts=n.copy(),tail=t.copy(),slow_clients=slow.copy(),tail_fraction=z.copy(),service_scale=service.copy())
    metric_shape,client_shape = (2,2,32,rounds,6),(2,2,32,rounds,20)
    for key in ('squared_error','conditional_bias_norm','conditional_bias_squared_norm','conditional_variance','conditional_mse','relative_squared_error'):
        a[key] = np.full(metric_shape,np.nan,dtype=np.float64)
    for key in ('rhat','ptilde','probability_error','conditional_rate_error','cache_residual_squared_norm'):
        a[key] = np.empty(client_shape,dtype=np.float64)
    for key in ('past_A','past_R','cache_age_before','cache_age_after'):
        a[key] = np.empty(client_shape,dtype=np.int64)
    for key in ('probability_clipped','never_completed_before','never_completed_after','cache_covered_before','cache_covered_after'):
        a[key] = np.empty(client_shape,dtype=np.bool_)
    a['merged_cache_residual_squared_norm'] = np.empty((2,2,32,rounds),dtype=np.float64)
    a['target_squared_norm'] = np.empty(rounds,dtype=np.float64)
    a['empty_return'] = ~np.any(a['future_R'],axis=-1)
    a['conditional_variance_known'] = np.array([False,True,True,True,True,True])
    a['conditional_mse_known'] = a['conditional_variance_known'].copy()
    past_a,past_r = np.zeros((2,2,32,20),dtype=np.int64),np.zeros((2,2,32,20),dtype=np.int64)
    for d in range(2):
        past_a[d,1] = np.sum(a['A_all'][:,:64],axis=1,dtype=np.int64)
        past_r[d,1] = np.sum(a['R_all'][d,:,:64],axis=1,dtype=np.int64)
    # Both histories start zero and share future R/h; storage sharing only.
    caches = np.zeros((2,32,20,12900),dtype=np.float64)
    last_seen = np.full((2,32,20),-1,dtype=np.int64)
    coeffs,mass_errors = [],[]
    before = time.perf_counter()
    for d in range(2):
        if check is not None:
            check()
        coeff,mass = exact_mean_coefficients(n,a['true_p'][d])
        coeffs.append(coeff); mass_errors.append(mass)
    a['mean_expectation_coefficients'] = np.stack(coeffs)
    coefficient_seconds = time.perf_counter()-before
    hashes,callback_seconds,aggregation_residuals,aggregation_bounds = [],[],[],[]
    for k in range(rounds):
        if check is not None:
            check()
        # Freeze predictions for ALL groups from PAST logs before this R.
        rhat,ptilde = actual_predictions(past_a,past_r)
        a['rhat'][:,:,:,k],a['ptilde'][:,:,:,k] = rhat,ptilde
        a['past_A'][:,:,:,k],a['past_R'][:,:,:,k] = past_a,past_r
        before = time.perf_counter(); h,ch = node(k)
        callback_seconds.append(time.perf_counter()-before)
        h,ch = np.asarray(h,dtype=np.float64),np.asarray(ch,dtype=np.float64)
        if h.shape != (20,12900) or ch.shape != (20,100,12900) or not np.all(np.isfinite(h)) or not np.all(np.isfinite(ch)):
            raise ValueError('finite h[20,12900], class_h[20,100,12900] required')
        for i in range(20):
            for c in np.flatnonzero(n[i] == 0):
                if np.any(ch[i,c] != 0):
                    raise ValueError('missing classes require class_h zero')
        residual_check = float(np.max(np.abs(h-np.sum(ch,axis=1))))
        scale = float(np.max(np.sum(np.abs(ch),axis=1)))
        bound = 256*np.finfo(np.float64).eps*max(scale,float(np.max(np.abs(h))))
        if residual_check > bound:
            raise ValueError('h != sum class_h: %r exceeds %r' % (residual_check,bound))
        aggregation_residuals.append(residual_check); aggregation_bounds.append(float(bound))
        hashes.append(hashlib.sha256(np.ascontiguousarray(h).tobytes()).hexdigest())
        target = np.sum(h,axis=0); target2 = float(norm2(target)); a['target_squared_norm'][k] = target2
        observed_mean = returned_mean(n,ch,a['future_R'][:,:,k].reshape(64,20)).reshape(2,32,12900)
        mean_b2 = [float(norm2(_mean_expectation(ch,coeffs[d])-target)) for d in range(2)]
        for d in range(2):
            old_M = caches[d]
            residual = h[None]-old_M
            rn,merged_rn = norm2(residual),norm2(np.sum(residual,axis=1))
            returned,invited = a['future_R'][d,:,k],a['future_A'][:,k]
            covered = last_seen[d] >= 0
            ages,p = np.where(covered,k-last_seen[d],-1),a['true_p'][d]
            # True p reaches ONLY the separate oracle/moment diagnostic.
            oracle = np.sum(old_M,axis=1)+np.einsum('si,sid->sd',returned.astype(np.float64)/p[None],residual,optimize=True)
            for g in range(2):
                pt = ptilde[d,g]
                estimates = _actual(h,old_M,residual,returned,pt)
                estimates.update(mean=observed_mean[d],oracle_cached=oracle,full=np.broadcast_to(target,(32,12900)))
                moments = _moments(h,old_M,residual,pt,p)
                for m,name in enumerate(METHODS):
                    se = norm2(estimates[name]-target[None])
                    a['squared_error'][d,g,:,k,m] = se
                    if target2 != 0:
                        a['relative_squared_error'][d,g,:,k,m] = se/target2
                    if name == 'mean':
                        b2 = np.full(32,mean_b2[d])  # variance/MSE UNKNOWN NaN
                    else:
                        b2,variance,mse = moments[name]
                        a['conditional_variance'][d,g,:,k,m] = variance
                        a['conditional_mse'][d,g,:,k,m] = mse
                    a['conditional_bias_squared_norm'][d,g,:,k,m] = b2
                    a['conditional_bias_norm'][d,g,:,k,m] = np.sqrt(b2)
                a['probability_error'][d,g,:,k] = pt-p[None]
                a['conditional_rate_error'][d,g,:,k] = rhat[d,g]-a['true_r'][d][None]
                a['probability_clipped'][d,g,:,k] = Q*rhat[d,g] < P_FLOOR
                a['never_completed_before'][d,g,:,k] = past_r[d,g] == 0
                a['cache_residual_squared_norm'][d,g,:,k] = rn
                a['merged_cache_residual_squared_norm'][d,g,:,k] = merged_rn
                a['cache_covered_before'][d,g,:,k] = covered
                a['cache_age_before'][d,g,:,k] = ages
            # Refresh AFTER both histories and ALL methods used OLD M.
            np.copyto(caches[d],h[None],where=returned[:,:,None])
            last_seen[d] = np.where(returned,k,last_seen[d])
            past_a[d] += invited[None].astype(np.int64); past_r[d] += returned[None].astype(np.int64)
            for g in range(2):
                a['never_completed_after'][d,g,:,k] = past_r[d,g] == 0
                a['cache_covered_after'][d,g,:,k] = last_seen[d] >= 0
                a['cache_age_after'][d,g,:,k] = np.where(last_seen[d] >= 0,k-last_seen[d],-1)
            del old_M,residual,estimates,oracle
        del h,ch,target,observed_mean  # RELEASE this node class tensor
        if check is not None:
            check()
    groups = _groups(a,heads)
    primary = next(g for g in groups if g['delta'] == 4 and g['history_rounds'] == 64)
    dynamic = len(heads) >= 2 and len(set(hashes)) >= 2
    comparison = {'delta':4,'history_rounds':64,'all_positions':heads,
        'aggregation':'ALL nodes mean SE within trajectory, then 32 equal-weight trajectories',
        'path_mean_squared_error':primary['path_mean_squared_error'],
        'trajectory_mean_squared_error':primary['trajectory_mean_squared_error'],
        'actual_cached_vs_IPW':primary['paired_actual_cached_vs_IPW'],
        'actual_cached_vs_cache':primary['paired_actual_cached_vs_cache'],
        'threshold_relative_reduction':.10,
        'zero_baseline_denominator':'None, ratio does not pass; retain absolute difference',
        'zero_target_denominator_positions':[heads[k] for k in range(rounds) if a['target_squared_norm'][k] == 0]}
    ratio_pass = comparison['actual_cached_vs_IPW']['passes_10_percent'] and comparison['actual_cached_vs_cache']['passes_10_percent']
    summary = {'protocol':'APRIME-EXP-v1 E02','dtype':'float64','methods':list(METHODS),
        'qualification':bool(dynamic and ratio_pass),'ratio_criterion_passed':bool(ratio_pass),
        'main_comparison':comparison,'groups':groups,'head_positions':heads,
        'head_gradient_sha256':hashes,'different_gradient_nodes':len(set(hashes)),
        'dynamic_evidence':'tested' if dynamic else 'not_tested: fewer than two different node gradients',
        'slow_clients':slow.tolist(),'tail_classes':t.tolist(),'tail_fraction':z.tolist(),
        'seeds':list(SEEDS),'deltas':list(DELTAS),'history_rounds':list(HISTORIES),
        'history_gradients':'none; cold and 64-log caches BOTH start zero',
        'simulated_history_rounds_per_seed_per_delta':64,'simulated_future_rounds_per_seed_per_delta':rounds,
        'stream_layout':'PCG64[80,20,2] first; col0 invite, col1 jitter=.5+U; histories share future[64:64+N]',
        'prediction_order':'freeze from past; estimate with OLD M; finally refresh logs/cache',
        'cache_storage':'merged M_i per client, histories share identical future caches; no class caches',
        'cache_age_definition':'round-last_future_completion before event; -1 uncovered; after refresh age0',
        'actual_information':'actual_predictions/actual helpers have NO true-p argument; p simulator/oracle/moments only',
        'returned_mean_conditional':'exact class-subset expectation bias; variance/MSE unknown, shared-R cross-class covariance NOT computed',
        'subset_probability_mass_max_residual':mass_errors,
        'client_merge_max_abs_residual':aggregation_residuals,'client_merge_float64_operation_bounds':aggregation_bounds,
        'node_callback_calls':rounds,'node_callback_seconds':callback_seconds,
        'node_callback_accounting':'includes gradient/class_h construction OR identity-checked saved-node readback; each new node once; parent accounts this, NOT free',
        'exact_mean_coefficient_seconds':coefficient_seconds,'module_wall_seconds':time.perf_counter()-started,
        'regularization':'known common term excluded; DATA G errors/denominators only',
        'interpretation':'finite exploratory L-BFGS public pressure path, NOT federated update trajectory; event repeats NOT training seeds; delta6 proxy-zero NOT returned-mean unbiasedness',
        'array_axes':{'metrics':['delta','history','seed','node','method'],'clients':['delta','history','seed','node','client'],
                      'uniform':['seed','80_rounds','client','column'],'future_R':['delta','seed','node','client']},
        'array_missing_values':'NaN only unknown mean conditional variance/MSE and G=0 relative SE; masks included; JSON null'}
    if output_prefix is not None:
        prefix = Path(output_prefix).resolve()
        summary['events_artifact'] = save_event_arrays(prefix.with_suffix('.npz'),a)
        jp = prefix.with_suffix('.json'); jp.parent.mkdir(parents=True,exist_ok=True)
        with jp.open('x',encoding='utf-8',newline='\n') as stream:
            json.dump(summary,stream,ensure_ascii=False,indent=2,allow_nan=False); stream.write('\n')
        if json.loads(jp.read_text(encoding='utf-8')) != summary:
            raise RuntimeError('summary JSON readback differs')
    json.dumps(summary,allow_nan=False)
    return summary,a

def save_event_arrays(path, arrays):
    """Exclusive save + full readback; never silently overwrite evidence."""
    target = Path(path).resolve()
    if target.suffix != '.npz':
        raise ValueError('explicit .npz target required')
    if target.exists():
        raise FileExistsError(str(target))
    target.parent.mkdir(parents=True,exist_ok=True)
    with target.open('xb') as stream:
        np.savez(stream,**arrays)
    with np.load(target,allow_pickle=False) as stored:
        if set(stored.files) != set(arrays):
            raise RuntimeError('npz keys differ on readback')
        for key,value in arrays.items():
            got = stored[key]
            if got.dtype != value.dtype or not np.array_equal(got,value,equal_nan=True):
                raise RuntimeError('npz array differs: '+key)
    digest = hashlib.sha256()
    with target.open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):
            digest.update(block)
    try:
        path_text = target.relative_to(ROOT).as_posix()
    except ValueError:
        path_text = str(target)
    return {'path':path_text,'sha256':digest.hexdigest(),'bytes':target.stat().st_size,
        'readback':'ALL arrays including dtype/shape and NaN unknown markers',
        'arrays':{k:{'shape':list(v.shape),'dtype':str(v.dtype)} for k,v in arrays.items()}}


def diagnose(n_ic, tail, heads, node, *, check=None):
    """E02 adapter: qualification/main_comparison + events.npz; budget guard."""
    parent = (ROOT/'artifacts_local'/'a_prime'/'e02').resolve()
    target = (parent/'events.npz').resolve()
    if target.parent != parent or target.name != 'events.npz':
        raise RuntimeError('unexpected output destination')
    if target.exists():
        raise FileExistsError('parent identity-checked recovery required; do not rerun existing events: '+str(target))
    summary,arrays = run_diagnostics(n_ic,tail,heads,node,check=check)
    if check is not None:
        check()
    summary['events_artifact'] = save_event_arrays(target,arrays)
    if check is not None:
        check()
    return summary

def selfcheck():
    """Parent-callable rational/empty/timing/paired-stream checks; no import run."""
    from fractions import Fraction as F
    hq,mq,pq,ptq = (F(1,2),F(-1,2)),(F(1,4),F(-1,8)),(F(2,5),F(1,5)),(F(3,10),F(1,4))
    exact = {name:[F(0),F(0)] for name in METHODS if name != 'mean'}
    mean_e = F(0)
    for b0 in (0,1):
        for b1 in (0,1):
            bits = (b0,b1)
            prob = (pq[0] if b0 else 1-pq[0])*(pq[1] if b1 else 1-pq[1])
            cache = sum(mq)
            values = {'IPW':sum(bits[i]*hq[i]/ptq[i] for i in range(2)),'cache':cache,
                'actual_cached':cache+sum(bits[i]*(hq[i]-mq[i])/ptq[i] for i in range(2)),
                'oracle_cached':cache+sum(bits[i]*(hq[i]-mq[i])/pq[i] for i in range(2)),'full':sum(hq)}
            for name,value in values.items():
                error = value-sum(hq)
                exact[name][0] += prob*error; exact[name][1] += prob*error*error
            mean_e += prob*(F(0) if not any(bits) else F(b0-b1,b0+b1))
    h,m = np.array([[.5],[-.5]]),np.array([[.25],[-.125]])
    p,pt = np.array([.4,.2]),np.array([[.3,.25]])
    moments,errors = _moments(h,m[None],h[None]-m[None],pt,p),{}
    for name,(bias,mse) in exact.items():
        b2,var,predicted_mse = moments[name]
        ref = np.array([float(bias*bias),float(mse-bias*bias),float(mse)])
        got = np.array([b2[0],var[0],predicted_mse[0]])
        if not np.allclose(ref,got,rtol=0,atol=2e-15):
            raise AssertionError('rational moment failure: '+name)
        errors[name] = float(np.max(np.abs(ref-got)))
    n,ch = np.ones((2,1)),h[:,None,:]
    coeff,mass = exact_mean_coefficients(n,p)
    if mean_e != F(1,5) or abs(float(_mean_expectation(ch,coeff)[0])-float(mean_e)) > 2e-15:
        raise AssertionError('finite returned mean must be rational 1/5')
    unequal = np.array([[9.],[1.]])
    uc,_ = exact_mean_coefficients(unequal,np.array([.4,.4]))
    beta = uc[:,0]*unequal[:,0]/10/(1-.6**2)
    if not np.allclose(beta,[.6,.4],rtol=0,atol=2e-15):
        raise AssertionError('same-p unequal-count returned-mean boundary failed')
    empty = np.zeros(2,dtype=np.bool_)
    ev = actual_estimators(h,m,empty,pt[0])
    if np.any(returned_mean(n,ch,empty) != 0) or np.any(ev['IPW'] != 0):
        raise AssertionError('empty mean/IPW not zero')
    if not np.array_equal(ev['cache'],np.sum(m,axis=0)) or not np.array_equal(ev['actual_cached'],np.sum(m,axis=0)):
        raise AssertionError('empty cache must retain OLD M')
    pa,pr = np.zeros(2,dtype=np.int64),np.zeros(2,dtype=np.int64)
    frozen_r,frozen_p = actual_predictions(pa,pr)
    old,ret = np.zeros_like(h),np.array([True,False])
    estimate = actual_estimators(h,old,ret,frozen_p)
    np.copyto(old,h,where=ret[:,None]); pa += [1,1]; pr += ret.astype(np.int64)
    next_r,next_p = actual_predictions(pa,pr)
    if not np.array_equal(frozen_r,[.5,.5]) or not np.array_equal(frozen_p,[.2,.2]):
        raise AssertionError('frozen cold prediction wrong/mutated')
    if not np.array_equal(estimate['cache'],[0.]) or not np.array_equal(estimate['actual_cached'],h[0]/.2):
        raise AssertionError('cache refreshed too early')
    if not np.allclose(next_r,[2/3,1/3]) or np.array_equal(next_p,frozen_p):
        raise AssertionError('next prediction failed to use past logs')
    cr,cp = actual_predictions([40],[0])
    if cp[0] != P_FLOOR or not Q*cr[0] < P_FLOOR:
        raise AssertionError('floor failure')
    service = np.ones(20); service[:10] = 4.
    events = make_event_arrays(service,2)
    ref = np.random.Generator(np.random.PCG64(SEEDS[0])).random((80,20,2),dtype=np.float64)
    if not np.array_equal(events['uniform'][0],ref):
        raise AssertionError('PCG64 layout changed')
    if not np.array_equal(events['future_A'],events['A_all'][:,64:66]) or not np.array_equal(events['future_R'],events['R_all'][:,:,64:66]):
        raise AssertionError('cold/64 future not paired')
    if not np.array_equal(events['R_all'][1],events['A_all']) or np.any(events['R_all'][0] & ~events['R_all'][1]):
        raise AssertionError('delta6 or paired delta nesting failed')
    zero = _paired(np.zeros(32),np.zeros(32))
    if zero['relative_reduction'] is not None or zero['passes_10_percent']:
        raise AssertionError('zero denominator falsely qualifies')
    return {'status':'passed','rational_max_absolute_moment_errors':errors,
        'rational_returned_mean_expectation':'1/5','subset_probability_mass_residual':mass,
        'same_p_conditional_unequal_count_weights':beta.tolist(),
        'empty_return':'mean/IPW zero; cached retains OLD M',
        'timing':'past prediction frozen; estimate then refresh; next prediction uses updated logs',
        'paired_stream':'32 PCG64 80x20x2 streams; both histories future slice64; deltas nested',
        'zero_denominator':'None, cannot pass ratio','scientific_experiments_added':False}


if __name__ == '__main__':
    print(json.dumps(selfcheck(),ensure_ascii=False,indent=2,allow_nan=False))
