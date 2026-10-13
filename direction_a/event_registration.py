"""Register the sealed 0.2 counts through an encoded local loopback only."""

import json
import time
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType

from direction_a.event_protocol import digest, encode


@dataclass(frozen=True)
class SealedTask:
    identity: str
    dataset: str
    classes: int
    ids: tuple
    n_ic: tuple
    N_c: tuple
    a_ic: tuple
    tail_classes: tuple
    train_totals: tuple
    index_hashes: tuple
    hashes: tuple
    tail_holders: tuple

    @property
    def file_hashes(self):
        return dict(self.hashes)


def read_sealed_task(folder, baseline_hashes, budget):
    """Hash/read only: never parse CIFAR labels or call the 0.2 audit/builder."""
    folder = Path(folder)
    budget.scan(folder.name + ":sealed_input_read")
    values, hashes = {}, {}
    for name in ("info.json", "data.json", "counts.json", "acceptance.json"):
        raw = (folder / name).read_bytes()
        hashes[name] = digest(raw)
        expected = baseline_hashes[f"tasks/{folder.name}/{name}"]
        if hashes[name] != expected:
            raise ValueError(f"0.2 sealed hash conflict: {folder / name}; stop, do not recount")
        values[name] = json.loads(raw)
    info, data, counts, accepted = (values[name] for name in ("info.json", "data.json", "counts.json", "acceptance.json"))
    if any(hashes[name] != value for name, value in info["artifact_sha256"].items()):
        raise ValueError("0.2 nested hash conflict")
    ids = tuple(client["id"] for client in data["clients"])
    C = info["spec"]["classes"]
    if len(ids) != 20 or len(set(ids)) != 20 or C not in (10, 100):
        raise ValueError("0.2 population identity conflict")
    # Metadata equality checks only; no n_ic/N_c/a_ic recomputation.
    if counts["N_c"] != accepted["training_class_counts"] or counts["class_groups"] != accepted["class_groups"]:
        raise ValueError("0.2 sealed metadata conflict")
    return SealedTask(folder.name, info["spec"]["dataset"], C, ids,
                      tuple(tuple(row) for row in counts["n_ic"]), tuple(counts["N_c"]),
                      tuple(tuple(row) for row in counts["a_ic"]), tuple(counts["class_groups"]["tail"]),
                      tuple(accepted["client_train_totals"]),
                      tuple(digest(encode(client["train"])) for client in data["clients"]),
                      tuple(hashes.items()), tuple(counts["tail_holding_clients"]))


@dataclass(frozen=True)
class Registration:
    client_id: str
    class_ids: tuple
    n_ic: tuple
    N_c: tuple
    a_ic: tuple
    train_split_hash: str
    registration_ok: bool


class Registry:
    def __init__(self, entries):
        self.entries = MappingProxyType(dict(entries))


def register_task(task, budget):
    budget.scan(task.identity + ":local_loopback_registration")
    started = time.perf_counter()
    messages, entries = [], {}
    up_bytes = down_bytes = 0
    for i, client_id in enumerate(task.ids):
        begin = time.perf_counter()
        message = {"message_type": "register_sealed_training_counts", "client_id": client_id,
                   "task_identity": task.identity, "class_ids": list(range(task.classes)),
                   "n_ic": list(task.n_ic[i]), "N_c": list(task.N_c), "a_ic": list(task.a_ic[i]),
                   "train_split_hash": task.index_hashes[i], "source_task_sha256": task.file_hashes,
                   "count_provenance": "copied from sealed 0.2 counts; never recounted"}
        upload = encode(message)
        budget.consume("registration_bytes", len(upload), task.identity + ":upload:" + client_id)
        decoded = json.loads(upload)  # Actual receiving path of this local loopback.
        if decoded != message or client_id in entries:
            raise ValueError("registration integrity/duplicate conflict")
        entry = Registration(client_id, tuple(decoded["class_ids"]), tuple(decoded["n_ic"]),
                             tuple(decoded["N_c"]), tuple(decoded["a_ic"]), decoded["train_split_hash"], True)
        entries[client_id] = entry
        ack = encode({"client_id": client_id, "registration_ok": True,
                      "task_identity": task.identity, "received_upload_sha256": digest(upload)})
        budget.consume("registration_bytes", len(ack), task.identity + ":ack:" + client_id)
        if json.loads(ack)["received_upload_sha256"] != digest(upload):
            raise ValueError("registration ack conflict")
        messages.append({"client_id": client_id, "registration_ok": True,
                         "upload_utf8": upload.decode("utf-8"), "ack_utf8": ack.decode("utf-8"),
                         "upload_bytes": len(upload), "ack_bytes": len(ack),
                         "upload_sha256": digest(upload), "ack_sha256": digest(ack),
                         "encode_decode_ack_seconds": time.perf_counter() - begin})
        up_bytes += len(upload)
        down_bytes += len(ack)
    result = {"task_identity": task.identity, "registered_ids": list(entries), "all_registered": True,
              "messages": messages, "registration_uplink_encoded_bytes": up_bytes,
              "registration_downlink_encoded_bytes": down_bytes,
              "registration_wall_seconds": time.perf_counter() - started,
              "transport": "local in-memory UTF-8 upload/decode/ACK; no actual network",
              "network_sent_bytes": None, "bootstrap_order": "completed before every event attempt",
              "registration_deadline": "separate bootstrap; not subject to per-attempt 8 simulated seconds",
              "source_file_sha256": task.file_hashes}
    return Registry(entries), result
