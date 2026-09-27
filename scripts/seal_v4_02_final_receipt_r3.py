from __future__ import annotations

"""Seal the R3 candidate without promoting a blocked accepted head."""

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


def load(relative: str) -> dict:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def main() -> int:
    manifest_path = ROOT / "reports/v4_02/V4_02_FINAL_STAGING_MANIFEST_R3.json"
    postcheck_path = ROOT / "reports/v4_02/V4_02_FINAL_INDEPENDENT_POSTCHECK_R3.json"
    audit_path = ROOT / "reports/v4_02/V4_02_PRICE_LIMIT_RANGE_EXCEPTION_AUDIT_R3.json"
    alias_path = ROOT / "reports/v4_02/V4_01_CODE_CHANGE_ALIAS_AUDIT_R7.json"
    test_path = ROOT / "reports/v4_02/V4_02_FINAL_R3_TEST_RECEIPT.json"
    manifest, postcheck, audit = (json.loads(path.read_text(encoding="utf-8")) for path in (manifest_path, postcheck_path, audit_path))
    alias, test = load("reports/v4_02/V4_01_CODE_CHANGE_ALIAS_AUDIT_R7.json"), load("reports/v4_02/V4_02_FINAL_R3_TEST_RECEIPT.json")
    checks = {
        "r1_final_head_revoked": load("data/v4/V4_02_ACCEPTED_HEAD.json").get("status") == "SUPERSEDED_BLOCKED_PENDING_R3",
        "r1_history_preserved": load("reports/v4_02/V4_02_FINAL_RECEIPT_R1_REVOKE_R3.json").get("status") == "SUPERSEDED_BLOCKED_PENDING_R3",
        "required_scope_code_change_alias_audit_zero_unresolved": alias.get("scan", {}).get("unresolved_required_scope_code_change_identities") == 0,
        "302132_board_and_alias_intervals_repaired": alias.get("target", {}).get("board") == "CHINEXT" and len(alias.get("target", {}).get("aliases", [])) == 2,
        "ordinary_suspension_no_longer_breaks_reference_chain": postcheck.get("checks", {}).get("ordinary_suspension_adjacent_bar_reason_removed") is True,
        "r3_regression_suite_pass": test.get("result") == "PASS" and test.get("failed") == 0,
        "official_rule_source_evidence_normalized": postcheck.get("checks", {}).get("official_rule_source_capture_hashes_match") is True,
        "all_range_exceptions_independently_dispositioned": audit.get("status") == "CLOSED" and audit.get("scope", {}).get("r3_current_exception_rows") == 0 and audit.get("scope", {}).get("r1_still_open") == 0,
        "independent_final_postcheck_pass": postcheck.get("status") == "PASS",
    }
    blockers = [name for name, passed in checks.items() if not passed]
    status = "PASS_WITH_BSE_SCOPE_DEGRADED" if not blockers else "BLOCKED"
    out = ROOT / "reports/v4_02/V4_02_FINAL_RECEIPT_R3.json"
    receipt = {
        "contract_id": "V4_02_FINAL_ACCEPTANCE_RECEIPT_R3",
        "version": "3.0.0",
        "stage": "V4-02 FINAL CLOSURE PACK / R3 TARGETED REPAIR",
        "status": status,
        "checks": checks,
        "blockers": blockers,
        "scope": {"start_date": "2023-07-04", "source_cutoff": "2026-09-24",
                  "required_boards": ["SH_MAIN", "SZ_MAIN", "CHINEXT", "STAR"], "optional_degraded": ["BSE"]},
        "evidence": {"manifest": {"path": str(manifest_path.relative_to(ROOT)).replace("\\", "/"), "sha256": sha(manifest_path), "status": manifest.get("status")},
                     "independent_postcheck": {"path": str(postcheck_path.relative_to(ROOT)).replace("\\", "/"), "sha256": sha(postcheck_path), "status": postcheck.get("status")},
                     "code_change_alias_audit": {"path": str(alias_path.relative_to(ROOT)).replace("\\", "/"), "sha256": sha(alias_path), "status": alias.get("status")},
                     "price_limit_range_exception_audit": {"path": str(audit_path.relative_to(ROOT)).replace("\\", "/"), "sha256": sha(audit_path), "status": audit.get("status"), "scope": audit.get("scope")},
                     "tests": {"path": str(test_path.relative_to(ROOT)).replace("\\", "/"), "sha256": sha(test_path), "result": test.get("result"), "passed": test.get("passed"), "failed": test.get("failed"), "skipped": test.get("skipped")}},
        "component_hashes": {name: item["sha256"] for name, item in manifest.get("components", {}).items()},
        "historical_adjusted_lineage": "DIAGNOSTIC_NON_PIT; HISTORICAL_PIT_NOT_CLAIMED",
        "atomic_publication": {"accepted_head_path": "data/v4/V4_02_ACCEPTED_HEAD.json", "head_promoted": False,
                               "current_head_status": "SUPERSEDED_BLOCKED_PENDING_R3"},
        "supersedes": "V4_02_FINAL_RECEIPT_R1; R1 HISTORY RETAINED AND REVOKED",
        "v4_03_entry": "BLOCKED",
        "scanner_factor_trading_runs": 0,
        "next_stage": "COMPLETE_OFFICIAL_ROW_SPECIFIC_DISPOSITIONS_FOR_ALL_OPEN_RANGE_EXCEPTIONS; DO_NOT_START_V4_03" if blockers else "WAIT_FOR_EXTERNAL_ACCEPTANCE; DO_NOT_START_V4_03",
        "observed_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    }
    atomic_json(out, receipt)
    print(json.dumps({"status": status, "blockers": blockers, "path": str(out.relative_to(ROOT)), "sha256": sha(out)}, ensure_ascii=False))
    return 0 if not blockers else 2


if __name__ == "__main__":
    raise SystemExit(main())
