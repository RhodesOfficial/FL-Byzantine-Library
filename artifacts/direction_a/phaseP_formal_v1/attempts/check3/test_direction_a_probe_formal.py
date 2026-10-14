"""CPU arithmetic and injected production lifecycle; no extra fitting."""
import math
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
import torch
from direction_a import probe_formal as f
import direction_a.probe_startup as startup

ROOT=Path(__file__).resolve().parents[1]
SYNTHETIC_FORWARDS=0
SYNTHETIC_SCANS=0


class SyntheticBudget:
    def scan(self):
        global SYNTHETIC_SCANS
        SYNTHETIC_SCANS+=1
    def consume(self,name,amount=1):
        global SYNTHETIC_FORWARDS
        if name!="forwards": raise AssertionError("synthetic checks cannot fit/backpropagate/update")
        SYNTHETIC_FORWARDS+=amount


class Arithmetic(unittest.TestCase):
    def test_unequal_class_equal_CE_and_complete_100_dimensions(self):
        b=SyntheticBudget()
        logits=torch.tensor([[math.log(3),0.],[0.,math.log(3)],[0.,math.log(3)],[0.,math.log(3)]])
        y=torch.tensor([0,0,0,1]); counts=torch.tensor([3.,1.])
        f.validate_loss_inputs(logits,y,counts); b.consume("forwards")
        actual=float(f.class_loss(logits,y,counts))
        expected=((math.log(4/3)+2*math.log(4))/3+math.log(4/3))/2
        sample=(2*math.log(4/3)+2*math.log(4))/4
        self.assertAlmostEqual(actual,expected,places=6); self.assertGreater(abs(actual-sample),.1)
        x=torch.zeros(300,100); y=torch.arange(100).repeat(3); counts=torch.full((100,),3.)
        f.validate_loss_inputs(x,y,counts); b.consume("forwards")
        self.assertAlmostEqual(float(f.class_loss(x,y,counts)),math.log(100),places=5)

    def test_zero_denominator_missing_dimension_and_invalid_labels_rejected(self):
        for x,y,n in [(torch.zeros(2,2),torch.tensor([0,0]),torch.tensor([2.,0.])),
                      (torch.zeros(2,1),torch.tensor([0,1]),torch.tensor([1.,1.])),
                      (torch.zeros(2,2),torch.tensor([0,2]),torch.tensor([1.,1.])),
                      (torch.zeros(2,2),torch.tensor([0,1]),torch.tensor([2.,1.]))]:
            with self.assertRaises(RuntimeError): f.validate_loss_inputs(x,y,n)

    def test_zero_recall_analytic_uniform_and_pp_arithmetic(self):
        b=SyntheticBudget(); b.consume("forwards")
        groups={"head":[0],"middle":[1],"tail":[1]}
        metrics=f.summarize(torch.tensor([[1.,0.],[1.,0.]]),torch.tensor([0,1]),groups,b)
        self.assertEqual(metrics["groups"]["tail"]["macro_recall_percent"],0.)
        control=f.uniform_control(2,[1,1],groups)
        self.assertEqual(control["CE"],math.log(2)); self.assertFalse(control["tie_argmax_used"])
        self.assertEqual(f.differences(metrics,{"u":control})["u"]["tail"],-50.)
        with self.assertRaises(RuntimeError): f.finite([torch.tensor(float("nan"))],b)

    def test_global_train_permutation_frequencies_and_ties_CP_boundaries(self):
        b=SyntheticBudget(); y=np.array([0]*9+[1]*3)
        perm=f.permute_labels(y,2,2026101501,b)
        np.testing.assert_array_equal(np.bincount(y),np.bincount(perm))
        np.testing.assert_array_equal(perm,np.random.default_rng(2026101501).permutation(y))
        row=f.train_control(20.,[20.]*99)
        self.assertEqual(row["exceedances_ge_including_ties"],99); self.assertEqual(row["plus_one_rank"],1.)
        self.assertEqual(row["clopper_pearson_95"][1],1.)
        row=f.train_control(20.,[0.]*99)
        self.assertEqual(row["plus_one_rank"],.01); self.assertEqual(row["clopper_pearson_95"][0],0.)
        self.assertAlmostEqual(row["clopper_pearson_95"][1],1-.025**(1/99),places=12)

    def test_validation_pairing_full_label_shuffle_integer_ties(self):
        b=SyntheticBudget(); y=np.array([0,0,1,1]); pred=np.array([0,1,0,1])
        rows=f.paired_permutation([pred,pred.copy()],y,[1],123,b,repeats=19)
        self.assertEqual(rows[0],rows[1])
        rng=np.random.default_rng(123)
        expected=[sum(int(p==v and v==1) for p,v in zip(pred,rng.permutation(y))) for _ in range(19)]
        self.assertEqual(rows[0]["permuted_tail_correct"],expected)
        exceed=sum(v>=1 for v in expected)
        self.assertEqual(rows[0]["p"],(1+exceed)/20)
        self.assertEqual(rows[0]["p_adj"],min(1,4*(1+exceed)/20))

    def test_bootstrap_paired_snapshots_class_order_fixed_denominators_linear_quantile(self):
        b=SyntheticBudget(); y=np.array([0,1,0,1,0,1]); original=np.zeros(6,np.int16); pred=np.array([0,1,0,0,0,1])
        rows=f.paired_bootstrap([(original,pred),(original.copy(),pred.copy())],y,[1],b,repeats=31)
        self.assertEqual(rows[0],rows[1])
        rng=np.random.default_rng(20261016); expected=[]
        for _ in range(31):
            _head=rng.choice(np.array([0,2,4]),3,replace=True)
            tail=rng.choice(np.array([1,3,5]),3,replace=True)
            R=100*np.count_nonzero(pred[tail]==y[tail])/3
            expected.append([R,R])
        np.testing.assert_array_equal(rows[0]["R_delta_replicates_percent_pp"],expected)
        np.testing.assert_array_equal(rows[0]["delta_decision"],np.quantile(np.asarray(expected)[:,1],[.0125,.9875],method="linear"))
        # Independent scalar interpolation example distinguishes 'linear' from nearest.
        self.assertEqual(float(np.quantile([0.,10.],.025,method="linear")),.25)

    def test_scientific_exact_threshold_strict_null_qualification_and_delta_bounds(self):
        p=dict(p_adj=.05); interval=dict(delta_decision=[.001,20.])
        row=f.science("CIFAR10",30.1,0.,[30.]*99,p,interval,True)
        self.assertEqual(row["calibration_space"],"PASS")
        row=f.science("CIFAR10",30.1,0.,[30.1]*99,p,interval,True)
        self.assertEqual(row["separability"],"FAIL")
        self.assertEqual(f.science("CIFAR10",30.1,0.,[0.]*99,p,interval,False)["separability"],"FAIL")
        self.assertEqual(f.science("CIFAR100",7.9,0.,[0.]*99,p,dict(delta_decision=[0.,20.]),True)["calibration_space"],"FAIL")

    def test_closed_preparation_once_and_separate_new_stage_limits(self):
        from importlib.util import spec_from_file_location,module_from_spec
        spec=spec_from_file_location("formal_history",ROOT/"scripts/run_direction_a_probe_formal.py")
        wrapper=module_from_spec(spec); spec.loader.exec_module(wrapper)
        totals=startup.history_totals(wrapper.preparation_history())
        self.assertEqual(totals["bytes"],11988355); self.assertEqual(totals["scan_upper_bound"],6020)
        self.assertAlmostEqual(totals["upper_seconds"],74.9171745)

    def test_formal_large_emergency_index_is_precharged_and_retained(self):
        import importlib.util
        spec=importlib.util.spec_from_file_location("formal_emergency",ROOT/"scripts/run_direction_a_probe_formal.py")
        wrapper=importlib.util.module_from_spec(spec); spec.loader.exec_module(wrapper)
        temporary_root=wrapper.OUT/"temporary_tests"
        temporary_root.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(dir=temporary_root) as folder:
            ctx=dict(output=Path(folder)/"attempt",started=startup.time.monotonic(),
                     history=dict(elapsed_seconds=0,counts=dict(evidence_bytes=0,archive_hash_scans=0),implementation_revisions=0,preparation_launches=0,failed_retries=0),
                     limits={**wrapper.LIMITS,"evidence_bytes":4*1024**2},implementation_revisions=1,
                     preparation_initial_write_bytes=0,preparation_initial_scans=0,source_write_events=[],
                     run_id="formal-large-index-synthetic",total_wall_seconds=4380,total_write_bytes=4*1024**2,
                     new_preparation_launches=0,new_failed_restarts=0,cpu_proxy_upper_bytes=0,cpu_proxy_basis="synthetic files",emergency_closure_bytes=1024**2)
            def namespace(context):
                def work(budget):
                    self.assertEqual(budget.reserve,1024**2)
                    self.assertGreaterEqual(budget.counts["evidence_bytes"],1024**2)
                    for i in range(1000): budget.write(ctx["output"]/f"synthetic-file-{i:04d}.json",b"nonzero",raw=True)
                    raise RuntimeError("large formal partial archive")
                return dict(LIMITS=ctx["limits"],main=work)
            value=wrapper.run_once(ctx,namespace)
            self.assertEqual(value["status"],"failed_no_retry")
            import json
            index=json.loads((ctx["output"]/"artifact_hashes.json").read_bytes())
            self.assertEqual(len(index["files"]),1003)
            self.assertGreater((ctx["output"]/"artifact_hashes.json").stat().st_size,128*1024)


def suite():
    import importlib.util
    spec=importlib.util.spec_from_file_location("accepted_startup_tests",ROOT/"tests/test_direction_a_probe_startup.py")
    old=importlib.util.module_from_spec(spec); spec.loader.exec_module(old)
    spec=importlib.util.spec_from_file_location("actual_formal_wrapper",ROOT/"scripts/run_direction_a_probe_formal.py")
    wrapper=importlib.util.module_from_spec(spec); spec.loader.exec_module(wrapper)
    old.wrapper=wrapper
    class Production(old.StartupTests):
        def setUp(self):
            temporary_root=ROOT/"artifacts/direction_a/phaseP_formal_v1/temporary_tests"
            temporary_root.mkdir(parents=True,exist_ok=True)
            self.directory=tempfile.TemporaryDirectory(prefix="P-formal-regression-",dir=temporary_root)
            self.addCleanup(self.directory.cleanup)
            self.output=Path(self.directory.name)/"attempt"
    names=["test_production_before_constructor","test_production_after_constructor_nonzero_work",
           "test_production_archive_error_nonzero_work","test_production_normal_preserves_peaks",
           "test_production_terminal_time_limit","test_production_terminal_write_limit","test_production_terminal_scan_limit",
           "test_real_parent_initialization_and_exact_write_inheritance","test_sealed_directories_rejected_without_access",
           "test_existing_marker_and_ledger_are_immutable"]
    return unittest.TestSuite([unittest.defaultTestLoader.loadTestsFromTestCase(Arithmetic),*[Production(name) for name in names]])
