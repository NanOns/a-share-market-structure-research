import hashlib
import json
import base64
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

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


def _frozen_inputs(root, *, day="2026-10-16", as_recorded=False, pit_eligible=False):
    tdx = _write(root, "data/v4/frozen/tdx.json", {
        "target_session": day,
        "target_bars": [{"trade_date": day, "source_security_key": "SH.600000", "close": 10.0}],
    })
    bao = _write(root, "data/v4/frozen/bao.json", {
        "target_date": day, "daily_rows": [{"code": "sh.600000"}], "adjustment_factor_rows": [],
    })
    runtime = _write(root, "data/v4/frozen/runtime.json", {"target_date": day, "status": "ACCEPTED"})
    from workbench_db.v4_market_universe_completeness_r1 import seal_universe_snapshot
    universe_doc = seal_universe_snapshot(
        trade_date=day, universe_id="TEST_MARKET_A_SHARE_T0",
        exchange_scope=["SSE", "SZSE", "BSE"],
        securities=[{"security_id": "SH.600000", "asset_class": "COMMON_STOCK",
                     "share_class": "A", "exchange": "SSE", "status": "ACTIVE",
                     "source_id": "test-security-master"}],
        source_fact_sha256="TEST_FIXTURE_SOURCE_BYTES_NOT_PROOF",
    )
    universe = _write(root, "data/v4/frozen/security_universe.json", universe_doc)
    freeze_doc = {
        "contract_id": "DYNAMIC_DAILY_SOURCE_FREEZE_V1", "target_session": day,
        "observed_at": day + "T07:15:00+00:00", "AS_RECORDED": as_recorded,
        "PIT_ELIGIBLE": pit_eligible, "canonical_qfq_authority": "TDX_GBBQ_UNCHANGED",
        "factor_role": "AUDIT_FACT_NOT_CANONICAL_QFQ_AUTHORITY",
        "tdx": tdx, "native_baostock": bao, "runtime_manifest": runtime,
        "security_universe": universe,
    }
    freeze = _write(root, "data/v4/frozen/freeze.json", freeze_doc)
    ready_doc = {
        "contract_id": "V4_DAILY_SOURCE_READINESS_V2", "trade_date": day, "source_ready": True,
        "observed_at": day + "T07:18:00+00:00",
        "AS_RECORDED": as_recorded, "PIT_ELIGIBLE": pit_eligible,
        "source_freeze": {"sha256": freeze["sha256"]},
    }
    readiness = _write(root, "data/v4/frozen/readiness.json", ready_doc)
    return day, freeze, readiness, freeze_doc


def _receipt(day, freeze, readiness, *, accepted_at="2026-10-16T13:00:00+00:00"):
    value = {
        "contract_id": "V4_DAILY_SOURCE_ACCEPTANCE_RECEIPT_R3",
        "acceptance_id": "accept-r1-001", "trade_date": day,
        "source_freeze_sha256": freeze["sha256"],
        "source_readiness_sha256": readiness["sha256"],
        "source_ready": True, "as_recorded": True, "pit_eligible": True,
        "accepted_at": accepted_at,
        "signed_at": accepted_at,
        "pit_cutoff_at": "2026-10-16T12:00:00+00:00",
        "pit_clock_contract_id": "V4_DAILY_PIT_DECISION_CLOCK_R1",
        "decision_session": "T0_AFTER_CLOSE",
        "trading_calendar_sha256": "a" * 64,
        "next_trade_date": "2026-10-19",
        "issuer_id": "TEST_AUTHORITY_ONLY",
    }
    value["source_fact_bindings_sha256"] = "0" * 64
    value["package_sha256"] = "0" * 64
    value["signature_ed25519"] = ""
    value["receipt_sha256"] = hashlib.sha256(_json_bytes({k:v for k,v in value.items() if k not in {"signature_ed25519","receipt_sha256"}})).hexdigest()
    return value


def _signed_receipt(plan, private_key, *, signed_at=None, accepted_at=None, cutoff=None):
    manifest = plan["package_manifest"]
    day = plan["trade_date"]
    signed_at = signed_at or day + "T07:25:00+00:00"
    accepted_at = accepted_at or day + "T07:20:00+00:00"
    cutoff = cutoff or day + "T12:00:00+00:00"
    value = {
        "contract_id": "V4_DAILY_SOURCE_ACCEPTANCE_RECEIPT_R3",
        "acceptance_id": "independent-r1-001", "trade_date": plan["trade_date"],
        "source_freeze_sha256": manifest["source_freeze_sha256"],
        "source_readiness_sha256": manifest["source_readiness_sha256"],
        "source_fact_bindings_sha256": manifest["source_fact_bindings_sha256"],
        "package_sha256": plan["package_sha256"],
        "source_ready": True,
        "as_recorded": True, "pit_eligible": True,
        "accepted_at": accepted_at, "signed_at": signed_at, "pit_cutoff_at": cutoff,
        "readiness_observed_at": manifest["source_readiness_observed_at"],
        "pit_clock_contract_id": "V4_DAILY_PIT_DECISION_CLOCK_R1",
        "decision_session": "T0_AFTER_CLOSE",
        "trading_calendar_sha256": "a" * 64,
        "next_trade_date": "2026-10-19",
        "issuer_id": "TEST_AUTHORITY_ONLY",
    }
    value["receipt_sha256"] = hashlib.sha256(_json_bytes(value)).hexdigest()
    value["signature_ed25519"] = base64.b64encode(private_key.sign(_json_bytes({k:v for k,v in value.items() if k != "receipt_sha256"}))).decode("ascii")
    return value


def _trust_test_authority(tmp_path, monkeypatch):
    import workbench_db.v4_daily_source_ingest_r6 as ingest

    private = Ed25519PrivateKey.generate()
    public = private.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    registry = tmp_path / "test-trust.json"
    registry.write_bytes(_json_bytes({
        "contract_id": "V4_DAILY_SOURCE_ACCEPTANCE_AUTHORITY_REGISTRY_R1",
        "contract_version": "1.0.0", "status": "ACTIVE",
        "issuers": {"TEST_AUTHORITY_ONLY": {
            "status": "ACTIVE", "public_key_b64": base64.b64encode(public).decode("ascii"),
            "scope": "TEST_ONLY_NO_PRODUCTION_AUTHORITY",
            "capabilities": ["ACCEPT_SOURCE_PACKAGE", "AS_RECORDED", "PIT_ELIGIBLE"],
        }},
    }))
    monkeypatch.setattr(ingest, "_acceptance_authority_registry", lambda pg=None: json.loads(registry.read_bytes()))
    return private


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
    assert {row["source_key"] for row in plan["source_facts"]} == {"tdx", "native_baostock", "runtime_manifest", "security_universe", "tdx_board_coverage"}


def test_self_hashed_receipt_cannot_create_acceptance_authority(tmp_path, monkeypatch):
    import workbench_db.v4_daily_source_ingest_r6 as ingest
    monkeypatch.setattr(ingest, "_acceptance_authority_registry", lambda pg=None: {})
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


def test_independent_ed25519_receipt_accepts_new_same_day_t0_and_emits_reader_fields(tmp_path, monkeypatch):
    day, freeze, readiness, _ = _frozen_inputs(tmp_path, as_recorded=True, pit_eligible=True)
    private = _trust_test_authority(tmp_path, monkeypatch)
    diagnostic = build_source_ingest_plan(tmp_path, trade_date=day, source_freeze=freeze, source_readiness=readiness)
    receipt = _signed_receipt(diagnostic, private, signed_at="2026-10-16T07:25:00+00:00",
                              accepted_at="2026-10-16T07:20:00+00:00", cutoff="2026-10-16T12:00:00+00:00")
    plan = build_source_ingest_plan(tmp_path, trade_date=day, source_freeze=freeze,
                                    source_readiness=readiness, acceptance_receipt=receipt)
    assert plan["status"] == "ACCEPTED"
    assert plan["package_manifest"]["accepted_scope"] == "ACCEPTED_SOURCE_PACKAGE"
    assert plan["package_manifest"]["AS_RECORDED"] is True
    assert plan["package_manifest"]["PIT_ELIGIBLE"] is True
    assert plan["package_manifest"]["acceptance_receipt_id"] == receipt["acceptance_id"]
    assert all(f["acceptance_receipt_id"] == receipt["acceptance_id"] for f in plan["package_manifest"]["source_fact_bindings"])
    assert plan["package_manifest"]["source_fact_bindings_sha256"] == receipt["source_fact_bindings_sha256"]
    from workbench_db.v4_daily_source_ingest_r6 import verify_source_package_manifest_authority
    assert verify_source_package_manifest_authority(plan["package_manifest"])["receipt_sha256"] == plan["package_manifest"]["acceptance_proof"]["receipt_sha256"]
    mutated = json.loads(json.dumps(plan["package_manifest"]))
    mutated["source_fact_bindings"][0]["source_fact_sha256"] = "0" * 64
    with pytest.raises(SourceIngestError, match="SOURCE_FACT_BINDINGS_DIGEST_MISMATCH"):
        verify_source_package_manifest_authority(mutated)


def test_post_close_source_is_eligible_for_evening_and_t1_preopen_cutoffs(tmp_path, monkeypatch):
    day, freeze, readiness, _ = _frozen_inputs(tmp_path, as_recorded=True, pit_eligible=True)
    private = _trust_test_authority(tmp_path, monkeypatch)
    diagnostic = build_source_ingest_plan(tmp_path, trade_date=day, source_freeze=freeze, source_readiness=readiness)
    evening = _signed_receipt(diagnostic, private)
    plan = build_source_ingest_plan(tmp_path, trade_date=day, source_freeze=freeze,
                                    source_readiness=readiness, acceptance_receipt=evening)
    assert plan["status"] == "ACCEPTED"
    preopen = _signed_receipt(diagnostic, private, accepted_at="2026-10-18T23:00:00+00:00",
                              signed_at="2026-10-18T23:05:00+00:00", cutoff="2026-10-19T01:20:00+00:00")
    preopen["decision_session"] = "T1_PREOPEN"
    preopen["next_trade_date"] = "2026-10-19"
    preopen["receipt_sha256"] = hashlib.sha256(_json_bytes({k:v for k,v in preopen.items() if k not in {"signature_ed25519","receipt_sha256"}})).hexdigest()
    preopen["signature_ed25519"] = base64.b64encode(private.sign(_json_bytes({k:v for k,v in preopen.items() if k not in {"signature_ed25519","receipt_sha256"}}))).decode("ascii")
    next_plan = build_source_ingest_plan(tmp_path, trade_date=day, source_freeze=freeze,
                                         source_readiness=readiness, acceptance_receipt=preopen)
    assert next_plan["status"] == "ACCEPTED", next_plan["acceptance_status"]


def test_decision_before_source_first_observation_is_rejected(tmp_path, monkeypatch):
    day, freeze, readiness, _ = _frozen_inputs(tmp_path, as_recorded=True, pit_eligible=True)
    private = _trust_test_authority(tmp_path, monkeypatch)
    diagnostic = build_source_ingest_plan(tmp_path, trade_date=day, source_freeze=freeze, source_readiness=readiness)
    receipt = _signed_receipt(diagnostic, private, accepted_at="2026-10-16T06:30:00+00:00",
                              signed_at="2026-10-16T06:45:00+00:00", cutoff="2026-10-16T06:55:00+00:00")
    plan = build_source_ingest_plan(tmp_path, trade_date=day, source_freeze=freeze,
                                    source_readiness=readiness, acceptance_receipt=receipt)
    assert plan["status"] == "DIAGNOSTIC_ONLY"
    assert plan["acceptance_status"] == "INDEPENDENT_ACCEPTANCE_TIME_ORDER_INVALID"


@pytest.mark.parametrize("fault", ["signature", "source_sha", "late_signature", "wrong_day"])
def test_independent_receipt_rejects_signature_binding_clock_and_old_t0(tmp_path, monkeypatch, fault):
    day, freeze, readiness, _ = _frozen_inputs(tmp_path, as_recorded=True, pit_eligible=True)
    private = _trust_test_authority(tmp_path, monkeypatch)
    diagnostic = build_source_ingest_plan(tmp_path, trade_date=day, source_freeze=freeze, source_readiness=readiness)
    if fault == "late_signature":
        receipt = _signed_receipt(diagnostic, private, signed_at="2026-10-16T12:01:00+00:00", accepted_at="2026-10-16T07:20:00+00:00")
    else:
        receipt = _signed_receipt(diagnostic, private)
    if fault == "signature":
        receipt["signature_ed25519"] = base64.b64encode(b"\0" * 64).decode("ascii")
    elif fault == "source_sha":
        receipt["source_freeze_sha256"] = "0" * 64
        receipt["receipt_sha256"] = hashlib.sha256(_json_bytes({k:v for k,v in receipt.items() if k not in {"signature_ed25519","receipt_sha256"}})).hexdigest()
    elif fault == "wrong_day":
        receipt["trade_date"] = "2026-10-12"
        receipt["receipt_sha256"] = hashlib.sha256(_json_bytes({k:v for k,v in receipt.items() if k not in {"signature_ed25519","receipt_sha256"}})).hexdigest()
    plan = build_source_ingest_plan(tmp_path, trade_date=day, source_freeze=freeze,
                                    source_readiness=readiness, acceptance_receipt=receipt)
    assert plan["status"] == "DIAGNOSTIC_ONLY"
    assert plan["package_manifest"]["AS_RECORDED"] is False
    assert plan["package_manifest"]["PIT_ELIGIBLE"] is False


def test_post_hoc_receipt_cannot_upgrade_frozen_2026_10_12_pit(tmp_path, monkeypatch):
    day, freeze, readiness, _ = _frozen_inputs(tmp_path, day="2026-10-12", as_recorded=True, pit_eligible=True)
    private = _trust_test_authority(tmp_path, monkeypatch)
    diagnostic = build_source_ingest_plan(tmp_path, trade_date=day, source_freeze=freeze, source_readiness=readiness)
    receipt = _signed_receipt(diagnostic, private, accepted_at="2026-10-12T06:30:00+00:00",
                              signed_at="2026-10-16T06:45:00+00:00", cutoff="2026-10-12T12:00:00+00:00")
    plan = build_source_ingest_plan(tmp_path, trade_date=day, source_freeze=freeze,
                                    source_readiness=readiness, acceptance_receipt=receipt)
    assert plan["status"] == "DIAGNOSTIC_ONLY"
    assert plan["acceptance_status"] == "INDEPENDENT_ACCEPTANCE_TIME_ORDER_INVALID"


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
    with pytest.raises(SourceIngestError, match="INDEPENDENT_ACCEPTANCE_RECEIPT_REQUIRED"):
        persist_source_ingest_plan(
            public_pg, plan, publication_id="pub-1", publication_revision=3,
            ingested_at="2026-10-16T12:30:00+00:00",
            system_available_at="2026-10-16T12:31:00+00:00",
        )
    assert public_pg.statements == []

    internal_pg = _AtomicityFakePg()
    with pytest.raises(SourceIngestError, match="INDEPENDENT_ACCEPTANCE_RECEIPT_REQUIRED"):
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
        lambda _plan, **_kwargs: ingest._IndependentAcceptanceProof(plan_digest, "TEST_ONLY_ATOMICITY_FIXTURE"),
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
