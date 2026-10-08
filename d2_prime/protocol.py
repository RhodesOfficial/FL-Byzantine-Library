"""Task/event backend with opt-in phase 0.3 reference preparation.

The legacy model-only seam uses external coefficients. Reference writes remain
pure calculations until gate 0.4 supplies shared-budget and joint commit logic.
Transport identities are trusted simulator inputs, not cryptographic identities.
"""
from collections import deque
from dataclasses import asdict, dataclass, replace
import hashlib
import heapq
import json
import math
from typing import Mapping

import torch

from .reference import (FeatureMap, ReferenceCandidate, ReferenceConfig,
                        ReferenceState, features, prepare_event)


@dataclass(frozen=True)
class ProtocolConfig:
    identities: int = 40
    max_outstanding: int = 40
    capacity: int = 20
    lifetime: float = 10.0
    max_staleness: int = 16
    clip_norm: float = 1.0
    eta_model: float = 1.0
    specification: str = "D2_PRIME_DESIGN:2.1/phase0.1+0.2-v1"

    def __post_init__(self):
        for value in (self.identities, self.max_outstanding, self.capacity):
            if type(value) is not int or value < 1:
                raise ValueError("counts must be positive integers")
        if type(self.max_staleness) is not int or self.max_staleness < 0:
            raise ValueError("max_staleness must be a nonnegative integer")
        for value in (self.lifetime, self.clip_norm, self.eta_model):
            if not math.isfinite(value) or value <= 0:
                raise ValueError("time, clipping and step must be finite and positive")

    @property
    def config_id(self):
        return hashlib.sha256(json.dumps(asdict(self), sort_keys=True).encode()).hexdigest()


@dataclass(frozen=True)
class SourceSnapshot:
    version: int
    model: tuple
    mu: tuple
    sigma: tuple
    evidence: float
    config_id: str


@dataclass(frozen=True)
class Task:
    task_id: int
    identity: int
    source_version: int
    issued_at: float
    expires_at: float
    config_id: str
    state: str = "issued"


@dataclass(frozen=True)
class Reply:
    task_id: int
    identity: int
    source_version: int
    local_model: tuple


class TaskProtocol:
    def __init__(self, initial_model, config=ProtocolConfig(), reference_config=None,
                 feature_map=None):
        self.config = config
        self._model = torch.as_tensor(initial_model, dtype=torch.float64, device="cpu").clone()
        if self._model.ndim != 1 or not self._model.numel() or not torch.isfinite(self._model).all():
            raise ValueError("model must be a finite nonempty vector")
        self._reference_config = reference_config
        if reference_config is not None and reference_config.n_boot > config.capacity:
            raise ValueError("require n_boot <= protocol capacity")
        if reference_config is None and feature_map is not None:
            raise ValueError("a feature map requires a reference configuration")
        self._feature_map = (feature_map or FeatureMap.generate(self._model.numel(), reference_config)
                             if reference_config is not None else None)
        if self._feature_map is not None and (len(self._feature_map.buckets) != self._model.numel()
            or self._feature_map.bucket_count != reference_config.projection_buckets):
            raise ValueError("feature map differs from run dimensions")
        self._reference = ReferenceState.initial(reference_config or ReferenceConfig())
        contract = {"protocol": asdict(config), "reference": asdict(reference_config),
                    "feature_map": asdict(self._feature_map)} if reference_config is not None else None
        self._config_id = (hashlib.sha256(json.dumps(contract, sort_keys=True).encode()).hexdigest()
                           if contract is not None else config.config_id)
        self.now, self.version, self._next_task, self._sequence = 0.0, 0, 0, 0
        self.tasks, self._live, self._sources, self._refs = {}, {}, {}, {}
        self._events, self._inbox, self._buffer, self._updates = [], deque(), [], {}
        self.ledger, self.batches, self.trace = [], [], []
        self._freeze()

    @property
    def model(self):
        return self._model.clone()

    @property
    def reference(self):
        return self._reference

    @property
    def reference_config(self):
        return self._reference_config

    @property
    def feature_map(self):
        return self._feature_map

    @property
    def config_id(self):
        return self._config_id

    @property
    def outstanding(self):
        return len(self._live)

    @property
    def buffer_ids(self):
        return tuple(self._buffer)

    def snapshot(self, version):
        return self._sources[version]  # Only frozen dataclasses/tuples, no mutable tensors.

    def _freeze(self):
        # Immutable tuples capture the reference at this commit version.
        self._sources[self.version] = SourceSnapshot(self.version, tuple(self._model.tolist()),
            self._reference.mu, self._reference.sigma, self._reference.evidence, self.config_id)
        self._refs.setdefault(self.version, 0)
        self._collect_sources()

    def _collect_sources(self):
        for version in list(self._sources):
            if version != self.version and self._refs[version] == 0:
                del self._sources[version]
                del self._refs[version]

    def _event(self, when, priority, task_id, payload):
        if not math.isfinite(when) or when < self.now:
            raise ValueError("event time must be finite and not in the past")
        heapq.heappush(self._events, (when, priority, task_id, self._sequence, payload))
        self._sequence += 1

    def issue(self, identity):
        if type(identity) is not int or not 0 <= identity < self.config.identities:
            raise ValueError("unknown identity")
        if identity in self._live or self.outstanding >= self.config.max_outstanding:
            raise RuntimeError("outstanding task limit")
        if not math.isfinite(self.now + self.config.lifetime):
            raise ValueError("task deadline overflow")
        task = Task(self._next_task, identity, self.version, self.now,
                    self.now + self.config.lifetime, self.config_id)
        self._next_task += 1
        self.tasks[task.task_id], self._live[identity] = task, task.task_id
        self._refs[task.source_version] += 1
        self._event(task.expires_at, 0, task.task_id, None)
        self.trace.append(("issue", self.now, task.task_id))
        return task

    def schedule_reply(self, reply, transport_identity, arrival_at):
        self._event(arrival_at, 1, reply.task_id, (reply, transport_identity))

    def _finish(self, task_id, state):
        task = self.tasks[task_id]
        self.tasks[task_id] = replace(task, state=state)
        self._live.pop(task.identity)
        self._refs[task.source_version] -= 1
        self._updates.pop(task_id, None)
        self._buffer = [i for i in self._buffer if i != task_id]
        self._inbox = deque(i for i in self._inbox if i != task_id)
        self.trace.append((state, self.now, task_id))
        self._collect_sources()

    def _fill(self):
        while self._inbox and len(self._buffer) < self.config.capacity:
            self._buffer.append(self._inbox.popleft())

    def cancel(self, task_id, lost=False):
        task = self.tasks.get(task_id)
        if task is None or task.state not in {"issued", "arrived"}:
            return False
        self._finish(task_id, "lost" if lost else "cancelled")
        self._fill()
        return True

    def advance(self, when):
        if not math.isfinite(when) or when < self.now:
            raise ValueError("clock cannot move backwards")
        while self._events and self._events[0][0] <= when:
            at, priority, task_id, _, payload = heapq.heappop(self._events)
            self.now = at
            task = self.tasks.get(task_id)
            if priority == 0:
                if task is not None and task.state in {"issued", "arrived"}:
                    self._finish(task_id, "expired")
                    self._fill()
            else:
                self.receive(*payload)
        self.now = when
        self._expire_stale()

    def _reject(self, reply, reason):
        self.trace.append(("invalid:" + reason, self.now, reply.task_id))
        return False

    def receive(self, reply, transport_identity):
        task = self.tasks.get(reply.task_id)
        if task is None:
            return self._reject(reply, "unknown")
        if reply.identity != task.identity or transport_identity != task.identity:
            return self._reject(reply, "identity")
        if reply.source_version != task.source_version or reply.source_version > self.version:
            return self._reject(reply, "source")
        if task.state != "issued":
            return self._reject(reply, "duplicate_or_terminal")
        if self.now >= task.expires_at or self.version - task.source_version > self.config.max_staleness:
            self._finish(task.task_id, "expired")
            self._fill()
            return self._reject(reply, "expired")
        local = torch.as_tensor(reply.local_model, dtype=torch.float64)
        if local.shape != self._model.shape or not torch.isfinite(local).all():
            return self._reject(reply, "vector")
        source = torch.tensor(self.snapshot(task.source_version).model, dtype=torch.float64)
        delta = source - local
        norm = delta.norm().item()
        if not torch.isfinite(delta).all() or not math.isfinite(norm):
            return self._reject(reply, "vector_norm")
        clipped = delta * min(1.0, self.config.clip_norm / norm) if norm else delta
        self._updates[task.task_id] = (delta, clipped)
        self.tasks[task.task_id] = replace(task, state="arrived")
        self._inbox.append(task.task_id)
        self._fill()
        self.trace.append(("arrive", self.now, task.task_id))
        return True  # Arrival changes protocol queues only, not model or ledger.

    def _expire_stale(self):
        for task_id in list(self._live.values()):
            if self.version - self.tasks[task_id].source_version > self.config.max_staleness:
                self._finish(task_id, "expired")
        self._fill()

    def candidates(self):
        return tuple({"task_id": i, "identity": self.tasks[i].identity,
            "source_version": self.tasks[i].source_version,
            "staleness": self.version - self.tasks[i].source_version,
            "delta": tuple(self._updates[i][0].tolist()),
            "clipped_delta": tuple(self._updates[i][1].tolist())} for i in self._buffer)

    def prepare_reference_event(self):
        """Only current buffer arrivals; no model/reference/receipt writes.

        Budget eligibility is not implemented in 0.3. Gate 0.4 must exclude
        exhausted identities before building its event, not after cold statistics.
        """
        if self.reference_config is None:
            raise RuntimeError("reference scoring must be explicitly enabled")
        self._expire_stale()
        rows = []
        for c in self.candidates():
            snapshot = self.snapshot(c["source_version"])
            if snapshot.config_id != self.config_id:
                raise ValueError("source snapshot configuration mismatch")
            source = ReferenceState(snapshot.mu, snapshot.sigma, snapshot.evidence)
            x = features(c["clipped_delta"], self.feature_map, self.config.clip_norm)
            rows.append(ReferenceCandidate(c["task_id"], c["identity"], c["source_version"], source, x))
        return prepare_event(rows, self.reference, self.reference_config, self.config.capacity,
                             self.config.eta_model, self.version)

    def commit_model(self, coefficients: Mapping[int, float]):
        """Model writeback seam only; NOT a D2 scoring/shared-budget commit."""
        self._expire_stale()
        candidates = self.candidates()
        if set(coefficients) != set(self._buffer):
            raise ValueError("supply exactly one coefficient per current candidate")
        for candidate in candidates:
            a = coefficients[candidate["task_id"]]
            ceiling = self.config.eta_model / (1 + candidate["staleness"]) / self.config.capacity
            if not math.isfinite(a) or not 0 <= a <= ceiling:
                raise ValueError("coefficient outside declared model-channel bound")
        positive = [c for c in candidates if coefficients[c["task_id"]] > 0]
        displacement = torch.zeros_like(self._model)
        for c in positive:
            displacement -= coefficients[c["task_id"]] * self._updates[c["task_id"]][1]
        updated_model = self._model + displacement
        if not torch.isfinite(displacement).all() or not torch.isfinite(updated_model).all():
            raise ValueError("nonfinite model writeback")
        if positive:
            self._model = updated_model
            self.batches.append({"at": self.now, "version_before": self.version,
                "version_after": self.version + 1, "candidates": list(candidates),
                "coefficients": [float(coefficients[c["task_id"]]) for c in candidates]})
        for c in candidates:
            a = float(coefficients[c["task_id"]])
            if a > 0:
                self.ledger.append({"task_id": c["task_id"], "identity": c["identity"],
                    "at": self.now, "source_version": c["source_version"], "a": a})
            self._finish(c["task_id"], "consumed" if a > 0 else "rejected")
        if positive:
            self.version += 1
            self._freeze()
        self._fill()
        self._expire_stale()
        return displacement.clone()
