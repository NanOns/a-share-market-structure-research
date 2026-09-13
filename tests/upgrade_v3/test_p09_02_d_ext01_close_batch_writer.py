from __future__ import annotations

import json

import duckdb
import pytest

from workbench_db.migrations import BASE_SCHEMA_VERSION, MigrationExecutor
from workbench_online.base import FetchResult
from workbench_online.event_batch import read_ext01_batch
from workbench_online.event_store import EventStoreError, store_close_event_batch


ROOT = __import__("pathlib").Path(__file__).parents[2]


def _connection():
    connection = duckdb.connect(":memory:")
    connection.execute((ROOT / "src/workbench_db/schema.sql").read_text(encoding="utf-8"))
    connection.execute("INSERT INTO schema_migrations VALUES (?, current_timestamp)", [BASE_SCHEMA_VERSION])
    MigrationExecutor(connection).apply()
    connection.execute(
        "INSERT INTO data_sources (source_id,name,source_class,adapter_version,enabled,terms_state,capabilities,cache_policy) VALUES (?,?,?,?,?,?,?,?)",
        ["EXT01", "THS limit-up", "PUBLIC", "v3-lz-ext01-event-adapter-v1.0", False, "RESEARCH_ONLY", '{"dataset":"LIMIT_POOL_UP"}', '{"raw_payloads":false}'],
    )
    return connection


def _body(page: int, has_more: bool, rows: list[dict]) -> bytes:
    return json.dumps({"status_code": 0, "data": {"page": {"page": page, "page_size": 20, "total_pages": 1, "has_more": has_more}, "msg": "", "trade_status": 1, "limit_up_count": {"today": {"num": len(rows)}}, "limit_down_count": {"today": {"num": 0}}, "info": rows}}).encode()


def _row(code: str) -> dict:
    return {"code": code, "name": f"SYNTHETIC_{code}", "latest": "10.12", "change_rate": "10.02", "amount": "--", "order_amount": "--", "currency_value": "--", "turnover_rate": "--", "open_num": 0, "reason_type": "synthetic", "first_limit_up_time": 1757554260, "last_limit_up_time": 0, "market_id": 17}


def _complete_result():
    def fake_fetcher(url, policy):
        return FetchResult("2026-09-12T17:28:00+00:00", "2026-09-12T17:28:09+00:00", 200, "application/json", _body(1, False, [_row("600000")]), url)

    return read_ext01_batch(trade_date="20260911", fetcher=fake_fetcher)


def test_close_batch_writer_commits_source_fetch_batch_bundle_header_and_members_atomically():
    connection = _connection()
    try:
        result = _complete_result()
        stored = store_close_event_batch(connection, result, fetch_id="fetch-ext01", requested_at="2026-09-12T17:28:00+00:00")

        assert stored["status"] == "STORED"
        assert stored["inserted"] is True
        assert stored["raw_payload_persisted"] is False
        assert connection.execute("SELECT count(*) FROM online_fetch_runs").fetchone()[0] == 1
        assert connection.execute("SELECT raw_hash FROM online_fetch_runs").fetchone()[0] is None
        assert connection.execute("SELECT count(*) FROM online_batches").fetchone()[0] == 1
        assert connection.execute("SELECT count(*) FROM online_event_bundles").fetchone()[0] == 1
        assert connection.execute("SELECT count(*) FROM online_event_header").fetchone()[0] == 1
        assert connection.execute("SELECT count(*) FROM online_pool_entries").fetchone()[0] == 1
        assert connection.execute("SELECT amount,ret1,m_days,n_boards FROM online_pool_entries").fetchone() == (None, None, None, None)
        assert connection.execute("SELECT counts->>'source_limit_count' FROM online_event_header").fetchone()[0] == "1"
    finally:
        connection.close()


def test_close_batch_writer_is_idempotent_and_does_not_overwrite_existing_batch():
    connection = _connection()
    try:
        result = _complete_result()
        first = store_close_event_batch(connection, result, fetch_id="fetch-ext01")
        second = store_close_event_batch(connection, result, fetch_id="fetch-ext01")
        assert first["status"] == "STORED"
        assert second["status"] == "ALREADY_STORED"
        assert second["inserted"] is False
        assert connection.execute("SELECT count(*) FROM online_batches").fetchone()[0] == 1
        assert connection.execute("SELECT count(*) FROM online_pool_entries").fetchone()[0] == 1
    finally:
        connection.close()


def test_close_batch_writer_rejects_incomplete_batch_without_writing_anything():
    connection = _connection()
    try:
        def fake_fetcher(url, policy):
            return FetchResult("2026-09-12T17:28:00+00:00", "2026-09-12T17:28:09+00:00", 200, "application/json", _body(1, True, [_row("600000")]), url)

        result = read_ext01_batch(trade_date="20260911", fetcher=fake_fetcher)
        with pytest.raises(EventStoreError, match="COVERAGE_INCOMPLETE"):
            store_close_event_batch(connection, result, fetch_id="fetch-incomplete")
        assert connection.execute("SELECT count(*) FROM online_fetch_runs").fetchone()[0] == 0
        assert connection.execute("SELECT count(*) FROM online_batches").fetchone()[0] == 0
    finally:
        connection.close()


def test_close_batch_writer_rolls_back_if_a_member_field_is_not_json_serializable():
    connection = _connection()
    try:
        result = _complete_result()
        row = result.rows[0]
        bad_row = __import__("dataclasses").replace(row, source_fields={"bad": object()})
        bad_result = __import__("dataclasses").replace(result, rows=(bad_row,))
        with pytest.raises(EventStoreError, match="CLOSE_BATCH_WRITE_FAILED"):
            store_close_event_batch(connection, bad_result, fetch_id="fetch-rollback")
        assert connection.execute("SELECT count(*) FROM online_fetch_runs").fetchone()[0] == 0
        assert connection.execute("SELECT count(*) FROM online_batches").fetchone()[0] == 0
        assert connection.execute("SELECT count(*) FROM online_event_header").fetchone()[0] == 0
        assert connection.execute("SELECT count(*) FROM online_pool_entries").fetchone()[0] == 0
    finally:
        connection.close()
