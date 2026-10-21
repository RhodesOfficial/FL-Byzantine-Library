"""Local structural checks and generated views; never searches or judges novelty."""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

GATES = ("G1_problem", "G2_code", "G3_scale", "G4_interface", "G5_baseline", "G6_mechanism")
CHECKS = ("K1_reliable", "K2_problem", "K3_interface", "K4_conditions",
          "K5_controls", "K6_prediction", "K7_resources", "K8_neighbors")
STATES = {"DISCOVERED", "VERIFIED", "READ", "CHALLENGED", "REVIEW_READY",
          "ACCEPTED", "HOLD", "REJECTED"}


def known(value):
    return isinstance(value, str) and value.strip().upper() not in {"", "UNKNOWN", "TODO", "TBD"}


def is_url(value):
    return isinstance(value, str) and urlsplit(value).scheme in {"http", "https"} and bool(urlsplit(value).netloc)


def canonical_url(value):
    """Retain identity-bearing query values and case-sensitive paths."""
    if not value:
        return ""
    p = urlsplit(str(value).strip())
    query = [(k, v) for k, v in parse_qsl(p.query, keep_blank_values=True)
             if not k.lower().startswith("utm_") and k.lower() not in {"fbclid", "gclid"}]
    return urlunsplit((p.scheme.lower(), p.netloc.lower().removeprefix("www."),
                       p.path.rstrip("/"), urlencode(sorted(query)), ""))


def identity_keys(d):
    links = d.get("links", {})
    stable_identity = False
    doi = str(links.get("doi", "")).strip().lower()
    doi = re.sub(r"^(https?://(dx\.)?doi\.org/|doi:\s*)", "", doi)
    if not known(doi):
        doi = ""
    if doi:
        stable_identity = True
        yield "doi", doi
    arxiv = str(links.get("arxiv_id", "")).strip()
    arxiv = re.sub(r"^https?://arxiv\.org/(abs|pdf)/", "", arxiv).removesuffix(".pdf")
    arxiv = re.sub(r"v\d+$", "", arxiv)
    if not known(arxiv):
        arxiv = ""
    if arxiv:
        stable_identity = True
        yield "arxiv", arxiv
    for url in (d.get("official_paper_url", ""), links.get("openreview_url", "")):
        if is_url(url):
            p = urlsplit(url)
            query = dict(parse_qsl(p.query))
            if p.netloc.lower().removeprefix("www.") == "openreview.net" and query.get("id"):
                stable_identity = True
                yield "openreview", query["id"]
            else:
                yield "url", canonical_url(url)
    # A title is a fallback identity, not proof that two distinct DOI works coincide.
    if not stable_identity:
        title = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "", str(d.get("title", "")).casefold())
        if title:
            yield "title_year", (title, d.get("year"))


def unique_object(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise ValueError(f"duplicate JSON key: {key}")
        out[key] = value
    return out


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"), object_pairs_hook=unique_object)


def evidence_map(d, owner, errors):
    result = {}
    for item in d.get("evidence", []):
        if not isinstance(item, dict):
            errors.append(f"{owner}: evidence must be an object")
            continue
        eid = item.get("id", "")
        if not isinstance(eid, str) or not eid.startswith(owner + ":") or eid in result:
            errors.append(f"{owner}: invalid/duplicate evidence id {eid}")
        if not is_url(item.get("source_url")) or not known(item.get("locator")) or not known(item.get("claim")):
            errors.append(f"{owner}: evidence {eid} lacks URL/locator/claim")
        if item.get("read_status") not in {"DIRECT", "METADATA", "UNAVAILABLE"}:
            errors.append(f"{owner}: evidence {eid} invalid read_status")
        if item.get("source_kind") not in {"paper", "code", "venue", "review", "recognition"}:
            errors.append(f"{owner}: evidence {eid} invalid source_kind")
        if not known(item.get("accessed_at")):
            errors.append(f"{owner}: evidence {eid} missing access time")
        result[eid] = item
    return result


def check_refs(ids, sources, errors, label, required=False):
    if not isinstance(ids, list):
        errors.append(f"{label}: evidence_ids must be an array")
        return []
    if required and not ids:
        errors.append(f"{label}: missing evidence_ids")
    found = []
    for eid in ids:
        if eid not in sources:
            errors.append(f"{label}: nonexistent evidence {eid}")
        elif sources[eid].get("read_status") != "DIRECT":
            errors.append(f"{label}: nondirect evidence {eid} cannot support a pass")
        else:
            found.append(sources[eid])
    return found


def validate_record(d, root=None):
    errors = []
    pid = d.get("paper_id", "")
    if not re.fullmatch(r"P\d{4}", str(pid)):
        errors.append("invalid paper_id; expected P0001 style")
    if d.get("status") not in STATES:
        errors.append(f"{pid}: invalid status")
    if not known(d.get("title")):
        errors.append(f"{pid}: missing title")
    if d.get("research_status") != "UNQUALIFIED":
        errors.append(f"{pid}: research_status must remain UNQUALIFIED")
    sources = evidence_map(d, pid, errors)
    if d.get("status") != "ACCEPTED":
        return errors
    if not is_url(d.get("official_paper_url")) or not known(d.get("paper_version")):
        errors.append(f"{pid}: missing official paper/version")
    if not known(d.get("family_id")):
        errors.append(f"{pid}: missing family_id")
    if d.get("pool_role") not in {"CORE_ORAL", "BACKGROUND", "ORAL_UNVERIFIED"}:
        errors.append(f"{pid}: invalid pool role")
    if d.get("pool_role") == "CORE_ORAL":
        presentation = d.get("presentation", {})
        if presentation.get("category") != "ORAL" or not is_url(presentation.get("official_source_url")):
            errors.append(f"{pid}: CORE_ORAL needs official oral identity")
        check_refs([presentation.get("evidence_id", "")], sources, errors, pid + ":oral", True)
    gate_sources = {}
    for name in GATES:
        gate = d.get("gates", {}).get(name, {})
        if gate.get("result") != "PASS" or not known(gate.get("reason")):
            errors.append(f"{pid}: {name} must have PASS and reason")
        gate_sources[name] = check_refs(gate.get("evidence_ids", []), sources, errors, pid + ":" + name, True)
    for name in ("G1_problem", "G6_mechanism"):
        if not any(x.get("source_kind") == "paper" for x in gate_sources[name]):
            errors.append(f"{pid}: {name} needs directly read paper evidence")
    if not any(x.get("source_kind") == "code" for x in gate_sources["G2_code"]):
        errors.append(f"{pid}: G2_code needs directly read code evidence")
    implementation = d.get("implementation", {})
    if implementation.get("core_code") != "YES" or not is_url(d.get("links", {}).get("code_url")):
        errors.append(f"{pid}: core code not established")
    for key in ("license", "core_location", "code_version", "environment", "config", "required_inputs"):
        if not known(implementation.get(key)):
            errors.append(f"{pid}: implementation.{key} unknown")
    for section, keys in {
        "problem": ("condition", "failure_step", "why"),
        "mechanism": ("summary", "formula_or_algorithm_location", "input", "output", "state", "training_information", "test_information"),
        "mechanism_interface": ("target", "vector_space", "time_version", "persistent_state", "available_information", "observable_failure_condition"),
        "comparisons": ("strongest_simple_baseline", "most_explanatory_ablation", "extra_budget_warning"),
        "resources": ("small_scale_cycle", "preserves_mechanism_because"),
    }.items():
        for key in keys:
            if not known(d.get(section, {}).get(key)):
                errors.append(f"{pid}: {section}.{key} missing/unknown")
    if not d.get("mechanism", {}).get("limitations"):
        errors.append(f"{pid}: missing limitation")
    resources = d.get("resources", {})
    if resources.get("assessment_basis") != "PAPER_ESTIMATE" or resources.get("measured") is not False:
        errors.append(f"{pid}: G3 is a paper estimate, not a local measurement")
    reviews = d.get("reviews", {})
    reader, auditor = reviews.get("reader", {}), reviews.get("auditor", {})
    if not known(reader.get("agent_id")) or not known(auditor.get("agent_id")) or reader.get("agent_id") == auditor.get("agent_id"):
        errors.append(f"{pid}: Reader and Auditor need different actual agent IDs")
    for role, review in (("reader", reader), ("auditor", auditor)):
        receipt = review.get("receipt", "")
        if not known(receipt):
            errors.append(f"{pid}: missing {role} receipt")
        elif root:
            path = (root / receipt).resolve()
            if not path.is_relative_to(root.resolve()) or not path.is_file():
                errors.append(f"{pid}: missing/outside-root {role} receipt")
    checked = check_refs(auditor.get("source_checked_ids", []), sources, errors, pid + ":audit", True)
    if not {"paper", "code"}.issubset({x.get("source_kind") for x in checked}):
        errors.append(f"{pid}: Auditor must check paper and code sources")
    if auditor.get("blocking_issues"):
        errors.append(f"{pid}: unresolved audit issues")
    decision = d.get("decision", {})
    if decision.get("by") != auditor.get("agent_id") or not known(decision.get("date")) or not known(decision.get("reason")):
        errors.append(f"{pid}: admission must be attributed to actual Auditor")
    return errors


def validate_pair(d, accepted, all_sources):
    errors = []
    qid = d.get("pair_id", "")
    if not re.fullmatch(r"Q\d{4}", str(qid)):
        errors.append("invalid pair_id")
    a, b = d.get("a_id"), d.get("b_id")
    if a == b or a not in accepted or b not in accepted:
        errors.append(f"{qid}: pair requires two distinct ACCEPTED papers")
    elif accepted[a].get("family_id") == accepted[b].get("family_id"):
        errors.append(f"{qid}: same-family pairing requires upstream dedup, not admission")
    if d.get("scientific_status") != "UNQUALIFIED" or d.get("training_authorized") is not False:
        errors.append(f"{qid}: paper screening cannot authorize research/training")
    if d.get("status") not in {"PAPER_COMPATIBLE", "HOLD", "REJECTED"}:
        errors.append(f"{qid}: invalid pair status")
    own = evidence_map(d, qid, errors)
    permitted = {eid: item for eid, item in all_sources.items()
                 if eid.startswith(str(a) + ":") or eid.startswith(str(b) + ":")}
    permitted.update(own)
    for i, name in enumerate(CHECKS):
        gate = d.get("checks", {}).get(name, {})
        expected = "SUPPORTED" if i < 4 else "PLAN_READY"
        if gate.get("result") not in {expected, "UNKNOWN", "CONFLICT", "NOT_EXAMINED"}:
            errors.append(f"{qid}: {name} has an invalid paper-stage result")
        if d.get("status") == "PAPER_COMPATIBLE":
            if gate.get("result") != expected or not known(gate.get("reason")):
                errors.append(f"{qid}: {name} requires {expected}, not scientific PASS")
            check_refs(gate.get("evidence_ids", []), permitted, errors, qid + ":" + name, True)
    if d.get("status") == "PAPER_COMPATIBLE":
        for key in ("common_problem", "a_limitation_b_mechanism", "interface_compatibility",
                    "nonempty_paper_conditions", "framework_to_derive", "possible_nontriviality",
                    "falsifiable_prediction", "failure_condition", "cost_plan_and_unknowns", "closest_work_check"):
            if not known(d.get(key)):
                errors.append(f"{qid}: missing {key}")
        if len(d.get("decisive_controls", [])) < 4 or not d.get("remaining_proofs_and_qualifications"):
            errors.append(f"{qid}: need decisive controls and explicit pending qualifications")
    return errors


def load_pool(root):
    records, pairs, errors = [], [], []
    if not root.is_dir():
        return records, pairs, ["run root does not exist"]
    for dirname, target, id_key in (("records", records, "paper_id"), ("pairs", pairs, "pair_id")):
        for path in sorted((root / dirname).glob("*.json")):
            try:
                d = read_json(path)
                if not isinstance(d, dict):
                    raise ValueError("record must be a JSON object")
                if path.stem != d.get(id_key):
                    errors.append(f"{path.name}: filename and ID differ")
                target.append(d)
            except (ValueError, OSError) as ex:
                errors.append(f"{path.name}: {ex}")
    seen = {}
    sources = {}
    for d in records:
        errors.extend(validate_record(d, root))
        for key in set(identity_keys(d)) | {("paper_id", d.get("paper_id"))}:
            if key in seen:
                errors.append(f"duplicate paper identity {key}: {seen[key]} / {d.get('paper_id')}")
            seen[key] = d.get("paper_id")
        sources.update({x["id"]: x for x in d.get("evidence", []) if isinstance(x, dict) and x.get("id")})
    accepted = {d["paper_id"]: d for d in records if d.get("status") == "ACCEPTED"}
    seen_pairs = set()
    for d in pairs:
        errors.extend(validate_pair(d, accepted, sources))
        key = (d.get("a_id"), d.get("b_id"))
        if key in seen_pairs:
            errors.append("duplicate directed pair")
        seen_pairs.add(key)
    if len(pairs) > 2:
        errors.append("pilot detailed-pair cap exceeded")
    manifest = root / "staging" / "run.json"
    if not manifest.is_file():
        errors.append("missing staging/run.json; empty pool is not a completed search")
    else:
        try:
            run = read_json(manifest)
            if not known(run.get("run_id")) or run.get("status") not in {
                    "NOT_STARTED", "PREFLIGHT", "RUNNING", "COMPLETE", "COMPLETE_NO_PAIR",
                    "PARTIAL", "CAPABILITY_BLOCKED"}:
                errors.append("run identity/status missing or invalid")
            if run.get("pressure") != "client_label_distribution_skew":
                errors.append("run pressure differs from frozen pilot")
            for key, limit in {"search_queries": 24, "fetch_calls": 60, "deep_read_papers": 6, "active_children_peak": 3}.items():
                n = run.get("usage", {}).get(key)
                if type(n) is not int or not 0 <= n <= limit:
                    errors.append(f"run usage.{key} missing/unknown/out of cap")
            if run.get("usage", {}).get("deep_read_papers", 0) < len(accepted):
                errors.append("accepted count exceeds reported deep reads")
        except (ValueError, OSError) as ex:
            errors.append(f"run.json: {ex}")
    return records, pairs, errors


def publish(root):
    records, pairs, errors = load_pool(root)
    if errors:
        return errors
    exp = root / "exports"
    exp.mkdir(parents=True, exist_ok=True)
    accepted = [d for d in records if d.get("status") == "ACCEPTED"]
    compatible = [d for d in pairs if d.get("status") == "PAPER_COMPATIBLE"]
    for dirname, prefix, items, key in (("cards", "P", accepted, "paper_id"), ("pairs", "Q", pairs, "pair_id")):
        folder = exp / dirname
        folder.mkdir(exist_ok=True)
        # Only these generated filename patterns belong to this publisher.
        for old in folder.glob(prefix + "*.md"):
            if re.fullmatch(prefix + r"\d{4}\.md", old.name):
                old.unlink()
        for d in items:
            (folder / (d[key] + ".md")).write_text(
                "# " + d[key] + " — " + d.get("title", d.get("status", "")) + "\n\n"
                + "纸面记录；研究资格未建立。\n\n~~~json\n"
                + json.dumps(d, ensure_ascii=False, indent=2) + "\n~~~\n", encoding="utf-8")
    for name, items in (("accepted_papers", accepted), ("paper_compatible_pairs", compatible)):
        (exp / (name + ".jsonl")).write_text("".join(json.dumps(d, ensure_ascii=False) + "\n" for d in items), encoding="utf-8")
    with (exp / "accepted_papers.csv").open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["paper_id", "title", "venue", "year", "pool_role", "official_paper_url"])
        writer.writeheader()
        writer.writerows({key: d.get(key, "") for key in writer.fieldnames} for d in accepted)
    index = ["# 已准入单篇索引（纸面资格）", ""]
    index += [f"- [{d['paper_id']}: {d['title']}](cards/{d['paper_id']}.md)" for d in accepted]
    (exp / "accepted_index.md").write_text("\n".join(index) + "\n", encoding="utf-8")
    handoff = ["# 交强推理模型：UNQUALIFIED", "", "没有训练或程序资格授权。先查必要条件和最强简单对照，再接现有研究工作流。", "",
               f"纸面入池 {len(accepted)} 篇；纸面可继续推理配对 {len(compatible)} 对。零配对不代表领域没有创新点。", "",
               "## 卡片入口", ""]
    handoff += [f"- [{d['pair_id']}](pairs/{d['pair_id']}.md)：{d['a_id']} → {d['b_id']}" for d in compatible]
    handoff += ["", "另读 accepted_index.md、../staging/run.json、../staging/pair_screen.json；HOLD/REJECTED 原因留 records/pairs。", "",
                "总控须在 pool_summary.md 写实际检索覆盖、分簇、未决字段、费用未知及要定向追的页；此入口不宣告创新成立。"]
    (exp / "TO_REASONING.md").write_text("\n".join(handoff) + "\n", encoding="utf-8")
    return []


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["check", "publish", "report"])
    parser.add_argument("--root", type=Path, required=True, help="one run directory, not the workspace/package root")
    a = parser.parse_args()
    root = a.root.resolve()
    try:
        records, pairs, errors = load_pool(root)
        if a.command == "publish" and not errors:
            errors = publish(root)
        print(json.dumps({"structural_check": "FAIL" if errors else "PASS", "records": len(records),
                          "accepted": sum(d.get("status") == "ACCEPTED" for d in records),
                          "pairs": len(pairs), "errors": errors,
                          "meaning": "structure only; not source truth, research qualification or search completion"},
                         ensure_ascii=False, indent=2))
        return int(bool(errors))
    except (TypeError, KeyError, AttributeError, ValueError) as ex:
        print("Malformed record: " + str(ex), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
