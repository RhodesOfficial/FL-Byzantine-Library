"""Independent scalar/constant oracles; fixed tensors, no real training."""
from pathlib import Path
import math
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT),str(ROOT/'easyFL')]
import torch
from aggregators.rfa import RFA
from aggregators.async_rfa_contributions import bind_async_mix
from flgo_byzantine.async_baseline_state import BaselineState, DeliveredReply
from scripts.summarize_d2_prime_async_baseline import calibrate


def state(method="avg", **kwargs):
    return BaselineState(torch.tensor([10.],dtype=torch.float32),method,"fixed-test",**kwargs)


def deliver(s,ticket,local,at):
    return s.receive(DeliveredReply(ticket.task_id,ticket.identity,ticket.source_version,
                                   torch.tensor(local,dtype=torch.float32)),ticket.identity,at)


class AsyncBaselineTests(unittest.TestCase):
    def test_same_tick_batches_advance_staleness(self):
        s=state(capacity=2,outstanding_limit=4)
        tickets=[s.issue(c) for c in range(4)]
        s.expire(1)
        for t,local in zip(tickets,([9.],[7.],[8.],[8.])):
            deliver(s,t,local,1)
        self.assertEqual(s.model.item(),10.)
        first=s.commit_next()
        self.assertEqual(s.model.item(),8.)  # (1+3)/2
        second=s.commit_next()
        self.assertEqual(second['staleness_commit'],[1,1])
        self.assertEqual(second['actual_coefficients'],[.25,.25])
        self.assertEqual(s.model.item(),7.)  # source10 still gives raw2; 2*.25 twice
        self.assertEqual((first['version_before'],second['version_before']),(0,1))
        s.audit()

    def test_mixed_sources_are_frozen(self):
        s=state(capacity=2,outstanding_limit=4)
        a,b,old=[s.issue(c) for c in range(3)]
        s.expire(1)
        deliver(s,a,[8.],1);deliver(s,b,[8.],1)
        s.commit_next()
        new=s.issue(3)
        self.assertEqual(new.source_version,1)
        s.expire(2)
        deliver(s,old,[6.],2);deliver(s,new,[7.],2)
        batch=s.commit_next()
        self.assertEqual(batch['source_versions'],[0,1])
        self.assertEqual(s.model.item(),6.5)  # 8 - .25*(10-6) - .5*(8-7)
        self.assertEqual(s.tasks[old.task_id]['raw_norm'],4.)

    def test_timeout_and_tail_keep_fixed_denominator(self):
        s=state()
        t=s.issue(0);s.expire(1);deliver(s,t,[6.],1)
        s.expire(8);self.assertIsNone(s.commit_next())
        s.expire(9);r=s.commit_next()
        self.assertEqual(r['reason'],'timeout')
        self.assertEqual(r['actual_coefficients'],[.05])
        self.assertTrue(torch.equal(s.model,torch.tensor([9.8])))
        tail=state();t=tail.issue(0);tail.expire(1);deliver(tail,t,[6.],1)
        self.assertIsNone(tail.commit_next())
        self.assertEqual(tail.commit_next(tail=True)['reason'],'tail')
        self.assertTrue(torch.equal(tail.model,torch.tensor([9.8])))

    def test_deadline_priority_and_late_norm(self):
        s=state();t=s.issue(0)
        s.expire(32)
        self.assertEqual(s.tasks[t.task_id]['state'],'expired')
        self.assertFalse(deliver(s,t,[9.],32))
        self.assertEqual(s.tasks[t.task_id]['raw_norm'],1.)
        self.assertIsNone(s.tasks[t.task_id]['arrived_at'])
        self.assertEqual((s.version,s.model.item()),(0,10.))
        self.assertFalse(deliver(s,t,[9.],32))
        self.assertEqual(s.terminated,1)

    def test_staleness_64_is_valid_65_expires_and_cancellation_versions(self):
        for count in (64,65):
            s=state(capacity=1,outstanding_limit=2,lifetime=1000)
            old=s.issue(0)
            for tick in range(1,count+1):
                s.expire(tick)
                t=s.issue(1);deliver(s,t,[10.],tick)
                s.commit_next()  # Zero vector, positive coefficient: version still advances.
            s.expire(count)
            if count==64:
                self.assertTrue(deliver(s,old,[9.],count))
                r=s.commit_next();self.assertEqual(r['staleness_commit'],[64])
                self.assertAlmostEqual(r['actual_coefficients'][0],1/65)
            else:
                self.assertEqual(s.tasks[old.task_id]['state'],'expired')
                self.assertFalse(deliver(s,old,[9.],count))
            s.audit()

    def test_invalid_duplicate_slots_and_no_future_information(self):
        s=state(outstanding_limit=2);a=s.issue(0);b=s.issue(1)
        with self.assertRaises(RuntimeError):s.issue(0)
        with self.assertRaises(RuntimeError):s.issue(2)
        self.assertIsNone(s.tasks[b.task_id]['raw_norm'])
        self.assertEqual(s.version,0)
        s.expire(1)
        bad=DeliveredReply(a.task_id,9,a.source_version,torch.tensor([9.]))
        self.assertFalse(s.receive(bad,9,1))
        self.assertFalse(deliver(s,a,[float('nan')],1))
        self.assertTrue(deliver(s,a,[9.],1))
        self.assertFalse(deliver(s,a,[9.],1))
        self.assertEqual(len(s.live),2)  # Arrival does not free a slot.
        self.assertIsNone(s.tasks[b.task_id]['raw_norm'])
        self.assertEqual(s.model.item(),10.)

    def test_zero_delay_same_K_same_source_degenerates(self):
        s=BaselineState(torch.tensor([100.]),'avg','zero')
        tickets=[s.issue(c) for c in range(20)]
        for t in tickets:deliver(s,t,[80.],0)
        s.commit_next()
        self.assertEqual(s.model.item(),80.)  # Identical to synchronous mean of 20 local80.
        r=BaselineState(torch.tensor([100.]),'rfa','zero')
        tickets=[r.issue(c) for c in range(20)]
        for t in tickets:deliver(r,t,[80.],0)
        r.commit_next()
        self.assertAlmostEqual(r.model.item(),80.,places=5)

    def test_RFA_anchor_distinguishes_weights_from_actual_coefficients(self):
        inputs=[torch.tensor([1.]),torch.tensor([3.])]
        r=RFA(T=1);z=r(inputs)
        a,record=bind_async_mix(r,inputs,[2,7],z,1,0,[12,19],[0,1],[1,0],20)
        self.assertAlmostEqual(z.item(),1.5)
        self.assertEqual(r.last_client_weights,(.75,.25))
        for actual,expected in zip(a,(.0375,.025)):
            self.assertAlmostEqual(actual,expected,places=15)  # f=.1; h=(.5,1), no renormalization
        self.assertEqual(record['rfa_layer']['semantics'],'rfa_final_mix_v1')
        with self.assertRaises(ValueError):
            bind_async_mix(r,[inputs[0]*.5,inputs[1]],[2,7],z,1,0,[12,19],[0,1],[1,0],20)

    def test_multiround_RFA_matches_independent_scalar_recursion(self):
        s=state('rfa',capacity=2)
        t=[s.issue(c) for c in (0,1)]
        s.expire(1)
        deliver(s,t[0],[9.],1);deliver(s,t[1],[7.],1)
        z=0.
        for _ in range(5):
            b=[.5/max(abs(z-u),1e-6) for u in (1.,3.)]
            z=(b[0]+3*b[1])/sum(b)
        batch=s.commit_next()
        self.assertAlmostEqual(s.model.item(),10-z,places=5)
        self.assertTrue(batch['checks']['writeback_exact'])

    def test_offline_window_left_boundary_and_all_identities(self):
        rows=[{'task_id':i,'identity':0,'state':'consumed','terminal_at':t,
               'staleness_commit':0,'nominal_fee':.055} for i,t in enumerate((0,2,4))]
        value=calibrate(rows,identities=3)
        self.assertEqual(value['H'],2.)
        # Window (t-2,t] excludes the previous commit, so Qmax=[.055,0,0].
        self.assertEqual([r['maximum_nominal_window_fee'] for r in value['per_identity']],[.055,0.,0.])
        self.assertAlmostEqual(value['beta'],.0495)  # linear p95 of literal [0,0,.055]
        self.assertEqual(value['positive_interval_count'],2)

    def test_GPU_float32_actual_writeback(self):
        self.assertTrue(torch.cuda.is_available())
        s=BaselineState(torch.tensor([10.,20.],device='cuda'),'avg','gpu',capacity=2)
        a,b=s.issue(0),s.issue(1)
        s.expire(1)
        for t,local in ((a,[9.,18.]),(b,[7.,16.])):
            s.receive(DeliveredReply(t.task_id,t.identity,t.source_version,
                                    torch.tensor(local)),t.identity,1)
        batch=s.commit_next()
        self.assertTrue(torch.equal(s.model,torch.tensor([8.,17.],device='cuda')))
        self.assertTrue(batch['checks']['writeback_exact'])
        self.assertEqual(s.model.dtype,torch.float32)


if __name__=='__main__':unittest.main()
