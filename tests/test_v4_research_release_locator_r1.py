from __future__ import annotations

import pytest

from workbench_db.v4_research_release_pg_r1 import resolve_legacy_schema


class _Readback:
    def __init__(self, rows):
        self.rows = rows
        self.calls = []

    def execute(self, query, params):
        self.calls.append((query, params))
        return self

    def fetchall(self):
        return self.rows


def test_resolve_legacy_schema_requires_exact_locator_before_query():
    pg = _Readback([])

    with pytest.raises(ValueError, match="PG_CANDIDATE_RELEASE_ID_REQUIRED"):
        resolve_legacy_schema(pg, "v4_research_bad")

    assert pg.calls == []


def test_resolve_legacy_schema_requires_every_table_verified():
    pg = _Readback(
        [
            ("a" * 24, {"status": "VERIFIED"}),
            ("a" * 24, {"status": "PENDING"}),
        ]
    )

    with pytest.raises(ValueError, match="LEGACY_SCHEMA_RELEASE_MAPPING_NOT_VERIFIED"):
        resolve_legacy_schema(pg, "v4_research_" + "b" * 24)


def test_resolve_legacy_schema_returns_one_verified_canonical_release():
    release_id = "c" * 24
    pg = _Readback(
        [
            (release_id, {"status": "VERIFIED"}),
            (release_id, {"status": "VERIFIED"}),
        ]
    )

    assert resolve_legacy_schema(pg, "v4_research_" + "d" * 24) == release_id
