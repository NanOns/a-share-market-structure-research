"""Deterministic local-TDX-over-package history source selection."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass

from tdx.day_reader import DAY_STRUCT


LOCAL_FAMILY = "TDX_LOCAL_CURRENT_CHAIN"
PACKAGE_FAMILY = "TDX_COMPLETE_PACKAGE"
CONTRACT_ID = "CANONICAL_SOURCE_SELECTION_V1"


@dataclass(frozen=True)
class SelectedRecord:
    trade_date: int
    source_family: str
    source_revision: str
    selected_record: bytes
    alternative_family: str | None
    alternative_revision: str | None
    alternative_record: bytes | None
    selection_reason: str


def select_records(
    source_security_key: str,
    package_records: dict[int, bytes],
    local_records: dict[int, bytes],
    *,
    package_revision: str,
    local_revision: str,
) -> tuple[list[SelectedRecord], dict[str, int]]:
    """Select by date, keeping local rows on overlap and package rows for gaps.

    No canonical entity identity is inferred from a source symbol. Returned
    records retain both source digests wherever an overlap exists.
    """
    if not source_security_key or not package_revision or not local_revision:
        raise ValueError("SOURCE_SELECTION_IDENTITY_MISSING")
    dates = sorted(set(package_records) | set(local_records))
    selected: list[SelectedRecord] = []
    counts = {"local_rows": 0, "package_rows": 0, "overlap_rows": 0,
              "market_field_conflicts": 0, "reserved_only_differences": 0}
    for day in dates:
        package_row = package_records.get(day)
        local_row = local_records.get(day)
        if package_row is None and local_row is None:
            continue
        if package_row is not None and len(package_row) != DAY_STRUCT.size:
            raise ValueError("SOURCE_RECORD_SIZE_INVALID")
        if local_row is not None and len(local_row) != DAY_STRUCT.size:
            raise ValueError("SOURCE_RECORD_SIZE_INVALID")
        if package_row is not None and local_row is not None:
            # Date is checked against the map key to prevent cross-date binding.
            if DAY_STRUCT.unpack(package_row)[0] != day or DAY_STRUCT.unpack(local_row)[0] != day:
                raise ValueError("SOURCE_RECORD_DATE_KEY_MISMATCH")
            chosen, alternative = local_row, package_row
            family, alt_family = LOCAL_FAMILY, PACKAGE_FAMILY
            revision, alt_revision = local_revision, package_revision
            reason = "LOCAL_PRIORITY_ON_OVERLAP"
            counts["overlap_rows"] += 1
            if local_row[:28] != package_row[:28]:
                counts["market_field_conflicts"] += 1
            elif local_row != package_row:
                counts["reserved_only_differences"] += 1
        elif local_row is not None:
            chosen, alternative = local_row, None
            family, alt_family = LOCAL_FAMILY, None
            revision, alt_revision = local_revision, None
            reason = "LOCAL_ONLY"
        else:
            chosen, alternative = package_row, None
            family, alt_family = PACKAGE_FAMILY, None
            revision, alt_revision = package_revision, None
            reason = "PACKAGE_FILLS_LOCAL_GAP"
        if DAY_STRUCT.unpack(chosen)[0] != day:
            raise ValueError("SELECTED_RECORD_DATE_KEY_MISMATCH")
        counts["local_rows" if family == LOCAL_FAMILY else "package_rows"] += 1
        selected.append(SelectedRecord(day, family, revision, chosen, alt_family,
                                       alt_revision, alternative, reason))
    return selected, counts


def selection_segments(records: list[SelectedRecord], source_security_key: str) -> list[dict[str, object]]:
    """Compress adjacent ordered selections into auditable digest segments."""
    segments: list[dict[str, object]] = []
    current: list[SelectedRecord] = []
    current_key: tuple[str, str, str] | None = None

    def finish(rows: list[SelectedRecord]) -> dict[str, object]:
        first, last = rows[0], rows[-1]
        selected_digest = hashlib.sha256()
        alternative_digest = hashlib.sha256()
        alternative_count = 0
        for row in rows:
            selected_digest.update(row.selected_record)
            if row.alternative_record is not None:
                alternative_digest.update(row.alternative_record)
                alternative_count += 1
        return {
            "source_security_key": source_security_key,
            "canonical_security_id": None,
            "identity_quality": "UNKNOWN_UNMAPPED",
            "first_trade_date": first.trade_date,
            "last_trade_date": last.trade_date,
            "row_count": len(rows),
            "selected_source_family": first.source_family,
            "selected_source_revision": first.source_revision,
            "selected_source_digest": selected_digest.hexdigest(),
            "alternative_source_family": first.alternative_family,
            "alternative_source_revision": first.alternative_revision,
            "alternative_source_digest": alternative_digest.hexdigest() if alternative_count else None,
            "alternative_row_count": alternative_count,
            "selection_reason": first.selection_reason,
        }

    for row in records:
        key = (row.source_family, row.source_revision, row.selection_reason)
        if current and key != current_key:
            segments.append(finish(current))
            current = []
        if not current:
            current_key = key
        current.append(row)
    if current:
        segments.append(finish(current))
    return segments


def selection_digest(segments: list[dict[str, object]]) -> str:
    digest = hashlib.sha256()
    for row in sorted(segments, key=lambda item: (str(item["source_security_key"]),
                                                   int(item["first_trade_date"]),
                                                   str(item["selected_source_family"]))):
        encoded = "\0".join(str(row.get(key, "")) for key in (
            "source_security_key", "first_trade_date", "last_trade_date", "row_count",
            "selected_source_family", "selected_source_revision", "selected_source_digest",
            "alternative_source_family", "alternative_source_revision", "alternative_source_digest",
            "alternative_row_count", "selection_reason",
        ))
        digest.update(encoded.encode("utf-8"))
        digest.update(b"\n")
    return digest.hexdigest()
