"""Bounded carry recorder regression. Only stdlib; no Git or scientific imports."""
import ctypes
from ctypes import wintypes
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import tracemalloc

ROOT = Path(__file__).resolve().parent
OLD = ROOT.parent / 'phaseG1_1_protection_validation_resume_v1'
START = time.perf_counter()
tracemalloc.start()
FIELDS = ['ticks', 'writes', 'metadata', 'scans', 'payload']
ORACLE = [17, 39, 52, 9, 272]
AFTER = [20, 42, 55, 12, 275]
CHILD = dict(seconds=3, writes=16384, metadata=262144, scans=4)


def peak():
    class Counters(ctypes.Structure):
        _fields_ = [('cb', wintypes.DWORD), ('PageFaultCount', wintypes.DWORD)] + [
            (n, ctypes.c_size_t) for n in ('PeakWorkingSetSize', 'WorkingSetSize',
             'QuotaPeakPagedPoolUsage', 'QuotaPagedPoolUsage', 'QuotaPeakNonPagedPoolUsage',
             'QuotaNonPagedPoolUsage', 'PagefileUsage', 'PeakPagefileUsage')]
    info = Counters()
    info.cb = ctypes.sizeof(info)
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    psapi = ctypes.WinDLL('psapi', use_last_error=True)
    psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.c_void_p, wintypes.DWORD]
    ok = psapi.GetProcessMemoryInfo(kernel.GetCurrentProcess(), ctypes.byref(info), info.cb)
    return dict(windows_peak_bytes=info.PeakWorkingSetSize if ok else None,
                cpu_proxy_bytes=tracemalloc.get_traced_memory()[1],
                error=None if ok else 'GetProcessMemoryInfo:' + str(ctypes.get_last_error()))


class Meter:
    def __init__(self, child=False, mode=None):
        self.limit = dict(CHILD) if child else dict(seconds=14, writes=131072, metadata=1048576, scans=18)
        if child and mode == 'syntax':
            self.limit['metadata'] = 327680
        self.tail = dict(seconds=.5, writes=4096, metadata=8192, scans=1) if child else dict(seconds=3, writes=16384, metadata=65536, scans=2)
        self.used = dict.fromkeys(self.limit, 0)
        self.actions = []
        self.hashes = {}

    def before(self, action, seconds=0, writes=0, metadata=0, scans=0):
        self.used['seconds'] = time.perf_counter() - START
        nxt = dict(seconds=seconds, writes=writes, metadata=metadata, scans=scans)
        if any(self.used[k] + nxt[k] + self.tail[k] > self.limit[k] for k in self.limit):
            raise RuntimeError('ResourceGate:' + action)
        p = peak()
        if p['windows_peak_bytes'] is None or p['windows_peak_bytes'] > 2147483648 or p['cpu_proxy_bytes'] > 536870912:
            raise RuntimeError('PeakGate:' + action)

    def charge(self, action, **cost):
        for k, v in cost.items():
            self.used[k] += v
        self.actions.append(dict(action=action, cost=cost))

    def remember(self, path, data):
        self.hashes[str(path)] = dict(bytes=len(data), sha256=hashlib.sha256(data).hexdigest())

    def read(self, path, cap, parse=False):
        self.before('read:' + path.name, metadata=4*(cap+1), scans=1)
        with path.open('rb') as stream:
            data = stream.read(cap+1)
        self.charge('read:' + path.name, metadata=4*len(data), scans=1)
        if len(data) > cap:
            raise RuntimeError('InputCap:' + path.name)
        self.remember(path, data)
        return json.loads(data) if parse else data

    def dump(self, name, value, cap=8192):
        self.before('dump:' + name, writes=cap, metadata=2*cap, scans=1)
        data = (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
        if len(data) > cap:
            raise RuntimeError('OutputCap:' + name)
        self.charge('dump:' + name, writes=len(data), metadata=2*len(data), scans=1)
        (ROOT / name).write_bytes(data)
        self.remember(ROOT / name, data)

    def seal(self):
        self.tail = dict.fromkeys(self.limit, 0)


def vector(values):
    return dict(zip(FIELDS, values))


def consistent(row):
    """Independent persisted field comparison, never trust the saved result."""
    if not isinstance(row.get('observed'), dict) or not isinstance(row.get('expected'), dict):
        return False
    if list(row['observed']) != FIELDS or list(row['expected']) != FIELDS:
        return False
    equal = all(row['observed'][k] == row['expected'][k] for k in FIELDS)
    return equal and row.get('result') == ('PASS' if equal else 'FAIL')


def child(mode):
    meter, failure, payload, status = Meter(True, mode), None, {}, 'FAIL'
    try:
        if mode == 'syntax':
            for name in ['regress.py', 'validate_snapshot.py']:
                data = meter.read(ROOT / name, 32768)
                meter.before('compile:' + name, metadata=len(data)*4)
                compile(data, name, 'exec')
                meter.charge('compile:' + name, metadata=len(data)*4)
        elif mode == 'reader':
            current = meter.read(ROOT / 'observations.json', 8192, True)
            old_bytes = meter.read(OLD / 'results.json', 32768)
            old = json.loads(old_bytes)
            # Compute Git blob identity from bounded bytes, allowing ONLY newline normalization.
            old_normalized = old_bytes.replace(b'\r\n', b'\n').replace(b'\r', b'\n')
            old_blob = hashlib.sha1(b'blob ' + str(len(old_normalized)).encode() + b'\0' + old_normalized).hexdigest()
            assert old_blob == '5f3044d25a456b739e711919524535aad9c3e7d4', 'OldResultIdentity'
            old_row = next(r for r in old['checks'] if r['name'] == 'carry_once')
            carry = current['checks'][0]
            post = current['checks'][1]
            per_field = {k: dict(observed=carry['observed'][k], expected=carry['expected'][k], equal=carry['observed'][k] == carry['expected'][k]) for k in FIELDS}
            assertions = dict(
                field_order=current['fields'] == FIELDS,
                carry_snapshot_literal=carry['observed'] == vector(ORACLE) and carry['expected'] == vector(ORACLE),
                snapshot_fields_and_result=consistent(carry),
                subsequent_ledger_literal=post['observed'] == vector(AFTER) and post['expected'] == vector(AFTER),
                subsequent_fields_and_result=consistent(post),
                duplicate_refused=current['duplicate_refused'] is True,
                snapshot_before_serialization=current['snapshots_still_independent'] is True,
                old_negative_rejected=not consistent(old_row),
                injected_alias_rejected=not consistent(current['injected_old_alias']),
                expected_snapshot_independent=current['expected_mutation_probe_passed'] is True,
                old_new_relation=old_row['expected'] == carry['expected'] and old_row['observed'] == post['observed'] and old_row['result'] == 'PASS')
            payload = dict(assertions=assertions, per_field=per_field,
                           old_row=old_row, old_blob=old_blob,
                           old_negative_is_planned_not_actual_repair_failure=True)
            assert all(assertions.values()), 'PersistedCarryRegression'
        else:
            raise RuntimeError('UnknownChildMode')
        status = 'PASS'
    except Exception as exc:
        failure = dict(type=type(exc).__name__, location='child:' + mode, root=str(exc), scientific_results=0)
    finally:
        meter.seal()
        meter.dump(mode + '_receipt.json', dict(status=status, payload=payload, failure=failure,
                   measurement=peak(), pid=os.getpid(), used_prefix=dict(meter.used),
                   final_receipt_upper=dict(writes=8192, metadata=16384, scans=1),
                   actions=meter.actions, hashes=meter.hashes, implicit_OS_IO=None))
    return 0 if status == 'PASS' else 1


def run_child(meter, mode):
    envelope = dict(CHILD)
    if mode == 'syntax':
        envelope['metadata'] = 327680
    meter.before('subprocess:' + mode, **envelope)
    meter.charge('subprocess:' + mode, **envelope)
    proc = subprocess.run([sys.executable, '-B', str(Path(__file__)), '--child', mode],
                          cwd=ROOT, timeout=3, capture_output=True)
    receipt = meter.read(ROOT / (mode + '_receipt.json'), 8192, True)
    for k in ['writes', 'metadata', 'scans']:
        assert receipt['used_prefix'][k] + receipt['final_receipt_upper'][k] <= envelope[k], 'ChildEnvelope:' + k
    assert receipt['used_prefix']['seconds'] < CHILD['seconds'], 'ChildSeconds'
    assert proc.returncode == 0 and receipt['status'] == 'PASS', 'ChildFailure:' + mode
    return receipt


def main():
    meter = Meter()
    status, failure, children = 'FAIL', None, {}
    syntax, cpu = 0, 0
    try:
        plan = meter.read(ROOT / 'plan.json', 8192, True)
        identity = meter.read(ROOT / 'identity.json', 16384, True)
        helper_bytes = meter.read(ROOT / 'validate_snapshot.py', 32768)
        assert identity['identity_verified'] and plan['first_success_stops'], 'IdentityOrPlan'
        syntax = 1
        children['syntax'] = run_child(meter, 'syntax')
        cpu = 1
        namespace = {'__name__': 'carry_snapshot_helper', '__file__': str(ROOT / 'validate_snapshot.py')}
        meter.before('load_patched_helper_and_snapshot_copies', metadata=131072)
        exec(compile(helper_bytes, 'validate_snapshot.py', 'exec'), namespace)
        meter.charge('load_patched_helper_and_snapshot_copies', metadata=131072)
        Guard, record, Refused = namespace['Guard'], namespace['snapshot_check'], namespace['Refused']
        expected = vector(ORACLE)
        g = Guard(dict.fromkeys(FIELDS, 1000))
        g.carry('old-only', expected)
        duplicate = False
        try:
            g.carry('old-only', expected)
        except Refused as exc:
            duplicate = str(exc) == 'DuplicateCarry:old-only'
        checks = []
        record(checks, 'carry_once', g.used, expected)
        aliased = dict(name='injected_old_alias', observed=g.used, expected=dict(expected), result='PASS')
        for directory, process in [('a', 1), ('b', 2), ('b', 3)]:
            g.charge('failed_repeat:' + directory + ':' + str(process), dict.fromkeys(FIELDS, 1))
        record(checks, 'failure_repeat_directory_process_no_reset', g.used, vector(AFTER))
        stable = checks[0]['observed'] == vector(ORACLE) and checks[0]['expected'] == vector(ORACLE)
        probe, original = [], vector(ORACLE)
        record(probe, 'expected_copy_probe', vector(ORACLE), original)
        original['ticks'] += 100
        probe_ok = probe[0]['expected'] == vector(ORACLE)
        assert stable and duplicate and probe_ok, 'MutableObservationReference'
        meter.dump('observations.json', dict(fields=FIELDS, checks=checks, duplicate_refused=duplicate,
                   snapshots_still_independent=stable, expected_mutation_probe_passed=probe_ok,
                   injected_old_alias=aliased, guard_actions=g.actions,
                   recorder='validate_snapshot.snapshot_check, delegated by synthetic.check',
                   full_synthetic_called=False))
        children['reader'] = run_child(meter, 'reader')
        status = 'PASS'
    except Exception as exc:
        failure = dict(type=type(exc).__name__, location='main', root=str(exc), scientific_results=0,
                       repeated_actual_signature_count=1, planned_negative_excluded=True)
    finally:
        meter.seal()
        prefix = dict(meter.used)
        meter.before('remaining_account_and_manifest', writes=32768, metadata=65536, scans=2)
        account = dict(status=status, failure=failure, children=children, measurement=peak(),
                       program_prefix=prefix, final_seal_upper=dict(writes=32768, metadata=65536, scans=2),
                       actions=meter.actions, syntax_starts=syntax, CPU_suite_starts=cpu,
                       D3_before=dict(engineering=5, revision=5, syntax=3, CPU=1),
                       D3_after=dict(engineering=6, revision=6, syntax=3+syntax, CPU=1+cpu),
                       prior_attempt='attempt1.json; syntax gate refused, CPU not started; all costs retained',
                       prospective_counts=dict(engineering=2, revision=2, syntax=1+syntax, CPU=cpu),
                       historical_engineering_known_after=10, old_criterion5='FAIL permanently',
                       historical_auxiliary_revision_exact=None, historical_segment_actual=None,
                       historical_joint_upper=None, historical_peak=None, implicit_interpreter_OS_IO=None,
                       science=dict(events=0, replays=0, formal_entries=0, fitting=0, evaluation=0,
                                    heads=0, encoding=0, gradients=0, real_fee_summaries=0, CUDA_initializations=0),
                       old_1_2_4_6='PASS cited from v8; not rerun', retained_counts=[778,0,0])
        meter.dump('accounting.json', account, 24576)
        meter.dump('artifact_hashes.json', dict(algorithm='SHA-256 raw bytes', files=meter.hashes,
                   self_exclusion='manifest itself; outer receipt and workflow final hashes separately',
                   cached_bytes_hashed=True))
        print(json.dumps(dict(status=status, failure=failure, guarded_used=meter.used,
                              peak=peak(), full_synthetic_called=False)))
    return 0 if status == 'PASS' else 1


if __name__ == '__main__':
    sys.exit(child(sys.argv[2]) if len(sys.argv) == 3 and sys.argv[1] == '--child' else main())
