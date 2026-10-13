"""G1.2 input preparation: ordinary FedAvg, sealed data, candidate packages.

No class-gradient measurement, probability estimator, calibration or probe.
"""

import hashlib
import io
import json
import pickle
import threading
import time
from pathlib import Path

import numpy as np
import torch

from direction_a.model import ResNet8Adapter, NORMALIZATION, transform_images


def encode(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n").encode("utf-8")


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def tensor_state_sha(state):
    """Same byte identity convention as the 0.2 adapter, including BN."""
    value = hashlib.sha256()
    for name, tensor in state.items():
        tensor = tensor.detach().cpu().contiguous()
        value.update(f"{name}:{tensor.dtype}:{tuple(tensor.shape)}".encode())
        value.update(tensor.numpy().tobytes())
    return value.hexdigest()


class PreparationLimit(RuntimeError):
    pass


class PreparationBudget:
    reserve = 128 * 1024

    def __init__(self, path, limits):
        self.path, self.limits = Path(path), limits
        self.started = time.monotonic()
        self.phase, self.phase_started = "startup", self.started
        self.phase_seconds = {}
        self.counts = {field: 0 for field in ("attempts", "optimizer_steps", "backwards", "forwards", "scans", "evidence_bytes", "logical_copy_bytes", "retries")}
        self.counts["evidence_bytes"] = self.reserve
        self.run_counts = {}
        self.progress = {}
        self.planned_references = []
        self.delivered_references = []
        self.status, self.hit = "running", None
        self.lock = threading.RLock()
        self.save()

    def snapshot(self, now=None):
        now = time.monotonic() if now is None else now
        phases = dict(self.phase_seconds)
        phases[self.phase] = phases.get(self.phase, 0) + now - self.phase_started
        return {"status": self.status, "hit": self.hit, "limits": self.limits, "counts": self.counts,
                "run_counts": self.run_counts, "elapsed_seconds": now - self.started,
                "phase_seconds": phases, "emergency_status_reserved_bytes": self.reserve,
                "progress": self.progress, "planned_references": self.planned_references,
                "delivered_references": self.delivered_references,
                "missing_references": [name for name in self.planned_references if name not in self.delivered_references]}

    def save(self, reserved=False):
        with self.lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            now = time.monotonic()
            if reserved:
                raw = encode(self.snapshot(now))
                if len(raw) > self.reserve:
                    raise RuntimeError("reserved status slot too small")
            else:
                before = self.counts["evidence_bytes"]
                for _ in range(4):
                    raw = encode(self.snapshot(now))
                    self.counts["evidence_bytes"] = before + len(raw)
                raw = encode(self.snapshot(now))
                self.counts["evidence_bytes"] = before + len(raw)
                if self.counts["evidence_bytes"] >= self.limits["evidence_bytes"]:
                    self.counts["evidence_bytes"] = before
                    self.stop("evidence_bytes", before + len(raw))
            self.path.write_bytes(raw)

    def stop(self, field, actual):
        self.status, self.hit = "budget_exhausted", {"field": field, "actual": actual}
        self.save(reserved=True)
        raise PreparationLimit(f"limit reached: {field}={actual}")

    def check(self):
        now = time.monotonic()
        if now - self.started >= self.limits["wall_seconds"]:
            self.stop("wall_seconds", now - self.started)
        if self.phase in self.limits["phase_seconds"]:
            spent = self.phase_seconds.get(self.phase, 0) + now - self.phase_started
            if spent >= self.limits["phase_seconds"][self.phase]:
                self.stop("phase_seconds." + self.phase, spent)

    def enter(self, phase):
        self.check()
        now = time.monotonic()
        self.phase_seconds[self.phase] = self.phase_seconds.get(self.phase, 0) + now - self.phase_started
        self.phase, self.phase_started = phase, now
        self.save()

    def consume(self, field, amount=1, run_id=None):
        self.check()
        proposed = self.counts[field] + amount
        if proposed >= self.limits[field]:
            self.stop(field, proposed)
        if run_id is not None and field in ("attempts", "optimizer_steps"):
            row = self.run_counts.setdefault(run_id, {"attempts": 0, "optimizer_steps": 0})
            per_run = row[field] + amount
            if per_run >= self.limits["per_run"][field]:
                self.stop(f"per_run.{run_id}.{field}", per_run)
            row[field] = per_run
        self.counts[field] = proposed

    def scan(self):
        self.consume("scans")

    def write(self, path, value, raw=False):
        data = value if raw else encode(value)
        self.consume("evidence_bytes", len(data))
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return sha(data)

    def finish(self):
        self.check()
        self.status = "candidate_package_delivered"
        self.save()


def watchdog(budget):
    import os

    def watch():
        while True:
            time.sleep(0.2)
            try:
                budget.check()
            except PreparationLimit:
                os._exit(124)
    threading.Thread(target=watch, daemon=True).start()


def windows_memory():
    """Actual Windows process working-set sample; no third-party dependency."""
    import ctypes
    from ctypes import wintypes

    class Counters(ctypes.Structure):
        _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD)] + [
            (name, ctypes.c_size_t) for name in ("PeakWorkingSetSize", "WorkingSetSize", "QuotaPeakPagedPoolUsage",
                                                "QuotaPagedPoolUsage", "QuotaPeakNonPagedPoolUsage", "QuotaNonPagedPoolUsage",
                                                "PagefileUsage", "PeakPagefileUsage")]
    kernel, psapi = ctypes.WinDLL("kernel32", use_last_error=True), ctypes.WinDLL("psapi", use_last_error=True)
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    psapi.GetProcessMemoryInfo.argtypes = (wintypes.HANDLE, ctypes.POINTER(Counters), wintypes.DWORD)
    value = Counters()
    value.cb = ctypes.sizeof(value)
    if not psapi.GetProcessMemoryInfo(kernel.GetCurrentProcess(), ctypes.byref(value), value.cb):
        raise OSError(ctypes.get_last_error(), "GetProcessMemoryInfo failed")
    return {"working_set_bytes": value.WorkingSetSize, "peak_working_set_bytes": value.PeakWorkingSetSize,
            "pagefile_usage_bytes": value.PagefileUsage, "measurement": "Windows PROCESS_MEMORY_COUNTERS, this process"}


def read_task(folder, baseline, budget, root):
    """Read/hash sealed files, without repartitioning or training-count scans."""
    budget.scan()
    folder = Path(folder)
    values, records = {}, {}
    for name in ("info.json", "data.json", "counts.json", "acceptance.json"):
        raw = (folder / name).read_bytes()
        digest = sha(raw)
        if digest != baseline[f"tasks/{folder.name}/{name}"]:
            raise RuntimeError(f"sealed 0.2 task mismatch: {folder / name}; stop, do not recount")
        records[name] = {"path": str((folder / name).relative_to(root)).replace("\\", "/"), "sha256": digest}
        values[name] = json.loads(raw)
    info, data, counts, acceptance = [values[name] for name in ("info.json", "data.json", "counts.json", "acceptance.json")]
    if any(records[name]["sha256"] != expected for name, expected in info["artifact_sha256"].items()):
        raise RuntimeError("0.2 nested hash mismatch")
    spec = info["spec"]
    if spec["clients"] != 20 or spec["classes"] not in (10, 100) or acceptance["status"] != "data_pass":
        raise RuntimeError("sealed population mismatch")
    return {"identity": folder.name, "info": info, "data": data, "counts": counts,
            "acceptance": acceptance, "source_records": records}


def task_binding(task, training_seed):
    info, counts, accepted = task["info"], task["counts"], task["acceptance"]
    return {"task_identity": task["identity"], "task_directory": task["source_records"]["info.json"]["path"].rsplit("/", 1)[0],
            "source_files": task["source_records"], "label_mapping": info["label_mapping"],
            "N": info["spec"]["clients"], "C": info["spec"]["classes"], "dataset": info["spec"]["dataset"],
            "split_identity": {"index_namespaces": task["data"]["index_namespaces"],
                               "validation_rule": info["validation_rule"], "test_rule": info["test_rule"],
                               "train_samples": accepted["train_total"], "validation_samples": accepted["validation_total"],
                               "test_samples": accepted["test_total"], "counts_source": task["source_records"]["counts.json"]},
            "nominal_IF": info["spec"]["imbalance_factor"], "actual_training_IF": info["actual_training_if"],
            "alpha": info["spec"]["alpha"], "alpha_statistical_definition": info["partitioner"],
            "alpha_parameter_vector": info["dirichlet_parameter_vector"],
            "alpha_integer_rule": "largest remainder; ties by client ID; no capacity balancing or redraw",
            "class_groups": counts["class_groups"], "tail_holding_clients": counts["tail_holding_clients"],
            "groups_tail_source": task["source_records"]["counts.json"],
            "data_seed": info["spec"]["seed"], "training_seed": training_seed,
            "counts_recomputed": False, "indices_changed": False, "test_used": False,
            "adjudication": "docs/DIRECTION_A_0_2_ADJUDICATION_v1.md; candidate name retained as historical identity"}


def load_train_cache(task, budget, device):
    budget.scan()
    dataset = task["info"]["spec"]["dataset"]
    hashes = task["info"]["source_file_sha256"]
    train_paths = [Path(path) for path in hashes if (Path(path).name.startswith("data_batch_") if dataset == "CIFAR10" else Path(path).name == "train")]
    train_paths.sort(key=lambda path: path.name)
    arrays, labels, verified = [], [], {}
    for path in train_paths:
        budget.check()
        raw = path.read_bytes()
        if sha(raw) != hashes[str(path)]:
            raise RuntimeError(f"original train file hash mismatch: {path}")
        batch = pickle.loads(raw, encoding="bytes")
        arrays.append(batch[b"data"])
        labels.extend(batch[b"labels"] if dataset == "CIFAR10" else batch[b"fine_labels"])
        verified[str(path)] = hashes[str(path)]
    raw_images = np.concatenate(arrays).reshape(-1, 3, 32, 32)
    raw_labels = np.asarray(labels, dtype=np.int64)
    train_indices = [index for client in task["data"]["clients"] for index in client["train"]]
    validation_indices = task["data"]["validation"]
    assert len(train_indices) == task["acceptance"]["train_total"]
    # Fetch exactly the sealed indices. No train-label counting or new split.
    cpu_x = transform_images(raw_images[train_indices], dataset)
    cpu_val_x = transform_images(raw_images[validation_indices], dataset)
    cpu_proxy = raw_images.nbytes + raw_labels.nbytes + cpu_x.numel() * cpu_x.element_size() + cpu_val_x.numel() * cpu_val_x.element_size()
    if cpu_proxy >= budget.limits["cpu_tensor_proxy_bytes"]:
        budget.stop("cpu_tensor_proxy_bytes", cpu_proxy)
    x, val_x = cpu_x.to(device), cpu_val_x.to(device)
    y = torch.tensor(raw_labels[train_indices], dtype=torch.long, device=device)
    val_y = torch.tensor(raw_labels[validation_indices], dtype=torch.long, device=device)
    offsets, position = [], 0
    for i, client in enumerate(task["data"]["clients"]):
        length = len(client["train"])
        assert length == task["acceptance"]["client_train_totals"][i] and length > 0
        offsets.append((position, position + length))
        position += length
    return {"x": x, "y": y, "validation_x": val_x, "validation_y": val_y, "offsets": offsets,
            "verified_original_train_sha256": verified, "cpu_resident_tensor_proxy_bytes": cpu_proxy,
            "raw_test_images_loaded": False, "windows_memory_after_load": windows_memory()}


def aggregate_states(states, volumes):
    if not states or len(states) != len(volumes) or any(n <= 0 for n in volumes):
        raise ValueError("invalid ordinary FedAvg inputs")
    keys = list(states[0])
    if any(list(state) != keys for state in states):
        raise ValueError("state key mismatch")
    weights = [n / sum(volumes) for n in volumes]
    result = {}
    for name in keys:
        tensors = [state[name] for state in states]
        if any(tensor.shape != tensors[0].shape or tensor.dtype != tensors[0].dtype for tensor in tensors):
            raise ValueError("state shape/dtype mismatch")
        if tensors[0].is_floating_point():
            combined = torch.zeros_like(tensors[0])
            for tensor, weight in zip(tensors, weights):
                combined.add_(tensor, alpha=weight)
            result[name] = combined
        elif name.endswith("num_batches_tracked"):
            result[name] = torch.stack(tensors).amax(dim=0)
        else:
            if not all(torch.equal(tensors[0], tensor) for tensor in tensors[1:]):
                raise ValueError("unsupported non-floating buffer mismatch")
            result[name] = tensors[0].clone()
    return result


def summarize_validation(confusion, ce_sum, groups):
    C = len(confusion)
    denominators = [sum(row) for row in confusion]
    correct = sum(confusion[c][c] for c in range(C))
    total = sum(denominators)
    recalls = [None if not denominators[c] else confusion[c][c] / denominators[c] for c in range(C)]

    def macro(classes):
        missing = [c for c in classes if recalls[c] is None]
        return {"value_fraction": None if missing or not classes else sum(recalls[c] for c in classes) / len(classes),
                "class_denominator": len(classes), "class_ids": classes, "missing_classes": missing}

    return {"mean_cross_entropy": ce_sum / total, "cross_entropy_unit": "nat per validation example",
            "sample_accuracy_fraction": correct / total, "sample_accuracy_percent": 100 * correct / total,
            "sample_denominator": total, "correct_samples": correct, "class_sample_denominators": denominators,
            "per_class_recall_fraction": recalls, "macro_recall": macro(list(range(C))),
            "group_macro_recall": {name: macro(classes) for name, classes in groups.items()},
            "confusion_true_rows_predicted_columns": confusion,
            "units": "accuracy/recall fractions [0,1]; accuracy percentage also provided"}


def validate_model(model, cache, groups, C, budget, batch=128):
    model.eval()
    before = tensor_state_sha(model.state_dict())
    confusion = torch.zeros(C, C, dtype=torch.int64, device=cache["validation_x"].device)
    ce_sum = 0.0
    budget.scan()
    with torch.inference_mode():
        for start in range(0, len(cache["validation_y"]), batch):
            budget.consume("forwards")
            logits = model(cache["validation_x"][start:start + batch])
            target = cache["validation_y"][start:start + batch]
            ce_sum += float(torch.nn.functional.cross_entropy(logits, target, reduction="sum"))
            codes = target * C + logits.argmax(dim=1)
            confusion += torch.bincount(codes, minlength=C * C).reshape(C, C)
    if tensor_state_sha(model.state_dict()) != before:
        raise RuntimeError("validation changed parameters/BN")
    return summarize_validation(confusion.cpu().tolist(), ce_sum, groups)


def save_candidate(path, model, metadata, budget):
    state = {name: value.detach().cpu().clone() for name, value in model.state_dict().items()}
    identity = tensor_state_sha(state)
    metadata = dict(metadata, state_sha256=identity)
    stream = io.BytesIO()
    torch.save({"state_dict": state, "metadata": metadata}, stream)
    file_hash = budget.write(path, stream.getvalue(), raw=True)
    budget.scan()
    actual = Path(path).read_bytes()
    assert sha(actual) == file_hash
    restored = torch.load(io.BytesIO(actual), map_location="cpu", weights_only=True)
    assert restored["metadata"] == metadata and list(restored["state_dict"]) == list(state)
    assert all(torch.equal(tensor, restored["state_dict"][name]) for name, tensor in state.items())
    assert tensor_state_sha(restored["state_dict"]) == identity
    reader = ResNet8Adapter(metadata["model"]["C"])
    reader.load_state_dict(restored["state_dict"], strict=True)
    reader.freeze_reference()
    assert tensor_state_sha(reader.state_dict()) == identity
    return {"file_sha256": file_hash, "state_sha256": identity,
            "file_bytes": len(actual), "bitwise_state_readback": True,
            "dtype": "float32 parameters; int64 BN num_batches_tracked", "metadata": metadata}


def restore_candidate(path, device="cpu"):
    """Load a prepared reference; this loader is not G1.2 acceptance."""
    packet = torch.load(path, map_location="cpu", weights_only=True)
    metadata = packet["metadata"]
    if tensor_state_sha(packet["state_dict"]) != metadata["state_sha256"]:
        raise RuntimeError("candidate state identity mismatch")
    model = ResNet8Adapter(metadata["model"]["C"]).to(device)
    model.load_state_dict(packet["state_dict"], strict=True)
    model.freeze_reference()
    return model, metadata


def resource_sample(budget):
    value = {"cuda_allocated_bytes": torch.cuda.memory_allocated(), "cuda_reserved_bytes": torch.cuda.memory_reserved(),
             "cuda_peak_allocated_bytes": torch.cuda.max_memory_allocated(), "cuda_peak_reserved_bytes": torch.cuda.max_memory_reserved(),
             "windows_process_memory": windows_memory()}
    if value["cuda_peak_allocated_bytes"] >= budget.limits["gpu_allocated_bytes"]:
        budget.stop("gpu_allocated_bytes", value["cuda_peak_allocated_bytes"])
    return value
