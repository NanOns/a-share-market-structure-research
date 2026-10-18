import hashlib
import json

from scripts import run_v4_dm01_daily_increment as daily
from workbench_db import v4_historical_source_ingress_pg_r1 as ingress


def test_daily_json_projection_returns_exact_pg_source_binding(monkeypatch, tmp_path):
    payload = {"target_date": "2026-10-16", "名称": "煤炭", "rows": [1, 2]}
    expected = json.dumps(payload, ensure_ascii=False, sort_keys=True,
                          separators=(",", ":"), allow_nan=False).encode("utf-8")
    captured = {}

    def ingest(root, logical_path, raw, *, source_revision, source_origin):
        captured.update(root=root, logical_path=logical_path, raw=raw,
                        source_revision=source_revision, source_origin=source_origin)
        return {"source_path": logical_path, "source_sha256": hashlib.sha256(raw).hexdigest(),
                "source_bytes": len(raw)}

    monkeypatch.setattr(daily, "ROOT", tmp_path)
    monkeypatch.setattr(ingress, "ingest_captured_bytes", ingest)
    binding = daily._ingest_pg_json_projection(
        "external/test/20261016/source.json", payload,
        source_revision="revision-1", source_origin="TEST_SOURCE_BOUNDARY")

    assert captured["raw"] == expected
    assert captured["root"] == tmp_path
    assert captured["source_revision"] == "revision-1"
    assert captured["source_origin"] == "TEST_SOURCE_BOUNDARY"
    assert binding == {"path": captured["logical_path"],
                       "sha256": hashlib.sha256(expected).hexdigest(),
                       "bytes": len(expected)}


def test_daily_runtime_acceptance_uses_pg_registered_contract(monkeypatch):
    day="2026-10-16"
    manifest={"contract_id":"BAOSTOCK_DAILY_UPDATE_RUNTIME_ACCEPTANCE_V1",
              "status":"ACCEPTED","auth_mode":"PUBLIC_ANONYMOUS",
              "live_smoke":{"target_date":day}}
    calls={}

    def contract(contract_id,version):
        calls["contract"]=(contract_id,version)
        return {"dm01_daily_updates":{"runtime_acceptance_manifest_template":"runtime/{YYYYMMDD}.json"}}

    def load(root,target,*,sdk):
        calls["load"]=(root,target,sdk)
        return {"manifest":manifest}

    monkeypatch.setattr(daily,"_daily_runtime_contract",contract)
    monkeypatch.setattr(daily,"load_baostock_runtime_pg",load)
    monkeypatch.setattr(daily,"runtime_acceptance_error",lambda *_args,**_kwargs:None)
    result,error=daily._runtime_acceptance(day)
    assert calls["contract"]==("BAOSTOCK_SUPPLEMENTAL_SOURCE_V1","1.1.0")
    assert calls["load"][1]==day
    assert result==manifest and error is None
