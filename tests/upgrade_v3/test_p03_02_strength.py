from pathlib import Path

import duckdb
import pandas as pd

from workbench_analysis.strength import (
    calculate_strength_daily,
    insert_strength_result_rows,
)
from workbench_db.migrations import BASE_SCHEMA_VERSION, MigrationExecutor


ROOT = Path(__file__).parents[2]


def _database(tmp_path):
    database = tmp_path / "strength-result-rows.duckdb"
    connection = duckdb.connect(str(database))
    connection.execute((ROOT / "src/workbench_db/schema.sql").read_text(encoding="utf-8"))
    connection.execute("INSERT INTO schema_migrations VALUES (?, current_timestamp)", [BASE_SCHEMA_VERSION])
    receipt = MigrationExecutor(connection).apply()
    assert receipt["applied"][-1]["version"] == "030_v3_member_state_result_rows"
    connection.close()
    return database


def _frame(*, quality="OK"):
    result = calculate_strength_daily(pd.DataFrame({
        "security_id": ["SH.600001"],
        "date": pd.to_datetime(["2026-08-28"]),
        "raw_close": [10.0],
        "adj_close": [10.0],
        "raw_amount": [100.0],
        "raw_volume": [1000.0],
        "data_quality_flag": [quality],
        "is_synthetic_fill": [False],
    }))
    if quality != "OK":
        result.at[0, "strength_quality_codes"] = [quality]
    return result


def _slice(connection, slice_id):
    connection.execute(
        "INSERT INTO analysis_slices VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        [slice_id, "strength", "2026-08-28", "TECHNICAL_HISTORY_V2_1_PREVIEW", "input", "dependency", "{}", 1, "legacy", "DUCKDB", None, "2026-08-28"],
    )


def test_strength_result_rows_share_content_but_preserve_slice_bindings(tmp_path):
    database = _database(tmp_path)
    with duckdb.connect(str(database)) as connection:
        _slice(connection, "slice-a")
        _slice(connection, "slice-b")
        assert insert_strength_result_rows(connection, "slice-a", _frame()) == 1
        assert insert_strength_result_rows(connection, "slice-b", _frame()) == 1

        assert connection.execute("SELECT count(*) FROM stock_strength_daily").fetchone()[0] == 0
        assert connection.execute("SELECT count(*) FROM strength_result_rows").fetchone()[0] == 1
        assert connection.execute("SELECT count(*) FROM analysis_result_objects WHERE domain='strength'").fetchone()[0] == 1
        assert connection.execute("SELECT count(*) FROM analysis_slice_result_bindings").fetchone()[0] == 2
        assert connection.execute("SELECT count(*) FROM strength_result_daily").fetchone()[0] == 2


def test_strength_quality_change_does_not_share_object(tmp_path):
    database = _database(tmp_path)
    with duckdb.connect(str(database)) as connection:
        _slice(connection, "slice-a")
        _slice(connection, "slice-b")
        insert_strength_result_rows(connection, "slice-a", _frame())
        insert_strength_result_rows(connection, "slice-b", _frame(quality="CORPORATE_ACTION_UNSAFE"))
        assert connection.execute("SELECT count(*) FROM analysis_result_objects WHERE domain='strength'").fetchone()[0] == 2
        assert connection.execute("SELECT count(*) FROM strength_result_rows").fetchone()[0] == 2
