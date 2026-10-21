"""Offline synthetic fixtures. No real paper, network, agent or training is run."""
import json
import sys
import subprocess
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

PACKAGE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE / "tools"))
import pool


def eligible(pid="P0001"):
    d = json.loads((PACKAGE / "templates/paper_card.json").read_text(encoding="utf-8"))
    d.update(paper_id=pid, title="Synthetic fixture " + pid, year=2025, status="ACCEPTED",
             family_id="fixture-family-" + pid, pool_role="BACKGROUND",
             official_paper_url="https://example.invalid/" + pid, paper_version="fixture-final")
    d["links"]["code_url"] = "https://example.invalid/code/" + pid
    d["implementation"].update(core_code="YES", license="fixture-license", core_location="method.py:step",
                               code_version="fixture-commit", environment="fixture env", config="fixture config",
                               required_inputs="fixture inputs")
    d["evidence"] = [
        {"id": pid + ":E01", "source_kind": "paper", "source_url": d["official_paper_url"],
         "locator": "fixture p.4 Eq.2", "claim": "synthetic claim", "accessed_at": "fixture-time", "read_status": "DIRECT"},
        {"id": pid + ":E02", "source_kind": "code", "source_url": d["links"]["code_url"],
         "locator": "fixture-commit method.py:step / LICENSE", "claim": "synthetic code claim",
         "accessed_at": "fixture-time", "read_status": "DIRECT"},
    ]
    for name in pool.GATES:
        d["gates"][name] = {"result": "PASS", "reason": "synthetic structural fixture",
                            "evidence_ids": [pid + ":E01", pid + ":E02"]}
    for section in ("problem", "mechanism", "mechanism_interface", "comparisons"):
        for key, value in d[section].items():
            if isinstance(value, str):
                d[section][key] = "fixture " + key
    d["mechanism"]["limitations"] = ["fixture limitation"]
    d["resources"].update(small_scale_cycle="fixture cycle", preserves_mechanism_because="fixture rationale")
    d["reviews"] = {
        "reader": {"agent_id": "fixture-reader-" + pid, "receipt": "inbox/reader-" + pid + ".md"},
        "auditor": {"agent_id": "fixture-auditor-" + pid, "receipt": "inbox/auditor-" + pid + ".md",
                    "source_checked_ids": [pid + ":E01", pid + ":E02"], "blocking_issues": []}}
    d["decision"] = {"by": "fixture-auditor-" + pid, "date": "2026-10-21", "reason": "fixture only"}
    return d


def pair_fixture():
    d = json.loads((PACKAGE / "templates/pair_card.json").read_text(encoding="utf-8"))
    d.update(a_id="P0001", b_id="P0002", status="PAPER_COMPATIBLE")
    for key, value in list(d.items()):
        if value == "" and isinstance(value, str):
            d[key] = "fixture " + key
    d["decisive_controls"] = ["A", "B", "naive A+B", "remove term", "simple alternative"]
    d["remaining_proofs_and_qualifications"] = ["activation and actual independent gain not tested"]
    for i, name in enumerate(pool.CHECKS):
        d["checks"][name] = {"result": "SUPPORTED" if i < 4 else "PLAN_READY",
                             "reason": "fixture paper screen", "evidence_ids": ["P0001:E01", "P0002:E01"]}
    return d


class PoolTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        for name in ("records", "pairs", "inbox", "staging"):
            (self.root / name).mkdir()
        self.manifest = {"run_id": "SYNTHETIC-OFFLINE-TEST", "status": "RUNNING",
                         "pressure": "client_label_distribution_skew",
                         "usage": {"search_queries": 0, "fetch_calls": 0, "deep_read_papers": 2, "active_children_peak": 0}}
        self.write("staging/run.json", self.manifest)

    def tearDown(self):
        self.temp.cleanup()

    def write(self, name, d):
        (self.root / name).write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")

    def record(self, d):
        self.write("records/" + d["paper_id"] + ".json", d)
        for review in d.get("reviews", {}).values():
            if review.get("receipt"):
                (self.root / review["receipt"]).write_text("SYNTHETIC RECEIPT", encoding="utf-8")

    def test_empty_pool_requires_manifest_not_fake_search_completion(self):
        self.assertEqual(pool.publish(self.root), [])
        (self.root / "staging/run.json").unlink()
        self.assertTrue(pool.publish(self.root))

    def test_valid_record_can_publish_without_running_paper_code(self):
        self.record(eligible())
        self.assertEqual(pool.publish(self.root), [])
        self.assertTrue((self.root / "exports/cards/P0001.md").is_file())

    def test_openreview_different_query_ids_do_not_collide(self):
        a = "https://openreview.net/forum?id=AbCd&utm_source=x"
        b = "https://openreview.net/forum?id=EfGh"
        self.assertNotEqual(pool.canonical_url(a), pool.canonical_url(b))
        self.assertIn("id=AbCd", pool.canonical_url(a))

    def test_openreview_forum_and_pdf_same_id_are_duplicates(self):
        a, b = eligible(), eligible("P0002")
        a["official_paper_url"] = "https://openreview.net/forum?id=CaseSensitive"
        b["official_paper_url"] = "https://openreview.net/pdf?id=CaseSensitive"
        self.record(a)
        self.record(b)
        self.assertTrue(any("duplicate paper identity" in e for e in pool.load_pool(self.root)[2]))

    def test_distinct_openreview_ids_can_have_same_title(self):
        a, b = eligible(), eligible("P0002")
        b["title"] = a["title"]
        a["official_paper_url"] = "https://openreview.net/forum?id=DifferentA"
        b["official_paper_url"] = "https://openreview.net/forum?id=DifferentB"
        self.record(a)
        self.record(b)
        self.assertEqual(pool.load_pool(self.root)[2], [])

    def test_arxiv_versions_not_two_independent_papers(self):
        a, b = eligible(), eligible("P0002")
        a["links"]["arxiv_id"], b["links"]["arxiv_id"] = "2501.00001v1", "2501.00001v2"
        self.record(a)
        self.record(b)
        self.assertTrue(any("arxiv" in e for e in pool.load_pool(self.root)[2]))

    def test_unknown_identity_fields_do_not_merge_distinct_hold_records(self):
        for pid in ("P0001", "P0002"):
            d = eligible(pid)
            d.update(status="HOLD", official_paper_url="UNKNOWN")
            d["links"].update(doi="UNKNOWN", arxiv_id="UNKNOWN", openreview_url="UNKNOWN")
            self.record(d)
        self.assertEqual(pool.load_pool(self.root)[2], [])

    def test_hold_cannot_be_published_as_accepted(self):
        d = eligible()
        d["gates"]["G3_scale"]["result"] = "HOLD"
        self.record(d)
        self.assertTrue(pool.publish(self.root))
        self.assertFalse((self.root / "exports/accepted_papers.jsonl").exists())

    def test_metadata_cannot_substitute_for_direct_method_evidence(self):
        d = eligible()
        d["evidence"][0]["read_status"] = "METADATA"
        self.assertTrue(pool.validate_record(d))

    def test_unknown_interface_or_license_blocks_acceptance(self):
        for section, key in (("mechanism_interface", "time_version"), ("implementation", "license")):
            d = eligible()
            d[section][key] = "UNKNOWN"
            self.assertTrue(pool.validate_record(d))

    def test_local_measurement_cannot_be_fabricated_in_paper_stage(self):
        d = eligible()
        d["resources"]["measured"] = True
        self.assertTrue(pool.validate_record(d))

    def test_fake_admission_signer_or_same_agent_blocks(self):
        d = eligible()
        d["decision"]["by"] = "unrelated-agent"
        self.assertTrue(pool.validate_record(d))
        d = eligible()
        d["reviews"]["auditor"]["agent_id"] = d["reviews"]["reader"]["agent_id"]
        self.assertTrue(pool.validate_record(d))

    def test_missing_receipt_or_invalid_filename_blocks(self):
        self.record(eligible())
        (self.root / "inbox/auditor-P0001.md").unlink()
        self.assertTrue(pool.load_pool(self.root)[2])
        d = eligible()
        d["paper_id"] = "../elsewhere"
        self.assertTrue(pool.validate_record(d))

    def test_withdrawal_removes_only_derived_accepted_card(self):
        d = eligible()
        self.record(d)
        self.assertEqual(pool.publish(self.root), [])
        d["status"] = "HOLD"
        self.record(d)
        self.assertEqual(pool.publish(self.root), [])
        self.assertFalse((self.root / "exports/cards/P0001.md").exists())
        self.assertTrue((self.root / "records/P0001.json").exists())

    def test_paper_pair_has_pending_science_and_cannot_authorize_training(self):
        a, b = eligible(), eligible("P0002")
        self.record(a)
        self.record(b)
        d = pair_fixture()
        self.write("pairs/Q0001.json", d)
        self.assertEqual(pool.publish(self.root), [])
        d["training_authorized"] = True
        self.write("pairs/Q0001.json", d)
        self.assertTrue(pool.publish(self.root))

    def test_pair_cannot_use_self_same_family_or_false_scientific_pass(self):
        a, b = eligible(), eligible("P0002")
        sources = {e["id"]: e for d in (a, b) for e in d["evidence"]}
        for mutation in ("self", "family", "pass", "source"):
            aa, bb, d = deepcopy(a), deepcopy(b), pair_fixture()
            if mutation == "self": d["b_id"] = d["a_id"]
            if mutation == "family": bb["family_id"] = aa["family_id"]
            if mutation == "pass": d["checks"]["K5_controls"]["result"] = "PASS"
            if mutation == "source": d["checks"]["K1_reliable"]["evidence_ids"] = ["P9999:E01"]
            self.assertTrue(pool.validate_pair(d, {"P0001": aa, "P0002": bb}, sources))

    def test_duplicate_json_keys_and_budget_overrun_block(self):
        (self.root / "records/P0001.json").write_text('{"paper_id":"P0001","paper_id":"P0002"}', encoding="utf-8")
        self.assertTrue(pool.load_pool(self.root)[2])
        (self.root / "records/P0001.json").unlink()
        self.manifest["usage"]["fetch_calls"] = 61
        self.write("staging/run.json", self.manifest)
        self.assertTrue(pool.load_pool(self.root)[2])

    def test_cli_works_from_parent_workspace_with_explicit_run_root(self):
        self.record(eligible())
        result = subprocess.run([sys.executable, str(PACKAGE / "tools/pool.py"), "check",
                                 "--root", str(self.root)], cwd=PACKAGE.parent, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["structural_check"], "PASS")


if __name__ == "__main__":
    unittest.main()
