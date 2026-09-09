import numpy as np
import pandas as pd
import pytest
import duckdb
from pathlib import Path
from datetime import datetime, timezone

from workbench_analysis.highs import calculate_high_daily, insert_high_rows
from workbench_analysis.strength import average_rank_percentile, calculate_strength_daily, insert_strength_rows
from workbench_db.migrations import BASE_SCHEMA_VERSION, MigrationExecutor
from workbench_service.app import Api


def test_new_high_uses_prior_window_only_and_equal_high_is_not_new():
    dates = pd.date_range("2026-01-01", periods=23, freq="B")
    close = [10.0] * 20 + [10.0, 10.01, 10.01]
    frame = pd.DataFrame({"security_id": "SH.600000", "date": dates, "adj_close": close})
    out = calculate_high_daily(frame)
    rows = out.set_index("date")
    assert rows.iloc[20]["new_high_20"] is False
    assert rows.iloc[20]["at_prior_high_20"] is True
    assert rows.iloc[21]["new_high_20"] is True
    assert rows.iloc[21]["high_streak_20"] == 1
    assert rows.iloc[22]["new_high_20"] is False
    assert rows.iloc[22]["at_prior_high_20"] is True
    assert rows.iloc[22]["high_streak_20"] == 0
    assert bool(rows.iloc[0]["is_left_censored_20"]) is True


def test_each_high_window_has_its_own_streak_and_missing_is_unknown():
    dates = pd.date_range("2026-01-01", periods=102, freq="B")
    close = np.arange(102, dtype=float) + 10
    frame = pd.DataFrame({"security_id": "SZ.000001", "date": dates, "adj_close": close})
    out = calculate_high_daily(frame)
    early = out.iloc[20]
    late = out.iloc[-1]
    assert bool(early["new_high_20"]) is True
    assert pd.isna(early["new_high_100"])
    assert bool(late["new_high_20"]) is True
    assert bool(late["new_high_100"]) is True
    missing = frame.copy()
    missing.loc[101, "adj_close"] = np.nan
    unknown = calculate_high_daily(missing).iloc[-1]
    assert pd.isna(unknown["new_high_20"])
    assert pd.isna(unknown["high_streak_20"])


def test_rps_uses_average_ties_divided_by_same_date_n():
    values = pd.Series([0.01, 0.01, 0.03, 0.04])
    result = average_rank_percentile(values)
    assert result.tolist() == pytest.approx([0.375, 0.375, 0.75, 1.0])


def test_rps_is_null_when_same_date_valid_universe_is_below_100():
    dates = pd.date_range("2026-01-01", periods=21, freq="B")
    rows = []
    for index in range(99):
        for date in dates:
            rows.append({"security_id": f"SH.{index:06d}", "date": date, "raw_close": 10 + index + dates.get_loc(date), "adj_close": 10 + index + dates.get_loc(date), "raw_amount": 100, "raw_volume": 1000, "universe_status": "IN_NORMAL_UNIVERSE"})
    out = calculate_strength_daily(pd.DataFrame(rows))
    last = out[out.date == dates[-1]]
    assert (last["rps_valid_universe_count20"] == 99).all()
    assert last["rps20"].isna().all()


def test_high_and_strength_rows_write_to_immutable_m8a02_tables(tmp_path):
    root = Path(__file__).parents[2]
    connection = duckdb.connect(str(tmp_path / "high-rps.duckdb"))
    try:
        connection.execute((root / "src/workbench_db/schema.sql").read_text(encoding="utf-8"))
        connection.execute("insert into schema_migrations values (?, current_timestamp)", [BASE_SCHEMA_VERSION])
        MigrationExecutor(connection).apply()
        connection.execute(
            "insert into analysis_slices values (?,?,?,?,?,?,?,?,?,?,?,?)",
            ["slice-1", "high", "2026-08-28", "c", "i", "d", "{}", 1, "l", "DUCKDB", None, "2026-08-28"],
        )
        prices = pd.DataFrame({"security_id": ["SH.600000"], "date": ["2026-08-28"], "adj_close": [10.0]})
        assert insert_high_rows(connection, "slice-1", calculate_high_daily(prices)) == 4
        strength = pd.DataFrame({"security_id": ["SH.600000"], "date": ["2026-08-28"], "raw_close": [10.0], "adj_close": [10.0], "raw_amount": [100.0], "raw_volume": [1000.0], "universe_status": ["IN_NORMAL_UNIVERSE"]})
        assert insert_strength_rows(connection, "slice-1", calculate_strength_daily(strength)) == 1
        assert connection.execute("select count(*) from stock_high_daily").fetchone()[0] == 4
        assert connection.execute("select count(*) from stock_strength_daily").fetchone()[0] == 1
    finally:
        connection.close()


def test_api11_reads_only_snapshot_bound_high_slices(tmp_path):
    root = Path(__file__).parents[2]
    (tmp_path / "config").mkdir()
    (tmp_path / "config/history_windows.yaml").write_text((root / "config/history_windows.yaml").read_text(encoding="utf-8"), encoding="utf-8")
    connection = duckdb.connect(str(tmp_path / "api.duckdb"))
    try:
        connection.execute((root / "src/workbench_db/schema.sql").read_text(encoding="utf-8"))
        connection.execute("insert into schema_migrations values (?, current_timestamp)", [BASE_SCHEMA_VERSION])
        MigrationExecutor(connection).apply()
        now = datetime.now(timezone.utc)
        connection.execute("insert into publications values (?,?,?,?,?,?,?,?,?,?,?,?)", ["pub-1", "2026-01-29", 1, "SUCCESS", 1, "test", None, None, None, None, "fixture", now])
        connection.execute("insert into analysis_snapshots values (?,?,?,?,?,?,?,?)", ["snapshot-1", "2026-01-29", "2025-01-01", "CN_A_LISTED_V2", "config", "manifest", "SUCCESS", now])
        connection.execute("insert into publication_analysis_snapshots values (?,?,?,?)", ["pub-1", "LOCAL_RECONSTRUCTED", "snapshot-1", now])
        connection.execute("insert into analysis_slices values (?,?,?,?,?,?,?,?,?,?,?,?)", ["slice-1", "high", "2026-01-29", "c", "i", "d", "{}", 84, "l", "DUCKDB", None, now])
        dates = pd.date_range("2025-12-31", periods=21, freq="B")
        prices = pd.DataFrame({"security_id": "SH.600000", "date": dates, "adj_close": [10.0] * 21})
        insert_high_rows(connection, "slice-1", calculate_high_daily(prices))
        connection.execute("insert into analysis_snapshot_entries values (?,?,?,?)", ["snapshot-1", "high", dates[-1].date(), "slice-1"])
        connection.close()
        api = Api(tmp_path / "api.duckdb", root=tmp_path)
        result = api.new_highs("pub-1", include_ties=True)
        assert result["snapshot_id"] == "snapshot-1"
        assert result["total"] == 1
        assert result["items"][0]["at_prior_high"] is True
        with pytest.raises(ValueError, match="RPS_NOT_BUILT"):
            api.new_highs("pub-1", rps_min="0.8")
    finally:
        if connection:
            try:
                connection.close()
            except Exception:
                pass
