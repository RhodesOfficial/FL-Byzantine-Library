"""G1.3 A only: metered metadata and artificial arithmetic, no torch imports."""
import ctypes
import hashlib
import json
import math
from pathlib import Path
import time

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'artifacts/direction_a/phaseG1_3_A_v1'
COMMITS = dict(D='e3c3528722cd4c4f55f96b37182255a4ade961b8',
               G='d3a3bd712d6bb28283b59faff16e17e099debcb4',
               F='b37efe0f53f899131b76926d681132af7b90f6b2',
               V='54eb6e02f4630df82cfdeb1c352fd5e4520ea5be',
               M='22c7418d40f62c81f2639e86d1b7a166a6898920')
WHITELIST = []
for ds in ('CIFAR10', 'CIFAR100'):
    for name in ('counts.json', 'info.json'):
        WHITELIST.append(('D', f'artifacts/direction_a/phase0_2_v1/tasks/FedPCC-0.2-candidate-{ds}-N20-v1/{name}'))
for group, directory, names in (
    ('G', 'phaseG1_2_full_v1', ('preregistration.json', 'reference_acceptance.json', 'artifact_hashes.json', 'archive_verification.json')),
    ('G', 'backbone_preparation_v1', ('manifest.json',)),
    ('F', 'phaseG1_1_formal_F_resume_v1', ('mechanism.json', 'input_checks.json', 'preregistration.json', 'replay_checks.json')),
    ('V', 'phaseG1_1_v1', ('speed_assignments.json',)),
    ('M', 'phaseG1_1_cost_M_v1', ('measurements.json',))):
    WHITELIST.extend((group, f'artifacts/direction_a/{directory}/{name}') for name in names)


class Gate(RuntimeError):
    pass


def encode(value):
    return (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)+'\n').encode('utf-8')


def working_peak():
    class Counters(ctypes.Structure):
        _fields_ = [('cb', ctypes.c_ulong), ('faults', ctypes.c_ulong)] + [
            (n, ctypes.c_size_t) for n in ('peak', 'working', 'p1', 'p2', 'n1', 'n2', 'page', 'peakpage')]
    c = Counters()
    c.cb = ctypes.sizeof(c)
    handle = ctypes.windll.kernel32.GetCurrentProcess
    handle.restype = ctypes.c_void_p
    if not ctypes.windll.psapi.GetProcessMemoryInfo(ctypes.c_void_p(handle()), ctypes.byref(c), c.cb):
        raise Gate('working-set monitor unavailable')
    return int(c.peak)


class Budget:
    """Each explicit action reserves BEFORE access; interpreter I/O stays unknown."""
    def __init__(self, previous=None, tiny=None):
        self.started = time.monotonic()
        self.prior = previous or {}
        self.used = dict(self.prior.get('used', dict(read=0, write=0, scans=0)))
        self.elapsed_prior = self.prior.get('elapsed_seconds', 0.)
        self.limits = tiny or dict(read=4*1024**2, write=4*1024**2, scans=256)
        self.active_limits = dict(read=3*1024**2, write=3*1024**2, scans=192)
        self.operations = list(self.prior.get('operations', []))
        self.proxy_peak = self.prior.get('cpu_proxy_peak_bytes', 0)
        self.peak = 0
        self.sealing = False

    def check(self):
        elapsed = self.elapsed_prior + time.monotonic()-self.started
        if elapsed > (120 if self.sealing else 90):
            raise Gate('cumulative time reserve')
        self.peak = max(self.peak, working_peak())
        if self.peak > 2*1024**3:
            raise Gate('Windows peak')

    def reserve(self, label, read=0, write=0, scans=0, proxy=0):
        self.check()
        proposed = dict(read=self.used['read']+read, write=self.used['write']+write,
                        scans=self.used['scans']+scans)
        for k, v in proposed.items():
            if v > min(self.limits[k], self.limits[k] if self.sealing else self.active_limits[k]):
                raise Gate('reserve '+k+': '+label)
        if proxy > 256*1024**2:
            raise Gate('reserve proxy: '+label)
        self.used = proposed
        self.proxy_peak = max(self.proxy_peak, proxy)
        self.operations.append(dict(label=label, read=read, write=write, scans=scans, proxy=proxy))

    def read(self, path):
        p = ROOT / path
        size = p.stat().st_size
        self.reserve('read '+path, read=size, scans=1, proxy=max(8*1024**2, size*24))
        raw = p.read_bytes()
        if len(raw) != size:
            raise Gate('input changed during read')
        return raw

    def write(self, name, value):
        # Limit BEFORE serialization, covering UTF-8 buffer and Python graph copies.
        self.reserve('serialize '+name, proxy=16*1024**2)
        raw = encode(value)
        if len(raw) > 256*1024:
            raise Gate('serialization capacity')
        self.reserve('write '+name, write=len(raw))
        (OUT / name).write_bytes(raw)

    def snapshot(self):
        return dict(used=self.used.copy(), elapsed_seconds=self.elapsed_prior+time.monotonic()-self.started,
                    operations=list(self.operations), cpu_proxy_peak_bytes=self.proxy_peak,
                    windows_peak_working_set_bytes=self.peak, physical_io_bytes=None,
                    interpreter_implicit_io_bytes=None, historical_peak_bytes=None)


def norm(x):
    return math.sqrt(math.fsum(v*v for v in x))


def dot(x, y):
    return math.fsum(a*b for a, b in zip(x, y))


def metric(counts, gradients, probabilities, budget):
    m = len(counts)
    budget.reserve('synthetic sources and pair diameter', scans=m+8, proxy=1024*1024)
    if not m or len(gradients) != m or len(probabilities) != m:
        raise ValueError('source schema')
    dim = len(gradients[0])
    if not dim or any(len(g) != dim for g in gradients):
        raise ValueError('complete head')
    if any(not math.isfinite(x) for g in gradients for x in g):
        raise ValueError('nonfinite')
    if any(type(n) is not int or n <= 0 for n in counts):
        raise ValueError('N')
    if any(not math.isfinite(p) or p < 0 or p > 1 for p in probabilities):
        raise ValueError('p')
    total = sum(counts)
    a = [n/total for n in counts]
    z = math.fsum(ai*p for ai, p in zip(a, probabilities))
    if z <= 0:
        raise ValueError('Z')
    b = [ai*p/z for ai, p in zip(a, probabilities)]
    target = [math.fsum(a[i]*gradients[i][j] for i in range(m)) for j in range(dim)]
    d = [math.fsum((b[i]-a[i])*gradients[i][j] for i in range(m)) for j in range(dim)]
    s = math.fsum(a[i]*norm(gradients[i]) for i in range(m))
    pairs = [norm([x-y for x, y in zip(gradients[i], gradients[j])])
             for i in range(m) for j in range(i)]
    diameter = max(pairs, default=0.)
    amplitude = norm(d)
    return dict(a=a, b=b, Z=z, G=target, d=d, S=s, A=amplitude,
                rho=amplitude/s if s else 0., tau=diameter/(total*s) if s else 0.,
                target_relative=amplitude/norm(target) if norm(target) else None,
                zero_target=norm(target) == 0, cancellation=norm(target) == 0 and amplitude > 0,
                single=m == 1, same=diameter == 0, diameter=diameter,
                pair_rms=norm(pairs)/math.sqrt(len(pairs)) if pairs else 0.)


def probability_bound(a, eta, norms, z):
    t = math.fsum(x*y for x, y in zip(a, eta))
    if z <= t:
        raise ValueError('probability approximation unidentifiable')
    return 2*max(norms)*t/(z-t)


def error_envelope(a, source_errors, max_norm, s, diameter, total, round_abs, z_floor=None):
    # B can use |b-a| L1 <= 2 and max(e_i), independent of s_i/L_i/p_i.
    es = math.fsum(x*y for x, y in zip(a, source_errors))+round_abs
    ed = 2*max(source_errors)+round_abs
    if s <= es:
        return dict(S_error=es, d_error=ed, rho_error=None, tau_error=None, status='unresolved scale')
    return dict(S_error=es, d_error=ed,
                rho_error=ed/(s-es)+2*max_norm*es/(s*(s-es)),
                tau_error=2*max(source_errors)/(total*(s-es))+diameter*es/(total*s*(s-es)),
                projection_error='2*E_X/(S-E_S)+2*R_X*E_S/(S*(S-E_S))+direction_error*R_X/S',
                z_floor=z_floor, status='conditional on supplied source bounds')


def paired_summary(main, uniform, analytic, numeric_error, threshold):
    if len(main) != 3 or len(uniform) != 3:
        raise ValueError('three paired seeds')
    delta = [x-y for x, y in zip(main, uniform)]
    mean = math.fsum(delta)/3
    sd = math.sqrt(math.fsum((x-mean)**2 for x in delta)/2)
    half = 4.302652729911275*sd/math.sqrt(3)
    lo, hi = mean-half, mean+half
    return dict(seeds=delta, main_Y=main, uniform_Y=uniform, mean=mean, sd_ddof1=sd,
                ci95=[lo, hi], analytic_included=lo-numeric_error <= analytic <= hi+numeric_error,
                passed=(analytic-numeric_error > threshold and lo-numeric_error > threshold
                        and lo-numeric_error <= analytic <= hi+numeric_error))


def random_projection(row, masks, uniform_masks, uniform_p, budget, fixed_direction=None):
    budget.reserve('synthetic projection', scans=10, proxy=1024*1024)
    g, a, z, s, d = row['gradients'], row['a'], row['Z'], row['S'], row['d']
    u = fixed_direction or ([v/norm(d) for v in d] if norm(d) else [0.]*len(d))
    def mean_x(ms, denominator):
        if not ms:
            raise ValueError('no attempts')
        return [math.fsum(a[i]*mask[i]*g[i][j]/denominator for mask in ms for i in range(len(a)))/len(ms)
                for j in range(len(d))]
    x, x0 = mean_x(masks, z), mean_x(uniform_masks, uniform_p)
    r, r0 = [xj-gj for xj, gj in zip(x, row['G'])], [xj-gj for xj, gj in zip(x0, row['G'])]
    return dict(Y=dot(u, r)/s if s else 0., Y0=dot(u, r0)/s if s else 0.,
                vector_residual=r, uniform_vector_residual=r0,
                all_direction_residual=norm(r), paired=dot(u, [v-w for v, w in zip(r, r0)])/s if s else 0.)
