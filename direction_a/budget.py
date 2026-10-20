"""Cumulative guard shared by all phase 0.2 measurements and retries."""

import json
import threading
import time
from pathlib import Path


class LimitReached(RuntimeError):
    pass


class Budget:
    def __init__(self, path, limits):
        self.path = Path(path)
        self.limits = limits
        self.started = time.monotonic()
        self.counts = {"forwards": 0, "scans": 0, "artifact_bytes": 0, "retries": 0}
        self.phase = "startup"
        self.phase_started = self.started
        self.phase_seconds = {}
        self.events = []
        self.status = "running"
        self.hit = None
        self.lock = threading.RLock()
        self.save()

    @classmethod
    def resume(cls, path):
        """Continue verification with consumed limits; never reset a run."""
        value = json.loads(Path(path).read_text(encoding="utf-8"))
        if value["hit"] is not None or value["status"] == "budget_exhausted":
            raise LimitReached("exhausted run cannot resume")
        instance = cls.__new__(cls)
        instance.path = Path(path)
        instance.limits = value["limits"]
        now = time.monotonic()
        instance.started = now - value["elapsed_seconds"]
        instance.counts = dict(value["counts"])
        instance.phase = "verification"
        instance.phase_started = now
        instance.phase_seconds = dict(value["phase_seconds"])
        instance.events = list(value["events"])
        instance.status = "running"
        instance.hit = None
        instance.lock = threading.RLock()
        instance.save()
        return instance

    def check(self):
        elapsed = time.monotonic() - self.started
        if elapsed >= self.limits["wall_seconds"]:
            self.stop("wall_seconds", elapsed)
        phase_elapsed = self.phase_seconds.get(self.phase, 0) + time.monotonic() - self.phase_started
        if self.phase in self.limits["phase_seconds"] and phase_elapsed >= self.limits["phase_seconds"][self.phase]:
            self.stop(f"phase_seconds.{self.phase}", phase_elapsed)

    def stop(self, field, actual):
        self.hit = {"field": field, "actual": actual}
        self.status = "budget_exhausted"
        self.save()
        raise LimitReached(f"budget reached: {field}={actual}")

    def enter(self, phase):
        self.check()
        self.phase_seconds[self.phase] = self.phase_seconds.get(self.phase, 0) + time.monotonic() - self.phase_started
        self.phase = phase
        self.phase_started = time.monotonic()
        self.save()

    def consume(self, field, name, amount=1):
        self.check()
        new = self.counts[field] + amount
        # Equality also stops: reaching an upper bound does not authorize more work.
        if new >= self.limits[field]:
            self.stop(field, new)
        self.counts[field] = new
        self.events.append({"field": field, "amount": amount, "name": name})

    def scan(self, name):
        self.consume("scans", name)

    def forward(self, name, fn):
        self.consume("forwards", name)
        value = fn()
        self.check()
        return value

    def write_json(self, path, value):
        data = (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")
        self.consume("artifact_bytes", str(path), len(data))
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return data

    def save(self):
        with self.lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            elapsed = time.monotonic() - self.started
            phases = dict(self.phase_seconds)
            phases[self.phase] = phases.get(self.phase, 0) + time.monotonic() - self.phase_started
            value = {"status": self.status, "hit": self.hit, "limits": self.limits,
                     "counts": self.counts, "elapsed_seconds": elapsed,
                     "phase_seconds": phases, "events": self.events}
            self.path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def finish(self, status):
        self.check()
        self.status = status
        self.save()
