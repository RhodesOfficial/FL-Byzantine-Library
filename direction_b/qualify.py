"""B-R01: finite vector qualification only; stdlib, no learning/model imports."""
import argparse
import copy
import ctypes
import hashlib
import itertools
import json
import math
import os
from pathlib import Path
import struct
import time

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts/direction_b/r01_v1"
PROTOCOL = ROOT / "docs/projects/direction_b/PROTOCOL.md"
FAMILIES = ("coherent", "heterogeneous_cache", "mixed_increment",
            "common_increment", "unrelated_increment", "stationary")
ALGORITHMS = ("C", "R", "CACHE", "ABS", "MSG", "ID", "U")
REP = ("heterogeneous_cache", "top1", "fresh")
START = time.perf_counter()
CAP_BYTES = 4 * 1024 * 1024
CAP_MEMORY = 256 * 1024 * 1024
ZERO = [0.0, 0.0]


def canonical(x):
    return json.dumps(x, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
                      allow_nan=False).encode("utf-8")


def digest(x):
    return hashlib.sha256(canonical(x)).hexdigest()


def save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_bytes(canonical(value) + b"\n")
    os.replace(tmp, path)
    assert json.loads(path.read_bytes()) == value


def read(path):
    return json.loads(Path(path).read_bytes())


def add(a, b):
    return [x + y for x, y in zip(a, b)]


def sub(a, b):
    return [x - y for x, y in zip(a, b)]


def scale(a, w):
    return [x * w for x in a]


def mean(vectors):
    assert vectors
    return [sum(v[k] for v in vectors) / len(vectors) for k in range(2)]


def norm2(a):
    return sum(x * x for x in a)


def close(a, b):
    return norm2(sub(a, b)) <= 1e-20 * max(1, norm2(b))


def frame(meta, values=()):
    head = canonical(meta)
    return struct.pack("<I", len(head)) + head + bytes(values)


def unpack(packet):
    n, = struct.unpack("<I", packet[:4])
    return json.loads(packet[4:4+n]), packet[4+n:]


def compress(v, codec):
    if codec == "dense":
        return list(v)
    assert codec == "top1"
    k = max(range(2), key=lambda j: (abs(v[j]), -j))
    q = list(ZERO)
    q[k] = v[k]
    return q


def update_packet(cid, seq, old, target, source, codec):
    q = compress(sub(target, old), codec)
    residual = math.sqrt(norm2(sub(target, add(old, q))))
    pairs = [(k, v) for k, v in enumerate(q) if v != 0]
    meta = dict(kind="update", protocol=1, epoch=1, cid=cid, seq=seq,
                base=seq-1, source=source, dimension=2, codec=codec,
                residual_norm=residual, nnz=len(pairs))
    body = (struct.pack("<2d", *q) if codec == "dense" else
            b"".join(struct.pack("<Id", k, v) for k, v in pairs))
    return frame(meta, body)


def decode_update(packet):
    meta, body = unpack(packet)
    assert meta["kind"] == "update" and meta["dimension"] == 2
    if meta["codec"] == "dense":
        q = list(struct.unpack("<2d", body))
    else:
        assert meta["codec"] == "top1" and len(body) == 12 * meta["nnz"]
        q = list(ZERO)
        for j in range(meta["nnz"]):
            k, v = struct.unpack("<Id", body[12*j:12*j+12])
            assert k < 2
            q[k] = v
    assert all(math.isfinite(v) for v in q)
    return meta, q


def cost_add(s, purpose, direction, packet):
    # Purpose buckets are disjoint. Direction/payload columns are cross-tabs.
    meta, body = unpack(packet)
    row = s["wire"].setdefault(purpose, dict(bytes=0, frames=0, up_bytes=0,
                                            down_bytes=0, payload_bytes=0,
                                            residual_metadata_bytes=0))
    row["bytes"] += len(packet)
    row["frames"] += 1
    row[direction + "_bytes"] += len(packet)
    row["payload_bytes"] += len(body)
    if "residual_norm" in meta:
        smaller = dict(meta)
        del smaller["residual_norm"]
        row["residual_metadata_bytes"] += len(canonical(meta))-len(canonical(smaller))


def empty_state(n=6):
    node = dict(h=list(ZERO), seq=0, source=0, residual=0.0,
                known=False, last_q=list(ZERO), last_digest=None)
    return dict(server=[copy.deepcopy(node) for _ in range(n)],
                client=[dict(h=list(ZERO), seq=0, pending=None) for _ in range(n)],
                frozen=None, buffer=[], consumed=False, output=None,
                version=2, wire={}, accepted=0, duplicates=0)


def reference(s, cid, source, purpose="downlink"):
    # An encoded two-dimensional reference stands in for a full model download.
    packet = frame(dict(kind="reference", protocol=1, epoch=1, cid=cid,
                        source=source, dimension=2), struct.pack("<2d", 0, 0))
    cost_add(s, purpose, "down", packet)


def prepare(s, cid, target, source, codec):
    c = s["client"][cid]
    assert c["pending"] is None
    packet = update_packet(cid, c["seq"]+1, c["h"], target, source, codec)
    m, q = decode_update(packet)
    c["pending"] = dict(packet=packet.hex(), h=add(c["h"], q), seq=m["seq"])
    return packet


def receive(s, packet, initialization=False):
    m, q = decode_update(packet)
    node = s["server"][m["cid"]]
    if m["epoch"] != 1 or m["protocol"] != 1:
        raise ValueError("epoch/protocol")
    packet_digest = hashlib.sha256(packet).hexdigest()
    ack = frame(dict(kind="ack", epoch=1, cid=m["cid"], seq=m["seq"]))
    if m["seq"] == node["seq"]:
        if node["last_digest"] != packet_digest:
            raise ValueError("duplicate content mismatch")
        s["duplicates"] += 1
        return ack
    if m["base"] != node["seq"] or m["seq"] != node["seq"]+1:
        raise ValueError("wrong base/sequence")
    if not initialization:
        if s["frozen"] is None or s["consumed"]:
            raise ValueError("buffer closed")
        if any(v["cid"] == m["cid"] for v in s["buffer"]):
            raise ValueError("second contribution")
    new_h = add(node["h"], q)
    node.update(h=new_h, seq=m["seq"], source=m["source"],
                residual=m["residual_norm"], known=True, last_q=q,
                last_digest=packet_digest)
    if not initialization:
        s["buffer"].append(dict(cid=m["cid"], q=q, h=new_h, source=m["source"]))
        s["accepted"] += 1
    return ack


def acknowledge(s, ack):
    m, body = unpack(ack)
    assert not body and m["kind"] == "ack" and m["epoch"] == 1
    c = s["client"][m["cid"]]
    if c["pending"] is None:
        assert c["seq"] == m["seq"]
        return
    p = c["pending"]
    assert p["seq"] == m["seq"]
    c.update(h=p["h"], seq=p["seq"], pending=None)
    assert c["h"] == s["server"][m["cid"]]["h"]


def exchange(s, cid, target, source, codec, initialization=False):
    purpose = "initialization" if initialization else "uplink"
    reference(s, cid, source, "initialization" if initialization else "downlink")
    packet = prepare(s, cid, target, source, codec)
    cost_add(s, purpose, "up", packet)
    ack = receive(s, packet, initialization)
    cost_add(s, "initialization" if initialization else "control", "down", ack)
    acknowledge(s, ack)


def open_buffer(s):
    assert all(c["pending"] is None for c in s["client"])
    s.update(frozen=copy.deepcopy(s["server"]), buffer=[], consumed=False, output=None)


def warm(hs):
    s = empty_state(len(hs))
    for cid, h in enumerate(hs):
        exchange(s, cid, sub(h, [.125, 0]), 0, "dense", True)
        exchange(s, cid, h, 0, "top1", True)
    assert all(x["last_q"] == [.125, 0] for x in s["server"])
    open_buffer(s)
    return s


def groups(vectors):
    result = []
    for cid, v in enumerate(vectors):
        def similar(other):
            if norm2(v) <= 1e-24 or norm2(other) <= 1e-24:
                return False
            cosine = sum(x*y for x, y in zip(v, other))/math.sqrt(norm2(v)*norm2(other))
            return cosine >= .8
        for group in result:
            if all(similar(vectors[j]) for j in group):
                group.append(cid)
                break
        else:
            result.append([cid])
    return result


def gate(s):
    for x in s["frozen"]:
        if not x["known"]:
            return "unknown_cache"
        length = math.sqrt(norm2(x["h"]))
        if length <= 1e-12:
            return "zero_cache"
        if x["residual"]/max(length, 1e-12) > .25:
            return "cache_residual"
        if s["version"]-x["source"] > 2:
            return "cache_age"
    return None


def stratify(partition, values, n):
    if any(not any(cid in values for cid in group) for group in partition):
        return None
    result = list(ZERO)
    for group in partition:
        sample = [values[cid] for cid in group if cid in values]
        result = add(result, scale(mean(sample), len(group)/n))
    return result


def aggregate(s):
    # No target or unreturned current vectors are passed into this function.
    old = s["frozen"]
    h = mean([x["h"] for x in old])
    increments = {x["cid"]: x["q"] for x in s["buffer"]}
    absolute = {x["cid"]: x["h"] for x in s["buffer"]}
    assert increments
    c = add(h, mean(list(increments.values())))
    partition = groups([x["h"] for x in old])
    reason = gate(s)
    residual = stratify(partition, increments, len(old))
    if reason is None and residual is None:
        reason = "missing_group"
    r = c if reason else add(h, residual)
    abs_value = c if reason else stratify(partition, absolute, len(old))
    outputs = dict(C=c, R=r, CACHE=mean([x["h"] for x in s["server"]]), ABS=abs_value)
    for name, p in (("MSG", groups([x["last_q"] for x in old])),
                    ("ID", [list(range(len(old)//2)), list(range(len(old)//2, len(old)))])):
        value = stratify(p, increments, len(old))
        outputs[name] = c if gate(s) or value is None else add(h, value)
    return dict(values=outputs, groups=partition, reason=reason,
                r_eligible=reason is None, r_nonzero=not close(c, r))


def consume(s):
    if not s["consumed"]:
        s["output"] = aggregate(s)
        s["consumed"] = True
    return copy.deepcopy(s["output"])


def fixture(family, codec, age):
    hs, increments, sources, visible = [], [], [], []
    unrelated = [[.5, 0], [-.5, 0], [0, .5], [0, -.5], [-.5, 0], [.5, 0]]
    for cid in range(6):
        a = cid % 2 == 0
        magnitude = 1 if family == "coherent" else [.75, 1, 1.25][cid//2]
        hs.append([magnitude, 0] if a else [0, magnitude])
        if family in ("coherent", "heterogeneous_cache"):
            inc = [.5, 0] if a else [0, .5]
        elif family == "mixed_increment":
            inc = [.5, .125] if a else [.125, .5]
        elif family == "common_increment":
            inc = [.25, .25]
        elif family == "unrelated_increment":
            inc = unrelated[cid]
        else:
            assert family == "stationary"
            inc = list(ZERO)
        increments.append(inc)
        aged = age == "aged" and not a
        sources.append(0 if aged else 2)
        visible.append(scale(inc, .5 if aged else 1))
    return dict(family=family, codec=codec, age=age, hs=hs,
                increments=increments, visible=visible, sources=sources)


def u_diagnostic(s, observed):
    # Uncompressed source increments for returning clients only; never feeds R.
    h = mean([x["h"] for x in s["frozen"]])
    c = add(h, mean(list(observed.values())))
    v = stratify(groups([x["h"] for x in s["frozen"]]), observed, len(s["frozen"]))
    return c if gate(s) or v is None else add(h, v)


def row_for(f, selected):
    s = warm(f["hs"])
    for cid in selected:
        exchange(s, cid, add(f["hs"][cid], f["visible"][cid]),
                 f["sources"][cid], f["codec"])
    output = consume(s)
    output["values"]["U"] = u_diagnostic(s, {cid: f["visible"][cid] for cid in selected})
    # Truth is evaluated only after the algorithm finishes.
    truth = mean([add(h, inc) for h, inc in zip(f["hs"], f["increments"])])
    output.update(selected=list(selected), truth=truth,
                  errors={k: norm2(sub(v, truth)) for k, v in output["values"].items()},
                  wire=s["wire"], accepted=s["accepted"])
    assert s["accepted"] == len(selected)
    assert all(c["h"] == v["h"] and c["seq"] == v["seq"]
               for c, v in zip(s["client"], s["server"]))
    return output


def cell_summary(rows):
    result = dict(buffers=len(rows), eligible=sum(x["r_eligible"] for x in rows),
                  nonzero=sum(x["r_nonzero"] for x in rows), algorithms={})
    result["fallback_counts"] = {}
    for row in rows:
        if row["reason"]:
            result["fallback_counts"][row["reason"]] = result["fallback_counts"].get(row["reason"], 0)+1
    for name in ALGORITHMS:
        all_errors = [r["errors"][name] for r in rows]
        eligible = [r["errors"][name] for r in rows if r["r_eligible"]]
        result["algorithms"][name] = dict(
            mean=sum(all_errors)/len(all_errors), maximum=max(all_errors),
            bias=mean([sub(r["values"][name], r["truth"]) for r in rows]),
            eligible_mean=None if not eligible else sum(eligible)/len(eligible),
            eligible_maximum=None if not eligible else max(eligible),
            eligible_bias=None if not eligible else mean([
                sub(r["values"][name], r["truth"]) for r in rows if r["r_eligible"]]))
    return result


def cell_key(spec):
    return "__".join(spec)


def run_cell(spec):
    f = fixture(*spec)
    rows = [row_for(f, selected) for selected in itertools.combinations(range(6), 3)]
    result = dict(spec=f, input_sha256=digest(f), rows=rows, summary=cell_summary(rows))
    save(OUT / "cells" / (cell_key(spec)+".json"), result)
    guard()
    return result


def science_state(s):
    return {k: s[k] for k in ("server", "client", "frozen", "buffer", "consumed", "output", "accepted")}


def recovery_stages():
    f = fixture(*REP)
    s = warm(f["hs"])
    selected = [0, 1, 2]
    reference(s, 0, 2)
    packet = prepare(s, 0, add(f["hs"][0], f["visible"][0]), 2, "top1")
    stages = [copy.deepcopy(s)]
    cost_add(s, "uplink", "up", packet)
    ack = receive(s, packet)
    stages.append(copy.deepcopy(s))
    cost_add(s, "control", "down", ack)
    stages.append(copy.deepcopy(s))
    acknowledge(s, ack)
    stages.append(copy.deepcopy(s))
    for cid in selected[1:]:
        exchange(s, cid, add(f["hs"][cid], f["visible"][cid]), 2, "top1")
    stages.append(copy.deepcopy(s))
    consume(s)
    stages.append(copy.deepcopy(s))
    return f, selected, stages


def finish_recovery(s, f, selected):
    if s["consumed"]:
        return consume(s)
    for cid in selected:
        if s["client"][cid]["pending"] is not None:
            packet = bytes.fromhex(s["client"][cid]["pending"]["packet"])
            cost_add(s, "recovery", "up", packet)
            ack = receive(s, packet)
            cost_add(s, "recovery", "down", ack)
            acknowledge(s, ack)
        elif not any(x["cid"] == cid for x in s["buffer"]):
            exchange(s, cid, add(f["hs"][cid], f["visible"][cid]), 2, "top1")
    return consume(s)


def controls():
    result = {}
    s = empty_state(1)
    trace = []
    for target, q_expected in (([3, 1], [3, 0]), ([3, 2], [0, 2]), ([2, 2], [-1, 0])):
        open_buffer(s)
        exchange(s, 0, target, 0, "top1")
        node = s["server"][0]
        assert node["last_q"] == q_expected
        assert close(sub(target, node["h"]), [0, 1] if not trace else ZERO)
        trace.append(dict(h=node["h"], q=node["last_q"],
                          residual=sub(target, node["h"])))
    result["top1_tracking"] = dict(trace=trace, wire=s["wire"], passed=True)
    cases = {}
    # Exact original warm-cache counterexample, with N=4.
    s = warm([[1, 0], [1, 0], [0, 1], [0, 1]])
    for cid in [0, 1, 2]:
        exchange(s, cid, s["client"][cid]["h"], 2, "top1")
    o = consume(s)
    assert o["values"]["R"] == [.5, .5] and not o["r_nonzero"]
    cases["old_accurate_cache"] = dict(output=o, wire=s["wire"], passed=True)
    s = empty_state(4)
    open_buffer(s)
    for cid, target in enumerate([[1, 0], [1, 0], [0, 1]]):
        exchange(s, cid, target, 2, "top1")
    o = consume(s)
    assert o["reason"] == "unknown_cache" and o["values"]["R"] == o["values"]["C"]
    cases["cold"] = dict(output=o, wire=s["wire"], passed=True)
    f = fixture(*REP)
    for name, selected in (("missing_group", [0, 2, 4]), ("full_participation", list(range(6))),
                            ("cache_age", [0, 1, 2]), ("cache_residual", [0, 1, 2])):
        s = warm(f["hs"])
        if name == "cache_age":
            s["frozen"][5]["source"] = -1
        if name == "cache_residual":
            s["frozen"][5]["residual"] = .5
        for cid in selected:
            exchange(s, cid, add(f["hs"][cid], f["visible"][cid]), 2, "top1")
        o = consume(s)
        assert close(o["values"]["R"], o["values"]["C"])
        if name != "full_participation":
            assert o["reason"] == name
        else:
            assert close(o["values"]["R"], mean([x["h"] for x in s["server"]]))
        cases[name] = dict(output=o, wire=s["wire"], passed=True)
    s = warm(f["hs"])
    for cid in [0, 2, 1]:
        exchange(s, cid, add(f["hs"][cid], [0, 1] if cid == 1 else ZERO), 2, "top1")
    o = consume(s)
    truth = mean(f["hs"])  # Unreturned B increments are -0.5, -0.5.
    err = {k: norm2(sub(v, truth)) for k, v in o["values"].items()}
    assert abs(err["R"]-.25) < 1e-12 and abs(err["C"]-1/9) < 1e-12
    cases["within_group_selection_bias"] = dict(output=o, errors=err,
                                               truth=truth, wire=s["wire"], passed=True)
    s = warm(f["hs"])
    exchange(s, 0, add(f["hs"][0], [.5, 0]), 2, "top1")
    original = copy.deepcopy(science_state(s))
    bad = update_packet(1, 4, f["hs"][1], add(f["hs"][1], [0, .5]), 2, "top1")
    cost_add(s, "uplink", "up", bad)
    try:
        receive(s, bad)
        raise AssertionError("invalid base accepted")
    except ValueError as error:
        assert str(error) == "wrong base/sequence"
        reject = frame(dict(kind="reject", cid=1, expected_base=s["server"][1]["seq"]))
        cost_add(s, "control", "down", reject)
    assert science_state(s) == original
    cases["wrong_base_rejected"] = dict(wire=s["wire"], passed=True)
    result["cases"] = cases
    f, selected, stages = recovery_stages()
    recovered = []
    for index, stage in enumerate(stages):
        save(OUT / "recovery" / ("boundary_"+str(index)+".json"), stage)
        restored = read(OUT / "recovery" / ("boundary_"+str(index)+".json"))
        before_wire = copy.deepcopy(restored["wire"])
        finish_recovery(restored, f, selected)
        assert science_state(restored) == science_state(stages[-1])
        before = copy.deepcopy(science_state(restored))
        consume(restored)
        assert science_state(restored) == before
        recovered.append(dict(boundary=index, equivalent=True,
                              duplicates=restored["duplicates"],
                              wire_before=before_wire, wire_after=restored["wire"]))
    result["serialization_boundaries"] = recovered
    # The second snapshot is resumed by a separate Python invocation.
    save(OUT / "recovery" / "cross_process_pending.json",
         dict(state=stages[1], fixture=f, selected=selected,
              expected=science_state(stages[-1]), identity=identity()))
    result["cross_process"] = "pending"
    return result


def identity():
    return dict(code_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                wrapper_sha256=hashlib.sha256((Path(__file__).parent / "invoke.ps1").read_bytes()).hexdigest(),
                protocol_sha256=hashlib.sha256(PROTOCOL.read_bytes()).hexdigest(),
                matrix_sha256=digest([fixture(f, c, a) for f, c, a in matrix()]))


def matrix():
    return itertools.product(FAMILIES, ("dense", "top1"), ("fresh", "aged"))


def peak_memory():
    # Windows OS peak resident working set; not Job bytes or Python allocations.
    from ctypes import wintypes
    class Counters(ctypes.Structure):
        _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD)] + [
            (name, ctypes.c_size_t) for name in (
                "PeakWorkingSetSize", "WorkingSetSize", "QuotaPeakPagedPoolUsage",
                "QuotaPagedPoolUsage", "QuotaPeakNonPagedPoolUsage", "QuotaNonPagedPoolUsage",
                "PagefileUsage", "PeakPagefileUsage")]
    counters = Counters()
    counters.cb = ctypes.sizeof(counters)
    get_process = ctypes.windll.kernel32.GetCurrentProcess
    get_process.restype = wintypes.HANDLE
    get_info = ctypes.windll.psapi.GetProcessMemoryInfo
    get_info.argtypes = [wintypes.HANDLE, ctypes.POINTER(Counters), wintypes.DWORD]
    if not get_info(get_process(), ctypes.byref(counters), counters.cb):
        raise ctypes.WinError()
    return counters.PeakWorkingSetSize


def file_bytes():
    return sum(p.stat().st_size for p in OUT.rglob("*") if p.is_file())


def guard():
    assert time.perf_counter()-START < 120, "process time cap"
    assert peak_memory() <= CAP_MEMORY, "peak working-set cap"
    assert file_bytes() <= CAP_BYTES, "artifact byte cap"


def summarize():
    cells = {cell_key(spec): read(OUT / "cells" / (cell_key(spec)+".json")) for spec in matrix()}
    controls_result = read(OUT / "controls.json")
    recovery = read(OUT / "recovery" / "cross_process_result.json")
    checks = dict(cross_process=recovery["equivalent"],
                  boundaries=all(r["equivalent"] for r in controls_result["serialization_boundaries"]),
                  controls=all(r["passed"] for r in controls_result["cases"].values()))
    for codec in ("dense", "top1"):
        a = cells[cell_key(("heterogeneous_cache", codec, "fresh"))]["summary"]["algorithms"]
        checks["heterogeneous_"+codec] = a["R"]["mean"]+1e-10 < min(a["C"]["mean"], a["ABS"]["mean"])
    a = cells[cell_key(("mixed_increment", "top1", "fresh"))]["summary"]["algorithms"]
    checks["mixed_top1"] = a["R"]["mean"]+1e-10 < a["C"]["mean"]
    checks["stationary"] = all(
        cell["summary"]["algorithms"]["R"]["maximum"] < 1e-10
        for cell in cells.values() if cell["spec"]["family"] == "stationary")
    wire = {}
    for cell in cells.values():
        for row in cell["rows"]:
            for purpose, counts in row["wire"].items():
                assert counts["bytes"] == counts["up_bytes"]+counts["down_bytes"]
                assert counts["bytes"] >= counts["payload_bytes"]+counts["residual_metadata_bytes"]
                dest = wire.setdefault(purpose, {k: 0 for k in counts})
                for k, v in counts.items():
                    dest[k] += v
    result = dict(identity=identity(), cells={k: v["summary"] for k, v in cells.items()},
                  checks=checks, passed=all(checks.values()), buffers=480, accepted_returns=1440,
                  matrix_wire=wire,
                  wire_scope="24 independent cells x 20 independently initialized counterfactual buffers; "
                             "not a temporal deployment trace. Controls/recovery are separate.",
                  model_training=False)
    save(OUT / "summary.json", result)
    return result


def run(phase):
    OUT.mkdir(parents=True, exist_ok=True)
    if phase == "representative":
        assert not (OUT / "manifest.json").exists(), "do not overwrite representative"
        save(OUT / "manifest.json", dict(identity=identity(), representative=list(REP),
                                        specs=[list(x) for x in matrix()], inputs=[
                                            fixture(*x) for x in matrix()]))
        save(OUT / "controls.json", controls())
        run_cell(REP)
    elif phase == "resume":
        assert not (OUT / "recovery" / "cross_process_result.json").exists()
        pending = read(OUT / "recovery" / "cross_process_pending.json")
        assert pending["identity"] == identity()
        s = pending["state"]
        before_wire = copy.deepcopy(s["wire"])
        finish_recovery(s, pending["fixture"], pending["selected"])
        equivalent = science_state(s) == pending["expected"]
        assert equivalent
        save(OUT / "recovery" / "cross_process_result.json",
             dict(equivalent=equivalent, duplicates=s["duplicates"],
                  wire_before=before_wire, wire_after=s["wire"], state=s,
                  identity=identity()))
    elif phase == "formal":
        assert (ROOT / "docs/projects/direction_b/RESOURCE_PLAN.md").exists()
        assert read(OUT / "manifest.json")["identity"] == identity()
        assert read(OUT / "recovery" / "cross_process_result.json")["equivalent"]
        rep = read(OUT / "cells" / (cell_key(REP)+".json"))
        assert rep["input_sha256"] == digest(fixture(*REP))
        for spec in matrix():
            if spec == REP:
                continue
            assert not (OUT / "cells" / (cell_key(spec)+".json")).exists()
            run_cell(spec)
        result = summarize()
        print(json.dumps(dict(passed=result["passed"], checks=result["checks"]), ensure_ascii=False))
    else:
        raise ValueError(phase)
    guard()
    save(OUT / ("process_"+phase+".json"),
         dict(phase=phase, internal_seconds=time.perf_counter()-START,
              peak_working_set_bytes=peak_memory(), artifact_bytes_before_this_file=file_bytes(),
              identity=identity()))
    guard()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=("representative", "resume", "formal"))
    args = parser.parse_args()
    run(args.phase)
