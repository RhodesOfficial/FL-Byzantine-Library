"""Read-only offline calibration/diagnostics; no model or D2' state creation."""
from collections import Counter, deque
import math

import numpy as np


def quantiles(values):
    if not values:
        return {"count": 0, "p50": None, "p95": None, "p99": None}
    if any(not math.isfinite(v) for v in values):
        raise ValueError("nonfinite diagnostic")
    return dict(count=len(values), **{f"p{q}": float(np.quantile(values, q/100, method="linear"))
                                    for q in (50,95,99)})


def calibrate(rows, identities=100):
    groups = [[r for r in rows if r["identity"] == cid and r["state"] == "consumed"]
              for cid in range(identities)]
    gaps, per_identity = [], []
    for cid, group in enumerate(groups):
        group.sort(key=lambda r: (r["terminal_at"], r["task_id"]))
        available = [b["terminal_at"]-a["terminal_at"] for a,b in zip(group,group[1:])
                     if b["terminal_at"] > a["terminal_at"]]
        gaps.extend(available)
        per_identity.append({"identity": cid, "commits": len(group), "positive_intervals": len(available)})
    H = float(np.quantile(gaps, .95, method="linear")) if gaps else 1.
    maxima = []
    for group in groups:
        window, total, maximum = deque(), 0., 0.
        for row in group:
            at = row["terminal_at"]
            while window and window[0][0] <= at-H:
                total -= window.popleft()[1]
            fee = .055/(1+row["staleness_commit"])
            if not math.isclose(fee,row["nominal_fee"],rel_tol=1e-12,abs_tol=1e-15):
                raise ValueError("nominal fee does not match the ruling")
            window.append((at,fee))
            total += fee
            maximum = max(maximum,total)
        maxima.append(maximum)
    beta = float(np.quantile(maxima, .95, method="linear"))
    for row,maximum in zip(per_identity,maxima):
        row["maximum_nominal_window_fee"] = maximum
    return {"H": H, "beta": beta, "positive_interval_count": len(gaps),
            "H_fallback_no_positive_intervals": not bool(gaps), "per_identity": per_identity,
            "quantile_method": "linear", "window": "(t-H,t]", "fee": "0.055/(1+staleness_commit)",
            "evidence_sufficient": bool(gaps) and math.isfinite(H) and H>0 and math.isfinite(beta) and beta>0}


def diagnose(rows, slow_ids, B_M):
    def norm_summary(group):
        observed = [r["raw_norm"] for r in group if r["raw_norm"] is not None]
        return dict(quantiles(observed), task_count=len(group), missing=len(group)-len(observed),
                    fraction_above_fixed_B_M=sum(v>B_M for v in observed)/len(observed) if observed else None)
    result = {"terminals": dict(Counter(r["state"] for r in rows)),
              "raw_norm_all_uploads": norm_summary(rows), "groups": {}}
    for name,group in [("fast",[r for r in rows if r["identity"] not in slow_ids]),
                       ("slow",[r for r in rows if r["identity"] in slow_ids]),
                       ("consumed",[r for r in rows if r["state"]=="consumed"]),
                       ("expired",[r for r in rows if r["state"]=="expired"])]:
        result["groups"][name] = norm_summary(group)
    lag_groups = {}
    for lo,hi in ((0,0),(1,1),(2,4),(5,8),(9,16),(17,64)):
        lag_groups[f"{lo}-{hi}"] = norm_summary([r for r in rows if r.get("staleness_commit") is not None
                                                 and lo<=r["staleness_commit"]<=hi])
    lag_groups["unconsumed"] = norm_summary([r for r in rows if r.get("staleness_commit") is None])
    result["staleness_commit_groups"] = lag_groups
    valid = sum(r["state"] not in ("expired","rejected") for r in rows)
    result["deadline_staleness_coverage"] = valid/len(rows)
    result["commit_age"] = quantiles([r["terminal_at"]-r["issued_at"] for r in rows if r["state"]=="consumed"])
    result["staleness_arrival"] = quantiles([r["staleness_arrival"] for r in rows if r["arrived_at"] is not None])
    result["staleness_commit"] = quantiles([r["staleness_commit"] for r in rows if r["state"]=="consumed"])
    retention = {}
    for name,membership in (("fast",False),("slow",True)):
        group = [r for r in rows if (r["identity"] in slow_ids)==membership]
        nominal = math.fsum(.05/(1+(r["staleness_arrival"] if r["arrived_at"] is not None
                                   else r["staleness_expiry"])) for r in group)
        actual = math.fsum(r["actual_coefficient"] for r in group)
        retention[name] = {"actual":actual,"arrival_nominal":nominal,"retention":actual/nominal}
    retention["R_slow"] = retention["slow"]["retention"]/retention["fast"]["retention"]
    result["retention_diagnostic_only"] = retention
    return result
