from contextlib import contextmanager
from datetime import date, datetime, timezone

import pytest

from workbench_db.v4_publication_candidate import (
    CandidatePlanError,
    build_publication_candidate,
    plan_publication_head_change,
)
from workbench_db.v4_publication_contract import CONTRACT_ID, effective_module_contract, required_module_keys
from workbench_db.v4_publication_reader import PgPublicationReader, PublicationReadError, reader_dsn
from workbench_service.v4_pg_current_adapter import ENDPOINT_MODULES, PgV4CurrentAdapter


DATABASE_IDENTITY = {"database": "market_research", "database_oid": 16384, "host": "127.0.0.1", "port": 5432}
DIGEST = "a" * 64
TARGET_DATE = date(2026, 10, 15)
ACCEPTED_AT = datetime(2026, 10, 15, 16, 0, tzinfo=timezone.utc)


def publication_row(**changes):
    row = {
        "publication_id": "pub-20261015-r1", "revision_no": 1, "trade_date": TARGET_DATE,
        "model_namespace_id": "v4-main", "status": "ACCEPTED", "accepted_at": ACCEPTED_AT,
        "core_revision": 1, "source_manifest_sha256": DIGEST,
        "computation_identity_sha256": "b" * 64, "publication_lineage_id": "lineage-20261015",
        "same_day_revision_parent_id": None, "prior_session_publication_id": None,
        "prior_session_state_head": None, "prior_session_state_logical_digest": None,
        "prior_session_gap_reason": "INITIAL_BOUNDARY", "state_head_id": "state-20261015-r1",
        "state_logical_digest": "c" * 64, "verified_state_digest": "c" * 64,
    }
    row.update(changes)
    return row


def binding_row(module, **changes):
    row = {
        "module_key": module, "module_contract_id": CONTRACT_ID,
        "database_identity": DATABASE_IDENTITY,
        "owner_schema": "v4_" + "a" * 56, "owner_relation": "owner_rows",
        "owner_version_token": f"{module}-owner-r1", "owner_trade_date": TARGET_DATE,
        "owner_contract_id": f"{module.upper()}_OWNER_R1", "result_digest": "d" * 64,
        "row_count": 1, "quality_status": "DEGRADED", "as_recorded": False,
        "pit_eligible": False,
    }
    row.update(changes)
    return row


def source_row(**changes):
    row = {
        "source_key": "tdx_daily", "source_revision_id": "src-r1", "digest": "e" * 64,
        "logical_fact_id": "tdx:2026-10-15", "revision_no": 1, "revision_digest": "e" * 64,
        "effective_from": TARGET_DATE, "effective_to": TARGET_DATE,
        "provider_available_at": datetime(2026, 10, 15, 15, 5, tzinfo=timezone.utc),
        "observed_at": datetime(2026, 10, 15, 15, 6, tzinfo=timezone.utc),
        "ingested_at": datetime(2026, 10, 15, 15, 7, tzinfo=timezone.utc),
        "system_available_at": datetime(2026, 10, 15, 15, 8, tzinfo=timezone.utc),
        "tombstone": False,
    }
    row.update(changes)
    return row


class Cursor:
    def __init__(self, one=None, all_rows=None):
        self.one = one
        self.all_rows = all_rows or []

    def fetchone(self):
        return self.one

    def fetchall(self):
        return self.all_rows


class FakeConnection:
    def __init__(self, *, head=None, bindings=None, sources=None, identity=None, role=None, missing_bindings=False, parent=None):
        self.head = head
        self.bindings = bindings if bindings is not None else [binding_row(module) for module in required_module_keys()]
        self.sources = sources if sources is not None else [source_row()]
        self.identity = identity or ("market_research", 16384, "127.0.0.1", 5432)
        self.role = role or ("v4_reader", False, False, False, False, False, False, False)
        self.missing_bindings = missing_bindings
        self.parent = parent
        self.statements = []

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def execute(self, statement, params=None):
        statement = str(statement)
        self.statements.append((statement, params))
        if statement.startswith("SET "):
            return Cursor()
        if "FROM v4.publication_heads" in statement:
            return Cursor(one=self.head)
        if "inet_server_addr()" in statement:
            return Cursor(one=self.identity)
        if "FROM pg_roles r" in statement:
            return Cursor(one=self.role)
        if "FROM v4.publications WHERE publication_id=%s" in statement:
            return Cursor(one=self.parent)
        if "FROM v4.publication_consumed_sources" in statement:
            return Cursor(all_rows=self.sources)
        if "FROM v4.publication_module_results" in statement:
            if self.missing_bindings:
                error = RuntimeError("relation missing")
                error.sqlstate = "42P01"
                raise error
            return Cursor(all_rows=self.bindings)
        raise AssertionError(f"unexpected SQL: {statement}")


def owner_readers():
    def resolve(pg, binding):
        return {
            "database_identity": binding["database_identity"],
            "owner_schema": binding["owner_schema"], "owner_relation": binding["owner_relation"],
            "owner_version_token": binding["owner_version_token"], "owner_trade_date": binding["owner_trade_date"],
            "owner_contract_id": binding["owner_contract_id"], "result_digest": binding["result_digest"],
            "row_count": binding["row_count"], "payload": [{"row": binding["module_key"]}],
        }
    return {module: resolve for module in required_module_keys()}


def reader_for(connection, **kwargs):
    @contextmanager
    def factory():
        with connection as pg:
            yield pg
    return PgPublicationReader(
        connection_factory=factory,
        expected_database_identity=DATABASE_IDENTITY,
        owner_readers=kwargs.pop("owner_readers", owner_readers()),
        **kwargs,
    )


def test_reader_dsn_never_falls_back_to_writer():
    with pytest.raises(PublicationReadError, match="PG_READ_ENV_UNAVAILABLE"):
        reader_dsn({"V4_NATIVE_PG_DSN": "writer-secret"})
    assert reader_dsn({"WORKBENCH_PG_DSN": "reader"}) == "reader"
    assert reader_dsn({"V4_NATIVE_PG_READER_DSN": "reader-role", "WORKBENCH_PG_DSN": "other"}) == "reader-role"


def test_contract_has_fixed_requiredness_for_all_current_entries():
    contract = effective_module_contract()
    assert contract["contract_id"] == CONTRACT_ID
    assert set(contract["modules"]) == set(ENDPOINT_MODULES.values())
    assert {row["requiredness"] for row in contract["modules"].values()} == {"REQUIRED"}
    assert all(row["quality_policy"] == "PRESERVE_OWNER_QUALITY_NO_PROMOTION" for row in contract["modules"].values())


def test_no_head_fails_closed_without_owner_or_source_query():
    connection = FakeConnection()
    reader = reader_for(connection)
    with pytest.raises(PublicationReadError, match="NO_ACCEPTED_PUBLICATION"):
        reader.read_context(trade_date="2026-10-15", model_namespace_id="v4-main")
    assert not any("publication_module_results" in sql or "publication_consumed_sources" in sql for sql, _ in connection.statements)


def test_reader_returns_final_schema_identity_and_preserves_owner_quality():
    connection = FakeConnection(head=publication_row())
    result = reader_for(connection).read_context(trade_date="2026-10-15", model_namespace_id="v4-main")
    assert result["candidate_only"] is True and result["readback_complete"] is True
    assert result["publication_id"] == "pub-20261015-r1" and result["revision_no"] == 1
    assert result["module_results"]["entity"]["quality_status"] == "DEGRADED"
    assert result["module_results"]["entity"]["as_recorded"] is False
    assert result["module_results"]["entity"]["pit_eligible"] is False
    assert result["state_head_id"] == "state-20261015-r1"
    assert result["source_bindings"][0]["source_revision_id"] == "src-r1"
    assert result["source_manifest_rehash_status"].startswith("NOT_PROVEN")
    assert len(result["module_results_digest"]) == 64
    assert result["context_token"].startswith("pg-candidate-")
    head_sql = next(sql for sql, _ in connection.statements if "FROM v4.publication_heads" in sql)
    assert "h.revision" not in head_sql and "p.revision," not in head_sql
    assert "p.revision_no" in head_sql and "state_heads" in head_sql
    source_sql = next(sql for sql, _ in connection.statements if "FROM v4.publication_consumed_sources" in sql)
    assert "ORDER BY convert_to(cs.source_key, 'UTF8')" in source_sql


def test_metadata_only_is_marked_unverified_and_is_not_the_default():
    connection = FakeConnection(head=publication_row())
    result = reader_for(connection).read_context(
        trade_date="2026-10-15", model_namespace_id="v4-main", resolve_payloads=False,
    )
    assert result["read_mode"] == "METADATA_ONLY_UNVERIFIED"
    assert result["readback_complete"] is False
    assert "module_payloads" not in result


def test_missing_payload_resolver_fails_closed_for_every_required_page():
    with pytest.raises(PublicationReadError, match="MODULE_OWNER_READER_UNAVAILABLE"):
        reader_for(FakeConnection(head=publication_row()), owner_readers={}).read_context(
            trade_date="2026-10-15", model_namespace_id="v4-main",
        )


def test_shared_context_token_pins_publication_and_source_module_snapshot():
    first = FakeConnection(head=publication_row())
    context = reader_for(first).read_context(trade_date="2026-10-15", model_namespace_id="v4-main")
    repeated = reader_for(FakeConnection(head=publication_row())).read_context(
        trade_date="2026-10-15", model_namespace_id="v4-main",
        expected_publication=(context["publication_id"], context["revision_no"]),
        expected_context_token=context["context_token"],
    )
    assert repeated["context_token"] == context["context_token"]
    changed = [binding_row(module) for module in required_module_keys()]
    changed[0] = binding_row(required_module_keys()[0], result_digest="f" * 64)
    with pytest.raises(PublicationReadError, match="STALE_CONTEXT_REQUIRES_REFRESH"):
        reader_for(FakeConnection(head=publication_row(), bindings=changed)).read_context(
            trade_date="2026-10-15", model_namespace_id="v4-main",
            expected_publication=(context["publication_id"], context["revision_no"]),
            expected_context_token=context["context_token"],
        )


def test_source_digest_clock_or_t0_corruption_blocks_context():
    cases = [
        (source_row(revision_digest="f" * 64), "PUBLICATION_SOURCE_DIGEST_MISMATCH"),
        (source_row(system_available_at=datetime(2026, 10, 16, tzinfo=timezone.utc)), "PUBLICATION_SOURCE_AVAILABLE_AFTER_ACCEPTANCE"),
        (source_row(effective_from=date(2026, 10, 16)), "PUBLICATION_SOURCE_OUTSIDE_T0_WINDOW"),
        (source_row(tombstone=True), "PUBLICATION_SOURCE_TOMBSTONED"),
    ]
    for source, code in cases:
        with pytest.raises(PublicationReadError, match=code):
            reader_for(FakeConnection(head=publication_row(), sources=[source])).read_context(
                trade_date="2026-10-15", model_namespace_id="v4-main",
            )


def test_wrong_owner_t0_module_contract_or_missing_module_fails_closed():
    bindings = [binding_row(module) for module in required_module_keys()]
    with pytest.raises(PublicationReadError, match="OWNER_T0_MISMATCH"):
        reader_for(FakeConnection(head=publication_row(), bindings=[binding_row("summary", owner_trade_date=date(2026, 10, 14)), *bindings[1:]])).read_context(
            trade_date="2026-10-15", model_namespace_id="v4-main",
        )
    wrong_contract = [binding_row(module) for module in required_module_keys()]
    wrong_contract[0] = binding_row(required_module_keys()[0], module_contract_id="UNVERSIONED_OPTIONAL")
    with pytest.raises(PublicationReadError, match="MODULE_CONTRACT_ID_MISMATCH"):
        reader_for(FakeConnection(head=publication_row(), bindings=wrong_contract)).read_context(
            trade_date="2026-10-15", model_namespace_id="v4-main",
        )
    with pytest.raises(PublicationReadError, match="MODULE_RESULT_UNBOUND"):
        reader_for(FakeConnection(head=publication_row(), bindings=bindings[:-1])).read_context(
            trade_date="2026-10-15", model_namespace_id="v4-main",
        )


def test_head_state_and_same_day_parent_identity_fail_closed():
    with pytest.raises(PublicationReadError, match="PUBLICATION_STATE_HEAD_INVALID"):
        reader_for(FakeConnection(head=publication_row(verified_state_digest="f" * 64))).read_context(
            trade_date="2026-10-15", model_namespace_id="v4-main",
        )
    next_pub = publication_row(revision_no=2, same_day_revision_parent_id="pub-20261015-r1")
    with pytest.raises(PublicationReadError, match="SAME_DAY_REVISION_PARENT_INVALID"):
        reader_for(FakeConnection(head=next_pub, parent={
            "publication_id": "pub-20261015-r1", "model_namespace_id": "v4-main",
            "trade_date": TARGET_DATE, "publication_lineage_id": "wrong-lineage", "revision_no": 1,
        })).read_context(trade_date="2026-10-15", model_namespace_id="v4-main")


def test_reader_role_write_privilege_blocks_even_read_only_transaction():
    with pytest.raises(PublicationReadError, match="PG_READER_ROLE_HAS_WRITE_PRIVILEGES"):
        reader_for(FakeConnection(head=publication_row(), role=("owner", False, False, False, True, False, False, False))).read_context(
            trade_date="2026-10-15", model_namespace_id="v4-main",
        )


def test_database_identity_and_binding_schema_must_match():
    with pytest.raises(PublicationReadError, match="PG_DATABASE_IDENTITY_MISMATCH"):
        reader_for(FakeConnection(head=publication_row(), identity=("market_research", 99, "127.0.0.1", 5432))).read_context(
            trade_date="2026-10-15", model_namespace_id="v4-main",
        )
    with pytest.raises(PublicationReadError, match="MODULE_RESULT_BINDING_SCHEMA_UNAVAILABLE"):
        reader_for(FakeConnection(head=publication_row(), missing_bindings=True)).read_context(
            trade_date="2026-10-15", model_namespace_id="v4-main",
        )


def test_stale_publication_and_unsafe_owner_locator_fail_closed():
    with pytest.raises(PublicationReadError, match="PUBLICATION_IDENTITY_MISMATCH"):
        reader_for(FakeConnection(head=publication_row())).read_context(
            trade_date="2026-10-15", model_namespace_id="v4-main", expected_publication=("older", 1),
        )
    bindings = [binding_row(module) for module in required_module_keys()]
    bindings[0] = binding_row(required_module_keys()[0], owner_schema="x;drop_schema")
    with pytest.raises(PublicationReadError, match="INVALID_OWNER_LOCATOR"):
        reader_for(FakeConnection(head=publication_row(), bindings=bindings)).read_context(
            trade_date="2026-10-15", model_namespace_id="v4-main",
        )


def test_adapter_maps_each_formal_current_entry_and_has_no_fallback():
    assert set(ENDPOINT_MODULES.values()) == set(required_module_keys())
    result = PgV4CurrentAdapter(reader_for(FakeConnection(head=publication_row()))).read_endpoint(
        "/api/v4/current/entity", trade_date="2026-10-15", model_namespace_id="v4-main",
    )
    assert result["candidate_only"] is True and result["module"] == "entity"
    assert result["payload"] == [{"row": "entity"}]
    with pytest.raises(PublicationReadError, match="PG_CURRENT_ENDPOINT_UNSUPPORTED"):
        PgV4CurrentAdapter(reader_for(FakeConnection(head=publication_row()))).read_endpoint(
            "/api/v4/current/unknown", trade_date="2026-10-15", model_namespace_id="v4-main",
        )


def owner_results(day="2026-10-15"):
    return [{
        "module_key": module, "module_contract_id": CONTRACT_ID,
        "database_identity": DATABASE_IDENTITY, "owner_schema": "v4_" + "a" * 56,
        "owner_relation": "owner_rows", "owner_version_token": f"{module}-r1",
        "owner_trade_date": day, "owner_contract_id": f"{module.upper()}_R1",
        "result_digest": "d" * 64, "row_count": 1, "quality_status": "DEGRADED",
        "as_recorded": False, "pit_eligible": False,
    } for module in required_module_keys()]


def candidate(**overrides):
    args = dict(
        publication_id="candidate-20261015-r1", trade_date="2026-10-15", revision_no=1,
        publication_lineage_id="lineage-20261015", model_namespace_id="v4-main", core_revision=1,
        source_manifest_sha256="a" * 64, computation_identity_sha256="b" * 64,
        expected_source_bindings={"tdx_daily": {"source_revision_id": "src-r1", "digest": "e" * 64}},
        observed_source_bindings={"tdx_daily": {"source_revision_id": "src-r1", "digest": "e" * 64}},
        module_results=owner_results(), state_head_id="state-20261015-r1", state_logical_digest="c" * 64,
        prior_session_gap_reason="INITIAL_BOUNDARY",
    )
    args.update(overrides)
    return build_publication_candidate(**args)


def test_candidate_is_candidate_only_and_preserves_quality_flags():
    plan = candidate()
    assert plan["status"] == "CANDIDATE_READY" and plan["publish_status"] == "CANDIDATE"
    assert plan["accepted_at"] is None and plan["head_update"] == "NOT_AUTHORIZED_BY_PLAN"
    assert plan["revision_no"] == 1 and plan["publication_lineage_id"] == "lineage-20261015"
    assert plan["module_results"][0]["quality_status"] == "DEGRADED"
    assert plan["module_results"][0]["as_recorded"] is False
    assert plan["module_results"][0]["pit_eligible"] is False
    assert len(plan["candidate_digest"]) == 64


def test_candidate_required_modules_and_versioned_contract_cannot_be_downgraded():
    partial = candidate(module_results=owner_results()[:-1])
    assert partial["status"] == "CANDIDATE_INCOMPLETE"
    assert len(partial["missing_required_modules"]) == 1
    bad = owner_results()
    bad[0]["module_contract_id"] = "OPTIONAL_OVERRIDE"
    with pytest.raises(CandidatePlanError, match="MODULE_CONTRACT_ID_MISMATCH"):
        candidate(module_results=bad)


def test_candidate_rejects_source_owner_and_state_identity_mismatch():
    with pytest.raises(CandidatePlanError, match="SOURCE_IDENTITY_MISMATCH"):
        candidate(observed_source_bindings={"tdx_daily": {"source_revision_id": "src-r1", "digest": "f" * 64}})
    bad_date = owner_results()
    bad_date[0]["owner_trade_date"] = "2026-10-14"
    with pytest.raises(CandidatePlanError, match="OWNER_T0_MISMATCH"):
        candidate(module_results=bad_date)
    with pytest.raises(CandidatePlanError, match="PUBLICATION_STATE_IDENTITY_INVALID"):
        candidate(state_logical_digest="bad")


def test_head_planner_uses_publication_id_and_exact_state_cas_without_writes():
    first = candidate()
    initial = plan_publication_head_change(first, None)
    assert initial["action"] == "INSERT_IF_ABSENT" and initial["initial_boundary_review_required"] is True
    assert initial["write_executed"] is False
    next_pub = candidate(
        publication_id="candidate-20261015-r2", revision_no=2,
        same_day_revision_parent_id=first["publication_id"], prior_session_gap_reason="INITIAL_BOUNDARY",
    )
    cas = plan_publication_head_change(next_pub, {
        "trade_date": "2026-10-15", "model_namespace_id": "v4-main",
        "publication_id": first["publication_id"], "revision_no": 1,
        "publication_lineage_id": first["publication_lineage_id"],
        "state_head_id": first["state_head_id"], "state_logical_digest": first["state_logical_digest"],
    })
    assert cas["action"] == "CAS_UPDATE" and cas["write_executed"] is False
    assert cas["expected_prior_head"]["publication_id"] == first["publication_id"]
    assert "revision" not in cas["expected_prior_head"]


def test_head_planner_rejects_wrong_parent_or_non_next_revision():
    first = candidate()
    wrong_parent = candidate(publication_id="candidate-r2", revision_no=2, same_day_revision_parent_id="other")
    with pytest.raises(CandidatePlanError, match="HEAD_CAS_PRECONDITION_MISMATCH"):
        plan_publication_head_change(wrong_parent, {
            "trade_date": first["trade_date"], "model_namespace_id": first["model_namespace_id"],
            "publication_id": first["publication_id"], "revision_no": 1,
            "publication_lineage_id": first["publication_lineage_id"],
            "state_head_id": first["state_head_id"], "state_logical_digest": first["state_logical_digest"],
        })
    gap = candidate(publication_id="candidate-r4", revision_no=4, same_day_revision_parent_id=first["publication_id"])
    with pytest.raises(CandidatePlanError, match="PUBLICATION_REVISION_NOT_NEXT"):
        plan_publication_head_change(gap, {
            "trade_date": first["trade_date"], "model_namespace_id": first["model_namespace_id"],
            "publication_id": first["publication_id"], "revision_no": 1,
            "publication_lineage_id": first["publication_lineage_id"],
            "state_head_id": first["state_head_id"], "state_logical_digest": first["state_logical_digest"],
        })
