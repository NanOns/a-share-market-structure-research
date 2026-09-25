from __future__ import annotations

"""Bounded historical supplemental-field materialization (B5).

Only turn/tradestatus/isST and a price fingerprint are persisted. The output is
append-only and is explicitly excluded from the local TDX price authority.
"""

import argparse
import hashlib
import importlib.metadata
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from workbench_analysis.baostock_supplemental import BaoStockClient, RequestBudget, _atomic_json  # noqa: E402
from tdx.day_reader import DAY_STRUCT


SNAPSHOT_ID = "1644752b002fdeb4f3d3a2968b9c77729f27efcdae8923ad14d814abe5c78c70"


def local_rows(code: str, start: str, end: str) -> dict[int, dict[str, float | int]]:
    market, number = code.split(".", 1)
    path = ROOT / "data/v4/local_tdx_snapshots" / SNAPSHOT_ID / market / "lday" / f"{market}{number}.day"
    rows: dict[int, dict[str, float | int]] = {}
    if not path.is_file():
        return rows
    lower, upper = int(start.replace("-", "")), int(end.replace("-", ""))
    raw = path.read_bytes()
    if len(raw) % DAY_STRUCT.size:
        raise SystemExit("B5_LOCAL_DAY_FILE_INVALID")
    for trade_date, open_, high, low, close, amount, volume, _ in DAY_STRUCT.iter_unpack(raw):
        if lower <= trade_date <= upper:
            rows[trade_date] = {"close": close / 100.0, "volume": volume, "amount": float(amount)}
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--code", default="sh.600000")
    parser.add_argument("--start", default="2025-09-01")
    parser.add_argument("--end", default="2025-09-30")
    parser.add_argument("--ledger", default="reports/v4_baostock/request_ledger.json")
    parser.add_argument("--output-dir", default="reports/v4_baostock/supplements")
    parser.add_argument("--receipt", default="reports/v4_baostock/public_b5_supplement_bootstrap_receipt.json")
    args = parser.parse_args()
    if args.start > args.end or "." not in args.code:
        raise SystemExit("B5_INPUT_INVALID")

    ledger_path = ROOT / args.ledger
    before = json.loads(ledger_path.read_text(encoding="utf-8")) if ledger_path.exists() else {"by_shanghai_date": {}}
    before_count = sum(int(x.get("count", 0)) for x in before.get("by_shanghai_date", {}).values())
    client = BaoStockClient(RequestBudget(ledger_path), auth_mode="PUBLIC_ANONYMOUS")
    started = time.monotonic()
    rows = []
    failure = None
    try:
        with client:
            rows = client.query_daily(args.code, args.start, args.end)
    except Exception as exc:
        failure = type(exc).__name__ + ":" + str(exc)

    local = local_rows(args.code, args.start, args.end)
    materialized = []
    for row in rows:
        day = int(row.trade_date.replace("-", ""))
        price_fp = hashlib.sha256(json.dumps({
            "code": row.query_code, "date": row.trade_date,
            "close": row.close_price_cny, "volume": row.volume_shares,
            "amount": row.amount_cny,
        }, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        candidate = local.get(day)
        exact = bool(candidate and candidate["close"] == row.close_price_cny
                     and candidate["volume"] == row.volume_shares
                     and candidate["amount"] == row.amount_cny)
        materialized.append({
            "security_code": row.query_code,
            "trade_date": row.trade_date,
            "turn_fraction": row.turn_fraction,
            "tradestatus": row.tradestatus,
            "is_st": row.is_st,
            "price_fingerprint_sha256": price_fp,
            "local_price_fingerprint_match": exact if candidate else None,
            "binding_status": "BOUND_SOFT" if exact else "UNBOUND",
            "source_row_digest": row.source_digest,
        })

    observed = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    identity = {
        "input_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    }
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "_" + hashlib.sha256(
        f"{args.code}|{args.start}|{args.end}|{observed}".encode()).hexdigest()[:8]
    out = ROOT / args.output_dir / f"{run_id}_{args.code.replace('.', '_')}_{args.start}_{args.end}.json"
    payload = {
        "supplement_contract_id": "BAOSTOCK_HISTORICAL_SUPPLEMENT_V1",
        "run_id": run_id,
        "created_at_utc": observed,
        "source": "BAOSTOCK_PUBLIC_ANONYMOUS",
        "auth_mode": "PUBLIC_ANONYMOUS",
        "package_version": importlib.metadata.version("baostock"),
        "security_code": args.code,
        "date_range": {"start": args.start, "end": args.end},
        "fields": ["turn_fraction", "tradestatus", "is_st", "price_fingerprint_sha256"],
        "authority": "SUPPLEMENT_ONLY_TDX_REMAINS_PRICE_AUTHORITY",
        "raw_provider_payload_persisted": False,
        "binding": "BOUND_SOFT_OR_UNBOUND_NO_CORE_EFFECT",
        "row_count": len(materialized),
        "rows": materialized,
        "failure": failure,
        "execution_identity": identity,
    }
    if out.exists():
        raise SystemExit("B5_APPEND_ONLY_TARGET_ALREADY_EXISTS")
    _atomic_json(out, payload)
    digest = hashlib.sha256(out.read_bytes()).hexdigest()
    after = json.loads(ledger_path.read_text(encoding="utf-8")) if ledger_path.exists() else {"by_shanghai_date": {}}
    after_count = sum(int(x.get("count", 0)) for x in after.get("by_shanghai_date", {}).values())
    success = failure is None and bool(rows) and client.login_result.get("error_code") == "0"
    receipt = {
        "stage": "V4-01/02-BAOSTOCK-PUBLIC-B5-SUPPLEMENT-BOOTSTRAP",
        "contract_id": "BAOSTOCK_HISTORICAL_SUPPLEMENT_V1",
        "observed_at_utc": observed,
        "status": "B5_SUPPLEMENT_MATERIALIZED_BINDING_UNACCEPTED" if success else "B5_BLOCKED",
        "artifact_path": str(out.relative_to(ROOT)).replace("\\", "/"),
        "artifact_sha256": digest,
        "row_count": len(materialized),
        "matched_local_fingerprint_rows": sum(row["local_price_fingerprint_match"] is True for row in materialized),
        "local_snapshot_id": SNAPSHOT_ID,
        "request_count_delta": after_count - before_count,
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "login": client.login_result,
        "logout": client.logout_result,
        "failure": failure,
        "execution_identity": identity,
        "acceptance_gaps": ["independent field/unit acceptance", "BOUND_STRICT tolerance acceptance", "lifecycle/PIT acceptance"],
        "next_stage": "B6_50_SECURITY_10_PLUS_DATE_FINGERPRINT_DIAGNOSTIC",
    }
    _atomic_json(ROOT / args.receipt, receipt)
    print(json.dumps({"status": receipt["status"], "rows": len(materialized),
                      "local_matches": receipt["matched_local_fingerprint_rows"],
                      "requests": receipt["request_count_delta"], "artifact": receipt["artifact_path"]}, ensure_ascii=False))
    return 0 if success else 2


if __name__ == "__main__":
    raise SystemExit(main())
