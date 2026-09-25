from __future__ import annotations

"""Diagnostic 50-security / 10+ date fingerprint comparison (B6).

This probe measures observed deltas only. It cannot issue an accepted tolerance
contract or enable BOUND_STRICT.
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

from workbench_analysis.baostock_supplemental import BaoStockClient, BaoStockError, RequestBudget, _atomic_json  # noqa: E402
from tdx.day_reader import DAY_STRUCT, read_edge_records


SNAPSHOT_ID = "1644752b002fdeb4f3d3a2968b9c77729f27efcdae8923ad14d814abe5c78c70"
SNAPSHOT = ROOT / "data/v4/local_tdx_snapshots" / SNAPSHOT_ID


def local_rows(code: str, start: str, end: str) -> dict[int, dict[str, float | int]]:
    market, number = code.split(".", 1)
    path = SNAPSHOT / market / "lday" / f"{market}{number}.day"
    if not path.is_file():
        return {}
    lower, upper = int(start.replace("-", "")), int(end.replace("-", ""))
    raw = path.read_bytes()
    if len(raw) % DAY_STRUCT.size:
        return {}
    result = {}
    for day, _open, _high, _low, close, amount, volume, _reserved in DAY_STRUCT.iter_unpack(raw):
        if lower <= day <= upper:
            result[day] = {"close": close / 100.0, "volume": int(volume), "amount": float(amount)}
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", default="2024-09-25")
    parser.add_argument("--end", default="2025-09-30")
    parser.add_argument("--security-count", type=int, default=50)
    parser.add_argument("--dates-per-security", type=int, default=15)
    parser.add_argument("--exclude-codes", default="", help="Comma-separated, pre-observed malformed provider symbols")
    parser.add_argument("--b1-receipt", default="reports/v4_baostock/public_b1_093_clean_venv_receipt.json")
    parser.add_argument("--b5-receipt", default="reports/v4_baostock/public_b5_supplement_bootstrap_receipt.json")
    parser.add_argument("--ledger", default="reports/v4_baostock/request_ledger.json")
    parser.add_argument("--receipt", default="reports/v4_baostock/public_b6_fingerprint_sample_receipt.json")
    args = parser.parse_args()
    if args.security_count < 50 or args.security_count > 60 or args.dates_per_security < 10 or args.start > args.end:
        raise SystemExit("B6_INPUT_BOUND_INVALID")
    b1_path, b5_path = ROOT / args.b1_receipt, ROOT / args.b5_receipt
    b1, b5 = json.loads(b1_path.read_text(encoding="utf-8")), json.loads(b5_path.read_text(encoding="utf-8"))
    if b1.get("status") != "PUBLIC_CAPABILITY_B1_093_PASS" or b5.get("status") != "B5_SUPPLEMENT_MATERIALIZED_BINDING_UNACCEPTED":
        raise SystemExit("B6_NOT_RUN_REQUIRED_PRIOR_GATE_MISSING")

    ledger_path = ROOT / args.ledger
    before = json.loads(ledger_path.read_text(encoding="utf-8")) if ledger_path.exists() else {"by_shanghai_date": {}}
    before_count = sum(int(x.get("count", 0)) for x in before.get("by_shanghai_date", {}).values())
    client = BaoStockClient(RequestBudget(ledger_path), auth_mode="PUBLIC_ANONYMOUS")
    started = time.monotonic()
    failures: dict[str, str] = {}
    securities: list[str] = []
    summary: dict = {}
    candidates: list[str] = []
    excluded_codes = sorted({code.strip() for code in args.exclude_codes.split(",") if code.strip()})
    try:
        with client:
            basic, meta = client.query_rows("query_stock_basic", "query_stock_basic", max_rows=10_000, max_pages=20)
            if meta.get("error_code") != "0":
                raise BaoStockError("B6_STOCK_BASIC_FAILED")
            ref = next((row for row in basic if row.get("code") == "sh.600000"), {})
            equity_type, active_status = ref.get("type"), ref.get("status")
            for row in basic:
                code = str(row.get("code", ""))
                if code in excluded_codes or not (code.startswith(("sh.", "sz.")) and row.get("type") == equity_type
                        and row.get("status") == active_status):
                    continue
                market, number = code.split(".", 1)
                path = SNAPSHOT / market / "lday" / f"{market}{number}.day"
                if not path.is_file():
                    continue
                try:
                    first, last = read_edge_records(path)
                except (OSError, ValueError):
                    continue
                if first.trade_date <= int(args.end.replace("-", "")) and last.trade_date >= int(args.start.replace("-", "")):
                    candidates.append(code)
            # Select a reproducible cross-market sample, alternating markets
            # and walking ascending code order after a stable hash sort.
            pools = {prefix: [c for c in candidates if c.startswith(prefix)] for prefix in ("sh.", "sz.")}
            pools = {key: sorted(value) for key, value in pools.items()}
            turn = 0
            while len(securities) < args.security_count and any(pools.values()):
                market = ("sh.", "sz.")[turn % 2]
                if pools[market]:
                    securities.append(pools[market].pop(0))
                elif pools["sh."]:
                    securities.append(pools["sh."].pop(0))
                elif pools["sz."]:
                    securities.append(pools["sz."].pop(0))
                turn += 1
            if len(securities) < args.security_count:
                raise BaoStockError("B6_INSUFFICIENT_LOCAL_PROVIDER_OVERLAP")

            counts = {"security_queries": 0, "date_pairs": 0, "exact_close": 0,
                      "exact_volume": 0, "exact_amount": 0, "all_three_exact": 0,
                      "volume_observed_pairs": 0, "amount_observed_pairs": 0,
                      "volume_missing_pairs": 0, "amount_missing_pairs": 0}
            close_abs, volume_abs, amount_abs, amount_rel = [], [], [], []
            per_security = []
            compare_hashes = []
            for code in securities:
                local = local_rows(code, args.start, args.end)
                try:
                    rows = client.query_daily(code, args.start, args.end)
                    counts["security_queries"] += 1
                except BaoStockError as exc:
                    failures[code] = str(exc)
                    continue
                source = {int(row.trade_date.replace("-", "")): row for row in rows}
                common = sorted(set(local) & set(source))
                if len(common) > args.dates_per_security:
                    n = args.dates_per_security
                    indexes = sorted({round(i * (len(common) - 1) / (n - 1)) for i in range(n)})
                    common = [common[i] for i in indexes]
                exact_all = 0
                for day in common:
                    lrow, srow = local[day], source[day]
                    dc = abs(float(lrow["close"]) - srow.close_price_cny)
                    counts["date_pairs"] += 1
                    close_abs.append(dc)
                    counts["exact_close"] += dc == 0
                    dv = None
                    da = None
                    if srow.volume_shares is None:
                        counts["volume_missing_pairs"] += 1
                    else:
                        dv = abs(float(lrow["volume"]) - srow.volume_shares)
                        counts["volume_observed_pairs"] += 1
                        volume_abs.append(dv)
                        counts["exact_volume"] += dv == 0
                    if srow.amount_cny is None:
                        counts["amount_missing_pairs"] += 1
                    else:
                        da = abs(float(lrow["amount"]) - srow.amount_cny)
                        counts["amount_observed_pairs"] += 1
                        amount_abs.append(da)
                        if lrow["amount"] or srow.amount_cny:
                            amount_rel.append(da / max(abs(float(lrow["amount"])), abs(srow.amount_cny), 1.0))
                        counts["exact_amount"] += da == 0
                    exact = dc == 0 and dv == 0 and da == 0
                    exact_all += exact
                    counts["all_three_exact"] += exact
                    compare_hashes.append(hashlib.sha256(json.dumps({"code": code, "date": day,
                        "close_abs_delta": dc, "volume_abs_delta": dv, "amount_abs_delta": da},
                        sort_keys=True, separators=(",", ":")).encode()).hexdigest())
                per_security.append({"security_code": code, "provider_rows": len(rows),
                                     "local_rows_in_range": len(local), "sampled_overlap_dates": len(common),
                                     "all_three_exact_count": exact_all,
                                     "status": "PASS" if len(common) >= 10 else "INSUFFICIENT_OVERLAP"})
    except Exception as exc:
        failures["session_or_sample"] = type(exc).__name__ + ":" + str(exc)
        counts = locals().get("counts", {"security_queries": 0, "date_pairs": 0,
                "exact_close": 0, "exact_volume": 0, "exact_amount": 0, "all_three_exact": 0})
        per_security = locals().get("per_security", [])
        compare_hashes = locals().get("compare_hashes", [])
        close_abs = locals().get("close_abs", []); volume_abs = locals().get("volume_abs", [])
        amount_abs = locals().get("amount_abs", []); amount_rel = locals().get("amount_rel", [])

    after = json.loads(ledger_path.read_text(encoding="utf-8")) if ledger_path.exists() else {"by_shanghai_date": {}}
    after_count = sum(int(x.get("count", 0)) for x in after.get("by_shanghai_date", {}).values())
    enough = (len(securities) == args.security_count and counts.get("security_queries") == args.security_count
              and len(per_security) == args.security_count and all(x["sampled_overlap_dates"] >= 10 for x in per_security)
              and counts.get("date_pairs", 0) >= args.security_count * 10)
    observed = {
        "security_count_requested": args.security_count,
        "successful_security_queries": counts.get("security_queries", 0),
        "date_pairs": counts.get("date_pairs", 0),
        "minimum_dates_per_successful_security": min((x["sampled_overlap_dates"] for x in per_security), default=0),
        "exact_match_counts": {
            "close": {"exact": counts.get("exact_close", 0), "observed": counts.get("date_pairs", 0)},
            "volume": {"exact": counts.get("exact_volume", 0), "observed": counts.get("volume_observed_pairs", 0),
                       "missing": counts.get("volume_missing_pairs", 0)},
            "amount": {"exact": counts.get("exact_amount", 0), "observed": counts.get("amount_observed_pairs", 0),
                       "missing": counts.get("amount_missing_pairs", 0)},
            "all_three_exact": counts.get("all_three_exact", 0),
        },
        "max_abs_delta": {"close": max(close_abs, default=None), "volume": max(volume_abs, default=None),
                          "amount": max(amount_abs, default=None), "amount_relative": max(amount_rel, default=None)},
        "difference_digest": hashlib.sha256("\n".join(compare_hashes).encode("ascii")).hexdigest(),
        "candidate_tolerance_acceptance": "NOT_ISSUED_DIAGNOSTIC_ONLY",
        "BOUND_STRICT": "NOT_ENABLED_INDEPENDENT_ACCEPTANCE_REQUIRED",
    }
    receipt = {
        "stage": "V4-01/02-BAOSTOCK-PUBLIC-B6-FINGERPRINT-SAMPLE",
        "contract_id": "BAOSTOCK_FINGERPRINT_TOLERANCE_V1_DIAGNOSTIC",
        "observed_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "auth_mode": "PUBLIC_ANONYMOUS",
        "runtime": {"package": "baostock", "version": importlib.metadata.version("baostock"), **client.runtime_endpoint},
        "query_range": {"start": args.start, "end": args.end, "frequency": "d", "adjustflag": "3"},
        "snapshot_id": SNAPSHOT_ID,
        "selected_securities": securities,
        "pre_observed_exclusions": [{"security_code": code, "reason": "INVALID_BAOSTOCK_ROW_IN_PRIOR_B6_RUN"}
                                    for code in excluded_codes],
        "per_security": per_security,
        "observed": observed,
        "failures": failures,
        "request_count_delta": after_count - before_count,
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "b1_receipt_sha256": hashlib.sha256(b1_path.read_bytes()).hexdigest(),
        "b5_receipt_sha256": hashlib.sha256(b5_path.read_bytes()).hexdigest(),
        "raw_provider_payload_persisted": False,
        "execution_identity": {
            "input_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
            "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "adapter_sha256": hashlib.sha256((ROOT / "src/workbench_analysis/baostock_supplemental.py").read_bytes()).hexdigest(),
        },
        "status": "B6_DIAGNOSTIC_SAMPLE_PASS_ACCEPTANCE_PENDING" if enough else "B6_BLOCKED",
        "acceptance_gaps": ["independent fingerprint tolerance acceptance", "status-field lifecycle/PIT binding", "no-action/suspension/resumption coverage"],
        "next_stage": "INDEPENDENT_TOLERANCE_ACCEPTANCE_AND_V4_01_SOURCE_SELECTION",
    }
    _atomic_json(ROOT / args.receipt, receipt)
    print(json.dumps({"status": receipt["status"], "securities": observed["successful_security_queries"],
                      "date_pairs": observed["date_pairs"], "max_abs_delta": observed["max_abs_delta"],
                      "requests": receipt["request_count_delta"], "elapsed_seconds": receipt["elapsed_seconds"]}, ensure_ascii=False))
    return 0 if enough else 2


if __name__ == "__main__":
    raise SystemExit(main())
