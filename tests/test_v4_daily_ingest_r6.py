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
        "target_session": day, "source_ready": True,
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
    assert plan["readiness_status"] == "ACCEPTANCE_RECEIPT_REJECTED"
    assert plan["capture_status"] == "CAPTURED"
    assert plan["write_mode"] == "PLAN_ONLY_NO_DATABASE_IO"
    assert {row["source_key"] for row in plan["source_facts"]} == {"tdx", "native_baostock", "runtime_manifest"}


def test_source_freeze_bytes_and_acceptance_receipt_are_exactly_bound(tmp_path):
    day, freeze, readiness, _ = _frozen_inputs(tmp_path, as_recorded=True, pit_eligible=True)
    receipt = _receipt(day, freeze, readiness)
    plan = build_source_ingest_plan(
        tmp_path, trade_date=day, source_freeze=freeze, source_readiness=readiness,
        acceptance_receipt=receipt,
    )
    assert plan["status"] == "ACCEPTED"
    assert all(fact["acceptance_receipt_id"] == receipt["acceptance_id"] for fact in plan["source_facts"])

    receipt["source_freeze_sha256"] = "0" * 64
    rejected = build_source_ingest_plan(
        tmp_path, trade_date=day, source_freeze=freeze, source_readiness=readiness,
        acceptance_receipt=receipt,
    )
    assert rejected["status"] == "DIAGNOSTIC_ONLY"

    (tmp_path / freeze["path"]).write_bytes(b"changed")
    with pytest.raises(SourceIngestError, match="SOURCE_FREEZE_DIGEST_MISMATCH"):
        build_source_ingest_plan(tmp_path, trade_date=day, source_freeze=freeze)


def test_source_readiness_must_bind_exact_freeze_and_t0(tmp_path):
    day, freeze, readiness, _ = _frozen_inputs(tmp_path)
    path = tmp_path / readiness["path"]
    doc = json.loads(path.read_bytes())
    doc["source_freeze"]["sha256"] = "1" * 64
    path.write_bytes(_json_bytes(doc))
    readiness["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    with pytest.raises(SourceIngestError, match="SOURCE_READINESS_FREEZE_BINDING_MISMATCH"):
        build_source_ingest_plan(tmp_path, trade_date=day, source_freeze=freeze, source_readiness=readiness)
