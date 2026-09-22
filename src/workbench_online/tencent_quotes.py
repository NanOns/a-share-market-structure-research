"""Bounded Tencent latest-quote adapter used as a P12-14 fallback source."""

from __future__ import annotations

from typing import Callable, Iterable
from urllib.parse import quote

from .base import FetchResult, OnlineFetchPolicy, bounded_get


TENCENT_QUOTE_SOURCE_ID = "TENCENT_QUOTES_LATEST"
TENCENT_QUOTE_URL = "https://qt.gtimg.cn/q="
MAX_SECURITY_IDS = 50


def _symbol(security_id: str) -> str | None:
    value = str(security_id or "")
    if "." not in value:
        return None
    exchange, code = value.split(".", 1)
    if exchange not in {"SH", "SZ"} or len(code) != 6 or not code.isdigit():
        return None
    return exchange.lower() + code


def fetch_tencent_quotes(
    security_ids: Iterable[str],
    policy: OnlineFetchPolicy | None = None,
    *,
    fetcher: Callable[..., FetchResult] = bounded_get,
) -> tuple[FetchResult, list[dict]]:
    policy = policy or OnlineFetchPolicy(cache_ttl_seconds=0, personal_research_only=True)
    requested = list(dict.fromkeys(str(value) for value in security_ids if value))
    if not requested or len(requested) > MAX_SECURITY_IDS:
        raise ValueError("TENCENT_QUOTE_SECURITY_ID_LIMIT")
    symbols = [_symbol(value) for value in requested]
    if any(value is None for value in symbols):
        raise ValueError("TENCENT_QUOTE_SECURITY_ID_UNMAPPED")
    result = fetcher(TENCENT_QUOTE_URL + quote(",".join(symbols), safe=","), policy, referer="https://gu.qq.com/")
    if result.status_code != 200:
        raise ValueError(f"TENCENT_QUOTE_HTTP_STATUS:{result.status_code}")
    try:
        text = result.body.decode("gb18030")
    except UnicodeDecodeError as exc:
        raise ValueError("TENCENT_QUOTE_ENCODING_INVALID") from exc
    by_symbol = dict(zip(symbols, requested))
    rows = []
    for line in text.splitlines():
        if '="' not in line:
            continue
        key, payload = line.split('="', 1)
        symbol = key.removeprefix("v_").strip()
        values = payload.rsplit('";', 1)[0].split("~")
        if symbol not in by_symbol or len(values) <= 38:
            continue
        try:
            price = float(values[3])
            volume = float(values[36]) * 100
            amount = float(values[35].split("/")[2])
            turnover = float(values[38]) / 100
        except (ValueError, IndexError) as exc:
            raise ValueError("TENCENT_QUOTE_SCHEMA_INVALID") from exc
        rows.append({
            "source_id": TENCENT_QUOTE_SOURCE_ID,
            "source_contract_id": "P12_14_TENCENT_TURNOVER_FALLBACK_V1",
            "field_map_version": "TENCENT_QT_GTIMG_INDEX_MAP_V1",
            "source_code": values[2],
            "security_id": by_symbol[symbol],
            "quote_time": values[30] or None,
            "observed_at_utc": result.received_at_utc,
            "price": price,
            "amount": amount,
            "volume": volume,
            "turnover_rate": turnover,
            "turnover_basis": "TENCENT_FLOAT_SHARE_BASIS",
            "normalized_turnover_basis": "FLOAT_SHARE",
            "basis_verification": "DECLARED_ONLY",
            "time_semantics": "SOURCE_TIMESTAMP_AND_OBSERVED_AT",
            "source_name": values[1],
        })
    return result, rows


__all__ = ["TENCENT_QUOTE_SOURCE_ID", "fetch_tencent_quotes"]
