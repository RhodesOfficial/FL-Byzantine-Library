"""One bounded synthetic suite; no project imports, Git, or scientific inputs.

Run only through launch.ps1. All explicit application reads/copies/scans/writes
use IO; implicit interpreter/OS loading remains unknown. Byte attribution is a
conservative logical operation count, not a claim about physical disk traffic.
"""
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
START = time.perf_counter()
tracemalloc.start()
LIMIT = dict(seconds=80, writes=786432, metadata=6291456, scans=160)
TAIL = dict(seconds=20, writes=131072, metadata=524288, scans=16)
TOTAL = dict(seconds=100, writes=1048576, metadata=7340032, scans=192)
KNOWN = []


class Refused(RuntimeError):
    pass


class Guard:
    def __init__(self, limit, tail=None, initial=None):
        self.limit = dict(limit)
        self.tail = {k: 0 for k in limit} if tail is None else dict(tail)
        self.used = {k: 0 for k in limit} if initial is None else dict(initial)
        self.actions = []
        self.imported = set()

    def check(self, action, cost):
        if cost is None or set(cost) != set(self.limit):
            raise Refused('MissingActionBound:' + action)
        if any(v < 0 for v in cost.values()):
            raise Refused('NegativeCost:' + action)
        for key in self.limit:
            if self.used[key] + cost[key] + self.tail[key] > self.limit[key]:
                raise Refused('Limit:' + key + ':' + action)

    def charge(self, action, cost):
        self.check(action, cost)
        for key in self.limit:
            self.used[key] += cost[key]
        self.actions.append(dict(action=action, cost=cost, used=dict(self.used)))

    def carry(self, identity, cost):
        if identity in self.imported:
            raise Refused('DuplicateCarry:' + identity)
        self.charge('carry:' + identity, cost)
        self.imported.add(identity)


def vec(**kwargs):
    return {k: kwargs.get(k, 0) for k in TOTAL}


def peak(simulate=False):
    cpu = tracemalloc.get_traced_memory()[1]
    if simulate:
        return dict(status='FAILED_SIMULATED', windows_peak_bytes=None,
                    cpu_proxy_bytes=cpu, error='SyntheticPeakFailure')
    class Counters(ctypes.Structure):
        _fields_ = [('cb', wintypes.DWORD), ('PageFaultCount', wintypes.DWORD)] + [
            (name, ctypes.c_size_t) for name in (
                'PeakWorkingSetSize', 'WorkingSetSize', 'QuotaPeakPagedPoolUsage',
                'QuotaPagedPoolUsage', 'QuotaPeakNonPagedPoolUsage',
                'QuotaNonPagedPoolUsage', 'PagefileUsage', 'PeakPagefileUsage')]
    info = Counters()
    info.cb = ctypes.sizeof(info)
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    psapi = ctypes.WinDLL('psapi', use_last_error=True)
    psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.c_void_p, wintypes.DWORD]
    if not psapi.GetProcessMemoryInfo(kernel.GetCurrentProcess(), ctypes.byref(info), info.cb):
        return dict(status='FAILED', windows_peak_bytes=None, cpu_proxy_bytes=cpu,
                    error='GetProcessMemoryInfo:' + str(ctypes.get_last_error()))
    return dict(status='MEASURED', windows_peak_bytes=info.PeakWorkingSetSize,
                cpu_proxy_bytes=cpu, method='Windows PeakWorkingSetSize; tracemalloc peak proxy')


class IO:
    def __init__(self):
        self.guard = Guard(TOTAL, TAIL)
        self.records = []

    def before(self, name, cost):
        elapsed = time.perf_counter() - START
        # Wall time is observed continuously, never reset on a child/directory change.
        self.guard.used['seconds'] = elapsed
        self.guard.check(name, cost)
        p = peak()
        if p['status'] != 'MEASURED':
            raise Refused('RealPeakUnavailable:' + name)
        if p['windows_peak_bytes'] > 2147483648 or p['cpu_proxy_bytes'] > 536870912:
            raise Refused('ProcessMemory:' + name)

    def read(self, path, cap, parse=False):
        path = Path(path)
        name = 'read:' + path.name
        self.before(name, vec(metadata=(cap + 1) * 4, scans=1))
        # A bounded read, plus explicitly attributed decode/check/hash/parse copies.
        with path.open('rb') as stream:
            data = stream.read(cap + 1)
        self.guard.charge(name, vec(metadata=len(data) * 4, scans=1))
        if len(data) > cap:
            raise Refused('InputCap:' + path.name)
        self.records.append(dict(operation=name, input_bytes=len(data),
                                 logical_read_copy_check_upper=len(data) * 4))
        return json.loads(data) if parse else data

    def dump(self, name, obj, cap=32768):
        # Reserve encoding/checking BEFORE json serialization, then debit actual
        # serialized length; Python-internal allocation is covered by peak proxy.
        self.before('serialize:' + name, vec(writes=cap, metadata=cap * 2, scans=1))
        data = (json.dumps(obj, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
        if len(data) > cap:
            raise Refused('OutputCap:' + name)
        self.guard.charge('write:' + name,
                          vec(writes=len(data), metadata=len(data) * 2, scans=1))
        (ROOT / name).write_bytes(data)
        if name not in KNOWN:
            KNOWN.append(name)

    def finish_mode(self):
        # TAIL has already been protected by every active action.
        self.guard.tail = vec()
        self.guard.used['seconds'] = time.perf_counter() - START


METER = IO()


# Single workload cost definition. The oracle below is handwritten independently.
PRICES = {
    'register': (1, 3, 2, 1), 'prepare': (2, 0, 5, 1),
    'main_replay': (3, 1, 7, 1), 'coverage_replay': (4, 1, 11, 1),
    'failed_state': (1, 13, 2, 1), 'gradient_prepare': (2, 0, 17, 1),
    'upload': (1, 0, 0, 1), 'metadata': (1, 2, 3, 1),
    'seal': (2, 19, 5, 1),
}


def cost(name, payload=0):
    ticks, writes, reads, scans = PRICES[name]
    return dict(ticks=ticks, writes=writes, metadata=reads,
                scans=scans, payload=payload)


def workload(sizes, empty=False):
    ops = [('register', 0), ('prepare', sum(sizes)), ('main_replay', sum(sizes)),
           ('coverage_replay', sum(sizes)), ('failed_state', 0),
           ('gradient_prepare', sum(sizes)),
           ('upload', 0 if empty else sum(sorted(sizes, reverse=True)[:8])),
           ('metadata', 0), ('seal', 0)]
    return [dict(name=n, cost=cost(n, b)) for n, b in ops]


def total(rows):
    return {key: sum(row['cost'][key] for row in rows) for key in rows[0]['cost']}


def reject(fn):
    try:
        fn()
    except Refused:
        return True
    return False


def synthetic():
    results = []
    def check(name, observed, expected=True):
        results.append(dict(name=name, observed=observed, expected=expected,
                            result='PASS' if observed == expected else 'FAIL'))

    sizes = [9, 1, 8, 2, 7, 3, 6, 4, 5, 10]
    oracle_names = ['register', 'prepare', 'main_replay', 'coverage_replay',
                    'failed_state', 'gradient_prepare', 'upload', 'metadata', 'seal']
    # Independently enumerated expected vectors, deliberately no call to cost().
    oracle_vectors = [
        [1, 3, 2, 1, 0], [2, 0, 5, 1, 55], [3, 1, 7, 1, 55],
        [4, 1, 11, 1, 55], [1, 13, 2, 1, 0], [2, 0, 17, 1, 55],
        [1, 0, 0, 1, 52], [1, 2, 3, 1, 0], [2, 19, 5, 1, 0]]
    rows = workload(sizes)
    fields = ['ticks', 'writes', 'metadata', 'scans', 'payload']
    expected_rows = [dict(name=n, cost=dict(zip(fields, v)))
                     for n, v in zip(oracle_names, oracle_vectors)]
    check('independent_action_oracle', rows, expected_rows)
    expected = dict(ticks=17, writes=39, metadata=52, scans=9, payload=272)
    check('independent_total', total(rows), expected)
    meter = Guard(expected)
    for row in rows:
        meter.charge(row['name'], row['cost'])
    check('single_definition_action_ledger', meter.used, expected)
    startup = Guard(expected)
    startup.check('full_workload', total(rows))
    check('startup_and_next_action_agree', meter.used == expected)
    for missing in ['main_replay', 'coverage_replay', 'failed_state', 'gradient_prepare']:
        incomplete = [r for r in rows if r['name'] != missing]
        def verify_expected(candidate):
            if candidate != expected_rows:
                raise Refused('OracleActionMismatch')
        check('oracle_detects_missing_' + missing,
              reject(lambda: verify_expected(incomplete)) and
              reject(lambda: Guard(total(incomplete)).check('complete_workload', expected)))
    for dim in expected:
        for reserve in [0, 2]:
            lim = {k: 100 for k in expected}
            used = {k: 1 for k in expected}
            tail = {k: reserve for k in expected}
            nxt = {k: 1 for k in expected}
            nxt[dim] = 99 - reserve
            g = Guard(lim, tail, used)
            g.check('equal', nxt)
            check('equal_' + dim + '_tail' + str(reserve), True)
            nxt[dim] += 1
            check('over_one_' + dim + '_tail' + str(reserve), reject(lambda: g.check('over', nxt)))
    for dim, bound in [('seconds', 100), ('windows', 2147483648),
                       ('cpu_proxy', 536870912), ('attempts', 0), ('CUDA', 0)]:
        g = Guard({dim: bound})
        g.check('exact_limit', {dim: bound})
        check('additional_equal_' + dim, True)
        check('additional_over_one_' + dim,
              reject(lambda d=dim, b=bound: g.check('over_limit', {d: b + 1})))
    check('changing_sizes_top8', workload([1, 30, 2, 29, 3, 28, 4, 27, 5, 26])[-3]['cost']['payload'], 152)
    empty = workload(sizes, empty=True)
    check('empty_return_keeps_preparation', empty[1]['cost']['payload'] == 55 and empty[-3]['cost']['payload'] == 0)
    g = Guard({k: 1000 for k in expected})
    g.carry('old-only', expected)
    check('carry_duplicate_refused', reject(lambda: g.carry('old-only', expected)))
    check('carry_once', g.used, expected)
    for directory, process in [('a', 1), ('b', 2), ('b', 3)]:
        g.charge('failed_repeat:' + directory + ':' + str(process), {k: 1 for k in expected})
    check('failure_repeat_directory_process_no_reset', g.used,
          {k: expected[k] + 3 for k in expected})
    check('peak_is_max', max([7, 19, 8, 19]), 19)
    external = dict(index=3, body=7, tail=2)
    def external_check(parts):
        if set(parts) != {'index', 'body', 'tail'}:
            raise Refused('MissingExternalAction')
        Guard(dict(bytes=12)).check('external', dict(bytes=sum(parts.values())))
    external_check(external)
    for missing in ['index', 'tail']:
        check('external_missing_' + missing,
              reject(lambda m=missing: external_check({k: v for k, v in external.items() if k != m})))
    u_guard = Guard(dict(bytes=34359738368))
    side_effects = []
    def blocked_u():
        u_guard.check('constant_U', dict(bytes=34871421077))
        side_effects.append('executed')
    check('U_refused_before_side_effects', reject(blocked_u) and side_effects == [])
    bootstrap_issue = dict(kind='finite_bootstrap_missing_bound', historical_peak=None)
    check('bootstrap_gap_registered_suite_continues', bootstrap_issue['historical_peak'] is None)
    action_effects = []
    def unbounded_action():
        u_guard.check('unbounded', None)
        action_effects.append(1)
    check('restricted_missing_bound_refused', reject(unbounded_action) and action_effects == [])
    # An actual copy is guarded before allocation, then charged, including checks.
    METER.before('explicit_fixture_copy', vec(metadata=512, scans=1))
    fixture_copy = bytes(bytearray(range(64)))
    METER.guard.charge('explicit_fixture_copy', vec(metadata=256, scans=1))
    check('guarded_real_copy', len(fixture_copy), 64)
    METER.dump('fixtures.json', dict(sizes=sizes, oracle=expected_rows, expected_total=expected,
                                    U_constant=34871421077, U_excess=511682709,
                                    simulated_numbers_only=True))
    return results


def child(mode):
    status, code, failure = 'PASS', 0, None
    try:
        source = METER.read(Path(__file__), 65536)
        if mode == 'syntax':
            METER.before('compile_source', vec(metadata=262144, scans=1))
            compile(source, str(Path(__file__).name), 'exec')
            METER.guard.charge('compile_source', vec(metadata=len(source) * 4, scans=1))
        elif mode == 'controlled':
            raise ValueError('PLANNED_CONTROLLED_EXCEPTION')
        elif mode != 'peakfail':
            raise RuntimeError('UnknownChildMode')
    except Exception as exc:
        status, code = 'CONTROLLED_EXCEPTION' if mode == 'controlled' else 'FAIL', 7
        failure = dict(type=type(exc).__name__, location='child:' + mode, root=str(exc))
    finally:
        METER.finish_mode()
        measurement = peak(mode == 'peakfail')
        METER.dump(mode + '_measurement.json', dict(mode=mode, status=status,
                   measurement=measurement, failure=failure, pid=os.getpid()))
        METER.dump(mode + '_ledger.json', dict(mode=mode, status=status,
                   used=METER.guard.used, seconds=time.perf_counter() - START,
                   actions=METER.guard.actions, implicit_interpreter_OS_io=None))
    return code


def run_child(mode):
    # Reserve whole child including launch, self-read, syntax/copy, measurement,
    # failure, and seal before dispatch; never refund on failure or mode change.
    envelope = vec(seconds=10, writes=65536, metadata=786432, scans=12)
    METER.before('subprocess:' + mode, envelope)
    METER.guard.charge('subprocess_reservation:' + mode, envelope)
    begin = time.perf_counter()
    proc = subprocess.run([sys.executable, '-B', str(Path(__file__)), '--child', mode],
                          cwd=ROOT, timeout=10, capture_output=True)
    elapsed = time.perf_counter() - begin
    for name in [mode + '_measurement.json', mode + '_ledger.json']:
        if name not in KNOWN:
            KNOWN.append(name)
    measurement = METER.read(ROOT / (mode + '_measurement.json'), 16384, True)
    ledger = METER.read(ROOT / (mode + '_ledger.json'), 32768, True)
    if elapsed > 10 or any(ledger['used'][k] > envelope[k] for k in envelope):
        raise Refused('ChildEnvelope:' + mode)
    return dict(mode=mode, returncode=proc.returncode, outer_seconds=elapsed,
                measurement=measurement, ledger=ledger, reservation=envelope,
                stdout_bytes=len(proc.stdout), stderr_bytes=len(proc.stderr))


def manifest():
    hashes = {}
    for name in list(KNOWN):
        data = METER.read(ROOT / name, 131072)
        hashes[name] = dict(bytes=len(data), sha256=hashlib.sha256(data).hexdigest())
    METER.dump('artifact_hashes.json', dict(algorithm='SHA-256 raw bytes', files=hashes,
              self_exclusion='this manifest; outer receipt written after process exit',
              old_evidence='Git tree/blob identities in bootstrap.json; no event scanning'), 32768)


def main():
    results, children, failure = [], [], None
    outcome = 'FAIL'
    try:
        for name, cap in [('validate.py', 65536), ('launch.ps1', 16384),
                          ('plan.json', 16384), ('bootstrap.json', 32768)]:
            data = METER.read(ROOT / name, cap)
            KNOWN.append(name)
            if name.endswith('.json'):
                parsed = json.loads(data)
                if name == 'bootstrap.json' and not parsed['identity_verified']:
                    raise Refused('IdentityMismatch')
        syntax = run_child('syntax')
        children.append(syntax)
        if syntax['returncode'] != 0:
            raise Refused('SyntaxFailureNoRetry')
        results = synthetic()
        for mode in ['controlled', 'peakfail']:
            children.append(run_child(mode))
        controlled, peakfailed = children[1], children[2]
        for name, ok in [
            ('controlled_exception_persisted_before_exit', controlled['returncode'] == 7 and
             controlled['measurement']['failure']['type'] == 'ValueError' and
             controlled['measurement']['measurement']['status'] == 'MEASURED'),
            ('peak_failure_null_independent_record', peakfailed['returncode'] == 0 and
             peakfailed['measurement']['measurement']['status'] == 'FAILED_SIMULATED' and
             peakfailed['measurement']['measurement']['windows_peak_bytes'] is None),
            ('child_peaks_within_limits', all(c['measurement']['measurement']['cpu_proxy_bytes'] <= 536870912
             and (c['measurement']['measurement']['windows_peak_bytes'] is None or
                  c['measurement']['measurement']['windows_peak_bytes'] <= 2147483648) for c in children)),
        ]:
            results.append(dict(name=name, result='PASS' if ok else 'FAIL', observed=ok, expected=True))
        outcome = 'PASS' if all(r['result'] == 'PASS' for r in results) else 'FAIL'
    except Exception as exc:
        failure = dict(type=type(exc).__name__, location='main', root=str(exc),
                       repeated_signature_count=1, retries_allowed=0)
    finally:
        METER.finish_mode()
        METER.dump('results.json', dict(status=outcome, checks=results,
                   passed=sum(r['result'] == 'PASS' for r in results),
                   failed=sum(r['result'] == 'FAIL' for r in results)))
        METER.dump('failure.json', dict(unexpected=failure, controlled_subcases=children), 65536)
        measurement = peak()
        METER.dump('measurement.json', dict(status=outcome, measurement=measurement,
                   all_child_peaks=[c['measurement'] for c in children],
                   CUDA_initializations=0, implicit_interpreter_OS_io=None))
        METER.dump('operations.json', dict(new_events=0, replays=0, formal_entries=0,
                   fitting=0, evaluation=0, heads=0, models=0, encoding=0, gradients=0,
                   real_fee_summaries=0, official_imports=[], retained_complete=778,
                   retained_partial=0, retained_not_started=0,
                   application_IO=METER.records, no_Git_inside_program=True), 32768)
        # Future sealing is charged conservatively in advance. This receipt is
        # immutable; it contains a measured prefix plus a bounded sealing tail.
        METER.before('remaining_seal', vec(writes=131072, metadata=524288, scans=24, seconds=10))
        prefix = dict(METER.guard.used)
        seal = vec(writes=131072, metadata=524288, scans=24, seconds=10)
        joint = {k: prefix[k] + seal[k] for k in prefix}
        bootstrap = METER.read(ROOT / 'bootstrap.json', 32768, True)
        METER.dump('accounting.json', dict(
            status=outcome, measured_prefix=prefix, remaining_seal_upper=seal,
            segment_guarded_upper=joint, segment_actual_total=None,
            explanation='prefix includes unreclaimed child reservations; seal upper is not actual; final wall time in outer_receipt.json',
            child_observed=[dict(mode=c['mode'], actual=c['ledger']['used'], outer_seconds=c['outer_seconds']) for c in children],
            explicit_IO_actions=METER.guard.actions, byte_scope='logical explicit read/copy/check attribution upper; not physical IO',
            old_base_once=dict(seconds=275.73515180000686, writes=3855811, metadata=23014556,
                               scans=907, simulated_bytes=29642603849),
            v1_risk_only=dict(seconds=20, writes=1048576, metadata=1048576, scans=64),
            new_simulated_payload=0, historical_segment_actual=None, historical_joint_upper=None,
            historical_windows_peak=None, historical_auxiliary_revision_exact=None,
            workflow=bootstrap['workflow'], limits=TOTAL,
            counters_before=dict(engineering=2, revision=2, syntax=1, CPU=0),
            counters_after=dict(engineering=3, revision=3, syntax=2, CPU=1),
            historical_engineering_known_after=7, official_entries='2/2 closed', fees='2/2 closed',
            official_revision_syntax_CPU='3/3 closed',
            new_process_peak_scope='each Python process independently measured; simulated failure null retained',
            fail_count=sum(r['result'] == 'FAIL' for r in results), unexpected=failure), 65536)
        manifest()
        actual_end = dict(METER.guard.used)
        actual_end['seconds'] = time.perf_counter() - START
        if any(actual_end[k] > joint[k] for k in joint):
            raise Refused('SealUpperExceeded')
        # Stdout is fixed-size and covered by the outer receipt allowance.
        print(json.dumps(dict(final_explicit_ledger=actual_end, peak=peak(),
                              guarded_upper_verified=True, result=outcome)))
    return 0 if outcome == 'PASS' and failure is None else 1


if __name__ == '__main__':
    sys.exit(child(sys.argv[2]) if len(sys.argv) == 3 and sys.argv[1] == '--child' else main())
