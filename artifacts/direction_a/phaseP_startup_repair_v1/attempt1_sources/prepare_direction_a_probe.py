"""Sole FedPCC-P-preparation-v2 execution, launched by the recovery wrapper.

Run through scripts/recover_direction_a_probe.py after its pure syntax check.
An existing output ledger forbids restarting, including after failure.
"""

import os
import time

if "RECOVERY_CONTEXT" not in globals():
    raise RuntimeError("Use the recovery wrapper: it records syntax/startup costs and forbids restarts")
STARTED = RECOVERY_CONTEXT["started"]
os.environ["CUBLAS_WORKSPACE_CONFIG"] = ":4096:8"

import gc
import hashlib
import importlib.util
import io
import json
import math
import subprocess
import sys
import threading
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.dont_write_bytecode = True

import numpy as np
import torch
import torch.nn.functional as F

from direction_a.backbone_preparation import encode, sha, tensor_state_sha, PreparationLimit
from direction_a.probe_startup import RecoveryBudget
from direction_a.probe_preparation import (ADAM, STEPS, SPLIT_SEED, PERMUTATION_SEEDS,
    differences, fit_head, permute_labels, split_train, summarize, uniform_control)

BASE = "d7706748e70f63885572aded57fab9e674d1a086"
EVIDENCE_COMMIT = "d3a3bd712d6bb28283b59faff16e17e099debcb4"
RUN_ID = "FedPCC-P-preparation-v2"
G12 = ROOT / "artifacts/direction_a/phaseG1_2_full_v1"
UPSTREAM = ROOT / "artifacts/direction_a/backbone_preparation_v1"
OUTPUT = ROOT / "artifacts/direction_a/phaseP_preparation_v2"
REVIEW = ROOT / "docs/workflow/TO_REVIEWER.md"
SOURCES = ["direction_a/probe_preparation.py", "scripts/prepare_direction_a_probe.py",
           "tests/test_direction_a_probe_preparation.py", "direction_a/class_gradient_full.py",
           "direction_a/backbone_preparation.py", "scripts/recover_direction_a_probe.py",
           "direction_a/probe_startup.py"]
LIMITS = dict(attempts=0, optimizer_steps=4800, backwards=4800, forwards=6000, scans=9984,
              evidence_bytes=120*1024**2, logical_copy_bytes=120*1024**2, retries=0, fits=24,
              preparation_runs=1, formal_runs=0, implementation_revisions=2, searches=0,
              feature_samples=0, client_scans=0, class_gradient_requests=0, extra_encoded_positions=0,
              encoder_forwards=0, communications=0, gpu_allocated_bytes=6*1024**3,
              windows_peak_working_set_bytes=6*1024**3, cpu_tensor_proxy_bytes=2*1024**3,
              wall_seconds=599, phase_seconds={}, per_run={})


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT).decode().strip()


def digest_file(path, budget):
    budget.scan()
    budget.check()
    with Path(path).open("rb") as stream:
        result = hashlib.file_digest(stream, "sha256").hexdigest()
    budget.check()
    return result


def read_json(path, budget):
    budget.scan()
    return json.loads(Path(path).read_bytes())


def repo_path(path):
    return Path(path).relative_to(ROOT).as_posix()


def committed(path, commit, budget):
    budget.scan()
    relative = repo_path(path)
    if git("hash-object", str(path)) != git("rev-parse", f"{commit}:{relative}"):
        raise RuntimeError("committed input changed: " + relative)


def write(path, value, budget, raw=False):
    data = value if raw else encode(value)
    path = Path(path)
    if len(data) > 20*1024**2:
        path = ROOT / "artifacts_local" / path.relative_to(ROOT)
    budget.write(path, data, raw=True)
    return dict(path=repo_path(path), bytes=len(data), sha256=sha(data))


def save_head(path, value, budget):
    stream = io.BytesIO()
    torch.save(value, stream)
    locator = write(path, stream.getvalue(), budget, raw=True)
    restored = torch.load(ROOT/locator["path"], map_location="cpu", weights_only=True)
    budget.scan()
    for k in ("weight", "bias"):
        if not torch.equal(value[k], restored[k]) or restored[k].dtype != torch.float32:
            raise RuntimeError("probe head save/readback mismatch")
    return locator


def frozen_checkpoint(reference, accepted, budget):
    path = UPSTREAM / reference["checkpoint_path"]
    if digest_file(path, budget) != reference["checkpoint_file_sha256"]:
        raise RuntimeError("checkpoint file identity mismatch")
    packet = torch.load(path, map_location="cpu", weights_only=True)
    state, meta = packet["state_dict"], packet["metadata"]
    budget.scan()
    state_hash = tensor_state_sha(state)
    if (state_hash != reference["state_sha256"] or meta["state_sha256"] != state_hash or
        accepted["state_before"] != state_hash or accepted["state_after"] != state_hash or
        meta["reference_id"] != reference["reference_id"] or
        meta["task_identity"] != reference["task_identity"] or
        meta["task_source_sha256"] != {k: v["sha256"] for k, v in accepted["binding"]["source_files"].items()} or
        meta["update_round"] != reference["training_progress"]["update_round"] or
        not accepted["no_parameter_grad_or_update"]):
        raise RuntimeError("accepted reference state/provenance mismatch")
    return packet, state_hash


def load_train(reference, point, accepted, index, budget):
    """All labels/features are the accepted train-only G1.2 cache; no raw data access."""
    task_dir = ROOT / accepted["binding"]["task_directory"]
    sealed = {}
    for name in ("data.json", "counts.json", "info.json"):
        path = task_dir/name
        if digest_file(path, budget) != accepted["binding"]["source_files"][name]["sha256"]:
            raise RuntimeError("sealed train task changed")
        sealed[name] = read_json(path, budget)
    # The sealed JSON also contains metadata for other splits. Only the train
    # fields below are used; no validation/test indices, labels or samples accessed.
    train_rows = [{"id": row["id"], "train": row["train"]} for row in sealed["data.json"]["clients"]]
    path = G12 / point["diagnostic"]["path"]
    expected = index["files"][point["diagnostic"]["path"]]
    if digest_file(path, budget) != expected or expected != point["diagnostic"]["sha256"]:
        raise RuntimeError("accepted train diagnostic changed")
    # Raw deserialization storage + tensor clones + feature concatenation/indexing
    # + save buffers + optimizer overhead, conservative for the largest cache.
    envelope = 8*path.stat().st_size + 8*point["sample_count"]*128*4 + 64*1024**2
    budget.cpu_proxy(envelope)
    cache = torch.load(path, map_location="cpu", weights_only=True)
    C, groups = accepted["binding"]["C"], sealed["counts.json"]["class_groups"]
    if groups != accepted["binding"]["class_groups"]:
        raise RuntimeError("sealed groups differ from accepted groups")
    features, labels, global_indices, clients = [], [], [], []
    if sorted(cache["clients"]) != list(range(20)) or len(train_rows) != 20:
        raise RuntimeError("cache is not the accepted full 20-client train population")
    for i, row in enumerate(train_rows):
        budget.scan()
        client = cache["clients"][i]
        z, y = client["features_float32"], client["labels"]
        indices = client["global_train_indices"]
        if torch.is_tensor(indices):
            indices = indices.tolist()
        if (row["id"] != f"client_{i:03d}" or row["train"] != indices or
            z.shape != (len(indices), 128) or z.dtype != torch.float32 or y.shape != (len(indices),) or
            y.dtype != torch.int64 or not bool(torch.isfinite(z).all()) or
            torch.bincount(y, minlength=C).tolist() != sealed["counts.json"]["n_ic"][i]):
            raise RuntimeError("client train feature/index/label/count mismatch")
        clients.append(dict(client_id=i, sample_denominator=len(indices),
                            train_indices_sha256=sha(encode(indices)), labels_sha256=sha(y.numpy().tobytes()),
                            features_sha256=sha(z.numpy().tobytes())))
        features.append(z); labels.append(y); global_indices.extend(indices)
    z, y = torch.cat(features), torch.cat(labels)
    indices = np.asarray(global_indices, np.int64)
    budget.scan()
    if len(np.unique(indices)) != len(indices) or torch.bincount(y, minlength=C).tolist() != sealed["counts.json"]["N_c"]:
        raise RuntimeError("global train population/count mismatch")
    order = np.argsort(indices)
    z, y, indices = z[order], y[order], indices[order]
    original = dict(weight=cache["weight_float32"].clone(), bias=cache["bias_float32"].clone())
    del cache, features, labels, sealed
    gc.collect()
    return z, y, indices, C, groups, original, dict(
        reference_id=reference["reference_id"], diagnostic_path=repo_path(path), diagnostic_sha256=expected,
        clients=clients, original_train_samples=len(indices),
        label_provenance="byte-identical accepted G1.2 train cache; accepted G1.2 measured labels against official train and sealed n_ic",
        raw_dataset_reads=0, validation_samples_accessed=0, test_samples_accessed=0,
        cpu_proxy_envelope_bytes=envelope)


def threshold_and_plan(results, splits, budget):
    """Descriptive proposals. Neither a P decision nor a frozen threshold."""
    null_rows, resolution, candidate = [], {}, {}
    for ds, split in splits.items():
        den = [r["calibration"] for r in split["denominators"]]
        group_ids = next(p["class_groups"] for p in results["references"] if p["dataset"] == ds)
        resolution[ds] = {name: dict(per_class_recall_increment_pp=[100/den[c] for c in ids],
                                     single_correct_macro_increment_pp=[100/(len(ids)*den[c]) for c in ids],
                                     sample_denominator=sum(den[c] for c in ids), class_denominator=len(ids))
                          for name, ids in {"all": list(range(len(den))), **group_ids}.items()}
        # Uses ONLY the null controls, chance, and denominators; never real scores.
        points = [p for p in results["references"] if p["dataset"] == ds]
        maximum = max(h["metrics"]["groups"]["tail"]["macro_recall_percent"]
                      for p in points for h in p["heads"] if h["label_kind"] == "permuted")
        tick = max(resolution[ds]["tail"]["single_correct_macro_increment_pp"])
        chance = 100/len(den)
        delta = max(5., 2*tick)
        candidate[ds] = dict(tau_probe_candidate_percent=math.ceil((max(maximum, chance)+tick)*10)/10,
                             minimum_improvement_candidate_pp=math.ceil(delta*10)/10,
                             largest_single_correct_tail_macro_tick_pp=tick,
                             descriptive_null_max_percent=maximum, chance_percent=chance,
                             frozen=False, uses_real_scores=False)
    for p in results["references"]:
        for g in ("all", "head", "middle", "tail"):
            scores = [h["metrics"]["groups"][g]["macro_recall_percent"] for h in p["heads"] if h["label_kind"] == "permuted"]
            null_rows.append(dict(reference=p["reference_id"], group=g, seeds=PERMUTATION_SEEDS,
                                  scores_percent=scores, min_percent=min(scores), max_percent=max(scores)))
    results["threshold_basis"] = dict(status="descriptive_only_NOT_frozen", null_ranges=null_rows,
                                      resolution=resolution, candidates=candidate)
    lines = ["# P准备门槛依据（未冻结）", "",
        "τ_probe定义为尾组macro recall绝对百分比门槛；改善量用百分点，二者不能混用。正式科学判据由审查者冻结。",
        "候选规则在预注册中锁定，只使用内部置乱范围、解析机会水平和分母：τ候选=ceil_0.1(max(零对照最大值,100/C)+最大单样本尾macro刻度)。",
        "最低改善量候选=ceil_0.1(max(5 pp,2×最大单样本尾macro刻度))；5 pp为待审的实际效果下限，两个刻度避免一例翻转决定改善。此选择不能代替统计不确定性评估。",
        "候选值仅作工程讨论，不是控制假阳性率的门槛；未用真实头分数调整，未通过或否定P，未更换参考。", "",
        "|数据集|零对照尾最大值 %|机会 %|最大一例尾macro刻度 pp|候选τ %|最低改善候选 pp|",
        "|---|---:|---:|---:|---:|---:|"]
    for ds, v in candidate.items():
        lines.append(f"|{ds}|{v['descriptive_null_max_percent']:.6f}|{v['chance_percent']:.6f}|{v['largest_single_correct_tail_macro_tick_pp']:.6f}|{v['tau_probe_candidate_percent']:.1f}|{v['minimum_improvement_candidate_pp']:.1f}|")
    lines.extend(["", "## 全部内部零对照范围", "", "|参考|分组|5次分数 %|范围 %|", "|---|---|---|---|"])
    for r in null_rows:
        lines.append(f"|{r['reference']}|{r['group']}|{', '.join(f'{x:.6f}' for x in r['scores_percent'])}|{r['min_percent']:.6f}–{r['max_percent']:.6f}|")
    lines.extend(["", "## 分母和离散性", "",
        "split.json保存每类拟合/校准分母；results.json.threshold_basis.resolution保存每类100/n_c召回刻度和每组100/(K*n_c)的单例macro刻度（百分点），保留单样本类。"])
    for ds, res in resolution.items():
        tail = res["tail"]
        lines.append(f"- {ds}尾组：{tail['class_denominator']}类/{tail['sample_denominator']}例；逐类刻度范围{min(tail['per_class_recall_increment_pp']):.6f}–{max(tail['per_class_recall_increment_pp']):.6f} pp；单例macro刻度范围{min(tail['single_correct_macro_increment_pp']):.6f}–{max(tail['single_correct_macro_increment_pp']):.6f} pp。")
    lines.extend(["", "## 限制与正式方案", "",
        "5次置乱只给描述性范围；加一置乱p值最小1/6，无法证明可靠95%尾部分位数。两个相关快照、20个客户端以及10个跨快照零头都不是独立重复，不能合并成独立样本。",
        "正式建议每点真实1头+99次train标签置乱，四参考不变，同数据集两快照沿用同置乱以配对比较；评价只在原封存validation，test不使用。",
        "门槛须在正式评价前冻结。建议对预定尾macro统计报告加一Monte Carlo p值（最小1/100）和置乱超越概率的二项置信区间，并处理四点多重比较；99次仍不是高精度95%分位数保证。",
        "建议对validation按类重采样2000次，原头/探针/零头在相同样本上配对，报告各点尾macro改善的区间；重采样不作为新训练重复，客户端/快照不作独立重复。类少样本和类内依赖的局限仍需报告。",
        "固定200步测量只能证明当前求解预算的表现。results.json保存目标0/50/100/200及100→200相对下降；继续下降与低召回可同时出现，优化不充分不能推断表征无信息。",
        "formal_plan.json申请统一1000步；这是更充分求解的待审预算，仍不能保证收敛，不按参考或分数选择步数。正式冻结后若求解不充分，交回审查，不自行搜索或延长。"])
    write(OUTPUT/"threshold_basis.md", ("\n".join(lines)+"\n").encode("utf-8"), budget, raw=True)
    fit_seconds = sum(h["fit_and_evaluate_seconds"] for p in results["references"] for h in p["heads"])
    max_growth = max(sum(r["train"] for r in s["denominators"])/sum(r["fit"] for r in s["denominators"]) for s in splits.values())
    factor = (400/24)*(1000/200)*max_growth
    projected = fit_seconds*factor
    overhead = time.monotonic()-STARTED-fit_seconds
    total_request = math.ceil((2*(projected + max(overhead, 15)) + 120)/60)*60
    plan = dict(status="proposal_requires_reviewer_threshold_and_budget_freeze", executed=False,
        references=[p["reference_id"] for p in results["references"]],
        fit_scope="original full sealed train (no internal holdout)", evaluation_scope="original sealed validation only",
        test_access=False, tau_probe=None, minimum_improvement_pp=None,
        controls=["original frozen reference head", "analytic uniform probabilities", "99 globally permuted train label heads per point"],
        repeats=dict(real_heads_per_reference=1, permuted_heads_per_reference=99, total_heads=400,
                     paired_permutations_across_snapshots=True, independent_snapshot_or_client_replicates=False,
                     proposed_seeds=list(range(2026101501, 2026101600)), uncertainty_resamples=2000,
                     uncertainty_seed=20261016),
        optimizer=dict(name="Adam", **{**ADAM, "betas": list(ADAM["betas"])}),
        loss="full fit class-equal mean CE", initialization="zero float32 complete C*128 weight and C bias",
        target_steps_per_head=1000, optimizer_steps=400000, backwards=400000,
        no_early_stop_or_search=True,
        extrapolation=dict(measured_24_head_fit_and_evaluation_seconds=fit_seconds,
                           measured_nonfit_program_seconds_to_plan=overhead, maximum_full_train_size_growth=max_growth,
                           head_and_step_and_size_factor=factor, projected_fit_seconds=projected,
                           safety_factor=2, unmeasured_validation_encoding_and_uncertainty_reserve_seconds=120,
                           encoder_cost_is_not_measured_by_this_preparation=True,
                           limitation="linear size/steps extrapolation; formal encoding and uncertainty cost need approval"),
        budget_request=dict(wall_seconds=total_request, cumulative_write_bytes=128*1024**2,
                            cuda_allocated_bytes=6*1024**3, windows_working_set_bytes=6*1024**3,
                            cpu_tensor_proxy_bytes=2*1024**3, optimizer_steps=400000, backwards=400000,
                            head_forwards=401204, statistical_scans=500000, runs=1, retries=0, searches=0,
                            encoder_forwards=32, newly_encoded_validation_samples=4000,
                            newly_encoded_train_samples=0, communications=0,
                            encoding_basis="reuse full-train G1.2 caches; validation 1000 samples/reference, batch=128; proposal only"),
        uncertainty_plan=dict(permutation_p="(1+null_exceedances)/(1+99), binomial uncertainty; adjust four-point multiplicity",
                              validation_interval="2000 class-stratified paired resamples of fixed validation predictions",
                              caveats="99 nulls do not guarantee a precise 95% quantile; clients/snapshots not independent",
                              scientific_decision="freeze criteria before formal scores; no P decision from preparation"))
    write(OUTPUT/"formal_plan.json", plan, budget)
    return plan


def review_text(criteria, results, budget, blocked):
    refs = results.get("references", [])
    lines = ["# 交付单：P 可分性探针有界准备", "", f"- 对应任务单的基准 commit：{BASE}",
             "- 本次交付 commit：见本提交", "", "## 做了什么（≤5 条）",
             "- 锁定已通过G1.2训练缓存/原参考头；按类内部划分、全局置乱和固定200步执行。",
             f"- 完成{sum(len(p['heads']) for p in refs)}/24个头；自检与存储读回均在同一次受限运行。",
             "- 提交描述性门槛依据及正式方案申请；τ_probe未冻结，未运行正式P验证。", "", "## 产出文件",
             "- artifacts/direction_a/phaseP_preparation_v1/preregistration.json、split.json：输入及划分/置乱锁定。",
             "- 同目录results.json、heads/：目标下降、所有对照、逐类CE/recall及分母。",
             "- 同目录syntax_check.json、selfchecks.json、run_record.json、artifact_hashes.json：实际语法/相关检查、累计成本及自动哈希索引。",
             "- 同目录threshold_basis.md、formal_plan.json：描述性零范围/离散性与未放行的正式预算。",
             "- direction_a/probe_preparation.py、scripts/prepare_direction_a_probe.py、tests/test_direction_a_probe_preparation.py：实现及相关测试。",
             "", "## 判据自评", "| 判据编号 | 结果 PASS/FAIL | 证据位置 / 关键数字 |", "|---|---|---|"]
    evidence = {"1": "syntax_check.json、selfchecks.json、results.json.input_checks：语法/自检通过，G1.2缓存哈希、20端索引/标签频数、参考状态；新编码/正式评价0",
                "2": "split.json：每类拟合≥2/校准≥1，互斥并集=原train，同数据集两点完全相同",
                "3": "split.json.label_permutations、results.json：四点各1真+5置乱，频数守恒、校准真标签不变",
                "4": "heads/、results.json：完整C维/bias零初始化，Adam固定200步，0/50/100/200目标及有限性",
                "5": "results.json：逐类/全类/头中尾CE/recall/分母、解析机会、所有差值用pp；零值保留",
                "6": "run_record.json、artifact_hashes.json：全部头定位/读回/哈希；v1历史按基准commit保留、未知峰值/旧覆盖写入保留，有限豁免不追溯PASS",
                "7": "threshold_basis.md、formal_plan.json：未冻结门槛；5置乱只描述，优化与表征信息分开"}
    for k, v in criteria.items():
        lines.append(f"|{k}|{v}|{evidence[k]}|")
    for p in refs:
        if not p["heads"]:
            continue
        real = p["heads"][0]
        lines.append(f"- {p['reference_id']}：内部尾recall={real['metrics']['groups']['tail']['macro_recall_percent']:.6f}%，原头={p['original_head']['groups']['tail']['macro_recall_percent']:.6f}%；100→200目标相对下降={real['optimization']['relative_decline_100_to_200']:.6f}（非科学裁决）。")
    lines += ["", "## 实际资源消耗", "- 精确累计秒数/峰值显存/Windows working-set/CPU代理/写入见run_record.json；包含启动、自检、读盘、保存、归档及128 KiB应急槽。",
              f"- 拟合{budget.counts['fits']}次；反向/优化器{budget.counts['backwards']}/{budget.counts['optimizer_steps']}；新增encoder/编码/通信/类梯度请求均0。",
              "- 原G1.2成本与80端训练缓存生成费用见results.json.reused_costs，不计作本轮新编码。",
              "- v1历史：0.8109854秒/205825 B/归档扫描16继承；旧准备峰值和覆盖源码写入仍未知；新阶段及可核算累计成本见run_record.json。",
              "", "## 阻塞", blocked or "无", "", "## 异议", "无", "", "## 需要审查者裁决的问题（≤3 条，没有写\"无\"）",
              "- 正式P的τ_probe、最低改善量、重复/不确定性程序与formal_plan.json预算须冻结后另行放行。"]
    if len(lines) > 80:
        raise RuntimeError("review handoff exceeds 80 lines")
    return ("\n".join(lines)+"\n").encode("utf-8")


def archive(budget, extra_paths):
    files = [p for p in OUTPUT.rglob("*") if p.is_file() and p.name not in ("artifact_hashes.json", "run_record.json")]
    local = ROOT/"artifacts_local"/OUTPUT.relative_to(ROOT)
    if local.exists():
        files += [p for p in local.rglob("*") if p.is_file()]
    files += extra_paths
    records = {repo_path(p): dict(path=repo_path(p), bytes=p.stat().st_size,
                                 sha256=digest_file(p, budget)) for p in files}
    ledger_name = repo_path(budget.path)
    records[ledger_name] = dict(path=ledger_name, bytes=0, sha256="0"*64)
    index = dict(algorithm="SHA-256 file bytes", files=records,
                 excluded=[repo_path(OUTPUT/"artifact_hashes.json")+" (self)"],
                 generating_script=repo_path(Path(__file__)), source_sha256=sha(Path(__file__).read_bytes()),
                 parameters="preregistration.json; fixed protocol; no command-line overrides",
                 verification="all head readbacks; all archive sizes and SHA-256 re-read in same run")
    # Charge final ledger and index exactly, with fixed-size digest placeholders.
    before = budget.counts["evidence_bytes"]
    if budget.hit is not None:
        budget.status = "blocked_partial_preparation"
    now = time.monotonic()+0.1
    budget.context["finalization_time_reserved_seconds"] = 0.1
    for _ in range(12):
        ledger = budget.snapshot(now)
        records[ledger_name]["bytes"] = len(encode(ledger))
        budget.counts["evidence_bytes"] = before + len(encode(ledger)) + len(encode(index))
    ledger_raw = encode(budget.snapshot(now))
    records[ledger_name]["sha256"] = sha(ledger_raw)
    index_raw = encode(index)
    if budget.counts["evidence_bytes"] >= LIMITS["evidence_bytes"]:
        budget.stop("evidence_bytes", budget.counts["evidence_bytes"])
    budget.path.write_bytes(ledger_raw)
    (OUTPUT/"artifact_hashes.json").write_bytes(index_raw)
    for name, row in records.items():
        path = ROOT/name
        if path.stat().st_size != row["bytes"] or digest_file(path, budget) != row["sha256"]:
            raise RuntimeError("archive verification mismatch: "+name)
    # Record verification runtime/scans and re-charge the final replacements;
    # this final fixed closure cannot introduce a self-hash cycle.
    before = budget.counts["evidence_bytes"]
    now = time.monotonic()
    for _ in range(12):
        ledger = budget.snapshot(now)
        records[ledger_name]["bytes"] = len(encode(ledger))
        budget.counts["evidence_bytes"] = before + len(encode(ledger)) + len(encode(index))
    ledger_raw = encode(budget.snapshot(now))
    records[ledger_name]["sha256"] = sha(ledger_raw)
    if budget.counts["evidence_bytes"] >= LIMITS["evidence_bytes"]:
        budget.stop("evidence_bytes", budget.counts["evidence_bytes"])
    budget.check()
    budget.path.write_bytes(ledger_raw)
    (OUTPUT/"artifact_hashes.json").write_bytes(encode(index))


def main():
    if Path(sys.executable).resolve() != Path(r"E:\anaconda3\python.exe").resolve():
        raise RuntimeError("required interpreter mismatch")
    if (OUTPUT/"run_record.json").exists():
        raise RuntimeError("preparation already attempted; retries are forbidden")
    if subprocess.run(["git", "merge-base", "--is-ancestor", BASE, "HEAD"], cwd=ROOT).returncode:
        raise RuntimeError("task baseline is not HEAD or ancestor")
    budget = RecoveryBudget(RECOVERY_CONTEXT)
    RECOVERY_CONTEXT["budget"] = budget
    budget.consume("preparation_runs")
    watchdog_done = threading.Event()
    def watch():
        while not watchdog_done.wait(.2):
            try:
                budget.check()
            except PreparationLimit:
                RECOVERY_CONTEXT["emergency_report"]("Resource guard reached; no retry")
                os._exit(124)
    threading.Thread(target=watch, daemon=True).start()
    results, splits = dict(run_id=RUN_ID, references=[], input_checks=[],
        previous_failure_commit=BASE, previous_failure_criteria={str(i):"FAIL" for i in range(1,8)},
        previous_failure_directory="artifacts/direction_a/phaseP_preparation_v1",
        historical_unknowns_retained=True), {}
    criteria = {str(i): "FAIL" for i in range(1, 8)}
    RECOVERY_CONTEXT["results"] = results
    RECOVERY_CONTEXT["criteria"] = criteria
    try:
        if not torch.cuda.is_available():
            raise RuntimeError("CUDA required by preregistered bounded cost estimate")
        torch.set_num_threads(2)
        torch.use_deterministic_algorithms(True)
        torch.backends.cuda.matmul.allow_tf32 = False
        torch.backends.cudnn.allow_tf32 = False
        torch.cuda.reset_peak_memory_stats()
        budget.enter("input_and_preregistration")
        for name in ("preregistration.json", "reference_acceptance.json", "measurements.json", "artifact_hashes.json", "run_record.json", "decision.json"):
            committed(G12/name, EVIDENCE_COMMIT, budget)
        index = read_json(G12/"artifact_hashes.json", budget)
        for name in ("preregistration.json", "reference_acceptance.json", "measurements.json", "run_record.json", "decision.json"):
            if digest_file(G12/name, budget) != index["files"][name]:
                raise RuntimeError("accepted G1.2 package mismatch")
        acceptance = read_json(G12/"reference_acceptance.json", budget)
        measurements = read_json(G12/"measurements.json", budget)
        old = read_json(G12/"run_record.json", budget)
        g12_decision = read_json(G12/"decision.json", budget)
        if g12_decision["fail_count"] or g12_decision["blocked"]:
            raise RuntimeError("G1.2 input not accepted")
        refs = [p["reference"] for p in acceptance["references"]]
        if len(refs) != 4 or {r["dataset"] for r in refs} != {"CIFAR10", "CIFAR100"}:
            raise RuntimeError("four accepted references unavailable")
        estimate = dict(method="geometry upper estimate: 6*N*d*C FLOPs/step at 20 GFLOP/s plus 0.04 s/step and 40 s I/O",
            wall_seconds=40+4800*.04 + sum(6*200*6*p["sample_count"]*128*a["binding"]["C"]/20e9
                for p, a in zip(measurements["references"], acceptance["references"])),
            write_bytes=8*1024**2, gpu_allocated_bytes=512*1024**2,
            windows_working_set_bytes=3*1024**3, cpu_proxy_bytes=1024**3,
            fits=24, backwards=4800, optimizer_steps=4800, head_forwards=4860, scans=6000)
        prereg = dict(run_id=RUN_ID, registered_at=datetime.now(timezone(timedelta(hours=8))).isoformat(),
            baseline_commit=BASE, input_commit=git("rev-parse", "HEAD"), accepted_evidence_commit=EVIDENCE_COMMIT,
            references=refs, source_fingerprints={p:digest_file(ROOT/p, budget) for p in SOURCES},
            task_sha256=digest_file(ROOT/"docs/workflow/TO_EXECUTOR.md", budget),
            adjudication_sha256=digest_file(ROOT/"docs/DIRECTION_A_G1_2_ADJUDICATION_v2.md", budget),
            P_adjudication=dict(path="docs/DIRECTION_A_P_ADJUDICATION_v1.md", input_commit=git("rev-parse", "HEAD"),
                               sha256=digest_file(ROOT/"docs/DIRECTION_A_P_ADJUDICATION_v1.md", budget)),
            input_archive_sha256=digest_file(G12/"artifact_hashes.json", budget),
            split=dict(seed=SPLIT_SEED, algorithm="dataset-local default_rng; ascending class IDs; sorted global indices before shuffle; first max(1,floor(.2*N_c)) calibration",
                       fit_order="sorted global indices", calibration_order="sorted global indices", minimum_fit_per_class=2,
                       minimum_calibration_per_class=1, same_dataset_split_shared=True),
            permutations=dict(seeds=PERMUTATION_SEEDS, scope="global fit labels in sorted fit-index order", frequency_preserving=True,
                              calibration_labels="unchanged true labels", shared_across_same_dataset_references=True),
            probe=dict(classes="complete original C", bias=True, dtype="float32", feature_transform="none",
                       initialization="zero", loss="full fit mean of per-class mean CE", optimizer={"name":"Adam", **ADAM},
                       steps=STEPS, objective_checkpoints=[0,50,100,200], heads_per_reference=6,
                       early_stop=False, search=False, reinitialization=False),
            metrics=dict(per_class=["CE", "recall_percent", "sample_denominator"], groups=["all","head","middle","tail"],
                         preserve_zero=True, differences="percentage points vs original/uniform/each permutation"),
            chance=dict(CE="log(C)", expected_recall_percent="100/C", analytic=True, argmax_ties=False),
            threshold_rule=dict(status="NOT_frozen", tau="ceil_0.1(max(per-dataset permuted tail maximum,100/C)+largest tail one-correct macro increment)",
                                minimum_improvement="ceil_0.1(max(5 pp,2*largest tail one-correct macro increment))",
                                real_scores_used=False, five_nulls="descriptive only; no reliable 95% tail quantile claim"),
            optimization_diagnostic="report relative objective decrease 100->200; not a separability decision",
            input_policy="accepted cached train features/labels only; train fields in sealed split metadata only; checkpoint tensors only; no raw datasets, validation/test samples, model or encoder execution",
            limits=LIMITS, historical_limits_and_consumption=RECOVERY_CONTEXT["history"],
            cumulative_limits=dict(wall_seconds=600, accountable_write_bytes=128*1024**2,
                                   scans=10000, fits=24, backwards=4800, optimizer_steps=4800,
                                   head_forwards=6000, preparation_launches=2, failed_restarts=1,
                                   implementation_revisions=4),
            syntax_check_sha256=digest_file(OUTPUT/"syntax_check.json", budget),
            prefit_estimate=estimate)
        write(OUTPUT/"preregistration.json", prereg, budget)
        for limit, actual in (("wall_seconds", estimate["wall_seconds"]), ("evidence_bytes", estimate["write_bytes"]),
                              ("gpu_allocated_bytes", estimate["gpu_allocated_bytes"]),
                              ("windows_peak_working_set_bytes", estimate["windows_working_set_bytes"]),
                              ("cpu_tensor_proxy_bytes", estimate["cpu_proxy_bytes"])):
            if actual >= LIMITS[limit]:
                raise RuntimeError("estimated over-limit: "+limit)
        budget.enter("selfchecks")
        spec = importlib.util.spec_from_file_location("probe_checks", ROOT/"tests/test_direction_a_probe_preparation.py")
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        checks = module.run_checks(budget)
        write(OUTPUT/"selfchecks.json", dict(run_id=RUN_ID, checks=checks, status="PASS"), budget)
        results["reused_costs"] = dict(G1_2_ledger_path=repo_path(G12/"run_record.json"),
            G1_2_elapsed_seconds=old["elapsed_seconds"], G1_2_resources=old["resources"], G1_2_counts=old["counts"],
            encoder_costs_by_reference={p["reference_id"]:sum(c["cost_seconds"]["encode"] for c in p["clients"]) for p in measurements["references"]},
            old_cost_not_charged_as_new=True, new_encoding_samples=0,
            earlier_missing_timing="C100 r80 old first-segment per-client timing remains null; never reconstructed")
        budget.planned_references = [r["reference_id"] for r in refs]
        # No calibration fit or extra optimizer step is used for cost estimation.
        available = min(599-(time.monotonic()-STARTED),
                        600-RECOVERY_CONTEXT["history"]["elapsed_seconds"]-(time.monotonic()-STARTED)) - 30
        prereg["prefit_estimate"].update(available_seconds_after_old_startup_selfchecks_and_30s_archive_reserve=available,
                                       archive_reserve_seconds=30, source_and_evidence_bytes_already_charged=budget.counts["evidence_bytes"])
        write(OUTPUT/"preregistration.json", prereg, budget)
        if estimate["wall_seconds"] >= available or budget.counts["evidence_bytes"]+estimate["write_bytes"] >= LIMITS["evidence_bytes"]:
            raise RuntimeError("insufficient remaining fixed budget before fitting")
        permutation_records, per_fit_seconds = {}, []
        for reference in refs:
            ref_id, ds = reference["reference_id"], reference["dataset"]
            budget.enter(ref_id)
            accepted = next(a for a in acceptance["references"] if a["reference"]["reference_id"] == ref_id)
            point = next(p for p in measurements["references"] if p["reference_id"] == ref_id)
            packet, before = frozen_checkpoint(reference, accepted, budget)
            z, y, indices, C, groups, original, input_check = load_train(reference, point, accepted, index, budget)
            if (not torch.equal(original["weight"], packet["state_dict"]["linear.weight"]) or
                not torch.equal(original["bias"], packet["state_dict"]["linear.bias"]) or
                original["weight"].shape != (C,128) or original["bias"].shape != (C,)):
                raise RuntimeError("cached original head disagrees with frozen checkpoint")
            split = split_train(indices, y.numpy(), C, budget)
            if ds in splits and split != {k:v for k,v in splits[ds].items()
                                         if k not in ("train_labels_by_global_index", "train_global_indices")}:
                raise RuntimeError("same-dataset references disagree on split")
            if ds in splits and splits[ds]["train_labels_by_global_index"] != y.tolist():
                raise RuntimeError("same-dataset references disagree on true labels")
            splits[ds] = {**split, "train_global_indices": indices.tolist(),
                          "train_labels_by_global_index": y.tolist()}
            fit_pos = np.searchsorted(indices, split["fit_global_indices"])
            cal_pos = np.searchsorted(indices, split["calibration_global_indices"])
            fit_labels, cal_labels = y[fit_pos].numpy(), y[cal_pos].numpy()
            permutations = [permute_labels(fit_labels, C, seed, budget) for seed in PERMUTATION_SEEDS]
            permutation_rows = [dict(seed=seed, fit_labels=values.tolist(),
                                     fit_labels_sha256=sha(values.tobytes()), frequencies=np.bincount(values,minlength=C).tolist(),
                                     changed_positions=int((values!=fit_labels).sum()))
                                for seed, values in zip(PERMUTATION_SEEDS, permutations)]
            row = dict(fit_true_labels=fit_labels.tolist(), calibration_true_labels=cal_labels.tolist(),
                       calibration_true_labels_sha256=sha(cal_labels.tobytes()), permutations=permutation_rows)
            if ds in permutation_records and permutation_records[ds] != row:
                raise RuntimeError("same-dataset label permutations differ across snapshots")
            permutation_records[ds] = row
            write(OUTPUT/"split.json", dict(run_id=RUN_ID, datasets=splits,
                                          label_permutations=permutation_records), budget)
            fit_z, cal_z = z[fit_pos].cuda(), z[cal_pos].cuda()
            true_cal = torch.as_tensor(cal_labels, device="cuda")
            del z, y
            budget.consume("forwards")
            with torch.no_grad():
                original_metrics = summarize(F.linear(cal_z, original["weight"].cuda(), original["bias"].cuda()), true_cal, groups, budget)
            uniform = uniform_control(C, [r["calibration"] for r in split["denominators"]], groups)
            result = dict(reference_id=ref_id, dataset=ds, class_groups=groups, original_head=original_metrics,
                          uniform_control=uniform, heads=[], state_before=before)
            results["references"].append(result)
            for kind, seed, labels in [("real",None,fit_labels)] + [("permuted",s,l) for s,l in zip(PERMUTATION_SEEDS,permutations)]:
                t = time.monotonic()
                fitted, objectives, metrics = fit_head(fit_z, torch.as_tensor(labels,device="cuda"), cal_z, true_cal, C, groups, budget)
                torch.cuda.synchronize()
                elapsed = time.monotonic()-t
                per_fit_seconds.append(elapsed)
                name = "real" if kind == "real" else f"permuted_s{seed}"
                metadata = dict(run_id=RUN_ID, reference_id=ref_id, label_kind=kind, seed=seed,
                                fit_labels_sha256=sha(labels.tobytes()), steps=STEPS,
                                input_split_sha256=sha(encode(split)), objective_checkpoints=objectives,
                                optimizer={"name":"Adam", **ADAM}, C=C, d=128, bias_included=True, zero_initialization=True)
                locator = save_head(OUTPUT/f"heads/{ref_id}/{name}.pt", {**fitted, "metadata":metadata}, budget)
                result["heads"].append(dict(label_kind=kind, seed=seed, name=name, head=locator,
                    objectives=objectives, metrics=metrics, fit_and_evaluate_seconds=elapsed,
                    optimization=dict(decline_0_to_200=objectives["0"]-objectives["200"],
                        decline_100_to_200=objectives["100"]-objectives["200"],
                        relative_decline_100_to_200=(objectives["100"]-objectives["200"])/max(abs(objectives["100"]),1e-12),
                        convergence_certified=False, low_score_not_information_absence=True)))
                budget.progress = dict(reference=ref_id, completed_heads=budget.counts["fits"])
                budget.save()
            result["differences_pp"] = differences(result["heads"][0]["metrics"],
                {"original":original_metrics, "uniform":uniform,
                 **{h["name"]:h["metrics"] for h in result["heads"] if h["label_kind"]=="permuted"}})
            budget.scan()
            result["state_after"] = tensor_state_sha(packet["state_dict"])
            repeated, repeated_hash = frozen_checkpoint(reference, accepted, budget)
            if result["state_after"] != before or repeated_hash != before:
                raise RuntimeError("frozen backbone/original head state changed")
            input_check.update(state_before=before, state_after=result["state_after"], state_repeated_read=repeated_hash,
                               cached_head_matches_checkpoint=True, split_identical_across_dataset_references=True,
                               permutation_identical_across_dataset_references=True)
            results["input_checks"].append(input_check)
            budget.delivered_references.append(ref_id)
            write(OUTPUT/"results.json", results, budget)
            del packet, repeated, fit_z, cal_z, fitted
            gc.collect()
        if budget.counts["fits"] != 24 or budget.counts["backwards"] != 4800 or budget.counts["optimizer_steps"] != 4800:
            raise RuntimeError("fixed operation totals not met")
        budget.enter("threshold_basis_formal_plan_and_archive")
        plan = threshold_and_plan(results, splits, budget)
        results["new_costs"] = dict(total_fit_and_evaluate_seconds=sum(per_fit_seconds),
                                   operation_counts=dict(budget.counts), detailed_final_ledger="run_record.json")
        results["formal_P_executed"] = False
        criteria = {str(i):"PASS" for i in range(1,8)}
        RECOVERY_CONTEXT["criteria"] = criteria
        results["criteria"] = criteria
        write(OUTPUT/"results.json", results, budget)
        write(REVIEW, review_text(criteria,results,budget,None), budget, raw=True)
        budget.status = "completed_preparation_engineering_PASS"
        return budget, results, criteria
    except Exception as exc:
        blocked = f"{type(exc).__name__}: {exc}；本轮不重跑，不调整步骤/对照/参考。"
        budget.status = "blocked_partial_preparation"
        budget.progress["blocked"] = blocked
        if budget.hit is None:
            # Partial results survive a failed one-shot; never claim finished criteria.
            write(OUTPUT/"results.json", {**results,"criteria":criteria,"blocked":blocked}, budget)
            write(REVIEW, review_text(criteria,results,budget,blocked), budget, raw=True)
            budget.save()
        else:
            budget.save(reserved=True)
        print(json.dumps(dict(status=budget.status,fail_count=sum(v=="FAIL" for v in criteria.values()),blocked=blocked),ensure_ascii=False))
        raise
    finally:
        watchdog_done.set()


if __name__ == "__main__":
    main()
