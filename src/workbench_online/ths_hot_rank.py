"""Personal-research-only adapter for the public THS hot-rank response."""

from __future__ import annotations

import json
from typing import Callable

from .base import FetchResult, OnlineFetchPolicy, bounded_get


THS_HOT_RANK_SOURCE_ID = "TONGHUASHUN_HOT_RANK"
THS_HOT_RANK_URL = "https://dq.10jqka.com.cn/fuyao/hot_list_data/out/hot_list/v1/stock?stock_type=a&type=hour&list_type=normal"
THS_HOT_RANK_PAGE = "https://eq.10jqka.com.cn/webpage/ths-hot-list/index.html?showStatusBar=true"
MARKET_EXCHANGE = {17: "SH", 33: "SZ"}


def _security_id(row: dict) -> str | None:
    market = row.get("market")
    code = str(row.get("code", "")).strip()
    exchange = MARKET_EXCHANGE.get(int(market)) if str(market).isdigit() else None
    if not exchange or not code.isdigit() or len(code) != 6:
        return None
    return f"{exchange}.{code}"


def fetch_ths_hot_rank(
    policy: OnlineFetchPolicy | None = None,
    *,
    fetcher: Callable[..., FetchResult] = bounded_get,
) -> tuple[FetchResult, dict]:
    policy = policy or OnlineFetchPolicy()
    result = fetcher(THS_HOT_RANK_URL, policy, referer=THS_HOT_RANK_PAGE)
    if result.status_code != 200:
        raise ValueError(f"HTTP_STATUS:{result.status_code}")
    payload = json.loads(result.body.decode("utf-8"))
    if payload.get("status_code") != 0:
        raise ValueError("SOURCE_STATUS_NOT_OK")
    rows = payload.get("data", {}).get("stock_list")
    if not isinstance(rows, list) or not rows:
        raise ValueError("EMPTY_HOT_RANK_LIST")
    normalized = []
    for index, row in enumerate(rows, start=1):
        if not isinstance(row, dict) or not {"code", "name", "order"}.issubset(row):
            raise ValueError("RANK_SCHEMA_DRIFT")
        normalized.append(
            {
                "source_code": str(row["code"]),
                "security_id": _security_id(row),
                "platform_rank": int(row["order"]),
                "rank_change": row.get("hot_rank_chg"),
                "security_name": str(row["name"]),
                "market": row.get("market"),
                "rise_and_fall": row.get("rise_and_fall"),
                "source_row_order": index,
            }
        )
    return result, {
        "source_id": THS_HOT_RANK_SOURCE_ID,
        "dataset": "HOT_RANKINGS",
        "list_type": "HOUR_NORMAL",
        "capability_status": "PERSONAL_RESEARCH_ONLY",
        "source_as_of": None,
        "time_semantics": "OBSERVED_AT_ONLY_SOURCE_AS_OF_MISSING",
        "upstream_paged": False,
        "upstream_total": len(normalized),
        "upstream_has_more": False,
        "rows": normalized,
    }
