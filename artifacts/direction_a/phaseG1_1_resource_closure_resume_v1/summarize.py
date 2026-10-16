"""Bounded, metadata-only recovery. Run --check, then --run, then --seal.
E:/anaconda3/python.exe -B; no experiment modules are imported.
"""
import ctypes
from ctypes import wintypes
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import tracemalloc

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
BASE = 'b37efe0f53f899131b76926d681132af7b90f6b2'
TASK = 'a8cfa0ab7e4c1ce4ba56d011407c7fa0b22b58ef'
AUTH = 'e720d5c23761ce6dfaf5f402aa4f29e12088c918'
DELIVERY = 'e0a097d4a8ab9d55bad58da695138b4f773e44fc'
F = 'artifacts/direction_a/phaseG1_1_formal_F_resume_v1/'
OLD = 'artifacts/direction_a/phaseG1_1_resource_closure_v1/'
PLAN = 'docs/DIRECTION_A_G1_1_RESOURCE_CLOSURE_PLAN_v2.md'
REVIEW = 'docs/workflow/TO_REVIEWER.md'
START = time.perf_counter()
tracemalloc.start()


def dump(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n',
                    encoding='utf-8', newline='\n')


class ReadBudget:
    def __init__(self, limit):
        self.limit, self.used, self.records = limit, 0, []

    def read(self, size, operation, label):
        if size < 0 or self.used + size > self.limit:
            raise RuntimeError('metadata_read_budget_before_IO')
        self.used += size
        raw = operation()
        assert len(raw) == size
        self.records.append({'locator': label, 'bytes': size})
        return raw


class Memory(ctypes.Structure):
    _fields_ = [('cb', wintypes.DWORD), ('PageFaultCount', wintypes.DWORD)] + [
        (n, ctypes.c_size_t) for n in ('PeakWorkingSetSize', 'WorkingSetSize',
        'QuotaPeakPagedPoolUsage', 'QuotaPagedPoolUsage', 'QuotaPeakNonPagedPoolUsage',
        'QuotaNonPagedPoolUsage', 'PagefileUsage', 'PeakPagefileUsage')]


def peak():
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    psapi = ctypes.WinDLL('psapi', use_last_error=True)
    kernel.GetCurrentProcess.argtypes = []
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE,
                                         ctypes.POINTER(Memory), wintypes.DWORD]
    psapi.GetProcessMemoryInfo.restype = wintypes.BOOL
    mem = Memory()
    mem.cb = ctypes.sizeof(mem)
    if not psapi.GetProcessMemoryInfo(kernel.GetCurrentProcess(), ctypes.byref(mem), mem.cb):
        raise ctypes.WinError(ctypes.get_last_error())
    return {'windows_peak_bytes': mem.PeakWorkingSetSize,
            'cpu_proxy_tracemalloc_peak_bytes': tracemalloc.get_traced_memory()[1],
            'handle_bytes': ctypes.sizeof(wintypes.HANDLE),
            'method': 'GetProcessMemoryInfo.PeakWorkingSetSize; tracemalloc Python allocation proxy',
            'CUDA_initializations': 0}


def persist_then_peak(folder, fee, sampler):
    # Fee survival must be independent of optional resource measurement.
    dump(folder / 'fees.json', fee)
    try:
        measured = sampler()
    except Exception as exc:
        dump(folder / 'failure.json', {'exception': type(exc).__name__,
             'location': 'peak sampler after fees persistence', 'root_cause': str(exc),
             'fees_preserved': True, 'scientific_results': 0})
        return None
    dump(folder / 'measurement.json', measured)
    return measured


def check():
    assert not (OUT / 'selfchecks.json').exists()
    effects = []
    budget = ReadBudget(8)
    assert budget.read(8, lambda: effects.append('read') or b'12345678', 'synthetic') == b'12345678'
    before = (budget.used, list(effects), list(budget.records))
    try:
        budget.read(1, lambda: effects.append('forbidden') or b'x', 'over1')
        raise AssertionError('over budget accepted')
    except RuntimeError:
        pass
    assert before == (budget.used, effects, budget.records)
    with tempfile.TemporaryDirectory(dir=OUT) as temp:
        folder = Path(temp)
        def fail_peak():
            raise OSError('synthetic_peak_failure')
        assert persist_then_peak(folder, {'synthetic_fee': 17}, fail_peak) is None
        assert json.loads((folder / 'fees.json').read_text()) == {'synthetic_fee': 17}
        assert json.loads((folder / 'failure.json').read_text())['fees_preserved']
    measured = peak()
    assert 0 < measured['windows_peak_bytes'] <= 2147483648
    assert measured['cpu_proxy_tracemalloc_peak_bytes'] <= 536870912
    assert 'direction_a.formal_f' not in sys.modules
    dump(OUT / 'selfchecks.json', {'status': 'PASS', 'synthetic_only': True,
         'real_fee_input_reads': 0, 'event_imports': 0,
         'cases': {'equal_limit_allowed': True, 'over1_rejected_no_side_effect': True,
                   'fees_survive_peak_failure': True, 'independent_failure_seal': True,
                   'Windows_HANDLE_API': True},
         'measurement': measured, 'seconds': time.perf_counter() - START})
    print('synthetic checks PASS')


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)


def normalize(raw):
    return raw.replace(b'\r\n', b'\n').replace(b'\r', b'\n')


def run():
    assert not (OUT / 'entry.json').exists(), 'remaining single summary already used'
    assert json.loads((OUT / 'selfchecks.json').read_text(encoding='utf-8'))['status'] == 'PASS'
    assert git('rev-parse', 'HEAD').decode().strip() == AUTH
    subprocess.run(['git', 'merge-base', '--is-ancestor', TASK, AUTH], cwd=ROOT, check=True)
    # Read bounds: <=512KiB input/rules/discovery, <=512KiB checks/copies,
    # <=1MiB seal/Git. Total <=2MiB and time <=120s including20s tail.
    budget = ReadBudget(512 * 1024)
    def load(commit, path):
        obj = commit + ':' + path
        size = int(git('cat-file', '-s', obj))
        return budget.read(size, lambda: git('show', obj), obj)
    identities = []
    for path in [F.rstrip('/'), 'artifacts/direction_a/phaseG1_1_formal_F_v1',
                 'direction_a/formal_f.py', 'direction_a/formal_f_policy.py',
                 'scripts/run_direction_a_formal_f.py']:
        original = git('rev-parse', BASE + ':' + path).decode().strip()
        current = git('rev-parse', AUTH + ':' + path).decode().strip()
        assert original == current, path
        assert not git('diff', '--name-only', AUTH, '--', path).strip(), path
        identities.append({'path': path, 'original_git_object': original,
                           'current_git_object': current})
    for path in [OLD.rstrip('/'), 'docs/DIRECTION_A_G1_1_RESOURCE_CLOSURE_PLAN_v1.md']:
        original = git('rev-parse', DELIVERY + ':' + path).decode().strip()
        assert original == git('rev-parse', AUTH + ':' + path).decode().strip()
        assert not git('diff', '--name-only', AUTH, '--', path).strip()
        identities.append({'path': path, 'old_delivery_git_object': original})
    previous_raw = load(DELIVERY, OLD + 'accounting.json')
    previous = json.loads(previous_raw)
    manifest = json.loads(load(DELIVERY, OLD + 'artifact_hashes.json'))
    old_hash_proofs = []
    for path, item in manifest['files'].items():
        raw = previous_raw if path == OLD + 'accounting.json' else load(DELIVERY, path)
        lf = normalize(raw)
        candidates = [raw, lf, lf.replace(b'\n', b'\r\n'), lf.replace(b'\n', b'\r')]
        match = [v for v in candidates if len(v) == item['bytes'] and
                 hashlib.sha256(v).hexdigest() == item['sha256']]
        proof_source = 'reconstructed uniform line endings'
        if not match:
            # Historical raw files can mix CRLF and LF. Authenticate their exact
            # recorded bytes before comparing only normalized line endings.
            p = ROOT / path
            witness = budget.read(p.stat().st_size, p.read_bytes, 'historical raw witness:' + path)
            assert len(witness) == item['bytes']
            assert hashlib.sha256(witness).hexdigest() == item['sha256']
            assert normalize(witness) == lf, path
            match = [witness]
            proof_source = 'exact historical raw hash witness; normalization equals Git object'
        assert match and normalize(match[0]) == normalize(raw), path
        old_hash_proofs.append({'path': path, 'git_object':
             git('rev-parse', DELIVERY + ':' + path).decode().strip(),
             'historical_raw_hash_matches_reconstructed_line_endings': True,
             'proof_source': proof_source,
             'normalized_sha256': hashlib.sha256(lf).hexdigest()})
    prior = previous['joint_upper']
    assert [prior[k] for k in ('seconds', 'writes', 'metadata', 'scans', 'simulated_bytes')] == [
        155.73515180000686, 2807235, 16723100, 651, 29642603849]
    assert previous['retained']['structural_complete'] == 778
    assert previous['retained']['partial'] == previous['retained']['not_started'] == 0
    # Permanently consume the single remaining fixed-input arithmetic invocation.
    dump(OUT / 'entry.json', {'summary_attempt_cumulative': 2,
         'historical_failed_attempts': 1, 'current_attempt': 1, 'retry_allowed': False,
         'identity': identities, 'old_raw_hash_proofs': old_hash_proofs,
         'task_baseline': TASK, 'authorization': AUTH, 'fee_input_commit': BASE})
    binding = json.loads(load(BASE, F + 'binding.json'))
    audit = json.loads(load(BASE, F + 'delivery_audit.json'))
    assert audit['resources']['attempts'] == 778
    assert len(binding['rows']) == 80 and len(binding['references']) == 4
    refs = []
    for ref in binding['references']:
        rows = [r for r in binding['rows'] if r['reference'] == ref['reference_id']]
        assert sorted(r['client'] for r in rows) == list(range(20))
        charges = [{'client': r['client'], 'reference': r['reference_bytes'],
                    'return_preparation': r['return_bytes'], 'gradient_preparation': r['message_bytes'],
                    'effective_upload_upper': r['return_bytes'] + r['message_bytes'],
                    'C': r['reference_bytes'] + 2*r['return_bytes'] + 2*r['message_bytes']} for r in rows]
        top = sorted(charges, key=lambda r: (-r['C'], r['client']))[:8]
        total = sum(r['C'] for r in top)
        refs.append({'reference': ref['reference_id'], 'client_charges': charges,
                     'top8_clients': [r['client'] for r in top], 'T': total, '192T': 192*total})
    components = {'main_sum_192T': sum(r['192T'] for r in refs),
                  'coverage_8T0': 8*refs[0]['T'],
                  'boundary_8maxC0': 8*max(r['C'] for r in refs[0]['client_charges']),
                  'registration': 70757, 'historical_preparation_metadata': 16777216}
    full = sum(components.values())
    fee = {'input_commit': BASE, 'formula': 'C=reference+2*return+2*message; T=top8 among20',
           'references': refs, 'components': components, 'U': full,
           'limit': 34359738368, 'U_minus_limit': full - 34359738368,
           'within_limit': full <= 34359738368, 'fixed_workload': 778,
           'preparation_includes_failed_dispatches': True, 'generation_and_replay_counted': True,
           'observed_end_states_or_selection_tracks_used': False,
           'physical_network': None, 'new_simulated_payload': 0,
           'historical_actual_payload_reference_only': 29642603849,
           'upper_is_alternative_not_added_to_actual': True,
           'metadata_16MiB_is_historical_fee_basis_not_current_read_cap': True}
    measurement = persist_then_peak(OUT, fee, peak)
    if measurement is not None:
        assert measurement['windows_peak_bytes'] <= 2147483648
        assert measurement['cpu_proxy_tracemalloc_peak_bytes'] <= 536870912
    delta = {'seconds': 120, 'writes': 1048576, 'metadata': 2097152,
             'scans': 256, 'simulated_bytes': 0}
    joint = dict(prior)
    for key, value in delta.items():
        joint[key] += value
    limits = {'seconds': 300, 'writes': 33554432, 'metadata': 25165824,
              'scans': 2048, 'simulated_bytes': 34359738368}
    assert all(joint[k] <= limits[k] for k in limits)
    joint['windows'] = joint['cpu_proxy'] = None
    dump(OUT / 'accounting.json', {
        'prior_once': {'locator': DELIVERY + ':' + OLD + 'accounting.json#joint_upper',
                       'resources': prior, 'old_F_not_added_again': True},
        'segment_upper': delta, 'joint_upper': joint,
        'remaining': {k: limits[k]-joint[k] for k in limits}, 'limits': limits,
        'fixed_input_read_ledger': budget.records, 'fixed_input_read_bytes': budget.used,
        'operation_delta': {'events': 0, 'models_training_encoding_gradients': 0,
            'bias_evaluation_statistics': 0, 'real_entries': 0,
            'formal_implementation_revisions': 0, 'formal_syntax_checks': 0, 'formal_CPU_suites': 0,
            'summary_attempts': 1, 'summary_completed': 1,
            'auxiliary_revision': 2, 'rejected_patch_attempt': 1,
            'auxiliary_syntax_check': 2, 'synthetic_CPU_suite': 2,
            'pre_fee_identity_engineering_failures': 1},
        'history_counts': {'engineering_attempts': 1, 'summary_attempts': 1,
            'summary_completed': 0, 'auxiliary_syntax_checks': 0, 'auxiliary_CPU_suites': 0,
            'auxiliary_revision_known_minimum': 3, 'auxiliary_revision_exact': None,
            'revision_source': OLD + 'accounting.json#metering.writes_budget_includes: discarded draft, final helper, small amendment',
            'unknown_revision_handling': 'known minimum3 plus2 current revisions and1 rejected patch; historical exact and guaranteed remaining unknown; criterion4 FAIL; no further revision',
            'formal_revision_syntax_CPU': [3, 3, 3], 'formal_real_entries': 2,
            'old_HANDLE_signature_consecutive_failures': 1,
            'after_synthetic_HANDLE_success_consecutive_failures': 0},
        'new_process_measurement': measurement,
        'new_segment_failed_identity_process_peak': None,
        'historical_failed_process_peak': None, 'historical_joint_peak': None,
        'retained': previous['retained'],
        'historical_FAIL': {'F_criterion_7': 'FAIL', 'previous_closure_criterion_5': 'FAIL'},
        'resource_basis': {
            'kind': 'conservative all-program envelopes, not actual traffic or measured total seconds',
            'input_rules_discovery_cap': 524288, 'synthetic_copies_cap': 524288,
            'seal_readback_Git_tail_cap': 1048576,
            'discovery_upper_bytes': 131072,
            'checks_and_copies_include': 'syntax/check interpreter reads, synthetic temp writes/readback, repeated helper reads',
            'all_costs_include': 'discovery, helper revision, syntax, synthetic, summary, repeated reads, failures, JSON/docs/hash writes, seal, Git stage/commit/verification',
            'failure_reserve_seconds': 20, 'global_failure_write_reserve_bytes': 2097152,
            'next_action_guard': 'each remaining metadata/seal action <=1MiB read; commit tail included in120s/1MiB writes/256 scans; no event entry',
            'new_peak_scope': 'measured Python helper processes only; shell/Git conservative256MiB allowance, no recovered historical peak',
            'non_Python_new_process_memory_upper': 268435456,
            'time_excludes': 'human reasoning time; all command times included'},
        'summary_seconds': time.perf_counter()-START,
        'classification': {'engineering': 'helper repaired; synthetic passed',
            'resource': 'current segment bounded; historical FAIL unchanged',
            'science': 'no new result; P full scope FAIL; G1.1 not closed; G1.3 closed'}})
    print(json.dumps({'components': components, 'U': full, 'U_minus_limit': full-34359738368,
                      'references': [{k: r[k] for k in ('reference', 'T', '192T')} for r in refs],
                      'input_read_bytes': budget.used, 'new_peak': measurement}, ensure_ascii=False))


def seal():
    assert not (OUT / 'artifact_hashes.json').exists()
    paths = sorted(p for p in OUT.iterdir() if p.is_file()) + [ROOT / PLAN, ROOT / REVIEW]
    records = {}
    for p in paths:
        raw = p.read_bytes()
        records[p.relative_to(ROOT).as_posix()] = {
            'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest(),
            'normalized_sha256': hashlib.sha256(normalize(raw)).hexdigest()}
    assert len((ROOT / PLAN).read_text(encoding='utf-8').splitlines()) <= 120
    assert len((ROOT / REVIEW).read_text(encoding='utf-8').splitlines()) <= 80
    assert sum(r['bytes'] for r in records.values()) < 131072
    dump(OUT / 'artifact_hashes.json', {'algorithm': 'SHA-256', 'files': records,
         'text_verification': 'normalize only CRLF/CR/LF; raw and normalized hashes both retained',
         'domain': 'new delivery excluding this manifest; old evidence locked by Git objects'})
    print('sealed files=' + str(len(records)))


if __name__ == '__main__':
    try:
        {'--check': check, '--run': run, '--seal': seal}[sys.argv[1]]()
    except Exception as exc:
        if not (OUT / 'failure.json').exists():
            dump(OUT / 'failure.json', {'exception': type(exc).__name__, 'root_cause': str(exc),
                 'location': sys.argv[1], 'fees_preserved': (OUT / 'fees.json').exists(),
                 'scientific_results': 0, 'no_automatic_summary_retry': True})
        raise
