from __future__ import annotations

import http.client
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from workbench_service import v4_server


class _FileReader:
    def __init__(self, root, require_runtime=False):
        self.calls = []

    def read(self, endpoint, query):
        self.calls.append((endpoint, query))
        return 200, {"reader": "file", "endpoint": endpoint}


class _Bff:
    def __init__(self, root):
        pass


class _Adapter:
    def __init__(self):
        self.calls = []
        self.error = None

    def read_endpoint(self, endpoint, **kwargs):
        self.calls.append((endpoint, kwargs))
        if self.error:
            raise self.error
        return {"candidate_only": True, "endpoint": endpoint, "context": {
            "context_token": kwargs["expected_context_token"],
            "model_namespace_id": kwargs["model_namespace_id"],
            "publication_id": "pub-20261016-r1",
            "trade_date": "2026-10-16",
            "contracts": {"V4_PUBLICATION_TEST_CONTRACT": {
                "version": "r1", "raw_sha256": "a" * 64,
                "schema_version": "1", "namespace": kwargs["model_namespace_id"],
                "publication_id": "pub-20261016-r1", "trade_date": "2026-10-16",
                "accepted_at": "2026-10-16T16:00:00+00:00", "approved_by": "reviewer",
                "approval_ref": "approval-1", "approval_source_revision": "approval-source-r1",
                "approval_occurred_at": "2026-10-16T15:59:00+00:00",
                "approval_recorded_at": "2026-10-16T15:59:01+00:00",
                "approval_source_sha256": "a" * 64,
            }},
            "database_identity": {"database": "market_research", "database_oid": 16384,
                                  "host": "127.0.0.1", "port": 5432},
            "module_results": {
                "research_priority": {"owner_schema": "v4_research_priority_aaaaaaaaaaaaaaaa"},
                "operational_risk": {"owner_schema": "v4_operational_risk_aaaaaaaaaaaaaaaa"},
                "sector_lifecycle": {"owner_schema": "v4_sector_lifecycle_aaaaaaaaaaaaaaaa"},
            },
        }}


def _base_handler():
    class Base(BaseHTTPRequestHandler):
        def send(self, status, body, content_type="application/json; charset=utf-8"):
            raw = json.dumps(body).encode()
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def log_message(self, *_):
            pass

    return Base


def _request(path):
    connection = http.client.HTTPConnection("127.0.0.1", 28766, timeout=3)
    try:
        connection.request("GET", path)
        response = connection.getresponse()
        return response.status, json.loads(response.read())
    finally:
        connection.close()


def test_current_api_explicit_pg_candidate_http_and_no_file_fallback(monkeypatch, tmp_path):
    monkeypatch.setattr(v4_server, "recover", lambda root: None)
    monkeypatch.setattr(v4_server, "CurrentAcceptedV4Reader", _FileReader)
    monkeypatch.setattr(v4_server, "make_shadow_handler", lambda root: _base_handler())
    monkeypatch.setattr(v4_server, "ResearchBFF", _Bff)
    adapter = _Adapter()
    from workbench_db.v4_native import workspace_namespace_identity
    identity=workspace_namespace_identity(tmp_path,'publication')
    registry=tmp_path/'workspace-mapping.json'
    registry.write_text(json.dumps({
        'contract_id':'V4_PG_WORKSPACE_OWNER_MAPPING_REGISTRY_R1','contract_version':'1.0.0',
        'status':'TEST_FIXTURE_ONLY','mappings':[{
            'status':'APPROVED','root_identity_sha256':identity['root_identity_sha256'],
            'model_namespace_id':'workspace-main','valid_from':'2026-10-01','valid_to':None,
            'authorized_by':'TEST_FIXTURE_ONLY','authorization_reference':'TEST_ONLY_NO_PRODUCTION_AUTHORITY',
            'database_identity':{'database':'market_research','database_oid':16384,'host':'127.0.0.1','port':5432},
            'owner_schemas':{'research_priority':'v4_research_priority_aaaaaaaaaaaaaaaa',
                             'operational_risk':'v4_operational_risk_aaaaaaaaaaaaaaaa',
                             'sector_lifecycle':'v4_sector_lifecycle_aaaaaaaaaaaaaaaa'},
        }],
    }),encoding='utf-8')
    handler = v4_server.make_v4_handler(
        tmp_path, adapter, allow_pg_candidate=True,
        workspace_mapping_registry_path=registry,
    )
    server = ThreadingHTTPServer(("127.0.0.1", 28766), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        pages = ("summary", "radar", "entity", "sector", "cohort", "settlement", "health")
        for page in pages:
            status, body = _request(
                f"/api/v4/current/{page}?source=pg_candidate&trade_date=2026-10-16"
                "&model_namespace_id=workspace-main&context_token=token-1"
            )
            assert status == 200, body
            assert body["candidate_only"] is True
            assert body["endpoint"] == f"/api/v4/current/{page}"
            assert body["workspace_identity"]["contract_id"] == "V4_PG_WORKSPACE_NAMESPACE_ID_R1"
            assert body["workspace_identity"]["purpose"] == "publication"
            assert body["workspace_mapping"]["model_namespace_id"] == "workspace-main"
            proof=body["context"]["contracts"]["V4_PUBLICATION_TEST_CONTRACT"]
            assert proof["publication_id"] == body["context"]["publication_id"]
            assert proof["trade_date"] == body["context"]["trade_date"]
            assert proof["approval_ref"] == "approval-1"
            assert proof["approval_recorded_at"] == "2026-10-16T15:59:01+00:00"
            assert str(tmp_path) not in json.dumps(body["workspace_identity"])
        assert [call[0] for call in adapter.calls] == [f"/api/v4/current/{page}" for page in pages]
        assert all(call[1] == {
            "trade_date": "2026-10-16", "model_namespace_id": "workspace-main",
            "expected_context_token": "token-1",
        } for call in adapter.calls)

        # The accepted publication itself must agree with the historically
        # authorized mapping. A same-T0 publication from another namespace is
        # not selected by date alone.
        adapter.read_endpoint=lambda endpoint, **kwargs: {
            'candidate_only':True,'context':{'context_token':kwargs['expected_context_token'],
               'model_namespace_id':'other-workspace',
               'publication_id':'pub-20261016-r1','trade_date':'2026-10-16',
               'contracts':{'V4_PUBLICATION_TEST_CONTRACT':{
                   'version':'r1','raw_sha256':'a'*64,'schema_version':'1','namespace':'other-workspace',
                   'publication_id':'pub-20261016-r1','trade_date':'2026-10-16',
                   'accepted_at':'2026-10-16T16:00:00+00:00','approved_by':'reviewer',
                   'approval_ref':'approval-1','approval_source_revision':'approval-source-r1',
                   'approval_occurred_at':'2026-10-16T15:59:00+00:00',
                   'approval_recorded_at':'2026-10-16T15:59:01+00:00','approval_source_sha256':'a'*64,
               }},
               'database_identity':{'database':'market_research','database_oid':16384,'host':'127.0.0.1','port':5432},
               'module_results':{}},
        }
        status,body=_request('/api/v4/current/entity?source=pg_candidate&trade_date=2026-10-16&model_namespace_id=workspace-main&context_token=token-1')
        assert status==409 and body['reason']=='WORKSPACE_PUBLICATION_NAMESPACE_MISMATCH'
        assert len(adapter.calls)==7

        status, body = _request("/api/v4/current/entity?source=pg_candidate&trade_date=2026-10-16&model_namespace_id=workspace-main")
        assert status == 400 and body["code"] == "PG_CANDIDATE_CONTEXT_REQUIRED"
        assert len(adapter.calls) == 7

        status, body = _request("/api/v4/current/entity")
        assert status == 200 and body["reader"] == "file"

        from workbench_db.v4_publication_reader import PublicationReadError
        adapter.read_endpoint = _Adapter.read_endpoint.__get__(adapter, _Adapter)
        adapter.error = PublicationReadError("NO_ACCEPTED_PUBLICATION")
        status, body = _request(
            "/api/v4/current/entity?source=pg_candidate&trade_date=2026-10-16"
            "&model_namespace_id=workspace-main&context_token=token-1"
        )
        assert status == 409
        assert body["data_state"] == "PENDING_PG_HEAD"
        assert body["reason"] == "NO_ACCEPTED_PUBLICATION"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)


def test_pg_candidate_http_mode_fails_closed_when_not_enabled(monkeypatch, tmp_path):
    monkeypatch.setattr(v4_server, "recover", lambda root: None)
    monkeypatch.setattr(v4_server, "CurrentAcceptedV4Reader", _FileReader)
    monkeypatch.setattr(v4_server, "make_shadow_handler", lambda root: _base_handler())
    monkeypatch.setattr(v4_server, "ResearchBFF", _Bff)
    handler = v4_server.make_v4_handler(tmp_path)
    server = ThreadingHTTPServer(("127.0.0.1", 28766), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        status, body = _request(
            "/api/v4/current/entity?source=pg_candidate&trade_date=2026-10-16"
            "&model_namespace_id=workspace-main&context_token=token-1"
        )
        assert status == 404 and body["code"] == "PG_CANDIDATE_MODE_DISABLED"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)


def test_candidate_server_factory_requires_explicit_database_identity(monkeypatch):
    monkeypatch.delenv("V4_PG_EXPECTED_DATABASE_IDENTITY_JSON", raising=False)
    with pytest.raises(RuntimeError, match="V4_PG_EXPECTED_DATABASE_IDENTITY_REQUIRED"):
        v4_server.pg_candidate_adapter_from_environment()
    monkeypatch.setenv("V4_PG_EXPECTED_DATABASE_IDENTITY_JSON", json.dumps({
        "database": "market_research", "database_oid": 16384, "host": "127.0.0.1", "port": 5432,
    }))
    adapter = v4_server.pg_candidate_adapter_from_environment()
    assert adapter.reader.expected_database_identity == {
        "database": "market_research", "database_oid": 16384, "host": "127.0.0.1", "port": 5432,
    }


def test_candidate_bff_rejects_missing_contract_approval_proof():
    from workbench_db.v4_publication_reader import PublicationReadError

    with pytest.raises(PublicationReadError, match="PG_CANDIDATE_CONTRACT_PROOF_REQUIRED"):
        v4_server._require_candidate_contract_proofs({
            "publication_id": "pub-1", "trade_date": "2026-10-16", "model_namespace_id": "workspace-main",
        })


def test_candidate_bff_rejects_approval_recorded_after_publication_acceptance():
    from workbench_db.v4_publication_reader import PublicationReadError

    proof={"version":"r1","raw_sha256":"a"*64,"schema_version":"1","namespace":"workspace-main",
           "publication_id":"pub-1","trade_date":"2026-10-16","accepted_at":"2026-10-16T16:00:00+00:00",
           "approved_by":"reviewer","approval_ref":"approval-1","approval_source_revision":"source-r1",
           "approval_occurred_at":"2026-10-16T15:59:00+00:00","approval_recorded_at":"2026-10-16T16:00:01+00:00",
           "approval_source_sha256":"a"*64}
    with pytest.raises(PublicationReadError, match="PG_CANDIDATE_CONTRACT_PROOF_INVALID"):
        v4_server._require_candidate_contract_proofs({"publication_id":"pub-1","trade_date":"2026-10-16",
            "model_namespace_id":"workspace-main","contracts":{"RULE":proof}})
