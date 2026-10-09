"""Q4 migration: fixed GPU tensors, scalar/formula oracles, no training."""
import copy
from dataclasses import asdict, replace
import math
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT),str(ROOT/'easyFL')]
import torch
from flgo.simulator.base import ElemClock
from d2_prime.protocol import ProtocolConfig, Reply
from d2_prime.reference import ReferenceConfig, ReferenceState, FeatureMap
from d2_prime.budget import BudgetConfig
from d2_prime.float32_protocol import Float32TaskProtocol
from flgo_byzantine.formal_d2_prime_algorithm import Server
from flgo_byzantine.async_baseline_state import DeliveredReply

EVIDENCE = []


def backend(value=10., **kw):
    return Float32TaskProtocol(torch.tensor([value],device='cuda',dtype=torch.float32),
        ProtocolConfig(identities=100,max_outstanding=40,capacity=20,lifetime=32.,
                       max_staleness=64,clip_norm=.9701598816245317),
        ReferenceConfig(), feature_map=FeatureMap((0,),(1,),32),
        budget_config=BudgetConfig(33.,.4125))


class Carrier(torch.nn.Module):
    def __init__(self, value):
        super().__init__();self.theta=torch.nn.Parameter(torch.tensor([value],device='cuda'))


def server(limit=12000,value=10.):
    s = object.__new__(Server)
    s.model=Carrier(value);s.protocol=backend(value);s.task_limit=limit
    s.eval_points=[];s.evaluated=[];s.current_round=0;s.attempts=0
    s.terminal_order=[];s.seen_terminal=set();s.journal=[]
    s.gv=SimpleNamespace(clock=ElemClock())
    s.on_event=lambda row:None;s.on_evaluate=lambda target,actual:None
    return s


def schedule(s,cid,delta=0.,at=None):
    p=s.protocol;t=p.issue(cid)
    local=p.snapshot(t.source_version).model.cpu()-delta
    s.gv.clock.put(dict(reply=DeliveredReply(t.task_id,cid,t.source_version,local),
                        __cid=cid,__t=p.now if at is None else at),p.now if at is None else at)
    return t


def harvest(s,at):
    s.gv.clock.step(at-s.gv.clock.current_time)
    s._expire(at)
    packets=s.gv.clock.get_sofar()
    s._receive({k:[r[k] for r in packets] for k in ('reply','__cid','__t')})
    s._drain();s.audit_tick()


class FormalMigration(unittest.TestCase):
    def test_actual_cnn_fixed_tensor_transport(self):
        from flgo.benchmark.cifar10_classification.model.cnn import Model
        from flgo_byzantine.async_baseline_algorithm import parameter_vector
        torch.set_num_threads(1)
        s=server();s.model=Model().cuda()
        initial=parameter_vector(s.model).clone()
        s.protocol=Float32TaskProtocol(initial,
            ProtocolConfig(identities=100,max_outstanding=40,capacity=20,lifetime=32.,
                           max_staleness=64,clip_norm=.9701598816245317),
            ReferenceConfig(),budget_config=BudgetConfig(33.,.4125))
        for cid in range(40):
            t=s.protocol.issue(cid)
            s.gv.clock.put(dict(reply=DeliveredReply(t.task_id,cid,0,initial.cpu().clone()),
                                __cid=cid,__t=1),1)
        harvest(s,1)
        self.assertEqual(initial.numel(),797962)
        self.assertTrue(torch.equal(initial,parameter_vector(s.model)))
        self.assertEqual(s.protocol.version,2)
        self.assertEqual(len(s.protocol.ledger),40)
        self.assertTrue(all(e['checks']['writeback_exact'] for e in s.journal if e['kind']=='commit'))
        self.assertAlmostEqual(s.protocol.reference.evidence,
            .1/math.sqrt(1.04)+.05*(1-.1/math.sqrt(1.04)),places=12)
        EVIDENCE.append(dict(case='actual797962CNN/nativeclock/fixedfloat32',parameters=797962,
            versions=2,receipts=40,real_training_tasks=0,exact_carrier=True))

    def test_retry_recomputes_and_cold_source_stays_cold(self):
        s=server();p=s.protocol
        for n in range(8):
            for cid in range(20):schedule(s,cid,0.,0)
            harvest(s,0)
        harvest(s,2)
        for cid in range(20):schedule(s,cid,0.,2)
        harvest(s,2)
        bound=p.snapshot(p.tasks[160].source_version)
        for cid in range(20,40):schedule(s,cid,0.,3)
        harvest(s,3) # waiting first20 cannot be skipped to backfill with the next20
        self.assertEqual(p.version,8)
        harvest(s,33)
        # First retry uses released balance and the original source; a newly
        # exposed second batch advances separately with recomputed h=1/2.
        commits=[e for e in s.journal if e['kind']=='commit' and e['receipts']]
        self.assertEqual(commits[-2]['event']['proposals'][0]['source_version'],8)
        self.assertEqual(commits[-2]['event']['proposals'][0]['h'],1.)
        self.assertEqual(commits[-1]['event']['proposals'][0]['h'],.5)
        self.assertEqual(p.tasks[160].expires_at,34.)
        self.assertEqual(bound.evidence,p._sources[8].evidence if 8 in p._sources else bound.evidence)
        cold=server();p=cold.protocol
        old=p.issue(99);p.receive(Reply(old.task_id,99,0,torch.tensor([10.])),99)
        # Keep signed cold task out of the first buffer until ready is actually
        # paid for; this is a transport/queue fixture, not prefilled evidence.
        p._buffer.remove(old.task_id);p._updates.pop(old.task_id);p._feature_cache.pop(old.task_id)
        p.tasks[old.task_id]=replace(old,state='issued')
        for n in range(7):
            for cid in range(20):schedule(cold,cid,0.,0)
            harvest(cold,0)
        self.assertTrue(p.reference.ready(p.reference_config))
        p.receive(Reply(old.task_id,99,0,torch.tensor([10.])),99)
        self.assertEqual(p.prepare_reference_event().proposals[0].path,'waiting')
        self.assertEqual(p.snapshot(0).evidence,0.)

    def test_q5_independent_segment_constants(self):
        from scripts.summarize_d2_prime_formal import summarize
        rows=[];events=[];base=[]
        for i in range(12000):
            rows.append(dict(task_id=i,identity=i%100,state='consumed',a=.005,b=.0005,
                first_arrival_at=i,staleness_arrival=0,staleness_terminal=0,staleness_commit=0,
                source_ready=True,ever_scored=True,source_scored=True,raw_norm=.2,clip_scale=1.))
        for n in range(600):
            ids=list(range(n*20,(n+1)*20))
            events.append(dict(kind='commit',attempt=n+1,at=n,version=n+1,ready=True,
                terminated_before=n*20,terminated_after=(n+1)*20,checks=dict(delta_norm=1.),
                receipts=[dict(task_id=i,identity=i%100,at=i,a=.005,b=.0005,q=.005+.0005) for i in ids]))
            base.append(dict(task_ids=ids,checks=dict(delta_norm=2.)))
        d=summarize(rows,list(range(12000)),events,set(range(50)),base)
        for segment in d['segments']:
            self.assertAlmostEqual(segment['A'],12.,places=12)
            self.assertAlmostEqual(segment['N'],120.,places=12)
            self.assertAlmostEqual(segment['P'],.10,places=15)
            self.assertEqual(segment['V'],120.)
            self.assertEqual(segment['baseline_V'],240.)
        self.assertEqual(d['retention']['R_slow'],1.)
        self.assertEqual(d['latter_unique_source'],6000)

    def test_formal_same_tick_mixed_and_no_future(self):
        s=server()
        for cid in range(40):schedule(s,cid,.5,1)
        self.assertEqual(s.model.theta.item(),10.)
        harvest(s,1)
        self.assertEqual(s.model.theta.item(),9.25)
        self.assertEqual(s.protocol.version,2)
        self.assertEqual([p['h'] for p in s.journal[-1]['event']['proposals']],[.5]*20)
        self.assertEqual([r['a'] for r in s.protocol.ledger],[.05]*20+[.025]*20)
        mixed=server()
        for cid in range(40):schedule(mixed,cid,.5,1 if cid<20 else (2 if cid<30 else 32))
        harvest(mixed,1)
        for cid in range(10):schedule(mixed,cid,.5,2)
        harvest(mixed,2)
        self.assertEqual(mixed.model.theta.item(),9.125)
        self.assertEqual([p['h'] for p in mixed.journal[-1]['event']['proposals']],[.5]*10+[1.]*10)
        # Last 10 new tasks await 8-tick timeout; source/version remains actual.
        self.assertTrue(torch.equal(mixed.protocol.snapshot(mixed.protocol.version).model,mixed.model.theta))
        EVIDENCE.append(dict(case='same-tick/mixed/native-clock',same_tick=9.25,mixed=9.125,K=20,H=33,beta=.4125))

    def test_timeout_tail_cold_wait_and_expiry(self):
        s=server()
        for cid in range(3):schedule(s,cid,.5,1)
        harvest(s,1);harvest(s,8)
        self.assertEqual(s.attempts,0)
        harvest(s,9)
        self.assertEqual(s.attempts,1)
        self.assertEqual(s.model.theta.item(),torch.tensor(9.925).item())
        tail=server(limit=3)
        for cid in range(3):schedule(tail,cid,.5,1)
        harvest(tail,1)
        self.assertEqual(tail.attempts,1)
        cold=server(limit=2)
        for cid in range(2):schedule(cold,cid,0.,1)
        harvest(cold,1);self.assertEqual(cold.attempts,1)
        self.assertEqual(cold.protocol.outstanding,2)
        self.assertEqual(cold.protocol.ledger,[])
        harvest(cold,2);self.assertEqual(cold.attempts,2) # one retry per tick, not a loop
        harvest(cold,32)
        self.assertEqual(cold.protocol.outstanding,0)
        self.assertEqual(cold.protocol.version,0)
        s2=server()
        for cid in range(3):schedule(s2,cid,0.,32)
        harvest(s2,32)
        self.assertTrue(all(t.state=='expired' for t in s2.protocol.tasks.values()))
        self.assertFalse(s2.protocol.ledger)

    def test_real_cold_ready_and_budget_exhaustion(self):
        s=server()
        for n in range(8):
            for cid in range(20):schedule(s,cid,0.,0)
            harvest(s,0)
            expected=(.1/math.sqrt(1.04)) if n==0 else 1-(1-.1/math.sqrt(1.04))*.9**n
            # On last partial-budget batch reference step is .05, not .1.
            if n<7:self.assertAlmostEqual(s.protocol.reference.evidence,expected,places=12)
        self.assertTrue(s.protocol.reference.ready(s.protocol.reference_config))
        fees=[r for r in s.protocol.ledger if r['identity']==0]
        self.assertEqual(len(fees),8)
        self.assertAlmostEqual(fees[-1]['a'],.025,places=14)
        self.assertAlmostEqual(fees[-1]['b'],.0025,places=14)
        self.assertEqual(s.protocol.budget_remaining(0),0.)
        for cid in range(20):schedule(s,cid,0.,0)
        harvest(s,0)
        self.assertEqual(s.protocol.outstanding,20)
        self.assertEqual(s.protocol.version,8)
        self.assertFalse(s.journal[-1]['event']['proposals'])
        self.assertEqual(s.attempts,9)
        harvest(s,32)
        self.assertEqual(s.protocol.outstanding,0)
        self.assertEqual(s.protocol.budget_remaining(0),0.) # H>lifetime loss, no refund
        s.protocol.advance(33.)
        self.assertEqual(s.protocol.budget_remaining(0),.4125)
        EVIDENCE.append(dict(case='paid cold-ready/partial/exhausted/expiry',fees=fees,
                             ready=True,expired_waiters=20,left_endpoint_release=33.))

    def test_causal_source_and_gpu_clipping(self):
        s=server()
        p=s.protocol
        for n in range(7):
            for cid in range(20):schedule(s,cid,0.,0)
            harvest(s,0)
        t=schedule(s,30,.25,1)
        source=p.snapshot(t.source_version)
        source.model.add_(100.)
        self.assertEqual(p.snapshot(t.source_version).model.item(),10.)
        # Ready source score must differ from an explicitly changed current state.
        p._reference=ReferenceState((.8,)*33,(.05,)*33,.9)
        harvest(s,1);p.advance(9.)
        a=p.prepare_reference_event().proposals[0]
        src=p._sources[t.source_version]
        x=list(a.feature)
        z=math.sqrt(sum((v-m)**2/(sig**2+(.1*(1-src.evidence))**2)
                        for v,m,sig in zip(x,src.mu,src.sigma))/33)
        self.assertAlmostEqual(a.z,z,places=12)
        current_z=math.sqrt(sum((v-.8)**2/(.05**2+.01**2) for v in x)/33)
        self.assertGreater(abs(current_z-z),1.)
        p._reference=ReferenceState((-.5,)*33,(.3,)*33,.8)
        self.assertEqual(p.prepare_reference_event().proposals[0].g,a.g)
        clip=server(limit=3)
        for cid in range(3):schedule(clip,cid,2.,1)
        harvest(clip,1)
        r=clip.protocol.observations[0]
        self.assertEqual(r['raw_norm'],2.)
        self.assertEqual(r['clipped_norm'],.9701598816245317)
        self.assertEqual(clip.journal[-1]['event']['proposals'][0]['feature'][-1],1.)
        self.assertEqual(clip.model.theta.item(),torch.tensor(10.-3*.05*.9701598816245317).item())
        EVIDENCE.append(dict(case='source/current distinct scalar score',source_z=z,current_z=current_z))

    def test_atomic_failure_and_negative_audit(self):
        for site in ('d2_prime.protocol.write_reference','d2_prime.budget.RollingBudget.record'):
            s=server(limit=3)
            for cid in range(3):schedule(s,cid,.5,1)
            s.gv.clock.step(1);s._expire(1)
            packets=s.gv.clock.get_sofar()
            s._receive({k:[r[k] for r in packets] for k in ('reply','__cid','__t')})
            p=s.protocol
            state=(p.model.clone(),p.reference,p.tasks.copy(),copy.deepcopy(p.observations),p.version)
            with patch(site,side_effect=ValueError('injected')):
                with self.assertRaisesRegex(ValueError,'injected'):s._drain()
            self.assertTrue(torch.equal(state[0],p.model))
            self.assertEqual(state[1:],(p.reference,p.tasks,p.observations,p.version))
            self.assertFalse(p.ledger)
            s._drain()
            original=copy.deepcopy(p.ledger)
            for kind in ('fee','missing','duplicate'):
                p.ledger=copy.deepcopy(original)
                if kind=='fee':p.ledger[0]['q']=p.ledger[0]['a']
                elif kind=='missing':p.ledger.pop()
                else:p.ledger.append(p.ledger[0])
                with self.assertRaises(ValueError):p.audit_budget()
            p.ledger=original;p.audit_budget()

    def test_identity_staleness_and_waiting_not_revived(self):
        p=backend();t=p.issue(0)
        r=Reply(t.task_id,0,0,torch.tensor([10.],dtype=torch.float32))
        for bad in (replace(r,identity=1),replace(r,source_version=1),replace(r,task_id=999)):
            self.assertFalse(p.receive(bad,bad.identity))
        self.assertTrue(p.receive(r,0));self.assertFalse(p.receive(r,0))
        with self.assertRaises(RuntimeError):p.issue(0)
        p.version=64;p._freeze()
        self.assertEqual(p.candidates()[0]['staleness'],64)
        p._expire_stale();self.assertEqual(p.tasks[0].state,'arrived')
        p.version=65;p._freeze();p._expire_stale()
        self.assertEqual(p.tasks[0].state,'expired')
        # A cold waiter is diagnosed, then another ready-source receipt makes it
        # exceed max-staleness. The driver must consume the authoritative terminal.
        s=server(limit=2);p=s.protocol
        old=p.issue(0);p.receive(Reply(0,0,0,torch.tensor([10.])),0)
        p.version=64;p._reference=ReferenceState((0.,)*33,(.25,)*33,.5);p._freeze()
        new=p.issue(1);p.receive(Reply(1,1,64,torch.tensor([10.])),1)
        s.current_round=64
        s._drain()
        self.assertEqual(p.version,65)
        self.assertEqual(p.tasks[0].state,'expired')
        self.assertIn((0,'cold'),s.journal[-1]['waiting'])
        self.assertEqual(p.outstanding,0)
        self.assertEqual(s.terminal_order,[0,1])

    def test_event_evaluation_and_cancellation(self):
        s=server()
        s.eval_points=[10,25];points=[];s.on_evaluate=lambda target,actual:points.append((target,actual))
        for cid in range(40):schedule(s,cid,0.,1)
        harvest(s,1)
        self.assertEqual(points,[(10,20),(25,40)])
        self.assertEqual(s.protocol.version,2)
        self.assertEqual(s.model.theta.item(),10.) # positive fees with zero net model
        for row in s.journal:
            if row['kind']=='commit':self.assertEqual(row['checks']['delta_norm'],0.)
        EVIDENCE.append(dict(case='per-event evaluation',points=points,zero_vector_versions=2))


if __name__=='__main__':
    unittest.main()
