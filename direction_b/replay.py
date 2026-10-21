"""B-E01 source-bound continuous replay. No target truth or gradient table enters state.

Parent owns model/gradient production, evaluation, pickle persistence and billing.
`step` consumes one buffer; `consume` twice returns an already-consumed receipt with
no vectors (and no repeated deployment). All communication is logical application
bytes, not network traffic. Initial model/each task download is a float32 D-vector.
"""
from __future__ import annotations
import os
for _name in ('OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'OMP_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ[_name] = '1'
import hashlib
import math
import random
import struct
import numpy as np

# epoch, client, seq, base_seq, source, dimension, encoding, nnz, residual norm
_HEADER = struct.Struct('<IIQQIIBId')
_ACK = struct.Struct('<IIQI')
_DOWN = struct.Struct('<IIQII')
DENSE, SPARSE = 0, 1
METHODS = ('R', 'C', 'CACHE', 'ABS', 'MSG', 'ID', 'AVG', 'Ucur', 'Uhist')


def _vector(x):
    x = np.asarray(x, dtype=np.float64)
    if x.ndim != 1 or not np.isfinite(x).all():
        raise ValueError('finite one-dimensional vector required')
    return x


def encode(vector, k=1.0, *, epoch=1, client=0, seq=1, base_seq=0,
           source=0, residual_norm=0.0):
    """Return an actual little-endian frame; Top-k ties choose smaller indices."""
    x = _vector(vector)
    d = len(x)
    if not 0 < k <= 1 or not 0 < d <= 2**32-1:
        raise ValueError('invalid k/dimension')
    if not math.isfinite(residual_norm) or residual_norm < 0:
        raise ValueError('invalid residual norm')
    if k == 1:
        kind, count = DENSE, d
        payload = x.astype('<f4').tobytes()
    else:
        kind, count = SPARSE, max(1, math.ceil(k*d))
        magnitudes = np.abs(x)
        cutoff = np.partition(magnitudes, d-count)[d-count]
        high = np.flatnonzero(magnitudes > cutoff)
        tied = np.flatnonzero(magnitudes == cutoff)[:count-len(high)]
        indices = np.sort(np.concatenate((high, tied))).astype('<u4')
        payload = indices.tobytes() + x[indices].astype('<f4').tobytes()
    frame = _HEADER.pack(epoch, client, seq, base_seq, source, d, kind,
                         count, residual_norm) + payload
    # Conversion overflow is an encoding error, not silently accepted infinity.
    if not np.isfinite(np.frombuffer(frame, '<f4', count=count,
          offset=_HEADER.size + (4*count if kind == SPARSE else 0))).all():
        raise ValueError('float32 payload overflow')
    return frame


def packet_info(frame):
    if len(frame) < _HEADER.size:
        raise ValueError('truncated header')
    values = _HEADER.unpack_from(frame)
    result = dict(zip(('epoch', 'client', 'seq', 'base_seq', 'source',
                       'dimension', 'kind', 'nnz', 'residual_norm'), values))
    d, count, kind = result['dimension'], result['nnz'], result['kind']
    if d < 1 or count < 1 or count > d or kind not in (DENSE, SPARSE):
        raise ValueError('invalid encoding metadata')
    if kind == DENSE and count != d:
        raise ValueError('dense count mismatch')
    expected = _HEADER.size + count*(4 if kind == DENSE else 8)
    if len(frame) != expected:
        raise ValueError('frame length mismatch')
    if not math.isfinite(result['residual_norm']) or result['residual_norm'] < 0:
        raise ValueError('invalid residual metadata')
    return result


def decode(frame):
    info = packet_info(frame)
    count, d = info['nnz'], info['dimension']
    if info['kind'] == DENSE:
        x = np.frombuffer(frame, '<f4', count=count, offset=_HEADER.size).astype(np.float64)
    else:
        indices = np.frombuffer(frame, '<u4', count=count, offset=_HEADER.size)
        if np.any(indices >= d) or np.any(indices[1:] <= indices[:-1]):
            raise ValueError('sparse indices not sorted, unique and in range')
        values = np.frombuffer(frame, '<f4', count=count, offset=_HEADER.size+4*count)
        x = np.zeros(d, dtype=np.float64)
        x[indices] = values
    if not np.isfinite(x).all():
        raise ValueError('nonfinite decoded values')
    return x


def _sq(x):
    return float(np.dot(x, x))


def _cos(gram, i, j):
    a, b = float(gram[i, i]), float(gram[j, j])
    if a <= 0 or b <= 0:
        return None
    return float(np.clip(gram[i, j]/math.sqrt(a*b), -1, 1))


def groups(gram, ids=None):
    """ID-order, first eligible group, complete-link cosine >= .8."""
    result = []
    for i in (range(len(gram)) if ids is None else sorted(ids)):
        for group in result:
            if all((c := _cos(gram, i, j)) is not None and c >= .8 for j in group):
                group.append(int(i))
                break
        else:
            result.append([int(i)])
    return result


def _communication():
    return {key: 0 for key in ('init_down', 'init_down_values', 'init_down_metadata', 'init_down_fixed_state', 'down_values', 'down_metadata', 'init_up_values', 'init_up_indices',
        'init_up_metadata', 'init_ack', 'down', 'up_values', 'up_indices',
        'up_metadata', 'ack', 'retransmission_bytes', 'retransmission_up_bytes',
        'retransmission_ack_bytes', 'natural_C_total',
        'total', 'diagnostic_dense_upload_bytes')}


def _charge_upload(state, frame, initial=False, retransmission=False):
    info = packet_info(frame)
    costs = state['communication']
    prefix = 'init_' if initial else ''
    costs[prefix+'up_values'] += 4*info['nnz']
    costs[prefix+'up_indices'] += 4*info['nnz']*(info['kind'] == SPARSE)
    costs[prefix+'up_metadata'] += _HEADER.size
    costs['total'] += len(frame)
    # Natural C frame uses identical fields except unused float64 residual norm.
    costs['natural_C_total'] += len(frame)-8
    if retransmission:
        costs['retransmission_bytes'] += len(frame)
        costs['retransmission_up_bytes'] += len(frame)


def _charge_ack(state, ack, initial=False, retransmission=False):
    costs = state['communication']
    costs['init_ack' if initial else 'ack'] += len(ack)
    costs['total'] += len(ack)
    costs['natural_C_total'] += len(ack)
    if retransmission:
        costs['retransmission_bytes'] += len(ack)
        costs['retransmission_ack_bytes'] += len(ack)


def _spawn(state, i, initial=False):
    rng = random.Random()
    rng.setstate(state['random_states'][i])
    jitter = rng.uniform(.9, 1.1)
    state['random_states'][i] = rng.getstate()
    state['task_seq'][i] += 1
    speed = 3.0 if state['hetero'] and i % 2 else 1.0
    state['pending_arrivals'][i] = {'client': i, 'source': state['t'],
        'task': int(state['task_seq'][i]), 'time': state['clock']+speed*jitter,
        'status': 'inflight'}
    header = _DOWN.pack(state['epoch'], i, int(state['task_seq'][i]), state['t'], state['D'])
    fixed = state['fixed_initialization_bytes'] if initial else 0
    amount = len(header) + 4*state['D'] + fixed
    costs = state['communication']
    prefix = 'init_' if initial else ''
    costs[prefix+'down_values'] += 4*state['D']
    costs[prefix+'down_metadata'] += len(header)
    costs['init_down_fixed_state'] += fixed
    costs['init_down' if initial else 'down'] += amount
    costs['total'] += amount
    costs['natural_C_total'] += amount
    state['counts']['tasks_spawned'] += 1


def new_state(initial, seed, k, hetero, *, buffer_size=4, max_buffers=16, fixed_initialization_bytes=0):
    """Only real initial full-client gradients; no other truth accepted.

    Production is N=20/B=4/t16; optional sizes exist solely for tiny boundary tests.
    After a consumed buffer, last_msgs are encoded frames, not a float64 NxD copy.
    """
    initial = np.asarray(initial, dtype=np.float64)
    if initial.ndim != 2 or not np.isfinite(initial).all():
        raise ValueError('initial must be finite NxD float64')
    n, d = initial.shape
    if not 0 < k <= 1 or not 1 <= buffer_size <= n or max_buffers < 1:
        raise ValueError('invalid replay configuration')
    frames = [encode(initial[i], 1, client=i, seq=0, base_seq=0, source=0) for i in range(n)]
    cache = np.stack([decode(frame) for frame in frames])
    norms = np.linalg.norm(cache, axis=1)
    residuals = np.linalg.norm(initial-cache, axis=1)
    frames = [frame[:_HEADER.size-8] + struct.pack('<d', float(residuals[i]))
              + frame[_HEADER.size:] for i, frame in enumerate(frames)]
    ratios = residuals/np.maximum(norms, 1e-12)
    gram = cache @ cache.T
    state = {'schema': 'B-E01-replay-v1', 'epoch': 1, 't': 0, 'seed': int(seed),
        'k': float(k), 'hetero': bool(hetero), 'N': n, 'D': d, 'B': int(buffer_size),
        'max_buffers': int(max_buffers), 'tau_max': 2*math.ceil(n/buffer_size),
        'fixed_initialization_bytes': int(fixed_initialization_bytes),
        'clock': 0.0, 'cache': cache, 'ratios': ratios, 'source_versions': np.zeros(n, np.int64),
        'known': np.ones(n, bool), 'last_msgs': frames,
        'hist_cache': cache.copy(), 'hist_ratios': ratios.copy(),
        'hist_source_versions': np.zeros(n, np.int64),
        'gram': gram, 'hist_gram': gram.copy(), 'msg_gram': gram.copy(), 'dirty': set(),
        'server_seq': np.zeros(n, np.int64), 'client_ack': np.zeros(n, np.int64),
        'task_seq': np.zeros(n, np.int64), 'pending': {}, 'pending_arrivals': [None]*n,
        'random_states': [random.Random(seed+1000*i).getstate() for i in range(n)],
        'committed_messages': {}, 'buffer': None, 'last_receipt': None,
        'communication': _communication(),
        'counts': {key: 0 for key in ('tasks_spawned', 'valid_returns', 'unique_contributions',
            'buffers_consumed', 'gradient_lookups', 'duplicate_messages', 'rejected_messages',
            'acks', 'initial_contributions')}}
    for i, frame in enumerate(frames):
        _charge_upload(state, frame, initial=True)
        _charge_ack(state, _ACK.pack(1, i, 0, 0), initial=True)
        state['counts']['initial_contributions'] += 1
        _spawn(state, i, initial=True)
    return state


def _refresh_grams(state):
    ids = sorted(state['dirty'])
    if not ids:
        return
    for key, matrix in (('gram', state['cache']), ('hist_gram', state['hist_cache'])):
        rows = matrix[ids] @ matrix.T
        state[key][ids, :] = rows
        state[key][:, ids] = rows.T
    messages = np.stack([decode(frame) for frame in state['last_msgs']])
    rows = messages[ids] @ messages.T
    state['msg_gram'][ids, :] = rows
    state['msg_gram'][:, ids] = rows.T
    state['dirty'].clear()


def begin_buffer(state):
    if state['buffer'] is not None:
        return state['buffer']
    if state['t'] >= state['max_buffers']:
        raise StopIteration('fixed replay horizon completed')
    _refresh_grams(state)
    n = state['N']
    state['buffer'] = {'id': state['t'], 'clock_open': state['clock'],
        'old': state['cache'].copy(), 'hist_old': state['hist_cache'].copy(),
        'ratios': state['ratios'].copy(), 'sources': state['source_versions'].copy(),
        'hist_ratios': state['hist_ratios'].copy(), 'hist_sources': state['hist_source_versions'].copy(),
        'groups': groups(state['gram']), 'msg_groups': groups(state['msg_gram']),
        'hist_groups': groups(state['hist_gram']),
        'id_groups': [list(range(n//2)), list(range(n//2, n))] if n > 1 else [[0]],
        'contributions': {}, 'communication_before': dict(state['communication']),
        'gram': state['gram'].copy(), 'hist_gram': state['hist_gram'].copy()}
    return state['buffer']


def next_arrival(state):
    begin_buffer(state)
    candidates = [a for a in state['pending_arrivals'] if a and a['status'] == 'inflight']
    if not candidates:
        raise RuntimeError('no remaining arrival')
    arrival = min(candidates, key=lambda a: (a['time'], a['client']))
    state['clock'] = max(state['clock'], arrival['time'])
    return dict(arrival)


def prepare_message(state, client, gradient, source=None):
    """Client preparation: only the already-returned client's source gradient."""
    buffer = begin_buffer(state)
    i = int(client)
    arrival = state['pending_arrivals'][i]
    if arrival is None or arrival['status'] != 'inflight' or state['clock'] < arrival['time']:
        raise ValueError('client has no returned task')
    if source is None:
        source = arrival['source']
    if int(source) != arrival['source']:
        raise ValueError('wrong task source')
    if i in state['pending']:
        return state['pending'][i]['frame']
    gradient = _vector(gradient)
    if gradient.size != state['D']:
        raise ValueError('gradient dimension mismatch')
    old = buffer['old'][i]
    frame = encode(gradient-old, state['k'], epoch=state['epoch'], client=i,
        seq=int(state['client_ack'][i])+1, base_seq=int(state['client_ack'][i]), source=int(source))
    reconstructed = old + decode(frame)
    residual = float(np.linalg.norm(gradient-reconstructed))
    frame = frame[:_HEADER.size-8] + struct.pack('<d', residual) + frame[_HEADER.size:]
    # Diagnostics use this source only, and dense float32 payloads, not future gradients.
    ucur = old + decode(encode(gradient-old, 1))-old
    hist_old = buffer['hist_old'][i]
    hist_frame = encode(gradient-hist_old, 1, client=i, source=int(source))
    hist_plus = hist_old + decode(hist_frame)
    state['pending'][i] = {'frame': frame, 'reconstructed': reconstructed,
        'ucur': ucur, 'hist_plus': hist_plus,
        'hist_residual': float(np.linalg.norm(gradient-hist_plus)),
        'hist_frame_bytes': len(hist_frame)}
    return frame


def receive(state, frame):
    """Server transaction: commits once before returning an ACK; truth-free.

    Rejected/duplicate frames are charged as actual attempted application uploads.
    A rejected frame never changes a cache, sequence or buffer contribution.
    """
    info = packet_info(frame)
    i = info['client']
    if not 0 <= i < state['N']:
        raise ValueError('invalid client')
    key = (i, info['seq'])
    digest = hashlib.sha256(frame).hexdigest()
    previous = state['committed_messages'].get(key)
    _charge_upload(state, frame, retransmission=previous is not None)
    if previous is not None:
        if previous != digest:
            state['counts']['rejected_messages'] += 1
            return {'status': 'rejected', 'reason': 'conflicting_duplicate', 'ack': None}
        state['counts']['duplicate_messages'] += 1
        ack = _ACK.pack(state['epoch'], i, info['seq'], info['source'])
        _charge_ack(state, ack, retransmission=True)
        return {'status': 'duplicate', 'ack': ack}
    reason = None
    if info['epoch'] != state['epoch'] or info['dimension'] != state['D']:
        reason = 'epoch_or_dimension'
    elif info['base_seq'] != state['server_seq'][i] or info['seq'] != state['server_seq'][i]+1:
        reason = 'base_or_sequence'
    elif state['t'] >= state['max_buffers']:
        reason = 'final_horizon'
    else:
        buffer = begin_buffer(state)
        arrival = state['pending_arrivals'][i]
        if i in buffer['contributions'] or len(buffer['contributions']) >= state['B']:
            reason = 'buffer_already_contributed_or_full'
        elif not arrival or arrival['status'] != 'inflight' or info['source'] != arrival['source']:
            reason = 'task_or_source'
        elif state['clock'] < arrival['time']:
            reason = 'not_arrived'
    if reason:
        state['counts']['rejected_messages'] += 1
        return {'status': 'rejected', 'reason': reason, 'ack': None}
    q = decode(frame)
    old = buffer['old'][i]
    plus = old + q
    u = plus-old  # The actual reconstructed difference, never raw q.
    prepared = state['pending'].get(i)
    if prepared is not None and prepared['frame'] != frame:
        state['counts']['rejected_messages'] += 1
        return {'status': 'rejected', 'reason': 'pending_content_mismatch', 'ack': None}
    contribution = {'client': i, 'seq': info['seq'], 'source': info['source'],
        'arrival_time': arrival['time'], 'task': arrival['task'], 'u': u,
        'reconstruction_rounding_squared': _sq(u-q), 'frame_bytes': len(frame)}
    if prepared is not None:
        if not np.array_equal(plus, prepared['reconstructed']):
            raise AssertionError('client/server actual reconstruction mismatch')
        hist_u = prepared['hist_plus']-buffer['hist_old'][i]
        contribution.update(ucur=prepared['ucur'], hist_u=hist_u)
        state['hist_cache'][i] = prepared['hist_plus']
        state['hist_ratios'][i] = prepared['hist_residual']/max(float(np.linalg.norm(prepared['hist_plus'])), 1e-12)
        state['hist_source_versions'][i] = info['source']
        state['communication']['diagnostic_dense_upload_bytes'] += prepared['hist_frame_bytes']
    state['cache'][i] = plus
    state['ratios'][i] = info['residual_norm']/max(float(np.linalg.norm(plus)), 1e-12)
    state['source_versions'][i] = info['source']
    state['last_msgs'][i] = frame
    state['server_seq'][i] = info['seq']
    state['committed_messages'][key] = digest
    buffer['contributions'][i] = contribution
    arrival['status'] = 'received'
    state['dirty'].add(i)
    state['counts']['valid_returns'] += 1
    state['counts']['unique_contributions'] += 1
    ack = _ACK.pack(state['epoch'], i, info['seq'], info['source'])
    _charge_ack(state, ack)
    return {'status': 'accepted', 'ack': ack}


def acknowledge(state, ack):
    epoch, i, seq, source = _ACK.unpack(ack)
    if epoch != state['epoch'] or not 0 <= i < state['N'] or seq > state['server_seq'][i]:
        raise ValueError('invalid acknowledgement')
    if seq <= state['client_ack'][i]:
        return False
    pending = state['pending'].get(i)
    if pending is None or packet_info(pending['frame'])['seq'] != seq:
        raise ValueError('ACK does not match client pending')
    info = packet_info(pending['frame'])
    if source != info['source']:
        raise ValueError('ACK source mismatch')
    state['client_ack'][i] = seq
    del state['pending'][i]
    state['counts']['acks'] += 1
    return True


def _qualification(state, buffer, hist=False):
    prefix = 'hist_' if hist else ''
    norms = np.linalg.norm(buffer[prefix+'old'], axis=1)
    ages = state['t']-buffer[prefix+'sources']
    ratios = buffer[prefix+'ratios']
    reasons = {'unknown': np.flatnonzero(~state['known']).tolist(),
        'norm': np.flatnonzero(norms <= 1e-12).tolist(),
        'residual': np.flatnonzero(~np.isfinite(ratios) | (ratios > .25)).tolist(),
        'age': np.flatnonzero((ages < 0) | (ages > state['tau_max'])).tolist()}
    bad = set(sum(reasons.values(), []))
    return [i for i in range(state['N']) if i not in bad], reasons, ages.tolist()


def _gate(partition, ids, reasons):
    result = {k: list(v) for k, v in reasons.items()}
    result['missing_groups'] = [j for j, group in enumerate(partition) if not set(group).intersection(ids)]
    return not any(result.values()), result


def _stratified(base, partition, contributions, field, n):
    value = base.copy()
    for group in partition:
        selected = [contributions[i][field] for i in group if i in contributions]
        value += (len(group)/n)*np.mean(selected, axis=0)
    return value


def _group_records(partition, contributions, n, b):
    records = []
    for group in partition:
        ids = [i for i in group if i in contributions]
        vectors = [contributions[i]['u'] for i in ids]
        mean = np.mean(vectors, axis=0) if vectors else None
        variance = sum(_sq(v-mean) for v in vectors)/len(vectors) if vectors else None
        records.append({'members': group, 'returned': ids, 'pi': len(group)/n,
            'f': len(ids)/b, 'change_dispersion': variance,
            'mean_change_squared': _sq(mean) if mean is not None else None})
    return records


def _agreement(buffer, common):
    main, hist = buffer['gram'], buffer['hist_gram']
    comparisons, changed, undefined = [], 0, 0
    min_edge = None
    for p, i in enumerate(common):
        for j in common[p+1:]:
            a, b = _cos(main, i, j), _cos(hist, i, j)
            if a is None or b is None:
                undefined += 1
                continue
            edge = min(abs(a-.8), abs(b-.8))
            min_edge = edge if min_edge is None else min(min_edge, edge)
            crossing = (a >= .8) != (b >= .8)
            changed += int(crossing)
            comparisons.append({'i': i, 'j': j, 'R_cosine': a, 'Uhist_cosine': b,
                'R_edge': a >= .8, 'Uhist_edge': b >= .8, 'threshold_crossing': crossing})
    ga, gb = groups(main, common), groups(hist, common)
    return {'common_qualified_clients': common, 'R_partition': ga, 'Uhist_partition': gb,
        'partitions_equal': ga == gb, 'threshold_crossings': changed,
        'undefined_pairs': undefined, 'minimum_threshold_distance': min_edge,
        'edge_comparisons': comparisons}


def consume(state):
    """Consume once. Repeated call returns receipt with empty vectors (no deployment)."""
    buffer = state['buffer']
    if buffer is None:
        if state['last_receipt'] is None:
            raise ValueError('no buffer to consume')
        return {'vectors': {}, 'diagnostics': state['last_receipt'], 'already_consumed': True}
    contributions = buffer['contributions']
    if len(contributions) != state['B']:
        raise ValueError('buffer not full')
    if any(state['client_ack'][i] != state['server_seq'][i] for i in contributions):
        raise ValueError('unacknowledged pending cannot be consumed')
    n, b = state['N'], state['B']
    ids = sorted(contributions)
    old_mean = np.mean(buffer['old'], axis=0)
    sum_u = np.sum([contributions[i]['u'] for i in ids], axis=0)
    c = old_mean + sum_u/b
    vectors = {'C': c, 'CACHE': old_mean+sum_u/n,
        'AVG': np.mean(state['cache'][ids], axis=0)}
    eligible, reasons, ages = _qualification(state, buffer)
    hist_eligible, hist_reasons, hist_ages = _qualification(state, buffer, True)
    gates = {}
    for name, key in (('R', 'groups'), ('ABS', 'groups'), ('MSG', 'msg_groups'), ('ID', 'id_groups')):
        partition = buffer[key]
        enabled, failures = _gate(partition, ids, reasons)
        gates[name] = {'enabled': enabled, 'reasons': failures}
        if not enabled:
            vectors[name] = c
        elif name == 'ABS':
            vectors[name] = sum((len(group)/n)*np.mean(state['cache'][[i for i in group if i in contributions]], axis=0)
                                for group in partition)
        else:
            vectors[name] = _stratified(old_mean, partition, contributions, 'u', n)
    if not all('ucur' in contributions[i] and 'hist_u' in contributions[i] for i in ids):
        raise ValueError('diagnostic replay requires source-bound prepare_message')
    uc = old_mean + np.mean([contributions[i]['ucur'] for i in ids], axis=0)
    vectors['Ucur'] = _stratified(old_mean, buffer['groups'], contributions, 'ucur', n) if gates['R']['enabled'] else uc
    hist_mean = np.mean(buffer['hist_old'], axis=0)
    hist_c = hist_mean + np.mean([contributions[i]['hist_u'] for i in ids], axis=0)
    enabled, failures = _gate(buffer['hist_groups'], ids, hist_reasons)
    gates['Uhist'] = {'enabled': enabled, 'reasons': failures}
    vectors['Uhist'] = _stratified(hist_mean, buffer['hist_groups'], contributions, 'hist_u', n) if enabled else hist_c
    reference = np.zeros(state['D'], np.float64)
    if gates['R']['enabled']:
        for group in buffer['groups']:
            selected = [contributions[i]['u'] for i in group if i in contributions]
            reference += (len(group)/n-len(selected)/b)*np.mean(selected, axis=0)
    record = {'buffer': state['t'], 'record_id': f"{state['seed']}:{state['k']}:{int(state['hetero'])}:{state['t']}",
        'clock_open': buffer['clock_open'], 'clock_close': state['clock'],
        'returned_ids': ids, 'sources': [contributions[i]['source'] for i in ids],
        'arrivals': [{key: contributions[i][key] for key in ('client', 'seq', 'source', 'arrival_time', 'task',
            'frame_bytes', 'reconstruction_rounding_squared')} for i in sorted(ids, key=lambda x: (contributions[x]['arrival_time'], x))],
        'partitions': {name: buffer[key] for name, key in (('R', 'groups'), ('MSG', 'msg_groups'), ('ID', 'id_groups'), ('Uhist', 'hist_groups'))},
        'gates': gates, 'old_source_versions': buffer['sources'].tolist(),
        'old_ratios': buffer['ratios'].tolist(), 'old_ages': ages, 'hist_old_ages': hist_ages,
        'group_changes': _group_records(buffer['groups'], contributions, n, b),
        'group_agreement': _agreement(buffer, sorted(set(eligible).intersection(hist_eligible))),
        'R_Uhist_gate_equal': gates['R']['enabled'] == gates['Uhist']['enabled'],
        'correction_squared': _sq(vectors['R']-c),
        'arithmetic_reference_difference_squared': _sq((vectors['R']-c)-reference),
        'vector_norm_squared': {name: _sq(vectors[name]) for name in METHODS},
        'unique_contributions': b}
    state['t'] += 1
    state['counts']['buffers_consumed'] += 1
    state['buffer'] = None  # Release full frozen NxD snapshots and change vectors.
    for i in ids:
        state['pending_arrivals'][i] = None
        if state['t'] < state['max_buffers']:
            _spawn(state, i)
    record['communication_delta'] = {key: state['communication'][key]-buffer['communication_before'][key]
                                       for key in state['communication']}
    record['communication_cumulative'] = dict(state['communication'])
    record['counts'] = dict(state['counts'])
    record['terminal_pending'] = [dict(a) for a in state['pending_arrivals'] if a] if state['t'] == state['max_buffers'] else []
    state['last_receipt'] = record
    return {'vectors': vectors, 'diagnostics': record, 'already_consumed': False}


def step(state, get_gradient):
    """Consume exactly one buffer, looking up ONLY actual returned (source,client)."""
    buffer = begin_buffer(state)
    # Resume a server commit preceding a lost ACK without looking up a gradient again.
    for i in list(buffer['contributions']):
        if state['client_ack'][i] < state['server_seq'][i]:
            result = receive(state, state['pending'][i]['frame'])
            acknowledge(state, result['ack'])
    while len(buffer['contributions']) < state['B']:
        arrival = next_arrival(state)
        i, source = arrival['client'], arrival['source']
        if i in state['pending']:
            frame = state['pending'][i]['frame']
        else:
            gradient = get_gradient(source, i)
            state['counts']['gradient_lookups'] += 1
            frame = prepare_message(state, i, gradient, source)
        result = receive(state, frame)
        if result['status'] not in ('accepted', 'duplicate'):
            raise RuntimeError('source-bound message rejected: '+result['reason'])
        acknowledge(state, result['ack'])
    return consume(state)


def boundary_tests():
    """Tiny synthetic high-D engineering checks; parent executes/bills this function."""
    import pickle
    d = 65537
    x = np.zeros(d, np.float64)
    x[2], x[5], x[9] = 2, -2, 1
    sparse = encode(x, 1/d)
    assert np.flatnonzero(decode(sparse)).tolist() == [2]
    dense = encode(x, 1)
    assert np.array_equal(decode(dense), x.astype(np.float32).astype(np.float64))
    all_sparse = encode(x, 1-.25/d)
    assert packet_info(all_sparse)['nnz'] == d
    assert np.array_equal(decode(all_sparse), decode(dense))
    # Float64 reconstructed subtraction need not equal decoded float32 q.
    large = np.full(d, 2**40, np.float64)
    raw = np.full(d, .1, np.float64)
    q = decode(encode(raw, 1))
    assert _sq((large+q-large)-q) > 0
    initial = np.stack([x+1 for _ in range(4)])
    state = new_state(initial, 2026102101, .1, False, max_buffers=2)
    begin_buffer(state)
    a = next_arrival(state)
    i = a['client']
    frame = prepare_message(state, i, initial[i]+.01, a['source'])
    info = packet_info(frame)
    bad = bytearray(frame)
    struct.pack_into('<Q', bad, 16, 99)  # base_seq offset
    before = state['cache'].copy()
    rejected = receive(state, bytes(bad))
    assert rejected['status'] == 'rejected' and np.array_equal(before, state['cache'])
    accepted = receive(state, frame)
    once = state['cache'].copy()
    duplicate = receive(state, frame)
    assert duplicate['status'] == 'duplicate' and np.array_equal(once, state['cache'])
    conflict = bytearray(frame)
    conflict[-1] ^= 1
    assert receive(state, bytes(conflict))['reason'] == 'conflicting_duplicate'
    state = pickle.loads(pickle.dumps(state))  # committed-before-ACK recovery
    assert acknowledge(state, accepted['ack'])
    assert not acknowledge(state, duplicate['ack'])
    calls = []
    def lookup(source, client):
        calls.append((source, client))
        return initial[client]+.01*source
    first = step(state, lookup)
    counts = dict(state['counts'])
    costs = dict(state['communication'])
    repeat = consume(state)
    assert repeat['already_consumed'] and repeat['vectors'] == {}
    assert state['counts'] == counts and state['communication'] == costs
    state = pickle.loads(pickle.dumps(state))
    second = step(state, lookup)
    assert state['t'] == 2 and state['counts']['unique_contributions'] == 8
    assert state['counts']['tasks_spawned'] == 8  # N + B, no spawn after final.
    assert all(source == 1 for source, client in calls[-4:])
    assert set(first['vectors']) == set(METHODS) and set(second['vectors']) == set(METHODS)
    assert first['diagnostics']['arithmetic_reference_difference_squared'] < 1e-20
    assert second['diagnostics']['arithmetic_reference_difference_squared'] < 1e-20
    try:
        step(state, lookup)
    except StopIteration:
        pass
    else:
        raise AssertionError('extra final buffer allowed')
    # Zero vectors form separate groups and force norm/coverage fallback.
    zero = new_state(np.zeros((4, 17)), 7, 1, False, max_buffers=1)
    out = step(zero, lambda s, i: np.zeros(17))
    assert out['diagnostics']['partitions']['R'] == [[0], [1], [2], [3]]
    assert not out['diagnostics']['gates']['R']['enabled']
    assert np.array_equal(out['vectors']['R'], out['vectors']['C'])
    return {'passed': True, 'dimension': d, 'dense_sparse_ties': True,
        'actual_reconstructed_difference': True, 'wrong_base_rejected': True,
        'duplicate_and_conflict_checked': True, 'commit_ack_pickle_recovery': True,
        'consume_idempotent': True, 'source_preserved': True,
        'zero_norm_gate': True, 'no_final_spawn': True,
        'frame_header_bytes': _HEADER.size, 'ack_bytes': _ACK.size,
        'download_header_bytes': _DOWN.size}


__all__ = ['new_state', 'step', 'encode', 'decode', 'packet_info', 'begin_buffer',
           'next_arrival', 'prepare_message', 'receive', 'acknowledge', 'consume',
           'groups', 'boundary_tests', 'METHODS']
# Error/MSE evaluation is deliberately left to the parent's truth-aware evaluator.
