"""Read-only V3 online event views backed by allowed close-event batches."""

from __future__ import annotations

import json
import math
from contextlib import AbstractContextManager
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Callable


ONLINE_EVENT_LADDER_API_CONTRACT = "v3-events-ladder-api-v1.0"
ONLINE_EVENT_EVIDENCE_API_CONTRACT = "v3-events-ladder-evidence-v1.0"
EXT01_SOURCE_ID = "EXT01"
EXT01_DATASET = "LIMIT_POOL_UP"
MAX_EVENT_API_PAGE_SIZE = 20
ALLOWED_EVENT_SORTS = {"DEFAULT", "FIRST_LIMIT_TIME"}

EVENT_FIELD_EVIDENCE_MAP = {
    "security_id": "code",
    "security_name": "name",
    "price": "latest",
    "ret1": "change_rate",
    "amount": "amount",
    "seal_amount": "order_amount",
    "float_market_cap": "currency_value",
    "turnover": "turnover_rate",
    "open_count": "open_num",
    "source_reason": "reason_type",
    "first_limit_time": "first_limit_up_time",
    "last_limit_time": "last_limit_up_time",
}
UNRESOLVED_SCALE_FIELDS = {"ret1", "amount", "seal_amount", "float_market_cap", "turnover"}


class OnlineEventQueryError(ValueError):
    """Raised when an online event API query is outside its contract."""


def _json_value(value: Any, fallback: Any) -> Any:
    if isinstance(value, (dict, list)):
        return value
    if value in (None, ""):
        return fallback
    try:
        return json.loads(value)
    except (TypeError, ValueError, json.JSONDecodeError):
        return fallback


def _json_number(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value) if value.is_finite() else None
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    return value


def _iso(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return str(value)


def _date_filter(value: str | None) -> str | None:
    if value in (None, ""):
        return None
    text = str(value).strip()
    if len(text) == 8 and text.isdigit():
        text = f"{text[:4]}-{text[4:6]}-{text[6:]}"
    try:
        return date.fromisoformat(text).isoformat()
    except ValueError as exc:
        raise OnlineEventQueryError("DATE_INVALID") from exc


def _page_value(value: Any, default: int, *, minimum: int = 1, maximum: int | None = None) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise OnlineEventQueryError("PAGINATION_INVALID") from exc
    if parsed < minimum or (maximum is not None and parsed > maximum):
        raise OnlineEventQueryError("PAGINATION_INVALID")
    return parsed


def _time_key(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.timestamp()
    try:
        return datetime.fromisoformat(str(value)).timestamp()
    except (TypeError, ValueError, OverflowError, OSError):
        return None


def _height_key(item: dict[str, Any]) -> int | None:
    value = item.get("consecutive_limit_days")
    return int(value) if isinstance(value, int) else None


def _sort_key_default(item: dict[str, Any]) -> tuple[Any, ...]:
    height = _height_key(item)
    last_limit = _time_key(item.get("last_limit_time"))
    seal_amount = item.get("seal_amount")
    return (
        height is None,
        -(height or 0),
        last_limit is None,
        last_limit or 0,
        seal_amount is None,
        -(float(seal_amount) if seal_amount is not None else 0),
        str(item.get("security_id") or item.get("source_code") or ""),
    )


def _sort_key_first_limit(item: dict[str, Any]) -> tuple[Any, ...]:
    first_limit = _time_key(item.get("first_limit_time"))
    return (
        first_limit is None,
        first_limit or 0,
        str(item.get("security_id") or item.get("source_code") or ""),
    )


def _unavailable(*, trade_date: str | None, event_bundle_id: str | None, code: str, message: str, page: int, page_size: int) -> dict[str, Any]:
    return {
        "api_contract": ONLINE_EVENT_LADDER_API_CONTRACT,
        "status": "UNAVAILABLE",
        "source": {"source_id": EXT01_SOURCE_ID, "dataset": EXT01_DATASET, "capability": "DEGRADED"},
        "event_bundle_id": event_bundle_id,
        "trade_date": trade_date,
        "page": page,
        "page_size": page_size,
        "total": 0,
        "returned_count": 0,
        "has_more": False,
        "sort": "DEFAULT",
        "header": None,
        "coverage": {"complete_pagination": False, "coverage_status": "UNAVAILABLE"},
        "items": [],
        "capabilities": {"ladder": "UNAVAILABLE", "pagination": "UNKNOWN", "field_scale": "UNRESOLVED"},
        "empty_state": {"code": code, "message": message},
        "next_action": "等待已获准归档的 EXT01 收盘事件批次；不使用本地估算冒充在线事实。",
    }


def _evidence_unavailable(*, security_id: str, source: dict[str, Any], code: str, message: str, base: dict[str, Any] | None = None) -> dict[str, Any]:
    base = base or {}
    return {
        "api_contract": ONLINE_EVENT_EVIDENCE_API_CONTRACT,
        "status": "UNAVAILABLE",
        "source": source,
        "security_id": security_id,
        "event_bundle_id": base.get("event_bundle_id"),
        "batch_id": base.get("batch_id"),
        "trade_date": base.get("trade_date"),
        "observed_at": base.get("observed_at"),
        "source_as_of": base.get("source_as_of"),
        "source_time": {"observed_at": base.get("observed_at"), "source_as_of": base.get("source_as_of"), "basis": "UNKNOWN"},
        "item": None,
        "evidence": None,
        "empty_state": {"code": code, "message": message},
        "next_action": "仅等待已获准归档的 EXT01 收盘事件；不以本地估算补写单股在线证据。",
    }


def _field_evidence(item: dict[str, Any]) -> list[dict[str, Any]]:
    source_fields = item.get("source_fields") if isinstance(item.get("source_fields"), dict) else {}
    evidence: list[dict[str, Any]] = []
    for normalized_field, source_field in EVENT_FIELD_EVIDENCE_MAP.items():
        if normalized_field == "security_name":
            value = source_fields.get("name")
        else:
            value = item.get(normalized_field)
        if value is None or value == "":
            status = "UNCONFIRMED"
        elif normalized_field in UNRESOLVED_SCALE_FIELDS:
            status = "OBSERVED_VALUE_SCALE_UNRESOLVED"
        else:
            status = "OBSERVED"
        evidence.append({
            "normalized_field": normalized_field,
            "source_field": source_field,
            "value": value,
            "status": status,
        })
    return evidence


class OnlineEventQueries:
    """Read-only query service; it never starts collection or a local run."""

    def __init__(self, connection_provider: Callable[[], AbstractContextManager[Any]]):
        self._connection_provider = connection_provider

    def ladder(
        self,
        *,
        event_bundle_id: str | None = None,
        trade_date: str | None = None,
        security_id: str | None = None,
        page: int | str = 1,
        page_size: int | str = MAX_EVENT_API_PAGE_SIZE,
        sort: str = "DEFAULT",
    ) -> dict[str, Any]:
        page_number = _page_value(page, 1)
        size = _page_value(page_size, MAX_EVENT_API_PAGE_SIZE, maximum=MAX_EVENT_API_PAGE_SIZE)
        sort_name = str(sort or "DEFAULT").strip().upper()
        if sort_name not in ALLOWED_EVENT_SORTS:
            raise OnlineEventQueryError("EVENT_SORT_UNSUPPORTED")
        requested_date = _date_filter(trade_date)

        with self._connection_provider() as connection:
            try:
                tables = {row[0] for row in connection.execute("SHOW TABLES").fetchall()}
            except Exception as exc:
                raise OnlineEventQueryError("EVENT_STORAGE_UNAVAILABLE") from exc
            required = {"online_event_bundles", "online_event_header", "online_pool_entries", "online_batches"}
            if not required.issubset(tables):
                return _unavailable(trade_date=requested_date, event_bundle_id=event_bundle_id, code="EVENT_STORAGE_NOT_BUILT", message="在线事件存储尚未构建。", page=page_number, page_size=size)

            filters = []
            args: list[Any] = []
            if event_bundle_id:
                filters.append("bundle_id=?")
                args.append(str(event_bundle_id))
            if requested_date:
                filters.append("cast(trade_date as varchar)=?")
                args.append(requested_date)
            clause = " WHERE " + " AND ".join(filters) if filters else ""
            bundles = connection.execute(
                "SELECT bundle_id,cast(trade_date as varchar),source_batch_bindings,source_statuses,observed_at,coverage FROM online_event_bundles"
                + clause
                + " ORDER BY trade_date DESC,observed_at DESC",
                args,
            ).fetchall()
            selected = None
            for bundle in bundles:
                bindings = _json_value(bundle[2], {})
                if not isinstance(bindings, dict) or not bindings.get(EXT01_SOURCE_ID):
                    continue
                selected = bundle
                break
            if selected is None:
                return _unavailable(trade_date=requested_date, event_bundle_id=event_bundle_id, code="EVENT_BUNDLE_UNAVAILABLE", message="当前没有可读取的 EXT01 收盘事件批次。", page=page_number, page_size=size)

            selected_bundle_id, selected_date, bindings_raw, statuses_raw, bundle_observed_at, coverage_raw = selected
            bindings = _json_value(bindings_raw, {})
            statuses = _json_value(statuses_raw, {})
            coverage = _json_value(coverage_raw, {})
            batch_id = bindings.get(EXT01_SOURCE_ID)
            source_status = str(statuses.get(EXT01_SOURCE_ID) or "UNKNOWN").upper()
            batch = connection.execute(
                "SELECT dataset,status,cast(trade_date as varchar),source_as_of,observed_at,row_count,adapter_version FROM online_batches WHERE batch_id=?",
                [batch_id],
            ).fetchone()
            header_row = connection.execute(
                "SELECT counts,rates,scope,source_notice FROM online_event_header WHERE batch_id=?", [batch_id]
            ).fetchone()
            if batch is None or header_row is None:
                return _unavailable(trade_date=selected_date, event_bundle_id=selected_bundle_id, code="EVENT_BATCH_OR_HEADER_MISSING", message="事件批次缺少头统计或批次绑定，已拒绝展示。", page=page_number, page_size=size)
            if batch[0] != EXT01_DATASET:
                return _unavailable(trade_date=selected_date, event_bundle_id=selected_bundle_id, code="EVENT_DATASET_MISMATCH", message="事件批次数据集不符合 EXT01 涨停池合同。", page=page_number, page_size=size)

            rows = connection.execute(
                "SELECT source_code,security_id,event_state,price,amount,seal_amount,ret1,turnover,float_market_cap,open_count,consecutive_limit_days,m_days,n_boards,first_limit_time,last_limit_time,last_break_time,source_reason,source_fields,quality_codes FROM online_pool_entries WHERE batch_id=? AND pool_type='LIMIT_UP'"
                + (" AND (security_id=? OR source_code=?)" if security_id else ""),
                [batch_id, str(security_id), str(security_id).replace(".", ":")] if security_id else [batch_id],
            ).fetchall()

        items: list[dict[str, Any]] = []
        for row in rows:
            source_code, row_security_id, event_state, price, amount, seal_amount, ret1, turnover, float_market_cap, open_count, consecutive, m_days, n_boards, first_limit, last_limit, last_break, reason, source_fields, quality_codes = row
            source_fields_value = _json_value(source_fields, {})
            height_display = "未确认"
            if consecutive is not None:
                height_display = f"{consecutive}板"
            elif m_days is not None or n_boards is not None:
                height_display = f"{m_days or '?'}天{n_boards or '?'}板"
            items.append(
                {
                    "source_id": EXT01_SOURCE_ID,
                    "dataset": EXT01_DATASET,
                    "trade_date": selected_date,
                    "event_bundle_id": selected_bundle_id,
                    "batch_id": batch_id,
                    "pool_type": "LIMIT_UP",
                    "source_code": source_code,
                    "security_id": row_security_id,
                    "security_name": source_fields_value.get("name") if isinstance(source_fields_value, dict) else None,
                    "event_state": event_state,
                    "price": _json_number(price),
                    "amount": _json_number(amount),
                    "seal_amount": _json_number(seal_amount),
                    "ret1": _json_number(ret1),
                    "turnover": _json_number(turnover),
                    "float_market_cap": _json_number(float_market_cap),
                    "open_count": open_count,
                    "consecutive_limit_days": consecutive,
                    "m_days": m_days,
                    "n_boards": n_boards,
                    "height_display": height_display,
                    "first_limit_time": _iso(first_limit),
                    "last_limit_time": _iso(last_limit),
                    "last_break_time": _iso(last_break),
                    "source_reason": reason,
                    "source_fields": source_fields_value,
                    "quality_codes": _json_value(quality_codes, []),
                }
            )
        items.sort(key=_sort_key_first_limit if sort_name == "FIRST_LIMIT_TIME" else _sort_key_default)
        total = len(items)
        start = (page_number - 1) * size
        page_items = items[start : start + size]
        result_status = "AVAILABLE" if source_status == "AVAILABLE" and str(batch[1]).upper() == "CLOSE_COMPLETE" else "DEGRADED"
        empty_state = None
        if not items:
            empty_state = {"code": "NO_LIMIT_UP_MEMBERS", "message": "当前收盘批次没有可展示的涨停成员；头统计与来源覆盖仍保留。"}
        return {
            "api_contract": ONLINE_EVENT_LADDER_API_CONTRACT,
            "status": result_status,
            "source": {"source_id": EXT01_SOURCE_ID, "dataset": EXT01_DATASET, "capability": source_status},
            "event_bundle_id": selected_bundle_id,
            "batch_id": batch_id,
            "trade_date": selected_date,
            "observed_at": _iso(bundle_observed_at or batch[4]),
            "source_as_of": _iso(batch[3]),
            "page": page_number,
            "page_size": size,
            "total": total,
            "returned_count": len(page_items),
            "has_more": start + size < total,
            "sort": sort_name,
            "header": {"counts": _json_value(header_row[0], {}), "rates": _json_value(header_row[1], {}), "scope": _json_value(header_row[2], {}), "source_notice": header_row[3]},
            "coverage": coverage,
            "capabilities": {"ladder": result_status, "pagination": "COMPLETE" if coverage.get("complete_pagination") is True else "PARTIAL_OR_UNVERIFIED", "field_scale": "UNRESOLVED"},
            "items": page_items,
            "empty_state": empty_state,
            "next_action": "字段倍率/梯队语义未确认的列保持未确认；不以空值改写在线事实。" if result_status == "DEGRADED" else "可继续查看单股事件详情。",
        }

    def ladder_evidence(
        self,
        *,
        security_id: str,
        event_bundle_id: str | None = None,
        trade_date: str | None = None,
    ) -> dict[str, Any]:
        normalized_security_id = str(security_id or "").strip()
        if not normalized_security_id:
            raise OnlineEventQueryError("SECURITY_ID_REQUIRED")
        result = self.ladder(
            event_bundle_id=event_bundle_id,
            trade_date=trade_date,
            security_id=normalized_security_id,
            page=1,
            page_size=1,
            sort="DEFAULT",
        )
        source = result.get("source", {"source_id": EXT01_SOURCE_ID, "dataset": EXT01_DATASET, "capability": "DEGRADED"})
        if result.get("status") == "UNAVAILABLE":
            return _evidence_unavailable(
                security_id=normalized_security_id,
                source=source,
                code=result.get("empty_state", {}).get("code", "EVENT_BUNDLE_UNAVAILABLE"),
                message=result.get("empty_state", {}).get("message", "当前没有可读取的 EXT01 收盘事件批次。"),
                base=result,
            )
        items = result.get("items") or []
        item = items[0] if items else None
        if item is None:
            return _evidence_unavailable(
                security_id=normalized_security_id,
                source=source,
                code="EVENT_MEMBER_UNAVAILABLE",
                message="当前事件批次没有该股票的涨停成员证据。",
                base=result,
            )
        observed_at = result.get("observed_at")
        source_as_of = result.get("source_as_of")
        return {
            "api_contract": ONLINE_EVENT_EVIDENCE_API_CONTRACT,
            "status": result.get("status"),
            "source": source,
            "event_bundle_id": result.get("event_bundle_id"),
            "batch_id": result.get("batch_id"),
            "trade_date": result.get("trade_date"),
            "observed_at": observed_at,
            "source_as_of": source_as_of,
            "source_time": {
                "observed_at": observed_at,
                "source_as_of": source_as_of,
                "basis": "SOURCE_AS_OF_AND_OBSERVED_AT" if source_as_of else "OBSERVED_AT_ONLY",
                "warning": "source_as_of未提供，不能把观察时间解释为逐股成交时间。" if source_as_of is None else None,
            },
            "security_id": item.get("security_id"),
            "item": item,
            "evidence": {
                "identity": {
                    "source_id": EXT01_SOURCE_ID,
                    "dataset": EXT01_DATASET,
                    "event_bundle_id": result.get("event_bundle_id"),
                    "batch_id": result.get("batch_id"),
                    "pool_type": item.get("pool_type"),
                    "source_code": item.get("source_code"),
                },
                "field_evidence": _field_evidence(item),
                "coverage": result.get("coverage"),
                "quality_codes": item.get("quality_codes", []),
                "raw_payload_persisted": False,
                "storage_basis": "NORMALIZED_CLOSE_EVENT_BATCH_ONLY",
            },
            "empty_state": None,
            "next_action": "保留来源字段与未确认倍率；不要把观察时间解释为逐股成交时间。",
        }
