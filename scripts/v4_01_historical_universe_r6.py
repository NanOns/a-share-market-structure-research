from __future__ import annotations

"""Build isolated Required, Optional BSE and Pending R6 historical universes."""

import argparse
import gzip
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from collections import Counter
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))
from v4_01_historical_evaluable_universe_r4 import UNIVERSE_CONTRACT, sha256_file, source_bar_dates  # noqa: E402
from workbench_analysis.baostock_supplemental import _atomic_json  # noqa: E402
from workbench_analysis.v4_01_required_scope import (  # noqa: E402
    REQUIRED_BOARD_KEYS, active_on, required_board, split_roster_scope,
)


def atomic_gzip_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, raw = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    os.close(fd)
    temp = Path(raw)
    try:
        with gzip.open(temp, "wt", encoding="utf-8", newline="\n", compresslevel=6) as stream:
            for record in records:
                stream.write(json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")
        with temp.open("rb+") as stream:
            os.fsync(stream.fileno())
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


def file_digest(records: list[dict[str, Any]]) -> str:
    h = hashlib.sha256()
    for row in records:
        h.update(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8"))
        h.update(b"\n")
    return h.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rosters", default="data/v4/artifact_store/v4_01/baostock_dated_rosters_R6_20260926.jsonl.gz")
    ap.add_argument("--roster-receipt", default="reports/v4_01/baostock_dated_roster_completeness_receipt_R6_20260926.json")
    ap.add_argument("--identity-map", default="data/v4/artifact_store/v4_01/security_entity_map_R5_20260925.json")
    ap.add_argument("--scope-receipt", default="reports/v4_01/required_scope_gates_receipt_R6_20260926.json")
    ap.add_argument("--scope-contract", default="config/v4_required_equity_scope_v1.json")
    ap.add_argument("--output", default="data/v4/artifact_store/v4_01/v4_01_historical_universe_required_R6_20260926.jsonl.gz")
    ap.add_argument("--bse-output", default="data/v4/artifact_store/v4_01/v4_01_historical_universe_bse_optional_R6_20260926.jsonl.gz")
    ap.add_argument("--pending-output", default="data/v4/artifact_store/v4_01/v4_01_roster_pending_classification_R6_20260926.jsonl.gz")
    ap.add_argument("--receipt", default="reports/v4_01/historical_evaluable_universe_receipt_R6_20260926.json")
    args = ap.parse_args()
    roster_path, roster_receipt_path = ROOT / args.rosters, ROOT / args.roster_receipt
    identity_path, scope_path, scope_contract_path = ROOT / args.identity_map, ROOT / args.scope_receipt, ROOT / args.scope_contract
    roster_receipt = json.loads(roster_receipt_path.read_text(encoding="utf-8"))
    scope_receipt = json.loads(scope_path.read_text(encoding="utf-8"))
    scope_contract = json.loads(scope_contract_path.read_text(encoding="utf-8"))
    if (scope_contract.get("contract_id") != "REQUIRED_EQUITY_SCOPE_V1"
            or tuple(scope_contract.get("required_boards", [])) != REQUIRED_BOARD_KEYS):
        raise SystemExit("R6_UNIVERSE_SCOPE_CONTRACT_INVALID")
    if roster_receipt.get("status") != "PASS" or roster_receipt.get("summary", {}).get("session_count") != 786:
        raise SystemExit("R6_ROSTER_COMPLETENESS_NOT_ACCEPTED")
    identity_doc = json.loads(identity_path.read_text(encoding="utf-8"))
    identities = identity_doc.get("records", [])
    by_key = {str(row.get("source_security_key", "")).lower(): row for row in identities}
    noncore_by_key = {str(row.get("source_security_key", "")).lower(): row
                      for row in identity_doc.get("non_core_candidates", [])}
    unresolved_bse = {str(row.get("source_security_key", "")).lower()
                      for row in identity_doc.get("unresolved", [])
                      if str(row.get("source_security_key", "")).upper().startswith("BJ.")}
    candidate = json.loads((ROOT / "reports/v4_01/historical_evaluable_universe_receipt_R4_20260925.json").read_text("utf-8"))
    sessions = [row["trade_date"] for row in candidate["daily_reconstructed_universe"]["days"]]
    rosters: dict[str, list[str]] = {}
    with gzip.open(roster_path, "rt", encoding="utf-8") as stream:
        for line in stream:
            item = json.loads(line)
            codes = item["source_codes"]
            if item["trade_date"] in rosters or codes != sorted(set(codes)):
                raise SystemExit("R6_ROSTER_RECORD_ORDER_OR_UNIQUENESS_INVALID")
            if item.get("row_count") != len(codes) or hashlib.sha256("\n".join(codes).encode("ascii")).hexdigest() != item.get("codes_sha256"):
                raise SystemExit("R6_ROSTER_RECORD_DIGEST_INVALID")
            rosters[item["trade_date"]] = codes
    if list(rosters) != sessions:
        raise SystemExit("R6_ROSTER_SESSION_COVERAGE_INVALID")

    required_keys = {key for key, row in by_key.items() if required_board(row)}
    session_ints = {int(date.fromisoformat(day).strftime("%Y%m%d")) for day in sessions}
    bar_dates, bar_errors = source_bar_dates(session_ints, {key.lower() for key in required_keys})
    required_rows: list[dict[str, Any]] = []
    bse_rows: list[dict[str, Any]] = []
    pending_rows: list[dict[str, Any]] = []
    daily_scope = []
    board_totals = {board: {"security_ids": set(), "membership_rows": 0, "identity_unresolved": 0,
                            "bar_missing": 0, "bar_invalid": 0} for board in REQUIRED_BOARD_KEYS}
    bse_seen_by_day: dict[str, set[str]] = {}
    bse_pending_count = 0
    noncore_count = 0
    pending_count = 0
    daily_root = hashlib.sha256()
    for index, day in enumerate(sessions, 1):
        day_int = int(date.fromisoformat(day).strftime("%Y%m%d"))
        split = split_roster_scope(rosters[day], by_key, day, noncore_by_key)
        board_counts = Counter()
        day_required = []
        for code in split["required"]:
            identity = by_key[code]
            board = required_board(identity)
            if not board or not identity.get("security_id") or not identity.get("source_revision_id"):
                board_totals[board or "SH_MAIN"]["identity_unresolved"] += 1
                continue
            bar_present = code in bar_dates.get(day_int, set())
            row = {"trade_date": day, "board_scope": board, "security_id": identity["security_id"],
                   "source_security_key": code.upper(), "security_type": "A_STOCK",
                   "universe_contract_id": UNIVERSE_CONTRACT,
                   "membership_basis": "R6_ACCEPTED_A_STOCK_IDENTITY_INTERSECTED_WITH_COMPLETE_DATED_ROSTER",
                   "lineage": "RECONSTRUCTED_CORRECTED", "source_revision_id": identity["source_revision_id"],
                   "source_bar_present": bar_present,
                   "eligibility_status": "EVALUABLE_BAR_AVAILABLE" if bar_present else "MEMBER_BAR_MISSING_STATUS_NOT_INFERRED"}
            required_rows.append(row)
            day_required.append(row)
            board_counts[board] += 1
            board_totals[board]["security_ids"].add(identity["security_id"])
            board_totals[board]["membership_rows"] += 1
            if not bar_present:
                board_totals[board]["bar_missing"] += 1

        bse_seen = set()
        for code in split["bse_optional"]:
            identity = by_key[code]
            security_id = identity.get("security_id")
            if security_id and security_id in bse_seen:
                continue
            if security_id:
                bse_seen.add(security_id)
            bse_rows.append({"trade_date": day, "scope": "BSE_OPTIONAL_DEGRADED", "security_id": security_id,
                             "source_security_key": code.upper(), "security_type": "A_STOCK",
                             "membership_basis": "Dated BaoStock roster plus candidate BSE lifecycle alias",
                             "identity_quality": identity.get("identity_quality"), "status": "DEGRADED_BSE"})
        for identity in identities:
            if str(identity.get("exchange", "")).upper() != "BJ" or identity.get("security_type") != "A_STOCK" or not active_on(identity, day):
                continue
            code = str(identity.get("source_security_key", "")).lower()
            security_id = str(identity.get("security_id") or "")
            if security_id in bse_seen:
                continue
            if code in rosters[day]:
                bse_seen.add(security_id)
                continue
            bse_seen.add(security_id)
            bse_rows.append({"trade_date": day, "scope": "BSE_OPTIONAL_DEGRADED", "security_id": identity.get("security_id"),
                             "source_security_key": code.upper(), "security_type": "A_STOCK",
                             "membership_basis": "BSE_OFFICIAL_INDEX_CAPTURE_CANDIDATE",
                             "identity_quality": identity.get("identity_quality"), "status": "DEGRADED_BSE"})
        for code in sorted(set(split["pending"]) | (set(rosters[day]) & unresolved_bse)):
            is_bse = code.startswith("bj.")
            pending_rows.append({"trade_date": day, "scope": "BSE_OPTIONAL_UNRESOLVED" if is_bse else "OUT_OF_REQUIRED_SCOPE_PENDING_CLASSIFICATION",
                                 "source_security_key": code.upper(), "security_id": None,
                                 "classification_status": "DEGRADED_BSE_IDENTITY" if is_bse else "PENDING_CLASSIFICATION"})
            if is_bse:
                bse_pending_count += 1
            else:
                pending_count += 1
        noncore_count += len(split["noncore"])
        day_digest = hashlib.sha256("\n".join(
            f"{row['board_scope']}\0{row['source_security_key']}\0{row['security_id']}\0{row['eligibility_status']}"
            for row in day_required).encode("utf-8")).hexdigest()
        daily_root.update(f"{day}\0{day_digest}\0{len(day_required)}\n".encode("ascii"))
        daily_scope.append({"trade_date": day, "required_membership_rows": len(day_required),
                            "by_board": {b: board_counts[b] for b in REQUIRED_BOARD_KEYS},
                            "identity_unresolved": 0, "required_digest": day_digest,
                            "bse_optional_rows": sum(1 for row in bse_rows if row["trade_date"] == day),
                            "pending_classification_rows": len(split["pending"])})
        if index % 100 == 0:
            print(json.dumps({"sessions": index, "required_rows": len(required_rows), "bse_rows": len(bse_rows)}, ensure_ascii=False), flush=True)

    required_path, bse_path, pending_path = ROOT / args.output, ROOT / args.bse_output, ROOT / args.pending_output
    atomic_gzip_jsonl(required_path, required_rows)
    atomic_gzip_jsonl(bse_path, bse_rows)
    atomic_gzip_jsonl(pending_path, pending_rows)
    board_result = {}
    for board, tally in board_totals.items():
        board_result[board] = {"required": True, "securities": len(tally["security_ids"]),
                               "membership_rows": tally["membership_rows"],
                               "identity_unresolved": tally["identity_unresolved"],
                               "bar_missing": tally["bar_missing"], "bar_invalid": tally["bar_invalid"],
                               "status": "PASS" if tally["identity_unresolved"] == 0 and tally["bar_invalid"] == 0 else "BLOCKED"}
    blockers = []
    if scope_receipt.get("status") != "PASS":
        blockers.append("REQUIRED_SCOPE_IDENTITY_LIFECYCLE_OR_EXCEPTION_GATE_BLOCKED")
    if len(sessions) != 786:
        blockers.append("R6_REQUIRED_SESSION_COUNT_INVALID")
    if bar_errors:
        blockers.append("LOCAL_SOURCE_BAR_VALIDATION_ERRORS")
    if any(item["status"] != "PASS" for item in board_result.values()):
        blockers.append("REQUIRED_BOARD_UNIVERSE_HAS_IDENTITY_OR_BAR_VALIDATION_ERRORS")
    status = "PASS" if not blockers else "BLOCKED"
    receipt = {"stage": "V4-01-HISTORICAL-UNIVERSE-R6", "contract_id": "V4_REQUIRED_HISTORICAL_UNIVERSE_R6_V1",
               "version": "1.0.0", "observed_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
               "status": status, "stage_completion_authorized": False,
               "input": {"roster_path": args.rosters, "roster_sha256": sha256_file(roster_path),
                         "roster_completeness_receipt": args.roster_receipt,
                         "roster_completeness_receipt_sha256": sha256_file(roster_receipt_path),
                         "identity_map_path": args.identity_map, "identity_map_sha256": sha256_file(identity_path),
                         "scope_gate_receipt": args.scope_receipt, "scope_gate_receipt_sha256": sha256_file(scope_path),
                         "scope_contract_path": args.scope_contract,
                         "scope_contract_sha256": sha256_file(scope_contract_path)},
               "required_scope": {"boards": board_result, "membership_rows": len(required_rows),
                                  "identity_unresolved": sum(x["identity_unresolved"] for x in board_result.values()),
                                  "daily_digest_root": daily_root.hexdigest(),
                                  "output": {"path": args.output, "sha256": sha256_file(required_path),
                                             "byte_count": required_path.stat().st_size,
                                             "row_count": len(required_rows), "scope_isolated": True}},
               "optional_bse_scope": {"status": "DEGRADED_BSE", "required": False,
                                      "candidate_and_roster_membership_rows": len(bse_rows),
                                      "unresolved_source_identity_count": len(unresolved_bse),
                                      "unresolved_roster_membership_rows": bse_pending_count,
                                      "output": {"path": args.bse_output, "sha256": sha256_file(bse_path),
                                                 "byte_count": bse_path.stat().st_size,
                                                 "row_count": len(bse_rows), "separate_from_required_digest": True}},
               "pending_classification": {"status": "PRESERVED_OUT_OF_REQUIRED_SCOPE",
                                          "row_count": len(pending_rows), "noncore_provider_confirmed_rows": noncore_count,
                                          "generic_pending_rows": pending_count,
                                          "output": {"path": args.pending_output, "sha256": sha256_file(pending_path),
                                                     "byte_count": pending_path.stat().st_size,
                                                     "row_count": len(pending_rows)}},
               "summary": {"session_count": len(sessions), "source_bar_validation_error_count": len(bar_errors),
                           "source_bar_missing_does_not_infer_trading_status": True,
                           "bar_missing_total": sum(x["bar_missing"] for x in board_totals.values())},
               "daily_scope": daily_scope, "blockers": blockers,
               "execution_identity": {"code_head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()},
               "next_stage": "V4_01_FINAL_REQUIRED_SCOPE_R6" if status == "PASS" else "V4_01_REMEDIATE_REQUIRED_SCOPE_UNIVERSE_R6"}
    _atomic_json(ROOT / args.receipt, receipt)
    print(json.dumps({"status": status, "boards": board_result, "required_membership_rows": len(required_rows),
                      "bse_rows": len(bse_rows), "pending_rows": len(pending_rows), "blockers": blockers,
                      "receipt": args.receipt}, ensure_ascii=False))
    return 0 if status == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
