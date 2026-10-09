"""Independent scalar anchors for the single formal z_cut=6 revision."""
from dataclasses import asdict
import math
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'easyFL'),str(ROOT/'tests')]
import torch
from d2_prime.reference import (ReferenceConfig,ReferenceState,ColdStatistics,
    ReferenceCandidate,score_feature,prepare_event,write_reference)
import test_d2_prime_formal as migration
EVIDENCE=[]


class RevisionAnchors(unittest.TestCase):
    def test_cold_and_source_boundaries(self):
        cfg=ReferenceConfig(z_cut=6.)
        cold=ColdStatistics((0.,)*33,(.125,)*33)
        ready=ReferenceState((0.,)*33,(.125,)*33,1.)
        anchors=[(0.,1.),(1.25,303601/331776),(3.,.5625),(6.,0.),(7.,0.)]
        # At z=1.25: (1-25/576)^2 = 551^2/576^2.
        for z,expected in anchors:
            for source,path in ((ReferenceState.initial(cfg),'cold'),(ready,'source')):
                actual=score_feature((z*.125,)*33,source,cold,cfg)
                self.assertEqual(actual[0],path)
                self.assertAlmostEqual(actual[1],z,places=14)
                self.assertAlmostEqual(actual[2],expected,places=14)
        old=score_feature((.375,)*33,ready,cold,ReferenceConfig())
        self.assertEqual(old[2],0.)
        self.assertEqual(ReferenceConfig().z_cut,3.)
        EVIDENCE.append(dict(case='cold/source boundaries',anchors=anchors,old_z3_g=old[2],default_cut=3.))

    def test_dual_coefficients_and_reference_hand_calculation(self):
        cfg=ReferenceConfig(z_cut=6.);initial=ReferenceState.initial(cfg)
        source=ReferenceState((0.,)*33,(.125,)*33,1.)
        candidates=[ReferenceCandidate(i,i,0,source,(.375,)*33) for i in range(3)]
        event=prepare_event(candidates,initial,cfg,20,1.,1)
        for p in event.proposals:
            self.assertEqual(p.g,.5625)
            self.assertEqual(p.h,.5)
            self.assertEqual(p.a0,.0140625)
            self.assertAlmostEqual(p.b0,.00140625,places=16)
        # Target-reference squared norm = .375^2 + .125^2 + 1 = 37/32.
        step=3*.00140625/math.sqrt(37/32)
        written=write_reference(event,{i:.00140625 for i in range(3)})
        self.assertAlmostEqual(written.after.evidence,step,places=14)
        for mu,sigma in zip(written.after.mu,written.after.sigma):
            self.assertAlmostEqual(mu,.375*step,places=14)
            self.assertAlmostEqual(sigma,.25+.125*step,places=14)
        self.assertEqual(initial,ReferenceState((0.,)*33,(.25,)*33,0.))
        EVIDENCE.append(dict(case='h=.5/g=.5625/K20 dual channels',a0=.0140625,b0=.00140625,
            expected_e=step,actual_e=written.after.evidence,immutable_before=True))

    def test_formal_option_only_changes_cut(self):
        from flgo_byzantine.formal_d2_prime_algorithm import Server
        from types import SimpleNamespace
        configurations=[]
        for option in ({},{'d2_z_cut':6.}):
            s=object.__new__(Server);s.model=migration.Carrier(10.)
            s.num_parallels=1;s.num_clients=100
            s.option=dict.fromkeys(('availability','connectivity','completeness','responsiveness'),'IDL')
            s.option.update(option);s.initialize()
            configurations.append(asdict(s.protocol.reference_config))
            self.assertEqual(s.protocol.reference.evidence,0.)
            self.assertEqual(s.protocol.reference.sigma,(.25,)*33)
            self.assertEqual(s.protocol.config.capacity,20)
            self.assertEqual(s.protocol.budget_remaining(0),.4125)
        expected=dict(configurations[0],z_cut=6.)
        self.assertEqual(configurations[1],expected)
        EVIDENCE.append(dict(case='formal opt-in only',default=configurations[0],revision=configurations[1]))

    def test_zcut6_budget_atomicity_expiry_and_causality(self):
        # Existing hand-computed, independent fixtures run again with explicit6.
        original=ReferenceConfig
        with patch.object(migration,'ReferenceConfig',side_effect=lambda:original(z_cut=6.)):
            case=migration.FormalMigration()
            for name in ('test_real_cold_ready_and_budget_exhaustion','test_atomic_failure_and_negative_audit',
                         'test_causal_source_and_gpu_clipping','test_identity_staleness_and_waiting_not_revived'):
                getattr(case,name)()
        EVIDENCE.append(dict(case='zcut6 joint invariants',partial_a=.025,partial_b=.0025,
            H=33,lifetime=32,no_early_refund=True,atomic_failure_rollback=True,source_causality=True))

    def test_diagnostic_has_independent_oracle_and_no_retry_counting(self):
        from scripts.run_d2_prime_zcut_revision import diagnostic
        rows=[dict(task_id=i,a=.028125,staleness_terminal=0) for i in range(12000)]
        earlier=[dict(task_id=i,h=1.,g=.25) for i in range(12000)]
        final=[dict(task_id=i,h=1.,g=.5625) for i in range(12000)]
        result=diagnostic(rows,list(range(12000)),[dict(event=dict(proposals=earlier)),
                          dict(event=dict(proposals=final))])
        for segment in result['segments']:
            self.assertEqual(segment['tasks'],2400)
            self.assertEqual(segment['G'],.5625)
            self.assertEqual(segment['A'],.5625)
            self.assertEqual(segment['sum_h'],2400.)
            self.assertEqual(segment['nominal_commit'],120.)
        self.assertEqual(result['latter_four']['tasks'],9600)
        EVIDENCE.append(dict(case='unique-task G/A oracle',G=.5625,A=.5625,retries_not_counted=True))
