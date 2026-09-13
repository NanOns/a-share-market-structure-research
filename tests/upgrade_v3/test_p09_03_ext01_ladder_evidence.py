from __future__ import annotations

import json
import threading
import urllib.parse
import urllib.request
from contextlib import nullcontext

import duckdb

import workbench_service.app as app
from workbench_service.online_events import ONLINE_EVENT_EVIDENCE_API_CONTRACT, OnlineEventQueries

from test_p09_03_ext01_ladder_slice import ROOT, _db


def test_ext01_single_stock_evidence_has_source_time_and_field_statuses(tmp_path):
    db = _db(tmp_path)
    connection = duckdb.connect(str(db))
    try:
        result = OnlineEventQueries(lambda: nullcontext(connection)).ladder_evidence(
            security_id="SH.600005", trade_date="2026-09-11"
        )
        assert result["api_contract"] == ONLINE_EVENT_EVIDENCE_API_CONTRACT
        assert result["status"] == "DEGRADED"
        assert result["security_id"] == "SH.600005"
        assert result["source_time"]["basis"] == "OBSERVED_AT_ONLY"
        assert result["source_time"]["source_as_of"] is None
        assert result["evidence"]["raw_payload_persisted"] is False
        fields = {item["normalized_field"]: item for item in result["evidence"]["field_evidence"]}
        assert fields["price"]["source_field"] == "latest"
        assert fields["price"]["status"] == "OBSERVED"
        assert fields["ret1"]["status"] == "UNCONFIRMED"
        assert result["item"]["security_name"] == "FIVE"
    finally:
        connection.close()


def test_ext01_single_stock_evidence_accepts_source_code_and_missing_member_is_explicit(tmp_path):
    db = _db(tmp_path)
    connection = duckdb.connect(str(db))
    try:
        service = OnlineEventQueries(lambda: nullcontext(connection))
        by_source_code = service.ladder_evidence(security_id="SH:600005", event_bundle_id="bundle-1")
        assert by_source_code["security_id"] == "SH.600005"
        missing = service.ladder_evidence(security_id="SH.999999", event_bundle_id="bundle-1")
        assert missing["status"] == "UNAVAILABLE"
        assert missing["empty_state"]["code"] == "EVENT_MEMBER_UNAVAILABLE"
        assert missing["item"] is None and missing["evidence"] is None
    finally:
        connection.close()


def test_ext01_single_stock_evidence_route_and_page_contract(tmp_path):
    db = _db(tmp_path)
    server = __import__("http.server").server.ThreadingHTTPServer(("127.0.0.1", 0), app.make_handler(ROOT, db))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        url = f"http://127.0.0.1:{server.server_port}/api/v3/events/ladder/{urllib.parse.quote('SH.600005')}?event_bundle_id=bundle-1"
        response = urllib.request.urlopen(url)
        payload = json.loads(response.read().decode("utf-8"))
        assert response.status == 200
        assert payload["api_contract"] == ONLINE_EVENT_EVIDENCE_API_CONTRACT
        assert payload["evidence"]["identity"]["batch_id"] == "batch-1"
        assert payload["source_time"]["observed_at"] == "2026-09-12T09:00:01"

        page_response = urllib.request.urlopen(f"http://127.0.0.1:{server.server_port}/v3/events")
        page = page_response.read().decode("utf-8")
        assert page_response.status == 200
        assert "/api/v3/events/ladder/" in page
        assert "source_as_of" in page
        assert "evidenceModal" in page
        assert "证据" in page
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
