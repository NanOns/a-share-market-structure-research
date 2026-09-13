"""Versioned in-memory event DTOs and the EXT01 limit-up adapter.

This module deliberately stops before persistence and API wiring.  The adapter
keeps source evidence in memory, refuses to infer unresolved scales, and keeps
the aggregate header separate from member rows as required by V3.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import re
from typing import Any, Mapping
from zoneinfo import ZoneInfo


EVENT_DTO_CONTRACT_VERSION = "v3-online-event-dto-v1.0"
EXT01_EVENT_ADAPTER_VERSION = "v3-lz-ext01-event-adapter-v1.0"
EXT01_SOURCE_ID = "EXT01"
EXT01_DATASET = "LIMIT_POOL_UP"
LIMIT_UP_POOL_TYPE = "LIMIT_UP"
_SHANGHAI = ZoneInfo("Asia/Shanghai")
_MARKET_EXCHANGE = {17: "SH", 33: "SZ"}
_REQUIRED_EXT01_FIELDS = frozenset({"code", "name", "latest", "change_rate"})


class EventSchemaError(ValueError):
    """Raised when an online event response cannot satisfy its contract."""


def _as_decimal(value: Any) -> Decimal | None:
    if value is None or isinstance(value, bool):
        return None
    text = str(value).strip().replace(",", "")
    if not text or text in {"-", "--", "N/A", "null", "None"}:
        return None
    try:
        return Decimal(text)
    except (InvalidOperation, ValueError):
        return None


def _as_int(value: Any) -> int | None:
    number = _as_decimal(value)
    if number is None or number != number.to_integral_value():
        return None
    return int(number)


def _aware_datetime(value: datetime | str) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    else:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def _source_time(value: Any) -> tuple[datetime | None, bool]:
    """Parse only explicit Unix seconds/milliseconds; return (value, invalid)."""
    number = _as_decimal(value)
    if number is None:
        return None, value not in (None, "", "-", "--", "0", 0)
    if number == 0:
        return None, False
    integer = int(number)
    if integer >= 10**12:
        timestamp = integer / 1000
    elif integer >= 10**9:
        timestamp = integer
    else:
        return None, True
    try:
        return datetime.fromtimestamp(timestamp, tz=timezone.utc).astimezone(_SHANGHAI), False
    except (OverflowError, OSError, ValueError):
        return None, True


def _market_namespace(row: Mapping[str, Any]) -> tuple[str, str | None]:
    raw_market = row.get("market_id")
    market_number = _as_int(raw_market)
    exchange = _MARKET_EXCHANGE.get(market_number) if market_number is not None else None
    if exchange is None:
        text = str(raw_market or row.get("market_type") or "").strip().upper()
        if text in {"SH", "SZ"}:
            exchange = text
    if exchange:
        return exchange, exchange
    if raw_market not in (None, ""):
        return f"MKT_{str(raw_market).strip()}", None
    return "MKT_UNRESOLVED", None


def _source_count(value: Any) -> tuple[int | None, str | None]:
    if not isinstance(value, Mapping):
        return _as_int(value), "$"
    for path in ("today.num", "num", "total", "count"):
        current: Any = value
        for part in path.split("."):
            if not isinstance(current, Mapping) or part not in current:
                current = None
                break
            current = current[part]
        parsed = _as_int(current)
        if parsed is not None:
            return parsed, f"$.{path}"
    return None, None


@dataclass(frozen=True)
class EventHeader:
    """Aggregate source facts; header counts are never repeated as member rows."""

    contract_version: str
    adapter_version: str
    source_id: str
    dataset: str
    trade_date: str
    observed_at: datetime
    source_as_of: datetime | None
    batch_id: str | None
    counts: Mapping[str, int | None]
    rates: Mapping[str, Decimal | None]
    scope: Mapping[str, Any]
    source_notice: str | None
    quality_codes: tuple[str, ...]

    def to_record(self) -> dict[str, Any]:
        return {
            "contract_version": self.contract_version,
            "adapter_version": self.adapter_version,
            "source_id": self.source_id,
            "dataset": self.dataset,
            "trade_date": self.trade_date,
            "observed_at": self.observed_at.isoformat(),
            "source_as_of": self.source_as_of.isoformat() if self.source_as_of else None,
            "batch_id": self.batch_id,
            "counts": dict(self.counts),
            "rates": {key: _json_number(value) for key, value in self.rates.items()},
            "scope": dict(self.scope),
            "source_notice": self.source_notice,
            "quality_codes": list(self.quality_codes),
        }


@dataclass(frozen=True)
class EventPoolRow:
    """Explainable member event facts with unresolved values left NULL."""

    contract_version: str
    adapter_version: str
    source_id: str
    dataset: str
    trade_date: str
    observed_at: datetime
    source_as_of: datetime | None
    batch_id: str | None
    pool_type: str
    source_code: str
    security_id: str | None
    security_name: str
    event_state: str
    consecutive_limit_days: int | None
    m_days: int | None
    n_boards: int | None
    first_limit_time: datetime | None
    last_limit_time: datetime | None
    last_break_time: datetime | None
    price: Decimal | None
    amount: Decimal | None
    seal_amount: Decimal | None
    ret1: Decimal | None
    turnover: Decimal | None
    float_market_cap: Decimal | None
    open_count: int | None
    source_reason: str | None
    source_fields: Mapping[str, Any]
    quality_codes: tuple[str, ...]

    def to_record(self) -> dict[str, Any]:
        record = {
            "contract_version": self.contract_version,
            "adapter_version": self.adapter_version,
            "source_id": self.source_id,
            "dataset": self.dataset,
            "trade_date": self.trade_date,
            "observed_at": self.observed_at.isoformat(),
            "source_as_of": self.source_as_of.isoformat() if self.source_as_of else None,
            "batch_id": self.batch_id,
            "pool_type": self.pool_type,
            "source_code": self.source_code,
            "security_id": self.security_id,
            "security_name": self.security_name,
            "event_state": self.event_state,
            "consecutive_limit_days": self.consecutive_limit_days,
            "m_days": self.m_days,
            "n_boards": self.n_boards,
            "first_limit_time": self.first_limit_time.isoformat() if self.first_limit_time else None,
            "last_limit_time": self.last_limit_time.isoformat() if self.last_limit_time else None,
            "last_break_time": self.last_break_time.isoformat() if self.last_break_time else None,
            "price": _json_number(self.price),
            "amount": _json_number(self.amount),
            "seal_amount": _json_number(self.seal_amount),
            "ret1": _json_number(self.ret1),
            "turnover": _json_number(self.turnover),
            "float_market_cap": _json_number(self.float_market_cap),
            "open_count": self.open_count,
            "source_reason": self.source_reason,
            "source_fields": dict(self.source_fields),
            "quality_codes": list(self.quality_codes),
        }
        return record


def _json_number(value: Decimal | None) -> str | None:
    return format(value, "f") if value is not None else None


def _normalize_row(
    row: Mapping[str, Any],
    *,
    trade_date: str,
    observed_at: datetime,
    source_as_of: datetime | None,
    batch_id: str | None,
) -> EventPoolRow:
    missing = sorted(_REQUIRED_EXT01_FIELDS - set(row))
    if missing:
        raise EventSchemaError(f"EXT01_ROW_FIELDS_MISSING:{','.join(missing)}")
    source_code_raw = str(row.get("code", "")).strip()
    security_name = str(row.get("name", "")).strip()
    if not source_code_raw or not security_name:
        raise EventSchemaError("EXT01_ROW_IDENTITY_EMPTY")
    namespace, exchange = _market_namespace(row)
    source_code = f"{namespace}:{source_code_raw}"
    security_id = f"{exchange}.{source_code_raw}" if exchange and source_code_raw.isdigit() else None
    quality: list[str] = []
    if security_id is None:
        quality.append("SECURITY_ID_UNMAPPED")

    price = _as_decimal(row.get("latest"))
    if price is None:
        quality.append("PRICE_INVALID")

    # V3 explicitly leaves these values unresolved until repeated samples fix scale/unit.
    unresolved = (
        "RET1_SCALE_UNRESOLVED",
        "AMOUNT_SCALE_UNRESOLVED",
        "SEAL_AMOUNT_SCALE_UNRESOLVED",
        "FLOAT_MARKET_CAP_SCALE_UNRESOLVED",
        "TURNOVER_SCALE_UNRESOLVED",
    )
    quality.extend(unresolved)

    first_limit_time, first_invalid = _source_time(row.get("first_limit_up_time"))
    last_limit_time, last_invalid = _source_time(row.get("last_limit_up_time"))
    if first_invalid:
        quality.append("FIRST_LIMIT_TIME_UNRESOLVED")
    if last_invalid:
        quality.append("LAST_LIMIT_TIME_UNRESOLVED")
    high_days = str(row.get("high_days") or "").strip()
    consecutive_days = m_days = n_boards = None
    if high_days == "首板":
        consecutive_days = m_days = n_boards = 1
    elif match := re.fullmatch(r"([1-9]\d*)天([1-9]\d*)板", high_days):
        m_days, n_boards = map(int, match.groups())
        if m_days == n_boards:
            consecutive_days = n_boards
    if high_days and n_boards is None:
        quality.append("LADDER_SEMANTICS_UNRESOLVED")
    elif not high_days:
        quality.append("LADDER_HEIGHT_SOURCE_MISSING")

    open_count = _as_int(row.get("open_num"))
    if row.get("open_num") not in (None, "", "-") and open_count is None:
        quality.append("OPEN_COUNT_INVALID")
    reason = row.get("reason_type")
    reason_text = str(reason).strip() if reason not in (None, "") else None
    return EventPoolRow(
        contract_version=EVENT_DTO_CONTRACT_VERSION,
        adapter_version=EXT01_EVENT_ADAPTER_VERSION,
        source_id=EXT01_SOURCE_ID,
        dataset=EXT01_DATASET,
        trade_date=trade_date,
        observed_at=observed_at,
        source_as_of=source_as_of,
        batch_id=batch_id,
        pool_type=LIMIT_UP_POOL_TYPE,
        source_code=source_code,
        security_id=security_id,
        security_name=security_name,
        event_state=LIMIT_UP_POOL_TYPE,
        consecutive_limit_days=consecutive_days,
        m_days=m_days,
        n_boards=n_boards,
        first_limit_time=first_limit_time,
        last_limit_time=last_limit_time,
        last_break_time=None,
        price=price,
        amount=None,
        seal_amount=None,
        ret1=None,
        turnover=None,
        float_market_cap=None,
        open_count=open_count,
        source_reason=reason_text,
        source_fields=dict(row),
        quality_codes=tuple(sorted(set(quality))),
    )


def adapt_ext01_payload(
    payload: Mapping[str, Any],
    *,
    trade_date: str,
    observed_at: datetime | str,
    source_as_of: datetime | str | None = None,
    batch_id: str | None = None,
) -> tuple[EventHeader, tuple[EventPoolRow, ...]]:
    """Adapt one legal EXT01 response without persisting or inventing facts."""
    if not isinstance(payload, Mapping) or payload.get("status_code") not in (0, "0"):
        raise EventSchemaError("EXT01_SOURCE_STATUS_NOT_OK")
    data = payload.get("data")
    if not isinstance(data, Mapping):
        raise EventSchemaError("EXT01_DATA_OBJECT_MISSING")
    source_rows = data.get("info")
    if not isinstance(source_rows, list):
        raise EventSchemaError("EXT01_INFO_ARRAY_MISSING")
    observed = _aware_datetime(observed_at)
    as_of = _aware_datetime(source_as_of) if source_as_of is not None else None
    rows = tuple(
        _normalize_row(
            row,
            trade_date=trade_date,
            observed_at=observed,
            source_as_of=as_of,
            batch_id=batch_id,
        )
        for row in source_rows
        if isinstance(row, Mapping)
    )
    if len(rows) != len(source_rows):
        raise EventSchemaError("EXT01_INFO_ROW_NOT_OBJECT")

    limit_count, limit_path = _source_count(data.get("limit_up_count"))
    down_count, down_path = _source_count(data.get("limit_down_count"))
    quality: list[str] = []
    if limit_count is None:
        quality.append("HEADER_LIMIT_COUNT_UNRESOLVED")
    if down_count is None:
        quality.append("HEADER_DOWN_COUNT_UNRESOLVED")
    quality.append("HEADER_RATES_NOT_COMPUTED")
    notice = str(data.get("msg")).strip() if data.get("msg") not in (None, "") else None
    if notice:
        quality.append("SOURCE_NOTICE_PRESENT")
    header = EventHeader(
        contract_version=EVENT_DTO_CONTRACT_VERSION,
        adapter_version=EXT01_EVENT_ADAPTER_VERSION,
        source_id=EXT01_SOURCE_ID,
        dataset=EXT01_DATASET,
        trade_date=trade_date,
        observed_at=observed,
        source_as_of=as_of,
        batch_id=batch_id,
        counts={
            "source_limit_count": limit_count,
            "source_broken_count": None,
            "source_down_count": down_count,
        },
        rates={"seal_rate": None, "broken_rate": None, "source_rate": None},
        scope={
            "row_path": "$.data.info",
            "page": _as_int(data.get("page")),
            "page_row_count": len(rows),
            "complete_pagination": False,
            "source_count_paths": {
                "source_limit_count": limit_path,
                "source_down_count": down_path,
            },
            "trade_status": data.get("trade_status"),
        },
        source_notice=notice,
        quality_codes=tuple(sorted(set(quality))),
    )
    return header, rows
