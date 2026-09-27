from __future__ import annotations

"""Bind R7 artifacts and the current gate state into a versioned manifest."""

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
    fd, name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(value, stream, ensure_ascii=False, sort_keys=True, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def artifact(relative: str, rows: int | None = None) -> dict:
    path = ROOT / relative
    return {"path": relative, "bytes": path.stat().st_size, "sha256": sha(path), "row_count": rows}


def main() -> int:
    r1_manifest_path = ROOT / "reports/v4_02/V4_02_FINAL_STAGING_MANIFEST_R1.json"
    r1_manifest = json.loads(r1_manifest_path.read_text(encoding="utf-8"))
    price = json.loads((ROOT / "reports/v4_02/V4_02_PRICE_LIMIT_ACCEPTANCE_R3_20260927.json").read_text(encoding="utf-8"))
    alias = json.loads((ROOT / "reports/v4_02/V4_01_CODE_CHANGE_ALIAS_AUDIT_R7.json").read_text(encoding="utf-8"))
    range_audit_path = ROOT / "reports/v4_02/V4_02_PRICE_LIMIT_RANGE_EXCEPTION_AUDIT_R3.json"
    range_audit = json.loads(range_audit_path.read_text(encoding="utf-8"))
    test_path = ROOT / "reports/v4_02/V4_02_FINAL_R3_TEST_RECEIPT.json"
    test = json.loads(test_path.read_text(encoding="utf-8"))
    components = dict(r1_manifest["components"])
    components.update({
        "SECURITY_ENTITY_MAP_R7": artifact("data/v4/artifact_store/v4_01/security_entity_map_R7_20260927.json"),
        "HISTORICAL_UNIVERSE_R7": artifact("data/v4/artifact_store/v4_01/v4_01_historical_universe_required_R7_20260927.jsonl.gz", alias["scan"]["output_membership_rows"]),
        "DATED_TRADING_STATUS_R7": artifact("data/v4/artifact_store/v4_02/V4_02_DATED_TRADING_STATUS_R7_20260927.jsonl.gz", alias["scan"]["output_membership_rows"]),
        "DATED_ISST_R7": artifact("data/v4/artifact_store/v4_02/V4_02_DATED_ST_STATUS_R7_20260927.jsonl.gz", alias["scan"]["output_membership_rows"]),
        "ADJUSTED_DAILY_R7": artifact("data/v4/artifact_store/v4_02/V4_02_ADJUSTED_CANONICAL_DAILY_R7_20260927.parquet", 4026611),
        "FORMAL_WEEKLY_R7": artifact("data/v4/artifact_store/v4_02/V4_02_FORMAL_WEEKLY_RAW_QFQ_R7_20260927.parquet", 1704964),
        "FORMAL_MONTHLY_R7": artifact("data/v4/artifact_store/v4_02/V4_02_FORMAL_MONTHLY_RAW_QFQ_R7_20260927.parquet", 400918),
        "PRICE_LIMIT_R3": artifact(price["artifact"]["path"], price["row_count"]),
        "PRICE_LIMIT_ACCEPTANCE_R3": artifact("reports/v4_02/V4_02_PRICE_LIMIT_ACCEPTANCE_R3_20260927.json"),
        "CODE_CHANGE_ALIAS_AUDIT_R7": artifact("reports/v4_02/V4_01_CODE_CHANGE_ALIAS_AUDIT_R7.json"),
        "PRICE_LIMIT_RANGE_EXCEPTION_AUDIT_R3": artifact(str(range_audit_path.relative_to(ROOT)).replace("\\", "/")),
        "R3_RULE_CONTRACT": artifact("config/v4_02_price_limit_rules_r3.json"),
        "R3_TEST_RECEIPT": artifact(str(test_path.relative_to(ROOT)).replace("\\", "/")),
        "R1_REVOCATION_RECEIPT": artifact("reports/v4_02/V4_02_FINAL_RECEIPT_R1_REVOKE_R3.json"),
    })
    blockers = []
    if alias.get("scan", {}).get("unresolved_required_scope_code_change_identities") != 0:
        blockers.append("REQUIRED_SCOPE_CODE_CHANGE_ALIAS_AUDIT_OPEN")
    if range_audit.get("status") != "CLOSED":
        blockers.append("PRICE_LIMIT_RANGE_EXCEPTION_AUDIT_OPEN")
    if test.get("result") != "PASS":
        blockers.append("R3_TEST_RECEIPT_NOT_PASS")
    manifest = {
        "contract_id": "V4_02_WHOLE_STAGE_STAGING_MANIFEST_R3",
        "version": "3.0.0",
        "status": "BLOCKED" if blockers else "STAGING_CANDIDATE_READY",
        "stage": "V4-02",
        "stage_contract": "R3 targeted alias/board repair and previous official close state propagation",
        "source_cutoff": "2026-09-24",
        "required_boards": ["SH_MAIN", "SZ_MAIN", "CHINEXT", "STAR"],
        "optional_degraded_boards": ["BSE"],
        "bse_in_required_outputs": False,
        "components": components,
        "acceptance": {"code_change_required_identities_unresolved": alias["scan"]["unresolved_required_scope_code_change_identities"],
                       "r1_range_exceptions_resolved": range_audit["scope"]["r1_resolved"],
                       "r1_range_exceptions_open": range_audit["scope"]["r1_still_open"],
                       "r3_current_range_exceptions": range_audit["scope"]["r3_current_exception_rows"],
                       "r3_additional_range_exceptions": range_audit["scope"]["r3_additional_exception_rows"],
                       "price_limit_unknown": price["limit_status_counts"].get("UNKNOWN", 0),
                       "price_limit_unknown_reasons": price.get("unknown_reason_counts", {}),
                       "ordinary_suspension_previous_actual_close_reason_count": price.get("unknown_reason_counts", {}).get("PREVIOUS_SESSION_ACTUAL_CLOSE_UNAVAILABLE", 0),
                       "test_result": test["result"]},
        "blockers": blockers,
        "evidence": {"governing_r3_audit": "V4_02_FINAL_EXTERNAL_AUDIT_AND_R3_TARGETED_REPAIR_20260926.md",
                     "official_code_change_capture_sha256": alias["evidence"]["source_capture_sha256"],
                     "r3_rule_contract_sha256": components["R3_RULE_CONTRACT"]["sha256"]},
        "supersedes": "V4_02_FINAL_STAGING_MANIFEST_R1",
        "scanner_factor_trading_runs": 0,
        "next_stage": "DISPOSITION_EACH_RANGE_EXCEPTION; DO_NOT_START_V4_03",
        "created_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    }
    out = ROOT / "reports/v4_02/V4_02_FINAL_STAGING_MANIFEST_R3.json"
    atomic_json(out, manifest)
    print(json.dumps({"status": manifest["status"], "blockers": blockers,
                      "components": len(components), "path": str(out.relative_to(ROOT)), "sha256": sha(out)}, ensure_ascii=False))
    return 0 if not blockers else 2


if __name__ == "__main__":
    raise SystemExit(main())
