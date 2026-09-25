from __future__ import annotations

import struct

from workbench_analysis.canonical_source_selection import (
    LOCAL_FAMILY, PACKAGE_FAMILY, select_records, selection_digest, selection_segments,
)


def day(day_value: int, *, close: int, volume: int = 100, amount: float = 1000.0, reserved: int = 0) -> bytes:
    return struct.pack("<IIIIIfII", day_value, close, close, close, close, amount, volume, reserved)


def test_local_overlap_priority_and_package_gap_fill_keep_dual_provenance():
    package = {20260101: day(20260101, close=100), 20260102: day(20260102, close=101),
               20260103: day(20260103, close=102)}
    local = {20260102: day(20260102, close=101), 20260103: day(20260103, close=103)}
    rows, counts = select_records("SH.600000", package, local,
                                  package_revision="pkg", local_revision="local")
    assert [row.source_family for row in rows] == [PACKAGE_FAMILY, LOCAL_FAMILY, LOCAL_FAMILY]
    assert [row.selection_reason for row in rows] == ["PACKAGE_FILLS_LOCAL_GAP", "LOCAL_PRIORITY_ON_OVERLAP", "LOCAL_PRIORITY_ON_OVERLAP"]
    assert rows[1].alternative_record == package[20260102]
    assert rows[2].alternative_record == package[20260103]
    assert counts["package_rows"] == 1
    assert counts["local_rows"] == 2
    assert counts["overlap_rows"] == 2
    assert counts["market_field_conflicts"] == 1
    segments = selection_segments(rows, "SH.600000")
    assert len(segments) == 2
    overlap_segment = segments[1]
    assert overlap_segment["selected_source_digest"]
    assert overlap_segment["alternative_source_digest"]
    assert overlap_segment["canonical_security_id"] is None
    assert overlap_segment["identity_quality"] == "UNKNOWN_UNMAPPED"


def test_identical_market_rows_with_reserved_difference_are_audited_separately():
    package = {20260101: day(20260101, close=100, reserved=0)}
    local = {20260101: day(20260101, close=100, reserved=7)}
    _, counts = select_records("SZ.000001", package, local,
                               package_revision="pkg", local_revision="local")
    assert counts["market_field_conflicts"] == 0
    assert counts["reserved_only_differences"] == 1


def test_selection_manifest_digest_is_deterministic():
    rows, _ = select_records("SH.600000", {20260101: day(20260101, close=100)},
                             {20260101: day(20260101, close=100)},
                             package_revision="pkg", local_revision="local")
    segments = selection_segments(rows, "SH.600000")
    assert selection_digest(segments) == selection_digest(list(reversed(segments)))
