"""Read-only result checks plus charged, one-shot final archive bookkeeping."""

import time
START = time.monotonic()

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.dont_write_bytecode = True

from direction_a.backbone_preparation import encode, sha, windows_memory

OUTPUT = ROOT / "artifacts/direction_a/phaseG1_2_full_v1"


def read(name):
    return json.loads((OUTPUT/name).read_bytes())


def main():
    if Path(sys.executable).resolve() != Path(r"E:\anaconda3\python.exe").resolve():
        raise RuntimeError("required interpreter mismatch")
    if (OUTPUT/"archive_verification.json").exists():
        raise RuntimeError("archive audit already recorded; no repeated audit cost reset")
    ledger_raw = (OUTPUT/"run_record.json").read_bytes()
    ledger, index = json.loads(ledger_raw), read("artifact_hashes.json")
    actual_names = {p.relative_to(OUTPUT).as_posix() for p in OUTPUT.rglob("*") if p.is_file()}
    assert actual_names == set(index["files"]) | {"artifact_hashes.json"}
    for name, digest in index["files"].items():
        with (OUTPUT/name).open("rb") as stream:
            assert hashlib.file_digest(stream, "sha256").hexdigest() == digest, name
    prereg, measured, decision = read("preregistration.json"), read("measurements.json"), read("decision.json")
    for name, digest in {**prereg["source_fingerprints"], **prereg["contracts"]}.items():
        assert sha((ROOT/name).read_bytes()) == digest, name
    acceptance = read("reference_acceptance.json")
    for name, digest in acceptance["verified_inputs"].items():
        assert sha((ROOT/name).read_bytes()) == digest, name
    refs = measured["references"]
    assert len(refs) == 4 and len(acceptance["references"]) == 4
    assert measured["message_count"] == 80 and measured["main_record_count"] == 1356 and measured["G_c_count"] == 220
    main_errors, target_errors, aux_errors, weight_errors = [], [], [], []
    locators = []
    for p in refs:
        assert [c["client_id"] for c in p["clients"]] == list(range(20))
        samples, positives, C = (11165, 85, 10) if p["dataset"] == "CIFAR10" else (9754, 593, 100)
        assert p["sample_count"] == samples and p["main_records"] == positives
        assert p["state_before"] == p["state_after"] == p["state_repeated_read"]
        assert p["no_parameter_grad_or_update"]
        assert len(p["provenance"]) == C
        for client in p["clients"]:
            assert client["sample_count"] == client["feature_statistics"]["sample_denominator"]
            assert client["positive_class_count"] + len(client["missing_class_ids"]) == C
            locators.append(client["message"]["path"])
        for row in p["provenance"].values():
            assert sum(r["n_ic"] for r in row["sources"]) == row["N_c"]
            weight_errors.append(row["weight_sum_error"])
        for row in p["comparisons"]:
            assert row["epsilon"] == 2e-6 and row["normalized_Linf"] <= 2e-6
            destination = main_errors if row["comparison"].endswith("/main") else (
                target_errors if row["comparison"].endswith("/Gc") or row["comparison"] == "equal_class_G" else aux_errors)
            destination.append(row["normalized_Linf"])
    assert len(set(locators)) == 80 and len(main_errors) == 1356 and len(target_errors) == 224
    assert len(aux_errors) == 480
    assert decision["fail_count"] == 0 and not decision["blocked"]
    elapsed = time.monotonic()-START
    resources = windows_memory()
    audit = {"checks": "all archive byte hashes/file set, frozen inputs, source identity, unique message locators, all counts/states/tolerances",
             "status": "PASS", "pre_audit_ledger_sha256": sha(ledger_raw),
             "audit_script_sha256": sha(Path(__file__).read_bytes()), "verified_files": len(index["files"]),
             "main_comparisons": len(main_errors), "auxiliary_comparisons": len(aux_errors),
             "target_comparisons_including_G": len(target_errors), "maximum_main_normalized_Linf": max(main_errors),
             "maximum_auxiliary_normalized_Linf": max(aux_errors), "maximum_target_normalized_Linf": max(target_errors),
             "maximum_weight_sum_error": max(weight_errors), "audit_seconds": elapsed,
             "audit_windows_working_set_peak_bytes": resources["peak_working_set_bytes"],
             "additional_encoding_forwards_gradients": 0, "audit_known_array_proxy_upper_bytes": 8*1024**2}
    audit_raw = encode(audit)
    ledger["measurement_program_seconds"] = ledger["elapsed_seconds"]
    ledger["post_run_archive_audit_seconds"] = elapsed
    ledger["elapsed_seconds"] += elapsed
    ledger["phase_seconds"]["post_run_archive_audit"] = elapsed
    ledger["counts"]["scans"] += len(index["files"]) + 4
    ledger["resources"]["windows_working_set_peak_bytes"] = max(
        ledger["resources"]["windows_working_set_peak_bytes"], resources["peak_working_set_bytes"])
    files = dict(index["files"])
    files["archive_verification.json"] = sha(audit_raw)
    index["files"] = files
    # Hashes have fixed encoded lengths, so final ledger + index rewrites can be
    # charged without a circular digest or an uncharged final ledger mutation.
    prior_bytes = ledger["counts"]["evidence_bytes"]
    for _ in range(8):
        ledger["counts"]["evidence_bytes"] = prior_bytes + len(audit_raw) + len(encode(ledger)) + len(encode(index))
    assert ledger["elapsed_seconds"] < ledger["limits"]["wall_seconds"]
    for field, value in ledger["counts"].items():
        assert value <= ledger["limits"][field], field
    assert ledger["resources"]["windows_working_set_peak_bytes"] < ledger["limits"]["windows_peak_working_set_bytes"]
    ledger_bytes = encode(ledger)
    index["files"]["run_record.json"] = sha(ledger_bytes)
    (OUTPUT/"archive_verification.json").write_bytes(audit_raw)
    (OUTPUT/"run_record.json").write_bytes(ledger_bytes)
    (OUTPUT/"artifact_hashes.json").write_bytes(encode(index))
    print(json.dumps({"audit": audit, "cumulative_seconds": ledger["elapsed_seconds"],
                      "cumulative_evidence_bytes": ledger["counts"]["evidence_bytes"],
                      "resources": ledger["resources"]}))


if __name__ == "__main__":
    main()
