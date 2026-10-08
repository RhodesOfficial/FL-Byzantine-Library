"""D2' benign asynchronous seam; only commit_event owns decision-state writes.

Phase-zero support is intentionally CPU float64, buffer-free models, sequential
clients and ideal availability/connectivity/completeness. No attack controller.
Native communication/clock are reused; native model-only restore is not used.
"""
import copy
from dataclasses import asdict
import hashlib
import json

import numpy as np
import torch
from torch.utils.data import default_collate

from flgo.algorithm.asyncbase import AsyncServer
from flgo.algorithm.fedbase import BasicClient
from d2_prime.budget import BudgetConfig
from d2_prime.protocol import ProtocolConfig, Reply, TaskProtocol
from d2_prime.reference import ReferenceConfig
from d2_prime.recovery import capture_checkpoint, restore_checkpoint
from d2_prime.diagnostics import check_batch


def parameter_vector(model):
    return torch.cat([p.detach().cpu().reshape(-1) for p in model.parameters()])


def copy_parameters(model, vector):
    # Copy a committed state into the transport carrier; this is not aggregation.
    offset = 0
    with torch.no_grad():
        for p in model.parameters():
            count = p.numel()
            p.copy_(vector[offset:offset+count].reshape(p.shape))
            offset += count
    if offset != vector.numel():
        raise ValueError("parameter dimension mismatch")


def observable_state(protocol):
    # No pending replies, source future versions, datasets or diagnostic labels.
    return {"now": protocol.now, "version": protocol.version,
            "model": tuple(protocol.model.tolist()), "reference": asdict(protocol.reference),
            "arrived_task_ids": tuple(c["task_id"] for c in protocol.candidates()),
            "ledger": copy.deepcopy(protocol.ledger)}


class Server(AsyncServer):
    def initialize(self):
        if (self.num_parallels != 1 or any(self.option[k] != "IDL" for k in
                ("availability", "connectivity", "completeness", "responsiveness"))):
            raise ValueError("phase-zero adapter requires sequential ideal simulator")
        if list(self.model.buffers()) or any(p.dtype != torch.float64 or p.device.type != "cpu"
                                             for p in self.model.parameters()):
            raise ValueError("phase-zero carrier must be buffer-free CPU float64")
        pc = ProtocolConfig(identities=self.num_clients,
                            **self.option.get("d2_protocol", {}))
        rc = ReferenceConfig(**self.option.get("d2_reference", {}))
        bc = BudgetConfig(**self.option["d2_budget"])
        self.protocol = TaskProtocol(parameter_vector(self.model), pc, rc, budget_config=bc)
        self.dispatch_rng = np.random.RandomState(self.option["seed"] + 700)
        self.dispatch_tasks = {}
        self.counts = dict(issued=0, executed=0, arrivals=0, score_attempts=0,
                           scored=0, accepted=0, evaluations=0, evaluation_examples=0)
        self.journal, self.logs = [], []
        self.errors = dict(model=0., carrier=0., reference=0., coefficients=0.)
        self.logging_enabled = self.option.get("d2_logging", True)
        self._in_transition = False
        self.current_round = self.protocol.version

    def pack(self, client_id, mtype=0):
        task = self.dispatch_tasks[client_id]
        model = copy.deepcopy(self.model)
        source = self.protocol.snapshot(task.source_version)
        copy_parameters(model, torch.tensor(source.model, dtype=torch.float64))
        return {"model": model, "task": task}

    def _commit_available(self):
        # One attempt for waiters; retry at later events. Drain full FIFO chunks
        # only while commits/rejections actually free slots. No spin on waiting.
        for _ in range(self.protocol.config.max_outstanding + 1):
            if not self.protocol.buffer_ids:
                return
            before = (self.protocol.version, self.protocol.buffer_ids)
            old_model = parameter_vector(self.model).numpy().copy()
            sources = {c["source_version"]: self.protocol.snapshot(c["source_version"])
                       for c in self.protocol.candidates()}
            result = self.protocol.commit_event()
            self.counts["score_attempts"] += 1
            self.counts["scored"] += len(result.event.proposals)
            self.counts["accepted"] += len(result.receipts)
            self.current_round = self.protocol.version
            copy_parameters(self.model, self.protocol.model)
            if result.receipts:
                r = self.protocol.reference
                d = self.protocol.reference_config.dimension
                normalized = [v/d**.5 for v in r.mu+r.sigma]+[r.evidence]
                errors = check_batch(self.protocol.batches[-1], old_model,
                                     self.protocol.model.numpy(), parameter_vector(self.model).numpy(),
                                     normalized, sources, self.protocol)
                for key, value in errors.items():
                    self.errors[key] = max(self.errors[key], value)
            self.journal.append({"at": self.protocol.now, "version": self.protocol.version,
                                 "receipts": [asdict(r) for r in result.receipts],
                                 "waiting": result.waiting, "rejected": result.rejected})
            if self.logging_enabled:
                self.logs.append(json.dumps(self.journal[-1], sort_keys=True))
            if before == (self.protocol.version, self.protocol.buffer_ids):
                return
        raise RuntimeError("unbounded commit drain")

    def _handle(self, packages):
        rows = zip(packages.get("reply", []), packages.get("__cid", []), packages.get("__t", []))
        for reply, cid, arrival in sorted(rows, key=lambda row: (row[2], row[0].task_id)):
            self.protocol.schedule_reply(reply, int(cid), float(arrival))
            self.counts["arrivals"] += 1
        self.protocol.advance(float(self.gv.clock.current_time))
        self._commit_available()

    def harvest(self):
        if self._in_transition:
            raise RuntimeError("nested transport transition")
        self._in_transition = True
        try:
            self._handle(self.communicate([], asynchronous=True))
        finally:
            self._in_transition = False

    def dispatch(self, identities, delays):
        if self.protocol.now != self.gv.clock.current_time or self._in_transition:
            raise RuntimeError("dispatch requires a harvested event boundary")
        self._in_transition = True
        try:
            self.dispatch_tasks = {i: self.protocol.issue(i) for i in identities}
            self.counts["issued"] += len(identities)
            self.gv.simulator.set_variable(self.gv.simulator.idx2id(identities), "latency", delays)
            packages = self.communicate(identities, asynchronous=True)
            self.counts["executed"] = sum(c.work["tasks"] for c in self.clients)
            self._handle(packages)
        finally:
            self.dispatch_tasks = {}
            self._in_transition = False

    def iterate(self):
        self.harvest()
        remaining = self.option.get("d2_task_limit", 200) - self.counts["issued"]
        free = [i for i in range(self.num_clients) if i not in self.protocol._live]
        count = min(remaining, self.protocol.config.max_outstanding-self.protocol.outstanding,
                    len(free), self.option.get("d2_dispatch_width", 10))
        if count > 0:
            chosen = sorted(self.dispatch_rng.choice(free, count, replace=False).tolist())
            delays = self.dispatch_rng.randint(1, 4, count).tolist()
            self.dispatch(chosen, delays)
        return self.protocol.version

    def tick(self):
        self.gv.clock.step(1)
        return self.iterate()

    def save_d2_checkpoint(self, input_id):
        if self._in_transition or self.dispatch_tasks:
            raise RuntimeError("save requires a complete transport/event boundary")
        sim = self.gv.simulator
        # Include ALL simulator instance state except shared object references.
        sim_state = {k: v for k, v in vars(sim).items()
                     if k not in {"server", "clients", "gv", "random_module"}}
        runtime = dict(input_id=input_id, model=self.model.state_dict(),
                       option=copy.deepcopy(self.option), current_round=self.current_round,
                       clock=self.gv.clock.time, queue=list(self.gv.clock.q.queue),
                       simulator=sim_state, simulator_rng=sim.random_module.get_state(),
                       dispatch_rng=self.dispatch_rng.get_state(), counts=self.counts,
                       journal=self.journal, errors=self.errors, client_work=[c.work for c in self.clients],
                       client_sim=[{k: v for k, v in vars(c).items() if
                                    k in {"_latency", "_working_amount"}} for c in self.clients])
        return capture_checkpoint(self.protocol, runtime)

    def load_d2_checkpoint(self, payload, input_id):
        if self._in_transition:
            raise RuntimeError("restore requires a safe transport boundary")
        # Validate runtime before publishing any restored state.
        runtime = payload["runtime"]
        if (runtime["input_id"] != input_id or runtime["option"] != self.option
                or len(runtime["client_work"]) != self.num_clients):
            raise ValueError("runtime/data/options mismatch")
        protocol, runtime = restore_checkpoint(payload, self.protocol.config_id)
        if runtime["clock"] != protocol.now or runtime["current_round"] != protocol.version:
            raise ValueError("clock/version mismatch")
        self.model.load_state_dict(runtime["model"])
        if not torch.equal(parameter_vector(self.model), protocol.model):
            raise ValueError("model mirror mismatch")
        self.protocol = protocol
        self.current_round = runtime["current_round"]
        self.gv.clock.time = runtime["clock"]
        self.gv.clock.q.queue = runtime["queue"]
        for k, v in runtime["simulator"].items():
            setattr(self.gv.simulator, k, v)
        self.gv.simulator.random_module.set_state(runtime["simulator_rng"])
        self.dispatch_rng.set_state(runtime["dispatch_rng"])
        self.counts, self.journal = runtime["counts"], runtime["journal"]
        self.errors = runtime["errors"]
        for c, work, sim in zip(self.clients, runtime["client_work"], runtime["client_sim"]):
            c.work = work
            for k, v in sim.items():
                setattr(c, k, v)
        self.logs = []  # Nondecision diagnostics do not seed any next event.


class Client(BasicClient):
    def initialize(self):
        self.work = dict(tasks=0, forwards=0, backwards=0, optimizer_steps=0, examples=0)

    def reply(self, package):
        task, model = package["task"], package["model"]
        self.active_task = task
        try:
            self.train(model)
        finally:
            del self.active_task
        self.work["tasks"] += 1
        return {"reply": Reply(task.task_id, task.identity, task.source_version,
                               tuple(parameter_vector(model).tolist()))}

    def train(self, model):
        # One stateless, deterministic minibatch per task: no hidden dataloader
        # iterator or optimizer momentum to recreate on checkpoint restore.
        if self.num_steps != 1 or self.momentum != 0 or self.weight_decay != 0:
            raise ValueError("phase-zero training requires one plain SGD step")
        size = min(int(self.batch_size), len(self.train_data))
        start = (self.active_task.task_id * size) % len(self.train_data)
        batch = default_collate([self.train_data[(start+j) % len(self.train_data)] for j in range(size)])
        batch = (batch[0].to(dtype=torch.float64), batch[1])
        model.train()
        optimizer = self.calculator.get_optimizer(model, lr=self.learning_rate,
                                                  momentum=0., weight_decay=0.)
        model.zero_grad()
        loss = self.calculator.compute_loss(model, batch)["loss"]
        if not torch.isfinite(loss):
            raise ValueError("nonfinite local loss")
        loss.backward()
        optimizer.step()
        for key in ("forwards", "backwards", "optimizer_steps"):
            self.work[key] += 1
        self.work["examples"] += size
