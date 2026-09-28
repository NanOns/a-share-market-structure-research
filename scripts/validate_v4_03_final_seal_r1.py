"""Validate the V4-03 final seal bindings and V4-04 entry authorization."""

import hashlib
import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_COMMIT = "e19bd4f376d9e47ae14610ad5c93247f3513c4bd"
RECEIPT = "reports/v4_03/V4_03_FINAL_STAGE_RECEIPT_R1_20260928.json"
V403_HEAD = "data/v4/V4_03_ACCEPTED_HEAD.json"
GLOBAL_HEAD = "data/v4/V4_STAGE_ACCEPTED_HEAD.json"
OUTPUT = ROOT / "reports/v4_03/V4_03_FINAL_SEAL_VALIDATION_R1_20260928.json"
ADDED_GLOBAL_KEYS = {"v4_03_binding", "v4_03_status", "v4_04_stock_core_entry",
                     "v4_08_sector_entry"}


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def load(relative: str) -> dict:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def main() -> None:
    failures = []
    receipt = load(RECEIPT)
    accepted = load(V403_HEAD)
    global_head = load(GLOBAL_HEAD)
    receipt_sha = sha(ROOT / RECEIPT)
    accepted_sha = sha(ROOT / V403_HEAD)

    for category in ("source", "contracts", "artifacts", "evidence"):
        for relative, expected in receipt.get("hashes", {}).get(category, {}).items():
            path = ROOT / relative
            if not path.is_file() or sha(path) != expected:
                failures.append(f"{category}_sha_mismatch:{relative}")

    if receipt.get("accepted_candidate_commit") != EXPECTED_COMMIT:
        failures.append("accepted_candidate_commit_mismatch")
    try:
        subprocess.run(["git", "cat-file", "-e", f"{EXPECTED_COMMIT}^{{commit}}"], cwd=ROOT, check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except subprocess.CalledProcessError:
        failures.append("accepted_candidate_commit_unavailable")
    if receipt.get("source_cutoff") != "2026-09-24":
        failures.append("source_cutoff_mismatch")
    if receipt.get("status") != "PASS_WITH_SECTOR_SCOPE_DEGRADED":
        failures.append("final_receipt_status_mismatch")
    if receipt.get("external_acceptance") != "PASS_WITH_CAPABILITY_SCOPE":
        failures.append("external_acceptance_mismatch")

    if accepted.get("final_stage_receipt") != {"path": RECEIPT, "sha256": receipt_sha}:
        failures.append("accepted_head_receipt_binding_mismatch")
    if accepted.get("accepted_candidate_commit") != EXPECTED_COMMIT:
        failures.append("accepted_head_candidate_commit_mismatch")
    if accepted.get("capabilities", {}).get("SECTOR_NATIVE") != "BLOCKED_MISSING_ACCEPTED_PIT_MEMBERSHIP":
        failures.append("sector_capability_not_blocked")
    if accepted.get("v4_04_stock_core_authorization") != "AUTHORIZED":
        failures.append("v4_04_stock_core_not_authorized")
    if accepted.get("v4_08_sector") != "BLOCKED_MISSING_ACCEPTED_PIT_MEMBERSHIP":
        failures.append("v4_08_sector_not_blocked")
    if accepted.get("incremental_update") != "DEFERRED_NON_BLOCKING":
        failures.append("incremental_update_disposition_mismatch")

    if global_head.get("v4_03_binding") != {"path": V403_HEAD, "sha256": accepted_sha}:
        failures.append("global_v4_03_binding_mismatch")
    if global_head.get("v4_03_status") != "PASS_WITH_SECTOR_SCOPE_DEGRADED":
        failures.append("global_v4_03_status_mismatch")
    if global_head.get("v4_04_stock_core_entry") != "AUTHORIZED":
        failures.append("global_v4_04_entry_mismatch")
    if global_head.get("v4_08_sector_entry") != "BLOCKED_MISSING_ACCEPTED_PIT_MEMBERSHIP":
        failures.append("global_v4_08_sector_status_mismatch")

    # Compare all old global-head fields with the candidate commit to prove
    # that the seal only appended the requested V4-03 governance binding.
    try:
        old_text = subprocess.check_output(
            ["git", "show", f"{EXPECTED_COMMIT}:{GLOBAL_HEAD}"], cwd=ROOT, text=True, encoding="utf-8")
        old_global = json.loads(old_text)
        current_old_fields = {key: value for key, value in global_head.items() if key not in ADDED_GLOBAL_KEYS}
        if current_old_fields != old_global:
            failures.append("preexisting_global_head_fields_changed")
    except (subprocess.CalledProcessError, json.JSONDecodeError):
        failures.append("candidate_global_head_snapshot_unavailable")

    # Final Seal authorizes entry only. No V4-04 business outputs may exist.
    business_artifacts = []
    for root_rel in ("reports", "data/v4"):
        root = ROOT / root_rel
        if root.exists():
            business_artifacts.extend(str(p.relative_to(ROOT)) for p in root.rglob("*")
                                      if p.is_file() and ("V4_04" in p.name.upper() or
                                                          (p.parent.name.lower() == "v4_04")))
    if business_artifacts:
        failures.append("v4_04_business_artifacts_present")
    if receipt.get("scanner_run_count") != 0 or receipt.get("trading_run_count") != 0 or receipt.get("tdx_root_write_count") != 0:
        failures.append("forbidden_execution_count_nonzero")
    if receipt.get("v4_04_business_calculation_started") is not False:
        failures.append("v4_04_business_calculation_started")

    report = {
        "contract_id": "V4_03_FINAL_SEAL_VALIDATION_R1_20260928",
        "status": "PASS" if not failures else "FAIL",
        "accepted_candidate_commit": EXPECTED_COMMIT,
        "final_receipt_sha256": receipt_sha,
        "v4_03_accepted_head_sha256": accepted_sha,
        "global_head_v4_03_binding_valid": not any(x.startswith("global_") for x in failures),
        "preexisting_global_head_fields_preserved": "preexisting_global_head_fields_changed" not in failures,
        "v4_04_business_artifacts": business_artifacts,
        "checked_file_hash_count": sum(len(receipt.get("hashes", {}).get(k, {}))
                                        for k in ("source", "contracts", "artifacts", "evidence")),
        "failures": failures,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    temp = OUTPUT.with_suffix(OUTPUT.suffix + ".tmp")
    temp.write_text(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    os.replace(temp, OUTPUT)
    print(json.dumps({"status": report["status"], "checked_hashes": report["checked_file_hash_count"],
                      "failures": failures}, ensure_ascii=False))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
