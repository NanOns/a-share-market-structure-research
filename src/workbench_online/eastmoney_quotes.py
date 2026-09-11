"""Ephemeral Eastmoney quote enrichment for the M14 hot-rank display."""

from __future__ import annotations

import json
from typing import Callable, Iterable
from urllib.parse import urlencode

from .base import FetchResult, OnlineFetchPolicy, bounded_get


EASTMONEY_QUOTE_SOURCE_ID = "EASTMONEY_QUOTES_LATEST"
EASTMONEY_QUOTE_URL = "https://push2.eastmoney.com/api/qt/ulist.np/get"
MAX_SECURITY_IDS = 50


def _optional_float(value: object, *, field: str) -> float | None:
    if value in (None, "", "-"):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"QUOTE_FIELD_INVALID:{field}") from exc
    return None if number < 0 and field in {"price", "amount", "volume", "turnover_rate"} else number


def _secid(security_id: str) -> str | None:
    value = str(security_id or "")
    if "." not in value:
        return None
    exchange, code = value.split(".", 1)
    if exchange not in {"SH", "SZ"} or len(code) != 6 or not code.isdigit():
        return None
    return f"{'1' if exchange == 'SH' else '0'}.{code}"


def fetch_eastmoney_quotes(
    security_ids: Iterable[str],
    policy: OnlineFetchPolicy | None = None,
    *,
    fetcher: Callable[..., FetchResult] = bounded_get,
) -> tuple[FetchResult, list[dict]]:
    policy = policy or OnlineFetchPolicy(cache_ttl_seconds=0, personal_research_only=True)
    requested_ids = list(dict.fromkeys(str(value) for value in security_ids if value))
    if not requested_ids or len(requested_ids) > MAX_SECURITY_IDS:
        raise ValueError("QUOTE_SECURITY_ID_LIMIT")
    secids = [_secid(value) for value in requested_ids]
    if any(value is None for value in secids):
        raise ValueError("QUOTE_SECURITY_ID_UNMAPPED")
    params = {
        "fltt": "2",
        "invt": "2",
        "fields": "f2,f3,f6,f12,f13,f14,f47,f168,f170",
        "secids": ",".join(secids),
    }
    result = fetcher(EASTMONEY_QUOTE_URL + "?" + urlencode(params), policy)
    if result.status_code != 200:
        raise ValueError(f"QUOTE_HTTP_STATUS:{result.status_code}")
    try:
        payload = json.loads(result.body.decode("utf-8"))
        diff = payload["data"]["diff"]
    except (UnicodeDecodeError, KeyError, TypeError, json.JSONDecodeError) as exc:
        raise ValueError("QUOTE_SCHEMA_INVALID") from exc
    if not isinstance(diff, list):
        raise ValueError("QUOTE_SCHEMA_INVALID")
    by_code = {value.split(".", 1)[1]: value for value in requested_ids}
    rows = []
    for item in diff:
        if not isinstance(item, dict):
            raise ValueError("QUOTE_SCHEMA_INVALID")
        code = str(item.get("f12") or "")
        exchange = "SH" if str(item.get("f13")) == "1" else "SZ" if str(item.get("f13")) == "0" else None
        security_id = f"{exchange}.{code}" if exchange and code in by_code else by_code.get(code)
        if not security_id:
            continue
        price = _optional_float(item.get("f2"), field="price")
        ret1_percent = _optional_float(item.get("f3"), field="ret1")
        amount = _optional_float(item.get("f6"), field="amount")
        volume = _optional_float(item.get("f47"), field="volume")
        turnover_rate_percent = _optional_float(item.get("f168"), field="turnover_rate")
        rows.append(
            {
                "source_id": EASTMONEY_QUOTE_SOURCE_ID,
                "source_code": code,
                "security_id": security_id,
                "quote_time": None,
                "observed_at_utc": result.received_at_utc,
                "price": price,
                "ret1": ret1_percent / 100 if ret1_percent is not None else None,
                "amount": amount,
                "volume": volume,
                "turnover_rate": turnover_rate_percent / 100 if turnover_rate_percent is not None else None,
                "quote_state": "UNKNOWN",
                "time_semantics": "OBSERVED_AT_ONLY",
                "price_unit": "CNY_PER_SHARE",
                "amount_unit": "CNY",
                "volume_unit": "SHARES",
                "source_name": item.get("f14"),
            }
        )
    return result, rows
