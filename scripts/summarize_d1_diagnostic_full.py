"""Seven-section diagnostic report plus time-binned attack appendices."""
from collections import Counter
import json
import math
from pathlib import Path
import statistics

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/d1_3b/diagnostic_full_20260930"
METHODS = ("fedavg", "brdrag", "class_bal_brdrag", "d1")
NAMES = dict(zip(METHODS, ("FedAvg", "BR-DRAG", "类别均衡 BR-DRAG", "D1")))
BRANCHES = ("benign_empty", "attacker_empty", "harmful_too_small",
            "all_candidates_rejected", "zero_candidate_returned", "success")


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def fmt(value, digits=6):
    return "—" if value is None else f"{value:.{digits}f}"


def pct(value):
    return "—" if value is None else f"{100*value:.2f}%"


def distribution(values):
    if not values:
        return {k: None for k in ("min", "q25", "median", "q75", "max", "exceed_002") } | {"n": 0}
    quantiles = np.quantile(values, (0, .25, .5, .75, 1)).tolist()
    return dict(zip(("min", "q25", "median", "q75", "max"), quantiles)) | {
        "n": len(values), "exceed_002": sum(x > .02 for x in values)/len(values)}


def main():
    execution = read(OUT / "execution.json")  # Require all four pipelines to have ended.
    manifest = read(OUT / "manifest.json")
    pipelines = {m: read(OUT / f"process_{m}.json") for m in METHODS}
    records = [r for p in pipelines.values() for r in p["units"]]
    results, diagnostics, failures = {}, {}, []
    for record in records:
        key = record["seed"], record["method"]
        directory = OUT / f"seed_{key[0]}_{key[1]}"
        if record["returncode"] or not (directory / "result.json").exists():
            failures.append(record)
            continue
        result = read(directory / "result.json")
        rows = [json.loads(line) for line in (directory / "diagnostic_log.jsonl").read_text(encoding="utf-8").splitlines()]
        assert result["rounds"] == len(result["round_stats"]) == len(rows) == 200
        assert [r["round"] for r in rows] == list(range(1, 201))
        assert result["task_hashes"] == manifest["tasks"][str(key[0])]
        assert [r["received_client_ids"] for r in rows] == result["participants"]
        for row, stats in zip(rows, result["round_stats"]):
            assert len(row["malicious_client_ids"]) == stats["malicious"]
            if row["attack_called"]:
                attack = row["attack"]
                assert attack["exit_branch"] in BRANCHES and len(attack["candidates"]) == 5
                assert attack["benign_count"] == 20 - stats["malicious"]
                assert attack["is_zero_return"] == stats["adaptive_zero_update"]
                for candidate in attack["candidates"]:
                    if not candidate["evaluated"]:
                        assert candidate["not_evaluated_reason"] in ("early_success", "upstream_empty", "harmful_too_small")
                        assert all(candidate[k] is None for k in ("scale", "norm", "is_zero_vector", "root_loss", "root_loss_delta", "passed_root_check"))
            if key[1] == "d1":
                d = row["d1"]
                assert d["root_audit_scope"]["sample_count"] == 1000
                assert d["root_audit_scope"]["model_point"] == "current_round_pre_aggregation_global_model"
                if d["root_audit_per_class_loss"] is not None:
                    assert len(d["root_audit_per_class_loss"]) == stats["aggregator_stats"]["covered_classes"]
                if d["root_audit_macro_loss"] is None:
                    assert d["skip_reason"] or row["nonfinite_fields"]
        if key[1] == "d1":
            assert len({json.dumps(r["d1"]["root_audit_scope"], sort_keys=True) for r in rows}) == 1
        results[key], diagnostics[key] = result, rows
    participant_matches = {}
    for seed in range(1, 6):
        available = [results[seed, m]["participants"] for m in METHODS if (seed, m) in results]
        participant_matches[seed] = all(p == available[0] for p in available) if available else None
    lines = ["# Smoke B 带诊断日志完整复现", "",
             f"完成 {len(results)}/20 个单元，失败 {len(failures)} 个。代码提交 `{manifest['git_head']}`；解释器 `E:\\anaconda3\\python.exe`。", "",
             "CIFAR-10-LT，IR=50；100 客户端，每轮 20 参与；Dirichlet α=0.1；根集 2000 条，训练/审计各 1000，缺第 8、9 类；30% adaptive_root；每单元 200 轮，本地 1 epoch；seed 1–5。", "",
             "五个新任务先串行生成，根集索引、训练池和客户端划分均核验与原任务一致；同一 seed 的四方法共享同一任务文件。四个方法进程同时启动，各自串行运行五个独立 subprocess 单元。", "",
             f"同 seed 四方法参与客户端序列一致性：{participant_matches}。未改门槛、容差、候选网格或攻击配置；未运行 3B 完整矩阵；未 push。", ""]

    def table(headers, rows):
        lines.extend(["| " + " | ".join(map(str, headers)) + " |",
                      "| " + " | ".join("---" for _ in headers) + " |"])
        lines.extend("| " + " | ".join(map(str, row)) + " |" for row in rows)
        lines.append("")

    d1_seeds = [seed for seed in range(1, 6) if (seed, "d1") in results]
    branch_counts, audit_curves, residual_summaries, delta_summaries, segments = {}, {}, {}, {}, {}
    lines += ["## 一、攻击退出分支分布", ""]
    for seed in d1_seeds:
        branch_counts[seed] = Counter(r["attack"]["exit_branch"] if r["attack_called"] else "not_called" for r in diagnostics[seed, "d1"])
    table(["分支", *[f"seed {s}" for s in range(1,6)], "合计"],
          [[b, *[branch_counts.get(s, {}).get(b, 0) if s in branch_counts else "—" for s in range(1,6)],
            sum(c[b] for c in branch_counts.values())] for b in (*BRANCHES, "not_called")])
    table(["seed", "恶意客户端在场轮数", "攻击调用轮数", "攻击零返回轮数", "零返回/200"],
          [[s, sum(bool(r["malicious_client_ids"]) for r in diagnostics[s,"d1"]),
            sum(r["attack_called"] for r in diagnostics[s,"d1"]),
            sum(r["attack_called"] and r["attack"]["is_zero_return"] for r in diagnostics[s,"d1"]),
            pct(results[s,"d1"]["adaptive_zero_fraction"])] for s in d1_seeds])

    def deltas(rows):
        return [c["root_loss_delta"] for r in rows if r["attack_called"] for c in r["attack"]["candidates"]
                if c["evaluated"] and c["root_loss_delta"] is not None and math.isfinite(c["root_loss_delta"])]

    lines += ["## 二、被评估候选根损失增量分布", "",
              "仅使用原攻击实际评估的候选；未评估候选不补算。分位数采用线性插值；超限比例按 delta >0.02 计算，分母为被评估且有有限 delta 的候选数。", ""]
    for s in d1_seeds:
        delta_summaries[s] = distribution(deltas(diagnostics[s,"d1"]))
    table(["seed", "候选数", "最小", "Q25", "中位", "Q75", "最大", ">0.02比例"],
          [[s, d["n"], *[fmt(d[k]) for k in ("min","q25","median","q75","max")], pct(d["exceed_002"])]
           for s,d in delta_summaries.items()])

    lines += ["## 三、根审计损失趋势", "",
              "固定 1000 条审计样本；模型为当前轮聚合前全局模型；宏平均为非空审计类别损失的等权平均。未经过审计的返回路径保留 null 和 skip_reason，不插值。", ""]
    table(["seed", *range(10,201,10)],
          [[s, *[fmt(diagnostics[s,"d1"][r-1]["d1"]["root_audit_macro_loss"]) for r in range(10,201,10)]] for s in d1_seeds])
    trends = []
    for s in d1_seeds:
        curve = [r["d1"]["root_audit_macro_loss"] for r in diagnostics[s,"d1"]]
        valid = [(i+1,x) for i,x in enumerate(curve) if x is not None and math.isfinite(x)]
        slope = float(np.polyfit([i for i,x in valid],[x for i,x in valid],1)[0]) if len(valid)>1 else None
        up = sum(b>a for a,b in zip(curve,curve[1:]) if a is not None and b is not None)
        change = valid[-1][1]-valid[0][1] if valid else None
        trend = "下降" if slope is not None and slope<0 and change<0 else ("上升" if slope is not None and slope>0 and change>0 else "震荡/数据不足")
        skips = Counter(r["d1"]["skip_reason"] for r in diagnostics[s,"d1"] if r["d1"]["root_audit_macro_loss"] is None)
        audit_curves[s] = {"values":curve,"slope":slope,"change":change,"upward_steps":up,"skip_reasons":dict(skips),"trend":trend}
        trends.append([s,len(valid),fmt(valid[0][1] if valid else None),fmt(valid[-1][1] if valid else None),fmt(change),fmt(slope),up,trend,json.dumps(dict(skips),ensure_ascii=False)])
    table(["seed","有效点","首个损失","最后损失","差值","线性斜率/轮","相邻上升次数","总体趋势","空值原因"],trends)

    lines += ["## 四、残差预算使用", "",
              "残差放行指 D1 正常选择且 residual_norm >1e-12。以下范数与使用率分布仅统计这些轮次；预算上限为 selected_step ×0.25。百分位为线性插值。", ""]
    norm_rows, ratio_rows = [], []
    for s in d1_seeds:
        accepted = [r["d1"] for r in diagnostics[s,"d1"] if r["d1"]["return_path"]=="success" and r["d1"]["residual_norm"]>1e-12]
        norms=[d["residual_norm"] for d in accepted]
        ratios=[d["residual_budget_used_ratio"] for d in accepted if d["residual_budget_used_ratio"] is not None]
        dist=distribution(ratios)
        residual_summaries[s]={"rounds":len(accepted),"mean_norm":statistics.mean(norms) if norms else None,"max_norm":max(norms) if norms else None,"ratio":dist,
                               "ge50":sum(x>=.5 for x in ratios),"ge80":sum(x>=.8 for x in ratios),"ge99":sum(x>=.99 for x in ratios),"sources":results[s,"d1"]["update_sources"]}
        v=residual_summaries[s]
        norm_rows.append([s,len(accepted),fmt(v["mean_norm"]),fmt(v["max_norm"]),v["ge50"],v["ge80"],v["ge99"]])
        ratio_rows.append([s,*[pct(dist[k]) for k in ("min","q25","median","q75","max")]])
    table(["seed","残差放行轮数","范数均值","范数最大","使用≥50%轮数","≥80%轮数","≥99%轮数"],norm_rows)
    table(["seed","使用率最小","Q25","中位","Q75","最大"],ratio_rows)
    table(["seed","残差放行","根回退","零更新","客户端方向接受但残差零"],
          [[s,*[results[s,"d1"]["update_sources"][k] for k in ("residual_pass","root_fallback","zero_update","client_direction_zero_residual")]] for s in d1_seeds])

    lines += ["## 五、D1 与 BR-DRAG 逐类准确率", "", "准确率单位为 %，差值为 D1−BR-DRAG，单位为百分点。均值仅使用双方成功的同 seed 配对。", ""]
    paired=[s for s in d1_seeds if (s,"brdrag") in results]
    class_rows=[]
    for c in range(10):
        a=[100*results[s,"d1"]["per_class_accuracy"][c] for s in paired]
        b=[100*results[s,"brdrag"]["per_class_accuracy"][c] for s in paired]
        class_rows.append([c,len(paired),fmt(statistics.mean(b) if b else None,2),fmt(statistics.mean(a) if a else None,2),fmt(statistics.mean([x-y for x,y in zip(a,b)]) if a else None,2)])
    table(["类别","配对数","BR-DRAG均值","D1均值","差值均值"],class_rows)
    table(["seed","类别","BR-DRAG","D1","差值"],
          [[s,c,fmt(100*results[s,"brdrag"]["per_class_accuracy"][c],2),fmt(100*results[s,"d1"]["per_class_accuracy"][c],2),fmt(100*(results[s,"d1"]["per_class_accuracy"][c]-results[s,"brdrag"]["per_class_accuracy"][c]),2)] for s in paired for c in range(10)])

    lines += ["## 六、方法级主表", "", "准确率及零更新比例均为百分数。攻击零更新比例以全部 200 轮为分母；未调用攻击的轮次不计零返回。", ""]
    table(["seed","方法","总体","宏平均","第8类","第9类","尾类平均","攻击零更新率"],
          [[s,NAMES[m],pct(results[s,m]["overall_accuracy"]),pct(results[s,m]["macro_accuracy"]),pct(results[s,m]["per_class_accuracy"][8]),pct(results[s,m]["per_class_accuracy"][9]),pct(results[s,m]["tail_accuracy"]),pct(results[s,m]["adaptive_zero_fraction"])] for s in range(1,6) for m in METHODS if (s,m) in results])
    table(["seed",*[f"{NAMES[m]} {metric}" for m in METHODS for metric in ("总体","尾类")]],
          [[s,*[pct(results[s,m][k]) if (s,m) in results else "—" for m in METHODS for k in ("overall_accuracy","tail_accuracy")]] for s in range(1,6)])
    def mean_std(values):
        return f"{statistics.mean(values):.2f} ± {statistics.stdev(values):.2f}" if len(values)>1 else "—"
    table(["方法","n","总体均值±样本std","宏平均均值±样本std","尾类均值±样本std"],
          [[NAMES[m],sum((s,m) in results for s in range(1,6)),*[mean_std([100*results[s,m][k] for s in range(1,6) if (s,m) in results]) for k in ("overall_accuracy","macro_accuracy","tail_accuracy")]] for m in METHODS])
    comparisons=[]
    for k,name in (("tail_accuracy","尾类"),("overall_accuracy","总体")):
        for m in METHODS[:-1]:
            diffs={s:100*(results[s,"d1"][k]-results[s,m][k]) for s in d1_seeds if (s,m) in results}
            comparisons.append([name,NAMES[m],*[fmt(diffs.get(s),2) for s in range(1,6)],fmt(statistics.mean(diffs.values()) if diffs else None,2),f"{sum(v>0 for v in diffs.values())}/{sum(v==0 for v in diffs.values())}/{sum(v<0 for v in diffs.values())}"])
    table(["指标","对照",*[f"seed {s}" for s in range(1,6)],"差值均值","高/同/低"],comparisons)

    lines += ["## 七、执行报告", ""]
    table(["项目","墙钟秒"],[[NAMES[m]+"进程",fmt(pipelines[m]["wall_seconds"],2)] for m in METHODS]+[["四进程启动至全部结束",fmt(execution["total_wall_seconds"],2)],["此前串行任务生成",fmt(manifest["preparation_seconds"],2)]])
    lines += [f"启动 UTC：{execution['started_at']}；结束 UTC：{execution['ended_at']}。",""]
    table(["seed","方法","单元subprocess墙钟秒","runner.run秒","平均每轮秒","JSONL字节"],
          [[r["seed"],NAMES[r["method"]],fmt(r["subprocess_wall_seconds"],2),fmt(results[r["seed"],r["method"]]["elapsed_seconds"],2),fmt(results[r["seed"],r["method"]]["seconds_per_round"],3),results[r["seed"],r["method"]]["diagnostic_log_bytes"]] for r in records if (r["seed"],r["method"]) in results])
    total_bytes=sum((OUT/f"seed_{s}_{m}/diagnostic_log.jsonl").stat().st_size for s,m in results)
    lines += [f"成功单元诊断日志总大小：{total_bytes:,} 字节；未抽样、未删轮次。", ""]
    for m in METHODS:
        rs=[r for r in records if r["method"]==m and (r["seed"],m) in results]
        median=statistics.median(r["subprocess_wall_seconds"] for r in rs) if rs else None
        slow=[r for r in rs if r["subprocess_wall_seconds"]>1.5*median]
        lines += [f"- {NAMES[m]}：单元墙钟中位数 {fmt(median,2)} 秒；超过其 1.5 倍："+("、".join(f"seed {r['seed']} {r['subprocess_wall_seconds']:.2f} 秒" for r in slow) if slow else "无")+"。"]
    lines += ["", "加日志前后运行的并发数分别为 2 与 4；下面只报告观测耗时比，不能单独归因为日志开销，也不是全程单进程基准。", ""]
    old_dir=ROOT/"outputs/d1_3b/smokeB_20260930"
    timing_comparisons=[]
    for m in METHODS:
        old=[read(old_dir/f"seed_{s}_{m}/result.json")["seconds_per_round"] for s in range(1,6)]
        new=[results[s,m]["seconds_per_round"] for s in range(1,6) if (s,m) in results]
        timing_comparisons.append([NAMES[m],fmt(statistics.mean(old),3),fmt(statistics.mean(new) if new else None,3),fmt(statistics.mean(new)/statistics.mean(old) if new else None,3)])
    table(["方法","加日志前两并行平均每轮秒","本次四并行平均每轮秒","观测耗时比"],timing_comparisons)
    smoke=read(ROOT/"outputs/d1_3b/diag_log_smoke_20260930/result.json")
    if (1,"d1") in results:
        smoke_mean=statistics.mean(smoke["round_seconds"])
        current_mean=statistics.mean(results[1,"d1"]["round_seconds"][:5])
        lines += [f"同为带日志的 seed 1 前五轮：单进程 smoke 平均 {smoke_mean:.3f} 秒/轮，本次四并行 {current_mean:.3f} 秒/轮，比值 {current_mean/smoke_mean:.3f}；该参照仅覆盖前五轮。", ""]
    if failures:
        for r in failures:
            tail=Path(r["log"]).read_text(encoding="utf-8",errors="replace").splitlines()[-15:]
            lines += [f"失败：seed {r['seed']} / {NAMES[r['method']]}，退出码 {r['returncode']}；涉及该单元的配对缺失。", "```text",*tail,"```",""]
    else:
        lines += ["无失败单元，全部方法的五个配对 seed 完整。", ""]
    lines += ["每个单元原始日志路径：", ""]
    lines += [f"- `outputs/d1_3b/diagnostic_full_20260930/seed_{s}_{m}/diagnostic_log.jsonl`" for s in range(1,6) for m in METHODS]

    lines += ["", "## 附加报告 A：攻击零更新率随轮次", "",
              "单元格记为 Z/S/R/O/N：零返回轮数 / success非零轮数 / all_candidates_rejected轮数 / 其他退出分支轮数 / 未调用攻击轮数。Z 与 R、O 可能重叠；S+R+O+N=20。", ""]
    segment_headers=[f"{i*20+1}–{(i+1)*20}" for i in range(10)]
    segment_table=[]; other_rows=[]
    for s in d1_seeds:
        cells=[]; segments[s]=[]
        for i in range(10):
            rows=diagnostics[s,"d1"][i*20:(i+1)*20]
            counts=Counter(r["attack"]["exit_branch"] if r["attack_called"] else "not_called" for r in rows)
            z=sum(r["attack_called"] and r["attack"]["is_zero_return"] for r in rows)
            other={b:counts[b] for b in BRANCHES if b not in ("success","all_candidates_rejected")}
            v={"range":segment_headers[i],"zero":z,"success":counts["success"],"all_candidates_rejected":counts["all_candidates_rejected"],"other_branches":other,"not_called":counts["not_called"],"deltas":distribution(deltas(rows))}
            segments[s].append(v)
            cells.append(f"{z}/{v['success']}/{v['all_candidates_rejected']}/{sum(other.values())}/{v['not_called']}")
            if any(other.values()) or v["not_called"]:
                other_rows.append([s,segment_headers[i],json.dumps(other,ensure_ascii=False),v["not_called"]])
        segment_table.append([s,*cells])
    table(["seed",*segment_headers],segment_table)
    if other_rows:
        table(["seed","轮次段","其他分支明细","未调用"],other_rows)
    else:
        lines += ["所有段的其他分支均为 0：benign_empty、attacker_empty、harmful_too_small、zero_candidate_returned；未调用攻击轮数也均为 0。", ""]
    early_late=[]
    for s in d1_seeds:
        rows=diagnostics[s,"d1"]
        early=sum(r["attack_called"] and r["attack"]["is_zero_return"] for r in rows[:5])
        late=sum(r["attack_called"] and r["attack"]["is_zero_return"] for r in rows[5:])
        early_late.append([s,f"{early}/5",pct(early/5),f"{late}/195",pct(late/195),pct((early+late)/200)])
    table(["seed","前5轮零返回","比例","第6–200轮零返回","比例","全200轮比例"],early_late)
    if (1,"d1") in results:
        first5=[r["attack"]["exit_branch"] if r["attack_called"] else "not_called" for r in diagnostics[1,"d1"][:5]]
        lines += [f"本次 seed 1 前五轮退出分支：{first5}。5 轮 smoke 的 success 为4/5、零返回为1/5；本次全程与早期的差别见上表及十段分布。不同 seed 的差别按同一轮次段直接列出；日志能定位退出分支，但不能单独建立模型状态差异的因果解释。", ""]

    lines += ["## 附加报告 B：按20轮分段的候选 root_loss_delta", "",
              "每行只统计该段实际评估候选；不按五个槽位补齐。", ""]
    table(["seed","轮次段","候选数","最小","中位","最大",">0.02比例"],
          [[s,v["range"],v["deltas"]["n"],*[fmt(v["deltas"][k]) for k in ("min","median","max")],pct(v["deltas"]["exceed_002"])] for s in d1_seeds for v in segments[s]])
    (OUT/"report.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    summary={"completed":len(results),"failures":failures,"execution":execution,"pipelines":pipelines,
             "participant_matches":participant_matches,"branch_counts":{s:dict(c) for s,c in branch_counts.items()},
             "delta_summaries":delta_summaries,"audit_curves":audit_curves,"residual_summaries":residual_summaries,
             "segments":segments,"diagnostic_total_bytes":total_bytes}
    (OUT/"summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding="utf-8")
    print(f"REPORT_READY completed={len(results)} failures={len(failures)} bytes={total_bytes} path={OUT/'report.md'}")


if __name__ == "__main__":
    main()
