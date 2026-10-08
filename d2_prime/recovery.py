"""Trusted local checkpoints at a single-threaded, safe event boundary.

The payload is a versioned copy of the complete backend state, not a model-only
checkpoint. Load only checkpoints produced by this application (torch pickle).
No TaskProtocol or reference-function interface is replaced.
"""
import copy
import random

import numpy as np
import torch

from .protocol import TaskProtocol

SCHEMA = "d2-prime/full-state/1"


def rng_state():
    return {"python": random.getstate(), "numpy": np.random.get_state(),
            "torch": torch.get_rng_state().clone(),
            "cuda": torch.cuda.get_rng_state_all() if torch.cuda.is_available() else []}


def restore_rng(state):
    random.setstate(state["python"])
    np.random.set_state(state["numpy"])
    torch.set_rng_state(state["torch"])
    if state["cuda"]:
        torch.cuda.set_rng_state_all(state["cuda"])


def capture_checkpoint(protocol, runtime=None):
    if not protocol.at_safe_event_boundary:
        raise RuntimeError("save requires a safe event boundary")
    protocol.audit_budget()
    return copy.deepcopy({"schema": SCHEMA, "config_id": protocol.config_id,
                          "protocol": vars(protocol), "runtime": runtime,
                          "rng": rng_state()})


def restore_checkpoint(payload, expected_config_id):
    if payload["schema"] != SCHEMA or payload["config_id"] != expected_config_id:
        raise ValueError("checkpoint schema/configuration mismatch")
    data = copy.deepcopy(payload)
    # Do not initialize R0, regenerate a feature map, or increment a version.
    protocol = TaskProtocol.__new__(TaskProtocol)
    protocol.__dict__ = data["protocol"]
    if protocol.config_id != expected_config_id or not protocol.at_safe_event_boundary:
        raise ValueError("unsafe or inconsistent saved state")
    protocol.audit_budget()
    restore_rng(data["rng"])
    return protocol, data["runtime"]


def save_checkpoint_file(path, payload):
    torch.save(payload, path)


def load_checkpoint_file(path):
    return torch.load(path, map_location="cpu", weights_only=False)
