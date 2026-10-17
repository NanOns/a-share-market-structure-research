from datetime import date, datetime, timezone, timedelta

import pytest

from workbench_db.v4_source_manifest import (
    SourceManifestError, canonical_source_rows, source_manifest_digest,
    canonical_source_rows_r3, source_manifest_digest_r3,
)


def row(**changes):
    value = {
        "source_key": "tdx_daily", "source_revision_id": "source-r1",
        "digest": "a" * 64, "logical_fact_id": "tdx:2026-10-15",
        "revision_no": 1, "revision_digest": "a" * 64,
        "effective_from": date(2026, 10, 15), "effective_to": date(2026, 10, 15),
        "provider_available_at": datetime(2026, 10, 15, 7, 5, tzinfo=timezone.utc),
        "observed_at": datetime(2026, 10, 15, 7, 6, tzinfo=timezone.utc),
        "ingested_at": datetime(2026, 10, 15, 7, 7, tzinfo=timezone.utc),
        "system_available_at": datetime(2026, 10, 15, 7, 7, tzinfo=timezone.utc),
        "tombstone": False,
        "source_package_id": "pkg-20261015-r1",
        "source_package_contract_version": "V4_DAILY_CAPTURE_R1",
        "source_package_sha256": "c" * 64,
        "source_package_page_observed_at": datetime(2026, 10, 15, 7, 6, tzinfo=timezone.utc),
        "source_package_target_trade_date": date(2026, 10, 15),
        "source_package_parser_version": "parser-r1",
        "source_package_accepted_scope": "ACCEPTED_SOURCE_PACKAGE",
    }
    value.update(changes)
    return value


def test_manifest_vectors_are_stable_order_independent_and_single_field_sensitive():
    first = row()
    second = row(source_key="identity", source_revision_id="identity-r2",
                 logical_fact_id="identity:000001", revision_no=2,
                 digest="b" * 64, revision_digest="b" * 64,
                 effective_from=None, effective_to=None, tombstone=True)
    baseline = source_manifest_digest([first, second])
    assert baseline == "83d7acd0850fb5704fb7a1a399ef7b564abb418d8c9f06c07096aedfc6a491ee"
    assert baseline == source_manifest_digest([second, first])
    assert baseline == source_manifest_digest([first, second])
    assert source_manifest_digest([first]) == "0401f69c38bd225a5551656692063beec35e65490c4bad90467b398c6e86ea1c"
    assert source_manifest_digest([row(observed_at=datetime(2026, 10, 15, 7, 6, tzinfo=timezone(timedelta(hours=0))))]) == source_manifest_digest([row()])
    assert source_manifest_digest([row(logical_fact_id="tdx:changed")]) == "c834321359debf6871b32283b9bbde4e04f5fce436fc6b8db5ffee8b56257c08"
    assert source_manifest_digest([row(logical_fact_id="tdx:changed")]) != source_manifest_digest([row()])
    assert len(baseline) == 64


def test_manifest_requires_complete_unique_and_typed_source_identity():
    with pytest.raises(SourceManifestError, match="SOURCE_MANIFEST_SOURCE_KEY_INVALID"):
        canonical_source_rows([row(), row()])
    with pytest.raises(SourceManifestError, match="SOURCE_MANIFEST_DIGEST_INVALID"):
        canonical_source_rows([row(digest="A" * 64)])
    with pytest.raises(SourceManifestError, match="SOURCE_MANIFEST_TIMESTAMP_MUST_BE_AWARE"):
        canonical_source_rows([row(ingested_at=datetime(2026, 10, 15, 7, 7))])


def test_manifest_requires_accepted_package_binding_and_canonical_dates():
    with pytest.raises(SourceManifestError, match="SOURCE_MANIFEST_PACKAGE_AUTHORITY_INVALID"):
        canonical_source_rows([row(source_package_accepted_scope="DIAGNOSTIC_ONLY")])
    with pytest.raises(SourceManifestError, match="SOURCE_MANIFEST_PACKAGE_DIGEST_INVALID"):
        canonical_source_rows([row(source_package_sha256="not-a-sha")])
    with pytest.raises(SourceManifestError, match="SOURCE_MANIFEST_DATE_NONCANONICAL"):
        canonical_source_rows([row(effective_from="20261015")])
    with pytest.raises(SourceManifestError, match="SOURCE_MANIFEST_DATE_WINDOW_INVALID"):
        canonical_source_rows([row(effective_from="2026-10-16", effective_to="2026-10-15")])


def r3_row(**changes):
    value = row(
        source_package_acceptance_receipt_id="issuer-r1-20261015",
        source_package_as_recorded=True, source_package_pit_eligible=True,
        source_package_acceptance_proof_sha256="d" * 64,
        source_fact_digest="a" * 64, source_fact_sha256="b" * 64,
        source_fact_record_locator={"path":"security_master.json","record_count":5001},
        source_fact_record_count=5001,
        source_fact_acceptance_receipt_id="issuer-r1-20261015",
    )
    value.update(changes)
    return value


def test_r3_manifest_includes_the_exact_acceptance_and_fact_proof_readers_consume():
    material = canonical_source_rows_r3([r3_row()])[0]
    assert material["source_package_acceptance_receipt_id"] == "issuer-r1-20261015"
    assert material["source_package_as_recorded"] is True
    assert material["source_package_pit_eligible"] is True
    assert material["source_fact_digest"] == "a" * 64
    assert material["source_fact_sha256"] == "b" * 64
    assert material["source_fact_record_locator"]["record_count"] == 5001
    assert material["source_fact_record_count"] == 5001
    assert material["source_fact_acceptance_receipt_id"] == material["source_package_acceptance_receipt_id"]
    assert len(source_manifest_digest_r3([r3_row()])) == 64
    assert source_manifest_digest_r3([r3_row(source_fact_sha256="c" * 64)]) != source_manifest_digest_r3([r3_row()])


@pytest.mark.parametrize("change,code", [
    ({"source_package_as_recorded":False}, "SOURCE_MANIFEST_R3_ACCEPTANCE_PROOF_INVALID"),
    ({"source_package_pit_eligible":False}, "SOURCE_MANIFEST_R3_ACCEPTANCE_PROOF_INVALID"),
    ({"source_fact_acceptance_receipt_id":"other"}, "SOURCE_MANIFEST_R3_ACCEPTANCE_PROOF_INVALID"),
    ({"source_fact_record_count":-1}, "SOURCE_MANIFEST_R3_RECORD_COUNT_INVALID"),
    ({"source_fact_record_locator":[]}, "SOURCE_MANIFEST_R3_FACT_LOCATOR_INVALID"),
])
def test_r3_manifest_rejects_missing_or_conflicting_acceptance_fact_proof(change, code):
    with pytest.raises(SourceManifestError, match=code):
        canonical_source_rows_r3([r3_row(**change)])
