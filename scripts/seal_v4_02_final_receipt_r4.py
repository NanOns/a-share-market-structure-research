from __future__ import annotations

"""Seal R4 only after the independent postcheck and exception gate pass."""

import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load(relative: str) -> dict:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(value, stream, ensure_ascii=False, sort_keys=True, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_name, path)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def main() -> int:
    manifest_path = ROOT / "reports/v4_02/V4_02_FINAL_STAGING_MANIFEST_R4.json"
    postcheck_path = ROOT / "reports/v4_02/V4_02_FINAL_INDEPENDENT_POSTCHECK_R4.json"
    audit_path = ROOT / "reports/v4_02/V4_02_PRICE_LIMIT_RANGE_EXCEPTION_AUDIT_R4.json"
    alias_path = ROOT / "reports/v4_02/V4_01_CODE_CHANGE_ALIAS_AUDIT_R7.json"
    test_path = ROOT / "reports/v4_02/V4_02_FINAL_R4_TEST_RECEIPT.json"
    r3_post_path = ROOT / "reports/v4_02/V4_02_FINAL_INDEPENDENT_POSTCHECK_R3.json"
    head_path = ROOT / "data/v4/V4_02_ACCEPTED_HEAD.json"
    manifest, postcheck, audit, alias, test, r3_post = (
        json.loads(path.read_text(encoding="utf-8"))
        for path in (manifest_path, postcheck_path, audit_path, alias_path, test_path, r3_post_path)
    )
    current_head = json.loads(head_path.read_text(encoding="utf-8"))

    checks = {
        "r4_manifest_ready": manifest.get("status") == "STAGING_CANDIDATE_READY" and not manifest.get("blockers"),
        "all_manifest_components_hash_bound": postcheck.get("checks", {}).get("all_component_hashes_match") is True,
        "independent_r4_postcheck_pass": postcheck.get("status") == "PASS",
        "all_76_dispositions_closed": audit.get("status") == "CLOSED"
            and audit.get("scope", {}).get("row_count") == 76
            and audit.get("scope", {}).get("r3_current_exception_rows") == 53
            and audit.get("scope", {}).get("r3_resolved_special_phase") == 22
            and audit.get("scope", {}).get("r3_fail_closed_dispositioned") == 31
            and audit.get("scope", {}).get("undispositioned_engineering_exceptions") == 0
            and audit.get("scope", {}).get("fail_closed_missing_evidence") == 0,
        "r7_alias_board_audit_pass": alias.get("scan", {}).get("unresolved_required_scope_code_change_identities") == 0,
        "r3_previous_close_freeze_pass": r3_post.get("status") == "PASS"
            and postcheck.get("checks", {}).get("frozen_r3_previous_close_chain_pass") is True,
        "r4_and_frozen_r3_tests_pass": test.get("result") == "PASS"
            and test.get("passed") == 20 and test.get("failed") == 0 and test.get("skipped") == 0
            and test.get("r3_22_test_freeze_receipt", {}).get("result") == "PASS"
            and test.get("r3_22_test_freeze_receipt", {}).get("passed") == 22,
        "bse_degraded_out_of_required_scope": manifest.get("bse_in_required_outputs") is False
            and postcheck.get("checks", {}).get("bse_isolated") is True,
        "current_accepted_head_is_r3_superseded": current_head.get("status") == "SUPERSEDED_BLOCKED_PENDING_R3",
    }
    blockers = [name for name, passed in checks.items() if not passed]
    status = "PASS_WITH_BSE_SCOPE_DEGRADED" if not blockers else "BLOCKED"
    out = ROOT / "reports/v4_02/V4_02_FINAL_RECEIPT_R4.json"
    receipt = {
        "contract_id": "V4_02_FINAL_ACCEPTANCE_RECEIPT_R4", "version": "4.0.0",
        "stage": "V4-02 FINAL SPECIAL PRICE PHASE CLOSURE / R4",
        "status": status, "checks": checks, "blockers": blockers,
        "scope": {"start_date": "2023-07-04", "source_cutoff": "2026-09-24",
                  "required_boards": ["SH_MAIN", "SZ_MAIN", "CHINEXT", "STAR"], "optional_degraded": ["BSE"]},
        "evidence": {
            "manifest": {"path": str(manifest_path.relative_to(ROOT)).replace("\\", "/"), "sha256": sha(manifest_path), "status": manifest.get("status")},
            "independent_postcheck": {"path": str(postcheck_path.relative_to(ROOT)).replace("\\", "/"), "sha256": sha(postcheck_path), "status": postcheck.get("status")},
            "range_exception_audit": {"path": str(audit_path.relative_to(ROOT)).replace("\\", "/"), "sha256": sha(audit_path), "status": audit.get("status"), "scope": audit.get("scope")},
            "code_change_alias_audit": {"path": str(alias_path.relative_to(ROOT)).replace("\\", "/"), "sha256": sha(alias_path), "status": alias.get("status")},
            "tests": {"path": str(test_path.relative_to(ROOT)).replace("\\", "/"), "sha256": sha(test_path), "result": test.get("result"), "passed": test.get("passed"), "failed": test.get("failed"), "skipped": test.get("skipped"), "execution_commit": test.get("execution_commit")},
            "frozen_r3_previous_close_postcheck": {"path": str(r3_post_path.relative_to(ROOT)).replace("\\", "/"), "sha256": sha(r3_post_path), "status": r3_post.get("status")},
        },
        "component_hashes": {name: item["sha256"] for name, item in manifest.get("components", {}).items()},
        "historical_adjusted_lineage": "DIAGNOSTIC_NON_PIT; HISTORICAL_PIT_NOT_CLAIMED",
        "atomic_publication": {"accepted_head_path": str(head_path.relative_to(ROOT)).replace("\\", "/"),
                               "head_promoted": not blockers,
                               "prior_head_status": current_head.get("status"),
                               "published_head_status": status if not blockers else current_head.get("status")},
        "supersedes": "V4_02_FINAL_RECEIPT_R3; R1 HISTORY RETAINED AND REVOKED",
        "v4_03_entry": "PENDING_EXTERNAL_ACCEPTANCE" if not blockers else "BLOCKED",
        "scanner_factor_trading_runs": 0,
        "next_stage": "WAIT_FOR_EXTERNAL_ACCEPTANCE; DO_NOT_START_V4-03" if not blockers else "REPAIR_R4_BLOCKERS; DO_NOT_PROMOTE_ACCEPTED_HEAD_OR_START_V4-03",
        "observed_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    }
    atomic_json(out, receipt)
    if not blockers:
        receipt_hash = sha(out)
        head = {
            "contract_id": "V4_02_ACCEPTED_HEAD_V1", "stage": "V4-02",
            "status": "PASS_WITH_BSE_SCOPE_DEGRADED", "source_cutoff": "2026-09-24",
            "final_receipt_path": str(out.relative_to(ROOT)).replace("\\", "/"),
            "final_receipt_sha256": receipt_hash,
            "manifest_path": str(manifest_path.relative_to(ROOT)).replace("\\", "/"),
            "manifest_sha256": sha(manifest_path),
            "accepted_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            "v4_03_entry": "PENDING_EXTERNAL_ACCEPTANCE",
            "supersedes_final_receipt_path": "reports/v4_02/V4_02_FINAL_RECEIPT_R3.json",
            "supersedes_final_receipt_sha256": sha(ROOT / "reports/v4_02/V4_02_FINAL_RECEIPT_R3.json"),
            "history": {"r1_revoked": True, "r3_blocked_receipt_retained": True},
        }
        atomic_json(head_path, head)
        readback = json.loads(head_path.read_text(encoding="utf-8"))
        if readback.get("status") != status or readback.get("final_receipt_sha256") != receipt_hash:
            raise RuntimeError("ATOMIC_ACCEPTED_HEAD_READBACK_FAILED")
    print(json.dumps({"status": status, "blockers": blockers,
                      "accepted_head_promoted": not blockers,
                      "receipt_sha256": sha(out), "path": str(out.relative_to(ROOT))}, ensure_ascii=False))
    return 0 if not blockers else 2


if __name__ == "__main__":
    raise SystemExit(main())
