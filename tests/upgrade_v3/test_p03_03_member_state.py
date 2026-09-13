from pathlib import Path

import duckdb
import pandas as pd

from workbench_analysis.member_state import (
    build_sector_member_state_daily,
    insert_member_state_result_rows,
)
from workbench_db.migrations import BASE_SCHEMA_VERSION, MigrationExecutor


ROOT = Path(__file__).parents[2]


def _database(tmp_path):
    database = tmp_path / "member-state-result-rows.duckdb"
    connection = duckdb.connect(str(database))
    connection.execute((ROOT / "src/workbench_db/schema.sql").read_text(encoding="utf-8"))
    connection.execute("INSERT INTO schema_migrations VALUES (?, current_timestamp)", [BASE_SCHEMA_VERSION])
    receipt = MigrationExecutor(connection).apply()
    assert receipt["applied"][-1]["version"] == "034_v3_signal_outcomes"
    connection.close()
    return database


def _frame(*, changed=False):
    result = build_sector_member_state_daily(
        pd.DataFrame({
            "security_id": ["SH.600001"],
            "trade_date": pd.to_datetime(["2026-08-28"]),
            "ret20": [0.20],
            "rps20": [0.90],
        }),
        pd.DataFrame({
            "sector_id": ["INDUSTRY:1"],
            "sector_name": ["测试行业"],
            "sector_type": ["INDUSTRY"],
            "trade_date": pd.to_datetime(["2026-08-28"]),
            "security_id": ["SH.600001"],
        }),
    )
    if changed:
        result.at[0, "strong_predicates"] = '{"data_valid":false}'
    return result


def _slice(connection, slice_id):
    connection.execute(
        "INSERT INTO analysis_slices VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        [slice_id, "member_state", "2026-08-28", "SECTOR_MEMBER_STATE_V1_2_EXCLUDE_DIAGNOSTIC", "input", "dependency", "{}", 1, "legacy", "DUCKDB", None, "2026-08-28"],
    )


def test_member_state_result_rows_share_content_and_preserve_binding(tmp_path):
    database = _database(tmp_path)
    with duckdb.connect(str(database)) as connection:
        _slice(connection, "slice-a")
        _slice(connection, "slice-b")
        assert insert_member_state_result_rows(connection, "slice-a", _frame()) == 1
        assert insert_member_state_result_rows(connection, "slice-b", _frame()) == 1
        for _ in range(3):
            assert insert_member_state_result_rows(connection, "slice-a", _frame()) == 1

        assert connection.execute("SELECT count(*) FROM sector_member_state_daily").fetchone()[0] == 0
        assert connection.execute("SELECT count(*) FROM member_state_result_rows").fetchone()[0] == 1
        assert connection.execute("SELECT count(*) FROM analysis_result_objects WHERE domain='member_state'").fetchone()[0] == 1
        assert connection.execute("SELECT count(*) FROM analysis_slice_result_bindings").fetchone()[0] == 2
        assert connection.execute("SELECT count(*) FROM member_state_result_daily").fetchone()[0] == 2


def test_member_state_json_value_change_does_not_share_object(tmp_path):
    database = _database(tmp_path)
    with duckdb.connect(str(database)) as connection:
        _slice(connection, "slice-a")
        _slice(connection, "slice-b")
        insert_member_state_result_rows(connection, "slice-a", _frame())
        insert_member_state_result_rows(connection, "slice-b", _frame(changed=True))

        assert connection.execute("SELECT count(*) FROM analysis_result_objects WHERE domain='member_state'").fetchone()[0] == 2
        assert connection.execute("SELECT count(*) FROM member_state_result_rows").fetchone()[0] == 2
