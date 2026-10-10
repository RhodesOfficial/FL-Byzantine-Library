"""Phase-3 no-defense average under the causal_joint_32_v1 joint time-vector attack.

Honest tasks keep the frozen native transport and delays. Malicious identities train
their real local model (so the per-task budget is honest), then at each task's native
available tick get exactly one online search opportunity: 32 joint candidates scored by
isolated 32-tick causal proxies, after which the chosen upload vector and release timing
are fixed. No server-side B_M clip, reference or budget is added (Q7).
"""
from collections import deque

import numpy as np
import torch

from .async_baseline_algorithm import Server as BaselineServer, Client as BaselineClient
from .async_baseline_algorithm import parameter_vector
from .async_attack_state import AttackBaselineState
from .async_baseline_state import DeliveredReply
from attacks.causal_joint_32 import TIMINGS

import math


def _json_float(value):
    """JSON-safe: non-finite scores (destroyed proxy models) are logged as null."""
    return value if math.isfinite(value) else None


class Client(BaselineClient):
    pass


class Server(BaselineServer):
    def initialize(self):
        super().initialize()
        if self.option["async_method"] != "avg":
            raise ValueError("phase-3 attack qualification runs only the no-defense average")
        self.baseline = AttackBaselineState(parameter_vector(self.model), "avg",
                                            self.option["async_config_id"], identities=self.num_clients)
        fraction = float(self.option.get("byz_malicious_fraction", 0.3))
        if not 0 < fraction < 1:
            raise ValueError("malicious fraction must be in (0, 1)")
        byz_seed = int(self.option.get("byz_seed", 101))
        count = int(fraction*self.num_clients)
        self.malicious_ids = frozenset(sorted(int(x) for x in
            np.random.default_rng(byz_seed).choice(self.num_clients, count, replace=False)))
        self.horizon = int(self.option.get("attack_proxy_horizon", 32))
        self.attacker = None
        self.on_decision = lambda record: None
        self.arrival_history = deque(maxlen=20)
        self.malicious_waiting, self.malicious_delivery = {}, {}
        self.pending, self.malicious_normal_diff = {}, {}
        self.search_candidates_total = self.gradients_total = 0
        self.decision_count = self.expire_action_count = self.zero_direction_count = 0

    def _receive(self, packages):
        rows = list(zip(packages.get("reply", []), packages.get("__cid", []), packages.get("__t", [])))
        for reply, cid, at in sorted(rows, key=lambda r: r[0].task_id):
            accepted = self.baseline.receive(reply, int(cid), int(at))
            if accepted and int(cid) not in self.malicious_ids:
                self.arrival_history.append((int(at), reply.task_id,
                                             self.baseline.updates[reply.task_id].detach()))

    def _freeze_tail(self):
        state = self.baseline
        return (len(state.tasks) == self.task_limit
                and not any(r["state"] == "issued" for r in state.tasks.values()))

    def _mu_vis(self, normal_diff):
        if not self.arrival_history:
            return normal_diff
        return torch.stack([u for _, _, u in self.arrival_history]).mean(dim=0)

    def _candidate_timing(self, timing, now, expires_at):
        if timing == "immediate":
            return now, "immediate"
        if timing == "delay4":
            release = now+4
            return (release, "delay4") if release < expires_at else (None, "expire")
        if timing == "delay8":
            release = now+8
            return (release, "delay8") if release < expires_at else (None, "expire")
        return None, "expire"

    def _decide(self, task_id, now, tail):
        state = self.baseline
        row = state.tasks[task_id]
        source = state.sources[row["source_version"]]
        normal_diff = self.malicious_normal_diff[task_id]
        mu_vis = self._mu_vis(normal_diff)
        grad_unit, grad_norm, published_loss = self.attacker.grad_direction(state.model)
        resolved, direction_info = self.attacker.resolve_directions(mu_vis, grad_unit, normal_diff)
        vectors = self.attacker.build_candidates(mu_vis, resolved)
        self.search_candidates_total += len(vectors)*len(TIMINGS)
        self.gradients_total += 1
        colluding = [(rt, tid, delta) for tid, (rt, delta) in self.pending.items()
                     if rt >= now and tid != task_id]
        proxy_cache = {}

        def end_model(release_tick, vector_index, vector):
            key = ("finite", release_tick, vector_index) if release_tick is not None else ("expire",)
            if key not in proxy_cache:
                deliveries = list(colluding)
                if release_tick is not None:
                    deliveries.append((release_tick, task_id, vector))
                clone = state.clone_for_proxy()
                proxy_cache[key] = clone.proxy_rollout(deliveries, self.horizon, tail).detach()
            return proxy_cache[key]

        scored = []
        for index, candidate in enumerate(vectors):
            for timing in TIMINGS:
                release_tick, action = self._candidate_timing(timing, now, row["expires_at"])
                model = end_model(release_tick, index, candidate["vector"])
                scored.append({"d": candidate["d"], "gamma": candidate["gamma"], "timing": timing,
                               "effective_action": action, "release_tick": release_tick,
                               "vector_index": index, "vector_norm": candidate["vector_norm"],
                               "L_adv": self.attacker.adv_loss(model)})
        finite = sum(math.isfinite(s["L_adv"]) for s in scored)
        if finite == 0:
            raise RuntimeError(f"search deactivation: all 32 candidates non-finite at task {task_id}")
        choice = self.attacker.select(scored)
        chosen = scored[choice]
        chosen_vector = vectors[chosen["vector_index"]]["vector"]
        self.decision_count += 1
        if chosen["vector_norm"] <= 1e-12:
            self.zero_direction_count += 1
        if chosen["effective_action"] == "expire":
            self.expire_action_count += 1
        else:
            uploaded = (source - chosen_vector).detach().cpu()
            reply = DeliveredReply(task_id, row["identity"], row["source_version"], uploaded)
            self.malicious_delivery.setdefault(chosen["release_tick"], []).append(reply)
            self.pending[task_id] = (chosen["release_tick"], chosen_vector.detach())
        distinct_release_ticks = sorted({s["release_tick"] for s in scored
                                         if s["release_tick"] is not None})
        self.on_decision({"task_id": task_id, "identity": row["identity"],
            "source_version": row["source_version"], "decided_at": now,
            "mu_vis_from_history": bool(self.arrival_history),
            "mu_vis_norm": direction_info["mu_vis_norm"],
            "normal_diff_norm": direction_info["normal_diff_norm"],
            "gradient_norm": grad_norm, "published_loss": _json_float(published_loss),
            "published_model_norm": float(state.model.detach().double().norm().item()),
            "distinct_release_ticks": distinct_release_ticks, "finite_candidate_count": finite,
            "chosen": {**{k: chosen[k] for k in ("d", "gamma", "timing", "effective_action",
                                                 "release_tick", "vector_norm")},
                       "L_adv": _json_float(chosen["L_adv"])},
            "candidate_L_adv": [_json_float(s["L_adv"]) for s in scored],
            "colluding_pending": len(colluding)})

    def _deliver_due(self, now):
        due = self.malicious_delivery.pop(now, [])
        if due:
            self._receive({"reply": [r for r in due], "__cid": [r.identity for r in due],
                           "__t": [now]*len(due)})
            for r in due:
                self.pending.pop(r.task_id, None)

    def iterate(self):
        state = self.baseline
        now = int(self.gv.clock.current_time)
        state.expire(now)  # Deadlines before same-tick packets.
        self._receive(self.communicate([], asynchronous=True))  # Honest native arrivals.
        self._deliver_due(now)  # Prior-scheduled malicious arrivals, collected before decisions.
        tail = self._freeze_tail()
        for task_id in sorted(self.malicious_waiting.pop(now, [])):
            self._decide(task_id, now, tail)
        self._deliver_due(now)  # Same-tick immediate releases, after decisions, before commit.
        self._drain()
        self._evaluate_boundary()
        count = min(self.task_limit-len(state.tasks), state.limit-len(state.live))
        if count > 0:
            free = [cid for cid in range(self.num_clients) if cid not in state.live]
            chosen = sorted(self.dispatch_rng.choice(free, count, replace=False).tolist())
            self.dispatch_tasks = {cid: state.issue(cid) for cid in chosen}
            delays = {cid: int(self.delay_rngs[cid].choice([6, 7, 8] if cid in self.slow_ids else [1, 2, 3]))
                      for cid in chosen}
            honest = [cid for cid in chosen if cid not in self.malicious_ids]
            malicious = [cid for cid in chosen if cid in self.malicious_ids]
            if honest:
                self.gv.simulator.set_variable(self.gv.simulator.idx2id(honest),
                                               "latency", [delays[cid] for cid in honest])
                self._receive(self.communicate(honest, asynchronous=True))
            for cid in malicious:
                ticket = self.dispatch_tasks[cid]
                package = self.pack(cid)
                package["__mtype__"] = 0
                reply = self.clients[cid].reply(package)["reply"]
                self.executed_order.append(ticket.task_id)
                source = state.sources[ticket.source_version]
                normal_diff = (source - reply.local_model.to(source.device)).detach()
                self.malicious_normal_diff[ticket.task_id] = normal_diff
                self.malicious_waiting.setdefault(now+delays[cid], []).append(ticket.task_id)
            self._drain()  # Honest/malicious delays are >=1, so this only supports zero-delay checks.
            self.dispatch_tasks = {}
        state.audit()
        return state.version

    def run(self):
        self.on_evaluate(0)
        while True:
            self.iterate()
            if (len(self.baseline.tasks) == self.task_limit
                    and self.baseline.terminated == self.task_limit and self.gv.clock.empty()
                    and not self.malicious_delivery and not self.malicious_waiting):
                break
            self.gv.clock.step(1)
            if self.gv.clock.current_time > self.task_limit*32+32:
                raise RuntimeError("transport did not drain")
        if self.evaluated != list(self.eval_points):
            raise RuntimeError("missing registered task evaluations")
