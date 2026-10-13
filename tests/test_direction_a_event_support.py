"""G1.1 independent scalar references; only run with a shared bounded ledger."""

import ast
import itertools
import json
from fractions import Fraction
from pathlib import Path
from unittest.mock import patch

from direction_a.event_diagnostics import probability
from direction_a.event_protocol import EventBudget, BudgetExceeded, digest, encode
from direction_a.invitation_events import EventSimulator


def coverage_plan(ids):
    planned = [ids[i] for i in (0, 1, 2, 10, 11, 12, 13, 14)]
    attempts = []
    for attempt in range(4):
        latent = {client_id: {"online_u": "0", "dropout_u": "1/2", "jitter_u": "0"} for client_id in ids}
        if attempt == 0:
            latent[ids[1]]["online_u"] = "63/64"
            latent[ids[2]]["dropout_u"] = "1/64"
            latent[ids[10]]["jitter_u"] = "63/64"
            latent[ids[11]]["jitter_u"] = "11/30"  # D=10*(1/4+3/2*11/30)=8.
            latent[ids[13]]["dropout_u"] = "0"
            latent[ids[14]]["jitter_u"] = "63/64"
        elif attempt == 1:
            for client_id in ids:
                latent[client_id]["online_u"] = "63/64"
        elif attempt == 2:
            for client_id in ids:
                latent[client_id]["dropout_u"] = "0"
        attempts.append({"attempt_id": attempt, "planned_ids": planned, "latent": latent})
    return {"identity": "handwritten-branch-boundary-fixture-v1", "attempts": attempts,
            "fixture_note": "not random observations; exact deadline uses off-grid 11/30 solely for boundary testing"}


def run_scalar_oracles(mechanism, registry, ids, budget):
    budget.scan("independent_probability_and_state_boundary_oracles")
    # Independently enumerate N=5,m=2: 10 possible sets, 4 include each ID.
    combinations = list(itertools.combinations(range(5), 2))
    assert len(combinations) == 10
    assert [sum(i in chosen for chosen in combinations) for i in range(5)] == [4] * 5
    assert mechanism.q == Fraction(2, 5) and mechanism.total_work == Fraction(5, 2)
    fast, slow = probability(mechanism, "1"), probability(mechanism, "4")
    assert Fraction(fast["r_ideal_fraction"]) == Fraction(171, 200)
    assert Fraction(fast["p_ideal_fraction"]) == Fraction(171, 500)
    assert Fraction(slow["jitter_cdf_ideal_fraction"]) == Fraction(11, 30)
    assert Fraction(slow["r_ideal_fraction"]) == Fraction(627, 2000)
    assert Fraction(slow["p_ideal_fraction"]) == Fraction(627, 5000)
    # Hand-written integer cardinalities for the actual 53-bit uniform grid.
    M = 9007199254740992
    assert Fraction(fast["online_grid_fraction"]) == Fraction(8106479329266893, M)
    assert Fraction(fast["connected_grid_fraction"]) == Fraction(8556839292003942, M)
    assert Fraction(slow["jitter_cdf_grid_fraction"]) == Fraction(3302639726738364, M)
    assert Fraction(fast["r_true_grid_fraction"]) == Fraction(8106479329266893 * 8556839292003942, M * M)
    assert Fraction(slow["r_true_grid_fraction"]) == Fraction(8106479329266893 * 8556839292003942 * 3302639726738364, M ** 3)

    # A separate four-point enumerated lattice tests strict/inclusive thresholds.
    with patch("direction_a.event_diagnostics.GRID", 4):
        small_fast, small_slow = probability(mechanism, "1"), probability(mechanism, "4")
        assert Fraction(small_fast["r_true_grid_fraction"]) == Fraction(3, 4)
        assert Fraction(small_slow["r_true_grid_fraction"]) == Fraction(3, 8)

    frozen = False
    try:
        registry.entries[ids[0]] = registry.entries[ids[0]]
    except TypeError:
        frozen = True
    assert frozen
    assert isinstance(registry.entries[ids[0]].n_ic, tuple)

    speeds = {client_id: "1" if i < 10 else "4" for i, client_id in enumerate(ids)}
    fixture = coverage_plan(ids)
    simulator = EventSimulator(mechanism, "independent_scalar_fixture", registry, speeds, "test:thresholds", budget, cap=10)
    first = simulator.step(fixture["attempts"][0]["planned_ids"], fixture["attempts"][0]["latent"])
    assert first["finish_ids"] == [ids[0], ids[11], ids[12]]
    assert first["not_dispatched_ids"] == [ids[1]]
    assert first["drop_ids"] == [ids[2], ids[13]]
    assert first["overdue_ids"] == [ids[10], ids[14]]
    boundary_event = next(e for e in first["events"] if e["client_id"] == ids[11] and e["event_type"] == "valid_return")
    assert boundary_event["simulated_at_seconds_fraction"] == "8"
    latent = json.loads(json.dumps(fixture["attempts"][0]["latent"]))
    latent[ids[0]]["online_u"] = "9/10"  # Strict < must reject equality.
    latent[ids[2]]["dropout_u"] = "1/20"  # Strict < must NOT drop equality.
    latent[ids[11]]["jitter_u"] = str(Fraction(11, 30) + Fraction(1, M))
    second = simulator.step(first["planned_ids"], latent)
    assert ids[0] in second["not_dispatched_ids"]
    assert ids[2] in second["finish_ids"] and ids[2] not in second["drop_ids"]
    assert ids[11] in second["overdue_ids"]  # One lattice step after deadline.
    invalid = ["unregistered"] + first["planned_ids"][1:]
    rejected = False
    try:
        simulator.step(invalid, latent)
    except ValueError:
        rejected = True
    assert rejected
    return {"probability": "hand scalar fractions + hand 53-bit cardinalities + enumerated four-point grid",
            "state": "strict online/drop thresholds; inclusive deadline; unregistered IDs rejected; immutable registry"}


def run_budget_oracles(budget):
    budget.scan("independent_budget_scalar_boundaries")
    limits = {"attempts": 3, "scans": 4, "registration_bytes": 10, "event_bytes": 10,
              "evidence_bytes": 100000, "retries": 2, "wall_seconds": 9, "phase_seconds": {"events": 4}}
    with patch.object(EventBudget, "save", lambda self, reserved=False: None), patch("direction_a.event_protocol.time.monotonic", return_value=100):
        guard = EventBudget("virtual-not-written.json", limits)
        guard.attempt("virtual")
        guard.attempt("virtual")
        rejected = False
        try:
            guard.attempt("virtual")
        except BudgetExceeded:
            rejected = True
        assert rejected and guard.hit == {"field": "attempts", "actual": 3}
        assert guard.counts["attempts"] == 2
        guard = EventBudget("virtual-not-written.json", limits)
        guard.enter("events")
        guard.phase_started = 96
        rejected = False
        try:
            guard.check()
        except BudgetExceeded:
            rejected = True
        assert rejected and guard.hit == {"field": "phase_seconds.events", "actual": 4}
        guard = EventBudget("virtual-not-written.json", limits)
        guard.started = 91
        rejected = False
        try:
            guard.check()
        except BudgetExceeded:
            rejected = True
        assert rejected and guard.hit == {"field": "wall_seconds", "actual": 9}
        guard = EventBudget("virtual-not-written.json", limits)
        rejected = False
        try:
            guard.consume("registration_bytes", 10, "virtual_payload")
        except BudgetExceeded:
            rejected = True
        assert rejected and guard.counts["registration_bytes"] == 0
    return ["attempt/time/phase/byte thresholds stop before next action; no real workload in virtual tests"]


def audit_registration(task, registry, record, budget):
    budget.scan(task.identity + ":independent_encoded_registration_audit")
    assert tuple(registry.entries) == task.ids
    uploads = acknowledgements = 0
    for i, message in enumerate(record["messages"]):
        raw, ack = message["upload_utf8"].encode(), message["ack_utf8"].encode()
        decoded = json.loads(raw)
        assert decoded["client_id"] == task.ids[i]
        assert decoded["n_ic"] == list(task.n_ic[i])
        assert decoded["N_c"] == list(task.N_c) and decoded["a_ic"] == list(task.a_ic[i])
        assert decoded["class_ids"] == list(range(task.classes))
        assert decoded["train_split_hash"] == task.index_hashes[i]
        assert len(raw) == message["upload_bytes"] and len(ack) == message["ack_bytes"]
        assert digest(raw) == message["upload_sha256"] and digest(ack) == message["ack_sha256"]
        assert json.loads(ack)["received_upload_sha256"] == digest(raw)
        assert registry.entries[task.ids[i]].registration_ok
        uploads += len(raw)
        acknowledgements += len(ack)
    assert uploads == record["registration_uplink_encoded_bytes"]
    assert acknowledgements == record["registration_downlink_encoded_bytes"]
    return {"clients": len(task.ids), "classes": task.classes, "all_registered": True,
            "uplink_encoded_bytes": uploads, "downlink_encoded_bytes": acknowledgements}


def audit_trace(trace, plan, mechanism, budget):
    """Use independent scalar rational conditions on the preserved raw plan."""
    budget.scan(trace["trace_id"] + ":independent_scalar_event_audit")
    previous_after = 0
    totals = {key: 0 for key in ("planned_invitation", "dispatch", "not_dispatched", "dropout", "timeout", "valid_return")}
    for a, (attempt, item) in enumerate(zip(trace["attempts"], plan["attempts"])):
        assert attempt["attempt_id"] == item["attempt_id"] == a
        assert attempt["round_id"] == previous_after
        assert attempt["planned_ids"] == item["planned_ids"] and len(set(item["planned_ids"])) == 8
        expected = {key: [] for key in ("dispatch", "not_dispatched", "dropout", "timeout", "valid_return")}
        by_client = {}
        for e in attempt["events"]:
            totals[e["event_type"]] += 1
            by_client.setdefault(e["client_id"], []).append(e)
            assert e["attempt_id"] == a and e["round_id"] == attempt["round_id"]
            assert e["task_identity"] == trace["task_identity"] and e["version_id"] == attempt["version_id"]
            if "payload_utf8" in e:
                raw = e["payload_utf8"].encode()
                assert len(raw) == e["payload_bytes"] and digest(raw) == e["payload_sha256"]
        for client_id in item["planned_ids"]:
            draw = item["latent"][client_id]
            duration = Fraction(trace["speed_seconds_per_work_unit"][client_id]) * Fraction(5, 2) * (Fraction(1, 4) + Fraction(3, 2) * Fraction(draw["jitter_u"]))
            start = 8 * a
            if Fraction(draw["online_u"]) >= Fraction(9, 10):
                reason, moment = "not_dispatched", Fraction(start)
            else:
                expected["dispatch"].append(client_id)
                if Fraction(draw["dropout_u"]) < Fraction(1, 20):
                    reason, moment = "dropout", start + min(duration / 2, Fraction(4))
                elif duration > 8:
                    reason, moment = "timeout", Fraction(start + 8)
                else:
                    reason, moment = "valid_return", start + duration
            expected[reason].append(client_id)
            types = [e["event_type"] for e in by_client[client_id]]
            assert types == ["planned_invitation", reason] if reason == "not_dispatched" else types == ["planned_invitation", "dispatch", reason]
            final_event = by_client[client_id][-1]
            assert Fraction(final_event["simulated_at_seconds_fraction"]) == moment
            assert final_event["invitation_event_id"] == f"a{a:04d}:{client_id}:planned_invitation"
            if reason == "valid_return":
                assert final_event["finish_valid"] is True
                payload = json.loads(final_event["payload_utf8"])
                assert payload["attempt_id"] == a and payload["client_id"] == client_id
                assert payload["round_id"] == attempt["round_id"] and payload["version_id"] == attempt["version_id"]
        for field, key in (("dispatch_ids", "dispatch"), ("not_dispatched_ids", "not_dispatched"), ("drop_ids", "dropout"),
                           ("overdue_ids", "timeout"), ("finish_ids", "valid_return")):
            assert attempt[field] == expected[key]
        assert set(expected["dispatch"]) == set(expected["dropout"] + expected["timeout"] + expected["valid_return"])
        assert set(item["planned_ids"]) == set(expected["not_dispatched"] + expected["dispatch"])
        previous_after += int(bool(expected["valid_return"]))
        assert attempt["round_id_after"] == previous_after and attempt["empty_completion"] == (not bool(expected["valid_return"]))
        assert attempt["actual_model_updates"] == 0
    assert len(trace["attempts"]) == len(plan["attempts"])
    observed = []
    for client_id in trace["speed_seconds_per_work_unit"]:
        invites = sum(client_id in a["planned_ids"] for a in trace["attempts"])
        dispatch = sum(client_id in a["dispatch_ids"] for a in trace["attempts"])
        returns = sum(client_id in a["finish_ids"] for a in trace["attempts"])
        observed.append({"client_id": client_id, "attempts": len(trace["attempts"]), "planned_invitations": invites,
                         "dispatches": dispatch, "valid_returns": returns,
                         "observed_invitation_fraction": str(Fraction(invites, len(trace["attempts"]))),
                         "observed_return_given_planned_invite": None if not invites else str(Fraction(returns, invites)),
                         "observed_return_fraction": str(Fraction(returns, len(trace["attempts"]))),
                         "interpretation": "retrospective description only; not a predictor or support test"})
    return {"trace_id": trace["trace_id"], "event_totals": totals,
            "attempts": len(trace["attempts"]), "empty_attempts": sum(a["empty_completion"] for a in trace["attempts"]),
            "round_ids": [a["round_id"] for a in trace["attempts"]], "logical_successful_slots": previous_after,
            "observed_rates": observed, "finite_zero_return_clients": [row["client_id"] for row in observed if row["valid_returns"] == 0]}


def audit_diagnostic_separation(root, traces, budget):
    budget.scan("diagnostic_strategy_separation_AST_and_payload_audit")
    checked = []
    for name in ("invitation_events.py", "event_registration.py", "event_protocol.py"):
        path = Path(root) / "direction_a" / name
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imports = [node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)]
        assert all("diagnostics" not in str(module) for module in imports)
        assert not any(isinstance(node, ast.Import) and any("diagnostics" in alias.name for alias in node.names) for node in ast.walk(tree))
        checked.append(str(path.relative_to(root)).replace("\\", "/"))
    prohibited = {"r_true", "p_true", "r_true_grid", "p_true_grid", "r_hat", "p_hat", "p_min", "p_tilde"}

    def walk(value):
        if isinstance(value, dict):
            assert not (set(value) & prohibited)
            for item in value.values():
                walk(item)
        elif isinstance(value, list):
            for item in value:
                walk(item)

    for trace in traces:
        walk(trace)
        for attempt in trace["attempts"]:
            for event in attempt["events"]:
                if "payload_utf8" in event:
                    walk(json.loads(event["payload_utf8"]))
    return {"status": "pass", "event_modules_checked": checked, "event_and_dispatch_return_payloads_have_no_true_probability": True,
            "q_known_is_allowed": True, "actual_predictor_implemented": False,
            "source": "only acceptance runner imports offline event_diagnostics"}
