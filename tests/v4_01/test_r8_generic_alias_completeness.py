from __future__ import annotations

from workbench_analysis.v4_01_alias_completeness import (
    classify_candidate,
    discover_exact_bar_continuity_candidates,
    duplicate_identity_date_count,
    final_receipt_requires_alias_completeness_gate,
    required_scope_alias_gate_passes,
    validate_alias_interval_integrity,
    validate_confirmed_alias_coverage,
)
from workbench_analysis.dated_security_alias import DatedSecurityAliasResolver


def _bars(left: str, right: str, left_id: str, right_id: str, sessions: int = 20) -> list[dict[str, object]]:
    rows = []
    for day in range(sessions):
        date = f"2024-01-{day + 1:02d}"
        common = {
            "trade_date": date,
            "raw_open": 10 + day,
            "raw_high": 12 + day,
            "raw_low": 9 + day,
            "raw_close": 11 + day,
            "volume": 1000 + day,
            "amount": 10000 + day,
            "board_scope": "SZ_MAIN",
        }
        rows.extend(
            [
                {**common, "source_security_key": left, "security_id": left_id},
                {**common, "source_security_key": right, "security_id": right_id},
            ]
        )
    return rows


def _alias_facts(left: str, right: str, stable_id: str, digest: str = "a" * 64) -> list[dict[str, object]]:
    return [
        {
            "security_id": stable_id,
            "source_security_key": left,
            "effective_from": "2020-01-01",
            "effective_to": "2024-01-31",
            "exchange": "SZ",
            "board": "CHINEXT",
            "alias_role": "PREDECESSOR",
            "source_revision": "official-revision-1",
            "evidence_ref": "https://exchange.example/code-change.pdf",
            "evidence_hash": digest,
        },
        {
            "security_id": stable_id,
            "source_security_key": right,
            "effective_from": "2024-02-01",
            "effective_to": None,
            "exchange": "SZ",
            "board": "CHINEXT",
            "alias_role": "CURRENT",
            "source_revision": "official-revision-1",
            "evidence_ref": "https://exchange.example/code-change.pdf",
            "evidence_hash": digest,
        },
    ]


def test_same_entity_code_change_not_split_into_two_entities() -> None:
    facts = _alias_facts("SZ.600001", "SZ.302001", "SEC-ENTITY")
    candidate = discover_exact_bar_continuity_candidates(
        _bars("SZ.600001", "SZ.302001", "SEC-OLD", "SEC-NEW")
    )[0]
    resolved = classify_candidate(
        candidate,
        baseline_identity_by_key={
            "SZ.600001": {"security_id": "SEC-OLD", "board": "MAIN", "exchange": "SZ"},
            "SZ.302001": {"security_id": "SEC-NEW", "board": "MAIN", "exchange": "SZ"},
        },
        final_identity_by_key={
            "SZ.600001": {"security_id": "SEC-ENTITY"},
            "SZ.302001": {"security_id": "SEC-ENTITY"},
        },
        alias_facts=facts,
        verified_evidence_digests={"a" * 64},
        evidence_refs=["artifact://raw-bars"],
        evidence_digests=["b" * 64],
    )
    assert resolved["resolution_status"] == "CONFIRMED_SAME_ENTITY_CODE_CHANGE"
    assert resolved["resolved_security_id"] == "SEC-ENTITY"


def test_distinct_entity_code_reuse_not_merged() -> None:
    facts = [
        {**_alias_facts("SZ.600001", "SZ.302001", "SEC-A")[0], "security_id": "SEC-A"},
        {**_alias_facts("SZ.600001", "SZ.302001", "SEC-B")[1], "security_id": "SEC-B"},
    ]
    resolver = DatedSecurityAliasResolver(facts)
    assert resolver.resolve_alias("SEC-A", "2024-01-15") == "SZ.600001"
    assert resolver.resolve_alias("SEC-B", "2024-02-15") == "SZ.302001"
    assert len({row["security_id"] for row in facts}) == 2


def test_unresolved_code_change_candidate_fails_closed() -> None:
    rows = _bars("SZ.600001", "SZ.302001", "SEC-OLD", "SEC-NEW")
    candidate = discover_exact_bar_continuity_candidates(rows)[0]
    unresolved = classify_candidate(
        candidate,
        baseline_identity_by_key={
            "SZ.600001": {"security_id": "SEC-OLD", "board": "MAIN", "exchange": "SZ"},
            "SZ.302001": {"security_id": "SEC-NEW", "board": "MAIN", "exchange": "SZ"},
        },
        final_identity_by_key={},
        alias_facts=[],
        verified_evidence_digests=set(),
        evidence_refs=["artifact://raw-bars"],
        evidence_digests=["b" * 64],
    )
    assert unresolved["resolution_status"] == "UNRESOLVED"
    assert unresolved["resolved_security_id"] is None


def test_alias_effective_interval_non_overlapping() -> None:
    facts = _alias_facts("SZ.600001", "SZ.302001", "SEC-ENTITY")
    assert validate_alias_interval_integrity(facts) == {
        "alias_interval_conflicts": 0,
        "entity_alias_interval_conflicts": 0,
    }


def test_dated_board_follows_alias_fact_not_prefix_only() -> None:
    resolver = DatedSecurityAliasResolver(
        _alias_facts("SZ.300001", "SZ.302001", "SEC-ENTITY")
    )
    assert resolver.resolve_board("SEC-ENTITY", "2024-02-15") == "CHINEXT"


def test_duplicate_stable_id_trade_date_rejected() -> None:
    rows = [
        {"security_id": "SEC-1", "trade_date": "2024-01-02"},
        {"security_id": "SEC-1", "trade_date": "2024-01-02"},
    ]
    assert duplicate_identity_date_count(rows) == 1


def test_generic_candidate_discovery_catches_split_ids() -> None:
    candidates = discover_exact_bar_continuity_candidates(
        _bars("SH.600123", "SH.601123", "SEC-ONE", "SEC-TWO"),
        minimum_shared_sessions=20,
    )
    assert len(candidates) == 1
    assert candidates[0]["security_ids"] == ["SEC-ONE", "SEC-TWO"]
    assert candidates[0]["shared_identical_raw_bar_sessions"] == 20


def test_known_300114_302132_case_passes_as_fact_fixture_not_hardcoded_logic() -> None:
    facts = _alias_facts("SZ.300114", "SZ.302132", "SEC-FACT")
    candidate = discover_exact_bar_continuity_candidates(
        _bars("SZ.300114", "SZ.302132", "SEC-OLD", "SEC-NEW")
    )[0]
    resolved = classify_candidate(
        candidate,
        baseline_identity_by_key={
            "SZ.300114": {"security_id": "SEC-OLD", "board": "CHINEXT", "exchange": "SZ"},
            "SZ.302132": {"security_id": "SEC-NEW", "board": "MAIN", "exchange": "SZ"},
        },
        final_identity_by_key={
            "SZ.300114": {"security_id": "SEC-FACT"},
            "SZ.302132": {"security_id": "SEC-FACT"},
        },
        alias_facts=facts,
        verified_evidence_digests={"a" * 64},
        evidence_refs=[],
        evidence_digests=[],
    )
    assert resolved["resolution_status"] == "CONFIRMED_SAME_ENTITY_CODE_CHANGE"
    assert resolved["dated_fact_board"] == ["CHINEXT"]


def test_all_day_required_coverage_still_zero() -> None:
    facts = _alias_facts("SZ.600001", "SZ.302001", "SEC-ENTITY")
    assert validate_confirmed_alias_coverage(facts, ["2024-01-02", "2024-02-02"]) == 0


def test_final_receipt_requires_alias_completeness_gate() -> None:
    passing = {
        "status": "PASS",
        "required_scope": {board: {"status": "PASS"} for board in ("SH_MAIN", "SZ_MAIN", "CHINEXT", "STAR")},
        "candidate_status_counts": {"UNRESOLVED": 0},
        "unresolved_required_scope_candidate_count": 0,
    }
    assert required_scope_alias_gate_passes(passing)
    assert final_receipt_requires_alias_completeness_gate(passing)
    assert not final_receipt_requires_alias_completeness_gate(None)
    blocked = {**passing, "unresolved_required_scope_candidate_count": 1}
    assert not final_receipt_requires_alias_completeness_gate(blocked)
