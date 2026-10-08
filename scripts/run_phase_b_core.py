"""Nine fresh paired B units; strict internal checks, no historical metric gate."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "easyFL")]
from scripts.run_phase_b import (OUT as SETUP, PYTHON, SOURCE, SEEDS, build_manifest,
                                create_runner, digest, read, save, validate_task)
from scripts.validate_phase_b_attack import capture_existing_evaluations, pooled_activity

OUT = ROOT / "outputs/d1_3b/phase_b_core_20261004"
METHODS = ("brdrag", "balanced_brdrag", "d1")
SESSION3 = ROOT / "outputs/d1_3b/phase_b_contribution_v2_20261004/verification_manifest.json"
CLIENT_FIELDS = ("client_parallel_coef", "client_residual_coef", "client_contrib_norm",
                 "client_contrib_along_final")
GROUPS = {"honest_tail_enriched", "other_honest", "malicious"}


def commit():
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def clean():
    assert not subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True).strip()


def finite(value):
    if isinstance(value, float):
        assert math.isfinite(value), value
    elif isinstance(value, dict):
        for item in value.values():
            finite(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            finite(item)


def check_record(row, checks, diagnostic, point, participants, method, directory):
    from aggregators.contribution_diagnostics import require_two_layers
    import numpy as np
    assert row["round"] == checks["round"] == diagnostic["round"] == point
    assert row["received_client_ids"] == diagnostic["received_client_ids"] == participants
    assert len(participants) == len(set(participants)) == 40
    assert not diagnostic["nonfinite_fields"]
    for key in CLIENT_FIELDS:
        assert len(row[key]) == 40
    assert all(v >= 0 for v in row["client_contrib_norm"])
    if checks["delta_norm"] == 0:
        assert row["client_contrib_along_final"] == [None] * 40
    assert row["decomposition_error"] is None or math.isfinite(row["decomposition_error"])
    finite(row); finite(checks)
    require_two_layers(checks)  # Old report-only decomposition_error is never a gate.
    if method != "d1":
        assert row["client_residual_coef"] == [0.] * 40
    periodic = method == "d1" and point % 20 == 0
    if not periodic:
        assert row["residual_vector"] is None and row["residual_group_cosine"] is None
        return None
    assert Path(row["residual_vector"]) == Path("residual_vectors") / f"round_{point:03d}.f32"
    path = directory / row["residual_vector"]
    assert path.is_file() and path.stat().st_size == 3191848
    vector = np.fromfile(path, dtype="<f4")
    assert vector.size == 797962 and np.isfinite(vector).all()
    metadata = read(directory / "contribution_metadata.json")
    assert sum(p["numel"] for p in metadata["parameter_layout"]) == vector.size
    cosine = row["residual_group_cosine"]
    assert set(cosine) == GROUPS
    assert all(v is None or math.isfinite(v) and -1 <= v <= 1 for v in cosine.values())
    norm = float(np.linalg.norm(vector.astype(np.float64)))
    if norm == 0:
        assert all(v is None for v in cosine.values())
    return {"round": point, "path": row["residual_vector"], "sha256": digest(path),
            "elements": vector.size, "bytes": path.stat().st_size, "norm": norm,
            "cosines": cosine, "passed": True}


def prepare():
    clean()
    assert not OUT.exists(), "Refusing to reuse core output directory"
    original_path = SETUP / "manifest.json"
    original, current = read(original_path), build_manifest()
    current["source_commit"] = original["source_commit"]
    assert current == original
    verification = read(SESSION3)
    assert verification["normal_path_cases_all_passed"] and verification["bytewise_model_audit"]["all_equal"]
    for filename, sha in verification["source_sha256"].items():
        assert digest(ROOT / filename) == sha, filename
    attack_path = SETUP / "attack_validation_seed_101/result.json"
    attack = read(attack_path)
    assert attack["verdict"]["passed"] and attack["integrity_passed"] and attack["participant_pairing_passed"]
    options = {str(seed): {method: dict(original["options"][str(seed)][method],
               byz_collect_contributions=True, byz_collect_nonzero=True)
               for method in METHODS} for seed in SEEDS}
    OUT.mkdir(parents=True)
    save(OUT / "run_manifest.json", dict(original,
         setup_manifest=str(original_path), setup_manifest_sha256=digest(original_path),
         source_commit=commit(), core_diagnostics_ready=True, options=options,
         session3_evidence={"path": str(SESSION3), "sha256": digest(SESSION3),
                            "source_commit": verification["source_commit"]},
         attack_validation_evidence={"path": str(attack_path), "sha256": digest(attack_path), "passed": True},
         from_scratch=True, expected_units=9, history_comparison="not_applicable: no completed same-method/config/version history",
         development_disclosure="Seeds101/102/103 participated in PhaseA configuration selection; paired development evidence, not independent held-out confirmation"))
    print("CORE_MANIFEST_READY tasks_generated=false diagnostics=true", flush=True)


def one_line(path, offsets):
    with path.open("r", encoding="utf-8") as stream:
        stream.seek(offsets.get(path, 0))
        line = stream.readline()
        assert line and not stream.readline(), (path, "expected exactly one new record")
        offsets[path] = stream.tell()
    return json.loads(line)


def unit(seed, method):
    import numpy as np
    import torch
    start = time.perf_counter()
    clean()
    manifest = read(OUT / "run_manifest.json")
    assert commit() == manifest["source_commit"]
    assert torch.cuda.is_available() and torch.__version__.startswith("2.5.1")
    assert os.environ.get("CUBLAS_WORKSPACE_CONFIG") is None
    assert not torch.backends.cudnn.deterministic and not torch.backends.cudnn.benchmark
    assert not torch.are_deterministic_algorithms_enabled()
    directory = OUT / f"seed_{seed}_{method}"
    runner = create_runner(manifest, seed, method, directory, collect_contributions=True)
    assert runner.option["byz_collect_nonzero"] and runner.option["byz_collect_contributions"]
    assert not runner.option["load_checkpoint"] and runner.option["num_rounds"] == 300
    initial = {k: v.detach().cpu().clone() for k, v in runner.model.state_dict().items()}
    torch.save(initial, directory / "initial_model.pt")
    state_hash = hashlib.sha256()
    for key, value in initial.items():
        state_hash.update(key.encode()); state_hash.update(value.numpy().tobytes())
    expected_malicious = sorted(np.random.default_rng(seed).choice(100, 30, replace=False).tolist())
    assert sorted(runner.byz_malicious_ids) == expected_malicious
    pair = {"initial_state_sha256": state_hash.hexdigest(), "malicious_ids": expected_malicious}
    for other in METHODS:
        sibling = OUT / f"seed_{seed}_{other}"
        if sibling != directory and (sibling / "pairing.json").is_file():
            assert read(sibling / "pairing.json") == pair
            reference = torch.load(sibling / "initial_model.pt", weights_only=True)
            assert initial.keys() == reference.keys()
            assert all(torch.equal(v, reference[k]) for k, v in initial.items())
    save(directory / "pairing.json", pair)
    runtime = {"torch_version": torch.__version__, "cuda_version": torch.version.cuda,
               "gpu": torch.cuda.get_device_name(0), "total_memory_bytes": torch.cuda.get_device_properties(0).total_memory,
               "cudnn_deterministic": torch.backends.cudnn.deterministic,
               "cudnn_benchmark": torch.backends.cudnn.benchmark,
               "deterministic_algorithms": torch.are_deterministic_algorithms_enabled(),
               "CUBLAS_WORKSPACE_CONFIG": os.environ.get("CUBLAS_WORKSPACE_CONFIG")}
    assert not runtime["cudnn_deterministic"] and not runtime["deterministic_algorithms"]
    assert not runtime["cudnn_benchmark"] and runtime["CUBLAS_WORKSPACE_CONFIG"] is None
    save(directory / "run_manifest.json", {"source_commit": commit(), "core_manifest_sha256": digest(OUT / "run_manifest.json"),
         "task": manifest["tasks"][str(seed)], "options": runner.option, "runtime": runtime,
         "from_scratch": True, "history_comparison": "not_applicable"})
    curves = capture_existing_evaluations(runner, directory)
    offsets, residuals, early = {}, [], []
    original = runner.iterate
    torch.cuda.reset_peak_memory_stats()
    training_start = time.perf_counter()
    def checked_iterate():
        value = original()
        point = len(runner.phase_b_participants)
        participants = runner.phase_b_participants[-1]
        row = one_line(directory / "contribution_log.jsonl", offsets)
        checks = one_line(directory / "contribution_checks.jsonl", offsets)
        diagnostic = one_line(directory / "diagnostic_log.jsonl", offsets)
        vector = check_record(row, checks, diagnostic, point, participants, method, directory)
        if vector:
            residuals.append(vector)
        stats = runner.full_round_stats[-1]
        assert stats["received"] == 40 and stats["aggregator"] == method and stats["attack"] == "label_flip"
        assert stats["malicious"] == sum(cid in runner.byz_malicious_ids for cid in participants)
        pooled_activity([stats])
        assert diagnostic["malicious_nonzero_fraction"] == stats["malicious_nonzero_fraction"]
        if point % 10 == 0:
            torch.cuda.synchronize()
            progress = {"round": point, "elapsed_training_seconds": time.perf_counter() - training_start,
                        "peak_allocated_bytes": torch.cuda.max_memory_allocated(),
                        "peak_reserved_bytes": torch.cuda.max_memory_reserved()}
            if point in (10, 20):
                early.append(progress)
            save(directory / "progress.json", dict(progress, early=early))
            print("RESOURCE " + json.dumps(progress), flush=True)
        return value
    runner.iterate = checked_iterate
    runner.run()
    assert runner.current_round == 301 and len(runner.phase_b_participants) == len(runner.full_round_stats) == 300
    assert curves["round"] == list(range(0, 301, 10)) and curves["class_total"] == [1000] * 10
    assert len(curves["class_correct"]) == len(curves["class_loss_mean"]) == 31
    assert len(residuals) == (15 if method == "d1" else 0)
    for filename in ("contribution_log.jsonl", "contribution_checks.jsonl", "diagnostic_log.jsonl"):
        assert len((directory / filename).read_text(encoding="utf-8").splitlines()) == 300
    validate_task(manifest["tasks"][str(seed)])
    per_class = [v / 1000 for v in curves["class_correct"][-1]]
    intervals = {f"{a}-{b}": pooled_activity(runner.full_round_stats[a-1:b])
                 for a, b in ((151, 200), (201, 250), (251, 300))}
    torch.save(runner.model.state_dict(), directory / "final_model.pt")
    save(directory / "residual_verification.json", residuals)
    save(directory / "result.json", {"seed": seed, "method": method, "rounds": 300, "options": runner.option,
         "participants": runner.phase_b_participants, "round_stats": runner.full_round_stats,
         "per_class_accuracy": per_class, "overall_accuracy": sum(per_class) / 10,
         "overall_loss": runner.gv.logger.output["test_loss"][-1], "activity_intervals": intervals,
         "internal_checks_passed": True, "contribution_rows": 300, "two_layer_rows": 300,
         "class_evaluations": 31, "residual_files": len(residuals), "early_resources": early,
         "history_comparison": "not_applicable", "training_seconds": time.perf_counter()-training_start,
         "wall_seconds": time.perf_counter()-start, "source_commit": commit()})
    print(f"CORE_UNIT_PASS seed={seed} method={method} rounds=300", flush=True)


def summarize_run(start, process_rows, concurrency):
    manifest = read(OUT / "run_manifest.json")
    results = []
    for seed in SEEDS:
        existing = []
        for method in METHODS:
            directory = OUT / f"seed_{seed}_{method}"
            if (directory / "result.json").is_file():
                result = read(directory / "result.json")
                results.append(result)
                existing.append(read(directory / "pairing.json"))
        assert all(v == existing[0] for v in existing)
        validate_task(manifest["tasks"][str(seed)])
    baselines = {}
    for method in METHODS[:2]:
        units = [r for r in results if r["method"] == method]
        complete = len(units) == 3
        nonzero = complete and all(r["per_class_accuracy"][8] > 0 and r["per_class_accuracy"][9] > 0 for r in units)
        means = [math.fsum(r["per_class_accuracy"][c] for r in units)/len(units) if units else None for c in (8, 9)]
        baselines[method] = {"complete": complete, "all_seed_tail_nonzero": nonzero,
                             "class8_mean": means[0], "class9_mean": means[1],
                             "passed": complete and nonzero and all(v >= .05 for v in means)}
    finished = len(results) == 9 and all(r["returncode"] == 0 for r in process_rows)
    verdict = finished and all(r["internal_checks_passed"] for r in results) and any(v["passed"] for v in baselines.values())
    save(OUT / "execution_report.json", {"source_commit": commit(), "processes": process_rows,
         "total_wall_seconds": time.perf_counter()-start, "completed_units": len(results),
         "remaining_concurrency": concurrency, "baselines": baselines, "B_to_C_passed": verdict,
         "attack_validation_passed": True, "history_comparison": "not_applicable",
         "no_method_specific_data_or_attack_or_test_changes": True})
    print(f"CORE_EXECUTION_END completed={len(results)}/9 B_to_C={verdict}", flush=True)


def run():
    clean()
    assert commit() == read(OUT / "run_manifest.json")["source_commit"]
    assert not any((OUT / f"seed_{s}_{m}").exists() for s in SEEDS for m in METHODS)
    begin, records = time.perf_counter(), []
    def spawn(seed, method):
        name = f"seed_{seed}_{method}"
        stream = (OUT / f"{name}_console.log").open("w", encoding="utf-8")
        process = subprocess.Popen([str(PYTHON), "-B", "-u", __file__, "unit", "--seed", str(seed), "--method", method],
                                   cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT)
        return (process, stream, seed, method, time.perf_counter())
    def finish(job):
        process, stream, seed, method, t = job
        code = process.wait(); stream.close()
        records.append({"seed": seed, "method": method, "returncode": code,
                        "process_wall_seconds": time.perf_counter()-t})
        print(f"PROCESS_END seed={seed} method={method} returncode={code}", flush=True)
        return code
    concurrency = 0
    for method in ("brdrag", "d1"):
        if finish(spawn(101, method)):
            summarize_run(begin, records, concurrency)
            return
    first = read(OUT / "seed_101_d1/result.json")
    runtime = read(OUT / "seed_101_d1/run_manifest.json")["runtime"]
    peak = max(r["peak_reserved_bytes"] for r in first["early_resources"])
    # Resource-only decision: two processes only when two peaks fit with >30% headroom.
    concurrency = 2 if peak * 2 < .7 * runtime["total_memory_bytes"] else 1
    save(OUT / "concurrency_decision.json", {"concurrency": concurrency, "early_resources": first["early_resources"],
         "total_memory_bytes": runtime["total_memory_bytes"], "criterion": "2*first_D1_peak_reserved < 0.7*total_memory; otherwise serial",
         "accuracy_used_for_decision": False, "initial_two_units_completed": True})
    print(f"CONCURRENCY remaining={concurrency} resource_only=true", flush=True)
    pending = [(101, "balanced_brdrag")] + [(seed, method) for seed in (102, 103) for method in METHODS]
    running, failed = [], False
    while running or pending and not failed:
        while pending and not failed and len(running) < concurrency:
            running.append(spawn(*pending.pop(0)))
        completed = [job for job in running if job[0].poll() is not None]
        for job in completed:
            failed |= finish(job) != 0
            running.remove(job)
        if running:
            time.sleep(1)
    summarize_run(begin, records, concurrency)


if __name__ == "__main__":
    assert Path(sys.executable).resolve() == PYTHON.resolve()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "run", "unit"))
    parser.add_argument("--seed", type=int, choices=SEEDS)
    parser.add_argument("--method", choices=METHODS)
    args = parser.parse_args()
    try:
        if args.action == "unit":
            unit(args.seed, args.method)
        else:
            (prepare if args.action == "prepare" else run)()
    except BaseException:
        if args.action == "unit":
            failure = OUT / f"seed_{args.seed}_{args.method}_failure.json"
            save(failure, {"seed": args.seed, "method": args.method, "traceback": traceback.format_exc(),
                           "action": "stop this unit; no retries; pause pending starts"})
        raise
