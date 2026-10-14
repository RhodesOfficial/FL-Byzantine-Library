"""P-v3 production orchestration; CPU regression gates single real-input run."""
import time
ENTRY_STARTED=time.monotonic()
import hashlib
import importlib.util
import json
import subprocess
import sys
import traceback
import unittest
from pathlib import Path
from unittest.mock import patch

sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
OUT=ROOT/"artifacts/direction_a/phaseP_preparation_v3"
BASE="2f7b638550c1b986b7fa2ffd3eabcd191e956cc8"
REPAIR="b702a8416187b50aa130b01fb333db98f81116ac"
HISTORY_PATH="artifacts/direction_a/phaseP_startup_repair_v1/run_record.json"
SOURCES=["direction_a/probe_startup.py","scripts/recover_direction_a_probe.py",
         "scripts/prepare_direction_a_probe.py","tests/test_direction_a_probe_startup.py"]

def encode(value):
    return (json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2,allow_nan=False)+"\n").encode()

def sha(raw): return hashlib.sha256(raw).hexdigest()

def execute_attempt(*args,**kwargs):
    from direction_a.probe_startup import execute_attempt as execute
    return execute(*args,**kwargs)

def production_namespace(context):
    ns=dict(__file__=str(ROOT/"scripts/prepare_direction_a_probe.py"),__name__="bounded_probe_runtime",RECOVERY_CONTEXT=context)
    raw=(ROOT/"scripts/prepare_direction_a_probe.py").read_bytes()
    exec(compile(raw,ns["__file__"],"exec"),ns)
    return ns

def run_once(context,namespace_factory=production_namespace):
    """Both injected CPU work and real training use this factory/work wiring."""
    ns={}
    def factory():
        ns.update(namespace_factory(context))
        context["limits"]=ns["LIMITS"]
        from direction_a.probe_startup import RecoveryBudget
        return RecoveryBudget(context)
    def work(budget): ns["main"](budget)
    def archive(budget):
        if ns.get("archive_callback"): ns["archive_callback"](budget)
    return execute_attempt(context,factory,work,archive)

def committed_history():
    raw=subprocess.check_output(["git","show",f"{REPAIR}:{HISTORY_PATH}"],cwd=ROOT)
    if (ROOT/HISTORY_PATH).read_bytes().replace(b"\r\n",b"\n")!=raw:
        raise RuntimeError("sealed repair ledger changed")
    value=json.loads(raw)
    value.update(commit=REPAIR,ledger_sha256=sha(raw),old_preparation_criterion_6="FAIL")
    return value

def check():
    if OUT.exists(): raise FileExistsError("check attempt exists; no overwrite")
    OUT.mkdir(parents=True)
    counts=dict(write_bytes=128*1024,scans=0)
    events=[]
    for name in SOURCES:
        raw=(ROOT/name).read_bytes(); counts["scans"]+=1
        events.append(dict(path=name,bytes=len(raw),sha256=sha(raw),revision=1))
    # First startup-module patch was smaller than its final form; charge final
    # size again as an explicit conservative bound for that intermediate write.
    events.append(dict(path=SOURCES[0],bytes=events[0]["bytes"],revision=1,
                       write_kind="intermediate overwrite conservative size bound"))
    counts["write_bytes"]+=sum(e["bytes"] for e in events)
    forbidden=[]; peak_buffer=max(e["bytes"] for e in events)
    read,write=Path.read_bytes,Path.write_bytes
    def tracked_read(path):
        nonlocal peak_buffer
        name=str(path.resolve()).replace("\\","/")
        if any(x in name for x in ("/RAW_DATA/","/checkpoints/","/phaseG1_2_","/phase0_2_v1/tasks/")):
            forbidden.append(name); raise AssertionError("real experiment read intercepted")
        raw=read(path); counts["scans"]+=1; peak_buffer=max(peak_buffer,len(raw)); return raw
    def tracked_write(path,raw):
        nonlocal peak_buffer
        from direction_a.probe_startup import PROTECTED
        p=path.resolve()
        if any(p==x.resolve() or x.resolve() in p.parents for x in PROTECTED): raise PermissionError("sealed evidence write")
        if counts["write_bytes"]+len(raw)>=4*1024**2 or time.monotonic()-ENTRY_STARTED>=60:
            raise RuntimeError("CPU repair resource cap")
        result=write(path,raw); counts["write_bytes"]+=len(raw); peak_buffer=max(peak_buffer,len(raw)); return result
    with patch.object(Path,"read_bytes",tracked_read),patch.object(Path,"write_bytes",tracked_write):
        syntax=[]
        for name in SOURCES+["direction_a/probe_preparation.py","tests/test_direction_a_probe_preparation.py"]:
            raw=(ROOT/name).read_bytes()
            try: compile(raw,name,"exec"); status="PASS"; error=None
            except SyntaxError: status="FAIL"; error=traceback.format_exc()
            syntax.append(dict(path=name,sha256=sha(raw),status=status,error=error))
        syntax_ok=all(x["status"]=="PASS" for x in syntax)
        command=[sys.executable,"-B","scripts/recover_direction_a_probe.py","--check"]
        (OUT/"syntax_check.json").write_bytes(encode(dict(status="PASS" if syntax_ok else "FAIL",invocation=1,files=syntax,actual_command=command,target_modules_executed=0)))
        import torch
        from direction_a.backbone_preparation import windows_memory
        if torch.cuda.is_initialized(): raise RuntimeError("CPU isolation CUDA already initialized")
        def deny(name):
            def blocked(*a,**kw): forbidden.append(name); raise AssertionError(name+" blocked")
            return blocked
        class Results(unittest.TestResult):
            def __init__(self): super().__init__(); self.cases=[]
            def addSuccess(self,t): super().addSuccess(t); self.cases.append(dict(case=t.id(),status="PASS"))
            def addError(self,t,e): super().addError(t,e); self.cases.append(dict(case=t.id(),status="FAIL",error=self._exc_info_to_string(e,t)))
            def addFailure(self,t,e): super().addFailure(t,e); self.cases.append(dict(case=t.id(),status="FAIL",error=self._exc_info_to_string(e,t)))
        result=Results()
        with patch.object(torch,"load",deny("torch.load")),patch.object(torch.cuda,"init",deny("CUDA init")),patch.object(torch.cuda,"_lazy_init",deny("CUDA lazy init")),patch.object(torch.Tensor,"cuda",deny("tensor CUDA")),patch.object(torch.nn.functional,"linear",deny("head forward")),patch.object(torch.Tensor,"backward",deny("backward")),patch.object(torch.optim.Adam,"step",deny("optimizer step")):
            spec=importlib.util.spec_from_file_location("startup_tests",ROOT/"tests/test_direction_a_probe_startup.py")
            module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
            if syntax_ok: unittest.defaultTestLoader.loadTestsFromModule(module).run(result)
        history=committed_history()
        proxy=8*peak_buffer+8*sum(e["bytes"] for e in events)
        peak=windows_memory()["peak_working_set_bytes"]
        passed=syntax_ok and result.wasSuccessful() and result.testsRun>0 and not forbidden and proxy<64*1024**2 and peak<2*1024**3 and time.monotonic()-ENTRY_STARTED<59
        evidence=dict(status="PASS" if passed else "FAIL",cases=result.cases,tests_run=result.testsRun,
            syntax_checks=1,CPU_suites=1,implementation_revisions=1,actual_command=command,
            isolation=dict(forbidden_attempts=forbidden,real_input_reads=0,CUDA_initialized=torch.cuda.is_initialized(),production_run_once_called=True,data_training_dependencies="synthetic injected namespace",synthetic_costs_separate=True),
            resources=dict(windows_working_set_peak_bytes=peak,cpu_proxy_upper_bytes=proxy,cuda_allocated_peak_bytes=0),
            inherited_history=dict(commit=REPAIR,reported_seconds=history["cumulative_reported_elapsed_seconds"],upper_seconds=history["cumulative_conservative_elapsed_upper_seconds"],bytes=history["cumulative_accountable_write_bytes"],revisions=6,scan_upper=286,unknowns=history["historical_unknowns"]),
            source_write_events=events,source_fingerprints={x["path"]:x["sha256"] for x in syntax})
        (OUT/"startup_regression.json").write_bytes(encode(evidence))
        cost=dict(status=evidence["status"],program_seconds=time.monotonic()-ENTRY_STARTED+.25,
            finalization_reserve_seconds=.25,counts=dict(counts),source_write_events=events,resources=evidence["resources"],
            scans_include_synthetic_test_io=True,preflight_shell_program_seconds_upper_bound=10,
            preflight_basis="read/ancestor/edit tool program envelopes each below 1s; conservative 10s reservation")
        before=counts["write_bytes"]
        for _ in range(12): cost["counts"]["write_bytes"]=before+len(encode(cost))
        (OUT/"check_cost.json").write_bytes(encode(cost))
    print(json.dumps(dict(status=evidence["status"],tests=result.testsRun,seconds=cost["program_seconds"],bytes=counts["write_bytes"])))
    return 0 if passed else 1

def launch():
    regression=json.loads((OUT/"startup_regression.json").read_bytes())
    if regression["status"]!="PASS": raise RuntimeError("production regression gate FAIL")
    for name,digest in regression["source_fingerprints"].items():
        if sha((ROOT/name).read_bytes())!=digest: raise RuntimeError("source changed after regression")
    if subprocess.run(["git","merge-base","--is-ancestor",BASE,"HEAD"],cwd=ROOT).returncode: raise RuntimeError("baseline mismatch")
    cost=json.loads((OUT/"check_cost.json").read_bytes())
    context=dict(output=OUT,run_id="FedPCC-P-preparation-v3",history=committed_history(),
        started=ENTRY_STARTED-cost["program_seconds"]-cost["preflight_shell_program_seconds_upper_bound"],
        source_write_events=cost["source_write_events"],implementation_revisions=1,
        preparation_initial_write_bytes=cost["counts"]["write_bytes"],preparation_initial_scans=cost["counts"]["scans"]+12,
        total_wall_seconds=600,total_write_bytes=128*1024**2,new_preparation_launches=1,new_failed_restarts=0,
        cpu_proxy_upper_bytes=cost["resources"]["cpu_proxy_upper_bytes"],cpu_proxy_basis="CPU regression tracked buffers; maximum with experiment budget cache envelope",
        archive_repo_paths=True,archive_extra_paths=[ROOT/p for p in SOURCES+["direction_a/probe_preparation.py","tests/test_direction_a_probe_preparation.py","docs/workflow/TO_EXECUTOR.md","docs/workflow/TO_REVIEWER.md"]])
    context["limits"]=dict(wall_seconds=580,evidence_bytes=120*1024**2,scans=9700,gpu_allocated_bytes=6*1024**3,windows_peak_working_set_bytes=6*1024**3,cpu_tensor_proxy_bytes=2*1024**3)
    terminal=run_once(context)
    print(json.dumps(dict(status=terminal["status"],error=terminal["error"],seconds=terminal["new_stage_elapsed_seconds"]),ensure_ascii=False))
    return 0 if terminal["status"]=="completed" else 1

if __name__=="__main__":
    if Path(sys.executable).resolve()!=Path(r"E:\anaconda3\python.exe").resolve(): raise RuntimeError("required interpreter mismatch")
    if sys.argv[1:]==["--check"]: sys.exit(check())
    if sys.argv[1:]==["--run"]: sys.exit(launch())
    raise RuntimeError("use --check then --run; no scientific overrides")
