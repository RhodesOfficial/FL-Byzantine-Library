"""Formal clean D2' GPU entry; native transport and native full local epoch.

The baseline and phase-zero entries are intentionally independent. This driver
consumes authoritative joint state, including stale expiry after a commit.
"""
import copy
from dataclasses import asdict
import numpy as np
import torch
from flgo.algorithm.asyncbase import AsyncServer
from flgo.simulator.base import with_clock

from d2_prime.protocol import ProtocolConfig, Reply
from d2_prime.reference import ReferenceConfig
from d2_prime.budget import BudgetConfig
from d2_prime.float32_protocol import Float32TaskProtocol
from .async_baseline_algorithm import Client, parameter_vector, copy_parameters


class Server(AsyncServer):
    def initialize(self):
        if self.num_parallels != 1 or any(self.option[k] != 'IDL' for k in
                ('availability','connectivity','completeness','responsiveness')):
            raise ValueError('formal entry requires sequential ideal transport')
        if list(self.model.buffers()):
            raise ValueError('buffer-free carrier required')
        self.protocol = Float32TaskProtocol(parameter_vector(self.model),
            ProtocolConfig(identities=self.num_clients, max_outstanding=40, capacity=20,
                lifetime=32., max_staleness=64, clip_norm=0.9701598816245317),
            ReferenceConfig(z_cut=self.option.get('d2_z_cut',3.)),
            budget_config=BudgetConfig(33., .4125))
        self.dispatch_rng = np.random.RandomState(801)
        self.slow_ids = frozenset(np.random.RandomState(1801).choice(100,50,replace=False).tolist())
        self.delay_rngs = [np.random.RandomState(2801+c) for c in range(self.num_clients)]
        self.dispatch_tasks, self.delay_sequence, self.executed_order = {}, [], []
        self.current_round, self.attempts = 0, 0
        self.terminal_order, self.journal, self.seen_terminal = [], [], set()
        self.task_limit = self.option.get('async_task_limit',12000)
        self.eval_points = self.option.get('async_eval_points',[10400,10800,11200,11600,12000])
        self.evaluated = []
        self.on_event = lambda row: None
        self.on_evaluate = lambda target, actual: None

    @property
    def terminated(self):
        return len(self.terminal_order)

    def pack(self, client_id, mtype=0):
        task = self.dispatch_tasks[client_id]
        model = copy.deepcopy(self.model)
        copy_parameters(model, self.protocol.snapshot(task.source_version).model)
        return {'model':model,'task':task}

    @with_clock
    def communicate(self, selected_clients, mtype=0, asynchronous=False):
        if selected_clients != sorted(set(selected_clients)):
            raise ValueError('sorted unique communication IDs required')
        packages = []
        for cid in selected_clients:
            package = self.pack(cid,mtype)
            package['__mtype__'] = mtype
            packages.append(self.communicate_with(self.clients[cid].id,package))
            self.executed_order.append(self.dispatch_tasks[cid].task_id)
        return self.unpack(packages)

    def _boundary(self, kind, details=None):
        p = self.protocol
        new = sorted(t.task_id for t in p.tasks.values()
                     if t.state not in ('issued','arrived') and t.task_id not in self.seen_terminal)
        before = self.terminated
        self.terminal_order.extend(new)
        self.seen_terminal.update(new)
        row = dict(kind=kind, at=p.now, version=p.version, terminated_before=before,
            terminated_after=self.terminated, terminal_task_ids=new,
            reference_evidence=p.reference.evidence, ready=p.reference.ready(p.reference_config))
        if details is not None:row.update(details)
        self.journal.append(row)
        self.on_event(row)
        # Called at EACH expiry/commit boundary, never only after the tick.
        for target in self.eval_points:
            if target not in self.evaluated and self.terminated >= target:
                if self.terminated-target > 39:
                    raise ValueError('evaluation event overshoot exceeded 40-slot bound')
                self.on_evaluate(target,self.terminated)
                self.evaluated.append(target)

    def _expire(self, tick):
        self.protocol.advance(tick)
        self._boundary('expiry')

    def _receive(self, packages):
        p = self.protocol
        for packet,cid,at in sorted(zip(packages.get('reply',[]),packages.get('__cid',[]),
                                       packages.get('__t',[])),key=lambda r:r[0].task_id):
            if at != p.now:
                raise ValueError('native clock delivered outside current tick')
            reply = Reply(packet.task_id,packet.identity,packet.source_version,packet.local_model)
            p.schedule_reply(reply,int(cid),at)
        p.advance(p.now)

    def _drain(self):
        p = self.protocol
        while p.buffer_ids:
            tail = (len(p.tasks)==self.task_limit and not any(t.state=='issued' for t in p.tasks.values()))
            oldest = min(p.observations[i]['first_arrival_at'] for i in p.buffer_ids)
            if len(p.buffer_ids)<20 and p.now-oldest<8 and not tail:
                return
            before = {t.task_id for t in p.tasks.values() if t.state not in ('issued','arrived')}
            self.attempts += 1
            result = p.commit_event()
            p.audit_budget()  # Includes pure waiting / all-rejected attempts.
            copy_parameters(self.model,p.model)
            self.current_round = p.version
            self.audit_tick()
            self._boundary('commit',dict(attempt=self.attempts, event=asdict(result.event),
                receipts=[asdict(r) for r in result.receipts], waiting=result.waiting,
                rejected=result.rejected, scales=result.scales,
                checks=p.last_checks, reference_displacement=result.reference_displacement))
            after = {t.task_id for t in p.tasks.values() if t.state not in ('issued','arrived')}
            if after==before:
                return  # A nonempty CommitResult does not imply progress/version.

    def audit_tick(self):
        p = self.protocol
        live = {t.identity:t.task_id for t in p.tasks.values() if t.state in ('issued','arrived')}
        if live != p._live or len(live)>40 or len(live)!=sum(t.state in ('issued','arrived') for t in p.tasks.values()):
            raise ValueError('authoritative tasks / identity slots disagree')
        queued = list(p.buffer_ids)+list(p._inbox)
        if len(set(queued))!=len(queued) or set(queued)!={t.task_id for t in p.tasks.values() if t.state=='arrived'}:
            raise ValueError('candidate queues do not reconcile')
        for version in p._sources:
            if p._refs[version]!=sum(t.source_version==version and t.state in ('issued','arrived') for t in p.tasks.values()):
                raise ValueError('source reference count mismatch')
        if (self.current_round!=p.version or not torch.equal(parameter_vector(self.model),p.model)
            or not torch.equal(p.snapshot(p.version).model.to(p.model.device),p.model)):
            raise ValueError('model carrier, snapshot or version mismatch')

    def iterate(self):
        p = self.protocol
        self._expire(int(self.gv.clock.current_time))
        self._receive(self.communicate([],asynchronous=True))
        self._drain()
        count = min(self.task_limit-len(p.tasks),40-p.outstanding)
        if count>0:
            free = [cid for cid in range(self.num_clients) if cid not in p._live]
            chosen = sorted(self.dispatch_rng.choice(free,count,replace=False).tolist())
            self.dispatch_tasks = {cid:p.issue(cid) for cid in chosen}
            delays = [int(self.delay_rngs[cid].choice([6,7,8] if cid in self.slow_ids else [1,2,3])) for cid in chosen]
            self.delay_sequence.extend(dict(task_id=self.dispatch_tasks[cid].task_id,identity=cid,delay=d)
                                       for cid,d in zip(chosen,delays))
            self.gv.simulator.set_variable(self.gv.simulator.idx2id(chosen),'latency',delays)
            self._receive(self.communicate(chosen,asynchronous=True))
            self._drain()
            self.dispatch_tasks = {}
        self.audit_tick()
        return p.version

    def run(self):
        self.on_evaluate(0,0)
        while True:
            self.iterate()
            if len(self.protocol.tasks)==self.task_limit and self.terminated==self.task_limit and self.gv.clock.empty():
                break
            self.gv.clock.step(1)
            if self.gv.clock.current_time>self.task_limit*32+32:
                raise RuntimeError('task/transport deadlock')
        if self.evaluated!=self.eval_points:
            raise RuntimeError('missing evaluation boundaries')

    def save_checkpoint(self):
        raise RuntimeError('formal GPU recovery unsupported')

    def load_checkpoint(self, checkpoint):
        raise RuntimeError('formal GPU recovery unsupported')
