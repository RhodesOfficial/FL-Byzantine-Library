r"""Produce four traceable G1.2 candidate inputs with bounded ordinary FedAvg.

Use E:\anaconda3\python.exe -B scripts/prepare_direction_a_backbones.py.
This entry does not accept G1.2 references or compute class-gradient probes.
"""

import time
PROGRAM_STARTED = time.monotonic()

import copy
import importlib.util
import json
import os
import subprocess
import sys
import traceback
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.dont_write_bytecode = True
# Deterministic CUDA GEMM requirement, before the first CUDA context.
os.environ["CUBLAS_WORKSPACE_CONFIG"] = ":4096:8"

from direction_a.backbone_preparation import (
    PreparationBudget, PreparationLimit, watchdog, encode, sha, tensor_state_sha,
    read_task, task_binding, load_train_cache, aggregate_states, validate_model,
    save_candidate, resource_sample,
)
from direction_a.model import ResNet8Adapter, NORMALIZATION
import numpy as np
import torch

OUT = ROOT / "artifacts" / "direction_a" / "backbone_preparation_v1"
LIMITS = {"attempts": 180, "optimizer_steps": 7200, "backwards": 7200, "forwards": 7500,
          "scans": 1024, "evidence_bytes": 256 * 1024 ** 2, "logical_copy_bytes": 4 * 1024 ** 3,
          "retries": 2, "wall_seconds": 1200, "gpu_allocated_bytes": 6 * 1024 ** 3,
          "cpu_tensor_proxy_bytes": 2 * 1024 ** 3, "per_run": {"attempts": 90, "optimizer_steps": 3600},
          "phase_seconds": {"input": 90, "train_CIFAR10": 480, "train_CIFAR100": 480, "validation": 90, "storage": 90}}
DATASETS = (("CIFAR10", 2026101321), ("CIFAR100", 2026101322))
POINTS = (40, 80)


def now():
    return datetime.now(ZoneInfo("Asia/Shanghai")).isoformat()


def reference_id(dataset, seed, round_id):
    return f"A-backbone-{dataset}-s{seed}-r{round_id:04d}-v1"


def git(*args):
    return subprocess.run(["git", *args], cwd=ROOT, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout


def generation_config(inputs, base_commit):
    sources = ["direction_a/backbone_preparation.py", "scripts/prepare_direction_a_backbones.py",
               "tests/test_direction_a_backbone_preparation.py", "direction_a/model.py", "models/ResNet.py"]
    return {"parent_checkpoint": "G1.2", "work_item": "合格骨干准备", "preparation_identity": "FedPCC-backbone-preparation-v1",
            "source_type": "new ordinary FedAvg training; no existing checkpoint or resumed run",
            "base_commit": base_commit, "input_versions": inputs,
            "implementation_fingerprints": {path: {"working_bytes_sha256": sha((ROOT / path).read_bytes())} for path in sources},
            "model": {"adapter": "direction_a.model.ResNet8Adapter", "backbone_source": "models.ResNet.ResNet_3Layer",
                      "blocks": [1, 1, 1], "channels": [32, 64, 128], "shortcut": "B", "feature_dim": 128,
                      "classes_by_dataset": {"CIFAR10": 10, "CIFAR100": 100},
                      "head_parameter_names": ["linear.weight", "linear.bias"], "head_bias": True,
                      "parameter_dtype": "float32", "loss": "mean CrossEntropy(raw logits), no class weights"},
            "transforms": {dataset: {"mean": values[0], "std": values[1], "raw": "uint8 RGB NCHW /255",
                                      "augmentation": "none", "scopes": ["train", "validation"],
                                      "same_as_frozen_0.2": True} for dataset, values in NORMALIZATION.items()},
            "BN": {"local_training": "train mode updates all running buffers", "affine": True, "eps": 1e-5, "momentum": 0.1,
                   "aggregation": "sample-weight float running_mean/var; max num_batches_tracked",
                   "reference_readout": "eval, requires_grad False; all buffers retained", "training_mode_certified_by_0.2": False},
            "training": {"rounds": 80, "N": 20, "m": 8, "local_optimizer_steps": 5, "batch_size": 64,
                         "sampling": "uniform within sealed client training indices with replacement",
                         "optimizer": "SGD", "momentum": 0.9, "weight_decay": 5e-4, "nesterov": False,
                         "local_optimizer_state": "reset at each invitation", "learning_rate": {"1-40": 0.05, "41-80": 0.01},
                         "aggregation": "ordinary sample-weighted FedAvg over all returning invited clients",
                         "weights_source": "sealed acceptance.client_train_totals normalized over invited set",
                         "initialization": "torch default initialization; manual_seed(training_seed)",
                         "training_seeds": dict(DATASETS), "data_seed": 20261012,
                         "invitation_rng": "PCG64(training_seed+1000), independent fixed-size samples",
                         "client_sampler_rng": "PCG64(training_seed+2000+client_index), persistent during this run",
                         "participation": "ideal all invited complete; no G1.1 proxy deadline/speed/dropout",
                         "communication": "single-host sequential in-memory state copies; no network registration/traffic",
                         "failure_or_resume": "no resumed training; any failed attempt remains charged and archived"},
            "reference_plan": {"rounds": list(POINTS), "reference_ids": [reference_id(dataset, seed, r) for dataset, seed in DATASETS for r in POINTS],
                               "selection_rule": "all prespecified progress points retained, no metric ranking or threshold",
                               "lowest_accuracy_gate": "none specified; no new success threshold introduced"},
            "validation": {"split": "fixed sealed global validation; official_train namespace", "batch_size": 128,
                           "mode": "eval/inference_mode", "test_used": False, "initial_baseline": "recorded separately, not a candidate",
                           "metrics": ["mean CE (nat)", "sample accuracy", "full-C macro recall", "fixed head/middle/tail recall"]},
            "environment": {"python": sys.executable, "torch": str(torch.__version__), "numpy": str(np.__version__),
                            "cuda_runtime": torch.version.cuda, "cudnn": torch.backends.cudnn.version(),
                            "device": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
                            "deterministic_algorithms": True, "cudnn_benchmark": False, "tf32": False,
                            "cpu_threads": 2, "cublas_workspace_config": ":4096:8"},
            "limits": LIMITS, "max_correction_retries": 1,
            "not_certified": ["G1.2 acceptance/class gradients", "G1.3", "P separability", "E1 recovery/lifecycle", "formal G1.1 event mechanism"]}


def train_run(task, seed, cache, config_hash, budget, validations, references):
    dataset, C = task["info"]["spec"]["dataset"], task["info"]["spec"]["classes"]
    run_id = f"FedPCC-backbone-prep-{dataset}-v1"
    phase = "train_" + dataset
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    server = ResNet8Adapter(C).cuda()
    local = copy.deepcopy(server)
    initial_hash = tensor_state_sha(server.state_dict())
    state_bytes = sum(value.numel() * value.element_size() for value in server.state_dict().values())
    invitation = np.random.Generator(np.random.PCG64(seed + 1000))
    samplers = [np.random.Generator(np.random.PCG64(seed + 2000 + i)) for i in range(20)]
    record = {"run_id": run_id, "parent_checkpoint": "G1.2", "work_item": "合格骨干准备", "dataset": dataset,
              "task_identity": task["identity"], "training_seed": seed, "data_seed": task["info"]["spec"]["seed"],
              "configuration_sha256": config_hash, "initial_state_sha256": initial_hash, "started_at": now(),
              "planned_updates": 80, "planned_attempts": 80, "updates_completed": 0, "attempts_completed": 0,
              "actual_optimizer_steps": 0, "local_client_updates": [], "rounds": [], "snapshots": [],
              "shared_reference_rounds": list(POINTS), "cost_ownership": "G1.2 backbone generation; shared run counted once",
              "network_actual_bytes": None, "network_reason": "single-machine sequential simulation, no network",
              "logical_state_bytes_per_transfer": state_bytes, "up_copy_theoretical_bytes": 0, "down_copy_theoretical_bytes": 0,
              "cpu_tensor_proxy_bytes": cache["cpu_resident_tensor_proxy_bytes"], "source_train_files_verified": cache["verified_original_train_sha256"],
              "raw_test_images_loaded": False, "resume_training": False}
    torch.cuda.reset_peak_memory_stats()
    budget.enter("validation")
    baseline = validate_model(server, cache, task["counts"]["class_groups"], C, budget)
    assert baseline["sample_denominator"] == task["acceptance"]["validation_total"]
    validations.append({"reference_id": None, "role": "initialization_baseline_not_candidate", "run_id": run_id,
                        "state_sha256": initial_hash, "round": 0, "validation_data_sha256": task["source_records"]["data.json"]["sha256"],
                        "metrics": baseline, "recorded_at": now(), "selected": False,
                        "selection_reason": "random initialization is not a trained candidate"})
    budget.write(OUT / "validation_record.json", {"records": validations})
    budget.enter(phase)
    for r in range(1, 81):
        budget.progress = {"run_id": run_id, "round_in_progress": r, "client_in_progress": None}
        budget.consume("attempts", run_id=run_id)
        chosen = sorted(int(i) for i in invitation.choice(20, 8, replace=False))
        lr = 0.05 if r <= 40 else 0.01
        states, volumes = [], []
        global_before = tensor_state_sha(server.state_dict()) if r in POINTS else None
        for i in chosen:
            client_id = task["data"]["clients"][i]["id"]
            budget.progress.update(client_in_progress=client_id)
            budget.consume("logical_copy_bytes", 2 * state_bytes)
            record["down_copy_theoretical_bytes"] += state_bytes
            record["up_copy_theoretical_bytes"] += state_bytes
            local.load_state_dict(server.state_dict(), strict=True)
            local.train()
            local.requires_grad_(True)
            optimizer = torch.optim.SGD(local.parameters(), lr=lr, momentum=0.9, weight_decay=5e-4, nesterov=False)
            start, end = cache["offsets"][i]
            sample_hash = __import__("hashlib").sha256()
            torch.cuda.synchronize()
            begin = time.perf_counter()
            losses = []
            for step in range(5):
                budget.progress["local_step_in_progress"] = step + 1
                indices = samplers[i].integers(start, end, size=64, dtype=np.int64)
                sample_hash.update(indices.tobytes())
                index = torch.as_tensor(indices, device="cuda", dtype=torch.long)
                optimizer.zero_grad(set_to_none=True)
                budget.consume("forwards")
                logits = local(cache["x"][index])
                loss = torch.nn.functional.cross_entropy(logits, cache["y"][index])
                scalar_loss = float(loss.detach())
                if not np.isfinite(scalar_loss):
                    raise RuntimeError("nonfinite ordinary training loss; stop, do not change LR to rescue")
                budget.consume("backwards")
                loss.backward()
                budget.consume("optimizer_steps", run_id=run_id)
                optimizer.step()
                losses.append(scalar_loss)
                record["actual_optimizer_steps"] += 1
            torch.cuda.synchronize()
            record["local_client_updates"].append({"attempt_id": r - 1, "update_round": r, "client_id": client_id,
                                                    "sealed_training_volume": task["acceptance"]["client_train_totals"][i],
                                                    "steps": 5, "batch_size": 64, "examples_processed": 320,
                                                    "lr": lr, "mean_batch_training_CE_nat": sum(losses) / 5,
                                                    "client_compute_seconds": time.perf_counter() - begin,
                                                    "sample_position_sha256": sample_hash.hexdigest(),
                                                    "sample_hash_scope": "int64 positions in concatenated sealed client train cache"})
            states.append({name: value.detach().clone() for name, value in local.state_dict().items()})
            volumes.append(task["acceptance"]["client_train_totals"][i])
        torch.cuda.synchronize()
        begin = time.perf_counter()
        combined = aggregate_states(states, volumes)
        server.load_state_dict(combined, strict=True)
        torch.cuda.synchronize()
        record["rounds"].append({"attempt_id": r - 1, "update_round": r, "planned_ids": [task["data"]["clients"][i]["id"] for i in chosen],
                                  "returned_ids": [task["data"]["clients"][i]["id"] for i in chosen], "empty_completion": False,
                                  "sealed_returned_volumes": volumes, "aggregation_weights": [n / sum(volumes) for n in volumes],
                                  "aggregation_seconds": time.perf_counter() - begin, "lr": lr,
                                  "real_training_update": True})
        record["updates_completed"], record["attempts_completed"] = r, r
        resource_sample(budget)
        if r % 10 == 0:
            budget.write(OUT / "runs" / f"{dataset}_run_record.json", record)
            budget.save()
            print(f"{dataset}: update {r}/80; SGD steps {record['actual_optimizer_steps']}", flush=True)
        if r in POINTS:
            ref = reference_id(dataset, seed, r)
            budget.enter("storage")
            metadata = {"parent_checkpoint": "G1.2", "work_item": "合格骨干准备", "reference_id": ref, "run_id": run_id,
                        "task_identity": task["identity"], "task_source_sha256": {name: row["sha256"] for name, row in task["source_records"].items()},
                        "generation_config_sha256": config_hash, "training_seed": seed, "data_seed": task["info"]["spec"]["seed"],
                        "update_round": r, "attempts_completed": r, "optimizer_steps_completed": record["actual_optimizer_steps"],
                        "model": {"adapter": "direction_a.model.ResNet8Adapter", "C": C, "d": 128,
                                  "head_names": ["linear.weight", "linear.bias"], "head_shapes": [[C, 128], [C]],
                                  "head_bias": True, "dtype": "float32", "BN_buffers": "all running_mean/var/num_batches_tracked",
                                  "readout_mode": "eval + requires_grad(False)", "restore_function": "direction_a.backbone_preparation.restore_candidate"},
                        "initialization_state_sha256": initial_hash, "saved_at": now(),
                        "source_type": "new ordinary FedAvg training", "qualification": "candidate_pending_G1.2_acceptance",
                        "full_training_resume_package": False}
            path = OUT / "checkpoints" / f"{ref}.pt"
            saved = save_candidate(path, server, metadata, budget)
            assert saved["state_sha256"] != initial_hash, "random initialization cannot stand in for trained candidate"
            assert saved["state_sha256"] != global_before, "selected round must be a real update"
            assert all(torch.isfinite(value).all() for value in server.state_dict().values() if value.is_floating_point())
            budget.delivered_references.append(ref)
            budget.enter("validation")
            metrics = validate_model(server, cache, task["counts"]["class_groups"], C, budget)
            assert metrics["sample_denominator"] == 1000
            assert metrics["class_sample_denominators"] == [task["info"]["spec"]["validation_per_class"]] * C
            validations.append({"reference_id": ref, "run_id": run_id, "checkpoint_path": str(path.relative_to(OUT)).replace("\\", "/"),
                                "checkpoint_file_sha256": saved["file_sha256"], "state_sha256": saved["state_sha256"],
                                "validation_identity": {"source": "sealed global validation", "task_identity": task["identity"],
                                                        "data_json_sha256": task["source_records"]["data.json"]["sha256"],
                                                        "indices": "data.json/validation; official_train namespace"},
                                "mode": "eval/inference_mode; BN unchanged", "transform_dataset": dataset, "validation_batch_size": 128,
                                "metrics": metrics, "missing_items": [], "recorded_at": now(),
                                "training_progress": {"update_round": r, "attempts": r, "optimizer_steps": record["actual_optimizer_steps"],
                                                      "scheduled_point_completed": True, "planned_run_rounds": 80},
                                "selected": True, "selection_reason": "prespecified progress point; all points retained",
                                "qualification_threshold": None, "threshold_reason": "no independent minimum accuracy requirement specified; no P claim"})
            point = {"reference_id": ref, "run_id": run_id, "dataset": dataset, "task_identity": task["identity"],
                     "checkpoint_path": str(path.relative_to(OUT)).replace("\\", "/"),
                     "checkpoint_file_sha256": saved["file_sha256"], "state_sha256": saved["state_sha256"],
                     "training_progress": {"update_round": r, "attempts": r, "optimizer_steps": record["actual_optimizer_steps"]},
                     "validation_record_path": "validation_record.json", "validation_record_key": f"records/reference_id={ref}",
                     "checkpoint_integrity": "bitwise complete state readback; no epsilon used", "qualification": "pending_G1.2_acceptance"}
            references.append(point)
            record["snapshots"].append(point)
            budget.write(OUT / "validation_record.json", {"records": validations})
            budget.write(OUT / "runs" / f"{dataset}_run_record.json", record)
            print(f"Saved {ref}: validation accuracy={metrics['sample_accuracy_percent']:.2f}%, macro={metrics['macro_recall']['value_fraction']:.4f}; retained by plan", flush=True)
            budget.save()
            budget.enter(phase)
    record["finished_at"], record["completion"] = now(), "planned_80_updates_complete"
    record["resource_measurements"] = resource_sample(budget)
    record["training_samples_processed_with_replacement"] = record["actual_optimizer_steps"] * 64
    assert record["actual_optimizer_steps"] == 3200 and len(record["local_client_updates"]) == 640
    budget.write(OUT / "runs" / f"{dataset}_run_record.json", record)
    del server, local, optimizer, states, combined
    return record


def main():
    if Path(sys.executable).resolve() != Path(r"E:\anaconda3\python.exe").resolve():
        raise RuntimeError("use E:\\anaconda3\\python.exe")
    prereg = ROOT / "docs" / "DIRECTION_A_BACKBONE_PREPARATION_RUN_RECORD_v1.md"
    if not prereg.is_file():
        raise RuntimeError("missing finite preregistration")
    if (OUT / "run_record.json").exists():
        raise RuntimeError("existing cumulative ledger; do not reset/overwrite an earlier generation")
    budget = PreparationBudget(OUT / "run_record.json", LIMITS)
    budget.started = budget.phase_started = PROGRAM_STARTED
    budget.planned_references = [reference_id(dataset, seed, r) for dataset, seed in DATASETS for r in POINTS]
    budget.save()
    watchdog(budget)
    manifest = {"parent_checkpoint": "G1.2", "work_item": "合格骨干准备", "preparation_identity": "FedPCC-backbone-preparation-v1",
                "status": "running", "started_at": now(), "base_commit": git("rev-parse", "HEAD").decode().strip(),
                "references": [], "missing_items": list(budget.planned_references), "input_versions": {}}
    validations, references, runs = [], [], []
    try:
        budget.enter("input")
        if not torch.cuda.is_available() or str(torch.__version__).split("+")[0] != "2.5.1":
            raise RuntimeError("required PyTorch 2.5.1 + CUDA environment unavailable; no CPU fallback")
        torch.set_num_threads(2)
        torch.use_deterministic_algorithms(True)
        torch.backends.cudnn.benchmark = False
        torch.backends.cudnn.deterministic = True
        torch.backends.cuda.matmul.allow_tf32 = False
        torch.backends.cudnn.allow_tf32 = False
        torch.cuda.set_device(0)
        budget.write(OUT / "preregistration.md", prereg.read_bytes(), raw=True)
        manifest["preregistration_sha256"] = sha(prereg.read_bytes())
        for name in ("DIRECTION_A_BACKBONE_PREPARATION_ADJUDICATION_v1.md", "DIRECTION_A_PROTOCOL_FREEZE_v1.md", "DIRECTION_A_CHECKPOINTS_v1.md",
                     "DIRECTION_A_G1_1_ADJUDICATION_v1.md", "DIRECTION_A_0_2_ADJUDICATION_v1.md", "DIRECTION_A_0_2_ACCEPTANCE_v1.md"):
            manifest["input_versions"]["docs/" + name] = {"version": "v1 current preflight working bytes", "sha256": sha((ROOT / "docs" / name).read_bytes())}
        config = generation_config(manifest["input_versions"], manifest["base_commit"])
        config_hash = budget.write(OUT / "generation_config.json", config)
        specification = importlib.util.spec_from_file_location("backbone_oracles", ROOT / "tests" / "test_direction_a_backbone_preparation.py")
        tests = importlib.util.module_from_spec(specification)
        specification.loader.exec_module(tests)
        manifest["independent_selfchecks"] = tests.run_oracles(budget) + tests.guard_oracles(budget)
        baseline = json.loads((ROOT / "artifacts" / "direction_a" / "phase0_2_v1" / "artifact_hashes.json").read_bytes())
        tasks, bindings = {}, {}
        for dataset, seed in DATASETS:
            identity = f"FedPCC-0.2-candidate-{dataset}-N20-v1"
            task = read_task(ROOT / "artifacts" / "direction_a" / "phase0_2_v1" / "tasks" / identity, baseline, budget, ROOT)
            tasks[dataset] = task
            bindings[dataset] = task_binding(task, seed)
        binding_hash = budget.write(OUT / "task_binding.json", bindings)
        manifest.update(generation_config_path="generation_config.json", generation_config_sha256=config_hash,
                        task_binding_path="task_binding.json", task_binding_sha256=binding_hash,
                        run_record_path="run_record.json", validation_record_path="validation_record.json")
        budget.write(OUT / "manifest.json", manifest)
        for dataset, seed in DATASETS:
            budget.enter("input")
            cache = load_train_cache(tasks[dataset], budget, "cuda")
            record = train_run(tasks[dataset], seed, cache, config_hash, budget, validations, references)
            runs.append({"run_id": record["run_id"], "dataset": dataset, "path": f"runs/{dataset}_run_record.json",
                         "completion": record["completion"], "actual_updates": record["updates_completed"],
                         "actual_attempts": record["attempts_completed"], "optimizer_steps": record["actual_optimizer_steps"],
                         "shared_reference_rounds": list(POINTS), "cost_counting": "one training run, not separately charged for each reference"})
            del cache
            torch.cuda.empty_cache()
            manifest["references"] = references
            manifest["missing_items"] = [name for name in budget.planned_references if name not in budget.delivered_references]
            budget.write(OUT / "manifest.json", manifest)
        budget.enter("storage")
        budget.scan()
        for path, version in manifest["input_versions"].items():
            assert sha((ROOT / path).read_bytes()) == version["sha256"], "input changed during generation"
        for fingerprint_path, fingerprint in config["implementation_fingerprints"].items():
            assert sha((ROOT / fingerprint_path).read_bytes()) == fingerprint["working_bytes_sha256"]
        for task in tasks.values():
            for name, record in task["source_records"].items():
                assert sha((ROOT / record["path"]).read_bytes()) == record["sha256"]
        assert len(references) == 4 and not manifest["missing_items"]
        manifest.update(status="candidate_package_complete_source_traceable", delivered_at=now(),
                        generation_runs=runs, qualification="G1.2 reception/gradient acceptance pending; P not claimed",
                        hash_algorithm="SHA-256, actual file bytes; state hashes cover name/dtype/shape/tensor bytes",
                        cost_ownership={"parent_checkpoint": "G1.2", "budget_row": "existing G1.1/G1.2/G1.3 row",
                                        "components": ["backbone generation", "validation/reference plan", "save/readback"],
                                        "class_gradient_measurement": "not executed", "shared_run_counted_once": True,
                                        "previous_G1.1_event_smoke": "separate historical ledger retained; not reset or upgraded"},
                        not_certified=config["not_certified"])
        budget.write(OUT / "manifest.json", manifest)
        handoff = ("# 合格骨干准备候选交付\n\nparent_checkpoint=G1.2；work_item=合格骨干准备。\n\n"
                   "两份封存任务各完成一个普通 FedAvg 运行，各留第 40/80 更新轮，共四个预选参考；全部保留，缺失项为空。\n\n"
                   "manifest.json 定位全部参考、运行进度与验证记录；task_binding.json 绑定原 0.2 八文件、标签/IF/α/分组及两类 seed；"
                   "generation_config.json 是预选普通训练/BN/变换/参与规则与实现指纹；run_record.json 是累计额度，runs/ 是实际进度/成本；"
                   "validation_record.json 含四参考和两初始基线的完整分母/缺失项；checkpoints/ 保存同版本 backbone/head/全部 BN；artifact_hashes.json 封存字节。\n\n"
                   "加载：direction_a.backbone_preparation.restore_candidate(path, device='cpu')，返回 eval/冻结模型与来源元数据。"
                   "仅核对保存/读取的精确状态，不使用 0.2 logits ε_num。没有断点续训，也不交 E1 全生命周期恢复包。\n\n"
                   "准备状态只是候选包完整、来源可核对，不签 G1.2 或 P；普通头验证不等于特征可分性，没有引入最低精度门槛。"
                   "G1.1 正式仍证据不足，本次理想参与和 W01 实测不替代 W02/正式事件绑定。\n\n"
                   "接收方须继续核对正式参考与任务/模型/变换/训练/多个参考点相符，独立完成完整头梯度（含 bias）、逐样本/端类均值、"
                   "a_ic 汇总 G_c、参数/缓冲读取不变、缺类/采样噪声口径及相关数值容差；之后 P 才裁决可分性。A1/A2/A3、G1.3、E1 均未执行。\n")
        budget.write(OUT / "handoff.md", handoff.encode("utf-8"), raw=True)
        budget.scan()
        inventory = {str(path.relative_to(OUT)).replace("\\", "/"): sha(path.read_bytes())
                     for path in OUT.rglob("*") if path.is_file() and path.name not in ("run_record.json", "artifact_hashes.json")}
        budget.write(OUT / "artifact_hashes.json", {"algorithm": "SHA-256 actual bytes", "files": inventory,
                                                    "excluded": ["self", "run_record.json (final mutable ledger; Git byte identity checked separately)"]})
        budget.finish()
        print(json.dumps({"status": manifest["status"], "references": len(references), "counts": budget.counts,
                          "elapsed_seconds": budget.snapshot()["elapsed_seconds"]}, ensure_ascii=False), flush=True)
        return 0
    except Exception as exc:
        if not isinstance(exc, PreparationLimit):
            budget.status = "preparation_failure"
            budget.hit = {"field": "exception", "type": type(exc).__name__, "message": str(exc)}
            budget.save(reserved=True)
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
