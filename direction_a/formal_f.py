"""Exact rational simulation utilities; no models, samples, or CUDA imports."""
from fractions import Fraction as F

N = 2**53
DELTA = F(16, 5)
IDS = tuple(f'client_{i:03d}' for i in range(20))
SCENARIOS = ('random', 'tail_slow', 'tail_fast')


def ceil(x):
    return -(-x.numerator // x.denominator)


def probability(L, speed, grid=N):
    L = F(L)
    if not 0 < L <= 1 or speed not in (1, 4):
        raise ValueError('invalid workload')
    A, H = ceil(F(9*grid, 10)), grid-ceil(F(grid, 20))
    x = (DELTA/(speed*L)-F(1, 4))/F(3, 2)
    K = max(0, min(grid, (grid*x).__floor__()+1))
    r = F(A*H*K, grid**3)
    ideal = F(171, 200)*min(1, max(0, x))
    assert abs(r-ideal) <= F(3, grid)
    assert r >= F(627, 2000)-F(3, grid) and r > 0
    return dict(q='2/5', r=str(r), p=str(F(2, 5)*r), A=A, H=H, K=K,
                continuous_r=str(ideal), continuous_error=str(abs(r-ideal)),
                display_r=float(r), display_error=str(abs(F(float(r))-r)),
                display_p=float(F(2,5)*r),display_p_error=str(abs(F(float(F(2,5)*r))-F(2,5)*r)))


def outcome(L, speed, draws, grid=N, rational=False):
    uo, ud, uj = map(F, draws) if rational else (F(int(k), grid) for k in draws)
    if not all(0 <= u < 1 for u in (uo, ud, uj)):
        raise ValueError('invalid exogenous value')
    duration = speed*F(L)*(F(1, 4)+F(3, 2)*uj)
    if uo >= F(9, 10):
        return 'offline', duration
    if ud < F(1, 20):
        return 'dropout', duration
    return ('returned' if duration <= DELTA else 'timeout'), duration


def classify(items, fields):
    complete, partial, unstarted = [], [], []
    for key, value in items.items():
        target = complete if all(f in value for f in fields) else partial if value else unstarted
        target.append(key)
    return dict(complete=complete, partial=partial, not_started=unstarted)


def charge(row, reference_bytes, returned):
    return dict(reference_downlink=reference_bytes,
                ordinary_state_return_preparation=row['return_bytes'],
                gradient_preparation=row['message_bytes'],
                effective_upload=(row['return_bytes']+row['message_bytes']) if returned else 0,
                W01_calls=1, W01_steps=5, W02_scans=1,
                W02_positions=row['sample_count'], service_seconds=str(F(row['b_seconds'])))
