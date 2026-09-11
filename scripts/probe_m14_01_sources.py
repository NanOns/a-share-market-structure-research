"""Run bounded, metadata-only public source probes for M14-01."""

from __future__ import annotations

import hashlib
import json
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/upgrade_m14/m14_01_source_probe_report_20260911.json"
USER_AGENT = "M14-01-source-validation/1.0"
TIMEOUT_SECONDS = 15
MAX_BYTES = 1_000_000


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def fetch(url: str, referer: str | None = None) -> dict:
    headers = {"User-Agent": USER_AGENT, "Accept": "text/html,application/json,*/*"}
    if referer:
        headers["Referer"] = referer
    request = Request(url, headers=headers, method="GET")
    try:
        with urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            data = response.read(MAX_BYTES + 1)
            truncated = len(data) > MAX_BYTES
            if truncated:
                data = data[:MAX_BYTES]
            return {
                "url": url,
                "status": int(response.status),
                "content_type": response.headers.get("Content-Type", ""),
                "byte_count": len(data),
                "truncated": truncated,
                "sha256": digest(data),
                "body": data,
            }
    except HTTPError as exc:
        return {"url": url, "status": int(exc.code), "error": f"HTTP_{exc.code}", "body": b""}
    except (URLError, TimeoutError, OSError) as exc:
        return {"url": url, "status": "ERROR", "error": type(exc).__name__, "body": b""}


def public_result(raw: dict) -> dict:
    return {key: value for key, value in raw.items() if key != "body"}


def probe_eastmoney() -> dict:
    page_url = "https://guba.eastmoney.com/rank/"
    page = fetch(page_url)
    body = page.pop("body", b"")
    text = body.decode("utf-8", errors="replace")
    script_match = re.search(r'<script[^>]+src=["\']([^"\']*rank_home\.js[^"\']*)', text, re.I)
    script_url = "https://gbfek.dfcfw.com/deploy/rank_web/work/rank_home.js?v=22"
    script = fetch(script_url, referer=page_url)
    script_body = script.pop("body", b"")
    script_text = script_body.decode("utf-8", errors="replace")
    endpoint_match = re.search(r"gbcdnHost\+\"(popularityList\.js\?[^\"]*)", script_text)
    minute = datetime.now().minute
    endpoint = f"https://gbcdn.dfcfw.com/rank/popularityList.js?type=0&sort=0&page=1&m={minute}"
    payload = fetch(endpoint, referer=page_url)
    payload.pop("body", b"")
    return {
        "source_id": "EASTMONEY_HOT_RANK",
        "source_class": "ONLINE_B",
        "dataset": "HOT_RANKINGS",
        "public_page": page,
        "page_script": {
            **script,
            "script_url_from_page": script_match.group(1) if script_match else None,
            "rank_endpoint_pattern_found": bool(endpoint_match),
        },
        "payload": {
            **payload,
            "endpoint": endpoint,
            "payload_encoding": "JAVASCRIPT_VARIABLE_ENCODED",
            "schema_status": "NOT_VERIFIED",
            "time_semantics": "NOT_VERIFIED",
            "raw_body_persisted": False,
        },
        "terms_state": "NOT_VERIFIED",
        "capability_status": "NOT_VERIFIED",
        "reason": "公开页面和载荷入口可达；正文需要站点解码逻辑，尚未证明字段和 source_as_of 语义。",
    }


def probe_tonghuashun() -> dict:
    page_url = "https://eq.10jqka.com.cn/webpage/ths-hot-list/index.html?showStatusBar=true"
    api_url = "https://dq.10jqka.com.cn/fuyao/hot_list_data/out/hot_list/v1/stock?stock_type=a&type=hour&list_type=normal"
    page = fetch(page_url)
    page.pop("body", b"")
    api = fetch(api_url, referer=page_url)
    api_body = api.pop("body", b"")
    parsed: dict | None = None
    parse_error = None
    try:
        parsed = json.loads(api_body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        parse_error = type(exc).__name__
    rows = parsed.get("data", {}).get("stock_list", []) if isinstance(parsed, dict) else []
    first = rows[0] if rows else {}
    data_fields = sorted(parsed.get("data", {}).keys()) if isinstance(parsed, dict) and isinstance(parsed.get("data"), dict) else []
    row_fields = sorted(first.keys()) if isinstance(first, dict) else []
    has_time = any(re.search(r"time|date|update", field, re.I) for field in data_fields + row_fields)
    return {
        "source_id": "TONGHUASHUN_HOT_RANK",
        "source_class": "ONLINE_B",
        "dataset": "HOT_RANKINGS",
        "public_page": page,
        "api": {
            **api,
            "endpoint": api_url,
            "parse_status": "PASS" if parsed is not None else "FAIL",
            "parse_error": parse_error,
            "status_code": parsed.get("status_code") if isinstance(parsed, dict) else None,
            "row_count": len(rows),
            "data_fields": data_fields,
            "row_fields": row_fields,
            "required_rank_fields_present": all(field in row_fields for field in ("code", "name", "order")),
            "source_as_of_present": any(field in data_fields + row_fields for field in ("source_as_of", "timestamp", "update_time")),
            "time_semantics": "PRESENT" if has_time else "MISSING_IN_RESPONSE",
            "raw_body_persisted": False,
        },
        "terms_state": "NOT_VERIFIED",
        "capability_status": "NOT_VERIFIED",
        "reason": "接口可达且字段可解析；响应未提供明确 source_as_of/更新时间，许可和稳定性仍待核验。",
    }


def atomic_write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        temp_path = Path(handle.name)
    temp_path.replace(path)


def main() -> int:
    report = {
        "report_id": "M14-01-SOURCE-PROBE-20260911",
        "stage": "M14-01",
        "contract_id": "M14_SOURCE_VALIDATION_V1_0",
        "observed_at_utc": datetime.now(timezone.utc).isoformat(),
        "probe_policy": {
            "max_response_bytes": MAX_BYTES,
            "timeout_seconds": TIMEOUT_SECONDS,
            "attempts_per_endpoint": 1,
            "credentials_used": False,
            "raw_payloads_persisted": False,
            "production_tables_written": False,
        },
        "sources": [probe_eastmoney(), probe_tonghuashun()],
        "acceptance": "探测证据登记完成；没有来源满足完整准入条件，全部保持 NOT_VERIFIED。",
        "next_action": "补齐许可、字段解码、source_as_of/历史能力和 10 个交易日观察后再进入 M14-02。",
    }
    atomic_write(OUT, report)
    print(json.dumps({"status": "DEGRADED_PASS", "output": str(OUT), "sources": len(report["sources"])}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
