"""Cached-code D4 child; started by outer.ps1, never a free-standing entry."""
import base64
import json
import os
import sys
import types
from pathlib import Path

if os.environ.get('G13_RPC_ACTIVE') != 'D4-v1':
    raise SystemExit('D4 protected owner required')


def rpc(action, **values):
    message = json.dumps(dict(action=action, token=os.environ['G13_TOKEN'], **values), separators=(',', ':'))
    if len(message.encode()) > 16384:
        raise RuntimeError('request frame too long')
    print(message, flush=True)
    line = sys.stdin.readline(16385)
    if not line or len(line.encode()) > 16384:
        raise RuntimeError('response frame')
    response = json.loads(line)
    if not response['ok']:
        raise RuntimeError(response['error'])
    return response.get('value')


def source(path):
    parts = []
    index = 0
    while index < 24:
        item = rpc('source', path=path, index=index)
        parts.append(base64.b64decode(item['data']))
        if item['last']:
            return b''.join(parts)
        index += 1
    raise RuntimeError('bounded source frames exhausted')


def main():
    mode = os.environ['G13_CHILD_MODE']
    if mode == 'probe':
        before = rpc('snapshot')
        after = rpc('continuation', expected=before['used']['scans'])
        assert after['used']['scans'] > before['used']['scans'] > 0
        rpc('probe', value=dict(status='PASS', before=before['used'], after=after['used'], inherited_job=True))
        return
    rpc('syntax_start')
    api = types.ModuleType('d4_kernel')
    api.__file__ = str(Path.cwd()/'direction_a/g1_3_preparation.py')
    # The runner itself was compiled once by the cached bootstrap.
    kernel = compile(source('direction_a/g1_3_preparation.py'), api.__file__, 'exec')
    suite_code = compile(source('tests/test_direction_a_g1_3_preparation.py'), 'tests/test_direction_a_g1_3_preparation.py', 'exec')
    rpc('syntax_pass')
    exec(kernel, api.__dict__)
    suite = {'__name__': 'D4_metered_suite'}
    exec(suite_code, suite)
    lease = rpc('lease')
    budget = api.Budget(lease)
    api.ACTIVE = budget
    bundle = dict(schema='G13-D4-v1', action_id='A02-A05', status='NOT_COMPLETED',
                  inputs=[], bindings=[], assertions=[], B_requirements=[], failures=[],
                  completed=[], partial=[], not_started=['A02', 'A03', 'A04'],
                  counters=dict(real_probability_calculations=0, gradient_binary_reads=0,
                                model_reads=0, formal_events=0, fitted_heads=0,
                                real_metrics=0, real_fee_calculations=0, registered_trajectories=0),
                  continuous_projection_bound=None, continuous_bound_reason='independent proof missing; B/C closed',
                  epsilon_bias=None, epsilon_num=None,
                  error_objects='sealed binary32 target perturbation=0 by definition; Q192 arithmetic width; historical sqrt(129C)*2e-6*Ri only implementation difference with Ri/vi unknown; continuous eta separate',
                  old_guard_reference='c35ae78:phaseG1_3_A_guard_v1/receipt.json; five prior successful cases not rerun')
    try:
        rpc('cpu_start')
        identities = rpc('identities')
        api.metadata(Path.cwd(), identities, budget, bundle)
        bundle['completed'].extend(['A02', 'A04'])
        bundle['not_started'] = ['A03']
        suite['run_suite'](api, budget, bundle['assertions'])
        bundle['completed'].append('A03'); bundle['not_started'] = []
        # New lease interfaces: explicit refusal before touching a sentinel.
        access = 0
        tiny = api.Budget(tiny=dict(read=0, write=0, scans=0))
        try:
            tiny.reserve('denied sentinel', read=1)
            access += 1
        except api.Gate:
            pass
        assert access == 0
        nested = api.Budget(tiny=dict(read=0, write=0, scans=1))
        nested.scan('outer accepted')
        try:
            nested.scan('inner denied')
            access += 1
        except api.Gate:
            pass
        assert nested.used['scans'] == 1 and access == 0
        budget.scan('A03 new interface witnesses', 8)
        bundle['guard_interfaces'] = dict(lease_refusal_before_access='PASS', zero_accesses=access,
                                           nested_partial_debit=1, byte_limit='PASS',
                                           outer_authorization='see receipt', subprocess='see receipt',
                                           small_byte_seal='see receipt')
        bundle['status'] = 'PASS'
    except Exception as exc:
        bundle['failures'].append(dict(type=type(exc).__name__, location='A02-A05',
                                      root_cause=str(exc)[:512], new_scientific_results=0))
        if bundle['assertions']:
            bundle['partial'].append('A03')
    finally:
        # Budget the bounded output graph before serialization/copy/write.
        nodes = api.container_count(bundle)
        budget.reserve('A05 bounded serialization/containers', scans=2*nodes, proxy=33554432)
        raw = (json.dumps(bundle, ensure_ascii=True, allow_nan=False, separators=(',', ':'))+'\n').encode()
        if len(raw) > 2097152:
            raise RuntimeError('bundle capacity')
        budget.reserve('A05 bundle write', write=len(raw))
        destination = Path(os.environ['G13_OUT'])/'bundle.json'
        destination.write_bytes(raw)
        rpc('settle', report=budget.report(), status=bundle['status'], failures=bundle['failures'],
            completed=bundle['completed'], partial=bundle['partial'], not_started=bundle['not_started'],
            assertion_count=len(bundle['assertions']))
    if bundle['status'] != 'PASS':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
