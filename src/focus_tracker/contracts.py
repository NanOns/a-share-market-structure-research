"""FOCUS-00 identities and canonical evidence encoding.

This package never reads a TDX source or selects a runtime head.  The caller
must supply accepted publication/source identities and materialized facts.
"""
from __future__ import annotations

import hashlib
import json
import math
import struct
from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any


CANONICAL_CONTRACT = "FOCUS_CANONICAL_JSON_V1"
SOURCE_AUTHORITY_CONTRACT = "FOCUS_SOURCE_AUTHORITY_V1"
EPISODE_CONTRACT = "FOCUS_EPISODE_ID_V2_1"
LIFECYCLE_CONTRACT = "FOCUS_EPISODE_LIFECYCLE_V2_1"
ANCHOR_CONTRACT = "FOCUS_ANCHOR_CONTRACT_V1"
SOURCE_FAMILIES = frozenset({
    "V3_SHORTLIST_STOCK", "V3_SECTOR_TRACK", "V3_3_TODAY_CANDIDATE",
    "V3_SHORTLIST_INDIVIDUAL",
})
SOURCE_MEMBERSHIPS = {
    "V3_SHORTLIST_STOCK": frozenset({"EARLY", "CURRENT"}),
    "V3_SECTOR_TRACK": frozenset({"EARLY", "CURRENT"}),
    "V3_3_TODAY_CANDIDATE": frozenset({"CANDIDATE"}),
    "V3_SHORTLIST_INDIVIDUAL": frozenset({"INDIVIDUAL"}),
}


def _canonical_value(value: Any) -> Any:
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("nonfinite float in focus evidence")
        return {"$binary64": struct.pack(">d", 0.0 if value == 0 else value).hex()}
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise ValueError("nonfinite decimal in focus evidence")
        return {"$decimal": format(value, "f")}
    if isinstance(value, datetime):
        if value.tzinfo is None:
            raise ValueError("naive timestamp in focus evidence")
        return value.astimezone(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, (list, tuple)):
        return [_canonical_value(item) for item in value]
    if isinstance(value, dict):
        if not all(isinstance(key, str) for key in value):
            raise ValueError("focus evidence keys must be strings")
        return {key: _canonical_value(item) for key, item in value.items()}
    raise TypeError(f"unsupported focus evidence type: {type(value).__name__}")


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(_canonical_value(value), ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


@dataclass(frozen=True, order=True)
class FocusKey:
    source_family: str
    entity_type: str
    entity_id: str
    selection_contract_family: str

    def __post_init__(self) -> None:
        if self.source_family not in SOURCE_FAMILIES:
            raise ValueError("unknown focus source family")
        expected = "SECTOR" if self.source_family == "V3_SECTOR_TRACK" else "STOCK"
        if self.entity_type != expected or not self.entity_id or not self.selection_contract_family:
            raise ValueError("invalid focus key")


def episode_id(key: FocusKey, start_trade_date: date) -> str:
    payload = {
        "contract": EPISODE_CONTRACT,
        "source_family": key.source_family,
        "entity_type": key.entity_type,
        "entity_id": key.entity_id,
        "episode_start_trade_date": start_trade_date,
        "source_selection_contract_family": key.selection_contract_family,
    }
    return "focus-" + digest(payload)[:32]


def anchor_id(episode: str, anchor_type: str, trade_date: date,
              ordinal: int = 1) -> str:
    allowed = {"FIRST_FOCUS", "CURRENT_UPGRADE", "EXIT_EFFECTIVE",
               "INVALIDATION", "FIRST_SUPPORTED", "MILESTONE"}
    if anchor_type not in allowed or ordinal < 1:
        raise ValueError("invalid focus anchor")
    return "anchor-" + digest({"contract": ANCHOR_CONTRACT,
                                "episode_id": episode, "anchor_type": anchor_type,
                                "trade_date": trade_date, "ordinal": ordinal})[:32]


def revisioned_anchor_id(base_anchor_id: str, source_revision: int) -> str:
    """Give a same-day revision its own immutable anchor identity."""
    if not base_anchor_id or source_revision < 1:
        raise ValueError("invalid revisioned Focus anchor identity")
    return "anchor-rev-" + digest({"contract": "FOCUS_REVISIONED_ANCHOR_V1",
                                   "base_anchor_id": base_anchor_id,
                                   "source_revision": source_revision})[:32]


def source_item_digest(source_item_key: str, source_contract_id: str,
                       source_row: dict[str, Any]) -> str:
    if not source_item_key or not source_contract_id:
        raise ValueError("source row identity required")
    return digest({"contract": CANONICAL_CONTRACT, "source_item_key": source_item_key,
                   "source_contract_id": source_contract_id, "source_row": source_row})
