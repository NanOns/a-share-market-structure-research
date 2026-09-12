from pathlib import Path

import duckdb
import pandas as pd

from workbench_analysis.highs import calculate_high_daily, insert_high_result_rows
from workbench_db.migrations import BASE_SCHEMA_VERSION, MigrationExecutor


ROOT = Path(__file__).parents[2]


def _database(tmp_path):
    database = tmp_path / "high-result-rows.duckdb"
    connection = duckdb.connect(str(database))
    connection.execute((ROOT / "src/workbench_db/schema.sql").read_text(encoding="utf-8"))
    connection.execute("INSERT INTO schema_migrations VALUES (?, current_timestamp)", [BASE_SCHEMA_VERSION])
    receipt = MigrationExecutor(connection).apply()
    assert receipt["applied"][-1]["version"] == "030_v3_member_state_result_rows"
    connection.close()
    return database


def _frame(*, changed=False):
    result = calculate_high_daily(pd.DataFrame({
        "security_id": ["SH.600001"],
        "date": pd.to_datetime(["2026-08-28"]),
        "raw_close": [10.0],
        "adj_close": [10.0],
        "raw_amount": [100.0],
        "raw_volume": [1000.0],
        "data_quality_flag": ["OK"],
        "is_synthetic_fill": [False],
    }))
    if changed:
        result.at[0, "new_high_20"] = True
    return result


def _slice(connection, slice_id):
    connection.execute(
        "INSERT INTO analysis_slices VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        [slice_id, "high", "2026-08-28", "TECHNICAL_HISTORY_V2_1_PREVIEW", "input", "dependency", "{}", 4, "legacy", "DUCKDB", None, "2026-08-28"],
    )


def test_high_result_rows_preserve_all_four_windows_and_share_content(tmp_path):
    database = _database(tmp_path)
    with duckdb.connect(str(database)) as connection:
        _slice(connection, "slice-a")
        _slice(connection, "slice-b")
        assert insert_high_result_rows(connection, "slice-a", _frame()) == 4
        assert insert_high_result_rows(connection, "slice-b", _frame()) == 4
        for _ in range(3):
            assert insert_high_result_rows(connection, "slice-a", _frame()) == 4

        assert connection.execute("SELECT count(*) FROM stock_high_daily").fetchone()[0] == 0
        assert connection.execute("SELECT count(*) FROM high_result_rows").fetchone()[0] == 4
        assert connection.execute("SELECT count(*) FROM analysis_result_objects WHERE domain='high'").fetchone()[0] == 1
        assert connection.execute("SELECT count(*) FROM analysis_slice_result_bindings").fetchone()[0] == 2
        assert connection.execute("SELECT count(*) FROM high_result_daily").fetchone()[0] == 8
        assert connection.execute('SELECT list("window" ORDER BY "window") FROM high_result_rows').fetchone()[0] == [20, 30, 60, 100]


def test_high_value_change_does_not_share_object(tmp_path):
    database = _database(tmp_path)
    with duckdb.connect(str(database)) as connection:
        _slice(connection, "slice-a")
        _slice(connection, "slice-b")
        insert_high_result_rows(connection, "slice-a", _frame())
        insert_high_result_rows(connection, "slice-b", _frame(changed=True))
        assert connection.execute("SELECT count(*) FROM analysis_result_objects WHERE domain='high'").fetchone()[0] == 2
        assert connection.execute("SELECT count(*) FROM high_result_rows").fetchone()[0] == 8
