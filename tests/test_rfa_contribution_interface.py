"""Fixed-tensor prerequisite evidence only: no task, data, forward or optimizer."""
import argparse
from collections import defaultdict
from dataclasses import asdict, replace
import hashlib
import io
import json
import math
from pathlib import Path
import random
import subprocess
import sys
import types
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "easyFL")]
import numpy as np
import torch
from aggregators.rfa import RFA, smoothed_weiszfeld
from aggregators.rfa_contributions import bind_final_mix, verify_model_writeback
from aggregators.contribution_diagnostics import trace
from flgo_byzantine.algorithm import Server, _parameter_vector, _aggregator_stats
from run_flgo_byzantine import ByzantineLogger, SimpleLogger

BASE = "b832abed31b5e34b0c0e51f09860245bb3278ab6"
OLD_SOURCE = subprocess.check_output(["git", "show", BASE+":aggregators/rfa.py"], cwd=ROOT).decode()
OLD = types.ModuleType("aggregators._acceptance_legacy_rfa")
OLD.__package__ = "aggregators"
exec(compile(OLD_SOURCE, "git:"+BASE+":aggregators/rfa.py", "exec"), OLD.__dict__)
EVIDENCE = {}


def oracle(rows, T, nu=1e-6):
    """Independent scalar math; no production RFA/helper/trace in expected values."""
    z = [0.] * len(rows[0])
    history = []
    for _ in range(T):
        beta = [(1/len(rows))/max(math.sqrt(sum((a-b)**2 for a, b in zip(z, row))), nu)
                for row in rows]
        den = sum(beta)
        weights = [b/den for b in beta]
        z = [sum(row[j]*b for row, b in zip(rows, beta))/den for j in range(len(z))]
        history.append({"betas": beta, "denominator": den, "weights": weights, "z": z})
    return history


def tensors(rows, dtype=torch.float64):
    return [torch.tensor(row, dtype=dtype) for row in rows]


class FixedModel(torch.nn.Module):
    def __init__(self, values, dtype=torch.float32):
        super().__init__()
        self.fixed = torch.nn.Parameter(torch.tensor(values, dtype=dtype))

    def forward(self, *args):
        raise AssertionError("no forward permitted in interface acceptance")


def server(theta, T, dtype=torch.float32):
    value = object.__new__(Server)
    value.option = {"seed": 13, "byz_aggregator": "rfa", "byz_attack": "none",
                    "byz_rfa_steps": T, "byz_rfa_nu": 1e-6}
    value.num_clients = 120
    value.task = "unused-fixed-tensor-task"
    value.model = FixedModel(theta, dtype)
    value.initialize()
    return value


class InterfaceChecks(unittest.TestCase):
    def close(self, actual, expected):
        torch.testing.assert_close(torch.as_tensor(actual, dtype=torch.float64),
                                   torch.as_tensor(expected, dtype=torch.float64), atol=1e-10, rtol=1e-8)

    def test_single_anchor(self):
        x = tensors([[1.], [3.]])
        a = RFA(1)
        self.assertIsNone(a.last_client_weights)
        self.assertEqual(set(a.get_attack_stats()), {"average_malicious_beta", "average_benign_beta"})
        z = a(x)
        self.close(z, [1.5])
        self.close(a.last_client_weights, [.75, .25])
        self.close(a.last_contribution_trace.final_betas, [.5, 1/6])
        self.assertFalse(torch.allclose(z, torch.tensor([2.], dtype=torch.float64), atol=1e-10, rtol=1e-8))
        default = smoothed_weiszfeld(x, [.5, .5], torch.zeros(1, dtype=torch.float64), 1e-6, 1, 5)
        expanded = smoothed_weiszfeld(x, [.5, .5], torch.zeros(1, dtype=torch.float64), 1e-6, 1, 5, return_weights=True)
        self.assertEqual(len(default), 3)
        self.assertEqual(len(expanded), 4)
        self.assertTrue(torch.equal(default[0], z))
        self.close(expanded[3], [.75, .25])
        EVIDENCE["single_anchor"] = {"inputs": [[1], [3]], "T": 1, "nu": 1e-6,
            "expected_weights": [.75, .25], "actual_weights": a.last_client_weights,
            "expected_z": [1.5], "actual_z": z.tolist(), "uniform_negative_z": 2.,
            "uniform_negative_rejected": True, "default_helper_items": len(default),
            "explicit_helper_items": len(expanded), "trace": asdict(a.last_contribution_trace)}

    def test_multiround_anchor_and_provenance(self):
        rows = [[1., 0.], [0., 1.], [-1., 0.]]
        w = [2/(4+math.sqrt(10)), math.sqrt(10)/(4+math.sqrt(10)), 2/(4+math.sqrt(10))]
        first = RFA(1)(tensors(rows))
        a = RFA(2)
        z = a(tensors(rows))
        self.close(first, [0., 1/3])
        self.close(a.last_client_weights, w)
        self.close(z, [0., w[1]])
        self.close(a.last_contribution_trace.final_betas, [1/math.sqrt(10), .5, 1/math.sqrt(10)])
        independent = oracle(rows, 3)
        self.assertGreater(max(abs(p-q) for p, q in zip(w, independent[2]["weights"])), 1e-3)
        self.assertGreater(max(abs(p-1/3) for p in w), 1e-3)
        saved = a.last_client_weights
        saved_trace = asdict(a.last_contribution_trace)
        a(tensors([[2.]]))
        self.close(saved, w)
        self.assertEqual(len(saved), 3)
        EVIDENCE["multi_anchor"] = {"inputs": rows, "T": 2, "nu": 1e-6,
            "expected_weights": w, "actual_weights": list(saved), "first_z": first.tolist(),
            "expected_z": [0., w[1]], "actual_z": z.tolist(), "independent_iterations": independent,
            "actual_trace": saved_trace,
            "next_iteration_max_weight_difference": max(abs(p-q) for p, q in zip(w, independent[2]["weights"])),
            "saved_record_independent_after_next_call": True}

    def test_old_compatibility_boundaries_and_groups(self):
        fixtures = [([[2., -1.]], 3), ([[0., 0.]]*3, 2), ([[2., -1.]]*5, 3),
            ([[1., 0.], [-1., 0.]], 4), ([[j+1., (-1.)**j] for j in range(7)], 5),
            ([[1., 0.], [0., 1.], [-1., 0.]], 2)]
        records = []
        for dtype in (torch.float64, torch.float32):
            for rows, T in fixtures:
                x = tensors(rows, dtype)
                a, old = RFA(T), OLD.RFA(T)
                z, oldz = a(x), old(x)
                self.assertIsInstance(z, torch.Tensor)
                self.assertEqual((z.shape, z.dtype, z.device), (x[0].shape, x[0].dtype, x[0].device))
                self.assertTrue(torch.equal(z, oldz))
                self.assertTrue(torch.equal(z.clone().detach(), oldz))
                self.assertEqual(a.malicious_betas, old.malicious_betas)
                self.assertEqual(a.benign_betas, old.benign_betas)
                self.assertEqual(a.get_attack_stats(), old.get_attack_stats())
                self.assertTrue(all(isinstance(v, (float, int)) for v in a.get_attack_stats().values()))
                self.assertEqual(len(a.last_client_weights), len(rows))
                self.assertTrue(all(isinstance(w, float) and math.isfinite(w) and w >= 0
                                    for w in a.last_client_weights))
                rebuilt = sum((w*v.double() for w, v in zip(a.last_client_weights, x)),
                              torch.zeros_like(z, dtype=torch.float64))
                reconstruction_error = (z.double()-rebuilt).norm().item()
                if dtype == torch.float64:
                    self.close(sum(a.last_client_weights), 1.)
                    self.close(rebuilt, z)
                else:
                    self.assertLessEqual(abs(sum(a.last_client_weights)-1.), 1e-6)
                    self.assertLessEqual(reconstruction_error, 1e-12+1e-5*z.double().norm().item())
                manual = oracle(rows, T)[-1]
                if dtype == torch.float64:
                    self.close(z, manual["z"])
                    self.close(a.last_client_weights, manual["weights"])
                    self.close(a.last_contribution_trace.final_betas, manual["betas"])
                for b in (0, 1, 5, 7):
                    grouped = RFA(T)
                    grouped.b = b
                    gz = grouped(x)
                    self.assertTrue(torch.equal(gz, z))
                    self.assertEqual(grouped.last_client_weights, a.last_client_weights)
                records.append({"m": len(rows), "T": T, "dtype": str(dtype), "inputs": rows,
                    "old_z": oldz.tolist(), "new_z": z.tolist(), "bitwise_equal": True,
                    "weights": a.last_client_weights, "sum_weights": sum(a.last_client_weights),
                    "aggregate_reconstruction_error": reconstruction_error,
                    "old_stats_equal": True, "groups_checked": [0, 1, 5, 7],
                    "actual_final_trace": asdict(a.last_contribution_trace),
                    "independent_scalar_final": manual})
        a = RFA(2)
        batches = []
        for m in (7, 1, 5, 3):
            z = a(tensors([[j+1.] for j in range(m)]))
            self.assertEqual(len(a.last_client_weights), m)
            self.close(z, oracle([[j+1.] for j in range(m)], 2)[-1]["z"])
            batches.append({"m": m, "call_id": a.last_contribution_trace.call_id, "weights": a.last_client_weights})
        EVIDENCE["compatibility_and_boundaries"] = {"cases": records, "continuous_batches": batches}

    def test_identity_and_actual_bridge_writeback(self):
        ids = [41, 7, 103]
        rows = [[1., 0.], [0., 1.], [-1., 0.]]
        manual = oracle(rows, 2)[-1]
        s = server([16., 32.], 2)
        s.received_clients = ids
        s.byz_malicious_ids = frozenset([7])
        models = [FixedModel([16-u[0], 32-u[1]]) for u in rows]
        with patch("flgo_byzantine.algorithm.load_root_data", side_effect=AssertionError("root forbidden")):
            new = s.aggregate(models)
        actual = _parameter_vector(new)
        expected = (torch.tensor([16., 32.], dtype=torch.float64)
                    -torch.tensor(manual["z"], dtype=torch.float32).double()).float()
        self.assertTrue(torch.equal(actual, expected))
        record = json.loads(json.dumps(s.byz_last_contribution, allow_nan=False))
        for entry, cid, row, w in zip(record["clients"], ids, rows, manual["weights"]):
            self.assertEqual(entry["client_id"], cid)
            self.assertAlmostEqual(entry["weight"], w, delta=1e-7)
            self.assertEqual(entry["is_malicious"], cid == 7)
            self.assertAlmostEqual(entry["model_coefficient"], -w, delta=1e-7)
        self.assertTrue(record["writeback_checks"]["writeback_exact"])
        s2 = server([16., 32.], 2)
        order = [2, 0, 1]
        s2.received_clients = [ids[i] for i in order]
        s2.byz_malicious_ids = frozenset([41, 103])
        new2 = s2.aggregate([models[i] for i in order])
        self.assertTrue(torch.equal(_parameter_vector(new2), actual))
        mapped = {c["client_id"]: c["weight"] for c in s2.byz_last_contribution["clients"]}
        for c in record["clients"]:
            self.assertAlmostEqual(mapped[c["client_id"]], c["weight"], delta=1e-7)
        self.assertIsNone(s._byz_root_data)
        # Same ordered inputs with different truth: no change to z/weights.
        s.byz_malicious_ids = frozenset([41])
        again = s.aggregate(models)
        self.assertTrue(torch.equal(_parameter_vector(again), actual))
        self.assertEqual([c["weight"] for c in record["clients"]],
                         [c["weight"] for c in s.byz_last_contribution["clients"]])
        EVIDENCE["identity_bridge"] = {"inputs": rows, "ids": ids, "theta": [16., 32.],
            "expected_scalar_weights": manual["weights"], "actual_new_parameters": actual.tolist(),
            "independent_reference_parameters": expected.tolist(), "record": record,
            "contributions_by_id": {str(c["client_id"]): [-c["weight"]*v for v in row]
                                     for c, row in zip(record["clients"], rows)},
            "permuted_record": s2.byz_last_contribution, "truth_only_changes_diagnostic": True,
            "root_read_calls": 0}

    def test_failures_and_freshness(self):
        cases = [("T_zero", {"T": 0}, [[1.]]), ("T_negative", {"T": -1}, [[1.]]),
            ("T_fraction", {"T": 1.5}, [[1.]]), ("T_bool", {"T": True}, [[1.]]),
            ("nu_zero", {"nu": 0}, [[1.]]), ("nu_negative", {"nu": -1}, [[1.]]),
            ("nu_nan", {"nu": float("nan")}, [[1.]]), ("nu_inf", {"nu": float("inf")}, [[1.]]),
            ("nu_bool", {"nu": True}, [[1.]]), ("empty", {}, []),
            ("input_nan", {}, [[float("nan")]]), ("input_inf", {}, [[float("inf")]]),
            ("norm_overflow_den_zero", {}, [[1e308, 1e308]]),
            ("beta_overflow_den_nonfinite", {"nu": 1e-320}, [[0.]])]
        results = []
        for name, settings, rows in cases:
            a = RFA(1)
            a(tensors([[1.], [3.]]))
            for key, val in settings.items():
                setattr(a, key, val)
            with self.assertRaises(ValueError) as caught:
                a(tensors(rows))
            self.assertIsNone(a.last_client_weights)
            self.assertIsNone(a.last_contribution_trace)
            self.assertEqual(a.get_attack_stats(), {"average_malicious_beta": 0, "average_benign_beta": 0})
            results.append({"case": name, "exception": str(caught.exception), "weights_after": None,
                            "trace_after": None, "stats_after": a.get_attack_stats()})
        for name, values in [("shape", tensors([[1.], [1., 2.]])),
                             ("dtype", [torch.ones(1, dtype=torch.float32), torch.ones(1, dtype=torch.float64)]),
                             ("device", [torch.ones(1), torch.ones(1, device="meta")]),
                             ("empty_vector", [torch.empty(0)]),
                             ("integer", [torch.ones(1, dtype=torch.int64)])]:
            a = RFA(1)
            with self.assertRaises(ValueError):
                a(values)
            self.assertIsNone(a.last_client_weights)
            results.append({"case": name, "rejected": True})
        with self.assertRaises(ValueError):
            smoothed_weiszfeld(tensors([[1.]]), [0.], torch.zeros(1, dtype=torch.float64), 1e-6, 1, 5)
        results.append({"case": "zero_alpha_denominator", "rejected": True})
        s = server([16.], 1)
        models = [FixedModel([15.]), FixedModel([13.])]
        for name, ids, supplied in [("ID_length", [41], models), ("ID_duplicate", [7, 7], models),
                                     ("empty_bridge", [], [])]:
            s.received_clients = [41, 7]
            s.aggregate(models)
            s.received_clients = ids
            with self.assertRaises(ValueError) as caught:
                s.aggregate(supplied)
            self.assertIsNone(s.byz_last_contribution)
            self.assertIsNone(s._byz_aggregator_instance.last_client_weights)
            results.append({"case": name, "exception": str(caught.exception), "boundary_record_after": None})
        EVIDENCE["failures"] = results

    def test_mandatory_negative_records_and_model_errors(self):
        x = tensors([[1.], [3.]])
        a = RFA(1)
        z = a(x)
        original = a.last_contribution_trace
        cases = [("weights_missing", None, original), ("weights_wrong_length", (.75,), original),
            ("old_call", (.75, .25), replace(original, call_id=0)),
            ("wrong_input_order", (.75, .25), replace(original, input_fingerprints=tuple(reversed(original.input_fingerprints)))),
            ("invalid_denominator", (.75, .25), replace(original, denominator=0.)),
            ("uniform_fitted", (.5, .5), replace(original, weights=(.5, .5))),
            ("wrong_weights", (.25, .75), replace(original, weights=(.25, .75))),
            ("wrong_semantics", (.75, .25), replace(original, semantics="causal"))]
        results = []
        for name, weights, record in cases:
            a.last_client_weights, a.last_contribution_trace = weights, record
            with self.assertRaises(ValueError) as caught:
                bind_final_mix(a, x, [41, 7], z, 1, 1)
            results.append({"case": name, "exception": str(caught.exception)})
        a.last_client_weights, a.last_contribution_trace = original.weights, original
        a(x)
        a.last_contribution_trace = original
        with self.assertRaises(ValueError):
            bind_final_mix(a, x, [41, 7], z, 2, 2)
        results.append({"case": "previous_success_same_inputs", "old_call_id": 1,
                        "current_call_id": 2, "rejected": True})
        rows = [[1., 0.], [0., 1.], [-1., 0.]]
        multi = RFA(2)
        mz = multi(tensors(rows))
        for name, wrong in [("first_iteration_weights", [1/3]*3),
                             ("next_iteration_weights", oracle(rows, 3)[-1]["weights"])]:
            multi.last_client_weights = tuple(wrong)
            multi.last_contribution_trace = replace(multi.last_contribution_trace, weights=tuple(wrong))
            with self.assertRaises(ValueError):
                bind_final_mix(multi, tensors(rows), [41, 7, 103], mz, 1, 1)
            results.append({"case": name, "wrong_weights": wrong, "rejected": True})
        # Reconstruction alone is insufficient for duplicate inputs.
        same = tensors([[1.], [1.]])
        a = RFA(1)
        zsame = a(same)
        a.last_client_weights = (.2, .8)
        a.last_contribution_trace = replace(a.last_contribution_trace, weights=(.2, .8))
        self.close(.2*same[0]+.8*same[1], zsame)
        with self.assertRaises(ValueError):
            bind_final_mix(a, same, [41, 7], zsame, 1, 1)
        results.append({"case": "reconstructible_but_not_final_beta", "reconstruction_matches": True, "rejected": True})
        xf = tensors([[1.], [3.]], torch.float32)
        a = RFA(1)
        zf = a(xf)
        _, correct = bind_final_mix(a, xf, [41, 7], zf, 1, 1)
        theta = torch.tensor([16.], dtype=torch.float32)
        new = torch.tensor([14.5], dtype=torch.float32)
        good = verify_model_writeback(correct, theta, zf, new)
        zero = torch.zeros_like(zf)
        for name, coefs in [("omitted_client", [-.75, 0.]), ("flipped_sign", [.75, .25]),
                             ("swapped_weights", [-.25, -.75])]:
            bad = trace(xf, [zero]*2, coefs, [0.]*2, zero, zero)
            with self.assertRaises(ValueError) as caught:
                verify_model_writeback(bad, theta, zf, new)
            results.append({"case": name, "exception": str(caught.exception)})
        # Independent rounding stress: 1e8 - 1.5 rounds back to 1e8 in float32.
        large = torch.tensor([1e8], dtype=torch.float32)
        rounded = torch.tensor([1e8], dtype=torch.float32)
        checks = verify_model_writeback(correct, large, zf, rounded)
        self.assertEqual(checks["E_alg"], 0.)
        self.assertEqual(checks["q_norm"], 1.5)
        self.assertEqual(checks["E_model"], 1.5)
        with self.assertRaises(ValueError):
            verify_model_writeback(correct, theta, zf, theta+zf)
        results.append({"case": "wrong_actual_parameter_writeback", "rejected": True})
        EVIDENCE["mandatory_negatives"] = results
        EVIDENCE["float32_layers"] = {"exact_case": good, "rounding_stress": checks,
                                      "client_contributions": [-.75, -.75], "q_assigned_to_clients": False}

    def test_consumer_failure_clears_and_observation_isolation(self):
        s = server([16.], 1)
        s.received_clients = [41, 7]
        models = [FixedModel([15.]), FixedModel([13.])]
        s.aggregate(models)
        instance = s._byz_aggregator_instance
        real = RFA.__call__
        failures = []
        for name in ("missing", "length", "stale"):
            def broken(obj, inputs, case=name):
                value = real(obj, inputs)
                if case == "missing":
                    obj.last_client_weights = None
                elif case == "length":
                    obj.last_client_weights = (.75,)
                else:
                    obj.last_contribution_trace = replace(obj.last_contribution_trace, call_id=0)
                return value
            with patch.object(RFA, "__call__", broken):
                with self.assertRaises(ValueError):
                    s.aggregate(models)
            self.assertIsNone(s.byz_last_contribution)
            self.assertIsNone(instance.last_client_weights)
            self.assertIsNone(instance.last_contribution_trace)
            self.assertEqual(s.byz_last_round, {})
            failures.append({"case": name, "rejected": True, "weights_after": None, "boundary_after": None})
        s.aggregate(models)
        py_before, np_before, torch_before = random.getstate(), np.random.get_state(), torch.get_rng_state().clone()
        immutable = instance.last_contribution_trace
        old_weights = instance.last_client_weights
        for logging in (False, True):
            for _ in range(3):
                stats = _aggregator_stats(instance)
                if logging:
                    json.dumps({"stats": stats, "record": s.byz_last_contribution}, allow_nan=False)
        logger = object.__new__(ByzantineLogger)
        logger.coordinator = s
        logger.output = defaultdict(list)
        with patch.object(SimpleLogger, "log_once", return_value=None):
            logger.log_once()
        self.assertEqual(logger.output["byz_rfa_contribution"][0], s.byz_last_contribution)
        self.assertIsNot(logger.output["byz_rfa_contribution"][0], s.byz_last_contribution)
        self.assertEqual(set(logger.output["byz_aggregator_stats"][0]),
                         {"average_malicious_beta", "average_benign_beta"})
        self.assertEqual(py_before, random.getstate())
        np_after = np.random.get_state()
        self.assertEqual(np_before[0], np_after[0])
        self.assertTrue(np.array_equal(np_before[1], np_after[1]))
        self.assertEqual(np_before[2:], np_after[2:])
        self.assertTrue(torch.equal(torch_before, torch.get_rng_state()))
        self.assertIs(instance.last_contribution_trace, immutable)
        self.assertIs(instance.last_client_weights, old_weights)
        with patch.object(instance, "get_attack_stats", side_effect=RuntimeError("optional stats fault")):
            no_stats_model = s.aggregate(models)
        self.assertEqual(_parameter_vector(no_stats_model).tolist(), [14.5])
        self.assertNotIn("aggregator_stats", s.byz_last_round)
        self.assertIsNotNone(s.byz_last_contribution)
        EVIDENCE["observation_isolation"] = {"consumer_failures": failures, "logging_switches": [False, True],
            "python_numpy_torch_cpu_rng_unchanged": True, "record_same_object_on_reads": True,
            "actual_logger_dedicated_record_equal": True, "logger_record_independent_copy": True,
            "optional_getter_fault_model": [14.5], "optional_fault_contribution_preserved": True,
            "old_stats_fields": list(instance.get_attack_stats())}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path)
    args = parser.parse_args()
    output = io.StringIO()
    result = unittest.TextTestRunner(stream=output, verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(InterfaceChecks))
    print(output.getvalue(), file=sys.stderr, end="")
    if args.manifest:
        paths = ["docs/D2_PRIME_RFA_CONTRIBUTION_RULING.md", "docs/D2_PRIME_PHASE1_REPORT.md",
                 "docs/D2_PRIME_PHASE1_MANIFEST.json", "aggregators/rfa.py", "aggregators/rfa_contributions.py",
                 "flgo_byzantine/algorithm.py", "run_flgo_byzantine.py", "tests/test_rfa_contribution_interface.py"]
        data = {"formal_verdict": "PENDING_USER_OR_REVIEW_AGENT", "baseline_commit": BASE,
            "ruling_date": "2026-10-09", "interpreter": sys.executable,
            "python_version": sys.version, "torch_version": str(torch.__version__),
            "configuration": {"inputs": "fixed tensors only", "training_runs": 0, "task": None,
                "algorithm_semantics": "rfa_final_mix_v1", "float64_atol": 1e-10, "float64_rtol": 1e-8,
                "training_authority": "ruling sections 4 training input and 5.1/5.3; user explicitly rejects IR50 authorization; future DESIGN section 6 IR5 alpha1"},
            "tests_run": result.testsRun, "failures": len(result.failures), "errors": len(result.errors),
            "command_argv": [sys.executable, "-B", *sys.argv], "unittest_output": output.getvalue(),
            "observed_assertions_satisfied": result.wasSuccessful(),
            "legacy_source_sha256": hashlib.sha256(OLD_SOURCE.encode()).hexdigest(),
            "sha256": {p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths},
            "evidence": EVIDENCE}
        args.manifest.write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False)+"\n", encoding="utf-8")
    sys.exit(0 if result.wasSuccessful() else 1)
