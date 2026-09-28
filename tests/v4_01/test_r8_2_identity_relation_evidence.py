from __future__ import annotations

from pathlib import Path

from workbench_analysis.security_identity_event_discovery import discover_identity_events

ROOT = Path(__file__).resolve().parents[2]
SESSIONS = ["2024-01-02", "2024-01-03"]


def _identity(security_id: str, list_date: str) -> dict[str, str]:
    return {
        "security_id": security_id,
        "exchange": "SH",
        "board": "MAIN",
        "list_date": list_date,
        "source_revision_id": "sha256:" + security_id.lower(),
    }


def _rosters() -> list[dict[str, object]]:
    return [
        {"trade_date": SESSIONS[0], "source_codes": ["SH.600001"]},
        {"trade_date": SESSIONS[1], "source_codes": ["SH.600002"]},
    ]


def _run(*, identities: dict[str, dict[str, str]], **kwargs: object) -> dict[str, object]:
    return discover_identity_events(
        mode="HISTORICAL_BACKSCAN", session_dates=SESSIONS, roster_snapshots=_rosters(),
        identities=identities, **kwargs,
    )


def test_different_listing_dates_do_not_confirm_distinct_without_identity_evidence() -> None:
    result = _run(identities={
        "SH.600001": _identity("SEC-A", "2010-01-01"),
        "SH.600002": _identity("SEC-B", "2020-01-01"),
    })
    assert result["candidate_count"] == 0
    assert result["status"] == "PASS"


def test_versioned_listing_anchor_alone_is_weak_evidence() -> None:
    result = discover_identity_events(
        mode="HISTORICAL_BACKSCAN", session_dates=SESSIONS,
        source_identity_assignments={"SH.600001": [
            {**_identity("SEC-A", "2010-01-01"), "effective_to": "2020-01-02"},
            {**_identity("SEC-B", "2020-01-03"), "effective_from": "2020-01-03"},
        ]},
        identities={"SH.600001": _identity("SEC-B", "2020-01-03")},
    )
    assert result["events"][0]["resolution_status"] == "UNRESOLVED"


def test_official_distinct_entity_evidence_confirms_distinct() -> None:
    digest = "a" * 64
    proof = {
        "source_security_keys": ["SH.600001", "SH.600002"],
        "security_ids": ["SEC-A", "SEC-B"], "issuer_ids": ["ISS-A", "ISS-B"],
        "entity_relation": "DISTINCT_ENTITY", "evidence_class": "OFFICIAL_DISTINCT_ISSUER_IDENTITY",
        "effective_date": "2024-01-03", "source_ref": "https://example.test/register",
        "source_capture_path": "evidence/register.json", "source_capture_sha256": digest,
        "observed_at": "2024-01-03T00:00:00+00:00", "system_available_at": "2024-01-03T00:00:00+00:00",
    }
    result = _run(
        identities={"SH.600001": _identity("SEC-A", "2010-01-01"),
                    "SH.600002": _identity("SEC-B", "2020-01-01")},
        identity_relation_evidence=[proof], verified_evidence_digests={digest},
    )
    assert result["events"][0]["resolution_status"] == "CONFIRMED_DISTINCT_ENTITY"


def test_official_same_entity_code_change_confirms_same() -> None:
    digest = "b" * 64
    proof = {
        "source_security_keys": ["SH.600001", "SH.600002"], "canonical_security_id": "SEC-A",
        "entity_relation": "SAME_ENTITY", "evidence_class": "OFFICIAL_CODE_CHANGE_NOTICE",
        "effective_date": "2024-01-03", "source_ref": "https://example.test/change",
        "source_capture_path": "evidence/change.pdf", "source_capture_sha256": digest,
        "observed_at": "2024-01-03T00:00:00+00:00", "system_available_at": "2024-01-03T00:00:00+00:00",
    }
    result = _run(
        identities={"SH.600001": _identity("SEC-A", "2010-01-01"),
                    "SH.600002": _identity("SEC-A", "2020-01-01")},
        identity_relation_evidence=[proof], verified_evidence_digests={digest},
    )
    assert result["events"][0]["resolution_status"] == "CONFIRMED_SAME_ENTITY_CODE_CHANGE"


def test_versioned_alias_revision_must_bind_the_verified_capture_digest() -> None:
    digest = "c" * 64
    fact_fields = {
        "contract_id": "DATED_SECURITY_ALIAS_V1", "security_id": "SEC-A",
        "effective_to": None, "evidence_hash": digest,
        "evidence_ref": "https://example.test/change", "evidence_capture_path": "evidence/change.pdf",
        "source_revision": "sha256:" + "f" * 64,
        "observed_at": "2024-01-03T00:00:00+00:00", "system_available_at": "2024-01-03T00:00:00+00:00",
    }
    aliases = [
        {**fact_fields, "source_security_key": "SH.600001", "effective_from": "2010-01-01",
         "effective_to": "2024-01-02", "alias_role": "PREDECESSOR"},
        {**fact_fields, "source_security_key": "SH.600002", "effective_from": "2024-01-03",
         "alias_role": "CURRENT"},
    ]
    result = _run(
        identities={"SH.600001": _identity("SEC-A", "2010-01-01"),
                    "SH.600002": _identity("SEC-A", "2020-01-01")},
        alias_facts=aliases, verified_evidence_digests={digest},
    )
    assert result["events"][0]["resolution_status"] == "UNRESOLVED"


def test_nonoverlap_transition_without_identity_evidence_remains_unresolved() -> None:
    result = _run(identities={
        "SH.600001": {**_identity("SEC-A", "2010-01-01"), "security_name": "Same"},
        "SH.600002": {**_identity("SEC-B", "2020-01-01"), "security_name": "Same"},
    })
    assert result["events"][0]["resolution_status"] == "UNRESOLVED"
    assert "WEAK_NAME_CONTINUITY" in result["events"][0]["candidate_signals"]


def test_required_scope_unresolved_blocks_gate() -> None:
    result = _run(identities={
        "SH.600001": {**_identity("SEC-A", "2010-01-01"), "security_name": "Same Issuer"},
        "SH.600002": {**_identity("SEC-B", "2020-01-01"), "security_name": "Same Issuer"},
    })
    assert result["unresolved_required_scope_candidate_count"] == 1
    assert result["status"] == "BLOCKED"


def test_candidate_discovery_remains_generic_and_codes_are_fixture_only() -> None:
    source = (ROOT / "src/workbench_analysis/security_identity_event_discovery.py").read_text("utf-8")
    assert "300114" not in source and "302132" not in source
    assert "SZ.300114" in (ROOT / "tests/v4_01/test_r8_generic_alias_completeness.py").read_text("utf-8")
