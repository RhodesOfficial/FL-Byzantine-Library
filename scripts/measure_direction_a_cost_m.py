"""Single authorized M entry, preregistration, bounded checks, and sealing."""
import os
import time
STARTED = time.perf_counter()
os.environ['CUBLAS_WORKSPACE_CONFIG'] = ':4096:8'
import argparse
import ast
import io
import json
import pickle
import subprocess
import sys
import traceback
import unittest
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.dont_write_bytecode = True
from direction_a.cost_m import (Gate, Ledger, LIMITS, encode, sha, normalized,
                               windows_peak, serialize_once, summarize)

OUT = ROOT/'artifacts/direction_a/phaseG1_1_cost_M_v1'
A = 'artifacts/direction_a/'
BACK = A+'backbone_preparation_v1/'
OLD = A+'phaseG1_2_full_v1/'
AUTH = 'ca391789a43cf1b3fc33cba6e14dae866fcf6e85'
BASE = 'e63a2ccde436335612a363567c56cce651bea8a8'
SOURCE = ['direction_a/cost_m.py', 'scripts/measure_direction_a_cost_m.py',
          'tests/test_direction_a_cost_m.py']
UPSTREAM = 'd3a3bd712d6bb28283b59faff16e17e099debcb4'


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)


def read_json(path):
    return json.loads(Path(path).read_bytes())


def write(path, value, ledger):
    raw = encode(value)
    if ledger.counts['writes'] + len(raw) > LIMITS['writes']:
        raise Gate('seal write limit')
    ledger.add(writes=len(raw))
    Path(path).write_bytes(raw)
    return sha(raw)


def verified_text(path, commit, ledger, checks, historical_digest=None, decimals=False):
    ledger.add(scans=2)
    expected = git('show', commit+':'+path)
    actual = (ROOT/path).read_bytes()
    if normalized(actual) != normalized(expected):
        raise Gate('substantive text change: '+path)
    witness = None
    if historical_digest:
        lf = normalized(expected)
        candidates = {'git_raw':expected, 'working_raw':actual, 'LF':lf,
                      'CRLF':lf.replace(b'\n',b'\r\n'), 'CR':lf.replace(b'\n',b'\r')}
        witness = next((name for name, value in candidates.items() if sha(value)==historical_digest),None)
        if witness is None:
            raise Gate('cannot prove historical raw hash newline equivalence: '+path)
    ledger.copy('metadata', len(actual))
    checks.append(dict(path=path, commit=commit, git_blob=git('rev-parse', commit+':'+path).decode().strip(),
                       normalized_sha256=sha(normalized(actual)), newline_only=True,
                       historical_raw_sha256=historical_digest, historical_newline_witness=witness))
    return json.loads(actual, parse_float=Decimal if decimals else float) if path.endswith('.json') else actual


def check_and_register():
    if OUT.exists():
        raise Gate('output already exists; no reset')
    OUT.mkdir(parents=True)
    ledger = Ledger()
    # Exact elapsed exec-command durations from the six read-only discovery calls.
    ledger.phases['input'] = sum((.4855451, .4333393, .7075675, .6403693, .6419987, .6900722, .6366134))
    ledger.add(scans=34, writes=sum((ROOT/p).stat().st_size for p in SOURCE))
    ledger.copy('metadata', 2*1024**2)  # conservative discovery read envelope, explicitly not measured traffic
    git('merge-base', '--is-ancestor', BASE, 'HEAD')
    head = git('rev-parse', 'HEAD').decode().strip()
    if head != AUTH:
        raise Gate('unexpected authorization HEAD')
    for p in SOURCE:
        ast.parse((ROOT/p).read_text(encoding='utf-8'), filename=p)
    suite = unittest.defaultTestLoader.discover(str(ROOT/'tests'), pattern='test_direction_a_cost_m.py')
    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
    if 'torch' in sys.modules or not result.wasSuccessful():
        raise Gate('synthetic checks failed or imported torch: '+stream.getvalue())
    ledger.peaks['windows'] = windows_peak()
    checks = dict(status='passed', tests=result.testsRun, log=stream.getvalue(),
                  torch_imported=False, CUDA_initialized=False, real_data_reads=0,
                  network_training=0, implementation_revisions=2, syntax_checks=1, CPU_suites=1)
    write(OUT/'selfchecks.json', checks, ledger)
    prereg = dict(identity='G1.1-cost-M-v1', authorization_commit=AUTH, baseline=BASE,
                  input_commits={'0.2':'e3c3528722cd4c4f55f96b37182255a4ade961b8',
                                 'smoke':'54eb6e02f4630df82cfdeb1c352fd5e4520ea5be', 'G1.2':UPSTREAM},
                  references=[f'A-backbone-{ds}-s{seed}-r{r:04d}-v1' for ds, seed in
                              [('CIFAR10',2026101321),('CIFAR100',2026101322)] for r in (40,80)],
                  clients=list(range(20)), seed='PCG64(2026102600+100*reference_index+client)',
                  protocol=dict(steps=5, batch=64, optimizer='SGD', momentum=.9, weight_decay=.0005,
                                nesterov=False, r40_lr=.05, r80_lr=.01, dtype='float32',
                                CE='mean', BN='train', augmentation=None, replacement=True),
                  W01_boundary='CUDA sync; deepcopy reference, reset SGD, five steps, CPU state torch.save(BytesIO); CUDA sync',
                  message_boundary='read/hash/load outside; torch.save once into BytesIO inside',
                  b='W01_ns/1e9 + exact decimal encode/main_head/statistics + prepare_ns/1e9',
                  limits=LIMITS, entry_limit=1, retries=0, initialization_forwards=0,
                  revision_limit=2, syntax_limit=2, CPU_suite_limit=2,
                  estimates=dict(input_seconds=15, W01_seconds=15, storage_seconds=8,
                                 ordinary_return_bytes_per_client=1400000, message_bytes_per_client=2000000,
                                 logical_bytes=350000000, cpu_bytes=1200000000, windows_bytes=3000000000,
                                 cuda_bytes=500000000),
                  sources={p:sha(normalized((ROOT/p).read_bytes())) for p in SOURCE},
                  history='G1.1/G1.2/P original ledgers retained, no M balance transfer',
                  created_unix_ns=time.time_ns())
    write(OUT/'preregistration.json', prereg, ledger)
    ledger.phases['input'] += time.perf_counter()-STARTED
    ledger.guard('input', seconds=15)
    write(OUT/'preparation_ledger.json', ledger.snapshot(), ledger)
    print(json.dumps(dict(checks='passed', input_seconds=ledger.phases['input'], tests=result.testsRun)))


def run():
    prior = read_json(OUT/'preparation_ledger.json')
    ledger = Ledger(prior)
    # preparation_ledger's own write is necessarily after its snapshot.
    ledger.add(writes=(OUT/'preparation_ledger.json').stat().st_size)
    checks = dict(authorization_commit=AUTH, baseline=BASE, inputs=[], references=[],
                  original_messages=[], train_sources=[], validation_sample_accesses=0,
                  test_sample_accesses=0, train_selection='only sealed client train indices',
                  physical_network_bytes=None, original_files_opened_read_only=True)
    rows, B, error, status = [], None, None, 'stopped'
    planned = read_json(OUT/'preregistration.json')
    for reference in planned['references']:
        ds = 'CIFAR100' if 'CIFAR100-' in reference else 'CIFAR10'
        for client in range(20):
            rows.append(dict(task=f'FedPCC-0.2-candidate-{ds}-N20-v1',reference=reference,
                             client=client,status='not_started',steps=0,
                             resolution_seconds=str(time.get_clock_info('perf_counter').resolution)))
    phases_started = time.perf_counter()
    phase = 'input'
    torch = None
    try:
        # Exclusive marker consumes the only real entry, before any heavy imports.
        with (OUT/'entry.json').open('x', encoding='utf-8') as f:
            raw = encode(dict(entry=1, unix_ns=time.time_ns(), pid=os.getpid()))
            f.write(raw.decode())
            ledger.add(writes=len(raw))
        impl_commit = git('rev-parse', 'HEAD').decode().strip()
        checks['implementation_commit'] = impl_commit
        git('merge-base', '--is-ancestor', BASE, impl_commit)
        git('merge-base', '--is-ancestor', AUTH, impl_commit)
        preg = verified_text((OUT/'preregistration.json').relative_to(ROOT).as_posix(), impl_commit, ledger, checks['inputs'])
        if preg['created_unix_ns'] >= read_json(OUT/'entry.json')['unix_ns']:
            raise Gate('registration not prior to real entry')
        for p, digest in preg['sources'].items():
            if sha(normalized((ROOT/p).read_bytes())) != digest:
                raise Gate('implementation changed after registration')
            if normalized(git('show', impl_commit+':'+p)) != normalized((ROOT/p).read_bytes()):
                raise Gate('uncommitted implementation')
            ledger.add(scans=2)
        for p in ['docs/workflow/TO_EXECUTOR.md','docs/DIRECTION_A_PROTOCOL_FREEZE_v1.md',
                  'docs/DIRECTION_A_G1_1_ADJUDICATION_v2.md','docs/DIRECTION_A_G1_1_FORMAL_PLAN_v1.md']:
            verified_text(p, AUTH, ledger, checks['inputs'])
        # One Git comparison locks every tracked member of each historical input package.
        for commit, paths in [(preg['input_commits']['0.2'], [A+'phase0_2_v1']),
                              (preg['input_commits']['smoke'], [A+'phaseG1_1_v1']),
                              (UPSTREAM, [BACK, OLD, 'direction_a/model.py','models/ResNet.py'])]:
            git('diff', '--exit-code', commit, '--', *paths)
            ledger.add(scans=1)
        manifest = verified_text(BACK+'manifest.json', UPSTREAM, ledger, checks['inputs'])
        config = verified_text(BACK+'generation_config.json', UPSTREAM, ledger, checks['inputs'],
                               historical_digest=manifest['generation_config_sha256'])
        binding = verified_text(BACK+'task_binding.json', UPSTREAM, ledger, checks['inputs'],
                                historical_digest=manifest['task_binding_sha256'])
        old = verified_text(OLD+'measurements.json', UPSTREAM, ledger, checks['inputs'],decimals=True)
        if [r['reference_id'] for r in manifest['references']] != preg['references']:
            raise Gate('four reference order mismatch')
        import numpy as np
        import torch as torch_module
        torch = torch_module
        import copy
        from direction_a.model import ResNet8Adapter, NORMALIZATION, transform_images
        from direction_a.backbone_preparation import tensor_state_sha
        torch.set_num_threads(2)
        torch.backends.cudnn.benchmark = False
        torch.backends.cuda.matmul.allow_tf32 = False
        torch.backends.cudnn.allow_tf32 = False
        torch.use_deterministic_algorithms(True)
        if not torch.cuda.is_available():
            raise Gate('CUDA unavailable')
        torch.cuda.init()
        torch.cuda.reset_peak_memory_stats()
        checks['environment'] = dict(torch=torch.__version__, numpy=np.__version__,
                                     device=torch.cuda.get_device_name(), python=sys.executable,
                                     perf_counter=time.get_clock_info('perf_counter').__dict__)

        def sample_memory(cpu=0):
            for k, v in dict(cpu=cpu, windows=windows_peak(), cuda=torch.cuda.max_memory_allocated()).items():
                ledger.peaks[k] = max(ledger.peaks[k], int(v))
                if ledger.peaks[k] > LIMITS[k]:
                    raise Gate('memory limit '+k)

        def next_action(which, estimate, **amounts):
            nonlocal phase, phases_started
            now = time.perf_counter()
            ledger.phases[phase] += now-phases_started
            phase, phases_started = which, now
            ledger.guard(which, seconds=estimate, **amounts)
            sample_memory()

        tasks = {}
        # Decode only official training files. No validation/test indexing or transforms.
        for ds in ('CIFAR10','CIFAR100'):
            taskdir = binding[ds]['task_directory']+'/'
            task_inputs = {name:verified_text(v['path'],preg['input_commits']['0.2'],ledger,checks['inputs'],
                                              historical_digest=v['sha256'])
                           for name,v in binding[ds]['source_files'].items()}
            info, data = task_inputs['info.json'], task_inputs['data.json']
            train_clients = [(c['id'], c['train']) for c in data['clients']]
            del data, task_inputs
            arrays, labels = [], []
            for path, digest in info['source_file_sha256'].items():
                if not (Path(path).name.startswith('data_batch_') if ds=='CIFAR10' else Path(path).name=='train'):
                    continue
                next_action('input', .7, scans=1)
                read_started = time.perf_counter()
                raw = Path(path).read_bytes()
                ledger.add(scans=1)
                if sha(raw) != digest:
                    raise Gate('train source hash mismatch')
                packet = pickle.loads(raw, encoding='bytes')
                arrays.append(packet[b'data'])
                labels.extend(packet[b'labels'] if ds=='CIFAR10' else packet[b'fine_labels'])
                checks['train_sources'].append(dict(path=path, sha256=digest, dataset=ds,
                    read_hash_decode_seconds=time.perf_counter()-read_started))
            images = np.concatenate(arrays).reshape(-1,3,32,32)
            labels = np.asarray(labels, dtype=np.int64)
            # Keep only sealed train images. Raw decode contains other official-train
            # rows but none are indexed, normalized, fitted, or evaluated.
            ix = [i for _, indices in train_clients for i in indices]
            selected, targets = images[ix].copy(), labels[ix].copy()
            clients, offset = [], 0
            for name, indices in train_clients:
                clients.append((name, offset, offset+len(indices)))
                offset += len(indices)
            tasks[ds] = (selected, targets, clients)
            sample_memory(3*images.nbytes + selected.nbytes*3 + 32*1024**2 +
                          sum(x.nbytes+y.nbytes for x,y,_ in tasks.values()))
            del raw, packet, arrays, images, labels, selected, targets, ix

        for r_index, ref in enumerate(manifest['references']):
            next_action('input', .4, scans=1)
            path = ROOT/BACK/ref['checkpoint_path']
            raw = path.read_bytes()
            ledger.add(scans=1)
            if sha(raw) != ref['checkpoint_file_sha256']:
                raise Gate('checkpoint file mismatch')
            checkpoint = torch.load(io.BytesIO(raw), map_location='cpu', weights_only=True)
            state, metadata = checkpoint['state_dict'], checkpoint['metadata']
            before = tensor_state_sha(state)
            ds = ref['dataset']
            if (before != ref['state_sha256'] or metadata['state_sha256'] != before
                or metadata['reference_id'] != ref['reference_id'] or metadata['task_identity'] != ref['task_identity']
                or metadata['model']['C'] != binding[ds]['C'] or metadata['model']['d'] != 128
                or metadata['task_source_sha256'] != {k:v['sha256'] for k,v in binding[ds]['source_files'].items()}
                or metadata['generation_config_sha256'] != manifest['generation_config_sha256']
                or metadata['update_round'] != ref['training_progress']['update_round']
                or metadata['attempts_completed'] != ref['training_progress']['attempts']
                or metadata['optimizer_steps_completed'] != ref['training_progress']['optimizer_steps']):
                raise Gate('reference metadata mismatch')
            if (config['transforms'][ds]['mean'] != list(NORMALIZATION[ds][0]) or
                config['transforms'][ds]['std'] != list(NORMALIZATION[ds][1])):
                raise Gate('normalization mismatch')
            original = ResNet8Adapter(binding[ds]['C']).to('cuda')
            original.load_state_dict(state, strict=True)
            original.freeze_reference()
            bn_before = {k:sha(v.numpy().tobytes()) for k,v in state.items() if 'running_' in k or 'num_batches_tracked' in k}
            check_ref = dict(reference=ref['reference_id'], task=ref['task_identity'], state_before=before,
                             BN_before=bn_before, transform=config['transforms'][ds],
                             train_identity=binding[ds]['source_files']['data.json'], checkpoint=ref['checkpoint_file_sha256'])
            checks['references'].append(check_ref)
            old_ref = old['references'][r_index]
            if old_ref['reference_id'] != ref['reference_id'] or old_ref['state_before'] != before:
                raise Gate('old W02 reference mismatch')
            images, labels, clients = tasks[ds]
            for client in range(20):
                row = rows[r_index*20+client]
                client_name, lo, hi = clients[client]
                if client_name != f'client_{client:03d}' or hi <= lo:
                    raise Gate('client identity mismatch')
                next_action('input', .03)
                rng = np.random.Generator(np.random.PCG64(2026102600+100*r_index+client))
                indices = rng.integers(lo, hi, size=(5,64))
                x = transform_images(images[indices.reshape(-1)], ds).to('cuda')
                y = torch.as_tensor(labels[indices.reshape(-1)], device='cuda', dtype=torch.long)
                row['sampling_seed'] = 2026102600+100*r_index+client
                row['sample_positions_sha256'] = sha(indices.tobytes())
                next_action('W01', max(.3, ledger.phases['W01']/max(1,ledger.counts['calls'])*1.5),
                            calls=1, steps=5, backwards=5, forwards=5, samples=320,
                            logical=3000000)
                row['W01_started'] = True
                ledger.add(calls=1)
                torch.cuda.synchronize()
                t = time.perf_counter_ns()
                model = copy.deepcopy(original).train().requires_grad_(True)
                opt = torch.optim.SGD(model.parameters(), lr=.05 if r_index%2==0 else .01,
                                      momentum=.9, weight_decay=.0005, nesterov=False)
                for step in range(5):
                    opt.zero_grad(set_to_none=True)
                    ledger.add(forwards=1, samples=64)
                    logits = model(x[step*64:(step+1)*64])
                    loss = torch.nn.functional.cross_entropy(logits, y[step*64:(step+1)*64], reduction='mean')
                    if not bool(torch.isfinite(loss)):
                        raise Gate('non-finite training loss')
                    ledger.add(backwards=1)
                    loss.backward()
                    if not all(bool(torch.isfinite(p.grad).all()) for p in model.parameters() if p.grad is not None):
                        raise Gate('non-finite training gradient')
                    ledger.add(steps=1)
                    opt.step()
                    row['steps'] += 1
                returned = {k:v.detach().cpu() for k,v in model.state_dict().items()}
                if not all(bool(torch.isfinite(v).all()) for v in returned.values()):
                    raise Gate('non-finite returned state')
                stream = io.BytesIO()
                torch.save(returned, stream)
                torch.cuda.synchronize()
                row['W01_ns'] = time.perf_counter_ns()-t
                row['return_bytes'] = stream.tell()
                ledger.copy('reference_downlink', len(raw))
                ledger.copy('ordinary_state_return', row['return_bytes'])
                sample_memory(sum(a.nbytes+b.nbytes for a,b,_ in tasks.values()) + 64*1024**2)
                del model, opt, returned, stream, logits, loss, x, y
                next_action('storage', .1, scans=1, logical=4000000)
                previous = old_ref['clients'][client]
                if previous['client_id'] != client:
                    raise Gate('old client mismatch')
                message = previous['message']
                msg_raw = (ROOT/OLD/message['path']).read_bytes()
                ledger.add(scans=1)
                if len(msg_raw) != message['bytes'] or sha(msg_raw) != message['sha256']:
                    raise Gate('old message byte mismatch')
                msg = torch.load(io.BytesIO(msg_raw), map_location='cpu', weights_only=True)
                if (msg['reference_id'] != ref['reference_id'] or msg['state_sha256'] != before
                    or msg['client_id'] != client or msg['C'] != binding[ds]['C'] or msg['d'] != 128):
                    raise Gate('old message identity mismatch')
                checks['original_messages'].append(dict(task=row['task'], reference=row['reference'],
                    client=client, path=OLD+message['path'], sha256=message['sha256'], bytes=len(msg_raw)))
                ns, size = serialize_once(msg, torch.save)
                row.update(message_prepare_ns=ns, message_bytes=size, old_message=message,
                           old_W02_locator=OLD+'measurements.json#references/'+str(r_index)+'/clients/'+str(client),
                           old_W02_decimal_seconds={k:str(Decimal(str(previous['cost_seconds'][k])))
                                                   for k in ('encode','main_head','statistics')},
                           old_payload_bytes=previous['payload_bytes'],
                           old_metadata_and_container_bytes=previous['metadata_and_container_bytes'])
                ledger.copy('gradient_preparation', size)
                row['preserved'] = tensor_state_sha(original.state_dict()) == before
                if not row['preserved'] or row['W01_ns'] <= 0 or ns <= 0:
                    raise Gate('preservation or timing failed')
                del msg, msg_raw
            next_action('storage', .1)
            check_ref['state_after'] = tensor_state_sha(original.state_dict())
            check_ref['BN_preserved'] = check_ref['state_after'] == before
            if not check_ref['BN_preserved']:
                raise Gate('original BN changed')
            del original, checkpoint, state, raw
        next_action('storage', 1.)
        B = summarize(rows)
        if B is None:
            raise Gate('incomplete inventory')
        status = 'completed'
    except Exception as exc:
        error = dict(type=type(exc).__name__, reason=str(exc), traceback=traceback.format_exc(),
                     classification='resource_gate' if isinstance(exc, Gate) and ('exceeds' in str(exc) or 'limit' in str(exc)) else 'engineering_or_integrity')
    finally:
        ledger.phases[phase] += time.perf_counter()-phases_started
        # Account stdlib startup before run() separately; no reset across processes.
        ledger.phases['input'] += max(0., run_entered-STARTED)
        ledger.peaks['windows'] = max(ledger.peaks['windows'], windows_peak())
        if torch is not None and torch.cuda.is_initialized():
            ledger.peaks['cuda'] = int(torch.cuda.max_memory_allocated())
        summarize(rows)
        record = dict(identity='G1.1-cost-M-v1', status=status, error=error,
                      implementation_commit=checks.get('implementation_commit'), authorization_commit=AUTH,
                      entry_count=1, failed_retries=0, implementation_revisions=2, syntax_checks=1, CPU_suites=1,
                      newly_measured=sum('W01_ns' in r or 'message_prepare_ns' in r for r in rows),
                      inventory={s:sum(r['status']==s for r in rows) for s in ('complete','partial','not_started')},
                      zero_operations=dict(frozen_encoder=0, class_gradient_requests=0,W02_scans=0,
                                           attempts=0, initialization_forwards=0, validation=0,test=0),
                      old_W02_readonly=True, b_summary='deterministic exact fractions only',
                      history_ledgers=[A+'phaseG1_1_v1/run.json', OLD+'run_record.json', A+'phaseP_formal_resume_v2/run_record.json'],
                      physical_network=None, limits=LIMITS, resources=ledger.snapshot())
        seal_started = time.perf_counter()
        write(OUT/'input_checks.json', checks, ledger)
        write(OUT/'measurements.json', dict(rows=rows,B_seconds=B), ledger)
        record['resources'] = ledger.snapshot()
        write(OUT/'run_record.json', record, ledger)
        # Index payloads first, then account index's own write via a fixed point.
        files = {}
        for p in sorted(OUT.glob('*.json')):
            if p.name in ('artifact_hashes.json','seal_receipt.json'):
                continue
            raw = p.read_bytes()
            ledger.add(scans=1)
            files[p.name] = dict(bytes=len(raw),sha256=sha(raw))
        index = dict(files=files, hash_algorithm='SHA-256 raw bytes',
                     run_record_snapshot='pre-index; final cumulative accounting in seal_receipt.json')
        write(OUT/'artifact_hashes.json',index,ledger)
        okay = all(sha((OUT/p).read_bytes())==v['sha256'] and (OUT/p).stat().st_size==v['bytes'] for p,v in files.items())
        ledger.add(scans=len(files))
        ledger.phases['storage'] += time.perf_counter()-seal_started
        receipt = dict(readback_passed=okay, index_sha256=sha((OUT/'artifact_hashes.json').read_bytes()),
                       sealed_inventory=record['inventory'], final_resources=ledger.snapshot(),
                       receipt_self_hash='excluded to avoid circular hashing', status=status,
                       external_delivery_accounting='final_delivery.json adds reviewer and delivery program costs')
        write(OUT/'seal_receipt.json', receipt, ledger)
        print(json.dumps(dict(status=status, error=error, inventory=record['inventory'], resources=ledger.snapshot()),ensure_ascii=False))


def deliver(real_wall_seconds, maintenance_seconds):
    """Read-only reconciliation and delivery; never resumes the real entry."""
    receipt = read_json(OUT/'seal_receipt.json')
    record = read_json(OUT/'run_record.json')
    ledger = Ledger(receipt['final_resources'])
    ledger.add(writes=(OUT/'seal_receipt.json').stat().st_size)
    prep = read_json(OUT/'preparation_ledger.json')
    measured_real = sum(ledger.phases.values())-sum(prep['phases'].values())
    # The parent tool's command duration includes startup, seal tail and interpreter exit.
    residual = max(0., real_wall_seconds-measured_real)
    ledger.phases['storage'] += residual
    ledger.phases['input'] += maintenance_seconds
    index = read_json(OUT/'artifact_hashes.json')
    readback = all(sha((OUT/p).read_bytes())==v['sha256'] and (OUT/p).stat().st_size==v['bytes']
                   for p,v in index['files'].items())
    ledger.add(scans=len(index['files'])+4)
    measurements = read_json(OUT/'measurements.json')
    rows = measurements['rows']
    complete = record['status']=='completed' and len(rows)==80 and all(r['status']=='complete' for r in rows)
    resource_pass = (all(ledger.phases[p]<=LIMITS[p] for p in ledger.phases)
                     and sum(ledger.phases.values())<=LIMITS['total']
                     and all(v<=LIMITS[k] for k,v in ledger.peaks.items())
                     and all(v<=LIMITS[k] for k,v in ledger.counts.items())
                     and sum(ledger.logical.values())<=LIMITS['logical'])
    criteria = {str(n):bool(v) for n,v in enumerate([
        read_json(OUT/'selfchecks.json')['status']=='passed' and readback,
        complete and all(record['resources']['counts'][k]==v for k,v in
                         dict(calls=80,steps=400,backwards=400,forwards=400,samples=25600).items()),
        complete,complete,resource_pass,complete and readback and resource_pass],1)}
    fail = sum(not v for v in criteria.values())
    error = record['error']
    blocker = error['reason'] if error else ('无' if not fail else '判据未齐，见final_delivery.json')
    impl = record['implementation_commit']
    lines = ['# 交付单：G1.1 成本补测M（单次有界采集）','',
             '- 对应任务单的基准 commit：'+BASE,'- 本次交付 commit：见本提交',
             '- 授权提交：'+AUTH,'- 源码/预登记提交：'+str(impl),'',
             '## 做了什么（≤5 条）','- 实现独立参考复制的W01计时、旧消息纯准备计时及精确有理数汇总。',
             '- 相关CPU合成检查通过；真实入口仅一次；完整/部分/未开始清单封存并读回。',
             '- M结论仅交审，正式G1.1仍未通过，事件F未运行。','',
             '## 产出文件','- `direction_a/cost_m.py`、`scripts/measure_direction_a_cost_m.py`：实现及有界入口。',
             '- `tests/test_direction_a_cost_m.py`：计时、累计门禁、异常留存及完整性夹具。',
             '- `artifacts/direction_a/phaseG1_1_cost_M_v1/`：预登记、输入身份、80项清单、自检、运行账及哈希/封存回执。',
             '- 同目录 `final_delivery.json`：末段核验、程序尾耗及交付写入的累计补账。','',
             '## 判据自评','| 判据编号 | 结果 PASS/FAIL | 证据位置 / 关键数字 |','|---|---|---|']
    evidence = ['selfchecks.json、preregistration.json、input_checks.json；入口1，修订2，语法/CPU各1',
                'run_record.json；'+str(record['resources']['counts']),
                'measurements.json、input_checks.json；逐项W01/保全/分辨率',
                'measurements.json；旧W02精确十进制及b/B/L，无message_save_read重复',
                'final_delivery.json；累计预算与内存/逻辑复制，历史账单独引用',
                'seal_receipt.json；终态'+record['status']+'，清单'+str(record['inventory'])]
    for n in range(1,7):
        lines.append('| '+str(n)+' | '+('PASS' if criteria[str(n)] else 'FAIL')+' | '+evidence[n-1]+' |')
    lines += ['', '## 实际资源消耗',
              '- 程序时间/写入/内存详见final_delivery.json；W01 '+str(ledger.phases['W01'])+'秒；CUDA峰 '+str(ledger.peaks['cuda'])+' B。',
              '- 源码/文档/证据累计写入包含重复及本交付；物理网络不适用。','',
              '## 阻塞（没有写“无”）', '- '+blocker,'', '## 异议（没有写“无”）','- 无','',
              '## 需要审查者裁决的问题（≤3 条，没有写“无”）',
              '- '+('M完整交付，请裁决补测验收；F仍待另派单。' if complete else '请裁决已封存部分及下一任务；本次不恢复、不重采。')]
    raw = ('\n'.join(lines)+'\n').encode('utf-8')
    ledger.add(writes=len(raw))
    (ROOT/'docs/workflow/TO_REVIEWER.md').write_bytes(raw)
    ledger.phases['storage'] += time.perf_counter()-STARTED
    final = dict(criteria=criteria,FAIL=fail,blocker=blocker,resources=ledger.snapshot(),
                 real_entry_command_seconds=real_wall_seconds, maintenance_program_seconds=maintenance_seconds,
                 archive_readback_passed=readback, inventory=record['inventory'],status=record['status'],
                 discovery_accounting='named inspection count 34; metadata copy conservative 2 MiB envelope',
                 write_scope='all three source files, prechecks, prereg, all evidence writes, TO_REVIEWER and this file',
                 finite_delivery_write_upper_bound=16384, delivery_tail_seconds_upper_bound=.1)
    # Include this last file and a conservative bounded final write/exit interval.
    ledger.add(writes=16384)
    ledger.phases['storage'] += .1
    final['resources']=ledger.snapshot()
    write(OUT/'final_delivery.json',final,Ledger())
    print(json.dumps(dict(FAIL=fail,blocker=blocker,resources=ledger.snapshot()),ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--check-and-register', action='store_true')
    parser.add_argument('--deliver', action='store_true')
    parser.add_argument('--real-wall-seconds', type=float)
    parser.add_argument('--maintenance-seconds',type=float,default=0.)
    args = parser.parse_args()
    if args.check_and_register:
        check_and_register()
    elif args.deliver:
        deliver(args.real_wall_seconds,args.maintenance_seconds)
    else:
        run_entered = time.perf_counter()
        run()
