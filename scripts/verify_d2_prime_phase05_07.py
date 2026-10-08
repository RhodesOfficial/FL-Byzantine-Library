"""One clipped acceptance run: synthetic integration then one CIFAR smoke.

Always use E:\\anaconda3\\python.exe -B. No native runner.run(), root access,
task generation, attack controls, hyperparameter search or framework edits.
"""
import copy
from dataclasses import asdict
import hashlib
import io
import json
from pathlib import Path
import random
import subprocess
import sys
import time
from types import SimpleNamespace
import unittest

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT/"easyFL"), str(ROOT/"tests")]
assert Path(sys.executable).resolve() == Path(r"E:\anaconda3\python.exe").resolve()
import numpy as np
import torch
import flgo
from flgo.experiment.logger import BasicLogger
from flgo.utils.fmodule import FModule
from torchvision.datasets import CIFAR10
from flgo_byzantine import d2_prime_algorithm as adapter
from flgo_byzantine.d1_cifar_lt.common import TRANSFORM
from d2_prime.protocol import Reply
from d2_prime.recovery import rng_state, save_checkpoint_file, load_checkpoint_file
from test_d2_prime_recovery import clean, digest

TASK = ROOT/"outputs/d1_3b/smokeB_20260930/shared/tasks/cifar10/s1_m20_a0p1_ir50_v2"
MANIFEST = ROOT/"docs/D2_PRIME_PHASE05_07_MANIFEST.json"
EVIDENCE = ROOT/"docs/d2_prime_phase05_07_evidence"
RAW = dict(synthetic={}, smoke={})
INPUT_ID = None


class QuietLogger(BasicLogger):
    def initialize(self):
        pass


class FixedVector(FModule):
    def __init__(self):
        super().__init__()
        self.vector = torch.nn.Parameter(torch.tensor([10., 20.], dtype=torch.float64))


class TinyCifar(FModule):
    def __init__(self):
        super().__init__()
        self.conv = torch.nn.Conv2d(3, 4, 3, padding=1)
        self.pool = torch.nn.AdaptiveAvgPool2d((4, 4))
        self.head = torch.nn.Linear(64, 10)
        self.double()

    def forward(self, x):
        return self.head(self.pool(torch.relu(self.conv(x))).flatten(1))


def fixed_train(self, model):
    delta = self.option.get("d2_fixed_delta", [0., 0.])
    with torch.no_grad():
        model.vector.sub_(torch.tensor(delta, dtype=torch.float64))


def make_runner(real=False, **options):
    # FLGo decorates class methods during init: fresh subclasses prevent stacking
    # wrappers across paired runs. The application/core methods remain untouched.
    client_attrs = {} if real else {"train": fixed_train}
    algorithm = SimpleNamespace(__name__="d2_prime_async",
        Server=type("Server", (adapter.Server,), {}),
        Client=type("Client", (adapter.Client,), client_attrs))
    model = SimpleNamespace(__name__="tiny_cifar" if real else "fixed_vector",
        init_global_module=lambda ob: setattr(ob, "model", TinyCifar() if real else FixedVector())
        if ob.id == -1 else None)
    base = dict(gpu=[], sample="uniform", aggregate="uniform", proportion=.1,
        num_parallels=1, num_workers=0, torch_num_threads=1, eval_interval=0,
        no_tqdm=True, train_holdout=0., test_holdout=0., no_log_console=True,
        log_file=False, seed=101, dataseed=101, num_steps=1, batch_size=16,
        learning_rate=.01, momentum=0., weight_decay=0.,
        d2_protocol=dict(max_outstanding=40, capacity=20, lifetime=30., max_staleness=64,
                         clip_norm=1., eta_model=1.),
        d2_reference=dict(n_boot=3), d2_budget=dict(window=5., limit=.2),
        d2_task_limit=200 if real else 0, d2_dispatch_width=10)
    base.update(options)
    return flgo.init(str(TASK), algorithm, option=base, model=model, Logger=QuietLogger)


def qualification():
    info = json.loads((TASK/"info").read_text())
    data = json.loads((TASK/"data.json").read_text())
    root = info["root_data"]
    train = CIFAR10(root=Path(flgo.benchmark.data_root)/"CIFAR10", train=True,
                    download=False, transform=TRANSFORM)
    test = CIFAR10(root=Path(flgo.benchmark.data_root)/"CIFAR10", train=False,
                   download=False, transform=TRANSFORM)
    ids = [i for name in data["client_names"] for i in data[name]["data"]]
    root_ids, pool = set(root["root_indices"]), set(root["client_pool_indices"])
    assert len(ids) == len(set(ids)) and set(ids) == pool and not root_ids & pool
    assert len(root_ids) == 2000 and len(train) == 50000 and len(test) == 10000
    assert len(data["client_names"]) == info["num_clients"] == 100
    assert all(data[name]["data"] for name in data["client_names"])
    labels = np.array(train.targets)
    assert np.bincount(labels[list(pool)], minlength=10).tolist() == root["lt_counts"]
    assert np.bincount(labels[list(root_ids)], minlength=10).tolist() == root["root_counts"]
    hashes = {name: hashlib.sha256((TASK/name).read_bytes()).hexdigest() for name in ("info", "data.json")}
    hashes["train_labels"] = hashlib.sha256(labels.tobytes()).hexdigest()
    hashes["test_labels"] = hashlib.sha256(np.array(test.targets).tobytes()).hexdigest()
    return dict(task=str(TASK), hashes=hashes, clients=100, root_size=2000,
                client_pool_size=len(pool), lt_counts=root["lt_counts"], root_counts=root["root_counts"],
                imbalance_ratio=root["imbalance_ratio"], missing_fraction=root["missing_fraction"],
                root_client_overlap=0, defense_root_reads=0, evaluation_split="official CIFAR10 test, first 128",
                qualification_scope="data isolation/labels only; no stage1 or historical experiment credit")


def decision_stamp(server):
    sim = server.gv.simulator
    return digest(dict(protocol=vars(server.protocol), round=server.current_round,
        clock=server.gv.clock.time, queue=list(server.gv.clock.q.queue),
        simulator={k: v for k, v in vars(sim).items() if k not in {"server", "clients", "gv", "random_module"}},
        simulator_rng=sim.random_module.get_state(), dispatch_rng=server.dispatch_rng.get_state(),
        rng=rng_state(), counts=server.counts, work=[c.work for c in server.clients],
        model=adapter.parameter_vector(server.model), journal=server.journal, errors=server.errors))


def totals(server):
    p = server.protocol
    terminal = {state: sum(t.state == state for t in p.tasks.values())
                for state in ("consumed", "rejected", "expired", "cancelled", "lost")}
    assert server.counts["issued"] == len(p.tasks) == server.counts["executed"]
    assert sum(terminal.values()) + p.outstanding == len(p.tasks)
    assert server.counts["accepted"] == terminal["consumed"] == len(p.ledger)
    assert p.outstanding <= p.config.max_outstanding and len(p.buffer_ids) <= p.config.capacity
    assert p.audit_budget()
    work = {k: sum(c.work[k] for c in server.clients) for k in server.clients[0].work}
    return dict(**server.counts, terminal=terminal, outstanding=p.outstanding,
                buffer_size=len(p.buffer_ids), native_pending=len(server.gv.clock.q.queue),
                version=p.version, simulated_time=p.now, training=work, reconstruction_max_errors=server.errors)


def synthetic():
    small = dict(d2_protocol=dict(max_outstanding=8, capacity=1, lifetime=5., max_staleness=32),
                 d2_reference=dict(n_boot=1, eta_reference=.5), d2_budget=dict(window=2., limit=.375))
    server = make_runner(**small)
    server.dispatch([0], [0])
    assert server.protocol.version == 1 and server.protocol.ledger[0]["q"] == .375
    server.dispatch([0], [0])
    assert server.protocol.buffer_ids == (1,) and server.protocol.budget_remaining(0) == 0
    server.dispatch([1, 2], [1, 6])
    # Composite native boundary includes paid R1, one budget waiter and TWO
    # trained replies still in FLGo's clock. Restoring must never retrain them.
    assert len(server.gv.clock.q.queue) == 2 and server.protocol.outstanding == 3
    saved = server.save_d2_checkpoint(INPUT_ID)
    EVIDENCE.mkdir(exist_ok=True)
    path = EVIDENCE/"synthetic_checkpoint.pt"
    save_checkpoint_file(path, saved)
    assert digest(load_checkpoint_file(path)) == digest(saved)
    before = adapter.observable_state(server.protocol)
    altered = copy.deepcopy(saved)
    for elem in altered["runtime"]["queue"]:
        r = elem.x["reply"]
        elem.x["reply"] = Reply(r.task_id, r.identity, r.source_version, (999., -999.))
    hidden = make_runner(**small)
    hidden.load_d2_checkpoint(altered, INPUT_ID)
    assert adapter.observable_state(hidden.protocol) == before
    assert hidden.protocol.prepare_reference_event() == server.protocol.prepare_reference_event()
    server._in_transition = True
    try:
        try:
            server.save_d2_checkpoint(INPUT_ID)
            raise AssertionError("mid-transition save accepted")
        except RuntimeError:
            pass
    finally:
        server._in_transition = False
    # Reestablish RNG from the saved boundary after the observer-only probe.
    server.load_d2_checkpoint(saved, INPUT_ID)
    def suffix(s, logging):
        s.logging_enabled = logging
        # Deliberate duplicate of already consumed task 0 at the current time.
        s.gv.clock.put({"reply": Reply(0, 0, 0, (10., 20.)), "__cid": 0, "__t": 0}, 0)
        s.harvest()
        trajectory = [decision_stamp(s)]
        for _ in range(6):
            s.tick()
            totals(s)
            trajectory.append(decision_stamp(s))
        return trajectory
    baseline = suffix(server, False)
    restored = make_runner(**small)
    restored.load_d2_checkpoint(load_checkpoint_file(path), INPUT_ID)
    recovered = suffix(restored, True)
    assert baseline == recovered
    assert len(restored.logs) > 0
    p = restored.protocol
    assert p.version == 3 and [r["task_id"] for r in p.ledger] == [0, 1, 2]
    assert [t.state for t in p.tasks.values()] == ["consumed"]*3+["expired"]
    assert torch.equal(p.model, torch.tensor([10., 20.], dtype=torch.float64))
    e1 = .125/math_sqrt(1.04)
    e2 = e1+.125*(1-e1)
    assert abs(p.reference.evidence-(e2+.125*(1-e2))) <= 1e-14
    assert sum(row[0] == "invalid:duplicate_or_terminal" for row in p.trace) == 2
    # 40 legal arrivals, K=20: FIFO chunks at one clock time. Hand-computed
    # h=1 then h=1/2, g=1; model 10 - .125*(20/20+20/(2*20)).
    pulse = make_runner(d2_fixed_delta=[.125, 0.], d2_budget=dict(window=5., limit=1.))
    pulse.dispatch(list(range(40)), [1]*40)
    pulse.tick()
    assert (pulse.protocol.version, len(pulse.protocol.ledger), pulse.protocol.outstanding) == (2, 40, 0)
    assert abs(pulse.protocol.model[0].item()-9.8125) < 1e-12
    assert pulse.protocol.model[1].item() == 20.
    result = dict(boundary=dict(clock=0, version=1, pending_native=2, buffer=[1],
        ledger_length=1, budget_wait=[1], outstanding=3), paired_stamps=baseline,
        restore_stamps=recovered, totals=totals(restored), pulse=totals(pulse),
        final_state=vars(p), pulse_state=vars(pulse.protocol), journal=restored.journal,
        faults={"duplicate_packets_rejected": 1, "expired_packets_rejected": 1,
                "budget_wait_release": [0, 2], "concentrated_legal_arrivals": 40},
        future_observer_equal=True, checkpoint_sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    print("synthetic integration PASS", flush=True)
    return clean(result)


def math_sqrt(value):
    return value**.5


def evaluate(server):
    data = server.test_data
    x, y = torch.utils.data.default_collate([data[i] for i in range(128)])
    server.model.eval()
    with torch.no_grad():
        logits = server.model(x.double())
        loss = torch.nn.functional.cross_entropy(logits, y).item()
        correct = int((logits.argmax(1) == y).sum())
    assert np.isfinite(loss)
    server.counts["evaluations"] += 1
    server.counts["evaluation_examples"] += 128
    return dict(loss=loss, correct=correct, examples=128, accuracy=correct/128)


def smoke():
    start = time.perf_counter()
    server = make_runner(real=True)
    trajectory, saved, split, prefix_work = [], None, None, None
    for tick in range(500):
        server.tick()
        trajectory.append(decision_stamp(server))
        totals(server)
        if saved is None and server.counts["issued"] >= 100 and server.gv.clock.q.queue:
            saved = server.save_d2_checkpoint(INPUT_ID)
            path = EVIDENCE/"smoke_checkpoint.pt"
            save_checkpoint_file(path, saved)
            split = len(trajectory)
            prefix_work = totals(server)["training"]["tasks"]
        if server.counts["issued"] == 200 and not server.protocol.outstanding and server.gv.clock.empty():
            break
    else:
        raise AssertionError("smoke task/expiry drain deadlocked")
    assert saved is not None
    uninterrupted = totals(server)
    evaluation = evaluate(server)
    final_stamp = decision_stamp(server)
    restored = make_runner(real=True)
    restored.load_d2_checkpoint(load_checkpoint_file(EVIDENCE/"smoke_checkpoint.pt"), INPUT_ID)
    replay = []
    for _ in range(500):
        restored.tick()
        replay.append(decision_stamp(restored))
        totals(restored)
        if restored.counts["issued"] == 200 and not restored.protocol.outstanding and restored.gv.clock.empty():
            break
    else:
        raise AssertionError("restored smoke drain deadlocked")
    assert replay == trajectory[split:]
    assert evaluate(restored) == evaluation
    assert decision_stamp(restored) == final_stamp
    assert uninterrupted["issued"] == uninterrupted["executed"] == uninterrupted["arrivals"] == 200
    assert uninterrupted["training"]["optimizer_steps"] == 200
    assert uninterrupted["outstanding"] == uninterrupted["native_pending"] == 0
    print("real smoke PASS", flush=True)
    return clean(dict(totals=totals(restored), evaluation=evaluation, paired_trajectory=trajectory,
        recovered_suffix=replay, checkpoint_tick=split, checkpoint_issued=prefix_work,
        actual_optimizer_steps_both_branches=400-prefix_work,
        actual_eval_calls_both_branches=2, actual_eval_examples_both_branches=256,
        actual_examples_both_branches=uninterrupted["training"]["examples"]+
            totals(restored)["training"]["examples"]-sum(c["examples"] for c in saved["runtime"]["client_work"]),
        model_parameters=adapter.parameter_vector(restored.model).numel(), dtype="float64", device="cpu",
        wall_seconds=time.perf_counter()-start, final_state=vars(restored.protocol),
        configuration=server.option,
        journal=restored.journal, final_stamp=final_stamp,
        checkpoint_sha256=hashlib.sha256((EVIDENCE/"smoke_checkpoint.pt").read_bytes()).hexdigest()))


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.discover(str(ROOT/"tests"), pattern="test_d2_prime_*.py")
    output = io.StringIO()
    result = unittest.TextTestRunner(stream=output).run(suite)
    print(output.getvalue(), flush=True)
    assert result.wasSuccessful(), "pure synthetic prerequisites failed; real smoke not started"
    qualification_result = qualification()
    INPUT_ID = digest(qualification_result)
    RAW["synthetic"] = synthetic()
    RAW["smoke"] = smoke()
    paths = ["d2_prime/protocol.py", "d2_prime/reference.py", "d2_prime/budget.py",
             "d2_prime/recovery.py", "d2_prime/diagnostics.py", "flgo_byzantine/d2_prime_algorithm.py",
             "tests/test_d2_prime_recovery.py", "scripts/verify_d2_prime_phase05_07.py",
             "docs/D2_PRIME_DESIGN.md", "docs/D2_PRIME_CHECKPOINTS_TRIMMED.md",
             "docs/D2_PRIME_PHASE04_MANIFEST.json"]
    manifest = dict(status="PASS", gates="0.5+0.6+0.7 clipped", interpreter=sys.executable,
        base_commit=subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        input_id=INPUT_ID, qualification=qualification_result,
        code_hashes={p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths},
        configuration=RAW["smoke"]["configuration"],
        pure_tests=dict(run=result.testsRun, failures=len(result.failures), errors=len(result.errors)),
        prior_failures=[
            "pure fixture: KeyError state; historic manifest uses final_state; corrected lookup",
            "native import: sandbox denied ZMQ context; authorized local escalation succeeded",
            "diagnostic adapter: KeyError raw_delta; existing candidate field is delta; corrected lookup",
            "NumPy oracle: tuple bucket indices treated as multidimensional; converted to array",
            "checkpoint adapter: assumed stdlib queue.unfinished_tasks; native queue has only a heap; removed field"],
        earlier_successful_smoke=dict(reason="added diagnostic-negative and normal-source tests plus explicit configuration evidence",
            optimizer_steps=300, examples=4800, evaluation_calls=2, evaluation_examples=256,
            first_wall_seconds=13.899839999998221),
        tolerance=dict(absolute=1e-10, relative=0., discrete="exact", recovery="exact state SHA256"),
        torch_version=torch.__version__, cuda_available=torch.cuda.is_available(), results=RAW)
    MANIFEST.write_text(json.dumps(clean(manifest), ensure_ascii=False, sort_keys=True, allow_nan=False), encoding="utf-8")
    print(json.dumps(dict(status="PASS", pure_tests=result.testsRun, synthetic=RAW["synthetic"]["totals"],
                          smoke=RAW["smoke"]["totals"], wall_seconds=RAW["smoke"]["wall_seconds"]), ensure_ascii=False), flush=True)
