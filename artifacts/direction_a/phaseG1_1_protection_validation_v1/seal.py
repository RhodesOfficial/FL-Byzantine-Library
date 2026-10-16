"""One-shot seal of stopped D3 task. No experiment import or fee computation.
Use E:/anaconda3/python.exe -B seal.py. Completed outputs cannot be overwritten.
"""
import ctypes
from ctypes import wintypes
import hashlib
import json
from pathlib import Path
import sys
import time
import tracemalloc

START = time.perf_counter()
tracemalloc.start()
OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
DELIVERY = '76ce7f5a490be24a084fe87a666c09d308e3be01'
BASE = 'a52371f9d38f1392ca519e2004e9b15065cdb4c1'
AUTH = '02cc22306eabdb8253198b301c85db1c5de711ab'
WRITTEN = []


def dump(name, value):
    path = OUT / name
    if path.exists():
        raise FileExistsError('completed evidence cannot be overwritten: ' + name)
    raw = (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
    if sum(n for _, n in WRITTEN) + len(raw) > 262144:
        raise RuntimeError('seal_only_write_sublimit')
    path.write_bytes(raw)
    WRITTEN.append((name, len(raw)))


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
    psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(Memory), wintypes.DWORD]
    psapi.GetProcessMemoryInfo.restype = wintypes.BOOL
    mem = Memory()
    mem.cb = ctypes.sizeof(mem)
    if not psapi.GetProcessMemoryInfo(kernel.GetCurrentProcess(), ctypes.byref(mem), mem.cb):
        raise ctypes.WinError(ctypes.get_last_error())
    return {'status': 'MEASURED', 'windows_peak_bytes': mem.PeakWorkingSetSize,
            'cpu_proxy_tracemalloc_peak_bytes': tracemalloc.get_traced_memory()[1],
            'method': 'GetProcessMemoryInfo PeakWorkingSetSize; tracemalloc Python allocations only',
            'scope': 'seal helper before final JSON/hash persistence, excludes external commands',
            'CUDA_initializations': 0}


def main():
    source = Path(__file__).read_bytes()
    compile(source, str(__file__), 'exec')
    dump('syntax.json', {'status': 'PASS', 'count': 1, 'method': 'compile only; no formal imports'})
    dump('failure.json', {
        'exception': 'GuardCoverageGap', 'phase': 'bootstrap before auxiliary implementation',
        'location': 'initial discovery/status/ancestry/history commands',
        'root_cause': 'external index/object/discovery reads and scans lacked complete prelaunch bounds and guard',
        'signature': 'GuardCoverageGap:bootstrap_external_IO:no_complete_prelaunch_bound',
        'consecutive_occurrences': 1, 'actual_hard_limit_exceeded': None,
        'new_scientific_results': 0, 'new_real_fee_summaries': 0,
        'decision': 'stop validation; seal for review; no repair or validation retry'})
    dump('patch_rejection.json', {
        'exception': 'PatchValidationError', 'phase': 'seal-only evidence authoring',
        'location': 'apply_patch', 'root_cause': 'delete and add targeted same TO_REVIEWER.md in one patch',
        'signature': 'PatchValidationError:duplicate_target:delete_add',
        'consecutive_occurrences': 1, 'mutations': 0, 'new_scientific_results': 0,
        'handling': 'one corrected evidence-creation patch; no experiment or synthetic suite'})
    cases = ['single cost definition links expansion, ledger, startup and next action',
             'independent expected list detects omitted main replay',
             'independent expected list detects omitted coverage replay',
             'independent expected list detects omitted failed state',
             'independent expected list detects omitted gradient preparation',
             'known U constant 34871421077 startup rejection at 34359738368',
             'all limited dimensions equal allowed and over one unit rejected without effects',
             'variable-sized clients top8', 'empty returns still charge preparation',
             'old ledger once and peak uses max', 'failures/repeats/directory/process preserve ledger',
             'next action includes used plus bound plus seal reserve',
             'missing index or Git tail rejected', 'success and controlled exception persist peaks',
             'simulated peak failure preserves null and failure status']
    dump('synthetic_results.json', {'suite_status': 'NOT_RUN_STOP_RULE', 'synthetic_CPU_suites': 0,
        'fixtures_created': 0, 'cases': [{'name': c, 'status': 'NOT_RUN',
        'reason': 'actual bootstrap protection gap; stopped before suite'} for c in cases]})
    dump('operations.json', {
        'source': 'tool transcript; wall times are not complete external I/O measurements',
        'commands_before_stop': [
            {'operation': 'read ROLE_EXECUTOR and TO_EXECUTOR', 'seconds': 0.5669677},
            {'operation': 'rg AGENTS.md discovery and git status --short', 'seconds': 0.5175943},
            {'operation': 'STATE, HEAD, ancestry, log, targeted directory/index sizes', 'seconds': 0.8262251},
            {'operation': 'four closure_resume metadata/source reads', 'seconds': 0.5732888}],
        'observed_command_seconds_before_stop': 2.4840759,
        'read_list': ['docs/workflow/ROLE_EXECUTOR.md', 'docs/workflow/TO_EXECUTOR.md',
            'docs/workflow/STATE.md', *['artifacts/direction_a/phaseG1_1_resource_closure_resume_v1/' + p
            for p in ['accounting.json', 'artifact_hashes.json', 'entry.json', 'summarize.py']]],
        'unbounded_operations': ['discovery scans', 'Git index/object/config/rule reads', 'external runtime'],
        'git_index_size_observed': 412758,
        'external_read_bytes': None, 'external_scans': None, 'external_peaks': None,
        'identity': {'HEAD_observed': AUTH, 'task_base': BASE, 'ancestor_check_exit': 0,
                     'locked_delivery_requested': DELIVERY, 'package_and_formal_objects_freshly_verified': False},
        'operation_delta': {k: 0 for k in ['events', 'replays', 'formal_entries', 'models',
            'training', 'encoding', 'gradients', 'bias_evaluation_statistics', 'real_fee_summaries']},
        'formal_event_module_imports': 0,
        'retained_reference_only': {'source': DELIVERY + ':artifacts/direction_a/phaseG1_1_resource_closure_resume_v1/accounting.json#retained',
            'complete': 778, 'partial': 0, 'not_started': 0, 'fresh_per_item_verification': False}})
    try:
        measured = peak()
    except Exception as exc:
        measured = {'status': 'FAILED', 'windows_peak_bytes': None,
                    'cpu_proxy_tracemalloc_peak_bytes': None,
                    'exception': type(exc).__name__, 'root_cause': str(exc)}
    dump('measurement.json', measured)
    prior = {'seconds': 275.73515180000686, 'writes': 3855811, 'metadata': 23014556,
             'scans': 907, 'simulated_bytes': 29642603849, 'windows': None, 'cpu_proxy': None}
    dump('accounting.json', {
        'status': 'STOPPED_PROTECTION_GAP',
        'prior_once': {'locator': DELIVERY + ':artifacts/direction_a/phaseG1_1_resource_closure_resume_v1/accounting.json#joint_upper',
                       'resources': prior, 'old_F_and_closure_added_again': False},
        'authorized_segment_cap': {'seconds': 120, 'writes': 2097152, 'metadata': 8388608,
                                   'scans': 256, 'simulated_bytes': 0},
        'authorized_joint_plan_reference_only': {'seconds': 395.73515180000686, 'writes': 5952963,
            'metadata': 31403164, 'scans': 1163, 'simulated_bytes': 29642603849},
        'segment_actual': {'seconds': None, 'writes': None, 'metadata': None, 'scans': None,
                           'simulated_bytes': 0, 'external_windows_peak': None, 'external_cpu_proxy': None},
        'joint_upper': None, 'reason_joint_unknown': 'external I/O/scans lack bounds; authorized plan is not compliance',
        'observed_seconds_before_stop': 2.4840759,
        'seal_seconds_to_accounting': time.perf_counter() - START,
        'seal_generated_writes_before_accounting': sum(n for _, n in WRITTEN),
        'seal_write_sublimit': 262144,
        'new_counts': {'engineering_attempts': 2, 'auxiliary_revisions_conservative': 2,
            'successful_auxiliary_revisions': 1, 'syntax_checks': 1, 'synthetic_CPU_suites': 0,
            'rejected_patches': 1, 'validation_retries': 0, 'fee_summaries': 0, 'formal_entries': 0},
        'count_basis': 'bootstrap attempt and rejected seal patch counted; corrected initial implementation included in repair attempt; no separate real entry',
        'history_counts': {'engineering_attempts_known': 4, 'engineering_known_including_current': 6,
            'auxiliary_revisions_exact': None, 'fee_summaries_used_limit': [2, 2],
            'formal_entries_used_limit': [2, 2], 'formal_revision_syntax_CPU_each_used_limit': [3, 3]},
        'historical_failed_peak': None, 'historical_joint_peak': None,
        'new_peak_does_not_replace_history_or_external_commands': True,
        'historical_FAIL': ['F criterion7', 'old closure criterion5', 'fee recovery criterion4', 'P full scope'],
        'known_U_reference_only': {'bytes': 34871421077, 'alternative_upper_gap': 511682709,
                                  'new_actual_cost': False, 'necessary_lower_bound': False},
        'classification': {'engineering': 'bootstrap guard gap and rejected evidence patch',
            'resource': 'whole-segment compliance unknown; actual hard-limit exceedance not asserted',
            'science': 'zero new results; stop is not a scientific conclusion'},
        'self_assessment': {'1': 'FAIL', '2': 'FAIL', '3': 'FAIL', '4': 'FAIL', '5': 'FAIL', '6': 'PASS',
                            'FAIL_count': 5, 'blocked': True}})
    paths = sorted(p for p in OUT.iterdir() if p.is_file()) + [
        ROOT / 'docs/DIRECTION_A_G1_1_QUALIFICATION_v1.md', ROOT / 'docs/workflow/TO_REVIEWER.md']
    records = {}
    total_read = 0
    for path in paths:
        size = path.stat().st_size
        if total_read + size > 262144:
            raise RuntimeError('seal_only_read_sublimit')
        total_read += size
        raw = path.read_bytes()
        lf = raw.replace(b'\r\n', b'\n').replace(b'\r', b'\n')
        records[path.relative_to(ROOT).as_posix()] = {
            'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest(),
            'normalized_sha256': hashlib.sha256(lf).hexdigest()}
        if path.name in ('TO_REVIEWER.md', 'DIRECTION_A_G1_1_QUALIFICATION_v1.md'):
            assert len(lf.splitlines()) <= (80 if path.name == 'TO_REVIEWER.md' else 120)
    assert not any(n.startswith('direction_a.') for n in sys.modules)
    dump('artifact_hashes.json', {'algorithm': 'SHA-256', 'files': records,
        'domain': 'new evidence plus two handoff docs; manifest excludes itself',
        'normalization': 'CRLF/CR/LF only; historical raw hashes not reinterpreted',
        'seal_readback_bytes': total_read, 'seal_seconds_before_manifest': time.perf_counter() - START})
    print('SEALED; syntax PASS; synthetic NOT_RUN; FAIL=5; blocked=true')


if __name__ == '__main__':
    main()
