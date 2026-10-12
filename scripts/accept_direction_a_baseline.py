r"""Checkpoint 0.2 only: bounded data audits, adapter measurements, no training.

Run with E:\anaconda3\python.exe -B scripts/accept_direction_a_baseline.py.
The parent PowerShell watchdog must stop this process after 900 seconds.
"""

import hashlib
import importlib.util
import json
import math
import os
import sys
import threading
import time
import traceback
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.dont_write_bytecode = True

from direction_a.budget import Budget, LimitReached

OUT = ROOT / "artifacts" / "direction_a" / "phase0_2_v1"
LIMITS = {"forwards": 128, "scans": 4096, "artifact_bytes": 32 * 1024 * 1024,
          "retries": 1, "wall_seconds": 900, "phase_seconds": {"data": 600, "model": 240, "verification": 60}}


def start_watchdog(budget):
    """Watch phase time as well as total time, even if a forward blocks."""
    def watchdog():
        while True:
            time.sleep(0.25)
            try:
                budget.check()
            except LimitReached:
                os._exit(124)
    threading.Thread(target=watchdog, daemon=True).start()


def difference(reference, value):
    import torch
    delta = value.detach().double() - reference.detach().double()
    linf = float(delta.abs().max())
    scale = max(1.0, float(reference.detach().abs().max()))
    assert torch.isfinite(reference).all() and torch.isfinite(value).all()
    return {"linf_absolute": linf, "frobenius_absolute": float(torch.linalg.vector_norm(delta)),
            "reference_scale_max_1_linf": scale, "normalized_linf": linf / scale,
            "reference_min": float(reference.min()), "reference_max": float(reference.max())}


def measure_models(sources, budget):
    import numpy as np
    import torch
    from direction_a.model import ResNet8Adapter, transform_images
    from models.ResNet import BasicBlock, ResNet_3Layer

    torch.set_num_threads(2)
    torch.use_deterministic_algorithms(True)
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    devices = ["cpu", "cuda"] if torch.cuda.is_available() else ["cpu"]
    measurements, identities, parameters = [], [], {}
    cpu_reference = {}
    for dataset, source in sources.items():
        C = source.classes
        for seed in (20261012, 20261013):
            torch.manual_seed(seed)
            base = ResNet8Adapter(C).freeze_reference()
            state = {key: value.detach().clone() for key, value in base.state_dict().items()}
            # Independent parameter arithmetic: stem, three residual blocks,
            # option-B projection weights and BN affine pairs, then head.
            manual_backbone = (864 + 64 + 18432 + 128 + 18432 + 36864 + 2048 + 384
                               + 73728 + 147456 + 8192 + 768)
            expected_parameters = manual_backbone + C * 128 + C
            assert sum(p.numel() for p in base.parameters()) == expected_parameters
            assert len([m for m in base.modules() if isinstance(m, torch.nn.BatchNorm2d)]) == 9
            assert list(base.state_dict()) == list(ResNet_3Layer(BasicBlock, [1, 1, 1], num_classes=C).state_dict())
            parameters[dataset] = {"parameter_count": expected_parameters, "feature_dim": 128,
                                   "head_shape": [C, 128], "head_bias": True, "batchnorm_layers": 9,
                                   "parameter_dtype": "float32", "architecture": "ResNet_3Layer(BasicBlock,[1,1,1]),32/64/128,shortcut B",
                                   "BN": {"mode": "eval", "eps": 1e-5, "momentum": 0.1, "affine": True,
                                          "running_mean_var_and_num_batches_tracked": "included in state SHA256; unchanged in all measurements"},
                                   "loss": "cross_entropy(raw logits, integer label), mean reduction; no class weights",
                                   "logit_semantics": "raw logits; legacy forward is log_softmax(logits)"}
            for device in devices:
                model = ResNet8Adapter(C).to(device).freeze_reference()
                model.load_state_dict(state)
                legacy = ResNet_3Layer(BasicBlock, [1, 1, 1], num_classes=C).to(device).eval()
                legacy.load_state_dict(state)
                legacy.requires_grad_(False)
                before = {k: v.detach().clone() for k, v in model.state_dict().items()}
                model_hash = model.state_identity()
                identities.append({"dataset": dataset, "seed": seed, "device": device, "state_sha256": model_hash,
                                   "origin": "torch default random initialization; zero training steps; no checkpoint file",
                                   "reference_qualification": "not certified; only 0.2 numerical object"})
                batches = {"actual_test_0_3": transform_images(source.test_images[:4], dataset).to(device),
                           "zero_normalized_input": torch.zeros(2, 3, 32, 32, device=device)}
                for batch_name, images in batches.items():
                    budget.check()
                    name = f"{dataset}:{seed}:{device}:{batch_name}"
                    with torch.inference_mode():
                        complete = budget.forward(name + ":complete", lambda: model(images))
                        features = None

                        def split_path():
                            nonlocal features
                            features = model.encode(images)
                            return model.head(features)

                        split = budget.forward(name + ":encode_head", split_path)
                        repeat = budget.forward(name + ":repeat_complete", lambda: model(images))
                        old = budget.forward(name + ":legacy_logprob", lambda: legacy(images))
                        assert tuple(complete.shape) == (len(images), C)
                        assert tuple(features.shape) == (len(images), 128)
                        checks = {"complete_vs_encode_head": difference(complete, split),
                                  "repeat_complete": difference(complete, repeat),
                                  "legacy_vs_logsoftmax": difference(old, torch.log_softmax(complete, dim=1))}
                        if batch_name == "zero_normalized_input":
                            # All default Conv biases absent, BN mean=0; zero
                            # propagates through every block -> head bias exactly.
                            assert torch.count_nonzero(features) == 0
                            assert torch.equal(complete, model.head.bias.expand_as(complete))
                            checks["independent_zero_input_bias"] = difference(model.head.bias.expand_as(complete), complete)
                        else:
                            # Scalar float64 fsum; no F.linear/matmul in reference.
                            f = features.detach().cpu().double().tolist()
                            w = model.head.weight.detach().cpu().double().tolist()
                            b = model.head.bias.detach().cpu().double().tolist()

                            def scalar_head():
                                return torch.tensor([[math.fsum(a * weight for a, weight in zip(row, wc)) + bc
                                                      for wc, bc in zip(w, b)] for row in f], dtype=torch.float64, device=device)

                            scalar = budget.forward(name + ":scalar_fsum_head", scalar_head)
                            checks["independent_scalar_head"] = difference(scalar, complete)
                        key = (dataset, seed, batch_name)
                        if device == "cpu":
                            cpu_reference[key] = complete.detach().clone()
                        else:
                            checks["CPU_float32_vs_CUDA_float32"] = difference(cpu_reference[key], complete.cpu())
                        # Same-path and legacy equivalence must be exact here;
                        # this catches systematic convention errors before any
                        # tolerance candidate can mask them.
                        assert checks["complete_vs_encode_head"]["linf_absolute"] == 0
                        assert checks["repeat_complete"]["linf_absolute"] == 0
                        assert checks["legacy_vs_logsoftmax"]["linf_absolute"] == 0
                        assert checks.get("independent_scalar_head", {"normalized_linf": 0})["normalized_linf"] < 1e-5
                        measurements.append({"dataset": dataset, "classes": C, "seed": seed, "device": device,
                                             "batch": batch_name, "batch_size": len(images), "checks": checks,
                                             "reference_logits": complete.detach().cpu().tolist()})
                assert all(torch.equal(v, before[k]) for k, v in model.state_dict().items()), "parameters/BN changed"
                assert model.state_identity() == model_hash
    max_normalized = max(check["normalized_linf"] for m in measurements for check in m["checks"].values())
    max_absolute = max(check["linf_absolute"] for m in measurements for check in m["checks"].values())
    raw_candidate = max(8 * float(np.finfo(np.float32).eps), 4 * max_normalized)
    magnitude = 10 ** math.floor(math.log10(raw_candidate))
    candidate = math.ceil(raw_candidate / magnitude) * magnitude
    assert all(check["normalized_linf"] <= candidate for m in measurements for check in m["checks"].values())
    return {"status": "model_smoke_pass_candidate_tolerance_only", "precision": "float32; scalar head reference math.fsum float64",
            "reference_object": "pre-softmax logits", "norms": ["Linf", "Frobenius"],
            "normalized_scale": "max(1, ||reference logits||_infinity)",
            "max_absolute_linf": max_absolute, "max_normalized_linf": max_normalized,
            "float32_machine_epsilon": float(np.finfo(np.float32).eps),
            "epsilon_num_candidate": candidate, "epsilon_num_status": "candidate_pending_review_not_frozen",
            "candidate_selection": "ceil to one decimal significant digit of max(8*u_float32,4*max measured normalized Linf)",
            "absolute_acceptance_formula": "Linf(delta logits) <= candidate * max(1,Linf(reference logits))",
            "scope": "only measured eval-mode logits; does not apply to gradients, state recovery or training",
            "systematic_consistency_guard": "same path, repeat and legacy log_softmax must match exactly; independent zero-input/head arithmetic required",
            "parameters": parameters, "identities": identities, "measurements": measurements,
            "environment": {"python": sys.executable, "torch": torch.__version__, "cuda": torch.version.cuda,
                            "cudnn": torch.backends.cudnn.version(), "gpu": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
                            "deterministic_algorithms": True, "tf32": False, "cpu_threads": 2,
                            "cuda_peak_allocated_bytes": torch.cuda.max_memory_allocated() if torch.cuda.is_available() else None}}


def verify_saved():
    """Bounded continuation: immutable reader and exact evidence inventory."""
    if Path(sys.executable).resolve() != Path(r"E:\anaconda3\python.exe").resolve():
        raise RuntimeError("wrong interpreter")
    budget = Budget.resume(OUT / "run.json")
    budget.limits["phase_seconds"]["verification"] = 60
    budget.save()
    start_watchdog(budget)
    verification = {"status": "running", "new_model_forwards": 0, "repartition_operations": 0}
    try:
        from direction_a.task import CIFARSource, TaskReader
        from direction_a.model import NORMALIZATION
        test_spec = importlib.util.spec_from_file_location("baseline_oracles", ROOT / "tests" / "test_direction_a_baseline.py")
        tests = importlib.util.module_from_spec(test_spec)
        test_spec.loader.exec_module(tests)
        verification["guard_oracles"] = tests.run_guard_oracles(budget)
        summary = json.loads((OUT / "summary.json").read_text(encoding="utf-8"))
        assert hashlib.sha256((OUT / "preregistration.md").read_bytes()).hexdigest() == summary["run_record_sha256_before_execution"]
        budget.consume("artifact_bytes", "preserved preregistration", (OUT / "preregistration.md").stat().st_size)
        sources = {name: CIFARSource(ROOT / "easyFL" / "flgo" / "benchmark" / "RAW_DATA", name, budget)
                   for name in ("CIFAR10", "CIFAR100")}
        verification["task_reader"] = []
        for task in summary["tasks"]:
            budget.scan(task["identity"] + ":immutable_reader_and_scalar_pixel_reference")
            reader = TaskReader(task["folder"])
            source = sources[reader.info["spec"]["dataset"]]
            assert reader.counts["N_c"] == task["acceptance"]["training_class_counts"]
            for split, client_id in (("validation", None), ("test", None), ("train", "client_000"), ("test", "client_000")):
                indices = reader.indices(split, client_id)
                assert isinstance(indices, tuple)
                view = reader.dataset_view(source, split, client_id)
                assert len(view) == len(indices) > 0
                image, label = view[0]
                raw_images = source.test_images if split == "test" else source.train_images
                raw_labels = source.test_labels if split == "test" else source.train_labels
                assert label == int(raw_labels[indices[0]])
                assert tuple(image.shape) == (3, 32, 32)
                mean, std = NORMALIZATION[source.dataset]
                for c in range(3):
                    scalar = (int(raw_images[indices[0], c, 0, 0]) / 255 - mean[c]) / std[c]
                    assert abs(float(image[c, 0, 0]) - scalar) < 4e-7
            verification["task_reader"].append({"identity": task["identity"], "status": "hash_and_indexed_view_pass"})
        budget.scan("sealed evidence: norms and implementation fingerprints")
        model = json.loads((OUT / "model_acceptance.json").read_text(encoding="utf-8"))
        check_names = sorted({name for m in model["measurements"] for name in m["checks"]})
        verification["comparison_maxima"] = {}
        for name in check_names:
            values = [m["checks"][name] for m in model["measurements"] if name in m["checks"]]
            verification["comparison_maxima"][name] = {field: max(v[field] for v in values)
                                                       for field in ("linf_absolute", "frobenius_absolute", "normalized_linf")}
        verification["implementation_sha256"] = {str(p.relative_to(ROOT)).replace("\\", "/"): hashlib.sha256(p.read_bytes()).hexdigest()
                                                  for p in list((ROOT / "direction_a").glob("*.py")) +
                                                  [ROOT / "scripts" / "accept_direction_a_baseline.py", ROOT / "tests" / "test_direction_a_baseline.py"]}
        verification["transform_version"] = {name: {"mean": values[0], "std": values[1], "input": "uint8 NCHW /255",
                                                     "augmentation": "none", "scope": "train/validation/test"}
                                              for name, values in NORMALIZATION.items()}
        verification["status"] = "pass"
        budget.write_json(OUT / "verification.json", verification)
        budget.scan("final evidence inventory SHA256")
        files = [p for p in OUT.rglob("*") if p.is_file() and p.name not in ("run.json", "artifact_hashes.json")]
        inventory = {str(p.relative_to(OUT)).replace("\\", "/"): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
        budget.write_json(OUT / "artifact_hashes.json", inventory)
        actual_bytes = sum(p.stat().st_size for p in OUT.rglob("*") if p.is_file())
        if actual_bytes >= budget.limits["artifact_bytes"]:
            budget.stop("artifact_bytes_actual", actual_bytes)
        budget.finish("pass_candidate_epsilon_pending_review")
        print(json.dumps({"verification": "pass", "cumulative_counts": budget.counts,
                          "cumulative_workload_seconds": time.monotonic() - budget.started,
                          "comparison_maxima": verification["comparison_maxima"]}, ensure_ascii=False), flush=True)
        return 0
    except Exception as exc:
        if not isinstance(exc, LimitReached):
            budget.status = "verification_failure"
            budget.save()
        verification["status"] = budget.status
        verification["error"] = {"type": type(exc).__name__, "message": str(exc)}
        (OUT / "verification_failure.json").write_text(json.dumps(verification, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        traceback.print_exc()
        return 1


def main():
    if Path(sys.executable).resolve() != Path(r"E:\anaconda3\python.exe").resolve():
        raise RuntimeError("use E:\\anaconda3\\python.exe")
    record = ROOT / "docs" / "DIRECTION_A_0_2_RUN_RECORD_v1.md"
    if not record.is_file():
        raise RuntimeError("missing pre-registered budget")
    if (OUT / "run.json").exists():
        raise RuntimeError("existing measurement ledger: no reset/overwrite; inspect cumulative limits before a retry")
    budget = Budget(OUT / "run.json", LIMITS)

    start_watchdog(budget)
    summary = {"checkpoint": "0.2", "started_at": datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(),
               "run_record_sha256_before_execution": hashlib.sha256(record.read_bytes()).hexdigest(),
               "input_sha256": {}, "tasks": [], "tests": {}, "stages_executed": ["data", "model"],
               "training_steps": 0, "attempts": 0, "calibration_steps": 0}
    try:
        for name in ("DIRECTION_A_CHECKPOINTS_v1.md", "DIRECTION_A_PROTOCOL_FREEZE_v1.md", "DIRECTION_A_FEASIBILITY_v1.md",
                     "RESEARCH_INNOVATIONS_v1.md", "DIRECTION_SELECTION_v1.md"):
            summary["input_sha256"][name] = hashlib.sha256((ROOT / "docs" / name).read_bytes()).hexdigest()
        from direction_a.task import CIFARSource, TaskSpec, save_task
        test_spec = importlib.util.spec_from_file_location("baseline_oracles", ROOT / "tests" / "test_direction_a_baseline.py")
        tests = importlib.util.module_from_spec(test_spec)
        test_spec.loader.exec_module(tests)
        budget.enter("data")
        summary["tests"]["data"] = tests.run_data_oracles(budget)
        budget.save()
        print("Independent data/arithmetic oracles passed", flush=True)
        sources = {}
        for dataset, C, full_head, validation in (("CIFAR10", 10, 4500, 100), ("CIFAR100", 100, 450, 10)):
            source = CIFARSource(ROOT / "easyFL" / "flgo" / "benchmark" / "RAW_DATA", dataset, budget)
            sources[dataset] = source
            # Smoke is constructed and checked before the separate full-size task.
            for spec in (TaskSpec(dataset, f"FedPCC-0.2-smoke-{dataset}-v1", C, 4, 100, 2, 8),
                         TaskSpec(dataset, f"FedPCC-0.2-candidate-{dataset}-N20-v1", C, 20, full_head, validation, 10000 // C)):
                result = save_task(OUT / "tasks" / spec.identity, source, spec, budget)
                summary["tasks"].append(result)
                budget.write_json(OUT / "summary.json", summary)
                budget.save()
                print(f"Data pass: {spec.identity}; train={result['acceptance']['train_total']}; IF={result['acceptance']['actual_training_if']}", flush=True)
        summary["data_status"] = "all_four_tasks_pass_independent_persisted_audit"
        budget.write_json(OUT / "summary.json", summary)
        budget.enter("model")
        summary["tests"]["model"] = tests.run_model_oracles(budget)
        model = measure_models(sources, budget)
        model_raw = budget.write_json(OUT / "model_acceptance.json", model)
        summary["model_sha256"] = hashlib.sha256(model_raw).hexdigest()
        summary["epsilon_num_candidate"] = model["epsilon_num_candidate"]
        summary["model_status"] = model["status"]
        summary["status"] = "executable_0.2_pass_formal_seal_pending_epsilon_review"
        summary["finished_at"] = datetime.now(ZoneInfo("Asia/Shanghai")).isoformat()
        summary["cost_fields"] = {"wall_seconds": "measured total in run.json; includes data, imports and model",
                                  "data_seconds": "phase data in run.json", "model_seconds": "phase model in run.json",
                                  "server_training_matching_retraining": "not applicable: not executed in 0.2",
                                  "client_compute": "not simulated; this is a single-host baseline audit",
                                  "simulation_wall_seconds": None, "transmission_seconds": None,
                                  "actual_up_down_registration_bytes": None,
                                  "theoretical_registration": "N*C*8 bytes int64 counts, per-task acceptance",
                                  "local_artifact_written_bytes": "cumulative in run.json; separate from network payload",
                                  "search_evaluations": 0, "paired_research_repeats": 0}
        budget.write_json(OUT / "summary.json", summary)
        # The ledger is also evidence: check actual saved bytes, including it.
        budget.scan("artifact inventory: cumulative size and SHA256")
        files = [p for p in OUT.rglob("*") if p.is_file() and p.name not in ("run.json", "artifact_hashes.json")]
        inventory = {str(p.relative_to(OUT)).replace("\\", "/"): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
        budget.write_json(OUT / "artifact_hashes.json", inventory)
        actual_bytes = sum(p.stat().st_size for p in OUT.rglob("*") if p.is_file())
        if actual_bytes >= LIMITS["artifact_bytes"]:
            budget.stop("artifact_bytes_actual", actual_bytes)
        budget.finish("pass_candidate_epsilon_pending_review")
        print(f"Model pass: epsilon_num candidate={model['epsilon_num_candidate']}; max abs={model['max_absolute_linf']}; max scaled={model['max_normalized_linf']}", flush=True)
        print(json.dumps({"status": summary["status"], "counts": budget.counts, "elapsed_seconds": time.monotonic() - budget.started}, ensure_ascii=False), flush=True)
        return 0
    except Exception as exc:
        if not isinstance(exc, LimitReached):
            budget.status = "assertion_or_execution_failure"
            budget.save()
        summary["status"] = budget.status
        summary["error"] = {"type": type(exc).__name__, "message": str(exc)}
        # Preserve already computed evidence without starting another scan/forward.
        (OUT / "failure.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    if len(sys.argv) == 2 and sys.argv[1] == "--verify-saved":
        raise SystemExit(verify_saved())
    if len(sys.argv) != 1:
        raise SystemExit("only default acceptance or --verify-saved is supported")
    raise SystemExit(main())
