"""Real daily executor → PG source-plan bridge regression.

The immutable 2026-10-12 freeze/readiness artifacts are local operational
evidence and are not tracked in Git. CI skips only when those exact artifacts
are absent; developer runs with the frozen evidence exercise the real bytes.
"""
import hashlib
import json
from pathlib import Path

import pytest

from workbench_analysis.operational_daily_executor_v1 import (
    build_daily_core_result_candidate,
    persist_daily_core_result_candidate,
    _pg_source_ingest_plan_diagnostic,
    _runtime_acceptance_manifest_path,
    _tdx_gbbq_source_path,
)
from workbench_db import v4_daily_source_ingest_r6 as source_ingest


ROOT = Path(__file__).resolve().parents[1]
DAY = "2026-10-12"
READINESS_DIR = ROOT / "data/v4/dynamic_daily_sources/source_readiness" / DAY


def _real_pair():
    if not READINESS_DIR.is_dir():
        return None
    for readiness_path in sorted(READINESS_DIR.glob("*.json")):
        readiness = json.loads(readiness_path.read_bytes())
        if readiness.get("contract_id") != "V4_DAILY_SOURCE_READINESS_V2":
            continue
        freeze = readiness.get("source_freeze")
        if not isinstance(freeze, dict):
            continue
        freeze_path = ROOT / freeze["path"]
        if (freeze_path.is_file()
                and hashlib.sha256(freeze_path.read_bytes()).hexdigest() == freeze.get("sha256")):
            return readiness_path, readiness
    return None


def test_real_20261012_executor_evidence_reaches_pg_adapter_as_diagnostic_only():
    pair = _real_pair()
    if pair is None:
        pytest.skip("immutable 2026-10-12 local executor evidence is not present")
    readiness_path, readiness = pair
    binding = {
        "path": readiness_path.relative_to(ROOT).as_posix(),
        "sha256": hashlib.sha256(readiness_path.read_bytes()).hexdigest(),
    }
    result = {
        "source_freeze": readiness["source_freeze"],
        "source_readiness": binding,
    }

    diagnostic = _pg_source_ingest_plan_diagnostic(ROOT, DAY, result)

    assert diagnostic is not None
    assert diagnostic["contract_id"] == "V4_DAILY_SOURCE_INGEST_ADAPTER_R6"
    assert diagnostic["status"] == "DIAGNOSTIC_ONLY"
    assert diagnostic["acceptance_status"] == "SOURCE_PIT_AUTHORITY_UNAVAILABLE"
    assert diagnostic["source_fact_count"] == 3
    assert diagnostic["write_mode"] == "PLAN_ONLY_NO_DATABASE_IO"
    assert diagnostic["persisted"] is False


def test_source_diagnostic_bridge_failure_does_not_break_executor(monkeypatch):
    def broken_plan(*args, **kwargs):
        raise RuntimeError("diagnostic adapter unavailable")

    monkeypatch.setattr(source_ingest, "build_source_ingest_plan", broken_plan)
    diagnostic = _pg_source_ingest_plan_diagnostic(
        ROOT, DAY, {"source_freeze": {}, "source_readiness": {}}
    )
    assert diagnostic["status"] == "BRIDGE_BLOCKED"
    assert diagnostic["acceptance_status"] == "diagnostic adapter unavailable"
    assert diagnostic["write_mode"] == "PLAN_ONLY_NO_DATABASE_IO"
    assert diagnostic["persisted"] is False


def test_actual_daily_owner_bridge_does_not_invent_publication_or_pit_authority():
    result = build_daily_core_result_candidate(
        ROOT, {"owners": {DAY: {"core": {"path": "unread"}}}}, DAY,
    )
    assert result == {
        "status": "BLOCKED_PG_PUBLICATION_CONTEXT_MISSING",
        "trade_date": DAY,
        "write_mode": "PLAN_ONLY_NO_DATABASE_IO",
        "persisted": False,
    }


def test_core_result_writer_bridge_is_explicit_and_delegates_to_caller_transaction(monkeypatch):
    from workbench_db import v4_daily_core_result_r6

    pg = object()
    plan = {"contract_id": v4_daily_core_result_r6.CONTRACT_ID, "trade_date": DAY}
    called = []

    def writer(received_pg, received_plan):
        called.append((received_pg, received_plan))
        return {"status": "INSERTED_CANDIDATE_ROWS", "committed": False}

    monkeypatch.setattr(v4_daily_core_result_r6, "persist_daily_core_result", writer)
    result = persist_daily_core_result_candidate(pg, {
        "status": "PLAN_READY_NOT_PERSISTED", "trade_date": DAY, "plan": plan,
    })
    assert called == [(pg, plan)]
    assert result["status"] == "PG_CANDIDATE_RESULT_INSERTED_NOT_ACCEPTED"
    assert result["write_mode"] == "CALLER_TRANSACTION_NO_COMMIT"
    assert result["persisted"] is True
    with pytest.raises(ValueError, match="PG_CORE_RESULT_PLAN_NOT_READY"):
        persist_daily_core_result_candidate(pg, {"status": "BLOCKED_PG_PUBLICATION_CONTEXT_MISSING"})


def test_active_runtime_receipt_path_comes_from_versioned_contract(tmp_path,monkeypatch):
    monkeypatch.setenv('V4_DAILY_CONTRACT_SOURCE','FILE')
    assert _runtime_acceptance_manifest_path(tmp_path, "2026-10-12") == (
        tmp_path / "reports/v4_baostock/runtime_acceptance/20261012/accepted_runtime_manifest.json"
    )


def test_tdx_gbbq_is_configured_as_read_only_input(monkeypatch):
    monkeypatch.setenv('V4_DAILY_CONTRACT_SOURCE','FILE')
    path = _tdx_gbbq_source_path()
    assert path.parts[-3:] == ("T0002", "hq_cache", "gbbq")
    assert path.is_absolute()


def test_tdx_gbbq_path_uses_central_configured_root(tmp_path,monkeypatch):
    from common.paths import resolve_tdx_root
    monkeypatch.setenv('V4_DAILY_CONTRACT_SOURCE','FILE')

    configured = tmp_path / "configured-tdx"
    (tmp_path / "config").mkdir()
    (tmp_path / "config/paths.yaml").write_text(
        f"tdx:\n  source_root: {configured.as_posix()}\n", encoding="utf-8"
    )

    assert _tdx_gbbq_source_path(tmp_path) == resolve_tdx_root(tmp_path) / "T0002/hq_cache/gbbq"


def test_daily_runtime_contract_uses_approved_pg_registry_by_default(monkeypatch):
    from contextlib import contextmanager
    from workbench_analysis import operational_daily_executor_v1 as executor
    import workbench_analysis.contract_registry_pg_v1 as contract_registry_pg_v1
    from workbench_db import v4_publication_reader

    monkeypatch.delenv('V4_DAILY_CONTRACT_SOURCE',raising=False)
    monkeypatch.setenv('V4_PG_MODEL_NAMESPACE_ID','runtime_ns')
    monkeypatch.setenv('V4_PG_EXPECTED_DATABASE_IDENTITY_JSON',
        '{"database":"market_research","database_oid":1,"host":"127.0.0.1","port":5432}')
    calls=[]
    @contextmanager
    def connection():
        yield object()
    def registered(pg,cid,version,namespace,**kwargs):
        calls.append((cid,version,namespace,kwargs))
        document={'contract_id':cid,'contract_version':version}
        if cid=='V4_DAILY_TDX_READONLY_SOURCE_R1':
            document.update(source_mode='READ_ONLY_INPUT',gbbq_relative_path='T0002/hq_cache/gbbq')
        return type('Registered',(),{'parsed_json':document})()
    monkeypatch.setattr(v4_publication_reader,'readonly_connection',connection)
    monkeypatch.setattr(contract_registry_pg_v1,'load_current_approved_contract',registered)

    contract=executor._daily_runtime_contract(ROOT,'V4_DAILY_TDX_READONLY_SOURCE_R1','1.1.0',
        'config/v4_daily_tdx_readonly_source_v1.json')

    assert contract['gbbq_relative_path']=='T0002/hq_cache/gbbq'
    assert calls[0][0:3]==('V4_DAILY_TDX_READONLY_SOURCE_R1','1.1.0','runtime_ns')
    assert calls[0][3]['expected_database_identity']['database']=='market_research'


def test_daily_runtime_contract_pg_mode_fails_closed_without_namespace(monkeypatch):
    from workbench_analysis import operational_daily_executor_v1 as executor
    monkeypatch.delenv('V4_DAILY_CONTRACT_SOURCE',raising=False)
    monkeypatch.delenv('V4_PG_MODEL_NAMESPACE_ID',raising=False)
    with pytest.raises(ValueError,match='PG_MODEL_NAMESPACE_REQUIRED'):
        executor._daily_runtime_contract(ROOT,'V4_DAILY_TDX_READONLY_SOURCE_R1','1.1.0',
            'config/v4_daily_tdx_readonly_source_v1.json')
