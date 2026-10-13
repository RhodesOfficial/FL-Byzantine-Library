"""G1.1 event simulator. Its strategy-facing outputs contain no true r/p.

Only sealed registration IDs, known invitation q, the mechanism and exogenous
draws are inputs. No gradients, errors, losses, estimator or diagnostic module.
"""

from fractions import Fraction

from direction_a.event_protocol import digest, encode, ratio


SEEDS = {"invite": 2026101301, "online": 2026101302, "dropout": 2026101303,
         "jitter": 2026101304, "speed_permutation": 2026101305}


def make_exogenous_plan(ids, mechanism, attempts, budget):
    import numpy as np
    budget.scan("fixed_exogenous_invitation_and_latent_plan")
    streams = {key: np.random.Generator(np.random.PCG64(seed)) for key, seed in SEEDS.items() if key != "speed_permutation"}
    plan = []
    for index in range(attempts):
        invitation = sorted(int(j) for j in streams["invite"].choice(len(ids), size=mechanism.invitations, replace=False))
        # Draw for ALL IDs independent of invitation and speed, enabling paired replay.
        draws = {name: stream.random(len(ids)).tolist() for name, stream in streams.items() if name != "invite"}
        latent = {client_id: {"online_u": ratio(draws["online"][i]),
                              "dropout_u": ratio(draws["dropout"][i]),
                              "jitter_u": ratio(draws["jitter"][i])} for i, client_id in enumerate(ids)}
        plan.append({"attempt_id": index, "planned_ids": [ids[j] for j in invitation], "latent": latent})
    return {"identity": "preselected-PCG64-plan-v1", "seeds": SEEDS, "attempts": plan,
            "draw_law": "independent 53-bit U grid 0..(2^53-1)/2^53; immutable across paired scenarios"}


def speed_assignments(task, budget):
    import numpy as np
    budget.scan(task.identity + ":derive_tail_share_and_speed_assignment_from_sealed_counts")
    shares = [Fraction(sum(task.n_ic[i][c] for c in task.tail_classes), task.train_totals[i]) for i in range(len(task.ids))]
    # Sorting only the derived tail share; never replacing sealed count/group tables.
    high_first = sorted(range(len(task.ids)), key=lambda i: (-shares[i], task.ids[i]))
    slow_ids = set(high_first[:10])
    rng = np.random.Generator(np.random.PCG64(SEEDS["speed_permutation"]))
    shuffled = rng.permutation([1] * 10 + [4] * 10).tolist()
    vectors = {"random": shuffled,
               "tail_slow": [4 if i in slow_ids else 1 for i in range(len(task.ids))],
               "tail_fast": [1 if i in slow_ids else 4 for i in range(len(task.ids))]}
    return {"task_identity": task.identity, "tail_share": {client_id: ratio(shares[i]) for i, client_id in enumerate(task.ids)},
            "tail_share_rank_high_first": [task.ids[i] for i in high_first],
            "assignments": {name: {client_id: str(values[i]) for i, client_id in enumerate(task.ids)} for name, values in vectors.items()},
            "speed_multiset_seconds_per_work_unit": [1] * 10 + [4] * 10,
            "slow_fast_median_duration_ratio": 4,
            "tail_share_denominator_provenance": "sealed acceptance.client_train_totals",
            "rank_tie_rule": "client ID ascending", "permutation_seed": SEEDS["speed_permutation"]}


class EventSimulator:
    def __init__(self, mechanism, task_identity, registry, speeds, trace_id, budget, cap=40):
        self.mechanism = mechanism
        self.task_identity = task_identity
        self.registry = registry
        self.speeds = dict(speeds)
        self.trace_id = trace_id
        self.budget = budget
        self.cap = cap
        self.next_attempt = 0
        self.round_id = 0
        if set(self.speeds) != set(registry.entries) or any(not entry.registration_ok for entry in registry.entries.values()):
            raise ValueError("event simulator requires complete registration")

    def step(self, planned_ids, latent):
        if len(planned_ids) != self.mechanism.invitations or len(set(planned_ids)) != len(planned_ids):
            raise ValueError("invalid planned invitation count")
        if not set(planned_ids).issubset(self.registry.entries):
            raise ValueError("unregistered invitation")
        self.budget.attempt(self.trace_id, self.cap)
        attempt, round_id = self.next_attempt, self.round_id
        deadline = Fraction(self.mechanism.deadline)
        start = attempt * deadline
        version = f"event-slot-{round_id:04d}"
        events, outcomes = [], []
        dispatch_ids, drop_ids, timeout_ids, finish_ids, unavailable_ids = [], [], [], [], []
        uplink_bytes = downlink_bytes = 0

        def event(client_id, kind, when, **fields):
            events.append({"event_id": f"a{attempt:04d}:{client_id}:{kind}", "event_type": kind,
                           "client_id": client_id, "attempt_id": attempt, "round_id": round_id,
                           "version_id": version, "task_identity": self.task_identity,
                           "simulated_at_seconds_fraction": ratio(when), **fields})

        for client_id in planned_ids:
            draw = latent[client_id]
            online, drop, jitter_u = (Fraction(draw[key]) for key in ("online_u", "dropout_u", "jitter_u"))
            if not all(0 <= value < 1 for value in (online, drop, jitter_u)):
                raise ValueError("latent draw outside U[0,1)")
            jitter = Fraction(self.mechanism.jitter_low) + (Fraction(self.mechanism.jitter_high) - Fraction(self.mechanism.jitter_low)) * jitter_u
            duration = Fraction(self.speeds[client_id]) * self.mechanism.total_work * jitter
            invitation_id = f"a{attempt:04d}:{client_id}:planned_invitation"
            event(client_id, "planned_invitation", start, q_known_invitation_fraction=ratio(self.mechanism.q))
            outcome = {"client_id": client_id, "invitation_event_id": invitation_id, "duration_seconds_fraction": ratio(duration),
                       "jitter_fraction": ratio(jitter), "finish_valid": False}
            if online >= Fraction(self.mechanism.online_probability):
                unavailable_ids.append(client_id)
                event(client_id, "not_dispatched", start, invitation_event_id=invitation_id, reason="offline_before_dispatch")
                outcome["reason"] = "not_dispatched"
            else:
                dispatch_ids.append(client_id)
                package = {"message_type": "event_work_token", "client_id": client_id, "task_identity": self.task_identity,
                           "attempt_id": attempt, "round_id": round_id, "version_id": version,
                           "deadline_seconds_fraction": ratio(deadline), "fixed_work_units": ratio(self.mechanism.total_work)}
                raw = encode(package)
                self.budget.consume("event_bytes", len(raw), self.trace_id + ":dispatch_metadata")
                downlink_bytes += len(raw)
                event(client_id, "dispatch", start, invitation_event_id=invitation_id, payload_utf8=raw.decode(), payload_bytes=len(raw), payload_sha256=digest(raw))
                if drop < Fraction(self.mechanism.dropout_probability):
                    drop_ids.append(client_id)
                    event(client_id, "dropout", start + min(duration / 2, deadline / 2), invitation_event_id=invitation_id, reason="connection_lost_after_dispatch")
                    outcome["reason"] = "dropout"
                elif duration > deadline:
                    timeout_ids.append(client_id)
                    event(client_id, "timeout", start + deadline, invitation_event_id=invitation_id,
                          would_finish_at_seconds_fraction=ratio(start + duration), reason="deadline_exceeded_no_late_acceptance")
                    outcome["reason"] = "timeout"
                else:
                    finish_ids.append(client_id)
                    returned = dict(package, message_type="event_valid_return_token", finish_valid=True)
                    raw = encode(returned)
                    self.budget.consume("event_bytes", len(raw), self.trace_id + ":return_metadata")
                    uplink_bytes += len(raw)
                    # Validate actual locally decoded token against its invitation/dispatch.
                    import json
                    received = json.loads(raw)
                    valid = all(received[key] == package[key] for key in ("task_identity", "client_id", "attempt_id", "round_id", "version_id"))
                    if not valid:
                        raise ValueError("return token mismatch")
                    event(client_id, "valid_return", start + duration, invitation_event_id=invitation_id,
                          finish_valid=True, payload_utf8=raw.decode(), payload_bytes=len(raw), payload_sha256=digest(raw))
                    outcome["finish_valid"], outcome["reason"] = True, "valid_return"
            outcomes.append(outcome)
        events.sort(key=lambda item: (Fraction(item["simulated_at_seconds_fraction"]), item["client_id"],
                                      {"planned_invitation": 0, "not_dispatched": 1, "dispatch": 1,
                                       "dropout": 2, "timeout": 2, "valid_return": 2}[item["event_type"]]))
        self.next_attempt += 1
        if finish_ids:
            self.round_id += 1
        return {"attempt_id": attempt, "round_id": round_id, "round_id_after": self.round_id, "version_id": version,
                "simulated_start_seconds_fraction": ratio(start), "deadline_seconds_fraction": ratio(deadline),
                "planned_ids": list(planned_ids), "dispatch_ids": dispatch_ids, "not_dispatched_ids": unavailable_ids,
                "drop_ids": drop_ids, "overdue_ids": timeout_ids, "finish_ids": finish_ids, "empty_completion": not bool(finish_ids),
                "events": events, "outcomes": outcomes, "downlink_metadata_encoded_bytes": downlink_bytes,
                "uplink_metadata_encoded_bytes": uplink_bytes, "actual_model_updates": 0}


def generate_trace(task, registry, speeds, scenario, mechanism, plan, budget):
    trace_id = f"{task.identity}:{scenario}"
    simulator = EventSimulator(mechanism, task.identity, registry, speeds, trace_id, budget)
    attempts = []
    for item in plan["attempts"]:
        budget.check()
        if item["attempt_id"] != simulator.next_attempt:
            raise ValueError("plan attempt order")
        attempts.append(simulator.step(item["planned_ids"], item["latent"]))
    return {"trace_id": trace_id, "kind": "preselected_random_engineering_trace", "task_identity": task.identity,
            "scenario": scenario, "speed_seconds_per_work_unit": speeds, "mechanism_identity": mechanism.identity,
            "plan_identity": plan["identity"], "attempts": attempts,
            "actual_model_updates": 0, "logical_successful_slots": simulator.round_id,
            "simulation_wall_seconds": ratio(len(attempts) * Fraction(mechanism.deadline)),
            "transport": "local encoded metadata only; no model/gradient/network payload"}
