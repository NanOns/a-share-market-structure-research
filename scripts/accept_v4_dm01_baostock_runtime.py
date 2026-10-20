from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, time, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from workbench_analysis.baostock_daily_update_source import (  # noqa: E402
    DAILY_METHOD,
    FACTOR_METHOD,
    _canonical_rows_digest,
    _validate_daily_rows,
    _validate_factor_rows,
)
from workbench_analysis.baostock_runtime_acceptance import (  # noqa: E402
    build_runtime_acceptance_manifest,
)
from workbench_analysis.baostock_supplemental import (  # noqa: E402
    BaoStockClient,
    BaoStockError,
    RequestBudget,
    package_metadata,
)
from workbench_analysis.daily_data_head import write_json_atomic  # noqa: E402
from workbench_analysis.market_source_acquisition import official_sessions  # noqa: E402
from common.paths import resolve_baostock_cache_root, resolve_baostock_request_ledger, resolve_tdx_root  # noqa: E402


SHANGHAI = ZoneInfo("Asia/Shanghai")
BASE_CUTOFF = "2026-09-24"
REQUIRED_DAILY_FIELDS = {"date", "code", "open", "high", "low", "close", "volume", "amount", "tradestatus", "isST"}
REQUIRED_FACTOR_FIELDS = {"code", "dividOperateDate", "foreAdjustFactor", "backAdjustFactor", "adjustFactor"}


def _record(method: str, rows: list[dict[str, str]], metadata: dict[str, object], required: set[str], target: str) -> dict:
    fields = list(metadata.get("fields") or [])
    if not required.issubset(fields):
        raise ValueError("BAOSTOCK_LIVE_SMOKE_REQUIRED_FIELDS_MISSING")
    if metadata.get("provider_date") != target:
        raise ValueError("BAOSTOCK_LIVE_SMOKE_PROVIDER_DATE_MISMATCH")
    return {
        "method": method,
        "provider_date": metadata["provider_date"],
        "row_count": len(rows),
        "fields": fields,
        "response_sha256": _canonical_rows_digest(rows),
        "page_count": metadata.get("page_count"),
        "error_code": metadata.get("error_code"),
    }


def _ledger_count(path: Path, target_date: str) -> int:
    try:
        ledger = json.loads(path.read_text(encoding="utf-8"))
        return int(ledger.get("by_shanghai_date", {}).get(target_date, {}).get("count", 0))
    except (OSError, ValueError, TypeError):
        return 0


def _target_is_official_session(root: Path, target_date: str, *, sessions_reader=None) -> bool:
    """Use the accepted PG calendar; do not treat an old receipt as current authority."""
    if target_date <= BASE_CUTOFF:
        return False
    reader = sessions_reader or official_sessions
    return target_date in reader(root)


def runtime_acceptance_cache_dir(root: Path, target_date: str) -> Path:
    """Place bounded runtime-ingress receipts under the configured BaoStock cache."""
    return resolve_baostock_cache_root(root) / "baostock" / target_date.replace("-", "") / "runtime_acceptance"


def main() -> int:
    parser = argparse.ArgumentParser(description="Accept only the bounded, exact-date BaoStock DM-01 DailyUpdates runtime.")
    parser.add_argument("--target-date", required=True)
    parser.add_argument("--ledger", type=Path)
    args = parser.parse_args()
    try:
        datetime.strptime(args.target_date, "%Y-%m-%d")
    except ValueError:
        print(json.dumps({"status": "BLOCKED", "reason": "TARGET_DATE_INVALID"}, ensure_ascii=False))
        return 2

    now = datetime.now(timezone.utc).replace(microsecond=0)
    local_now = now.astimezone(SHANGHAI)
    if local_now.date().isoformat() != args.target_date or local_now.time() < time(15, 0):
        print(json.dumps({"status": "WAIT_MARKET_CLOSE", "target_date": args.target_date,
                          "observed_at": now.isoformat(), "auth_mode": "PUBLIC_ANONYMOUS",
                          "request_count": 0}, ensure_ascii=False))
        return 2

    try:
        official_session = _target_is_official_session(ROOT, args.target_date)
    except (OSError, RuntimeError, ValueError) as exc:
        print(json.dumps({"status": "BLOCKED_OFFICIAL_SESSION_NOT_VERIFIED",
                          "reason": str(exc)[:160]}, ensure_ascii=False))
        return 2
    if not official_session:
        print(json.dumps({"status": "BLOCKED_OFFICIAL_SESSION_NOT_VERIFIED", "target_date": args.target_date},
                         ensure_ascii=False))
        return 2

    args.ledger = resolve_baostock_request_ledger(ROOT, args.ledger)

    receipt_dir = runtime_acceptance_cache_dir(ROOT, args.target_date)
    smoke_path = receipt_dir / "live_smoke_receipt.json"
    manifest_path = receipt_dir / "accepted_runtime_manifest.json"
    runtime = package_metadata()
    request_count_before = _ledger_count(args.ledger, args.target_date)
    receipt: dict = {
        "contract_id": "BAOSTOCK_DAILY_UPDATE_LIVE_SMOKE_V1",
        "version": "1.0.0",
        "status": "FAIL",
        "target_date": args.target_date,
        "observed_at": now.isoformat(),
        "auth_mode": "PUBLIC_ANONYMOUS",
        "runtime": {key: runtime[key] for key in ("package", "version", "installed_python_sources_sha256")},
        "live_smoke": None,
        "request_count": 0,
        "tdx_root_write_count": 0,
    }
    try:
        budget = RequestBudget(ROOT / args.ledger)
        with BaoStockClient(budget, auth_mode="PUBLIC_ANONYMOUS", allow_unaccepted_runtime_smoke=True) as client:
            daily_rows, daily_meta = client.query_rows(
                "dm01_runtime_smoke_daily", DAILY_METHOD, date=args.target_date, max_rows=20_000, max_pages=1
            )
            factor_rows, factor_meta = client.query_rows(
                "dm01_runtime_smoke_adjustment_factor", FACTOR_METHOD, date=args.target_date,
                max_rows=20_000, max_pages=1,
            )
            _validate_daily_rows(daily_rows, args.target_date)
            _validate_factor_rows(factor_rows, args.target_date)
            if not daily_rows:
                raise ValueError("BAOSTOCK_LIVE_SMOKE_NO_TARGET_DATE_DAILY_ROWS")
            live_smoke = {
                "status": "PASS",
                "target_date": args.target_date,
                "auth_mode": client.auth_mode,
                "endpoint": dict(client.runtime_endpoint),
                "daily": _record(DAILY_METHOD, daily_rows, daily_meta, REQUIRED_DAILY_FIELDS, args.target_date),
                "adjustment_factor": _record(FACTOR_METHOD, factor_rows, factor_meta,
                                              REQUIRED_FACTOR_FIELDS, args.target_date),
            }
            receipt.update({"status": "PASS", "live_smoke": live_smoke})
    except (BaoStockError, ValueError, OSError) as exc:
        receipt["reason"] = str(exc)[:160]
    receipt["request_count"] = max(0, _ledger_count(args.ledger, args.target_date) - request_count_before)
    receipt["request_ledger_path"] = args.ledger.relative_to(ROOT).as_posix() if args.ledger.is_relative_to(ROOT) else str(args.ledger)

    tdx_root = resolve_tdx_root(ROOT)
    receipt_digest = write_json_atomic(smoke_path, receipt, tdx_root=tdx_root)
    if receipt["status"] != "PASS":
        print(json.dumps({"status": "WAIT_BAOSTOCK_DAILY_UPDATE", "reason": receipt.get("reason"),
                          "smoke_receipt": str(smoke_path), "smoke_receipt_sha256": receipt_digest},
                         ensure_ascii=False))
        return 2
    manifest = build_runtime_acceptance_manifest(
        sdk=runtime,
        auth_mode=receipt["auth_mode"],
        live_smoke=receipt["live_smoke"],
        smoke_receipt_path=smoke_path.relative_to(ROOT).as_posix(),
        smoke_receipt_sha256=receipt_digest,
    )
    manifest_digest = write_json_atomic(manifest_path, manifest, tdx_root=tdx_root)
    print(json.dumps({"status": "ACCEPTED", "target_date": args.target_date,
                      "auth_mode": receipt["auth_mode"], "sdk_version": runtime["version"],
                      "installed_source_sha256": runtime["installed_python_sources_sha256"],
                      "live_smoke_receipt": str(smoke_path), "live_smoke_receipt_sha256": receipt_digest,
                      "runtime_manifest": str(manifest_path), "runtime_manifest_sha256": manifest_digest},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
