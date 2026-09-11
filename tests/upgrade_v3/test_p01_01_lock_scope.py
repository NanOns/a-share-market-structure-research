import threading
import time
from contextlib import contextmanager

import workbench_service.app as app
from workbench_service.app import Api


class _NoopService:
    def __init__(self, *args, **kwargs):
        pass

    def recover_interrupted(self, *args, **kwargs):
        return []


def test_hot_rank_route_skips_request_scope(monkeypatch, tmp_path):
    scope_events = []

    class _Api:
        def __init__(self, *args, **kwargs):
            pass

        @contextmanager
        def request_scope(self):
            scope_events.append("enter")
            yield
            scope_events.append("exit")

    monkeypatch.setattr(app, "Api", _Api)
    for name in (
        "HistoryJobService",
        "AnalysisActivationService",
        "OperationsConfig",
        "StorageGovernance",
        "BackupService",
        "MaintenanceService",
    ):
        monkeypatch.setattr(app, name, _NoopService)

    handler_type = app.make_handler(tmp_path, tmp_path / "test.duckdb")
    handler = handler_type.__new__(handler_type)
    handler._do_GET = lambda: "handled"

    handler.path = "/api/hot-rankings?page=1"
    assert handler_type.do_GET(handler) == "handled"
    assert scope_events == []

    handler.path = "/api/publications"
    assert handler_type.do_GET(handler) == "handled"
    assert scope_events == ["enter", "exit"]


def test_hot_rank_network_wait_does_not_block_short_local_read(monkeypatch, tmp_path):
    api = Api.__new__(Api)
    api._root = tmp_path
    api._db_lock = threading.RLock()
    api._request_state = threading.local()

    def publications():
        with api._db_lock:
            return {"latest_publication_id": "publication-1"}

    api.publications = publications
    api._security_names = lambda publication_id, security_ids: {
        security_id: f"本地-{security_id}" for security_id in security_ids
    }

    started = threading.Event()
    release = threading.Event()
    result_box = {}

    def slow_direct_response(**kwargs):
        started.set()
        release.wait(timeout=8.0)
        return {
            "items": [{"security_id": "SZ.000001", "security_name": None}],
            "local_snapshot_mutated": False,
        }

    monkeypatch.setattr(app, "build_hot_rank_direct_response", slow_direct_response)
    def run_hot_rank():
        result_box["value"] = api.hot_rankings(page_size=1)

    worker = threading.Thread(target=run_hot_rank)
    worker.start()
    assert started.wait(timeout=2.0)

    started_at = time.perf_counter()
    assert api.publications()["latest_publication_id"] == "publication-1"
    local_read_seconds = time.perf_counter() - started_at
    assert local_read_seconds < 0.5
    assert worker.is_alive()

    release.set()
    worker.join(timeout=2.0)
    assert not worker.is_alive()
    assert result_box["value"]["items"][0]["security_name"] == "本地-SZ.000001"


def test_send_marks_disconnected_client_closed(monkeypatch, tmp_path):
    class _Api:
        def __init__(self, *args, **kwargs):
            pass

    monkeypatch.setattr(app, "Api", _Api)
    for name in (
        "HistoryJobService",
        "AnalysisActivationService",
        "OperationsConfig",
        "StorageGovernance",
        "BackupService",
        "MaintenanceService",
    ):
        monkeypatch.setattr(app, name, _NoopService)
    handler_type = app.make_handler(tmp_path, tmp_path / "test.duckdb")
    handler = handler_type.__new__(handler_type)
    handler.send_response = lambda status: None
    handler.send_header = lambda name, value: None
    handler.end_headers = lambda: None

    class _BrokenWriter:
        def write(self, raw):
            raise BrokenPipeError()

    handler.wfile = _BrokenWriter()
    handler.close_connection = False

    assert handler_type._send(handler, 200, {"ok": True}) is False
    assert handler.close_connection is True
