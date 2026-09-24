"""Experimental update rules for the four robust-FL research questions.

These are new hypotheses, not reproductions of BRAFed or BR-DRAG.  All
vectors use the bridge convention: starting model minus trained model.
No oracle client labels enter any defense decision.
"""

from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter

import torch


@dataclass
class Update:
    client_id: int
    vector: torch.Tensor
    sent_round: int
    arrival_time: int


def _unit(vector: torch.Tensor) -> torch.Tensor:
    return vector / vector.norm().clamp_min(1e-12)


def cosine(a: torch.Tensor, b: torch.Tensor) -> float:
    return float(torch.dot(_unit(a), _unit(b)).item())


def clipped_mean(vectors: list[torch.Tensor], cap: float | None = None) -> torch.Tensor:
    if not vectors:
        raise ValueError("cannot aggregate an empty update set")
    if cap is None:
        norms = torch.stack([v.norm() for v in vectors])
        cap = float((2 * norms.median()).clamp_min(1e-12).item())
    return torch.stack([v * min(1.0, cap / max(float(v.norm()), 1e-12))
                        for v in vectors]).mean(dim=0)


def project_conflict(vector: torch.Tensor, reference: torch.Tensor,
                     strength: float = 1.0) -> torch.Tensor:
    """Remove at most `strength` of the component opposite to reference."""
    denominator = torch.dot(reference, reference).clamp_min(1e-12)
    coefficient = (torch.dot(vector, reference) / denominator).clamp(max=0)
    return vector - strength * coefficient * reference


class Triage:
    """Accept, partially correct, or defer using version, history and peers.

    A client's history is never accepted as truth on its own.  Both its
    history and peer support are required to preserve an opposing update.
    The pending queue is bounded and each item expires after max_age rounds.
    """

    def __init__(self, *, peer_threshold: float = 0.55,
                 history_threshold: float = 0.55, max_age: int = 3,
                 correction: float = 0.8):
        self.peer_threshold = peer_threshold
        self.history_threshold = history_threshold
        self.max_age = max_age
        self.correction = correction
        self.history: dict[int, torch.Tensor] = {}
        self.pending: dict[int, Update] = {}

    def process(self, arrivals: list[Update], reference: torch.Tensor,
                round_number: int) -> tuple[list[torch.Tensor], dict[int, str]]:
        current_ids = {u.client_id for u in arrivals}
        expired = {cid: "rejected" for cid, u in self.pending.items()
                   if round_number - u.sent_round > self.max_age}
        candidates = arrivals + [u for cid, u in self.pending.items()
                                 if cid not in current_ids and
                                 round_number - u.sent_round <= self.max_age]
        self.pending = {}
        if not candidates:
            return [], expired
        ref = _unit(reference)
        normalized = [_unit(u.vector) for u in candidates]
        accepted: list[torch.Tensor] = []
        decisions: dict[int, str] = expired
        for index, update in enumerate(candidates):
            age = max(0, round_number - update.sent_round)
            alignment = float(torch.dot(normalized[index], ref))
            peers = sum(float(torch.dot(normalized[index], other)) >= self.peer_threshold
                        for j, other in enumerate(normalized) if j != index)
            past = self.history.get(update.client_id)
            stable = past is not None and cosine(update.vector, past) >= self.history_threshold
            supported = peers >= 2 or (peers >= 1 and stable)
            if alignment >= 0.1 or supported:
                value = update.vector
                decision = "accepted"
            elif age > 0 and alignment >= -0.45:
                value = project_conflict(update.vector, reference, self.correction)
                decision = "corrected"
            elif age <= self.max_age and update.client_id not in self.pending:
                self.pending[update.client_id] = update
                decisions[update.client_id] = "deferred"
                continue
            else:
                decisions[update.client_id] = "rejected"
                continue
            accepted.append(value)
            decisions[update.client_id] = decision
            # Small EMA limits the influence of one apparently valid round.
            self.history[update.client_id] = (
                0.8 * past + 0.2 * _unit(value) if past is not None else _unit(value)
            ).detach().clone()
        return accepted, decisions


def reference_fusion(root: torch.Tensor | None, history: torch.Tensor | None,
                     peer: torch.Tensor | None, *, floor: float = 0.1,
                     root_weight: float = 0.7) -> tuple[torch.Tensor, float]:
    """Downweight an inconsistent trusted root direction without an oracle."""
    if root is None or root.norm() < 1e-12:
        if history is None and peer is None:
            raise ValueError("no reference direction is available")
        return (history if peer is None else peer if history is None else
                0.5 * history + 0.5 * peer), 0.0
    alternatives = [x for x in (history, peer) if x is not None and x.norm() > 1e-12]
    if not alternatives:
        return root, 1.0
    agreement = sum(max(0.0, cosine(root, x)) for x in alternatives) / len(alternatives)
    weight = floor + (root_weight - floor) * agreement
    alternative = torch.stack([_unit(x) for x in alternatives]).mean(dim=0)
    direction = weight * _unit(root) + (1.0 - weight) * _unit(alternative)
    return direction * root.norm(), weight


def root_align(vectors: list[torch.Tensor], reference: torch.Tensor,
               correction: float = 0.5) -> torch.Tensor:
    """Align directions while keeping the step on the client-update scale."""
    if not vectors:
        raise ValueError("cannot align an empty update set")
    norm = torch.stack([v.norm() for v in vectors]).median().clamp_min(1e-12)
    direction = _unit(reference) * norm
    aligned = []
    for vector in vectors:
        scaled = _unit(vector) * vector.norm().clamp(max=2 * norm)
        divergence = 1.0 - cosine(vector, reference)
        weight = min(1.0, correction * divergence)
        aligned.append((1.0 - weight) * scaled + weight * direction)
    return torch.stack(aligned).mean(dim=0)


class Anytime:
    """Stage expensive checks while recording the actual deadline misses.

    The budget is a soft deadline: even the initial norm/sign pass takes
    time.  Callers must report p95 and deadline misses, not just averages.
    """

    def __init__(self, budget_ms: float, uncertainty: float = 0.25):
        if budget_ms <= 0:
            raise ValueError("budget_ms must be positive")
        self.budget_ms = budget_ms
        self.uncertainty = uncertainty

    def aggregate(self, updates: list[Update], reference: torch.Tensor,
                  triage: Triage, round_number: int) -> tuple[torch.Tensor, dict]:
        if reference.is_cuda:
            torch.cuda.synchronize(reference.device)
        start = perf_counter()
        norms = torch.stack([u.vector.norm() for u in updates])
        cap = float((2 * norms.median()).clamp_min(1e-12).item())
        quick = [u for u in updates if float(u.vector.norm()) <= cap and
                 cosine(u.vector, reference) >= -self.uncertainty]
        quick_ids = {id(u) for u in quick}
        uncertain = [u for u in updates if id(u) not in quick_ids]
        if reference.is_cuda:
            torch.cuda.synchronize(reference.device)
        elapsed_ms = (perf_counter() - start) * 1000
        stage = "cheap"
        decisions = {u.client_id: "accepted" for u in quick}
        vectors = [u.vector for u in quick]
        if uncertain and elapsed_ms < self.budget_ms:
            refined, detail = triage.process(uncertain, reference, round_number)
            vectors.extend(refined)
            decisions.update(detail)
            stage = "triage"
        else:
            decisions.update({u.client_id: "deferred" for u in uncertain})
        if not vectors:
            vectors = [project_conflict(u.vector, reference) for u in updates]
            stage = "fallback"
        result = clipped_mean(vectors, cap)
        if reference.is_cuda:
            torch.cuda.synchronize(reference.device)
        elapsed_ms = (perf_counter() - start) * 1000
        return result, {"decisions": decisions, "stage": stage,
                        "aggregation_ms": elapsed_ms,
                        "deadline_miss": elapsed_ms > self.budget_ms}
