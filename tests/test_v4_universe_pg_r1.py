import hashlib
import json
from pathlib import Path

import pytest

from workbench_db.v4_universe_pg_r1 import (
    UniversePgError, VerifiedUniverseReadback, build_universe_persistence_plan,
    is_verified_universe_readback, persist_universe_snapshot, read_universe_snapshot,
)


class _Pg:
    def __init__(self, values):
        self.values = iter(values)

    def execute(self, *_args):
        class _Result:
            def __init__(self, value): self.value=value
            def fetchone(self): return (self.value,)
        return _Result(next(self.values))


def test_mapping_or_direct_dataclass_cannot_forge_universe_proof():
    fake = VerifiedUniverseReadback(
        publication_id="p", publication_revision=1, trade_date="2026-10-16",
        source_manifest_sha256="a"*64, source_package_id="pkg", universe_id="u",
        universe_sha256="b"*64, raw_artifact_sha256="c"*64, expected_count=1,
        core_count=1, reconciliation_sha256="d"*64, readback_receipt_sha256="e"*64,
        status="PASS", _proof=object(),
    )
    assert not is_verified_universe_readback(fake)
    assert not is_verified_universe_readback({"status":"PASS","universe_sha256":"b"*64})


def test_readback_requires_repeatable_read_and_read_only():
    pg = _Pg(["read committed", "on"])
    with pytest.raises(UniversePgError, match="REPEATABLE_READ_ONLY"):
        read_universe_snapshot(pg, publication_id="p", publication_revision=1,
                               trade_date="2026-10-16", source_manifest_sha256="a"*64, core_rows=[])


def test_readback_rejects_writable_transaction():
    pg = _Pg(["repeatable read", "off"])
    with pytest.raises(UniversePgError, match="REPEATABLE_READ_ONLY"):
        read_universe_snapshot(pg, publication_id="p", publication_revision=1,
                               trade_date="2026-10-16", source_manifest_sha256="a"*64, core_rows=[])


def test_persistence_does_not_accept_a_caller_fabricated_mapping():
    with pytest.raises(UniversePgError, match="PERSISTENCE_PLAN"):
        persist_universe_snapshot(object(), {"contract_id":"V4_MARKET_UNIVERSE_COMPLETENESS_R1","status":"PASS"})


def test_build_requires_an_independent_accepted_receipt_and_exact_raw_bytes():
    snapshot={"contract_id":"V4_MARKET_UNIVERSE_COMPLETENESS_R1","contract_version":"1.0.0",
        "trade_date":"2026-10-16","universe_id":"fixture","exchange_scope":["SSE","SZSE","BSE"],
        "securities":[],"universe_sha256":"0"*64}
    raw=json.dumps(snapshot,separators=(",",":"),sort_keys=True).encode()
    with pytest.raises(UniversePgError, match="INDEPENDENT_ACCEPTANCE_REQUIRED"):
        build_universe_persistence_plan(publication_id="p",publication_revision=1,
            trade_date="2026-10-16",source_manifest_sha256="a"*64,
            accepted_source_package_plan={"status":"ACCEPTED","trade_date":"2026-10-16",
                "package_id":"pkg","package_sha256":"b"*64,"package_manifest":{},
                "source_facts":[],"acceptance_receipt":None},raw_snapshot_bytes=raw,
            snapshot=snapshot,core_rows=[])


def test_migration_is_registered_as_unapplied_frontier_not_runtime_claim():
    root=Path(__file__).resolve().parents[1]
    migration=(root/"src/workbench_db/migrations/v4_postgres/042_market_universe_persistence_r1.sql").read_text()
    runner=(root/"scripts/apply_v4_phase0_schema.py").read_text()
    assert '"042_market_universe_persistence_r1.sql":"V4_MARKET_UNIVERSE_PERSISTENCE_R1"' in runner
    assert "CREATE TABLE v4.market_universe_snapshots" in migration
    assert "CREATE TABLE v4.market_universe_snapshot_rows" in migration
    assert "CREATE TABLE v4.market_universe_reconciliation_rows" in migration
    assert "accepted_publication_requires_universe" in migration
    assert "DROP TABLE" not in migration.upper()
