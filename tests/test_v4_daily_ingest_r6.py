import hashlib
import json

import pytest

from workbench_db.v4_daily_source_ingest_r6 import (
    SourceIngestError,
    build_source_ingest_plan,
)


def _json_bytes(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def _write(root, relative, value):
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = value if isinstance(value, bytes) else _json_bytes(value)
    path.write_bytes(raw)
    return {"path": relative, "sha256": hashlib.sha256(raw).hexdigest()}


def _frozen_inputs(root, *, as_recorded=False, pit_eligible=False):
    day = "2026-10-16"
    tdx = _write(root, "data/v4/frozen/tdx.json", {
        "target_session": day,
        "target_bars": [{"trade_date": day, "source_security_key": "SH.600000", "close": 10.0}],
    })
    bao = _write(root, "data/v4/frozen/bao.json", {
        "target_date": day, "daily_rows": [{"code": "sh.600000"}], "adjustment_factor_rows": [],
    })
    runtime = _write(root, "data/v4/frozen/runtime.json", {"target_date": day, "status": "ACCEPTED"})
    freeze_doc = {
        "contract_id": "DYNAMIC_DAILY_SOURCE_FREEZE_V1", "target_session": day,
        "observed_at": "2026-10-16T12:00:00+00:00", "AS_RECORDED": as_recorded,
        "PIT_ELIGIBLE": pit_eligible, "canonical_qfq_authority": "TDX_GBBQ_UNCHANGED",
        "factor_role": "AUDIT_FACT_NOT_CANONICAL_QFQ_AUTHORITY",
        "tdx": tdx, "native_baostock": bao, "runtime_manifest": runtime,
    }
    freeze = _write(root, "data/v4/frozen/freeze.json", freeze_doc)
    ready_doc = {
        "contract_id": "V4_DAILY_SOURCE_READINESS_V2", "trade_date": day, "source_ready": True,
        "AS_RECORDED": as_recorded, "PIT_ELIGIBLE": pit_eligible,
        "source_freeze": {"sha256": freeze["sha256"]},
    }
    readiness = _write(root, "data/v4/frozen/readiness.json", ready_doc)
    return day, freeze, readiness, freeze_doc


def _receipt(day, freeze, readiness, *, accepted_at="2026-10-16T13:00:00+00:00"):
    value = {
        "contract_id": "V4_DAILY_SOURCE_ACCEPTANCE_RECEIPT_R1",
        "acceptance_id": "accept-r1-001", "trade_date": day,
        "source_freeze_sha256": freeze["sha256"],
        "source_readiness_sha256": readiness["sha256"],
        "source_ready": True, "as_recorded": True, "pit_eligible": True,
        "accepted_at": accepted_at,
    }
    value["receipt_sha256"] = hashlib.sha256(_json_bytes(value)).hexdigest()
    return value


def test_actual_style_freeze_stays_diagnostic_without_accepted_pit_receipt(tmp_path):
    day, freeze, readiness, _ = _frozen_inputs(tmp_path)
    plan = build_source_ingest_plan(
        tmp_path, trade_date=day, source_freeze=freeze, source_readiness=readiness,
        acceptance_receipt=_receipt(day, freeze, readiness),
    )
    assert plan["status"] == "DIAGNOSTIC_ONLY"
    assert plan["readiness_status"] == "SOURCE_PIT_AUTHORITY_UNAVAILABLE"
    assert plan["capture_status"] == "CAPTURED"
    assert plan["write_mode"] == "PLAN_ONLY_NO_DATABASE_IO"
    assert {row["source_key"] for row in plan["source_facts"]} == {"tdx", "native_baostock", "runtime_manifest"}


def test_self_hashed_receipt_cannot_create_acceptance_authority(tmp_path):
    day, freeze, readiness, _ = _frozen_inputs(tmp_path, as_recorded=True, pit_eligible=True)
    receipt = _receipt(day, freeze, readiness)
    plan = build_source_ingest_plan(
        tmp_path, trade_date=day, source_freeze=freeze, source_readiness=readiness,
        acceptance_receipt=receipt,
    )
    assert plan["status"] == "DIAGNOSTIC_ONLY"
    assert plan["acceptance_status"] == "INDEPENDENT_ACCEPTANCE_AUTHORITY_UNAVAILABLE"
    assert plan["package_manifest"]["acceptance_receipt_id"] is None
    assert all("acceptance_receipt_id" not in fact for fact in plan["source_facts"])

    receipt["source_freeze_sha256"] = "0" * 64
    rejected = build_source_ingest_plan(
        tmp_path, trade_date=day, source_freeze=freeze, source_readiness=readiness,
        acceptance_receipt=receipt,
    )
    assert rejected["status"] == "DIAGNOSTIC_ONLY"

    (tmp_path / freeze["path"]).write_bytes(b"changed")
    with pytest.raises(SourceIngestError, match="SOURCE_FREEZE_DIGEST_MISMATCH"):
        build_source_ingest_plan(tmp_path, trade_date=day, source_freeze=freeze)


class _AtomicityFakePg:
    """Small cursor double records that detected replay conflicts roll back."""

    def __init__(self):
        self.writes = 0
        self.statements = []
        self.consumed_reads = 0

    def execute(self, sql, params=None):
        self.statements.append((sql, params))
        normalized = " ".join(sql.split()).lower()
        if normalized.startswith("select revision_no from v4.publications"):
            return _Row((3,))
        if normalized.startswith("select package_id, package_sha256, manifest, accepted_scope"):
            return _Row(None)
        if normalized.startswith("select logical_fact_id,revision_no,digest,payload"):
            return _Row(None)
        if normalized.startswith("select revision_no,source_revision_id from v4.source_revisions"):
            return _Row(None)
        if normalized.startswith("select source_revision_id,digest from v4.publication_consumed_sources"):
            self.consumed_reads += 1
            return _Row(None if self.consumed_reads == 1 else ("different-revision", "f" * 64))
        if normalized.startswith(("insert", "update", "delete")):
            self.writes += 1
        if normalized.startswith("rollback to savepoint"):
            self.writes = 0
        return _Row(None)


class _Row:
    def __init__(self, value):
        self.value = value

    def fetchone(self):
        return self.value


def test_detected_conflict_rolls_back_all_prior_plan_writes(tmp_path, monkeypatch):
    import workbench_db.v4_daily_source_ingest_r6 as ingest

    from workbench_db.v4_daily_source_ingest_r6 import (
        SourceIngestConflict,
        _persist_accepted_source_ingest_plan_transaction,
        persist_source_ingest_plan,
    )

    facts = []
    for key in ("tdx", "native_baostock"):
        facts.append({
            "source_key": key, "logical_fact_id": "daily-source:2026-10-16:" + key,
            "fact_digest": key[0] * 64, "source_fact_sha256": key[0] * 64,
            "record_locator": {"path": key + ".json"}, "record_count": 1, "byte_count": 10,
        })
    manifest = {
        "accepted_scope": "ACCEPTED_SOURCE_PACKAGE", "source_observed_at": "2026-10-16T12:00:00+00:00",
        "source_freeze_sha256": "a" * 64, "acceptance_receipt_id": "authority-ref",
    }
    plan = {
        "contract_id": "V4_DAILY_SOURCE_INGEST_ADAPTER_R6", "status": "ACCEPTED",
        "package_id": "pkg", "package_sha256": "b" * 64, "trade_date": "2026-10-16",
        "package_manifest": manifest, "source_facts": facts,
    }
    public_pg = _AtomicityFakePg()
    with pytest.raises(SourceIngestError, match="INDEPENDENT_ACCEPTANCE_AUTHORITY_UNAVAILABLE"):
        persist_source_ingest_plan(
            public_pg, plan, publication_id="pub-1", publication_revision=3,
            ingested_at="2026-10-16T12:30:00+00:00",
            system_available_at="2026-10-16T12:31:00+00:00",
        )
    assert public_pg.statements == []

    internal_pg = _AtomicityFakePg()
    with pytest.raises(SourceIngestError, match="INDEPENDENT_ACCEPTANCE_AUTHORITY_UNAVAILABLE"):
        _persist_accepted_source_ingest_plan_transaction(
            internal_pg, plan, publication_id="pub-1", publication_revision=3,
            ingested_at="2026-10-16T12:30:00+00:00",
            system_available_at="2026-10-16T12:31:00+00:00",
        )
    assert internal_pg.statements == []

    # Exercise only the transaction rollback mechanics with an explicit test
    # verifier; this does not model or claim a production acceptance authority.
    plan_digest = hashlib.sha256(_json_bytes(plan)).hexdigest()
    monkeypatch.setattr(
        ingest, "_verify_independent_acceptance_authority",
        lambda _plan: ingest._IndependentAcceptanceProof(plan_digest, "TEST_ONLY_ATOMICITY_FIXTURE"),
    )

    pg = _AtomicityFakePg()
    with pytest.raises(SourceIngestConflict, match="PUBLICATION_CONSUMED_SOURCE_CONFLICT"):
        _persist_accepted_source_ingest_plan_transaction(
            pg, plan, publication_id="pub-1", publication_revision=3,
            ingested_at="2026-10-16T12:30:00+00:00",
            system_available_at="2026-10-16T12:31:00+00:00",
        )
    assert pg.writes == 0
    assert any("ROLLBACK TO SAVEPOINT" in sql for sql, _ in pg.statements)
    assert not any("revision=%s" in sql for sql, _ in pg.statements)
    consumed_sql = [sql for sql, _ in pg.statements if "publication_consumed_sources" in sql]
    assert all("source_key=%s" in sql or "(publication_id, source_key," in sql for sql in consumed_sql)


def test_source_readiness_must_bind_exact_freeze_and_t0(tmp_path):
    day, freeze, readiness, _ = _frozen_inputs(tmp_path)
    path = tmp_path / readiness["path"]
    doc = json.loads(path.read_bytes())
    doc["source_freeze"]["sha256"] = "1" * 64
    path.write_bytes(_json_bytes(doc))
    readiness["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    with pytest.raises(SourceIngestError, match="SOURCE_READINESS_FREEZE_BINDING_MISMATCH"):
        build_source_ingest_plan(tmp_path, trade_date=day, source_freeze=freeze, source_readiness=readiness)
