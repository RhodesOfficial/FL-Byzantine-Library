"""Separate-process real-CNN verification only, never the 300-round attack unit."""
import argparse
import copy
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "easyFL"), str(ROOT / "tests")]
CHECKS = ROOT / "outputs/d1_3b/phase_b_20261003/verification"


def controlled_runtime():
    os.environ["CUBLAS_WORKSPACE_CONFIG"] = ":4096:8"
    import torch
    torch.set_num_threads(1)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False
    torch.use_deterministic_algorithms(True, warn_only=False)


def one_round():
    from scripts.run_phase_b import build_manifest, create_runner, read, save, SOURCE
    runner = create_runner(build_manifest(), 101, "brdrag", CHECKS / "one_round", verification_rounds=1)
    runner.run()
    expected = read(SOURCE.parent / "seed_101/result.json")["participants"][0]
    assert len(runner.full_round_stats) == len(runner.phase_b_participants) == 1
    assert runner.phase_b_participants[0] == expected
    save(CHECKS / "one_round/pairing.json", {"seed": 101, "method": "brdrag", "rounds": 1,
         "participants": runner.phase_b_participants, "phase_a_first_round": expected, "matched": True})
    print("FIRST_ROUND_PASS seed=101 method=brdrag received=40 matches_phase_a=true")


def initialization():
    import torch
    from scripts.run_phase_b import build_manifest, create_runner, read, SOURCE, SEEDS
    manifest = build_manifest()
    for seed in SEEDS:
        reference = None
        for method in ("brdrag", "balanced_brdrag", "d1"):
            runner = create_runner(manifest, seed, method, CHECKS / f"pair_{seed}_{method}")
            state = {k: v.detach().cpu().clone() for k, v in runner.model.state_dict().items()}
            ids = sorted(runner.byz_malicious_ids)
            if reference is not None:
                assert ids == reference[1]
                assert state.keys() == reference[0].keys()
                assert all(torch.equal(v, reference[0][k]) for k, v in state.items())
            reference = state, ids
        print(f"INITIALIZATION_PASS seed={seed} initial_tensors={len(state)} malicious_ids=30 three_methods_equal=true")


def roots():
    import torch
    from aggregators.d1_category_coverage import _preserve_global_rng
    from aggregators.d1_reference_baselines import RootBaseline, B_BASELINE_VERSION
    from scripts.run_phase_b import build_manifest, create_runner
    from test_phase_b import rng_state, same_rng
    runner = create_runner(build_manifest(), 101, "brdrag", CHECKS / "fixed_cnn_roots")
    runner._load_context()
    for method in ("brdrag", "balanced_brdrag"):
        for budget in (1000, 2000):
            kwargs = {} if budget == 1000 else {"version": B_BASELINE_VERSION, "root_budget": 2000}
            original = RootBaseline(runner._byz_context, 10, method, seed=101, **kwargs)
            values = []
            for profile in ("unprotected", "X", "Y"):
                baseline = copy.copy(original)
                baseline._loader_generator = (torch.Generator().manual_seed(101) if profile == "X" else None)
                before = rng_state()
                # Outer guard restores test state; only X/Y are caller-preserving calls.
                with _preserve_global_rng():
                    if profile == "unprotected":
                        value = baseline._root_unprotected()
                    else:
                        with _preserve_global_rng():
                            value = baseline._root_unprotected()
                        assert same_rng(before, rng_state())
                assert same_rng(before, rng_state())
                values.append(value)
            assert all(torch.equal(values[0], v) for v in values[1:])
            print(f"CNN_ROOT_PASS method={method} budget={budget} X=Y=unprotected bitwise max_abs=0 four_rng_restored=true")


def short_unit(profile):
    import torch
    from scripts.run_phase_b import build_manifest, create_runner, save, upload_activity
    from test_phase_b import rng_state
    rounds = 10 if profile == "activity" else 20
    method = "avg" if profile == "activity" else "brdrag"
    runner = create_runner(build_manifest(), 101, method, CHECKS / profile, verification_rounds=rounds)
    if profile != "activity":
        runner._load_context()
        instance = runner._aggregator()
        if profile == "Y":
            instance._loader_generator = None
        log_once = runner.gv.logger.log_once

        def checkpoint(*args, **kwargs):
            log_once(*args, **kwargs)
            point = int(runner.gv.logger.output["time"][-1])
            torch.save({"model": {k: v.detach().cpu().clone() for k, v in runner.model.state_dict().items()},
                        "rng": rng_state(), "participants": list(runner.phase_b_participants),
                        "accuracy": runner.gv.logger.output["test_accuracy"][-1],
                        "loss": runner.gv.logger.output["test_loss"][-1]}, CHECKS / profile / f"round_{point}.pt")

        runner.gv.logger.log_once = checkpoint
    runner.run()
    assert len(runner.full_round_stats) == rounds
    rows = runner.full_round_stats
    assert all(row["malicious_nonzero_fraction"] is None if not row["malicious"]
               else 0 <= row["malicious_nonzero_fraction"] <= 1 for row in rows)
    save(CHECKS / profile / "verification.json", {"rounds": rounds, "method": method,
         "malicious_nonzero_fraction": upload_activity(rows), "round_stats": rows,
         "deterministic": torch.are_deterministic_algorithms_enabled(), "torch_version": torch.__version__})
    print(f"SHORT_PASS profile={profile} rounds={rounds} uploads={sum(r['malicious'] for r in rows)} pooled_nonzero={upload_activity(rows)}")


def run_checks():
    import torch
    from scripts.run_phase_b import PYTHON, save, read
    from test_phase_b import same_rng
    CHECKS.mkdir(parents=True, exist_ok=False)
    def child(action):
        path = CHECKS / f"{action}_console.log"
        with path.open("w", encoding="utf-8") as stream:
            result = subprocess.run([str(PYTHON), "-B", "-u", __file__, action], cwd=ROOT,
                                    stdout=stream, stderr=subprocess.STDOUT)
        if result.returncode:
            print(path.read_text(encoding="utf-8")[-6000:])
            raise RuntimeError(f"Verification failed: {action}; no further units started")
        print("\n".join(line for line in path.read_text(encoding="utf-8").splitlines()
                        if "PASS" in line))
    child("one-round")
    child("initialization")
    child("roots")
    child("X")
    child("Y")
    comparisons = []
    for point in (0, 10, 20):
        x = torch.load(CHECKS / "X" / f"round_{point}.pt", weights_only=False)
        y = torch.load(CHECKS / "Y" / f"round_{point}.pt", weights_only=False)
        assert x["model"].keys() == y["model"].keys()
        differences = {k: float((v-y["model"][k]).abs().max()) for k,v in x["model"].items()}
        assert all(torch.equal(v, y["model"][k]) for k,v in x["model"].items()), (point, differences)
        assert same_rng(x["rng"], y["rng"]), (point, "RNG differs")
        assert x["participants"] == y["participants"], (point, "participants differ")
        assert x["accuracy"] == y["accuracy"] and x["loss"] == y["loss"], (point, "metrics differ", x["accuracy"]-y["accuracy"], x["loss"]-y["loss"])
        comparisons.append({"round": point, "tensor_max_abs_differences": differences,
                            "max_relative_difference": 0.0, "rng_equal": True,
                            "participants_equal": True, "accuracy_difference": 0.0, "loss_difference": 0.0})
        print(f"TRAJECTORY_PASS round={point} max_abs=0 max_rel=0 RNG_equal=true accuracy_diff=0 loss_diff=0")
    child("activity")
    save(CHECKS / "checks.json", {"comparisons": comparisons, "activity": read(CHECKS / "activity/verification.json"),
         "controlled_settings": {"cudnn_deterministic": True, "cudnn_benchmark": False,
                                 "CUBLAS_WORKSPACE_CONFIG": ":4096:8", "deterministic_algorithms": True}})


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("run", "one-round", "initialization", "roots", "X", "Y", "activity"))
    action = parser.parse_args().action
    if action in ("roots", "X", "Y"):
        controlled_runtime()
    if action == "run":
        run_checks()
    elif action == "one-round":
        one_round()
    elif action == "initialization":
        initialization()
    elif action == "roots":
        roots()
    else:
        short_unit(action)
