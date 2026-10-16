"""Literal guard regression only; explicit I/O goes through the outer owner."""
import json
import os
import sys
import types

if os.environ.get('G13_RPC_ACTIVE') != 'guard-v1':
    raise SystemExit('shared outer supervisor required')
if sys.argv[1:] not in (['--guard-regression'], ['--continuation-probe']):
    raise SystemExit('B/C, inspect, and unsupervised entries closed')


def rpc(action, **values):
    print(json.dumps(dict(action=action, **values)), flush=True)
    reply = json.loads(sys.stdin.readline())
    if not reply['ok']:
        raise RuntimeError(reply['error'])
    return reply['value']


def main():
    import base64
    if sys.argv[1] == '--continuation-probe':
        before = rpc('snapshot')
        rpc('reserve', label='second interpreter continuation marker', scans=1,
            read=0, write=0, proxy=33554432)
        after = rpc('snapshot')
        assert after['used']['scans'] == before['used']['scans'] + 1
        assert before['used']['scans'] > 0
        rpc('result', value=dict(probe='PASS', before=before['used'], after=after['used']))
        return
    rpc('syntax_start')
    compiled = {}
    for path in ('direction_a/g1_3_preparation.py', 'scripts/prepare_direction_a_g1_3.py',
                 'tests/test_direction_a_g1_3_preparation.py'):
        raw = base64.b64decode(rpc('read', path=path))
        compiled[path] = compile(raw, path, 'exec')
    rpc('syntax_pass')
    module = types.ModuleType('guard_under_test')
    module.__file__ = os.path.abspath('direction_a/g1_3_preparation.py')
    exec(compiled['direction_a/g1_3_preparation.py'], module.__dict__)
    tests = {'__name__': 'guard_regression_only'}
    exec(compiled['tests/test_direction_a_g1_3_preparation.py'], tests)
    rpc('cpu_start')
    results = tests['run_guard_regressions'](module)
    rpc('result', value=results)


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        rpc('failure', value=dict(type=type(exc).__name__, location='guard regression',
            root_cause=str(exc), new_scientific_results=0))
        raise
