"""Fail-closed M14-06 low-priority Dragon-Tiger list capability gate."""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Iterable


CONTRACT_ID = "M14_LH_LIST_V1_0"
UNAVAILABLE_REASON = "NO_VERIFIED_LH_SOURCE"


def _parse_date(value: object) -> date | None:
    if value in (None, ""):
        return None
    try:
        return date.fromisoformat(str(value))
    except ValueError as exc:
        raise ValueError("LH_TRADE_DATE_INVALID") from exc


def _parse_time(value: object) -> datetime | None:
    if value in (None, ""):
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("LH_PUBLISHED_TIME_INVALID") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def unavailable_lh_list_view(*, trade_date: str | None = None, as_of: str | None = None) -> dict:
    _parse_date(trade_date)
    _parse_time(as_of)
    return {
        "contract_id": CONTRACT_ID,
        "dataset": "LH_LIST",
        "capability_status": "UNAVAILABLE",
        "unavailable_reason": UNAVAILABLE_REASON,
        "source_ids": [],
        "trade_date": trade_date,
        "as_of": as_of,
        "batch_id": None,
        "items": [],
        "personal_research_only": True,
        "publication_enabled": False,
    }


def validate_lh_item(item: dict, *, as_of: str | None = None) -> dict:
    required = {
        "evidence_id", "source_id", "security_id", "source_code", "trade_date", "published_at",
        "first_seen_at", "raw_ref", "source_url", "seat_name", "buy_amount", "sell_amount", "amount_unit",
    }
    if not isinstance(item, dict) or not required.issubset(item):
        raise ValueError("LH_SCHEMA_INVALID")
    trade_date = _parse_date(item["trade_date"])
    published_at = _parse_time(item["published_at"])
    first_seen_at = _parse_time(item["first_seen_at"])
    if trade_date is None or published_at is None or first_seen_at is None:
        raise ValueError("LH_TIME_OR_TRADE_DATE_MISSING")
    if trade_date > published_at.date():
        raise ValueError("LH_TRADE_DATE_AFTER_PUBLICATION")
    anchor = _parse_time(as_of)
    if anchor and (published_at > anchor or first_seen_at > anchor):
        raise ValueError("LH_AFTER_AS_OF")
    if anchor and trade_date > anchor.date():
        raise ValueError("LH_AFTER_AS_OF")
    source_url = str(item["source_url"]).strip()
    if not source_url.startswith(("https://", "http://")):
        raise ValueError("LH_SOURCE_URL_INVALID")
    if not str(item["amount_unit"]).strip():
        raise ValueError("LH_AMOUNT_UNIT_MISSING")
    if any(not str(item[key]).strip() for key in ("evidence_id", "source_id", "security_id", "source_code", "raw_ref")):
        raise ValueError("LH_SOURCE_MAPPING_MISSING")
    return {
        "evidence_id": str(item["evidence_id"]),
        "source_id": str(item["source_id"]),
        "security_id": str(item["security_id"]),
        "source_code": str(item["source_code"]),
        "trade_date": item["trade_date"],
        "published_at": item["published_at"],
        "first_seen_at": item["first_seen_at"],
        "raw_ref": str(item["raw_ref"]),
        "source_url": str(item["source_url"]),
        "seat_name": str(item["seat_name"]) if item["seat_name"] is not None else None,
        "buy_amount": item["buy_amount"],
        "sell_amount": item["sell_amount"],
        "amount_unit": str(item["amount_unit"]),
    }


def build_lh_list_view(items: Iterable[dict], *, source_status: str = "UNAVAILABLE", trade_date: str | None = None, as_of: str | None = None) -> dict:
    if source_status != "ENABLED":
        return unavailable_lh_list_view(trade_date=trade_date, as_of=as_of)
    _parse_date(trade_date)
    normalized = []
    for item in items:
        candidate = validate_lh_item(item, as_of=as_of)
        if trade_date is None or candidate["trade_date"] == trade_date:
            normalized.append(candidate)
    return {
        "contract_id": CONTRACT_ID,
        "dataset": "LH_LIST",
        "capability_status": "ENABLED",
        "unavailable_reason": None,
        "source_ids": sorted({item["source_id"] for item in normalized}),
        "trade_date": trade_date,
        "as_of": as_of,
        "batch_id": None,
        "items": normalized,
        "personal_research_only": True,
        "publication_enabled": False,
    }
