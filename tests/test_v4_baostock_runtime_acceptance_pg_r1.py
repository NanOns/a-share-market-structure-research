from contextlib import contextmanager
import base64
import hashlib
import json

from workbench_analysis.baostock_runtime_acceptance import build_runtime_acceptance_manifest
from workbench_db import v4_baostock_runtime_acceptance_pg_r1 as pg_acceptance
from workbench_db.v4_forward_pg_r1 import canonical, digest


def _fixture():
    day = "2026-10-16"
    runtime = {"package": "baostock", "version": "0.9.0", "installed_python_sources_sha256": "a" * 64}
    smoke = {
        "status": "PASS", "target_date": day, "auth_mode": "PUBLIC_ANONYMOUS",
        "daily": {"method": "query_daily_history_k_AStock", "provider_date": day,
                  "row_count": 1, "response_sha256": "b" * 64, "fields": ["code"]},
        "adjustment_factor": {"method": "query_daily_adjust_factor", "provider_date": day,
                  "row_count": 1, "response_sha256": "c" * 64, "fields": ["code"]},
    }
    observed_at = "2026-10-16T11:00:00+00:00"
    native_payload = {"target_date": day, "observed_at": observed_at,
                      "daily_rows": [{"code": "sh.600000"}],
                      "daily_metadata": {"error_code": "0"},
                      "adjustment_factor_rows": [{"code": "sh.600000"}],
                      "adjustment_factor_metadata": {"error_code": "0"}}
    native_raw = canonical(native_payload)
    native_sha = hashlib.sha256(native_raw).hexdigest()
    receipt = {"contract_id": "BAOSTOCK_DAILY_UPDATE_LIVE_SMOKE_V1", "status": "PASS",
               "target_date": day, "runtime": runtime, "auth_mode": "PUBLIC_ANONYMOUS",
               "live_smoke": smoke, "observed_at": observed_at,
               "native_response": {"path": "reports/v4_baostock/runtime_acceptance/20261016/raw.json",
                                   "sha256": native_sha}}
    receipt_raw = canonical(receipt)
    manifest = build_runtime_acceptance_manifest(
        sdk=runtime, auth_mode="PUBLIC_ANONYMOUS", live_smoke=smoke,
        smoke_receipt_path="reports/v4_baostock/runtime_acceptance/20261016/smoke.json",
        smoke_receipt_sha256=hashlib.sha256(receipt_raw).hexdigest(),
    )
    native_response = {
        "source_binding": {"path": receipt["native_response"]["path"], "sha256": native_sha,
                           "bytes": len(native_raw)},
        "source_sha256": native_sha, "payload": native_payload,
        "raw_b64": base64.b64encode(native_raw).decode("ascii"),
    }
    record = pg_acceptance._record(day, manifest, receipt_raw, native_response=native_response)
    payload = canonical(record).decode()
    return day, runtime, record, (payload, digest(payload.encode()))


def test_pg_loader_reads_date_fact_and_validates_database_identity(monkeypatch):
    day, runtime, record, row = _fixture()
    identity = {"database": "market_research", "database_oid": 42, "host": "127.0.0.1", "port": 5432}

    class Cursor:
        def __init__(self):
            self._relation_query = False

        def execute(self, query, params=None):
            if "to_regclass" in query:
                self._relation_query = True
                return self
            assert "FROM forward_facts" in query
            assert params == (pg_acceptance.KIND, day)
            self._relation_query = False
            return self

        def fetchone(self):
            return ("forward_facts",) if self._relation_query else row

    @contextmanager
    def connection(schema, *, read_only):
        assert schema.startswith("v4_forward_")
        assert read_only is True
        yield Cursor()

    monkeypatch.setattr(pg_acceptance.v4_native, "connection", connection)
    monkeypatch.setattr(pg_acceptance.v4_native, "workspace_schema", lambda *_: "v4_forward_fixture")
    monkeypatch.setattr(pg_acceptance.ForwardFactStore, "_database_identity", staticmethod(lambda _pg: identity))
    monkeypatch.setattr(pg_acceptance, "_expected_identity", lambda: identity)

    result = pg_acceptance.load("G:/codex work/大A交易", day, sdk=runtime)
    assert result["source"] == "PG_ACCEPTED_DAILY_RUNTIME_FACT"
    assert result["manifest"] == record["manifest"]
    assert result["smoke_receipt"] == record["smoke_receipt"]
    assert result["native_response"] == record["native_response"]


def test_pg_loader_rejects_payload_digest_mismatch(monkeypatch):
    day, runtime, _record, _row = _fixture()
    class Cursor:
        def execute(self, query, *_args): self.relation_query="to_regclass" in query; return self
        def fetchone(self):
            return ("forward_facts",) if self.relation_query else (json.dumps({"contract_id": pg_acceptance.CONTRACT}), "0" * 64)

    @contextmanager
    def connection(*_args, **_kwargs): yield Cursor()
    identity = {"database": "market_research", "database_oid": 42, "host": "127.0.0.1", "port": 5432}
    monkeypatch.setattr(pg_acceptance.v4_native, "connection", connection)
    monkeypatch.setattr(pg_acceptance.v4_native, "workspace_schema", lambda *_: "v4_forward_fixture")
    monkeypatch.setattr(pg_acceptance.ForwardFactStore, "_database_identity", staticmethod(lambda _pg: identity))
    monkeypatch.setattr(pg_acceptance, "_expected_identity", lambda: identity)
    try:
        pg_acceptance.load("G:/codex work/大A交易", day, sdk=runtime)
    except ValueError as exc:
        assert str(exc) == "BAOSTOCK_PG_RUNTIME_PAYLOAD_DIGEST_MISMATCH"
    else:
        raise AssertionError("payload digest mismatch was accepted")


def test_pg_loader_reports_missing_unmigrated_store_as_not_found(monkeypatch):
    class Cursor:
        def execute(self, *_args): return self
        def fetchone(self): return (None,)

    @contextmanager
    def connection(*_args, **_kwargs): yield Cursor()

    monkeypatch.setattr(pg_acceptance.v4_native, "connection", connection)
    monkeypatch.setattr(pg_acceptance.v4_native, "workspace_schema", lambda *_: "v4_forward_fixture")
    try:
        pg_acceptance.load("G:/codex work/大A交易", "2026-10-16", sdk={})
    except ValueError as exc:
        assert str(exc) == "BAOSTOCK_PG_RUNTIME_ACCEPTANCE_NOT_FOUND"
    else:
        raise AssertionError("missing uninitialized runtime store was not reported")


def test_native_response_binding_rejects_modified_exact_bytes():
    _day, _runtime, record, _row = _fixture()
    native = dict(record["native_response"])
    native["raw_b64"] = base64.b64encode(b'{"target_date":"tampered"}').decode("ascii")
    try:
        pg_acceptance._validate_native_response("2026-10-16", record["smoke_receipt"], native)
    except ValueError as exc:
        assert str(exc) == "BAOSTOCK_PG_NATIVE_RESPONSE_DIGEST_MISMATCH"
    else:
        raise AssertionError("modified BaoStock source bytes were accepted")


def test_capture_entrypoint_uses_pg_runtime_authority_by_default(monkeypatch):
    from scripts import capture_baostock_daily_update as capture
    expected = {"contract_id": "BAOSTOCK_DAILY_UPDATE_RUNTIME_ACCEPTANCE_V1", "status": "ACCEPTED"}
    called = {}

    def load(root, day, *, sdk):
        called.update(root=root, day=day, sdk=sdk)
        return {"manifest": expected}

    monkeypatch.delenv("V4_BAOSTOCK_RUNTIME_ACCEPTANCE_SOURCE", raising=False)
    monkeypatch.setattr(pg_acceptance, "load", load)
    monkeypatch.setattr(capture, "package_metadata", lambda: {
        "package": "baostock", "version": "0.9.0", "installed_python_sources_sha256": "a" * 64,
    })
    assert capture.load_runtime_acceptance("G:/repo", "2026-10-16", "ignored.json") == expected
    assert called["day"] == "2026-10-16"


def test_operational_executor_materializes_manifest_from_pg_bundle_without_file_reader(monkeypatch, tmp_path):
    from workbench_analysis import operational_daily_executor_v1 as executor
    day, runtime, record, _row = _fixture()
    bundle = {"manifest": record["manifest"], "smoke_receipt": record["smoke_receipt"],
              "native_response": record["native_response"], "payload_sha256": "f" * 64,
              "database_identity": {"database": "fixture", "database_oid": 1, "host": "fixture", "port": 5432},
              "schema": "v4_fixture"}
    calls = {}

    def load(root, target, *, sdk):
        calls.update(root=root, target=target, sdk=sdk)
        return bundle

    def export(root, loaded):
        assert loaded is bundle
        return {"path": "data/v4/runtime_pg_ingress_cache/baostock/20261016/native_response.json",
                "sha256": record["native_response"]["source_sha256"], "bytes": 100}

    monkeypatch.setattr(pg_acceptance, "load", load)
    monkeypatch.setattr(pg_acceptance, "export_native_response", export)
    monkeypatch.setattr(executor, "package_metadata", lambda: runtime)

    result = executor._load_pg_runtime_acceptance(tmp_path, day)
    assert calls["target"] == day
    assert result["raw"] == record["native_response"]["payload"]
    assert result["receipt"] == record["smoke_receipt"]
    assert result["raw_path"].as_posix().endswith("runtime_pg_ingress_cache/baostock/20261016/native_response.json")
    assert result["manifest_path"].is_file()
    assert result["bundle"]["database_identity"]["database"] == "fixture"


def test_zero_change_pg_bundle_requires_every_exact_universe_response():
    day = "2026-10-16"
    runtime = {"package": "baostock", "version": "0.9.0", "installed_python_sources_sha256": "a" * 64}
    ref = {"path": "data/v4/no_change/proof.json", "sha256": "1" * 64, "bytes": 10}
    response_ref = {"path": "data/v4/no_change/600000.json", "sha256": "2" * 64, "bytes": 20}
    manifest = {"runtime": runtime, "live_smoke": {"target_date": day,
                "adjustment_factor": {"no_change_proof": ref}}}
    payload = {"code": "sh.600000", "rows": [],
               "params": {"code": "sh.600000", "start_date": day, "end_date": day},
               "metadata": {"error_code": "0"}, "sdk": runtime}
    evidence = {"proof_binding": ref,
                "proof": {"acceptance": "VERIFIED_ALL_TARGET_UNIVERSE_NO_CHANGE",
                          "target_session": day, "target_universe_codes": ["sh.600000"],
                          "queried_codes": ["sh.600000"], "responses": [response_ref]},
                "responses": [{"source_binding": response_ref, "payload": payload}]}
    pg_acceptance._validate_zero_change_evidence(manifest, evidence)
    evidence["responses"][0]["payload"] = {**payload, "rows": [{"date": day}]}
    try:
        pg_acceptance._validate_zero_change_evidence(manifest, evidence)
    except ValueError as exc:
        assert str(exc) == "BAOSTOCK_PG_ZERO_CHANGE_RESPONSE_INVALID"
    else:
        raise AssertionError("nonempty response rows were accepted as zero-change proof")
