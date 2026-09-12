from pathlib import Path

import duckdb
import pandas as pd

from workbench_analysis.structures import (
    build_historical_structure_rows,
    insert_structure_result_rows,
)
from workbench_db.migrations import BASE_SCHEMA_VERSION, MigrationExecutor


ROOT = Path(__file__).parents[2]


def _database(tmp_path):
    database = tmp_path / "structure-result-rows.duckdb"
    connection = duckdb.connect(str(database))
    connection.execute((ROOT / "src/workbench_db/schema.sql").read_text(encoding="utf-8"))
    connection.execute("INSERT INTO schema_migrations VALUES (?, current_timestamp)", [BASE_SCHEMA_VERSION])
    receipt = MigrationExecutor(connection).apply()
    assert receipt["applied"][-1]["version"] == "031_v3_structure_result_rows"
    connection.close()
    return database


def _frame(*, changed=False):
    result = build_historical_structure_rows(
        pd.DataFrame([{
            "security_id": "SH.600001",
            "trade_date": "2026-08-28",
            "v1_steady_trend": True,
            "continuity_value": 0.65,
            "continuity_valid_count": 20,
            "continuity_valid_ratio": 0.80,
            "pulse_value": 0.20,
            "v1_strong_pullback": False,
            "v1_breakout_prep": False,
            "v1_sector_leader": False,
            "v1_early_mover": False,
        }]),
        cutoff="2026-08-28",
    )
    if changed:
        result.at[0, "hit"] = True
    return result


def _slice(connection, slice_id):
    connection.execute(
        "INSERT INTO analysis_slices VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        [slice_id, "structure", "2026-08-28", "HISTORICAL_STRUCTURE_V2_1_RECONSTRUCTED", "input", "dependency", "{}", 5, "legacy", "DUCKDB", None, "2026-08-28"],
    )


def test_structure_result_rows_share_content_and_preserve_binding(tmp_path):
    database = _database(tmp_path)
    with duckdb.connect(str(database)) as connection:
        _slice(connection, "slice-a")
        _slice(connection, "slice-b")
        assert insert_structure_result_rows(connection, "slice-a", _frame()) == 5
        assert insert_structure_result_rows(connection, "slice-b", _frame()) == 5
        for _ in range(3):
            assert insert_structure_result_rows(connection, "slice-a", _frame()) == 5

        assert connection.execute("SELECT count(*) FROM historical_structure_daily").fetchone()[0] == 0
        assert connection.execute("SELECT count(*) FROM structure_result_rows").fetchone()[0] == 5
        assert connection.execute("SELECT count(*) FROM analysis_result_objects WHERE domain='structure'").fetchone()[0] == 1
        assert connection.execute("SELECT count(*) FROM analysis_slice_result_bindings").fetchone()[0] == 2
        assert connection.execute("SELECT count(*) FROM historical_structure_result_daily").fetchone()[0] == 10
        assert connection.execute("SELECT count(*) FROM historical_structure_result_daily WHERE result_object_id IS NULL").fetchone()[0] == 0


def test_structure_evidence_change_does_not_share_object(tmp_path):
    database = _database(tmp_path)
    with duckdb.connect(str(database)) as connection:
        _slice(connection, "slice-a")
        _slice(connection, "slice-b")
        insert_structure_result_rows(connection, "slice-a", _frame())
        insert_structure_result_rows(connection, "slice-b", _frame(changed=True))

        assert connection.execute("SELECT count(*) FROM analysis_result_objects WHERE domain='structure'").fetchone()[0] == 2
        assert connection.execute("SELECT count(*) FROM structure_result_rows").fetchone()[0] == 10
