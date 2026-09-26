from __future__ import annotations

"""Fresh-session completeness repair and sealing for suspicious R5 roster days."""

import argparse
import gzip
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from workbench_analysis.baostock_supplemental import BaoStockClient, RequestBudget, _atomic_json  # noqa: E402
from workbench_analysis.v4_01_required_scope import (  # noqa: E402
    REQUIRED_BOARD_KEYS, active_on, missing_traded_required_codes, required_board,
    required_identity_missing_from_roster, roster_suspicion_flags, validate_fresh_roster_runs,
)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def code_digest(codes: list[str]) -> str:
    return hashlib.sha256("\n".join(codes).encode("ascii")).hexdigest()


def query_fresh_roster(day: str, ledger: Path) -> dict[str, Any]:
    with BaoStockClient(RequestBudget(ledger), auth_mode="PUBLIC_ANONYMOUS", timeout=30) as client:
        rows, meta = client.query_rows("query_all_stock", "query_all_stock", day=day,
                                       max_rows=10_000, max_pages=10)
    codes = [str(row.get("code", "")).strip().lower() for row in rows]
    duplicates = len(codes) - len(set(codes))
    codes = sorted(set(codes))
    return {"row_count": len(rows), "unique_code_count": len(codes), "duplicate_count": duplicates,
            "codes_sha256": code_digest(codes), "codes": codes,
            "provider_error_code": meta.get("error_code"), "provider_page_count_observed": meta.get("page_count"),
            "provider_fields": meta.get("fields", [])}


def query_daily_market(day: str, ledger: Path) -> dict[str, Any]:
    with BaoStockClient(RequestBudget(ledger), auth_mode="PUBLIC_ANONYMOUS", timeout=30) as client:
        rows, meta = client.query_rows("query_daily_history_k_AStock", "query_daily_history_k_AStock",
                                       date=day, max_rows=20_000, max_pages=1)
    invalid_dates = sum(str(row.get("date")) != day for row in rows)
    duplicate_codes = len(rows) - len({str(row.get("code", "")).lower() for row in rows})
    all_codes = {str(row.get("code", "")).lower() for row in rows}
    traded_codes = {str(row.get("code", "")).lower() for row in rows
                    if str(row.get("tradestatus", "")) == "1"
                    and float(row.get("volume") or 0) > 0}
    return {"row_count": len(rows), "all_a_stock_codes_sha256": code_digest(sorted(all_codes)),
            "traded_a_stock_codes_sha256": code_digest(sorted(traded_codes)),
            "traded_a_stock_count": len(traded_codes), "all_a_stock_count": len(all_codes),
            "duplicate_code_count": duplicate_codes, "invalid_date_row_count": invalid_dates,
            "provider_error_code": meta.get("error_code"), "provider_page_count_observed": meta.get("page_count"),
            "provider_fields": meta.get("fields", []), "all_codes": all_codes,
            "traded_codes": traded_codes}


def load_rosters(path: Path, expected_days: list[str]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    with gzip.open(path, "rt", encoding="utf-8") as stream:
        for line in stream:
            record = json.loads(line)
            day, codes = record.get("trade_date"), record.get("source_codes")
            if day in result or day not in expected_days or not isinstance(codes, list):
                raise SystemExit("R5_ROSTER_RECORD_INVALID")
            if (codes != sorted(set(codes)) or record.get("row_count") != len(codes)
                    or code_digest(codes) != record.get("codes_sha256")):
                raise SystemExit("R5_ROSTER_INTERNAL_DIGEST_INVALID")
            result[day] = {**record, "source_codes": codes}
    if list(result) != expected_days:
        raise SystemExit("R5_ROSTER_SESSION_COVERAGE_INVALID")
    return result


def atomic_gzip_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    os.close(fd)
    temp = Path(name)
    try:
        with gzip.open(temp, "wt", encoding="utf-8", newline="\n", compresslevel=6) as stream:
            for record in records:
                stream.write(json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")
        with temp.open("rb+") as stream:
            os.fsync(stream.fileno())
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rosters", default="data/v4/artifact_store/v4_01/baostock_dated_rosters_R5_20260925.jsonl.gz")
    ap.add_argument("--roster-receipt", default="reports/v4_01/baostock_dated_roster_receipt_R5_20260925.json")
    ap.add_argument("--identity-map", default="data/v4/artifact_store/v4_01/security_entity_map_R5_20260925.json")
    ap.add_argument("--ledger", default="reports/v4_baostock/request_ledger.json")
    ap.add_argument("--contract", default="config/baostock_dated_roster_completeness_v1.json")
    ap.add_argument("--output", default="data/v4/artifact_store/v4_01/baostock_dated_rosters_R6_20260926.jsonl.gz")
    ap.add_argument("--receipt", default="reports/v4_01/baostock_dated_roster_completeness_receipt_R6_20260926.json")
    args = ap.parse_args()
    roster_path, roster_receipt_path = ROOT / args.rosters, ROOT / args.roster_receipt
    identity_path, ledger_path = ROOT / args.identity_map, ROOT / args.ledger
    contract_path = ROOT / args.contract
    receipt_path, output_path = ROOT / args.receipt, ROOT / args.output
    roster_receipt = json.loads(roster_receipt_path.read_text(encoding="utf-8"))
    identity_doc = json.loads(identity_path.read_text(encoding="utf-8"))
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    if contract.get("contract_id") != "BAOSTOCK_DATED_ROSTER_COMPLETENESS_V1":
        raise SystemExit("R6_ROSTER_COMPLETENESS_CONTRACT_ID_INVALID")
    trigger = contract.get("suspicion_triggers", {})
    revalidation = contract.get("revalidation", {})
    if int(revalidation.get("fresh_sessions_per_suspicious_day", 0)) != 2:
        raise SystemExit("R6_FRESH_SESSION_REVALIDATION_CONTRACT_INVALID")
    input_rosters = load_rosters(roster_path, [row["trade_date"] for row in roster_receipt["daily_counts"]])
    days = list(input_rosters)
    identities = identity_doc.get("records", [])
    identities_by_key = {str(row.get("source_security_key", "")).lower(): row for row in identities}
    active_required_counts = {}
    flagged: list[tuple[str, list[str]]] = []
    prior = None
    for day in days:
        row = input_rosters[day]
        active = [r for r in identities if required_board(r) and active_on(r, day)]
        active_required_counts[day] = len(active)
        flags = roster_suspicion_flags(row_count=row["row_count"], prior_row_count=prior,
                                       required_lifecycle_count=len(active),
                                       page_multiple=int(trigger.get("exact_provider_page_multiple", 2000)),
                                       large_drop=int(trigger.get("absolute_day_over_day_drop", 500)),
                                       large_lifecycle_gap=int(trigger.get("large_lifecycle_count_gap", 500)))
        if flags:
            flagged.append((day, flags))
        prior = row["row_count"]

    audit_days = []
    replacements: dict[str, list[str]] = {}
    blocker_count = Counter()
    for day, flags in flagged:
        old_codes = input_rosters[day]["source_codes"]
        first = query_fresh_roster(day, ledger_path)
        second = query_fresh_roster(day, ledger_path)
        market = query_daily_market(day, ledger_path)
        failures = validate_fresh_roster_runs(first, second)
        fresh_codes = first["codes"]
        active_expected = {str(r.get("source_security_key", "")).lower() for r in identities
                           if required_board(r) and active_on(r, day)}
        missing_lifecycle = active_expected - set(fresh_codes)
        required_traded = {code for code in market["traded_codes"]
                           if required_board(identities_by_key.get(code, {}))}
        missing_traded = missing_traded_required_codes(required_traded, set(fresh_codes))
        unknown_traded = sorted(code for code in market["traded_codes"] - set(identities_by_key)
                                if not code.startswith("bj."))
        if first["provider_error_code"] != "0" or second["provider_error_code"] != "0":
            failures.append("FRESH_SESSION_PROVIDER_QUERY_FAILED")
        if market["provider_error_code"] != "0" or market["invalid_date_row_count"] or market["duplicate_code_count"]:
            failures.append("FULL_MARKET_DAILY_CROSSCHECK_INVALID")
        if missing_lifecycle:
            failures.append("REQUIRED_LIFECYCLE_IDENTITY_MISSING_FROM_FRESH_ROSTER")
        if missing_traded:
            failures.append("TRADED_REQUIRED_SCOPE_NOT_SUBSET_OF_FRESH_ROSTER")
        if unknown_traded:
            failures.append("TRADED_A_STOCK_WITHOUT_ACCEPTED_IDENTITY")
        if active_required_counts[day] - len(fresh_codes) >= 500:
            failures.append("LIFECYCLE_COUNT_SANITY_FAILED")
        for failure in failures:
            blocker_count[failure] += 1
        replacements[day] = fresh_codes
        boards = Counter()
        for code in market["traded_codes"]:
            identity = identities_by_key.get(code)
            board = required_board(identity) if identity else None
            if board:
                boards[board] += 1
        audit_days.append({
            "trade_date": day, "suspicion_triggers": flags,
            "old_roster": {"row_count": len(old_codes), "codes_sha256": code_digest(old_codes)},
            "fresh_session_1": {k: v for k, v in first.items() if k != "codes"},
            "fresh_session_2": {k: v for k, v in second.items() if k != "codes"},
            "stable_fresh_digest": first["codes_sha256"] == second["codes_sha256"],
            "full_market_daily_crosscheck": {k: v for k, v in market.items()
                                              if k not in {"all_codes", "traded_codes"}},
            "required_traded_scope_count_by_board": {b: boards[b] for b in REQUIRED_BOARD_KEYS},
            "missing_active_required_lifecycle_identities": sorted(missing_lifecycle),
            "missing_traded_required_scope_codes": sorted(missing_traded),
            "traded_a_stock_without_accepted_identity": unknown_traded,
            "accepted": not failures, "blockers": failures,
        })

    records = []
    daily = []
    for day in days:
        source = input_rosters[day]
        codes = replacements.get(day, source["source_codes"])
        digest = code_digest(codes)
        records.append({"contract_id": "BAOSTOCK_DATED_ROSTER_SNAPSHOT_R6_V1", "trade_date": day,
                        "row_count": len(codes), "page_count_observed_only": source.get("page_count"),
                        "codes_sha256": digest, "source_codes": codes})
        daily.append({"trade_date": day, "row_count": len(codes), "codes_sha256": digest,
                      "acceptance_basis": "FRESH_SESSION_STABLE_DIGEST_AND_INDEPENDENT_CROSSCHECK"
                      if day in replacements else "NO_AUTOMATIC_SUSPICION_TRIGGER"})

    missing_suspicious_days = [day for day, _ in flagged if day not in replacements]
    if missing_suspicious_days:
        blocker_count["SUSPICIOUS_DATES_NOT_REVALIDATED"] += len(missing_suspicious_days)
    expected_sessions = int(contract.get("session_count_required", 786))
    all_accepted = not blocker_count and len(daily) == expected_sessions and len(audit_days) == len(flagged)
    if all_accepted:
        atomic_gzip_jsonl(output_path, records)
    ledger_doc = json.loads(ledger_path.read_text(encoding="utf-8"))
    daily_budget = ledger_doc.get("by_shanghai_date", {})
    exceeded = [day for day, item in daily_budget.items() if int(item.get("count", 0)) > 40_000]
    if exceeded:
        blocker_count["SYSTEM_DAILY_SOFT_BUDGET_EXCEEDED"] += len(exceeded)
        all_accepted = False
    receipt = {
        "stage": "V4-01-ROSTER-COMPLETENESS-R6", "contract_id": "BAOSTOCK_DATED_ROSTER_COMPLETENESS_V1",
        "version": "1.0.0", "observed_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "status": "PASS" if all_accepted else "BLOCKED", "stage_completion_authorized": False,
        "source": {"provider": "BaoStock", "auth_mode": "PUBLIC_ANONYMOUS",
                   "roster_method": "query_all_stock(day)", "crosscheck_method": "query_daily_history_k_AStock"},
        "input": {"r5_roster_path": args.rosters, "r5_roster_sha256": sha256(roster_path),
                  "r5_receipt_path": args.roster_receipt, "r5_receipt_sha256": sha256(roster_receipt_path),
                  "identity_map_path": args.identity_map, "identity_map_sha256": sha256(identity_path),
                  "contract_path": args.contract, "contract_sha256": sha256(contract_path),
                  "session_count": len(days), "first_session": days[0], "last_session": days[-1]},
        "summary": {"session_count": len(days), "suspicious_day_count": len(flagged),
                    "revalidated_day_count": len(audit_days), "fresh_query_count": len(audit_days) * 2,
                    "full_market_daily_crosscheck_count": len(audit_days),
                    "accepted_suspicious_day_count": sum(row["accepted"] for row in audit_days),
                    "blocked_reason_counts": dict(blocker_count),
                    "required_scope": list(REQUIRED_BOARD_KEYS),
                    "row_count_before": sum(row["row_count"] for row in input_rosters.values()),
                    "row_count_after": sum(row["row_count"] for row in records)},
        "daily_completeness": daily, "suspicious_day_evidence": audit_days,
        "output": ({"path": args.output, "sha256": sha256(output_path), "byte_count": output_path.stat().st_size,
                    "format": "GZIP_JSONL", "daily_roster_digest_root": hashlib.sha256(
                        "".join(f"{r['trade_date']}\0{r['row_count']}\0{r['codes_sha256']}\n" for r in daily).encode("ascii")
                    ).hexdigest()} if all_accepted else None),
        "request_budget": {"ledger_path": args.ledger, "ledger_sha256": sha256(ledger_path),
                           "by_shanghai_date": daily_budget,
                           "configured_soft_cap": 40_000, "configured_hard_cap": 45_000,
                           "provider_daily_limit": 50_000},
        "execution_identity": {"code_head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
                               "script_sha256": sha256(Path(__file__))},
        "next_stage": "V4_01_REQUIRED_SCOPE_IDENTITY_LIFECYCLE_UNIVERSE_R6" if all_accepted
                      else "V4_01_REPAIR_BLOCKED_ROSTER_DATES_R6",
    }
    _atomic_json(receipt_path, receipt)
    print(json.dumps({"status": receipt["status"], "summary": receipt["summary"], "receipt": args.receipt}, ensure_ascii=False))
    return 0 if all_accepted else 2


if __name__ == "__main__":
    raise SystemExit(main())
