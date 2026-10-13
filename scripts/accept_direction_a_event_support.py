r"""G1.1 only. Use E:\anaconda3\python.exe -B; no torch or training import."""

import importlib.util
import json
import sys
from dataclasses import asdict
from datetime import datetime
from fractions import Fraction
from pathlib import Path
import subprocess
import traceback
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.dont_write_bytecode = True

from direction_a.event_protocol import EventBudget, BudgetExceeded, Mechanism, digest, encode, start_watchdog

OUT = ROOT / "artifacts" / "direction_a" / "phaseG1_1_v1"
LIMITS = {"attempts": 512, "scans": 1024, "registration_bytes": 1024 ** 2,
          "event_bytes": 2 * 1024 ** 2, "evidence_bytes": 16 * 1024 ** 2,
          "retries": 2, "wall_seconds": 300,
          "phase_seconds": {"registration": 60, "events": 90, "audit": 90}}
TASKS = ("FedPCC-0.2-candidate-CIFAR10-N20-v1", "FedPCC-0.2-candidate-CIFAR100-N20-v1")


def git_output(*args):
    return subprocess.run(["git", *args], cwd=ROOT, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout


def load_tests():
    specification = importlib.util.spec_from_file_location("event_support_oracles", ROOT / "tests" / "test_direction_a_event_support.py")
    tests = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(tests)
    return tests


def main():
    if Path(sys.executable).resolve() != Path(r"E:\anaconda3\python.exe").resolve():
        raise RuntimeError("use E:\\anaconda3\\python.exe")
    record = ROOT / "docs" / "DIRECTION_A_G1_1_RUN_RECORD_v1.md"
    if not record.is_file():
        raise RuntimeError("register bounded workload before execution")
    if (OUT / "run.json").exists():
        raise RuntimeError("existing cumulative ledger; never reset it to rerun")
    budget = EventBudget(OUT / "run.json", LIMITS)
    start_watchdog(budget)
    result = {"checkpoint": "G1.1", "status": "running",
              "started_at": datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(),
              "base_commit": git_output("rev-parse", "HEAD").decode().strip(),
              "attempts_per_random_trace": 32, "main_trace_attempt_ceiling": 40,
              "input_file_sha256": {}, "tasks": {}, "tests": {}, "random_trace_audits": [],
              "forwards": 0, "actual_training_updates": 0, "gradient_requests": 0,
              "actual_predictor": "not implemented; E05/G2.1 is outside this checkpoint",
              "paired_research_repeats": 0, "search_evaluations": 0, "max_correction_retries": 1}
    try:
        prereg_raw = record.read_bytes()
        result["preregistration_sha256"] = digest(prereg_raw)
        budget.consume("evidence_bytes", len(prereg_raw), "exact preregistration preservation")
        (OUT / "preregistration.md").write_bytes(prereg_raw)
        for name in ("DIRECTION_A_CHECKPOINTS_v1.md", "DIRECTION_A_PROTOCOL_FREEZE_v1.md", "DIRECTION_A_0_2_ACCEPTANCE_v1.md",
                     "DIRECTION_A_0_2_ADJUDICATION_v1.md", "RESEARCH_INNOVATIONS_v1.md", "DIRECTION_A_FEASIBILITY_v1.md"):
            result["input_file_sha256"]["docs/" + name] = digest((ROOT / "docs" / name).read_bytes())
        from direction_a.event_registration import read_sealed_task, register_task
        from direction_a.invitation_events import make_exogenous_plan, speed_assignments, generate_trace, EventSimulator
        from direction_a.event_diagnostics import support_evidence
        import numpy as np
        result["environment"] = {"python": sys.executable, "numpy": np.__version__, "rng": "PCG64",
                                 "random_u_grid": "53-bit uniform", "torch_loaded": "torch" in sys.modules}
        assert "torch" not in sys.modules
        mechanism = Mechanism()
        budget.write(OUT / "mechanism.json", {"mechanism": mechanism.manifest(), "run_limits": LIMITS,
                                             "binding": "event smoke only; no actual training/resource-budget freeze",
                                             "registration": "local UTF-8 loopback, independent bootstrap",
                                             "zero_network_training": True})
        tests = load_tests()
        budget.enter("registration")
        baseline_manifest_path = "artifacts/direction_a/phase0_2_v1/artifact_hashes.json"
        baseline_raw = (ROOT / baseline_manifest_path).read_bytes()
        if baseline_raw != git_output("show", "HEAD:" + baseline_manifest_path):
            raise ValueError("0.2 hash manifest differs from preflight commit; stop")
        result["input_file_sha256"][baseline_manifest_path] = digest(baseline_raw)
        baseline = json.loads(baseline_raw)
        tasks, registries, registration_records = {}, {}, {}
        for identity in TASKS:
            folder = ROOT / "artifacts" / "direction_a" / "phase0_2_v1" / "tasks" / identity
            task = read_sealed_task(folder, baseline, budget)
            registry, registration = register_task(task, budget)
            tasks[task.dataset], registries[task.dataset] = task, registry
            registration_records[task.dataset] = registration
            budget.write(OUT / f"registration_{task.dataset}.json", registration)
            result["tasks"][task.dataset] = {"identity": task.identity, "classes": task.classes,
                                             "clients": len(task.ids), "source_file_sha256": task.file_hashes,
                                             "sealed_N_c": list(task.N_c), "sealed_n_ic_shape": [20, task.classes],
                                             "registered_ids": list(registry.entries), "train_counts_recomputed": False,
                                             "indices_repartitioned": False}
            result["tests"]["registration_" + task.dataset] = tests.audit_registration(task, registry, registration, budget)
            print(f"Registration pass: {task.dataset} all 20 clients; encoded up={registration['registration_uplink_encoded_bytes']} down={registration['registration_downlink_encoded_bytes']}", flush=True)
        budget.status_checkpoint()

        budget.enter("events")
        plan = make_exogenous_plan(tasks["CIFAR10"].ids, mechanism, 32, budget)
        plan_hash = budget.write(OUT / "exogenous_plan.json", plan)
        assignments, supports, traces = {}, {}, []
        for dataset, task in tasks.items():
            assignment = speed_assignments(task, budget)
            assignments[dataset] = assignment
            supports[dataset] = support_evidence(task, assignment, mechanism, budget)
        budget.write(OUT / "speed_assignments.json", assignments)
        for dataset, support in supports.items():
            budget.write(OUT / f"support_{dataset}.json", support)
            result["tasks"][dataset]["nonzero_source_pairs_per_scenario"] = support["nonzero_source_pairs_per_scenario"]
        # The same immutable plan precedes every paired scenario; no result-based filtering.
        for dataset, task in tasks.items():
            for scenario, speeds in assignments[dataset]["assignments"].items():
                trace = generate_trace(task, registries[dataset], speeds, scenario, mechanism, plan, budget)
                trace["plan_sha256"] = plan_hash
                filename = f"trace_{dataset}_{scenario}.json"
                budget.write(OUT / filename, trace)
                traces.append((filename, dataset, trace))
                print(f"Generated {dataset}/{scenario}: 32 attempts, planned 8 each", flush=True)
        fixture = tests.coverage_plan(tasks["CIFAR10"].ids)
        fixture_speeds = {client_id: "1" if i < 10 else "4" for i, client_id in enumerate(tasks["CIFAR10"].ids)}
        fixture_sim = EventSimulator(mechanism, tasks["CIFAR10"].identity, registries["CIFAR10"], fixture_speeds,
                                     "coverage:handwritten", budget, cap=8)
        fixture_attempts = [fixture_sim.step(item["planned_ids"], item["latent"]) for item in fixture["attempts"]]
        fixture_trace = {"trace_id": "coverage:handwritten", "kind": "deterministic_branch_boundary_fixture",
                         "task_identity": tasks["CIFAR10"].identity, "attempts": fixture_attempts,
                         "speed_seconds_per_work_unit": fixture_speeds, "actual_model_updates": 0,
                         "excluded_from_random_empirical_rates": True, "fixture_note": fixture["fixture_note"]}
        budget.write(OUT / "coverage_plan.json", fixture)
        budget.write(OUT / "coverage_trace.json", fixture_trace)
        budget.status_checkpoint()

        budget.enter("audit")
        result["tests"]["scalar_oracles"] = tests.run_scalar_oracles(mechanism, registries["CIFAR10"], tasks["CIFAR10"].ids, budget)
        result["tests"]["budget_oracles"] = tests.run_budget_oracles(budget)
        # Re-read files: scalar audit + actual simulator replay, both under same budget.
        stored_plan = json.loads((OUT / "exogenous_plan.json").read_bytes())
        replay_passes = []
        for filename, dataset, _ in traces:
            stored = json.loads((OUT / filename).read_bytes())
            audit = tests.audit_trace(stored, stored_plan, mechanism, budget)
            result["random_trace_audits"].append(audit)
            replay_sim = EventSimulator(mechanism, stored["task_identity"], registries[dataset], stored["speed_seconds_per_work_unit"],
                                        "replay:" + stored["trace_id"], budget, cap=40)
            replayed = [replay_sim.step(item["planned_ids"], item["latent"]) for item in stored_plan["attempts"]]
            if replayed != stored["attempts"]:
                raise AssertionError("event replay not exact")
            replay_passes.append({"trace_file": filename, "status": "exact", "attempts": 32})
        stored_fixture = json.loads((OUT / "coverage_trace.json").read_bytes())
        stored_fixture_plan = json.loads((OUT / "coverage_plan.json").read_bytes())
        coverage_audit = tests.audit_trace(stored_fixture, stored_fixture_plan, mechanism, budget)
        assert coverage_audit["round_ids"] == [0, 1, 1, 1]
        assert coverage_audit["empty_attempts"] == 2
        assert coverage_audit["logical_successful_slots"] == 2
        assert all(coverage_audit["event_totals"][kind] > 0 for kind in coverage_audit["event_totals"])
        replay_fixture_sim = EventSimulator(mechanism, stored_fixture["task_identity"], registries["CIFAR10"], fixture_speeds,
                                            "replay:coverage", budget, cap=8)
        assert [replay_fixture_sim.step(item["planned_ids"], item["latent"]) for item in stored_fixture_plan["attempts"]] == stored_fixture["attempts"]
        result["tests"]["coverage"] = coverage_audit
        result["tests"]["replay"] = replay_passes + [{"trace_file": "coverage_trace.json", "status": "exact", "attempts": 4}]
        budget.scan("independent_every_source_and_same_speed_set_support_audit")
        for dataset, task in tasks.items():
            assignment = assignments[dataset]
            support = json.loads((OUT / f"support_{dataset}.json").read_bytes())
            assert len(support["probabilities"]) == 60
            expected_pairs = {(scenario, client_id, c) for scenario in ("random", "tail_slow", "tail_fast")
                              for i, client_id in enumerate(task.ids) for c, n in enumerate(task.n_ic[i]) if n > 0}
            actual_pairs = {(row["scenario"], row["client_id"], row["class_id"]) for row in support["nonzero_sources"]}
            assert actual_pairs == expected_pairs and len(actual_pairs) == len(support["nonzero_sources"])
            for scenario, speeds in assignment["assignments"].items():
                assert sorted(Fraction(s) for s in speeds.values()) == [Fraction(1)] * 10 + [Fraction(4)] * 10
            for row in support["nonzero_sources"]:
                assert Fraction(row["q_fraction"]) == Fraction(2, 5)
                assert Fraction(row["r_true_grid_fraction"]) > 0 and Fraction(row["p_true_grid_fraction"]) > 0
            expected_high = sorted(task.ids, key=lambda client_id: (-Fraction(assignment["tail_share"][client_id]), client_id))[:10]
            assert {client_id for client_id, speed in assignment["assignments"]["tail_slow"].items() if speed == "4"} == set(expected_high)
            assert {client_id for client_id, speed in assignment["assignments"]["tail_fast"].items() if speed == "1"} == set(expected_high)
        result["tests"]["support"] = "all nonzero sealed sources across all three scenarios; positive exact fractions; same multiset and rank ties"
        channel = tests.audit_diagnostic_separation(ROOT, [trace for _, _, trace in traces] + [fixture_trace], budget)
        budget.write(OUT / "diagnostic_channel_audit.json", channel)
        result["tests"]["diagnostic_separation"] = channel
        budget.scan("final input-byte preservation and implementation fingerprints")
        for relative, expected in result["input_file_sha256"].items():
            assert digest((ROOT / relative).read_bytes()) == expected
        for dataset, task in tasks.items():
            folder = ROOT / "artifacts" / "direction_a" / "phase0_2_v1" / "tasks" / task.identity
            for name, expected in task.file_hashes.items():
                assert digest((folder / name).read_bytes()) == expected
        sources = [ROOT / "direction_a" / name for name in ("event_protocol.py", "event_registration.py", "invitation_events.py", "event_diagnostics.py")]
        sources += [Path(__file__).resolve(), ROOT / "tests" / "test_direction_a_event_support.py"]
        result["implementation_sha256"] = {str(path.relative_to(ROOT)).replace("\\", "/"): digest(path.read_bytes()) for path in sources}
        result["status"] = "G1.1_pass_within_declared_event_mechanism"
        result["completed_at"] = datetime.now(ZoneInfo("Asia/Shanghai")).isoformat()
        result["scope"] = "sealed-count registration/local protocol, event mechanism, exact support and diagnostic provenance; no training or G1.2/G1.3"
        result["future_revalidation"] = "changing workload/deadline/online law/assignments/target population requires G1.1 or 0.2 revalidation"
        result["payload_accounting"] = {"registration": "UTF-8 bytes actually encoded/decoded in local loopback",
                                        "events": "only dispatch and valid-return metadata bytes, including replay/test executions",
                                        "network_actual_sent_bytes": None,
                                        "model_or_gradient_payload_bytes": "not applicable; no model/gradient produced",
                                        "evidence_bytes": "cumulative actual writes + precharged 65536-byte emergency reserve; includes ledger rewrites",
                                        "simulation_time": "32*8=256 seconds per main trace; not added to actual compute time"}
        budget.write(OUT / "acceptance.json", result)
        budget.scan("final evidence hashes excluding mutable ledger and self")
        inventory = {str(path.relative_to(OUT)).replace("\\", "/"): digest(path.read_bytes())
                     for path in OUT.rglob("*") if path.is_file() and path.name not in ("run.json", "artifact_hashes.json")}
        budget.write(OUT / "artifact_hashes.json", inventory)
        assert "torch" not in sys.modules
        budget.finish()
        print(json.dumps({"status": result["status"], "counts": budget.counts,
                          "elapsed_seconds": budget.snapshot()["elapsed_seconds"],
                          "source_pairs": {name: task["nonzero_source_pairs_per_scenario"] for name, task in result["tasks"].items()}}, ensure_ascii=False), flush=True)
        return 0
    except Exception as exc:
        if not isinstance(exc, BudgetExceeded):
            budget.status = "execution_failure"
            budget.hit = {"field": "exception", "type": type(exc).__name__, "message": str(exc)}
            budget.save(reserved=True)
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
