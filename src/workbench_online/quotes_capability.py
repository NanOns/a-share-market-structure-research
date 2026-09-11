"""Fail-closed M14-05 latest-quote capability gate."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable


CONTRACT_ID = "M14_QUOTES_LATEST_V1_0"
UNVERIFIED_REASON = "NO_VERIFIED_QUOTE_SOURCE"


def _parse_time(value: object) -> datetime | None:
    if value in (None, ""):
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("QUOTE_TIME_INVALID") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def unavailable_quote_view(*, security_ids: list[str] | None = None, as_of: str | None = None) -> dict:
    _parse_time(as_of)
    return {
        "contract_id": CONTRACT_ID,
        "dataset": "QUOTES_LATEST",
        "capability_status": "NOT_VERIFIED",
        "unavailable_reason": UNVERIFIED_REASON,
        "source_ids": [],
        "security_ids": security_ids or [],
        "batch_id": None,
        "source_as_of": None,
        "as_of": as_of,
        "items": [],
        "personal_research_only": True,
        "publication_enabled": False,
    }


def validate_quote_item(item: dict, *, as_of: str | None = None) -> dict:
    required = {
        "source_id", "source_code", "security_id", "quote_time", "price", "ret1",
        "amount", "volume", "quote_state", "price_unit", "amount_unit", "volume_unit",
    }
    if not isinstance(item, dict) or not required.issubset(item):
        raise ValueError("QUOTE_SCHEMA_INVALID")
    quote_time = _parse_time(item["quote_time"])
    if quote_time is None:
        raise ValueError("QUOTE_TIME_MISSING")
    anchor = _parse_time(as_of)
    if anchor and quote_time > anchor:
        raise ValueError("QUOTE_AFTER_AS_OF")
    if any(not str(item[key]).strip() for key in ("source_id", "source_code", "security_id", "quote_state", "price_unit", "amount_unit", "volume_unit")):
        raise ValueError("QUOTE_IDENTITY_OR_UNIT_MISSING")
    return {
        "source_id": str(item["source_id"]),
        "source_code": str(item["source_code"]),
        "security_id": str(item["security_id"]),
        "quote_time": item["quote_time"],
        "price": item["price"],
        "ret1": item["ret1"],
        "amount": item["amount"],
        "volume": item["volume"],
        "quote_state": str(item["quote_state"]),
        "price_unit": str(item["price_unit"]),
        "amount_unit": str(item["amount_unit"]),
        "volume_unit": str(item["volume_unit"]),
    }


def build_quote_view(items: Iterable[dict], *, source_status: str = "NOT_VERIFIED", security_ids: list[str] | None = None, as_of: str | None = None) -> dict:
    if source_status != "ENABLED":
        return unavailable_quote_view(security_ids=security_ids, as_of=as_of)
    normalized = []
    wanted = set(security_ids or [])
    for item in items:
        candidate = validate_quote_item(item, as_of=as_of)
        if not wanted or candidate["security_id"] in wanted:
            normalized.append(candidate)
    return {
        "contract_id": CONTRACT_ID,
        "dataset": "QUOTES_LATEST",
        "capability_status": "ENABLED",
        "unavailable_reason": None,
        "source_ids": sorted({item["source_id"] for item in normalized}),
        "security_ids": security_ids or [],
        "batch_id": None,
        "source_as_of": None,
        "as_of": as_of,
        "items": normalized,
        "personal_research_only": True,
        "publication_enabled": False,
    }
