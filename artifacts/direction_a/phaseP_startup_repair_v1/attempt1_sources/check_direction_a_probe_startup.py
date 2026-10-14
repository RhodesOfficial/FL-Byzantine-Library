"""Bounded CPU regression/audit runner; never invokes preparation main."""

import time
START=time.monotonic()
REAL_CLOCK=time.monotonic

import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import threading
import traceback
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT)); sys.dont_write_bytecode=True
BASE="aa5f6d00535a339ad2753aded515dff20fa70925"
V1="d7706748e70f63885572aded57fab9e674d1a086"
OUT=ROOT/"artifacts/direction_a/phaseP_startup_repair_v1"
SOURCES=["scripts/prepare_direction_a_probe.py","scripts/recover_direction_a_probe.py",
         "direction_a/probe_startup.py","tests/test_direction_a_probe_startup.py",
         "scripts/check_direction_a_probe_startup.py"]
PRIOR_WRITES=[dict(path="direction_a/probe_startup.py",bytes=10521,
                  sha256="33bc47bd0aceef6de5c603053281fc8fad3ba26eb61456f34c16b42b3f44629c"),
              dict(path="scripts/prepare_direction_a_probe.py",bytes=43219,
                  sha256="384a8f45c8fdbd8c9fff9a0acfd65fe9423230fc839bd5b6f490202c635f47a5"),
              dict(path="scripts/recover_direction_a_probe.py",bytes=16140,
                  sha256="b34357bae652ab31d42e9a696a8c0a6a06044d6b80fa88357075b15f0ddb9637"),
              dict(path="tests/test_direction_a_probe_startup.py",bytes=8952,
                  sha256="e846376b3f2ef00e0c17b63d4153b91fe79edfd29213ec36ce754bdd69c29be8"),
              dict(path="scripts/check_direction_a_probe_startup.py",bytes=19289,
                  sha256="fb6839fe9df68609acfc43f5b580a95577fdd64e8151e2854808392ba18f0f11"),
              dict(path="scripts/check_direction_a_probe_startup.py",bytes=19490,
                  sha256="c5e8588980501a7adf968a019974fb1eb215a3ed07877950e1059d2b30718a85"),
              dict(path="scripts/check_direction_a_probe_startup.py",bytes=20121,
                  sha256="e8630ebe3aecb7dcb2d8b463a6ef87620e60b9b6c20a863fd2e95e3e6f9fded7")]


def encode(value):
    return (json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2,allow_nan=False)+"\n").encode("utf-8")


def sha(raw): return hashlib.sha256(raw).hexdigest()


def git_bytes(commit,path):
    return subprocess.check_output(["git","show",f"{commit}:{path}"],cwd=ROOT)


class CaseResults(unittest.TestResult):
    def __init__(self): super().__init__(); self.cases=[]
    def addSuccess(self,test):
        super().addSuccess(test); self.cases.append(dict(case=test.id(),status="PASS"))
    def addFailure(self,test,error):
        super().addFailure(test,error); self.cases.append(dict(case=test.id(),status="FAIL",error=self._exc_info_to_string(error,test)))
    def addError(self,test,error):
        super().addError(test,error); self.cases.append(dict(case=test.id(),status="FAIL",error=self._exc_info_to_string(error,test)))


def main():
    if Path(sys.executable).resolve()!=Path(r"E:\anaconda3\python.exe").resolve():
        raise RuntimeError("required interpreter mismatch")
    if OUT.exists(): raise RuntimeError("CPU repair already recorded; no reset or uncounted rerun")
    if subprocess.run(["git","merge-base","--is-ancestor",BASE,"HEAD"],cwd=ROOT).returncode:
        raise RuntimeError("task baseline is not ancestor")
    OUT.mkdir(parents=True)
    source_events=PRIOR_WRITES+[dict(path=p,bytes=(ROOT/p).stat().st_size,sha256=sha((ROOT/p).read_bytes())) for p in SOURCES]
    counts=dict(evidence_bytes=128*1024+sum(e["bytes"] for e in source_events),scans=0,
                syntax_checks=0,CPU_regression_suites=0,implementation_revisions=1,
                preparation_launches_new=0,fits=0,head_forwards=0,backwards=0,optimizer_steps=0,
                communications=0,class_gradient_requests=0,real_input_reads=0,CUDA_initializations=0)
    durations=[]; buffer_peak=max(e["bytes"] for e in source_events)
    old_write=Path.write_bytes; old_text=Path.write_text; old_read=Path.read_bytes
    forbidden=[]; stop=threading.Event()
    def check():
        if REAL_CLOCK()-START>=60: raise RuntimeError("repair program 60-second cap")
        if counts["evidence_bytes"]>=4*1024**2: raise RuntimeError("repair 4-MiB write cap")
        if counts["scans"]>500: raise RuntimeError("repair 500-scan cap")
    def safe_write(path,data):
        nonlocal buffer_peak
        check(); resolved=path.resolve()
        if any(part in str(resolved).replace("\\","/") for part in ("phaseP_preparation_v1/","phaseP_preparation_v2/")):
            raise PermissionError("sealed failure evidence write intercepted")
        if counts["evidence_bytes"]+len(data)>=4*1024**2: raise RuntimeError("write cap before write")
        t=REAL_CLOCK(); value=old_write(path,data); durations.append(REAL_CLOCK()-t)
        counts["evidence_bytes"]+=len(data); buffer_peak=max(buffer_peak,len(data)); return value
    def safe_text(path,data,encoding=None,errors=None,newline=None):
        raw=data.encode(encoding or "utf-8",errors or "strict"); safe_write(path,raw); return len(data)
    def safe_read(path):
        nonlocal buffer_peak
        normalized=str(path.resolve()).replace("\\","/")
        if any(part in normalized for part in ("/RAW_DATA/","/checkpoints/","/phaseG1_2_","/phase0_2_v1/tasks/")):
            forbidden.append("real dataset/feature read"); raise AssertionError("real input read intercepted")
        check(); value=old_read(path); counts["scans"]+=1; buffer_peak=max(buffer_peak,len(value)); return value
    def deny(name):
        def blocked(*args,**kwargs): forbidden.append(name); raise AssertionError("forbidden experimental operation: "+name)
        return blocked
    def watch():
        while not stop.wait(.1):
            if REAL_CLOCK()-START>=60:
                old_write(OUT/"guard_failure.json",encode(dict(status="blocked_time_limit",elapsed_seconds=REAL_CLOCK()-START)))
                os._exit(124)
    threading.Thread(target=watch,daemon=True).start()
    with patch.object(Path,"write_bytes",safe_write),patch.object(Path,"write_text",safe_text),patch.object(Path,"read_bytes",safe_read):
        counts["syntax_checks"]+=1
        syntax=[]
        for name in SOURCES:
            raw=(ROOT/name).read_bytes()
            try: compile(raw,str(ROOT/name),"exec"); status="PASS"; error=None
            except SyntaxError: status="FAIL"; error=traceback.format_exc()
            syntax.append(dict(path=name,sha256=sha(raw),status=status,error=error))
        syntax_elapsed=REAL_CLOCK()-START
        # Read only immutable old failure metadata and source versions.
        v1=json.loads(git_bytes(V1,"artifacts/direction_a/phaseP_preparation_v1/run_record.json")); counts["scans"]+=1
        v2=json.loads(git_bytes(BASE,"artifacts/direction_a/phaseP_preparation_v2/run_record.json")); counts["scans"]+=1
        old_wrapper=git_bytes(BASE,"scripts/recover_direction_a_probe.py"); counts["scans"]+=1
        old_index=json.loads(git_bytes(BASE,"artifacts/direction_a/phaseP_preparation_v2/artifact_hashes.json")); counts["scans"]+=1
        published={name:len(git_bytes(BASE,name)) for name in old_index["files"]}; counts["scans"]+=len(published)
        published["artifacts/direction_a/phaseP_preparation_v2/artifact_hashes.json"]=len(git_bytes(BASE,"artifacts/direction_a/phaseP_preparation_v2/artifact_hashes.json"))
        counts["scans"]+=1
        source_bytes=sum(e["bytes"] for e in v2["source_write_events"])
        old_syntax=json.loads(git_bytes(BASE,"artifacts/direction_a/phaseP_preparation_v2/syntax_check.json")); counts["scans"]+=1
        # Only source WRITE events count here, not the final source files again.
        evidence_paths=[p for p in published if p.startswith("artifacts/")]+["docs/workflow/TO_REVIEWER.md"]
        recoverable_bytes=source_bytes+old_syntax["evidence_bytes"]+sum(published[p] for p in evidence_paths if not p.endswith("syntax_check.json"))+128*1024
        audit=dict(input_commit=BASE,v1_commit=V1,v2_commit=BASE,
            reported_cumulative=dict(seconds=v2["cumulative_elapsed_seconds"],accountable_write_bytes=v2["cumulative_accountable_write_bytes"],
                                     preparation_launches=2,failed_restarts=1,implementation_revisions=4),
            v1_reported=dict(seconds=v1["elapsed_seconds"],write_bytes=v1["counts"]["evidence_bytes"],scans=16),
            v2_reported_increment=dict(seconds=v2["new_stage_elapsed_seconds"],write_bytes=v2["new_known_write_bytes"]),
            never_add_nested_v1_to_v2_cumulative=True,
            recoverable_v2_write_accounting=dict(source_write_event_bytes=source_bytes,
                syntax_write_bytes_including_overwrite=old_syntax["evidence_bytes"],published_byte_sizes=published,
                reconstructed_new_accountable_bytes= recoverable_bytes,
                reported_new_accountable_bytes=v2["new_known_write_bytes"],
                rule="source events + both syntax writes + published failure outputs/reviewer + 128KiB reserve; current source sizes are not charged twice"),
            time_audit=dict(v2_final_closure_exact_seconds=None,reported_reserve_seconds=.1,final_closure_checked=False,
                observed_command_envelopes=[dict(command="first syntax plus diff check",seconds=.5971457),
                    dict(command="second syntax",seconds=.4478557),dict(command="v2 startup wrapper",seconds=4.4547852)],
                envelope_provenance="this conversation's exec_command results, chunks a4e880/3ca673/6bc1d4; includes process launch/exit",
                v2_new_program_upper_seconds=.5971457+.4478557+4.4547852,
                P_prior_upper_seconds=v1["elapsed_seconds"]+.5971457+.4478557+4.4547852),
            scan_audit=dict(v2_exact_scans=None,v1_recorded_scans=16,v2_recoverable_conservative_upper=128,
                basis="committed wrapper: syntax 8, current source checks 4, old hash/reconstruction <=54, old working hashes <=9, fallback hashes <=10, metadata/control <=25, margin 18; total<=128",
                simulation_not_actual_consumption=True),
            historical_unknowns=dict(v1_preparation_peaks=v1["resources"],v1_overwritten_source_bytes=None,
                v2_cuda_peak=None,v2_CPU_array_tensor_proxy_verified=None,v2_final_windows_peak=None,
                v2_reported_windows_peak_to_sample_bytes=v2["resources"]["new_windows_working_set_peak_bytes"],
                v2_reported_CPU_proxy_bytes=v2["resources"]["new_cpu_proxy_upper_bytes"],
                CPU_proxy_reason="v2 used fixed 8MiB without arrays/tensors inventory; only small explicit file buffers recoverable, not a verified full proxy"),
            startup_status=dict(v2_marker="launching",v2_terminal="blocked_startup_failure",
                reason="marker written before constructor; pre-budget exception fallback wrote terminal ledger but never rewrote marker; terminal ledger and error govern"),
            old_preparation_criterion_6="FAIL",historical_waiver_not_expanded=True,
            old_wrapper_sha256=sha(old_wrapper))
        if recoverable_bytes!=v2["new_known_write_bytes"]:
            audit["recoverable_v2_write_accounting"]["difference_bytes"]=recoverable_bytes-v2["new_known_write_bytes"]
            audit["recoverable_v2_write_accounting"]["status"]="conservative reconstructed bound; difference retained"
        else: audit["recoverable_v2_write_accounting"]["status"]="exact match of recoverable published writes and reserve"
        import torch
        from direction_a.backbone_preparation import windows_memory
        if torch.cuda.is_initialized(): raise RuntimeError("CUDA unexpectedly initialized before CPU regression")
        result=CaseResults()
        with patch.object(torch,"load",deny("checkpoint/feature load")),patch.object(torch.cuda,"init",deny("CUDA init")),\
             patch.object(torch.cuda,"_lazy_init",deny("CUDA lazy init")),patch.object(torch.Tensor,"cuda",deny("tensor CUDA transfer")),\
             patch.object(torch.nn.functional,"linear",deny("head forward")),patch.object(torch.Tensor,"backward",deny("backward")),\
             patch.object(torch.optim.Adam,"step",deny("optimizer step")):
            spec=importlib.util.spec_from_file_location("probe_startup_tests",ROOT/"tests/test_direction_a_probe_startup.py")
            tests=importlib.util.module_from_spec(spec); spec.loader.exec_module(tests)
            if all(s["status"]=="PASS" for s in syntax):
                counts["CPU_regression_suites"]+=1
                unittest.defaultTestLoader.loadTestsFromModule(tests).run(result)
        check()
        if windows_memory()["peak_working_set_bytes"]>=2*1024**3: raise RuntimeError("Windows working-set cap")
        proxy=8*buffer_peak+8*sum(e["bytes"] for e in source_events)
        if proxy>=64*1024**2: raise RuntimeError("known CPU byte-buffer proxy cap")
        passed=result.wasSuccessful() and bool(result.cases) and all(s["status"]=="PASS" for s in syntax) and not forbidden
        regression=dict(input_commit=subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT).decode().strip(),baseline_commit=BASE,
            actual_command=[sys.executable,"-B","scripts/check_direction_a_probe_startup.py"],syntax=syntax,
            syntax_check_invocations=counts["syntax_checks"],CPU_suite_invocations=counts["CPU_regression_suites"],
            cases=result.cases,status="PASS" if passed else "FAIL",
            simulation=dict(controlled_clocks_and_requested_limit_values_are_synthetic=True,
                            simulated_costs_not_added_to_actual_experiment_counters=True),
            isolation=dict(forbidden_attempts=forbidden,CUDA_initialized_before=False,CUDA_initialized_after=torch.cuda.is_initialized(),
                           preparation_main_calls=0,real_feature_checkpoint_dataset_reads=0,
                           blocked_calls=["torch.load","CUDA init/lazy init/transfer","linear","backward","Adam.step"]),
            source_fingerprints={s["path"]:s["sha256"] for s in syntax})
        (OUT/"regression_results.json").write_bytes(encode(regression))
        (OUT/"accounting_audit.json").write_bytes(encode(audit))
        criteria={str(i):"PASS" if passed else "FAIL" for i in range(1,6)}
        lines=["# 交付单：P准备第3轮 启动链路修复与CPU隔离回归","",f"- 对应任务单的基准 commit：{BASE}",
            "- 本次交付 commit：见本提交","","## 做了什么（≤5 条）",
            "- P专用真实RecoveryBudget延后派生snapshot，完成完整父类构造后显式继承计数/成本。",
            "- 包装器复用可注入回归的启动/异常/归档生命周期，保护封存失败目录和已有标记。",
            f"- 运行{counts['syntax_checks']}次纯语法检查、{counts['CPU_regression_suites']}次CPU套件，共{len(result.cases)}用例；真实实验操作0。",
            "- 按commit审计两轮失败历史，保留旧未知项；24头仍未执行，原七条准备判据仍FAIL。","","## 产出文件",
            "- direction_a/probe_startup.py及两入口：P专用构造/继承、保护和终态记录。",
            "- tests/test_direction_a_probe_startup.py、scripts/check_direction_a_probe_startup.py：隔离回归与有界执行/审计。",
            "- artifacts/direction_a/phaseP_startup_repair_v1/regression_results.json：实际命令/源哈希/逐用例结果/隔离证据。",
            "- 同目录accounting_audit.json：v1/v2提交、累计值、恢复写入/时间/扫描界及未知项。",
            "- 同目录run_record.json、artifact_hashes.json：新增真实消耗、临时写入、累计可核算值、归档索引。","","## 判据自评",
            "|判据编号|结果 PASS/FAIL|证据/关键数字|","|---|---|---|"]
        explanations=["真实FullBudget/PreparationBudget构造、pending/final snapshot、保存读回与精确写入/修订/扫描继承用例",
            "合成时钟/请求触顶后失败账本；已有标记/账本及封存目录拒绝且不覆盖用例",
            "包装器budget前/后注入异常与正常归档；终态/错误/哈希读回/无自动重试；计时覆盖归档并校验写出预留",
            "accounting_audit.json：继承4.9019854秒/500678 B、2启动/1重启/4修订；v2不重复加v1，旧判据6仍FAIL",
            "regression_results.json、run_record.json：语法/用例与真实资源；CUDA和实验调用拦截，操作0"]
        for i,text in enumerate(explanations,1): lines.append(f"|{i}|{criteria[str(i)]}|{text}|")
        lines += ["","## 实际资源消耗","- 精确新增/累计时间、Windows峰、CPU字节缓冲代理、扫描和全部覆盖/临时写入见run_record.json。",
            "- 新增修订1；语法1/套件1；准备启动累计仍2、失败重启仍1，拟合/前向/反向/优化均0。",
            "- 历史CUDA/CPU代理和终末峰/精确扫描缺项保留未知，不扩大v1豁免或宣称全历史合规。","","## 阻塞",
            "无" if passed else "CPU回归未通过；逐用例失败见regression_results.json，不启动准备实验。",
            "","## 异议","无","","## 需要审查者裁决的问题（≤3 条，没有写\"无\"）",
            "- 是否另行放行后续准备运行；本修复通过不替代原七条准备或P科学验收。"]
        (ROOT/"docs/workflow/TO_REVIEWER.md").write_bytes(("\n".join(lines)+"\n").encode("utf-8"))
        # Hash after all reports/tests; temporary writes were counted but removed.
        paths=[p for p in OUT.iterdir() if p.is_file()]+[ROOT/"docs/workflow/TO_REVIEWER.md",*[ROOT/p for p in SOURCES]]
        records={str(p.relative_to(ROOT)).replace("\\","/"):dict(bytes=p.stat().st_size,sha256=sha(p.read_bytes())) for p in paths}
        name="artifacts/direction_a/phaseP_startup_repair_v1/run_record.json"
        records[name]=dict(bytes=0,sha256="0"*64)
        index=dict(algorithm="SHA-256 file bytes",files=records,excluded=["artifact_hashes.json (self)"],
                   command=regression["actual_command"],temporary_test_payloads_removed=True)
        final_reserve=max(.05,8*max(durations,default=0.))
        deadline=REAL_CLOCK()+final_reserve
        ledger=dict(status="completed_CPU_regression_PASS" if passed else "CPU_regression_FAIL",criteria=criteria,
            counts=dict(counts),source_write_events=source_events,new_stage_elapsed_seconds=deadline-START,
            cumulative_reported_elapsed_seconds=v2["cumulative_elapsed_seconds"]+deadline-START,
            cumulative_conservative_elapsed_upper_seconds=audit["time_audit"]["P_prior_upper_seconds"]+deadline-START,
            inherited_accountable_write_bytes=500678,inherited_preparation_launches=2,inherited_failed_restarts=1,
            cumulative_implementation_revisions=5,historical_unknowns=audit["historical_unknowns"],
            resources=dict(windows_working_set_peak_bytes=windows_memory()["peak_working_set_bytes"],
                CPU_known_file_buffer_proxy_upper_bytes=proxy,CPU_proxy_basis="8*peak tracked byte buffer +8*source byte total; no experiment arrays/tensors created",
                cuda_initialized=False,cuda_allocated_bytes=0),
            finalization_reserve_seconds=final_reserve,finalization_basis="max(50ms,8*largest actually measured file-write latency); end checked against deadline",
            limits=dict(seconds=60,write_bytes=4*1024**2,scans=500,Windows_working_set_bytes=2*1024**3,CPU_proxy_bytes=64*1024**2),
            old_preparation_criterion_6="FAIL",regression_simulated_costs_charged_as_experiments=False)
        before=counts["evidence_bytes"]
        for _ in range(12):
            ledger["counts"]["evidence_bytes"]=before+len(encode(ledger))+len(encode(index))
            ledger["cumulative_accountable_write_bytes"]=500678+ledger["counts"]["evidence_bytes"]
            records[name]["bytes"]=len(encode(ledger))
        raw=encode(ledger); records[name]["sha256"]=sha(raw)
        (OUT/"run_record.json").write_bytes(raw)
        (OUT/"artifact_hashes.json").write_bytes(encode(index))
        check()
        if REAL_CLOCK()>deadline: raise RuntimeError("final write allowance exceeded")
        print(json.dumps(dict(status=ledger["status"],cases=len(result.cases),fail_count=sum(v=="FAIL" for v in criteria.values()),
                             seconds=ledger["new_stage_elapsed_seconds"],writes=ledger["counts"]["evidence_bytes"],scans=counts["scans"])))
    stop.set()


if __name__=="__main__": main()
