import hashlib
import json
from pathlib import Path
from datetime import date, datetime, timezone
from dataclasses import replace
import sys

import pytest

from workbench_db.v4_universe_pg_r1 import (
    UniversePgError, VerifiedUniverseReadback, build_universe_persistence_plan,
    is_verified_universe_readback, persist_universe_snapshot, read_universe_snapshot,
)

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_v4_daily_ingest_r6 import _frozen_inputs, _trust_test_authority, _signed_receipt
from workbench_db.v4_daily_source_ingest_r6 import build_source_ingest_plan
from test_v4_daily_core_result_r6 import _input as _core_input, _pg as _core_pg


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
        readback_contract_id="V4_UNIVERSE_PG_READBACK_R2", readback_contract_version="1.0.0",
        publication_id="p", publication_revision=1, trade_date="2026-10-16",
        source_manifest_sha256="a"*64, source_package_id="pkg", source_package_sha256="a"*64,
        source_fact_sha256="a"*64, logical_fact_id="fact", fact_digest="b"*64,
        acceptance_receipt_id="receipt", acceptance_receipt_sha256="c"*64,
        acceptance_authority_id="TEST_ONLY", universe_id="u",
        universe_contract_id="V4_MARKET_UNIVERSE_COMPLETENESS_R1", universe_contract_version="1.0.0",
        universe_sha256="b"*64, raw_artifact_sha256="c"*64, expected_count=1,
        core_count=1, coverage_ratio=1.0, reconciliation_sha256="d"*64, readback_receipt_sha256="e"*64,
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


def test_signed_source_to_pg_shaped_universe_readback_emits_closed_receipt(tmp_path, monkeypatch):
    core_receipt, core_rows, source_manifest, producer_sha = _core_input()
    day, freeze, readiness, freeze_doc = _frozen_inputs(tmp_path, day="2026-10-15",
                                                        as_recorded=True, pit_eligible=True)
    private = _trust_test_authority(tmp_path, monkeypatch)
    diagnostic = build_source_ingest_plan(tmp_path, trade_date=day, source_freeze=freeze,
                                          source_readiness=readiness)
    receipt = _signed_receipt(diagnostic, private)
    accepted = build_source_ingest_plan(tmp_path, trade_date=day, source_freeze=freeze,
                                        source_readiness=readiness, acceptance_receipt=receipt)
    assert accepted["status"] == "ACCEPTED"
    universe_ref = freeze_doc["security_universe"]
    raw = (tmp_path / universe_ref["path"]).read_bytes()
    snapshot = json.loads(raw)
    universe_core_rows = [{"security_id": "SH.600000"}]
    publication_id = "pub-20261016-r1"
    plan = build_universe_persistence_plan(
        publication_id=publication_id, publication_revision=1, trade_date=day,
        source_manifest_sha256=source_manifest, accepted_source_package_plan=accepted,
        raw_snapshot_bytes=raw, snapshot=snapshot, core_rows=universe_core_rows,
    )
    fact = next(row for row in accepted["source_facts"] if row["source_key"] == "security_universe")
    manifest = accepted["package_manifest"]
    header = (
        date.fromisoformat(day), source_manifest, accepted["package_id"], plan["acceptance_receipt_id"],
        plan["acceptance_receipt_sha256"], plan["acceptance_authority_id"], plan["source_fact_sha256"],
        plan["logical_fact_id"], plan["fact_digest"], plan["raw_artifact_sha256"], plan["universe_id"],
        plan["contract_id"], plan["contract_version"], plan["universe_sha256"], plan["exchange_scope"],
        plan["expected_count"], plan["core_count"], plan["coverage_ratio"], plan["reconciliation_sha256"],
        plan["category_counts"], plan["persistence_identity_sha256"], "PASS",
    )
    snapshot_rows = [tuple(row[k] for k in ("security_id", "asset_class", "share_class", "exchange", "status", "source_id"))
                     for row in plan["snapshot_rows"]]
    reconciliation_rows = [tuple(row[k] for k in ("security_id", "source_present", "core_present",
        "expected_in_denominator", "category", "asset_class", "share_class", "exchange", "status", "source_id"))
        for row in plan["reconciliation_rows"]]
    package_fact = (accepted["package_id"], "security_universe", fact["logical_fact_id"], fact["fact_digest"],
        fact["source_fact_sha256"], fact["record_locator"], accepted["package_sha256"],
        "ACCEPTED_SOURCE_PACKAGE", manifest, plan["acceptance_receipt_id"])

    class Result:
        def __init__(self, one=None, all_rows=None): self.one, self.all_rows = one, all_rows or []
        def fetchone(self): return self.one
        def fetchall(self): return self.all_rows

    class Pg:
        def execute(self, query, _params=None):
            if query == "SHOW transaction_isolation": return Result(("repeatable read",))
            if query == "SHOW transaction_read_only": return Result(("on",))
            if "SELECT r.rolsuper" in query:
                return Result((False, False, False, False, False, True, False, False, False, False))
            if "FROM v4.market_universe_snapshots" in query: return Result(header)
            if "FROM v4.market_universe_snapshot_rows" in query: return Result(all_rows=snapshot_rows)
            if "FROM v4.market_universe_reconciliation_rows" in query: return Result(all_rows=reconciliation_rows)
            if "SELECT trade_date,revision_no,source_manifest_sha256 FROM v4.publications" in query:
                return Result((date.fromisoformat(day), 1, source_manifest))
            if "FROM v4.source_package_facts f JOIN v4.source_packages" in query: return Result(package_fact)
            if "publication_consumed_sources cs" in query: return Result((1,))
            raise AssertionError("unexpected PG-shaped query: " + query)

    proof = read_universe_snapshot(Pg(), publication_id=publication_id, publication_revision=1,
                                   trade_date=day, source_manifest_sha256=source_manifest,
                                   core_rows=universe_core_rows)
    assert is_verified_universe_readback(proof)
    assert proof.acceptance_receipt_sha256 == plan["acceptance_receipt_sha256"]
    assert proof.acceptance_authority_id == "TEST_AUTHORITY_ONLY"
    assert proof.universe_contract_id == plan["contract_id"]
    for field, value in (("acceptance_receipt_sha256", "0" * 64), ("trade_date", "2026-10-16"),
                         ("source_package_sha256", "1" * 64), ("reconciliation_sha256", "2" * 64)):
        assert not is_verified_universe_readback(replace(proof, **{field: value}))

    # Carry the actual typed Universe readback through Core, candidate, and Head planning.
    from workbench_db import v4_daily_core_result_r6 as core_module
    from workbench_db.v4_daily_core_result_r6 import DAILY_COMPLETENESS_CONTRACT, build_daily_core_result_plan, read_daily_core_result
    from workbench_db.v4_publication_candidate import build_publication_candidate, plan_publication_head_change
    from workbench_db.v4_source_manifest import source_manifest_digest
    from tests.test_v4_pg_publication_candidate import DATABASE_IDENTITY
    core_plan = build_daily_core_result_plan(
        publication_id=publication_id, publication_revision=1, trade_date=day,
        source_manifest_sha256=source_manifest, producer_contract_id="V4_OPERATIONAL_DAILY_OWNER_R1",
        producer_sha256=producer_sha, producer_receipt=core_receipt, rows=core_rows,
        completeness_contract=DAILY_COMPLETENESS_CONTRACT,
    )
    monkeypatch.setattr(core_module, "R3_SOURCE_EFFECTIVE_DATE", date.fromisoformat(day))
    # Keep the pre-existing Core fixture's TDX contract rows while exercising
    # the actual Universe reader on the same PG-shaped connection.
    monkeypatch.setattr(core_module, "_read_consumed_source_proofs",
        lambda *_args, **_kwargs: ([], core_receipt["source_artifact_bindings"]))
    core_pg = _core_pg(core_plan)
    universe_pg = Pg()
    class CombinedPg:
        def execute(self, query, params=None):
            if ("SELECT r.rolsuper" in query or "v4.market_universe_" in query
                    or "SELECT trade_date,revision_no,source_manifest_sha256 FROM v4.publications" in query
                    or "v4.source_package_facts f JOIN v4.source_packages" in query
                    or ("publication_consumed_sources cs" in query and "cs.source_key='security_universe'" in query)):
                return universe_pg.execute(query, params)
            return core_pg.execute(query, params)
    combined_pg = CombinedPg()
    combined_proof = read_universe_snapshot(combined_pg, publication_id=publication_id,
        publication_revision=1, trade_date=day, source_manifest_sha256=source_manifest,
        core_rows=[{k: v for k, v in row.items() if k != "row_sha256"} for row in core_rows])
    assert is_verified_universe_readback(combined_proof)
    verified_core = read_daily_core_result(CombinedPg(), publication_id=publication_id,
        publication_revision=1, trade_date=day, source_manifest_sha256=source_manifest)
    from workbench_db.v4_daily_core_result_r6 import is_verified_daily_core_result
    assert is_verified_daily_core_result(verified_core)
    assert verified_core.universe_completeness_status == "PASS"
    assert verified_core.universe_contract_id == proof.universe_contract_id
    assert verified_core.universe_sha256 == proof.universe_sha256
    assert verified_core.universe_readback_receipt_sha256 == proof.readback_receipt_sha256
    assert verified_core.publishable is True and verified_core.completeness_status == "PASS", (
        verified_core.completeness_status, verified_core.universe_completeness_status,
        verified_core.observed_completeness_status, verified_core.completeness_contract_id,
        verified_core.completeness_contract_version,
    )
    manifest_rows = [{
        "source_key": "tdx", "source_revision_id": "v4sr-tdx-r1", "digest": "d" * 64,
        "logical_fact_id": "daily-source:2026-10-15:tdx", "revision_no": 1,
        "revision_digest": "d" * 64, "effective_from": date(2026, 10, 15),
        "effective_to": date(2026, 10, 15),
        "provider_available_at": datetime(2026, 10, 15, 9, tzinfo=timezone.utc),
        "observed_at": datetime(2026, 10, 15, 10, tzinfo=timezone.utc),
        "ingested_at": datetime(2026, 10, 15, 10, 1, tzinfo=timezone.utc),
        "system_available_at": datetime(2026, 10, 15, 10, 1, tzinfo=timezone.utc),
        "tombstone": False, "source_package_id": "pkg-r1",
        "source_package_contract_version": "V4_DAILY_SOURCE_INGEST_R6/1.2.0",
        "source_package_sha256": "c" * 64,
        "source_package_page_observed_at": datetime(2026, 10, 15, 9, tzinfo=timezone.utc),
        "source_package_target_trade_date": date(2026, 10, 15),
        "source_package_parser_version": "V4_DAILY_SOURCE_INGEST_R6",
        "source_package_accepted_scope": "ACCEPTED_SOURCE_PACKAGE",
    }]
    assert source_manifest_digest(manifest_rows) == source_manifest
    candidate = build_publication_candidate(
        publication_id=publication_id, trade_date=day, revision_no=1,
        publication_lineage_id="lineage-20261016", model_namespace_id="v4-main", core_revision=1,
        source_manifest_sha256=source_manifest, source_manifest_rows=manifest_rows,
        source_manifest_contract_id="V4_PG_CONSUMED_SOURCE_MANIFEST_R2",
        computation_identity_sha256="b" * 64,
        expected_source_bindings={"tdx": {"source_revision_id": "v4sr-tdx-r1", "digest": "d" * 64}},
        observed_source_bindings={"tdx": {"source_revision_id": "v4sr-tdx-r1", "digest": "d" * 64}},
        database_identity=DATABASE_IDENTITY, module_results=[], state_head_id="state-r19",
        state_logical_digest="c" * 64, prior_session_gap_reason="INITIAL_BOUNDARY",
        verified_core_result=verified_core,
    )
    head_plan = plan_publication_head_change(candidate, None, verified_core_result=verified_core)
    assert head_plan["action"] == "INSERT_IF_ABSENT"
