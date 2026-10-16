from datetime import date, datetime, timezone, timedelta

import pytest

from workbench_db.v4_source_manifest import (
    SourceManifestError, canonical_source_rows, source_manifest_digest,
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
    assert baseline == "5aae36d0bef1f5df5200bc9fe549be5c6300ae2cfc095009f59fb71751486c33"
    assert baseline == source_manifest_digest([second, first])
    assert baseline == source_manifest_digest([first, second])
    assert source_manifest_digest([first]) == "6b4cef3a9a1fe2ad846d878ebb1714e9960daa7abbda2765010ed2a470506ae8"
    assert source_manifest_digest([row(observed_at=datetime(2026, 10, 15, 7, 6, tzinfo=timezone(timedelta(hours=0))))]) == source_manifest_digest([row()])
    assert source_manifest_digest([row(logical_fact_id="tdx:changed")]) == "65f2f4a0fd4f997bfa552b4143225091e36179e98e8d8f0670bbcf9d8fa5b4dd"
    assert source_manifest_digest([row(logical_fact_id="tdx:changed")]) != source_manifest_digest([row()])
    assert len(baseline) == 64


def test_manifest_requires_complete_unique_and_typed_source_identity():
    with pytest.raises(SourceManifestError, match="SOURCE_MANIFEST_SOURCE_KEY_INVALID"):
        canonical_source_rows([row(), row()])
    with pytest.raises(SourceManifestError, match="SOURCE_MANIFEST_DIGEST_INVALID"):
        canonical_source_rows([row(digest="A" * 64)])
    with pytest.raises(SourceManifestError, match="SOURCE_MANIFEST_TIMESTAMP_MUST_BE_AWARE"):
        canonical_source_rows([row(ingested_at=datetime(2026, 10, 15, 7, 7))])
