from __future__ import annotations

import json
import threading
import urllib.request
from contextlib import nullcontext
from datetime import datetime
from pathlib import Path

import duckdb

import workbench_service.app as app
from workbench_db import WorkbenchRepository
from workbench_service.online_events import OnlineEventQueries


ROOT = Path(__file__).parents[2]


def _seed(connection: duckdb.DuckDBPyConnection) -> None:
    connection.execute("INSERT INTO data_sources (source_id,name,source_class,adapter_version,enabled,terms_state,capabilities,cache_policy) VALUES (?,?,?,?,?,?,?,?)", ["EXT01", "THS limit-up", "PUBLIC", "v3-lz-ext01-event-adapter-v1.0", False, "RESEARCH_ONLY", '{"dataset":"LIMIT_POOL_UP"}', '{"raw_payloads":false}'])
    connection.execute("INSERT INTO online_fetch_runs (fetch_id,source_id,dataset,requested_at,received_at,status,http_status,adapter_version) VALUES (?,?,?,?,?,?,?,?)", ["fetch-1", "EXT01", "LIMIT_POOL_UP", "2026-09-12 09:00:00", "2026-09-12 09:00:01", "CLOSE_DEGRADED", 200, "v3-lz-ext01-event-adapter-v1.0"])
    connection.execute("INSERT INTO online_batches (batch_id,fetch_id,dataset,trade_date,source_as_of,observed_at,first_seen_at,status,row_count,logical_hash,adapter_version) VALUES (?,?,?,?,?,?,?,?,?,?,?)", ["batch-1", "fetch-1", "LIMIT_POOL_UP", "2026-09-11", None, "2026-09-12 09:00:01", "2026-09-12 09:00:01", "CLOSE_DEGRADED", 3, "logical-1", "v3-lz-ext01-event-adapter-v1.0"])
    connection.execute("INSERT INTO online_event_header (batch_id,counts,rates,scope,source_notice) VALUES (?,?,?,?,?)", ["batch-1", '{"source_limit_count":3,"source_broken_count":null,"source_down_count":0}', '{"seal_rate":null,"broken_rate":null,"source_rate":null}', '{"complete_pagination":true,"coverage_status":"COMPLETE"}', None])
    connection.execute("INSERT INTO online_event_bundles (bundle_id,trade_date,source_batch_bindings,source_statuses,observed_at,coverage) VALUES (?,?,?,?,?,?)", ["bundle-1", "2026-09-11", '{"EXT01":"batch-1"}', '{"EXT01":"DEGRADED"}', "2026-09-12 09:00:01", '{"complete_pagination":true,"coverage_status":"COMPLETE"}'])
    rows = [
        ("batch-1", "LIMIT_UP", "SH:600005", "SH.600005", "LIMIT_UP", 5, None, None, "2026-09-11 09:35:00", "2026-09-11 09:40:00", None, 10.1, None, None, None, None, None, 0, "five boards", '{"name":"FIVE"}', '["RET1_SCALE_UNRESOLVED"]'),
        ("batch-1", "LIMIT_UP", "SH:600002", "SH.600002", "LIMIT_UP", 2, None, None, "2026-09-11 09:31:00", "2026-09-11 09:32:00", None, 10.2, None, None, None, None, None, 1, "two boards", '{"name":"TWO"}', '["RET1_SCALE_UNRESOLVED"]'),
        ("batch-1", "LIMIT_UP", "SZ:300001", "SZ.300001", "LIMIT_UP", None, 9, 5, "2026-09-11 09:30:00", "2026-09-11 09:30:30", None, 20.0, None, None, None, None, None, 0, "m days n boards", '{"name":"M_N"}', '["LADDER_SEMANTICS_UNRESOLVED"]'),
    ]
    connection.executemany("INSERT INTO online_pool_entries (batch_id,pool_type,source_code,security_id,event_state,consecutive_limit_days,m_days,n_boards,first_limit_time,last_limit_time,last_break_time,price,amount,seal_amount,ret1,turnover,float_market_cap,open_count,source_reason,source_fields,quality_codes) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", rows)


def _db(tmp_path: Path):
    db = tmp_path / "events.duckdb"
    with WorkbenchRepository(ROOT, db):
        pass
    connection = duckdb.connect(str(db))
    _seed(connection)
    connection.close()
    return db


def test_ext01_ladder_query_has_explicit_status_header_pagination_and_two_sort_modes(tmp_path):
    db = _db(tmp_path)
    connection = duckdb.connect(str(db))
    try:
        service = OnlineEventQueries(lambda: nullcontext(connection))
        result = service.ladder(page=1, page_size=2)
        assert result["api_contract"] == "v3-events-ladder-api-v1.0"
        assert result["status"] == "DEGRADED"
        assert result["total"] == 3 and result["returned_count"] == 2 and result["has_more"] is True
        assert result["header"]["counts"]["source_limit_count"] == 3
        assert [item["security_id"] for item in result["items"]] == ["SH.600005", "SH.600002"]
        assert result["items"][0]["height_display"] == "5板"
        assert result["items"][1]["height_display"] == "2板"

        first = service.ladder(sort="FIRST_LIMIT_TIME")
        assert [item["security_id"] for item in first["items"]] == ["SZ.300001", "SH.600002", "SH.600005"]
        mn = next(item for item in first["items"] if item["security_id"] == "SZ.300001")
        assert mn["consecutive_limit_days"] is None and mn["m_days"] == 9 and mn["n_boards"] == 5 and mn["height_display"] == "9天5板"
    finally:
        connection.close()


def test_ext01_ladder_query_returns_explicit_empty_state_without_batch(tmp_path):
    db = _db(tmp_path)
    connection = duckdb.connect(str(db))
    try:
        connection.execute("DELETE FROM online_event_bundles")
        result = OnlineEventQueries(lambda: nullcontext(connection)).ladder(trade_date="2026-09-12")
        assert result["status"] == "UNAVAILABLE"
        assert result["empty_state"]["code"] == "EVENT_BUNDLE_UNAVAILABLE"
        assert result["items"] == []
    finally:
        connection.close()


def test_ext01_ladder_api_and_page_are_independently_reachable(tmp_path):
    db = tmp_path / "empty-events.duckdb"
    with WorkbenchRepository(ROOT, db):
        pass
    server = __import__("http.server").server.ThreadingHTTPServer(("127.0.0.1", 0), app.make_handler(ROOT, db))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        api_response = urllib.request.urlopen(f"http://127.0.0.1:{server.server_port}/api/v3/events/ladder?page=1&page_size=20")
        payload = json.loads(api_response.read().decode("utf-8"))
        assert api_response.status == 200
        assert payload["status"] == "UNAVAILABLE"
        page_response = urllib.request.urlopen(f"http://127.0.0.1:{server.server_port}/v3/events")
        page = page_response.read().decode("utf-8")
        assert page_response.status == 200
        assert "V3 在线涨停简图" in page
        assert "/api/v3/events/ladder" in page
        assert "不以本地数据冒充在线事实" in page
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
