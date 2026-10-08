"""Persistent immutable sliding-budget state, owned by a TaskProtocol instance."""
from collections import defaultdict, deque
from dataclasses import dataclass
import math


@dataclass(frozen=True)
class BudgetConfig:
    window: float
    limit: float
    specification: str = "D2_PRIME_DESIGN:2.1.5/phase0.4-v1"

    def __post_init__(self):
        if any(not math.isfinite(x) or x <= 0 for x in (self.window, self.limit)):
            raise ValueError("H and beta must be explicit finite positive values")


@dataclass(frozen=True)
class Receipt:
    task_id: int
    identity: int
    at: float
    a: float
    b: float
    q: float

    def __post_init__(self):
        if any(type(x) is not int or x < 0 for x in (self.task_id, self.identity)):
            raise ValueError("invalid receipt task or identity")
        if any(not math.isfinite(x) or x < 0 for x in (self.at, self.a, self.b, self.q)):
            raise ValueError("nonfinite or negative receipt")
        if self.q <= 0 or self.q != self.a + self.b:
            raise ValueError("receipt must charge the exact positive a+b coefficient sum")


def check_limit(spent, limit):
    # Only relative roundoff allowance; never clamp/forgive a material overcharge.
    if spent > limit and not math.isclose(spent, limit, rel_tol=1e-12, abs_tol=0.):
        raise ValueError("sliding contribution limit exceeded")


def audit_history(receipts, config):
    """Check all historical windows, including charges now outside the live window."""
    seen, queues, previous = set(), defaultdict(deque), 0.
    for receipt in receipts:
        if receipt.task_id in seen:
            raise ValueError("duplicate task consumption in budget history")
        if receipt.at < previous:
            raise ValueError("nonmonotone budget history")
        seen.add(receipt.task_id)
        previous = receipt.at
        queue = queues[receipt.identity]
        while queue and queue[0].at <= receipt.at - config.window:
            queue.popleft()
        queue.append(receipt)
        check_limit(math.fsum(r.q for r in queue), config.limit)
    return frozenset(seen)


@dataclass(frozen=True)
class RollingBudget:
    config: BudgetConfig
    entries: tuple = ()
    consumed: frozenset = frozenset()
    at: float = 0.

    def __post_init__(self):
        object.__setattr__(self, "entries", tuple(self.entries))
        object.__setattr__(self, "consumed", frozenset(self.consumed))
        if not math.isfinite(self.at) or self.at < 0:
            raise ValueError("invalid budget clock")

    def _time(self, at):
        if not math.isfinite(at) or at < self.at:
            raise ValueError("budget time cannot move backwards")

    def remaining(self, identity, at):
        self._time(at)
        spent = math.fsum(r.q for r in self.entries
                         if r.identity == identity and at-self.config.window < r.at <= at)
        return max(0., self.config.limit - spent)

    def prune(self, at):
        self._time(at)
        live = tuple(r for r in self.entries if at-self.config.window < r.at <= at)
        return RollingBudget(self.config, live, self.consumed, at)

    def record(self, receipts, at):
        receipts = tuple(receipts)
        state = self.prune(at)
        seen = set(state.consumed)
        for r in receipts:
            if r.at != at or r.task_id in seen:
                raise ValueError("duplicate task or wrong actual commit time")
            seen.add(r.task_id)
        entries = state.entries + tuple(receipts)
        for identity in {r.identity for r in entries}:
            check_limit(math.fsum(r.q for r in entries if r.identity == identity), self.config.limit)
        return RollingBudget(self.config, entries, frozenset(seen), at)
