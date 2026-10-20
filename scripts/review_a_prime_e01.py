"""Directed Reviewer reduction of sealed E01 vectors; no training or resampling.
Enumerates only class holders to distinguish finite-return means from E01's proxy.
Not an additional qualification gate or confirmation experiment.
"""
import time
START = time.perf_counter()
from pathlib import Path
import hashlib
import json
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'artifacts/a_prime/e01/reviewer_check.json'
assert not OUT.exists(), 'Do not repeat a completed review reduction'

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def load(p):
    return json.loads(p.read_text(encoding='utf-8'))

result_path = ROOT / 'artifacts/a_prime/e01/results.json'
result = load(result_path)
state = load(ROOT / 'artifacts/a_prime/e01/state.json')
summary = load(ROOT / 'artifacts/a_prime/e01/summary.json')
assert sha(result_path) == state['result_sha256'] == summary['results_sha256']
counts_path = ROOT / 'artifacts/direction_a/phase0_2_v1/tasks/FedPCC-0.2-candidate-CIFAR100-N20-v1/counts.json'
assert sha(counts_path) == result['identity']['task_counts_sha256']
counts = load(counts_path)
n = np.asarray(counts['n_ic'], dtype=np.int64)
N = np.asarray(counts['N_c'], dtype=np.int64)
assert np.array_equal(n.sum(axis=0), N)
a = n / N
by_class = [[] for _ in range(100)]
for i, unit in enumerate(state['sources']):
    assert unit['status'] == 'complete'
    record = unit['record']
    pth = ROOT / record['decoded_path']
    assert sha(pth) == record['decoded_sha256']
    with np.load(pth, allow_pickle=False) as packet:
        ids, gradients = packet['class_ids'], packet['gradients']
        assert np.array_equal(ids, np.flatnonzero(n[i]))
        for c, g in zip(ids, gradients):
            by_class[int(c)].append((i, g.copy()))
vector_path = ROOT / result['vectors']['path']
assert sha(vector_path) == result['vectors']['sha256']
with np.load(vector_path, allow_pickle=False) as saved:
    target = saved['G_c'].copy()
    proxy = saved['d_c'].copy()

# Scalar reference positive example, empty return set is exactly zero.
def subset_weights(cnt, p):
    k = len(cnt)
    assert k <= 20
    bits = ((np.arange(1 << k, dtype=np.uint32)[:, None] >> np.arange(k)) & 1).astype(np.float64)
    prob = np.prod(np.where(bits == 1, p, 1-p), axis=1)
    den = bits @ cnt
    w = np.divide(bits * cnt, den[:, None], out=np.zeros_like(bits), where=den[:, None] > 0)
    beta = prob @ w
    empty = float(np.prod(1-p))
    assert abs(prob.sum()-1) < 1e-13
    assert abs(beta.sum() - (1-empty)) < 1e-13
    return beta, empty

b, e = subset_weights(np.array([1, 1]), np.array([.4, .2]))
assert abs(float(b @ np.array([1., -1.])) - .2) < 1e-15
# Equal probabilities and unequal source counts need not yield target weights even conditional on nonempty.
b0, e0 = subset_weights(np.array([9, 1]), np.array([.4, .4]))
assert not np.allclose(b0/(1-e0), np.array([.9, .1]))

checks = []
for j in (1, 3):  # fixed primary deadline 4, homogeneous probability deadline 6
    p = np.asarray(result['identity']['conditions'][j]['p'])
    actual_bias = np.zeros_like(target)
    conditional_bias = np.zeros_like(target)
    recomputed_proxy = np.zeros_like(target)
    rows = []
    for c, source_rows in enumerate(by_class):
        ids = np.array([i for i, _ in source_rows])
        gs = np.stack([g for _, g in source_rows])
        beta, empty = subset_weights(n[ids, c], p[ids])
        weights = a[ids, c]
        gc = weights @ gs
        assert np.max(np.abs(gc - target[c])) < 1e-12
        actual_bias[c] = (beta - weights) @ gs
        conditional_bias[c] = (beta/(1-empty) - weights) @ gs
        recomputed_proxy[c] = (weights * p[ids] / np.dot(weights, p[ids]) - weights) @ gs
        rows.append({'class_id': c, 'holders': ids.tolist(), 'expected_return_normalized_weights': beta.tolist(),
                     'empty_probability': empty, 'finite_return_bias_L2': float(np.linalg.norm(actual_bias[c]))})
    residual = float(np.max(np.abs(recomputed_proxy-proxy[j])))
    assert residual < 1e-12
    def metrics(arr, ids):
        rms = float(np.sqrt(np.mean(np.sum(arr[ids]**2, axis=1))))
        denominator = float(np.sqrt(np.mean(np.sum(target[ids]**2, axis=1))))
        return {'class_count': len(ids), 'bias_RMS': rms, 'target_RMS': denominator, 'relative_RMS': rms/denominator}
    full_g = target.mean(axis=0)
    full_b = actual_bias.mean(axis=0)
    checks.append({'mapping': 'primary', 'deadline': int(result['conditions'][j]['deadline']),
                   'proxy_vector_max_abs_residual': residual,
                   'finite_return_all_classes': metrics(actual_bias, list(range(100))),
                   'finite_return_tail_classes': metrics(actual_bias, counts['class_groups']['tail']),
                   'equal_class_mean_finite_return_bias_L2': float(np.linalg.norm(full_b)),
                   'equal_class_mean_target_L2': float(np.linalg.norm(full_g)),
                   'equal_class_mean_relative_finite_return_bias': float(np.linalg.norm(full_b)/np.linalg.norm(full_g)),
                   'conditional_nonempty_all_classes_description_only': metrics(conditional_bias, list(range(100))),
                   'classes': rows})
payload = {'scope': 'Reviewer directed verification of E01 proxy and exact finite-return expectation, not method utility or independent confirmation',
           'review_input_commit': '3253a89063637836f0dcabcd95f9169da05cfb26',
           'results_sha256': sha(result_path), 'vectors_sha256': sha(vector_path),
           'implementation_sha256': sha(Path(__file__)),
           'definition': 'beta_ic = sum_S P(S) 1{i in S} n_ic / sum_{j in S} n_jc; empty class gradient zero; aggregate all 100 classes equally',
           'exact_enumeration': 'all independent return subsets of each class holder set; float64 arithmetic, no Monte Carlo',
           'max_holders_per_class': int((n > 0).sum(axis=0).max()),
           'positive_example_expected_ratio': .2,
           'equal_p_unequal_count_counterexample': {'counts': [9, 1], 'p': [.4, .4], 'target_weights': [.9, .1],
                                                  'finite_weights': b0.tolist(), 'conditional_nonempty_weights': (b0/(1-e0)).tolist()},
           'conditions': checks,
           'models_trained': 0, 'events_resampled': 0, 'images_or_predictions_read': 0,
           'inner_program_wall_seconds': time.perf_counter()-START}
OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False)+'\n', encoding='utf-8')
assert load(OUT) == payload
print(json.dumps({k: v for k, v in payload.items() if k != 'conditions'}, ensure_ascii=False))
for condition in checks:
    print(json.dumps({k: v for k, v in condition.items() if k != 'classes'}, ensure_ascii=False))
print('reviewer_check_bytes', OUT.stat().st_size)
print('wall_seconds_including_save_readback', time.perf_counter()-START)
