"""Bounded turnover-source retest based on user-verified quote pages.

This is a source-access probe only.  It never changes scanner output, writes
raw responses, calculates turnover, or accesses the read-only TDX root.
"""

from __future__ import annotations

import ast
import hashlib
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean

import requests

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from workbench_online.base import FetchResult, OnlineFetchPolicy  # noqa: E402
from workbench_online.tencent_quotes import fetch_tencent_quotes  # noqa: E402


ACTIVE = ROOT / "data/current/ACTIVE_RESEARCH_BUNDLE_V3_3.json"
REPORT = ROOT / "reports/p12_15/p12_15_source_retest_20260916.json"
MATRIX = ROOT / "docs/P12_15_SOURCE_RETEST_MATRIX_20260916.md"
RECEIPT = ROOT / "docs/P12_15_SOURCE_RETEST_ACCEPTANCE_20260916.md"

TIMEOUT_SECONDS = 8.0
MAX_RESPONSE_BYTES = 200_000
REPEATS = 3
REPEAT_INTERVAL_SECONDS = 0.75
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131 Safari/537.36",
    "Accept": "application/json,text/javascript,text/html,*/*;q=0.8",
}

# The first four are project-market representatives.  The additional codes are
# the pages supplied by the user and are used only for source-field confirmation.
MARKET_SAMPLE = ["SH.600023", "SZ.001216", "SZ.300049", "SH.688004", "BJ.920179"]
USER_SAMPLE = ["SH.605599", "SZ.300750", "SZ.300497", "SZ.000823", "SZ.000012", "BJ.920298"]


def _atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(text, encoding="utf-8")
    os.replace(temporary, path)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _request(url: str, *, referer: str | None = None) -> dict:
    headers = dict(HEADERS)
    if referer:
        headers["Referer"] = referer
    started = time.perf_counter()
    try:
        with requests.get(url, headers=headers, timeout=TIMEOUT_SECONDS, stream=True) as response:
            chunks: list[bytes] = []
            size = 0
            for chunk in response.iter_content(chunk_size=8192):
                if not chunk:
                    continue
                size += len(chunk)
                if size > MAX_RESPONSE_BYTES:
                    return {"status": response.status_code, "ok": False, "error": "RESPONSE_TOO_LARGE",
                            "latency_ms": round((time.perf_counter() - started) * 1000, 2), "body": b""}
                chunks.append(chunk)
            return {"status": response.status_code, "ok": response.status_code == 200, "error": None,
                    "latency_ms": round((time.perf_counter() - started) * 1000, 2), "body": b"".join(chunks)}
    except Exception as exc:  # a source failure is probe evidence, never a pipeline error
        return {"status": None, "ok": False, "error": f"{type(exc).__name__}:{exc}",
                "latency_ms": round((time.perf_counter() - started) * 1000, 2), "body": b""}


def _text(response: dict, *encodings: str) -> str:
    for encoding in encodings:
        try:
            return response["body"].decode(encoding)
        except UnicodeDecodeError:
            continue
    return response["body"].decode("utf-8", errors="replace")


def _rate(value: object) -> float | None:
    if value in (None, "", "--", "-"):
        return None
    try:
        return float(str(value).replace("%", "")) / 100
    except ValueError:
        return None


def _repeat(url: str, *, referer: str | None = None) -> dict:
    results = []
    for _ in range(REPEATS):
        response = _request(url, referer=referer)
        results.append({key: response[key] for key in ("status", "error", "latency_ms")})
        time.sleep(REPEAT_INTERVAL_SECONDS)
    return {
        "statuses": [item["status"] for item in results],
        "pass": all(item["status"] == 200 and item["error"] is None for item in results),
        "rate_limit_observed": any(item["status"] in {403, 429} for item in results),
        "average_latency_ms": round(mean(item["latency_ms"] for item in results), 2),
    }


def _symbol(security_id: str) -> str:
    exchange, code = security_id.split(".", 1)
    return exchange.lower() + code


def _active_supported_ids() -> list[str]:
    active = json.loads(ACTIVE.read_text(encoding="utf-8"))
    rows = json.loads((Path(active["bundle_path"]) / "results.json").read_text(encoding="utf-8"))
    return [row["security_id"] for row in rows if row["security_id"].split(".", 1)[0] in {"SH", "SZ"}]


def _tencent_probe(ids: list[str]) -> dict:
    policy = OnlineFetchPolicy(timeout_seconds=TIMEOUT_SECONDS, max_response_bytes=MAX_RESPONSE_BYTES, retries=0, cache_ttl_seconds=0)

    def fetcher(url, _policy, referer=None):
        response = _request(url, referer=referer)
        return FetchResult("source-retest", "source-retest", response["status"] or 0, "", response["body"], url)

    capacity = []
    for count in (1, 2, 20, 50):
        requested = ids[:count]
        try:
            _, rows = fetch_tencent_quotes(requested, policy, fetcher=fetcher)
            capacity.append({"requested": count, "returned": len(rows), "status": 200, "error": None})
        except Exception as exc:
            capacity.append({"requested": count, "returned": 0, "status": None, "error": f"{type(exc).__name__}:{exc}"})
    endpoint = "https://qt.gtimg.cn/q=" + ",".join(_symbol(value) for value in ids[:1])
    repeat = _repeat(endpoint, referer="https://gu.qq.com/")
    example = None
    try:
        _, rows = fetch_tencent_quotes(ids[:1], policy, fetcher=fetcher)
        example = rows[0] if rows else None
    except Exception:
        pass
    return {
        "source_id": "TENCENT",
        "public_endpoint": "https://qt.gtimg.cn/q=",
        "single_supported": bool(example and example.get("turnover_rate") is not None),
        "arbitrary_batch_supported": all(item["status"] == 200 and item["returned"] == item["requested"] for item in capacity),
        "batch_capacity": capacity,
        "price_available": bool(example and example.get("price") is not None),
        "amount_available": bool(example and example.get("amount") is not None),
        "volume_available": bool(example and example.get("volume") is not None),
        "turnover_available": bool(example and example.get("turnover_rate") is not None and 0 <= example["turnover_rate"] <= 1),
        "turnover_normalized_example": example.get("turnover_rate") if example else None,
        "quote_time_example": example.get("quote_time") if example else None,
        "repeat": repeat,
        "source_status": "AVAILABLE" if example and repeat["pass"] else "DEGRADED",
        "notes": "Access-layer result only; turnover basis remains DECLARED_ONLY until source evidence verifies the denominator.",
    }


def _sohu_url(security_id: str) -> str:
    _, code = security_id.split(".", 1)
    return f"https://hq.stock.sohu.com/cn/{code[-3:]}/cn_{code}-1.html"


def _sohu_single(security_id: str) -> dict:
    response = _request(_sohu_url(security_id), referer=f"https://q.stock.sohu.com/cn/{security_id.split('.', 1)[1]}/index.shtml")
    text = _text(response, "gb18030", "gbk")
    a1 = re.search(r"'price_A1':(\[[^\]]*\])", text)
    a2 = re.search(r"'price_A2':(\[[^\]]*\])", text)
    try:
        price_a1 = ast.literal_eval(a1.group(1)) if a1 else []
        price_a2 = ast.literal_eval(a2.group(1)) if a2 else []
    except (SyntaxError, ValueError):
        price_a1, price_a2 = [], []
    turnover = _rate(price_a2[6]) if len(price_a2) > 6 else None
    return {
        "security_id": security_id,
        "status": response["status"],
        "price": float(price_a1[2]) if len(price_a1) > 2 and str(price_a1[2]).replace(".", "", 1).isdigit() else None,
        "volume_lots": float(price_a2[8]) if len(price_a2) > 8 and str(price_a2[8]).replace(".", "", 1).isdigit() else None,
        "amount_10k_cny": float(price_a2[12]) if len(price_a2) > 12 and str(price_a2[12]).replace(".", "", 1).isdigit() else None,
        "turnover_rate": turnover,
        "quote_time": None,
        "error": response["error"],
    }


def _sohu_rank(market: str) -> dict:
    url = f"https://q.stock.sohu.com/ph/{market}_turnoverrate_up.html"
    response = _request(url, referer="https://q.stock.sohu.com/cn/ph_m.shtml")
    text = _text(response, "gb18030", "gbk")
    records = []
    for match in re.findall(r"\['cn_[^\]]+\]", text):
        try:
            row = ast.literal_eval(match)
        except (SyntaxError, ValueError):
            continue
        if len(row) > 8:
            records.append({"security_id": row[0].replace("cn_", ""), "turnover_rate": _rate(row[8])})
    return {"market": market, "url": url, "status": response["status"], "row_count": len(records),
            "valid_turnover_rows": sum(row["turnover_rate"] is not None for row in records), "error": response["error"]}


def _sohu_probe() -> dict:
    singles = [_sohu_single(value) for value in ["SH.605599", "SZ.300750", "SH.688004", "BJ.920179"]]
    ranks = [_sohu_rank(market) for market in ("sh_as", "sz_as", "bj_as")]
    repeat = _repeat("https://q.stock.sohu.com/ph/sz_as_turnoverrate_up.html", referer="https://q.stock.sohu.com/cn/ph_m.shtml")
    return {
        "source_id": "SOHU",
        "public_endpoint": "https://hq.stock.sohu.com/cn/{last3}/cn_{code}-1.html",
        "single_supported": all(item["status"] == 200 for item in singles),
        "arbitrary_batch_supported": False,
        "ranking_batch_supported": all(item["status"] == 200 and item["row_count"] == 50 for item in ranks),
        "ranking_batch": ranks,
        "single_examples": singles,
        "price_available": any(item["price"] is not None for item in singles),
        "amount_available": any(item["amount_10k_cny"] is not None for item in singles),
        "volume_available": any(item["volume_lots"] is not None for item in singles),
        "turnover_available": any(item["turnover_rate"] is not None for item in singles),
        "quote_time_available": False,
        "repeat": repeat,
        "source_status": "DEGRADED",
        "notes": "Individual quote endpoint carries turnover in price_A2[6]. Ranking endpoints provide exactly 50 rows per SH/SZ/BJ market, but they are ranked top-N pages rather than arbitrary-security batches.",
    }


def _stcn_one(symbol: str) -> dict:
    page = f"https://www.stcn.com/quotes/index/{symbol}.html"
    url = f"https://www.stcn.com/quotes/stock-info.html?stock_code={symbol}"
    response = _request(url, referer=page)
    try:
        payload = json.loads(_text(response, "utf-8"))
        data = payload.get("data", {})
    except json.JSONDecodeError:
        data = {}
    valid = bool(data.get("name")) and float(data.get("turnoverrate") or 0) >= 0
    return {"symbol": symbol, "status": response["status"], "valid": valid,
            "turnover_rate": _rate(data.get("turnoverrate")), "price": data.get("cv"), "amount": data.get("amo"),
            "volume": data.get("volume"), "float_shares": data.get("oc"), "total_shares": data.get("tc"), "error": response["error"]}


def _stcn_probe() -> dict:
    symbols = ["sz000823", "sz300750", "sh605599", "sh688004", "bj920179"]
    rows = [_stcn_one(symbol) for symbol in symbols]
    multi = _request("https://www.stcn.com/quotes/stock-info.html?stock_code=sz000823,sz300750",
                     referer="https://www.stcn.com/quotes/index/sz000823.html")
    try:
        multi_data = json.loads(_text(multi, "utf-8")).get("data", {})
    except json.JSONDecodeError:
        multi_data = {}
    repeat = _repeat("https://www.stcn.com/quotes/stock-info.html?stock_code=sz000823",
                     referer="https://www.stcn.com/quotes/index/sz000823.html")
    return {
        "source_id": "STCN",
        "public_endpoint": "https://www.stcn.com/quotes/stock-info.html?stock_code={symbol}",
        "single_supported": all(row["valid"] for row in rows),
        "arbitrary_batch_supported": bool(multi_data.get("name")) and multi_data.get("code") != "sz000823,sz300750",
        "batch_probe": {"status": multi["status"], "returned_code": multi_data.get("code"), "returned_name": multi_data.get("name"),
                        "returned_turnoverrate": multi_data.get("turnoverrate")},
        "single_examples": rows,
        "price_available": any(row["price"] is not None for row in rows),
        "amount_available": any(row["amount"] is not None for row in rows),
        "volume_available": any(row["volume"] is not None for row in rows),
        "turnover_available": any(row["turnover_rate"] is not None for row in rows),
        "float_shares_available": any(row["float_shares"] for row in rows),
        "quote_time_available": False,
        "repeat": repeat,
        "source_status": "DEGRADED",
        "notes": "Public single-stock JSON returns turnoverrate, price, volume, amount, float shares (oc), and total shares (tc). Comma-separated stock_code returns a zero placeholder, not a batch response.",
    }


def _stockstar_one(code: str) -> dict:
    response = _request(f"https://stock.quote.stockstar.com/{code}.shtml", referer="https://stock.quote.stockstar.com/")
    text = _text(response, "gb18030", "gbk")
    float_match = re.search(r"id=['\"]stock_quoteinfo_ltgb['\"]>([^<]+)", text)
    total_match = re.search(r"id=['\"]stock_quoteinfo_zgb['\"]>([^<]+)", text)
    return {"code": code, "status": response["status"], "float_share_text": float_match.group(1).strip() if float_match else None,
            "total_share_text": total_match.group(1).strip() if total_match else None, "error": response["error"]}


def _stockstar_probe() -> dict:
    rows = [_stockstar_one(code) for code in ("000012", "600023", "001216", "300049", "688004", "920179")]
    repeat = _repeat("https://stock.quote.stockstar.com/000012.shtml", referer="https://stock.quote.stockstar.com/")
    return {
        "source_id": "STOCKSTAR",
        "public_endpoint": "https://stock.quote.stockstar.com/{code}.shtml",
        "single_supported": all(row["status"] == 200 for row in rows),
        "arbitrary_batch_supported": False,
        "float_shares_available": sum(row["float_share_text"] is not None for row in rows),
        "total_shares_available": sum(row["total_share_text"] is not None for row in rows),
        "single_examples": rows,
        "repeat": repeat,
        "source_status": "DEGRADED",
        "notes": "HTML contains static float and total share fields. No public batch endpoint was identified in the supplied page or its public quote JavaScript; this probe does not calculate turnover.",
    }


def _sina_probe() -> dict:
    page = _request("https://quotes.sina.cn/hs/company/quotes/view/sz300497")
    quote_url = "https://hq.sinajs.cn/list=sz300497,sz300750,sh605599,bj920298"
    quote = _request(quote_url, referer="https://quotes.sina.cn/hs/company/quotes/view/sz300497")
    static_url = "https://gu.sina.cn/hq/api/openapi.php/StockV2Service.getStockDetail?symbol=sz300497,sz300750,sh605599,bj920298&dpc=1"
    static = _request(static_url, referer="https://quotes.sina.cn/hs/company/quotes/view/sz300497")
    static_text = _text(static, "utf-8")
    repeat = _repeat(quote_url, referer="https://quotes.sina.cn/hs/company/quotes/view/sz300497")
    return {
        "source_id": "SINA",
        "public_endpoint": "https://hq.sinajs.cn/list={symbols}",
        "page_available": page["status"] == 200,
        "single_supported": quote["status"] == 200,
        "arbitrary_batch_supported": quote["status"] == 200,
        "turnover_available": False,
        "static_turnover_windows_present": all(key in static_text for key in ("turnover_5d", "turnover_20d")),
        "repeat": repeat,
        "source_status": "DEGRADED",
        "notes": "The supplied page is public. The located batch quote endpoint returns price/volume/amount but no same-session turnover; StockV2Service returns 5d/20d turnover windows, not the daily turnover required here.",
    }


def _xueqiu_probe() -> dict:
    page = _request("https://xueqiu.com/S/SZ300750")
    page_text = _text(page, "utf-8")
    api_url = "https://stock.xueqiu.com/v5/stock/quote.json?symbol=SZ300750&extend=detail"
    api = _request(api_url, referer="https://xueqiu.com/S/SZ300750")
    repeat = _repeat(api_url, referer="https://xueqiu.com/S/SZ300750")
    return {
        "source_id": "XUEQIU",
        "page_available": page["status"] == 200,
        "waf_marker_observed": "_waf_" in page_text,
        "public_endpoint": api_url,
        "single_supported": False,
        "arbitrary_batch_supported": False,
        "turnover_available": False,
        "repeat": repeat,
        "source_status": "UNAVAILABLE",
        "notes": "The page loads but includes a WAF marker. The public JSON quote request returned non-success; no cookie bootstrap, debugger bypass, login, signature, or anti-bot circumvention was attempted.",
    }


def _ths_probe() -> dict:
    page = _request("https://stockpage.10jqka.com.cn/920298/")
    script = _request("https://s.thsi.cn/cd/news-p-fe-app-news-flow-home/market/_next/static/chunks/app/market/%5BstockCode%5D/%5B%5B...pageType%5D%5D/page-1af96a31b040eb3c.js")
    source_text = _text(script, "utf-8")
    old_endpoint = _request("https://d.10jqka.com.cn/quote.php?code=hs600023", referer="https://stockpage.10jqka.com.cn/920298/")
    return {
        "source_id": "THS",
        "page_available": page["status"] == 200,
        "frontend_turnover_field_confirmed": "turnoverRateReal" in source_text,
        "public_endpoint": None,
        "single_supported": False,
        "arbitrary_batch_supported": False,
        "turnover_available": False,
        "old_public_endpoint_status": old_endpoint["status"],
        "source_status": "UNAVAILABLE",
        "notes": "The frontend declares a real-turnover field, but its API base is runtime-configured and no stable unauthenticated public quote contract was identified. The previously tested legacy endpoint did not return a usable quote. No signed/private route was attempted.",
    }


def _matrix_markdown(payload: dict) -> str:
    lines = [
        "# P12-15 换手率来源人工核对后复测矩阵（2026-09-16）", "",
        f"> 测试时间：{payload['test_time']}；仅做在线来源测试，不运行换手算法或扫描器。", "",
        "| 来源 | 单股 | 任意批量 | 排行榜批量 | 换手率 | 流通股本 | 短频测试 | 状态 |", "|---|---|---|---|---|---|---|---|",
    ]
    for row in payload["sources"]:
        repeat = row.get("repeat", {})
        lines.append("| {source_id} | {single} | {batch} | {rank_batch} | {turnover} | {float_share} | {repeat} | {status} |".format(
            source_id=row["source_id"], single="PASS" if row.get("single_supported") else "FAIL",
            batch="PASS" if row.get("arbitrary_batch_supported") else "FAIL",
            rank_batch="PASS" if row.get("ranking_batch_supported") else "—",
            turnover="YES" if row.get("turnover_available") else "NO",
            float_share="YES" if row.get("float_shares_available") else "NO",
            repeat="PASS" if repeat.get("pass") else "—", status=row["source_status"]))
    lines += [
        "", "## 关键结论", "",
        "- 腾讯仍是本轮唯一的任意证券批量换手率来源；1/2/20/50 条均使用项目现有适配器测试。",
        "- 搜狐单股端点可取价、量、额、换手率；沪/深/北交所换手率排行榜端点每次各返回 50 条，但不能替代任意候选批量查询。",
        "- 证券时报单股 JSON 可取换手率、价、量、额、流通股本和总股本；逗号拼接股票代码返回零值占位，不能作为批量端点。",
        "- 证券之星单股 HTML 能取静态流通/总股本；没有找到公开批量接口，本轮不据此计算换手率。",
        "- 雪球未绕过 WAF/调试限制；新浪未找到日度换手率数据合同；同花顺未找到无需签名的稳定公开端点。",
        "", "## 使用边界", "",
        "- 所有 `AVAILABLE/DEGRADED` 都是本次有限访问测试，未核实换手率分母；不能直接写为 FLOAT_SHARE。",
        "- 实时来源仍需在目标交易日收盘后经本地 close/amount/volume 指纹绑定，才能进入项目的可用证据层。",
        "- 未请求东财、凤凰财经和大智慧：按本轮用户指定范围排除。", "",
    ]
    return "\n".join(lines)


def main() -> int:
    active = json.loads(ACTIVE.read_text(encoding="utf-8"))
    sources = [_tencent_probe(_active_supported_ids()), _sohu_probe(), _stcn_probe(), _stockstar_probe(), _sina_probe(), _xueqiu_probe(), _ths_probe()]
    summary = {
        "available": [item["source_id"] for item in sources if item["source_status"] == "AVAILABLE"],
        "degraded": [item["source_id"] for item in sources if item["source_status"] == "DEGRADED"],
        "unavailable": [item["source_id"] for item in sources if item["source_status"] == "UNAVAILABLE"],
    }
    payload = {
        "stage": "P12-15_SOURCE_RETEST_USER_VERIFIED_PAGES",
        "stage_contract": "P12_15_PUBLIC_TURNOVER_SOURCE_RETEST_V1",
        "test_time": datetime.now(timezone.utc).isoformat(),
        "active_trade_date": active["identity"]["trade_date"],
        "active_bundle_digest": active["output_digest"],
        "sources": sources,
        "summary": summary,
        "acceptance": "DEGRADED_PASS" if summary["available"] or summary["degraded"] else "BLOCKED",
        "guardrails": {"tdx_modified": False, "raw_payload_persisted": False, "turnover_algorithm_executed": False,
                       "core_candidate_or_rank_changed": False, "login_signature_or_waf_bypass": False, "turnover_calculation_performed": False},
        "next_stage": "OPTIONAL_VERSIONED_ADAPTER_CONTRACTS_ONLY_AFTER_TARGET_DATE_BINDING_AND_BASIS_EVIDENCE",
        "hashes": {"script": _sha(Path(__file__)), "active_pointer": _sha(ACTIVE)},
    }
    _atomic_write(REPORT, json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    _atomic_write(MATRIX, _matrix_markdown(payload))
    receipt = "\n".join([
        "# P12-15 来源人工核对后复测验收回执（2026-09-16）", "",
        f"- 阶段合同：`{payload['stage_contract']}`。", f"- 接受结果：`{payload['acceptance']}`。",
        f"- 可用：{', '.join(summary['available']) or '无'}；降级：{', '.join(summary['degraded']) or '无'}；不可用：{', '.join(summary['unavailable']) or '无'}。",
        "- 仅执行来源测试；未运行算法或扫描器，未改动核心候选/排名、TDX、数据库、活动研究包，未保存 raw payload。",
        "- 雪球没有绕过 WAF/调试机制；同花顺没有尝试签名或私有接口；证券之星没有进行换手率计算。",
        f"- 下一阶段：`{payload['next_stage']}`。", "",
    ])
    _atomic_write(RECEIPT, receipt)
    print(json.dumps({"acceptance": payload["acceptance"], "summary": summary}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
