from __future__ import annotations

"""Read-only TDX and BaoStock source-behavior diagnostic for a code change."""

import argparse
import contextlib
import csv
import hashlib
import io
import json
import os
import re
import socket
import subprocess
import sys
import tempfile
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from tdx.day_reader import DAY_RECORD_LENGTH, decode_record  # noqa: E402
from tdx.security_master import read_industry_assignments, read_tnf  # noqa: E402
from common.paths import resolve_tdx_root  # noqa: E402
from workbench_analysis.baostock_supplemental import (  # noqa: E402
    BaoStockClient,
    BaoStockError,
    RequestBudget,
    package_metadata,
)
from v4_01.source_fingerprint_candidate import analyze_source_fingerprint  # noqa: E402

CONTRACT_ID = "V4_01_CODE_CHANGE_SOURCE_FINGERPRINT_DIAGNOSTIC_V1"
CONTRACT_VERSION = "1.0.0"
DIAGNOSTIC_MAX_TRANSIENT_RETRIES = 1
DIAGNOSTIC_FIELDS = (
    "date,code,open,high,low,close,preclose,volume,amount,"
    "adjustflag,turn,tradestatus,isST"
)
BUSINESS_FIELDS = (
    "open", "high", "low", "close", "preclose", "volume",
    "amount", "tradestatus", "isST",
)
NUMERIC_FIELDS = {
    "open", "high", "low", "close", "preclose", "volume", "amount",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_write(path: Path, payload: bytes, tdx_root: Path) -> None:
    destination = path.resolve()
    root = tdx_root.resolve()
    if destination == root or root in destination.parents:
        raise ValueError("PROJECT_ARTIFACT_MUST_BE_OUTSIDE_TDX_ROOT")
    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(
        prefix=destination.name + ".", suffix=".tmp", dir=destination.parent
    )
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, destination)
    finally:
        Path(temporary).unlink(missing_ok=True)


def parse_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("date must be YYYY-MM-DD") from exc


def parse_code(value: str) -> tuple[str, str, str]:
    match = re.fullmatch(r"(SH|SZ|BJ)\.(\d{6})", value.strip().upper())
    if not match:
        raise argparse.ArgumentTypeError("code must be EXCHANGE.NNNNNN")
    exchange, digits = match.groups()
    return exchange, digits, f"{exchange.lower()}.{digits}"


def date_text(value: int) -> str:
    return datetime.strptime(str(value), "%Y%m%d").date().isoformat()


def numeric_equal(left: Any, right: Any) -> bool:
    if left == right:
        return True
    try:
        return Decimal(str(left)) == Decimal(str(right))
    except (InvalidOperation, ValueError):
        return False


def load_day_file(path: Path, code: str, window_start: date, window_end: date) -> dict[str, Any]:
    metadata: dict[str, Any] = {"code": code, "path": str(path), "exists": path.is_file()}
    if not path.is_file():
        return {"metadata": metadata, "records": [], "by_date": {}}
    raw = path.read_bytes()
    remainder = len(raw) % DAY_RECORD_LENGTH
    complete = len(raw) - remainder
    records = []
    by_date: dict[str, dict[str, Any]] = {}
    duplicate_dates = 0
    non_increasing_dates = 0
    previous_date = None
    for offset in range(0, complete, DAY_RECORD_LENGTH):
        raw_record = raw[offset:offset + DAY_RECORD_LENGTH]
        decoded = decode_record(raw_record)
        day = date_text(decoded.trade_date)
        if day in by_date:
            duplicate_dates += 1
        if previous_date is not None and decoded.trade_date <= previous_date:
            non_increasing_dates += 1
        previous_date = decoded.trade_date
        row = {
            "code": code,
            "trade_date": day,
            "open": decoded.open,
            "high": decoded.high,
            "low": decoded.low,
            "close": decoded.close,
            "amount": decoded.amount,
            "volume": decoded.volume,
            "reserved": decoded.reserved,
            "_raw": raw_record,
        }
        records.append(row)
        by_date[day] = row
    metadata.update({
        "byte_count": len(raw),
        "record_count": len(records),
        "trailing_bytes": remainder,
        "sha256": hashlib.sha256(raw).hexdigest(),
        "first_date": records[0]["trade_date"] if records else None,
        "last_date": records[-1]["trade_date"] if records else None,
        "duplicate_date_count": duplicate_dates,
        "non_increasing_date_count": non_increasing_dates,
        "window_rows": [
            {
                key: value for key, value in row.items() if key != "_raw"
            } | {"raw_record_sha256": hashlib.sha256(row["_raw"]).hexdigest()}
            for row in records
            if window_start.isoformat() <= row["trade_date"] <= window_end.isoformat()
        ],
    })
    return {"metadata": metadata, "records": records, "by_date": by_date}


def file_identity(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"path": str(path), "exists": False, "sha256": None, "byte_count": None}
    return {
        "path": str(path),
        "exists": True,
        "sha256": sha256_file(path),
        "byte_count": path.stat().st_size,
    }


def tdx_master_snapshot(tdx_root: Path, codes: list[tuple[str, str, str]]) -> dict[str, Any]:
    cache = tdx_root / "T0002" / "hq_cache"
    tnf_paths = {
        market: cache / f"{market.lower()}s.tnf"
        for market in sorted({code[0] for code in codes})
    }
    industry_path = cache / "tdxhy.cfg"
    sources = {
        "tnf": {market: file_identity(path) for market, path in tnf_paths.items()},
        "industry_assignment": file_identity(industry_path),
    }
    names: dict[str, str] = {}
    assignments: list[dict[str, Any]] = []
    for market, tnf_path in tnf_paths.items():
        if tnf_path.is_file():
            market_names, _ = read_tnf(tnf_path, market)
            names.update(market_names)
    if industry_path.is_file():
        assignments = read_industry_assignments(industry_path)
    by_security: dict[str, list[dict[str, Any]]] = {}
    for row in assignments:
        by_security.setdefault(row["security_id"], []).append(row)
    securities = {}
    for exchange, digits, _provider_code in codes:
        security_id = f"{exchange}.{digits}"
        matching = by_security.get(security_id, [])
        securities[security_id] = {
            "current_tnf_present": security_id in names,
            "current_tnf_name": names.get(security_id),
            "current_tdxhy_assignment_present": bool(matching),
            "industry_assignments": [
                {"industry_code": row["industry_code"], "line_number": row["line_number"]}
                for row in matching
            ],
            "market": exchange,
            "board_classification": "NOT_EXPOSED_AS_A_FIELD_BY_TNF_OR_TDXHY_CFG",
        }
    return {
        "formal_reader_basis": (
            "src/production/daily.py reads the exchange TNF file and tdxhy.cfg "
            "from configured TDX root"
        ),
        "sources": sources,
        "securities": securities,
    }


def total_ledger_count(doc: dict[str, Any]) -> int:
    return sum(int(item.get("count", 0)) for item in doc.get("by_shanghai_date", {}).values())


def load_ledger(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"ledger_version": 1, "by_shanghai_date": {}}
    return json.loads(path.read_text(encoding="utf-8"))


def bounded_diagnostic_history(
    client: BaoStockClient,
    query_code: str,
    start_date: str,
    end_date: str,
    max_rows: int = 10_000,
    max_pages: int = 20,
) -> tuple[list[dict[str, str]], dict[str, Any]]:
    """Use diagnostic fields while charging every SDK page to the central ledger."""
    if not client.logged_in or client.sdk is None:
        raise BaoStockError("BAOSTOCK_SESSION_NOT_READY")
    operation = "query_history_k_data_plus_code_change_diagnostic_adjustflag_3"
    retry_count = 0
    while True:
        client.budget.consume(operation if retry_count == 0 else operation + "_retry")
        try:
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                result = client.sdk.query_history_k_data_plus(
                    query_code,
                    DIAGNOSTIC_FIELDS,
                    start_date=start_date,
                    end_date=end_date,
                    frequency="d",
                    adjustflag="3",
                )
        except (TimeoutError, socket.timeout, ConnectionError, OSError):
            if retry_count < DIAGNOSTIC_MAX_TRANSIENT_RETRIES:
                retry_count += 1
                continue
            raise BaoStockError("BAOSTOCK_DIAGNOSTIC_HISTORY_TRANSPORT_FAILED") from None
        client.last_query_result = {
            "error_code": str(getattr(result, "error_code", "UNKNOWN")),
            "error_msg": client._safe_message(getattr(result, "error_msg", "")),
            "fields": list(getattr(result, "fields", [])),
            "provider_date": str(getattr(result, "date", "") or "") or None,
        }
        if (
            client.last_query_result["error_code"] == "10002007"
            and retry_count < DIAGNOSTIC_MAX_TRANSIENT_RETRIES
        ):
            retry_count += 1
            continue
        break
    if getattr(result, "error_code", None) != "0":
        raise BaoStockError(
            "BAOSTOCK_DIAGNOSTIC_HISTORY_FAILED",
            provider_code=str(getattr(result, "error_code", "UNKNOWN")),
            provider_message=client.last_query_result["error_msg"],
        )
    rows: list[dict[str, str]] = []
    pages = 1
    while True:
        if (
            getattr(result, "cur_row_num", 0) >= len(getattr(result, "data", []))
            and len(getattr(result, "data", [])) == getattr(result, "per_page_count", -1)
            and result.cur_row_num > 0
        ):
            if pages >= max_pages:
                raise BaoStockError("QUERY_PAGE_BOUND_EXCEEDED")
            client.budget.consume(operation + "_page")
            pages += 1
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            if not result.next():
                break
            rows.append(dict(zip(result.fields, result.get_row_data(), strict=True)))
        if len(rows) > max_rows:
            raise BaoStockError("QUERY_ROW_BOUND_EXCEEDED")
    metadata = {
        "error_code": str(getattr(result, "error_code", "UNKNOWN")),
        "error_msg": client._safe_message(getattr(result, "error_msg", "")),
        "fields": list(getattr(result, "fields", [])),
        "provider_date": str(getattr(result, "date", "") or "") or None,
        "page_count": pages,
        "row_count": len(rows),
        "query_code": query_code,
        "start_date": start_date,
        "end_date": end_date,
        "frequency": "d",
        "adjustflag": "3",
        "fields_requested": DIAGNOSTIC_FIELDS,
        "retry_count": retry_count,
    }
    if metadata["error_code"] != "0":
        raise BaoStockError(
            "BAOSTOCK_QUERY_FAILED_AFTER_PAGINATION",
            provider_code=metadata["error_code"],
            provider_message=metadata["error_msg"],
        )
    client.last_query_result = metadata
    return rows, metadata


def query_roster(client: BaoStockClient, day: str, target_codes: set[str]) -> dict[str, Any]:
    rows, metadata = client.query_rows(
        "query_all_stock_code_change_diagnostic",
        "query_all_stock",
        day=day,
        max_rows=10_000,
        max_pages=20,
    )
    all_codes = sorted({
        str(row.get("code", "")).strip().lower()
        for row in rows if re.fullmatch(r"(?:sh|sz|bj)\.\d{6}", str(row.get("code", "")).strip().lower())
    })
    return {
        "trade_date": day,
        "row_count": len(rows),
        "valid_unique_code_count": len(all_codes),
        "code_set_sha256": hashlib.sha256("\n".join(all_codes).encode("ascii")).hexdigest(),
        "provider_fields": metadata.get("fields", []),
        "page_count": metadata.get("page_count"),
        "provider_error_code": metadata.get("error_code"),
        "target_codes": {
            code: {
                "present": any(str(row.get("code", "")).strip().lower() == code for row in rows),
                "provider_rows": [
                    row for row in rows if str(row.get("code", "")).strip().lower() == code
                ],
            }
            for code in sorted(target_codes)
        },
    }


def compare_history_rows(
    old_rows: list[dict[str, str]],
    new_rows: list[dict[str, str]],
    fields: tuple[str, ...],
    sample_limit: int = 25,
) -> dict[str, Any]:
    old_by_date: dict[str, dict[str, str]] = {}
    new_by_date: dict[str, dict[str, str]] = {}
    duplicate_dates = {"old_query": [], "new_query": []}
    for label, rows, target in (
        ("old_query", old_rows, old_by_date), ("new_query", new_rows, new_by_date),
    ):
        for row in rows:
            day = row.get("date", "")
            if day in target:
                duplicate_dates[label].append(day)
            target[day] = row
    common = sorted(set(old_by_date) & set(new_by_date))
    exact = 0
    all_samples = []
    mismatch_fields: dict[str, int] = {}
    mismatch_dates = []
    mismatch_categories: dict[str, int] = {}
    for day in common:
        mismatches = {}
        for field in fields:
            left, right = old_by_date[day].get(field, ""), new_by_date[day].get(field, "")
            equal = numeric_equal(left, right) if field in NUMERIC_FIELDS else left == right
            if not equal:
                mismatches[field] = {"old_query": left, "new_query": right}
                mismatch_fields[field] = mismatch_fields.get(field, 0) + 1
        if not mismatches:
            exact += 1
        else:
            mismatch_dates.append(day)
            all_samples.append({"date": day, "mismatches": mismatches})
            old_status = old_by_date[day].get("tradestatus")
            new_status = new_by_date[day].get("tradestatus")
            if old_status != new_status:
                category = "TRADING_STATUS_DIFF"
            elif old_status == new_status == "0" and all(
                field in NUMERIC_FIELDS
                and (
                    (left == "" and numeric_equal(right, 0))
                    or (right == "" and numeric_equal(left, 0))
                )
                for field, values in mismatches.items()
                for left, right in [(values["old_query"], values["new_query"])]
            ):
                category = "SUSPENDED_BLANK_VS_ZERO_ONLY"
            elif old_status == new_status == "1":
                category = "ACTUAL_BAR_VALUE_DIFF"
            else:
                category = "OTHER_BUSINESS_FIELD_DIFF"
            mismatch_categories[category] = mismatch_categories.get(category, 0) + 1
    samples = all_samples if len(all_samples) <= sample_limit else (
        all_samples[:sample_limit // 2] + all_samples[-(sample_limit - sample_limit // 2):]
    )
    return {
        "common_date_count": len(common),
        "exact_business_field_match_count": exact,
        "mismatch_count": len(common) - exact,
        "mismatch_samples": samples,
        "mismatch_date_range": {
            "first": mismatch_dates[0] if mismatch_dates else None,
            "last": mismatch_dates[-1] if mismatch_dates else None,
        },
        "mismatch_field_counts": dict(sorted(mismatch_fields.items())),
        "mismatch_category_counts": dict(sorted(mismatch_categories.items())),
        "duplicate_date_count": {key: len(value) for key, value in duplicate_dates.items()},
        "duplicate_date_samples": {key: value[:sample_limit] for key, value in duplicate_dates.items()},
        "compared_fields": list(fields),
        "code_field_excluded": True,
    }


def tdx_overlap(old: dict[str, Any], new: dict[str, Any]) -> dict[str, Any]:
    old_records, new_records = old["records"], new["records"]
    old_by_date, new_by_date = old["by_date"], new["by_date"]
    common_dates = sorted(set(old_by_date) & set(new_by_date))
    exact_raw = 0
    exact_decoded = 0
    mismatch_samples = []
    mismatch_dates = []
    mismatch_field_counts: dict[str, int] = {}
    decoded_fields = ("open", "high", "low", "close", "amount", "volume", "reserved")
    for day in common_dates:
        left, right = old_by_date[day], new_by_date[day]
        exact_raw += int(left["_raw"] == right["_raw"])
        decoded_equal = all(left[field] == right[field] for field in decoded_fields)
        exact_decoded += int(decoded_equal)
        if not decoded_equal:
            mismatches = {
                field: {"old": left[field], "new": right[field]}
                for field in decoded_fields if left[field] != right[field]
            }
            mismatch_dates.append(day)
            for field in mismatches:
                mismatch_field_counts[field] = mismatch_field_counts.get(field, 0) + 1
            if len(mismatch_samples) < 25:
                mismatch_samples.append({
                    "trade_date": day,
                    "old_raw_record_sha256": hashlib.sha256(left["_raw"]).hexdigest(),
                    "new_raw_record_sha256": hashlib.sha256(right["_raw"]).hexdigest(),
                    "mismatches": mismatches,
                })
    prefix = 0
    for left, right in zip(old_records, new_records):
        if left["_raw"] != right["_raw"]:
            break
        prefix += 1
    old_count = len(old_records)
    return {
        "overlap_session_count": len(common_dates),
        "exact_decoded_match_count": exact_decoded,
        "decoded_mismatch_count": len(common_dates) - exact_decoded,
        "exact_raw_record_match_count": exact_raw,
        "raw_record_mismatch_count": len(common_dates) - exact_raw,
        "record_count_old": old_count,
        "record_count_new": len(new_records),
        "longest_common_prefix_in_records": prefix,
        "common_prefix_ratio": prefix / old_count if old_count else None,
        "exact_raw_overlap_ratio": exact_raw / len(common_dates) if common_dates else None,
        # An absent/empty old file is not evidence of a matching prefix.
        "old_history_equals_full_new_prefix": (
            old_count > 0 and old_count <= len(new_records) and prefix == old_count
        ),
        "mismatch_date_range": {
            "first": mismatch_dates[0] if mismatch_dates else None,
            "last": mismatch_dates[-1] if mismatch_dates else None,
        },
        "mismatch_field_counts": dict(sorted(mismatch_field_counts.items())),
        "mismatch_samples": mismatch_samples,
    }


def f6_actual_trading_signals(
    substantive_dual_trade_days: list[dict[str, Any]],
    identical_provider_alias_bar_days: list[dict[str, Any]],
) -> dict[str, Any]:
    """Separate identical provider alias bars from substantive dual-bar conflicts."""
    return {
        "F6_no_substantive_dual_actual_trading": not substantive_dual_trade_days,
        "F6_identical_provider_alias_bar_dates": [
            item["trade_date"] for item in identical_provider_alias_bar_days
        ],
        "F6_substantive_dual_trade_dates": [
            item["trade_date"] for item in substantive_dual_trade_days
        ],
    }


def provider_code_set(rows: list[dict[str, str]]) -> list[str]:
    return sorted({row.get("code", "") for row in rows if row.get("code")})


def actual_baostock_trade(row: dict[str, Any] | None) -> bool:
    if not row or str(row.get("tradestatus", "")) != "1":
        return False
    try:
        return Decimal(str(row.get("volume", "0") or "0")) > 0
    except InvalidOperation:
        return False


def cross_source_row(
    tdx_row: dict[str, Any] | None,
    provider_row: dict[str, str] | None,
) -> dict[str, Any]:
    if tdx_row is None or provider_row is None:
        return {"tdx_row_exists": tdx_row is not None, "baostock_row_exists": provider_row is not None}
    comparisons = {}
    for field in ("open", "high", "low", "close", "volume", "amount"):
        tdx_value, bao_value = tdx_row.get(field), provider_row.get(field)
        try:
            delta = float(Decimal(str(bao_value)) - Decimal(str(tdx_value)))
        except (InvalidOperation, TypeError, ValueError):
            delta = None
        comparisons[field] = {
            "tdx": tdx_value,
            "baostock": bao_value,
            "numeric_equal": numeric_equal(tdx_value, bao_value),
            "baostock_minus_tdx": delta,
        }
    return {
        "tdx_row_exists": True,
        "baostock_row_exists": True,
        "tdx_volume_positive": int(tdx_row.get("volume", 0) or 0) > 0,
        "baostock_actual_trade": actual_baostock_trade(provider_row),
        "field_comparisons": comparisons,
    }


def render_markdown(report: dict[str, Any], json_sha256: str) -> str:
    tdx = report["tdx"]
    bao = report["baostock"]
    overlap = tdx["overlap"]
    old_code, new_code = report["inputs"]["old_code"], report["inputs"]["new_code"]
    old_tdx, new_tdx = tdx["files"].get(old_code, {}), tdx["files"].get(new_code, {})
    old_hist = bao.get("long_history_summary", {}).get(old_code.lower(), {})
    new_hist = bao.get("long_history_summary", {}).get(new_code.lower(), {})
    roster = bao.get("roster_matrix", {})
    lines = [
        "# V4-01 TDX + BaoStock 代码变更源级指纹诊断",
        "",
        f"- 诊断合同：{CONTRACT_ID} v{CONTRACT_VERSION}",
        f"- 接受结果：{report['acceptance_result']}；模式：{report['conclusion']['pattern_class']}",
        f"- 样本：{old_code} → {new_code}；有效日：{report['inputs']['effective_date']}",
        f"- 执行时间：{report['observed_at_utc']}；输入 HEAD：{report['execution_identity']['input_commit']}",
        f"- JSON SHA-256：{json_sha256}",
        f"- 生产 identity 修改授权：{str(report['conclusion']['production_change_authorized']).lower()}",
        "",
        "## 阶段合同与门禁",
        "",
        "- 只读读取配置 TDX root；BaoStock 请求经项目 BaoStockClient 和中心 request ledger 计数。",
        "- 不修改 canonical identity、dated alias、Historical Universe、V4-02/V4-03 或 Accepted Head。",
        "- PASS 只表示本次诊断证据采集完整，不表示 identity candidate、V4-01 owner gate 或下游阶段通过。",
        f"- TDX 写入计数：{report['execution_identity']['tdx_root_write_count']}；"
        f"源文件前后哈希一致：{report['execution_identity']['tdx_sources_unchanged']}。",
        f"- 本阶段验收：{report['acceptance_result']}；下一步：{report['next_stage']}。",
        "",
        "## TDX 日线文件",
        "",
        "| 代码 | 存在 | 首日 | 末日 | 记录 | 字节 | SHA-256 |",
        "|---|---:|---|---|---:|---:|---|",
    ]
    for code, item in ((old_code, old_tdx), (new_code, new_tdx)):
        lines.append(
            f"| {code} | {item.get('exists')} | {item.get('first_date')} | {item.get('last_date')} "
            f"| {item.get('record_count')} | {item.get('byte_count')} | {item.get('sha256')} |"
        )
    lines.extend([
        "",
        f"- 共同日期：{overlap.get('overlap_session_count')}；解码字段完全匹配："
        f"{overlap.get('exact_decoded_match_count')}；解码不匹配：{overlap.get('decoded_mismatch_count')}。",
        f"- 原始 32-byte record 完全匹配：{overlap.get('exact_raw_record_match_count')}；"
        f"最长 raw 前缀：{overlap.get('longest_common_prefix_in_records')}；"
        f"旧文件是否等于新文件完整前缀：{overlap.get('old_history_equals_full_new_prefix')}。",
        f"- 切换窗口：{tdx['window']['start_date']} ~ {tdx['window']['end_date']}；"
        f"TDX 行存在矩阵：{tdx['window']['boundary_presence']}。",
        "",
        "## 当前 TDX 证券主数据",
        "",
    ])
    for code, item in tdx["current_security_master"]["securities"].items():
        lines.append(
            f"- {code}：TNF 存在 {item['current_tnf_present']}，名称 {item['current_tnf_name']}，"
            f"行业 assignment {item['industry_assignments']}。板块分类字段未由 TNF/tdxhy.cfg 直接提供。"
        )
    signals = report["signals"]
    dual_trade_days = [
        evidence.get("trade_date")
        for contradiction in report["conclusion"]["contradictions"]
        if contradiction.get("code") == "SUBSTANTIVE_OVERLAPPING_DUAL_ACTUAL_TRADING"
        for evidence in contradiction.get("evidence", [])
    ]
    alias_duplicate_days = signals.get("F6_identical_provider_alias_bar_dates", [])
    f7 = signals["F7_old_close_new_preclose_continuity"]
    metadata = signals["F5_provider_metadata_continuity"]
    lines.extend([
        "",
        "## BaoStock",
        "",
        f"- SDK：{bao.get('runtime', {}).get('package')} {bao.get('runtime', {}).get('version')}；"
        f"请求数增量：{bao.get('request_budget', {}).get('request_count_delta')}。",
        f"- roster 前一交易日：{roster.get(report['inputs']['previous_session'])}；"
        f"有效日：{roster.get(report['inputs']['effective_date'])}。",
        f"- {old_code} 长历史：首行 {old_hist.get('first_date')}，末行 {old_hist.get('last_date')}，"
        f"行数 {old_hist.get('row_count')}。",
        f"- {new_code} 长历史：首行 {new_hist.get('first_date')}，末行 {new_hist.get('last_date')}，"
        f"行数 {new_hist.get('row_count')}；有效日前可见 {new_hist.get('pre_effective_history_visible')}。",
        f"- old/new 共有日期 {bao.get('overlap', {}).get('common_date_count')}；精确业务字段匹配 "
        f"{bao.get('overlap', {}).get('exact_business_field_match_count')}；不匹配 "
        f"{bao.get('overlap', {}).get('mismatch_count')}；差异类别 "
        f"{bao.get('overlap', {}).get('mismatch_category_counts')}。",
        f"- provider 返回 code 行为：{bao.get('provider_returned_code_behavior')}。",
        "",
        "原始短窗口、长历史与目标股票的基本资料行保存在 JSON 中，包含 query code 与 provider 返回 code。"
        "成交量/额按项目字段映射标为股/CNY 元；TDX 按项目 .day 解码器读取浮点 amount、uint32 volume 与价格比例。"
        "没有执行复权、成交量缩放或金额换算。",
        "",
        "## 切换与交叉源结果",
        "",
        "| 信号 | 结果 |",
        "|---|---|",
        f"| F1 旧文件结束于前一交易日 | {signals['F1_old_file_terminates_previous_market_session']} |",
        f"| F2 新文件含变更日前历史 | {signals['F2_new_file_contains_pre_effective_history']} |",
        f"| F3 旧文件等于新文件 raw 前缀 | {signals['F3_old_raw_history_equals_full_new_prefix']} |",
        f"| F4 BaoStock roster 原子切换 | {signals['F4_baostock_roster_atomic_flip']} |",
        f"| F5 Provider metadata | ipoDate 相同：{metadata.get('ipoDate_equal')}；名称不同：{metadata.get('code_names_differ')}；"
        f"旧 outDate：{metadata.get('old_outDate')}；新 status：{metadata.get('new_status')} |",
        f"| F6 实质不同的双代码实际交易冲突 | {signals.get('F6_substantive_dual_trade_dates', [])}；"
        f"完全相同的 provider alias bar：{alias_duplicate_days} |",
        f"| F7 收盘/前收盘衔接 | 旧 close：{f7.get('baostock_old_close')}；新 preclose："
        f"{f7.get('baostock_new_preclose')}；新 open：{f7.get('baostock_new_open')} |",
        "",
        "同日两代码查询都返回实际交易时，完全相同的业务 bar 记为 provider alias duplication candidate signal；"
        "只有业务字段不同的双边实际交易才构成 source conflict。停牌空值/零值表示差异单独归类，成交金额严格比较且无容差。",
        "",
        f"- 未决项：{[item.get('code') for item in report['conclusion']['contradictions']]}；"
        f"长历史差异分类：{bao.get('overlap', {}).get('mismatch_category_counts')}。",
        f"- 结论：{report['conclusion']['summary']}",
        f"- candidate 信号强度：{report['conclusion']['candidate_signal_strength']}；"
        "单个样本不足以定义新的 SAME_ENTITY confirmation contract。",
        "",
        "## 最终问题答复",
        "",
    ])
    for question, answer in report["final_answers"].items():
        lines.append(f"{question}. {answer}")
    lines.extend([
        "",
        "## 可复核证据",
        "",
        f"- BaoStock request ledger SHA-256：{report['baostock']['request_budget'].get('ledger_sha256_after')}",
        f"- JSON artifact SHA-256：{json_sha256}",
        "- 原始 BaoStock 查询行随 JSON 冻结；不含账户凭据。",
        "",
    ])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--old-code", required=True)
    parser.add_argument("--new-code", required=True)
    parser.add_argument("--effective-date", required=True, type=parse_date)
    parser.add_argument("--previous-session", required=True, type=parse_date)
    parser.add_argument("--tdx-root", type=Path)
    parser.add_argument("--ledger", type=Path, default=ROOT / "reports/v4_baostock/request_ledger.json")
    parser.add_argument("--task-card", type=Path)
    parser.add_argument("--history-start", type=parse_date)
    parser.add_argument("--history-end", type=parse_date)
    parser.add_argument("--window-start", type=parse_date)
    parser.add_argument("--window-end", type=parse_date)
    parser.add_argument("--json-output", type=Path)
    parser.add_argument("--markdown-output", type=Path)
    args = parser.parse_args()

    old, new = parse_code(args.old_code), parse_code(args.new_code)
    if args.previous_session >= args.effective_date:
        parser.error("previous-session must precede effective-date")
    tdx_root = args.tdx_root.resolve() if args.tdx_root else resolve_tdx_root(ROOT)
    old_code, new_code = f"{old[0]}.{old[1]}", f"{new[0]}.{new[1]}"
    window_start = args.window_start or (args.previous_session - timedelta(days=4))
    window_end = args.window_end or (args.effective_date + timedelta(days=4))
    json_output = args.json_output or ROOT / "reports/v4_01" / (
        f"V4_01_CODE_CHANGE_SOURCE_FINGERPRINT_{old[1]}_{new[1]}_R1.json"
    )
    markdown_output = args.markdown_output or ROOT / "docs/audits" / (
        f"V4_01_CODE_CHANGE_SOURCE_FINGERPRINT_{old[1]}_{new[1]}_R1.md"
    )
    ledger_path = args.ledger if args.ledger.is_absolute() else ROOT / args.ledger
    ledger_path = ledger_path.resolve()
    default_attachment = Path(
        r"D:\Users\lps\Desktop\V4_01_CODE_CHANGE_TDX_BAOSTOCK_FINGERPRINT_DIAGNOSTIC_TASK_20260928.md"
    )
    attachment = args.task_card or default_attachment
    r8_receipt_path = ROOT / "reports/v4_01/v4_01_final_stage_receipt_R8_3_20260928.json"
    upgrade_path = ROOT / "docs/V4_01_TDX_HISTORY_BOOTSTRAP_20260925.md"
    before_ledger = load_ledger(ledger_path)
    before_count = total_ledger_count(before_ledger)
    before_ledger_hash = sha256_file(ledger_path) if ledger_path.is_file() else None

    day_old = load_day_file(
        tdx_root / "vipdoc" / old[0].lower() / "lday" / f"{old[0].lower()}{old[1]}.day",
        old_code, window_start, window_end,
    )
    day_new = load_day_file(
        tdx_root / "vipdoc" / new[0].lower() / "lday" / f"{new[0].lower()}{new[1]}.day",
        new_code, window_start, window_end,
    )
    master = tdx_master_snapshot(tdx_root, [old, new])

    market_calendar_path = ROOT / "reports/phase0_1/MASTER_TRADING_CALENDAR.csv"
    sessions: list[str] = []
    calendar_status: dict[str, Any] = {
        "path": str(market_calendar_path),
        "available": market_calendar_path.is_file(),
    }
    if market_calendar_path.is_file():
        with market_calendar_path.open("r", encoding="utf-8-sig", newline="") as stream:
            for row in csv.DictReader(stream):
                if str(row.get("is_market_open", "")).lower() == "true":
                    sessions.append(str(row["calendar_date"]))
        previous_key = args.previous_session.strftime("%Y%m%d")
        effective_key = args.effective_date.strftime("%Y%m%d")
        calendar_status.update({
            "previous_session_present": previous_key in sessions,
            "effective_session_present": effective_key in sessions,
            "consecutive_open_sessions": (
                sessions.index(effective_key) == sessions.index(previous_key) + 1
                if previous_key in sessions and effective_key in sessions else False
            ),
            "sha256": sha256_file(market_calendar_path),
        })
    history_start = args.history_start or (
        date.fromisoformat(day_old["metadata"]["first_date"])
        if day_old["metadata"].get("first_date") else date(1990, 1, 1)
    )
    history_end = args.history_end or window_end
    if history_end < args.effective_date or history_start >= args.effective_date:
        parser.error("long history range must span dates before and through effective-date")

    roster_days = sorted({
        args.previous_session.isoformat(),
        args.effective_date.isoformat(),
    })

    api: dict[str, Any] = {
        "runtime": {},
        "stock_basic": {},
        "rosters": {},
        "window_history": {},
        "long_history": {},
        "query_failures": [],
    }
    try:
        api["runtime"] = {
            **package_metadata(),
            "python_version": sys.version.split()[0],
            "auth_mode": "PUBLIC_ANONYMOUS",
            "login_result": None,
            "logout_result": None,
            "endpoint": {},
        }
    except Exception as exc:
        api["runtime"] = {"runtime_identity_error": type(exc).__name__}
    started_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    client = BaoStockClient(RequestBudget(ledger_path), auth_mode="PUBLIC_ANONYMOUS", timeout=45)
    try:
        with client:
            api["runtime"].update({"login_result": client.login_result, "endpoint": client.runtime_endpoint})
            for code in (old[2], new[2]):
                print(f"BaoStock query_stock_basic: {code}", flush=True)
                try:
                    rows, metadata = client.query_rows(
                        "query_stock_basic_code_change_diagnostic", "query_stock_basic",
                        code=code, max_rows=10, max_pages=1
                    )
                    api["stock_basic"][code] = {
                        "query_code": code, "provider_rows": rows, "metadata": metadata,
                    }
                except Exception as exc:
                    api["query_failures"].append({
                        "operation": "query_stock_basic", "query_code": code,
                        "error": f"{type(exc).__name__}:{str(exc)[:240]}",
                        "last_query": client.last_query_result,
                    })
            for day in roster_days:
                print(f"BaoStock query_all_stock: {day}", flush=True)
                try:
                    api["rosters"][day] = query_roster(client, day, {old[2], new[2]})
                except Exception as exc:
                    api["query_failures"].append({
                        "operation": "query_all_stock", "day": day,
                        "error": f"{type(exc).__name__}:{str(exc)[:240]}",
                        "last_query": client.last_query_result,
                    })
            for query_code in (old[2], new[2]):
                print(f"BaoStock switch-window history: {query_code}", flush=True)
                try:
                    rows, metadata = bounded_diagnostic_history(
                        client, query_code, window_start.isoformat(), window_end.isoformat()
                    )
                    api["window_history"][query_code] = {
                        "query_code": query_code, "metadata": metadata, "raw_rows": rows,
                    }
                except Exception as exc:
                    api["query_failures"].append({
                        "operation": "window_history", "query_code": query_code,
                        "error": f"{type(exc).__name__}:{str(exc)[:240]}",
                        "last_query": client.last_query_result,
                    })
            for query_code in (old[2], new[2]):
                print(f"BaoStock long history: {query_code}", flush=True)
                try:
                    rows, metadata = bounded_diagnostic_history(
                        client, query_code, history_start.isoformat(), history_end.isoformat()
                    )
                    api["long_history"][query_code] = {
                        "query_code": query_code, "metadata": metadata, "raw_rows": rows,
                    }
                except Exception as exc:
                    api["query_failures"].append({
                        "operation": "long_history", "query_code": query_code,
                        "error": f"{type(exc).__name__}:{str(exc)[:240]}",
                        "last_query": client.last_query_result,
                    })
    except Exception as exc:
        api["query_failures"].append({
            "operation": "baostock_session",
            "error": f"{type(exc).__name__}:{str(exc)[:240]}",
        })
    api["runtime"].update({
        "login_result": api["runtime"].get("login_result") or client.login_result,
        "logout_result": client.logout_result,
        "endpoint": api["runtime"].get("endpoint") or client.runtime_endpoint,
    })

    long_summary = {}
    for code in (old[2], new[2]):
        data = api["long_history"].get(code)
        rows = data["raw_rows"] if data else []
        dates = sorted(row.get("date", "") for row in rows if row.get("date"))
        long_summary[code] = {
            "query_code": code,
            "first_row": rows[0] if rows else None,
            "last_row": rows[-1] if rows else None,
            "first_date": dates[0] if dates else None,
            "last_date": dates[-1] if dates else None,
            "row_count": len(rows),
            "pre_effective_history_visible": any(
                row.get("date", "") < args.effective_date.isoformat() for row in rows
            ),
            "provider_returned_codes": provider_code_set(rows),
        }
    old_long = api["long_history"].get(old[2], {}).get("raw_rows", [])
    new_long = api["long_history"].get(new[2], {}).get("raw_rows", [])
    bao_overlap = compare_history_rows(old_long, new_long, BUSINESS_FIELDS)

    old_basic_rows = api["stock_basic"].get(old[2], {}).get("provider_rows", [])
    new_basic_rows = api["stock_basic"].get(new[2], {}).get("provider_rows", [])
    old_basic = old_basic_rows[0] if old_basic_rows else {}
    new_basic = new_basic_rows[0] if new_basic_rows else {}
    metadata_continuity = {
        "old_ipoDate": old_basic.get("ipoDate"),
        "new_ipoDate": new_basic.get("ipoDate"),
        "ipoDate_equal": bool(old_basic and new_basic) and old_basic.get("ipoDate") == new_basic.get("ipoDate"),
        "old_code_name": old_basic.get("code_name"),
        "new_code_name": new_basic.get("code_name"),
        "code_name_equal": (
            bool(old_basic and new_basic)
            and old_basic.get("code_name") == new_basic.get("code_name")
        ),
        "code_names_differ": (
            bool(old_basic and new_basic)
            and old_basic.get("code_name") != new_basic.get("code_name")
        ),
        "code_name_equal": bool(old_basic and new_basic) and old_basic.get("code_name") == new_basic.get("code_name"),
        "code_names_differ": bool(old_basic and new_basic) and old_basic.get("code_name") != new_basic.get("code_name"),
        "old_outDate": old_basic.get("outDate"),
        "new_outDate": new_basic.get("outDate"),
        "old_status": old_basic.get("status"),
        "new_status": new_basic.get("status"),
        "both_queries_returned_rows": bool(old_basic and new_basic),
    }
    window_summary = {}
    for code in (old[2], new[2]):
        data = api["window_history"].get(code)
        rows = data["raw_rows"] if data else []
        window_summary[code] = {
            "first_date": min((row.get("date", "") for row in rows), default=None),
            "last_date": max((row.get("date", "") for row in rows), default=None),
            "row_count": len(rows),
            "provider_returned_codes": provider_code_set(rows),
            "has_previous_session_row": any(row.get("date") == args.previous_session.isoformat() for row in rows),
            "has_effective_date_row": any(row.get("date") == args.effective_date.isoformat() for row in rows),
            "previous_session_row": next(
                (row for row in rows if row.get("date") == args.previous_session.isoformat()), None
            ),
            "effective_date_row": next(
                (row for row in rows if row.get("date") == args.effective_date.isoformat()), None
            ),
        }
    roster_matrix = {
        day: {
            code: api["rosters"].get(day, {}).get("target_codes", {}).get(code, {}).get("present")
            for code in (old[2], new[2])
        }
        for day in roster_days
    }
    roster_atomic_flip = (
        roster_matrix.get(args.previous_session.isoformat(), {}).get(old[2]) is True
        and roster_matrix.get(args.previous_session.isoformat(), {}).get(new[2]) is False
        and roster_matrix.get(args.effective_date.isoformat(), {}).get(old[2]) is False
        and roster_matrix.get(args.effective_date.isoformat(), {}).get(new[2]) is True
    )
    bao_window_by_code_date = {}
    for code in (old[2], new[2]):
        for row in api["window_history"].get(code, {}).get("raw_rows", []):
            bao_window_by_code_date[(code, row.get("date"))] = row
    tdx_window_by_code_date = {}
    for code, data in ((old_code, day_old), (new_code, day_new)):
        for day, row in data["by_date"].items():
            if window_start.isoformat() <= day <= window_end.isoformat():
                tdx_window_by_code_date[(code, day)] = row
    cross_source_rows = []
    for file_code, query_code in ((old_code, old[2]), (new_code, new[2])):
        for day in (args.previous_session.isoformat(), args.effective_date.isoformat()):
            cross_source_rows.append({
                "source": "TDX .day vs BaoStock history",
                "file_code": file_code,
                "query_code": query_code,
                "trade_date": day,
                **cross_source_row(
                    tdx_window_by_code_date.get((file_code, day)),
                    bao_window_by_code_date.get((query_code, day)),
                ),
            })
    bao_window_old = api["window_history"].get(old[2], {}).get("raw_rows", [])
    bao_window_new = api["window_history"].get(new[2], {}).get("raw_rows", [])
    bao_window_overlap = compare_history_rows(bao_window_old, bao_window_new, BUSINESS_FIELDS)
    tdx_window_presence = {
        "previous_session": {
            old_code: args.previous_session.isoformat() in day_old["by_date"],
            new_code: args.previous_session.isoformat() in day_new["by_date"],
        },
        "effective_date": {
            old_code: args.effective_date.isoformat() in day_old["by_date"],
            new_code: args.effective_date.isoformat() in day_new["by_date"],
        },
    }
    dual_trade_days = []
    identical_provider_alias_bar_days = []
    for day, roster in roster_matrix.items():
        if roster.get(old[2]) is not True or roster.get(new[2]) is not True:
            continue
        old_row = bao_window_by_code_date.get((old[2], day))
        new_row = bao_window_by_code_date.get((new[2], day))
        if actual_baostock_trade(old_row) and actual_baostock_trade(new_row):
            row_comparison = compare_history_rows([old_row], [new_row], BUSINESS_FIELDS)
            evidence = {
                "source": "BaoStock roster + daily rows",
                "trade_date": day,
                "both_present_in_roster": True,
                "old_query_actual_row": old_row,
                "new_query_actual_row": new_row,
                "business_fields_exact_match": row_comparison["exact_business_field_match_count"] == 1,
                "business_field_differences": row_comparison["mismatch_samples"],
            }
            if evidence["business_fields_exact_match"]:
                identical_provider_alias_bar_days.append(evidence)
            else:
                dual_trade_days.append(evidence)

    old_tdx_meta, new_tdx_meta = day_old["metadata"], day_new["metadata"]
    tdx_overlap_result = tdx_overlap(day_old, day_new)
    old_last_matches_prev = old_tdx_meta.get("last_date") == args.previous_session.isoformat()
    new_prehistory = bool(
        new_tdx_meta.get("first_date")
        and new_tdx_meta["first_date"] < args.effective_date.isoformat()
    )
    new_bao_backfills = long_summary[new[2]]["pre_effective_history_visible"]
    bao_new_first = long_summary[new[2]]["first_date"]
    contradictions = []
    if dual_trade_days:
        contradictions.append({"code": "SUBSTANTIVE_OVERLAPPING_DUAL_ACTUAL_TRADING", "evidence": dual_trade_days})
    if any(item.get("row_count", 0) == 0 for item in long_summary.values()):
        contradictions.append({"code": "LONG_HISTORY_QUERY_EMPTY_OR_UNAVAILABLE"})
    returned_code_anomalies = {}
    for query_code, summary in long_summary.items():
        returned = summary["provider_returned_codes"]
        if returned and returned != [query_code]:
            returned_code_anomalies[query_code] = returned
    if returned_code_anomalies:
        contradictions.append({
            "code": "PROVIDER_RETURNED_CODE_DIFFERS_FROM_QUERY_CODE",
            "details": returned_code_anomalies,
        })
    if api["query_failures"]:
        contradictions.append({
            "code": "BAOSTOCK_EVIDENCE_INCOMPLETE",
            "query_failure_count": len(api["query_failures"]),
        })
    candidate_contract_path = ROOT / "config/v4_01_source_fingerprint_candidate_v1.json"
    candidate_contract = json.loads(candidate_contract_path.read_text(encoding="utf-8"))
    candidate_detector = analyze_source_fingerprint({
        "inputs": {
            "old_code": old_code,
            "new_code": new_code,
            "effective_date": args.effective_date.isoformat(),
        },
        "tdx": {
            "files": {old_code: old_tdx_meta, new_code: new_tdx_meta},
            "overlap": tdx_overlap_result,
        },
        "baostock": {
            "long_history": api["long_history"],
            "query_failures": api["query_failures"],
            "stock_basic_metadata_continuity": metadata_continuity,
            "roster_matrix": roster_matrix,
            "window_history": api["window_history"],
        },
    }, candidate_contract)
    if contradictions:
        pattern_class = "PATTERN_D_UNRESOLVED_IDENTITY_RELATION"
        candidate_strength = "BLOCKED_FAIL_CLOSED"
    elif candidate_detector["disposition"] == "STRONG_ALIAS_MIGRATION_SOURCE_FINGERPRINT_CANDIDATE":
        pattern_class = "STRONG_ALIAS_MIGRATION_SOURCE_FINGERPRINT"
        candidate_strength = "STRONG_GENERIC_IDENTITY_RELATION_CANDIDATE"
    elif candidate_detector["disposition"] == "NO_STRONG_ALIAS_FINGERPRINT_IN_SAMPLE":
        pattern_class = "PATTERN_C_SOURCES_SPLIT_BY_CODE"
        candidate_strength = "NO_STRONG_FINGERPRINT_SIGNAL"
    else:
        pattern_class = "PATTERN_D_UNRESOLVED_IDENTITY_RELATION"
        candidate_strength = "UNRESOLVED_FAIL_CLOSED"

    complete_queries = (
        len(api["stock_basic"]) == 2 and len(api["rosters"]) == len(roster_days)
        and len(api["window_history"]) == 2 and len(api["long_history"]) == 2
        and not api["query_failures"]
    )
    tdx_complete = all(item.get("exists") for item in (old_tdx_meta, new_tdx_meta))
    post_sources = {
        old_code: file_identity(Path(old_tdx_meta["path"])),
        new_code: file_identity(Path(new_tdx_meta["path"])),
    }
    for market, source in master["sources"]["tnf"].items():
        post_sources[f"security_master.tnf.{market}"] = file_identity(Path(source["path"]))
    source = master["sources"]["industry_assignment"]
    post_sources["security_master.industry_assignment"] = file_identity(Path(source["path"]))
    initial_hashes = {
        old_code: old_tdx_meta.get("sha256"),
        new_code: new_tdx_meta.get("sha256"),
        **{
            f"security_master.tnf.{market}": source.get("sha256")
            for market, source in master["sources"]["tnf"].items()
        },
        "security_master.industry_assignment": master["sources"]["industry_assignment"].get("sha256"),
    }
    tdx_unchanged = all(
        initial_hashes.get(name) == source.get("sha256")
        for name, source in post_sources.items()
    )
    ledger_after = load_ledger(ledger_path)
    after_count = total_ledger_count(ledger_after)
    ledger_sha_after = sha256_file(ledger_path) if ledger_path.is_file() else None
    stage_acceptance = (
        "PASS" if complete_queries and tdx_complete and tdx_unchanged
        else "DEGRADED_PASS" if tdx_complete and tdx_unchanged
        else "BLOCKED"
    )

    old_tdx_prev = day_old["by_date"].get(args.previous_session.isoformat())
    new_tdx_effective = day_new["by_date"].get(args.effective_date.isoformat())
    old_bao_prev = bao_window_by_code_date.get((old[2], args.previous_session.isoformat()))
    new_bao_effective = bao_window_by_code_date.get((new[2], args.effective_date.isoformat()))

    def relative_difference(reference: Any, observed: Any) -> float | None:
        try:
            left, right = float(reference), float(observed)
            return None if left == 0 else (right / left) - 1.0
        except (TypeError, ValueError, ZeroDivisionError):
            return None

    signals = {
        "F1_old_file_terminates_previous_market_session": old_last_matches_prev,
        "F2_new_file_contains_pre_effective_history": new_prehistory,
        "F3_old_raw_history_equals_full_new_prefix": tdx_overlap_result["old_history_equals_full_new_prefix"],
        "F4_baostock_roster_atomic_flip": roster_atomic_flip,
        "F5_provider_metadata_continuity": metadata_continuity,
        **f6_actual_trading_signals(dual_trade_days, identical_provider_alias_bar_days),
        "F6_check_scope": {
            "session_rosters_queried": roster_days,
            "actual_trade_checked_only_when_both_codes_are_rostered": True,
        },
        "F7_old_close_new_preclose_continuity": {
            "tdx_old_close": old_tdx_prev.get("close") if old_tdx_prev else None,
            "tdx_new_effective_open": new_tdx_effective.get("open") if new_tdx_effective else None,
            "tdx_new_open_vs_old_close_return": relative_difference(
                old_tdx_prev.get("close") if old_tdx_prev else None,
                new_tdx_effective.get("open") if new_tdx_effective else None,
            ),
            "baostock_old_close": old_bao_prev.get("close") if old_bao_prev else None,
            "baostock_new_preclose": new_bao_effective.get("preclose") if new_bao_effective else None,
            "baostock_new_open": new_bao_effective.get("open") if new_bao_effective else None,
            "baostock_preclose_vs_old_close_return": relative_difference(
                old_bao_prev.get("close") if old_bao_prev else None,
                new_bao_effective.get("preclose") if new_bao_effective else None,
            ),
            "baostock_open_vs_old_close_return": relative_difference(
                old_bao_prev.get("close") if old_bao_prev else None,
                new_bao_effective.get("open") if new_bao_effective else None,
            ),
            "interpretation": "descriptive_only_no_corporate_action_or_identity_inference",
        },
    }
    observed_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    input_commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    r8_receipt_path = ROOT / "reports/v4_01/v4_01_final_stage_receipt_R8_3_20260928.json"
    upgrade_path = ROOT / "docs/V4_01_TDX_HISTORY_BOOTSTRAP_20260925.md"
    report: dict[str, Any] = {
        "contract_id": CONTRACT_ID,
        "contract_version": CONTRACT_VERSION,
        "stage": "V4-01 CODE-CHANGE SOURCE FINGERPRINT DIAGNOSTIC",
        "acceptance_result": stage_acceptance,
        "observed_at_utc": observed_at,
        "inputs": {
            "old_code": old_code,
            "new_code": new_code,
            "effective_date": args.effective_date.isoformat(),
            "previous_session": args.previous_session.isoformat(),
            "window_start": window_start.isoformat(),
            "window_end": window_end.isoformat(),
            "history_start": history_start.isoformat(),
            "history_end": history_end.isoformat(),
            "tdx_root": str(tdx_root),
            "request_ledger": str(ledger_path),
        },
        "stage_contract": {
            "purpose": "read-only source-behavior study and identity-relation candidate evidence",
            "canonical_identity_mutation": False,
            "historical_universe_mutation": False,
            "v4_02_v4_03_artifact_mutation": False,
            "accepted_head_mutation": False,
            "automated_trading_or_probability_claims": False,
            "baostock_auth_mode": "PUBLIC_ANONYMOUS",
            "baostock_fields": DIAGNOSTIC_FIELDS,
            "baostock_frequency": "d",
            "baostock_adjustflag": "3",
            "request_bounds": {"max_rows_per_history_query": 10000, "max_pages_per_history_query": 20},
            "production_change_authorized": False,
            "does_not_supersede_latest_v4_01_owner_gate": True,
        },
        "baseline": {
            "task_card_path": str(attachment),
            "task_card_sha256": sha256_file(attachment) if attachment.is_file() else None,
            "latest_v4_01_stage_receipt": str(r8_receipt_path),
            "latest_v4_01_stage_receipt_sha256": (
                sha256_file(r8_receipt_path) if r8_receipt_path.is_file() else None
            ),
            "latest_applicable_upgrade_document": str(upgrade_path),
            "latest_applicable_upgrade_document_sha256": (
                sha256_file(upgrade_path) if upgrade_path.is_file() else None
            ),
            "latest_stage_receipt_status": (
                json.loads(r8_receipt_path.read_text(encoding="utf-8")).get("status")
                if r8_receipt_path.is_file() else None
            ),
        },
        "tdx": {
            "files": {old_code: old_tdx_meta, new_code: new_tdx_meta},
            "window": {
                "start_date": window_start.isoformat(),
                "end_date": window_end.isoformat(),
                "rows": {
                    old_code: old_tdx_meta.get("window_rows", []),
                    new_code: new_tdx_meta.get("window_rows", []),
                },
                "boundary_presence": tdx_window_presence,
            },
            "overlap": tdx_overlap_result,
            "current_security_master": master,
            "post_execution_source_files": post_sources,
        },
        "baostock": {
            **api,
            "request_budget": {
                "ledger_path": str(ledger_path),
                "request_count_before": before_count,
                "request_count_after": after_count,
                "request_count_delta": after_count - before_count,
                "ledger_sha256_before": before_ledger_hash,
                "ledger_sha256_after": ledger_sha_after,
                "shanghai_day_count": ledger_after.get("by_shanghai_date", {}).get(
                    datetime.now(ZoneInfo("Asia/Shanghai")).date().isoformat(), {}
                ).get("count", 0),
                "soft_limit": 40000,
                "hard_limit": 45000,
            },
            "roster_matrix": roster_matrix,
            "roster_atomic_flip": roster_atomic_flip,
            "stock_basic_metadata_continuity": metadata_continuity,
            "window_history_summary": window_summary,
            "long_history_summary": long_summary,
            "overlap": bao_overlap,
            "window_overlap": bao_window_overlap,
            "provider_returned_code_behavior": {
                code: {
                    "provider_returned_codes": long_summary[code]["provider_returned_codes"],
                    "matches_query_code_only": long_summary[code]["provider_returned_codes"] in ([], [code]),
                }
                for code in (old[2], new[2])
            },
            "raw_rows_preserved": {
                "stock_basic": "baostock.stock_basic.*.provider_rows",
                "window_history": "baostock.window_history.*.raw_rows",
                "long_history": "baostock.long_history.*.raw_rows",
                "roster_target_rows": "baostock.rosters.*.target_codes.*.provider_rows",
            },
        },
        "cross_source": {
            "switch_matrix": [
                {
                    "source": row["source"],
                    "query_or_file_code": row["query_code"],
                    "trade_date": row["trade_date"],
                    "row_exists": {"tdx": row["tdx_row_exists"], "baostock": row["baostock_row_exists"]},
                    "tdx": row.get("field_comparisons"),
                }
                for row in cross_source_rows
            ],
            "row_comparisons": cross_source_rows,
            "unit_notes": {
                "TDX": "project DAY_STRUCT decoder: OHLC uint32 divided by 100; amount stored as IEEE float32; volume uint32 shares",
                "BaoStock": "project field mapping uses volume_shares and amount_cny; raw rows preserved without scaling",
                "comparison": "numeric raw-field comparison; no adjustment, volume scaling, or amount conversion; float32 amount precision can differ from provider decimals",
            },
        },
        "signals": signals,
        "candidate_detector": {
            "contract_id": candidate_contract["contract_id"],
            "contract_version": candidate_contract["version"],
            "contract_sha256": sha256_file(candidate_contract_path),
            **candidate_detector,
        },
        "conclusion": {
            "pattern_class": pattern_class,
            "candidate_signal_strength": candidate_strength,
            "summary": (
                "Contradictory or incomplete source evidence remains unresolved; fail closed."
                if contradictions else
                "Source behavior is descriptive candidate evidence only. A strong fingerprint remains candidate-only; independent evidence is required for SAME_ENTITY."
                if candidate_detector["disposition"] == "STRONG_ALIAS_MIGRATION_SOURCE_FINGERPRINT_CANDIDATE" else
                "No strong alias-migration fingerprint was established; retain unresolved or split-by-code research status."
            ),
            "detected_signals": [key for key, value in signals.items() if value is True],
            "contradictions": contradictions,
            "source_query_failures": api["query_failures"],
            "recommend_new_confirmation_contract": False,
            "candidate_auto_link_allowed": False,
            "production_change_authorized": False,
            "upstream_v4_01_owner_gate_cleared": False,
        },
        "calendar_check": calendar_status,
        "execution_identity": {
            "input_commit": input_commit,
            "script_sha256": sha256_file(Path(__file__)),
            "observed_at_utc": started_at,
            "tdx_root_write_count": 0,
            "tdx_sources_unchanged": tdx_unchanged,
            "python_version": sys.version.split()[0],
        },
        "next_stage": (
            "DESIGN_GENERIC_CANDIDATE_DETECTOR_AND_BLIND_TEST_MULTIPLE_KNOWN_CODE_CHANGES"
            if pattern_class == "STRONG_ALIAS_MIGRATION_SOURCE_FINGERPRINT"
            else "RETAIN_R8_3_EVIDENCE_POLICY_AND_REASSESS_OFFICIAL_EVENT_COMPLETENESS_GATE"
        ),
        "final_answers": {},
    }
    report["final_answers"] = {
        "1": f"TDX 同时存在：{old_code}={old_tdx_meta.get('exists')}，{new_code}={new_tdx_meta.get('exists')}。",
        "2": f"{old_code}.day 最后日期 {old_tdx_meta.get('last_date')}。",
        "3": f"{new_code}.day 首日期 {new_tdx_meta.get('first_date')}。",
        "4": f"包含有效日前历史：{new_prehistory}。",
        "5": f"两文件共同日期 {tdx_overlap_result['overlap_session_count']}。",
        "6": f"共同日期 raw 32-byte 完全相同 {tdx_overlap_result['exact_raw_record_match_count']}。",
        "7": f"旧文件是否等于新文件完整前缀：{tdx_overlap_result['old_history_equals_full_new_prefix']}；"
             f"最长前缀 {tdx_overlap_result['longest_common_prefix_in_records']} 条。",
        "8": f"BaoStock {args.previous_session.isoformat()} roster：{roster_matrix.get(args.previous_session.isoformat())}。",
        "9": f"BaoStock {args.effective_date.isoformat()} roster：{roster_matrix.get(args.effective_date.isoformat())}。",
        "10": f"BaoStock 新代码查询有效日前历史：{new_bao_backfills}；first row {bao_new_first}。",
        "11": f"BaoStock 旧代码行数 {long_summary[old[2]]['row_count']}，"
              f"边界 {long_summary[old[2]]['first_date']} ~ {long_summary[old[2]]['last_date']}。",
        "12": f"BaoStock old/new overlap {bao_overlap['common_date_count']} dates, "
              f"exact {bao_overlap['exact_business_field_match_count']}, mismatch {bao_overlap['mismatch_count']}。",
        "13": f"Provider returned code behavior {report['baostock']['provider_returned_code_behavior']}。",
        "14": f"综合模式 {pattern_class}；强度 {candidate_strength}。",
        "15": (
            "强 alias-migration source fingerprint，仅足以生成通用 candidate；不足以建立 SAME_ENTITY confirmation contract。仍须独立正式证据。"
            if candidate_detector["disposition"] == "STRONG_ALIAS_MIGRATION_SOURCE_FINGERPRINT_CANDIDATE"
            else "没有从本样本建立强 alias-migration fingerprint；保留 split-by-code 或 unresolved 研究状态，不修改 identity。"
        ),
        "16": (
            f"provider alias duplicate 实际交易日期：{signals['F6_identical_provider_alias_bar_dates']}；"
            f"实质不同的双边实际交易日期：{signals['F6_substantive_dual_trade_dates']}。"
            f"BaoStock 长历史差异类别：{bao_overlap['mismatch_category_counts']}；停牌空值/零值仅按研究合同归一，成交金额不设置容差。"
        ),
    }
    report_path = json_output if json_output.is_absolute() else ROOT / json_output
    markdown_path = markdown_output if markdown_output.is_absolute() else ROOT / markdown_output
    json_bytes = (json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")
    json_sha = hashlib.sha256(json_bytes).hexdigest()
    atomic_write(report_path, json_bytes, tdx_root)
    atomic_write(markdown_path, render_markdown(report, json_sha).encode("utf-8"), tdx_root)
    print(json.dumps({
        "acceptance_result": stage_acceptance,
        "pattern_class": pattern_class,
        "candidate_signal_strength": candidate_strength,
        "json_output": str(report_path),
        "json_sha256": json_sha,
        "markdown_output": str(markdown_path),
        "request_count_delta": after_count - before_count,
        "query_failures": api["query_failures"],
        "tdx_sources_unchanged": tdx_unchanged,
    }, ensure_ascii=False, indent=2))
    return 0 if stage_acceptance == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
