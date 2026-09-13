"""Explicit, versioned EXT03 topic to local sector joins.

No name or substring fallback is allowed. Empty mapping is an expected
degraded state until a reviewed crosswalk is available.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

CONTRACT_ID = "v3-p09-topic-sector-mapping-v1.0"


def _security_key(value: object) -> str | None:
    raw = str(value or "").upper().strip()
    if not raw:
        return None
    if "." in raw:
        left, right = raw.split(".", 1)
        if left in {"SH", "SZ", "BJ"} and len(right) == 6 and right.isdigit():
            return f"{left}.{right}"
        if len(left) == 6 and left.isdigit() and right in {"SS", "SH", "SZ", "BJ"}:
            return f"{'SH' if right in {'SS', 'SH'} else right}.{left}"
        return None
    if len(raw) == 6 and raw.isdigit():
        market = "SH" if raw.startswith(("6", "9")) else "BJ" if raw.startswith(("4", "8")) else "SZ"
        return f"{market}.{raw}"
    return None


def load_mapping(root: Path) -> dict[str, Any]:
    try:
        payload = json.loads((root / "config/p09_topic_sector_mapping_v1.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"contract_id": CONTRACT_ID, "entries": [], "status": "UNAVAILABLE"}
    if payload.get("contract_id") != CONTRACT_ID or not isinstance(payload.get("entries"), list):
        return {"contract_id": CONTRACT_ID, "entries": [], "status": "INVALID_CONTRACT"}
    return payload


def select_mappings(mapping: dict[str, Any], *, publication_id: str, sector_id: str, topics: list[dict[str, Any]], source_date: str | None = None, local_run_id: str | None = None, local_date: str | None = None) -> list[dict[str, Any]]:
    if mapping.get("local_run_id") and mapping.get("local_run_id") != local_run_id:
        return []
    if mapping.get("local_trade_date") and mapping.get("local_trade_date") != local_date:
        return []
    by_key = {f"EXT03:{item.get('source_topic_id')}": item for item in topics if item.get("source_topic_id") is not None}
    selected = []
    for entry in mapping.get("entries", []):
        if not isinstance(entry, dict):
            continue
        if entry.get("publication_id") != publication_id or entry.get("sector_id") != sector_id:
            continue
        if entry.get("source_trade_date") and entry.get("source_trade_date") != source_date:
            continue
        if entry.get("relation") not in {"EXACT", "RELATED"} or not entry.get("evidence_id"):
            continue
        topic = by_key.get(entry.get("source_topic_key"))
        if topic is not None and (not entry.get("source_topic_name") or entry["source_topic_name"] == topic.get("topic_name")):
            selected.append({"mapping": entry, "topic": topic})
    return selected


def intersect_members(mapped: list[dict[str, Any]], local_ids: set[str], *, local_complete: bool) -> dict[str, Any]:
    if not mapped:
        return {"status": "UNAVAILABLE", "reason": "NO_VERSIONED_TOPIC_SECTOR_MAPPING", "items": [], "count": None}
    if not local_complete:
        return {"status": "DEGRADED", "reason": "LOCAL_MEMBERSHIP_INCOMPLETE", "items": [], "count": None}
    canonical_local = {key for item in local_ids if (key := _security_key(item)) is not None}
    seen: set[str] = set()
    items = []
    for pair in mapped:
        for member in pair["topic"].get("members", []):
            code = _security_key(member.get("source_code"))
            if code is not None and code in canonical_local and code not in seen:
                seen.add(code)
                items.append({"security_id": code, "source_topic_key": pair["mapping"]["source_topic_key"], "relation": pair["mapping"]["relation"]})
    return {"status": "AVAILABLE", "reason": None, "items": items, "count": len(items)}
