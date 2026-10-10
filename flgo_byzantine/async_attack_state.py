"""Causal proxy state for the phase-3 joint attack; reuses the frozen baseline.

The real no-defense average run uses the inherited BaselineState.commit_next with
its full two-layer writeback verification. Only the attacker's F_t^{32} candidate
search uses the read-only proxy methods below: an isolated clone that shares tensor
references (never mutated in place) but copies the mutable bookkeeping containers,
so a 32-tick rollout cannot leak fees, RNG or references into the real run.
"""
from collections import deque

import torch

from .async_baseline_state import BaselineState


class AttackBaselineState(BaselineState):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._proxy = False

    def clone_for_proxy(self):
        """Isolated average-only clone; shares immutable tensors, copies containers.

        Only tasks that are still live or sitting in the arrival FIFO can be touched
        by expire/commit, so the full (unbounded) task history is not copied.
        """
        if self.method != "avg" or self.rfa is not None:
            raise ValueError("proxy rollout is defined only for the no-defense average")
        clone = object.__new__(AttackBaselineState)
        clone.method = self.method
        clone.config_id = self.config_id
        clone.identities, clone.capacity, clone.limit = self.identities, self.capacity, self.limit
        clone.lifetime, clone.max_staleness, clone.wait = self.lifetime, self.max_staleness, self.wait
        clone.now, clone.version, clone.terminated = self.now, self.version, self.terminated
        clone.model = self.model  # Shared; proxy commits assign new tensors, never mutate in place.
        clone.sources = dict(self.sources)
        clone.refs = dict(self.refs)
        active = set(self.live.values()) | set(self.fifo)
        clone.tasks = {tid: dict(self.tasks[tid]) for tid in active}
        clone.live = dict(self.live)
        clone.fifo = deque(self.fifo)
        clone.updates = dict(self.updates)  # Share update tensors by reference.
        clone.journal, clone.batches = [], []
        clone.rfa = None
        clone.maximum_outstanding, clone.maximum_arrived = self.maximum_outstanding, self.maximum_arrived
        clone._proxy = True
        return clone

    def proxy_deliver(self, tid, delta, at):
        """Deliver an attacker-controlled (or colluding) raw update u into the clone."""
        if not self._proxy:
            raise RuntimeError("proxy_deliver is read-only clone state only")
        row = self.tasks.get(tid)
        if row is None or row["state"] != "issued":
            return False
        if at >= row["expires_at"] or self.version-row["source_version"] > self.max_staleness:
            return False
        row.update(state="arrived", arrived_at=at, arrival_version=self.version,
                   staleness_arrival=self.version-row["source_version"], first_packet_at=at,
                   raw_norm=float(delta.detach().double().norm().item()))
        self.updates[tid] = delta
        self.fifo.append(tid)
        return True

    def _proxy_finish(self, tid, state, reason=None):
        row = self.tasks[tid]
        row.update(state=state, terminal_at=self.now, terminal_version=self.version, terminal_reason=reason)
        del self.live[row["identity"]]
        self.updates.pop(tid, None)
        self.fifo = deque(i for i in self.fifo if i != tid)
        self.terminated += 1

    def _proxy_expire(self, now):
        self.now = now
        for tid in list(self.live.values()):
            row = self.tasks[tid]
            if now >= row["expires_at"] or self.version-row["source_version"] > self.max_staleness:
                if row["arrived_at"] is None:
                    row["staleness_expiry"] = self.version-row["source_version"]
                reason = "deadline" if now >= row["expires_at"] else "staleness"
                self._proxy_finish(tid, "expired", reason)

    def _proxy_commit(self, tail=False):
        """Average-only commit mirroring BaselineState.commit_next without auditing."""
        self._proxy_expire(self.now)
        if not self.fifo:
            return False
        full = len(self.fifo) >= self.capacity
        if not full and not tail and self.now-self.tasks[self.fifo[0]]["arrived_at"] < self.wait:
            return False
        tids = list(self.fifo)[:self.capacity]
        rows = [self.tasks[tid] for tid in tids]
        lags = [self.version-r["source_version"] for r in rows]
        inputs = [self.updates[tid] for tid in tids]
        coefficients = [1/(1+lag)/self.capacity for lag in lags]
        displacement = torch.zeros_like(self.model)
        for a, u in zip(coefficients, inputs):
            displacement = displacement - a*u
        self.model = self.model + displacement
        self.version += 1
        for tid in tids:
            self._proxy_finish(tid, "consumed")
        return True

    def proxy_rollout(self, deliveries, horizon, tail):
        """Run a 32-tick causal proxy: no new issue, no invisible honest arrival.

        ``deliveries`` is a list of (release_tick, task_id, raw_update) covering the
        candidate under evaluation plus the already-registered colluding releases.
        The tail flag is frozen to the real pre-state so the proxy never enables the
        tail rule early merely because future honest arrivals are invisible.
        """
        if not self._proxy:
            raise RuntimeError("proxy_rollout is read-only clone state only")
        by_tick = {}
        for at, tid, delta in deliveries:
            by_tick.setdefault(at, []).append((tid, delta))
        start = self.now
        for tick in range(start, start+horizon+1):
            self._proxy_expire(tick)
            for tid, delta in sorted(by_tick.get(tick, []), key=lambda x: x[0]):
                self.proxy_deliver(tid, delta, tick)
            while self._proxy_commit(tail=tail):
                pass
        return self.model
