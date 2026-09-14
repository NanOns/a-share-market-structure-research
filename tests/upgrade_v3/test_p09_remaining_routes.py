from __future__ import annotations

import json
import threading
import urllib.parse
import urllib.request
from pathlib import Path

import duckdb

import workbench_service.app as app
from workbench_db import WorkbenchRepository


ROOT = Path(__file__).parents[2]


class _Response:
    def __init__(self, source_id="EXT02"):
        self.source_id = source_id
        self.status = "AVAILABLE"
        self.error_code = None
        self.normalized = []
        self.source_trade_date = "2026-09-14"
        self.source_as_of = "2026-09-14T07:30:00+00:00"


class _FakeP09:
    def batch(self, requests):
        return tuple(_Response(source_id) for source_id, _params in requests)

    def fetch(self, source_id, params=None):
        return _Response(source_id)

    def view(self, response, **kwargs):
        return {"status": "AVAILABLE", "source": {"source_id": response.source_id}, "items": [], "returned_count": 0, "total": 0, "has_more": False, "coverage": {}, "storage": {"mode": "REQUEST_TIME_ONLY", "raw_payload_persisted": False, "rows_persisted": False, "batch_persisted": False}, "empty_state": None}

    def events_pools(self, **kwargs):
        return {"status": "AVAILABLE", "pools": {"limit_up": self.view(_Response("EXT05"))}, "storage": {"mode": "REQUEST_TIME_ONLY"}}

    def promotion(self, **kwargs):
        return {"status": "AVAILABLE", "rate": 0.25, "success_count": 1, "eligible_count": 4, "unknown_count": 0, "items": []}

    def topics(self, **kwargs):
        return {"status": "AVAILABLE", "date": kwargs.get("trade_date"), "items": [{"source_topic_id": "7", "topic_name": "机器人", "members": [], "limit_up_member_count": 0, "unique_member_count": 0}], "topic_count": 1, "unique_limit_up_member_count": 0, "source_status": {"EXT03": "AVAILABLE", "EXT04": "AVAILABLE"}, "storage": {"mode": "REQUEST_TIME_ONLY"}, "empty_state": None}

    def hot_rankings(self, **kwargs):
        return {"status": "AVAILABLE", "lists": {"hour_normal": self.view(_Response("EXT07"))}, "persistence": "FORBIDDEN_REQUEST_TIME_ONLY", "raw_payload_persisted": False, "rows_persisted": False}

    def hot_plates(self, **kwargs):
        return {**self.view(_Response("EXT08")), "plate_type": kwargs.get("plate_type"), "persistence": "FORBIDDEN_REQUEST_TIME_ONLY"}

    def hot_topics(self, **kwargs):
        return {**self.view(_Response("EXT09")), "page": 1, "page_size": 30, "persistence": "FORBIDDEN_REQUEST_TIME_ONLY"}


def test_p09_api_routes_and_page_are_reachable_without_source_network(tmp_path, monkeypatch):
    db = tmp_path / "routes.duckdb"
    with WorkbenchRepository(ROOT, db):
        pass
    monkeypatch.setattr(app, "P09OnlineProducts", _FakeP09)
    server = __import__("http.server").server.ThreadingHTTPServer(("127.0.0.1", 0), app.make_handler(ROOT, db))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    paths = [
        "/api/v3/online/latest-trade-date",
        "/api/v3/events/overview",
        "/api/v3/events/pools?pool_type=limit_up",
        "/api/v3/events/topics",
        "/api/v3/events/distribution",
        "/api/v3/events/topics/7/members",
        "/api/v3/events/stocks/SH.600001",
        "/api/v3/hot-rankings",
        "/api/v3/hot-plates?type=concept",
        "/api/v3/hot-topics?page=1&page_size=30",
        "/api/v3/research/sectors/X/online-context",
    ]
    try:
        for path in paths:
            response = urllib.request.urlopen(f"http://127.0.0.1:{server.server_port}{path}")
            assert response.status == 200
            payload = json.loads(response.read().decode("utf-8"))
            assert "status" in payload
            if path == "/api/v3/events/overview":
                assert payload["promotion"]["rate"] == 0.25
            if path == "/api/v3/online/latest-trade-date":
                assert payload["trade_date"] == "2026-09-14"
                assert payload["independent_from_local_publication"] is True
            if path == "/api/v3/events/distribution":
                assert "amount_coverage" in payload
        page = urllib.request.urlopen(f"http://127.0.0.1:{server.server_port}/v3/online").read().decode("utf-8")
        assert "V3 在线事件与热度" in page
        assert "/api/v3/events/distribution" in page
        assert "REQUEST_TIME_ONLY" in page or "raw/row/batch" in page
        assert "龙字诀" not in page
        assert "龙字决" not in page
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
