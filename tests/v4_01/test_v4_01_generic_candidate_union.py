from __future__ import annotations

from scripts.v4_01_generic_relation_resolution import (
    build_candidate_union,
    candidates_from_events,
    validate_resolution_coverage,
)
from scripts.postcheck_v4_01_identity_completeness_gate_v2 import _dated_identity_pair


WINDOW = {"window_start": "2023-07-04", "window_end": "2026-09-24"}


def _candidate(old: str, new: str, effective: str) -> dict[str, str]:
    return {
        "old_source_security_key": old,
        "new_source_security_key": new,
        "effective_date": effective,
    }


def _union(scan=(), generic=(), official=()):
    return build_candidate_union(
        scan,
        generic,
        official,
        **WINDOW,
    )


def test_two_candidates_with_two_resolutions_pass() -> None:
    candidates = [
        _candidate("SZ.600001", "SZ.600101", "2024-01-02"),
        _candidate("SH.600002", "SH.600102", "2024-02-02"),
    ]
    union = _union(scan=candidates)
    resolutions = [
        {**candidate, "resolution": "CONFIRMED_SAME_ENTITY_CODE_CHANGE"}
        for candidate in candidates
    ]
    result = validate_resolution_coverage(union, resolutions)
    assert result["status"] == "PASS"
    assert result["candidate_union_count"] == result["resolution_count"] == 2
    assert result["unresolved_count"] == 0


def test_two_candidates_with_one_unresolved_block() -> None:
    candidates = [
        _candidate("SZ.600001", "SZ.600101", "2024-01-02"),
        _candidate("SH.600002", "SH.600102", "2024-02-02"),
    ]
    union = _union(scan=candidates)
    resolutions = [
        {**candidates[0], "resolution": "CONFIRMED_SAME_ENTITY_CODE_CHANGE"},
        {**candidates[1], "resolution": "UNRESOLVED_IDENTITY_RELATION"},
    ]
    result = validate_resolution_coverage(union, resolutions)
    assert result["status"] == "BLOCKED"
    assert result["unresolved_count"] == 1


def test_extra_r8_generic_candidate_is_added_to_union() -> None:
    generic = candidates_from_events(
        [
            {
                "candidate_id": "R8-GENERIC-EXTRA",
                "required_scope_affected": True,
                "effective_date_candidates": ["2024-03-04"],
                "resolution_evidence": [
                    _candidate("SH.600003", "SH.600103", "2024-03-04")
                ],
            }
        ],
        source="r8_generic_relation",
        **WINDOW,
        require_required_scope=True,
    )
    union = _union(generic=generic)
    key = ("SH.600003", "SH.600103", "2024-03-04")
    assert key in union
    assert "r8_generic_relation" in union[key]["sources"]


def test_in_window_known_official_candidate_is_added_to_union() -> None:
    official = candidates_from_events(
        [
            {
                "old_source_security_key": "SZ.600004",
                "new_source_security_key": "SZ.600104",
                "effective_date": "2024-04-05",
                "entity_relation": "SAME_ENTITY",
            }
        ],
        source="known_official_event",
        **WINDOW,
    )
    union = _union(official=official)
    key = ("SZ.600004", "SZ.600104", "2024-04-05")
    assert key in union
    assert "known_official_event" in union[key]["sources"]
    crosscheck_resolution = {
        **official[0],
        "resolution": "CONFIRMED_SAME_ENTITY_CODE_CHANGE",
    }
    assert validate_resolution_coverage(union, [crosscheck_resolution])["status"] == "PASS"


def test_resolution_key_outside_union_blocks() -> None:
    union = _union(scan=[_candidate("SZ.600001", "SZ.600101", "2024-01-02")])
    extra = {
        **_candidate("SZ.600009", "SZ.600109", "2024-09-09"),
        "resolution": "CONFIRMED_DISTINCT_CODE_REUSE",
    }
    result = validate_resolution_coverage(union, [extra])
    assert result["status"] == "BLOCKED"
    assert result["extra_keys"] == [["SZ.600009", "SZ.600109", "2024-09-09"]]


def test_dated_identity_evidence_is_resolved_generically() -> None:
    candidate = _candidate("SZ.600010", "SZ.600110", "2024-02-01")
    facts = [
        {"source_security_key": "SZ.600010", "security_id": "SEC-X", "symbol_effective_to": "2024-01-31"},
        {"source_security_key": "SZ.600110", "security_id": "SEC-X", "symbol_effective_from": "2024-02-01"},
    ]
    result = _dated_identity_pair(candidate, facts)
    assert result["boundary_facts_match"] is True
    assert result["same_security_id"] is True
