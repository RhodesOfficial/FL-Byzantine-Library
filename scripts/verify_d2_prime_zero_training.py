"""One-off CPU probe: native FLGo wiring, fixed replies, no training or repair."""
import copy
import io
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "easyFL")]
import torch
import flgo
from flgo.algorithm import asyncbase, fedbuff
from flgo.algorithm.fedbase import BasicClient
from flgo.benchmark.partition import IIDPartitioner
from flgo.utils.fmodule import FModule
from flgo_byzantine import toy_benchmark
from flgo_byzantine.algorithm import _model_from_update, _parameter_vector

assert Path(sys.executable).resolve() == Path(r"E:\anaconda3\python.exe").resolve()
OUT = ROOT / "outputs/d2_prime_zero_training_20261008"
OUT.mkdir(parents=True, exist_ok=True)
RUN = Path(tempfile.mkdtemp(prefix="run_", dir=OUT))
TASK = RUN / "synthetic_task"
flgo.gen_task_by_(toy_benchmark, IIDPartitioner(num_clients=2), str(TASK), seed=19)
CALLS = {"fixed_reply": 0, "forward": 0, "optimizer": 0, "loss": 0}
RESULT = {}


def forbidden(kind):
    def fail(*args, **kwargs):
        CALLS[kind] += 1
        raise AssertionError(f"Forbidden real computation: {kind}")
    return fail


class TensorCarrier(FModule):
    def __init__(self):
        super().__init__()
        self.vector = torch.nn.Parameter(torch.tensor([10., 20.]), requires_grad=False)

    forward = forbidden("forward")


def fixed_reply(self, model):
    CALLS["fixed_reply"] += 1
    with torch.no_grad():
        model.vector.add_(torch.tensor([1., -2.]) * (self.id + 1))


def make_runner(kind, latency=0):
    base = asyncbase.AsyncServer if kind == "async" else fedbuff.Server
    client = BasicClient if kind == "async" else fedbuff.Client
    # Fresh subclasses isolate flgo.init's class-level simulator decorators.
    algorithm = SimpleNamespace(__name__=f"probe_{kind}",
        Server=type("Server", (base,), {}),
        Client=type("Client", (client,), {"train": fixed_reply}))
    model = SimpleNamespace(__name__="fixed_tensor_carrier",
        init_global_module=lambda ob: setattr(ob, "model", TensorCarrier())
        if ob.id == -1 else None)
    svr = flgo.init(str(TASK), algorithm, model=model, option={
        "gpu": [], "sample": "uniform", "aggregate": "uniform",
        "proportion": 1., "num_parallels": 1, "num_workers": 0,
        "torch_num_threads": 1, "eval_interval": 0, "no_tqdm": True,
        "train_holdout": 0., "test_holdout": 0., "no_log_console": True,
        "algo_para": [] if kind == "async" else [1., 1.]})
    svr.current_round = 7
    svr.reference_marker = torch.tensor([3., 4.])
    svr.seen = []
    pack = svr.pack

    def stamped_pack(cid, mtype=0):
        pkg = pack(cid, mtype)
        pkg.update(task_id=f"7:{cid}", source_version=svr.current_round,
                   issued_at=svr.gv.clock.current_time,
                   reference_snapshot=svr.reference_marker.clone())
        return pkg

    svr.pack = stamped_pack
    handle = svr.package_handler

    def record(pkg):
        if pkg["__cid"]:
            svr.seen.append(copy.deepcopy(pkg))
        return handle(pkg)

    svr.package_handler = record
    for ob in [svr, *svr.clients]:
        ob.calculator.compute_loss = forbidden("loss")
        ob.calculator.get_optimizer = forbidden("optimizer")
    for c in svr.clients:
        reply = c.reply

        def stamped_reply(pkg, reply=reply):
            res = reply(pkg)
            res.update({k: pkg[k] for k in
                        ("task_id", "source_version", "issued_at", "reference_snapshot")})
            return res

        c.actions[0] = stamped_reply
    svr.gv.simulator.set_variable([0, 1], "latency", [latency, latency])
    return svr


def vector(svr):
    return _parameter_vector(svr.model).tolist()


def dispatch(svr):
    svr.gv.clock.step()
    return svr.iterate()  # The real inherited AsyncServer.iterate, not a replacement.


def release(svr, at):
    svr.sample = lambda: []  # No new tasks; isolate already-issued replies.
    svr.gv.clock.step(at - svr.gv.clock.current_time)
    return svr.iterate()


a, b = make_runner("async"), make_runner("fedbuff")
assert dispatch(a) and dispatch(b)
assert vector(a) == vector(b) == [11.5, 17.]
RESULT["1_wiring"] = {"status": "通过", "async": vector(a), "fedbuff": vector(b),
    "async_received": [int(cid) for cid in a.received_clients], "fedbuff_buffer_after": len(b.buffer)}
p = b.seen[0]
assert sorted(p["task_id"]) == ["7:0", "7:1"]
assert p["source_version"] == [7, 7] and p["issued_at"] == p["__t"] == [1, 1]
assert all(u._round == 7 for u in p["model"])
negative = -torch.stack([_parameter_vector(u) for u in p["model"]]).mean(0)
assert _parameter_vector(_model_from_update(TensorCarrier(), negative)).tolist() == vector(b)
s = make_runner("fedbuff", 2)
assert dispatch(s) is False
s.current_round = 8
with torch.no_grad():
    s.model.vector.copy_(torch.tensor([100., 200.]))
assert release(s, 3)
expected = torch.tensor([100., 200.]) + torch.tensor([1.5, -3.]) / (2 ** .5)
assert torch.equal(_parameter_vector(s.model), expected)
RESULT["2_source_sign"] = {"status": "通过", "zero_delay_mean": vector(b),
    "bridge_negative_update": negative.tolist(), "stale_result": vector(s),
    "source_versions": s.seen[0]["source_version"], "arrival": s.seen[0]["__t"]}

# Transport-only causality probe. This marker is NOT an implemented D2 reference.
d = make_runner("fedbuff", 2)
assert dispatch(d) is False
pending = copy.deepcopy(d.gv.clock.q.queue[0].x)
d.reference_marker.fill_(99.)
d.gv.clock.put(pending, pending["__t"])  # Replay the identical issued task fixture.
assert release(d, 3)
received = d.seen[0]
assert all(torch.equal(v, torch.tensor([3., 4.])) for v in received["reference_snapshot"])
assert len(received["task_id"]) == 3 and len(set(received["task_id"])) == 2
RESULT["4_causality_budget"] = {"status": "部分通过", "frozen_marker": [3., 4.],
    "later_marker": d.reference_marker.tolist(), "consumed_tasks": received["task_id"],
    "duplicate_consumed": True, "duplicate_model": vector(d),
    "native_reference_scoring": "未实现", "native_budget_accounting": "未实现"}

# Test native checkpoint only. Do NOT save/restore an extra queue or repair the round.
q = make_runner("fedbuff", 2)
assert dispatch(q) is False
stream = io.BytesIO()
torch.save(q.save_checkpoint(), stream)
stream.seek(0)
cpt = torch.load(stream, weights_only=False)
r = make_runner("fedbuff", 2)
r.load_checkpoint(cpt)
before = {"original_queue": q.gv.clock.q.size(), "restored_queue": r.gv.clock.q.size(),
          "original_round": q.current_round, "restored_round": r.current_round}
qu, ru = release(q, 3), release(r, 3)
assert qu is True and ru is False and vector(q) != vector(r)
RESULT["3_checkpoint"] = {"status": "失败", **before, "checkpoint_keys": sorted(cpt),
    "original_updated": qu, "restored_updated": ru,
    "original_model": vector(q), "restored_model": vector(r),
    "restored_concurrent": [int(cid) for cid in sorted(r.concurrent_clients)]}
assert CALLS["forward"] == CALLS["optimizer"] == CALLS["loss"] == 0
RESULT["execution"] = {"python": sys.executable, "calls": CALLS,
    "stopped_without_framework_repair": True, "script_lines": len(Path(__file__).read_text(encoding="utf-8").splitlines())}
(RUN / "results.json").write_text(json.dumps(RESULT, ensure_ascii=False, indent=2), encoding="utf-8")
sys.stdout.reconfigure(encoding="utf-8")
print(json.dumps({"results_path": str(RUN / "results.json"), **RESULT}, ensure_ascii=False, indent=2))
