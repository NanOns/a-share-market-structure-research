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
        return {"candidate_only": True, "endpoint": endpoint, "context": {"context_token": kwargs["expected_context_token"]}}


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
    handler = v4_server.make_v4_handler(tmp_path, adapter, allow_pg_candidate=True)
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
            assert status == 200
            assert body["candidate_only"] is True
            assert body["endpoint"] == f"/api/v4/current/{page}"
        assert [call[0] for call in adapter.calls] == [f"/api/v4/current/{page}" for page in pages]
        assert all(call[1] == {
            "trade_date": "2026-10-16", "model_namespace_id": "workspace-main",
            "expected_context_token": "token-1",
        } for call in adapter.calls)

        status, body = _request("/api/v4/current/entity?source=pg_candidate&trade_date=2026-10-16&model_namespace_id=workspace-main")
        assert status == 400 and body["code"] == "PG_CANDIDATE_CONTEXT_REQUIRED"
        assert len(adapter.calls) == 7

        status, body = _request("/api/v4/current/entity")
        assert status == 200 and body["reader"] == "file"

        from workbench_db.v4_publication_reader import PublicationReadError
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
