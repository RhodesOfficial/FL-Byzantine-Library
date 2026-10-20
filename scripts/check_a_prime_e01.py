"""APRIME-EXP-v1 E01: fixed C100 r80 source diagnostic, no model/data access.
Run through run_a_prime_e01.ps1 so process startup and receipt I/O share the limit.
"""
import time
START = time.perf_counter()
import argparse
import ctypes
from ctypes import wintypes
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import threading
import zipfile
import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'artifacts/a_prime/e01'
LOCAL = ROOT / 'artifacts_local/a_prime/e01'
META = LOCAL / 'metadata'
REF = 'A-backbone-CIFAR100-s2026101322-r0080-v1'
PACKAGE = 'artifacts/direction_a/phaseG1_2_full_v1'
SOURCE = 'ba9b542'
INPUT = 'b9e83363e5d74589454a26f812b13ece839f8d36'
TASK = ROOT / 'artifacts/direction_a/phase0_2_v1/tasks/FedPCC-0.2-candidate-CIFAR100-N20-v1'
CONDITIONS = [('primary', 3), ('primary', 4), ('primary', 5), ('primary', 6), ('shuffled', 4)]
K = 100 * 129
LIMIT_BYTES = 256 * 1024**2
EPS = np.finfo(np.float64).eps


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def save_json(path, value, exclusive=True):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if exclusive and path.exists():
        raise FileExistsError(str(path))
    temp = path.with_name(path.name + '.tmp')
    # Verify both absolute move targets are the intended project output paths before replacement.
    assert any(base.resolve() in path.resolve().parents and base.resolve() in temp.resolve().parents for base in (OUT, LOCAL))
    with temp.open('w', encoding='utf-8', newline='\n') as f:
        json.dump(value, f, indent=2, ensure_ascii=False, allow_nan=False)
        f.write('\n')
        f.flush()
        os.fsync(f.fileno())
    if read_json(temp) != value:
        raise RuntimeError('JSON readback differs: ' + str(path))
    temp.replace(path)
    assert read_json(path) == value


def size_all():
    return sum(p.stat().st_size for root in (OUT, LOCAL) for p in root.rglob('*') if p.is_file())


class Memory(ctypes.Structure):
    _fields_ = [('cb', wintypes.DWORD), ('PageFaultCount', wintypes.DWORD)] + [
        (n, ctypes.c_size_t) for n in ('PeakWorkingSetSize', 'WorkingSetSize', 'QuotaPeakPagedPoolUsage',
         'QuotaPagedPoolUsage', 'QuotaPeakNonPagedPoolUsage', 'QuotaNonPagedPoolUsage',
         'PagefileUsage', 'PeakPagefileUsage')]


def memory():
    if os.name != 'nt':
        raise RuntimeError('This entry uses Windows process working-set accounting')
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    api = ctypes.WinDLL('psapi', use_last_error=True).GetProcessMemoryInfo
    api.argtypes = [wintypes.HANDLE, ctypes.POINTER(Memory), wintypes.DWORD]
    m = Memory()
    m.cb = ctypes.sizeof(m)
    if not api(kernel.GetCurrentProcess(), ctypes.byref(m), m.cb):
        raise ctypes.WinError(ctypes.get_last_error())
    return int(m.WorkingSetSize), int(m.PeakWorkingSetSize)


class Guard:
    def __init__(self, seconds):
        self.seconds = seconds
        self.working_max = 0
        self.peak = 0
        self.failure = None
        self.done = threading.Event()
        self.thread = threading.Thread(target=self.watch, daemon=True)
        self.thread.start()

    def watch(self):
        while not self.done.wait(0.05):
            try:
                current, peak = memory()
                self.working_max = max(self.working_max, current)
                self.peak = max(self.peak, peak)
                if peak > 8 * 1024**3:
                    self.failure = '8 GiB process working-set limit exceeded'
                if time.perf_counter() - START > self.seconds:
                    self.failure = 'stage time limit exceeded'
            except Exception as exc:
                self.failure = str(exc)

    def check(self):
        if self.failure:
            raise RuntimeError(self.failure)
        if size_all() > LIMIT_BYTES:
            raise RuntimeError('256 MiB local artifact limit exceeded')
        if time.perf_counter() - START > self.seconds:
            raise RuntimeError('stage time limit exceeded')

    def finish(self):
        self.check()
        self.done.set()
        self.thread.join()
        current, peak = memory()
        self.working_max = max(self.working_max, current)
        self.peak = max(self.peak, peak)
        return {'sampled_current_working_set_max_bytes': self.working_max,
                'windows_process_peak_working_set_bytes': self.peak,
                'memory_scope': 'Windows GetProcessMemoryInfo of this process; OS peak includes cold startup, not a Job or GPU peak',
                'sampling_interval_seconds': 0.05,
                'gpu_used': False, 'external_paid_cost': 0}


def inputs():
    hashes = read_json(META / 'artifact_hashes.json')['files']
    for name in ('reference_acceptance.json', 'preregistration.json'):
        if sha(META / name) != hashes[name]:
            raise RuntimeError('historical metadata hash mismatch')
    prereg = read_json(META / 'preregistration.json')
    for name, key in [('class_gradient_full.py', 'direction_a/class_gradient_full.py'),
                      ('measure_direction_a_class_gradient_full.py', 'scripts/measure_direction_a_class_gradient_full.py')]:
        if sha(META / name) != prereg['source_fingerprints'][key]:
            raise RuntimeError('affected serializer code identity mismatch')
    entries = read_json(META / 'reference_acceptance.json')['references']
    entry = next(e for e in entries if e['reference']['reference_id'] == REF)
    reference = entry['reference']
    if next(r for r in prereg['references'] if r['reference_id'] == REF) != reference:
        raise RuntimeError('reference binding mismatch')
    binding = entry['binding']
    counts = read_json(TASK / 'counts.json')
    info = read_json(TASK / 'info.json')
    for name in ('counts.json', 'info.json'):
        if sha(TASK / name) != binding['source_files'][name]['sha256']:
            raise RuntimeError('task identity mismatch')
    if sha(TASK / 'counts.json') != info['artifact_sha256']['counts.json']:
        raise RuntimeError('count/info hash mismatch')
    n = np.asarray(counts['n_ic'], dtype=np.int64)
    totals = np.asarray(counts['N_c'], dtype=np.int64)
    assert n.shape == (20, 100) and np.all(n.sum(axis=1) > 0)
    assert np.array_equal(n.sum(axis=0), totals) and np.all(totals > 0)
    assert binding['label_mapping'] == {str(c): c for c in range(100)}
    startup = read_json(ROOT / 'artifacts/a_prime/s00/startup_check.json')
    s00 = next(t for t in startup['tasks'] if t['classes'] == 100)
    assert startup['e01_minimum_structure_eligible'] and s00['counts_sha256'] == sha(TASK / 'counts.json')
    assert s00['tail_classes'] == counts['class_groups']['tail'] == binding['class_groups']['tail']
    probabilities = []
    for mapping, deadline in CONDITIONS:
        rates = startup['rates'][str(deadline)]
        fast, slow = (float(__import__('fractions').Fraction(rates[k])) for k in ('fast', 'slow'))
        probabilities.append(np.array([slow if i in s00[mapping]['slow_clients'] else fast for i in range(20)]))
    # Only the selected reference tree is listed, and only its twenty source files are extracted.
    listing = subprocess.run(['git', 'ls-tree', '-l', f'{SOURCE}:{PACKAGE}/messages/{REF}/'],
                             stdout=subprocess.PIPE, check=True, text=True).stdout
    sizes = {line.split('\t')[1]: int(line.split('\t')[0].split()[-1]) for line in listing.splitlines()}
    assert set(sizes) == {f'client_{i:03d}.pt' for i in range(20)}
    identity = {'protocol': 'APRIME-EXP-v1', 'execution_input_commit': INPUT,
                'reference': reference, 'source_commit': SOURCE, 'package': PACKAGE,
                'protocol_sha256': sha(ROOT / 'docs/projects/a_prime/PROTOCOL.md'),
                's00_sha256': sha(ROOT / 'artifacts/a_prime/s00/startup_check.json'),
                'task_counts_sha256': sha(TASK / 'counts.json'),
                'task_info_sha256': sha(TASK / 'info.json'),
                'metadata_sha256': {p.name: sha(p) for p in META.iterdir() if p.is_file()},
                'conditions': [{'mapping': m, 'deadline': d, 'p': p.tolist()} for (m, d), p in zip(CONDITIONS, probabilities)]}
    return n, totals, counts['class_groups']['tail'], s00, probabilities, hashes, sizes, identity


def verify_packet(packet, i, n, reference):
    active = np.flatnonzero(n[i]).tolist()
    missing = np.flatnonzero(n[i] == 0).tolist()
    assert packet['reference_id'] == REF and packet['state_sha256'] == reference['state_sha256']
    assert packet['client_id'] == i and packet['C'] == 100 and packet['d'] == 128 and packet['bias'] is True
    assert packet['class_ids'] == active and packet['missing_class_ids'] == missing
    assert set(packet['gradients']) == set(active)
    assert packet['denominators'] == {c: int(n[i, c]) for c in active}
    rows = []
    for c in active:
        w, b = packet['gradients'][c]
        assert w.shape == (100, 128) and b.shape == (100,)
        assert w.dtype == b.dtype == torch.float32 and w.device.type == b.device.type == 'cpu'
        row = np.concatenate([w.numpy().reshape(-1), b.numpy()]).astype(np.float64)
        assert row.shape == (K,) and np.isfinite(row).all()
        rows.append(row)
    return np.array(active, dtype=np.int64), np.stack(rows)


def source_unit(i, n, totals, probabilities, hashes, sizes, identity, guard):
    t = time.perf_counter()
    rel = f'messages/{REF}/client_{i:03d}.pt'
    raw = LOCAL / 'sources' / f'client_{i:03d}.pt'
    raw.parent.mkdir(parents=True, exist_ok=True)
    # Called only for incomplete units. A interrupted extraction may leave an invalid partial file.
    raw_valid = raw.exists() and raw.stat().st_size == sizes[raw.name] and sha(raw) == hashes[rel]
    if not raw_valid:
        if size_all() + sizes[raw.name] > LIMIT_BYTES:
            raise RuntimeError('input extraction exceeds artifact budget')
        with raw.open('wb') as f:
            subprocess.run(['git', 'show', f'{SOURCE}:{PACKAGE}/{rel}'], stdout=f, check=True)
    assert raw.stat().st_size == sizes[raw.name] and sha(raw) == hashes[rel]
    packet = torch.load(raw, map_location='cpu', weights_only=True)
    ids, g = verify_packet(packet, i, n, identity['reference'])
    a = n / totals
    # The representative computes contributions, not a scientific full-class bias from one client.
    for p in probabilities:
        z = (a * p[:, None]).sum(axis=0)
        contribution = ((a[i, ids] * p[i] / z[ids] - a[i, ids])[:, None] * g)
        assert np.isfinite(contribution).all()
    dest = LOCAL / 'decoded' / f'client_{i:03d}.npz'
    dest.parent.mkdir(parents=True, exist_ok=True)
    decoded_valid = False
    if dest.exists():
        try:
            with np.load(dest, allow_pickle=False) as previous:
                decoded_valid = np.array_equal(previous['class_ids'], ids) and np.array_equal(previous['gradients'], g)
        except (ValueError, OSError, EOFError, KeyError, zipfile.BadZipFile):
            pass
    if not decoded_valid:
        # Only a not-yet-complete decoded artifact can be repaired; complete ones were hash-checked and skipped.
        needed = g.nbytes + ids.nbytes + 65536
        if size_all() + needed - (dest.stat().st_size if dest.exists() else 0) > LIMIT_BYTES:
            raise RuntimeError('decoded save would exceed artifact budget')
        with dest.open('wb') as f:
            np.savez(f, class_ids=ids, gradients=g)
    with np.load(dest, allow_pickle=False) as restored:
        assert np.array_equal(restored['class_ids'], ids) and np.array_equal(restored['gradients'], g)
    guard.check()
    return {'client_id': i, 'source_path': str(raw.relative_to(ROOT)).replace('\\', '/'),
            'source_sha256': sha(raw), 'source_bytes': raw.stat().st_size,
            'decoded_path': str(dest.relative_to(ROOT)).replace('\\', '/'),
            'decoded_sha256': sha(dest), 'decoded_bytes': dest.stat().st_size,
            'positive_class_count': len(ids), 'seconds_including_save_readback': time.perf_counter()-t}


def verify_state(state, identity):
    assert state['identity'] == identity
    assert len(state['sources']) == 20
    for i, unit in enumerate(state['sources']):
        assert unit['status'] in ('complete', 'partial', 'not_started')
        if unit['status'] == 'complete':
            row = unit['record']
            assert row['client_id'] == i
            for name in ('source', 'decoded'):
                path = (ROOT / row[name + '_path']).resolve()
                assert LOCAL.resolve() in path.parents
                assert sha(path) == row[name + '_sha256']
        else:
            assert 'record' not in unit
    return [i for i, unit in enumerate(state['sources']) if unit['status'] == 'complete']


def tests():
    # Sign and denominator, including equal-probability and equal-gradient controls.
    a = np.array([0.5, 0.5]); g = np.array([1., -1.]); p = np.array([.4, .2])
    d = np.dot(a*p, g)/np.dot(a, p) - np.dot(a, g)
    assert math.isclose(d, 1/3, abs_tol=1e-15)
    assert np.dot(a*.4, g)/.4 - np.dot(a, g) == 0
    assert abs(np.dot(a*p, np.ones(2))/np.dot(a, p)-1) < 1e-15
    # A missing/nonmatching class, count or reference is rejected without invoking legacy acceptance.
    n = np.zeros((20, 100), dtype=np.int64); n[0, 3] = 2
    ref = {'state_sha256': 'test'}
    packet = {'reference_id': REF, 'state_sha256': 'test', 'client_id': 0, 'C': 100, 'd': 128,
              'bias': True, 'class_ids': [3], 'missing_class_ids': [c for c in range(100) if c != 3],
              'denominators': {3: 2}, 'gradients': {3: (torch.ones((100,128)), torch.ones(100))}}
    ids, rows = verify_packet(packet, 0, n, ref)
    assert ids.tolist() == [3] and rows.shape == (1, K) and rows.dtype == np.float64
    rejected = 0
    for key, value in [('denominators', {3: 1}), ('state_sha256', 'wrong'), ('class_ids', [4])]:
        bad = dict(packet); bad[key] = value
        try:
            verify_packet(bad, 0, n, ref)
        except AssertionError:
            rejected += 1
    assert rejected == 3
    return {'positive_case': {'d': d, 'expected': '1/3'}, 'zero_controls': True,
            'layout_and_dtype': True, 'bad_count_reference_class_rejections': rejected}


def diagnostic(g, n, totals, tail, s00, probabilities, guard):
    a = n / totals
    targets = np.sum(a[:, :, None] * g, axis=0)
    # Independent scalar math.fsum for every stored target coordinate, not a vectorized duplicate.
    target_residual_max = 0.0
    target_tolerance_max = 0.0
    for c in range(100):
        holders = np.flatnonzero(n[:, c])
        ref = np.fromiter((math.fsum(float(a[i,c])*float(g[i,c,k]) for i in holders) for k in range(K)), dtype=np.float64, count=K)
        diff = float(np.max(np.abs(ref-targets[c])))
        tol = 128*EPS * float(np.max(np.sum(a[:,c,None]*np.abs(g[:,c]), axis=0)))
        assert diff <= tol
        target_residual_max = max(target_residual_max, diff)
        target_tolerance_max = max(target_tolerance_max, tol)
    target_norms = np.linalg.norm(targets, axis=1)
    dispersion = np.sqrt(np.sum(a * np.sum((g-targets[None,:,:])**2, axis=2), axis=0))
    all_arrays = []
    reports = []
    gamma = 128 * EPS / (1-128*EPS)
    for (mapping, deadline), p in zip(CONDITIONS, probabilities):
        z = np.sum(a*p[:, None], axis=0)
        weights = a*p[:,None]/z
        d = np.sum(weights[:,:,None]*g, axis=0)-targets
        classes = []
        for c in range(100):
            holders = np.flatnonzero(n[:,c])
            scalar_z_count = math.fsum(float(n[i,c])*float(p[i]) for i in holders)
            scalar_coeff = {i: float(n[i,c])*float(p[i])/scalar_z_count-float(n[i,c])/float(totals[c]) for i in holders}
            scalar = np.fromiter((math.fsum(scalar_coeff[i]*float(g[i,c,k]) for i in holders)
                         for k in range(K)), dtype=np.float64, count=K)
            residual = float(np.max(np.abs(d[c]-scalar)))
            bound = gamma*np.sum((np.abs(weights[:,c])+a[:,c])[:,None]*np.abs(g[:,c]), axis=0)
            linf_tol = float(np.max(bound))
            norm = float(np.linalg.norm(d[c]))
            l2_tol = float(np.linalg.norm(bound)) + (2*K*EPS)*norm
            assert residual <= linf_tol
            structure_zero = len(set(p[holders].tolist())) == 1
            if structure_zero:
                assert norm <= l2_tol
            slow = s00[mapping]['slow_clients']
            classes.append({'class_id': c, 'N_c': int(totals[c]), 'source_count': len(holders),
                            'fast_sample_count': int(sum(n[i,c] for i in holders if i not in slow)),
                            'slow_sample_count': int(sum(n[i,c] for i in holders if i in slow)),
                            'Z_c': float(z[c]), 'G_c_L2': float(target_norms[c]),
                            'gradient_dispersion_weighted_RMS': float(dispersion[c]),
                            'd_c_L2': norm, 'arithmetic_Linf_tolerance': linf_tol,
                            'arithmetic_L2_tolerance': l2_tol, 'scalar_reference_max_abs_residual': residual,
                            'structural_zero_same_probability_sources': structure_zero,
                            'arithmetic_resolved_nonzero': norm > l2_tol})
            guard.check()
        norms = np.array([r['d_c_L2'] for r in classes])
        def summary(ids):
            rms = float(np.sqrt(np.mean(norms[ids]**2)))
            den = float(np.sqrt(np.mean(target_norms[ids]**2)))
            return {'class_denominator': len(ids), 'bias_RMS': rms, 'target_RMS': den,
                    'relative_RMS': rms/den if den != 0 else None,
                    'mixed_probability_source_class_count': sum(not classes[c]['structural_zero_same_probability_sources'] for c in ids),
                    'arithmetic_resolved_nonzero_class_count': sum(classes[c]['arithmetic_resolved_nonzero'] for c in ids),
                    'weighted_gradient_dispersion_RMS': float(np.sqrt(np.mean(dispersion[ids]**2)))}
        reports.append({'mapping': mapping, 'deadline': deadline, 'all_classes': summary(list(range(100))),
                        'tail_classes': summary(tail), 'classes': classes})
        all_arrays.append(d)
    return targets, np.stack(all_arrays), reports, {'target_scalar_max_abs_residual': target_residual_max,
                                                   'target_arithmetic_Linf_tolerance_max': target_tolerance_max}


def main(args):
    torch.set_num_threads(1)
    guard = Guard(args.stage_seconds)
    OUT.mkdir(parents=True, exist_ok=True)
    if args.mode == 'test':
        save_json(OUT/'implementation_checks.json', tests())
    else:
        n, totals, tail, s00, probabilities, hashes, sizes, identity = inputs()
        state_path = OUT / 'state.json'
        if args.mode == 'representative':
            if state_path.exists():
                raise FileExistsError('representative already exists')
            state = {'identity': identity, 'sources': [{'status': 'not_started'} for _ in range(20)],
                     'conditions': [{'mapping': m, 'deadline': d, 'status': 'not_started'} for m,d in CONDITIONS]}
            state['sources'][0] = {'status': 'partial'}
            save_json(state_path, state)
            first_row = source_unit(0, n, totals, probabilities, hashes, sizes, identity, guard)
            # Read back a real partial state after files are saved but before the complete marker.
            assert verify_state(read_json(state_path), identity) == []
            row = source_unit(0, n, totals, probabilities, hashes, sizes, identity, guard)
            assert row['source_sha256'] == first_row['source_sha256'] and row['decoded_sha256'] == first_row['decoded_sha256']
            state['sources'][0] = {'status': 'complete', 'record': row}
            # Intentional boundary pause, not an error or a rerun caused by scores.
            state['sources'][1] = {'status': 'partial'}
            save_json(state_path, state, exclusive=False)
            restored = read_json(state_path)
            assert verify_state(restored, identity) == [0]
            estimate = {'source_file_bytes': sum(sizes.values()), 'source_file_max_bytes': max(sizes.values()),
                        'positive_source_class_units': int((n>0).sum()),
                        'decoded_numpy_bytes': int((n>0).sum())*K*8,
                        'result_numpy_bytes': 6*100*K*8,
                        'source_unit': first_row, 'partial_resume_unit': row, 'partial_resume_verified': True,
                        'saved_partial_files_preserved_bitwise': True,
                        'scope': 'one source contribution; not a full-class scientific result',
                        'remaining_sources': list(range(1,20))}
            save_json(OUT/'representative.json', estimate)
        elif args.mode == 'full' and (OUT/'results.json').exists():
            # Result publication preceded a crash before completion marking/receipt: only finalize identities.
            state = read_json(state_path)
            assert verify_state(state, identity) == list(range(20))
            result = read_json(OUT/'results.json')
            assert result['identity'] == identity
            assert sha(ROOT/result['vectors']['path']) == result['vectors']['sha256']
            for cond in state['conditions']:
                cond['status'] = 'complete'
            state['result_sha256'] = sha(OUT/'results.json')
            state['vectors_sha256'] = result['vectors']['sha256']
            save_json(state_path, state, exclusive=False)
        elif args.mode == 'full':
            plan = read_json(OUT/'plan.json')
            assert plan['identity'] == identity and plan['budget_covers_complete_remaining_cycle']
            state = read_json(state_path)
            completed = verify_state(state, identity)
            before = {i: state['sources'][i]['record']['decoded_sha256'] for i in completed}
            for i in range(20):
                if i in completed:
                    continue
                state['sources'][i] = {'status': 'partial'}
                save_json(state_path, state, exclusive=False)
                record = source_unit(i,n,totals,probabilities,hashes,sizes,identity,guard)
                state['sources'][i] = {'status': 'complete', 'record': record}
                save_json(state_path, state, exclusive=False)
            assert verify_state(state, identity) == list(range(20))
            g = np.zeros((20,100,K), dtype=np.float64)
            for i in range(20):
                record = state['sources'][i]['record']
                with np.load(ROOT/record['decoded_path'], allow_pickle=False) as loaded:
                    ids = loaded['class_ids']
                    assert ids.tolist() == np.flatnonzero(n[i]).tolist()
                    g[i, ids] = loaded['gradients']
            for cond in state['conditions']:
                cond['status'] = 'partial'
            save_json(state_path, state, exclusive=False)
            t = time.perf_counter()
            targets, biases, reports, target_checks = diagnostic(g,n,totals,tail,s00,probabilities,guard)
            computation = time.perf_counter()-t
            vectors = LOCAL/'result_vectors.npz'
            if vectors.exists():
                # An unpublished partial condition is resumable; preserve matching saved vectors.
                with np.load(vectors, allow_pickle=False) as prior:
                    assert np.array_equal(prior['G_c'], targets) and np.array_equal(prior['d_c'], biases)
            else:
                if size_all() + targets.nbytes + biases.nbytes + 65536 > LIMIT_BYTES:
                    raise RuntimeError('result save would exceed artifact budget')
                temp = vectors.with_name(vectors.name + '.tmp')
                assert LOCAL.resolve() in vectors.resolve().parents and LOCAL.resolve() in temp.resolve().parents
                with temp.open('wb') as f:
                    np.savez(f, G_c=targets, d_c=biases)
                    f.flush()
                    os.fsync(f.fileno())
                with np.load(temp, allow_pickle=False) as prior:
                    assert np.array_equal(prior['G_c'], targets) and np.array_equal(prior['d_c'], biases)
                temp.replace(vectors)
            with np.load(vectors, allow_pickle=False) as loaded:
                assert np.array_equal(loaded['G_c'], targets) and np.array_equal(loaded['d_c'], biases)
            payload = {'identity': identity, 'implementation_sha256': sha(Path(__file__)),
                       'run_id': 'APRIME-E01-20261020-01', 'conditions': reports,
                       'tail_class_ids': tail, 'client_count': 20,
                       'positive_source_class_units': int((n>0).sum()),
                       'training_samples_count_only': int(n.sum()), 'missing_classes': [],
                       'vectors': {'path': str(vectors.relative_to(ROOT)).replace('\\','/'),
                                   'sha256': sha(vectors), 'bytes': vectors.stat().st_size,
                                   'layout': 'G_c[100,12900], d_c[5,100,12900]; flattened full W then bias'},
                       'numerics': {'dtype': 'float64', 'source_dtype': 'float32',
                         'reference': 'independent math.fsum at every class/coordinate, count-based coefficients',
                         'tolerance_rule': 'gamma_128*sum_i(|a_ic*p_i/Z_c|+a_ic)*|g_ic| per coordinate; L2 plus 2*K*eps*norm',
                         'tolerance_scope': 'current encoded-float arithmetic only; not error versus true gradients',
                         'diagnostic_compute_seconds': computation, **target_checks},
                       'recovery': {'completed_at_resume': completed, 'new_sources_computed': [i for i in range(20) if i not in completed],
                                    'preserved_decoded_hashes': before, 'completed_sources_recomputed': False},
                       'scientific_scope': 'controlled fixed-gradient source mismatch only; not random-ratio expectation, deployable estimates, representation or utility'}
            save_json(OUT/'results.json', payload)
            for cond in state['conditions']:
                cond['status'] = 'complete'
            state['result_sha256'] = sha(OUT/'results.json')
            state['vectors_sha256'] = sha(vectors)
            save_json(state_path, state, exclusive=False)
        elif args.mode == 'verify':
            state = read_json(state_path)
            assert verify_state(state, identity) == list(range(20))
            result = read_json(OUT/'results.json')
            assert result['identity'] == identity and sha(OUT/'results.json') == state['result_sha256']
            assert all(c['status'] == 'complete' for c in state['conditions'])
            assert sha(ROOT/result['vectors']['path']) == state['vectors_sha256'] == result['vectors']['sha256']
            with np.load(ROOT/result['vectors']['path'], allow_pickle=False) as arrays:
                for j, cond in enumerate(result['conditions']):
                    norms = np.linalg.norm(arrays['d_c'][j], axis=1)
                    assert np.allclose(norms, [r['d_c_L2'] for r in cond['classes']], rtol=8*EPS, atol=0)
            save_json(OUT/'recovery_verification.json', {'identity_verified': True, 'all_source_and_result_hashes_verified': True,
                'complete_sources': list(range(20)), 'partial_sources': [], 'not_started_sources': [],
                'complete_conditions': [f'{m}_d{d}' for m,d in CONDITIONS],
                'scientific_computation_repeated': False, 'vector_norm_readback_verified': True})
    resources = guard.finish()
    resources.update({'stage': args.mode, 'inner_program_seconds': time.perf_counter()-START,
                      'inner_time_add_to_total': False, 'new_artifact_live_bytes': size_all(),
                      'python_version': sys.version, 'numpy_version': np.__version__, 'torch_version': str(torch.__version__)})
    save_json(OUT/f'{args.mode}_inner_receipt.json', resources)
    print(json.dumps(resources))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=['test','representative','full','verify'])
    parser.add_argument('--stage-seconds', type=float, required=True)
    main(parser.parse_args())
