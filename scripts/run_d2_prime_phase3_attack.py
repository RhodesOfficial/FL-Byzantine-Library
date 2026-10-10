"""Phase 3.1: causal_joint_32_v1 attack smoke and one full no-defense-average unit.

prepare  registers the frozen attack contract (malicious identities, optimization set,
         candidate family, Q, budgets, damage/liveness gates) before any smoke.
smoke    runs ~200 tasks and dumps the artifacts the engineering gate inspects.
unit     runs one full 12,000-task no-defense average under the attack from the
         original initial state.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys
import time
import traceback
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT/'outputs/d2_prime_phase2_1_async_20261009'
OUT = ROOT/'outputs/d2_prime_phase3_1_attack_20261010'
sys.path[:0] = [str(ROOT), str(ROOT/'easyFL')]
PYTHON = Path(r'E:\anaconda3\python.exe')

SOURCE_FILES = ['attacks/causal_joint_32.py', 'flgo_byzantine/async_attack_state.py',
    'flgo_byzantine/async_attack_algorithm.py', 'flgo_byzantine/async_baseline_state.py',
    'flgo_byzantine/async_baseline_algorithm.py', 'aggregators/async_rfa_contributions.py',
    'aggregators/contribution_diagnostics.py', 'scripts/run_d2_prime_phase3_attack.py',
    'scripts/summarize_d2_prime_phase3_attack.py', 'tests/test_d2_prime_phase3_attack.py',
    'easyFL/flgo/algorithm/asyncbase.py', 'easyFL/flgo/simulator/base.py']

GATE = {'reference_M': 0.50876, 'reference_endpoint': 0.5240,
        'M_attack_max': 0.45876, 'endpoint_below': 0.5240,
        'eval_points': [10400, 10800, 11200, 11600, 12000],
        'liveness_segments': {'L1': [6001, 8000], 'L2': [8001, 10000], 'L3': [10001, 12000]},
        'liveness_min_fraction': 0.80}


def read(path): return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def save(path, value): Path(path).write_text(
    json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)+'\n', encoding='utf-8')


def digest(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def object_digest(value): return hashlib.sha256(
    json.dumps(value, sort_keys=True, allow_nan=False).encode()).hexdigest()


def load_runner(method='avg', limit=200, points=None):
    import flgo
    import flgo_byzantine.async_attack_algorithm as algorithm
    from flgo.experiment.logger.simple_logger import SimpleLogger
    base = read(BASE/'preregister.json')
    task = Path(base['task'])
    options = dict(gpu=[0], num_rounds=12000, num_epochs=1, num_steps=-1, batch_size=64,
        learning_rate=.1, lr_scheduler='-1', optimizer='SGD', momentum=0., weight_decay=0.,
        seed=101, dataseed=0, num_workers=0, num_parallels=1, torch_num_threads=1,
        train_holdout=0., test_holdout=0., test_batch_size=128, no_tqdm=True,
        no_log_console=True, log_file=True, eval_interval=0, async_method=method,
        async_task_limit=limit, async_eval_points=points or [200],
        async_config_id='phase3-transient', byz_malicious_fraction=0.3, byz_seed=101)
    runner = flgo.init(str(task), algorithm, options, Logger=SimpleLogger)
    return runner, base, task


def build_opt_set(runner, base, task):
    import torch
    data = read(task/'data.json')
    names = data['client_names']
    malicious = sorted(runner.malicious_ids)
    union = sorted({int(i) for cid in malicious for i in data[names[cid]]['data']})
    dataset = runner.clients[0].train_data.dataset
    targets = [int(t) for t in dataset.targets]
    by_class = {}
    for idx in union:  # union already ascending => per-class "first 6" is lowest indices.
        by_class.setdefault(targets[idx], []).append(idx)
    chosen = []
    for cls in sorted(by_class):
        chosen.extend(by_class[cls][:6])
    if len(chosen) > 60:
        raise ValueError("optimization set exceeded 60 samples")
    info = read(task/'info')['root_data']
    pool, root = set(info['client_pool_indices']), set(info['root_indices'])
    if not set(chosen) <= pool or set(chosen) & root:
        raise ValueError("optimization indices must lie in the client pool and avoid the root")
    images = torch.stack([dataset[i][0] for i in chosen])
    labels = torch.tensor([targets[i] for i in chosen], dtype=torch.long)
    per_class = {int(c): len(by_class[c][:6]) for c in sorted(by_class)}
    record = {'malicious_ids': malicious, 'malicious_ids_sha256': object_digest(malicious),
        'optimization_indices': chosen, 'optimization_count': len(chosen),
        'per_class_counts': per_class, 'present_classes': sorted(per_class),
        'labels': [int(x) for x in labels.tolist()],
        'optimization_sha256': object_digest([chosen, [int(x) for x in labels.tolist()]]),
        'union_size': len(union), 'subset_of_client_pool': True, 'disjoint_from_root': True,
        'disjoint_from_development': not (set(chosen) & set(base['development_indices'])),
        'disjoint_from_final_evaluation': not (set(chosen) & set(base['final_evaluation_indices'])),
        'note': 'optimization samples are CIFAR10 train indices; evaluation uses held-out test indices'}
    return images, labels, record


def prepare():
    import torch
    runner, base, task = load_runner()
    for p, h in base['task_sha256'].items():
        assert digest(task/p) == h, p
    images, labels, opt = build_opt_set(runner, base, task)
    B_M = base['B_M']
    config = {k: base[k] for k in ('task', 'task_sha256', 'IR', 'alpha', 'num_clients', 'num_epochs',
        'batch_size', 'learning_rate', 'lr_scheduler', 'optimizer', 'momentum', 'weight_decay',
        'seed', 'dataseed', 'development_indices', 'final_evaluation_indices',
        'train_labels_sha256', 'test_labels_sha256', 'B_M', 'H', 'beta', 'K', 'eta_model',
        'task_limit', 'evaluation_points', 'max_outstanding', 'buffer_wait', 'lifetime',
        'max_staleness', 'dispatch_seed', 'slow_seed', 'delay_seeds', 'slow_ids', 'slow_ids_sha256',
        'fast_ids', 'delays_fast', 'delays_slow')}
    config.update(
        attack_registered_name='causal_joint_32_v1', byz_malicious_fraction=0.3, byz_seed=101,
        malicious_ids=opt['malicious_ids'], malicious_ids_sha256=opt['malicious_ids_sha256'],
        malicious_count=len(opt['malicious_ids']),
        optimization_set=opt, B_M_attack_clip_cap=10.0*B_M, server_clip_on_average=False,
        attack_directions='v1=unit(mu_vis); v2=unit(class-balanced CE grad of published model)',
        attack_gammas=[0.0, 0.5, 1.0, 4.0], attack_timings=['immediate', 'delay4', 'delay8', 'expire'],
        attack_vector_formula='u=clip_{10 B_M}(mu_vis - gamma*B_M*v_d); uploaded=theta_source-u',
        mu_vis_rule='mean of up to 20 most recent legally-arrived non-colluding raw updates by (arrival_tick, task_id); else this task normal local model-diff',
        Q='32 = 8 vectors x 4 timings per qualifying malicious task; no Q/2Q, no restart',
        proxy_horizon=32, proxy_rule='32-tick causal rollout on isolated pre-state copy; no new issue, no invisible honest arrival, tail frozen to real pre-state',
        gradient_budget_per_decision=1, candidate_hard_cap=32*base['task_limit'],
        gradient_cap=base['task_limit'], tie_break='max L_adv; then earlier release, smaller gamma, smaller direction; expire after finite releases',
        stop_rule='enumerate 32 then stop; no no-improvement restart',
        decision_timing='native available tick: expire -> collect arrivals -> decision -> real open-batch; no reading this tick commit; malicious sorted by task_id',
        damage_gate=GATE, reference_source='outputs/d2_prime_phase2_1_async_20261009/full_avg',
        source_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        registered_at=datetime.now(timezone.utc).isoformat(), device='cuda:0', dtype='float32',
        model='original CIFAR10 CNN, 797962 parameters, no buffers',
        source_sha256={p: digest(ROOT/p) for p in SOURCE_FILES})
    config['configuration_hash'] = object_digest({k: v for k, v in config.items()
        if k not in ('registered_at',)})
    OUT.mkdir(exist_ok=True)
    if (OUT/'preregister.json').exists():
        raise RuntimeError('registration already exists; preserve it before an explicit repair')
    save(OUT/'preregister.json', config)
    torch.save({'images': images, 'labels': labels}, OUT/'optimization_set.pt')
    print('REGISTERED '+json.dumps({'configuration_hash': config['configuration_hash'],
        'malicious_count': config['malicious_count'], 'optimization_count': opt['optimization_count'],
        'present_classes': opt['present_classes'], 'clip_cap': config['B_M_attack_clip_cap']}), flush=True)


def run_unit(smoke, override_limit=None):
    import copy
    import numpy as np
    import torch
    from attacks.causal_joint_32 import CausalJoint32Attacker
    from attacks.flgo_label_flip import LabelFlippedDataset
    from flgo.experiment.logger.simple_logger import SimpleLogger
    config = read(OUT/'preregister.json')
    for p, h in config['source_sha256'].items():
        assert digest(ROOT/p) == h, p
    diagnostic = override_limit is not None
    limit = 200 if smoke else (override_limit if diagnostic else config['task_limit'])
    points = [limit] if (smoke or diagnostic) else config['evaluation_points']
    runner, base, task = load_runner(limit=limit, points=points)
    for p, h in config['task_sha256'].items():
        assert digest(task/p) == h, p
    assert sorted(runner.malicious_ids) == config['malicious_ids']
    assert runner.baseline.capacity == 20 and runner.baseline.limit == 40
    assert sum(p.numel() for p in runner.model.parameters()) == 797962 and not list(runner.model.buffers())
    assert not any(k in vars(runner.baseline) for k in ('reference', 'budget', 'clip_norm'))
    initial = torch.cat([p.detach().reshape(-1) for p in runner.model.parameters()])
    initial_hash = hashlib.sha256(initial.cpu().numpy().tobytes()).hexdigest()
    assert initial_hash == 'f266aa56cc0cfc3947bb2b83966b309c3a14cce26801d47854a5655c53af5d0b'
    images, labels, opt = build_opt_set(runner, base, task)
    assert opt['optimization_sha256'] == config['optimization_set']['optimization_sha256']
    device = next(runner.model.parameters()).device
    scratch = copy.deepcopy(runner.model)
    runner.attacker = CausalJoint32Attacker(images, labels, opt['present_classes'],
                                            config['B_M'], scratch, device)
    assert not hasattr(runner.attacker, 'slow_ids') and not hasattr(runner.attacker, 'delay_rngs')
    label = 'smoke' if smoke else (f'diag{limit}' if diagnostic else 'full')
    directory = OUT/f'{label}_attack'
    if directory.exists():
        import shutil
        shutil.rmtree(directory)
    directory.mkdir()
    for p in ('record', 'log'):
        (directory/p).mkdir()

    class UnitLogger(SimpleLogger):
        def get_output_path(self): return str(directory/'record')
        def get_log_path(self): return str(directory/'log')
        def get_output_name(self, suffix='.json'): return directory.name+suffix
    import flgo_byzantine.async_baseline_algorithm as bridge
    assert len(runner.test_data) == 10000
    runner.test_data = torch.utils.data.Subset(runner.test_data, config['development_indices'])
    runner.calculator.collect_class_stats = True
    curves = {"terminated_tasks": [], "training_samples": [], "minibatches": [], "simulated_time": [],
              "model_version": [], "class_total": [500]*10, "class_correct": [], "macro_accuracy": []}

    def evaluate(progress):
        result = runner.test()
        stats = runner.calculator.last_class_statistics
        assert stats['class_total'] == [500]*10
        work = {k: sum(c.work[k] for c in runner.clients) for k in ('tasks', 'minibatches', 'examples')}
        for key, value in [('terminated_tasks', progress), ('training_samples', work['examples']),
            ('minibatches', work['minibatches']), ('simulated_time', runner.baseline.now),
            ('model_version', runner.baseline.version), ('class_correct', stats['class_correct']),
            ('macro_accuracy', sum(stats['class_correct'])/5000)]:
            curves[key].append(value)
        print('EVALUATE '+json.dumps({'tasks': progress, 'M': curves['macro_accuracy'][-1],
            'time': runner.baseline.now, 'version': runner.baseline.version}), flush=True)
    runner.on_evaluate = evaluate
    def log_safe(value):
        # Instrumentation-only: non-finite *logged* diagnostics become null so the
        # trajectory can be observed. Changes no computation; commit_next's own
        # torch.isfinite(model) assert still fires if the model itself overflows.
        if isinstance(value, float):
            return value if math.isfinite(value) else None
        if isinstance(value, dict):
            return {k: log_safe(v) for k, v in value.items()}
        if isinstance(value, list):
            return [log_safe(v) for v in value]
        return value
    decisions = (directory/'decisions.jsonl').open('w', encoding='utf-8')
    runner.on_decision = lambda record: (decisions.write(json.dumps(log_safe(record), allow_nan=False)+'\n'),
                                         decisions.flush())
    with (directory/'batches.jsonl').open('w', encoding='utf-8') as output:
        def on_batch(record):
            output.write(json.dumps(log_safe(record), allow_nan=False)+'\n')
            output.flush()
            if runner.baseline.terminated % 600 == 0:
                print(f'PROGRESS terminal={runner.baseline.terminated} issued={len(runner.baseline.tasks)} '
                      f'tick={runner.baseline.now} candidates={runner.search_candidates_total}', flush=True)
        runner.on_batch = on_batch
        start = time.perf_counter()
        try:
            runner.run()
        except Exception:
            save(directory/'failure.json', {'exception': traceback.format_exc(),
                'issued': len(runner.baseline.tasks), 'terminated': runner.baseline.terminated,
                'tick': runner.baseline.now, 'version': runner.baseline.version})
            raise
        elapsed = time.perf_counter()-start
    decisions.close()
    state = runner.baseline
    state.audit()
    rows = list(state.tasks.values())
    assert len(rows) == state.terminated == limit and not state.live and not state.fifo
    assert runner.gv.clock.empty() and not runner.malicious_delivery and not runner.malicious_waiting
    smoke = smoke or diagnostic  # M only meaningful on the full 5-point unit.
    work = {k: sum(c.work[k] for c in runner.clients) for k in ('tasks', 'minibatches', 'examples')}
    assert work['tasks'] == limit
    save(directory/'tasks.json', rows)
    save(directory/'events.json', state.journal)
    save(directory/'class_curves.json', curves)
    result = dict(configuration_hash=config['configuration_hash'], engineering_ok=True,
        task_limit=limit, work=work, simulated_time=state.now, model_version=state.version,
        initial_model_sha256=initial_hash, terminal_counts=dict(Counter(r['state'] for r in rows)),
        batch_sizes=dict(Counter(r['batch_size'] for r in state.batches)),
        batch_reasons=dict(Counter(r['reason'] for r in state.batches)),
        malicious_count=len(config['malicious_ids']), decision_count=runner.decision_count,
        expire_action_count=runner.expire_action_count, zero_direction_count=runner.zero_direction_count,
        search_candidates_total=runner.search_candidates_total, gradients_total=runner.gradients_total,
        candidate_hard_cap=config['candidate_hard_cap'], gradient_cap=config['gradient_cap'],
        maximum_E_alg=max((r['checks']['E_alg'] for r in state.batches if math.isfinite(r['checks']['E_alg'])), default=None),
        maximum_E_model=max((r['checks']['E_model'] for r in state.batches if math.isfinite(r['checks']['E_model'])), default=None),
        all_actual_writebacks_exact=all(r['checks']['writeback_exact'] for r in state.batches),
        elapsed_seconds=elapsed, peak_cuda_memory_allocated=torch.cuda.max_memory_allocated(),
        M=sum(curves['macro_accuracy'][-5:])/5 if not smoke else None,
        endpoint=curves['macro_accuracy'][-1])
    save(directory/'result.json', result)
    torch.save(runner.model.state_dict(), directory/'final_model_only.pt')
    for p, h in config['task_sha256'].items():
        assert digest(task/p) == h
    print('UNIT_COMPLETE '+json.dumps({k: result[k] for k in ('M', 'endpoint', 'work',
        'model_version', 'simulated_time', 'search_candidates_total', 'gradients_total',
        'terminal_counts', 'elapsed_seconds')}, allow_nan=False), flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('action', choices=['prepare', 'smoke', 'unit'])
    p.add_argument('--limit', type=int, default=None)
    args = p.parse_args()
    assert Path(sys.executable).resolve() == PYTHON.resolve()
    try:
        if args.action == 'prepare':
            prepare()
        else:
            run_unit(args.action == 'smoke', override_limit=args.limit if args.action == 'unit' else None)
    except Exception:
        traceback.print_exc()
        sys.exit(1)
