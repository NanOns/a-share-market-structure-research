from __future__ import annotations

import duckdb

from workbench_db.migrations import BASE_SCHEMA_VERSION, MigrationExecutor


def _connection():
    connection = duckdb.connect(":memory:")
    connection.execute((__import__("pathlib").Path(__file__).parents[2] / "src/workbench_db/schema.sql").read_text(encoding="utf-8"))
    connection.execute("INSERT INTO schema_migrations VALUES (?, current_timestamp)", [BASE_SCHEMA_VERSION])
    return connection


def test_p09_02_c_migration_creates_bounded_close_event_tables_and_required_fields():
    connection = _connection()
    try:
        result = MigrationExecutor(connection).apply()
        assert result["status"] == "APPLIED"
        tables = {row[0] for row in connection.execute("SHOW TABLES").fetchall()}
        assert {"online_event_bundles", "online_event_header", "online_pool_entries"}.issubset(tables)

        header_columns = {row[1] for row in connection.execute("PRAGMA table_info('online_event_header')").fetchall()}
        assert {"batch_id", "counts", "rates", "scope", "source_notice"}.issubset(header_columns)

        pool_columns = {row[1] for row in connection.execute("PRAGMA table_info('online_pool_entries')").fetchall()}
        assert {
            "batch_id",
            "pool_type",
            "source_code",
            "security_id",
            "event_state",
            "consecutive_limit_days",
            "m_days",
            "n_boards",
            "first_limit_time",
            "last_limit_time",
            "last_break_time",
            "price",
            "amount",
            "seal_amount",
            "ret1",
            "turnover",
            "float_market_cap",
            "open_count",
            "source_reason",
            "source_fields",
            "quality_codes",
        }.issubset(pool_columns)

        dependency = connection.execute(
            "SELECT dependencies FROM schema_migration_checks WHERE version=?", ["033_v3_online_events"]
        ).fetchone()[0]
        assert "032_v3_structure_summary_result_rows" in str(dependency)
    finally:
        connection.close()


def test_p09_02_c_stores_header_separately_and_keeps_unknowns_null():
    connection = _connection()
    try:
        MigrationExecutor(connection).apply()
        connection.execute(
            "INSERT INTO online_batches (batch_id,fetch_id,dataset,trade_date,source_as_of,observed_at,first_seen_at,status,row_count,logical_hash,adapter_version) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            ["batch-ext01", "fetch-ext01", "LIMIT_POOL_UP", "2026-09-11", None, "2026-09-12 17:28:09", "2026-09-12 17:28:09", "CLOSE_DEGRADED", 1, "hash", "v3-lz-ext01-batch-read-v1.0"],
        )
        connection.execute(
            "INSERT INTO online_event_header (batch_id,counts,rates,scope,source_notice) VALUES (?,?,?,?,?)",
            ["batch-ext01", '{"source_limit_count":1,"source_broken_count":null}', '{"seal_rate":null,"broken_rate":null}', '{"complete_pagination":false}', None],
        )
        connection.execute(
            "INSERT INTO online_pool_entries (batch_id,pool_type,source_code,security_id,event_state,consecutive_limit_days,m_days,n_boards,price,amount,seal_amount,ret1,turnover,float_market_cap,open_count,source_reason,source_fields,quality_codes) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ["batch-ext01", "LIMIT_UP", "SH:600000", "SH.600000", "LIMIT_UP", None, None, None, 10.12, None, None, None, None, None, 0, "reason", '{"amount":"--"}', '["AMOUNT_SCALE_UNRESOLVED"]'],
        )
        assert connection.execute("SELECT count(*) FROM online_event_header").fetchone()[0] == 1
        row = connection.execute("SELECT amount,seal_amount,ret1,turnover,float_market_cap,consecutive_limit_days,m_days,n_boards FROM online_pool_entries").fetchone()
        assert row == (None, None, None, None, None, None, None, None)
        assert connection.execute("SELECT counts->>'source_limit_count' FROM online_event_header").fetchone()[0] == "1"
    finally:
        connection.close()
