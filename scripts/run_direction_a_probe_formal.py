"""One frozen P-formal entry: --check, commit sources/registration, --run, --seal.

No scientific command-line overrides or retry after any real-input read.
"""
import time
ENTRY_STARTED = time.monotonic()
import os
os.environ["CUBLAS_WORKSPACE_CONFIG"] = ":4096:8"
import gc
import hashlib
import importlib.util
import io
import json
import pickle
import subprocess
import sys
import tempfile
import traceback
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.dont_write_bytecode = True
OUT = ROOT/"artifacts/direction_a/phaseP_formal_v1"
BASE = "0dc4a1331ef307cff65657190eb1b048ebd98410"
G12_COMMIT = "d3a3bd712d6bb28283b59faff16e17e099debcb4"
PREP_COMMIT = "a0f6428c6f3deec5c5fda76c8b0b01763e83f344"
RUN_ID = "FedPCC-P-formal-v1"
SOURCES = ["scripts/run_direction_a_probe_formal.py", "direction_a/probe_formal.py",
           "tests/test_direction_a_probe_formal.py", "direction_a/probe_startup.py",
           "direction_a/probe_preparation.py", "scripts/prepare_direction_a_probe.py",
           "scripts/recover_direction_a_probe.py", "direction_a/class_gradient_full.py",
           "direction_a/backbone_preparation.py", "direction_a/class_gradient_smoke.py",
           "direction_a/model.py", "models/ResNet.py", "tests/test_direction_a_probe_startup.py"]
LIMITS = dict(wall_seconds=4380, evidence_bytes=128*1024**2, scans=500000,
              fits=400, backwards=400000, optimizer_steps=400000, forwards=401204,
              encoder_forwards=32, feature_samples=4000, formal_runs=1, implementation_revisions=3,
              preparation_runs=0, communications=0, client_scans=0, class_gradient_requests=0,
              extra_encoded_positions=0, searches=0, attempts=0, retries=0, logical_copy_bytes=128*1024**2,
              gpu_allocated_bytes=6*1024**3, windows_peak_working_set_bytes=6*1024**3,
              cpu_tensor_proxy_bytes=2*1024**3, phase_seconds={}, per_run={})


def encode(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)+"\n").encode()


def sha(raw): return hashlib.sha256(raw).hexdigest()
def git(*args): return subprocess.check_output(["git", *args], cwd=ROOT).decode().strip()


def module(name, path, context=None):
    spec = importlib.util.spec_from_file_location(name, ROOT/path)
    value = importlib.util.module_from_spec(spec)
    if context is not None: value.RECOVERY_CONTEXT = context
    spec.loader.exec_module(value)
    return value


def preparation_history():
    # Closed, accepted preparation is inherited exactly once, separately from the new-stage cap.
    return dict(closed_preparation=True, commit=PREP_COMMIT,
                ledger_path="artifacts/direction_a/phaseP_preparation_v3/run_record.json",
                reported_seconds=73.50838789984118, upper_seconds=74.91717449986027, bytes=11988355,
                scan_lower_bound=5892, scan_upper_bound=6020, revisions=9, launches=3, restarts=1,
                old_preparation_criterion_6="FAIL", unknown_history_retained=True)


def run_once(context, namespace_factory=None):
    """Real and injected synthetic production share the accepted lifecycle."""
    from direction_a.probe_startup import execute_attempt, RecoveryBudget
    namespace = {}
    def factory():
        namespace.update(namespace_factory(context) if namespace_factory else
                         dict(LIMITS=LIMITS, main=lambda b: experiment(context, b)))
        context["limits"] = namespace["LIMITS"]
        budget = RecoveryBudget(context)
        for name,value in context.get("precheck_resource_peaks",{}).items():
            budget.resources[name]=max(value,budget.resources[name])
        if context.get("synthetic_head_forwards"):
            budget.consume("forwards", context["synthetic_head_forwards"])
        return budget
    def work(budget): namespace["main"](budget)
    def archive(budget):
        if namespace.get("archive_callback"): namespace["archive_callback"](budget)
    return execute_attempt(context, factory, work, archive)


def registration(fingerprints):
    refs = [f"A-backbone-{ds}-s{seed}-r{r:04d}-v1" for ds, seed in
            [("CIFAR10", 2026101321), ("CIFAR100", 2026101322)] for r in (40, 80)]
    return dict(run_id=RUN_ID, baseline_commit=BASE, protocol_commit=git("rev-parse", "HEAD"),
                protocol_path="docs/DIRECTION_A_P_ADJUDICATION_v5.md",
                protocol_sha256=sha((ROOT/"docs/DIRECTION_A_P_ADJUDICATION_v5.md").read_bytes()),
                G1_2_commit=G12_COMMIT, preparation_commit=PREP_COMMIT, references=refs,
                source_fingerprints=fingerprints,
                actual_command=[r"E:\anaconda3\python.exe", "-B", "scripts/run_direction_a_probe_formal.py", "--run"],
                train=dict(samples={"CIFAR10":11165,"CIFAR100":9754}, d=128, dtype="float32", order="sorted global indices", reencoded=0),
                validation=dict(samples_per_point=1000, class_counts={"CIFAR10":100,"CIFAR100":10},
                                order="sorted sealed 0.2 indices", batch=128, mode="eval/no_grad", test_reads=0),
                probe=dict(heads=400, heads_per_point=100, steps=1000, objective_steps=[0,100,500,1000],
                           initialization="complete C by 128 float32 weight and C bias zero",
                           loss="per-class mean CE averaged equally over complete C",
                           optimizer=dict(name="Adam", lr=.01, betas=[.9,.999], eps=1e-8, weight_decay=0)),
                train_permutations=dict(seeds=list(range(2026101501,2026101600)), global_frequency_preserving=True, paired_snapshots=True),
                validation_permutations=dict(repeats=9999, seeds={"CIFAR10":2026101701,"CIFAR100":2026101702},
                                            algorithm="dataset-local default_rng, globally permute all labels, fixed predictions, shared snapshots",
                                            statistic="integer tail correct count", ties="greater than or equal", p="(1+b)/10000", p_adj="min(1,4*p)"),
                bootstrap=dict(seed=20261016, repeats=2000, order="replicate outer/class ascending; sorted class positions",
                               sampling="classwise replacement, paired snapshots/original/real", fixed_denominators=True,
                               quantile_method="linear", R_delta_95=[.025,.975], delta_decision=[.0125,.9875]),
                scientific_thresholds=dict(CIFAR10=dict(tau_percent=30.1,delta_pp=5.6), CIFAR100=dict(tau_percent=7.9,delta_pp=5.9)),
                estimates=dict(fitting_seconds=2090.6519772480947, fitting_safety_factor=1.8,
                               remaining_nonfit_seconds=160, terminal_reserve_seconds=120, terminal_reserve_bytes=8*1024**2,
                               remaining_write_bytes=60*1024**2,
                               basis="accepted 24-head fixed-step measurement, linear full-train size extrapolation; no additional fits"),
                preparation=preparation_history(), limits=LIMITS,
                inference_assumptions="fixed predictions exchangeable with labels conditional on counts; independent validation sampling; no validation-based fitting or selection",
                disclosure="backbone validation previously reported; r40/r80 preregistered, all four delivered; bootstrap approximate validation-sampling coverage, not training repeats")


def check():
    import torch
    from direction_a.backbone_preparation import windows_memory
    if (OUT/"startup_record.json").exists() or (OUT/"run_record.json").exists():
        raise FileExistsError("existing attempt; checks cannot permit a real-input retry")
    prior = json.loads((OUT/"check_cost.json").read_bytes()) if (OUT/"check_cost.json").exists() else None
    invocation = 1 if prior is None else prior["CPU_suites"]+1
    if invocation > 3: raise RuntimeError("three revisions / CPU suites exhausted")
    OUT.mkdir(parents=True, exist_ok=True)
    attempt = OUT/"attempts"/f"check{invocation}"
    attempt.mkdir(parents=True, exist_ok=False)
    counts = dict(write_bytes=0, scans=0)
    events = []
    forbidden = []
    read, write = Path.read_bytes, Path.write_bytes
    peak = 0
    def tracked_read(path):
        nonlocal peak
        name = path.resolve().as_posix()
        if any(x in name for x in ("/RAW_DATA/", "/checkpoints/", "/phaseG1_2_", "/phase0_2_v1/tasks/")):
            forbidden.append(name); raise AssertionError("synthetic check real input intercepted")
        raw = read(path); counts["scans"]+=1; peak=max(peak,len(raw)); return raw
    def tracked_write(path, raw):
        nonlocal peak
        p = path.resolve()
        if not (p == OUT or OUT in p.parents): raise AssertionError("synthetic writes must stay in formal directory")
        if counts["write_bytes"]+len(raw) > 8*1024**2: raise RuntimeError("check write envelope exceeded")
        counts["write_bytes"]+=len(raw); peak=max(peak,len(raw)); return write(path,raw)
    def deny(name):
        def blocked(*a, **k): forbidden.append(name); raise AssertionError(name+" forbidden during CPU selfchecks")
        return blocked
    class Results(unittest.TestResult):
        def __init__(self): super().__init__(); self.cases=[]
        def addSuccess(self,t): super().addSuccess(t); self.cases.append(dict(case=t.id(),status="PASS"))
        def addError(self,t,e): super().addError(t,e); self.cases.append(dict(case=t.id(),status="FAIL",error=self._exc_info_to_string(e,t)))
        def addFailure(self,t,e): super().addFailure(t,e); self.cases.append(dict(case=t.id(),status="FAIL",error=self._exc_info_to_string(e,t)))
    result = Results()
    with patch.object(Path,"read_bytes",tracked_read), patch.object(Path,"write_bytes",tracked_write):
        fingerprints = {}
        syntax = []
        for name in SOURCES:
            raw = (ROOT/name).read_bytes(); fingerprints[name]=sha(raw)
            try: compile(raw,name,"exec"); syntax.append(dict(path=name,sha256=sha(raw),status="PASS"))
            except SyntaxError: syntax.append(dict(path=name,status="FAIL",error=traceback.format_exc()))
            if prior is None or prior["fingerprints"].get(name) != sha(raw):
                events.append(dict(path=name,bytes=len(raw),sha256=sha(raw),revision=invocation))
            if name in SOURCES[:4]:
                (attempt/Path(name).name).write_bytes(raw)
        syntax_ok=all(s["status"]=="PASS" for s in syntax)
        with patch.object(torch,"load",deny("torch.load")), patch.object(torch.cuda,"init",deny("CUDA init")), patch.object(torch.cuda,"_lazy_init",deny("CUDA lazy init")), patch.object(torch.Tensor,"cuda",deny("tensor CUDA")), patch.object(torch.Tensor,"backward",deny("backward")), patch.object(torch.optim.Adam,"step",deny("optimizer")):
            checks=module("formal_tests", "tests/test_direction_a_probe_formal.py")
            if syntax_ok: checks.suite().run(result)
        passed=syntax_ok and result.wasSuccessful() and result.testsRun>0 and not forbidden and not torch.cuda.is_initialized()
        syntax_record=dict(status="PASS" if syntax_ok else "FAIL", invocation=invocation, files=syntax)
        selfchecks=dict(status="PASS" if passed else "FAIL", CPU_suites=invocation, cases=result.cases,
                        tests_run=result.testsRun, actual_command=[sys.executable,"-B","scripts/run_direction_a_probe_formal.py","--check"],
                        isolation=dict(forbidden_attempts=forbidden,real_input_reads=0,CUDA_initialized=torch.cuda.is_initialized(),backwards=0,optimizer_steps=0,production_run_once_injected=True),
                        synthetic_arithmetic=dict(head_forwards=checks.SYNTHETIC_FORWARDS,statistical_scans=checks.SYNTHETIC_SCANS))
        for name,value in [("syntax_check.json",syntax_record),("selfchecks.json",selfchecks)]:
            (attempt/name).write_bytes(encode(value)); (OUT/name).write_bytes(encode(value))
        (OUT/"preregistration.json").write_bytes(encode(registration(fingerprints)))
        cost=dict(status="PASS" if passed else "FAIL", CPU_suites=invocation, syntax_checks=invocation,
                  implementation_revisions=invocation, fingerprints=fingerprints,
                  program_seconds=(prior["program_seconds"] if prior else 0)+time.monotonic()-ENTRY_STARTED+.5,
                  shell_and_implementation_program_upper_seconds=90,
                  postrun_verification_program_reserve_seconds=10,
                  source_write_events=(prior["source_write_events"] if prior else [])+events,
                  counts=dict(write_bytes=(prior["counts"]["write_bytes"] if prior else 0)+counts["write_bytes"]+sum(e["bytes"] for e in events)+131072,
                              scans=(prior["counts"]["scans"] if prior else 0)+counts["scans"]+checks.SYNTHETIC_SCANS),
                  resources=dict(windows_peak_bytes=windows_memory()["peak_working_set_bytes"],cpu_proxy_bytes=8*peak+8*sum(e["bytes"] for e in events)),
                  synthetic_head_forwards=(prior["synthetic_head_forwards"] if prior else 0)+checks.SYNTHETIC_FORWARDS)
        before=cost["counts"]["write_bytes"]
        for _ in range(12): cost["counts"]["write_bytes"]=before+len(encode(cost))
        (OUT/"check_cost.json").write_bytes(encode(cost))
    print(json.dumps(dict(status=cost["status"],cases=result.testsRun,seconds=cost["program_seconds"],bytes=cost["counts"]["write_bytes"])))
    if not passed: print(json.dumps(result.cases,ensure_ascii=False))
    return 0 if passed else 1


def inherited_helpers(context):
    return module("accepted_probe_input", "scripts/prepare_direction_a_probe.py", context)


def write_json(path, value, budget):
    budget.write(path, encode(value), raw=True)


def save_prediction(path, prediction, ce, budget):
    import numpy as np
    stream=io.BytesIO(); np.savez_compressed(stream,argmax=prediction,true_label_CE=ce)
    raw=stream.getvalue(); budget.write(path,raw,raw=True); budget.scan()
    with np.load(path) as restored:
        if not np.array_equal(prediction,restored["argmax"]) or not np.array_equal(ce,restored["true_label_CE"]):
            raise RuntimeError("prediction readback mismatch")
    return dict(path=path.relative_to(ROOT).as_posix(),bytes=len(raw),sha256=sha(raw))


def validation_features(accepted, packet, train_indices, ds, C, budget, helper):
    import numpy as np
    import torch
    from direction_a.model import ResNet8Adapter, transform_images
    from direction_a.backbone_preparation import tensor_state_sha
    task=ROOT/accepted["binding"]["task_directory"]
    data=helper.read_json(task/"data.json",budget)
    info=helper.read_json(task/"info.json",budget)
    indices=np.sort(np.asarray(data["validation"],np.int64))
    if len(indices)!=1000 or len(np.unique(indices))!=1000 or np.intersect1d(indices,train_indices).size:
        raise RuntimeError("sealed original validation count/isolation mismatch")
    paths=[Path(p) for p in info["source_file_sha256"] if
           (Path(p).name.startswith("data_batch_") if ds=="CIFAR10" else Path(p).name=="train")]
    paths.sort(key=lambda p:p.name)
    images=np.empty((1000,3,32,32),dtype=np.uint8); labels=np.empty(1000,dtype=np.int64)
    offset=0; selected=0; source_records=[]
    # Only selected validation images are transformed/encoded. Official train containers are verified in full.
    for path in paths:
        budget.scan(); raw=path.read_bytes()
        if sha(raw)!=info["source_file_sha256"][str(path)]: raise RuntimeError("official train source hash mismatch")
        batch=pickle.loads(raw,encoding="bytes"); image_array=batch[b"data"]
        ys=np.asarray(batch[b"labels"] if ds=="CIFAR10" else batch[b"fine_labels"],np.int64)
        positions=np.flatnonzero((indices>=offset)&(indices<offset+len(ys)))
        local=indices[positions]-offset
        images[positions]=image_array[local].reshape(-1,3,32,32); labels[positions]=ys[local]
        selected+=len(positions); offset+=len(ys)
        budget.cpu_proxy(4*(len(raw)+image_array.nbytes+ys.nbytes)+256*1024**2)
        source_records.append(dict(path=str(path),sha256=sha(raw),selected_validation_images=len(positions)))
        del raw,batch,image_array,ys
    if selected!=1000 or np.bincount(labels,minlength=C).tolist()!=[1000//C]*C:
        raise RuntimeError("validation label universe / denominators mismatch")
    model=ResNet8Adapter(C); model.load_state_dict(packet["state_dict"]); model.freeze_reference(); model.cuda()
    before=tensor_state_sha(model.state_dict())
    tensor=transform_images(images,ds); pieces=[]; batches=[]
    with torch.no_grad():
        for start in range(0,1000,128):
            x=tensor[start:start+128].cuda()
            if model.training or torch.is_grad_enabled() or any(m.training for m in model.modules()):
                raise RuntimeError("encoder eval/no_grad isolation violated")
            budget.consume("encoder_forwards"); budget.consume("feature_samples",len(x))
            z=model.encode(x)
            if z.shape!=(len(x),128) or z.dtype!=torch.float32 or not bool(torch.isfinite(z).all()):
                raise RuntimeError("validation encoder dimension/nonfinite mismatch")
            pieces.append(z); batches.append(dict(start=start,count=len(x),eval=True,no_grad=True))
    result=torch.cat(pieces)
    after=tensor_state_sha(model.state_dict()); budget.scan()
    if before!=after or before!=accepted["state_before"] or any(p.grad is not None for p in model.parameters()):
        raise RuntimeError("backbone/original head/BN changed")
    del model,tensor,images; gc.collect()
    return result,labels,indices,dict(validation_sources=source_records,validation_samples=1000,
                                    validation_denominators=[1000//C]*C,validation_train_disjoint=True,
                                    encoder_batches=batches,state_before=before,state_after=after,
                                    test_images_read=0,new_train_encoding=0)


def experiment(context, budget):
    import numpy as np
    import torch
    import torch.nn.functional as F
    from direction_a import probe_formal as formal
    from direction_a.backbone_preparation import tensor_state_sha
    helper=inherited_helpers(context)
    budget.consume("formal_runs")
    context["real_input_started"]=True
    budget.progress=dict(real_input_started=True,actual_run_commit=git("rev-parse","HEAD"),actual_command=sys.argv)
    budget.save()
    prereg=json.loads((OUT/"preregistration.json").read_bytes())
    results=dict(run_id=RUN_ID,references=[],engineering_criteria={str(i):"FAIL" for i in range(1,8)},scientific_status="not_completed")
    results["engineering_criteria"]["1"]="PASS"
    inputs=dict(run_id=RUN_ID,status="partial",references=[])
    context["results"]=results
    try:
        budget.enter("input_qualification")
        for name in ("preregistration.json","reference_acceptance.json","measurements.json","artifact_hashes.json","run_record.json","decision.json"):
            helper.committed(helper.G12/name,G12_COMMIT,budget)
        index=helper.read_json(helper.G12/"artifact_hashes.json",budget)
        for name in ("preregistration.json","reference_acceptance.json","measurements.json","run_record.json","decision.json"):
            if helper.digest_file(helper.G12/name,budget)!=index["files"][name]: raise RuntimeError("G1.2 package hash mismatch")
        accepted=helper.read_json(helper.G12/"reference_acceptance.json",budget)["references"]
        measurements=helper.read_json(helper.G12/"measurements.json",budget)["references"]
        decision=helper.read_json(helper.G12/"decision.json",budget)
        if decision["fail_count"] or decision["blocked"]: raise RuntimeError("G1.2 not accepted")
        refs=[a["reference"] for a in accepted]
        if [r["reference_id"] for r in refs]!=prereg["references"]: raise RuntimeError("frozen four reference identities/order mismatch")
        prep=helper.read_json(ROOT/context["history"]["ledger_path"],budget)
        helper.committed(ROOT/context["history"]["ledger_path"],PREP_COMMIT,budget)
        if abs(prep["cumulative_conservative_elapsed_upper_seconds"]-context["history"]["upper_seconds"])>1e-6 or prep["cumulative_accountable_write_bytes"]!=context["history"]["bytes"]:
            raise RuntimeError("preparation inheritance differs from accepted ledger")
        context["history"]["historical_unknowns"]=prep["historical_failure"]["historical_unknowns"]
        source=helper.UPSTREAM/"preregistration.md"
        helper.committed(source,PREP_COMMIT,budget)
        input_provenance=dict(preselected_rounds_preregistration=dict(path=source.relative_to(ROOT).as_posix(),sha256=helper.digest_file(source,budget)),
                              prior_validation_reported=True,all_four_preselected_references_delivered=True,
                              selection_leakage_detected=False,selection_basis="original preregistration fixed r40/r80, accepted v5 adjudication; no point selection")
        inputs.update(provenance=input_provenance)
        if not torch.cuda.is_available(): raise RuntimeError("preregistered CUDA device unavailable")
        torch.set_num_threads(2); torch.use_deterministic_algorithms(True)
        torch.backends.cuda.matmul.allow_tf32=False; torch.backends.cudnn.allow_tf32=False
        torch.cuda.reset_peak_memory_stats()
        write_json(OUT/"environment.json",dict(actual_run_commit=git("rev-parse","HEAD"),actual_command=prereg["actual_command"],
                   python=sys.version,numpy=np.__version__,torch=torch.__version__,CUDA=torch.version.cuda,device=torch.cuda.get_device_name(),
                   libraries=dict(scipy=__import__("scipy").__version__),protocol_sha256=prereg["protocol_sha256"]),budget)
        estimate=prereg["estimates"]
        remaining=estimate["fitting_seconds"]*estimate["fitting_safety_factor"]+estimate["remaining_nonfit_seconds"]+estimate["terminal_reserve_seconds"]
        qualification=dict(remaining_operations_estimate_seconds=remaining,already_spent_seconds=time.monotonic()-budget.started,
                           remaining_write_estimate_bytes=estimate["remaining_write_bytes"]+estimate["terminal_reserve_bytes"],
                           already_written_bytes=budget.counts["evidence_bytes"])
        write_json(OUT/"prefit_budget.json",qualification,budget)
        if remaining+time.monotonic()-budget.started>=4380 or qualification["remaining_write_estimate_bytes"]+budget.counts["evidence_bytes"]>=LIMITS["evidence_bytes"]:
            raise RuntimeError("insufficient remaining fixed budget before fitting; no protocol truncation")
        budget.planned_references=prereg["references"]
        datasets={}; prediction_store={}
        for a in accepted:
            ref=a["reference"]; rid=ref["reference_id"]; ds=ref["dataset"]
            budget.enter(rid)
            point=next(p for p in measurements if p["reference_id"]==rid)
            packet,before=helper.frozen_checkpoint(ref,a,budget)
            z,y,indices,C,groups,original,check=helper.load_train(ref,point,a,index,budget)
            if len(y)!=prereg["train"]["samples"][ds] or groups!=a["binding"]["class_groups"] or sorted(sum(groups.values(),[]))!=list(range(C)):
                raise RuntimeError("full train / frozen exhaustive class groups mismatch")
            if not torch.equal(original["weight"],packet["state_dict"]["linear.weight"]) or not torch.equal(original["bias"],packet["state_dict"]["linear.bias"]):
                raise RuntimeError("original cached head differs from checkpoint")
            val,labels,val_indices,vcheck=validation_features(a,packet,indices,ds,C,budget,helper)
            mapping=dict(train_indices=indices.tolist(),train_labels=y.tolist(),validation_indices=val_indices.tolist(),validation_labels=labels.tolist(),
                         class_groups=groups,label_mapping=a["binding"]["label_mapping"],index_namespace="official_train",test_samples=0)
            if ds in datasets and datasets[ds]!=mapping: raise RuntimeError("same dataset two points label/index/group mismatch")
            if ds not in datasets:
                datasets[ds]=mapping; write_json(OUT/f"predictions/{ds}_mapping.json",mapping,budget)
            check.update(vcheck,train_frequencies=torch.bincount(y,minlength=C).tolist(),original_head_matches=True)
            inputs["references"].append(check); write_json(OUT/"input_checks.json",inputs,budget)
            train=z.cuda(); true=torch.as_tensor(labels,device="cuda"); del z
            with torch.no_grad():
                budget.consume("forwards")
                logits=F.linear(val,original["weight"].cuda(),original["bias"].cuda())
                original_metrics=formal.summarize(logits,true,groups,budget)
                original_prediction=logits.argmax(1).cpu().numpy().astype(np.int16)
                original_ce=F.cross_entropy(logits,true,reduction="none").cpu().numpy()
            original_locator=save_prediction(OUT/f"predictions/{rid}/original.npz",original_prediction,original_ce,budget)
            result=dict(reference_id=rid,dataset=ds,class_groups=groups,original_head=original_metrics,original_prediction=original_locator,
                        uniform_control=formal.uniform_control(C,[1000//C]*C,groups),heads=[],state_before=before)
            results["references"].append(result)
            real_prediction=None
            for seed in [None,*formal.TRAIN_SEEDS]:
                label=y.numpy() if seed is None else formal.permute_labels(y.numpy(),C,seed,budget)
                name="real" if seed is None else f"permuted_s{seed}"
                start=time.monotonic()
                fitted,objectives,metrics,pred,ce,diagnostic=formal.fit(train,torch.as_tensor(label,device="cuda"),val,true,C,groups,budget)
                metadata=dict(run_id=RUN_ID,reference_id=rid,seed=seed,label_kind="real" if seed is None else "permuted",steps=1000,
                              labels_sha256=sha(label.tobytes()),label_frequencies=np.bincount(label,minlength=C).tolist(),
                              objectives=objectives,optimizer=prereg["probe"]["optimizer"],C=C,d=128,zero_initialization=True,bias_included=True)
                locator=helper.save_head(OUT/f"heads/{rid}/{name}.pt",{**fitted,"metadata":metadata},budget)
                pred_locator=save_prediction(OUT/f"predictions/{rid}/{name}.npz",pred,ce,budget)
                result["heads"].append(dict(name=name,seed=seed,head=locator,prediction=pred_locator,objectives=objectives,
                                           metrics=metrics,optimization=diagnostic,fit_save_seconds=time.monotonic()-start,
                                           train_labels_sha256=metadata["labels_sha256"]))
                write_json(OUT/f"head_results/{rid}/{name}.json",result["heads"][-1],budget)
                if seed is None: real_prediction=pred.copy()
                budget.progress.update(completed_heads=budget.counts["fits"],reference=rid)
                if len(result["heads"])%10==0: budget.save(); print(json.dumps(budget.progress),flush=True)
            result["differences_pp"]=formal.differences(result["heads"][0]["metrics"],{"original":original_metrics,"uniform":result["uniform_control"],
                                                **{h["name"]:h["metrics"] for h in result["heads"][1:]}})
            R=result["heads"][0]["metrics"]["groups"]["tail"]["macro_recall_percent"]
            nulls=[h["metrics"]["groups"]["tail"]["macro_recall_percent"] for h in result["heads"][1:]]
            result["train_empirical_controls"]=formal.train_control(R,nulls)
            repeated,after=helper.frozen_checkpoint(ref,a,budget)
            if before!=after or tensor_state_sha(packet["state_dict"])!=before: raise RuntimeError("reference changed")
            result["state_after"]=after
            prediction_store[rid]=(original_prediction,real_prediction)
            budget.delivered_references.append(rid)
            # Per-point incremental fragments avoid repeatedly serializing 400 heads.
            write_json(OUT/f"point_results/{rid}.json",result,budget)
            del train,val,true,packet,repeated,fitted,logits; gc.collect(); torch.cuda.empty_cache()
        if any(budget.counts[k]!=n for k,n in dict(fits=400,backwards=400000,optimizer_steps=400000,encoder_forwards=32,feature_samples=4000).items()):
            raise RuntimeError("fixed operation totals incomplete")
        inputs["status"]="PASS"; write_json(OUT/"input_checks.json",inputs,budget)
        budget.enter("fixed_prediction_statistics")
        uncertainty=dict(run_id=RUN_ID,references={},interpretation="approximate validation sampling intervals; not training repeats or finite-sample exact coverage",
                         validation_permutation_assumptions=prereg["inference_assumptions"],prior_validation_disclosure=prereg["disclosure"])
        for ds,mapping in datasets.items():
            rows=[r for r in results["references"] if r["dataset"]==ds]
            labels=np.asarray(mapping["validation_labels"]); tail=mapping["class_groups"]["tail"]
            perm=formal.paired_permutation([prediction_store[r["reference_id"]][1] for r in rows],labels,tail,formal.VAL_SEEDS[ds],budget)
            boot=formal.paired_bootstrap([prediction_store[r["reference_id"]] for r in rows],labels,tail,budget)
            for row,p,b in zip(rows,perm,boot):
                uncertainty["references"][row["reference_id"]]=dict(validation_permutation=p,paired_bootstrap=b)
                row["science"]=formal.science(ds,row["heads"][0]["metrics"]["groups"]["tail"]["macro_recall_percent"],
                              row["original_head"]["groups"]["tail"]["macro_recall_percent"],row["train_empirical_controls"]["tail_scores_percent"],p,b,True)
                if row["science"]["calibration_space"]=="FAIL" and row["heads"][0]["optimization"]["final_segment_still_changing"]:
                    row["failure_interpretation"]="求解未稳定，失败原因未定；不据此断言表征无信息"
        results["engineering_criteria"]={str(i):"PASS" for i in range(1,8)}
        results["scientific_dataset_status"]={ds:"PASS" if all(r["science"]["calibration_space"]=="PASS" for r in results["references"] if r["dataset"]==ds) else "FAIL" for ds in datasets}
        results["scientific_status"]="PASS" if all(v=="PASS" for v in results["scientific_dataset_status"].values()) else "FAIL"
        write_json(OUT/"uncertainty.json",uncertainty,budget)
        budget.enter("archive")
    except Exception:
        results["blocked"]=traceback.format_exc(); raise
    finally:
        # Failure records remain partial, never fabricated or auto-retried.
        write_json(OUT/"results.json",results,budget)


def launch():
    cost=json.loads((OUT/"check_cost.json").read_bytes())
    if cost["status"]!="PASS": raise RuntimeError("CPU gate failed")
    if subprocess.run(["git","merge-base","--is-ancestor",BASE,"HEAD"],cwd=ROOT).returncode: raise RuntimeError("baseline is not ancestor")
    for name,fingerprint in cost["fingerprints"].items():
        if sha((ROOT/name).read_bytes())!=fingerprint: raise RuntimeError("source changed after checks")
        if git("hash-object",name)!=git("rev-parse",f"HEAD:{name}"): raise RuntimeError("source uncommitted before input")
    registered="artifacts/direction_a/phaseP_formal_v1/preregistration.json"
    if git("hash-object",registered)!=git("rev-parse",f"HEAD:{registered}"): raise RuntimeError("registration not committed")
    history=preparation_history()
    context=dict(output=OUT,run_id=RUN_ID,history=history,limits=LIMITS,
                 started=ENTRY_STARTED-cost["program_seconds"]-cost["shell_and_implementation_program_upper_seconds"]-cost["postrun_verification_program_reserve_seconds"],
                 preparation_initial_write_bytes=cost["counts"]["write_bytes"],preparation_initial_scans=cost["counts"]["scans"]+100,
                 source_write_events=cost["source_write_events"],implementation_revisions=cost["implementation_revisions"],
                 total_wall_seconds=4380+history["upper_seconds"],total_write_bytes=LIMITS["evidence_bytes"]+history["bytes"],
                 cumulative_scan_limit=500000+history["scan_upper_bound"],new_preparation_launches=0,new_failed_restarts=0,
                 cpu_proxy_upper_bytes=cost["resources"]["cpu_proxy_bytes"],cpu_proxy_basis="eight times tracked synthetic buffers; full input cache/official containers inventory envelope",
                 emergency_closure_bytes=1024**2,synthetic_head_forwards=cost["synthetic_head_forwards"],
                 precheck_resource_peaks=dict(windows_working_set_peak_bytes=cost["resources"]["windows_peak_bytes"],
                                             cpu_known_arrays_tensor_proxy_peak_bytes=cost["resources"]["cpu_proxy_bytes"]),
                 archive_repo_paths=True,archive_extra_paths=[ROOT/name for name in SOURCES])
    # Shared budget constructor records source/check counts before work begins.
    ledger=run_once(context)
    print(json.dumps(dict(status=ledger["status"],seconds=ledger["new_stage_elapsed_seconds"],counts=ledger["counts"],error=ledger["error"]),ensure_ascii=False))
    return 0 if ledger["status"]=="completed" else 1


def guarded_launch():
    """Gate failures before claim/input are separately sealed, never overwritten."""
    entries=list((OUT/"attempts").glob("startup*"))
    if len(entries)>=3: raise RuntimeError("entry attempts exhausted (three pre-input failures plus one real entry)")
    try:
        return launch()
    except Exception:
        if (OUT/"startup_record.json").exists() or (OUT/"run_record.json").exists():
            # Existing real-input attempt is immutable; failure inside lifecycle is already closed.
            raise
        error=traceback.format_exc()
        attempt=OUT/"attempts"/f"startup{len(entries)+1}"
        attempt.mkdir(parents=True,exist_ok=False)
        cost=json.loads((OUT/"check_cost.json").read_bytes())
        record=dict(status="failed_before_real_input",error=error,real_input_reads=0,
                    actual_command=[sys.executable,*sys.argv],attempt=len(entries)+1,
                    program_seconds=time.monotonic()-ENTRY_STARTED+.5,
                    source_write_bytes_preserved=cost["counts"]["write_bytes"],
                    no_automatic_retry=True)
        raw=encode(record); (attempt/"run_record.json").write_bytes(raw)
        idx=encode(dict(files={"run_record.json":dict(bytes=len(raw),sha256=sha(raw))}))
        (attempt/"artifact_hashes.json").write_bytes(idx)
        cost["counts"]["write_bytes"]+=len(raw)+len(idx)+131072
        cost["counts"]["scans"]+=3
        cost["program_seconds"]+=record["program_seconds"]
        raw=encode(cost); cost["counts"]["write_bytes"]+=len(raw)
        (OUT/"check_cost.json").write_bytes(encode(cost))
        print(error)
        return 1


def review(ledger,results):
    criteria=results.get("engineering_criteria",{str(i):"FAIL" for i in range(1,8)})
    if ledger["status"]!="completed":
        criteria["7"]="FAIL"
        for row in results.get("references",[]):
            if "science" in row:
                row["science"]["separability_conditions"]["engineering_qualification"]=False
                row["science"]["separability"]="FAIL"; row["science"]["calibration_space"]="FAIL"
    science=results.get("scientific_status","FAIL") if ledger["status"]=="completed" else "FAIL"
    fail=sum(v=="FAIL" for v in criteria.values())+int(science!="PASS")
    blocked=ledger["status"]!="completed"
    counts=ledger["counts"]; resources=ledger["resources"]
    lines=["# 交付单：P 正式可分性与校准空间验证","",f"- 对应任务单的基准 commit：{BASE}","- 本次交付 commit：见本提交","", "## 做了什么（≤5 条）",
           "- 正式入口/预登记先提交，复用已验收启动生命周期，CPU合成注入核验。",
           f"- 一次真实运行，完成 {counts.get('fits',0)}/400 头；固定1000步，无科学分数驱动重跑。",
           "- 双置乱、类配对bootstrap、逐点机械判据和封存索引独立报告。","", "## 产出文件",
           "- artifacts/direction_a/phaseP_formal_v1/：preregistration、syntax_check、selfchecks、input_checks、results、uncertainty、run_record、artifact_hashes。",
           "- 同目录 heads/、predictions/、point_results/：完整参数/目标检查点、argmax/真标签CE/映射、增量指标。","", "## 判据自评",
           "|判据编号|结果 PASS/FAIL|证据位置 / 关键数字|","|---|---|---|"]
    evidence={"1":"syntax_check.json / selfchecks.json；合成生产生命周期与数学对照",
              "2":f"input_checks.json；encoder {counts.get('encoder_forwards',0)}/32；验证 {counts.get('feature_samples',0)}/4000",
              "3":f"heads/；拟合 {counts.get('fits',0)}；backward/Adam {counts.get('backwards',0)}/{counts.get('optimizer_steps',0)}",
              "4":"results.json / predictions/；完整类/组分母、解析机会、99经验对照和CP区间",
              "5":"uncertainty.json；9999×4全验证标签配对置乱、整数≥及四点Bonferroni",
              "6":"uncertainty.json / results.json；2000×4类配对重采样、linear分位、固定目标诊断",
              "7":f"run_record.json / artifact_hashes.json；终态 {ledger['status']}；全部索引读回"}
    for k,v in criteria.items(): lines.append(f"|{k}|{v}|{evidence[k]}|")
    lines.append(f"|8|{science}|四点科学判据见下表及 results.json；FAIL是合法科学交付|")
    lines += ["", "|参考|尾R %|Δ pp|可分性|校准空间|", "|---|---:|---:|---|---|"]
    for row in results.get("references",[]):
        s=row.get("science")
        if s: lines.append(f"|{row['reference_id']}|{s['R_percent']:.6f}|{s['delta_pp']:.6f}|{s['separability']}|{s['calibration_space']}|")
        else: lines.append(f"|{row['reference_id']}|未完成|未完成|FAIL|FAIL|")
    lines += ["", "## 实际资源消耗",
              f"- 正式全部程序保守 {ledger['new_stage_elapsed_seconds']:.6f} 秒；累计写入 {counts['evidence_bytes']} B；统计/核验/归档扫描 {counts['scans']}。",
              f"- CUDA峰 {resources['gpu_allocated_peak_bytes']} B；Windows峰 {resources['windows_working_set_peak_bytes']} B；CPU代理峰 {resources['cpu_known_arrays_tensor_proxy_peak_bytes']} B。",
              f"- 准备一次继承74.9171745秒/11988355 B；P累计保守 {ledger['cumulative_conservative_elapsed_upper_seconds']:.6f}秒/{ledger['cumulative_accountable_write_bytes']} B；旧未知及旧判据6 FAIL保留。",
              f"- 自评 FAIL {fail} 条；完整性/资源资格与科学得分分开；区间仅为近似验证抽样。", "", "## 阻塞（没有写“无”）",
              ("- "+(ledger.get("error") or "终态资格未通过").splitlines()[-1]) if blocked else "无", "", "## 异议（没有写“无”）", "无", "", "## 需要审查者裁决的问题（≤3 条，没有写“无”）", "- 按v5裁决各点及全范围科学结果；G1.1暂缓任务接续。"]
    if len(lines)>80: raise RuntimeError("review exceeds 80 lines")
    return ("\n".join(lines)+"\n").encode(),fail,blocked


def seal():
    # Archive verification only. Never reruns input qualification, encoding, fits or statistics.
    from direction_a.backbone_preparation import windows_memory
    import torch
    ledger=json.loads((OUT/"run_record.json").read_bytes())
    if ledger.get("delivery_verification"): raise FileExistsError("delivery already sealed")
    results=json.loads((OUT/"results.json").read_bytes()) if (OUT/"results.json").exists() else {}
    index=json.loads((OUT/"artifact_hashes.json").read_bytes())
    error=None; scans=0
    try:
        for name,row in index["files"].items():
            raw=(ROOT/name).read_bytes(); scans+=1
            if len(raw)!=row["bytes"] or sha(raw)!=row["sha256"]: raise RuntimeError("archive readback mismatch: "+name)
    except Exception: error=traceback.format_exc()
    elapsed=time.monotonic()-ENTRY_STARTED+.5
    # A ten-second verification envelope was charged before launch, not added twice.
    if elapsed>10 or ledger["counts"]["scans"]+scans+5>500000: error=(error or "")+"seal verification reserve exceeded"
    if error: ledger.update(status="failed_no_retry",error=error)
    ledger["counts"]["scans"]+=scans+5
    ledger["cumulative_scan_known_lower_bound"]+=scans+5
    ledger["cumulative_scan_conservative_upper_bound"]+=scans+5
    ledger["resources"]["windows_working_set_peak_bytes"]=max(ledger["resources"]["windows_working_set_peak_bytes"],windows_memory()["peak_working_set_bytes"])
    ledger["delivery_verification"]=dict(program_seconds=elapsed,program_reserve_already_in_new_stage_seconds=10,
                                          checked_files=scans,source_commit=git("rev-parse","HEAD"),
                                          real_input_reads=0,experiment_runs_new=0,command=[sys.executable,"-B",__file__,"--seal"],
                                          source_coverage=SOURCES,index_readback="PASS" if error is None else "FAIL")
    records=index["files"]; review_path=ROOT/"docs/workflow/TO_REVIEWER.md"
    ledger_name="artifacts/direction_a/phaseP_formal_v1/run_record.json"
    marker_name="artifacts/direction_a/phaseP_formal_v1/startup_record.json"
    before=ledger["counts"]["evidence_bytes"]
    for _ in range(16):
        reviewer,fail,blocked=review(ledger,results)
        marker=json.loads((OUT/"startup_record.json").read_bytes()); marker.update(status=ledger["status"],error=ledger.get("error")); marker_raw=encode(marker)
        records["docs/workflow/TO_REVIEWER.md"]=dict(bytes=len(reviewer),sha256=sha(reviewer))
        records[marker_name]=dict(bytes=len(marker_raw),sha256=sha(marker_raw))
        records[ledger_name]=dict(bytes=len(encode(ledger)),sha256="0"*64)
        ledger["counts"]["evidence_bytes"]=before+len(reviewer)+len(encode(ledger))+len(encode(index))+len(marker_raw)
        ledger["cumulative_accountable_write_bytes"]=11988355+ledger["counts"]["evidence_bytes"]
    if ledger["counts"]["evidence_bytes"]>=LIMITS["evidence_bytes"]: raise RuntimeError("seal reserved write envelope exceeded")
    reviewer,fail,blocked=review(ledger,results)
    raw=encode(ledger); records[ledger_name]=dict(bytes=len(raw),sha256=sha(raw))
    review_path.write_bytes(reviewer); (OUT/"startup_record.json").write_bytes(marker_raw)
    (OUT/"run_record.json").write_bytes(raw); (OUT/"artifact_hashes.json").write_bytes(encode(index))
    print(json.dumps(dict(status=ledger["status"],FAIL=fail,blocked=blocked,verified_files=scans),ensure_ascii=False))
    return 0


if __name__=="__main__":
    if Path(sys.executable).resolve()!=Path(r"E:\anaconda3\python.exe").resolve(): raise RuntimeError("required project interpreter mismatch")
    if sys.argv[1:]==["--check"]: sys.exit(check())
    if sys.argv[1:]==["--run"]: sys.exit(guarded_launch())
    if sys.argv[1:]==["--seal"]: sys.exit(seal())
    raise RuntimeError("use --check, commit, --run once, then --seal")
