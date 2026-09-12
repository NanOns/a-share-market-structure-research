from pathlib import Path

import duckdb
import pandas as pd

from workbench_analysis.structures import insert_structure_summary_result_rows
from workbench_db.migrations import BASE_SCHEMA_VERSION, MigrationExecutor


ROOT = Path(__file__).parents[2]


def _database(tmp_path):
    database = tmp_path / "summary-result-rows.duckdb"
    connection = duckdb.connect(str(database))
    connection.execute((ROOT / "src/workbench_db/schema.sql").read_text(encoding="utf-8"))
    connection.execute("INSERT INTO schema_migrations VALUES (?, current_timestamp)", [BASE_SCHEMA_VERSION])
    receipt = MigrationExecutor(connection).apply()
    assert receipt["applied"][-1]["version"] == "032_v3_structure_summary_result_rows"
    connection.close()
    return database


def _frame(*, changed=False):
    return pd.DataFrame([
        {
            "security_id": "SH.600001",
            "trade_date": "2026-08-28",
            "queues_json": '{"STEADY_QUEUE":{"hit":true,"queue_rank":1}}',
            "research_band": "CORE_RESEARCH",
            "research_band_quality": "AVAILABLE",
            "unique_hit_count": 1,
            "queue_contract": "research-priority-v2-shadow-v1.0",
        },
        {
            "security_id": "SZ.000001",
            "trade_date": "2026-08-28",
            "queues_json": '{"STEADY_QUEUE":{"hit":false,"queue_rank":null}}',
            "research_band": "DIAGNOSTIC_ONLY" if changed else "SUPPORTED_RESEARCH",
            "research_band_quality": "DATA_INSUFFICIENT" if changed else "AVAILABLE",
            "unique_hit_count": 0,
            "queue_contract": "research-priority-v2-shadow-v1.0",
        },
    ])


def _slice(connection, slice_id):
    connection.execute(
        "INSERT INTO analysis_slices VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        [slice_id, "summary", "2026-08-28", "HISTORICAL_STRUCTURE_V2_1_RECONSTRUCTED", "input", "dependency", "{}", 2, "legacy", "DUCKDB", None, "2026-08-28"],
    )


def test_summary_result_rows_share_content_preserve_identity_and_cut_read(tmp_path):
    database = _database(tmp_path)
    with duckdb.connect(str(database)) as connection:
        _slice(connection, "slice-a")
        _slice(connection, "slice-b")
        assert insert_structure_summary_result_rows(connection, "slice-a", _frame()) == 2
        assert insert_structure_summary_result_rows(connection, "slice-b", _frame()) == 2
        for _ in range(3):
            assert insert_structure_summary_result_rows(connection, "slice-a", _frame()) == 2

        assert connection.execute("SELECT count(*) FROM stock_structure_summary_daily").fetchone()[0] == 0
        assert connection.execute("SELECT count(*) FROM structure_summary_result_rows").fetchone()[0] == 2
        assert connection.execute("SELECT count(*) FROM analysis_result_objects WHERE domain='summary'").fetchone()[0] == 1
        assert connection.execute("SELECT count(*) FROM analysis_slice_result_bindings").fetchone()[0] == 2
        assert connection.execute("SELECT count(*) FROM structure_summary_result_daily").fetchone()[0] == 4
        assert connection.execute("SELECT count(*) FROM structure_summary_result_daily WHERE result_object_id IS NULL").fetchone()[0] == 0


def test_summary_value_or_quality_change_does_not_share_object(tmp_path):
    database = _database(tmp_path)
    with duckdb.connect(str(database)) as connection:
        _slice(connection, "slice-a")
        _slice(connection, "slice-b")
        insert_structure_summary_result_rows(connection, "slice-a", _frame())
        insert_structure_summary_result_rows(connection, "slice-b", _frame(changed=True))

        assert connection.execute("SELECT count(*) FROM analysis_result_objects WHERE domain='summary'").fetchone()[0] == 2
        assert connection.execute("SELECT count(*) FROM structure_summary_result_rows").fetchone()[0] == 4
