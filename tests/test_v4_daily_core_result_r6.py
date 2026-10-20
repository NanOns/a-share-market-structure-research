import hashlib
import json
from datetime import date, datetime, timezone

import pytest

from workbench_db.v4_daily_core_result_r6 import (
    CoreResultError, DAILY_COMPLETENESS_CONTRACT, VerifiedDailyCoreResult, build_daily_core_result_plan,
    is_verified_daily_core_result, persist_daily_core_result, read_daily_core_result,
)


def _canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def _sha(value):
    return hashlib.sha256(_canonical(value)).hexdigest()


def _input():
    producer_sha = "a" * 64
    fact_digest = "d" * 64
    source_fact_sha = "e" * 64
    package_sha = "c" * 64
    locator = {"path": "data/source/tdx_day.bin", "role": "TDX_TARGET"}
    manifest_row = {
        "source_key": "tdx", "source_revision_id": "v4sr-tdx-r1", "digest": fact_digest,
        "logical_fact_id": "daily-source:2026-10-15:tdx", "revision_no": 1,
        "revision_digest": fact_digest, "effective_from": date.fromisoformat("2026-10-15"),
        "effective_to": date.fromisoformat("2026-10-15"),
        "provider_available_at": datetime(2026, 10, 15, 9, tzinfo=timezone.utc),
        "observed_at": datetime(2026, 10, 15, 10, tzinfo=timezone.utc),
        "ingested_at": datetime(2026, 10, 15, 10, 1, tzinfo=timezone.utc),
        "system_available_at": datetime(2026, 10, 15, 10, 1, tzinfo=timezone.utc),
        "tombstone": False, "source_package_id": "pkg-r1",
        "source_package_contract_version": "V4_DAILY_SOURCE_INGEST_R6/1.2.0",
        "source_package_sha256": package_sha,
        "source_package_page_observed_at": datetime(2026, 10, 15, 9, tzinfo=timezone.utc),
        "source_package_target_trade_date": date.fromisoformat("2026-10-15"),
        "source_package_parser_version": "V4_DAILY_SOURCE_INGEST_R6",
        "source_package_accepted_scope": "ACCEPTED_SOURCE_PACKAGE",
    }
    from workbench_db.v4_source_manifest import build_source_manifest
    source_sha = build_source_manifest([manifest_row])["source_manifest_sha256"]
    artifact_binding = {
        "source_key": "tdx", "source_revision_id": "v4sr-tdx-r1",
        "source_package_id": "pkg-r1", "package_sha256": package_sha,
        "logical_fact_id": "daily-source:2026-10-15:tdx", "fact_digest": fact_digest,
        "source_fact_sha256": source_fact_sha, "acceptance_receipt_id": "accepted-r1",
        "target_trade_date": "2026-10-15", "record_locator": locator, "record_count": 1,
    }
    receipt = {
        "trade_date": "2026-10-15", "producer_contract_id": "V4_OPERATIONAL_DAILY_OWNER_R1",
        "producer_sha256": producer_sha, "publication_id": "pub-20261016-r1",
        "publication_revision": 1, "source_manifest_sha256": source_sha,
        "source_artifact_bindings": [artifact_binding],
    }
    receipt["receipt_sha256"] = _sha(receipt)
    rows = [{
        "trade_date": "2026-10-15", "security_id": "SH.600000", "security_type": "STOCK",
        "trade_status": "TRADING", "open": 9.8, "high": 10.2, "low": 9.7,
        "close": 10.0, "volume": 1000, "amount": 1_000_000,
        "turnover_rate": None, "turnover_status": "TURNOVER_UNAVAILABLE",
        "ma5": None, "ma20": None, "ma60": None,
        "history_status": "INSUFFICIENT_NEW_LISTING_HISTORY",
        "price_basis": "TDX_GBBQ_UNCHANGED", "source_revision_id": "v4sr-tdx-r1",
        "profile_payload": {"label": "CORE"}, "quality_status": "ACTUAL_PRODUCER_ROW",
    }]
    return receipt, rows, source_sha, producer_sha


def _pg(plan, *, proof_rows=None, proof_overrides=None,
        isolation="repeatable read", read_only="on"):
    receipt, _, source_sha, producer_sha = _input()
    row = plan["rows"][0]
    db_row = tuple(date.fromisoformat(row[key]) if key == "trade_date" else row[key] for key in (
        "trade_date", "security_id", "security_type", "trade_status", "open", "high", "low", "close",
        "volume", "amount", "turnover_rate", "turnover_status", "ma5", "ma20", "ma60",
        "history_status", "price_basis", "source_revision_id", "profile_payload", "quality_status", "row_sha256",
    ))
    artifact = receipt["source_artifact_bindings"][0]
    fact = {
        "source_key": artifact["source_key"], "logical_fact_id": artifact["logical_fact_id"],
        "fact_digest": artifact["fact_digest"], "source_fact_sha256": artifact["source_fact_sha256"],
        "record_locator": artifact["record_locator"], "record_count": artifact["record_count"],
    }
    package_manifest = {"acceptance_receipt_id": artifact["acceptance_receipt_id"],
                        "AS_RECORDED": True, "PIT_ELIGIBLE": True,
                        "source_fact_bindings": [fact]}
    proof = (
        date.fromisoformat("2026-10-15"), "V4_PG_CONSUMED_SOURCE_MANIFEST_R2", source_sha,
        "tdx", artifact["source_revision_id"], artifact["fact_digest"], artifact["logical_fact_id"], 1,
        artifact["fact_digest"], date.fromisoformat("2026-10-15"), date.fromisoformat("2026-10-15"),
        datetime(2026, 10, 15, 9, tzinfo=timezone.utc), datetime(2026, 10, 15, 10, tzinfo=timezone.utc),
        datetime(2026, 10, 15, 10, 1, tzinfo=timezone.utc), datetime(2026, 10, 15, 10, 1, tzinfo=timezone.utc),
        False, artifact["source_package_id"], artifact["source_key"], artifact["fact_digest"],
        artifact["source_package_id"], "V4_DAILY_SOURCE_INGEST_R6/1.2.0", artifact["package_sha256"],
        datetime(2026, 10, 15, 9, tzinfo=timezone.utc), date.fromisoformat("2026-10-15"),
        "V4_DAILY_SOURCE_INGEST_R6", "ACCEPTED_SOURCE_PACKAGE", package_manifest,
        artifact["source_package_id"], artifact["source_key"], artifact["logical_fact_id"],
        artifact["fact_digest"], artifact["source_fact_sha256"], artifact["record_locator"],
        artifact["record_count"], artifact["acceptance_receipt_id"], "ACCEPTED",
        datetime(2026, 10, 15, 11, tzinfo=timezone.utc),
    )
    proof_fields = (
        "publication_trade_date", "source_manifest_contract_id", "publication_manifest_sha256",
        "source_key", "source_revision_id", "consumed_digest", "logical_fact_id", "revision_no",
        "revision_digest", "effective_from", "effective_to", "provider_available_at", "observed_at",
        "ingested_at", "system_available_at", "tombstone", "revision_package_id",
        "revision_package_source_key", "revision_source_fact_digest", "source_package_id",
        "source_package_contract_version", "source_package_sha256", "source_package_page_observed_at",
        "source_package_target_trade_date", "source_package_parser_version", "source_package_accepted_scope",
        "source_package_manifest", "fact_package_id", "fact_source_key", "fact_logical_fact_id",
        "fact_digest", "source_fact_sha256", "record_locator", "fact_record_count", "acceptance_receipt_id",
        "publication_status", "publication_accepted_at",
    )
    if proof_overrides:
        material = dict(zip(proof_fields, proof))
        material.update(proof_overrides)
        proof = tuple(material[key] for key in proof_fields)
    snapshot = (
        date.fromisoformat("2026-10-15"), plan["result_identity"],
        "V4_DAILY_CORE_RESULT_BINDING_R6", plan["producer_contract_id"], producer_sha,
        plan["producer_receipt_sha256"], source_sha, plan["result_sha256"], 1, 0,
        plan["completeness_contract_id"], plan["completeness_contract_version"],
        plan["completeness_status"], "CORE_RESULT_ROWS_VERIFIED_CANDIDATE",
    )

    selected_proof_rows = [proof] if proof_rows is None else proof_rows
    class PG:
        def __init__(self, *, isolation="repeatable read", read_only="on"):
            self.isolation = isolation
            self.read_only = read_only

        def execute(self, query, params=None):
            if query == "SHOW transaction_isolation":
                return type("Result", (), {"fetchone": lambda self: (self_outer.isolation,)})()
            if query == "SHOW transaction_read_only":
                return type("Result", (), {"fetchone": lambda self: (self_outer.read_only,)})()
            if "daily_core_result_snapshots" in query:
                return type("Result", (), {"fetchone": lambda self: snapshot})()
            if "daily_core_result_rows" in query:
                return type("Result", (), {"fetchall": lambda self: [db_row]})()
            assert "source_package_facts" in query
            assert "JOIN v4.source_package_facts" in query
            return type("Result", (), {"fetchall": lambda self: selected_proof_rows})()
    pg = PG(isolation=isolation, read_only=read_only)
    self_outer = pg
    return pg


def test_core_result_plan_binds_actual_rows_and_keeps_unresolved_gate_closed():
    receipt, rows, source_sha, producer_sha = _input()
    plan = build_daily_core_result_plan(
        publication_id="pub-20261016-r1", publication_revision=1,
        trade_date="2026-10-15", source_manifest_sha256=source_sha,
        producer_contract_id="V4_OPERATIONAL_DAILY_OWNER_R1", producer_sha256=producer_sha,
        producer_receipt=receipt, rows=rows,
    )
    assert plan["row_count"] == 1
    assert plan["missing_price_rows"] == 0
    assert plan["rows"][0]["turnover_status"] == "TURNOVER_UNAVAILABLE"
    assert plan["rows"][0]["history_status"] == "INSUFFICIENT_NEW_LISTING_HISTORY"
    assert plan["publishability_status"] == "BLOCKED_COMPLETENESS_CONTRACT_UNRESOLVED"
    assert plan["write_mode"] == "PLAN_ONLY_NO_DATABASE_IO"


def test_core_result_rejects_wrong_receipt_t0_and_price_basis():
    receipt, rows, source_sha, producer_sha = _input()
    receipt["trade_date"] = "2026-10-14"
    receipt["receipt_sha256"] = _sha({key: value for key, value in receipt.items() if key != "receipt_sha256"})
    with pytest.raises(CoreResultError, match="CORE_RESULT_PRODUCER_RECEIPT_BINDING_MISMATCH"):
        build_daily_core_result_plan(
            publication_id="pub-20261016-r1", publication_revision=1,
            trade_date="2026-10-15", source_manifest_sha256=source_sha,
            producer_contract_id="V4_OPERATIONAL_DAILY_OWNER_R1", producer_sha256=producer_sha,
            producer_receipt=receipt, rows=rows,
        )
    receipt, rows, source_sha, producer_sha = _input()
    rows[0]["price_basis"] = "BAOSTOCK_ADJUSTED"
    with pytest.raises(CoreResultError, match="CORE_RESULT_PRICE_BASIS_UNSUPPORTED"):
        build_daily_core_result_plan(
            publication_id="pub-20261016-r1", publication_revision=1,
            trade_date="2026-10-15", source_manifest_sha256=source_sha,
            producer_contract_id="V4_OPERATIONAL_DAILY_OWNER_R1", producer_sha256=producer_sha,
            producer_receipt=receipt, rows=rows,
        )


def test_core_readback_rejects_new_t0_r2_manifest_without_independent_signature():
    from workbench_db.v4_daily_core_result_r6 import _read_consumed_source_proofs

    receipt, rows, source_sha, producer_sha = _input()
    plan = build_daily_core_result_plan(
        publication_id="pub-20261016-r1", publication_revision=1,
        trade_date="2026-10-15", source_manifest_sha256=source_sha,
        producer_contract_id="V4_OPERATIONAL_DAILY_OWNER_R1", producer_sha256=producer_sha,
        producer_receipt=receipt, rows=rows,
    )
    pg = _pg(plan, proof_overrides={
        "publication_trade_date": date(2026, 10, 16),
        "effective_to": date(2026, 10, 16),
        "source_package_target_trade_date": date(2026, 10, 16),
    })
    with pytest.raises(CoreResultError, match="CORE_RESULT_NEW_PUBLICATION_REQUIRES_R3_MANIFEST"):
        _read_consumed_source_proofs(
            pg, publication_id="pub-20261016-r1", publication_revision=1,
            target="2026-10-16", source_manifest_sha256=source_sha,
            core_source_revision_ids={"v4sr-tdx-r1"},
        )
def test_pg_reader_returns_typed_result_with_planner_contract_fields():
    receipt, rows, source_sha, producer_sha = _input()
    plan = build_daily_core_result_plan(
        publication_id="pub-20261016-r1", publication_revision=1,
        trade_date="2026-10-15", source_manifest_sha256=source_sha,
        producer_contract_id="V4_OPERATIONAL_DAILY_OWNER_R1", producer_sha256=producer_sha,
        producer_receipt=receipt, rows=rows,
    )
    verified = read_daily_core_result(
        _pg(plan), publication_id="pub-20261016-r1", publication_revision=1,
        trade_date="2026-10-15", source_manifest_sha256=source_sha,
    )
    assert isinstance(verified, VerifiedDailyCoreResult)
    assert is_verified_daily_core_result(verified)
    assert verified.status == "PG_READBACK_VERIFIED"
    assert verified.contract_id == "V4_DAILY_CORE_RESULT_BINDING_R6"
    assert verified.source_manifest_sha256 == source_sha
    assert verified.observed_completeness_status == "CONTRACT_UNRESOLVED"
    assert verified.completeness_status == "CONTRACT_UNRESOLVED"
    assert verified.publishable is False


def test_verified_core_result_cannot_be_forged_without_reader_proof():
    from dataclasses import replace

    receipt, rows, source_sha, producer_sha = _input()
    plan = build_daily_core_result_plan(
        publication_id="pub-20261016-r1", publication_revision=1,
        trade_date="2026-10-15", source_manifest_sha256=source_sha,
        producer_contract_id="V4_OPERATIONAL_DAILY_OWNER_R1", producer_sha256=producer_sha,
        producer_receipt=receipt, rows=rows,
    )
    verified = read_daily_core_result(
        _pg(plan), publication_id="pub-20261016-r1", publication_revision=1,
        trade_date="2026-10-15", source_manifest_sha256=source_sha,
    )
    assert not is_verified_daily_core_result(replace(verified, _proof=object()))
    for change in (
        {"publishable": True}, {"status": "FAKE_READBACK"},
        {"row_count": 999}, {"source_manifest_sha256": "f" * 64},
        {"result_sha256": "f" * 64}, {"completeness_status": "PASS"},
        {"completeness_contract_id": "FORGED"},
        {"readback_receipt_sha256": "f" * 64},
    ):
        assert not is_verified_daily_core_result(replace(verified, **change))


def test_database_pass_without_independent_completeness_contract_stays_blocked():
    receipt, rows, source_sha, producer_sha = _input()
    plan = build_daily_core_result_plan(
        publication_id="pub-20261016-r1", publication_revision=1,
        trade_date="2026-10-15", source_manifest_sha256=source_sha,
        producer_contract_id="V4_OPERATIONAL_DAILY_OWNER_R1", producer_sha256=producer_sha,
        producer_receipt=receipt, rows=rows,
    )
    verified = read_daily_core_result(
        _pg(plan), publication_id="pub-20261016-r1", publication_revision=1,
        trade_date="2026-10-15", source_manifest_sha256=source_sha,
    )
    assert verified.observed_completeness_status == "CONTRACT_UNRESOLVED"
    assert verified.completeness_status == "CONTRACT_UNRESOLVED"
    assert verified.publishable is False
    assert is_verified_daily_core_result(verified)
    from workbench_db.v4_publication_candidate import (
        CandidatePlanError, MINIMUM_DAILY_PUBLICATION_CONTRACT_ID,
        plan_publication_head_change,
    )
    from workbench_service.current_v4_context import canonical, digest
    candidate = {
        "status": "METADATA_CANDIDATE_READY",
        "metadata_readiness_status": "SOURCE_AND_IDENTITY_VALIDATED",
        "business_publishability_status": "PUBLISHABLE_BUSINESS_SNAPSHOT",
        "global_requiredness_status": "PASS_PUBLISHABLE_BUSINESS_SNAPSHOT",
        "minimum_publish_contract_id": MINIMUM_DAILY_PUBLICATION_CONTRACT_ID,
        "source_manifest_sha256": source_sha,
        "publication_id": "pub-20261016-r1", "revision_no": 1,
        "trade_date": "2026-10-15", "model_namespace_id": "test-namespace",
        "same_day_revision_parent_id": None,
    }
    candidate["candidate_digest"] = digest(canonical(candidate))
    with pytest.raises(CandidatePlanError, match="CORE_RESULT_PG_READBACK_REQUIRED"):
        plan_publication_head_change(candidate, None, verified_core_result=verified)


def test_completeness_contract_evaluates_real_rows_and_rejects_unsupported_rules():
    receipt, rows, source_sha, producer_sha = _input()
    kwargs = dict(
        publication_id="pub-20261016-r1", publication_revision=1,
        trade_date="2026-10-15", source_manifest_sha256=source_sha,
        producer_contract_id="V4_OPERATIONAL_DAILY_OWNER_R1", producer_sha256=producer_sha,
        producer_receipt=receipt, rows=rows,
    )
    plan = build_daily_core_result_plan(**kwargs, completeness_contract=DAILY_COMPLETENESS_CONTRACT)
    assert plan["completeness_contract_id"] == "V4_DAILY_COMPLETENESS_R1"
    assert plan["completeness_status"] == "PASS"
    assert plan["publishability_status"] == "CORE_RESULT_COMPLETENESS_PASS"

    count_mismatch_receipt = dict(receipt)
    count_mismatch_receipt["source_artifact_bindings"] = [dict(receipt["source_artifact_bindings"][0], record_count=2)]
    count_mismatch_receipt["receipt_sha256"] = _sha({key: value for key, value in count_mismatch_receipt.items() if key != "receipt_sha256"})
    mismatch = build_daily_core_result_plan(
        **{**kwargs, "producer_receipt": count_mismatch_receipt},
        completeness_contract=DAILY_COMPLETENESS_CONTRACT,
    )
    assert mismatch["completeness_status"] == "FAIL"
    assert "CORE_SOURCE_PACKAGE_RECORD_COUNT_MISMATCH" in mismatch["completeness_reasons"]

    incomplete_rows = [dict(rows[0], close=None)]
    incomplete_rows[0]["trade_status"] = "SUSPENDED"
    failed = build_daily_core_result_plan(
        **{**kwargs, "rows": incomplete_rows}, completeness_contract=DAILY_COMPLETENESS_CONTRACT,
    )
    assert failed["completeness_status"] == "FAIL"
    assert failed["publishability_status"] == "BLOCKED_CORE_RESULT_INCOMPLETE"

    with pytest.raises(CoreResultError, match="CORE_RESULT_COMPLETENESS_CONTRACT_UNSUPPORTED"):
        build_daily_core_result_plan(**kwargs, completeness_contract={
            **DAILY_COMPLETENESS_CONTRACT, "maximum_missing_close_rows": 1,
        })


def test_positive_core_readback_plus_candidate_reaches_head_plan():
    receipt, rows, source_sha, producer_sha = _input()
    plan = build_daily_core_result_plan(
        publication_id="pub-20261016-r1", publication_revision=1,
        trade_date="2026-10-15", source_manifest_sha256=source_sha,
        producer_contract_id="V4_OPERATIONAL_DAILY_OWNER_R1", producer_sha256=producer_sha,
        producer_receipt=receipt, rows=rows, completeness_contract=DAILY_COMPLETENESS_CONTRACT,
    )
    verified = read_daily_core_result(
        _pg(plan), publication_id="pub-20261016-r1", publication_revision=1,
        trade_date="2026-10-15", source_manifest_sha256=source_sha,
    )
    assert is_verified_daily_core_result(verified)
    assert verified.completeness_status == "PASS" and verified.publishable is True
    assert verified.completeness_contract_id == "V4_DAILY_COMPLETENESS_R1"
    assert verified.completeness_contract_version == "1.0.0"

    from workbench_db.v4_publication_candidate import (
        build_publication_candidate, plan_publication_head_change,
    )
    from tests.test_v4_pg_publication_candidate import DATABASE_IDENTITY
    from workbench_db.v4_source_manifest import source_manifest_digest
    # The publication candidate binds the same independently read Core result.
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
    manifest_sha = source_manifest_digest(manifest_rows)
    assert manifest_sha == source_sha
    candidate = build_publication_candidate(
        publication_id="pub-20261016-r1", trade_date="2026-10-15", revision_no=1,
        publication_lineage_id="lineage-20261016", model_namespace_id="v4-main",
        core_revision=1, source_manifest_sha256=source_sha, source_manifest_rows=manifest_rows,
        source_manifest_contract_id="V4_PG_CONSUMED_SOURCE_MANIFEST_R2",
        computation_identity_sha256="b" * 64,
        expected_source_bindings={"tdx": {"source_revision_id": "v4sr-tdx-r1", "digest": "d" * 64}},
        observed_source_bindings={"tdx": {"source_revision_id": "v4sr-tdx-r1", "digest": "d" * 64}},
        database_identity=DATABASE_IDENTITY, module_results=[],
        state_head_id="state-20261016-r1", state_logical_digest="c" * 64,
        prior_session_gap_reason="INITIAL_BOUNDARY", verified_core_result=verified,
    )
    assert candidate["business_publishability_status"] == "PUBLISHABLE_BUSINESS_SNAPSHOT"
    head_plan = plan_publication_head_change(candidate, None, verified_core_result=verified)
    assert head_plan["action"] == "INSERT_IF_ABSENT"


def test_reader_fails_closed_when_independent_consumed_source_proof_is_missing():
    receipt, rows, source_sha, producer_sha = _input()
    plan = build_daily_core_result_plan(
        publication_id="pub-20261016-r1", publication_revision=1,
        trade_date="2026-10-15", source_manifest_sha256=source_sha,
        producer_contract_id="V4_OPERATIONAL_DAILY_OWNER_R1", producer_sha256=producer_sha,
        producer_receipt=receipt, rows=rows,
    )
    with pytest.raises(CoreResultError, match="CORE_RESULT_INDEPENDENT_SOURCE_PROOF_MISSING"):
        read_daily_core_result(
            _pg(plan, proof_rows=[]), publication_id="pub-20261016-r1",
            publication_revision=1, trade_date="2026-10-15", source_manifest_sha256=source_sha,
        )


def test_reader_rejects_stored_pass_when_accepted_package_row_count_exceeds_core_readback():
    receipt, rows, source_sha, producer_sha = _input()
    plan = build_daily_core_result_plan(
        publication_id="pub-20261016-r1", publication_revision=1,
        trade_date="2026-10-15", source_manifest_sha256=source_sha,
        producer_contract_id="V4_OPERATIONAL_DAILY_OWNER_R1", producer_sha256=producer_sha,
        producer_receipt=receipt, rows=rows, completeness_contract=DAILY_COMPLETENESS_CONTRACT,
    )
    original = _pg(plan)
    # The source fact and immutable package manifest both independently attest
    # two rows, while PG Core contains one. The stored PASS cannot override it.
    class MismatchPG:
        def execute(self, query, params=None):
            result = original.execute(query, params)
            if "source_package_facts" not in query:
                return result
            values = list(result.fetchall()[0])
            values[26] = {**values[26], "source_fact_bindings": [
                {**values[26]["source_fact_bindings"][0], "record_count": 2}
            ]}
            values[33] = 2
            return type("Result", (), {"fetchall": lambda self: [tuple(values)]})()
    with pytest.raises(CoreResultError, match="CORE_RESULT_PRODUCER_RECEIPT_SOURCE_BINDING_MISMATCH"):
        read_daily_core_result(
            MismatchPG(), publication_id="pub-20261016-r1", publication_revision=1,
            trade_date="2026-10-15", source_manifest_sha256=source_sha,
        )


@pytest.mark.parametrize("field,late", [
    ("provider_available_at", datetime(2026, 10, 15, 12, tzinfo=timezone.utc)),
    ("observed_at", datetime(2026, 10, 15, 12, tzinfo=timezone.utc)),
    ("ingested_at", datetime(2026, 10, 15, 12, tzinfo=timezone.utc)),
    ("system_available_at", datetime(2026, 10, 15, 12, tzinfo=timezone.utc)),
    ("source_package_page_observed_at", datetime(2026, 10, 15, 12, tzinfo=timezone.utc)),
])
def test_reader_rejects_any_source_clock_after_publication_accepted_at(field, late):
    receipt, rows, source_sha, producer_sha = _input()
    plan = build_daily_core_result_plan(
        publication_id="pub-20261016-r1", publication_revision=1,
        trade_date="2026-10-15", source_manifest_sha256=source_sha,
        producer_contract_id="V4_OPERATIONAL_DAILY_OWNER_R1", producer_sha256=producer_sha,
        producer_receipt=receipt, rows=rows,
    )
    with pytest.raises(CoreResultError, match="CORE_RESULT_SOURCE_AFTER_PUBLICATION_ACCEPTANCE"):
        read_daily_core_result(
            _pg(plan, proof_overrides={field: late}), publication_id="pub-20261016-r1",
            publication_revision=1, trade_date="2026-10-15", source_manifest_sha256=source_sha,
        )


def test_reader_rejects_source_package_from_another_trade_date():
    receipt, rows, source_sha, producer_sha = _input()
    plan = build_daily_core_result_plan(
        publication_id="pub-20261016-r1", publication_revision=1,
        trade_date="2026-10-15", source_manifest_sha256=source_sha,
        producer_contract_id="V4_OPERATIONAL_DAILY_OWNER_R1", producer_sha256=producer_sha,
        producer_receipt=receipt, rows=rows,
    )
    with pytest.raises(CoreResultError, match="CORE_RESULT_CONSUMED_SOURCE_ARTIFACT_MISMATCH"):
        read_daily_core_result(
            _pg(plan, proof_overrides={"source_package_target_trade_date": date.fromisoformat("2026-10-14")}),
            publication_id="pub-20261016-r1", publication_revision=1,
            trade_date="2026-10-15", source_manifest_sha256=source_sha,
        )


def test_reader_uses_publication_accepted_at_as_the_actual_source_cutoff():
    receipt, rows, source_sha, producer_sha = _input()
    plan = build_daily_core_result_plan(
        publication_id="pub-20261016-r1", publication_revision=1,
        trade_date="2026-10-15", source_manifest_sha256=source_sha,
        producer_contract_id="V4_OPERATIONAL_DAILY_OWNER_R1", producer_sha256=producer_sha,
        producer_receipt=receipt, rows=rows,
    )
    with pytest.raises(CoreResultError, match="CORE_RESULT_SOURCE_AFTER_PUBLICATION_ACCEPTANCE"):
        read_daily_core_result(
            _pg(plan, proof_overrides={
                "publication_accepted_at": datetime(2026, 10, 15, 10, tzinfo=timezone.utc),
            }), publication_id="pub-20261016-r1", publication_revision=1,
            trade_date="2026-10-15", source_manifest_sha256=source_sha,
        )


@pytest.mark.parametrize("proof_overrides,match", [
    ({"acceptance_receipt_id": ""}, "CORE_RESULT_CONSUMED_SOURCE_ARTIFACT_MISMATCH"),
    ({"source_package_manifest": {"acceptance_receipt_id": "accepted-r1",
                                  "AS_RECORDED": False, "PIT_ELIGIBLE": True,
                                  "source_fact_bindings": []}}, "CORE_RESULT_SOURCE_ACCEPTANCE_PROOF_INVALID"),
])
def test_reader_rejects_missing_or_non_pit_acceptance_proof(proof_overrides, match):
    receipt, rows, source_sha, producer_sha = _input()
    plan = build_daily_core_result_plan(
        publication_id="pub-20261016-r1", publication_revision=1,
        trade_date="2026-10-15", source_manifest_sha256=source_sha,
        producer_contract_id="V4_OPERATIONAL_DAILY_OWNER_R1", producer_sha256=producer_sha,
        producer_receipt=receipt, rows=rows,
    )
    with pytest.raises(CoreResultError, match=match):
        read_daily_core_result(
            _pg(plan, proof_overrides=proof_overrides), publication_id="pub-20261016-r1",
            publication_revision=1, trade_date="2026-10-15", source_manifest_sha256=source_sha,
        )


@pytest.mark.parametrize("isolation,read_only", [("read committed", "on"), ("repeatable read", "off")])
def test_reader_requires_same_repeatable_read_only_transaction(isolation, read_only):
    receipt, rows, source_sha, producer_sha = _input()
    plan = build_daily_core_result_plan(
        publication_id="pub-20261016-r1", publication_revision=1,
        trade_date="2026-10-15", source_manifest_sha256=source_sha,
        producer_contract_id="V4_OPERATIONAL_DAILY_OWNER_R1", producer_sha256=producer_sha,
        producer_receipt=receipt, rows=rows,
    )
    with pytest.raises(CoreResultError, match="CORE_RESULT_READ_TRANSACTION_MUST_BE_REPEATABLE_READ_ONLY"):
        read_daily_core_result(
            _pg(plan, isolation=isolation, read_only=read_only), publication_id="pub-20261016-r1",
            publication_revision=1, trade_date="2026-10-15", source_manifest_sha256=source_sha,
        )


def test_core_rows_must_reference_a_receipted_source_revision():
    receipt, rows, source_sha, producer_sha = _input()
    rows[0]["source_revision_id"] = "v4sr-not-consumed"
    with pytest.raises(CoreResultError, match="CORE_RESULT_ROW_SOURCE_NOT_IN_PRODUCER_RECEIPT"):
        build_daily_core_result_plan(
            publication_id="pub-20261016-r1", publication_revision=1,
            trade_date="2026-10-15", source_manifest_sha256=source_sha,
            producer_contract_id="V4_OPERATIONAL_DAILY_OWNER_R1", producer_sha256=producer_sha,
            producer_receipt=receipt, rows=rows,
        )


def test_core_writer_prefers_explicit_writer_dsn_and_checks_readonly_before_writing(monkeypatch):
    receipt, rows, source_sha, producer_sha = _input()
    plan = build_daily_core_result_plan(
        publication_id="pub-20261016-r1", publication_revision=1,
        trade_date="2026-10-15", source_manifest_sha256=source_sha,
        producer_contract_id="V4_OPERATIONAL_DAILY_OWNER_R1", producer_sha256=producer_sha,
        producer_receipt=receipt, rows=rows,
    )
    monkeypatch.setenv("V4_NATIVE_PG_DSN", "postgresql://writer@example.invalid/market_research")
    monkeypatch.setenv("WORKBENCH_PG_DSN", "postgresql://reader@example.invalid/market_research")
    class PG:
        def __init__(self): self.queries = []
        def execute(self, query, *args, **kwargs):
            self.queries.append(query)
            return type("Result", (), {"fetchone": lambda self: ("on",)})()
    pg = PG()
    with pytest.raises(CoreResultError, match="CORE_RESULT_WRITE_TRANSACTION_MUST_BE_WRITABLE"):
        persist_daily_core_result(pg, plan)
    assert pg.queries == ["SHOW transaction_read_only"]


def test_core_writer_rejects_read_only_transaction_before_any_write(monkeypatch):
    receipt, rows, source_sha, producer_sha = _input()
    plan = build_daily_core_result_plan(
        publication_id="pub-20261016-r1", publication_revision=1,
        trade_date="2026-10-15", source_manifest_sha256=source_sha,
        producer_contract_id="V4_OPERATIONAL_DAILY_OWNER_R1", producer_sha256=producer_sha,
        producer_receipt=receipt, rows=rows,
    )
    monkeypatch.setenv("V4_NATIVE_PG_DSN", "postgresql://writer@example.invalid/market_research")
    class PG:
        def __init__(self): self.queries=[]
        def execute(self, query, params=None):
            self.queries.append((query,params))
            return type("Result", (), {"fetchone": lambda self: ("on",)})()
    pg=PG()
    with pytest.raises(CoreResultError, match="CORE_RESULT_WRITE_TRANSACTION_MUST_BE_WRITABLE"):
        persist_daily_core_result(pg, plan)
    assert pg.queries == [("SHOW transaction_read_only", None)]
