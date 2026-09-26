from __future__ import annotations

"""Requery only dates flagged by the R6.1 all-day required-coverage audit."""

import gzip
import hashlib
import json
import sys
from contextlib import nullcontext
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from workbench_analysis.baostock_supplemental import (  # noqa: E402
    BaoStockClient, BaoStockError, RequestBudget, _atomic_json,
)

AUDIT = ROOT / "reports/v4_01/V4_01_ALL_DAY_REQUIRED_ROSTER_COVERAGE_R6_1.json"
ROSTER = ROOT / "data/v4/artifact_store/v4_01/baostock_dated_rosters_R6_20260926.jsonl.gz"
LEDGER = ROOT / "reports/v4_baostock/request_ledger.json"
OUTPUT = ROOT / "reports/v4_01/V4_01_MISSING_DAY_REQUERY_R6_1.json"


def code_digest(codes: list[str]) -> str:
    return hashlib.sha256("\n".join(codes).encode("ascii")).hexdigest()


def bounded_query(client: BaoStockClient, operation: str, method: str, **kwargs):
    """Retry one provider timeout once and return sanitized failure metadata."""
    last_error = None
    for attempt in range(2):
        try:
            rows, meta = client.query_rows(operation, method, **kwargs)
            return rows, meta, attempt
        except Exception as exc:
            code = exc.provider_code if isinstance(exc, BaoStockError) else None
            last_error = {"error_code": code or "CLIENT_ERROR", "error_type": type(exc).__name__}
    return None, last_error, 1


def main() -> int:
    audit = json.loads(AUDIT.read_text(encoding="utf-8"))
    flagged = [row for row in audit["daily"] if row["missing_required_identity_count"]]
    expected_missing = {row["trade_date"]: sorted({code for codes in row["missing_codes_by_board"].values()
                                                    for code in codes}) for row in flagged}
    audit_sha = hashlib.sha256(AUDIT.read_bytes()).hexdigest()
    prior_results = []
    if OUTPUT.exists():
        prior = json.loads(OUTPUT.read_text(encoding="utf-8"))
        if prior.get("input_all_day_coverage_sha256") == audit_sha:
            prior_results = prior.get("requeried_dates", [])
    existing = {}
    with gzip.open(ROSTER, "rt", encoding="utf-8") as stream:
        for line in stream:
            row = json.loads(line)
            existing[row["trade_date"]] = set(row["source_codes"])
    for row in prior_results:
        if ("target_codes_present_in_fresh_query_1" not in row
                and row.get("fresh_query_1", {}).get("codes_sha256") == row.get("accepted_roster_codes_sha256")
                and row.get("fresh_query_2", {}).get("codes_sha256") == row.get("accepted_roster_codes_sha256")):
            absent = sorted(set(row.get("target_missing_codes", [])) & existing.get(row["trade_date"], set()))
            row["target_codes_present_in_fresh_query_1"] = absent
            row["target_codes_present_in_fresh_query_2"] = absent
        row.setdefault("target_codes_present_in_fresh_query_1", [])
        row.setdefault("target_codes_present_in_fresh_query_2", [])
    prior_by_day = {row["trade_date"]: row for row in prior_results}
    results = list(prior_results)
    client_context = (BaoStockClient(RequestBudget(LEDGER), auth_mode="PUBLIC_ANONYMOUS", timeout=30)
                      if any(day not in prior_by_day for day in expected_missing) else nullcontext())
    with client_context as client:
        for day, missing in expected_missing.items():
            if day in prior_by_day:
                continue
            fresh_runs = []
            for _ in range(2):
                rows, meta, retries = bounded_query(client, "query_all_stock", "query_all_stock", day=day,
                                                    max_rows=10_000, max_pages=10)
                if rows is None:
                    fresh_runs.append({"row_count": None, "unique_code_count": None, "duplicate_count": None,
                                       "codes_sha256": None, "codes": set(), "provider_error_code": meta["error_code"],
                                       "provider_page_count": None, "retry_count": retries,
                                       "error_type": meta["error_type"]})
                    continue
                codes = sorted({str(row.get("code", "")).strip().lower() for row in rows})
                fresh_runs.append({"row_count": len(rows), "unique_code_count": len(codes),
                                   "duplicate_count": len(rows) - len(codes),
                                   "codes_sha256": code_digest(codes), "codes": set(codes),
                                   "provider_error_code": meta.get("error_code"),
                                   "provider_page_count": meta.get("page_count"), "retry_count": retries})
            market_rows, market_meta, market_retries = bounded_query(
                client, "query_daily_history_k_AStock", "query_daily_history_k_AStock", date=day,
                max_rows=20_000, max_pages=1)
            if market_rows is None:
                market_rows, market_meta = [], market_meta
            market_codes = {str(row.get("code", "")).strip().lower() for row in market_rows}
            traded_codes = {str(row.get("code", "")).strip().lower() for row in market_rows
                            if str(row.get("tradestatus", "")) == "1"
                            and float(row.get("volume") or 0) > 0}
            targets_in_market = {str(row.get("code", "")).strip().lower(): {
                "tradestatus": row.get("tradestatus"), "volume": row.get("volume"),
                "amount": row.get("amount"), "date": row.get("date"),
            } for row in market_rows if str(row.get("code", "")).strip().lower() in missing}
            result = {
                "trade_date": day, "target_missing_codes": missing,
                "accepted_roster_codes_sha256": code_digest(sorted(existing[day])),
                "fresh_query_1": {key: value for key, value in fresh_runs[0].items() if key != "codes"},
                "fresh_query_2": {key: value for key, value in fresh_runs[1].items() if key != "codes"},
                "fresh_runs_stable": bool(fresh_runs[0]["codes_sha256"] and
                                           fresh_runs[0]["codes_sha256"] == fresh_runs[1]["codes_sha256"]),
                "fresh_query_failure_count": sum(run["codes_sha256"] is None for run in fresh_runs),
                "target_codes_present_in_roster": sorted(set(missing) & existing[day]),
                "target_codes_present_in_fresh_query_1": sorted(set(missing) & fresh_runs[0]["codes"]),
                "target_codes_present_in_fresh_query_2": sorted(set(missing) & fresh_runs[1]["codes"]),
                "target_codes_present_in_both_fresh_rosters": sorted(set(missing) & fresh_runs[0]["codes"] & fresh_runs[1]["codes"]),
                "target_codes_present_in_daily_market": sorted(set(missing) & market_codes),
                "target_codes_traded_in_daily_market": sorted(set(missing) & traded_codes),
                "target_code_daily_market_rows": targets_in_market,
                "daily_market_row_count": len(market_rows),
                "daily_market_codes_sha256": code_digest(sorted(market_codes)),
                "daily_market_provider_error_code": market_meta.get("error_code") if isinstance(market_meta, dict) else "CLIENT_ERROR",
                "daily_market_invalid_date_row_count": sum(str(row.get("date")) != day for row in market_rows),
                "daily_market_retry_count": market_retries,
                "daily_market_error_type": market_meta.get("error_type") if isinstance(market_meta, dict) else None,
            }
            results.append(result)
            checkpoint = {
                "stage": "V4-01-R6.1-MISSING-DATE-REQUERY", "contract_id": "V4_01_MISSING_DAY_REQUERY_R6_1",
                "version": "1.0.0", "observed_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
                "status": "IN_PROGRESS", "requeried_date_count": len(results), "requeried_dates": results,
                "blockers": [], "input_all_day_coverage_sha256": audit_sha,
                "requery_scope": "Only dates with a nonzero required identity miss were queried; two fresh query_all_stock sessions plus one same-day daily market crosscheck per date.",
                "auth_mode": "PUBLIC_ANONYMOUS", "request_ledger_path": str(LEDGER.relative_to(ROOT)),
            }
            _atomic_json(OUTPUT, checkpoint)
    results = [prior_by_day[day] if day in prior_by_day else next(
        row for row in results if row["trade_date"] == day) for day in expected_missing]
    blockers = []
    for result in results:
        if (not result["fresh_runs_stable"] or result["fresh_query_failure_count"]
                or result["fresh_query_1"]["duplicate_count"]
                or result["fresh_query_2"]["duplicate_count"]
                or result["fresh_query_1"]["provider_error_code"] != "0"
                or result["fresh_query_2"]["provider_error_code"] != "0"
                or result["fresh_query_1"]["codes_sha256"] != result["accepted_roster_codes_sha256"]
                or result["fresh_query_2"]["codes_sha256"] != result["accepted_roster_codes_sha256"]
                or result["target_codes_present_in_fresh_query_1"]
                or result["target_codes_present_in_fresh_query_2"]
                or result["daily_market_provider_error_code"] != "0"
                or result["daily_market_invalid_date_row_count"]):
            blockers.append(result["trade_date"])
    receipt = {
        "stage": "V4-01-R6.1-MISSING-DATE-REQUERY", "contract_id": "V4_01_MISSING_DAY_REQUERY_R6_1",
        "version": "1.0.0", "observed_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "status": "PASS" if not blockers else "BLOCKED", "requeried_date_count": len(results),
        "all_target_dates_covered": len(results) == len(expected_missing),
        "requeried_dates": results, "blockers": blockers,
        "input_all_day_coverage_sha256": audit_sha,
        "requery_scope": "Only dates with a nonzero required identity miss were queried; two fresh query_all_stock sessions plus one same-day daily market crosscheck per date.",
        "auth_mode": "PUBLIC_ANONYMOUS", "request_ledger_path": str(LEDGER.relative_to(ROOT)),
        "execution_script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "next_stage": "REPAIR_ONLY_CONFIRMED_DATES_AND_RESEAL" if not blockers else "INVESTIGATE_PROVIDER_REQUERY_ERRORS",
    }
    _atomic_json(OUTPUT, receipt)
    print(json.dumps({"status": receipt["status"], "requeried_date_count": len(results),
                      "blockers": blockers, "codes_present_in_market": sum(
                          len(row["target_codes_present_in_daily_market"]) for row in results),
                      "codes_traded": sum(len(row["target_codes_traded_in_daily_market"]) for row in results)}, ensure_ascii=False))
    return 0 if not blockers else 2


if __name__ == "__main__":
    raise SystemExit(main())
