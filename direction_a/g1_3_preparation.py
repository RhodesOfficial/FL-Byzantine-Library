"""D4 A implementation. Only the metered owner may supply a kernel lease.

No model loader, random generator, training or real probability entry exists here.
Integers, including exact rational temporaries, are capped before arithmetic.
"""
import hashlib
import json
import math
import os
import struct
import sys
import time
from fractions import Fraction as F
from pathlib import Path

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

K = 192
Q = 1 << K
CAP = 4096
ACTIVE = None


class Gate(RuntimeError):
    pass


class Unresolved(Gate):
    pass


def rpc(action, **values):
    print(json.dumps(dict(action=action, token=os.environ['G13_TOKEN'], **values), separators=(',', ':')), flush=True)
    line = sys.stdin.readline(16385)
    if not line or len(line.encode()) > 16384:
        raise Gate('owner disconnected/frame capacity')
    reply = json.loads(line)
    if not reply['ok']:
        raise Gate(reply['error'])
    return reply.get('value')


class Budget:
    """A single nonrenewable lease, settled into its parent's current V account."""
    def __init__(self, lease=None, tiny=None):
        if os.environ.get('G13_RPC_ACTIVE') != 'D4-v1':
            raise Gate('D4 owner required')
        if lease is None and tiny is None:
            raise Gate('no unleased kernel access')
        self.limit = tiny or lease['limits']
        self.used = dict(read=0, write=0, scans=0)
        self.ops = 0
        self.max_bits = 0
        self.max_live = 0
        self.actual = dict(interval_add=0, interval_multiply=0, interval_divide=0,
                           sqrt_steps=0, packed_get=0, packed_set=0, coordinates=0,
                           json_nodes=0, integer_checks=0)
        self.by_action = {}
        self.start = time.monotonic()
        self.seconds = (lease or {}).get('seconds', 900)

    def reserve(self, label, read=0, write=0, scans=0, proxy=33554432, ops=0):
        if time.monotonic()-self.start >= self.seconds-2:
            raise Gate('active time reserve; return to S')
        if min(read, write, scans, proxy, ops) < 0 or proxy > 268435456:
            raise Gate('CPU proxy/negative charge')
        delta = dict(read=read, write=write, scans=scans)
        if any(self.used[k]+v > self.limit[k] for k, v in delta.items()):
            raise Gate('lease refusal before access: '+label)
        if self.ops+ops > 725873600:
            raise Gate('integer operation lease')
        row = self.by_action.setdefault(label, dict(read=0, write=0, scans=0, operations=0))
        if len(self.by_action) > 180:
            raise Gate('action row capacity')
        for k, v in delta.items():
            self.used[k] += v
            row[k] += v
        row['operations'] += ops
        self.ops += ops
        self.max_live = max(self.max_live, proxy)

    def scan(self, label, count=1):
        self.reserve(label, scans=count)

    def report(self):
        return dict(used=self.used, actions=self.by_action, integer_operation_upper_charges=self.ops,
                    actual_instrumented=self.actual, exact_total_scans=None,
                    actual_count_scope='named events only; upper debits are not exact actual scans',
                    max_integer_bits=self.max_bits, cpu_proxy_peak=self.max_live,
                    seconds=time.monotonic()-self.start)


def bits(n):
    if ACTIVE:
        ACTIVE.actual['integer_checks'] += 1
    if n.bit_length() > CAP:
        raise Gate('PRECISION_CAP')
    if ACTIVE:
        ACTIVE.max_bits = max(ACTIVE.max_bits, n.bit_length())
    return n


def product(a, b):
    if a and b and a.bit_length()+b.bit_length() > CAP:
        raise Gate('PRECISION_CAP before multiply')
    return bits(a*b)


def shift(a, k):
    if a.bit_length()+k > CAP:
        raise Gate('PRECISION_CAP before shift')
    return bits(a << k)


def exact(value):
    value = F(value)
    bits(value.numerator)
    bits(value.denominator)
    return value


class I:
    __slots__ = ('lo', 'hi')

    def __init__(self, lo, hi=None):
        self.lo, self.hi = bits(lo), bits(lo if hi is None else hi)
        if self.lo > self.hi:
            raise ValueError('inverted interval')

    @staticmethod
    def of(value):
        if isinstance(value, I):
            return value
        v = exact(value)
        n = shift(v.numerator, K)
        return I(n//v.denominator, -((-n)//v.denominator))

    def __add__(self, other):
        if ACTIVE:
            ACTIVE.actual['interval_add'] += 1
        o = I.of(other)
        return I(bits(self.lo+o.lo), bits(self.hi+o.hi))

    __radd__ = __add__

    def __neg__(self):
        return I(-self.hi, -self.lo)

    def __sub__(self, other):
        return self+-I.of(other)

    def __rsub__(self, other):
        return I.of(other)+-self

    def __mul__(self, other):
        if ACTIVE:
            ACTIVE.actual['interval_multiply'] += 1
        o = I.of(other)
        vals = (product(self.lo, o.lo), product(self.lo, o.hi),
                product(self.hi, o.lo), product(self.hi, o.hi))
        return I(min(vals)//Q, -((-max(vals))//Q))

    __rmul__ = __mul__

    def __truediv__(self, other):
        if ACTIVE:
            ACTIVE.actual['interval_divide'] += 1
        o = I.of(other)
        if o.lo <= 0 <= o.hi:
            raise Unresolved('divisor contains zero')
        vals = [(shift(a, K), b) for a in (self.lo, self.hi) for b in (o.lo, o.hi)]
        lows = [a//b for a, b in vals]
        highs = [-((-a)//b) for a, b in vals]
        return I(min(lows), max(highs))

    def sqrt(self):
        if self.lo < 0:
            raise ValueError('negative square root')
        lo, hi = shift(self.lo, K), shift(self.hi, K)
        # Newton's integer sqrt is library implementation; bounded binary search
        # here makes the declared 4096-step ceiling independently inspectable.
        def root(n):
            left, right = 0, 1 << ((n.bit_length()+1)//2)
            for _ in range(4096):
                if ACTIVE:
                    ACTIVE.actual['sqrt_steps'] += 1
                if left >= right:
                    return left
                mid = (left+right+1)//2
                if product(mid, mid) <= n:
                    left = mid
                else:
                    right = mid-1
            raise Gate('sqrt step cap')
        a, b = root(lo), root(hi)
        return I(a, b+(product(b, b) != hi))

    def text(self):
        if max(len(str(self.lo)), len(str(self.hi))) > 96:
            raise Gate('PRECISION_CAP endpoint output')
        return f'{self.lo}:{self.hi}:192'


ZERO = I(0)


class Packed:
    """Fixed 16-slot arena model; signed endpoints in 512 bytes each."""
    live = 0
    peak = 0

    def __init__(self, n, budget):
        if n not in (1290, 12900) or Packed.live >= 16:
            raise Gate('packed arena capacity')
        budget.reserve('A03 packed allocation', proxy=(Packed.live+1)*n*1024+33554432)
        self.data = bytearray(n*1024)
        self.n = n
        Packed.live += 1
        Packed.peak = max(Packed.peak, Packed.live)

    def set(self, j, v):
        if ACTIVE:
            ACTIVE.actual['packed_set'] += 1
        self.data[j*1024:j*1024+512] = v.lo.to_bytes(512, 'little', signed=True)
        self.data[j*1024+512:(j+1)*1024] = v.hi.to_bytes(512, 'little', signed=True)

    def get(self, j):
        if ACTIVE:
            ACTIVE.actual['packed_get'] += 1
        start = j*1024
        return I(int.from_bytes(self.data[start:start+512], 'little', signed=True),
                 int.from_bytes(self.data[start+512:start+1024], 'little', signed=True))

    def close(self):
        self.data = None
        Packed.live -= 1


def f32(value):
    """Decode finite IEEE binary32 (including signed zero/subnormal) exactly."""
    raw = struct.unpack('<I', struct.pack('<f', value))[0]
    sign, exp, frac = raw >> 31, (raw >> 23) & 255, raw & ((1 << 23)-1)
    if exp == 255:
        raise ValueError('nonfinite binary32')
    mantissa = frac if exp == 0 else (1 << 23)+frac
    power = -149 if exp == 0 else exp-150
    return F((-1 if sign else 1)*mantissa)*(F(2)**power)


def metric(counts, gradients, probabilities, h, budget, shape=None, dtype='float32'):
    m = len(counts)
    budget.scan('A03 M validation', 2)
    if h not in (1290, 12900) or dtype != 'float32':
        raise ValueError('dtype/head dimension')
    if shape is not None and shape != ((h//129, 128), (h//129,)):
        raise ValueError('weight/bias shape')
    if not 1 <= m <= 3 or len(gradients) != m or len(probabilities) != m:
        raise ValueError('source schema')
    if any(type(n) is not int or not 0 < n <= 2**31-1 for n in counts):
        raise ValueError('N')
    if any(len(g) != h for g in gradients):
        raise ValueError('complete head shape')
    p = [exact(v) for v in probabilities]
    if any(v < 0 or v > 1 or v.denominator > 2**64 for v in p):
        raise ValueError('p')
    total = sum(counts)
    a = [F(n, total) for n in counts]
    z = sum((ai*pi for ai, pi in zip(a, p)), F(0))
    if z <= 0:
        raise ValueError('Z')
    b = [ai*pi/z for ai, pi in zip(a, p)]
    target, delta = Packed(h, budget), Packed(h, budget)
    norm2 = [ZERO for _ in range(m)]
    pairs = {(i, j): ZERO for i in range(m) for j in range(i)}
    tg2 = dd2 = dgerr2 = dderr2 = ZERO
    exact_g0 = exact_d0 = structural = True
    try:
        budget.reserve('A03 M coordinates/norms/pairs/exact-zero', scans=6+3*m+len(pairs),
                       ops=h*(128*m+32*len(pairs)+64)+256)
        for j in range(h):
            budget.actual['coordinates'] += 1
            # All weight rows, then all bias coordinates; no two-coordinate shortcut.
            values = [f32(g[j]) for g in gradients]
            structural &= all(v == 0 for v in values)
            eg = sum((a[i]*values[i] for i in range(m)), F(0))
            ed = sum(((b[i]-a[i])*values[i] for i in range(m)), F(0))
            bits(eg.numerator); bits(eg.denominator); bits(ed.numerator); bits(ed.denominator)
            exact_g0 &= eg == 0
            exact_d0 &= ed == 0
            gi = sum((I.of(a[i])*I.of(values[i]) for i in range(m)), ZERO)
            di = sum((I.of(b[i]-a[i])*I.of(values[i]) for i in range(m)), ZERO)
            dgerr2 = dgerr2 + radius(gi)*radius(gi)
            dderr2 = dderr2 + radius(di)*radius(di)
            target.set(j, gi); delta.set(j, di)
            tg2 = tg2+gi*gi
            dd2 = dd2+di*di
            for i in range(m):
                vi = I.of(values[i])
                norm2[i] = norm2[i]+vi*vi
                for k in range(i):
                    diff = vi-I.of(values[k])
                    pairs[i, k] = pairs[i, k]+diff*diff
        # Squared interval sums are mathematically nonnegative; only here clamp.
        def norm(v):
            return I(max(0, v.lo), v.hi).sqrt()
        source_norms = [norm(v) for v in norm2]
        distances = [norm(v) for v in pairs.values()]
        s = sum((I.of(a[i])*source_norms[i] for i in range(m)), ZERO)
        amp = ZERO if exact_d0 else norm(dd2)
        diameter = I(max((v.lo for v in distances), default=0), max((v.hi for v in distances), default=0))
        gnorm = ZERO if exact_g0 else norm(tg2)
        if structural:
            rho = tau = ZERO
        elif s.lo <= 0:
            raise Unresolved('nonstructural S lower endpoint')
        else:
            rho, tau = amp/s, diameter/(I.of(total)*s)
        pair_rms = norm(sum((v*v for v in distances), ZERO)/len(distances)) if distances else ZERO
        ed, eg = norm(dderr2), norm(dgerr2)
        errors = dict(E_d=ed, E_G=eg, E_S=radius(s), E_A=radius(amp),
                      E_D=radius(diameter), E_rho=radius(rho), E_tau=radius(tau),
                      E_u=ZERO if exact_d0 else (2*ed/I(amp.lo) if amp.lo > 0 else None),
                      E_target_relative=None if exact_g0 else radius(amp/gnorm))
        return dict(a=a, b=b, Z=z, G=target, d=delta, S=s, A=amp, rho=rho, tau=tau,
                    D=diameter, pair_rms=pair_rms, target_relative=None if exact_g0 else amp/gnorm,
                    structural_zero=structural, d_zero=exact_d0, G_zero=exact_g0,
                    u_zero=exact_d0, cancellation=exact_g0 and not exact_d0,
                    gradients=gradients, h=h, n=total, source_norms=source_norms,
                    errors=errors, error_target='exact sealed binary32; source perturbations zero',
                    denominator_status='STRUCTURAL_ZERO' if structural else 'POSITIVE')
    except BaseException:
        target.close(); delta.close()
        raise


def release(row):
    row['G'].close(); row['d'].close()


def radius(value):
    """Error of the rational midpoint of an enclosing Q192 interval."""
    return I.of(F(value.hi-value.lo, 2*Q))


def replacement(row, positive, budget):
    budget.reserve('A03 Rj coordinate delta/norm/fixed projection', scans=4,
                   ops=16*row['h']+64)
    ss = projection = ZERO
    for j in range(row['h']):
        d = (I.of(f32(row['gradients'][1][j]))-I.of(f32(row['gradients'][0][j])))/row['n']
        if not positive:
            d = -d
        ss = ss+d*d
        projection = projection+d
    return dict(relative=I(max(0, ss.lo), ss.hi).sqrt()/row['S'],
                fixed_projection=projection/(I.of(row['h']).sqrt()*row['S']))


def projection(row, masks, uniform_masks, p0, budget, fixed=False):
    h, m = row['h'], len(row['a'])
    if len(masks) != 32 or len(uniform_masks) != 32 or not 0 < p0 <= 1:
        raise ValueError('32 paired attempts/positive p0 required')
    budget.reserve('A03 Pj masks/coordinates/residual/projection', scans=8+4*32*(m+1)+4*m,
                   ops=h*(16*32*m+16*m+64)+256)
    for left, right in zip(masks, uniform_masks):
        if len(left) != m or len(right) != m or any(v not in (0, 1) for v in (*left, *right)):
            raise ValueError('mask schema')
    # Mean masks are exact sums, sharing the same literal stream/attempt order.
    coeff = [row['a'][i]*F(sum(mask[i] for mask in masks), 32)/row['Z'] for i in range(m)]
    coeff0 = [row['a'][i]*F(sum(mask[i] for mask in uniform_masks), 32)/p0 for i in range(m)]
    y = y0 = r2 = r02 = ew2 = ex2 = ex02 = eu2 = ZERO
    fixed_unit = I.of(1)/I.of(h).sqrt() if fixed else None
    residual_first = residual_last = None
    for j in range(h):
        budget.actual['coordinates'] += 1
        x = sum((I.of(coeff[i])*I.of(f32(row['gradients'][i][j])) for i in range(m)), ZERO)
        x0 = sum((I.of(coeff0[i])*I.of(f32(row['gradients'][i][j])) for i in range(m)), ZERO)
        r, r0 = x-row['G'].get(j), x0-row['G'].get(j)
        u = fixed_unit if fixed else (ZERO if row['d_zero'] else row['d'].get(j)/row['A'])
        ew2 = ew2+radius(x-x0)*radius(x-x0)
        ex2 = ex2+radius(x)*radius(x)
        ex02 = ex02+radius(x0)*radius(x0)
        eu2 = eu2+radius(u)*radius(u)
        y, y0, r2, r02 = y+u*r, y0+u*r0, r2+r*r, r02+r0*r0
        if j == 0:
            residual_first = r.text()
        residual_last = r.text()
    if row['structural_zero']:
        y = y0 = ZERO
    else:
        y, y0 = y/row['S'], y0/row['S']
    # Direct enclosing operation graph includes weights, direction, scale and
    # dot products; its midpoint radii are absolute arithmetic error budgets.
    errors = dict(E_X=ex2.sqrt(), E_X0=ex02.sqrt(), E_W=ew2.sqrt(),
                  E_u=eu2.sqrt(), E_Y=radius(y), E_Y0=radius(y0), E_P=radius(y-y0))
    return dict(Y=y, Y0=y0, P=y-y0, residual=I(max(0, r2.lo), r2.hi).sqrt(),
                residual0=I(max(0, r02.lo), r02.hi).sqrt(),
                residual_first=residual_first, residual_last=residual_last,
                attempts=32, same_stream=True, errors=errors)


def probability_bound(a, eta, maximum, z, budget):
    budget.reserve('A03 Bnd source traversal', scans=2, ops=512)
    t = sum((x*y for x, y in zip(a, eta)), F(0))
    if z <= t:
        raise Unresolved('Z <= t')
    return dict(t=I.of(t), bound=I.of(2*maximum*t)/I.of(z-t))


def error_envelope(s, es, amplitude, ea, budget, propagation=None):
    budget.reserve('A03 E scalar propagation', scans=1, ops=512)
    if s <= es:
        return dict(status='UNRESOLVED', rho_error=None, E_tau=None, E_u=None, E_P=None)
    rho = I.of(ea)/I.of(s-es)+I.of(abs(amplitude)*es)/I.of(s*(s-es))
    result = dict(status='RESOLVED', rho_error=rho, E_S=I.of(es), E_A=I.of(ea),
                  E_d=None, E_tau=None, E_u=None, E_P=None)
    if propagation is not None:
        p = propagation
        ed, ediam, diameter, n = (I.of(p[k]) for k in ('E_d', 'E_D', 'D', 'N'))
        etau = ediam/(n*I.of(s-es))+diameter*I.of(es)/(n*I.of(s*(s-es)))
        eu = None if amplitude <= ea else 2*ed/I.of(amplitude-ea)+I.of(p['E_normalize'])
        ep = None
        if eu is not None:
            et = (1+eu)*I.of(p['E_W'])+eu*I.of(p['R_W'])+I.of(p['E_dot'])
            ep = et/I.of(s-es)+I.of(abs(p['T'])*es)/I.of(s*(s-es))+I.of(p['E_div'])
        result.update(E_d=ed, E_tau=etau, E_u=eu, E_P=ep)
    return result


def paired_summary(main, uniform, analytic, threshold, budget, seed_errors=None,
                   analytic_error=F(0), continuous_error=F(0)):
    budget.reserve('A03 S3 paired delta mean sd ci', scans=7, ops=1024)
    if len(main) != 3 or len(uniform) != 3:
        raise ValueError('three paired seeds required')
    delta = [I.of(x)-I.of(y) for x, y in zip(main, uniform)]
    mean = sum(delta, ZERO)/3
    variance = sum(((v-mean)*(v-mean) for v in delta), ZERO)/2
    sd = I(max(0, variance.lo), variance.hi).sqrt()
    t = (I.of(722)/39).sqrt()
    half = t*sd/I.of(3).sqrt()
    lower, upper = mean-half, mean+half
    errors = [I.of(v) for v in (seed_errors if seed_errors is not None else [0]*3)]
    if len(errors) != 3 or any(e.lo < 0 for e in errors):
        raise ValueError('three nonnegative seed errors')
    emean = sum(errors, ZERO)/3
    esd = sum((e*e for e in errors), ZERO).sqrt()/I.of(2).sqrt()
    ei = emean+t*esd/I.of(3).sqrt()+radius(half)+radius(mean)
    er = I.of(analytic_error)
    ec = None if continuous_error is None else I.of(continuous_error)
    # Endpoint tokens represent the exact algebraic L/U for boundary tests;
    # same-expression equality is proved symbolically, not by interval overlap.
    equal_endpoint = analytic in ('L', 'U') if isinstance(analytic, str) else False
    ai = lower if analytic == 'L' else upper if analytic == 'U' else I.of(analytic)
    included = equal_endpoint or (ai.lo >= (lower-ei-er).hi and ai.hi <= (upper+ei+er).lo)
    threshold_equal_lower = threshold == 'L'
    th = lower if threshold_equal_lower else I.of(threshold)
    strict = ec is not None and not threshold_equal_lower and (lower-ei-ec).lo > th.hi and (ai-er-ec).lo > th.hi
    return dict(mean=mean, sd=sd, L=lower, U=upper, t=t, included=included,
                passed=included and strict, endpoint_equality=equal_endpoint,
                df=2, same_seed_difference_first=True, E_mean=emean, E_SD=esd,
                E_I=ei, E_R=er, E_cont=ec)


def macro(rows, indices, budget):
    budget.reserve('A03 Ag fixed class/seed traversal', scans=2, ops=256)
    if not indices or any(len(row) != 3 for row in rows):
        raise ValueError('macro schema')
    return [sum((I.of(rows[i][s]) for i in indices), ZERO)/len(indices) for s in range(3)]


def intersection(statuses, budget):
    budget.reserve('A03 Ag eight-way intersection', scans=1, ops=256)
    if len(statuses) != 8:
        raise ValueError('four references times all/tail')
    def eligible(row):
        if isinstance(row, bool):
            return row
        return (row['passed'] and all(row[k] is not None for k in ('E_I', 'E_R', 'E_cont')))
    return all(eligible(row) for row in statuses)


class StreamJSON:
    """Depth/node/token-limited parser; discarded top-level fields never form trees."""
    def __init__(self, raw, budget):
        budget.scan('A02 UTF8 decode and stream parse', 2)
        self.text = raw.decode('utf-8')
        self.pos = self.nodes = 0
        self.decoder = json.JSONDecoder(parse_float=F, parse_constant=lambda s: (_ for _ in ()).throw(ValueError(s)))

    def ws(self):
        while self.pos < len(self.text) and self.text[self.pos] in ' \r\n\t':
            self.pos += 1

    def value(self, keep=True, depth=0, selected=None):
        self.nodes += 1
        if ACTIVE:
            ACTIVE.actual['json_nodes'] += 1
        if depth > 16 or self.nodes > 65536:
            raise Gate('JSON depth/node capacity')
        self.ws()
        ch = self.text[self.pos]
        if ch not in '[{':
            end = self.pos
            # raw_decode is applied only to one bounded scalar token.
            if ch == '"':
                end += 1
                escaped = False
                while end < len(self.text):
                    c = self.text[end]
                    if c == '"' and not escaped:
                        end += 1
                        break
                    escaped = c == '\\' and not escaped
                    if c != '\\':
                        escaped = False
                    end += 1
                    if end-self.pos > 4096:
                        raise Gate('JSON token capacity')
            else:
                while end < len(self.text) and self.text[end] not in ',]} \r\n\t':
                    end += 1
                    if end-self.pos > 4096:
                        raise Gate('JSON token capacity')
            value = self.decoder.decode(self.text[self.pos:end])
            self.pos = end
            return value if keep else None
        is_object = ch == '{'
        result = {} if is_object else []
        close = '}' if is_object else ']'
        self.pos += 1
        self.ws()
        if self.text[self.pos] == close:
            self.pos += 1
            return result if keep else None
        seen = set()
        while True:
            key = None
            if is_object:
                key = self.value(True, depth+1)
                if not isinstance(key, str) or key in seen:
                    raise ValueError('JSON key/duplicate')
                seen.add(key)
                self.ws()
                if self.text[self.pos] != ':':
                    raise ValueError('JSON colon')
                self.pos += 1
            retain = keep and (selected is None or key in selected)
            val = self.value(retain, depth+1)
            if retain:
                if is_object:
                    result[key] = val
                else:
                    result.append(val)
            self.ws()
            term = self.text[self.pos]
            self.pos += 1
            if term == close:
                break
            if term != ',':
                raise ValueError('JSON separator')
        return result if keep else None

    def parse(self, selected):
        value = self.value(selected=selected)
        self.ws()
        if self.pos != len(self.text):
            raise ValueError('trailing JSON')
        return value


def metadata(root, identities, budget, bundle):
    import base64
    inputs, cache, dsets = bundle['inputs'], {}, {}
    for group, path in WHITELIST:
        size = (root/path).stat().st_size
        if sum(v['raw_bytes'] for v in inputs)+size > 1048576:
            raise Gate('15-input byte ceiling')
        budget.reserve('A02 metadata read/hash/identity', read=size, scans=3)
        raw = (root/path).read_bytes()
        if len(raw) != size:
            raise Gate('input size changed')
        budget.scan('A02 cached raw IPC chunk traversal/copies', 2)
        for offset in range(0, size, 11000):
            rpc('cache_chunk', path=path, data=base64.b64encode(raw[offset:offset+11000]).decode('ascii'))
        normalized = raw.replace(b'\r\n', b'\n').replace(b'\r', b'\n')
        object_id = hashlib.sha1(b'blob '+str(len(normalized)).encode()+b'\0'+normalized).hexdigest()
        if object_id != identities[path]:
            raise Gate('frozen metadata Git identity: '+path)
        selected = None
        if group == 'D':
            selected = {'N_c', 'n_ic', 'class_groups', 'sources_per_class'} if path.endswith('counts.json') else {'label_mapping', 'spec', 'validation_rule', 'test_rule', 'artifact_sha256'}
        elif group == 'M':
            selected = {'B_seconds', 'rows'}
        elif group == 'F':
            selected = {'identity', 'draw_order', 'streams', 'mechanism', 'A', 'H', 'K', 'status'}
        elif group == 'G' and path.endswith('preregistration.json'):
            selected = {'references', 'input_versions', 'definitions'}
        elif group == 'G' and path.endswith('archive_verification.json'):
            selected = {'status', 'verified_files', 'main_comparisons'}
        elif group == 'G' and 'backbone' in path:
            selected = {'references', 'input_versions'}
        value = StreamJSON(raw, budget).parse(selected)
        cache[path] = value
        inputs.append(dict(action_id='A02', commit=COMMITS[group], path=path, raw_bytes=size,
                           raw_sha256=hashlib.sha256(raw).hexdigest(), git_object=object_id,
                           field_locators=','.join(sorted(value.keys())), checks='Git normalized LF identity',
                           status='PASS', missing=''))
        if group == 'D':
            ds = 'CIFAR100' if 'CIFAR100' in path else 'CIFAR10'
            dsets.setdefault(ds, {})['counts' if path.endswith('counts.json') else 'info'] = value
    bindings, b_rows = bundle['bindings'], bundle['B_requirements']
    acceptance = cache[WHITELIST[5][1]]
    archive = cache[WHITELIST[6][1]]['files']
    backbone = cache[WHITELIST[8][1]]['references']
    for ds, data in dsets.items():
        counts, info = data['counts'], data['info']
        C = info['spec']['classes']
        n, N = counts['n_ic'], counts['N_c']
        budget.scan('A02 D labels/count rows/classes/copies', 2+20+C)
        assert C in (10, 100) and len(n) == 20 and len(N) == C
        assert sorted(info['label_mapping'].values()) == list(range(C))
        assert len(info['label_mapping']) == C and info['spec']['clients'] == 20
        assert 'official_train' in info['validation_rule'] and 'official_test' in info['test_rule']
        assert all(len(row) == C and all(type(x) is int and 0 <= x <= 2**31-1 for x in row) for row in n)
        assert all(type(x) is int and x > 0 for x in N)
        order = sorted(range(C), key=lambda c: (-N[c], c))
        tail = order[(2*C)//3:]
        assert tail == counts['class_groups']['tail'] and len(tail) == (4 if C == 10 else 34)
        assert all(sum(n[i][c] for i in range(20)) == N[c] for c in range(C))
        for entry in acceptance['references']:
            ref = entry['reference']
            if ref['dataset'] != ds:
                continue
            budget.scan('A02 G reference/client/message binding', 22)
            other = next(v for v in backbone if v['reference_id'] == ref['reference_id'])
            assert ref == other
            assert ref['task_identity'] == info['spec']['identity'] == entry['binding']['task_identity']
            assert ref['state_sha256'] == entry['state_before'] == entry['state_after'] == entry['repeated_read']
            assert entry['binding']['class_groups'] == counts['class_groups']
            assert entry['binding']['label_mapping'] == info['label_mapping']
            assert entry['binding']['source_files']['counts.json']['sha256'] == info['artifact_sha256']['counts.json']
            assert entry['binding']['split_identity']['counts_source']['sha256'] == info['artifact_sha256']['counts.json']
            assert entry['binding']['split_identity']['validation_rule'] == info['validation_rule']
            assert entry['binding']['split_identity']['test_rule'] == info['test_rule']
            hashes = []
            for i in range(20):
                locator = f"messages/{ref['reference_id']}/client_{i:03d}.pt"
                sha = archive[locator]
                assert len(sha) == 64
                hashes.append(sha)
            bindings.append(dict(ref=ref['reference_id'], dataset=ds, task=ref['task_identity'],
                                 checkpoint=ref['checkpoint_path'], state=ref['state_sha256'],
                                 progress=str(ref['training_progress']), clients=20, classes=C,
                                 message_index_sha256=hashlib.sha256(''.join(hashes).encode()).hexdigest(),
                                 message_locator=f"messages/{ref['reference_id']}/client_{{000..019}}.pt",
                                 denominator_source=f"D/{ds}/counts.json:n_ic[0:20],N_c[0:{C}]",
                                 denominator_binding='reference_acceptance.json:references[].binding.source_files["counts.json"].sha256 + binding.split_identity.counts_source.sha256 == info.json:artifact_sha256["counts.json"]; counts.json:n_ic/N_c',
                                 field_sources='reference_acceptance.json:references[].reference.{reference_id,dataset,task_identity,checkpoint_path,state_sha256,training_progress}; backbone_preparation_v1/manifest.json:references[] equals reference; binding.{class_groups,label_mapping,split_identity}; phaseG1_2_full_v1/artifact_hashes.json:files[message_locator]',
                                 tail_denominator=len(tail), metadata_binding_status='PASS',
                                 binary_qualification='NOT_RUN'))
            for c in range(C):
                budget.scan('A04 class source pair/lifetime work rows', 4)
                m = sum(n[i][c] > 0 for i in range(20))
                assert m == counts['sources_per_class'][c]
                h = 129*C
                pairs = m*(m-1)//2
                b_rows.append(dict(ref=ref['reference_id'], c=c, N=N[c], m=m, h=h, pairs=pairs,
                                   source_coordinate_visits=m*h, pair_coordinate_visits=pairs*h,
                                   operation_bound=h*(128*m+32*pairs+64)+256,
                                   read_hash_actions='2 reads + 2 SHA scans per message; 80 messages total',
                                   copy_lifetimes='raw<=1929208 -> bounded decoded storage(?) -> packed float32 -> float64/Q192 -> release; output/seal cache separate',
                                   copy_bytes=f'packed_sources={4*m*h}; float64_sources={8*m*h}; interval_arena<=16*{h}*1024; storage/objects=null',
                                   time_bound=None, Windows_peak_bound=None,
                                   missing='binary qualification; decoder seconds/peak; independent Ri/vi; continuous projection proof; real epsilon'))
    m_record = cache[WHITELIST[14][1]]
    budget.scan('A02 M locator fields only')
    assert m_record['rows'] and all('L' in row and 'b_seconds' in row for row in m_record['rows'])
    bundle['auxiliary_locators'] = 'F:mechanism.identity/mechanism, preregistration.draw_order/streams; V:CIFAR10/CIFAR100.assignments; M:B_seconds/rows[].b_seconds/rows[].L; location only, none passed into B'
    assert len(bindings) == 4 and len(b_rows) == 220
    return inputs, bindings, b_rows


def container_count(value, depth=0):
    if depth > 16:
        raise Gate('container depth')
    if isinstance(value, dict):
        count = 1+sum(container_count(v, depth+1) for v in value.values())
    elif isinstance(value, (list, tuple)):
        count = 1+sum(container_count(v, depth+1) for v in value)
    else:
        if isinstance(value, str) and len(value.encode()) > 8192:
            raise Gate('scalar length capacity')
        return 0
    if count > 2048:
        raise Gate('container count capacity')
    return count
