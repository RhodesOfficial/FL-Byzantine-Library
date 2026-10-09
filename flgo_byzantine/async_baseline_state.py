"""GPU-capable baseline task state. No reference, clipping, budget or recovery.

Only delivered replies enter decision state. Sources outlive both live tasks and
unreceived transport packets, so late finite uploads can still be diagnosed.
"""
from collections import deque
from dataclasses import asdict, dataclass
import math

import torch

from aggregators.rfa import RFA
from aggregators.async_rfa_contributions import bind_async_mix
from aggregators.contribution_diagnostics import trace, two_layer_errors, require_two_layers


@dataclass(frozen=True)
class Ticket:
    task_id: int
    identity: int
    source_version: int
    issued_at: int
    expires_at: int
    config_id: str


@dataclass(frozen=True)
class DeliveredReply:
    task_id: int
    identity: int
    source_version: int
    local_model: torch.Tensor


class BaselineState:
    def __init__(self, model, method, config_id, identities=100, capacity=20,
                 outstanding_limit=40, lifetime=32, max_staleness=64, wait=8):
        if method not in ("avg", "rfa") or model.dtype != torch.float32:
            raise ValueError("baseline requires average/RFA and float32")
        if model.ndim != 1 or not model.numel() or not torch.isfinite(model).all():
            raise ValueError("invalid model")
        self.model = model.detach().clone()
        self.method, self.config_id = method, config_id
        self.identities, self.capacity, self.limit = identities, capacity, outstanding_limit
        self.lifetime, self.max_staleness, self.wait = lifetime, max_staleness, wait
        self.now = self.version = self.terminated = 0
        self.tasks, self.live = {}, {}
        self.sources, self.refs = {0: self.model.clone()}, {0: 0}
        self.fifo, self.updates = deque(), {}
        self.journal, self.batches = [], []
        self.rfa = RFA(T=5, nu=1e-6) if method == "rfa" else None
        self.maximum_outstanding = self.maximum_arrived = 0

    def issue(self, identity):
        if type(identity) is not int or not 0 <= identity < self.identities:
            raise ValueError("unknown identity")
        if identity in self.live or len(self.live) >= self.limit:
            raise RuntimeError("outstanding task limit")
        ticket = Ticket(len(self.tasks), identity, self.version, self.now,
                        self.now + self.lifetime, self.config_id)
        self.tasks[ticket.task_id] = dict(asdict(ticket), state="issued", first_packet_at=None,
            arrived_at=None, arrival_version=None, staleness_arrival=None,
            terminal_at=None, terminal_version=None, raw_norm=None, actual_coefficient=0.)
        self.live[identity] = ticket.task_id
        self.refs[self.version] += 1
        self.maximum_outstanding = max(self.maximum_outstanding, len(self.live))
        self.journal.append(dict(event="issue", **asdict(ticket)))
        return ticket

    def _collect(self):
        for version in list(self.sources):
            if version != self.version and self.refs[version] == 0:
                del self.sources[version], self.refs[version]

    def _finish(self, tid, state, reason=None):
        row = self.tasks[tid]
        if row["state"] not in ("issued", "arrived"):
            raise ValueError("duplicate terminal transition")
        row.update(state=state, terminal_at=self.now, terminal_version=self.version,
                   terminal_reason=reason)
        del self.live[row["identity"]]
        self.updates.pop(tid, None)
        self.fifo = deque(i for i in self.fifo if i != tid)
        if row["first_packet_at"] is not None:
            self.refs[row["source_version"]] -= 1
        self.terminated += 1
        self.journal.append(dict(event="terminal", task_id=tid, identity=row["identity"],
                                 at=self.now, version=self.version, state=state, reason=reason))
        self._collect()

    def expire(self, now):
        if type(now) is not int or now < self.now:
            raise ValueError("clock must advance in integer ticks")
        self.now = now
        for tid in list(self.live.values()):
            row = self.tasks[tid]
            if now >= row["expires_at"] or self.version-row["source_version"] > self.max_staleness:
                if row["arrived_at"] is None:
                    row["staleness_expiry"] = self.version-row["source_version"]
                reason = "deadline" if now >= row["expires_at"] else "staleness"
                self._finish(tid, "expired", reason)

    def receive(self, reply, transport_identity, at):
        if at != self.now:
            raise ValueError("deliver at the current tick")
        row = self.tasks.get(reply.task_id)
        reason = None
        if row is None:
            reason = "unknown"
        elif (transport_identity != row["identity"] or reply.identity != row["identity"]
              or reply.source_version != row["source_version"]):
            reason = "identity_or_source"
        elif row["first_packet_at"] is not None:
            reason = "duplicate"
        if reason is not None:
            self.journal.append(dict(event="reject_packet", task_id=reply.task_id, at=at, reason=reason))
            return False
        local = reply.local_model
        if (not isinstance(local, torch.Tensor) or local.dtype != torch.float32
                or local.shape != self.model.shape or not torch.isfinite(local).all()):
            self.journal.append(dict(event="reject_packet", task_id=reply.task_id, at=at, reason="vector"))
            return False
        delta = self.sources[row["source_version"]] - local.to(self.model.device)
        norm = delta.detach().double().norm().item()
        if not math.isfinite(norm):
            raise ValueError("nonfinite source update")
        row.update(first_packet_at=at, raw_norm=norm)
        if row["state"] not in ("issued", "arrived"):
            self.refs[row["source_version"]] -= 1
            self._collect()
            self.journal.append(dict(event="reject_packet", task_id=reply.task_id, at=at,
                                     reason="terminal", raw_norm=norm))
            return False
        # The driver expires all tasks before delivering this tick's packets.
        if at >= row["expires_at"] or self.version-row["source_version"] > self.max_staleness:
            raise RuntimeError("driver did not expire before arrival")
        row.update(state="arrived", arrived_at=at, arrival_version=self.version,
                   staleness_arrival=self.version-row["source_version"])
        self.updates[reply.task_id] = delta
        self.fifo.append(reply.task_id)
        self.maximum_arrived = max(self.maximum_arrived, len(self.fifo))
        self.journal.append(dict(event="arrival", task_id=reply.task_id, identity=row["identity"],
            at=at, version=self.version, staleness_arrival=row["staleness_arrival"], raw_norm=norm))
        return True

    def commit_next(self, tail=False):
        self.expire(self.now)  # Revalidate after each previous same-tick commit.
        if not self.fifo:
            return None
        full = len(self.fifo) >= self.capacity
        if not full and not tail and self.now-self.tasks[self.fifo[0]]["arrived_at"] < self.wait:
            return None
        tids = list(self.fifo)[:self.capacity]
        rows = [self.tasks[tid] for tid in tids]
        ids = [r["identity"] for r in rows]
        if len(set(ids)) != len(ids) or any(r["state"] != "arrived" for r in rows):
            raise ValueError("invalid or duplicate batch")
        inputs = [self.updates[tid] for tid in tids]
        lags = [self.version-r["source_version"] for r in rows]
        batch_id = len(self.batches)
        before = self.model
        if self.rfa is None:
            coefficients = tuple(1/(1+lag)/self.capacity for lag in lags)
            record = {"batch_id": batch_id, "adaptation_semantics": "async_average_fixed_K_v1"}
        else:
            expected_call = self.rfa._call_sequence+1
            z = self.rfa(inputs)  # Never preweight inputs by staleness.
            coefficients, record = bind_async_mix(self.rfa, inputs, ids, z, expected_call,
                batch_id, tids, [r["source_version"] for r in rows], lags, self.capacity)
        zero = torch.zeros_like(before)
        decomposition = trace(inputs, [zero]*len(tids), [-a for a in coefficients],
                              [0.]*len(tids), zero, zero)
        displacement = torch.zeros_like(before)
        for a, u in zip(coefficients, inputs):
            displacement -= a*u
        after = before + displacement
        checks = two_layer_errors(decomposition, before, displacement, after)
        try:
            require_two_layers(checks)
        except Exception:
            self.failed_batch = dict(before=before.cpu(), inputs=[u.cpu() for u in inputs],
                coefficients=coefficients, displacement=displacement.cpu(), after=after.cpu(), checks=checks)
            raise
        record.update(at=self.now, version_before=self.version, version_after=self.version+1,
            task_ids=tids, client_ids=ids, source_versions=[r["source_version"] for r in rows],
            staleness_commit=lags, actual_coefficients=list(coefficients), checks=checks,
            batch_size=len(tids), reason="full" if full else "tail" if tail else "timeout")
        # Validate all numerics before publication. This is a baseline model-only path.
        self.model = after
        self.version += 1
        self.sources[self.version], self.refs[self.version] = self.model.clone(), 0
        for tid, a, lag in zip(tids, coefficients, lags):
            row = self.tasks[tid]
            row.update(actual_coefficient=a, staleness_commit=lag, batch_id=batch_id,
                       nominal_model=1/(1+lag)/20, nominal_reference=.1/(1+lag)/20,
                       nominal_fee=.055/(1+lag))
            self._finish(tid, "consumed")
        self.batches.append(record)
        self._collect()
        return record

    def audit(self):
        assert len(self.live) <= self.limit
        assert len(set(self.fifo)) == len(self.fifo) and len(self.fifo) <= self.limit
        assert all(self.tasks[tid]["state"] == "arrived" for tid in self.fifo)
        assert set(self.live) == {r["identity"] for r in self.tasks.values() if r["state"] in ("issued","arrived")}
        assert self.terminated == sum(r["state"] not in ("issued","arrived") for r in self.tasks.values())
        assert self.version == len(self.batches)
        assert torch.isfinite(self.model).all()
        return True
