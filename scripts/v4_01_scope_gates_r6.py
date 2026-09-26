from __future__ import annotations

"""Seal board-scoped identity, formal lifecycle and exception gates for R6."""

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import psycopg

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))
from scripts.apply_v4_phase0_schema import dsn  # noqa: E402
from workbench_analysis.baostock_supplemental import _atomic_json  # noqa: E402
from workbench_analysis.v4_01_required_scope import (  # noqa: E402
    REQUIRED_BOARD_KEYS, classify_bse_scope, required_board, required_scope_counts,
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--identity-map", default="data/v4/artifact_store/v4_01/security_entity_map_R5_20260925.json")
    ap.add_argument("--identity-receipt", default="reports/v4_01/security_entity_map_receipt_R5_20260925.json")
    ap.add_argument("--lifecycle-facts", default="reports/v4_01/baostock_lifecycle_facts_R4_20260925.json")
    ap.add_argument("--exceptions", default="reports/v4_01/source_exception_classification_R5_20260925.json")
    ap.add_argument("--contract", default="config/v4_required_equity_scope_v1.json")
    ap.add_argument("--output", default="reports/v4_01/required_scope_gates_receipt_R6_20260926.json")
    args = ap.parse_args()
    map_path, map_receipt_path, facts_path, exceptions_path, contract_path = (ROOT / args.identity_map,
        ROOT / args.identity_receipt, ROOT / args.lifecycle_facts, ROOT / args.exceptions, ROOT / args.contract)
    identities = json.loads(map_path.read_text(encoding="utf-8"))
    map_receipt = json.loads(map_receipt_path.read_text(encoding="utf-8"))
    lifecycle_facts = json.loads(facts_path.read_text(encoding="utf-8"))
    exception_doc = json.loads(exceptions_path.read_text(encoding="utf-8"))
    scope_contract = json.loads(contract_path.read_text(encoding="utf-8"))
    if (scope_contract.get("contract_id") != "REQUIRED_EQUITY_SCOPE_V1"
            or tuple(scope_contract.get("required_boards", [])) != REQUIRED_BOARD_KEYS):
        raise SystemExit("R6_REQUIRED_SCOPE_CONTRACT_INVALID")
    if map_receipt.get("output", {}).get("sha256") != sha256(map_path):
        raise SystemExit("R6_IDENTITY_MAP_RECEIPT_DIGEST_MISMATCH")
    records = identities.get("records", [])
    identity_by_key = {str(row.get("source_security_key", "")).lower(): row for row in records}
    facts_by_key = {str(row.get("source_security_key", "")).lower(): row
                    for row in lifecycle_facts.get("facts", [])}
    identity_counts = required_scope_counts(records)
    identity_errors: dict[str, list[str]] = {board: [] for board in REQUIRED_BOARD_KEYS}
    required_rows = [row for row in records if required_board(row)]
    for row in required_rows:
        board = required_board(row)
        key = str(row.get("source_security_key") or "").lower()
        if not row.get("security_id") or not row.get("source_revision_id") or not row.get("list_date"):
            identity_errors[board].append(key or "EMPTY_SOURCE_KEY")
        fact = facts_by_key.get(key)
        if (not fact or fact.get("security_type_provider") != "1"
                or fact.get("listed_from") != row.get("list_date")
                or row.get("source_contract_id") != "BAOSTOCK_LIFECYCLE_FACTS_R5_V1"):
            identity_errors[board].append(key + ":TYPE1_SOURCE_BINDING_INVALID")
    for board in REQUIRED_BOARD_KEYS:
        identity_counts[board]["unresolved_identity_rows"] += len(identity_errors[board])

    lifecycle_board = {board: {"required": True, "expected_fact_rows": 0, "materialized_fact_rows": 0,
                               "missing_fact_rows": 0, "source_revision_binding_violations": 0,
                               "timestamp_rule_violations": 0, "status": "BLOCKED"}
                       for board in REQUIRED_BOARD_KEYS}
    fact_keys = {}
    for row in required_rows:
        board = required_board(row)
        effective = row.get("symbol_effective_from") or row.get("list_date")
        fact_key = f"{row['security_id']}|lifecycle|{row['symbol']}|{effective}"
        fact_keys[fact_key] = (board, row)
        lifecycle_board[board]["expected_fact_rows"] += 1
    database_error = None
    try:
        with psycopg.connect(dsn()) as pg:
            db_rows = pg.execute(
                """select h.lifecycle_fact_key,h.security_id,h.symbol,h.security_type,h.board,h.list_date,
                          h.effective_from,h.effective_to,h.source_contract_id,h.source_identity,
                          h.source_revision_id,h.supersedes_revision_id,h.observed_at,h.ingested_at,
                          h.system_available_at,s.logical_fact_id,s.supersedes_revision_id
                   from v4.security_lifecycle_history h
                   join v4.source_revisions s using(source_revision_id)"""
            ).fetchall()
            append_only_trigger_count = pg.execute(
                """select count(*) from pg_trigger where tgrelid='v4.security_lifecycle_history'::regclass
                   and not tgisinternal and tgname='v4_security_lifecycle_history_append_only'"""
            ).fetchone()[0]
        db_by_key = {row[0]: row for row in db_rows}
        for fact_key, (board, identity) in fact_keys.items():
            db_row = db_by_key.get(fact_key)
            if db_row is None:
                lifecycle_board[board]["missing_fact_rows"] += 1
                continue
            lifecycle_board[board]["materialized_fact_rows"] += 1
            expected = (identity["security_id"], identity["symbol"], identity["security_type"], identity["board"],
                        identity.get("list_date"), identity.get("symbol_effective_from") or identity.get("list_date"),
                        identity.get("symbol_effective_to"), identity["source_contract_id"])
            observed = tuple(str(value) if value is not None else None for value in db_row[1:9])
            expected_normalized = tuple(str(value) if value is not None else None for value in expected)
            if observed != expected_normalized or db_row[15] != fact_key or db_row[16] != db_row[11]:
                lifecycle_board[board]["source_revision_binding_violations"] += 1
            if db_row[14] != max(db_row[12], db_row[13]):
                lifecycle_board[board]["timestamp_rule_violations"] += 1
        for board, item in lifecycle_board.items():
            item["status"] = "PASS" if (item["missing_fact_rows"] == 0
                and item["source_revision_binding_violations"] == 0
                and item["timestamp_rule_violations"] == 0 and append_only_trigger_count == 1) else "BLOCKED"
            item["append_only_trigger_present"] = append_only_trigger_count == 1
    except Exception as exc:
        database_error = type(exc).__name__ + ":DATABASE_SCOPE_VALIDATION_FAILED"
        for board in REQUIRED_BOARD_KEYS:
            lifecycle_board[board]["error"] = database_error
    for board, item in identity_counts.items():
        item["status"] = "PASS" if item["security_keys"] > 0 and item["unresolved_identity_rows"] == 0 else "BLOCKED"
    bse_unresolved = sum(1 for row in identities.get("unresolved", [])
                         if str(row.get("source_security_key", "")).upper().startswith("BJ."))
    bse_lifecycle_count = sum(1 for row in records if str(row.get("exchange", "")).upper() == "BJ"
                              and row.get("security_type") == "A_STOCK")
    bse = classify_bse_scope(bse_unresolved, False)
    bse.update({"mapped_candidate_lifecycle_rows": bse_lifecycle_count,
                "pending_non_equity_candidates": sum(1 for row in identities.get("non_core_candidates", [])
                    if str(row.get("source_security_key", "")).upper().startswith("BJ.")),
                "required_scope_blocking": False})

    exception_records = exception_doc.get("records", [])
    exception_scope = {board: 0 for board in REQUIRED_BOARD_KEYS}
    required_unexplained = []
    pending_noncore = 0
    bse_exceptions = 0
    for row in exception_records:
        key = str(row.get("source_security_key") or "").lower()
        identity = identity_by_key.get(key)
        board = required_board(identity or {})
        if board:
            exception_scope[board] += 1
            required_unexplained.append(key)
        elif key.startswith("bj."):
            bse_exceptions += 1
        elif row.get("acceptance_status") == "CLASSIFIED_NONCORE_CANDIDATE":
            pending_noncore += 1
        elif not key:
            pending_noncore += 1
    source_exception_gate = {"status": "PASS" if not required_unexplained else "BLOCKED",
                             "unexplained_required_a_stock_exception_count": len(required_unexplained),
                             "unexplained_required_a_stock_keys": required_unexplained,
                             "non_core_pending_count": pending_noncore,
                             "bse_exception_count": bse_exceptions,
                             "R5_all_exception_rows_retained": len(exception_records),
                             "R5_core_unexplained_claim": exception_doc.get("summary", {}).get("core_a_stock_unexplained_exception_count")}

    status = "PASS" if (not database_error
        and all(row["status"] == "PASS" for row in identity_counts.values())
        and all(row["status"] == "PASS" for row in lifecycle_board.values())
        and source_exception_gate["status"] == "PASS") else "BLOCKED"
    receipt = {
        "stage": "V4-01-REQUIRED-SCOPE-IDENTITY-LIFECYCLE-R6",
        "contract_id": "REQUIRED_EQUITY_SCOPE_V1", "version": scope_contract.get("version", "1.0.0"),
        "observed_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "status": status, "stage_completion_authorized": False,
        "required_scope": {board: {"identity": identity_counts[board], "lifecycle": lifecycle_board[board]}
                           for board in REQUIRED_BOARD_KEYS},
        "source_exception_gate": source_exception_gate,
        "optional_scope": {"BSE": bse},
        "identity_policy": {"accepted_type": "BaoStock lifecycle security_type=1 plus stable ID/list-date/source-revision",
                            "board_policy": "explicit exchange plus mapped board; code prefix alone is not identity evidence",
                            "unknown_policy": "OUT_OF_REQUIRED_SCOPE_PENDING_CLASSIFICATION",
                            "old_r5_core_a_stock_unexplained_2997": "RETIRED_PREFIX_PROXY_NOT_A_GATE"},
        "inputs": {"identity_map_path": args.identity_map, "identity_map_sha256": sha256(map_path),
                   "identity_map_receipt_path": "reports/v4_01/security_entity_map_receipt_R5_20260925.json",
                   "identity_map_receipt_sha256": sha256(map_receipt_path),
                   "lifecycle_facts_path": args.lifecycle_facts, "lifecycle_facts_sha256": sha256(facts_path),
                   "exceptions_path": args.exceptions, "exceptions_sha256": sha256(exceptions_path),
                   "scope_contract_path": args.contract, "scope_contract_sha256": sha256(contract_path)},
        "execution_identity": {"code_head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()},
        "next_stage": "V4_01_REQUIRED_HISTORICAL_UNIVERSE_R6" if status == "PASS" else "V4_01_REPAIR_REQUIRED_SCOPE_GATES_R6",
    }
    _atomic_json(ROOT / args.output, receipt)
    print(json.dumps({"status": status, "identity": identity_counts, "lifecycle": lifecycle_board,
                      "exceptions": source_exception_gate, "BSE": bse, "receipt": args.output}, ensure_ascii=False))
    return 0 if status == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
