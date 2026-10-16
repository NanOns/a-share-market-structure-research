from contextlib import contextmanager
from datetime import date, datetime, timedelta, timezone

import pytest

from workbench_db.v4_publication_candidate import (
    CandidatePlanError,
    build_publication_candidate,
    plan_publication_head_change,
)
from workbench_db.v4_publication_contract import CONTRACT_ID, OWNER_FAMILIES, effective_module_contract, required_module_keys, supported_owner_keys
from workbench_db.v4_publication_reader import PgPublicationReader, PublicationReadError, reader_dsn
from workbench_db.v4_source_manifest import CONTRACT_ID as SOURCE_MANIFEST_CONTRACT_ID, source_manifest_digest
from workbench_service.v4_pg_current_adapter import ENDPOINT_MODULES, PgV4CurrentAdapter


DATABASE_IDENTITY = {"database": "market_research", "database_oid": 16384, "host": "127.0.0.1", "port": 5432}
DIGEST = "a" * 64
TARGET_DATE = date(2026, 10, 15)
ACCEPTED_AT = datetime(2026, 10, 15, 16, 0, tzinfo=timezone.utc)


def publication_row(**changes):
    row = {
        "publication_id": "pub-20261015-r1", "revision_no": 1, "trade_date": TARGET_DATE,
        "model_namespace_id": "v4-main", "status": "ACCEPTED", "accepted_at": ACCEPTED_AT,
        "core_revision": 1, "source_manifest_sha256": source_manifest_digest([source_row()]),
        "source_manifest_contract_id": SOURCE_MANIFEST_CONTRACT_ID,
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
        "owner_schema": "v4_" + "a" * 56,
        "owner_relation": "owner_rows" if module == "sector_lifecycle" else "owner_payloads",
        "owner_version_token": f"{module}-owner-r1", "owner_trade_date": TARGET_DATE,
        "owner_contract_id": OWNER_FAMILIES[module]["owner_contract_id"], "result_digest": "d" * 64,
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
        "source_package_id": "pkg-20261015-r1",
        "source_package_contract_version": "V4_DAILY_CAPTURE_R1",
        "source_package_sha256": "f" * 64,
        "source_package_page_observed_at": datetime(2026, 10, 15, 15, 6, tzinfo=timezone.utc),
        "source_package_target_trade_date": TARGET_DATE,
        "source_package_parser_version": "daily-parser-r1",
        "source_package_accepted_scope": "ACCEPTED_SOURCE_PACKAGE",
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
    def __init__(self, *, head=None, bindings=None, sources=None, identity=None, role=None, missing_bindings=False, parent=None, page_data=None, core_snapshot=None, core_rows=None):
        self.head = head
        self.bindings = bindings if bindings is not None else [binding_row(module) for module in supported_owner_keys()]
        self.sources = sources if sources is not None else [source_row()]
        self.identity = identity or ("market_research", 16384, "127.0.0.1", 5432)
        self.role = role or ("v4_reader", False, False, False, False, False, False, False, False, False, False, False)
        self.missing_bindings = missing_bindings
        self.parent = parent
        self.page_data = page_data or {}
        self.core_snapshot = core_snapshot
        self.core_rows = core_rows or []
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
        if "FROM v4.event_observations" in statement:
            return Cursor(all_rows=self.page_data.get("summary_events", []))
        if "FROM v4.security_lifecycle_facts" in statement:
            return Cursor(all_rows=self.page_data.get("entity_lifecycle", []))
        if "FROM v4.daily_core_result_snapshots" in statement:
            return Cursor(one=self.core_snapshot)
        if "FROM v4.daily_core_result_rows" in statement:
            return Cursor(all_rows=self.core_rows)
        if "FROM v4.sector_membership_facts" in statement:
            return Cursor(all_rows=self.page_data.get("sector_membership_rows", []))
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
    return {module: resolve for module in supported_owner_keys()}


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


def test_contract_maps_real_owner_families_and_does_not_infer_daily_requiredness():
    contract = effective_module_contract()
    assert contract["contract_id"] == CONTRACT_ID
    assert set(contract["owner_families"]) == set(supported_owner_keys())
    assert all(row["daily_publication_required"] is False for row in contract["owner_families"].values())
    assert contract["page_projections"]["entity"]["owner_families"] == []
    assert "membership" in contract["page_projections"]["sector"]["uncovered_groups"]


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
    assert result["module_results"]["research_priority"]["quality_status"] == "DEGRADED"
    assert result["module_results"]["research_priority"]["as_recorded"] is False
    assert result["module_results"]["research_priority"]["pit_eligible"] is False
    assert result["state_head_id"] == "state-20261015-r1"
    assert result["source_bindings"][0]["source_revision_id"] == "src-r1"
    assert result["source_manifest_rehash_status"] == "REHASH_PASS"
    assert result["source_manifest_recomputed_sha256"] == result["source_manifest_sha256"]
    assert len(result["module_results_digest"]) == 64
    assert result["context_token"].startswith("pg-candidate-")
    head_sql = next(sql for sql, _ in connection.statements if "FROM v4.publication_heads" in sql)
    assert "h.revision" not in head_sql and "p.revision," not in head_sql
    assert "p.revision_no" in head_sql and "state_heads" in head_sql
    source_sql = next(sql for sql, _ in connection.statements if "FROM v4.publication_consumed_sources" in sql)
    assert "ORDER BY convert_to(cs.source_key, 'UTF8')" in source_sql
    assert "JOIN v4.source_packages sp ON sp.package_id=sr.source_package_id" in source_sql
    assert "sp.accepted_scope AS source_package_accepted_scope" in source_sql
    event_sql = next(sql for sql, _ in connection.statements if "FROM v4.event_observations" in sql)
    assert "row_number() OVER" in event_sql and "ORDER BY observation_revision DESC" in event_sql


def test_metadata_only_is_marked_unverified_and_is_not_the_default():
    connection = FakeConnection(head=publication_row())
    result = reader_for(connection).read_context(
        trade_date="2026-10-15", model_namespace_id="v4-main", resolve_payloads=False,
    )
    assert result["read_mode"] == "METADATA_ONLY_UNVERIFIED"
    assert result["readback_complete"] is False
    assert "module_payloads" not in result


def test_missing_payload_resolver_fails_closed_for_bound_owner_family():
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
    changed = [binding_row(module) for module in supported_owner_keys()]
    changed[0] = binding_row(supported_owner_keys()[0], result_digest="f" * 64)
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


def test_reader_rechecks_accepted_package_identity_and_t0_clock():
    cases = [
        (source_row(source_package_accepted_scope="DIAGNOSTIC_ONLY"), "SOURCE_PACKAGE_NOT_ACCEPTED_OR_UNBOUND"),
        (source_row(source_package_target_trade_date=date(2026, 10, 14)), "SOURCE_PACKAGE_T0_MISMATCH"),
        (source_row(source_package_page_observed_at=datetime(2026, 10, 14, 15, 0, tzinfo=timezone.utc)), "FUTURE_TRADE_DATE_WITHOUT_SAME_DAY_SOURCE_OBSERVATION"),
        (source_row(source_package_page_observed_at=ACCEPTED_AT + timedelta(seconds=1)), "SOURCE_PACKAGE_OBSERVED_AFTER_PUBLICATION_ACCEPTANCE"),
    ]
    for source, code in cases:
        with pytest.raises(PublicationReadError, match=code):
            reader_for(FakeConnection(head=publication_row(), sources=[source])).read_context(
                trade_date="2026-10-15", model_namespace_id="v4-main",
            )


def test_source_manifest_contract_must_be_supported_and_rehash_must_match():
    with pytest.raises(PublicationReadError, match="SOURCE_MANIFEST_CONTRACT_UNSUPPORTED"):
        reader_for(FakeConnection(head=publication_row(source_manifest_contract_id=None))).read_context(
            trade_date="2026-10-15", model_namespace_id="v4-main",
        )
    changed = source_row(logical_fact_id="tdx:changed")
    with pytest.raises(PublicationReadError, match="SOURCE_MANIFEST_REHASH_MISMATCH"):
        reader_for(FakeConnection(head=publication_row(), sources=[changed])).read_context(
            trade_date="2026-10-15", model_namespace_id="v4-main",
        )


def test_wrong_owner_t0_and_module_contract_fail_closed_but_absent_optional_owner_does_not():
    bindings = [binding_row(module) for module in supported_owner_keys()]
    with pytest.raises(PublicationReadError, match="OWNER_T0_MISMATCH"):
        reader_for(FakeConnection(head=publication_row(), bindings=[binding_row("research_priority", owner_trade_date=date(2026, 10, 14)), *bindings[1:]])).read_context(
            trade_date="2026-10-15", model_namespace_id="v4-main",
        )
    wrong_contract = [binding_row(module) for module in supported_owner_keys()]
    wrong_contract[0] = binding_row(supported_owner_keys()[0], module_contract_id="UNVERSIONED_OPTIONAL")
    with pytest.raises(PublicationReadError, match="MODULE_CONTRACT_ID_MISMATCH"):
        reader_for(FakeConnection(head=publication_row(), bindings=wrong_contract)).read_context(
            trade_date="2026-10-15", model_namespace_id="v4-main",
        )
    # Existing Owners are capability-optional; a missing one cannot be
    # represented by a fabricated empty result or block unrelated pages.
    result = reader_for(FakeConnection(head=publication_row(), bindings=bindings[:-1])).read_context(
        trade_date="2026-10-15", model_namespace_id="v4-main",
    )
    assert result["readback_complete"] is True


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
        reader_for(FakeConnection(head=publication_row(), role=("owner", False, False, False, False, False, False, True, False, False, False, False))).read_context(
            trade_date="2026-10-15", model_namespace_id="v4-main",
        )


@pytest.mark.parametrize("index", [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11])
def test_reader_rejects_every_privileged_role_or_namespace_write_capability(index):
    role=["v4_reader"]+[False]*11
    role[index]=True
    with pytest.raises(PublicationReadError, match="PG_READER_ROLE_HAS_WRITE_PRIVILEGES"):
        reader_for(FakeConnection(head=publication_row(), role=tuple(role))).read_context(
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
    bindings = [binding_row(module) for module in supported_owner_keys()]
    bindings[0] = binding_row(supported_owner_keys()[0], owner_schema="x;drop_schema")
    with pytest.raises(PublicationReadError, match="INVALID_OWNER_LOCATOR"):
        reader_for(FakeConnection(head=publication_row(), bindings=bindings)).read_context(
            trade_date="2026-10-15", model_namespace_id="v4-main",
        )


def test_adapter_maps_each_formal_current_entry_and_has_no_fallback():
    assert set(ENDPOINT_MODULES.values()) == {"summary", "radar", "entity", "sector", "cohort", "settlement", "health"}
    result = PgV4CurrentAdapter(reader_for(FakeConnection(head=publication_row()))).read_endpoint(
        "/api/v4/current/entity", trade_date="2026-10-15", model_namespace_id="v4-main",
    )
    assert result["candidate_only"] is True and result["page"] == "entity"
    assert result["status"] == "PENDING"
    assert result["quality_status"] == "NOT_VERIFIABLE_PAGE_PARITY"
    assert result["payload"] == {}
    assert result["uncovered_reasons"]["RAW_DAILY"] == "NO_V4_PUBLICATION_BOUND_DAILY_PRICE_RELATION"
    with pytest.raises(PublicationReadError, match="PG_CURRENT_ENDPOINT_UNSUPPORTED"):
        PgV4CurrentAdapter(reader_for(FakeConnection(head=publication_row()))).read_endpoint(
            "/api/v4/current/unknown", trade_date="2026-10-15", model_namespace_id="v4-main",
        )


@pytest.mark.parametrize(("page", "expected_owner"), [
    ("summary", "operational_risk"),
    ("radar", "research_priority"),
    ("sector", "sector_lifecycle"),
    ("health", "operational_risk"),
])
def test_partial_owner_projection_never_promotes_page_to_ready(page, expected_owner):
    result = PgV4CurrentAdapter(reader_for(FakeConnection(head=publication_row()))).read_endpoint(
        f"/api/v4/current/{page}", trade_date="2026-10-15", model_namespace_id="v4-main",
    )
    assert result["status"] == "DEGRADED"
    assert result["candidate_only"] is True
    assert result["quality_status"] == "NOT_VERIFIABLE_PAGE_PARITY"
    assert expected_owner in result["payload"]
    assert result["uncovered_input_groups"]


def test_adapter_parses_exact_publication_bound_events_and_lifecycle_fields():
    events = [{
        "logical_event_id": "event-1", "observation_revision": 1, "status": "ACTIVE",
        "payload": {"effective_event": "BREAKOUT", "trade_date": "2026-10-15", "why_now": "volume"},
    }]
    lifecycle = [{
        "security_id": "000001.SZ", "security_type": "STOCK", "board": "MAIN",
        "listed_from": date(2000, 1, 1), "listed_to": None, "st_state": None,
        "trade_status": "ACTIVE", "effective_from": date(2026, 10, 1), "effective_to": None,
        "observed_at": ACCEPTED_AT, "ingested_at": ACCEPTED_AT, "system_available_at": ACCEPTED_AT,
        "source_revision_id": "src-r1", "source_identity": "fixture-source", "quality": "KNOWN",
    }]
    readers = owner_readers()
    def risk_reader(pg, binding):
        return {
            "database_identity": binding["database_identity"],
            "owner_schema": binding["owner_schema"], "owner_relation": binding["owner_relation"],
            "owner_version_token": binding["owner_version_token"], "owner_trade_date": binding["owner_trade_date"],
            "owner_contract_id": binding["owner_contract_id"], "result_digest": binding["result_digest"],
            "row_count": binding["row_count"], "payload": {
                "contract_id": "V4_OPERATIONAL_RISK_CHANGE_R1", "T0": "2026-10-15",
                "families": {name: {"status": "KNOWN", "changes": []} for name in (
                    "STOCK_STRUCTURE_RISK", "SECTOR_ECOLOGY_RISK", "MARKET_PRESSURE_RISK",
                )},
            },
        }
    readers["operational_risk"] = risk_reader
    reader = reader_for(FakeConnection(
        head=publication_row(), page_data={"summary_events": events, "entity_lifecycle": lifecycle},
    ), owner_readers=readers)
    adapter = PgV4CurrentAdapter(reader)
    summary = adapter.read_endpoint("/api/v4/current/summary", trade_date="2026-10-15", model_namespace_id="v4-main")
    entity = adapter.read_endpoint("/api/v4/current/entity", trade_date="2026-10-15", model_namespace_id="v4-main")
    assert summary["parsed_business_fields"]["events"][0]["fields"] == {
        "effective_event": "BREAKOUT", "trade_date": "2026-10-15", "why_now": "volume",
    }
    assert summary["field_mapping"]["effective_event"] == "page_data.summary_events[0].payload.effective_event"
    assert summary["parsed_business_fields"]["events"][0]["field_states"]["effective_event"] == "PG_FIELD_VERIFIED"
    assert summary["parsed_business_fields"]["events"][0]["field_states"]["counterevidence"] == "SOURCE_MISSING"
    assert len(summary["parsed_business_fields"]["risk_change_summary"]) == 3
    assert summary["parsed_business_fields"]["risk_change_summary"][0]["source_owner"] == "operational_risk"
    assert summary["parsed_business_fields"]["risk_change_summary"][0]["context_token"] == summary["context"]["context_token"]
    assert entity["parsed_business_fields"]["lifecycle"][0]["security_id"] == "000001.SZ"
    assert entity["parsed_business_fields"]["lifecycle"][0]["field_states"]["security_id"] == "PG_FIELD_VERIFIED"
    assert entity["status"] == "DEGRADED"
    assert entity["field_states"]["trade_date"] == "PG_FIELD_VERIFIED"
    assert entity["field_states"]["close"] == "SOURCE_MISSING"
    assert entity["field_mapping"]["security_id"] == "page_data.entity_lifecycle[0].security_id"
    assert entity["uncovered_reasons"]["RAW_DAILY"] == "NO_V4_PUBLICATION_BOUND_DAILY_PRICE_RELATION"


def test_adapter_field_coverage_does_not_promote_one_row_hit_to_page_coverage():
    events = [
        {"logical_event_id": "event-1", "observation_revision": 1, "status": "ACTIVE",
         "payload": {"effective_event": "BREAKOUT", "trade_date": "2026-10-15"}},
        {"logical_event_id": "event-2", "observation_revision": 1, "status": "ACTIVE",
         "payload": {"primary_scenario": "TREND", "trade_date": "2026-10-15"}},
    ]
    reader = reader_for(FakeConnection(head=publication_row(), page_data={"summary_events": events}))
    result = PgV4CurrentAdapter(reader).read_endpoint(
        "/api/v4/current/summary", trade_date="2026-10-15", model_namespace_id="v4-main",
    )
    assert result["field_states"]["effective_event"] == "PARTIAL_PG_FIELD_VERIFIED"
    assert result["field_data_states"]["effective_event"] == "PARTIAL_DATA_VERIFIED"
    assert result["field_coverage"]["effective_event"] == {
        "present_rows": 1, "eligible_rows": 2, "verified_rows": 1,
        "missing_reason": "FIELD_NOT_PRESENT_IN_ALL_ELIGIBLE_ROWS",
        "source_paths": ["page_data.summary_events[0].payload.effective_event"],
        "status": "PARTIAL_PG_FIELD_VERIFIED",
    }
    assert result["parsed_business_fields"]["events"][1]["field_states"]["effective_event"] == "SOURCE_MISSING"


def test_field_coverage_reports_empty_owner_and_excludes_mixed_t0_rows():
    from workbench_service.v4_pg_current_adapter import _field_coverage

    empty = _field_coverage(
        ("entity_id",), [], target_t0="2026-10-15", no_row_reason="OWNER_FAMILY_UNAVAILABLE",
        contract_known=True,
    )
    assert empty["entity_id"]["eligible_rows"] == 0
    assert empty["entity_id"]["missing_reason"] == "OWNER_FAMILY_UNAVAILABLE"
    mixed = _field_coverage(
        ("entity_id",), [
            {"row": {"entity_id": "A", "T0": "2026-10-15"}, "verified": True},
            {"row": {"entity_id": "B", "T0": "2026-10-14"}, "verified": True},
        ], target_t0="2026-10-15", no_row_reason="NO_PUBLICATION_BOUND_ROWS", contract_known=True,
    )
    assert mixed["entity_id"] == {
        "present_rows": 1, "eligible_rows": 1, "verified_rows": 1,
        "missing_reason": None, "source_paths": [], "status": "PG_FIELD_VERIFIED",
    }


def test_missing_daily_prices_remain_explicit_for_entity_even_when_lifecycle_is_present():
    lifecycle = [{
        "security_id": "000001.SZ", "security_type": "STOCK", "board": "MAIN",
        "listed_from": date(2000, 1, 1), "listed_to": None, "st_state": None,
        "trade_status": "ACTIVE", "effective_from": date(2026, 10, 1), "effective_to": None,
        "observed_at": ACCEPTED_AT, "ingested_at": ACCEPTED_AT, "system_available_at": ACCEPTED_AT,
        "source_revision_id": "src-r1", "source_identity": "fixture-source", "quality": "KNOWN",
    }]
    reader = reader_for(FakeConnection(head=publication_row(), page_data={"entity_lifecycle": lifecycle}))
    result = PgV4CurrentAdapter(reader).read_endpoint(
        "/api/v4/current/entity", trade_date="2026-10-15", model_namespace_id="v4-main",
    )
    for field in ("open", "high", "low", "close"):
        assert result["field_states"][field] == "SOURCE_MISSING"
        assert result["field_coverage"][field]["missing_reason"] == "NO_PUBLICATION_BOUND_CORE_RESULT"
    assert result["parsed_business_fields"]["lifecycle"][0]["field_coverage"]["security_id"]["verified_rows"] == 1


def test_entity_candidate_projects_only_publication_bound_core_rows_and_ma_profile():
    from workbench_db.v4_daily_core_result_r6 import _sha

    row = {
        "trade_date": "2026-10-15", "security_id": "000001.SZ", "security_type": "STOCK",
        "trade_status": "TRADING", "open": 10.0, "high": 11.0, "low": 9.5, "close": 10.5,
        "volume": 1000.0, "amount": 10500.0, "turnover_rate": None,
        "turnover_status": "TURNOVER_UNAVAILABLE", "ma5": 10.1, "ma20": 9.9, "ma60": 9.5,
        "history_status": "SUFFICIENT", "price_basis": "TDX_GBBQ_UNCHANGED",
        "source_revision_id": "src-r1", "profile_payload": {"trend": "OBSERVED"},
        "quality_status": "ACTUAL_OPERATIONAL_DAILY_OWNER_V1",
    }
    row["row_sha256"] = _sha(row)
    pub = publication_row()
    material = {
        "contract_id": "V4_DAILY_CORE_RESULT_BINDING_R6", "contract_version": "1.0.0",
        "publication_id": pub["publication_id"], "publication_revision": pub["revision_no"],
        "trade_date": "2026-10-15", "source_manifest_sha256": pub["source_manifest_sha256"],
        "producer_contract_id": "V4_OPERATIONAL_DAILY_PRODUCER_R1", "producer_sha256": "1" * 64,
        "producer_receipt_sha256": "2" * 64, "rows": [row],
    }
    snapshot = (TARGET_DATE, "V4_DAILY_CORE_RESULT_BINDING_R6", pub["source_manifest_sha256"],
                _sha(material), 1, "V4_OPERATIONAL_DAILY_PRODUCER_R1", "1" * 64, "2" * 64)
    reader = reader_for(FakeConnection(head=pub, core_snapshot=snapshot, core_rows=[row]))
    result = PgV4CurrentAdapter(reader).read_endpoint(
        "/api/v4/current/entity", trade_date="2026-10-15", model_namespace_id="v4-main",
    )
    assert result["field_coverage"]["close"]["status"] == "PG_FIELD_VERIFIED"
    assert result["field_coverage"]["ma20"]["status"] == "PG_FIELD_VERIFIED"
    assert result["parsed_business_fields"]["daily_core"][0]["profile_payload"] == {"trend": "OBSERVED"}
    entity = result["parsed_business_fields"]["entities"][0]
    assert entity["security_id"] == "000001.SZ"
    assert entity["identity_name_state"] == "DATA_MISSING"
    assert entity["context_token"] == result["context"]["context_token"]


def test_entity_candidate_rejects_core_rows_with_bad_row_digest():
    from workbench_db.v4_daily_core_result_r6 import _sha

    row = {
        "trade_date": "2026-10-15", "security_id": "000001.SZ", "security_type": "STOCK",
        "trade_status": "TRADING", "open": 10.0, "high": 11.0, "low": 9.5, "close": 10.5,
        "volume": 1000.0, "amount": 10500.0, "turnover_rate": None,
        "turnover_status": "TURNOVER_UNAVAILABLE", "ma5": 10.1, "ma20": 9.9, "ma60": 9.5,
        "history_status": "SUFFICIENT", "price_basis": "TDX_GBBQ_UNCHANGED",
        "source_revision_id": "src-r1", "profile_payload": {}, "quality_status": "ACTUAL",
    }
    row["row_sha256"] = "0" * 64
    pub = publication_row()
    material = {
        "contract_id": "V4_DAILY_CORE_RESULT_BINDING_R6", "contract_version": "1.0.0",
        "publication_id": pub["publication_id"], "publication_revision": pub["revision_no"],
        "trade_date": "2026-10-15", "source_manifest_sha256": pub["source_manifest_sha256"],
        "producer_contract_id": "P", "producer_sha256": "1" * 64,
        "producer_receipt_sha256": "2" * 64, "rows": [row],
    }
    snapshot = (TARGET_DATE, "V4_DAILY_CORE_RESULT_BINDING_R6", pub["source_manifest_sha256"],
                _sha(material), 1, "P", "1" * 64, "2" * 64)
    reader = reader_for(FakeConnection(head=pub, core_snapshot=snapshot, core_rows=[row]))
    with pytest.raises(PublicationReadError, match="CORE_RESULT_ROW_DIGEST_MISMATCH"):
        PgV4CurrentAdapter(reader).read_endpoint(
            "/api/v4/current/entity", trade_date="2026-10-15", model_namespace_id="v4-main",
        )


def test_sector_lifecycle_supplement_does_not_claim_membership_or_algorithm_state():
    readers = owner_readers()

    def lifecycle_reader(pg, binding):
        return {
            "database_identity": binding["database_identity"],
            "owner_schema": binding["owner_schema"], "owner_relation": binding["owner_relation"],
            "owner_version_token": binding["owner_version_token"], "owner_trade_date": binding["owner_trade_date"],
            "owner_contract_id": binding["owner_contract_id"], "result_digest": binding["result_digest"],
            "row_count": binding["row_count"], "payload": [{
                "sector_id": "INDUSTRY:T0706", "T0": "2026-10-15",
                "contract_id": "SECTOR_LIFECYCLE_RECONSTRUCTED_V1", "maturity": "OBSERVED",
                "health": "HEALTHY",
            }],
        }

    readers["sector_lifecycle"] = lifecycle_reader
    reader = reader_for(FakeConnection(head=publication_row()), owner_readers=readers)
    result = PgV4CurrentAdapter(reader).read_endpoint(
        "/api/v4/current/sector", trade_date="2026-10-15", model_namespace_id="v4-main",
    )
    assert result["parsed_business_fields"]["sector_membership"] == []
    assert result["parsed_business_fields"]["sector_lifecycle_supplement"][0]["maturity"] == "OBSERVED"
    assert result["field_data_states"]["member_count"] == "DATA_MISSING"
    assert result["field_data_states"]["algorithm_state"] == "DATA_MISSING"
    assert result["field_coverage"]["sector_id"]["status"] == "SOURCE_MISSING"


def test_sector_membership_requires_same_publication_source_and_reports_non_pit_basis():
    shared = {
        "snapshot_id": "a" * 64, "source_revision_id": "src-r1", "sector_id": "INDUSTRY:T0706",
        "sector_code": "T0706", "sector_name": "通信设备", "sector_type": "INDUSTRY",
        "target_trade_date": TARGET_DATE, "membership_asof_date": TARGET_DATE,
        "membership_basis": "CURRENT_TDX_MEMBERSHIP", "membership_quality": "CURRENT_TDX_DIAGNOSTIC",
        "pit_observed": False, "historical_backtest_safe": False, "snapshot_source_digest": "e" * 64,
        "snapshot_row_count": 2, "snapshot_quality": "CURRENT_TDX_DIAGNOSTIC",
        "snapshot_pit_observed": False,
    }
    rows = [
        {**shared, "membership_fact_id": "1" * 64, "source_security_key": "SZ.000001",
         "security_id": "000001.SZ", "identity_status": "MAPPED"},
        {**shared, "membership_fact_id": "2" * 64, "source_security_key": "SZ.000002",
         "security_id": None, "identity_status": "UNKNOWN"},
    ]
    reader = reader_for(FakeConnection(head=publication_row(), page_data={"sector_membership_rows": rows}))
    result = PgV4CurrentAdapter(reader).read_endpoint(
        "/api/v4/current/sector", trade_date="2026-10-15", model_namespace_id="v4-main",
    )
    sector = result["parsed_business_fields"]["sector_membership"][0]
    assert sector["member_count"] == 1
    assert sector["unknown_identity_count"] == 1
    assert sector["membership_basis"] == "CURRENT_TDX_MEMBERSHIP"
    assert result["field_coverage"]["member_count"]["status"] == "PG_FIELD_VERIFIED"
    assert result["field_data_states"]["member_count"] == "NOT_PIT_ELIGIBLE"
    assert result["field_data_states"]["sector_name"] == "DATA_VERIFIED"
    assert result["uncovered_reasons"]["membership"] is None
    assert sector["field_data_states"]["algorithm_state"] == "DATA_MISSING"


def owner_results(day="2026-10-15"):
    return [{
        "module_key": module, "module_contract_id": CONTRACT_ID,
        "database_identity": DATABASE_IDENTITY, "owner_schema": "v4_" + "a" * 56,
        "owner_relation": OWNER_FAMILIES[module]["relation"], "owner_version_token": f"{module}-r1",
        "owner_trade_date": day, "owner_contract_id": OWNER_FAMILIES[module]["owner_contract_id"],
        "result_digest": "d" * 64, "row_count": 1, "quality_status": "DEGRADED",
        "as_recorded": False, "pit_eligible": False,
    } for module in supported_owner_keys()]


def candidate(**overrides):
    args = dict(
        publication_id="candidate-20261015-r1", trade_date="2026-10-15", revision_no=1,
        publication_lineage_id="lineage-20261015", model_namespace_id="v4-main", core_revision=1,
        source_manifest_sha256=source_manifest_digest([source_row()]), source_manifest_rows=[source_row()], computation_identity_sha256="b" * 64,
        source_manifest_contract_id=SOURCE_MANIFEST_CONTRACT_ID,
        expected_source_bindings={"tdx_daily": {"source_revision_id": "src-r1", "digest": "e" * 64}},
        observed_source_bindings={"tdx_daily": {"source_revision_id": "src-r1", "digest": "e" * 64}},
        database_identity=DATABASE_IDENTITY,
        module_results=owner_results(), state_head_id="state-20261015-r1", state_logical_digest="c" * 64,
        prior_session_gap_reason="INITIAL_BOUNDARY",
    )
    args.update(overrides)
    return build_publication_candidate(**args)


def test_candidate_is_candidate_only_and_preserves_quality_flags():
    plan = candidate()
    assert plan["status"] == "METADATA_CANDIDATE_READY" and plan["publish_status"] == "BLOCKED_BUSINESS_PUBLISHABILITY"
    assert plan["accepted_at"] is None and plan["head_update"] == "PLAN_ONLY_NOT_EXECUTED"
    assert plan["metadata_readiness_status"] == "SOURCE_AND_IDENTITY_VALIDATED"
    assert plan["business_publishability_status"] == "BLOCKED_CORE_RESULT_NOT_BOUND"
    assert plan["global_requiredness_status"] == "PASS_METADATA_IDENTITY_ONLY"
    assert plan["minimum_publish_contract_id"] == "V4_DAILY_PUBLICATION_MINIMUM_R2"
    assert plan["revision_no"] == 1 and plan["publication_lineage_id"] == "lineage-20261015"
    assert plan["module_results"][0]["quality_status"] == "DEGRADED"
    assert plan["module_results"][0]["as_recorded"] is False
    assert plan["module_results"][0]["pit_eligible"] is False
    assert len(plan["candidate_digest"]) == 64


def test_new_t0_rejects_r2_manifest_downgrade():
    with pytest.raises(CandidatePlanError, match="NEW_PUBLICATION_REQUIRES_R3_SOURCE_MANIFEST"):
        candidate(trade_date="2026-10-16", source_manifest_contract_id=SOURCE_MANIFEST_CONTRACT_ID)


def test_owner_binding_writer_inserts_inside_caller_transaction_and_never_seals_head(monkeypatch):
    from workbench_db.v4_publication_module_writer_r4 import persist_publication_module_results

    monkeypatch.setenv("V4_NATIVE_PG_DSN", "postgresql://v4_writer@127.0.0.1/market_research")
    pg = OwnerBindingWriterConnection()
    result = persist_publication_module_results(pg, candidate())
    assert result == {
        "status": "OWNER_BINDINGS_INSERTED_NOT_HEAD_ACCEPTED", "row_count": 3,
        "write_mode": "CALLER_TRANSACTION_NO_COMMIT", "head_changed": False, "committed": False,
    }
    assert len(pg.inserted) == 3
    assert not any("INSERT INTO v4.publication_heads" in sql for sql, _ in pg.statements)
    assert not any("COMMIT" in sql.upper() for sql, _ in pg.statements)
    repeated = persist_publication_module_results(pg, candidate())
    assert repeated["status"] == "EXISTING_BINDINGS_VERIFIED"
    assert repeated["row_count"] == 3
    assert len(pg.inserted) == 3


class OwnerBindingWriterConnection:
    """SQL-shaped fixture for the pure caller-transaction writer contract."""

    def __init__(self):
        self.statements = []
        self.inserted = []

    def execute(self, statement, params=None):
        from datetime import date

        sql = str(statement)
        self.statements.append((sql, params))
        if sql == "SHOW transaction_read_only":
            return Cursor(one=("off",))
        if "FROM pg_roles r WHERE r.rolname=current_user" in sql:
            return Cursor(one=("v4_writer", False, False, False, False, False, False, True, False))
        if "inet_server_addr()" in sql:
            return Cursor(one=("market_research", 16384, "127.0.0.1", 5432))
        if "pg_advisory_xact_lock" in sql:
            return Cursor()
        if "FROM v4.publications WHERE publication_id=%s" in sql:
            return Cursor(one=(date(2026, 10, 15), 1, source_manifest_digest([source_row()]), "ACCEPTED", ACCEPTED_AT))
        if "FROM v4.publication_heads WHERE publication_id=%s" in sql:
            return Cursor()
        if "FROM v4.publication_module_results" in sql and sql.lstrip().startswith("SELECT"):
            rows = []
            for row in self.inserted:
                row = list(row[1:])
                row[2] = row[2].obj
                row[6] = date.fromisoformat(row[6])
                rows.append(tuple(row))
            return Cursor(all_rows=rows)
        if sql.lstrip().startswith("INSERT INTO v4.publication_module_results"):
            self.inserted.append(tuple(params))
            return Cursor()
        raise AssertionError(f"unexpected SQL: {sql}")


def test_candidate_required_modules_and_versioned_contract_cannot_be_downgraded():
    partial = candidate(module_results=[])
    assert partial["status"] == "METADATA_CANDIDATE_READY"
    assert partial["module_results"] == []
    bad = owner_results()
    bad[0]["module_contract_id"] = "OPTIONAL_OVERRIDE"
    with pytest.raises(CandidatePlanError, match="MODULE_CONTRACT_ID_MISMATCH"):
        candidate(module_results=bad)


def test_candidate_requires_explicit_source_manifest_contract_version():
    with pytest.raises(CandidatePlanError, match="SOURCE_MANIFEST_CONTRACT_UNSUPPORTED"):
        candidate(source_manifest_contract_id="LEGACY_UNKNOWN")


def test_candidate_rehashes_complete_source_rows_and_blocks_missing_or_changed_manifest():
    with pytest.raises(CandidatePlanError, match="CANDIDATE_SOURCE_MANIFEST_UNVERIFIED"):
        candidate(source_manifest_rows=[])
    with pytest.raises(CandidatePlanError, match="SOURCE_MANIFEST_DIGEST_MISMATCH"):
        candidate(source_manifest_sha256="a" * 64)
    with pytest.raises(CandidatePlanError, match="SOURCE_MANIFEST_DIGEST_MISMATCH"):
        candidate(source_manifest_rows=[source_row(revision_digest="f" * 64)])
    assert candidate(source_manifest_sha256=None)["source_manifest_sha256"] == source_manifest_digest([source_row()])


def test_candidate_rejects_source_owner_and_state_identity_mismatch():
    with pytest.raises(CandidatePlanError, match="SOURCE_IDENTITY_MISMATCH"):
        candidate(observed_source_bindings={"tdx_daily": {"source_revision_id": "src-r1", "digest": "f" * 64}})
    bad_date = owner_results()
    bad_date[0]["owner_trade_date"] = "2026-10-14"
    with pytest.raises(CandidatePlanError, match="OWNER_T0_MISMATCH"):
        candidate(module_results=bad_date)
    with pytest.raises(CandidatePlanError, match="PUBLICATION_STATE_IDENTITY_INVALID"):
        candidate(state_logical_digest="bad")
    with pytest.raises(CandidatePlanError, match="PUBLICATION_DATABASE_IDENTITY_INVALID"):
        candidate(database_identity={"database": "market_research"})
    bad_owner = owner_results()
    bad_owner[0]["database_identity"] = {**DATABASE_IDENTITY, "database": "other"}
    with pytest.raises(CandidatePlanError, match="OWNER_DATABASE_IDENTITY_MISMATCH"):
        candidate(module_results=bad_owner)


def test_metadata_candidate_ready_does_not_authorize_head_change():
    plan = candidate()
    assert plan["status"] == "METADATA_CANDIDATE_READY"
    with pytest.raises(CandidatePlanError, match="CANDIDATE_NOT_READY"):
        plan_publication_head_change(plan, None)


def test_manually_promoted_candidate_requires_fresh_digest_and_verified_core_readback():
    plan = candidate()
    plan.update(
        business_publishability_status="PUBLISHABLE_BUSINESS_SNAPSHOT",
        global_requiredness_status="PASS_PUBLISHABLE_BUSINESS_SNAPSHOT",
    )
    with pytest.raises(CandidatePlanError, match="CANDIDATE_DIGEST_MISMATCH"):
        plan_publication_head_change(plan, None)

    # Recomputing a plain digest does not manufacture the missing PG-backed
    # daily core result or authorize a publication Head CAS.
    from workbench_service.current_v4_context import canonical, digest
    plan["candidate_digest"] = digest(canonical({key: value for key, value in plan.items() if key != "candidate_digest"}))
    with pytest.raises(CandidatePlanError, match="CORE_RESULT_PG_READBACK_REQUIRED"):
        plan_publication_head_change(plan, None)

    # A forged dict with the old advertised status is not PG evidence. Only the
    # typed object emitted by read_daily_core_result can unlock the planner.
    with pytest.raises(CandidatePlanError, match="CORE_RESULT_PG_READBACK_REQUIRED"):
        plan_publication_head_change(plan, None, verified_core_result={
            "status": "PG_READBACK_VERIFIED", "publishable": True,
            "contract_id": "V4_DAILY_CORE_RESULT_BINDING_R6",
            "publication_id": plan["publication_id"], "publication_revision": plan["revision_no"],
            "trade_date": plan["trade_date"], "source_manifest_sha256": plan["source_manifest_sha256"],
            "result_sha256": "1" * 64, "row_count": 1,
        })


def test_candidate_rejects_package_scope_t0_and_future_observation_mismatch():
    with pytest.raises(CandidatePlanError, match="CANDIDATE_SOURCE_MANIFEST_UNVERIFIED"):
        candidate(source_manifest_rows=[source_row(source_package_accepted_scope="REJECTED")])
    with pytest.raises(CandidatePlanError, match="SOURCE_PACKAGE_T0_MISMATCH"):
        candidate(source_manifest_sha256=None, source_manifest_rows=[source_row(source_package_target_trade_date=date(2026, 10, 14))])
    with pytest.raises(CandidatePlanError, match="FUTURE_TRADE_DATE_WITHOUT_SAME_DAY_SOURCE_OBSERVATION"):
        candidate(source_manifest_sha256=None, source_manifest_rows=[source_row(source_package_page_observed_at=datetime(2026, 10, 14, 15, 0, tzinfo=timezone.utc))])
    with pytest.raises(CandidatePlanError, match="INVALID_TRADE_DATE"):
        candidate(trade_date="20261015")


def test_head_planner_blocks_metadata_ready_without_business_result_binding():
    first = candidate()
    assert first["metadata_readiness_status"] == "SOURCE_AND_IDENTITY_VALIDATED"
    assert first["business_publishability_status"] == "BLOCKED_CORE_RESULT_NOT_BOUND"
    with pytest.raises(CandidatePlanError, match="CANDIDATE_NOT_READY"):
        plan_publication_head_change(first, None)


def test_head_planner_keeps_cas_unreachable_until_business_snapshot_is_verified():
    first = candidate()
    wrong_parent = candidate(publication_id="candidate-r2", revision_no=2, same_day_revision_parent_id="other")
    with pytest.raises(CandidatePlanError, match="CANDIDATE_NOT_READY"):
        plan_publication_head_change(wrong_parent, {
            "trade_date": first["trade_date"], "model_namespace_id": first["model_namespace_id"],
            "publication_id": first["publication_id"], "revision_no": 1,
            "publication_lineage_id": first["publication_lineage_id"],
            "state_head_id": first["state_head_id"], "state_logical_digest": first["state_logical_digest"],
        })
    gap = candidate(publication_id="candidate-r4", revision_no=4, same_day_revision_parent_id=first["publication_id"])
    with pytest.raises(CandidatePlanError, match="CANDIDATE_NOT_READY"):
        plan_publication_head_change(gap, {
            "trade_date": first["trade_date"], "model_namespace_id": first["model_namespace_id"],
            "publication_id": first["publication_id"], "revision_no": 1,
            "publication_lineage_id": first["publication_lineage_id"],
            "state_head_id": first["state_head_id"], "state_logical_digest": first["state_logical_digest"],
        })
