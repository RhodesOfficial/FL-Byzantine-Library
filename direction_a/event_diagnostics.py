"""Offline true-probability diagnostic channel, never imported by event policy."""

import math
from fractions import Fraction

from direction_a.event_protocol import ratio


GRID = 2 ** 53


def continuous_cdf(limit, low, high):
    return max(Fraction(0), min(Fraction(1), (limit - low) / (high - low)))


def below_grid_probability(threshold):
    # Grid k/M < threshold, k=0..M-1: exactly ceil(M*threshold) points.
    scaled = threshold * GRID
    count = -((-scaled.numerator) // scaled.denominator)
    return Fraction(max(0, min(GRID, count)), GRID)


def at_most_grid_probability(threshold):
    # k/M <= threshold: floor(M*threshold)+1, including the zero endpoint.
    scaled = threshold * GRID
    count = scaled.numerator // scaled.denominator + 1
    return Fraction(max(0, min(GRID, count)), GRID)


def probability(mechanism, speed):
    N, m = mechanism.clients, mechanism.invitations
    q = Fraction(math.comb(N - 1, m - 1), math.comb(N, m))
    online, drop = Fraction(mechanism.online_probability), Fraction(mechanism.dropout_probability)
    low, high = Fraction(mechanism.jitter_low), Fraction(mechanism.jitter_high)
    limit = Fraction(mechanism.deadline) / (Fraction(speed) * mechanism.total_work)
    cdf = continuous_cdf(limit, low, high)
    u_limit = (limit - low) / (high - low)
    jitter_grid = at_most_grid_probability(u_limit)
    online_grid, connected_grid = below_grid_probability(online), 1 - below_grid_probability(drop)
    r_ideal = online * (1 - drop) * cdf
    r_grid = online_grid * connected_grid * jitter_grid
    p_ideal, p_grid = q * r_ideal, q * r_grid
    r_error, p_error = abs(r_grid - r_ideal), abs(p_grid - p_ideal)
    # Three independent grid thresholds each differ by at most one grid step.
    bound = Fraction(3, GRID)
    if r_error > bound or p_error > q * bound:
        raise ArithmeticError("grid/continuous discrepancy exceeds declared independent bound")
    float_error = abs(Fraction(float(r_grid)) - r_grid)
    return {"q_fraction": ratio(q), "online_grid_fraction": ratio(online_grid),
            "connected_grid_fraction": ratio(connected_grid), "jitter_cdf_ideal_fraction": ratio(cdf),
            "jitter_cdf_grid_fraction": ratio(jitter_grid), "deadline_over_speed_work_fraction": ratio(limit),
            "r_ideal_fraction": ratio(r_ideal), "p_ideal_fraction": ratio(p_ideal),
            "r_true_grid_fraction": ratio(r_grid), "p_true_grid_fraction": ratio(p_grid),
            "q": float(q), "r_true_grid": float(r_grid), "p_true_grid": float(p_grid),
            "r_ideal": float(r_ideal), "p_ideal": float(p_ideal),
            "r_grid_vs_ideal_absolute_fraction": ratio(r_error), "p_grid_vs_ideal_absolute_fraction": ratio(p_error),
            "r_grid_vs_ideal_bound_fraction": ratio(bound), "r_float64_roundoff_absolute_fraction": ratio(float_error),
            "positive_support": q > 0 and r_grid > 0,
            "source": "declared sampler/online/dropout/jitter law + fixed workload/deadline, not observed-return estimator"}


def support_evidence(task, assignments, mechanism, budget):
    budget.scan(task.identity + ":independent_true_probability_and_every_source_support")
    rows, sources = [], []
    for scenario, speeds in assignments["assignments"].items():
        for i, client_id in enumerate(task.ids):
            values = probability(mechanism, speeds[client_id])
            if not values["positive_support"]:
                raise ValueError(f"permanent absence under mechanism: {client_id}; do not shrink population")
            row_id = f"{scenario}:{client_id}"
            rows.append({"probability_row_id": row_id, "scenario": scenario, "client_id": client_id,
                         "speed_seconds_per_work_unit": speeds[client_id], **values})
            for c, n in enumerate(task.n_ic[i]):
                if n > 0:
                    sources.append({"scenario": scenario, "client_id": client_id, "class_id": c, "n_ic": n,
                                    "probability_row_id": row_id, "q_fraction": values["q_fraction"],
                                    "r_true_grid_fraction": values["r_true_grid_fraction"],
                                    "p_true_grid_fraction": values["p_true_grid_fraction"], "positive_support": True})
    return {"task_identity": task.identity, "channel": "offline_diagnostic_only",
            "source_counts_sha256": task.file_hashes["counts.json"], "probabilities": rows, "nonzero_sources": sources,
            "nonzero_source_pairs_per_scenario": len(sources) // 3,
            "grid_denominator": GRID, "sampling_law": "three independent 53-bit U draws, exact rational grid probabilities",
            "diagnostic_not_strategy_input": True, "actual_predictor": "not implemented (G2.1)",
            "finite_zero_returns": "observation insufficiency; not a zero-probability claim"}
