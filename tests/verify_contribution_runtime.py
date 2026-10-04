"""Independent real-CNN checks, isolated from formal B training processes."""
import argparse
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "easyFL"), str(ROOT / "tests")]
OUT = ROOT / "outputs/d1_3b/phase_b_contribution_v2_20261004"
METHODS = ("brdrag", "balanced_brdrag", "d1")


def controlled():
    os.environ["CUBLAS_WORKSPACE_CONFIG"] = ":4096:8"
    import torch
    torch.set_num_threads(1)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False
    torch.use_deterministic_algorithms(True, warn_only=False)


def fixed():
    import torch
    from aggregators.contribution_diagnostics import (summarize, reconstruct64,
        two_layer_errors, require_two_layers)
    from flgo_byzantine.algorithm import _model_from_update, _parameter_vector
    from scripts.run_phase_b import build_manifest, create_runner, save
    from test_phase_b import rng_state, same_rng
    runner = create_runner(build_manifest(), 101, "d1", OUT / "fixed")
    runner._load_context()
    context = runner._byz_context
    base = _parameter_vector(runner.model)
    generator = torch.Generator().manual_seed(991)
    inputs = [torch.randn(base.shape, generator=generator).to(base) * .0001 for _ in range(3)]
    records = []
    for method in METHODS:
        from aggregators.d1_reference_baselines import RootBaseline, B_BASELINE_VERSION
        from aggregators.d1_category_coverage import D1CategoryCoverage
        original = (D1CategoryCoverage(context, 10, seed=101) if method == "d1" else
                    RootBaseline(context, 10, method, seed=101, version=B_BASELINE_VERSION, root_budget=2000))
        results, states = [], []
        for enabled in (False, True):
            instance = copy.copy(original)
            instance._loader_generator = torch.Generator()
            instance._loader_generator.set_state(original._loader_generator.get_state())
            instance.collect_contributions = enabled
            before = rng_state()
            result = instance(inputs)
            assert same_rng(before, rng_state()), (method, "caller RNG changed")
            results.append(result)
            states.append(_model_from_update(runner.model, result).state_dict())
            if enabled:
                theta_new = _parameter_vector(_model_from_update(runner.model, result))
                actual = theta_new.double() - base.double()
                summary = summarize(instance.last_contribution_trace, actual)
                checks = two_layer_errors(instance.last_contribution_trace, base, -result, theta_new)
                hat, _ = reconstruct64(instance.last_contribution_trace)
                torch.save({"model_state": {k: v.detach().cpu().clone() for k, v in runner.model.state_dict().items()},
                            "uploads": [v.detach().cpu() for v in inputs],
                            "theta": base.detach().cpu(), "theta_new": theta_new.detach().cpu(),
                            "d": -result.detach().cpu(), "hat_d": hat.detach().cpu(),
                            "return_path": instance.last_stats.get("fallback", "baseline"),
                            "checks": checks}, OUT / f"fixed/{method}_case.pt")
                save(OUT / f"fixed/{method}_checks.json", dict(checks,
                     decomposition_error=summary["decomposition_error"],
                     original_input_restored=False,
                     attribution_status="原失败未完成归因；原始模型/向量未保存，本例依据保存的生成过程重建同类用例",
                     generation="CNN initialization from seed101 task/dataseed0; private CPU generator991; 3 randn vectors * 1e-4"))
                require_two_layers(checks)
        assert torch.equal(results[0], results[1]), (method, "aggregate changed")
        assert all(torch.equal(v, states[1][k]) for k, v in states[0].items())
        records.append({"method": method, "aggregate_bitwise": True, "model_bitwise": True,
                        "caller_four_rng_restored": True, "decomposition_error": summary["decomposition_error"], **checks})
        print(f"FIXED_CNN_PASS method={method} output_bitwise=true four_rng=true "
              f"old_relative={summary['decomposition_error']:.9g} two_layers={checks}", flush=True)
    save(OUT / "fixed/checks.json", records)


def unit(method, enabled, rounds=20):
    import torch
    from scripts.run_phase_b import build_manifest, create_runner, save
    from test_phase_b import rng_state
    directory = OUT / (f"{method}_{'on' if enabled else 'off'}" if rounds == 20 else "fields_d1_10")
    runner = create_runner(build_manifest(), 101, method, directory, verification_rounds=rounds,
                           collect_contributions=enabled)
    def checkpoint(point):
        torch.save({"model": {k: v.detach().cpu().clone() for k, v in runner.model.state_dict().items()},
                    "rng": rng_state(), "participants": list(runner.phase_b_participants)},
                   directory / f"round_{point:02d}.pt")
    original_log = runner.gv.logger.log_once
    def log(*args, **kwargs):
        original_log(*args, **kwargs)
        if runner.gv.logger.output["time"][-1] == 0:
            checkpoint(0)
    runner.gv.logger.log_once = log
    original_iterate = runner.iterate
    def iterate():
        value = original_iterate()
        checkpoint(len(runner.phase_b_participants))
        return value
    runner.iterate = iterate
    begin = time.perf_counter()
    runner.run()
    assert len(runner.phase_b_participants) == rounds
    if enabled and method == "d1":
        torch.save(runner._byz_aggregator_instance.last_contribution_trace["final_residual"].detach().cpu(),
                   directory / "final_residual_expected.pt")
    save(directory / "metrics.json", {"time": runner.gv.logger.output["time"],
         "accuracy": runner.gv.logger.output["test_accuracy"], "loss": runner.gv.logger.output["test_loss"],
         "wall_seconds": time.perf_counter() - begin})
    print(f"CNN_UNIT_COMPLETE method={method} enabled={enabled} rounds={rounds}", flush=True)


def compare(method):
    import numpy as np
    import torch
    from scripts.run_phase_b import read, save
    from test_phase_b import same_rng
    comparisons = []
    off, on = (OUT / f"{method}_{name}" for name in ("off", "on"))
    for point in range(21):
        a = torch.load(off / f"round_{point:02d}.pt", weights_only=False)
        b = torch.load(on / f"round_{point:02d}.pt", weights_only=False)
        assert a["model"].keys() == b["model"].keys()
        differences = {k: float((v - b["model"][k]).abs().max()) for k, v in a["model"].items()}
        assert all(torch.equal(v, b["model"][k]) for k, v in a["model"].items()), (method, point, differences)
        assert same_rng(a["rng"], b["rng"]), (method, point, "RNG mismatch")
        assert a["participants"] == b["participants"], (method, point, "participant mismatch")
        comparisons.append({"round": point, "tensor_max_abs": differences, "max_relative": 0.,
                            "four_rng_equal": True, "participants_equal": True})
    a, b = read(off / "metrics.json"), read(on / "metrics.json")
    assert a["time"] == b["time"] == [0, 10, 20]
    assert a["accuracy"] == b["accuracy"] and a["loss"] == b["loss"], (method, a, b)
    rows = [json.loads(line) for line in (on / "contribution_log.jsonl").read_text().splitlines()]
    checks = [json.loads(line) for line in (on / "contribution_checks.jsonl").read_text().splitlines()]
    assert len(rows) == 20 and [r["round"] for r in rows] == list(range(1, 21))
    assert len(checks) == 20
    fields = {"client_parallel_coef", "client_residual_coef", "client_contrib_norm",
              "client_contrib_along_final", "decomposition_error", "residual_vector", "residual_group_cosine"}
    for i, row in enumerate(rows):
        assert fields.issubset(row)
        from aggregators.contribution_diagnostics import require_two_layers
        require_two_layers(checks[i])
        assert checks[i]["round"] == row["round"]
        assert row["received_client_ids"] == b_participants(on, i)
        assert all(len(row[k]) == 40 for k in fields if k.startswith("client_"))
        if method == "d1" and row["round"] == 20:
            assert row["residual_vector"] is not None and isinstance(row["residual_group_cosine"], dict)
            vector = np.fromfile(on / row["residual_vector"], dtype="<f4")
            metadata = read(on / "contribution_metadata.json")
            assert vector.size == sum(p["numel"] for p in metadata["parameter_layout"])
            assert np.isfinite(vector).all()
            expected = torch.load(on / "final_residual_expected.pt", weights_only=True).numpy()
            assert np.array_equal(vector, expected)
        else:
            assert row["residual_vector"] is None and row["residual_group_cosine"] is None
        if method != "d1":
            assert row["client_residual_coef"] == [0.] * 40
    assert not (off / "contribution_log.jsonl").exists()
    result = {"method": method, "comparisons": comparisons, "accuracy_difference": [0.] * 3,
              "loss_difference": [0.] * 3,
              "max_decomposition_error": max(r["decomposition_error"] for r in rows if r["decomposition_error"] is not None),
              "two_layer_checks_all_passed": True,
              "field_rows": 20, "ten_round_fields_complete": fields.issubset(rows[9]),
              "off_seconds": a["wall_seconds"], "on_seconds": b["wall_seconds"]}
    save(OUT / f"{method}_comparison.json", result)
    print(f"CNN_NEUTRALITY_PASS method={method} points=0..20 tensors_bitwise=true four_rng=true "
          f"participants=true metrics_diff=0 fields=20 max_error={result['max_decomposition_error']:.9g}", flush=True)
    return result


def fields10():
    from scripts.run_phase_b import save, read
    from aggregators.contribution_diagnostics import require_two_layers
    directory = OUT / "fields_d1_10"
    rows = [json.loads(line) for line in (directory / "contribution_log.jsonl").read_text().splitlines()]
    checks = [json.loads(line) for line in (directory / "contribution_checks.jsonl").read_text().splitlines()]
    assert len(rows) == len(checks) == 10
    fields = {"client_parallel_coef", "client_residual_coef", "client_contrib_norm",
              "client_contrib_along_final", "decomposition_error", "residual_vector", "residual_group_cosine"}
    for point, (row, check) in enumerate(zip(rows, checks), 1):
        assert row["round"] == check["round"] == point and fields.issubset(row)
        require_two_layers(check)
        assert all(len(row[k]) == 40 for k in fields if k.startswith("client_"))
        assert row["residual_vector"] is None and row["residual_group_cosine"] is None
    assert not (directory / "residual_vectors").exists()
    metadata = read(directory / "contribution_metadata.json")
    assert metadata["residual_save_interval"] == 20 and "error_definitions" in metadata
    result = {"rounds": 10, "fields_present_all_rounds": sorted(fields), "two_layers_passed": True,
              "periodic_fields": "null at rounds1..10; first vector/cosine validated separately at round20"}
    save(directory / "field_checks.json", result)
    print("FIELDS10_PASS rounds=10 fields=7 client_arrays=40 two_layers=true periodic_interval20_preserved", flush=True)
    return result


def b_participants(directory, index):
    import torch
    return torch.load(directory / "round_20.pt", weights_only=False)["participants"][index]


def run():
    from scripts.run_phase_b import PYTHON, save
    OUT.mkdir(parents=True, exist_ok=True)
    assert all(p.name == "unit_cases" for p in OUT.iterdir()), "Refusing to reuse runtime results"
    start = time.perf_counter()
    def child(args, name):
        path = OUT / f"{name}_console.log"
        with path.open("w", encoding="utf-8") as stream:
            result = subprocess.run([str(PYTHON), "-B", "-u", __file__, *args], cwd=ROOT,
                                    stdout=stream, stderr=subprocess.STDOUT)
        print("\n".join(line for line in path.read_text(encoding="utf-8").splitlines()
                        if "PASS" in line or "COMPLETE" in line), flush=True)
        if result.returncode:
            print(path.read_text(encoding="utf-8")[-8000:], flush=True)
            raise RuntimeError(f"Verification failed: {name}; stopped before further tests")
    child(["fixed"], "fixed")
    results = []
    for method in METHODS:
        child(["unit", "--method", method], method + "_off")
        child(["unit", "--method", method, "--enabled"], method + "_on")
        results.append(compare(method))
    child(["unit", "--method", "d1", "--enabled", "--rounds", "10"], "fields_d1_10")
    field_results = fields10()
    save(OUT / "checks.json", {"results": results, "total_wall_seconds": time.perf_counter() - start,
         "fields10": field_results,
         "controlled_settings": {"cudnn_deterministic": True, "cudnn_benchmark": False,
                                 "deterministic_algorithms": True, "CUBLAS_WORKSPACE_CONFIG": ":4096:8"},
         "scope": "Independent engineering checks only; no formal B units or new evaluations"})


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("run", "fixed", "unit"))
    parser.add_argument("--method", choices=METHODS)
    parser.add_argument("--enabled", action="store_true")
    parser.add_argument("--rounds", type=int, choices=(10, 20), default=20)
    args = parser.parse_args()
    if args.action in {"fixed", "unit"}:
        controlled()
    if args.action == "run":
        run()
    elif args.action == "fixed":
        fixed()
    else:
        unit(args.method, args.enabled, args.rounds)
