from __future__ import annotations

from pathlib import Path

import pytest

from workbench_analysis.security_identity_event_discovery import discover_identity_events

ROOT = Path(__file__).resolve().parents[2]
SESSIONS = ["2024-01-02", "2024-01-03"]


def _identity(
    security_id: str,
    *,
    list_date: str = "2010-01-01",
    name: str = "Example",
    effective_from: str = "2010-01-01",
    effective_to: str | None = None,
) -> dict[str, object]:
    return {
        "security_id": security_id,
        "exchange": "SH",
        "board": "MAIN",
        "list_date": list_date,
        "security_name": name,
        "symbol_effective_from": effective_from,
        "symbol_effective_to": effective_to,
        "source_revision_id": "sha256:" + security_id.lower(),
    }


def _rosters(old: str = "SH.600001", new: str = "SH.600002") -> list[dict[str, object]]:
    return [
        {"trade_date": SESSIONS[0], "source_codes": [old]},
        {"trade_date": SESSIONS[1], "source_codes": [new]},
    ]


def _discover(**kwargs: object) -> dict[str, object]:
    return discover_identity_events(mode="HISTORICAL_BACKSCAN", session_dates=SESSIONS, **kwargs)


def test_non_overlapping_code_transition_without_linkage_remains_atomic() -> None:
    report = _discover(
        roster_snapshots=_rosters(),
        identities={"SH.600001": _identity("SEC-A", name="Old Company"),
                    "SH.600002": _identity("SEC-A", name="New Company")},
    )
    assert report["candidate_count"] == 0
    assert report["boundary_event_counts"] == {"SECURITY_ENTRY": 1, "SECURITY_EXIT": 1}
    assert report["unlinked_boundary_anomaly_count"] == 0


def test_roster_exit_entry_boundary_is_atomic_without_linkage_signal() -> None:
    report = _discover(
        roster_snapshots=_rosters("SZ.000001", "SZ.000002"),
        identities={"SZ.000001": {**_identity("SEC-A"), "exchange": "SZ"},
                    "SZ.000002": {**_identity("SEC-A"), "exchange": "SZ"}},
    )
    assert report["candidate_count"] == 1  # exact normalized name, candidate only
    assert report["signal_counts"]["WEAK_NAME_CONTINUITY"] == 1
    assert report["boundary_event_counts"] == {"SECURITY_ENTRY": 1, "SECURITY_EXIT": 1}
    assert "ROSTER_EXIT_ENTRY_ADJACENCY" not in report["signal_counts"]


def test_lifecycle_boundary_without_shared_bar_is_candidate() -> None:
    old = {"source_security_key": "SH.600001", **_identity("SEC-A", effective_to="2024-01-02")}
    new = {"source_security_key": "SH.600002", **_identity("SEC-B", effective_from="2024-01-03")}
    report = _discover(
        lifecycle_records=[old, new],
        identities={"SH.600001": old, "SH.600002": new},
    )
    assert report["signal_counts"]["WEAK_NAME_CONTINUITY"] == 1
    assert "LIFECYCLE_BOUNDARY_ADJACENCY" not in report["signal_counts"]
    assert report["candidate_count"] == 1


def test_overlapping_retrospective_alias_is_candidate() -> None:
    report = _discover(
        retrospective_bar_candidates=[{
            "source_keys": ["SH.600001", "SH.600002"],
            "security_ids": ["SEC-A", "SEC-B"],
            "shared_identical_raw_bar_sessions": 24,
        }],
        identities={"SH.600001": _identity("SEC-A"), "SH.600002": _identity("SEC-B")},
    )
    assert report["signal_counts"]["PERSISTENT_RETROSPECTIVE_BAR_ALIAS"] == 1
    assert report["events"][0]["resolution_status"] == "UNRESOLVED"


def test_existing_alias_fact_is_candidate_and_verified_fact_confirms_it() -> None:
    digest = "a" * 64
    facts = [
        {"contract_id": "DATED_SECURITY_ALIAS_V1", "security_id": "SEC-A", "source_security_key": "SH.600001", "effective_from": "2010-01-01",
         "effective_to": "2024-01-02", "alias_role": "PREDECESSOR", "evidence_hash": digest,
         "evidence_ref": "https://example.test/notice", "evidence_capture_path": "evidence/notice.pdf",
         "source_revision": "sha256:" + digest, "observed_at": "2024-01-01T00:00:00+00:00",
         "system_available_at": "2024-01-01T00:00:00+00:00"},
        {"contract_id": "DATED_SECURITY_ALIAS_V1", "security_id": "SEC-A", "source_security_key": "SH.600002", "effective_from": "2024-01-03",
         "effective_to": None, "alias_role": "CURRENT", "evidence_hash": digest,
         "evidence_ref": "https://example.test/notice", "evidence_capture_path": "evidence/notice.pdf",
         "source_revision": "sha256:" + digest, "observed_at": "2024-01-01T00:00:00+00:00",
         "system_available_at": "2024-01-01T00:00:00+00:00"},
    ]
    report = _discover(alias_facts=facts, verified_evidence_digests={digest},
                       identities={"SH.600001": _identity("SEC-OLD"),
                                   "SH.600002": _identity("SEC-A")})
    assert report["signal_counts"]["DATED_ALIAS_FACT"] == 1
    assert report["events"][0]["resolution_status"] == "CONFIRMED_SAME_ENTITY_CODE_CHANGE"
    assert report["events"][0]["resolved_security_id"] == "SEC-A"


def test_disjoint_lifecycle_and_listing_dates_remain_unresolved_without_relation_evidence() -> None:
    versions = [
        _identity("SEC-A", list_date="2010-01-01", effective_to="2020-01-02"),
        _identity("SEC-B", list_date="2020-01-03", effective_from="2020-01-03"),
    ]
    report = _discover(
        source_identity_assignments={"SH.600001": versions},
        identities={"SH.600001": versions[-1]},
    )
    assert report["signal_counts"]["SOURCE_SYMBOL_REASSIGNMENT_OR_CODE_REUSE_CANDIDATE"] == 1
    assert report["events"][0]["resolution_status"] == "UNRESOLVED"
    assert report["status"] == "BLOCKED"
    assert report["events"][0]["resolved_security_id"] is None


def test_weak_name_match_is_candidate_only_and_never_merges() -> None:
    left = _identity("SEC-A", name="Same Company", list_date="2010-01-01")
    right = _identity("SEC-B", name="Same Company", list_date="2010-01-01")
    report = _discover(
        roster_snapshots=_rosters(),
        identities={"SH.600001": left, "SH.600002": right},
    )
    event = report["events"][0]
    assert "WEAK_NAME_CONTINUITY" in event["candidate_signals"]
    assert event["resolution_status"] == "UNRESOLVED"
    assert event["resolved_security_id"] is None


def test_unresolved_candidate_fails_closed() -> None:
    report = _discover(
        roster_snapshots=_rosters(),
        identities={"SH.600001": _identity("SEC-A"), "SH.600002": _identity("SEC-A")},
    )
    assert report["status"] == "BLOCKED"
    assert report["unresolved_required_scope_candidate_count"] == 1
    assert report["fail_closed"]["weak_signal_can_merge_identity"] is False


def test_candidate_signal_union_deduplicates_the_same_event() -> None:
    digest = "b" * 64
    facts = [
        {"contract_id": "DATED_SECURITY_ALIAS_V1", "security_id": "SEC-A", "source_security_key": "SH.600001", "effective_from": "2010-01-01",
         "effective_to": "2024-01-02", "alias_role": "PREDECESSOR", "evidence_hash": digest,
         "evidence_ref": "https://example.test/notice", "evidence_capture_path": "evidence/notice.pdf",
         "source_revision": "sha256:" + digest, "observed_at": "2024-01-01T00:00:00+00:00",
         "system_available_at": "2024-01-01T00:00:00+00:00"},
        {"contract_id": "DATED_SECURITY_ALIAS_V1", "security_id": "SEC-A", "source_security_key": "SH.600002", "effective_from": "2024-01-03",
         "effective_to": None, "alias_role": "CURRENT", "evidence_hash": digest,
         "evidence_ref": "https://example.test/notice", "evidence_capture_path": "evidence/notice.pdf",
         "source_revision": "sha256:" + digest, "observed_at": "2024-01-01T00:00:00+00:00",
         "system_available_at": "2024-01-01T00:00:00+00:00"},
    ]
    official = [{"old_source_security_key": "SH.600001", "new_source_security_key": "SH.600002",
                 "effective_date": "2024-01-03", "entity_relation": "SAME_ENTITY",
                 "security_id": "SEC-A", "source_capture_sha256": digest}]
    identities = {"SH.600001": _identity("SEC-OLD"), "SH.600002": _identity("SEC-A")}
    report = _discover(roster_snapshots=_rosters(), alias_facts=facts, official_events=official,
                       verified_evidence_digests={digest}, identities=identities)
    assert report["candidate_count"] == 1
    assert set(report["events"][0]["candidate_signals"]) >= {
        "DATED_ALIAS_FACT", "OFFICIAL_CODE_CHANGE_EVENT"
    }


def test_no_specific_security_literals_in_discovery_logic() -> None:
    source = (ROOT / "src/workbench_analysis/security_identity_event_discovery.py").read_text("utf-8")
    assert "300114" not in source
    assert "302132" not in source


def test_known_transition_codes_are_fixture_data_only() -> None:
    source = (ROOT / "src/workbench_analysis/security_identity_event_discovery.py").read_text("utf-8")
    assert "300114" not in source and "302132" not in source
    fixture = (ROOT / "tests/v4_01/test_r8_generic_alias_completeness.py").read_text("utf-8")
    assert "SZ.300114" in fixture and "SZ.302132" in fixture


def test_different_listing_dates_alone_do_not_clear_required_scope() -> None:
    blocked = _discover(
        roster_snapshots=_rosters(),
        identities={"SH.600001": _identity("SEC-A"), "SH.600002": _identity("SEC-A")},
    )
    different_dates_only = _discover(
        roster_snapshots=_rosters(),
        identities={"SH.600001": _identity("SEC-A", list_date="2010-01-01"),
                    "SH.600002": _identity("SEC-B", list_date="2020-01-01")},
    )
    assert blocked["unresolved_required_scope_candidate_count"] == 1
    assert different_dates_only["unresolved_required_scope_candidate_count"] == 1
    assert different_dates_only["status"] == "BLOCKED"


def test_official_distinct_issuer_evidence_confirms_distinct_entities() -> None:
    digest = "c" * 64
    evidence = {
        "source_security_keys": ["SH.600001", "SH.600002"],
        "security_ids": ["SEC-A", "SEC-B"], "issuer_ids": ["ISS-A", "ISS-B"],
        "entity_relation": "DISTINCT_ENTITY", "evidence_class": "OFFICIAL_DISTINCT_ISSUER_IDENTITY",
        "effective_date": "2024-01-03", "source_ref": "https://example.test/issuer-register",
        "source_capture_path": "evidence/issuer-register.json", "source_capture_sha256": digest,
        "observed_at": "2024-01-03T00:00:00+00:00", "system_available_at": "2024-01-03T00:00:00+00:00",
    }
    report = _discover(
        roster_snapshots=_rosters(), identity_relation_evidence=[evidence],
        verified_evidence_digests={digest},
        identities={"SH.600001": _identity("SEC-A"), "SH.600002": _identity("SEC-B")},
    )
    assert report["events"][0]["resolution_status"] == "CONFIRMED_DISTINCT_ENTITY"
    assert report["unresolved_required_scope_candidate_count"] == 0


def test_official_code_change_notice_confirms_same_entity() -> None:
    digest = "d" * 64
    evidence = {
        "source_security_keys": ["SH.600001", "SH.600002"], "canonical_security_id": "SEC-A",
        "entity_relation": "SAME_ENTITY", "evidence_class": "OFFICIAL_CODE_CHANGE_NOTICE",
        "effective_date": "2024-01-03", "source_ref": "https://example.test/code-change",
        "source_capture_path": "evidence/code-change.pdf", "source_capture_sha256": digest,
        "observed_at": "2024-01-03T00:00:00+00:00", "system_available_at": "2024-01-03T00:00:00+00:00",
    }
    report = _discover(
        identity_relation_evidence=[evidence], verified_evidence_digests={digest},
        identities={"SH.600001": _identity("SEC-A"), "SH.600002": _identity("SEC-A")},
    )
    assert report["events"][0]["resolution_status"] == "CONFIRMED_SAME_ENTITY_CODE_CHANGE"
    assert report["events"][0]["resolved_security_id"] == "SEC-A"


def test_daily_incremental_rejects_non_session_target() -> None:
    with pytest.raises(ValueError, match="IDENTITY_EVENT_TARGET_NOT_OFFICIAL_SESSION"):
        discover_identity_events(
            mode="DAILY_INCREMENTAL", target_date="2024-01-04", session_dates=SESSIONS,
            identities={},
        )
