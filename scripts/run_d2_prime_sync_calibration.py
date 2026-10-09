"""Trimmed phase 1: one seed, fixed synchronous FedAvg/RFA, no D2' runs."""
import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys
import time
import traceback
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/d2_prime_phase1_sync_20261009"
SOURCE = ROOT / "outputs/d1_3b/phase_a_ir5_p40_r300_20261002/manifest.json"
PYTHON = Path(r"E:\anaconda3\python.exe")
SEED = 101
sys.path[:0] = [str(ROOT), str(ROOT / "easyFL")]


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def save(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)+"\n", encoding="utf-8")


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def object_digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, allow_nan=False).encode()).hexdigest()


def evaluation_indices(labels, classes=10):
    dev, final = [], []
    for c in range(classes):
        ids = [i for i, label in enumerate(labels) if label == c]
        assert len(ids) % 2 == 0 and ids
        dev.extend(ids[:len(ids)//2])
        final.extend(ids[len(ids)//2:])
    return sorted(dev), sorted(final)


def metrics(curves):
    assert curves["round"][-5:] == [260, 270, 280, 290, 300]
    totals = curves["class_total"]
    assert len(totals) == 10 and all(n > 0 for n in totals)
    per_class = [[c/n for c, n in zip(row, totals)] for row in curves["class_correct"]]
    macro = [math.fsum(row)/10 for row in per_class]
    return {"M": math.fsum(macro[-5:])/5, "M_endpoint": macro[-1],
            "tail8_last5": math.fsum(row[8] for row in per_class[-5:])/5,
            "tail9_last5": math.fsum(row[9] for row in per_class[-5:])/5,
            "per_class_endpoint": per_class[-1], "M_last5_values": macro[-5:]}


def attack_decision(clean_avg, avg, rfa, activity_ok):
    if avg["M"] <= .15 and rfa["M"] <= .15:
        return "NEEDS_10_PERCENT" if activity_ok else "FAIL_INACTIVE_ATTACK"
    if not activity_ok:
        return "FAIL_INACTIVE_ATTACK"
    if clean_avg["M"]-avg["M"] < .05 or clean_avg["M_endpoint"] <= avg["M_endpoint"]:
        return "FAIL_INSUFFICIENT_AVG_DAMAGE"
    return "PASS" if rfa["M"] > .15 else "FAIL_RFA_FLOOR"


def norm_quantile(values):
    import numpy as np
    assert values and all(math.isfinite(v) and v >= 0 for v in values)
    q = float(np.quantile(values, .95, method="linear"))
    return {"B_M": q, "count": len(values), "method": "linear", "quantile": .95,
            "fraction_above_B_M": sum(v > q for v in values)/len(values)}


def prepare():
    import numpy as np
    import torch
    from flgo_byzantine.d1_cifar_lt.common import dataset
    assert not OUT.exists(), "refuse to overwrite experiment outputs"
    source = read(SOURCE)
    assert (source["IR"], source["alpha"], source["num_clients"]) == (5, 1., 100)
    record = source["tasks"][str(SEED)]
    task = Path(record["task"])
    assert digest(task/"info") == record["info_sha256"]
    assert digest(task/"data.json") == record["data_sha256"]
    info, data = read(task/"info"), read(task/"data.json")
    root = info["root_data"]
    assert root["imbalance_ratio"] == 5 and "dir1.00" in info["partitioner"]
    assert info["num_clients"] == len(data["client_names"]) == 100
    clients = [int(i) for name in data["client_names"] for i in data[name]["data"]]
    roots, pool = set(root["root_indices"]), set(root["client_pool_indices"])
    assert len(roots) == 2000 and len(clients) == len(set(clients)) and set(clients) == pool
    assert not roots & pool
    train_labels, test_labels = dataset("CIFAR10", True).targets, dataset("CIFAR10", False).targets
    expected = [int(round(4000*5**(-c/9))) for c in range(10)]
    counts = Counter(train_labels[i] for i in clients)
    assert [counts[c] for c in range(10)] == expected == root["lt_counts"]
    assert [sum(train_labels[i] == c for i in roots) for c in range(10)] == root["root_counts"]
    assert Counter(test_labels) == Counter({c: 1000 for c in range(10)})
    dev, final = evaluation_indices(test_labels)
    assert len(dev) == len(final) == 5000 and not set(dev) & set(final)
    assert set(dev) | set(final) == set(range(10000))
    assert torch.cuda.is_available() and torch.__version__.startswith("2.5.1")
    history = []
    for name, path, method, fraction in [
        ("avg_clean", SOURCE.parent/"seed_101/result.json", "avg", 0.),
        ("avg_flip30", ROOT/"outputs/d1_3b/phase_b_20261003/attack_validation_seed_101/result.json", "avg", .3)]:
        old = read(path)
        assert old["seed"] == SEED and old["rounds"] == 300
        history.append({"requested_unit": name, "path": str(path), "sha256": digest(path),
            "task_match": True, "seed_match": True, "training_budget_match": True,
            "historical_method": old["method"], "historical_attack": old["attack"],
            "metric_dataset_match": False, "historical_class_total": old.get("class_total", [1000]*10),
            "new_class_total": [500]*10, "implementation_semantics_verified_equal": False,
            "implementation_difference": "legacy model average / legacy full bridge vs current difference average; no numeric trajectory equivalence evidence",
            "paired_participants_available": len(old["participants"]) == 300,
            "raw_norms_for_B_M_available": False, "credited": False,
            "reason": "evaluation indices differ; numeric implementation equivalence not established; clean run lacks raw upload norms"})
    for name in ("rfa_clean", "rfa_flip30"):
        history.append({"requested_unit": name, "credited": False,
            "reason": "no matching RFA training unit identified in D1 summary sections 2/7; root methods are different algorithms"})
    files = ["docs/D2_PRIME_CHECKPOINTS_TRIMMED.md", "docs/D2_PRIME_CHECKPOINTS.md", "docs/D2_PRIME_DESIGN.md",
             "docs/D2_PRIME_PHASE05_07_REPORT.md", "docs/D1_EXPERIMENT_COMPLETE_SUMMARY_20261005.md",
             "docs/D2_PRIME_RFA_INTERFACE_REPORT.md", "aggregators/rfa.py", "aggregators/rfa_contributions.py",
             "flgo_byzantine/algorithm.py", "run_flgo_byzantine.py", "scripts/run_d2_prime_sync_calibration.py"]
    prereg = {"seed": SEED, "source_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "task": str(task), "task_sha256": {k: digest(task/k) for k in ("info", "data.json")},
        "IR": 5, "alpha": 1., "num_clients": 100, "rounds": 300, "clients_per_round": 40,
        "num_epochs": 1, "batch_size": 64, "learning_rate": .1, "lr_scheduler": "-1",
        "optimizer": "SGD", "momentum": 0., "weight_decay": 0., "dataseed": 0,
        "rfa_T": 5, "rfa_nu": 1e-6, "B": "rfa", "gpu": torch.cuda.get_device_name(0),
        "cuda_memory_free_total": list(torch.cuda.mem_get_info()), "root_pool": len(roots),
        "client_pool": len(pool), "class_counts": expected, "training_client_indices": {n:data[n]["data"] for n in data["client_names"]},
        "development_indices": dev, "final_evaluation_indices": final,
        "data_usage": {"client_training": "unchanged historical IR5 task, roots excluded",
            "attack_optimization": "none; fixed cyclic flip uses malicious training labels only",
            "development": "first 500 official-test samples per class, original-index order; used for calibration metrics",
            "final_evaluation": "remaining 500 per class, never evaluated by this runner; already seen in historical D1 full-test evaluation, not pristine data",
            "test_history": "entire official test set previously evaluated in D1; seed101 is development, not confirmation"},
        "train_labels_sha256": hashlib.sha256(np.asarray(train_labels, dtype="<i8").tobytes()).hexdigest(),
        "test_labels_sha256": hashlib.sha256(np.asarray(test_labels, dtype="<i8").tobytes()).hexdigest(),
        "history_credit": history, "credited_units": 0,
        "initial_matrix": [{"method": m, "fraction": f} for f in (0., .3) for m in ("avg", "rfa")],
        "max_full_units": 6, "conditional_10": "only if BOTH 30% methods at M<=15% and attack wiring valid",
        "source_sha256": {p:digest(ROOT/p) for p in files}}
    prereg["configuration_hash"] = object_digest(prereg)
    OUT.mkdir(parents=True)
    save(OUT/"preregister.json", prereg)
    print("DATA_AUDIT_OK " + json.dumps({k:prereg[k] for k in ("task", "client_pool", "root_pool", "class_counts", "configuration_hash", "gpu")}), flush=True)


def run_unit(method, fraction, smoke):
    import numpy as np
    import torch
    import flgo
    import flgo_byzantine
    import flgo_byzantine.algorithm as bridge
    from aggregators.rfa import RFA
    from aggregators.fedavg import fedAVG
    from aggregators.contribution_diagnostics import trace, two_layer_errors, require_two_layers
    from attacks.flgo_label_flip import LabelFlippedDataset
    from run_flgo_byzantine import ByzantineLogger

    prereg = read(OUT/"preregister.json")
    for p, h in prereg["source_sha256"].items():
        assert digest(ROOT/p) == h, f"source changed after preregistration: {p}"
    task = Path(prereg["task"])
    for p, h in prereg["task_sha256"].items():
        assert digest(task/p) == h
    assert method in ("avg", "rfa") and fraction in (0., .1, .3)
    if not smoke:
        for m in ("avg", "rfa"):
            for f in (0., .3):
                assert read(OUT/f"smoke_{m}_{int(f*100)}/result.json")["engineering_ok"]
        if fraction:
            assert read(OUT/"full_avg_0/result.json")["metrics"]["M"] >= .4
            assert read(OUT/"full_rfa_0/result.json")["metrics"]["M"] > .15
        if fraction == .1:
            assert all(read(OUT/f"full_{m}_30/result.json")["metrics"]["M"] <= .15 for m in ("avg", "rfa"))
            assert all(read(OUT/f"full_{m}_30/result.json")["activity_ok"] for m in ("avg", "rfa"))
    rounds = 5 if smoke else 300
    directory = OUT/f"{'smoke' if smoke else 'full'}_{method}_{int(fraction*100)}"
    directory.mkdir()
    for name in ("record", "log"):
        (directory/name).mkdir()
    options = {"gpu": [0], "num_rounds": rounds, "num_epochs": 1, "batch_size": 64,
        "test_batch_size": 128, "num_steps": -1, "proportion": .4, "sample": "uniform", "aggregate": "uniform",
        "learning_rate": .1, "lr_scheduler": "-1", "optimizer": "SGD", "momentum": 0., "weight_decay": 0.,
        "seed": SEED, "dataseed": 0, "num_workers": 0, "num_parallels": 1, "torch_num_threads": 1,
        "train_holdout": 0., "test_holdout": 0., "eval_interval": 1 if smoke else 10,
        "no_tqdm": True, "no_log_console": True, "log_file": True,
        "byz_aggregator": method, "byz_attack": "none" if not fraction else "label_flip",
        "byz_malicious_fraction": fraction, "byz_label_flip_num_classes": 10, "byz_seed": SEED,
        "byz_assumed_count": 0, "byz_rfa_steps": 5, "byz_rfa_nu": 1e-6}
    class UnitLogger(ByzantineLogger):
        def get_output_path(self): return str(directory/"record")
        def get_log_path(self): return str(directory/"log")
    with patch.object(bridge, "load_root_data", side_effect=AssertionError("defense must never load roots")) as root_guard:
        runner = flgo.init(str(task), flgo_byzantine, options, Logger=UnitLogger)
        assert runner.num_clients == 100 and len(runner.clients) == 100
        assert runner.learning_rate == .1 and runner.lr_scheduler_type == "-1"
        assert type(runner.model).__module__ == "flgo.benchmark.cifar10_classification.model.cnn"
        assert sum(p.numel() for p in runner.model.parameters()) == 797962
        assert all(p.dtype == torch.float32 for p in runner.model.parameters())
        assert sum(c.datavol for c in runner.clients) == prereg["client_pool"]
        initial = bridge._parameter_vector(runner.model)
        initial_hash = hashlib.sha256(initial.cpu().numpy().tobytes()).hexdigest()
        sampling_initial = object_digest(np.random.get_state()[1].tolist())
        full_test = runner.test_data
        assert len(full_test) == 10000
        runner.test_data = torch.utils.data.Subset(full_test, prereg["development_indices"])
        assert len(runner.test_data) == 5000
        malicious = frozenset(int(cid) for cid in np.random.default_rng(SEED).choice(100, int(100*fraction), replace=False))
        assert runner.byz_malicious_ids == malicious
        train_targets = runner.clients[0].train_data
        while hasattr(train_targets, "source") or hasattr(train_targets, "dataset"):
            train_targets = train_targets.source if hasattr(train_targets, "source") else train_targets.dataset
        labels = train_targets.targets
        names = read(task/"data.json")["client_names"]
        label_audit = {"malicious_labels": 0, "honest_labels": 0, "root_labels_unwrapped": 2000,
                       "development_labels_unwrapped": 5000, "final_evaluation_forward_count": 0}
        for c in runner.clients:
            assert isinstance(c.train_data, LabelFlippedDataset) == (c.id in malicious)
            assert c.val_data is None and c.test_data is None
            source = c.train_data.source if c.id in malicious else c.train_data
            assert list(source.indices) == prereg["training_client_indices"][names[c.id]]
            for j, raw_id in enumerate(source.indices):
                observed = int(c.train_data[j][-1])
                expected = (labels[raw_id]+1) % 10 if c.id in malicious else labels[raw_id]
                assert observed == expected
            label_audit["malicious_labels" if c.id in malicious else "honest_labels"] += len(c.train_data)
        work = {"tasks": 0, "minibatches": 0, "training_samples": 0}
        for c in runner.clients:
            assert c.num_steps == math.ceil(c.datavol/64) and c.learning_rate == .1
            loss_fn = c.calculator.compute_loss
            def loss(model, batch, fn=loss_fn):
                work["minibatches"] += 1
                work["training_samples"] += len(batch[-1])
                return fn(model, batch)
            c.calculator.compute_loss = loss
            train_fn = c.train
            def train(model, fn=train_fn):
                work["tasks"] += 1
                return fn(model)
            c.train = train
        curves = {"round": [], "class_total": [500]*10, "class_correct": [], "class_loss_mean": []}
        runner.calculator.collect_class_stats = True
        original_log = runner.gv.logger.log_once
        def log_once(*args, **kwargs):
            original_log(*args, **kwargs)
            stats = runner.calculator.last_class_statistics
            assert stats["class_total"] == [500]*10
            correct = stats["class_correct"]
            assert all(type(n) is int and 0 <= n <= 500 for n in correct)
            assert sum(correct)/5000 == runner.gv.logger.output["test_accuracy"][-1]
            curves["round"].append(0 if not curves["round"] else int(runner.current_round))
            curves["class_correct"].append(correct)
            curves["class_loss_mean"].append(stats["class_loss_mean"])
        runner.gv.logger.log_once = log_once
        rows, participants, upload_norms = [], [], []
        captured = {}
        original_call = (RFA if method == "rfa" else fedAVG).__call__
        def capture_call(instance, inputs):
            output = original_call(instance, inputs)
            captured["z"] = output.detach().clone()
            return output
        original_aggregate = runner.aggregate
        round_file = (directory/"rounds.jsonl").open("w", encoding="utf-8")
        def aggregate(models, *args, **kwargs):
            before = bridge._parameter_vector(runner.model)
            actual_inputs = [before-bridge._parameter_vector(m).to(before) for m in models]
            ids = [int(cid) for cid in runner.received_clients]
            assert ids == [int(cid) for cid in runner.selected_clients] and len(set(ids)) == len(ids) == 40
            norms = [v.double().norm().item() for v in actual_inputs]
            assert all(math.isfinite(n) for n in norms)
            result_model = original_aggregate(models, *args, **kwargs)
            z = captured.pop("z")
            if method == "rfa":
                record = runner.byz_last_contribution
                assert record["semantics"] == "rfa_final_mix_v1"
                assert [entry["client_id"] for entry in record["clients"]] == ids
                weights = tuple(entry["weight"] for entry in record["clients"])
                assert weights == runner._byz_aggregator_instance.last_client_weights
                checks = record["writeback_checks"]
                assert checks["layer1_pass"] and checks["layer2_pass"] and checks["writeback_exact"]
            else:
                weights = (1/40,)*40  # The exact FedAvg definition, not an RFA fallback.
                zero = torch.zeros_like(z)
                decomposition = trace(actual_inputs, [zero]*40, [-w for w in weights], [0.]*40, zero, zero)
                checks = two_layer_errors(decomposition, before, -z, bridge._parameter_vector(result_model))
                require_two_layers(checks)
                record = None
            bad = [i for i, cid in enumerate(ids) if cid in malicious]
            row = {"round": len(rows)+1, "received_ids": ids, "raw_update_l2": norms,
                "malicious_uploads": len(bad), "malicious_legal_nonzero": sum(norms[i] > 1e-12 for i in bad),
                "malicious_effective_contribution_l2_sum": sum(weights[i]*norms[i] for i in bad),
                "checks": checks, "rfa_contribution": record}
            assert runner._byz_root_data is None and root_guard.call_count == 0
            rows.append(row)
            participants.append(ids)
            upload_norms.extend(norms)
            round_file.write(json.dumps(row, allow_nan=False)+"\n")
            round_file.flush()
            return result_model
        runner.aggregate = aggregate
        started = time.perf_counter()
        with patch.object(RFA if method == "rfa" else fedAVG, "__call__", capture_call):
            runner.run()
        elapsed = time.perf_counter()-started
        round_file.close()
        assert len(rows) == rounds and runner.current_round == rounds+1
        assert work["tasks"] == rounds*40
        data = read(task/"data.json")
        expected_samples = sum(len(data[names[cid]]["data"]) for p in participants for cid in p)
        expected_batches = sum(math.ceil(len(data[names[cid]]["data"])/64) for p in participants for cid in p)
        assert work["training_samples"] == expected_samples and work["minibatches"] == expected_batches
        intervals = {}
        if fraction and not smoke:
            for lo, hi in ((151, 200), (201, 250), (251, 300)):
                den = sum(r["malicious_uploads"] for r in rows[lo-1:hi])
                num = sum(r["malicious_legal_nonzero"] for r in rows[lo-1:hi])
                intervals[f"{lo}-{hi}"] = {"nonzero": num, "uploads": den, "fraction": num/den if den else None}
        result = {"method": method, "fraction": fraction, "seed": SEED, "rounds": rounds,
            "configuration_hash": prereg["configuration_hash"], "effective_options": runner.option,
            "initial_model_sha256": initial_hash, "sampling_initial_sha256": sampling_initial,
            "participants_sha256": object_digest(participants), "participants": participants,
            "root_loader_calls": root_guard.call_count, "label_audit": label_audit,
            "work": work, "engineering_ok": True, "activity_intervals": intervals,
            "activity_ok": all(v["fraction"] is not None and v["fraction"] >= .8 for v in intervals.values()),
            "metrics": metrics(curves) if not smoke else {"endpoint_macro": sum(curves["class_correct"][-1])/5000},
            "elapsed_seconds": elapsed, "peak_cuda_memory_allocated": torch.cuda.max_memory_allocated(),
            "maximum_E_alg": max(r["checks"]["E_alg"] for r in rows),
            "maximum_E_model": max(r["checks"]["E_model"] for r in rows),
            "all_actual_writebacks_exact": all(r["checks"]["writeback_exact"] for r in rows)}
        if method == "avg" and fraction == 0 and not smoke:
            assert len(upload_norms) == 12000
            result["norm_quantile"] = norm_quantile(upload_norms)
        save(directory/"class_curves.json", curves)
        save(directory/"result.json", result)
        torch.save(runner.model.state_dict(), directory/"final_model.pt")
        for p, h in prereg["task_sha256"].items():
            assert digest(task/p) == h
        print("UNIT_COMPLETE "+json.dumps({"unit": directory.name, "metrics": result["metrics"],
              "elapsed_seconds": elapsed, "work": work, "initial_model_sha256": initial_hash,
              "participants_sha256": result["participants_sha256"]}), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("prepare", "smoke", "unit"))
    parser.add_argument("--method", choices=("avg", "rfa"))
    parser.add_argument("--fraction", type=float, choices=(0., .1, .3), default=0.)
    args = parser.parse_args()
    assert Path(sys.executable).resolve() == PYTHON.resolve()
    try:
        prepare() if args.action == "prepare" else run_unit(args.method, args.fraction, args.action == "smoke")
    except Exception:
        traceback.print_exc()
        sys.exit(1)
