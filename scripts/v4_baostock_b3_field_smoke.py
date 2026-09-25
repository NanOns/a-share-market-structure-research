from __future__ import annotations

"""Bounded 10+ instrument, 10-session public BaoStock field smoke (B3)."""

import argparse
import hashlib
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from workbench_analysis.baostock_supplemental import BaoStockClient, BaoStockError, RequestBudget, _atomic_json  # noqa: E402


BASE_CODES = [
    "sh.600000", "sh.600519", "sz.000001", "sz.000858",
    "sz.300750", "sz.300059", "sh.688981", "sh.688111",
]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", default="2026-09-01")
    parser.add_argument("--end", default="2026-09-14")
    parser.add_argument("--max-securities", type=int, default=14)
    parser.add_argument("--ledger", default="reports/v4_baostock/request_ledger.json")
    parser.add_argument("--receipt", default="reports/v4_baostock/public_b3_field_smoke_receipt.json")
    args = parser.parse_args()
    if args.max_securities < 10 or args.max_securities > 20 or args.start > args.end:
        raise SystemExit("B3_INPUT_BOUND_INVALID")

    ledger_path = ROOT / args.ledger
    before = json.loads(ledger_path.read_text(encoding="utf-8")) if ledger_path.exists() else {"by_shanghai_date": {}}
    before_count = sum(int(item.get("count", 0)) for item in before.get("by_shanghai_date", {}).values())
    execution_identity = {
        "input_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "script_sha256": hashlib.sha256(Path(__file__).resolve().read_bytes()).hexdigest(),
        "adapter_sha256": hashlib.sha256((ROOT / "src/workbench_analysis/baostock_supplemental.py").read_bytes()).hexdigest(),
    }
    client = BaoStockClient(RequestBudget(ledger_path), auth_mode="PUBLIC_ANONYMOUS")
    started = time.monotonic()
    samples: list[dict] = []
    failures: dict[str, str] = {}
    catalog_summary: dict = {}
    categories: dict[str, int] = {}

    try:
        with client:
            catalog_rows, catalog_meta = client.query_rows(
                "query_stock_basic", "query_stock_basic", max_rows=10_000, max_pages=10
            )
            catalog_summary = {
                "error_code": catalog_meta["error_code"],
                "row_count": len(catalog_rows),
                "page_count": catalog_meta["page_count"],
                "fields": catalog_meta["fields"],
                "rows_digest": hashlib.sha256("\n".join(
                    hashlib.sha256(json.dumps(row, ensure_ascii=False, sort_keys=True,
                                              separators=(",", ":")).encode("utf-8")).hexdigest()
                    for row in catalog_rows
                ).encode("ascii")).hexdigest(),
            }
            basic_by_code = {str(row.get("code", "")): row for row in catalog_rows}
            equity_reference = basic_by_code.get("sh.600000", {})
            equity_type = equity_reference.get("type")
            equity_status = equity_reference.get("status")

            def active_equity(row: dict[str, str]) -> bool:
                code = str(row.get("code", ""))
                return bool(code and equity_type and row.get("type") == equity_type
                            and row.get("status") == equity_status
                            and code.startswith(("sh.", "sz.", "bj.")))

            candidate_codes = list(BASE_CODES)

            def append_first(predicate) -> None:
                for row in catalog_rows:
                    code = str(row.get("code", ""))
                    if active_equity(row) and code not in candidate_codes and predicate(row):
                        candidate_codes.append(code)
                        return

            append_first(lambda row: str(row.get("code", "")).startswith("bj."))
            append_first(lambda row: "ST" in str(row.get("code_name", "")).upper())
            append_first(lambda row: ("2025-09-01" <= str(row.get("ipoDate", "")) <= args.end))
            # Fill to the minimum deterministically from provider's sorted catalog.
            for row in catalog_rows:
                code = str(row.get("code", ""))
                if active_equity(row) and code not in candidate_codes:
                    candidate_codes.append(code)
                if len(candidate_codes) >= args.max_securities:
                    break
            selected = candidate_codes[:args.max_securities]

            for code in selected:
                query_started = time.monotonic()
                try:
                    rows = client.query_daily(code, args.start, args.end)
                    per_security = {
                        "security_code": code,
                        "board": ("BEIJING" if code.startswith("bj.") else
                                  "STAR" if code.startswith("sh.68") else
                                  "CHINEXT" if code.startswith("sz.30") else
                                  "SH_MAIN" if code.startswith("sh.60") else
                                  "SZ_MAIN" if code.startswith("sz.00") else "OTHER"),
                        "instrument_type": basic_by_code.get(code, {}).get("type"),
                        "active_status": basic_by_code.get(code, {}).get("status"),
                        "matches_equity_reference_type": basic_by_code.get(code, {}).get("type") == equity_type,
                        "security_name_digest": hashlib.sha256(str(basic_by_code.get(code, {}).get("code_name", "")).encode("utf-8")).hexdigest(),
                        "ipo_date": basic_by_code.get(code, {}).get("ipoDate") or None,
                        "row_count": len(rows),
                        "first_date": min((row.trade_date for row in rows), default=None),
                        "last_date": max((row.trade_date for row in rows), default=None),
                        "is_st_row_count": sum(row.is_st == "1" for row in rows),
                        "suspended_row_count": sum(row.tradestatus == "0" for row in rows),
                        "resume_transition_observed": any(
                            prior.tradestatus == "0" and later.tradestatus == "1"
                            for prior, later in zip(rows, rows[1:])
                        ),
                        "rows_digest": hashlib.sha256("\n".join(row.source_digest for row in rows).encode("ascii")).hexdigest(),
                        "elapsed_seconds": round(time.monotonic() - query_started, 3),
                        "status": "PASS" if rows else "EMPTY_RESULT",
                    }
                    category = per_security["board"]
                    categories[category] = categories.get(category, 0) + 1
                    samples.append(per_security)
                except BaoStockError as exc:
                    failures[code] = str(exc)
                    samples.append({"security_code": code, "status": "QUERY_FAILED", "failure_reason": str(exc),
                                    "elapsed_seconds": round(time.monotonic() - query_started, 3)})
    except BaoStockError as exc:
        failures["session_or_catalog"] = str(exc)

    after = json.loads(ledger_path.read_text(encoding="utf-8")) if ledger_path.exists() else {"by_shanghai_date": {}}
    after_count = sum(int(item.get("count", 0)) for item in after.get("by_shanghai_date", {}).values())
    today = datetime.now(ZoneInfo("Asia/Shanghai")).date().isoformat()
    successful = [item for item in samples if item.get("status") == "PASS"]
    observed = {
        "security_count": len(successful),
        "board_categories": categories,
        "st_in_sample": sum(int(item.get("is_st_row_count", 0)) > 0 for item in successful),
        "halted_rows_in_sample": sum(int(item.get("suspended_row_count", 0)) for item in successful),
        "resume_transitions_in_sample": sum(bool(item.get("resume_transition_observed")) for item in successful),
        "recent_ipo_in_sample": sum(str(item.get("ipo_date") or "") >= "2025-09-01" for item in successful),
        "no_action_empirical_sample": "NOT_ESTABLISHED_BY_THIS_FIELD_SMOKE",
    }
    passed = len(successful) >= 10 and catalog_summary.get("error_code") == "0"
    payload = {
        "stage": "V4-01/02-BAOSTOCK-PUBLIC-B3-FIELD-SMOKE",
        "contract_id": "BAOSTOCK_PUBLIC_RUNTIME_ROUTE_V1",
        "observed_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "auth_mode": "PUBLIC_ANONYMOUS",
        "runtime": client.runtime_endpoint,
        "login": client.login_result,
        "logout": client.logout_result,
        "query_range": {"start_date": args.start, "end_date": args.end, "adjustflag": "3", "frequency": "d"},
        "requested_fields": ["date", "code", "close", "volume", "amount", "turn", "tradestatus", "isST"],
        "catalog": catalog_summary,
        "samples": samples,
        "observed_coverage": observed,
        "catalog_classification": {"equity_reference_code": "sh.600000", "equity_reference_type": equity_type,
                                   "equity_reference_status": equity_status,
                                   "classification_rule": "provider type/status values are interpreted relative to verified query_stock_basic(sh.600000) reference row"},
        "failures": failures,
        "request_count_delta": after_count - before_count,
        "request_counts_for_shanghai_day": after.get("by_shanghai_date", {}).get(today, {}),
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "raw_payload_persisted": False,
        "execution_identity": execution_identity,
        "status": "B3_SMOKE_PASS_WITH_ACCEPTANCE_GAPS" if passed else "B3_SMOKE_BLOCKED",
        "capability": "PUBLIC_ROUTE_OPERATIONAL_FIELD_ACCEPTANCE_PENDING",
    }
    _atomic_json(ROOT / args.receipt, payload)
    print(json.dumps({"status": payload["status"], "selected": len(samples), "successful": len(successful),
                      "observed_coverage": observed, "requests": after_count - before_count,
                      "receipt": str((ROOT / args.receipt).relative_to(ROOT))}, ensure_ascii=False))
    return 0 if passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
