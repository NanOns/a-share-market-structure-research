from __future__ import annotations

"""R4 bounded probes for BSE symbol support, suspension status, and one malformed row."""

import argparse
import hashlib
import importlib.metadata
import json
import math
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from workbench_analysis.baostock_supplemental import (  # noqa: E402
    BaoStockClient, BaoStockError, RequestBudget, _atomic_json, normalize_row,
)
from tdx.day_reader import DAY_STRUCT


def prefix_counts(rows: list[dict[str, str]]) -> dict[str, int]:
    result = {"sh.": 0, "sz.": 0, "bj.": 0, "other": 0}
    for row in rows:
        code = str(row.get("code", ""))
        key = next((prefix for prefix in ("sh.", "sz.", "bj.") if code.startswith(prefix)), "other")
        result[key] += 1
    return result


def malformed_field_flags(row: dict[str, str]) -> list[str]:
    flags = []
    if not str(row.get("code", "")).strip():
        flags.append("CODE_EMPTY")
    try:
        datetime.strptime(str(row.get("date", "")), "%Y-%m-%d")
    except ValueError:
        flags.append("DATE_INVALID")
    for name in ("close", "volume", "amount"):
        try:
            value = float(row.get(name, ""))
            if not math.isfinite(value) or value < 0:
                flags.append(name.upper() + "_NONFINITE_OR_NEGATIVE")
            elif name == "volume" and value != int(value):
                flags.append("VOLUME_NONINTEGER")
        except (TypeError, ValueError, OverflowError):
            flags.append(name.upper() + "_NOT_NUMERIC")
    try:
        turn = str(row.get("turn", "")).strip()
        if turn:
            number = float(turn)
            if not math.isfinite(number) or number < 0:
                flags.append("TURN_INVALID")
    except (TypeError, ValueError, OverflowError):
        flags.append("TURN_INVALID")
    for name in ("tradestatus", "isST"):
        if str(row.get(name, "")).strip() not in {"0", "1"}:
            flags.append(name.upper() + "_ENUM_INVALID")
    return flags


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog-date", default="2026-09-07")
    parser.add_argument("--history-start", default="2026-09-01")
    parser.add_argument("--history-end", default="2026-09-07")
    parser.add_argument("--ledger", default="reports/v4_baostock/request_ledger.json")
    parser.add_argument("--receipt", default="reports/v4_baostock/r4_edge_case_probe_receipt.json")
    args = parser.parse_args()

    ledger_path = ROOT / args.ledger
    before = json.loads(ledger_path.read_text(encoding="utf-8")) if ledger_path.exists() else {"by_shanghai_date": {}}
    before_count = sum(int(x.get("count", 0)) for x in before.get("by_shanghai_date", {}).values())
    client = BaoStockClient(RequestBudget(ledger_path), auth_mode="PUBLIC_ANONYMOUS")
    started = time.monotonic()
    catalog_counts = {}
    all_stock_counts = {}
    direct_bse = []
    suspension_samples = []
    anomaly = {"code": "sz.000016", "query_range": {"start": "2024-09-25", "end": "2025-09-30"},
               "status": "NOT_RUN", "invalid_row_count": 0, "invalid_reason_counts": {},
               "suspended_blank_field_row_count": 0, "suspended_blank_field_samples": [], "invalid_row_samples": []}
    failures: dict[str, str] = {}
    try:
        with client:
            catalog, catalog_meta = client.query_rows("query_stock_basic", "query_stock_basic",
                                                     max_rows=10_000, max_pages=10)
            catalog_counts = {"error_code": catalog_meta["error_code"], "row_count": len(catalog),
                              "page_count": catalog_meta["page_count"], "prefix_counts": prefix_counts(catalog)}
            stocks, stocks_meta = client.query_rows("query_all_stock", "query_all_stock",
                                                    day=args.catalog_date, max_rows=10_000, max_pages=10)
            all_stock_counts = {"error_code": stocks_meta["error_code"], "row_count": len(stocks),
                                "page_count": stocks_meta["page_count"], "prefix_counts": prefix_counts(stocks)}

            # BSE's official code mapping lists 920799 as a current code and 830799
            # as its predecessor. Probe both dotted BaoStock forms independently.
            for code in ("bj.920799", "bj.830799"):
                item = {"code": code}
                try:
                    basic, meta = client.query_rows("query_stock_basic", "query_stock_basic",
                                                    code=code, max_rows=5, max_pages=1)
                    item["basic"] = {"error_code": meta["error_code"], "row_count": len(basic),
                                     "fields": meta["fields"],
                                     "returned_code_digest": hashlib.sha256("\n".join(r.get("code", "") for r in basic).encode()).hexdigest()}
                except BaoStockError as exc:
                    item["basic_failure"] = str(exc)
                try:
                    rows = client.query_daily(code, args.history_start, args.history_end)
                    item["history"] = {"error_code": client.last_query_result["error_code"],
                                       "row_count": len(rows), "first_date": min((r.trade_date for r in rows), default=None),
                                       "last_date": max((r.trade_date for r in rows), default=None),
                                       "tradestatus_counts": {status: sum(r.tradestatus == status for r in rows) for status in ("0", "1")}}
                except BaoStockError as exc:
                    item["history_failure"] = str(exc)
                    item["provider_error_code"] = exc.provider_code
                direct_bse.append(item)

            candidates = [
                ("sz.300104", "2017-01-01", "2020-12-31"),
                ("sh.600401", "2017-01-01", "2021-12-31"),
                ("sh.600145", "2017-01-01", "2019-12-31"),
                ("sh.600806", "2018-01-01", "2022-12-31"),
                ("sh.600240", "2018-01-01", "2022-12-31"),
                ("sh.600087", "2017-01-01", "2020-12-31"),
                ("sh.600275", "2017-01-01", "2020-12-31"),
                ("sz.000979", "2017-01-01", "2020-12-31"),
            ]
            for code, start, end in candidates:
                row = {"code": code, "query_range": {"start": start, "end": end}}
                try:
                    values = client.query_daily(code, start, end)
                    suspended_dates = [r.trade_date for r in values if r.tradestatus == "0"]
                    transitions = [{"from_date": prior.trade_date, "to_date": current.trade_date}
                                   for prior, current in zip(values, values[1:])
                                   if prior.tradestatus == "0" and current.tradestatus == "1"]
                    row.update({"status": "PASS", "row_count": len(values),
                                "tradestatus_counts": {status: sum(r.tradestatus == status for r in values) for status in ("0", "1")},
                                "suspended_date_count": len(suspended_dates),
                                "suspended_dates_sample": suspended_dates[:5],
                                "resume_transitions_sample": transitions[:5],
                                "rows_digest": hashlib.sha256("\n".join(r.source_digest for r in values).encode("ascii")).hexdigest()})
                except BaoStockError as exc:
                    row.update({"status": "QUERY_FAILED", "failure": str(exc), "provider_error_code": exc.provider_code})
                suspension_samples.append(row)

            # Reproduce the prior invalid-row observation without persisting any
            # provider values. Only field-quality flags, dates, and status enums
            # are retained in this diagnostic.
            sdk = client.sdk
            client.budget.consume("query_history_k_data_plus_adjustflag_3_exception_diagnostic")
            result = sdk.query_history_k_data_plus(
                anomaly["code"], "date,code,close,volume,amount,turn,tradestatus,isST",
                start_date=anomaly["query_range"]["start"], end_date=anomaly["query_range"]["end"],
                frequency="d", adjustflag="3")
            anomaly["error_code"] = str(getattr(result, "error_code", "UNKNOWN"))
            anomaly["error_msg"] = client._safe_message(getattr(result, "error_msg", ""))
            anomaly["fields"] = list(getattr(result, "fields", []))
            if anomaly["error_code"] == "0":
                local_path = ROOT / "data/v4/local_tdx_snapshots/1644752b002fdeb4f3d3a2968b9c77729f27efcdae8923ad14d814abe5c78c70/sz/lday/sz000016.day"
                local_by_date = {}
                if local_path.is_file() and local_path.stat().st_size % DAY_STRUCT.size == 0:
                    local_by_date = {day: {"close": close / 100.0, "volume": volume, "amount": float(amount)}
                                     for day, _open, _high, _low, close, amount, volume, _reserved
                                     in DAY_STRUCT.iter_unpack(local_path.read_bytes())}
                invalids = []
                suspended_blank = []
                normalized_rows = 0
                local_path = ROOT / "data/v4/local_tdx_snapshots/1644752b002fdeb4f3d3a2968b9c77729f27efcdae8923ad14d814abe5c78c70/sz/lday/sz000016.day"
                local_by_date = {}
                if local_path.is_file() and local_path.stat().st_size % DAY_STRUCT.size == 0:
                    local_by_date = {day: {"volume": volume, "amount": float(amount)}
                                     for day, _open, _high, _low, _close, amount, volume, _reserved
                                     in DAY_STRUCT.iter_unpack(local_path.read_bytes())}
                while result.next():
                    values = dict(zip(result.fields, result.get_row_data(), strict=True))
                    date_value = str(values.get("date", ""))
                    if values.get("tradestatus") == "0" and (not str(values.get("volume", "")).strip()
                                                               or not str(values.get("amount", "")).strip()):
                        local = local_by_date.get(int(date_value.replace("-", ""))) if len(date_value) == 10 else None
                        suspended_blank.append({
                            "date": date_value if len(date_value) == 10 else None,
                            "volume_blank": not str(values.get("volume", "")).strip(),
                            "amount_blank": not str(values.get("amount", "")).strip(),
                            "local_tdx_same_date": local is not None,
                        })
                    try:
                        normalize_row(anomaly["code"], values)
                        normalized_rows += 1
                    except BaoStockError:
                        flags = malformed_field_flags(values)
                        summary = {"row_index": len(invalids), "date": date_value if len(date_value) == 10 else None,
                                   "tradestatus": values.get("tradestatus") if values.get("tradestatus") in ("0", "1") else None,
                                   "field_flags": flags or ["NORMALIZER_REJECTED_UNCLASSIFIED"]}
                        if len(date_value) == 10:
                            local = local_by_date.get(int(date_value.replace("-", "")))
                            summary["local_tdx_same_date"] = local is not None
                            summary["local_tdx_volume_zero"] = (local is not None and local["volume"] == 0)
                            summary["local_tdx_amount_zero"] = (local is not None and local["amount"] == 0)
                        invalids.append(summary)
                reasons: dict[str, int] = {}
                for row in invalids:
                    for flag in row["field_flags"]:
                        reasons[flag] = reasons.get(flag, 0) + 1
                anomaly.update({"status": "SUSPENDED_BLANKS_PRESERVED_NULL" if suspended_blank and not invalids
                                else "DIAGNOSED" if invalids else "NO_INVALID_ROWS_REPRODUCED",
                                "normalized_row_count": normalized_rows,
                                "suspended_blank_field_row_count": len(suspended_blank),
                                "suspended_blank_field_samples": suspended_blank[:10],
                                "invalid_row_count": len(invalids), "invalid_reason_counts": reasons,
                                "invalid_row_samples": invalids[:10]})
            else:
                anomaly["status"] = "PROVIDER_QUERY_FAILED"
    except Exception as exc:
        failures["session"] = type(exc).__name__ + ":" + str(exc)[:200]

    after = json.loads(ledger_path.read_text(encoding="utf-8")) if ledger_path.exists() else {"by_shanghai_date": {}}
    after_count = sum(int(x.get("count", 0)) for x in after.get("by_shanghai_date", {}).values())
    bse_supported = any((item.get("basic", {}).get("row_count", 0) > 0 and item.get("history", {}).get("row_count", 0) > 0)
                        for item in direct_bse)
    bse_not_supported_for_tested_codes = (catalog_counts.get("prefix_counts", {}).get("bj.") == 0
        and len(direct_bse) == 2
        and all(item.get("basic", {}).get("row_count", 0) == 0
                and item.get("provider_error_code") == "10004011" for item in direct_bse))
    has_suspension = any(item.get("suspended_date_count", 0) > 0 for item in suspension_samples)
    has_resumption = any(item.get("resume_transitions_sample") for item in suspension_samples)
    receipt = {
        "stage": "V4-01/02-BAOSTOCK-R4-EDGE-CASE-PROBE",
        "contract_id": "BAOSTOCK_PUBLIC_SOURCE_EDGE_CASES_V1",
        "observed_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "runtime": {"package": "baostock", "version": importlib.metadata.version("baostock"),
                    "auth_mode": client.auth_mode, **client.runtime_endpoint},
        "catalog": {"query_stock_basic": catalog_counts, "query_all_stock": all_stock_counts,
                    "reference": "https://www.bse.cn/service/code_mapping.html",
                    "reference_observed_at": "2026-09-25", "known_bse_old_new_code_pair": ["830799", "920799"]},
        "bse_direct_probes": direct_bse,
        "bse_capability": ("SUPPORTED_BY_DIRECT_BASIC_AND_HISTORY" if bse_supported else
                           "NOT_SUPPORTED_FOR_OFFICIAL_OLD_NEW_CODE_PROBES" if bse_not_supported_for_tested_codes else
                           "NOT_YET_ESTABLISHED"),
        "historical_status_probes": suspension_samples,
        "historical_suspension_observed": has_suspension,
        "historical_resumption_transition_observed": has_resumption,
        "prior_b6_anomaly": anomaly,
        "request_count_delta": after_count - before_count,
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "raw_provider_payload_persisted": False,
        "failures": failures,
        "execution_identity": {
            "input_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
            "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "adapter_sha256": hashlib.sha256((ROOT / "src/workbench_analysis/baostock_supplemental.py").read_bytes()).hexdigest(),
        },
        "status": "R4_EDGE_CASES_OBSERVED" if not failures else "R4_EDGE_CASES_PARTIAL",
        "acceptance_gaps": ["independent evidence review", "representative board/status acceptance", "turnover denominator semantics"],
    }
    _atomic_json(ROOT / args.receipt, receipt)
    print(json.dumps({"status": receipt["status"], "catalog_prefix_counts": catalog_counts.get("prefix_counts"),
                      "all_stock_prefix_counts": all_stock_counts.get("prefix_counts"),
                      "bse_capability": receipt["bse_capability"], "suspension": has_suspension,
                      "resumption": has_resumption, "anomaly": {"status": anomaly["status"],
                      "invalid_row_count": anomaly["invalid_row_count"], "reasons": anomaly["invalid_reason_counts"]},
                      "requests": receipt["request_count_delta"], "failures": failures}, ensure_ascii=False))
    return 0 if not failures else 2


if __name__ == "__main__":
    raise SystemExit(main())
