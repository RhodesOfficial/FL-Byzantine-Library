"""Pure-stdlib accounting and exact arithmetic for the single cost-M run."""
import ctypes
import hashlib
import io
import json
import time
from fractions import Fraction

MIB = 1024 ** 2
LIMITS = dict(input=30., W01=60., storage=30., total=120., writes=16*MIB,
              logical=512*MIB, scans=512, calls=80, steps=400, backwards=400,
              forwards=400, samples=25600, cuda=1024*MIB, windows=6144*MIB,
              cpu=2048*MIB)


def encode(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2,
                       allow_nan=False) + '\n').encode('utf-8')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def normalized(raw):
    return raw.replace(b'\r\n', b'\n').replace(b'\r', b'\n')


def windows_peak():
    from ctypes import wintypes
    class Counters(ctypes.Structure):
        _fields_ = [('cb', wintypes.DWORD), ('faults', wintypes.DWORD)] + [
            (name, ctypes.c_size_t) for name in ('peak', 'working', 'qpp', 'qp',
                'qnp', 'qn', 'pagefile', 'peakpagefile')]
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    api = ctypes.WinDLL('psapi', use_last_error=True).GetProcessMemoryInfo
    api.argtypes = (wintypes.HANDLE, ctypes.POINTER(Counters), wintypes.DWORD)
    value = Counters()
    value.cb = ctypes.sizeof(value)
    if not api(kernel.GetCurrentProcess(), ctypes.byref(value), value.cb):
        raise OSError(ctypes.get_last_error())
    return value.peak


class Gate(RuntimeError):
    pass


class Ledger:
    def __init__(self, prior=None, clock=time.perf_counter):
        self.clock = clock
        self.phases = dict(input=0., W01=0., storage=0.)
        self.counts = {k: 0 for k in ('writes', 'scans', 'calls', 'steps',
                                     'backwards', 'forwards', 'samples')}
        self.logical = dict(reference_downlink=0, ordinary_state_return=0,
                            gradient_preparation=0, metadata=0)
        self.peaks = dict(cuda=0, windows=0, cpu=0)
        self.actions = []
        if prior:
            self.phases.update(prior['phases'])
            self.counts.update(prior['counts'])
            self.logical.update(prior['logical'])
            self.peaks.update(prior['peaks'])

    def guard(self, phase, seconds=0., writes=0, logical=0, **counts):
        proposed = dict(self.counts)
        for name, amount in dict(counts, writes=writes).items():
            proposed[name] += amount
        for name, amount in proposed.items():
            if amount > LIMITS[name] - (MIB if name == 'writes' else 0):
                raise Gate('next action exceeds ' + name)
        if sum(self.logical.values()) + logical > LIMITS['logical']:
            raise Gate('next action exceeds logical')
        reserve = 5. if phase == 'storage' else 0.
        if self.phases[phase] + seconds > LIMITS[phase] - reserve:
            raise Gate('next action exceeds phase ' + phase)
        if sum(self.phases.values()) + seconds > LIMITS['total'] - 5.:
            raise Gate('next action exceeds total')
        for name, amount in self.peaks.items():
            if amount > LIMITS[name]:
                raise Gate('memory limit ' + name)
        self.actions.append(dict(phase=phase, estimated_seconds=seconds,
                                 estimated_writes=writes, estimated_logical=logical,
                                 remaining_phase=LIMITS[phase]-self.phases[phase],
                                 remaining_total=LIMITS['total']-sum(self.phases.values()),
                                 failure_seconds_reserved=5, failure_bytes_reserved=MIB))

    def add(self, **counts):
        for name, amount in counts.items():
            self.counts[name] += amount

    def copy(self, column, amount):
        self.logical[column] += amount

    def timed(self, phase, function):
        started = self.clock()
        try:
            return function()
        finally:
            self.phases[phase] += self.clock() - started

    def snapshot(self):
        return dict(phases=self.phases, counts=self.counts, logical=self.logical,
                    peaks=self.peaks, next_action_audit=self.actions)


def serialize_once(value, serializer, clock=time.perf_counter_ns, synchronize=lambda: None):
    """In-memory preparation only. Reads and disk writes belong to the caller."""
    synchronize()
    started = clock()
    stream = io.BytesIO()
    serializer(value, stream)
    synchronize()
    ns = clock() - started
    if type(ns) is not int or ns <= 0:
        raise Gate('non-positive or unresolved timer')
    return ns, stream.tell()


def exact_b(row):
    old = row['old_W02_decimal_seconds']
    values = [Fraction(old[k]) for k in ('encode', 'main_head', 'statistics')]
    if any(v < 0 for v in values):
        raise Gate('negative old cost')
    return Fraction(row['W01_ns'] + row['message_prepare_ns'], 10**9) + sum(values)


def record_state(row):
    required = ('W01_ns', 'message_prepare_ns', 'return_bytes', 'message_bytes',
                'old_W02_decimal_seconds', 'steps', 'resolution_seconds', 'preserved')
    if (all(k in row for k in required) and row['steps'] == 5 and row['preserved']
            and row['W01_ns'] > 0 and row['message_prepare_ns'] > 0
            and row['return_bytes'] > 0 and row['message_bytes'] > 0
            and Fraction(row['resolution_seconds']) > 0):
        return 'complete'
    return 'partial' if any(k in row for k in ('W01_started', 'W01_ns', 'message_prepare_ns')) else 'not_started'


def summarize(rows):
    for row in rows:
        row['status'] = record_state(row)
    complete = [r for r in rows if r['status'] == 'complete']
    if len(complete) != 80:
        return None
    keys = [(r['task'], r['reference'], r['client']) for r in rows]
    if len(set(keys)) != 80:
        raise Gate('duplicate identity')
    b = [exact_b(r) for r in rows]
    if min(b) <= 0:
        raise Gate('non-positive b')
    B = max(b)
    for row, value in zip(rows, b):
        row.update(b_seconds=str(value), L=str(value/B))
    return str(B)
