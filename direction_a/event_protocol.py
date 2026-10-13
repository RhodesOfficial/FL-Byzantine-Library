"""G1.1 mechanism types and bounded ledger; no models or probability predictor."""

import hashlib
import json
import threading
import time
from dataclasses import asdict, dataclass
from fractions import Fraction
from pathlib import Path


def encode(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def ratio(value):
    return str(Fraction(value))


@dataclass(frozen=True)
class Mechanism:
    identity: str = "FedPCC-G1.1-event-smoke-v1"
    clients: int = 20
    invitations: int = 8
    deadline: str = "8"
    online_probability: str = "9/10"
    dropout_probability: str = "1/20"
    jitter_low: str = "1/4"
    jitter_high: str = "7/4"
    work_units: tuple = (("ordinary_training", "1"), ("reference_class_gradient_scan", "1"),
                         ("feature_norm_statistics", "1/4"), ("message_preparation", "1/4"))

    @property
    def total_work(self):
        return sum((Fraction(value) for _, value in self.work_units), Fraction(0))

    @property
    def q(self):
        return Fraction(self.invitations, self.clients)

    def manifest(self):
        value = asdict(self)
        value["total_work_units"] = ratio(self.total_work)
        value["q_known_invitation_fraction"] = ratio(self.q)
        value["workload_status"] = "logical-duration-proxy; no computation is executed or benchmarked"
        value["random_grid_denominator"] = 2 ** 53
        value["jitter_formula"] = "low + (high-low)*U_jitter"
        value["r_conditioning"] = "valid return given planned invitation, including offline and dropout failures"
        value["round_semantics"] = "simulated successful completion slot; actual model updates=0"
        return value


class BudgetExceeded(RuntimeError):
    pass


class EventBudget:
    """All generation, tests and replay share the same cumulative ceilings."""
    reserve = 65536

    def __init__(self, path, limits):
        self.path = Path(path)
        self.limits = limits
        self.started = time.monotonic()
        self.phase_started = self.started
        self.phase = "startup"
        self.phase_seconds = {}
        self.counts = {name: 0 for name in ("attempts", "scans", "registration_bytes", "event_bytes", "evidence_bytes", "retries")}
        self.trace_attempts = {}
        self.actions = []
        self.hit = None
        self.status = "running"
        self.lock = threading.RLock()
        # Failure/status space is part of the ceiling, not an exception to it.
        self.counts["evidence_bytes"] = self.reserve
        self.save()

    def snapshot(self, now=None):
        phases = dict(self.phase_seconds)
        now = time.monotonic() if now is None else now
        phases[self.phase] = phases.get(self.phase, 0) + now - self.phase_started
        return {"status": self.status, "hit": self.hit, "limits": self.limits,
                "counts": self.counts, "trace_attempts": self.trace_attempts,
                "elapsed_seconds": now - self.started, "phase_seconds": phases,
                "reserved_failure_status_bytes": self.reserve, "actions": self.actions}

    def save(self, reserved=False):
        with self.lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            frozen_now = time.monotonic()
            if reserved:
                value = self.snapshot(frozen_now)
                value.pop("actions")
                value["journal_note"] = "emergency snapshot in pre-reserved slot; existing evidence is retained"
                raw = encode(value) + b"\n"
                if len(raw) > self.reserve:
                    raise RuntimeError("emergency snapshot exceeded reserved slot")
            else:
                previous = self.counts["evidence_bytes"]
                # Include the ledger's own writes, including its changed digit count.
                for _ in range(4):
                    raw = encode(self.snapshot(frozen_now)) + b"\n"
                    self.counts["evidence_bytes"] = previous + len(raw)
                raw = encode(self.snapshot(frozen_now)) + b"\n"
                self.counts["evidence_bytes"] = previous + len(raw)
                if self.counts["evidence_bytes"] >= self.limits["evidence_bytes"]:
                    self.counts["evidence_bytes"] = previous
                    self.stop("evidence_bytes", previous + len(raw))
            self.path.write_bytes(raw)

    def stop(self, field, actual):
        self.status = "budget_exhausted"
        self.hit = {"field": field, "actual": actual}
        self.save(reserved=True)
        raise BudgetExceeded(f"limit reached: {field}={actual}")

    def check(self):
        now = time.monotonic()
        if now - self.started >= self.limits["wall_seconds"]:
            self.stop("wall_seconds", now - self.started)
        if self.phase in self.limits["phase_seconds"]:
            spent = self.phase_seconds.get(self.phase, 0) + now - self.phase_started
            if spent >= self.limits["phase_seconds"][self.phase]:
                self.stop(f"phase_seconds.{self.phase}", spent)

    def enter(self, phase):
        self.check()
        now = time.monotonic()
        self.phase_seconds[self.phase] = self.phase_seconds.get(self.phase, 0) + now - self.phase_started
        self.phase = phase
        self.phase_started = now
        self.save()

    def consume(self, field, amount, name):
        self.check()
        new = self.counts[field] + amount
        if new >= self.limits[field]:
            self.stop(field, new)
        self.counts[field] = new
        # Bound the journal; counts are cumulative even where names aggregate.
        self.actions.append({"field": field, "amount": amount, "name": name})

    def scan(self, name):
        self.consume("scans", 1, name)

    def attempt(self, trace_id, cap=None):
        if cap is not None and self.trace_attempts.get(trace_id, 0) + 1 >= cap:
            self.stop("trace_attempts." + trace_id, self.trace_attempts.get(trace_id, 0) + 1)
        self.consume("attempts", 1, trace_id)
        self.trace_attempts[trace_id] = self.trace_attempts.get(trace_id, 0) + 1

    def write(self, path, value):
        raw = encode(value) + b"\n"
        self.consume("evidence_bytes", len(raw), str(path))
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
        return digest(raw)

    def status_checkpoint(self):
        # save() itself charges every ledger write.
        self.save()

    def finish(self):
        self.check()
        self.status = "pass"
        self.status_checkpoint()


def start_watchdog(budget):
    import os

    def watch():
        while True:
            time.sleep(0.1)
            try:
                budget.check()
            except BudgetExceeded:
                os._exit(124)
    threading.Thread(target=watch, daemon=True).start()
