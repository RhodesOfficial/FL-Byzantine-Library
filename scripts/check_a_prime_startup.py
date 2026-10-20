"""S00: exact necessary-condition examples and training-count support only."""

import hashlib
import itertools
import json
import random
import time
import tracemalloc
from fractions import Fraction as F
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts/a_prime/s00/startup_check.json"
Q = F(2, 5)


def probability(scale, deadline):
    return Q * min(F(1), max(F(0), F(deadline, scale) - F(1, 2)))


def moments(g, m, p, used):
    """Enumerate outcomes, independently of closed-form bias/variance."""
    if any(x <= 0 for x in p) or any(x <= 0 for x in used):
        raise ValueError("positive support required")
    target = sum(g) / 2
    mean = mse = F(0)
    ratio_mean = F(0)
    for r in itertools.product((0, 1), repeat=2):
        mass = F(1)
        for j in range(2):
            mass *= p[j] if r[j] else 1 - p[j]
        estimate = sum(m[j] + r[j] / used[j] * (g[j] - m[j])
                       for j in range(2)) / 2
        mean += mass * estimate
        mse += mass * (estimate - target) ** 2
        ratio = sum(r[j] * g[j] for j in range(2)) / sum(r) if sum(r) else F(0)
        ratio_mean += mass * ratio
    bias = sum((p[j] / used[j] - 1) * (g[j] - m[j])
               for j in range(2)) / 2
    variance = sum(p[j] * (1 - p[j]) / used[j] ** 2 * (g[j] - m[j]) ** 2
                   for j in range(2)) / 4
    assert mean - target == bias
    assert mse == bias ** 2 + variance
    return {"mean": str(mean), "bias": str(bias), "variance": str(variance),
            "mse": str(mse), "finite_ratio_mean_empty_zero": str(ratio_mean)}


def support(dataset):
    folder = ROOT / "artifacts/direction_a/phase0_2_v1/tasks" / (
        f"FedPCC-0.2-candidate-{dataset}-N20-v1")
    info = json.loads((folder / "info.json").read_text(encoding="utf-8"))
    raw = (folder / "counts.json").read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    assert digest == info["artifact_sha256"]["counts.json"]
    counts = json.loads(raw)
    n = counts["n_ic"]
    # The archived contract uses client-major counts.
    assert isinstance(n, list) and len(n) == 20
    c = info["spec"]["classes"]
    assert all(len(row) == c and sum(row) > 0 for row in n)
    assert [sum(row[k] for row in n) for k in range(c)] == counts["N_c"]
    tail = counts["class_groups"]["tail"]
    tail_share = [F(sum(row[k] for k in tail), sum(row)) for row in n]
    slow = sorted(range(20), key=lambda i: (-tail_share[i], i))[:10]
    shuffled = random.Random(20261020).sample(range(20), 10)

    def mapping(ids):
        mixed = []
        single = []
        zero = []
        for k in range(c):
            holders = [i for i in range(20) if n[i][k]]
            if not holders:
                zero.append(k)
            if len(holders) == 1:
                single.append(k)
            if any(i in ids for i in holders) and any(i not in ids for i in holders):
                mixed.append(k)
        return {"slow_clients": sorted(ids), "mixed_classes": mixed,
                "mixed_tail_classes": [k for k in tail if k in mixed],
                "single_source_classes": single, "zero_source_classes": zero}

    primary = mapping(slow)
    return {"task": info["spec"]["identity"], "counts_sha256": digest,
            "source_commit": "e2d2b81", "classes": c, "clients": 20,
            "tail_classes": tail, "tail_share": [str(v) for v in tail_share],
            "primary": primary, "shuffled": mapping(shuffled),
            "minimum_structure_eligible": bool(primary["mixed_tail_classes"])
            and not primary["zero_source_classes"]}


def main():
    start = time.perf_counter()
    tracemalloc.start()
    if OUT.exists():
        raise FileExistsError("S00 evidence already exists; do not overwrite or rerun silently")
    p = (F(2, 5), F(1, 5))
    g = (F(1), F(-1))
    available_target = sum(p[j] * g[j] for j in range(2)) / sum(p)
    assert available_target == F(1, 3)
    results = {
        "oracle_no_cache": moments(g, (F(0), F(0)), p, p),
        "oracle_good_cache": moments(g, (F(4, 5), F(-4, 5)), p, p),
        "oracle_bad_cache": moments(g, (F(-1), F(1)), p, p),
        "estimated_probability": moments(g, (F(4, 5), F(-4, 5)), p, (F(2, 5), F(1, 4))),
        "cache_only_bias_example": {"cache": ["1", "0"], "mean": "1/2", "target": "0"},
    }
    assert results["oracle_no_cache"]["mse"] == "11/8"
    assert results["oracle_good_cache"]["mse"] == "11/200"
    assert results["oracle_bad_cache"]["mse"] == "11/2"
    assert results["estimated_probability"]["bias"] == "1/50"
    assert results["oracle_no_cache"]["finite_ratio_mean_empty_zero"] == "1/5"
    equal_p = (Q, Q)
    equal_probability_bias = sum(equal_p[j] * g[j] for j in range(2)) / sum(equal_p)
    equal_gradient_bias = sum(p) / sum(p) - 1
    single_source_bias = p[0] / p[0] - 1
    assert equal_probability_bias == equal_gradient_bias == single_source_bias == 0
    try:
        moments(g, (F(0), F(0)), (Q, F(0)), (Q, F(0)))
    except ValueError:
        zero_support_rejected = True
    else:
        raise AssertionError("zero support was accepted")
    rates = {str(d): {"fast": str(probability(1, d)), "slow": str(probability(4, d))}
             for d in (3, 4, 5, 6)}
    assert rates == {"3": {"fast": "2/5", "slow": "1/10"},
                     "4": {"fast": "2/5", "slow": "1/5"},
                     "5": {"fast": "2/5", "slow": "3/10"},
                     "6": {"fast": "2/5", "slow": "2/5"}}
    tasks = [support(d) for d in ("CIFAR10", "CIFAR100")]
    payload = {
        "run_id": "APRIME-S00-20261020-01", "protocol": "APRIME-EXP-v1",
        "scope": "exact_toys_and_training_counts_only_no_training",
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "availability_weighted_target_positive_case": str(available_target),
        "moments": results, "rates": rates,
        "zero_effect_controls_exact": True, "zero_support_rejected": zero_support_rejected,
        "tasks": tasks, "e01_minimum_structure_eligible": all(
            t["minimum_structure_eligible"] for t in tasks),
        "new_gradient_or_validation_or_test_results_read": False,
        "scientific_limit": "No real-gradient bias, representation qualification or utility established",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    assert len(encoded.encode()) < 1024 ** 2
    OUT.write_text(encoded, encoding="utf-8", newline="\n")
    assert json.loads(OUT.read_text(encoding="utf-8")) == payload
    elapsed = time.perf_counter() - start
    peak = tracemalloc.get_traced_memory()[1]
    tracemalloc.stop()
    assert elapsed < 60
    # Resource envelope includes evidence save/readback; receipt writing excluded.
    receipt = {"run_id": payload["run_id"], "compute_and_evidence_io_seconds": elapsed,
               "python_tracemalloc_peak_bytes": peak,
               "process_peak_bytes": None, "gpu_used": False,
               "evidence_bytes": OUT.stat().st_size,
               "scope_note": "imports/process startup and receipt write excluded"}
    receipt_path = OUT.with_name("resource_receipt.json")
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"eligible": payload["e01_minimum_structure_eligible"],
                      "mixed_tail_counts": {t["task"]: len(t["primary"]["mixed_tail_classes"])
                                            for t in tasks},
                      "resources": receipt}, ensure_ascii=False))


if __name__ == "__main__":
    main()
