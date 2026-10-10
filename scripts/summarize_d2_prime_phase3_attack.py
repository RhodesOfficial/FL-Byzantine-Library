"""Offline phase-3.1 gate judgment from saved artifacts; independent constants only.

Damage, liveness, engineering and joint-search gates are evaluated with hand-written
reference constants (Q6 of the ruling), never with values produced by the tested run.
"""
from fractions import Fraction
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'outputs/d2_prime_phase3_1_attack_20261010'

# Independent reference constants (D2_PRIME_PHASE3_0_3_1_RULING Q6; 2.1 full_avg).
REFERENCE_M = Fraction(12719, 25000)          # 50.876%
REFERENCE_ENDPOINT = Fraction(262, 500)       # 52.40%
M_ATTACK_MAX = Fraction(45876, 100000)        # 45.876%
EVAL_POINTS = [10400, 10800, 11200, 11600, 12000]
SEGMENTS = {'L1': (6001, 8000), 'L2': (8001, 10000), 'L3': (10001, 12000)}
LIVENESS_MIN = Fraction(80, 100)
NONZERO_EPS = 1e-12


def read(path): return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def terminal_sequence(events):
    """Deterministic termination order from the journal: sequence 1..N."""
    order = [e['task_id'] for e in events if e['event'] == 'terminal']
    return {tid: i+1 for i, tid in enumerate(order)}


def damage_gate(curves):
    correct = curves['class_correct']
    assert curves['terminated_tasks'] == [0]+EVAL_POINTS, curves['terminated_tasks']
    per_point = [sum(point)/5000 for point in correct]  # macro accuracy at each eval point
    M = sum(Fraction(sum(point), 5000) for point in correct[-5:])/5
    endpoint = Fraction(sum(correct[-1]), 5000)
    damage = REFERENCE_M - M
    return {'per_point_macro_accuracy': {p: float(sum(point)/5000) for p, point in zip(EVAL_POINTS, correct)},
            'M_attack': float(M), 'M_attack_exact': str(M), 'reference_M': float(REFERENCE_M),
            'damage_pp': float(damage*100), 'M_gate_pass': M <= M_ATTACK_MAX,
            'endpoint': float(endpoint), 'reference_endpoint': float(REFERENCE_ENDPOINT),
            'endpoint_gate_pass': endpoint < REFERENCE_ENDPOINT,
            'pass': bool(M <= M_ATTACK_MAX and endpoint < REFERENCE_ENDPOINT)}


def liveness_gate(rows, events, malicious_ids):
    malicious = set(malicious_ids)
    sequence = terminal_sequence(events)
    by_id = {r['task_id']: r for r in rows}
    report, overall = {}, True
    for name, (lo, hi) in SEGMENTS.items():
        segment = [by_id[tid] for tid, seq in sequence.items()
                   if lo <= seq <= hi and by_id[tid]['identity'] in malicious]
        denominator = len(segment)
        legal_nonzero = [r for r in segment if r['arrived_at'] is not None
                         and r['raw_norm'] is not None and r['raw_norm'] > NONZERO_EPS]
        original_nonzero = sum(r['raw_norm'] is not None and r['raw_norm'] > NONZERO_EPS
                               for r in segment if r['first_packet_at'] is not None)
        legal_arrivals = sum(r['arrived_at'] is not None for r in segment)
        consumed = sum(r['state'] == 'consumed' for r in segment)
        expired = sum(r['state'] == 'expired' for r in segment)
        fraction = Fraction(len(legal_nonzero), denominator) if denominator else None
        passed = denominator > 0 and fraction >= LIVENESS_MIN
        overall = overall and passed
        report[name] = {'range': [lo, hi], 'denominator': denominator,
            'numerator_legal_nonzero': len(legal_nonzero),
            'fraction': float(fraction) if fraction is not None else None,
            'original_nonzero': original_nonzero, 'legal_arrivals': legal_arrivals,
            'model_consumed': consumed, 'expired': expired,
            'judgable': denominator > 0, 'pass': bool(passed)}
    return {'segments': report, 'pass': bool(overall)}


def engineering_gate(result, rows):
    total = len(rows)
    exact = result['all_actual_writebacks_exact']
    finite = result['maximum_E_model'] < 1e-3 and result['maximum_E_alg'] < 1e-3
    within_caps = (result['search_candidates_total'] <= result['candidate_hard_cap']
                   and result['gradients_total'] <= result['gradient_cap'])
    expected_candidates = result['decision_count']*32
    return {'exactly_12000_terminated': total == 12000,
            'all_writebacks_exact': bool(exact), 'errors_finite': bool(finite),
            'maximum_E_alg': result['maximum_E_alg'], 'maximum_E_model': result['maximum_E_model'],
            'search_candidates_total': result['search_candidates_total'],
            'candidate_hard_cap': result['candidate_hard_cap'],
            'gradients_total': result['gradients_total'], 'gradient_cap': result['gradient_cap'],
            'candidates_equal_decisions_times_32': result['search_candidates_total'] == expected_candidates,
            'gradients_equal_decisions': result['gradients_total'] == result['decision_count'],
            'within_caps': bool(within_caps), 'terminal_counts': result['terminal_counts'],
            'pass': bool(total == 12000 and exact and finite and within_caps
                         and result['search_candidates_total'] == expected_candidates
                         and result['gradients_total'] == result['decision_count'])}


def joint_search_gate(decisions):
    multi_release = [d for d in decisions if len(d['distinct_release_ticks']) >= 2]
    chosen_actions = {}
    for d in decisions:
        chosen_actions[d['chosen']['effective_action']] = chosen_actions.get(
            d['chosen']['effective_action'], 0)+1
    return {'decisions': len(decisions),
            'decisions_with_multiple_release_ticks': len(multi_release),
            'chosen_action_distribution': chosen_actions,
            'timing_actually_searched': len(multi_release) > 0,
            'pass': len(multi_release) > 0}


def summarize(name='full_attack'):
    directory = OUT/name
    config = read(OUT/'preregister.json')
    rows = read(directory/'tasks.json')
    events = read(directory/'events.json')
    result = read(directory/'result.json')
    curves = read(directory/'class_curves.json')
    decisions = [json.loads(line) for line in (directory/'decisions.jsonl').read_text().splitlines()]
    damage = damage_gate(curves)
    liveness = liveness_gate(rows, events, config['malicious_ids'])
    engineering = engineering_gate(result, rows)
    search = joint_search_gate(decisions)
    verdict = bool(damage['pass'] and liveness['pass'] and engineering['pass'] and search['pass'])
    report = {'unit': name, 'damage_gate': damage, 'liveness_gate': liveness,
              'engineering_gate': engineering, 'joint_search_gate': search,
              'PASS': verdict, 'logic': 'damage AND liveness AND engineering AND joint_search'}
    return report


if __name__ == '__main__':
    name = sys.argv[1] if len(sys.argv) > 1 else 'full_attack'
    report = summarize(name)
    (OUT/f'gate_report_{name}.json').write_text(
        json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False, indent=2))
