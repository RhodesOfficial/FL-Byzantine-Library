"""Continue G1.2 segment 1 without rewriting any previously archived result.

Recovery of discarded fourth-point diagnostics requires explicit user scope.
"""

import argparse
import copy
import importlib.util
import json
import os
import sys
import threading
import time
from pathlib import Path

PROGRAM_STARTED = time.monotonic()
os.environ["CUBLAS_WORKSPACE_CONFIG"] = ":4096:8"
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.dont_write_bytecode = True

import numpy as np
import torch

from direction_a.backbone_preparation import PreparationLimit, resource_sample, restore_candidate, sha, tensor_state_sha, watchdog
from direction_a.class_gradient_smoke import (SmokeBudget, analytic_gradient, compare_gradient, encode_client,
    epsilon_candidate, feature_statistics, head_gradient, save_tensors, selected_images, timed, to_tensors, weighted_partial)

original_spec = importlib.util.spec_from_file_location("original_gradient_smoke", ROOT / "scripts/measure_direction_a_class_gradient_smoke.py")
original = importlib.util.module_from_spec(original_spec)
original_spec.loader.exec_module(original)
OUTPUT, SELECTED = original.OUTPUT, original.SELECTED
PREREG = ROOT / "docs/DIRECTION_A_G1_2_SMOKE_RESUME_RUN_RECORD_v1.md"


class ContinuedBudget(SmokeBudget):
    def __init__(self, old, old_sha, limits):
        # Initialize directly from the frozen ledger; never publish a zero counter.
        self.path, self.limits = OUTPUT / "resume_run_record.json", limits
        self.started = PROGRAM_STARTED - old["elapsed_seconds"]
        self.phase, self.phase_started = "resume_startup", PROGRAM_STARTED
        self.phase_seconds = copy.deepcopy(old["phase_seconds"])
        self.counts = copy.deepcopy(old["counts"])
        self.counts["evidence_bytes"] += self.reserve
        self.run_counts = copy.deepcopy(old["run_counts"])
        self.progress = {"scope": "missing-fourth-point diagnostics and final summaries ONLY"}
        self.planned_references = [row["reference_id"] for row in original.json_file(original.UPSTREAM / "manifest.json")["references"]]
        self.delivered_references = [row["reference_id"] for row in original.json_file(OUTPUT / "smoke_measurements.json")["completed_references"]]
        self.status, self.hit = "resuming_with_preserved_counters", None
        self.lock = threading.RLock()
        self.origin = {"path": "run_record.json", "sha256": old_sha, "old_counts": old["counts"],
                       "historical_hit": old["hit"], "historical_limits": old["limits"],
                       "old_elapsed_seconds": old["elapsed_seconds"], "additional_emergency_reserve_bytes": self.reserve}
        self.save()

    def snapshot(self, now=None):
        value = super().snapshot(now)
        value["continuation_from"] = self.origin
        value["additional_counts"] = {k: value["counts"][k] - self.origin["old_counts"].get(k, 0) for k in value["counts"]}
        value["additional_elapsed_seconds"] = value["elapsed_seconds"] - self.origin["old_elapsed_seconds"]
        return value


def audit_preserved(budget, config):
    budget.enter("resume_input")
    files = {str(path.relative_to(OUTPUT)).replace("\\", "/"): sha(path.read_bytes()) for path in OUTPUT.rglob("*") if path.is_file()
             and path.name not in ("resume_run_record.json",)}
    old_inventory = {name: digest for name, digest in files.items() if not name.startswith("resume_")}
    if len(old_inventory) != 22:
        raise RuntimeError("expected the exact 22 archived partial-result files")
    for path, digest in config["source_fingerprints"].items():
        if sha((ROOT / path).read_bytes()) != digest:
            raise RuntimeError("original measurement source changed: " + path)
    points = original.json_file(OUTPUT / "smoke_measurements.json")["completed_references"]
    for point in points:
        for row in point["clients"]:
            if sha((OUTPUT / row["message"]["path"]).read_bytes()) != row["message"]["sha256"]:
                raise RuntimeError("prior message hash changed")
        if sha((OUTPUT / point["diagnostic_tensor_file"]["path"]).read_bytes()) != point["diagnostic_tensor_file"]["sha256"]:
            raise RuntimeError("prior complete diagnostic hash changed")
    return old_inventory, points


def recover_fourth(reference, task, clients, budget, old):
    budget.enter("recover_missing_diagnostic")
    ref_id, C = reference["reference_id"], task["info"]["spec"]["classes"]
    path = original.UPSTREAM / reference["checkpoint_path"]
    model, metadata = restore_candidate(path, "cuda")
    before = tensor_state_sha(model.state_dict())
    if before != reference["state_sha256"] or sha(path.read_bytes()) != reference["checkpoint_file_sha256"]:
        raise RuntimeError("fourth checkpoint changed")
    if model.training or any(p.requires_grad for p in model.parameters()) or C != 100 or tuple(model.head.weight.shape) != (100, 128):
        raise RuntimeError("fourth reference model/readout identity mismatch")
    wp, bp = model.head.weight, model.head.bias
    wn, bn = wp.detach().cpu().numpy(), bp.detach().cpu().numpy()
    gradients, features, diagnostics, records, comparisons = {}, {}, {}, [], []
    recovery_cost = {"encode_seconds": 0., "feature_statistics_seconds": 0., "independent_reference_auxiliary_smoke_seconds": 0.,
                     "existing_message_read_seconds": 0.}
    for i in SELECTED:
        message_path = OUTPUT / "messages" / ref_id / f"client_{i:03d}.pt"
        start = time.perf_counter()
        packet = torch.load(message_path, weights_only=True)
        read_seconds = time.perf_counter() - start
        if (packet["reference_id"] != ref_id or packet["client_id"] != f"client_{i:03d}" or
            packet["state_sha256"] != before or packet["C"] != C or packet["d"] != 128 or packet["bias"] is not True):
            raise RuntimeError("fourth saved primary message identity mismatch")
        n_ic = task["counts"]["n_ic"][i]
        active = [c for c in range(C) if n_ic[c] > 0]
        absent = [c for c in range(C) if n_ic[c] == 0]
        if packet["gradient_class_ids"] != active or packet["missing_class_ids"] != absent:
            raise RuntimeError("fourth saved source mask mismatch")
        by_class = {}
        for c in active:
            gw, gb = packet["gradients"][c]["linear.weight"], packet["gradients"][c]["linear.bias"]
            if (tuple(gw.shape) != (C, 128) or tuple(gb.shape) != (C,) or gw.dtype != torch.float32 or gb.dtype != torch.float32 or
                packet["gradient_sample_denominators"][c] != n_ic[c] or not torch.isfinite(gw).all() or not torch.isfinite(gb).all()):
                raise RuntimeError("fourth saved complete-head gradient invalid")
            by_class[c] = (gw.numpy(), gb.numpy())
        gradients[i] = by_class
        # The full class gradients above are reused, not recomputed or rewritten.
        z, encode_seconds = timed(lambda: encode_client(model, clients[i], budget))
        z_np, labels_np = z.cpu().numpy(), clients[i]["y"].numpy()
        stats, stats_seconds = timed(lambda: feature_statistics(z, budget))
        features[i] = (z_np, labels_np)
        gold, small = {}, []
        start = time.perf_counter()
        for c in range(C):
            positions = np.flatnonzero(labels_np == c)
            if len(positions) != n_ic[c]:
                raise RuntimeError("recovery train labels disagree with frozen counts")
            if c not in active:
                continue
            gold[c] = analytic_gradient(z_np[positions], labels_np[positions], wn, bn, budget)
            comparisons.append(compare_gradient(by_class[c], gold[c], f"{ref_id}/client_{i:03d}/class_{c}/full-vs-analytic", budget))
        for c in sorted(set([active[0], active[-1]])):
            positions = np.flatnonzero(labels_np == c)[:8]
            idx = torch.tensor(positions, dtype=torch.long, device="cuda")
            zs, ys = z[idx], torch.full((len(positions),), c, dtype=torch.long, device="cuda")
            batch = head_gradient(zs, ys, wp, bp, budget)
            individuals = [head_gradient(zs[j:j+1], ys[j:j+1], wp, bp, budget) for j in range(len(positions))]
            mean = tuple(np.mean([row[k].astype(np.float64) for row in individuals], axis=0) for k in (0, 1))
            cpu = head_gradient(zs.cpu(), ys.cpu(), wp.cpu(), bp.cpu(), budget)
            analytic = analytic_gradient(z_np[positions], labels_np[positions], wn, bn, budget)
            for actual, gold_gradient, name in ((batch, mean, "batch-vs-singletons"), (batch, analytic, "batch-vs-analytic"), (batch, cpu, "CUDA-vs-CPU")):
                comparisons.append(compare_gradient(actual, gold_gradient, f"{ref_id}/client_{i:03d}/class_{c}/" + name, budget))
            small.append({"class_id": c, "sample_positions": positions.tolist(), "global_train_indices": [clients[i]["indices"][j] for j in positions],
                          "features_float32": z_np[positions], "batch_mean": batch, "singleton_mean": mean, "CPU_float32": cpu, "analytic_float64": analytic})
        oracle_seconds = time.perf_counter() - start
        diagnostics[i] = {"features_float32": z_np, "labels": labels_np, "global_train_indices": clients[i]["indices"],
                          "analytic_gradients_float64": gold, "small_sample_smoke": small}
        theory = len(active) * C * 129 * 4
        message = {"path": str(message_path.relative_to(OUTPUT)).replace("\\", "/"), "sha256": sha(message_path.read_bytes()), "bytes": message_path.stat().st_size}
        records.append({"client_id": f"client_{i:03d}", "sealed_sample_count": len(labels_np), "positive_class_count": len(active),
                        "missing_class_ids": absent, "feature_statistics": stats, "feature_forwards": (len(labels_np)+127)//128,
                        "gradient_mode": "complete selected-client train class gradient reused from original persisted float32 message",
                        "sampling_noise": "none within selected client classes; not full-population", "scan_frequency": "one original scan plus one authorized missing-feature reconstruction",
                        "message": message, "message_rewritten": False, "gradient_tensor_payload_bytes": theory,
                        "reference_downlink_theoretical_file_bytes": path.stat().st_size,
                        "original_per_client_compute_seconds": None, "original_timing_missing_reason": "only in terminated process memory; do not fabricate",
                        "recovery_cost": {"encode_seconds": encode_seconds, "feature_statistics_seconds": stats_seconds,
                                          "independent_reference_auxiliary_smoke_seconds": oracle_seconds, "existing_message_read_seconds": read_seconds}})
        for key, value in (("encode_seconds", encode_seconds), ("feature_statistics_seconds", stats_seconds),
                           ("independent_reference_auxiliary_smoke_seconds", oracle_seconds), ("existing_message_read_seconds", read_seconds)):
            recovery_cost[key] += value
        resource_sample(budget)
        print(f"recovered missing diagnostics {ref_id} client_{i:03d}; full primary gradients reused", flush=True)
    start = time.perf_counter()
    partial = weighted_partial(gradients, task["counts"]["n_ic"], task["counts"]["N_c"], C, 128)
    partial_reference = {}
    for c in range(C):
        rows = [features[i][0][features[i][1] == c] for i in SELECTED if c in gradients[i]]
        if rows:
            joined = np.concatenate(rows)
            analytic = analytic_gradient(joined, np.full(len(joined), c), wn, bn, budget)
            direct = tuple(g * len(joined)/task["counts"]["N_c"][c] for g in analytic)
        else:
            direct = (np.zeros((C, 128), np.float64), np.zeros(C, np.float64))
        partial_reference[c] = direct
        comparisons.append(compare_gradient((partial[c]["weight"], partial[c]["bias"]), direct, f"{ref_id}/class_{c}/partial-weighted-vs-direct", budget))
    recovery_cost["partial_target_diagnostic_seconds"] = time.perf_counter() - start
    after = tensor_state_sha(model.state_dict())
    repeated, repeated_metadata = restore_candidate(path, "cpu")
    if after != before or repeated.state_identity() != before or repeated_metadata != metadata or any(p.grad is not None for p in model.parameters()):
        raise RuntimeError("recovery changed reference state")
    diagnostics.update(partial_contributions=partial, independent_partial_reference=partial_reference,
                       weight_float32=wn, bias_float32=bn)
    diagnostic = save_tensors(OUTPUT / "diagnostics" / f"{ref_id}.pt", to_tensors(diagnostics), budget)
    diagnostic["path"] = str(Path(diagnostic["path"]).relative_to(OUTPUT)).replace("\\", "/")
    return {"reference_id": ref_id, "dataset": "CIFAR100", "checkpoint_file_sha256": reference["checkpoint_file_sha256"],
            "state_sha256_before": before, "state_sha256_after": after, "repeated_read_state_sha256": repeated.state_identity(),
            "actual_loaded_identity_checked": True, "complete_C_bias": True, "no_parameter_grad_or_update": True,
            "formal_qualification": "NOT_decided_in_segment_1", "clients": records, "comparisons": comparisons,
            "diagnostic_tensor_file": diagnostic, "costs": {"original_reference_phase_seconds": old["phase_seconds"]["reference_3"],
            "original_per_client_times": None, "missing_reason": "not persisted before process termination", "recovery": recovery_cost},
            "recovery_scope": "saved full primary gradients retained; discarded features/oracles/auxiliary smoke reconstructed once",
            "recovered_features_equal_to_lost_cache": "not asserted: old cache/hash not persisted", "resources": resource_sample(budget)}


def main():
    args = argparse.ArgumentParser()
    args.add_argument("--recover-missing-fourth-diagnostic", action="store_true")
    if not args.parse_args().recover_missing_fourth_diagnostic:
        raise RuntimeError("explicit missing-diagnostic recovery scope required; no automatic fresh run")
    if Path(sys.executable).resolve() != Path(r"E:\anaconda3\python.exe").resolve():
        raise RuntimeError("required interpreter mismatch")
    if (OUTPUT / "resume_run_record.json").exists():
        raise RuntimeError("continuation ledger already exists; no rerun/reset")
    old_path, old_config = OUTPUT / "run_record.json", original.json_file(OUTPUT / "measurement_config.json")
    old = original.json_file(old_path)
    if old["hit"] != {"actual": 78479043, "field": "evidence_bytes"}:
        raise RuntimeError("unexpected original stop identity")
    limits = copy.deepcopy(old["limits"])
    limits.update(evidence_bytes=256*1024**2, scans=2000)
    limits["phase_seconds"].update(resume_input=90, recover_missing_diagnostic=90, resume_storage=90)
    budget = ContinuedBudget(old, sha(old_path.read_bytes()), limits)
    watchdog(budget)
    try:
        prereg = PREREG.read_bytes()
        budget.write(OUTPUT / "resume_preregistration.md", prereg, raw=True)
        preserved, points = audit_preserved(budget, old_config)
        config = {"continuation": "single missing fourth-point diagnostics, no remeasurement of primary class gradients",
                  "base_commit": original.git("rev-parse", "HEAD").decode().strip(), "limits": limits, "previous_counters": old["counts"],
                  "preregistration_sha256": sha(prereg), "old_files_preserved_sha256": preserved,
                  "original_source_fingerprints": old_config["source_fingerprints"],
                  "resume_source_sha256": sha(Path(__file__).read_bytes()), "started_at": original.now(),
                  "estimated_cumulative_bytes_with_25MiB_margin_and_extra_reserve": 104824515,
                  "actual_recovery_authorization": "direct human reply: 允许仅补算 C100 r80 缺失诊断; earlier three points and all saved messages unchanged, additional costs cumulative",
                  "old_files_overwritten": [], "commit_authorized": False, "epsilon_frozen": False}
        budget.write(OUTPUT / "resume_config.json", config)
        if not torch.cuda.is_available() or not torch.__version__.startswith("2.5.1"):
            raise RuntimeError("declared environment mismatch")
        torch.set_num_threads(2)
        torch.use_deterministic_algorithms(True)
        torch.backends.cuda.matmul.allow_tf32 = False
        torch.backends.cudnn.allow_tf32 = False
        torch.backends.cudnn.benchmark = False
        budget.write(OUTPUT / "resume_environment.json", {"torch": torch.__version__, "numpy": np.__version__, "GPU": torch.cuda.get_device_name(),
                    "CPU_threads": 2, "TF32": False, "deterministic_algorithms": True, "python": sys.version})
        tasks, manifest, binding, upstream = original.verify_inputs(budget)
        budget.enter("resume_input")
        clients, input_record = selected_images(tasks["CIFAR100"], SELECTED, budget)
        fourth = manifest["references"][-1]
        point = recover_fourth(fourth, tasks["CIFAR100"], clients, budget, old)
        points.append(point)
        budget.delivered_references.append(fourth["reference_id"])
        budget.enter("resume_storage")
        budget.write(OUTPUT / "smoke_measurements_complete.json", {"scope": "segment 1 only; NOT formal acceptance", "completed_references": points,
                    "missing_reference_ids": [], "prior_three_records_reused": True, "prior_messages_rewritten": False})
        comparisons = [r for point in points for r in point["comparisons"]]
        epsilon = epsilon_candidate(comparisons)
        epsilon.update(measurement_count=len(comparisons), worst_comparison=max(comparisons, key=lambda r: r["normalized_Linf"]),
                       recovery_scope="fourth primary class gradients reused; missing features/references and auxiliary checks reconstructed; earlier comparisons reused")
        budget.write(OUTPUT / "epsilon_candidate.json", epsilon)
        budget.write(OUTPUT / "W02_measurement.json", {"status": "first-segment measurement, NOT frozen", "references": points,
                    "original_encoded_positions": old["counts"]["feature_samples"], "recovery_encoded_positions": 2205,
                    "cumulative_encoded_positions": budget.counts["feature_samples"], "original_selected_client_scans": 12, "recovery_scans": 3,
                    "original_input_phase_seconds": old["phase_seconds"]["input"], "recovery_source_loading": input_record,
                    "original_missing_timing": "C100 r80 per-client times not persisted; retain original phase total and recovery time separately",
                    "frequency": "one original scan per selected client/reference plus three authorized recovery scans, not a frozen event protocol",
                    "network": "no actual network; original local message bytes and reference theoretical copies retained, no re-upload",
                    "target_scope": "selected 3/20-source partial contribution, not formal full G_c"})
        for name, digest in preserved.items():
            if sha((OUTPUT / name).read_bytes()) != digest:
                raise RuntimeError("old result was changed: " + name)
        for name, digest in upstream.items():
            if sha((ROOT / name).read_bytes()) != digest:
                raise RuntimeError("sealed upstream changed: " + name)
        budget.write(OUTPUT / "decision.json", {"checkpoint": "G1.2", "segment": 1,
                    "smoke": "passed_with_candidate_numerical_basis_and_disclosed_recovery", "state": "证据不足/预算耗尽",
                    "reason": "正式验收证据不足；本次新额度未耗尽，原64MiB触顶历史保留", "formal_pass": False,
                    "reference_qualification_not_decided": True, "epsilon_frozen": False, "W02_frozen": False,
                    "missing_segment_1_diagnostic_items": [], "formal_missing": ["gradient epsilon adoption/freeze",
                    "formal W02 freeze", "second-segment authorization and full G1.2 formal measurement/target package"],
                    "limitations": ["only clients 0/9/19", "no P/G1.3/A1/A2/A3/A7/A8 or training",
                    "C100 r80 original per-client timing lost; recovery cost separately recorded", "four reference tail validation recall=0"],
                    "no_commit": True, "finished_at": original.now()})
        budget.status = "segment_1_completed_formal_G1.2_evidence_insufficient"
        budget.save()
        file_hashes = {str(p.relative_to(OUTPUT)).replace("\\", "/"): sha(p.read_bytes()) for p in OUTPUT.rglob("*") if p.is_file()
                       and p.name not in ("artifact_hashes.json", "resume_run_record.json")}
        budget.write(OUTPUT / "artifact_hashes.json", {"algorithm": "SHA-256 actual bytes", "files": file_hashes,
                    "excluded": ["self", "resume_run_record.json (mutable final continuation ledger, report hash separately)"],
                    "original_trigger_ledger_included": True, "old_files_unchanged": True,
                    "hash_objects": "file bytes; checkpoint tensor state identity remains separately referenced"})
        budget.save()
        print(json.dumps({"resume_complete": True, "epsilon_candidate": epsilon["value"], "cumulative_counts": budget.counts,
                          "cumulative_seconds": budget.snapshot()["elapsed_seconds"], "old_files_preserved": len(preserved)}, ensure_ascii=False), flush=True)
    except BaseException as error:
        if not isinstance(error, PreparationLimit):
            budget.status = "stopped_resume_error"
            budget.progress["error"] = f"{type(error).__name__}: {error}"
            budget.save(reserved=True)
        raise


if __name__ == "__main__":
    main()
