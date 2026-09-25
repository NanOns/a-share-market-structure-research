from __future__ import annotations

"""Run the staged BaoStock public-route B0/B1 probes without credentials."""

import argparse
import hashlib
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from workbench_analysis.baostock_supplemental import (  # noqa: E402
    BaoStockClient,
    BaoStockError,
    RequestBudget,
    _atomic_json,
    package_metadata,
)


def digest_rows(rows: list[dict]) -> str:
    encoded = [json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) for row in rows]
    return hashlib.sha256("\n".join(encoded).encode("utf-8")).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", choices=("B0", "B1"), default="B0")
    parser.add_argument("--ledger", default="reports/v4_baostock/request_ledger.json")
    parser.add_argument("--b0-receipt", default="reports/v4_baostock/public_b0_history_receipt.json")
    parser.add_argument("--receipt", default=None)
    parser.add_argument("--code", default="sh.600000")
    parser.add_argument("--start", default="2026-09-01")
    parser.add_argument("--end", default="2026-09-07")
    parser.add_argument("--metadata-day", default="2026-09-07")
    args = parser.parse_args()

    ledger_path = ROOT / args.ledger
    receipt_path = ROOT / (args.receipt or (
        "reports/v4_baostock/public_b0_history_receipt.json" if args.stage == "B0"
        else "reports/v4_baostock/public_b1_cross_interface_receipt.json"
    ))
    if args.stage == "B1":
        b0_path = ROOT / args.b0_receipt
        b0_receipt = json.loads(b0_path.read_text(encoding="utf-8"))
        if b0_receipt.get("status") != "PUBLIC_ROUTE_B0_PASS":
            raise SystemExit("B1_NOT_RUN_B0_GATE_NOT_PASSED")
    else:
        b0_path = None
        b0_receipt = None

    before_payload = json.loads(ledger_path.read_text(encoding="utf-8")) if ledger_path.exists() else {"by_shanghai_date": {}}
    calls_before = sum(int(item.get("count", 0)) for item in before_payload.get("by_shanghai_date", {}).values())
    execution_identity = {
        "input_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "script_sha256": hashlib.sha256(Path(__file__).resolve().read_bytes()).hexdigest(),
        "adapter_sha256": hashlib.sha256((ROOT / "src/workbench_analysis/baostock_supplemental.py").read_bytes()).hexdigest(),
        "contract_sha256": hashlib.sha256((ROOT / "config/baostock_supplemental_contract_v1.json").read_bytes()).hexdigest(),
    }
    client = BaoStockClient(RequestBudget(ledger_path), auth_mode="PUBLIC_ANONYMOUS")
    started = time.monotonic()
    query_results: dict[str, dict] = {}
    row_counts: dict[str, int] = {}
    row_digests: dict[str, str] = {}
    date_ranges: dict[str, dict] = {}
    failure: dict | None = None

    def run_query(name: str, callback):
        nonlocal failure
        try:
            return callback()
        except BaoStockError as exc:
            query_results[name] = dict(client.last_query_result)
            if failure is None:
                failure = {"client_error": str(exc), "provider_error_code": exc.provider_code,
                           "provider_error_msg": client._safe_message(exc.provider_message)}
            else:
                failure.setdefault("query_failures", {})[name] = {
                    "client_error": str(exc), "provider_error_code": exc.provider_code,
                    "provider_error_msg": client._safe_message(exc.provider_message),
                }
            return None

    try:
        with client:
            if args.stage == "B0":
                rows = run_query("history", lambda: client.query_daily(args.code, args.start, args.end))
                if rows is not None:
                    query_results["history"] = dict(client.last_query_result)
                    row_counts["history"] = len(rows)
                    row_digests["history"] = hashlib.sha256("\n".join(row.source_digest for row in rows).encode("ascii")).hexdigest()
                    dates = sorted({row.trade_date for row in rows})
                    date_ranges["history"] = {"first": dates[0] if dates else None, "last": dates[-1] if dates else None}
            else:
                basic_rows = run_query("stock_basic", lambda: client.probe_stock_basic(args.code))
                if basic_rows is not None:
                    query_results["stock_basic"] = dict(client.last_query_result)
                    row_counts["stock_basic"] = len(basic_rows)
                    row_digests["stock_basic"] = digest_rows(basic_rows)

                calendar_pair = run_query("trade_dates", lambda: client.probe_trade_dates(args.start, args.end))
                if calendar_pair is not None:
                    calendar_rows, calendar_result = calendar_pair
                    query_results["trade_dates"] = calendar_result
                    row_counts["trade_dates"] = len(calendar_rows)
                    row_digests["trade_dates"] = digest_rows(calendar_rows)
                    dates = sorted(str(row.get("calendar_date", "")) for row in calendar_rows if row.get("is_trading_day") == "1")
                    date_ranges["trade_dates"] = {"first_trading_day": dates[0] if dates else None,
                                                   "last_trading_day": dates[-1] if dates else None}

                all_stock_pair = run_query("all_stock", lambda: client.probe_all_stock(args.metadata_day))
                if all_stock_pair is not None:
                    all_stock_rows, all_stock_result = all_stock_pair
                    query_results["all_stock"] = all_stock_result
                    row_counts["all_stock"] = len(all_stock_rows)
                    row_digests["all_stock"] = digest_rows(all_stock_rows)
                    date_ranges["all_stock"] = {"as_of": args.metadata_day}
    except BaoStockError as exc:
        failure = {
            "client_error": str(exc),
            "provider_error_code": exc.provider_code,
            "provider_error_msg": client._safe_message(exc.provider_message),
        }
        if client.last_query_result.get("error_code") not in ("NOT_ATTEMPTED", "0"):
            query_results.setdefault("last_failed_query", dict(client.last_query_result))

    checks = {name: item.get("error_code") == "0" and row_counts.get(name, 0) > 0
              for name, item in query_results.items() if name != "last_failed_query"}
    if args.stage == "B0":
        status = "PUBLIC_ROUTE_B0_PASS" if client.login_result.get("error_code") == "0" and checks.get("history", False) else "PUBLIC_ROUTE_B0_BLOCKED"
    else:
        expected = {"stock_basic", "trade_dates", "all_stock"}
        status = "PUBLIC_CAPABILITY_B1_PASS" if expected.issubset(checks) and all(checks[name] for name in expected) else "PUBLIC_CAPABILITY_B1_BLOCKED"

    after_payload = json.loads(ledger_path.read_text(encoding="utf-8")) if ledger_path.exists() else {"by_shanghai_date": {}}
    calls_after = sum(int(item.get("count", 0)) for item in after_payload.get("by_shanghai_date", {}).values())
    today = datetime.now().astimezone().date().isoformat()
    payload = {
        "stage": "V4-01/02-BAOSTOCK-PUBLIC-ROUTE-" + args.stage,
        "contract_id": "BAOSTOCK_PUBLIC_RUNTIME_ROUTE_V1",
        "observed_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "auth_mode": "PUBLIC_ANONYMOUS",
        "api_key_setter_called": False,
        "user_credentials_passed": False,
        "runtime": package_metadata(),
        "endpoint": {"auth_mode": "PUBLIC_ANONYMOUS", **client.runtime_endpoint},
        "login": dict(client.login_result),
        "logout": dict(client.logout_result),
        "queries": query_results,
        "row_counts": row_counts,
        "row_digests": row_digests,
        "returned_date_ranges": date_ranges,
        "request_count_delta": calls_after - calls_before,
        "request_counts_for_shanghai_day": after_payload.get("by_shanghai_date", {}).get(today, {}),
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "raw_payload_persisted": False,
        "failure": failure,
        "execution_identity": execution_identity,
        "b0_evidence": ({"receipt": b0_path.relative_to(ROOT).as_posix(),
                         "receipt_sha256": hashlib.sha256(b0_path.read_bytes()).hexdigest(),
                         "status": b0_receipt.get("status")} if b0_path else None),
        "status": status,
        "capability": ("PUBLIC_ROUTE_B0_PASS_PENDING_B1" if args.stage == "B0" and status.endswith("PASS")
                       else "OPERATIONAL" if args.stage == "B1" and status.endswith("PASS") else "UNVERIFIED_OR_BLOCKED"),
    }
    _atomic_json(receipt_path, payload)
    print(json.dumps({"status": status, "row_counts": row_counts,
                      "endpoint": payload["endpoint"], "receipt": receipt_path.relative_to(ROOT).as_posix()}, ensure_ascii=False))
    return 0 if status.endswith("PASS") else 2


if __name__ == "__main__":
    raise SystemExit(main())
