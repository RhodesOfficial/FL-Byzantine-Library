"""The single authorized FedPCC-G1.2-full-measurement-v1 run; never retries."""

import os
import time

PROGRAM_STARTED = time.monotonic()
os.environ["CUBLAS_WORKSPACE_CONFIG"] = ":4096:8"

import gc
import importlib.util
import json
import pickle
import platform
import sys
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.dont_write_bytecode = True

import numpy as np
import torch

from direction_a.backbone_preparation import encode, sha, restore_candidate, tensor_state_sha, PreparationLimit
from direction_a.class_gradient_full import FullBudget, aggregate, compare, direct_class_sum
from direction_a.class_gradient_smoke import (analytic_gradient, encode_client, feature_statistics,
    full_class_gradient, head_gradient, save_tensors, timed, to_tensors)
from direction_a.model import NORMALIZATION, transform_images
from measure_direction_a_class_gradient_smoke import verify_inputs, git, json_file, now, UPSTREAM

OUTPUT = ROOT / "artifacts/direction_a/phaseG1_2_full_v1"
BASE = "bfec9265ad57ac66fd45b90472e572a0e0eda0d3"
LIMITS = dict(attempts=0, optimizer_steps=0, retries=0, searches=0, backwards=10000,
              forwards=20000, scans=20000, feature_samples=41838, client_scans=80,
              extra_encoded_positions=0, class_gradient_requests=10000, formal_runs=1,
              implementation_revisions=2, evidence_bytes=256*1024**2, logical_copy_bytes=256*1024**2,
              gpu_allocated_bytes=6*1024**3, windows_peak_working_set_bytes=6*1024**3,
              cpu_tensor_proxy_bytes=2*1024**3, wall_seconds=600, phase_seconds={}, per_run={})
SOURCE_PATHS = ["direction_a/class_gradient_full.py", "scripts/measure_direction_a_class_gradient_full.py",
                "tests/test_direction_a_class_gradient_full.py", "direction_a/class_gradient_smoke.py",
                "scripts/measure_direction_a_class_gradient_smoke.py", "direction_a/model.py",
                "direction_a/backbone_preparation.py", "models/ResNet.py"]


def relative(path):
    return Path(path).relative_to(OUTPUT).as_posix()


def save(path, value, budget):
    result = save_tensors(OUTPUT / path, to_tensors(value), budget)
    result["path"] = relative(result["path"])
    return result


def load_raw(task, budget):
    budget.scan()
    dataset = task["info"]["spec"]["dataset"]
    paths = sorted([Path(p) for p in task["info"]["source_file_sha256"] if
                    (Path(p).name.startswith("data_batch_") if dataset == "CIFAR10" else Path(p).name == "train")])
    arrays, labels, verified = [], [], {}
    for path in paths:
        raw = path.read_bytes()
        digest = sha(raw)
        if digest != task["info"]["source_file_sha256"][str(path)]:
            raise RuntimeError("official training source changed")
        data = pickle.loads(raw, encoding="bytes")
        arrays.append(data[b"data"])
        labels.extend(data[b"labels"] if dataset == "CIFAR10" else data[b"fine_labels"])
        verified[str(path)] = digest
    images = np.concatenate(arrays).reshape(-1, 3, 32, 32)
    labels = np.asarray(labels, np.int64)
    # Conservative live-array envelope: raw decode/concat, largest client transform
    # (including its temporaries), all per-reference diagnostics and save/read buffers.
    max_n = max(task["acceptance"]["client_train_totals"])
    C = task["info"]["spec"]["classes"]
    diagnostic_bound = sum(n > 0 for row in task["counts"]["n_ic"] for n in row)*C*129*8
    proxy = 3*images.nbytes + 2*labels.nbytes + max_n*3*32*32*4*4 + 4*diagnostic_bound + 64*1024**2
    budget.cpu_proxy(proxy)
    return images, labels, {"verified_train_sources": verified, "cpu_known_array_envelope_bytes": proxy,
                            "test_loaded": False, "validation_indices_accessed": False}


def identity(reference, task):
    path = UPSTREAM / reference["checkpoint_path"]
    model, metadata = restore_candidate(path, "cuda")
    before = tensor_state_sha(model.state_dict())
    C = task["info"]["spec"]["classes"]
    if (before != reference["state_sha256"] or sha(path.read_bytes()) != reference["checkpoint_file_sha256"] or
        metadata["reference_id"] != reference["reference_id"] or metadata["task_identity"] != task["identity"] or
        metadata["task_source_sha256"] != {k: v["sha256"] for k, v in task["source_records"].items()} or
        metadata["generation_config_sha256"] != sha((UPSTREAM / "generation_config.json").read_bytes()) or
        metadata["update_round"] != reference["training_progress"]["update_round"] or
        metadata["attempts_completed"] != reference["training_progress"]["attempts"] or
        metadata["optimizer_steps_completed"] != reference["training_progress"]["optimizer_steps"] or
        metadata["model"]["C"] != C or metadata["model"]["d"] != 128 or
        tuple(model.head.weight.shape) != (C, 128) or tuple(model.head.bias.shape) != (C,) or
        model.training or any(p.requires_grad or p.grad is not None or p.dtype != torch.float32 for p in model.parameters())):
        raise RuntimeError("frozen reference identity mismatch")
    config = json_file(UPSTREAM / "generation_config.json")
    transform = config["transforms"][reference["dataset"]]
    if transform["mean"] != list(NORMALIZATION[reference["dataset"]][0]) or transform["std"] != list(NORMALIZATION[reference["dataset"]][1]):
        raise RuntimeError("frozen transform mismatch")
    return model, metadata, before


def measure(reference, task, images, raw_labels, budget):
    budget.enter(reference["reference_id"])
    started = time.monotonic()
    model, metadata, before = identity(reference, task)
    ref_id, C = reference["reference_id"], task["info"]["spec"]["classes"]
    wp, bp = model.head.weight, model.head.bias
    wn, bn = wp.detach().cpu().numpy(), bp.detach().cpu().numpy()
    gradients, direct_sums, diagnostic_clients, records, comparisons = {}, {}, {}, [], []
    direct_sums = {c: [np.zeros((C, 128), np.float64), np.zeros(C, np.float64)] for c in range(C)}
    for i in range(20):
        client_started = time.monotonic()
        row = task["data"]["clients"][i]
        indices = row["train"]
        if row["id"] != f"client_{i:03d}" or len(indices) != task["acceptance"]["client_train_totals"][i]:
            raise RuntimeError("client identity/count mismatch")
        client = {"x": transform_images(images[indices], reference["dataset"]),
                  "y": torch.tensor(raw_labels[indices], dtype=torch.long), "indices": indices}
        budget.consume("client_scans")
        z, encode_seconds = timed(lambda: encode_client(model, client, budget, batch=128))
        z_np, y_np = z.detach().cpu().numpy(), client["y"].numpy()
        stats, stats_seconds = timed(lambda: feature_statistics(z, budget))
        n_ic = task["counts"]["n_ic"][i]
        actuals, golds, auxiliary = {}, {}, []
        head_seconds, independent_seconds = 0., 0.
        for c in range(C):
            positions = np.flatnonzero(y_np == c)
            budget.scan()
            if len(positions) != n_ic[c]:
                raise RuntimeError("sealed n_ic disagrees with training labels")
            if not len(positions):
                continue
            idx = torch.tensor(positions, device="cuda")
            labels = torch.full((len(positions),), c, dtype=torch.long, device="cuda")
            actual, cost = timed(lambda: full_class_gradient(z[idx], labels, wp, bp, budget, batch=128))
            head_seconds += cost
            t = time.monotonic()
            gold = analytic_gradient(z_np[positions], y_np[positions], wn, bn, budget)
            comparisons.append(compare(actual, gold, f"client_{i:03d}/class_{c}/main", budget))
            independent_sum = direct_class_sum(z_np[positions], c, wn, bn, budget)
            for j in range(2):
                direct_sums[c][j] += independent_sum[j]
            independent_seconds += time.monotonic() - t
            actuals[c], golds[c] = actual, gold
        active = sorted(actuals)
        if not active:
            raise RuntimeError("unexpected empty client")
        t = time.monotonic()
        for c in sorted({active[0], active[-1]}):
            positions = np.flatnonzero(y_np == c)[:8]
            idx = torch.tensor(positions, device="cuda")
            zs, ys = z[idx], torch.full((len(positions),), c, dtype=torch.long, device="cuda")
            batch = head_gradient(zs, ys, wp, bp, budget)
            individuals = [head_gradient(zs[j:j+1], ys[j:j+1], wp, bp, budget) for j in range(len(positions))]
            mean = tuple(np.mean([g[j].astype(np.float64) for g in individuals], axis=0) for j in range(2))
            cpu = head_gradient(zs.cpu(), ys.cpu(), wp.cpu(), bp.cpu(), budget)
            analytic = analytic_gradient(z_np[positions], y_np[positions], wn, bn, budget)
            for value, gold, name in ((batch, mean, "batch-vs-singletons"), (batch, cpu, "CUDA-vs-CPU"),
                                      (batch, analytic, "aux-vs-analytic")):
                comparisons.append(compare(value, gold, f"client_{i:03d}/class_{c}/{name}", budget))
            auxiliary.append({"class_id": c, "sample_positions": positions.tolist(),
                              "global_train_indices": [indices[j] for j in positions]})
        aux_seconds = time.monotonic() - t
        absent = [c for c in range(C) if c not in actuals]
        packet = {"reference_id": ref_id, "state_sha256": before, "client_id": i,
                  "C": C, "d": 128, "bias": True, "class_ids": active, "missing_class_ids": absent,
                  "denominators": {c: n_ic[c] for c in active}, "gradients": actuals,
                  "layout": "gradients[class_id][0]=C*128 weight, [1]=C bias; float32"}
        t = time.monotonic()
        message = save(f"messages/{ref_id}/client_{i:03d}.pt", packet, budget)
        restored = torch.load(OUTPUT / message["path"], weights_only=True)
        if restored["class_ids"] != active or restored["missing_class_ids"] != absent:
            raise RuntimeError("message readback mask mismatch")
        for c in active:
            if any(not np.array_equal(restored["gradients"][c][j].numpy(), actuals[c][j]) for j in range(2)):
                raise RuntimeError("message readback values mismatch")
        payload = len(active)*C*129*4
        downlink = (UPSTREAM / reference["checkpoint_path"]).stat().st_size
        budget.consume("logical_copy_bytes", message["bytes"] + downlink)
        diagnostic_clients[i] = {"features_float32": z_np, "labels": y_np, "global_train_indices": indices,
                                 "analytic_class_means_float64": golds, "auxiliary_sample_selection": auxiliary}
        gradients[i] = actuals
        records.append({"client_id": i, "sample_count": len(indices), "positive_class_count": len(active),
                        "missing_class_ids": absent, "message": message, "feature_statistics": stats,
                        "payload_bytes": payload, "metadata_and_container_bytes": message["bytes"]-payload,
                        "theoretical_reference_downlink_bytes": downlink,
                        "cost_seconds": {"encode": encode_seconds, "main_head": head_seconds,
                                         "statistics": stats_seconds, "independent_numpy": independent_seconds,
                                         "auxiliary_checks": aux_seconds, "message_save_read": time.monotonic()-t},
                        "client_elapsed_seconds": time.monotonic()-client_started})
        budget.progress = {"reference": ref_id, "last_client": i, "completed_main_records": sum(len(g) for g in gradients.values())}
        budget.save()
        del client, z, restored
    t = time.monotonic()
    targets, provenance = aggregate(gradients, task["counts"]["n_ic"], task["counts"]["N_c"], C, budget)
    direct = {c: tuple(p/task["counts"]["N_c"][c] for p in direct_sums[c]) for c in range(C)}
    for c in range(C):
        comparisons.append(compare(targets[c], direct[c], f"class_{c}/Gc", budget))
    G = tuple(sum(targets[c][j] for c in range(C))/C for j in range(2))
    independent_G = tuple(sum(direct[c][j] for c in range(C))/C for j in range(2))
    comparisons.append(compare(G, independent_G, "equal_class_G", budget))
    target_seconds = time.monotonic()-t
    after = tensor_state_sha(model.state_dict())
    repeated, repeat_metadata = restore_candidate(UPSTREAM / reference["checkpoint_path"], "cpu")
    repeated_hash = tensor_state_sha(repeated.state_dict())
    if after != before or repeated_hash != before or repeat_metadata != metadata or any(p.grad is not None for p in model.parameters()):
        raise RuntimeError("frozen parameters/BN/repeated read changed")
    t = time.monotonic()
    diagnostic = save(f"diagnostics/{ref_id}.pt", {"clients": diagnostic_clients, "G_c": targets,
        "independent_G_c": direct, "G": G, "independent_G": independent_G,
        "weight_float32": wn, "bias_float32": bn}, budget)
    point = {"reference_id": ref_id, "dataset": reference["dataset"], "clients": records,
             "comparisons": comparisons, "provenance": provenance, "diagnostic": diagnostic,
             "state_before": before, "state_after": after, "state_repeated_read": repeated_hash,
             "no_parameter_grad_or_update": True, "main_records": sum(len(g) for g in gradients.values()),
             "sample_count": sum(row["sample_count"] for row in records),
             "target_aggregation_comparison_seconds": target_seconds,
             "diagnostic_save_seconds": time.monotonic()-t, "reference_elapsed_seconds": time.monotonic()-started,
             "locator": "messages/<reference>/client_NNN.pt: gradients[class_id][0/1]; diagnostics/<reference>.pt: clients[id], G_c[class_id], independent_G_c[class_id], G, independent_G"}
    del model, repeated
    return point


def selfchecks(budget):
    results = {}
    for name, function in (("test_direction_a_class_gradient_smoke", "run_oracles"),
                           ("test_direction_a_class_gradient_full", "run_checks")):
        spec = importlib.util.spec_from_file_location(name, ROOT / "tests" / (name + ".py"))
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        results[name] = getattr(module, function)(budget)
    return results


def archive(budget):
    """Finalize a noncircular index including the final ledger; charge before hashing."""
    files = {p.relative_to(OUTPUT).as_posix(): sha(p.read_bytes()) for p in OUTPUT.rglob("*")
             if p.is_file() and p.name not in ("artifact_hashes.json", "run_record.json")}
    value = {"algorithm": "SHA-256 file bytes", "files": {**files, "run_record.json": "0"*64},
             "excluded": ["artifact_hashes.json (self)"]}
    size = len(encode(value))
    budget.consume("evidence_bytes", size)
    budget.check()
    budget.save()
    value["files"]["run_record.json"] = sha(budget.path.read_bytes())
    raw = encode(value)
    assert len(raw) == size
    (OUTPUT / "artifact_hashes.json").write_bytes(raw)


def main():
    if Path(sys.executable).resolve() != Path(r"E:\anaconda3\python.exe").resolve():
        raise RuntimeError("required interpreter mismatch")
    if OUTPUT.exists():
        raise RuntimeError("existing full-run evidence directory: no reset or rerun")
    budget = FullBudget(OUTPUT / "run_record.json", LIMITS, PROGRAM_STARTED)
    stop = threading.Event()
    def monitor():
        while not stop.wait(.2):
            try:
                budget.check()
            except PreparationLimit:
                os._exit(124)
    thread = threading.Thread(target=monitor, daemon=True); thread.start()
    points, accepted = [], []
    try:
        head = git("rev-parse", "HEAD").decode().strip()
        git("merge-base", "--is-ancestor", BASE, "HEAD")
        manifest = json_file(UPSTREAM / "manifest.json")
        prereg = {"run_id": "FedPCC-G1.2-full-measurement-v1", "input_commit": head, "baseline_commit": BASE,
                  "started_at": now(), "limits": LIMITS, "references": manifest["references"],
                  "contracts": {p: sha((ROOT/p).read_bytes()) for p in
                      ("docs/workflow/TO_EXECUTOR.md", "docs/DIRECTION_A_PROTOCOL_FREEZE_v1.md", "docs/DIRECTION_A_G1_2_ADJUDICATION_v1.md")},
                  "source_fingerprints": {p: sha((ROOT/p).read_bytes()) for p in SOURCE_PATHS},
                  "scan_plan": {"client_ids": list(range(20)), "client_scans": 80, "encoded_positions": 41838,
                                "extra_encoding": 0, "CIFAR10_per_point": [11165, 85], "CIFAR100_per_point": [9754, 593],
                                "main_records": 1356, "G_c": 220, "encode_chunk": 128, "head_chunk": 128},
                  "definitions": {"mode": "eval, float32, pure sum CE; CPU float64 chunk accumulation/n_ic -> float32",
                                  "epsilon": 2e-6, "norm": "joint weight+bias Linf / max(1, reference Linf)",
                                  "G_c": "sum_i n_ic/N_c * client class mean", "G": "equal-class mean of G_c",
                                  "oracle": "NumPy float64 class means; separate individual outer-product sums/N_c",
                                  "noise": "no within-client subsampling; auxiliary <=8 first samples of min/max present class"},
                  "resource_estimate": {"seconds": 180, "evidence_bytes_including_reserve": 264000000,
                                        "logical_bytes": 100000000, "gpu_bytes": 1024**3,
                                        "windows_working_set_bytes": 3*1024**3, "cpu_proxy_bytes": 1900000000,
                                        "basis": "sealed counts, complete head array sizes; 14 MB envelope for metadata/serialization/cumulative ledgers; old smoke scaling"},
                  "old_costs": {"original": "artifacts/direction_a/phaseG1_2_smoke_v1/run_record.json",
                                "continuation": "artifacts/direction_a/phaseG1_2_smoke_v1/resume_run_record.json",
                                "C100_r80_old_per_client_timing": None, "reason": "lost in old terminated process; never reconstructed"}}
        budget.write(OUTPUT / "preregistration.json", prereg)
        for field, key in (("wall_seconds", "seconds"), ("evidence_bytes", "evidence_bytes_including_reserve"),
                           ("logical_copy_bytes", "logical_bytes"), ("gpu_allocated_bytes", "gpu_bytes"),
                           ("windows_peak_working_set_bytes", "windows_working_set_bytes"), ("cpu_tensor_proxy_bytes", "cpu_proxy_bytes")):
            if prereg["resource_estimate"][key] >= LIMITS[field]:
                budget.stop("estimated_" + field, prereg["resource_estimate"][key])
        if not torch.cuda.is_available():
            raise RuntimeError("CUDA unavailable")
        environment = {"python": sys.version, "torch": torch.__version__, "numpy": np.__version__,
                       "cuda_runtime": torch.version.cuda, "GPU": torch.cuda.get_device_name(),
                       "CPU_threads": 2, "deterministic_algorithms": True, "TF32": False, "cudnn_benchmark": False}
        old = json_file(ROOT / "artifacts/direction_a/phaseG1_2_smoke_v1/environment.json")
        if any(environment[k] != old[k] for k in environment) or platform.python_version() != "3.12.8":
            raise RuntimeError("frozen environment mismatch")
        torch.set_num_threads(2); torch.use_deterministic_algorithms(True)
        torch.backends.cuda.matmul.allow_tf32 = False; torch.backends.cudnn.allow_tf32 = False
        torch.backends.cudnn.benchmark = False
        budget.write(OUTPUT / "environment.json", environment)
        tasks, manifest, binding, unchanged = verify_inputs(budget)
        for ds, samples, positive in (("CIFAR10", 11165, 85), ("CIFAR100", 9754, 593)):
            task = tasks[ds]
            if sum(task["counts"]["N_c"]) != samples or sum(n > 0 for row in task["counts"]["n_ic"] for n in row) != positive:
                raise RuntimeError("sealed full-population count mismatch")
        budget.enter("selfchecks")
        budget.write(OUTPUT / "selfchecks.json", selfchecks(budget))
        budget.consume("formal_runs")
        budget.planned_references = [r["reference_id"] for r in manifest["references"]]
        inputs = {}
        for ds in ("CIFAR10", "CIFAR100"):
            budget.enter("input")
            images, labels, inputs[ds] = load_raw(tasks[ds], budget)
            for ref in [r for r in manifest["references"] if r["dataset"] == ds]:
                point = measure(ref, tasks[ds], images, labels, budget)
                points.append(point)
                accepted.append({"reference": ref, "binding": binding[ds], "state_before": point["state_before"],
                    "state_after": point["state_after"], "repeated_read": point["state_repeated_read"],
                    "no_parameter_grad_or_update": True, "transform": json_file(UPSTREAM / "generation_config.json")["transforms"][ds],
                    "generation_record": f"artifacts/direction_a/backbone_preparation_v1/runs/{ds}_run_record.json",
                    "validation_record": {"path": "artifacts/direction_a/backbone_preparation_v1/validation_record.json",
                                          "reference_id": ref["reference_id"]}})
                budget.delivered_references.append(ref["reference_id"])
                budget.save()
                print(f"completed {ref['reference_id']}: {point['main_records']} main records", flush=True)
                gc.collect()
            del images, labels
        budget.enter("storage")
        assert budget.counts["client_scans"] == 80 and budget.counts["feature_samples"] == 41838
        assert sum(p["main_records"] for p in points) == 1356
        assert sum(len(p["provenance"]) for p in points) == 220
        for path, digest in {**unchanged, **prereg["source_fingerprints"], **prereg["contracts"]}.items():
            if sha((ROOT/path).read_bytes()) != digest:
                raise RuntimeError("input/source changed during run: " + path)
        budget.write(OUTPUT / "reference_acceptance.json", {"references": accepted, "verified_inputs": unchanged,
                     "original_snapshots_referenced_without_copy": True})
        budget.write(OUTPUT / "measurements.json", {"run_id": prereg["run_id"], "references": points,
                     "main_record_count": 1356, "G_c_count": 220, "message_count": 80})
        costs = {key: sum(c["cost_seconds"][key] for p in points for c in p["clients"]) for key in points[0]["clients"][0]["cost_seconds"]}
        budget.write(OUTPUT / "W02_measurement.json", {"frozen_protocol": prereg["definitions"], "cost_seconds": costs,
                     "input_sources": inputs, "client_scans": 80, "encoded_positions": 41838,
                     "within_client_sampling_noise": "none", "encode_head_chunk": 128,
                     "tensor_payload_bytes": sum(c["payload_bytes"] for p in points for c in p["clients"]),
                     "metadata_container_bytes": sum(c["metadata_and_container_bytes"] for p in points for c in p["clients"]),
                     "theoretical_reference_downlink_bytes": sum(c["theoretical_reference_downlink_bytes"] for p in points for c in p["clients"]),
                     "diagnostic_disk_bytes": sum(p["diagnostic"]["bytes"] for p in points),
                     "diagnostic_storage_seconds": sum(p["diagnostic_save_seconds"] for p in points),
                     "target_seconds": sum(p["target_aggregation_comparison_seconds"] for p in points),
                     "network": "single host; no actual network; logical uploads=message file bytes, downlink=checkpoint file bytes per client",
                     "old_costs": prereg["old_costs"], "ownership": "G1.2 full diagnosis; not free downstream estimator input"})
        budget.write(OUTPUT / "P_plan.md", (ROOT / "scripts/direction_a_P_plan.md").read_bytes(), raw=True)
        maximum = max(c["normalized_Linf"] for p in points for c in p["comparisons"])
        budget.write(OUTPUT / "decision.json", {"checkpoint": "G1.2", "run_id": prereg["run_id"],
                     "criteria": {str(i): "PASS" for i in range(1, 8)}, "fail_count": 0, "blocked": False,
                     "executor_self_assessment": True, "reviewer_acceptance_pending": True,
                     "maximum_normalized_Linf": maximum, "no_P_or_source_bias_or_method_benefit_claim": True})
        budget.status = "completed_G1.2_executor_self_assessment_PASS"
        budget.progress = {"completed_references": 4, "main_records": 1356, "G_c": 220}
        stop.set(); thread.join()
        archive(budget)
        print(json.dumps({"status": budget.status, "counts": budget.counts, "elapsed_seconds": budget.snapshot()["elapsed_seconds"],
                          "maximum_error": maximum}), flush=True)
    except BaseException as error:
        stop.set(); thread.join()
        if not isinstance(error, PreparationLimit):
            budget.status = "blocked_full_measurement"
            budget.progress["error"] = f"{type(error).__name__}: {error}"
            budget.save(reserved=True)
        # Preserve completed packets and counters. No experiment retry is permitted.
        raise


if __name__ == "__main__":
    main()
