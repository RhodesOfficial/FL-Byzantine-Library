"""Independent fixed-input path, combination-coefficient, and null-direction checks."""
import copy
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "easyFL"), str(ROOT / "tests")]
import torch
from aggregators.contribution_diagnostics import (group_cosines, summarize, trace,
    two_layer_errors, require_two_layers)
from aggregators.d1_category_coverage import D1CategoryCoverage
from aggregators.d1_reference_baselines import RootBaseline, B_BASELINE_VERSION
from test_d1_category_coverage import fixture, RandomizedCalculator
from test_phase_b import rng_state, same_rng


class ContributionTests(unittest.TestCase):
    path_results = []

    def setUp(self):
        torch.set_num_threads(1)
        if torch.cuda.is_available():
            torch.cuda.get_rng_state_all()

    def assert_neutral(self, original, inputs, label):
        off, on = copy.deepcopy(original), copy.deepcopy(original)
        on.collect_contributions = True
        before = rng_state()
        a = off(inputs)
        after_off = rng_state()
        b = on(inputs)
        after_on = rng_state()
        self.assertTrue(torch.equal(a, b))
        self.assertTrue(same_rng(before, after_off) and same_rng(after_off, after_on))
        self.assertEqual(off.last_client_weights, on.last_client_weights)
        if isinstance(on, D1CategoryCoverage):
            self.assertEqual(off.last_stats, on.last_stats)
            self.assertEqual(off.last_diagnostics, on.last_diagnostics)
        summary = summarize(on.last_contribution_trace, -b)
        if isinstance(on, D1CategoryCoverage):
            theta = torch.nn.utils.parameters_to_vector(on.context.model.parameters()).detach().clone()
        else:
            theta = torch.tensor([.12345, -.54321])
        displacement = -b
        theta_new = theta + displacement
        checks = two_layer_errors(on.last_contribution_trace, theta, displacement, theta_new)
        from scripts.run_phase_b import save
        directory = ROOT / "outputs/d1_3b/phase_b_contribution_v2_20261004/unit_cases"
        directory.mkdir(parents=True, exist_ok=True)
        method = getattr(on, "method", "d1")
        self.path_results.append(dict(method=method, path=label, **checks))
        save(directory / "paths.json", self.path_results)
        torch.save({"theta": theta, "uploads": inputs, "d": displacement,
                    "theta_new": theta_new, "trace": on.last_contribution_trace,
                    "return_path": on.last_stats.get("fallback", label), "checks": checks},
                   directory / f"{method}_{label}.pt")
        require_two_layers(checks)
        self.assertEqual(len(summary["client_parallel_coef"]), len(inputs))
        print(f"PATH_PASS method={getattr(on, 'method', 'd1')} path={on.last_stats.get('fallback', 'baseline')} "
              f"case={label} E_alg={checks['E_alg']:.9g} E_model={checks['E_model']:.9g} "
              f"d_norm={checks['d_norm']:.9g} q_norm={checks['q_norm']:.9g} tau_rel={checks['tau_rel']} "
              "two_layers=true output_bitwise=true four_rng=true")
        return on, summary

    def test_d1_return_paths(self):
        paths = [
            ("success", fixture(False, candidate_lambdas=(1.,), loss_tolerance=1.),
             [torch.tensor([-.3, -1.])] * 3, "none"),
            ("root", fixture(False, drag_strength=0., loss_tolerance=0., candidate_lambdas=(0.,)),
             [torch.tensor([.4, 0.])], "root"),
            ("zero_residual", fixture(False, candidate_lambdas=(1.,)),
             [torch.tensor([-.3, 0.])] * 3, "none"),
            ("no_reliable", fixture(False, min_class_count=100),
             [torch.tensor([-.3, -.1])], "skip_no_reliable_class"),
        ]
        skip = fixture(False)
        skip._feasible = lambda *args: None
        paths.append(("audit_skip", skip, [torch.tensor([-.3, -.1])], "skip_audit"))
        no_root = fixture(False)
        no_root._root_evidence = lambda model: (torch.tensor([[1., 0.]]), {0: torch.tensor([0.])},
                                               [0], {0: 4, 1: 0}, {0: 1., 1: 0.})
        paths.append(("no_root", no_root, [torch.tensor([-.3, -.1])], "skip_no_root_direction"))
        clipped = fixture(False, candidate_lambdas=(1.,), loss_tolerance=1.)
        clipped.clip_norm = .03
        paths.append(("final_cap", clipped, [torch.tensor([-.3, -1.])] * 3, "none"))
        for name, agg, inputs, expected in paths:
            with self.subTest(path=name):
                agg.context.calculator = RandomizedCalculator()
                on, result = self.assert_neutral(agg, inputs, name)
                self.assertEqual(on.last_stats["fallback"], expected)
                if name in {"zero_residual", "root", "audit_skip", "no_reliable", "no_root"}:
                    self.assertEqual(on.last_contribution_trace["final_residual"].norm().item(), 0)
                if name in {"audit_skip", "no_reliable", "no_root"}:
                    self.assertEqual(result["client_contrib_along_final"], [None] * len(inputs))

    def test_actual_median_combinations(self):
        for name, points, steps in (
                ("hit_point", [[0., 0.], [1., 0.], [-1., 0.]], 20),
                ("converged", [[0., 0.], [1., 0.]], 20),
                ("iteration_limit", [[0., 0.], [2., 0.], [0., 1.]], 1)):
            agg = object.__new__(D1CategoryCoverage)
            agg.median_steps = steps
            vectors = [torch.tensor(x) for x in points]
            off = agg._geometric_median(vectors)
            agg.collect_contributions = True
            on = agg._geometric_median(vectors)
            self.assertTrue(torch.equal(off, on))
            combination = (torch.stack(vectors).double() * agg._median_combination.double()[:, None]).sum(0)
            self.assertTrue(torch.allclose(combination, on.double(), atol=1e-7, rtol=1e-6))
            if name == "hit_point":
                self.assertEqual(agg._median_combination.tolist(), [1., 0., 0.])
            print(f"MEDIAN_PASS path={name} coefficients={agg._median_combination.tolist()} bitwise=true")

    def test_baseline_zero_and_nonzero(self):
        from types import SimpleNamespace
        root_data = [(torch.tensor([1., 0.]), i % 8) for i in range(2000)]
        context = SimpleNamespace(root_data=root_data)
        for method in ("brdrag", "balanced_brdrag"):
            for root in (torch.tensor([.1, -.2]), torch.zeros(2)):
                agg = RootBaseline(context, 10, method, version=B_BASELINE_VERSION, root_budget=2000)
                agg._root = lambda: root.clone()
                on, result = self.assert_neutral(agg, [torch.tensor([.3, .1]), torch.zeros(2), torch.tensor([-.2, .4])],
                                                 "nonzero_root" if root.norm() > 0 else "zero_root")
                self.assertEqual(result["client_residual_coef"], [0., 0., 0.])
                self.assertEqual(result["client_parallel_coef"][1], 0)

    def test_group_cosine_and_signed_projection(self):
        p = [torch.tensor([1., 0.]), torch.tensor([-2., 0.])]
        e = [torch.tensor([0., 1.]), torch.tensor([0., -1.])]
        value = trace(p, e, [1., 1.], [0., 0.], torch.tensor([2., 0.]), torch.tensor([0., 1.]))
        stats = summarize(value, torch.tensor([1., 0.]))
        self.assertEqual(stats["client_contrib_along_final"], [1., -2.])
        groups = group_cosines(value, {"empty": [], "zero_mean": [0, 1], "positive": [0], "negative": [1]})
        self.assertEqual(groups, {"empty": None, "zero_mean": None, "positive": 1., "negative": -1.})
        value["final_residual"] = torch.zeros(2)
        self.assertTrue(all(v is None for v in group_cosines(value, {"a": [0], "b": []}).values()))
        print("GROUP_PASS empty/zero_mean/zero_residual=null; signed_projection_not_probability=true")

    def test_writeback_scales(self):
        from scripts.run_phase_b import save
        rows = []
        theta = torch.linspace(-.5, .5, 4096)
        direction = (torch.arange(4096, dtype=torch.float64) % 17) - 8
        direction /= direction.norm()
        zero = torch.zeros_like(theta)
        for size in (.1, .03, 1e-4, 0.):
            d = (direction * size).float()
            value = trace([d], [zero], [1.], [0.], zero, zero)
            new = theta + d  # Actual float32 writeback; independent reference is inside the checker.
            checks = two_layer_errors(value, theta, d, new)
            rows.append(dict(requested_norm=size, **checks))
            directory = ROOT / "outputs/d1_3b/phase_b_contribution_v2_20261004/unit_cases"
            directory.mkdir(parents=True, exist_ok=True)
            save(directory / "writeback_scales.json", rows)
            torch.save({"theta": theta, "d": d, "theta_new": new, "trace": value, "checks": checks},
                       directory / f"writeback_{size}.pt")
            require_two_layers(checks)
            if size == 0:
                self.assertIsNone(checks["tau_rel"])
                self.assertIsNone(summarize(value, new.double() - theta.double())["decomposition_error"])
            print(f"WRITEBACK_PASS requested_norm={size} checks={checks}")

    def test_rounding_never_absorbs_missing_contribution(self):
        theta = torch.ones(2)
        d = torch.tensor([1e-10, -1e-10])
        zero = torch.zeros_like(d)
        good = trace([d], [zero], [1.], [0.], zero, zero)
        checks = two_layer_errors(good, theta, d, theta + d)
        require_two_layers(checks)
        self.assertEqual(checks["delta_norm"], 0.)
        self.assertIsNone(checks["tau_rel"])
        self.assertEqual(summarize(good, zero.double())["client_contrib_along_final"], [None])
        missing = trace([d], [zero], [0.], [0.], zero, zero)
        bad = two_layer_errors(missing, theta, d, theta + d)
        self.assertEqual(bad["q_norm"], checks["q_norm"])
        self.assertFalse(bad["layer1_pass"])
        with self.assertRaisesRegex(ValueError, "pre-write"):
            require_two_layers(bad)
        wrong = two_layer_errors(good, theta, d, theta + .001)
        self.assertFalse(wrong["writeback_exact"])
        print("NEGATIVE_CONTROLS_PASS missing_contribution_rejected; q_independent; wrong_writeback_rejected; zero_delta_null")


if __name__ == "__main__":
    unittest.main(verbosity=2)
