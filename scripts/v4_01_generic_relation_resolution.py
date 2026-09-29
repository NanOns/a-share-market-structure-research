from __future__ import annotations

"""Pure helpers for fail-closed V4-01 relation candidate coverage."""

from datetime import date, timedelta
from itertools import permutations
from typing import Any, Iterable


RESOLUTION_STATES = {
    "CONFIRMED_SAME_ENTITY_CODE_CHANGE",
    "CONFIRMED_DISTINCT_MERGER_SUCCESSOR",
    "CONFIRMED_DISTINCT_CODE_REUSE",
    "UNRESOLVED_IDENTITY_RELATION",
}


def candidate_key(candidate: dict[str, Any]) -> tuple[str, str, str] | None:
    old = str(candidate.get("old_source_security_key") or "").strip().upper()
    new = str(candidate.get("new_source_security_key") or "").strip().upper()
    effective = str(candidate.get("effective_date") or "").strip()
    if not old or not new or old == new or not effective:
        return None
    try:
        date.fromisoformat(effective)
    except ValueError:
        return None
    return old, new, effective


def _in_window(effective_date: str, start: str, end: str) -> bool:
    return start <= effective_date <= end


def _identity_orientations(
    source_keys: list[str], effective_date: str, identity_records: Iterable[dict[str, Any]]
) -> list[tuple[str, str]]:
    by_key: dict[str, list[dict[str, Any]]] = {}
    for row in identity_records:
        key = str(row.get("source_security_key") or "").upper()
        if key:
            by_key.setdefault(key, []).append(row)
    prior_date = (date.fromisoformat(effective_date) - timedelta(days=1)).isoformat()
    matches = []
    for old, new in permutations([str(key).upper() for key in source_keys], 2):
        old_ends = any(
            row.get("symbol_effective_to") == prior_date
            or row.get("effective_to") == prior_date
            for row in by_key.get(old, [])
        )
        new_starts = any(
            row.get("symbol_effective_from") == effective_date
            or row.get("effective_from") == effective_date
            for row in by_key.get(new, [])
        )
        if old_ends and new_starts:
            matches.append((old, new))
    return matches


def candidates_from_events(
    events: Iterable[dict[str, Any]],
    *,
    source: str,
    window_start: str,
    window_end: str,
    identity_records: Iterable[dict[str, Any]] = (),
    require_required_scope: bool = False,
) -> list[dict[str, Any]]:
    """Normalize generic relation events without relying on specific codes."""
    records = list(identity_records)
    normalized: dict[tuple[str, str, str], dict[str, Any]] = {}
    for event in events:
        if require_required_scope and event.get("required_scope_affected") is not True:
            continue
        base_dates = event.get("effective_date_candidates") or ([event.get("effective_date")] if event.get("effective_date") else [])
        variants: list[tuple[str, str, str]] = []

        direct_key = candidate_key(event)
        if direct_key:
            variants.append(direct_key)

        for evidence in event.get("resolution_evidence", []):
            key = candidate_key(evidence)
            if key:
                variants.append(key)

        if not variants:
            source_keys = [str(key).upper() for key in event.get("source_keys", []) if key]
            if len(source_keys) >= 2:
                for effective in base_dates:
                    effective = str(effective or "")
                    if not effective or not _in_window(effective, window_start, window_end):
                        continue
                    oriented = _identity_orientations(source_keys, effective, records)
                    # Without accepted dated facts establishing direction, keep
                    # every orientation so the owner gate fails closed.
                    pairs = oriented or list(permutations(source_keys, 2))
                    variants.extend((old, new, effective) for old, new in pairs)

        event_id = str(event.get("candidate_id") or event.get("event_id") or "")
        for old, new, effective in variants:
            if not _in_window(effective, window_start, window_end):
                continue
            key = candidate_key({
                "old_source_security_key": old,
                "new_source_security_key": new,
                "effective_date": effective,
            })
            if key is None:
                continue
            row = normalized.setdefault(key, {
                "old_source_security_key": key[0],
                "new_source_security_key": key[1],
                "effective_date": key[2],
                "sources": [],
                "source_event_ids": [],
            })
            if source not in row["sources"]:
                row["sources"].append(source)
            if event_id and event_id not in row["source_event_ids"]:
                row["source_event_ids"].append(event_id)
    return [normalized[key] for key in sorted(normalized)]


def build_candidate_union(
    scan_candidates: Iterable[dict[str, Any]],
    generic_candidates: Iterable[dict[str, Any]],
    known_official_candidates: Iterable[dict[str, Any]],
    *,
    window_start: str,
    window_end: str,
) -> dict[tuple[str, str, str], dict[str, Any]]:
    """Union the three required discovery sources by the canonical triple."""
    union: dict[tuple[str, str, str], dict[str, Any]] = {}
    sources = (
        ("source_fingerprint_scan", scan_candidates),
        ("r8_generic_relation", generic_candidates),
        ("known_official_event", known_official_candidates),
    )
    for source, candidates in sources:
        for candidate in candidates:
            key = candidate_key(candidate)
            if key is None or not _in_window(key[2], window_start, window_end):
                continue
            row = union.setdefault(key, {
                "old_source_security_key": key[0],
                "new_source_security_key": key[1],
                "effective_date": key[2],
                "candidate_key": list(key),
                "sources": [],
                "source_event_ids": [],
            })
            for label in candidate.get("sources", []):
                if label not in row["sources"]:
                    row["sources"].append(label)
            if source not in row["sources"]:
                row["sources"].append(source)
            for event_id in candidate.get("source_event_ids", []):
                if event_id and event_id not in row["source_event_ids"]:
                    row["source_event_ids"].append(event_id)
            event_id = candidate.get("candidate_id") or candidate.get("event_id")
            if event_id and event_id not in row["source_event_ids"]:
                row["source_event_ids"].append(str(event_id))
    return dict(sorted(union.items()))


def validate_resolution_coverage(
    candidate_union: dict[tuple[str, str, str], dict[str, Any]],
    resolutions: Iterable[dict[str, Any]],
) -> dict[str, Any]:
    """Require one valid four-state resolution for every and only union key."""
    items = list(resolutions)
    keys = [candidate_key(item) for item in items]
    valid_keys = [key for key in keys if key is not None]
    union_keys = set(candidate_union)
    resolution_keys = set(valid_keys)
    unresolved = sum(item.get("resolution") == "UNRESOLVED_IDENTITY_RELATION" for item in items)
    invalid_states = [item for item in items if item.get("resolution") not in RESOLUTION_STATES]
    duplicates = len(valid_keys) != len(resolution_keys)
    complete = (
        len(items) == len(candidate_union)
        and resolution_keys == union_keys
        and not duplicates
        and not invalid_states
        and unresolved == 0
    )
    return {
        "status": "PASS" if complete else "BLOCKED",
        "candidate_union_count": len(candidate_union),
        "resolution_count": len(items),
        "candidate_union_keys": [list(key) for key in sorted(union_keys)],
        "resolution_keys": [list(key) for key in sorted(resolution_keys)],
        "unresolved_count": unresolved,
        "duplicate_resolution_count": len(valid_keys) - len(resolution_keys),
        "invalid_state_count": len(invalid_states),
        "missing_keys": [list(key) for key in sorted(union_keys - resolution_keys)],
        "extra_keys": [list(key) for key in sorted(resolution_keys - union_keys)],
    }
