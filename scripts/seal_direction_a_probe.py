"""One post-run artifact verification/closure; never reads experiment inputs."""
import time
START=time.monotonic()
import ctypes
import hashlib
import json
import subprocess
import sys
from ctypes import wintypes
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"artifacts/direction_a/phaseP_preparation_v3"

def encode(value): return (json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2,allow_nan=False)+"\n").encode()
def sha(raw): return hashlib.sha256(raw).hexdigest()

def working_set_peak():
    class Counters(ctypes.Structure):
        _fields_=[("cb",wintypes.DWORD),("PageFaultCount",wintypes.DWORD)]+[(n,ctypes.c_size_t) for n in ("PeakWorkingSetSize","WorkingSetSize","QuotaPeakPagedPoolUsage","QuotaPagedPoolUsage","QuotaPeakNonPagedPoolUsage","QuotaNonPagedPoolUsage","PagefileUsage","PeakPagefileUsage")]
    kernel=ctypes.WinDLL("kernel32",use_last_error=True); api=ctypes.WinDLL("psapi",use_last_error=True)
    kernel.GetCurrentProcess.restype=wintypes.HANDLE
    api.GetProcessMemoryInfo.argtypes=(wintypes.HANDLE,ctypes.POINTER(Counters),wintypes.DWORD)
    value=Counters(); value.cb=ctypes.sizeof(value)
    if not api.GetProcessMemoryInfo(kernel.GetCurrentProcess(),ctypes.byref(value),value.cb): raise OSError(ctypes.get_last_error())
    return int(value.PeakWorkingSetSize)

def main():
    if Path(sys.executable).resolve()!=Path(r"E:\anaconda3\python.exe").resolve(): raise RuntimeError("interpreter mismatch")
    if (OUT/"archive_verification.json").exists(): raise FileExistsError("delivery already sealed")
    old=json.loads((OUT/"run_record.json").read_bytes())
    index=json.loads((OUT/"artifact_hashes.json").read_bytes())
    if old["status"]!="completed": raise RuntimeError("failed preparation cannot be certified")
    scans=2; rows=[]
    for name,row in index["files"].items():
        raw=(ROOT/name).read_bytes(); scans+=1
        ok=len(raw)==row["bytes"] and sha(raw)==row["sha256"]
        rows.append(dict(path=name,bytes=len(raw),status="PASS" if ok else "FAIL"))
    if any(r["status"]!="PASS" for r in rows): raise RuntimeError("artifact verification mismatch")
    marker=json.loads((OUT/"startup_record.json").read_bytes()); scans+=1
    results=json.loads((OUT/"results.json").read_bytes()); scans+=1
    checks=json.loads((OUT/"selfchecks.json").read_bytes()); scans+=1
    regression=json.loads((OUT/"startup_regression.json").read_bytes()); scans+=1
    assert marker["status"]==old["status"] and marker["retry_allowed"] is False
    assert all(v=="PASS" for v in results["criteria"].values()) and len(results["criteria"])==8
    assert len(results["references"])==4 and all(len(r["heads"])==6 for r in results["references"])
    assert old["counts"]["fits"]==24 and old["counts"]["backwards"]==old["counts"]["optimizer_steps"]==4800
    assert checks["status"]==regression["status"]=="PASS"
    source=Path(__file__).read_bytes(); scans+=1
    compile(source,__file__,"exec")
    ledger=dict(old); ledger["counts"]=dict(old["counts"])
    ledger["resources"]=dict(old["resources"])
    ledger["resources"]["windows_working_set_peak_bytes"]=max(old["resources"]["windows_working_set_peak_bytes"],working_set_peak())
    ledger["counts"]["implementation_revisions"]+=1
    ledger["cumulative_implementation_revisions"]+=1
    ledger["source_write_events"]=old["source_write_events"]+[dict(path="scripts/seal_direction_a_probe.py",bytes=7314,revision=3,scope="initial full source write before process-memory measurement addition"),dict(path="scripts/seal_direction_a_probe.py",bytes=len(source),sha256=sha(source),revision=3,scope="delivery verification only; no scientific code or parameters changed")]
    ledger["delivery_verification"]=dict(command=[sys.executable,"-B","scripts/seal_direction_a_probe.py"],
        syntax_checks_total=3,CPU_suites_total=2,experiment_runs_new=1,source_commit=subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT).decode().strip(),
        additional_implementation_revisions=1,preflight_seconds_already_reserved=20,
        program_seconds=None,final_write_reserve_seconds=.5)
    verification=dict(status="PASS",preclosure_files=rows,marker_ledger_consistent=True,
        completed_heads=24,scientific_selfchecks="PASS",regression_tests=20,
        actual_command=ledger["delivery_verification"]["command"],
        new_experiment_input_reads=0,new_fits=0,new_backwards=0,new_optimizer_steps=0,
        final_closure="replacement ledger and index generated together; index excludes itself",
        no_file_over_20MiB=all(r["bytes"]<=20*1024**2 or r["path"].startswith("artifacts_local/") for r in rows),
        delivery_windows_working_set_peak_bytes=working_set_peak(),
        delivery_CPU_byte_buffer_proxy_upper_bytes=8*sum(r["bytes"] for r in rows)+8*len(source),
        CPU_proxy_basis="8 times all verified payload sizes plus source buffer; conservative for retained JSON/index objects and current buffers")
    assert verification["no_file_over_20MiB"]
    ledger["resources"]["cpu_known_arrays_tensor_proxy_peak_bytes"]=max(old["resources"]["cpu_known_arrays_tensor_proxy_peak_bytes"],verification["delivery_CPU_byte_buffer_proxy_upper_bytes"])
    before=old["counts"]["evidence_bytes"]+7314+len(source)
    elapsed=time.monotonic()-START+.5
    ledger["delivery_verification"]["program_seconds"]=elapsed
    for key in ("new_stage_elapsed_seconds","cumulative_elapsed_seconds","cumulative_conservative_elapsed_upper_seconds","elapsed_seconds"):
        ledger[key]=old[key]+elapsed
    review_path=ROOT/"docs/workflow/TO_REVIEWER.md"
    review=review_path.read_text(encoding="utf-8"); scans+=1
    review=review.replace("- 精确累计秒数/峰值显存/Windows working-set/CPU代理/写入见run_record.json；包含启动、自检、读盘、保存、归档及128 KiB应急槽。",
        f"- 新阶段程序及预检包络上界{ledger['new_stage_elapsed_seconds']:.3f}秒；P累计保守上界{ledger['cumulative_conservative_elapsed_upper_seconds']:.3f}秒（含20秒预检工具包络和终末预留）。\n"
        f"- CUDA峰{old['resources']['gpu_allocated_peak_bytes']} B；Windows峰{old['resources']['windows_working_set_peak_bytes']} B；CPU代理峰{old['resources']['cpu_known_arrays_tensor_proxy_peak_bytes']} B。\n"
        "- 最终核验archive_verification.json；修订3/累计9，语法3、CPU套件2（最终20例全PASS）；首次测试参数缺项已封存。\n"
        "- 新增/累计写入、全部覆盖及临时文件成本见run_record.json；封存历史未知项仍保留。")
    review=review.replace("v1历史按基准commit保留", "b702a84修复账本按commit继承")
    assert len(review.splitlines())<=80
    payloads={review_path:review.encode(),OUT/"archive_verification.json":encode(verification)}
    before+=sum(len(raw) for raw in payloads.values())
    files=dict(index["files"])
    for path,raw in payloads.items(): files[path.relative_to(ROOT).as_posix()]=dict(bytes=len(raw),sha256=sha(raw))
    files["scripts/seal_direction_a_probe.py"]=dict(bytes=len(source),sha256=sha(source))
    ledger_name="artifacts/direction_a/phaseP_preparation_v3/run_record.json"
    files[ledger_name]=dict(bytes=0,sha256="0"*64)
    index["files"]=files
    index["verification_record"]="artifacts/direction_a/phaseP_preparation_v3/archive_verification.json"
    ledger["counts"]["scans"]=old["counts"]["scans"]+scans+1
    for key in ("cumulative_scan_known_lower_bound","cumulative_scan_conservative_upper_bound"):
        ledger[key]=old[key]+scans+1
    for _ in range(16):
        ledger["counts"]["evidence_bytes"]=before+len(encode(ledger))+len(encode(index))
        ledger["cumulative_accountable_write_bytes"]=old["historical_failure"]["cumulative_accountable_write_bytes"]+ledger["counts"]["evidence_bytes"]
        files[ledger_name]["bytes"]=len(encode(ledger))
    raw=encode(ledger); files[ledger_name]["sha256"]=sha(raw)
    assert ledger["new_stage_elapsed_seconds"]<580 and ledger["cumulative_conservative_elapsed_upper_seconds"]<600
    assert ledger["counts"]["evidence_bytes"]<120*1024**2 and ledger["cumulative_accountable_write_bytes"]<128*1024**2
    assert ledger["counts"]["scans"]<=9700 and ledger["cumulative_scan_conservative_upper_bound"]<=10000
    assert ledger["cumulative_implementation_revisions"]<=9
    assert ledger["resources"]["windows_working_set_peak_bytes"]<6*1024**3 and ledger["resources"]["cpu_known_arrays_tensor_proxy_peak_bytes"]<2*1024**3
    for path,data in payloads.items(): path.write_bytes(data)
    (OUT/"run_record.json").write_bytes(raw)
    (OUT/"artifact_hashes.json").write_bytes(encode(index))
    if time.monotonic()-START>elapsed: raise RuntimeError("delivery exceeded finalization reserve; not certified")
    print(json.dumps(dict(status="PASS",files=len(files),fail_count=0,blocked=False,
        stage_seconds=ledger["new_stage_elapsed_seconds"],P_upper_seconds=ledger["cumulative_conservative_elapsed_upper_seconds"],
        new_write_bytes=ledger["counts"]["evidence_bytes"],cumulative_write_bytes=ledger["cumulative_accountable_write_bytes"],scans=ledger["counts"]["scans"])))

if __name__=="__main__": main()
