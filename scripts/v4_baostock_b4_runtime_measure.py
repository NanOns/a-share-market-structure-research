from __future__ import annotations

"""Measure a bounded two-year single-name and one-day full-market request."""

import argparse
import hashlib
import importlib.metadata
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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--code", default="sh.600000")
    parser.add_argument("--start", default="2024-09-25")
    parser.add_argument("--end", default="2026-09-24")
    parser.add_argument("--market-day", default="2026-09-07")
    parser.add_argument("--b1-receipt", default="reports/v4_baostock/public_b1_093_clean_venv_receipt.json")
    parser.add_argument("--ledger", default="reports/v4_baostock/request_ledger.json")
    parser.add_argument("--receipt", default="reports/v4_baostock/public_b4_runtime_measurement.json")
    args = parser.parse_args()

    b1_path = ROOT / args.b1_receipt
    b1 = json.loads(b1_path.read_text(encoding="utf-8"))
    if b1.get("status") != "PUBLIC_CAPABILITY_B1_093_PASS":
        raise SystemExit("B4_NOT_RUN_B1_GATE_NOT_PASSED")
    ledger_path = ROOT / args.ledger
    before = json.loads(ledger_path.read_text(encoding="utf-8")) if ledger_path.exists() else {"by_shanghai_date": {}}
    before_count = sum(int(item.get("count", 0)) for item in before.get("by_shanghai_date", {}).values())
    client = BaoStockClient(RequestBudget(ledger_path), auth_mode="PUBLIC_ANONYMOUS")
    started = time.monotonic()
    measurements: dict[str, dict] = {}
    failure = None
    try:
        with client:
            one_started = time.monotonic()
            history = client.query_daily(args.code, args.start, args.end)
            measurements["one_security_two_year"] = {
                "security_code": args.code,
                "start_date": args.start,
                "end_date": args.end,
                "request_count": 1,
                "row_count": len(history),
                "first_date": min((row.trade_date for row in history), default=None),
                "last_date": max((row.trade_date for row in history), default=None),
                "rows_digest": hashlib.sha256("\n".join(row.source_digest for row in history).encode("ascii")).hexdigest(),
                "elapsed_seconds": round(time.monotonic() - one_started, 3),
                "rows_per_second": round(len(history) / max(time.monotonic() - one_started, 0.001), 2),
            }

            market_started = time.monotonic()
            market_rows, market_meta = client.query_rows(
                "query_daily_history_k_AStock", "query_daily_history_k_AStock",
                date=args.market_day, max_rows=20_000, max_pages=1,
            )
            measurements["full_market_single_day"] = {
                "date": args.market_day,
                "request_count": 1,
                "row_count": len(market_rows),
                "fields": market_meta["fields"],
                "page_count": market_meta["page_count"],
                "rows_digest": hashlib.sha256("\n".join(
                    hashlib.sha256(json.dumps(row, ensure_ascii=False, sort_keys=True,
                                             separators=(",", ":")).encode("utf-8")).hexdigest()
                    for row in market_rows
                ).encode("ascii")).hexdigest(),
                "elapsed_seconds": round(time.monotonic() - market_started, 3),
                "rows_per_second": round(len(market_rows) / max(time.monotonic() - market_started, 0.001), 2),
            }
    except BaoStockError as exc:
        failure = str(exc)

    after = json.loads(ledger_path.read_text(encoding="utf-8")) if ledger_path.exists() else {"by_shanghai_date": {}}
    after_count = sum(int(item.get("count", 0)) for item in after.get("by_shanghai_date", {}).values())
    today = datetime.now(ZoneInfo("Asia/Shanghai")).date().isoformat()
    success = (failure is None and client.login_result.get("error_code") == "0"
               and client.logout_result.get("error_code") == "0"
               and set(measurements) == {"one_security_two_year", "full_market_single_day"})
    payload = {
        "stage": "V4-01/02-BAOSTOCK-PUBLIC-B4-RUNTIME-MEASURE",
        "contract_id": "BAOSTOCK_PUBLIC_RUNTIME_CONTRACT_V1",
        "observed_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "auth_mode": "PUBLIC_ANONYMOUS",
        "runtime": {"package": "baostock", "version": importlib.metadata.version("baostock"),
                    "python": sys.version.split()[0], **client.runtime_endpoint},
        "login": client.login_result,
        "logout": client.logout_result,
        "measurements": measurements,
        "request_count_delta": after_count - before_count,
        "request_counts_for_shanghai_day": after.get("by_shanghai_date", {}).get(today, {}),
        "session_elapsed_seconds": round(time.monotonic() - started, 3),
        "b1_receipt_sha256": hashlib.sha256(b1_path.read_bytes()).hexdigest(),
        "execution_identity": {
            "input_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
            "script_sha256": hashlib.sha256(Path(__file__).resolve().read_bytes()).hexdigest(),
            "adapter_sha256": hashlib.sha256((ROOT / "src/workbench_analysis/baostock_supplemental.py").read_bytes()).hexdigest(),
        },
        "raw_payload_persisted": False,
        "failure": failure,
        "status": "B4_RUNTIME_MEASURED_FIELD_ACCEPTANCE_PENDING" if success else "B4_RUNTIME_BLOCKED",
    }
    _atomic_json(ROOT / args.receipt, payload)
    print(json.dumps({"status": payload["status"], "measurements": measurements,
                      "requests": after_count - before_count}, ensure_ascii=False))
    return 0 if success else 2


if __name__ == "__main__":
    raise SystemExit(main())
