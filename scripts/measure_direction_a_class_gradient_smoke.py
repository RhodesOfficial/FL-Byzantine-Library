"""Run only the explicitly authorized first segment of G1.2."""

import importlib.util
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

PROGRAM_STARTED = time.monotonic()
os.environ["CUBLAS_WORKSPACE_CONFIG"] = ":4096:8"
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.dont_write_bytecode = True

import numpy as np
import torch

from direction_a.backbone_preparation import (PreparationLimit, read_task, resource_sample,
                                             restore_candidate, sha, tensor_state_sha, watchdog)
from direction_a.class_gradient_smoke import (SmokeBudget, analytic_gradient, compare_gradient,
    encode_client, epsilon_candidate, feature_statistics, full_class_gradient, head_gradient,
    save_tensors, selected_images, timed, to_tensors, weighted_partial)

oracle_spec = importlib.util.spec_from_file_location("gradient_smoke_oracles", ROOT / "tests/test_direction_a_class_gradient_smoke.py")
oracle_module = importlib.util.module_from_spec(oracle_spec)
oracle_spec.loader.exec_module(oracle_module)
run_oracles = oracle_module.run_oracles

OUTPUT = ROOT / "artifacts/direction_a/phaseG1_2_smoke_v1"
UPSTREAM = ROOT / "artifacts/direction_a/backbone_preparation_v1"
PREREG = ROOT / "docs/DIRECTION_A_G1_2_SMOKE_RUN_RECORD_v1.md"
SELECTED = [0, 9, 19]
LIMITS = {"attempts": 1, "optimizer_steps": 1, "retries": 1, "backwards": 2000,
          "forwards": 3000, "scans": 1000, "feature_samples": 12000, "class_gradient_requests": 1000,
          "evidence_bytes": 64 * 1024**2, "logical_copy_bytes": 64 * 1024**2,
          "gpu_allocated_bytes": 6 * 1024**3, "windows_peak_working_set_bytes": 6 * 1024**3,
          "cpu_tensor_proxy_bytes": 2 * 1024**3, "wall_seconds": 600, "per_run": {},
          "phase_seconds": {"input": 90, "oracles": 60, "storage": 90, **{f"reference_{i}": 90 for i in range(4)}}}


def now():
    return datetime.now(ZoneInfo("Asia/Shanghai")).isoformat()


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT)


def json_file(path):
    return json.loads(Path(path).read_bytes())


def verify_inputs(budget):
    budget.enter("input")
    manifest, binding = json_file(UPSTREAM / "manifest.json"), json_file(UPSTREAM / "task_binding.json")
    config = json_file(UPSTREAM / "generation_config.json")
    inventory, validation = json_file(UPSTREAM / "artifact_hashes.json"), json_file(UPSTREAM / "validation_record.json")
    expected = set(inventory["files"]) | {"artifact_hashes.json", "run_record.json"}
    if {str(p.relative_to(UPSTREAM)).replace("\\", "/") for p in UPSTREAM.rglob("*") if p.is_file()} != expected:
        raise RuntimeError("candidate package file set changed")
    evidence = {}
    for name in sorted(expected):
        budget.scan()
        path = UPSTREAM / name
        raw = path.read_bytes()
        digest = sha(raw)
        if name in inventory["files"] and digest != inventory["files"][name]:
            raise RuntimeError("candidate file hash mismatch: " + name)
        relative = str(path.relative_to(ROOT)).replace("\\", "/")
        if raw != git("show", "HEAD:" + relative):
            raise RuntimeError("candidate working/Git bytes mismatch: " + name)
        evidence[relative] = digest
    for path, record in config["implementation_fingerprints"].items():
        if sha((ROOT / path).read_bytes()) != record["working_bytes_sha256"]:
            raise RuntimeError("candidate implementation changed: " + path)
    tasks = {}
    for dataset in ("CIFAR10", "CIFAR100"):
        bound = binding[dataset]
        baseline = {"tasks/" + bound["task_identity"] + "/" + name: row["sha256"]
                    for name, row in bound["source_files"].items()}
        task = read_task(ROOT / bound["task_directory"], baseline, budget, ROOT)
        if task["counts"]["class_groups"] != bound["class_groups"] or task["counts"]["tail_holding_clients"] != bound["tail_holding_clients"]:
            raise RuntimeError("frozen group/source identity changed")
        if task["info"]["actual_training_if"] != bound["actual_training_IF"]:
            raise RuntimeError("IF binding changed")
        tasks[dataset] = task
        evidence.update({row["path"]: row["sha256"] for row in task["source_records"].values()})
    ids = [f"A-backbone-{ds}-s{seed}-r{r:04d}-v1" for ds, seed in
           (("CIFAR10", 2026101321), ("CIFAR100", 2026101322)) for r in (40, 80)]
    if [ref["reference_id"] for ref in manifest["references"]] != ids:
        raise RuntimeError("preselected four-reference plan changed")
    for reference in manifest["references"]:
        vals = [r for r in validation["records"] if r["reference_id"] == reference["reference_id"]]
        if len(vals) != 1:
            raise RuntimeError("candidate validation correspondence missing")
    docs = ["DIRECTION_A_CHECKPOINTS_v1.md", "DIRECTION_A_PROTOCOL_FREEZE_v1.md",
            "DIRECTION_A_BACKBONE_CANDIDATE_ADJUDICATION_v1.md", "DIRECTION_A_BACKBONE_PREPARATION_HANDOFF_v1.md"]
    evidence.update({"docs/" + name: sha((ROOT / "docs" / name).read_bytes()) for name in docs})
    return tasks, manifest, binding, evidence


def measure_reference(reference, task, clients, budget, index):
    budget.enter(f"reference_{index}")
    path, C = UPSTREAM / reference["checkpoint_path"], task["info"]["spec"]["classes"]
    model, metadata = restore_candidate(path, "cuda")
    before = tensor_state_sha(model.state_dict())
    if before != reference["state_sha256"] or sha(path.read_bytes()) != reference["checkpoint_file_sha256"]:
        raise RuntimeError("checkpoint state/file mismatch")
    if (metadata["reference_id"] != reference["reference_id"] or metadata["task_identity"] != task["identity"] or
        metadata["task_source_sha256"] != {name: row["sha256"] for name, row in task["source_records"].items()} or
        metadata["generation_config_sha256"] != sha((UPSTREAM / "generation_config.json").read_bytes()) or
        metadata["model"]["C"] != C or metadata["model"]["d"] != 128 or
        tuple(model.head.weight.shape) != (C, 128) or tuple(model.head.bias.shape) != (C,) or
        model.training or any(p.requires_grad for p in model.parameters())):
        raise RuntimeError("actual loaded model/head/task/mode mismatch")
    ref_id = reference["reference_id"]
    wp, bp = model.head.weight, model.head.bias
    wn, bn = wp.detach().cpu().numpy(), bp.detach().cpu().numpy()
    all_gradients, features, records, comparisons, diagnostics = {}, {}, [], [], {}
    partial_cost = {"encode_seconds": 0., "head_class_gradient_seconds": 0., "feature_statistics_seconds": 0.,
                    "independent_oracle_smoke_seconds": 0., "message_save_readback_seconds": 0.}
    point_start = time.perf_counter()
    for i in SELECTED:
        client, n_ic = clients[i], task["counts"]["n_ic"][i]
        z, encode_seconds = timed(lambda: encode_client(model, client, budget))
        z_np, y_np = z.detach().cpu().numpy(), client["y"].numpy()
        stats, stats_seconds = timed(lambda: feature_statistics(z, budget))
        features[i] = (z_np, y_np)
        gradients, gold, absent, client_comparisons, small_smoke = {}, {}, [], [], []
        head_seconds, independent_seconds = 0., 0.
        for c in range(C):
            positions = np.flatnonzero(y_np == c)
            if len(positions) != n_ic[c]:
                raise RuntimeError("selected train labels disagree with sealed n_ic; stop without recounting")
            if n_ic[c] == 0:
                absent.append(c)
                continue
            idx = torch.tensor(positions, dtype=torch.long, device="cuda")
            labels = torch.full((len(positions),), c, dtype=torch.long, device="cuda")
            actual, cost = timed(lambda: full_class_gradient(z[idx], labels, wp, bp, budget))
            head_seconds += cost
            start = time.perf_counter()
            gold[c] = analytic_gradient(z_np[positions], y_np[positions], wn, bn, budget)
            gradients[c] = actual
            client_comparisons.append(compare_gradient(actual, gold[c], f"{ref_id}/client_{i:03d}/class_{c}/full-vs-analytic", budget))
            independent_seconds += time.perf_counter() - start
        active = sorted(gradients)
        chosen = sorted(set([active[0], active[-1]]))
        for c in chosen:
            start = time.perf_counter()
            positions = np.flatnonzero(y_np == c)[:8]
            idx = torch.tensor(positions, dtype=torch.long, device="cuda")
            zs, ys = z[idx], torch.full((len(positions),), c, dtype=torch.long, device="cuda")
            batch_mean = head_gradient(zs, ys, wp, bp, budget)
            individuals = [head_gradient(zs[j:j+1], ys[j:j+1], wp, bp, budget) for j in range(len(positions))]
            singleton_mean = tuple(np.mean([row[k].astype(np.float64) for row in individuals], axis=0) for k in (0, 1))
            cpu = head_gradient(zs.cpu(), ys.cpu(), wp.cpu(), bp.cpu(), budget)
            oracle = analytic_gradient(z_np[positions], y_np[positions], wn, bn, budget)
            for actual, reference_gradient, name in ((batch_mean, singleton_mean, "batch-vs-singletons"),
                                                   (batch_mean, oracle, "batch-vs-analytic"),
                                                   (batch_mean, cpu, "CUDA-vs-CPU")):
                client_comparisons.append(compare_gradient(actual, reference_gradient, f"{ref_id}/client_{i:03d}/class_{c}/"+name, budget))
            small_smoke.append({"class_id": c, "sample_positions": positions.tolist(), "global_train_indices": [client["indices"][j] for j in positions],
                                "features_float32": z_np[positions], "batch_mean": batch_mean,
                                "singleton_mean": singleton_mean, "CPU_float32": cpu, "analytic_float64": oracle})
            independent_seconds += time.perf_counter() - start
        all_gradients[i] = gradients
        packet = {"reference_id": ref_id, "state_sha256": before, "client_id": f"client_{i:03d}",
                  "scope": "first-segment diagnostic ONLY, not formal class-gradient acceptance",
                  "C": C, "d": 128, "bias": True, "head_parameter_names": ["linear.weight", "linear.bias"],
                  "missing_class_ids": absent, "gradient_class_ids": active,
                  "gradient_sample_denominators": {c: n_ic[c] for c in active},
                  "gradients": {c: {"linear.weight": actual[0], "linear.bias": actual[1]} for c, actual in gradients.items()}}
        start = time.perf_counter()
        message = save_tensors(OUTPUT / "messages" / ref_id / f"client_{i:03d}.pt", to_tensors(packet), budget)
        restored = torch.load(message["path"], weights_only=True)
        if restored["gradient_class_ids"] != active or restored["missing_class_ids"] != absent:
            raise RuntimeError("smoke message source mask mismatch")
        for c in active:
            if (not np.array_equal(restored["gradients"][c]["linear.weight"].numpy(), gradients[c][0]) or
                not np.array_equal(restored["gradients"][c]["linear.bias"].numpy(), gradients[c][1])):
                raise RuntimeError("gradient message readback changed values")
        saved_seconds = time.perf_counter() - start
        message["path"] = str(Path(message["path"]).relative_to(OUTPUT)).replace("\\", "/")
        theory = len(active) * C * (128 + 1) * 4
        budget.consume("logical_copy_bytes", message["bytes"] + path.stat().st_size)
        records.append({"client_id": f"client_{i:03d}", "sealed_sample_count": len(y_np),
                        "positive_class_count": len(active), "missing_class_ids": absent, "feature_statistics": stats,
                        "feature_forwards": (len(y_np) + 127) // 128, "gradient_mode": "complete selected-client train per class",
                        "sampling_noise": "none for complete selected-client class; global 17 omitted clients not represented",
                        "scan_frequency": "one encode scan per selected client per reference, no periodic event binding",
                        "message": message, "gradient_tensor_payload_bytes": theory,
                        "reference_downlink_theoretical_file_bytes": path.stat().st_size,
                        "encode_seconds": encode_seconds, "class_head_gradient_seconds": head_seconds,
                        "feature_statistics_seconds": stats_seconds, "independent_oracle_smoke_seconds": independent_seconds,
                        "message_save_readback_seconds": saved_seconds})
        for key, value in (('encode_seconds', encode_seconds), ('head_class_gradient_seconds', head_seconds),
                           ('feature_statistics_seconds', stats_seconds), ('independent_oracle_smoke_seconds', independent_seconds),
                           ('message_save_readback_seconds', saved_seconds)):
            partial_cost[key] += value
        comparisons.extend(client_comparisons)
        diagnostics[i] = {"features_float32": z_np, "labels": y_np, "global_train_indices": client["indices"],
                          "analytic_gradients_float64": gold, "small_sample_smoke": small_smoke}
        resource_sample(budget)
        print(f"measured {ref_id} client_{i:03d}: samples={len(y_np)}, classes={len(active)}, missing={len(absent)}", flush=True)
    start = time.perf_counter()
    partial = weighted_partial(all_gradients, task["counts"]["n_ic"], task["counts"]["N_c"], C, 128)
    partial_references = {}
    for c in range(C):
        relevant = [features[i][0][features[i][1] == c] for i in SELECTED if c in all_gradients[i]]
        if relevant:
            combined = np.concatenate(relevant)
            oracle = analytic_gradient(combined, np.full(len(combined), c), wn, bn, budget)
            direct = tuple(g * len(combined) / task["counts"]["N_c"][c] for g in oracle)
        else:
            direct = (np.zeros((C, 128), np.float64), np.zeros(C, np.float64))
        partial_references[c] = direct
        comparisons.append(compare_gradient((partial[c]["weight"], partial[c]["bias"]), direct,
                                            f"{ref_id}/class_{c}/partial-weighted-vs-direct", budget))
    partial_cost["partial_target_diagnostic_seconds"] = time.perf_counter() - start
    after = tensor_state_sha(model.state_dict())
    repeated, repeated_metadata = restore_candidate(path, "cpu")
    if after != before or repeated.state_identity() != before or repeated_metadata != metadata or any(p.grad is not None for p in model.parameters()):
        raise RuntimeError("reference parameters/buffers or repeat-read identity changed")
    diagnostics.update(partial_contributions=partial, independent_partial_reference=partial_references,
                       weight_float32=wn, bias_float32=bn)
    diagnostic = save_tensors(OUTPUT / "diagnostics" / f"{ref_id}.pt", to_tensors(diagnostics), budget)
    diagnostic["path"] = str(Path(diagnostic["path"]).relative_to(OUTPUT)).replace("\\", "/")
    return {"reference_id": ref_id, "dataset": reference["dataset"], "checkpoint_file_sha256": reference["checkpoint_file_sha256"],
            "state_sha256_before": before, "state_sha256_after": after, "repeated_read_state_sha256": repeated.state_identity(),
            "actual_loaded_identity_checked": True, "complete_C_bias": True, "no_parameter_grad_or_update": True,
            "formal_qualification": "NOT_decided_in_segment_1", "clients": records, "comparisons": comparisons,
            "diagnostic_tensor_file": diagnostic, "costs": partial_cost,
            "reference_elapsed_seconds": time.perf_counter() - point_start, "resources": resource_sample(budget)}


def main():
    if Path(sys.executable).resolve() != Path(r"E:\anaconda3\python.exe").resolve():
        raise RuntimeError("use the explicitly required interpreter")
    if (OUTPUT / "run_record.json").exists():
        raise RuntimeError("existing smoke ledger: no rerun or counter reset authorized")
    budget = SmokeBudget(OUTPUT / "run_record.json", LIMITS)
    budget.started = budget.phase_started = PROGRAM_STARTED
    watchdog(budget)
    started = now()
    try:
        original_prereg = PREREG.read_bytes()
        budget.write(OUTPUT / "preregistration.md", original_prereg, raw=True)
        source_paths = ["direction_a/class_gradient_smoke.py", "scripts/measure_direction_a_class_gradient_smoke.py",
                        "tests/test_direction_a_class_gradient_smoke.py", "direction_a/model.py", "models/ResNet.py",
                        "direction_a/backbone_preparation.py"]
        config = {"run_id": "FedPCC-G1.2-gradient-smoke-v1", "parent_checkpoint": "G1.2", "segment": 1,
                  "base_commit": git("rev-parse", "HEAD").decode().strip(), "selected_clients": SELECTED, "limits": LIMITS,
                  "preregistration_sha256": sha(original_prereg), "interpreter": sys.executable,
                  "source_fingerprints": {p: sha((ROOT / p).read_bytes()) for p in source_paths},
                  "head_batch": 128, "precision": "CUDA float32 autograd; NumPy float64 head reference on same cached float32 features",
                  "sampling": "complete train per selected client; auxiliary smoke <=8 samples/class, extreme positive class IDs",
                  "epsilon_rule": "max(8*float32 epsilon,4*maximum normalized difference), decimal significant ceil",
                  "debug_bound_only_not_frozen_epsilon": 1e-4, "training_updates": 0, "optimizer_steps": 0,
                  "tensor_readback": "bitwise exact", "gradients": "complete C outputs, bias present; no regularization",
                  "target_scope": "selected sources partial contribution, NOT full G_c",
                  "cost_ownership": "new G1.2 smoke/W02 measurement subaccount; earlier preparation and G1.1 ledger retained separately",
                  "network": "no network; local message bytes measured and reference downlink theoretical",
                  "not_authorized": ["formal G1.2 qualification", "epsilon freeze", "full-population formal gradient/target package",
                                     "P", "G1.3", "A1/A2/A3", "A7/A8", "FedAvg training"]}
        budget.write(OUTPUT / "measurement_config.json", config)
        if not torch.cuda.is_available() or not torch.__version__.startswith("2.5.1"):
            raise RuntimeError("declared PyTorch 2.5.1/CUDA environment mismatch")
        torch.set_num_threads(2)
        torch.use_deterministic_algorithms(True)
        torch.backends.cuda.matmul.allow_tf32 = False
        torch.backends.cudnn.allow_tf32 = False
        torch.backends.cudnn.benchmark = False
        budget.write(OUTPUT / "environment.json", {"torch": torch.__version__, "numpy": np.__version__, "cuda_runtime": torch.version.cuda,
                    "GPU": torch.cuda.get_device_name(), "CPU_threads": 2, "deterministic_algorithms": True,
                    "TF32": False, "cudnn_benchmark": False, "python": sys.version, "started_at": started})
        tasks, manifest, binding, unchanged = verify_inputs(budget)
        budget.write(OUTPUT / "reception_identity_check.json", {"status": "candidate_package_receivable_identity_only",
                    "upstream_files_and_tasks": unchanged, "all_four_preselected_references": manifest["references"],
                    "candidate_adjudication": "docs/DIRECTION_A_BACKBONE_CANDIDATE_ADJUDICATION_v1.md §三",
                    "missing_input_items": [], "formal_reference_qualification": "NOT_decided", "training_or_validation_repeated": False,
                    "history": "generation contract hash remains historical; current successor contract recorded separately"})
        budget.enter("oracles")
        oracles = run_oracles(budget)
        budget.write(OUTPUT / "independent_oracles.json", oracles)
        print("independent hand/scalar oracles passed; starting bounded real-candidate measurements", flush=True)
        points, inputs = [], {}
        for dataset in ("CIFAR10", "CIFAR100"):
            budget.enter("input")
            clients, input_record = selected_images(tasks[dataset], SELECTED, budget)
            inputs[dataset] = input_record
            for reference in [r for r in manifest["references"] if r["dataset"] == dataset]:
                points.append(measure_reference(reference, tasks[dataset], clients, budget, len(points)))
                budget.write(OUTPUT / "smoke_measurements.json", {"scope": "segment 1 only", "completed_references": points,
                            "missing_reference_ids": [r["reference_id"] for r in manifest["references"] if r["reference_id"] not in [p["reference_id"] for p in points]]})
                budget.save()
            del clients
        budget.enter("storage")
        comparisons = [row for point in points for row in point["comparisons"]]
        epsilon = epsilon_candidate(comparisons)
        epsilon["measurement_count"] = len(comparisons)
        epsilon["worst_comparison"] = max(comparisons, key=lambda row: row["normalized_Linf"])
        budget.write(OUTPUT / "epsilon_candidate.json", epsilon)
        w02 = {"status": "measured_segment_1_NOT_frozen", "references": [{k: p[k] for k in ("reference_id", "dataset", "clients", "costs", "resources")} for p in points],
               "input_source_loading": inputs, "sample_positions_encoded": budget.counts["feature_samples"],
               "full_selected_client_scans": len(points)*len(SELECTED), "C_and_d": "C=10/100,d=128,bias=True",
               "frequency": "one complete train scan per selected client per reference",
               "network_reason": "single-host diagnostic; no actual upload/download or registration, measured message encodings separate from theoretical reference copies",
               "missing_formal_work": "17 remaining clients per task/reference, full target, applicable W02/epsilon freeze and second-segment authorization"}
        budget.write(OUTPUT / "W02_measurement.json", w02)
        for relative, digest in unchanged.items():
            if sha((ROOT / relative).read_bytes()) != digest:
                raise RuntimeError("sealed input changed during measurement: " + relative)
        for relative, digest in config["source_fingerprints"].items():
            if sha((ROOT / relative).read_bytes()) != digest:
                raise RuntimeError("measurement implementation changed midrun: " + relative)
        budget.write(OUTPUT / "decision.json", {"checkpoint": "G1.2", "segment": 1, "smoke": "passed_with_candidate_numerical_basis",
                    "state": "证据不足/预算耗尽", "reason": "证据不足，未耗尽", "formal_pass": False,
                    "references_qualified": [], "references_disqualified": [], "reference_qualification_not_decided": True,
                    "epsilon_frozen": False, "W02_frozen": False, "missing": ["gradient epsilon adoption/freeze record",
                    "formal W02 protocol freeze", "subsequent authorization and full G1.2 formal measurements/diagnostic package"],
                    "limitations": ["3/20 clients only", "partial contribution is not full G_c", "four snapshots tail validation recall=0",
                                    "no representation/separability or downstream method conclusion", "no formal G1.1 upgrade"],
                    "started_at": started, "finished_at": now()})
        files = {str(p.relative_to(OUTPUT)).replace("\\", "/"): sha(p.read_bytes()) for p in OUTPUT.rglob("*")
                 if p.is_file() and p.name not in ("artifact_hashes.json", "run_record.json")}
        budget.write(OUTPUT / "artifact_hashes.json", {"algorithm": "SHA-256 actual bytes", "files": files,
                    "excluded": ["self", "run_record.json (final ledger; Git exact-byte verification separate)"]})
        budget.status = "segment_1_completed_formal_G1.2_evidence_insufficient"
        budget.save()
        print(json.dumps({"segment": 1, "smoke": "passed", "checkpoint_state": "evidence_insufficient_not_budget_exhausted",
                          "epsilon_candidate": epsilon["value"], "elapsed_seconds": budget.snapshot()["elapsed_seconds"],
                          "counts": budget.counts}, ensure_ascii=False), flush=True)
    except BaseException as error:
        if not isinstance(error, PreparationLimit):
            budget.status = "stopped_measurement_error"
            budget.progress["error"] = f"{type(error).__name__}: {error}"
            budget.save(reserved=True)
        raise


if __name__ == "__main__":
    main()
