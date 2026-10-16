"""Real daily executor → PG source-plan bridge regression.

The immutable 2026-10-12 freeze/readiness artifacts are local operational
evidence and are not tracked in Git. CI skips only when those exact artifacts
are absent; developer runs with the frozen evidence exercise the real bytes.
"""
import hashlib
import json
from pathlib import Path
from pathlib import PureWindowsPath

import pytest

from workbench_analysis.operational_daily_executor_v1 import (
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


def test_active_runtime_receipt_path_comes_from_versioned_contract(tmp_path):
    assert _runtime_acceptance_manifest_path(tmp_path, "2026-10-12") == (
        tmp_path / "reports/v4_baostock/runtime_acceptance/20261012/accepted_runtime_manifest.json"
    )


def test_tdx_gbbq_is_configured_as_read_only_input():
    assert PureWindowsPath(str(_tdx_gbbq_source_path())).is_absolute()
