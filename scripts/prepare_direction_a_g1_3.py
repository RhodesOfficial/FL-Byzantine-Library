"""Run only under the sibling PowerShell cumulative supervisor."""
import os
import sys
from pathlib import Path

if os.environ.get('G13_OUTER_ACTIVE') != '1':
    raise SystemExit('Use scripts/prepare_direction_a_g1_3_outer.ps1; unmetered launch refused')
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from direction_a.g1_3_preparation import Budget, COMMITS, OUT, ROOT, WHITELIST, encode
import json
import time


def main():
    if sys.argv[1:] != ['--inspect']:
        raise SystemExit('B/C and other entries closed')
    OUT.mkdir(parents=True, exist_ok=True)
    budget = Budget()
    stats = [dict(group=g, commit=COMMITS[g], path=p, bytes=(ROOT/p).stat().st_size) for g, p in WHITELIST]
    assert len(stats) <= 24 and sum(r['bytes'] for r in stats) <= 1024**2
    budget.write('preregistration.json', dict(stage='A', whitelist=stats, real_entries=0,
        allocations=dict(time_seconds=[50,40,30], read_bytes=[2097152,1048576,1048576],
                         write_bytes=[2097152,1048576,1048576], scans=[128,64,64]),
        counts=dict(engineering=1, revisions=1, syntax=0, cpu=0),
        estimator='metadata bytes from stat; parse copies <=24*bytes; runtime risk allocation, not proved time bound',
        unknowns=dict(interpreter_io=None, physical_io=None), synthetic_only=True))
    schemas = []
    for r in stats:
        value = json.loads(budget.read(r['path']))
        def schema(v, depth=0):
            if depth > 2:
                return type(v).__name__
            if isinstance(v, dict):
                return {k:schema(x, depth+1) for k,x in list(v.items())[:16]}
            if isinstance(v, list):
                return dict(length=len(v), first=schema(v[0],depth+1) if v else None)
            return v
        schemas.append(dict(path=r['path'], schema=schema(value)))
    budget.write('input_index.json', dict(whitelist=stats, schemas=schemas, binary_reverified=False))
    budget.sealing = True
    budget.write('resource_ledger.json', budget.snapshot())
    print(json.dumps(schemas, ensure_ascii=False))


if __name__ == '__main__':
    main()
