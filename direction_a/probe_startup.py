"""P-only startup accounting. Shared accepted G1.2 budget classes stay intact."""

import hashlib
import json
import time
import traceback
from pathlib import Path

from direction_a.backbone_preparation import encode, windows_memory
from direction_a.class_gradient_full import FullBudget

ROOT = Path(__file__).resolve().parents[1]
PROTECTED = [ROOT/"artifacts/direction_a"/name for name in
             ("phaseP_preparation_v1", "phaseP_preparation_v2", "phaseP_startup_repair_v1")]


def writable_output(output):
    output = Path(output).resolve()
    if any(output == p.resolve() or p.resolve() in output.parents for p in PROTECTED):
        raise PermissionError("sealed P failure directory: " + str(output))
    return output


def history_totals(history):
    """v2 already contains v1; never add the nested history twice."""
    if "cumulative_reported_elapsed_seconds" in history:
        return dict(seconds=history["cumulative_reported_elapsed_seconds"],
                    upper_seconds=history["cumulative_conservative_elapsed_upper_seconds"],
                    bytes=history["cumulative_accountable_write_bytes"], scans=None,
                    scan_lower_bound=history["counts"]["scans"]+16,
                    scan_upper_bound=286, revisions=history["cumulative_implementation_revisions"],
                    launches=history["inherited_preparation_launches"],
                    restarts=history["inherited_failed_restarts"])
    if "cumulative_elapsed_seconds" in history:
        return dict(seconds=history["cumulative_elapsed_seconds"],
                    bytes=history["cumulative_accountable_write_bytes"],
                    scans=None, scan_lower_bound=history["historical_failure"]["counts"]["archive_hash_scans"],
                    revisions=history["historical_failure"]["implementation_revisions"]+
                              len({e["revision"] for e in history["source_write_events"]}),
                    launches=history["preparation_launches"], restarts=history["failed_restarts"])
    return dict(seconds=history["elapsed_seconds"], bytes=history["counts"]["evidence_bytes"],
                scans=history["counts"]["archive_hash_scans"], scan_lower_bound=history["counts"]["archive_hash_scans"],
                revisions=history["implementation_revisions"], launches=history["preparation_launches"],
                restarts=history["failed_retries"])


class RecoveryBudget(FullBudget):
    """Defer P-derived snapshots until BOTH real parent constructors finish."""

    def __init__(self, context):
        self.context = context
        self.history = history_totals(context["history"])
        output = writable_output(context["output"])
        path = output/"run_record.json"
        if path.exists():
            raise FileExistsError("ledger exists; no restart or overwrite")
        marker = output/"startup_record.json"
        if marker.exists():
            if not context.get("startup_token"):
                raise FileExistsError("startup marker exists; no restart")
            value = json.loads(marker.read_bytes())
            if value["token"] != context["startup_token"]:
                raise FileExistsError("startup marker exists; no restart")
        # These are mandatory inherited inputs, validated before writing anything.
        self.initial_bytes = context["preparation_initial_write_bytes"]
        self.initial_scans = context["preparation_initial_scans"]
        self.revisions = context["implementation_revisions"]
        self._initializing = True
        # Publish the actual object before parent constructors can fail or write.
        context["budget"] = self
        super().__init__(path, context["limits"], context["started"])
        self.counts.update(fits=0, preparation_runs=0, encoder_forwards=0,
                           communications=0, implementation_revisions=self.revisions)
        self.counts["evidence_bytes"] += self.initial_bytes
        self.counts["scans"] += self.initial_scans
        self.cpu_proxy(context["cpu_proxy_upper_bytes"])
        self._initializing = False
        self.check()
        self.save()

    def check(self):
        super().check()
        elapsed = time.monotonic()-self.started+self.history["seconds"]
        if elapsed >= self.context["total_wall_seconds"]:
            self.stop("P_cumulative_wall_seconds", elapsed)
        if self.counts["evidence_bytes"]+self.history["bytes"] >= self.context["total_write_bytes"]:
            self.stop("P_cumulative_write_bytes", self.counts["evidence_bytes"]+self.history["bytes"])
        if self.history.get("upper_seconds", self.history["seconds"])+time.monotonic()-self.started >= self.context["total_wall_seconds"]:
            self.stop("P_cumulative_upper_wall_seconds", time.monotonic()-self.started)
        if self.counts["scans"]+self.history.get("scan_upper_bound", self.history["scan_lower_bound"]) > 10000:
            self.stop("P_cumulative_scans", self.counts["scans"])

    def snapshot(self, now=None):
        value = super().snapshot(now)
        if self._initializing:
            # Parent save() dynamically dispatches here. Its snapshot is complete
            # for that initialization phase; no P counters exist yet or read as 0.
            value["P_initialization_pending"] = True
            return value
        scans = None if self.history["scans"] is None else self.history["scans"]+self.counts["scans"]
        value.update(run_id=self.context["run_id"], historical_failure=self.context["history"],
                     source_write_events=self.context["source_write_events"],
                     new_stage_elapsed_seconds=value["elapsed_seconds"],
                     cumulative_elapsed_seconds=self.history["seconds"]+value["elapsed_seconds"],
                     cumulative_accountable_write_bytes=self.history["bytes"]+self.counts["evidence_bytes"],
                     cumulative_scans=scans,
                     cumulative_scan_known_lower_bound=self.history["scan_lower_bound"]+self.counts["scans"],
                     cumulative_preparation_launches=self.history["launches"]+self.context["new_preparation_launches"],
                     cumulative_failed_restarts=self.history["restarts"]+self.context["new_failed_restarts"],
                     cumulative_implementation_revisions=self.history["revisions"]+self.revisions,
                     no_full_historical_peak_or_write_compliance_claim=True)
        value["cumulative_conservative_elapsed_upper_seconds"] = self.history.get("upper_seconds", self.history["seconds"])+value["elapsed_seconds"]
        value["cumulative_scan_conservative_upper_bound"] = self.history.get("scan_upper_bound", self.history["scan_lower_bound"])+self.counts["scans"]
        return value


def claim_startup(context):
    output = writable_output(context["output"])
    if (output/"run_record.json").exists() or (output/"startup_record.json").exists():
        raise FileExistsError("attempt already marked; automatic retry forbidden")
    output.mkdir(parents=True, exist_ok=True)
    token = hashlib.sha256(f"{output}:{time.monotonic_ns()}".encode()).hexdigest()
    context["startup_token"] = token
    raw = encode(dict(token=token, status="launching", retry_allowed=False))
    (output/"startup_record.json").write_bytes(raw)
    context["preparation_initial_write_bytes"] += len(raw)
    return output


def finalize_attempt(context, budget, status, error, archive_callback=None):
    """Close one attempt, including archive exceptions and terminal limit hits."""
    budget = budget or context.get("budget")
    output = writable_output(context["output"])
    clock = context.get("clock", time.monotonic)
    durations = []
    bytes_written = context["preparation_initial_write_bytes"]+128*1024 if budget is None else budget.counts["evidence_bytes"]
    scans = context["preparation_initial_scans"] if budget is None else budget.counts["scans"]
    def put(path, raw):
        nonlocal bytes_written
        t = clock(); Path(path).write_bytes(raw); durations.append(max(0.,clock()-t))
        bytes_written += len(raw)
    if archive_callback is not None:
        try:
            archive_callback(budget)
        except Exception:
            status = "failed_no_retry"
            error = (error or "")+"\nARCHIVE:\n"+traceback.format_exc()
        if budget is not None:
            bytes_written = budget.counts["evidence_bytes"]
            scans = budget.counts["scans"]
    if error:
        put(output/"startup_failure.txt", error.encode("utf-8"))
    history = history_totals(context["history"])
    resources = dict(getattr(budget, "resources", {}))
    torch = __import__("torch")
    for name, actual in (("windows_working_set_peak_bytes", windows_memory()["peak_working_set_bytes"]),
                         ("gpu_allocated_peak_bytes", torch.cuda.max_memory_allocated() if torch.cuda.is_initialized() else 0),
                         ("cpu_known_arrays_tensor_proxy_peak_bytes", context["cpu_proxy_upper_bytes"])):
        resources[name] = max(resources.get(name, 0), actual)
    resources["cpu_proxy_basis"] = context["cpu_proxy_basis"]+"; maximum with measured budget training envelope"
    records = {}
    paths = [p for p in output.rglob("*") if p.is_file() and p.name not in ("run_record.json", "artifact_hashes.json", "startup_record.json")]
    paths += [Path(p) for p in context.get("archive_extra_paths", [])]
    local = ROOT/"artifacts_local"/output.relative_to(ROOT) if output.is_relative_to(ROOT) else None
    if local and local.exists():
        paths += [p for p in local.rglob("*") if p.is_file()]
    base = ROOT if context.get("archive_repo_paths") else output
    for path in paths:
        scans += 1
        try:
            raw = path.read_bytes()
            records[path.relative_to(base).as_posix()] = dict(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
        except Exception:
            status="failed_no_retry"
            error=(error or "")+"\nARCHIVE INDEX:\n"+traceback.format_exc()
    if budget is None:
        ledger = dict(run_id=context["run_id"], historical_failure=context["history"], counts={"scans":scans},
                      source_write_events=context["source_write_events"])
    else:
        budget.status=status; ledger=budget.snapshot(clock()); ledger["counts"]=dict(ledger["counts"])
    ledger.update(status=status, error=error, resources=resources, retry_allowed=False,
                  cumulative_preparation_launches=history["launches"]+context["new_preparation_launches"],
                  cumulative_failed_restarts=history["restarts"]+context["new_failed_restarts"],
                  cumulative_implementation_revisions=history["revisions"]+context["implementation_revisions"])
    index=dict(files=records,excluded=["artifact_hashes.json (self)"],algorithm="SHA-256 file bytes")
    ledger_name = (output/"run_record.json").relative_to(base).as_posix()
    marker_name = (output/"startup_record.json").relative_to(base).as_posix()
    records[ledger_name]=dict(bytes=0,sha256="0"*64)
    # The bound comes from actual writes in this closing operation, with a 10ms
    # scheduling floor and eight times the maximum observed write latency.
    reserve=max(.25,8*max(durations,default=0.))
    end_bound=clock()+reserve
    ledger.update(finalization_reserve_seconds=reserve, finalization_reserve_basis="max(10ms,8*measured closing write latency)",
                  new_stage_elapsed_seconds=end_bound-context["started"],
                  cumulative_elapsed_seconds=history["seconds"]+end_bound-context["started"])
    ledger["cumulative_conservative_elapsed_upper_seconds"] = history.get("upper_seconds", history["seconds"])+end_bound-context["started"]
    ledger["cumulative_scan_conservative_upper_bound"] = history.get("scan_upper_bound",history["scan_lower_bound"])+scans+1
    # A terminal repair uses the already charged emergency slot. Completed is
    # never accepted unless all post-archive limits, including closure, pass.
    for closing_attempt in range(3):
        violations = []
        if end_bound-context["started"] >= context["limits"]["wall_seconds"] or ledger["cumulative_conservative_elapsed_upper_seconds"] >= context["total_wall_seconds"]:
            violations.append("terminal time limit")
        if scans+1 > context["limits"]["scans"] or ledger["cumulative_scan_conservative_upper_bound"] > 10000:
            violations.append("terminal scans limit")
        if budget is not None and budget.hit:
            violations.append(str(budget.hit))
        for field, name in (("gpu_allocated_bytes","gpu_allocated_peak_bytes"),("windows_peak_working_set_bytes","windows_working_set_peak_bytes"),("cpu_tensor_proxy_bytes","cpu_known_arrays_tensor_proxy_peak_bytes")):
            if resources[name] >= context["limits"][field]: violations.append(field)
        if violations:
            status="failed_terminal_limit"; error=(error or "")+"; "+"; ".join(violations)
        emergency = status != "completed"
        ledger.update(status=status,error=error,terminal_limit_violations=violations,
                      emergency_closure_from_precharged_slot=emergency)
        marker=encode(dict(token=context["startup_token"],status=status,retry_allowed=False,error=error))
        records[marker_name]=dict(bytes=len(marker),sha256=hashlib.sha256(marker).hexdigest())
        for _ in range(16):
            extra = 0 if emergency else len(marker)+len(encode(ledger))+len(encode(index))
            ledger["counts"].update(scans=scans+1,evidence_bytes=bytes_written+extra)
            ledger["cumulative_scans"]=None if history["scans"] is None else history["scans"]+scans+1
            ledger["cumulative_scan_known_lower_bound"]=history["scan_lower_bound"]+scans+1
            ledger["cumulative_accountable_write_bytes"]=history["bytes"]+ledger["counts"]["evidence_bytes"]
            records[ledger_name]["bytes"]=len(encode(ledger))
        if not emergency and (ledger["counts"]["evidence_bytes"] >= context["limits"]["evidence_bytes"] or ledger["cumulative_accountable_write_bytes"] >= context["total_write_bytes"]):
            status="failed_terminal_limit"; error="terminal write limit"; continue
        raw=encode(ledger); records[ledger_name]["sha256"]=hashlib.sha256(raw).hexdigest()
        if emergency and len(raw)+len(encode(index))+len(marker) > 128*1024:
            raise RuntimeError("emergency closure exceeds precharged slot")
        (output/"startup_record.json").write_bytes(marker)
        (output/"run_record.json").write_bytes(raw)
        (output/"artifact_hashes.json").write_bytes(encode(index))
        if clock() <= end_bound:
            break
        status="failed_terminal_limit"; error="finalization exceeded measured allowance"
        end_bound=clock()+max(.25, reserve)
        ledger.update(new_stage_elapsed_seconds=end_bound-context["started"],
                      cumulative_elapsed_seconds=history["seconds"]+end_bound-context["started"],
                      cumulative_conservative_elapsed_upper_seconds=history.get("upper_seconds",history["seconds"])+end_bound-context["started"])
    else:
        raise RuntimeError("terminal failure could not be closed within allowance")
    if budget is not None:
        budget.counts.update(ledger["counts"]); budget.status=status
    return ledger


def execute_attempt(context, budget_factory, work, archive_callback=None):
    """Same wrapper lifecycle used by CPU injected failures and real launches."""
    claim_startup(context)
    budget = None
    try:
        budget = budget_factory()
        context["budget"] = budget
        work(budget)
    except Exception:
        return finalize_attempt(context,budget or context.get("budget"),"failed_no_retry",traceback.format_exc(),archive_callback)
    return finalize_attempt(context,budget,"completed",None,archive_callback)
