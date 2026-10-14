"""One syntax-only check, then one accounted P-v2 startup, including failure capture.

E:\\anaconda3\\python.exe -B scripts/recover_direction_a_probe.py --syntax-only
E:\\anaconda3\\python.exe -B scripts/recover_direction_a_probe.py

Never imports/executes experimental modules during the syntax-only check.
No third launch, reset, v1 modification or runtime science override exists.
"""

import time
ENTRY_STARTED = time.monotonic()

import ctypes
import hashlib
import json
import os
import subprocess
import sys
import threading
import traceback
from ctypes import wintypes
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts/direction_a/phaseP_preparation_v2"
BASE = "d7706748e70f63885572aded57fab9e674d1a086"
OLD = ROOT / "artifacts/direction_a/phaseP_preparation_v1"
CHECK_PATHS = ["scripts/recover_direction_a_probe.py", "scripts/prepare_direction_a_probe.py",
               "direction_a/probe_preparation.py", "tests/test_direction_a_probe_preparation.py"]
NEW_SOURCE_WRITES = ["scripts/recover_direction_a_probe.py"]
# Full resulting file writes from implementation revision 1, measured before
# applying revision 2. Both overwrites are charged, including this wrapper.
PRIOR_SOURCE_WRITE_EVENTS = [
    dict(path="scripts/prepare_direction_a_probe.py", bytes=45184, revision=1,
         sha256="ac8f8a720dd5adfde726c07c0aa1a1440c4d33d8dc7edbaf4219c63fc539b681"),
    dict(path="scripts/recover_direction_a_probe.py", bytes=11147, revision=1,
         sha256="9aea145eabfd11f3f211499b8739ab83cacdb783cb8a6ade265bb85da734c50c"),
    dict(path="scripts/prepare_direction_a_probe.py", bytes=45742, revision=2,
         sha256="ee5c00efc455100ed0d15b124ddb96b48b999ea36bd839d5198d57a34c896d47"),
    dict(path="scripts/recover_direction_a_probe.py", bytes=15370, revision=2,
         sha256="be5a7f4065d0d96c5daf7d943c265d110f68e781290fd3422a35ae690e147bb9")]


def encode(value):
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False)+"\n").encode("utf-8")


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def git_raw(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT)


def peak_memory():
    class Counters(ctypes.Structure):
        _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD)] + [
            (name, ctypes.c_size_t) for name in ("PeakWorkingSetSize", "WorkingSetSize", "QuotaPeakPagedPoolUsage",
                "QuotaPagedPoolUsage", "QuotaPeakNonPagedPoolUsage", "QuotaNonPagedPoolUsage", "PagefileUsage", "PeakPagefileUsage")]
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    api = ctypes.WinDLL("psapi", use_last_error=True)
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    api.GetProcessMemoryInfo.argtypes = (wintypes.HANDLE, ctypes.POINTER(Counters), wintypes.DWORD)
    value = Counters(); value.cb = ctypes.sizeof(value)
    if not api.GetProcessMemoryInfo(kernel.GetCurrentProcess(), ctypes.byref(value), value.cb):
        raise OSError(ctypes.get_last_error(), "GetProcessMemoryInfo failed")
    return int(value.PeakWorkingSetSize)


def syntax_only():
    previous = None
    if OUT.exists():
        if {p.name for p in OUT.iterdir()} != {"syntax_check.json"}:
            raise RuntimeError("P-v2 startup/output exists: refusing a repeated syntax check")
        previous = json.loads((OUT/"syntax_check.json").read_bytes())
        if previous["syntax_check_invocations"] >= 2:
            raise RuntimeError("pure syntax check cap reached")
    else:
        OUT.mkdir(parents=True)
    records, errors = {}, []
    for name in CHECK_PATHS:
        raw = (ROOT/name).read_bytes()
        try:
            compile(raw, str(ROOT/name), "exec")
            status = "PASS"
        except SyntaxError as exc:
            errors.append(dict(path=name, error=str(exc)))
            status = "FAIL"
        records[name] = dict(bytes=len(raw), sha256=sha(raw), status=status)
    value = dict(status="FAIL" if errors else "PASS", syntax_check_invocations=1 if previous is None else 2,
        target_modules_imported=0, experiment_inputs_read=0, fits=0, optimizer_steps=0,
        check_method="compile(source_bytes, filename, 'exec') only; no module execution",
        files=records, errors=errors, program_seconds=time.monotonic()-ENTRY_STARTED+0.05,
        final_write_time_reserved_seconds=0.05, windows_peak_working_set_bytes=peak_memory(),
        cpu_known_array_proxy_upper_bytes=8*1024**2)
    if previous is not None:
        value["prior_checks"] = [previous]
        value["program_seconds"] += previous["program_seconds"]
        value["windows_peak_working_set_bytes"] = max(value["windows_peak_working_set_bytes"],previous["windows_peak_working_set_bytes"])
    # Fixed-length closure measures the syntax evidence write itself.
    value["evidence_bytes"] = 0
    for _ in range(8):
        value["evidence_bytes"] = len(encode(value)) + (0 if previous is None else previous["evidence_bytes"])
    (OUT/"syntax_check.json").write_bytes(encode(value))
    print(json.dumps(dict(syntax_check=value["status"], seconds=value["program_seconds"])))
    return 1 if errors else 0


def failure_without_budget(context, error):
    """Outer fallback even for parsing/import errors before target budget creation."""
    report = dict(run_id="FedPCC-P-preparation-v2", status="blocked_startup_failure",
        fail_count=7, blocked=error, criteria={str(i):"FAIL" for i in range(1,8)},
        heads=[], completed_heads=0, historical_failure=context["history"],
        source_write_events=context["source_write_events"],
        new_stage_elapsed_seconds=time.monotonic()-context["started"]+0.1,
        new_known_write_bytes=context["preparation_initial_write_bytes"]+128*1024,
        resources=dict(new_windows_working_set_peak_bytes=peak_memory(),
                       new_cuda_peak_bytes=None, new_cpu_proxy_upper_bytes=8*1024**2),
        preparation_launches=2, failed_restarts=1, additional_retry_permitted=False)
    reviewer = (f"# 交付单：P 准备v2启动失败\n\n- 对应任务单的基准 commit：{BASE}\n"
        "- 本次交付 commit：见本提交\n\n## 做了什么（≤5 条）\n- 纯语法检查后一次恢复启动失败，无再次启动。\n"
        "## 产出文件\n- phaseP_preparation_v2/run_record.json、results.json、startup_failure.txt：外层失败捕获。\n"
        "## 判据自评\n|判据编号|结果 PASS/FAIL|证据|\n|---|---|---|\n"+
        "\n".join(f"|{i}|FAIL|启动失败，未完成|" for i in range(1,8))+
        f"\n\n## 实际资源消耗\n- 自动账本见run_record.json；v1历史保留。\n## 阻塞\n{error}\n## 异议\n无\n## 需要审查者裁决的问题\n- 重新执行须另行授权。\n")
    data = {OUT/"startup_failure.txt":error.encode("utf-8"),
            OUT/"results.json":encode(report),
            ROOT/"docs/workflow/TO_REVIEWER.md":reviewer.encode("utf-8")}
    for path, raw in data.items():
        path.write_bytes(raw)
        report["new_known_write_bytes"] += len(raw)
    index = dict(files={},excluded=["artifact_hashes.json (self)"], historical_failure_commit=BASE)
    for path in [*OUT.glob("*"), ROOT/"docs/workflow/TO_REVIEWER.md", *[ROOT/p for p in CHECK_PATHS]]:
        if path.is_file() and path.name not in ("run_record.json","artifact_hashes.json"):
            raw = path.read_bytes(); name = path.relative_to(ROOT).as_posix()
            index["files"][name] = dict(path=name,bytes=len(raw),sha256=sha(raw))
    name = (OUT/"run_record.json").relative_to(ROOT).as_posix()
    index["files"][name] = dict(path=name,bytes=0,sha256="0"*64)
    previous = report["new_known_write_bytes"]
    report["new_stage_elapsed_seconds"] = time.monotonic()-context["started"]+0.1
    report["cumulative_elapsed_seconds"] = context["history"]["elapsed_seconds"]+report["new_stage_elapsed_seconds"]
    for _ in range(8):
        index["files"][name]["bytes"] = len(encode(report))
        report["new_known_write_bytes"] = previous+len(encode(report))+len(encode(index))
    report["cumulative_accountable_write_bytes"] = context["history"]["counts"]["evidence_bytes"]+report["new_known_write_bytes"]
    for _ in range(8):
        index["files"][name]["bytes"] = len(encode(report))
        report["new_known_write_bytes"] = previous+len(encode(report))+len(encode(index))
        report["cumulative_accountable_write_bytes"] = context["history"]["counts"]["evidence_bytes"]+report["new_known_write_bytes"]
    raw = encode(report); index["files"][name]["sha256"] = sha(raw)
    (OUT/"run_record.json").write_bytes(raw)
    (OUT/"artifact_hashes.json").write_bytes(encode(index))


def run_once():
    if (OUT/"run_record.json").exists() or (OUT/"startup_record.json").exists():
        raise RuntimeError("P-v2 startup ledger exists: refusing another launch")
    syntax_raw = (OUT/"syntax_check.json").read_bytes()
    syntax = json.loads(syntax_raw)
    if syntax["status"] != "PASS":
        raise RuntimeError("pure syntax check has not passed")
    if subprocess.run(["git","merge-base","--is-ancestor",BASE,"HEAD"],cwd=ROOT).returncode:
        raise RuntimeError("baseline commit is not an ancestor of HEAD")
    for name, record in syntax["files"].items():
        if sha((ROOT/name).read_bytes()) != record["sha256"]:
            raise RuntimeError("source changed after syntax check: "+name)
    history_raw = (OLD/"run_record.json").read_bytes()
    history = json.loads(history_raw)
    old_index = json.loads((OLD/"artifact_hashes.json").read_bytes())
    # Source/reviewer paths in the v1 index resolve against BASE, never newer files.
    restored_line_endings = {}
    for name, record in old_index["files"].items():
        raw = git_raw("show", f"{BASE}:{name}")
        # Git stores LF; the v1 PowerShell JSON serializer emitted internal CRLF
        # plus a final LF. Reconstruct only those byte-preserving newline forms,
        # then require the ORIGINAL archived size/hash. No v1 file is rewritten.
        alternatives = {"committed_LF":raw, "CRLF":raw.replace(b"\n",b"\r\n")}
        if raw.endswith(b"\n"):
            alternatives["internal_CRLF_final_LF"] = raw[:-1].replace(b"\n",b"\r\n")+b"\n"
        matched = next((kind for kind, candidate in alternatives.items()
                        if sha(candidate)==record["sha256"] and len(candidate)==record["bytes"]),None)
        if matched is None:
            raise RuntimeError("v1 committed failure archive mismatch: "+name)
        restored_line_endings[name] = dict(committed_LF_sha256=sha(raw), indexed_original_sha256=record["sha256"],
                                           matching_line_endings=matched, original_bytes=record["bytes"])
        if name.startswith("artifacts/direction_a/phaseP_preparation_v1/") and sha((ROOT/name).read_bytes()) != record["sha256"]:
            raise RuntimeError("v1 preserved evidence changed: "+name)
    history.update(commit=BASE, directory="artifacts/direction_a/phaseP_preparation_v1",
        ledger_sha256=sha(history_raw), old_source_paths_resolved_at_commit=True,
        unknown_old_peak_values_retained=True, unknown_old_overwrite_bytes=None,
        committed_original_line_ending_provenance=restored_line_endings,
        old_criterion_6="FAIL (never retrospectively upgraded)")
    source_events = PRIOR_SOURCE_WRITE_EVENTS + [dict(path=name, bytes=(ROOT/name).stat().st_size,
        sha256=sha((ROOT/name).read_bytes()), revision=2, write_kind="full file after applied implementation revision")
        for name in NEW_SOURCE_WRITES]
    initial_bytes = sum(e["bytes"] for e in source_events)+syntax["evidence_bytes"]
    context = dict(started=ENTRY_STARTED-syntax["program_seconds"], syntax=syntax,
        history=history, source_write_events=source_events,
        preparation_initial_write_bytes=initial_bytes,
        preparation_initial_scans=90,
        initial_scan_accounting="90-scan conservative envelope: both pure syntax checks, source hashes, v1 committed/working validation including line-ending hashes")
    startup = dict(run_id="FedPCC-P-preparation-v2", status="launching", launches_new=1,
        launches_cumulative=2, failed_restarts_cumulative=1, retry_allowed=False,
        source_sha256=syntax["files"]["scripts/prepare_direction_a_probe.py"]["sha256"],
        input_commit=git_raw("rev-parse","HEAD").decode().strip(),
        historical_failure_commit=BASE, startup_elapsed_seconds=time.monotonic()-context["started"])
    startup_raw = encode(startup)
    (OUT/"startup_record.json").write_bytes(startup_raw)
    context["preparation_initial_write_bytes"] += len(startup_raw)
    stop_event = threading.Event()
    namespace = {"__file__":str(ROOT/"scripts/prepare_direction_a_probe.py"),
                 "__name__":"bounded_probe_runtime", "RECOVERY_CONTEXT":context}
    def emergency_report(message):
        # The slot was included in the new-stage evidence budget before fitting.
        # Emit a short handoff even if a guard terminates the active process.
        raw = (f"# 交付单：P准备v2资源触顶\n\n- 对应任务单的基准 commit：{BASE}\n"
               "- 本次交付 commit：见本提交\n\n## 做了什么\n- 一次恢复运行触顶，保留部分文件，未重跑。\n"
               "## 产出文件\n- artifacts/direction_a/phaseP_preparation_v2/：部分交付与已消耗账本。\n"
               "## 判据自评\n|编号|PASS/FAIL|证据|\n|---|---|---|\n"+
               "\n".join(f"|{i}|FAIL|资源触顶，未完成验收|" for i in range(1,8))+
               f"\n## 实际资源消耗\n- 见run_record.json及startup_record.json。\n## 阻塞\n{message}\n"
               "## 异议\n无\n## 需要审查者裁决的问题\n- 完成剩余交付需要另行授权。\n").encode("utf-8")
        (ROOT/"docs/workflow/TO_REVIEWER.md").write_bytes(raw)
    context["emergency_report"] = emergency_report
    def outer_watch():
        while not stop_event.wait(.1):
            if time.monotonic()-context["started"] >= 599 or peak_memory() >= 6*1024**3:
                startup["status"]="blocked_outer_time_or_working_set_limit"
                startup["elapsed_seconds"]=time.monotonic()-context["started"]
                # This small emergency record fits the pre-reserved slot.
                (OUT/"startup_record.json").write_bytes(encode(startup))
                emergency_report("Outer startup/time/working-set guard reached; no retry")
                os._exit(124)
    threading.Thread(target=outer_watch,daemon=True).start()
    try:
        raw = (ROOT/"scripts/prepare_direction_a_probe.py").read_bytes()
        exec(compile(raw, namespace["__file__"], "exec"), namespace)
        budget, results, criteria = namespace["main"]()
        startup.update(status="completed_preparation", completed_heads=budget.counts["fits"],
                       elapsed_seconds_before_archive=time.monotonic()-context["started"])
        namespace["write"](OUT/"startup_record.json",startup,budget)
        namespace["archive"](budget,[ROOT/"docs/workflow/TO_REVIEWER.md", *[ROOT/p for p in CHECK_PATHS]])
        print(json.dumps(dict(status=budget.status,fail_count=0,blocked=False,
            new_stage_seconds=budget.snapshot()["elapsed_seconds"],
            cumulative_seconds=budget.snapshot()["cumulative_elapsed_seconds"],
            counts=budget.counts,resources=budget.resources)))
        return 0
    except BaseException:
        error = traceback.format_exc()
        budget = context.get("budget")
        if budget is None:
            failure_without_budget(context,error)
        else:
            budget.status="blocked_partial_preparation"
            if budget.hit is not None:
                emergency_report(error)
                budget.save(reserved=True)
            else:
                namespace["write"](OUT/"startup_failure.txt",error.encode("utf-8"),budget,raw=True)
                startup.update(status="failed_no_retry",elapsed_seconds=time.monotonic()-context["started"])
                namespace["write"](OUT/"startup_record.json",startup,budget)
                criteria = dict(context.get("criteria",{str(i):"FAIL" for i in range(1,8)}))
                criteria["6"] = "FAIL"
                results = context.get("results",dict(references=[]))
                results.update(criteria=criteria,blocked=error)
                namespace["write"](OUT/"results.json",results,budget)
                namespace["write"](ROOT/"docs/workflow/TO_REVIEWER.md",
                    namespace["review_text"](criteria,results,budget,error),budget,raw=True)
                budget.save()
                namespace["archive"](budget,[ROOT/"docs/workflow/TO_REVIEWER.md", *[ROOT/p for p in CHECK_PATHS]])
        print(error, file=sys.stderr)
        return 1
    finally:
        stop_event.set()


if __name__ == "__main__":
    if Path(sys.executable).resolve() != Path(r"E:\anaconda3\python.exe").resolve():
        raise RuntimeError("required interpreter mismatch")
    if sys.argv[1:] == ["--syntax-only"]:
        sys.exit(syntax_only())
    if sys.argv[1:]:
        raise RuntimeError("no runtime protocol overrides supported")
    sys.exit(run_once())
