"""Formal benign buffered async baselines; native FLGo transport/local training.

Discrete clock and task progress own run termination/evaluation, not BasicServer
rounds. Mid-run resume is explicitly unsupported. Phase-zero seam is untouched.
"""
import copy

import numpy as np
import torch
from flgo.algorithm.asyncbase import AsyncServer
from flgo.algorithm.fedbase import BasicClient
from flgo.simulator.base import with_clock

from .async_baseline_state import BaselineState, DeliveredReply


def parameter_vector(model):
    return torch.cat([p.detach().reshape(-1) for p in model.parameters()])


def copy_parameters(model, vector):
    offset = 0
    with torch.no_grad():
        for p in model.parameters():
            size = p.numel()
            p.copy_(vector[offset:offset+size].reshape(p.shape))
            offset += size
    if offset != vector.numel():
        raise ValueError("parameter dimension mismatch")


class Server(AsyncServer):
    def initialize(self):
        if self.num_parallels != 1 or any(self.option[k] != "IDL" for k in
                ("availability", "connectivity", "completeness", "responsiveness")):
            raise ValueError("formal adapter requires sequential ideal transport")
        if list(self.model.buffers()) or any(p.dtype != torch.float32 or p.device.type != "cuda"
                                             for p in self.model.parameters()):
            raise ValueError("formal carrier requires buffer-free GPU/float32")
        self.baseline = BaselineState(parameter_vector(self.model), self.option["async_method"],
                                     self.option["async_config_id"], identities=self.num_clients)
        self.dispatch_rng = np.random.RandomState(801)
        self.slow_ids = frozenset(np.random.RandomState(1801).choice(100, 50, replace=False).tolist())
        self.delay_rngs = [np.random.RandomState(2801+c) for c in range(self.num_clients)]
        self.dispatch_tasks, self.delay_sequence, self.executed_order = {}, [], []
        self.current_round = 0
        self.on_batch = lambda record: None
        self.on_evaluate = lambda progress: None
        self.task_limit = self.option.get("async_task_limit", 12000)
        self.eval_points = self.option.get("async_eval_points", [10400,10800,11200,11600,12000])
        self.evaluated = []

    def pack(self, client_id, mtype=0):
        ticket = self.dispatch_tasks[client_id]
        model = copy.deepcopy(self.model)
        copy_parameters(model, self.baseline.sources[ticket.source_version])
        return {"model": model, "task": ticket}

    @with_clock
    def communicate(self, selected_clients, mtype=0, asynchronous=False):
        # Native BasicServer uses list(set(selected_clients)); explicitly preserve
        # the ruling's sorted-ID compute/issue order, while retaining with_clock.
        if selected_clients != sorted(set(selected_clients)):
            raise ValueError("communication IDs must be unique and sorted")
        packages = []
        for cid in selected_clients:
            package = self.pack(cid, mtype)
            package["__mtype__"] = mtype
            packages.append(self.communicate_with(self.clients[cid].id, package))
            self.executed_order.append(self.dispatch_tasks[cid].task_id)
        return self.unpack(packages)

    def _evaluate_boundary(self):
        progress = self.baseline.terminated
        remaining = [p for p in self.eval_points if p not in self.evaluated]
        if remaining and progress > remaining[0]:
            raise RuntimeError("a batch skipped an exact registered task evaluation point")
        if remaining and progress == remaining[0]:
            self.on_evaluate(progress)
            self.evaluated.append(progress)

    def _receive(self, packages):
        rows = zip(packages.get("reply", []), packages.get("__cid", []), packages.get("__t", []))
        for reply, cid, at in sorted(rows, key=lambda r: r[0].task_id):
            self.baseline.receive(reply, int(cid), int(at))

    def _drain(self):
        state = self.baseline
        while True:
            tail = (len(state.tasks) == self.task_limit
                    and not any(r["state"] == "issued" for r in state.tasks.values()))
            record = state.commit_next(tail=tail)
            if record is None:
                return
            copy_parameters(self.model, state.model)
            if not torch.equal(parameter_vector(self.model), state.model):
                raise ValueError("actual model carrier differs from validated writeback")
            self.current_round = state.version
            self.on_batch(record)
            self._evaluate_boundary()

    def iterate(self):
        state = self.baseline
        state.expire(int(self.gv.clock.current_time))  # Deadlines before same-tick packets.
        self._receive(self.communicate([], asynchronous=True))
        self._drain()
        self._evaluate_boundary()
        count = min(self.task_limit-len(state.tasks), state.limit-len(state.live))
        if count > 0:
            free = [cid for cid in range(self.num_clients) if cid not in state.live]
            chosen = sorted(self.dispatch_rng.choice(free, count, replace=False).tolist())
            self.dispatch_tasks = {cid: state.issue(cid) for cid in chosen}
            delays = [int(self.delay_rngs[cid].choice([6,7,8] if cid in self.slow_ids else [1,2,3]))
                      for cid in chosen]
            self.delay_sequence.extend({"task_id": self.dispatch_tasks[cid].task_id,
                "identity": cid, "delay": delay} for cid, delay in zip(chosen, delays))
            self.gv.simulator.set_variable(self.gv.simulator.idx2id(chosen), "latency", delays)
            self._receive(self.communicate(chosen, asynchronous=True))
            self._drain()  # Supports zero-delay short checks without dispatching again.
            self.dispatch_tasks = {}
        state.audit()
        return state.version

    def run(self):
        self.on_evaluate(0)
        while True:
            self.iterate()  # t=0 fills 40 slots before the first clock increment.
            if (len(self.baseline.tasks) == self.task_limit
                    and self.baseline.terminated == self.task_limit and self.gv.clock.empty()):
                break
            self.gv.clock.step(1)
            if self.gv.clock.current_time > self.task_limit*32+32:
                raise RuntimeError("transport did not drain")
        if self.evaluated != list(self.eval_points):
            raise RuntimeError("missing registered task evaluations")

    def save_checkpoint(self):
        raise RuntimeError("formal GPU mid-run recovery is not supported")

    def load_checkpoint(self, checkpoint):
        raise RuntimeError("formal GPU mid-run recovery is not supported")


class Client(BasicClient):
    def initialize(self):
        self.work = dict(tasks=0, minibatches=0, examples=0)
        compute_loss = self.calculator.compute_loss
        def counted_loss(model, batch):
            self.work["minibatches"] += 1
            self.work["examples"] += len(batch[-1])
            return compute_loss(model, batch)
        self.calculator.compute_loss = counted_loss

    def reply(self, package):
        ticket, model = package["task"], package["model"]
        self.train(model)  # Inherited full native local epoch, SGD and dataloader.
        self.work["tasks"] += 1
        return {"reply": DeliveredReply(ticket.task_id, ticket.identity, ticket.source_version,
                                       parameter_vector(model).detach().cpu())}
