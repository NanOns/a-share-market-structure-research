"""Fail-closed M14-04 external-evidence capability gate."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable


CONTRACT_ID = "M14_EXTERNAL_EVIDENCE_V1_0"
UNAVAILABLE_REASON = "NO_VERIFIED_REASON_SOURCE"


def _parse_time(value: object) -> datetime | None:
    if value in (None, ""):
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("EXTERNAL_EVIDENCE_TIME_INVALID") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def unavailable_external_evidence_view(*, security_id: str | None = None, mode: str = "LATEST", as_of: str | None = None) -> dict:
    if mode not in {"LATEST", "AS_OF"}:
        raise ValueError("EXTERNAL_EVIDENCE_MODE_INVALID")
    if mode == "AS_OF" and as_of is None:
        raise ValueError("EXTERNAL_EVIDENCE_AS_OF_REQUIRED")
    _parse_time(as_of)
    return {
        "contract_id": CONTRACT_ID,
        "dataset": "EXTERNAL_EVIDENCE",
        "capability_status": "UNAVAILABLE",
        "unavailable_reason": UNAVAILABLE_REASON,
        "source_ids": [],
        "security_id": security_id,
        "mode": mode,
        "as_of": as_of,
        "batch_id": None,
        "source_as_of": None,
        "items": [],
        "post_hoc_items": [],
        "personal_research_only": True,
        "publication_enabled": False,
    }


def validate_external_evidence_item(item: dict, *, as_of: str | None = None) -> dict:
    required = {"evidence_id", "source_id", "security_id", "event_time", "published_at", "first_seen_at", "text_hash", "raw_ref", "text"}
    if not isinstance(item, dict) or not required.issubset(item):
        raise ValueError("EXTERNAL_EVIDENCE_SCHEMA_INVALID")
    if not str(item["text"]).strip() or not str(item["text_hash"]).strip() or not str(item["raw_ref"]).strip():
        raise ValueError("EXTERNAL_EVIDENCE_CONTENT_INVALID")
    event_time = _parse_time(item["event_time"])
    published_at = _parse_time(item["published_at"])
    first_seen_at = _parse_time(item["first_seen_at"])
    if event_time is None or published_at is None or first_seen_at is None:
        raise ValueError("EXTERNAL_EVIDENCE_TIME_MISSING")
    anchor = _parse_time(as_of)
    if anchor and (published_at > anchor or first_seen_at > anchor):
        raise ValueError("EXTERNAL_EVIDENCE_AFTER_AS_OF")
    return {
        "evidence_id": str(item["evidence_id"]),
        "source_id": str(item["source_id"]),
        "security_id": str(item["security_id"]),
        "event_time": item["event_time"],
        "published_at": item["published_at"],
        "first_seen_at": item["first_seen_at"],
        "text_hash": str(item["text_hash"]),
        "raw_ref": str(item["raw_ref"]),
        "text": str(item["text"]),
    }


def build_external_evidence_view(items: Iterable[dict], *, security_id: str | None = None, mode: str = "LATEST", as_of: str | None = None, source_status: str = "UNAVAILABLE") -> dict:
    if source_status != "ENABLED":
        return unavailable_external_evidence_view(security_id=security_id, mode=mode, as_of=as_of)
    if mode not in {"LATEST", "AS_OF"}:
        raise ValueError("EXTERNAL_EVIDENCE_MODE_INVALID")
    anchor = _parse_time(as_of) if as_of else None
    normalized = []
    post_hoc = []
    for item in items:
        candidate = validate_external_evidence_item(item)
        if security_id and candidate["security_id"] != security_id:
            continue
        if anchor and (_parse_time(candidate["published_at"]) > anchor or _parse_time(candidate["first_seen_at"]) > anchor):
            post_hoc.append(candidate)
        else:
            normalized.append(candidate)
    return {
        "contract_id": CONTRACT_ID,
        "dataset": "EXTERNAL_EVIDENCE",
        "capability_status": "ENABLED",
        "unavailable_reason": None,
        "source_ids": sorted({item["source_id"] for item in normalized + post_hoc}),
        "security_id": security_id,
        "mode": mode,
        "as_of": as_of,
        "batch_id": None,
        "source_as_of": None,
        "items": normalized,
        "post_hoc_items": post_hoc,
        "personal_research_only": True,
        "publication_enabled": False,
    }
