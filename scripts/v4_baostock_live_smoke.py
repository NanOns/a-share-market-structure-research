from __future__ import annotations

"""Perform one bounded, secret-free BaoStock connectivity/field smoke run.

Secrets must be supplied in BAOSTOCK_USERNAME, BAOSTOCK_PASSWORD and
BAOSTOCK_API_KEY. The output records metadata/counts/digests only; no raw rows.
"""

import argparse
import hashlib
import hashlib
import json
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from workbench_analysis.baostock_supplemental import (  # noqa: E402
    BaoStockClient,
    BaoStockError,
    RequestBudget,
    _atomic_json,
    package_metadata,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--code", default="sh.600000")
    parser.add_argument("--probe", choices=("daily", "basic"), default="daily")
    parser.add_argument("--start", default="2026-09-01")
    parser.add_argument("--end", default="2026-09-07")
    parser.add_argument("--ledger", default="reports/v4_baostock/request_ledger.json")
    parser.add_argument("--receipt", default="reports/v4_baostock/live_smoke_receipt.json")
    args = parser.parse_args()

    started = time.monotonic()
    ledger_path = ROOT / args.ledger
    execution_identity = {
        "input_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "script_sha256": hashlib.sha256(Path(__file__).resolve().read_bytes()).hexdigest(),
        "adapter_sha256": hashlib.sha256((ROOT / "src/workbench_analysis/baostock_supplemental.py").read_bytes()).hexdigest(),
        "contract_sha256": hashlib.sha256((ROOT / "config/baostock_supplemental_contract_v1.json").read_bytes()).hexdigest(),
    }
    try:
        if ledger_path.exists():
            before_payload = json.loads(ledger_path.read_text(encoding="utf-8"))
            calls_before = sum(int(item.get("count", 0)) for item in before_payload.get("by_shanghai_date", {}).values())
        else:
            calls_before = 0
        with BaoStockClient(RequestBudget(ledger_path)) as client:
            if args.probe == "basic":
                basic_rows = client.probe_stock_basic(args.code)
                rows = []
                result_digests = [hashlib.sha256(json.dumps(row, sort_keys=True, ensure_ascii=False).encode()).hexdigest() for row in basic_rows]
            else:
                rows = client.query_daily(args.code, args.start, args.end)
                basic_rows = []
                result_digests = [row.source_digest for row in rows]
        calls = json.loads(ledger_path.read_text(encoding="utf-8"))["by_shanghai_date"]
        calls_after = sum(int(item["count"]) for item in calls.values())
        payload = {
            "stage": "V4-01/02-BAOSTOCK-LIVE-SMOKE",
            "contract_id": "BAOSTOCK_SUPPLEMENTAL_SOURCE_V1",
            "contract_version": "1.0.0",
            "field_map_version": "BAOSTOCK_FIELD_MAP_V1",
            "observed_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            "runtime": package_metadata(),
            "execution_identity": execution_identity,
            "endpoint": "vip-api.baostock.com",
            "transport": "Baostock SDK TCP socket",
            "auth_mode": "API_KEY",
            "credential_present": True,
            "credential_storage": "process_environment_only",
            "query": {"probe": args.probe, "code": args.code, "start_date": args.start, "end_date": args.end, "frequency": "d", "adjustflag": "3"},
            "fields": (["code", "code_name", "ipoDate", "outDate", "type", "status"] if args.probe == "basic" else ["date", "code", "close", "volume", "amount", "turn", "tradestatus", "isST"]),
            "row_count": len(basic_rows) if args.probe == "basic" else len(rows),
            "returned_dates": sorted({row.trade_date for row in rows}) if args.probe == "daily" else [],
            "rows_digest": hashlib.sha256("\n".join(result_digests).encode("ascii")).hexdigest(),
            "raw_payload_persisted": False,
            "request_count_delta": calls_after - calls_before,
            "elapsed_seconds": round(time.monotonic() - started, 3),
            "status": "SMOKE_PASS" if (rows or basic_rows) else "BLOCKED_EMPTY_RESULT",
            "capability": "UNAVAILABLE_PENDING_INDEPENDENT_ACCEPTANCE",
        }
        receipt = ROOT / args.receipt
        receipt.parent.mkdir(parents=True, exist_ok=True)
        temp = receipt.with_suffix(receipt.suffix + ".tmp")
        temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        temp.replace(receipt)
        print(json.dumps({"status": payload["status"], "row_count": payload["row_count"], "receipt": str(receipt.relative_to(ROOT))}, ensure_ascii=False))
        return 0 if payload["status"] == "SMOKE_PASS" else 2
    except BaoStockError as exc:
        ledger_snapshot = {}
        if ledger_path.exists():
            ledger_snapshot = json.loads(ledger_path.read_text(encoding="utf-8"))
        today_bucket = ledger_snapshot.get("by_shanghai_date", {}).get(
            datetime.now(ZoneInfo("Asia/Shanghai")).date().isoformat(), {}
        )
        safe_code = re.search(r"(BAOSTOCK_(?:BASIC_)?QUERY_FAILED_CODE_[A-Za-z0-9_-]+)", str(exc))
        payload = {
            "stage": "V4-01/02-BAOSTOCK-LIVE-SMOKE",
            "contract_id": "BAOSTOCK_SUPPLEMENTAL_SOURCE_V1",
            "field_map_version": "BAOSTOCK_FIELD_MAP_V1",
            "observed_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            "runtime": package_metadata(),
            "execution_identity": execution_identity,
            "credential_present": BaoStockClient.credentials_present(),
            "credential_storage": "process_environment_only",
            "endpoint": "vip-api.baostock.com",
            "transport": "Baostock SDK TCP socket",
            "auth_mode": "API_KEY",
            "probe": args.probe,
            "query": {"code": args.code, "start_date": args.start, "end_date": args.end, "frequency": "d", "adjustflag": "3"},
            "request_counts_for_shanghai_day": today_bucket,
            "login_status": "PASS" if int(today_bucket.get("operations", {}).get("login", 0)) == int(today_bucket.get("operations", {}).get("logout", -1)) else "UNKNOWN",
            "data_query_status": "BLOCKED_PROVIDER_ERROR" if safe_code else "BLOCKED",
            "status": "BLOCKED",
            "failure_reason": safe_code.group(1) if safe_code else str(exc),
            "credential_values_emitted": False,
            "raw_payload_persisted": False,
            "capability": "UNAVAILABLE_PENDING_INDEPENDENT_ACCEPTANCE",
        }
        _atomic_json(ROOT / args.receipt, payload)
        print(json.dumps({"status": "BLOCKED", "reason": str(exc), "credential_values_emitted": False}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
