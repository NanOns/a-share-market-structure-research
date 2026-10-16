from contextlib import contextmanager
from datetime import date, datetime, timezone

import pytest

from workbench_db.v4_publication_candidate import (
    CandidatePlanError,
    build_publication_candidate,
    plan_publication_head_change,
)
from workbench_db.v4_publication_reader import (
    PgPublicationReader,
    PublicationReadError,
    reader_dsn,
)


DATABASE_IDENTITY = {"database": "market_research", "database_oid": 16384, "host": "127.0.0.1", "port": 5432}
DIGEST = "a" * 64


def publication_row(**changes):
    row = (
        "pub-20261015-r1", 1, date(2026, 10, 15), "v4-main", "ACCEPTED",
        datetime(2026, 10, 15, 9, 0, tzinfo=timezone.utc), 1, DIGEST, "b" * 64,
    )
    return tuple(changes.get(i, value) for i, value in enumerate(row))


def binding_row(**changes):
    row = (
        "entity", DATABASE_IDENTITY, "v4_core_abc123",
        "owner_records", "owner-token-r1", date(2026, 10, 15), "CORE_OWNER_R1",
        "c" * 64, 10, "DEGRADED", False, False,
    )
    return tuple(changes.get(i, value) for i, value in enumerate(row))


class Cursor:
    def __init__(self, one=None, all_rows=None):
        self.one = one
        self.all_rows = all_rows or []

    def fetchone(self):
        return self.one

    def fetchall(self):
        return self.all_rows


class FakeConnection:
    def __init__(self, *, head=None, bindings=None, identity=None, missing_bindings=False):
        self.head = head
        self.bindings = bindings or []
        self.identity = identity or ("market_research", 16384, "127.0.0.1", 5432)
        self.missing_bindings = missing_bindings
        self.statements = []

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def execute(self, statement, params=None):
        self.statements.append((statement, params))
        if "FROM v4.publication_heads" in statement:
            return Cursor(one=self.head)
        if "inet_server_addr()" in statement:
            return Cursor(one=self.identity)
        if "FROM v4.publication_module_results" in statement:
            if self.missing_bindings:
                error = RuntimeError("relation missing")
                error.sqlstate = "42P01"
                raise error
            return Cursor(all_rows=self.bindings)
        raise AssertionError(f"unexpected SQL: {statement}")


def reader_for(connection, **kwargs):
    @contextmanager
    def factory():
        with connection as pg:
            yield pg

    return PgPublicationReader(
        connection_factory=factory,
        expected_database_identity=DATABASE_IDENTITY,
        **kwargs,
    )


def test_reader_dsn_never_falls_back_to_writer():
    with pytest.raises(PublicationReadError, match="PG_READ_ENV_UNAVAILABLE"):
        reader_dsn({"V4_NATIVE_PG_DSN": "writer-secret"})
    assert reader_dsn({"WORKBENCH_PG_DSN": "reader"}) == "reader"
    assert reader_dsn({"V4_NATIVE_PG_READER_DSN": "reader-role", "WORKBENCH_PG_DSN": "other"}) == "reader-role"


def test_no_head_fails_closed_without_owner_query():
    connection = FakeConnection()
    reader = reader_for(connection)
    with pytest.raises(PublicationReadError, match="NO_ACCEPTED_PUBLICATION"):
        reader.read_context(
            trade_date="2026-10-15",
            model_namespace_id="v4-main",
            required_modules={"entity": "REQUIRED"},
        )
    assert not any("publication_module_results" in sql for sql, _ in connection.statements)


def test_reader_returns_exact_bound_publication_and_preserves_quality():
    connection = FakeConnection(head=publication_row(), bindings=[binding_row()])
    reader = reader_for(connection)
    result = reader.read_context(
        trade_date="2026-10-15",
        model_namespace_id="v4-main",
        required_modules={"entity": "REQUIRED", "settlement": "OPTIONAL"},
    )
    assert result["candidate_only"] is True
    assert result["publication_id"] == "pub-20261015-r1"
    assert result["revision"] == 1
    assert result["module_results"]["entity"]["quality_status"] == "DEGRADED"
    assert result["module_results"]["entity"]["as_recorded"] is False
    assert result["module_results"]["entity"]["pit_eligible"] is False
    assert len(result["module_results_digest"]) == 64
    assert result["module_requirements"]["settlement"] == "OPTIONAL"
    assert result["context_token"].startswith("pg-candidate-")


def test_shared_context_token_pins_later_page_reads_to_same_snapshot():
    first = FakeConnection(head=publication_row(), bindings=[binding_row()])
    context = reader_for(first).read_context(
        trade_date="2026-10-15", model_namespace_id="v4-main",
        required_modules={"entity": "REQUIRED"},
    )
    same = FakeConnection(head=publication_row(), bindings=[binding_row()])
    repeated = reader_for(same).read_context(
        trade_date="2026-10-15", model_namespace_id="v4-main",
        required_modules={"entity": "REQUIRED"},
        expected_publication=(context["publication_id"], context["revision"]),
        expected_context_token=context["context_token"],
    )
    assert repeated["context_token"] == context["context_token"]
    rows = list(binding_row())
    rows[7] = "e" * 64
    changed = FakeConnection(head=publication_row(), bindings=[tuple(rows)])
    with pytest.raises(PublicationReadError, match="STALE_CONTEXT_REQUIRES_REFRESH"):
        reader_for(changed).read_context(
            trade_date="2026-10-15", model_namespace_id="v4-main",
            required_modules={"entity": "REQUIRED"},
            expected_publication=(context["publication_id"], context["revision"]),
            expected_context_token=context["context_token"],
        )


def test_missing_required_module_is_not_filled_from_other_date_or_revision():
    connection = FakeConnection(head=publication_row(), bindings=[])
    with pytest.raises(PublicationReadError, match="MODULE_RESULT_UNBOUND"):
        reader_for(connection).read_context(
            trade_date="2026-10-15",
            model_namespace_id="v4-main",
            required_modules={"entity": "REQUIRED"},
        )


def test_stale_publication_selector_fails_closed():
    connection = FakeConnection(head=publication_row())
    with pytest.raises(PublicationReadError, match="PUBLICATION_IDENTITY_MISMATCH"):
        reader_for(connection).read_context(
            trade_date="2026-10-15",
            model_namespace_id="v4-main",
            required_modules={"entity": "REQUIRED"},
            expected_publication=("older-publication", 1),
        )


def test_system_identity_mismatch_blocks_bindings():
    connection = FakeConnection(head=publication_row(), identity=("market_research", 99, "127.0.0.1", 5432))
    with pytest.raises(PublicationReadError, match="PG_DATABASE_IDENTITY_MISMATCH"):
        reader_for(connection).read_context(
            trade_date="2026-10-15",
            model_namespace_id="v4-main",
            required_modules={"entity": "REQUIRED"},
        )
    assert not any("publication_module_results" in sql for sql, _ in connection.statements)


def test_binding_schema_missing_is_explicit_and_never_falls_back():
    connection = FakeConnection(head=publication_row(), missing_bindings=True)
    with pytest.raises(PublicationReadError, match="MODULE_RESULT_BINDING_SCHEMA_UNAVAILABLE"):
        reader_for(connection).read_context(
            trade_date="2026-10-15",
            model_namespace_id="v4-main",
            required_modules={"entity": "REQUIRED"},
        )


def test_unsafe_owner_locator_is_rejected_without_dynamic_sql():
    unsafe = list(binding_row())
    unsafe[3] = "x;drop_schema"
    connection = FakeConnection(head=publication_row(), bindings=[tuple(unsafe)])
    with pytest.raises(PublicationReadError, match="INVALID_OWNER_LOCATOR"):
        reader_for(connection).read_context(
            trade_date="2026-10-15",
            model_namespace_id="v4-main",
            required_modules={"entity": "REQUIRED"},
        )
    assert all("x;drop_schema" not in sql for sql, _ in connection.statements)


def test_required_payload_resolver_must_verify_owner_identity_in_same_transaction():
    connection = FakeConnection(head=publication_row(), bindings=[binding_row()])
    def resolver(pg, binding):
        assert pg is connection
        return {
            "database_identity": binding["database_identity"],
            "owner_schema": binding["owner_schema"],
            "owner_relation": binding["owner_relation"],
            "owner_version_token": binding["owner_version_token"],
            "owner_trade_date": binding["owner_trade_date"],
            "owner_contract_id": binding["owner_contract_id"],
            "result_digest": binding["result_digest"],
            "row_count": binding["row_count"],
            "payload": [{"id": "x"}],
        }
    result = reader_for(connection, owner_readers={"entity": resolver}).read_context(
        trade_date="2026-10-15",
        model_namespace_id="v4-main",
        required_modules={"entity": "REQUIRED"},
        resolve_payloads=True,
    )
    assert result["module_payloads"]["entity"] == [{"id": "x"}]


def test_owner_payload_identity_mismatch_blocks_projection():
    connection = FakeConnection(head=publication_row(), bindings=[binding_row()])
    wrong = lambda pg, binding: {
        "database_identity": DATABASE_IDENTITY,
        "owner_schema": "v4_core_abc123", "owner_relation": "owner_records",
        "owner_version_token": "different-token", "owner_trade_date": "2026-10-15",
        "owner_contract_id": "CORE_OWNER_R1", "result_digest": "c" * 64,
        "row_count": 10, "payload": [],
    }
    with pytest.raises(PublicationReadError, match="OWNER_READBACK_IDENTITY_MISMATCH"):
        reader_for(connection, owner_readers={"entity": wrong}).read_context(
            trade_date="2026-10-15",
            model_namespace_id="v4-main",
            required_modules={"entity": "REQUIRED"},
            resolve_payloads=True,
        )


def test_requiredness_unknown_blocks_candidate_read():
    reader = reader_for(FakeConnection(head=publication_row()))
    with pytest.raises(PublicationReadError, match="MODULE_REQUIREDNESS_UNKNOWN"):
        reader.read_context(
            trade_date="2026-10-15",
            model_namespace_id="v4-main",
            required_modules={"entity": "UNKNOWN"},
        )


def candidate(**overrides):
    args = dict(
        publication_id="candidate-20261015-r1",
        trade_date="2026-10-15",
        revision=1,
        model_namespace_id="v4-main",
        core_revision=1,
        source_manifest_sha256="a" * 64,
        computation_identity_sha256="b" * 64,
        expected_source_bindings={"tdx_daily": {"source_revision_id": "src-r1", "digest": "d" * 64}},
        observed_source_bindings={"tdx_daily": {"source_revision_id": "src-r1", "digest": "d" * 64}},
        module_requirements={"entity": "REQUIRED", "settlement": "OPTIONAL"},
        module_results=[{
            "module_key": "entity", "database_identity": DATABASE_IDENTITY,
            "owner_schema": "v4_core_abc123",
            "owner_relation": "owner_records", "owner_version_token": "owner-token-r1",
            "owner_trade_date": "2026-10-15", "owner_contract_id": "CORE_OWNER_R1",
            "result_digest": "c" * 64, "row_count": 10, "quality_status": "DEGRADED",
            "as_recorded": False, "pit_eligible": False,
        }],
    )
    args.update(overrides)
    return build_publication_candidate(**args)


def test_candidate_plan_is_never_accepted_and_preserves_quality_flags():
    plan = candidate()
    assert plan["status"] == "CANDIDATE_READY"
    assert plan["publish_status"] == "CANDIDATE"
    assert plan["accepted_at"] is None
    assert plan["head_update"] == "NOT_AUTHORIZED_BY_PLAN"
    result = plan["module_results"][0]
    assert result["quality_status"] == "DEGRADED"
    assert result["as_recorded"] is False and result["pit_eligible"] is False
    assert len(plan["candidate_digest"]) == 64


def test_candidate_plan_marks_missing_required_and_unknown_contracts_incomplete():
    missing = candidate(module_results=[])
    assert missing["status"] == "CANDIDATE_INCOMPLETE"
    assert missing["missing_required_modules"] == ["entity"]
    unknown = candidate(module_requirements={"entity": "UNKNOWN"})
    assert unknown["status"] == "CANDIDATE_INCOMPLETE"
    assert unknown["unknown_requiredness_modules"] == ["entity"]


def test_candidate_plan_rejects_duplicate_or_uncontracted_modules():
    row = candidate()["module_results"][0]
    with pytest.raises(CandidatePlanError, match="DUPLICATE_MODULE_RESULT"):
        candidate(module_results=[row, row])
    with pytest.raises(CandidatePlanError, match="MODULE_NOT_IN_CONTRACT"):
        candidate(module_results=[{**row, "module_key": "other"}])


def test_candidate_plan_rejects_invalid_identity_or_digest():
    with pytest.raises(CandidatePlanError, match="SOURCE_MANIFEST_DIGEST_INVALID"):
        candidate(source_manifest_sha256="not-a-digest")
    rows = candidate()["module_results"]
    with pytest.raises(CandidatePlanError, match="INVALID_OWNER_LOCATOR"):
        candidate(module_results=[{**rows[0], "owner_relation": "x;drop"}])


def test_source_sha_mismatch_blocks_candidate():
    with pytest.raises(CandidatePlanError, match="SOURCE_IDENTITY_MISMATCH"):
        candidate(observed_source_bindings={"tdx_daily": {"source_revision_id": "src-r1", "digest": "e" * 64}})


def test_same_day_revision_requires_exact_prior_head_and_returns_cas_plan():
    next_revision = candidate(
        publication_id="candidate-20261015-r2",
        revision=2,
        prior_publication=("candidate-20261015-r1", 1),
    )
    plan = plan_publication_head_change(
        next_revision,
        {
            "trade_date": "2026-10-15", "model_namespace_id": "v4-main",
            "publication_id": "candidate-20261015-r1", "revision": 1,
        },
    )
    assert plan["action"] == "CAS_UPDATE"
    assert plan["expected_prior_head"] == {"publication_id": "candidate-20261015-r1", "revision": 1}
    assert plan["write_executed"] is False


def test_competing_same_day_publication_fails_exact_cas_precondition():
    next_revision = candidate(
        publication_id="candidate-20261015-r4",
        revision=4,
        prior_publication=("candidate-20261015-r1", 1),
    )
    with pytest.raises(CandidatePlanError, match="PUBLICATION_REVISION_NOT_NEXT"):
        plan_publication_head_change(
            next_revision,
            {
                "trade_date": "2026-10-15", "model_namespace_id": "v4-main",
                "publication_id": "candidate-20261015-r2", "revision": 2,
            },
        )


def test_competitor_that_advanced_to_expected_revision_invalidates_parent_cas():
    next_revision = candidate(
        publication_id="candidate-20261015-r3",
        revision=3,
        prior_publication=("candidate-20261015-r1", 1),
    )
    with pytest.raises(CandidatePlanError, match="HEAD_CAS_PRECONDITION_MISMATCH"):
        plan_publication_head_change(
            next_revision,
            {
                "trade_date": "2026-10-15", "model_namespace_id": "v4-main",
                "publication_id": "candidate-20261015-r2", "revision": 2,
            },
        )


def test_idempotent_replay_requires_same_publication_source_and_compute_identity():
    same = candidate()
    current = {
        "trade_date": "2026-10-15", "model_namespace_id": "v4-main",
        "publication_id": "candidate-20261015-r1", "revision": 1,
        "source_manifest_sha256": "a" * 64,
        "computation_identity_sha256": "b" * 64,
        "module_results_digest": same["module_results_digest"],
    }
    assert plan_publication_head_change(same, current)["action"] == "IDEMPOTENT_REPLAY"
    current["source_manifest_sha256"] = "d" * 64
    with pytest.raises(CandidatePlanError, match="PUBLICATION_IDENTITY_CONFLICT"):
        plan_publication_head_change(same, current)


def test_idempotent_retry_requires_module_binding_digest_readback():
    plan = candidate()
    current = {
        "trade_date": plan["trade_date"], "model_namespace_id": plan["model_namespace_id"],
        "publication_id": plan["publication_id"], "revision": plan["revision"],
        "source_manifest_sha256": plan["source_manifest_sha256"],
        "computation_identity_sha256": plan["computation_identity_sha256"],
    }
    with pytest.raises(CandidatePlanError, match="IDEMPOTENT_IDENTITY_UNVERIFIED"):
        plan_publication_head_change(plan, current)


def test_new_trade_date_is_not_implicitly_accepted_as_contiguous():
    new_date = candidate(
        publication_id="candidate-20261016-r1",
        trade_date="2026-10-16",
        prior_session_state_head="state-head-20261015-r1",
    )
    plan = plan_publication_head_change(new_date, None)
    assert plan["action"] == "INSERT_IF_ABSENT"
    assert plan["prior_session_state_head"] == "state-head-20261015-r1"
    assert plan["initial_boundary_review_required"] is False
    assert plan["write_executed"] is False


def test_first_publication_without_prior_state_is_marked_for_boundary_review():
    plan = plan_publication_head_change(candidate(), None)
    assert plan["action"] == "INSERT_IF_ABSENT"
    assert plan["initial_boundary_review_required"] is True
    assert plan["write_executed"] is False
