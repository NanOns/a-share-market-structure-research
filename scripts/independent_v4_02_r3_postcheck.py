from __future__ import annotations

"""Independent row and hash checks for the V4-02 R3 candidate."""

import gzip
import hashlib
import json
import os
import tempfile
from collections import Counter
from datetime import datetime, timezone
from itertools import zip_longest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "reports/v4_02/V4_02_FINAL_STAGING_MANIFEST_R3.json"
OUT = ROOT / "reports/v4_02/V4_02_FINAL_INDEPENDENT_POSTCHECK_R3.json"


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


def load(relative: str) -> dict:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def main() -> int:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    findings = []
    checks = {}
    # Every manifest entry is hash-bound to a local artifact.
    component_hash_failures = []
    for name, item in manifest["components"].items():
        path = ROOT / item["path"]
        if not path.exists() or sha(path) != item["sha256"]:
            component_hash_failures.append(name)
    checks["all_manifest_component_hashes_match"] = not component_hash_failures
    if component_hash_failures:
        findings.append("MANIFEST_COMPONENT_HASH_MISMATCH:" + ",".join(component_hash_failures))

    alias = load("reports/v4_02/V4_01_CODE_CHANGE_ALIAS_AUDIT_R7.json")
    identity = load("data/v4/artifact_store/v4_01/security_entity_map_R7_20260927.json")
    target_records = [row for row in identity["records"] if row.get("security_id") == "SEC-EDEDE35FE66896ACCA0AC85EEB2F133B"]
    by_alias = {row.get("source_security_key"): row for row in target_records}
    checks["code_change_alias_audit_unresolved_zero"] = alias["scan"]["unresolved_required_scope_code_change_identities"] == 0
    checks["302132_board_chinext"] = by_alias.get("SZ.302132", {}).get("board") == "CHINEXT"
    checks["302132_alias_starts_20250217"] = by_alias.get("SZ.302132", {}).get("symbol_effective_from") == "2025-02-17"
    checks["300114_alias_ends_20250216"] = by_alias.get("SZ.300114", {}).get("symbol_effective_to") == "2025-02-16"
    for key, passed in checks.items():
        if not passed:
            findings.append(key.upper() + "_FAILED")

    # Independently reconcile the four daily JSONL components by exact row key.
    relative = ["data/v4/artifact_store/v4_01/v4_01_historical_universe_required_R7_20260927.jsonl.gz",
                "data/v4/artifact_store/v4_02/V4_02_DATED_TRADING_STATUS_R7_20260927.jsonl.gz",
                "data/v4/artifact_store/v4_02/V4_02_DATED_ST_STATUS_R7_20260927.jsonl.gz",
                "data/v4/artifact_store/v4_02/V4_02_PRICE_LIMIT_R7_20260927.jsonl.gz"]
    streams = [gzip.open(ROOT / name, "rt", encoding="utf-8") for name in relative]
    count = 0
    duplicate_key_count = 0
    key_mismatch_count = 0
    reason_counts = Counter()
    prev_reason = 0
    target_rows = target_pre_code = target_post_code = target_wrong_board = 0
    day_ids: set[str] = set()
    current_day = None
    try:
        for lines in zip_longest(*streams):
            if any(line is None for line in lines):
                key_mismatch_count += 1
                break
            rows = [json.loads(line) for line in lines]
            count += 1
            keys = {(str(row.get("security_id")), str(row.get("trade_date")).replace("-", ""), str(row.get("source_security_key"))) for row in rows}
            if len(keys) != 1:
                key_mismatch_count += 1
            universe, status, isst, price = rows
            day = str(universe["trade_date"]).replace("-", "")
            if day != current_day:
                current_day = day
                day_ids = set()
            sid = str(universe["security_id"])
            if sid in day_ids:
                duplicate_key_count += 1
            day_ids.add(sid)
            if price.get("limit_status") == "UNKNOWN":
                reason = price.get("reason")
                if not reason:
                    key_mismatch_count += 1
                if reason:
                    reason_counts[str(reason)] += 1
            if price.get("reason") == "PREVIOUS_SESSION_ACTUAL_CLOSE_UNAVAILABLE":
                prev_reason += 1
            if sid == "SEC-EDEDE35FE66896ACCA0AC85EEB2F133B":
                target_rows += 1
                if day < "20250217":
                    target_pre_code += 1
                    if universe.get("source_security_key") != "SZ.300114":
                        target_wrong_board += 1
                else:
                    target_post_code += 1
                    if universe.get("source_security_key") != "SZ.302132":
                        target_wrong_board += 1
                if universe.get("board_scope") != "CHINEXT" or price.get("board_scope") != "CHINEXT":
                    target_wrong_board += 1
            if count % 1000000 == 0:
                print(json.dumps({"postcheck_rows": count}), flush=True)
    finally:
        for stream in streams:
            stream.close()
    checks["daily_membership_component_rows_reconcile"] = count == manifest["components"]["HISTORICAL_UNIVERSE_R7"]["row_count"]
    checks["no_duplicate_stable_id_trade_date"] = duplicate_key_count == 0
    checks["universe_status_isst_price_row_keys_match"] = key_mismatch_count == 0
    checks["ordinary_suspension_adjacent_bar_reason_removed"] = prev_reason == 0
    checks["302132_target_sessions_use_dated_alias_and_chinext"] = target_rows == 786 and target_wrong_board == 0 and target_pre_code > 0 and target_post_code > 0
    checks["all_unknown_price_rows_have_reason"] = "" not in reason_counts
    if not checks["daily_membership_component_rows_reconcile"]:
        findings.append(f"MEMBERSHIP_ROW_COUNT_MISMATCH:{count}")
    if duplicate_key_count:
        findings.append(f"DUPLICATE_STABLE_ID_SESSION:{duplicate_key_count}")
    if key_mismatch_count:
        findings.append(f"DAILY_COMPONENT_BINDING_MISMATCH:{key_mismatch_count}")
    if prev_reason:
        findings.append(f"OLD_SUSPENSION_REASON_REMAINS:{prev_reason}")
    if target_wrong_board or target_rows != 786:
        findings.append(f"TARGET_ALIAS_BOARD_ROW_CHECK_FAILED:{target_rows}:{target_wrong_board}")

    rule = load("config/v4_02_price_limit_rules_r3.json")
    capture_failures = []
    for evidence in rule["source_evidence"]["captures"].values():
        path = ROOT / evidence["source_capture_path"]
        if not path.exists() or sha(path) != evidence["source_capture_sha256"]:
            capture_failures.append(evidence["source_capture_path"])
    rule_fields_ok = all(row.get("source_ref") and row.get("source_capture_path") and row.get("source_capture_sha256") and row.get("clause_mapping_sha256") for row in rule["rules"])
    checks["official_rule_source_capture_hashes_match"] = not capture_failures and rule_fields_ok
    if capture_failures or not rule_fields_ok:
        findings.append("RULE_SOURCE_CAPTURE_OR_NORMALIZATION_FAILED")

    import duckdb
    con = duckdb.connect()
    target = "SEC-EDEDE35FE66896ACCA0AC85EEB2F133B"
    old = "SEC-B2F87F189D1D143B67730E3640E617CA"
    daily = "data/v4/artifact_store/v4_02/V4_02_ADJUSTED_CANONICAL_DAILY_R7_20260927.parquet"
    weekly = "data/v4/artifact_store/v4_02/V4_02_FORMAL_WEEKLY_RAW_QFQ_R7_20260927.parquet"
    monthly = "data/v4/artifact_store/v4_02/V4_02_FORMAL_MONTHLY_RAW_QFQ_R7_20260927.parquet"
    daily_result = con.execute(f"select count(*), count(distinct canonical_security_id || ':' || cast(trade_date as varchar)), count_if(canonical_security_id='{old}'), count_if(canonical_security_id='{target}' and board_scope <> 'CHINEXT'), count_if(canonical_security_id='{target}' and source_security_key <> case when trade_date < 20250217 then 'SZ.300114' else 'SZ.302132' end) from read_parquet('{(ROOT/daily).as_posix()}')").fetchone()
    checks["adjusted_daily_unique_and_target_dated"] = daily_result[0] == daily_result[1] and daily_result[2] == 0 and daily_result[3] == 0 and daily_result[4] == 0
    for name, path in (("weekly", weekly), ("monthly", monthly)):
        result = con.execute(f"select count_if(canonical_security_id='{old}'), count_if(canonical_security_id='{target}' and board_scope <> 'CHINEXT') from read_parquet('{(ROOT/path).as_posix()}')").fetchone()
        checks[f"{name}_old_id_removed_and_board_fixed"] = result == (0, 0)
    if not checks["adjusted_daily_unique_and_target_dated"]:
        findings.append(f"ADJUSTED_DAILY_R7_IDENTITY_CHECK_FAILED:{daily_result}")
    if not checks["weekly_old_id_removed_and_board_fixed"] or not checks["monthly_old_id_removed_and_board_fixed"]:
        findings.append("FORMAL_PERIOD_R7_IDENTITY_CHECK_FAILED")

    range_audit = load("reports/v4_02/V4_02_PRICE_LIMIT_RANGE_EXCEPTION_AUDIT_R3.json")
    checks["range_exception_audit_closed"] = (range_audit.get("status") == "CLOSED"
        and range_audit.get("scope", {}).get("r3_current_exception_rows", 0) == 0
        and range_audit.get("scope", {}).get("r1_still_open", 0) == 0)
    if not checks["range_exception_audit_closed"]:
        findings.append(f"ENGINEERING_RANGE_EXCEPTIONS_OPEN:{range_audit.get('scope', {}).get('r3_current_exception_rows')}_current; {range_audit.get('scope', {}).get('r1_still_open')}_R1_open")
    test = load("reports/v4_02/V4_02_FINAL_R3_TEST_RECEIPT.json")
    checks["r3_test_receipt_pass"] = test.get("result") == "PASS" and test.get("failed") == 0 and test.get("skipped") == 0
    if not checks["r3_test_receipt_pass"]:
        findings.append("R3_TEST_RECEIPT_NOT_PASS")
    head = load("data/v4/V4_02_ACCEPTED_HEAD.json")
    revocation = load("reports/v4_02/V4_02_FINAL_RECEIPT_R1_REVOKE_R3.json")
    checks["r1_head_revoked_and_v4_03_blocked"] = head.get("status") == "SUPERSEDED_BLOCKED_PENDING_R3" and head.get("v4_03_entry") == "BLOCKED" and revocation.get("v4_03_entry") == "BLOCKED"
    if not checks["r1_head_revoked_and_v4_03_blocked"]:
        findings.append("R1_HEAD_REVOCATION_OR_V4_03_GATE_FAILED")

    status = "PASS" if not findings else "BLOCKED"
    result = {"contract_id": "V4_02_FINAL_INDEPENDENT_POSTCHECK_R3", "version": "3.0.0", "status": status,
              "manifest": {"path": str(MANIFEST.relative_to(ROOT)).replace("\\", "/"), "sha256": sha(MANIFEST)},
              "checks": checks, "findings": findings,
              "row_reconciliation": {"membership_rows": count, "price_unknown_reasons": dict(reason_counts),
                                     "old_previous_actual_reason_count": prev_reason, "target_identity_sessions": target_rows,
                                     "target_pre_code_sessions": target_pre_code, "target_post_code_sessions": target_post_code,
                                     "target_wrong_alias_or_board_rows": target_wrong_board,
                                     "adjusted_daily_rows": daily_result[0], "adjusted_daily_unique_identity_dates": daily_result[1]},
              "execution_identity": {"script_sha256": sha(Path(__file__).resolve())},
              "tdx_root_write_count": 0,
              "observed_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
              "next_stage": "RESOLVE_RANGE_EXCEPTION_AUDIT; DO_NOT_PROMOTE_ACCEPTED_HEAD_OR_START_V4_03" if status != "PASS" else "SEAL_FINAL_R3_RECEIPT"}
    atomic_json(OUT, result)
    print(json.dumps({"status": status, "findings": findings, "path": str(OUT.relative_to(ROOT))}, ensure_ascii=False))
    return 0 if status == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
