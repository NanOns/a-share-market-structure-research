from pathlib import Path

import duckdb
import pandas as pd

from workbench_analysis.technical import (
    calculate_technical_daily,
    insert_technical_result_rows,
)
from workbench_db.migrations import BASE_SCHEMA_VERSION, MigrationExecutor


ROOT = Path(__file__).parents[2]


def _database(tmp_path):
    database = tmp_path / "technical-result-rows.duckdb"
    connection = duckdb.connect(str(database))
    connection.execute((ROOT / "src/workbench_db/schema.sql").read_text(encoding="utf-8"))
    connection.execute("INSERT INTO schema_migrations VALUES (?, current_timestamp)", [BASE_SCHEMA_VERSION])
    receipt = MigrationExecutor(connection).apply()
    assert receipt["applied"][-1]["version"] == "028_v3_strength_result_rows"
    connection.close()
    return database


def _frame(*, quality="OK"):
    return calculate_technical_daily(pd.DataFrame({
        "security_id": ["SH.600001"],
        "date": pd.to_datetime(["2026-08-28"]),
        "raw_close": [10.0],
        "adj_close": [10.0],
        "raw_amount": [100.0],
        "raw_volume": [1000.0],
        "data_quality_flag": [quality],
        "is_synthetic_fill": [False],
    }))


def _slice(connection, slice_id):
    connection.execute(
        "INSERT INTO analysis_slices VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        [slice_id, "technical", "2026-08-28", "TECHNICAL_HISTORY_V2_1_PREVIEW", "input", "dependency", "{}", 1, "legacy", "DUCKDB", None, "2026-08-28"],
    )


def test_technical_result_rows_share_content_but_preserve_slice_bindings(tmp_path):
    database = _database(tmp_path)
    with duckdb.connect(str(database)) as connection:
        _slice(connection, "slice-a")
        _slice(connection, "slice-b")
        assert insert_technical_result_rows(connection, "slice-a", _frame()) == 1
        assert insert_technical_result_rows(connection, "slice-b", _frame()) == 1

        assert connection.execute("SELECT count(*) FROM stock_technical_daily").fetchone()[0] == 0
        assert connection.execute("SELECT count(*) FROM technical_result_rows").fetchone()[0] == 1
        assert connection.execute("SELECT count(*) FROM analysis_result_objects WHERE domain='technical'").fetchone()[0] == 1
        assert connection.execute("SELECT count(*) FROM analysis_slice_result_bindings").fetchone()[0] == 2
        assert connection.execute("SELECT count(*) FROM technical_result_daily").fetchone()[0] == 2
        assert connection.execute("SELECT count(*) FROM analysis_slices WHERE storage_object_id IS NOT NULL").fetchone()[0] == 2


def test_technical_result_quality_change_does_not_share_object(tmp_path):
    database = _database(tmp_path)
    with duckdb.connect(str(database)) as connection:
        _slice(connection, "slice-a")
        _slice(connection, "slice-b")
        insert_technical_result_rows(connection, "slice-a", _frame())
        insert_technical_result_rows(connection, "slice-b", _frame(quality="CORPORATE_ACTION_UNSAFE"))
        assert connection.execute("SELECT count(*) FROM analysis_result_objects WHERE domain='technical'").fetchone()[0] == 2
        assert connection.execute("SELECT count(*) FROM technical_result_rows").fetchone()[0] == 2
