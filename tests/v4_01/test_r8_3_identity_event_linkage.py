from __future__ import annotations

from pathlib import Path

from workbench_analysis.official_code_change_event_index import validate_index_coverage
from workbench_analysis.security_identity_event_discovery import discover_identity_events

ROOT = Path(__file__).resolve().parents[2]
SESSIONS = ["2024-01-02", "2024-01-03"]


def _identity(security_id: str, *, name: str = "", list_date: str = "2010-01-01") -> dict[str, str]:
    return {
        "security_id": security_id,
        "exchange": "SH",
        "board": "MAIN",
        "security_name": name,
        "list_date": list_date,
        "source_revision_id": "sha256:" + security_id.lower(),
    }


def _discover(**kwargs: object) -> dict[str, object]:
    return discover_identity_events(
        mode="HISTORICAL_BACKSCAN", session_dates=SESSIONS, **kwargs,
    )


def _coverage(exchange: str) -> dict[str, object]:
    return {
        "exchange": exchange,
        "window_start": "2023-07-04",
        "window_end": "2026-09-24",
        "coverage_complete": True,
        "query_or_index_method": "captured official exchange event archive",
        "source_revision": "sha256:" + exchange.lower(),
        "event_count": 0,
        "failed_query_count": 0,
        "unresolved_source_windows": [],
    }


def test_single_exit_three_unrelated_ipos_does_not_create_three_pairs() -> None:
    result = _discover(
        roster_snapshots=[
            {"trade_date": SESSIONS[0], "source_codes": ["SH.600001"]},
            {"trade_date": SESSIONS[1], "source_codes": ["SH.600002", "SH.600003", "SH.600004"]},
        ],
        identities={
            "SH.600001": _identity("SEC-A", name="Old Issuer"),
            "SH.600002": _identity("SEC-B", name="New Issuer B"),
            "SH.600003": _identity("SEC-C", name="New Issuer C"),
            "SH.600004": _identity("SEC-D", name="New Issuer D"),
        },
    )
    assert result["candidate_count"] == 0
    assert result["boundary_event_counts"] == {"SECURITY_ENTRY": 3, "SECURITY_EXIT": 1}


def test_multiple_exit_entry_same_day_has_no_cartesian_product() -> None:
    result = _discover(
        roster_snapshots=[
            {"trade_date": SESSIONS[0], "source_codes": ["SH.600001", "SH.600002"]},
            {"trade_date": SESSIONS[1], "source_codes": ["SH.600003", "SH.600004", "SH.600005"]},
        ],
        identities={key: _identity(f"SEC-{key[-1]}", name=f"Issuer {key[-1]}") for key in (
            "SH.600001", "SH.600002", "SH.600003", "SH.600004", "SH.600005"
        )},
    )
    assert result["candidate_count"] == 0
    assert result["boundary_event_count"] == 5


def test_roster_boundary_without_link_signal_remains_atomic_event() -> None:
    result = _discover(
        roster_snapshots=[
            {"trade_date": SESSIONS[0], "source_codes": ["SZ.000001"]},
            {"trade_date": SESSIONS[1], "source_codes": ["SZ.000002"]},
        ],
        identities={"SZ.000001": _identity("SEC-A", name="Old"),
                    "SZ.000002": _identity("SEC-B", name="New")},
    )
    assert result["candidate_count"] == 0
    assert {event["event_type"] for event in result["boundary_events"]} == {"SECURITY_EXIT", "SECURITY_ENTRY"}
    assert all(not event["linked_to_relation_candidate"] for event in result["boundary_events"])


def test_lifecycle_boundary_without_link_signal_remains_atomic_event() -> None:
    old = {"source_security_key": "SH.600001", **_identity("SEC-A", name="Old"),
           "effective_to": "2024-01-02", "delist_date": "2024-01-02"}
    new = {"source_security_key": "SH.600002", **_identity("SEC-B", name="New"),
           "effective_from": "2024-01-03", "list_date": "2024-01-03"}
    result = _discover(lifecycle_records=[old, new], identities={"SH.600001": old, "SH.600002": new})
    assert result["candidate_count"] == 0
    assert {event["event_type"] for event in result["boundary_events"]} == {"LISTING_END", "LISTING_START"}


def test_official_code_change_links_nonoverlap_symbols() -> None:
    digest = "a" * 64
    result = _discover(
        official_events=[{
            "old_source_security_key": "SH.600001", "new_source_security_key": "SH.600002",
            "effective_date": "2024-01-03", "entity_relation": "SAME_ENTITY",
            "canonical_security_id": "SEC-A", "evidence_class": "OFFICIAL_CODE_CHANGE_NOTICE",
            "source_ref": "https://exchange.example/change", "source_capture_path": "evidence/change.pdf",
            "source_capture_sha256": digest, "observed_at": "2024-01-03T00:00:00+00:00",
            "system_available_at": "2024-01-03T00:00:00+00:00",
        }],
        identities={"SH.600001": _identity("SEC-A"), "SH.600002": _identity("SEC-A")},
        verified_evidence_digests={digest},
    )
    assert result["candidate_count"] == 1
    assert result["events"][0]["resolution_status"] == "CONFIRMED_SAME_ENTITY_CODE_CHANGE"


def test_same_issuer_id_creates_candidate_but_does_not_confirm_same() -> None:
    old = {"source_security_key": "SH.600001", **_identity("SEC-A", name="Old"),
           "effective_to": "2024-01-02", "issuer_id": "ISSUER-1"}
    new = {"source_security_key": "SH.600002", **_identity("SEC-B", name="New"),
           "effective_from": "2024-01-03", "issuer_id": "ISSUER-1"}
    result = _discover(lifecycle_records=[old, new], identities={"SH.600001": old, "SH.600002": new})
    assert result["candidate_count"] == 1
    assert "VERSIONED_SAME_ISSUER_ID" in result["events"][0]["candidate_signals"]
    assert result["events"][0]["resolution_status"] == "UNRESOLVED"


def test_same_company_entity_id_creates_candidate_only() -> None:
    old = {"source_security_key": "SH.600001", **_identity("SEC-A", name="Old"),
           "effective_to": "2024-01-02", "company_entity_id": "ENTITY-1"}
    new = {"source_security_key": "SH.600002", **_identity("SEC-B", name="New"),
           "effective_from": "2024-01-03", "company_entity_id": "ENTITY-1"}
    result = _discover(lifecycle_records=[old, new], identities={"SH.600001": old, "SH.600002": new})
    assert result["candidate_count"] == 1
    assert "VERSIONED_SAME_COMPANY_ENTITY_ID" in result["events"][0]["candidate_signals"]
    assert result["events"][0]["resolution_status"] == "UNRESOLVED"


def test_same_normalized_name_creates_candidate_but_does_not_confirm_same() -> None:
    result = _discover(
        roster_snapshots=[
            {"trade_date": SESSIONS[0], "source_codes": ["SH.600001"]},
            {"trade_date": SESSIONS[1], "source_codes": ["SH.600002"]},
        ],
        identities={"SH.600001": _identity("SEC-A", name="Same Company"),
                    "SH.600002": _identity("SEC-B", name=" same-company ")},
    )
    assert result["candidate_count"] == 1
    assert "WEAK_NAME_CONTINUITY" in result["events"][0]["candidate_signals"]
    assert result["events"][0]["resolution_status"] == "UNRESOLVED"


def test_different_listing_dates_never_confirm_distinct_alone() -> None:
    result = _discover(identities={
        "SH.600001": _identity("SEC-A", name="Issuer A", list_date="2010-01-01"),
        "SH.600002": _identity("SEC-B", name="Issuer B", list_date="2020-01-01"),
    })
    assert result["candidate_count"] == 0
    assert result["status"] == "PASS"


def test_official_distinct_issuer_evidence_confirms_distinct() -> None:
    digest = "b" * 64
    proof = {
        "source_security_keys": ["SH.600001", "SH.600002"],
        "security_ids": ["SEC-A", "SEC-B"], "issuer_ids": ["ISS-A", "ISS-B"],
        "entity_relation": "DISTINCT_ENTITY", "evidence_class": "OFFICIAL_DISTINCT_ISSUER_IDENTITY",
        "effective_date": "2024-01-03", "source_ref": "https://exchange.example/register",
        "source_capture_path": "evidence/register.json", "source_capture_sha256": digest,
        "observed_at": "2024-01-03T00:00:00+00:00", "system_available_at": "2024-01-03T00:00:00+00:00",
    }
    result = _discover(
        identity_relation_evidence=[proof], verified_evidence_digests={digest},
        identities={"SH.600001": _identity("SEC-A"), "SH.600002": _identity("SEC-B")},
    )
    assert result["events"][0]["resolution_status"] == "CONFIRMED_DISTINCT_ENTITY"


def test_symbol_reuse_disjoint_lifecycle_is_candidate() -> None:
    result = _discover(
        source_identity_assignments={"SH.600001": [
            {**_identity("SEC-A"), "effective_to": "2024-01-02"},
            {**_identity("SEC-B"), "effective_from": "2024-01-03"},
        ]},
        identities={"SH.600001": _identity("SEC-B")},
    )
    assert result["candidate_count"] == 1
    assert "SOURCE_SYMBOL_REASSIGNMENT_OR_CODE_REUSE_CANDIDATE" in result["events"][0]["candidate_signals"]
    assert any(event["event_type"] == "SYMBOL_REASSIGNMENT" for event in result["boundary_events"])
    assert result["events"][0]["resolution_status"] == "UNRESOLVED"


def test_official_event_index_coverage_is_required() -> None:
    receipt = validate_index_coverage(coverage_records=[], events=[])
    assert receipt["coverage_status"] == "BLOCKED"
    assert receipt["event_index_completeness_pass"] is False


def test_complete_official_event_index_coverage_passes() -> None:
    rows = [_coverage(exchange) for exchange in ("SH_MAIN", "SZ_MAIN", "CHINEXT", "STAR")]
    receipt = validate_index_coverage(coverage_records=rows, events=[])
    assert receipt["coverage_status"] == "PASS"
    assert receipt["event_index_completeness_pass"] is True


def test_missing_exchange_event_index_blocks_completeness() -> None:
    rows = [_coverage(exchange) for exchange in ("SH_MAIN", "SZ_MAIN", "CHINEXT")]
    receipt = validate_index_coverage(coverage_records=rows, events=[])
    assert receipt["coverage_status"] == "BLOCKED"
    assert any(row["exchange"] == "STAR" for row in receipt["unresolved_source_windows"])


def test_known_300114_302132_fixture_passes() -> None:
    from scripts.v4_01_identity_event_discovery_r8_1 import (
        ALIAS_FACTS, IDENTITY_R5, digest, read_json, read_jsonl,
    )

    aliases = read_jsonl(ALIAS_FACTS)
    digest_value = str(aliases[0]["evidence_hash"])
    identity_rows = read_json(IDENTITY_R5)["records"]
    identities = {row["source_security_key"]: row for row in identity_rows}
    result = discover_identity_events(
        mode="HISTORICAL_BACKSCAN", session_dates=["2025-02-14", "2025-02-17"],
        identities=identities, required_scope_source_keys=["SZ.300114", "SZ.302132"],
        alias_facts=aliases, verified_evidence_digests={digest_value},
    )
    pair = next(event for event in result["events"]
                if event["source_keys"] == ["SZ.300114", "SZ.302132"])
    assert pair["resolution_status"] == "CONFIRMED_SAME_ENTITY_CODE_CHANGE"
    assert digest(ALIAS_FACTS)


def test_no_specific_security_literals_in_generic_linkage_runtime() -> None:
    source = (ROOT / "src/workbench_analysis/security_identity_event_discovery.py").read_text("utf-8")
    assert "300114" not in source and "302132" not in source


def test_incomplete_coverage_window_blocks_even_with_all_exchange_rows() -> None:
    rows = [_coverage(exchange) for exchange in ("SH_MAIN", "SZ_MAIN", "CHINEXT", "STAR")]
    rows[2]["window_start"] = "2024-01-01"
    receipt = validate_index_coverage(coverage_records=rows, events=[])
    assert receipt["coverage_status"] == "BLOCKED"
    assert any(row["exchange"] == "CHINEXT" for row in receipt["unresolved_source_windows"])
