"""Plan, run, resume and summarize the four FLGo research experiments.

Example:
  python research_suite.py --task ./mnist_dir20 --root-ids 2,11 --output ./research_runs_v2 --run
  python research_suite.py --output ./research_runs --summarize
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import statistics
import subprocess
import sys
from pathlib import Path
from time import perf_counter


ROOT = Path(__file__).resolve().parent


def _implementation_revision():
    digest = hashlib.sha256()
    for name in ("run_research.py", "research_suite.py",
                 "flgo_byzantine/research_algorithm.py",
                 "flgo_byzantine/research_methods.py"):
        digest.update((ROOT / name).read_bytes())
    return digest.hexdigest()[:8]


def _ids(value):
    return [int(x) for x in value.split(",") if x.strip()]


def _percentile(values, fraction):
    if not values:
        return None
    values = sorted(values)
    index = (len(values) - 1) * fraction
    low = int(index)
    high = min(low + 1, len(values) - 1)
    return values[low] + (values[high] - values[low]) * (index - low)


def _conditions(phases, root_ids, root_class):
    conditions = []
    if 1 in phases:
        for attack in ("none", "ipm", "backdoor"):
            for mode in ("baseline", "triage"):
                conditions.append((1, f"{mode}_{attack}",
                                   {"mode": mode, "attack": attack}))
    if 2 in phases:
        for attack in ("ipm", "timed_ipm", "joint_random", "joint_timing"):
            for mode in ("baseline", "triage"):
                conditions.append((2, f"{mode}_{attack}",
                                   {"mode": mode, "attack": attack}))
    if 3 in phases:
        if not root_ids:
            raise ValueError("phase 3 needs --root-ids for a disjoint trusted set")
        conditions.append((3, "baseline_reserved_root",
                           {"mode": "baseline", "attack": "ipm"}))
        for mode in ("root_only", "root_fusion"):
            for samples in (20, 100):
                for noise in (0.0, 0.2):
                    conditions.append((3, f"{mode}_n{samples}_noise{noise}",
                                       {"mode": mode, "attack": "ipm",
                                        "root_samples": samples, "root_noise": noise}))
            conditions.append((3, f"{mode}_class{root_class}_only",
                               {"mode": mode, "attack": "ipm",
                                "root_samples": 100, "root_classes": [root_class]}))
    if 4 in phases:
        for attack in ("ipm", "joint_timing"):
            for mode in ("baseline", "triage"):
                conditions.append((4, f"{mode}_{attack}",
                                   {"mode": mode, "attack": attack}))
            for budget in (2.0, 10.0, 50.0):
                conditions.append((4, f"anytime_{attack}_{int(budget)}ms",
                                   {"mode": "anytime", "attack": attack,
                                    "budget_ms": budget}))
    return conditions


def _command(task, case, common):
    command = [sys.executable, str(ROOT / "run_research.py"),
               "--task", str(task), "--mode", case["settings"]["mode"],
               "--attack", case["settings"]["attack"],
               "--run-id", case["id"], "--seed", str(case["seed"]),
               "--rounds", str(common["rounds"]),
               "--proportion", str(common["proportion"]),
               "--malicious-fraction", str(common["malicious_fraction"]),
               "--delay-min", str(common["delay_min"]),
               "--delay-max", str(common["delay_max"]),
               "--max-staleness", str(common["max_staleness"]),
               "--attack-max-delay", str(common["attack_max_delay"])]
    if common["gpu"] is not None:
        command += ["--gpu", str(common["gpu"])]
    if common["root_ids"] and case["phase"] == 3:
        command += ["--root-ids", ",".join(map(str, common["root_ids"]))]
    for key, value in case["settings"].items():
        if key in {"mode", "attack"}:
            continue
        cli = "--" + key.replace("_", "-")
        command += [cli, ",".join(map(str, value)) if isinstance(value, list) else str(value)]
    return command


def _find_record(task, run_id, expected_rounds):
    for path in (task / "record").glob("*RESEARCH_*.json"):
        try:
            content = json.loads(path.read_text(encoding="utf-8"))
            config = content.get("research_config", [{}])[0]
            if (config.get("byz_run_id") == run_id and
                    len(content.get("test_accuracy", [])) >= expected_rounds):
                return str(path.resolve())
        except (OSError, ValueError, IndexError, TypeError):
            continue
    return None


def _last(values):
    return values[-1] if values else None


def _summarize_case(case):
    row = {"phase": case["phase"], "condition": case["condition"],
           "seed": case["seed"], "status": case["status"],
           "wall_seconds": case.get("wall_seconds"),
           "record": case.get("record") or ""}
    path = case.get("record")
    if not path or not Path(path).is_file():
        return row
    record = json.loads(Path(path).read_text(encoding="utf-8"))
    test_acc = record.get("test_accuracy", [])
    val_acc = record.get("val_accuracy_dist", [])
    asr = record.get("research_backdoor_asr", [])
    elapsed = record.get("time", [])
    aggregation = [float(x) for x in record.get("research_server_ms", [])
                   if x is not None]
    losses = [float(x) for x in record.get("test_loss", []) if x is not None]
    max_loss = max(losses, default=None)
    used = record.get("research_used", [])[1:]
    halted_rounds = 0
    for count in reversed(used):
        if count != 0:
            break
        halted_rounds += 1
    loss_explosion = max_loss is not None and (not math.isfinite(max_loss) or max_loss > 1e6)
    benign = sum(record.get("research_benign_decisions", []))
    minority = sum(record.get("research_minority_decisions", []))
    staleness = [x for round_values in record.get("research_staleness", [])
                 for x in round_values]
    misses = [x for x in record.get("research_deadline_miss", [])
              if isinstance(x, bool)]
    row.update({
        "final_accuracy": _last(test_acc),
        "run_health": "loss_explosion" if loss_explosion else "ok",
        "max_test_loss": max_loss,
        "halted_rounds": halted_rounds,
        "updates_used": sum(used),
        "malicious_updates_used": sum(record.get("research_malicious", [])),
        "minority_decisions": sum(record.get("research_minority_decisions", [])),
        "last_10_accuracy": statistics.mean(test_acc[-10:]) if test_acc else None,
        "worst_client_accuracy": min(_last(val_acc)) if val_acc and _last(val_acc) else None,
        "backdoor_asr": _last(asr),
        "virtual_time": _last(elapsed),
        "benign_false_reject_rate": sum(record.get("research_false_reject", [])) / benign if benign else None,
        "benign_defer_rate": sum(record.get("research_benign_deferred", [])) / benign if benign else None,
        "minority_false_reject_rate": sum(record.get("research_minority_false_reject", [])) / minority if minority else None,
        "minority_defer_rate": sum(record.get("research_minority_deferred", [])) / minority if minority else None,
        "mean_staleness": statistics.mean(staleness) if staleness else None,
        "server_p95_ms": _percentile(aggregation, 0.95),
        "deadline_miss_rate": sum(misses) / len(misses) if misses else None,
    })
    return row


def summarize(manifest, output):
    rows = [_summarize_case(case) for case in manifest["cases"]]
    fields = ["phase", "condition", "seed", "status", "final_accuracy",
              "run_health", "max_test_loss", "halted_rounds", "updates_used",
              "malicious_updates_used", "minority_decisions",
              "last_10_accuracy", "worst_client_accuracy", "backdoor_asr",
              "virtual_time", "wall_seconds", "benign_false_reject_rate",
              "benign_defer_rate", "minority_false_reject_rate",
              "minority_defer_rate", "mean_staleness",
              "server_p95_ms", "deadline_miss_rate", "record"]
    with (output / "summary.csv").open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    lines = ["# Research suite summary", "",
             f"Completed: {sum(c['status'] == 'complete' for c in manifest['cases'])}/{len(rows)}", "",
             "All numbers are descriptive; compare matched seeds and equal threat budgets before making claims.",
             "Completed means the process exited and wrote a record; run_health flags loss above 1e6 or non-finite loss.", "",
             "| Phase | Condition | Runs | Mean final accuracy | Mean ASR | Mean minority false reject | Mean p95 server ms |",
             "| --- | --- | ---: | ---: | ---: | ---: | ---: |"]
    groups = {}
    for row in rows:
        groups.setdefault((row["phase"], row["condition"]), []).append(row)
    def mean(group, key):
        values = [float(r[key]) for r in group if r.get(key) is not None]
        return f"{statistics.mean(values):.4f}" if values else "—"
    for (phase, condition), group in sorted(groups.items()):
        lines.append(f"| {phase} | {condition} | {sum(r['status'] == 'complete' for r in group)} | "
                     f"{mean(group, 'final_accuracy')} | {mean(group, 'backdoor_asr')} | "
                     f"{mean(group, 'minority_false_reject_rate')} | "
                     f"{mean(group, 'server_p95_ms')} |")
    lines += ["", "## Interpretation notes", "",
              "- Phase 1: evaluate minority false rejection jointly with clean accuracy and attack damage.",
              "- Phase 2: joint_random and joint_timing share the same vector rule and delay bound; inspect realized staleness before attributing changes to timing choice.",
              "- Phase 3: trusted clients are reserved from ordinary training in every phase-3 condition. Root noise and class coverage are controlled separately.",
              "- Phase 4: the deadline is soft. Report p95 aggregation time, deadline misses and virtual training time together.",
              "- Only backdoor conditions have an ASR. IPM and timing conditions use accuracy degradation and update diagnostics.", ""]
    (output / "summary.md").write_text("\n".join(lines), encoding="utf-8")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--run", action="store_true", help="Execute all planned conditions")
    parser.add_argument("--summarize", action="store_true", help="Only refresh summary from manifest")
    parser.add_argument("--phases", type=_ids, default=[1, 2, 3, 4])
    parser.add_argument("--seeds", type=_ids, default=[0, 1, 2])
    parser.add_argument("--root-ids", type=_ids, default=[])
    parser.add_argument("--root-class", type=int, default=0,
                        help="Class used for the root coverage stress test")
    parser.add_argument("--rounds", type=int, default=100)
    parser.add_argument("--proportion", type=float, default=0.3)
    parser.add_argument("--malicious-fraction", type=float, default=0.2)
    parser.add_argument("--delay-min", type=int, default=0)
    parser.add_argument("--delay-max", type=int, default=3)
    parser.add_argument("--max-staleness", type=int, default=8)
    parser.add_argument("--attack-max-delay", type=int, default=6)
    parser.add_argument("--gpu", type=int)
    args = parser.parse_args(argv)
    args.output.mkdir(parents=True, exist_ok=True)
    manifest_path = args.output / "manifest.json"
    if args.summarize:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        summarize(manifest, args.output)
        print(args.output / "summary.md")
        return
    if args.task is None or not args.task.is_dir():
        parser.error("--task must name an existing FLGo task")
    args.task = args.task.resolve()
    if not args.seeds or any(phase not in {1, 2, 3, 4} for phase in args.phases):
        parser.error("seeds must be nonempty and phases chosen from 1,2,3,4")
    if (args.rounds < 1 or not 0 < args.proportion <= 1 or
            not 0 <= args.malicious_fraction < 1 or
            args.delay_min < 0 or args.delay_max < args.delay_min or
            args.max_staleness < 0 or args.attack_max_delay < 0):
        parser.error("invalid training, participation, attack or delay settings")
    common = {"rounds": args.rounds, "proportion": args.proportion,
              "malicious_fraction": args.malicious_fraction,
              "delay_min": args.delay_min, "delay_max": args.delay_max,
              "max_staleness": args.max_staleness,
              "attack_max_delay": args.attack_max_delay,
              "root_ids": args.root_ids, "root_class": args.root_class,
              "gpu": args.gpu}
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest["task"] != str(args.task.resolve()) or manifest["common"] != common:
            parser.error("existing manifest has a different task or common settings; choose a new output directory")
        if args.run and manifest.get("implementation_revision") != _implementation_revision():
            parser.error("implementation changed since this manifest was created; choose a new output directory")
    else:
        revision = _implementation_revision()
        conditions = _conditions(set(args.phases), args.root_ids, args.root_class)
        cases = [{"id": f"p{phase}_{name}_s{seed}_v{revision}", "phase": phase,
                  "condition": name, "seed": seed, "settings": settings,
                  "status": "planned", "record": None}
                 for phase, name, settings in conditions for seed in args.seeds]
        manifest = {"task": str(args.task.resolve()), "common": common,
                    "cases": cases, "implementation_revision": revision}
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    if args.run:
        for case in manifest["cases"]:
            if case["status"] == "complete" and case.get("record") and Path(case["record"]).is_file():
                continue
            existing = _find_record(args.task, case["id"], common["rounds"])
            if existing:
                case["record"] = existing
                case["status"] = "complete"
                continue
            command = _command(args.task, case, common)
            print(f"Running {case['id']}", flush=True)
            started = perf_counter()
            with (args.output / (case["id"] + ".log")).open("w", encoding="utf-8") as log:
                result = subprocess.run(command, cwd=ROOT, check=False,
                                        stdout=log, stderr=subprocess.STDOUT)
            case["wall_seconds"] = perf_counter() - started
            case["record"] = _find_record(args.task, case["id"], common["rounds"])
            case["status"] = "complete" if result.returncode == 0 and case["record"] else "failed"
            manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
            if case["status"] == "failed":
                print(f"Failed {case['id']}; see {args.output / (case['id'] + '.log')}")
    summarize(manifest, args.output)
    print(f"Plan: {manifest_path}\nSummary: {args.output / 'summary.md'}")


if __name__ == "__main__":
    main()
