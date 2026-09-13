"""V3 P09 request-time online product adapters.

This module is deliberately side-effect free.  It turns the approved public
source responses into explainable request-time DTOs and never writes a raw
payload, row, batch, cache, or snapshot.  Close-event persistence remains the
separate EXT01 path in :mod:`workbench_service.online_events`.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, wait
from dataclasses import dataclass
from datetime import date, datetime, time as day_time, timedelta, timezone
from typing import Any, Callable, Iterable
from urllib.parse import urlencode

from .base import FetchResult, OnlineFetchPolicy, bounded_get


P09_PRODUCTS_CONTRACT = "v3-p09-online-products-v1.0"
P09_CAPABILITY_CONTRACT = "v3-p09-runtime-capabilities-v1.0"
P09_REQUEST_POLICY_ID = "P09_ONLINE_BOUNDED_V1"
P09_MAX_TOTAL_SECONDS = 12.0
P09_MAX_SOURCE_SECONDS = 8.0
P09_MAX_CONCURRENT = 4
MAX_PAGE_SIZE = 30

SOURCE_URLS = {
    "EXT02": "https://data.10jqka.com.cn/dataapi/limit_up/lower_limit_pool",
    "EXT03": "https://flash-api.xuangubao.cn/api/surge_stock/plates",
    "EXT04": "https://flash-api.xuangubao.cn/api/surge_stock/stocks",
    "EXT05": "https://flash-api.xuangubao.cn/api/pool/detail",
    "EXT06": "https://data.10jqka.com.cn/mobileapi/hotspot_focus/market_state/v1/overview",
    "EXT07": "https://dq.10jqka.com.cn/fuyao/hot_list_data/out/hot_list/v1/stock",
    "EXT08": "https://dq.10jqka.com.cn/fuyao/hot_list_data/out/hot_list/v1/plate",
    "EXT09": "https://dq.10jqka.com.cn/fuyao/hot_list_data/out/hot_list/v1/topic",
}
EVENT_POOLS = (
    "super_stock",
    "limit_up",
    "limit_up_broken",
    "yesterday_limit_up",
    "limit_down",
    "new_stock",
    "nearly_new",
)
HOT_RANK_MODES = (
    ("hour", "normal"),
    ("hour", "skyrocket"),
    ("day", "normal"),
    ("day", "skyrocket"),
)


def _capabilities() -> dict[str, str]:
    try:
        root = Path(__file__).resolve().parents[2]
        registry = json.loads((root / "config/online_source_registry_v3.json").read_text(encoding="utf-8"))
        runtime = json.loads((root / "config/p09_runtime_capabilities_v1.json").read_text(encoding="utf-8"))
        receipt = json.loads((root / runtime["evidence_receipt"]).read_text(encoding="utf-8"))
    except (OSError, ValueError, KeyError, TypeError):
        # Bad or absent online evidence cannot take down the local workbench.
        return {}
    if runtime.get("contract_id") != P09_CAPABILITY_CONTRACT:
        return {}
    registered = {item["source_id"] for item in registry.get("sources", [])}
    observations = [item for item in receipt.get("requests", []) if item.get("status") == "AVAILABLE"]
    observed = {item.get("source_id") for item in observations}
    enabled = {source: state for source, state in runtime.get("sources", {}).items()
            if source in registered and source in observed and state == "CURRENT_PROBE"}
    for item in observations:
        source = item.get("source_id")
        if source not in enabled:
            continue
        params = item.get("request") or {}
        if source == "EXT05" and params.get("pool_name"):
            enabled[f"{source}:{params['pool_name']}"] = "CURRENT_PROBE"
        elif source == "EXT07" and params.get("type") and params.get("list_type"):
            enabled[f"{source}:{params['type']}:{params['list_type']}"] = "CURRENT_PROBE"
        elif source == "EXT08" and params.get("type"):
            enabled[f"{source}:{params['type']}"] = "CURRENT_PROBE"
    return enabled


class P09ProductError(ValueError):
    """A contract-level error that must become an explicit unavailable view."""


@dataclass(frozen=True)
class SourceResponse:
    source_id: str
    status: str
    requested_at: str | None
    received_at: str | None
    http_status: int | None
    content_type: str | None
    byte_count: int | None
    raw_sha256: str | None
    source_as_of: str | None
    normalized: Any
    error_code: str | None = None
    source_trade_date: str | None = None

    def receipt(self, *, include_rows: bool = False) -> dict[str, Any]:
        # include_rows is intentionally ignored.  Receipts are metadata only,
        # including for hot-rank datasets whose rows are forbidden to persist.
        del include_rows
        return {
            "source_id": self.source_id,
            "status": self.status,
            "requested_at": self.requested_at,
            "received_at": self.received_at,
            "http_status": self.http_status,
            "content_type": self.content_type,
            "byte_count": self.byte_count,
            "raw_sha256": self.raw_sha256,
            "source_as_of": self.source_as_of,
            "source_trade_date": self.source_trade_date,
            "error_code": self.error_code,
            "raw_payload_persisted": False,
            "rows_persisted": False,
            "batch_persisted": False,
            "contract_id": P09_PRODUCTS_CONTRACT,
        }


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json(result: FetchResult) -> Any:
    try:
        return json.loads(result.body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise P09ProductError("JSON_INVALID") from exc


def _source_time_fields(source_id: str, payload: Any) -> tuple[str | None, str | None]:
    data = _mapping(_data(payload))
    if source_id == "EXT03":
        # Verified against the public response: manual_updated_at is a Unix
        # second; timestamp is the requested Beijing trade-date midnight.
        value = data.get("manual_updated_at")
        date_value = data.get("timestamp")
        source_date = datetime.fromtimestamp(date_value, timezone(timedelta(hours=8))).date().isoformat() if isinstance(date_value, (int, float)) and 1_000_000_000 <= date_value <= 4_000_000_000 else None
        if isinstance(value, (int, float)) and 1_000_000_000 <= value <= 4_000_000_000:
            return datetime.fromtimestamp(value, timezone.utc).isoformat(), source_date
        return None, source_date
    if source_id == "EXT02":
        value = data.get("date")
        if isinstance(value, str) and len(value) == 8 and value.isdigit():
            return None, f"{value[:4]}-{value[4:6]}-{value[6:]}"
    return None, None


def _mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _data(payload: Any) -> Any:
    if isinstance(payload, dict) and "data" in payload:
        return payload["data"]
    return payload


def _rows(payload: Any, names: Iterable[str]) -> list[dict[str, Any]]:
    names = tuple(names)
    candidates: list[Any] = [payload, _data(payload)]
    for item in list(candidates):
        if isinstance(item, dict):
            for name in names:
                candidates.append(item.get(name))
    for candidate in candidates:
        if isinstance(candidate, list) and all(isinstance(row, dict) for row in candidate):
            return candidate
    return []


def _source_fields(row: dict[str, Any], keys: Iterable[str]) -> dict[str, Any]:
    return {key: row.get(key) for key in keys if key in row}


def _value(row: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in row and row[key] not in (None, ""):
            return row[key]
    return None


def _explicit_bool(value: Any) -> bool | None:
    if value is True or value in (1, "1", "true", "TRUE"):
        return True
    if value is False or value in (0, "0", "false", "FALSE"):
        return False
    return None


def _status_payload(payload: Any) -> None:
    if not isinstance(payload, dict):
        return
    status = payload.get("status_code", payload.get("code"))
    if status not in (None, 0, "0", True, 20000, "20000"):
        raise P09ProductError("SOURCE_STATUS_NOT_OK")


def _url(source_id: str, params: dict[str, Any]) -> str:
    if source_id not in SOURCE_URLS:
        raise P09ProductError("SOURCE_NOT_IN_P09_TARGET_CHAIN")
    query = {key: value for key, value in params.items() if value is not None}
    if source_id == "EXT02":
        query.setdefault("page", 1)
        query.setdefault("limit", 50)
        query.setdefault("field", "")
        query.setdefault("filter", "HS,GEM2STAR")
        query.setdefault("order_field", 330334)
        query.setdefault("order_type", 0)
    if source_id == "EXT03" and query.get("date"):
        # XGT's plates endpoint is the one V3 source whose date contract is
        # Beijing midnight epoch seconds.
        date_value = str(query["date"]).replace("/", "-")
        if len(date_value) == 8 and date_value.isdigit():
            date_value = f"{date_value[:4]}-{date_value[4:6]}-{date_value[6:]}"
        parsed = date.fromisoformat(date_value)
        query["date"] = int(datetime.combine(parsed, day_time.min, timezone(timedelta(hours=8))).timestamp())
    if source_id == "EXT04" and query.get("date"):
        # The stock endpoint accepts the compact YYYYMMDD form.  Its hyphen
        # form returns an empty structural envelope even for the same day.
        query["date"] = str(query["date"]).replace("-", "")
    if source_id == "EXT04":
        query.setdefault("normal", "true")
        query.setdefault("uplimit", "true")
    if source_id == "EXT02" and query.get("date"):
        query["date"] = str(query["date"]).replace("-", "")
    if source_id == "EXT06" and query.get("date"):
        # Longzijue api.ths_market_overview.build_url requires YYYYMMDD.
        query["date"] = str(query["date"]).replace("-", "")
    if source_id == "EXT05" and query.get("date"):
        date_value = str(query["date"]).replace("/", "-")
        if len(date_value) == 8 and date_value.isdigit():
            date_value = f"{date_value[:4]}-{date_value[4:6]}-{date_value[6:]}"
        query["date"] = date_value
    if source_id == "EXT07":
        query.setdefault("stock_type", "a")
    encoded = urlencode(query)
    return SOURCE_URLS[source_id] + ("?" + encoded if encoded else "")


def _normalize_event_rows(rows: list[dict[str, Any]], source_id: str, pool_type: str) -> list[dict[str, Any]]:
    result = []
    declared = {
        "code", "name", "latest", "price", "change_rate", "amount", "order_amount",
        "currency_value", "turnover_rate", "open_num", "reason_type", "first_limit_up_time",
        "last_limit_up_time", "first_limit_down_time", "last_limit_down_time", "symbol",
        "stock_chi_name", "change_percent", "turnover_ratio", "non_restricted_capital",
        "first_limit_up", "last_limit_up", "last_break_limit_up", "break_limit_up_times",
        "m_days_n_boards_days", "m_days_n_boards_boards", "limit_up_days", "yesterday_limit_up_days",
        "plate_name", "surge_reason",
    }
    for index, row in enumerate(rows, 1):
        code = _value(row, "code", "symbol", "security_id")
        name = _value(row, "name", "stock_chi_name", "security_name")
        if code is None and name is None:
            continue
        result.append({
            "source_id": source_id,
            "pool_type": pool_type,
            "source_code": str(code) if code is not None else None,
            "security_id": str(code) if code is not None else None,
            "security_name": str(name) if name is not None else None,
            "price": _value(row, "latest", "price"),
            "ret1": _value(row, "change_rate", "change_percent"),
            "amount": row.get("amount"),
            "seal_amount": row.get("order_amount"),
            "turnover": _value(row, "turnover_rate", "turnover_ratio"),
            "float_market_cap": _value(row, "currency_value", "non_restricted_capital"),
            "open_count": _value(row, "open_num", "break_limit_up_times"),
            "first_limit_time": _value(row, "first_limit_up_time", "first_limit_up", "first_limit_down_time"),
            "last_limit_time": _value(row, "last_limit_up_time", "last_limit_up", "last_limit_down_time"),
            "last_break_time": _value(row, "last_break_limit_up"),
            "m_days": row.get("m_days_n_boards_days"),
            "n_boards": row.get("m_days_n_boards_boards"),
            "source_limit_days": row.get("limit_up_days"),
            "previous_source_limit_days": row.get("yesterday_limit_up_days"),
            "source_reason": row.get("surge_reason", {}).get("stock_reason") if isinstance(row.get("surge_reason"), dict) else _value(row, "reason_type", "surge_reason"),
            "source_topic_name": row.get("plate_name"),
            "source_fields": _source_fields(row, declared),
            "source_row_order": index,
        })
    return result


def _parse_event_pool(payload: Any, source_id: str, pool_type: str) -> list[dict[str, Any]]:
    _status_payload(payload)
    rows = _rows(payload, ("info", "items", "rows", "list", "stock_list"))
    normalized = _normalize_event_rows(rows, source_id, pool_type)
    if not rows:
        raise P09ProductError("EMPTY_EVENT_POOL")
    return normalized


def _parse_topics(payload: Any) -> list[dict[str, Any]]:
    _status_payload(payload)
    rows = _rows(payload, ("plates", "plate_list", "items", "rows", "list"))
    result = []
    for index, row in enumerate(rows, 1):
        topic_id = _value(row, "id", "code", "topic_id", "plate_id")
        name = _value(row, "name", "topic_name", "plate_name")
        if topic_id is None and name is None:
            continue
        result.append({
            "source_topic_id": str(topic_id) if topic_id is not None else None,
            "topic_name": str(name) if name is not None else None,
            "source_description": _value(row, "description", "desc"),
            "source_row_order": index,
            "source_fields": _source_fields(row, ("id", "code", "topic_id", "plate_id", "name", "topic_name", "plate_name", "description", "desc")),
        })
    if not rows:
        raise P09ProductError("EMPTY_TOPIC_LIST")
    return result


def _array_topic_members(data: dict[str, Any]) -> list[dict[str, Any]]:
    fields = data.get("fields")
    values = data.get("stock_array")
    if not isinstance(values, list):
        values = data.get("items")
    if not isinstance(fields, list) or not isinstance(values, list):
        return []
    if any(not isinstance(row, list) for row in values):
        raise P09ProductError("TOPIC_ARRAY_SCHEMA_INVALID")
    if any(len(row) != len(fields) for row in values):
        raise P09ProductError("TOPIC_ARRAY_LENGTH_MISMATCH")
    result = []
    for row in values:
        item = dict(zip((str(field) for field in fields), row))
        plates = item.get("plates")
        if isinstance(plates, list) and plates:
            for plate in plates:
                if isinstance(plate, dict):
                    result.append({**item, "topic_id": plate.get("id"), "topic_name": plate.get("name")})
        else:
            result.append(item)
    return result


def _parse_topic_members(payload: Any) -> list[dict[str, Any]]:
    _status_payload(payload)
    data = _mapping(_data(payload))
    rows = _rows(payload, ("items", "rows", "list", "stock_list")) or _array_topic_members(data)
    result = []
    for index, row in enumerate(rows, 1):
        topic_id = _value(row, "topic_id", "plate_id", "id", "source_topic_id")
        code = _value(row, "code", "stock_code", "symbol", "source_code")
        if code is None:
            continue
        uplimit = _value(row, "uplimit", "up_limit", "is_limit_up", "limit_up")
        # Longzijue xgt_topic_api._parse_stock_row (bytecode line 288):
        # source column 4 is circulation_value (yuan), column 10 is
        # turnover_ratio (fraction); the intermediate display percent cancels.
        # This is a displayed estimate in yi, not a verified exchange amount.
        capital = _value(row, "circulation_value", "non_restricted_capital", "free_float_capital")
        turnover = row.get("turnover_ratio")
        estimate_yi = None
        if (isinstance(capital, (int, float)) and not isinstance(capital, bool)
                and isinstance(turnover, (int, float)) and not isinstance(turnover, bool)
                and 0 <= capital < float("inf") and 0 <= turnover <= 1):
            estimate_yi = turnover * capital / 100_000_000
        result.append({
            "source_topic_id": str(topic_id) if topic_id is not None else None,
            "source_code": str(code),
            "is_limit_up": _explicit_bool(uplimit),
            "security_name": _value(row, "name", "prod_name", "stock_chi_name", "security_name"),
            "source_description": row.get("description"),
            "source_enter_time": row.get("enter_time"),
            "source_amount": _value(row, "amount", "turnover_amount"),
            "dragon_estimated_amount_yi": estimate_yi,
            "source_row_order": index,
            "source_fields": _source_fields(row, ("topic_id", "plate_id", "id", "source_topic_id", "code", "stock_code", "symbol", "source_code", "uplimit", "up_limit", "is_limit_up", "limit_up", "name", "stock_chi_name", "description", "enter_time", "amount", "turnover_amount", "circulation_value", "non_restricted_capital", "free_float_capital", "turnover_ratio", "turnover_rate")),
        })
    if not rows:
        raise P09ProductError("EMPTY_TOPIC_MEMBER_LIST")
    return result


def _parse_market_overview(payload: Any) -> dict[str, Any]:
    _status_payload(payload)
    data = _mapping(_data(payload))
    if not isinstance(_data(payload), dict):
        raise P09ProductError("MARKET_OVERVIEW_DATA_MISSING")
    # Preserve the Longzijue source grouping and labels. Turnover strings are
    # displayed verbatim because their Chinese unit is source-defined.
    source_fields = {}
    for key, value in (data or _mapping(payload)).items():
        if isinstance(value, (str, int, float, bool)) or value is None:
            source_fields[str(key)] = value
    rise_fall = _mapping(data.get("rise_fall"))
    counts = {key: value for key in ("rise", "fall", "deuce", "limit_up", "limit_down")
              if isinstance((value := rise_fall.get(key)), int) and not isinstance(value, bool) and value >= 0}
    turnover = _mapping(data.get("turnover"))
    return {"source_fields": source_fields, "field_count": len(source_fields),
            "rise_fall": counts, "turnover_display": {key: turnover.get(key) for key in ("pre", "now") if isinstance(turnover.get(key), str)},
            "source_groups": sorted(key for key in data if isinstance(data[key], dict))}


def _parse_hot_stocks(payload: Any) -> list[dict[str, Any]]:
    _status_payload(payload)
    rows = _rows(payload, ("stock_list", "items", "rows", "list"))
    result = []
    for index, row in enumerate(rows, 1):
        code = _value(row, "code", "stock_code", "symbol")
        name = _value(row, "name", "stock_chi_name", "security_name")
        order = _value(row, "order", "rank", "rankNumber", "platform_rank")
        if code is None or order is None:
            continue
        try:
            platform_rank = int(order)
        except (TypeError, ValueError) as exc:
            raise P09ProductError("HOT_RANK_SCHEMA_INVALID") from exc
        result.append({
            "source_code": str(code),
            "security_name": str(name) if name is not None else None,
            "platform_rank": platform_rank,
            "rank_change": _value(row, "hot_rank_chg", "rank_change", "changeNumber"),
            "rise_and_fall": row.get("rise_and_fall"),
            "source_rate": row.get("rate"),
            "source_tag": row.get("tag"),
            "source_row_order": index,
        })
    if not rows:
        raise P09ProductError("EMPTY_HOT_RANK_LIST")
    return result


def _parse_hot_plates(payload: Any) -> list[dict[str, Any]]:
    _status_payload(payload)
    rows = _rows(payload, ("plate_list", "items", "rows", "list"))
    result = []
    for index, row in enumerate(rows, 1):
        plate_id = _value(row, "code", "id", "plate_id")
        name = _value(row, "name", "plate_name")
        if plate_id is None and name is None:
            continue
        result.append({
            "source_plate_id": str(plate_id) if plate_id is not None else None,
            "plate_name": str(name) if name is not None else None,
            "hot_value": row.get("hot_value"),
            "source_rate": row.get("rate"),
            "platform_rank": _value(row, "order", "rank"),
            "source_tag": row.get("hot_tag"),
            "etf_fields": row.get("etf_fields") if isinstance(row.get("etf_fields"), (str, int, float, bool, type(None))) else None,
            "source_row_order": index,
        })
    if not rows:
        raise P09ProductError("EMPTY_HOT_PLATE_LIST")
    return result


def _parse_hot_topics(payload: Any) -> list[dict[str, Any]]:
    _status_payload(payload)
    rows = _rows(payload, ("topic_list", "items", "rows", "list"))
    result = []
    for index, row in enumerate(rows, 1):
        title = _value(row, "title", "topic_title", "name")
        if title is None:
            continue
        result.append({
            "topic_title": str(title),
            "topic_subtitle": _value(row, "subtitle", "topic_subtitle"),
            "source_description": _value(row, "description", "desc"),
            "safe_external_url": _safe_external_url(_value(row, "jump_url", "url")),
            "hot_value": row.get("hot_value"),
            "source_row_order": index,
        })
    if not rows:
        raise P09ProductError("EMPTY_HOT_TOPIC_LIST")
    return result


def _safe_external_url(value: Any) -> str | None:
    from urllib.parse import urlparse

    if not isinstance(value, str) or len(value) > 2048:
        return None
    parsed = urlparse(value)
    return value if parsed.scheme == "https" and parsed.hostname else None


PARSERS: dict[str, Callable[[Any], Any]] = {
    "EXT02": lambda payload: _parse_event_pool(payload, "EXT02", "LIMIT_DOWN"),
    "EXT03": _parse_topics,
    "EXT04": _parse_topic_members,
    "EXT05": lambda payload: _parse_event_pool(payload, "EXT05", "SOURCE_POOL"),
    "EXT06": _parse_market_overview,
    "EXT07": _parse_hot_stocks,
    "EXT08": _parse_hot_plates,
    "EXT09": _parse_hot_topics,
}


class P09OnlineProducts:
    """Bounded request-time source access with fail-closed result contracts."""

    def __init__(
        self,
        *,
        fetcher: Callable[..., FetchResult] = bounded_get,
        policy: OnlineFetchPolicy | None = None,
        capabilities: dict[str, str] | None = None,
    ) -> None:
        self.fetcher = fetcher
        self.capabilities = _capabilities() if capabilities is None else capabilities
        self.strict_variants = capabilities is None
        self.policy = policy or OnlineFetchPolicy(
            timeout_seconds=P09_MAX_SOURCE_SECONDS,
            max_response_bytes=2_000_000,
            retries=0,
            personal_research_only=True,
        )

    def fetch(self, source_id: str, params: dict[str, Any] | None = None) -> SourceResponse:
        params = params or {}
        # Configuration mistakes are caller errors, not upstream outages.
        if source_id not in SOURCE_URLS or source_id not in PARSERS:
            raise P09ProductError("SOURCE_NOT_IN_P09_TARGET_CHAIN")
        requested_at = _now()
        if self.capabilities.get(source_id) != "CURRENT_PROBE":
            return SourceResponse(source_id, "UNAVAILABLE", requested_at, requested_at, None, None, None, None, None, None, "SOURCE_CAPABILITY_DISABLED")
        variant = None
        if source_id == "EXT05":
            variant = f"EXT05:{params.get('pool_name')}"
        elif source_id == "EXT07":
            variant = f"EXT07:{params.get('type')}:{params.get('list_type')}"
        elif source_id == "EXT08":
            variant = f"EXT08:{params.get('type')}"
        if self.strict_variants and variant and self.capabilities.get(variant) != "CURRENT_PROBE":
            return SourceResponse(source_id, "UNAVAILABLE", requested_at, requested_at, None, None, None, None, None, None, "DATASET_CAPABILITY_DISABLED")
        try:
            result = self.fetcher(_url(source_id, params), self.policy)
            if result.status_code != 200:
                raise P09ProductError(f"HTTP_STATUS_{result.status_code}")
            payload = _json(result)
            try:
                normalized = PARSERS[source_id](payload)
            except P09ProductError as exc:
                empty_page = source_id in {"EXT02", "EXT09"} and int(params.get("page", 1)) > 1 and str(exc) in {"EMPTY_EVENT_POOL", "EMPTY_HOT_TOPIC_LIST"}
                if not empty_page:
                    raise
                normalized = []
            status = "AVAILABLE" if normalized or int(params.get("page", 1)) > 1 and source_id in {"EXT02", "EXT09"} else "DEGRADED"
            source_as_of, source_trade_date = _source_time_fields(source_id, payload)
            requested_date = str(params.get("date") or "").replace("/", "-")
            if len(requested_date) == 8 and requested_date.isdigit():
                requested_date = f"{requested_date[:4]}-{requested_date[4:6]}-{requested_date[6:]}"
            if requested_date and source_trade_date and requested_date != source_trade_date:
                raise P09ProductError("SOURCE_DATE_MISMATCH")
            return SourceResponse(source_id, status, result.requested_at_utc, result.received_at_utc, result.status_code, result.content_type, result.byte_count, result.raw_sha256, source_as_of, normalized, source_trade_date=source_trade_date)
        except Exception as exc:  # each source must degrade independently
            return SourceResponse(source_id, "UNAVAILABLE", requested_at, _now(), None, None, None, None, None, None, str(exc)[:120])

    def batch(self, requests: Iterable[tuple[str, dict[str, Any]]]) -> list[SourceResponse]:
        request_list = list(requests)
        if not request_list:
            return []
        started = time.monotonic()
        results: list[SourceResponse] = []
        pool = ThreadPoolExecutor(max_workers=P09_MAX_CONCURRENT, thread_name_prefix="p09-online")
        futures = {pool.submit(self.fetch, source_id, params): index for index, (source_id, params) in enumerate(request_list)}
        indexed: dict[int, SourceResponse] = {}
        pending = set(futures)
        while pending:
            remaining = P09_MAX_TOTAL_SECONDS - (time.monotonic() - started)
            if remaining <= 0:
                break
            done, pending = wait(pending, timeout=remaining)
            for future in done:
                indexed[futures[future]] = future.result()
        for future in pending:
            future.cancel()
        pool.shutdown(wait=False, cancel_futures=True)
        # Any request that was still running at the global budget is explicit,
        # rather than silently dropped from the product response.
        for index, (source_id, _) in enumerate(request_list):
            results.append(indexed.get(index) or SourceResponse(source_id, "UNAVAILABLE", None, _now(), None, None, None, None, None, None, "TOTAL_TIME_BUDGET_EXCEEDED"))
        return results

    @staticmethod
    def unavailable(source_id: str, code: str, *, params: dict[str, Any] | None = None) -> dict[str, Any]:
        return {
            "api_contract": P09_PRODUCTS_CONTRACT,
            "status": "UNAVAILABLE",
            "source": {"source_id": source_id, "capability": "UNAVAILABLE"},
            "request": params or {},
            "source_time": {"requested_at": None, "received_at": None, "source_as_of": None, "basis": "UNKNOWN"},
            "items": [],
            "total": 0,
            "returned_count": 0,
            "has_more": False,
            "coverage": {"coverage_status": "UNAVAILABLE", "complete_pagination": False},
            "storage": {"mode": "REQUEST_TIME_ONLY", "raw_payload_persisted": False, "rows_persisted": False, "batch_persisted": False},
            "empty_state": {"code": code, "message": "当前公开来源不可用，未以本地估算冒充在线事实。"},
        }

    @staticmethod
    def view(response: SourceResponse, *, request: dict[str, Any] | None = None, page: int = 1, page_size: int = MAX_PAGE_SIZE) -> dict[str, Any]:
        request = request or {}
        page = max(1, int(page))
        page_size = max(1, min(MAX_PAGE_SIZE, int(page_size)))
        if response.status == "UNAVAILABLE":
            return P09OnlineProducts.unavailable(response.source_id, response.error_code or "SOURCE_UNAVAILABLE", params=request)
        items = response.normalized if isinstance(response.normalized, list) else []
        total = len(items)
        start = (page - 1) * page_size
        page_items = items[start:start + page_size]
        return {
            "api_contract": P09_PRODUCTS_CONTRACT,
            "status": response.status,
            "source": {"source_id": response.source_id, "capability": response.status},
            "request": request,
            "source_time": {"requested_at": response.requested_at, "received_at": response.received_at, "source_as_of": response.source_as_of, "source_trade_date": response.source_trade_date, "basis": "SOURCE_AS_OF_AND_OBSERVED_AT" if response.source_as_of else "SOURCE_DATE_AND_OBSERVED_AT" if response.source_trade_date else "OBSERVED_AT_ONLY"},
            "items": page_items,
            "total": total,
            "returned_count": len(page_items),
            "has_more": start + len(page_items) < total,
            "coverage": {"coverage_status": "UNKNOWN", "complete_pagination": False, "upstream_total": None},
            "storage": {"mode": "REQUEST_TIME_ONLY", "raw_payload_persisted": False, "rows_persisted": False, "batch_persisted": False},
            "empty_state": None if page_items else {"code": "NO_SOURCE_ROWS", "message": "来源已响应，但当前没有可展示的规范化行。"},
        }

    def events_pools(self, *, pool_type: str | None = None, trade_date: str | None = None, page: int = 1, page_size: int = MAX_PAGE_SIZE) -> dict[str, Any]:
        names = [pool_type] if pool_type else list(EVENT_POOLS)
        invalid = [name for name in names if name not in EVENT_POOLS]
        if invalid:
            raise P09ProductError("POOL_TYPE_INVALID")
        results = self.batch(("EXT05", {"pool_name": name, "date": trade_date}) for name in names)
        by_name = {}
        for name, response in zip(names, results):
            view = self.view(response, request={"pool_name": name, "date": trade_date}, page=page, page_size=page_size)
            view["pool_name"] = name
            by_name[name] = view
        statuses = [item["status"] for item in by_name.values()]
        overall = "AVAILABLE" if statuses and all(status == "AVAILABLE" for status in statuses) else "DEGRADED" if any(status != "UNAVAILABLE" for status in statuses) or any(status == "AVAILABLE" for status in statuses) else "UNAVAILABLE"
        return {"api_contract": P09_PRODUCTS_CONTRACT, "status": overall, "pools": by_name, "pool_names": names, "storage": {"mode": "REQUEST_TIME_ONLY", "raw_payload_persisted": False, "rows_persisted": False, "batch_persisted": False}}

    def promotion(self, *, trade_date: str | None) -> dict[str, Any]:
        """Describe the Longzijue yesterday-limit-up transition pool.

        EXT05 supplies yesterday_limit_up_days and today's limit_up_days on
        each returned stock. This follows the source's existing product path
        and does not derive a probability or substitute an excerpted ladder.
        """
        if not trade_date:
            return {"api_contract": "v3-p09-promotion-v1.0", "status": "UNAVAILABLE", "rate": None, "reason": "TRADE_DATE_REQUIRED", "items": []}
        response = self.fetch("EXT05", {"pool_name": "yesterday_limit_up", "date": trade_date})
        if response.status != "AVAILABLE" or not isinstance(response.normalized, list):
            return {"api_contract": "v3-p09-promotion-v1.0", "status": "UNAVAILABLE", "rate": None, "reason": response.error_code or "SOURCE_POOL_UNAVAILABLE", "items": []}
        transitions = []
        counts = {"SUCCESS": 0, "NOT_PROMOTED": 0, "UNKNOWN": 0}
        for row in response.normalized:
            previous = row.get("previous_source_limit_days")
            current = row.get("source_limit_days")
            observable = isinstance(row.get("ret1"), (int, float)) and not isinstance(row.get("ret1"), bool)
            if not isinstance(previous, int) or isinstance(previous, bool) or previous < 1 or not observable:
                state = "UNKNOWN"
            elif isinstance(current, int) and not isinstance(current, bool) and current == previous + 1:
                state = "SUCCESS"
            else:
                state = "NOT_PROMOTED"
            counts[state] += 1
            transitions.append({"source_code": row.get("source_code"), "security_name": row.get("security_name"), "previous_limit_days": previous, "current_limit_days": current, "ret1": row.get("ret1"), "state": state})
        eligible = counts["SUCCESS"] + counts["NOT_PROMOTED"]
        return {"api_contract": "v3-p09-promotion-v1.0", "status": "AVAILABLE", "source_id": "EXT05", "dataset": "yesterday_limit_up", "trade_date": trade_date, "success_count": counts["SUCCESS"], "not_promoted_count": counts["NOT_PROMOTED"], "unknown_count": counts["UNKNOWN"], "eligible_count": eligible, "rate": counts["SUCCESS"] / eligible if eligible else None, "rate_basis": "SOURCE_YESTERDAY_LIMIT_UP_TRANSITION_POOL", "coverage": {"returned_count": len(transitions), "all_returned_rows_classified": True, "source_pool_scope": "LONGZIJUE_EXT05"}, "items": transitions, "storage": {"mode": "REQUEST_TIME_ONLY", "raw_payload_persisted": False, "rows_persisted": False, "batch_persisted": False}}

    def topics(self, *, trade_date: str | None = None) -> dict[str, Any]:
        plates, members = self.batch((("EXT03", {"date": trade_date}), ("EXT04", {"date": trade_date})))
        plate_view = self.view(plates, request={"date": trade_date})
        member_view = self.view(members, request={"date": trade_date})
        # Presentation paging must never truncate the join or its denominators.
        all_plates = plates.normalized if isinstance(plates.normalized, list) else []
        all_members = members.normalized if isinstance(members.normalized, list) else []
        member_by_topic: dict[str, list[dict[str, Any]]] = {}
        for item in all_members:
            member_by_topic.setdefault(str(item.get("source_topic_id")), []).append(item)
        topics = []
        for item in all_plates:
            topic_id = str(item.get("source_topic_id"))
            members_for_topic = member_by_topic.get(topic_id, [])
            limit_members = [member for member in members_for_topic if member.get("is_limit_up") is True]
            valid_amounts = {member.get("source_code"): member.get("source_amount") for member in members_for_topic if isinstance(member.get("source_amount"), (int, float)) and not isinstance(member.get("source_amount"), bool)}
            estimated = {member.get("source_code"): member["dragon_estimated_amount_yi"] for member in members_for_topic if member.get("dragon_estimated_amount_yi") is not None}
            topics.append({**item, "members": members_for_topic, "limit_up_member_count": len({member.get("source_code") for member in limit_members}), "unique_member_count": len({member.get("source_code") for member in members_for_topic}), "membership_count": len(members_for_topic), "amount_sum": None, "amount_valid_count": len(valid_amounts), "amount_coverage": "UNIT_UNVERIFIED" if valid_amounts else "SOURCE_FIELD_UNAVAILABLE", "dragon_estimated_amount_yi": round(sum(estimated.values()), 2) if estimated else None, "dragon_estimated_valid_count": len(estimated), "dragon_estimated_basis": "CIRCULATION_VALUE_YUAN_TIMES_TURNOVER_RATIO"})
        status = "AVAILABLE" if plate_view["status"] == "AVAILABLE" and member_view["status"] == "AVAILABLE" else "DEGRADED" if plate_view["status"] != "UNAVAILABLE" or member_view["status"] != "UNAVAILABLE" else "UNAVAILABLE"
        global_estimated = {item.get("source_code"): item["dragon_estimated_amount_yi"] for item in all_members if item.get("dragon_estimated_amount_yi") is not None}
        return {"api_contract": P09_PRODUCTS_CONTRACT, "status": status, "date": trade_date, "source_status": {"EXT03": plate_view["status"], "EXT04": member_view["status"]}, "source_hashes": {"EXT03": plates.raw_sha256, "EXT04": members.raw_sha256}, "source_time": {"EXT03": plate_view["source_time"], "EXT04": member_view["source_time"]}, "coverage": {"EXT03": plate_view["coverage"], "EXT04": member_view["coverage"]}, "items": topics, "topic_count": len(topics), "unique_limit_up_member_count": len({item.get("source_code") for item in all_members if item.get("is_limit_up") is True}), "global_unique_member_count": len({item.get("source_code") for item in all_members}), "membership_count": sum(item["membership_count"] for item in topics), "amount_sum": None, "amount_valid_count": len({item.get("source_code") for item in all_members if isinstance(item.get("source_amount"), (int, float)) and not isinstance(item.get("source_amount"), bool)}), "amount_coverage": "SOURCE_FIELD_OR_UNIT_UNVERIFIED", "dragon_estimated_amount_yi": round(sum(global_estimated.values()), 2) if global_estimated else None, "dragon_estimated_valid_count": len(global_estimated), "dragon_estimated_basis": "CIRCULATION_VALUE_YUAN_TIMES_TURNOVER_RATIO", "storage": {"mode": "REQUEST_TIME_ONLY", "raw_payload_persisted": False, "rows_persisted": False, "batch_persisted": False}, "empty_state": None if topics else {"code": "TOPIC_JOIN_UNAVAILABLE", "message": "题材及成员未形成可展示的同日来源连接。"}}

    def hot_rankings(self, *, modes: Iterable[tuple[str, str]] = HOT_RANK_MODES, page: int = 1, page_size: int = MAX_PAGE_SIZE) -> dict[str, Any]:
        mode_list = list(modes)
        if any(mode not in HOT_RANK_MODES for mode in mode_list):
            raise P09ProductError("HOT_RANK_MODE_INVALID")
        results = self.batch(("EXT07", {"type": period, "list_type": kind}) for period, kind in mode_list)
        views = {}
        for (period, kind), response in zip(mode_list, results):
            views[f"{period}_{kind}"] = self.view(response, request={"type": period, "list_type": kind}, page=page, page_size=page_size)
        statuses = [view["status"] for view in views.values()]
        overall = "AVAILABLE" if statuses and all(status == "AVAILABLE" for status in statuses) else "DEGRADED" if any(status == "AVAILABLE" for status in statuses) else "UNAVAILABLE"
        return {"api_contract": P09_PRODUCTS_CONTRACT, "status": overall, "lists": views, "persistence": "FORBIDDEN_REQUEST_TIME_ONLY", "raw_payload_persisted": False, "rows_persisted": False}

    def hot_plates(self, *, plate_type: str = "concept", page: int = 1, page_size: int = MAX_PAGE_SIZE) -> dict[str, Any]:
        if plate_type not in {"concept", "industry"}:
            raise P09ProductError("PLATE_TYPE_INVALID")
        if int(page) < 1 or not 1 <= int(page_size) <= MAX_PAGE_SIZE:
            raise P09ProductError("PAGINATION_INVALID")
        response = self.fetch("EXT08", {"type": plate_type})
        return {**self.view(response, request={"type": plate_type}, page=page, page_size=page_size), "plate_type": plate_type, "persistence": "FORBIDDEN_REQUEST_TIME_ONLY"}

    def hot_topics(self, *, page: int = 1, page_size: int = MAX_PAGE_SIZE) -> dict[str, Any]:
        page = int(page)
        page_size = int(page_size)
        if page < 1 or not 1 <= page_size <= MAX_PAGE_SIZE:
            raise P09ProductError("PAGINATION_INVALID")
        response = self.fetch("EXT09", {"page": page, "page_size": page_size})
        view = self.view(response, request={"page": page, "page_size": page_size}, page=1, page_size=page_size)
        view["has_more"] = response.status == "AVAILABLE" and isinstance(response.normalized, list) and len(response.normalized) == page_size
        view["has_more_basis"] = "PAGE_FULL_POSSIBLE_MORE" if view["has_more"] else "SOURCE_PAGE_SHORT_OR_EMPTY" if response.status == "AVAILABLE" else "UNAVAILABLE"
        return {**view, "page": int(page), "page_size": page_size, "persistence": "FORBIDDEN_REQUEST_TIME_ONLY"}
