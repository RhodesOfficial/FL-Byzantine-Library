"""Separate async consumer; the synchronous bind_final_mix contract is unchanged."""
import math

from .rfa_contributions import bind_final_mix


SEMANTICS = "async_rfa_post_staleness_v1"


def bind_async_mix(instance, inputs, client_ids, aggregate, call_id, batch_id,
                   task_ids, source_versions, staleness, capacity):
    bound, _ = bind_final_mix(instance, inputs, client_ids, aggregate, call_id, batch_id)
    m = len(inputs)
    if not (len(task_ids) == len(source_versions) == len(staleness) == m
            and len(set(task_ids)) == m and 0 < m <= capacity):
        raise ValueError("invalid asynchronous task batch")
    if any(type(x) is not int or x < 0 for x in (*source_versions, *staleness)):
        raise ValueError("invalid source version/staleness")
    weights = instance.last_client_weights
    coefficients = tuple((m / capacity) * w / (1 + lag)
                         for w, lag in zip(weights, staleness))
    if any(not math.isfinite(a) or a < 0 for a in coefficients):
        raise ValueError("invalid asynchronous coefficient")
    # Retain the genuine RFA layer, but do not copy its synchronous writeback labels.
    layer = {k: bound[k] for k in ("rfa_call_id", "semantics", "T", "nu",
                                  "aggregate_reconstruction_error", "final_betas", "denominator")}
    layer["clients"] = [{"client_id": row["client_id"], "position": row["position"],
                          "weight": row["weight"], "input_fingerprint": row["input_fingerprint"]}
                         for row in bound["clients"]]
    return coefficients, {
        "batch_id": batch_id, "adaptation_semantics": SEMANTICS,
        "input_direction": "source_parameters-minus-local_parameters",
        "model_displacement": "minus-sum(a_i*u_i); C_i=-a_i*u_i",
        "rfa_layer": layer,
        "clients": [{"client_id": cid, "task_id": tid, "source_version": source,
                     "staleness_commit": lag, "rfa_weight": w, "actual_coefficient": a,
                     "contribution_norm": a * u.detach().double().norm().item()}
                    for cid, tid, source, lag, w, a, u in zip(client_ids, task_ids, source_versions,
                                                           staleness, weights, coefficients, inputs)]}
