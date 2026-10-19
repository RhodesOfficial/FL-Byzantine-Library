"""Independent rational/radical oracles; only the metered runner executes this."""
import math
from fractions import Fraction as F


def root_oracle(r, coefficient=F(1)):
    r, scale = F(r), 1 << 256
    k = math.isqrt(r.numerator*scale*scale//r.denominator)
    assert k*k*r.denominator <= r.numerator*scale*scale
    assert (k+1)*(k+1)*r.denominator > r.numerator*scale*scale
    equal = k*k*r.denominator == r.numerator*scale*scale
    lo, hi = F(k, scale)*coefficient, F(k+(not equal), scale)*coefficient
    return (lo, hi) if coefficient >= 0 else (hi, lo)


def run_suite(api, budget, results):
    def full(h, x, y=0):
        budget.reserve('A03 full coordinate fixture', scans=1, ops=3*h)
        return [float(F(x)+F(y)*(1 if j % 2 == 0 else -1)) for j in range(h)]

    def invoke(group, h, kind, fn, verify=None, reject=False):
        budget.reserve('A03 independent oracle '+kind,
                       scans=1,
                       ops=dict(M=544*h+256, Pj=1648*h+256, Rj=16*h+64, E=128*h+512,
                                Bnd=128*h+512, S3=1024, Ag=256)[kind])
        record = dict(group=group, h=h, kind=kind, status='NOT_COMPLETED', expected='', observed='', checks='')
        results.append(record)
        checks, expected, observed = [], [], []
        def ck(name, got, want):
            if isinstance(want, tuple):
                passed = F(got.lo, api.Q) <= want[0] and F(got.hi, api.Q) >= want[1]
                actual = got.text()
            elif isinstance(got, api.I):
                passed = F(got.lo, api.Q) <= F(want) <= F(got.hi, api.Q)
                actual = got.text()
            else:
                passed, actual = got == want, str(got)
            checks.append(name+('=PASS' if passed else '=FAIL'))
            expected.append(name+'='+str(want)); observed.append(name+'='+actual)
            if not passed:
                raise AssertionError(f'{h}/{group}/{kind}/{name}: {actual} vs {want}')
        try:
            try:
                value = fn()
            except (ValueError, api.Unresolved) as exc:
                if not reject:
                    raise
                ck('actual_rejection', True, True)
                observed.append(type(exc).__name__+':'+str(exc)); value = None
            else:
                if reject:
                    raise AssertionError('expected rejection did not occur')
                verify(value, ck)
            record['status'] = 'PASS'
            return value
        finally:
            record.update(expected=';'.join(expected), observed=';'.join(observed), checks=';'.join(checks))

    for h in (1290, 12900):
        v, w = full(h, 1), full(h, 0, 1)
        p = [F(3, 4), F(1, 4)]
        def M(g=None, pp=None, ns=(1, 1), **kw):
            return api.metric(list(ns), list((v, w) if g is None else g), list(p if pp is None else pp), h, budget, **kw)
        def qcheck(r, c, scale=1, uniform=False):
            c('S', r['S'], root_oracle(h, F(scale)))
            c('D', r['D'], root_oracle(2*h, F(scale)))
            c('tau', r['tau'], root_oracle(2, F(1, 2)))
            c('rho', r['rho'], 0 if uniform else root_oracle(2, F(1, 4)))
            c('A', r['A'], 0 if uniform else root_oracle(2*h, F(scale, 4)))
            c('u_zero', r['u_zero'], uniform)
            c('a', r['a'], [F(1, 2)]*2)
            c('b', r['b'], [F(1, 2)]*2 if uniform else p)
            c('G_even', r['G'].get(0), scale); c('G_bias_last', r['G'].get(h-1), 0)
            c('d_even', r['d'].get(0), 0); c('d_bias_last', r['d'].get(h-1), 0 if uniform else F(scale, 2))
            c('pair_rms', r['pair_rms'], root_oracle(2*h, F(scale)))
        row = invoke('01', h, 'M', lambda: M(pp=[F(1, 2)]*2), lambda r, c: qcheck(r, c, uniform=True)); api.release(row)
        for group, positive in (('02', True), ('03', False)):
            row = invoke(group, h, 'M', M, qcheck)
            invoke(group, h, 'Rj', lambda: api.replacement(row, positive, budget),
                   lambda r, c: (c('relative', r['relative'], root_oracle(2, F(1, 2))),
                                  c('fixed_projection', r['fixed_projection'], F(-1 if positive else 1, 2))))
            api.release(row)
        row = invoke('04', h, 'M', lambda: M(g=(full(h, 4), full(h, 0, 4))), lambda r, c: qcheck(r, c, scale=4)); api.release(row)
        budget.scan('A03 ordered fixture')
        ordered = [float(F(j+1, 16384)) for j in range(h)]
        def ordered_check(r, c):
            budget.scan('A03 independent ordered full-coordinate comparison')
            for j in range(h):
                got = r['G'].get(j)
                assert got.lo == got.hi == (j+1)*api.Q//16384
            c('all_coordinate_order', True, True)
            c('S', r['S'], root_oracle(F(h*(h+1)*(2*h+1), 6*2**28)))
            c('exact_d_zero', r['d_zero'], True)
        row = invoke('04', h, 'M', lambda: M(g=(ordered,), pp=(F(1, 4),), ns=(2,)), ordered_check); api.release(row)
        def same(r, c):
            c('S', r['S'], root_oracle(h, F(5)))
            for key in ('A', 'D', 'rho', 'tau'):
                c(key, r[key], 0)
            c('G_even', r['G'].get(0), 7); c('G_bias_last', r['G'].get(h-1), -1)
        f = full(h, 3, 4)
        row = invoke('05', h, 'M', lambda: M(g=(f,), pp=(F(1, 4),), ns=(2,)), same); api.release(row)
        row = invoke('06', h, 'M', lambda: M(g=(f, f)), same); api.release(row)
        zero = full(h, 0)
        def zerock(r, c):
            for key in ('S', 'A', 'D', 'rho', 'tau'):
                c(key, r[key], 0)
            c('structural_zero', r['structural_zero'], True); c('u_zero', r['u_zero'], True)
            c('target_relative', r['target_relative'], None)
        row = invoke('07', h, 'M', lambda: M(g=(zero, zero)), zerock)
        masks = [[1, 1] for _ in range(32)]
        invoke('07', h, 'Pj', lambda: api.projection(row, masks, masks, F(1, 2), budget),
               lambda r, c: [c(k, r[k], 0) for k in ('Y', 'Y0', 'P', 'residual', 'residual0')]); api.release(row)
        invoke('07', h, 'Ag', lambda: api.macro([[0]*3, [F(1, 2)]*3], [0, 1], budget),
               lambda r, c: [c('macro'+str(s), r[s], F(1, 4)) for s in range(3)])
        def cancel(r, c):
            c('G_zero', r['G_zero'], True); c('cancellation', r['cancellation'], True)
            c('S', r['S'], root_oracle(h)); c('A', r['A'], root_oracle(h, F(1, 2)))
            c('rho', r['rho'], F(1, 2)); c('tau', r['tau'], 1); c('target_relative', r['target_relative'], None)
        row = invoke('08', h, 'M', lambda: M(g=(v, full(h, -1))), cancel); api.release(row)
        def no_bias(r, c):
            c('Z', r['Z'], F(1, 3)); c('b', r['b'], [F(1, 4), F(1, 4), F(1, 2)])
            c('G_even', r['G'].get(0), 1); c('G_bias_last', r['G'].get(h-1), 0)
            c('exact_d_zero', r['d_zero'], True); c('A', r['A'], 0)
        row = invoke('09', h, 'M', lambda: M(g=(v, w, full(h, F(1, 2), F(1, 2))), pp=(F(1, 4), F(1, 4), F(1, 2)), ns=(1, 1, 1)), no_bias); api.release(row)
        d = F(1, 1024)
        def near(r, c):
            c('S', r['S'], root_oracle(h, 1+d/2)); c('rho', r['rho'], d/(4+2*d))
            c('tau', r['tau'], d/(2+d)); c('d', r['d'].get(0), -d/4)
            c('near_synthetic_threshold', (r['D']/r['S']).hi <= api.I.of(F(1, 100)).lo, True)
        row = invoke('10', h, 'M', lambda: M(g=(v, full(h, 1+d))), near); api.release(row)
        row = invoke('11', h, 'M', M, qcheck)
        empty = [[0, 0] for _ in range(32)]
        invoke('11', h, 'Pj', lambda: api.projection(row, empty, empty, F(1, 2), budget, fixed=True),
               lambda r, c: (c('Y', r['Y'], F(-1, 2)), c('Y0', r['Y0'], F(-1, 2)), c('P', r['P'], 0), c('residual', r['residual'], root_oracle(F(h, 2)))))
        invoke('11', h, 'Pj', lambda: api.projection(row, [], empty, F(1, 2), budget), reject=True); api.release(row)
        invalid = [lambda: M(ns=(0, 0)), lambda: M(ns=(), g=(), pp=()), lambda: M(pp=(0, 0)),
                   lambda: M(pp=(-1, 1)), lambda: M(pp=(2, 1)), lambda: M(g=([float('nan')]*h, w)),
                   lambda: M(g=([float('inf')]*h, w)), lambda: M(g=([float('-inf')]*h, w)),
                   lambda: M(shape=((h//129, 127), (h//129,))), lambda: M(shape=((h//129, 128), (h//129+1,))), lambda: M(dtype='float64')]
        for fn in invalid:
            invoke('12', h, 'M', fn, reject=True)
        invoke('12', h, 'E', lambda: api.error_envelope(F(1), F(1), F(1), F(0), budget),
               lambda r, c: (c('status', r['status'], 'UNRESOLVED'), c('rho_missing', r['rho_error'], None)))
        invoke('13', h, 'Bnd', lambda: api.probability_bound([F(1, 2)]*2, [F(1, 16)]*2, F(1), F(1, 2), budget),
               lambda r, c: (c('t', r['t'], F(1, 16)), c('bound', r['bound'], F(2, 7))))
        invoke('13', h, 'Bnd', lambda: api.probability_bound([F(1, 2)]*2, [F(1, 16)]*2, F(1), F(1, 16), budget), reject=True)
        invoke('13', h, 'E', lambda: api.error_envelope(F(1), F(1, 4), F(1, 2), F(1, 8), budget), lambda r, c: c('rho_error', r['rho_error'], F(1, 3)))
        row = invoke('14', h, 'M', lambda: M(pp=[F(1, 2)]*2), lambda r, c: qcheck(r, c, uniform=True))
        invoke('14', h, 'Pj', lambda: api.projection(row, masks, masks, F(1, 2), budget, fixed=True),
               lambda r, c: (c('Y0', r['Y0'], F(1, 2)), c('residual', r['residual'], root_oracle(F(h, 2))),
                              c('residual_even', r['residual_first'], api.I.of(1).text()), c('residual_bias_last', r['residual_last'], api.ZERO.text())))
        invoke('14', h, 'Pj', lambda: api.projection(row, masks, masks, F(1, 2), budget),
               lambda r, c: (c('P', r['P'], 0), c('u_zero_Y', r['Y'], 0), c('nonzero_residual', r['residual'], root_oracle(F(h, 2))))); api.release(row)
        def pairedck(r, c):
            c('mean', r['mean'], 5); c('SD_ddof1', r['sd'], 1); c('t_df2', r['t'], root_oracle(F(722, 39)))
            lo, hi = root_oracle(F(722, 117))
            c('L', r['L'], (5-hi, 5-lo)); c('U', r['U'], (5+lo, 5+hi))
            c('included', r['included'], True); c('pass', r['passed'], True)
        invoke('14', h, 'S3', lambda: api.paired_summary([5, 6, 7], [1, 1, 1], 5, 1, budget), pairedck)
        invoke('14', h, 'S3', lambda: api.paired_summary([5, 6, 7], [1, 1, 1], 5, 'L', budget), lambda r, c: c('strict_L_equal_FAIL', r['passed'], False))
        invoke('14', h, 'S3', lambda: api.paired_summary([5, 6, 7], [1, 1, 1], 100, 1, budget), lambda r, c: (c('outside', r['included'], False), c('pass', r['passed'], False)))
        invoke('14', h, 'S3', lambda: api.paired_summary([5, 6], [1, 1], 5, 1, budget), reject=True)
        invoke('14', h, 'S3', lambda: api.paired_summary([1]*3, [0]*3, 1, 1, budget), lambda r, c: c('strict_point_equal_FAIL', r['passed'], False))
        for endpoint in ('L', 'U'):
            invoke('14', h, 'S3', lambda ep=endpoint: api.paired_summary([5, 6, 7], [1]*3, ep, 0, budget),
                   lambda r, c: (c('endpoint_included', r['included'], True), c('symbolic_equality', r['endpoint_equality'], True)))
        for ix, want in (([0, 1], 2), ([1], 3)):
            invoke('14', h, 'Ag', lambda ids=ix: api.macro([[1]*3, [3]*3], ids, budget), lambda r, c, v=want: [c('macro'+str(s), r[s], v) for s in range(3)])
        invoke('14', h, 'Ag', lambda: api.intersection([True]*7+[False], budget), lambda r, c: c('eight_intersection', r, False))
    assert len(results) == 92 and all(r['status'] == 'PASS' for r in results)
    assert api.f32(-0.0) == 0 and api.f32(2**-149) == F(1, 2**149)
    assert (api.I.of(F(1, 2**200)).lo, api.I.of(F(1, 2**200)).hi) == (0, 1)
    try:
        api.shift(1 << 4095, 1)
    except api.Gate as exc:
        assert 'PRECISION_CAP' in str(exc)
    else:
        raise AssertionError('4096-bit preflight absent')
    return results
