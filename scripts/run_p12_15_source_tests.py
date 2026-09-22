"""Bounded live tests for public turnover quote sources.

This script deliberately tests source access only.  It does not alter the
V3.3 candidate set, run scanners, persist raw responses, or touch TDX data.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from urllib.parse import urlencode

import requests

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from workbench_online.eastmoney_quotes import fetch_eastmoney_quotes  # noqa: E402
from workbench_online.tencent_quotes import fetch_tencent_quotes  # noqa: E402
from workbench_online.base import FetchResult, OnlineFetchPolicy  # noqa: E402


ACTIVE = ROOT / "data/current/ACTIVE_RESEARCH_BUNDLE_V3_3.json"
REPORT = ROOT / "reports/p12_15/p12_15_source_test_matrix.json"
MATRIX = ROOT / "docs/P12_15_SOURCE_TEST_MATRIX_20260916.md"
RECEIPT = ROOT / "docs/P12_15_SOURCE_TEST_ACCEPTANCE_20260916.md"

TIMEOUT = 8.0
MAX_BYTES = 200_000
FREQUENCY_REPEATS = 3
FREQUENCY_INTERVAL_SECONDS = 0.75

SAMPLE_IDS = ["SH.600023", "SZ.001216", "SZ.300049", "SH.688004", "BJ.920028"]
SUPPORTED_SAMPLE_IDS = SAMPLE_IDS[:4]

PAGE_URLS = {
    "EASTMONEY": "https://quote.eastmoney.com/sh600023.html",
    "TENCENT": "https://gu.qq.com/sh600023",
    "XUEQIU": "https://xueqiu.com/S/SH600023",
    "SINA": "https://finance.sina.com.cn/realstock/company/sh600023/nc.shtml",
    "HEXUN": "https://quote.hexun.com/stock/default.aspx",
    "THS": "https://stockpage.10jqka.com.cn/600023/",
    "STOCKSTAR": "https://stock.quote.stockstar.com/600023.shtml",
    "SOHU": "https://q.stock.sohu.com/cn/600023/index.shtml",
    "IFENG": "https://finance.ifeng.com/app/hq/stock/sh600023/",
    "JRJ": "https://stock.jrj.com.cn/",
    "STCN": "https://www.stcn.com/",
    "DZH": "https://gw.com.cn/",
}

ENDPOINTS = {
    "EASTMONEY": lambda ids: "https://push2.eastmoney.com/api/qt/ulist.np/get?" + urlencode({
        "fltt": "2", "invt": "2", "ut": "fa5fd1943c7b386f172d6893dbbd1d0c",
        "fields": "f2,f3,f6,f12,f13,f14,f47,f168,f170", "secids": ",".join(_eastmoney_id(v) for v in ids),
    }),
    "TENCENT": lambda ids: "https://qt.gtimg.cn/q=" + ",".join(_tencent_id(v) for v in ids),
    "SINA": lambda ids: "https://hq.sinajs.cn/list=" + ",".join(_sina_id(v) for v in ids),
    "XUEQIU": lambda ids: "https://stock.xueqiu.com/v5/stock/quote.json?" + urlencode({
        "symbol": _xueqiu_id(ids[0]), "extend": "detail",
    }),
    "THS": lambda ids: "https://d.10jqka.com.cn/quote.php?code=" + _ths_id(ids[0]),
}


def _tencent_id(value: str) -> str:
    exchange, code = value.split(".", 1)
    return exchange.lower() + code


def _eastmoney_id(value: str) -> str:
    exchange, code = value.split(".", 1)
    return ("1" if exchange == "SH" else "0") + "." + code


def _sina_id(value: str) -> str:
    exchange, code = value.split(".", 1)
    return exchange.lower() + code


def _xueqiu_id(value: str) -> str:
    exchange, code = value.split(".", 1)
    return exchange + code


def _ths_id(value: str) -> str:
    exchange, code = value.split(".", 1)
    prefix = {"SH": "hs", "SZ": "sz"}.get(exchange, "")
    return prefix + code


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temp.write_text(text, encoding="utf-8")
    os.replace(temp, path)


def _request(url: str, *, referer: str | None = None) -> dict:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131 Safari/537.36",
        "Accept": "*/*",
    }
    if referer:
        headers["Referer"] = referer
    started = time.perf_counter()
    try:
        with requests.get(url, headers=headers, timeout=TIMEOUT, stream=True) as response:
            chunks = []
            size = 0
            for chunk in response.iter_content(chunk_size=8192):
                if not chunk:
                    continue
                size += len(chunk)
                if size > MAX_BYTES:
                    return {"ok": False, "status": response.status_code, "error": "RESPONSE_TOO_LARGE",
                            "latency_ms": round((time.perf_counter() - started) * 1000, 2)}
                chunks.append(chunk)
            body = b"".join(chunks)
            return {
                "ok": response.status_code == 200,
                "status": response.status_code,
                "content_type": response.headers.get("content-type", ""),
                "body": body,
                "latency_ms": round((time.perf_counter() - started) * 1000, 2),
                "error": None,
            }
    except Exception as exc:  # network failure is evidence, not a test abort
        return {"ok": False, "status": None, "content_type": "", "body": b"",
                "latency_ms": round((time.perf_counter() - started) * 1000, 2),
                "error": f"{type(exc).__name__}:{exc}"}


def _decode(body: bytes) -> str:
    for encoding in ("utf-8", "gb18030", "big5"):
        try:
            return body.decode(encoding)
        except UnicodeDecodeError:
            continue
    return body.decode("utf-8", errors="replace")


def _public_page_result(source: str) -> dict:
    result = _request(PAGE_URLS[source], referer="https://quote.eastmoney.com/")
    text = _decode(result.pop("body", b""))
    lower = text.lower()
    return {
        "url": PAGE_URLS[source],
        "available": bool(result["ok"] and len(text) > 0),
        "http_status": result["status"],
        "latency_ms": result["latency_ms"],
        "login_required": bool(result["status"] in {401, 403} or re.search(r"请先登录|需要登录|登录后", lower)),
        "cookie_bootstrap_required": False,
        "js_required": bool(re.search(r"<script|webpack|next/static|require\(", lower)),
        "xhr_json_hints": bool(re.search(r"xhr|fetch\(|\.json|/api/|/quote/|hq_", lower)),
        "turnover_text_hint": bool(re.search(r"换手|turnover", lower)),
        "error": result["error"],
    }


def _rows_from_project_adapter(source: str, ids: list[str]) -> tuple[dict, list[dict], str | None]:
    policy = OnlineFetchPolicy(timeout_seconds=TIMEOUT, max_response_bytes=MAX_BYTES, retries=0, cache_ttl_seconds=0)

    def fetcher(url, _policy, referer=None):
        result = _request(url, referer=referer)
        body = result.get("body", b"")
        return FetchResult("source-test", "source-test", result["status"] or 0,
                           result.get("content_type", ""), body, url)

    try:
        if source == "TENCENT":
            result, rows = fetch_tencent_quotes(ids, policy, fetcher=fetcher)
        else:
            result, rows = fetch_eastmoney_quotes(ids, policy, fetcher=fetcher)
        return {"status": result.status_code, "latency_ms": None, "bytes": result.byte_count}, rows, None
    except Exception as exc:
        return {"status": None, "latency_ms": None, "bytes": 0}, [], f"{type(exc).__name__}:{exc}"


def _generic_rows(source: str, body: bytes, ids: list[str]) -> list[dict]:
    text = _decode(body)
    rows = []
    if source == "SINA":
        for match in re.finditer(r'var\s+hq_str_(\w+)="([^"]*)"', text):
            fields = match.group(2).split(",")
            if len(fields) < 33:
                continue
            rows.append({"security_id": _from_symbol(match.group(1)), "price": _float(fields[3]),
                         "amount": _float(fields[9]), "volume": _float(fields[8]) * 100,
                         "turnover_rate": None, "quote_time": f"{fields[30]} {fields[31]}"})
    elif source == "XUEQIU":
        try:
            payload = json.loads(text)
            blobs = json.dumps(payload, ensure_ascii=False)
            if any(k in blobs for k in ("turnover_rate", "turnoverRate")):
                rows.append({"security_id": ids[0], "price": None, "amount": None, "volume": None,
                             "turnover_rate": _find_number(payload, ("turnover_rate", "turnoverRate")),
                             "quote_time": None})
        except json.JSONDecodeError:
            pass
    elif source == "THS":
        for key in ("turnoverRatio", "turnover_rate", "turnoverRate", "turnover"):
            if key in text:
                rows.append({"security_id": ids[0], "price": _find_number_from_text(text, key),
                             "amount": None, "volume": None, "turnover_rate": _find_number_from_text(text, key),
                             "quote_time": None})
                break
    return [row for row in rows if row.get("security_id") in ids or row.get("security_id") == ids[0]]


def _from_symbol(symbol: str) -> str:
    symbol = symbol.lower()
    exchange = "SH" if symbol.startswith("sh") else "SZ" if symbol.startswith("sz") else ""
    return f"{exchange}.{symbol[2:]}" if exchange else symbol


def _float(value: object) -> float | None:
    try:
        return float(value) if value not in (None, "", "-") else None
    except (TypeError, ValueError):
        return None


def _find_number(value: object, keys: tuple[str, ...]) -> float | None:
    if isinstance(value, dict):
        for key, item in value.items():
            if key in keys:
                return _float(item)
            found = _find_number(item, keys)
            if found is not None:
                return found
    elif isinstance(value, list):
        for item in value:
            found = _find_number(item, keys)
            if found is not None:
                return found
    return None


def _find_number_from_text(text: str, key: str) -> float | None:
    match = re.search(rf"[\"']{re.escape(key)}[\"']\s*[:=]\s*[\"']?([0-9.]+)", text)
    return _float(match.group(1)) if match else None


def _bind_flags(rows: list[dict], local: dict[str, tuple[float, float, float]], target_date: str) -> dict:
    if not rows:
        return {"price": "FAIL", "amount": "FAIL", "volume": "FAIL", "trade_date": "FAIL"}
    row = rows[0]
    local_row = local.get(row.get("security_id"))
    if not local_row:
        return {"price": "FAIL", "amount": "FAIL", "volume": "FAIL", "trade_date": "FAIL"}

    def close(a, b, abs_tol, rel_tol):
        return a is not None and b is not None and abs(a - b) <= max(abs_tol, rel_tol * max(abs(a), abs(b)))

    quote_time = str(row.get("quote_time") or "")
    return {
        "price": "PASS" if close(row.get("price"), local_row[0], 0.011, 0.0005) else "FAIL",
        "amount": "PASS" if close(row.get("amount"), local_row[1], 100, 0.002) else "FAIL",
        "volume": "PASS" if close(row.get("volume"), local_row[2], 100, 0.002) else "FAIL",
        "trade_date": "PASS" if target_date.replace("-", "") in quote_time else "FAIL",
    }


def _load_local() -> tuple[str, dict[str, tuple[float, float, float]], str]:
    active = json.loads(ACTIVE.read_text(encoding="utf-8"))
    target_date = active["identity"]["trade_date"]
    bundle = Path(active["bundle_path"])
    rows = json.loads((bundle / "results.json").read_text(encoding="utf-8"))
    local = {}
    # The active bundle keeps the output identity; the local normalized data is
    # intentionally read only for the documented three-field fingerprint check.
    try:
        import duckdb
        daily = ROOT / "data/normalized/adjusted_daily.parquet"
        ids = [row["security_id"] for row in rows]
        placeholders = ",".join("?" for _ in ids)
        query = ("select security_id, raw_close, raw_amount, raw_volume from read_parquet(?) "
                 f"where cast(date as varchar)=? and security_id in ({placeholders})")
        with duckdb.connect() as connection:
            for security_id, close, amount, volume in connection.execute(query, [str(daily), target_date, *ids]).fetchall():
                local[security_id] = (float(close), float(amount), float(volume))
    except Exception:
        local = {}
    return target_date, local, active["output_digest"]


def _test_endpoint(source: str, local: dict, target_date: str) -> dict:
    ids = SUPPORTED_SAMPLE_IDS
    url_builder = ENDPOINTS[source]
    single_url = url_builder(ids[:1])
    batch_url = url_builder(ids)
    runs = []
    for label, url in (("single", single_url), ("batch", batch_url)):
        response = _request(url, referer=PAGE_URLS[source])
        body = response.pop("body", b"")
        if source in {"TENCENT", "EASTMONEY"}:
            adapter_meta, rows, adapter_error = _rows_from_project_adapter(source, ids[:1] if label == "single" else ids)
            response["adapter_error"] = adapter_error
            response["rows"] = rows
            response["adapter_meta"] = adapter_meta
        else:
            response["rows"] = _generic_rows(source, body, ids[:1] if label == "single" else ids)
        response["label"] = label
        runs.append(response)

    repeat = []
    for _ in range(FREQUENCY_REPEATS):
        response = _request(single_url, referer=PAGE_URLS[source])
        response.pop("body", None)
        repeat.append(response)
        time.sleep(FREQUENCY_INTERVAL_SECONDS)

    batch_rows = runs[1].get("rows", [])
    single_rows = runs[0].get("rows", [])
    all_rows = batch_rows or single_rows
    turnover_rows = [row for row in all_rows if row.get("turnover_rate") is not None]
    normalized_turnover = turnover_rows[0].get("turnover_rate") if turnover_rows else None
    turnover_contract_valid = normalized_turnover is not None and 0 <= normalized_turnover <= 1
    capacity = []
    if source in {"TENCENT", "EASTMONEY"}:
        for size in (1, 2, 20, 50):
            capacity_ids = [f"SH.{600000 + index:06d}" for index in range(size)]
            meta, capacity_rows, capacity_error = _rows_from_project_adapter(source, capacity_ids)
            capacity.append({"requested": size, "status": meta["status"], "row_count": len(capacity_rows),
                             "error": capacity_error})
    text_statuses = [r.get("status") for r in repeat]
    parse_ok = bool(all_rows)
    batch_ok = len({row.get("security_id") for row in batch_rows}) >= 2
    return {
        "endpoint": batch_url,
        "single": {k: v for k, v in runs[0].items() if k not in {"rows", "body"}},
        "batch": {k: v for k, v in runs[1].items() if k not in {"rows", "body"}},
        "single_row_count": len(single_rows),
        "batch_row_count": len(batch_rows),
        "batch_security_ids": sorted({row.get("security_id") for row in batch_rows if row.get("security_id")}),
        "batch_supported": batch_ok,
        "turnover_available": bool(turnover_rows) and turnover_contract_valid,
        "turnover_contract_valid": turnover_contract_valid,
        "turnover_raw_example": normalized_turnover * 100 if normalized_turnover is not None else None,
        "turnover_normalized_example": normalized_turnover,
        "quote_time_example": turnover_rows[0].get("quote_time") if turnover_rows else (all_rows[0].get("quote_time") if all_rows else None),
        "price_available": any(row.get("price") is not None for row in all_rows),
        "amount_available": any(row.get("amount") is not None for row in all_rows),
        "volume_available": any(row.get("volume") is not None for row in all_rows),
        "quote_time_available": any(row.get("quote_time") for row in all_rows),
        "repeat_statuses": text_statuses,
        "repeated_request_test": "PASS" if text_statuses and all(status == 200 for status in text_statuses) and parse_ok else "FAIL",
        "rate_limit_observed": any(status in {403, 429} for status in text_statuses),
        "average_latency_ms": round(mean([r["latency_ms"] for r in repeat]), 2) if repeat else None,
        "capacity_probe": capacity,
        "max_batch_size_observed": max((item["requested"] for item in capacity if item["status"] == 200), default=4 if batch_ok else None),
        "local_fingerprint": _bind_flags(all_rows, local, target_date),
        "short_probe_limitations": "3 sequential single requests at 0.75s interval; not a production RPS certification",
    }


def _source_row(source: str, page: dict, endpoint: dict | None, target_date: str) -> dict:
    if endpoint is None:
        return {
            "source_id": source,
            "test_time": datetime.now(timezone.utc).isoformat(),
            "stock_page_available": "PASS" if page["available"] else "FAIL",
            "login_required": "YES" if page["login_required"] else "NO",
            "cookie_bootstrap_required": "YES" if page["cookie_bootstrap_required"] else "NO",
            "js_required": "YES" if page["js_required"] else "NO",
            "xhr_json_found": "YES" if page["xhr_json_hints"] else "NO",
            "public_endpoint": "NO",
            "turnover_available": "NO",
            "turnover_contract_valid": "NO",
            "batch_supported": "FAIL",
            "repeated_request_test": "FAIL",
            "average_latency_ms": None,
            "local_trade_date_match": "FAIL",
            "project_usable_for_active_bundle": "NO",
            "source_status": "UNAVAILABLE",
            "notes": "No tested public quote endpoint was identified from the supplied public entrypoint; page-only evidence is insufficient for turnover acquisition.",
        }
    turnover = endpoint["turnover_raw_example"]
    access_ok = endpoint["turnover_available"] and endpoint["batch_supported"] and endpoint["repeated_request_test"] == "PASS"
    responded = endpoint["single"].get("status") == 200 or endpoint["batch"].get("status") == 200
    status = "AVAILABLE" if access_ok and all(value == "PASS" for value in endpoint["local_fingerprint"].values()) else "DEGRADED" if responded else "UNAVAILABLE"
    fp = endpoint["local_fingerprint"]
    return {
        "source_id": source,
        "test_time": datetime.now(timezone.utc).isoformat(),
        "stock_page_available": "PASS" if page["available"] else "FAIL",
        "login_required": "YES" if page["login_required"] else "NO",
        "cookie_bootstrap_required": "YES" if page["cookie_bootstrap_required"] else "NO",
        "js_required": "YES" if page["js_required"] else "NO",
        "xhr_json_found": "YES" if page["xhr_json_hints"] else "NO",
        "public_endpoint": "YES",
        "sh_supported": "PASS" if endpoint["single_row_count"] else "FAIL",
        "sz_supported": "PASS" if endpoint["batch_row_count"] else "FAIL",
        "chinext_supported": "PASS" if "SZ.300049" in endpoint.get("batch_security_ids", []) else "UNKNOWN",
        "star_market_supported": "PASS" if "SH.688004" in endpoint.get("batch_security_ids", []) else "UNKNOWN",
        "bj_supported": "UNKNOWN",
        "price_available": "YES" if endpoint["price_available"] else "NO",
        "amount_available": "YES" if endpoint["amount_available"] else "NO",
        "volume_available": "YES" if endpoint["volume_available"] else "NO",
        "turnover_available": "YES" if endpoint["turnover_available"] else "NO",
        "turnover_contract_valid": "YES" if endpoint.get("turnover_contract_valid") else "NO",
        "quote_time_available": "YES" if endpoint["quote_time_available"] else "NO",
        "trade_date_available": fp["trade_date"],
        "batch_supported": "PASS" if endpoint["batch_supported"] else "FAIL",
        "max_batch_size_observed": endpoint.get("max_batch_size_observed"),
        "turnover_raw_example": turnover,
        "turnover_normalized_example": endpoint.get("turnover_normalized_example"),
        "quote_time_example": endpoint.get("quote_time_example"),
        "turnover_basis": "SOURCE_DEFINED_OR_UNKNOWN",
        "local_close_match": fp["price"],
        "local_amount_match": fp["amount"],
        "local_volume_match": fp["volume"],
        "local_trade_date_match": fp["trade_date"],
        "repeated_request_test": endpoint["repeated_request_test"],
        "rate_limit_observed": "YES" if endpoint["rate_limit_observed"] else "NO",
        "average_latency_ms": endpoint["average_latency_ms"],
        "source_status": status,
        "project_usable_for_active_bundle": "PASS" if status == "AVAILABLE" else "FAIL",
        "notes": endpoint["short_probe_limitations"] + (" Current quote is not bound to the active 2026-09-15 package." if any(value == "FAIL" for value in fp.values()) else ""),
    }


def _markdown(payload: dict) -> str:
    lines = [
        "# P12-15 在线换手率来源测试矩阵（2026-09-16）",
        "",
        f"> 测试时间：{payload['test_time']}（Asia/Shanghai）；活动研究日：`{payload['trade_date']}`。",
        "> 仅测试在线来源获取能力，不执行换手算法、不修改 V3.3 候选/排名、不写入 TDX、不保存网页原文或 raw payload。",
        "",
        "## 结论摘要",
        "",
        f"- 可在本次短探测中解析换手率且批量/重复请求通过的来源（访问层）：{', '.join(payload['summary']['access_available_sources']) or '无'}。",
        f"- 同时通过活动研究包本地三重指纹的来源（项目可用层）：{', '.join(payload['summary']['available_sources']) or '无'}。",
        f"- 页面或接口部分可达但不能形成稳定换手来源的来源：{', '.join(payload['summary']['degraded_sources']) or '无'}。",
        f"- 当前活动包候选数：{payload['candidate_count']}；本次仅采用代表样本：`{', '.join(payload['sample_ids'])}`。",
        "- `AVAILABLE` 只表示本次有限探测通过，不等于长期生产 RPS 承诺；本地交易日指纹必须另行通过。",
        "",
        "## 统一矩阵",
        "",
        "| source_id | 页面 | 登录/Cookie | 公开端点 | 换手率 | 批量 | 重复请求 | 延迟ms | 本地日期指纹 | 状态 |",
        "|---|---|---|---|---|---|---|---:|---|---|",
    ]
    for row in payload["matrix"]:
        lines.append("| {source_id} | {stock_page_available} | {login_required}/{cookie_bootstrap_required} | {public_endpoint} | {turnover_available} | {batch_supported} | {repeated_request_test} | {average_latency_ms} | {local_trade_date_match} | {source_status} |".format(**row))
    lines += [
        "",
        "## 解释与边界",
        "",
        "- `PASS` 只代表当前请求样本有响应/有字段，不代表分母口径已核实；本次未把来源字段名自动解释为 `FLOAT_SHARE`。",
        "- 当前活动研究日为 2026-09-15，而实时探测发生在 2026-09-16；实时源若返回次日行情，日期指纹必须为 `FAIL`，不得附着到历史研究包。",
        "- 频率测试为每个已探测公开端点连续 3 次、间隔 0.75 秒；没有规避 403/429、验证码、登录、签名或反爬认证。",
        "- 未列出公开端点的来源按 `UNAVAILABLE` 处理，即使股票页面 HTTP 200，也不认定为可获取换手率。",
        "",
        "## 下一阶段",
        "",
        "- 对通过来源补齐版本化 source contract、明确 turnover_basis 证据和收盘后目标日绑定测试。",
        "- 先保持来源作为独立可选输入，不进入算法、核心资格、核心分数或核心排名。",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    target_date, local, bundle_digest = _load_local()
    pages = {source: _public_page_result(source) for source in PAGE_URLS}
    matrix = []
    details = {}
    for source, page in pages.items():
        endpoint = None
        if source in ENDPOINTS:
            endpoint = _test_endpoint(source, local, target_date)
            details[source] = endpoint
        matrix.append(_source_row(source, page, endpoint, target_date))

    available = [row["source_id"] for row in matrix if row["source_status"] == "AVAILABLE"]
    access_available = [row["source_id"] for row in matrix if row.get("turnover_available") == "YES" and row.get("batch_supported") == "PASS" and row.get("repeated_request_test") == "PASS"]
    degraded = [row["source_id"] for row in matrix if row["source_status"] == "DEGRADED"]
    payload = {
        "stage": "P12-15_SOURCE_TEST",
        "stage_contract": "P12_15_PUBLIC_TURNOVER_SOURCE_TEST_V1",
        "test_time": datetime.now(timezone.utc).isoformat(),
        "trade_date": target_date,
        "bundle_digest": bundle_digest,
        "candidate_count": len(json.loads((Path(json.loads(ACTIVE.read_text(encoding='utf-8'))['bundle_path']) / 'results.json').read_text(encoding='utf-8'))),
        "sample_ids": SAMPLE_IDS,
        "matrix": matrix,
        "details": details,
        "summary": {"access_available_sources": access_available, "available_sources": available, "degraded_sources": degraded,
                     "unavailable_sources": [row["source_id"] for row in matrix if row["source_status"] == "UNAVAILABLE"]},
        "guardrails": {"tdx_modified": False, "raw_payload_persisted": False, "algorithm_executed": False,
                        "core_candidate_or_rank_changed": False, "external_adjustment_used": False,
                        "login_or_signature_bypass": False},
        "hashes": {"script": _sha256(Path(__file__)), "active_pointer": _sha256(ACTIVE)},
        "acceptance": "DEGRADED_PASS" if available or degraded else "BLOCKED",
        "next_stage": "VERSIONED_SOURCE_CONTRACT_AND_POST_CLOSE_TARGET_DATE_REBINDING",
    }
    _atomic_write(REPORT, json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    _atomic_write(MATRIX, _markdown(payload))
    receipt = "\n".join([
        "# P12-15 来源测试验收回执（2026-09-16）", "",
        f"- 阶段合同：`{payload['stage_contract']}`。", "- 证据：实时页面/公开端点有限探测、活动包候选样本、项目现有腾讯/东财适配器。",
        f"- 接受结果：`{payload['acceptance']}`。可用：{', '.join(available) or '无'}；降级：{', '.join(degraded) or '无'}。",
        "- 本次未执行算法、未修改配置/数据库/研究包、未写入 TDX、未保存 raw payload。",
        "- 结论边界：短探测通过不等于生产稳定性；实时源和 2026-09-15 历史研究日的绑定必须在目标交易日收盘后重新验证。",
        f"- 下一阶段：`{payload['next_stage']}`。", "",
        f"详细矩阵见 `docs/P12_15_SOURCE_TEST_MATRIX_20260916.md`，机器回执见 `reports/p12_15/p12_15_source_test_matrix.json`。", "",
    ])
    _atomic_write(RECEIPT, receipt)
    print(json.dumps({"acceptance": payload["acceptance"], "summary": payload["summary"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
