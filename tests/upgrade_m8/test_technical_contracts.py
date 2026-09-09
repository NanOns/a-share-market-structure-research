import numpy as np
import pandas as pd
import pytest
import duckdb
from pathlib import Path

from workbench_analysis.technical import insert_technical_rows
from workbench_db.migrations import BASE_SCHEMA_VERSION, MigrationExecutor
from workbench_analysis.technical import (
    CONTRACT_VERSION,
    amount_class,
    calculate_technical_daily,
    ma_alignment,
)


def _frame(days=65):
    dates = pd.date_range("2026-06-01", periods=days, freq="B")
    return pd.DataFrame({
        "security_id": "SH.600000",
        "date": dates,
        "raw_close": np.arange(days, dtype=float) + 10,
        "adj_close": np.arange(days, dtype=float) + 10,
        "raw_amount": 100.0,
        "raw_volume": 1000.0,
        "universe_status": "IN_NORMAL_UNIVERSE",
        "data_quality_flag": "OK",
        "is_synthetic_fill": False,
    })


def test_technical_contract_uses_same_anchor_and_keeps_legacy_amount_ratio():
    frame = _frame()
    frame.loc[64, "raw_amount"] = 300.0
    out = calculate_technical_daily(frame)
    row = out.iloc[-1]
    assert row["technical_contract_id"] == CONTRACT_VERSION
    assert row["ma5"] == pytest.approx(frame["adj_close"].tail(5).mean())
    assert row["amount_ratio20"] == pytest.approx(300 / ((19 * 100 + 300) / 20))
    assert row["amount_vs_prior20"] == pytest.approx(3.0)
    assert row["volume_vs_prior20"] == pytest.approx(1.0)


def test_missing_observation_is_not_skipped_to_fill_a_window():
    frame = _frame()
    frame.loc[60, "adj_close"] = np.nan
    out = calculate_technical_daily(frame)
    assert pd.isna(out.iloc[-1]["ma5"])
    assert pd.isna(out.iloc[-1]["ret5"])
    assert "INSUFFICIENT_HISTORY" in out.iloc[-1]["quality_codes"]


def test_amount_classes_and_ma_alignment_have_explicit_boundaries():
    assert [amount_class(x) for x in (1.49, 1.5, 2, 3)] == ["NORMAL", "INCREASED", "NOTABLE", "SIGNIFICANT"]
    assert ma_alignment((5, 4, 3, 2)) == "BULLISH"
    assert ma_alignment((2, 3, 4, 5)) == "BEARISH"
    assert ma_alignment((5, 4, 4, 2)) == "MIXED"
    assert ma_alignment((None, 4, 3, 2)) is None


def test_future_rows_are_rejected_before_factor_output():
    with pytest.raises(ValueError, match="FUTURE_TECHNICAL_INPUT"):
        calculate_technical_daily(_frame(), cutoff="2026-08-27")


def test_technical_rows_are_immutable_and_written_to_008_table(tmp_path):
    root = Path(__file__).parents[2]
    connection = duckdb.connect(str(tmp_path / "technical.duckdb"))
    try:
        connection.execute((root / "src/workbench_db/schema.sql").read_text(encoding="utf-8"))
        connection.execute("insert into schema_migrations values (?, current_timestamp)", [BASE_SCHEMA_VERSION])
        MigrationExecutor(connection).apply()
        connection.execute(
            "insert into analysis_slices values (?,?,?,?,?,?,?,?,?,?,?,?)",
            ["slice-1", "technical", "2026-08-28", "c", "i", "d", "{}", 1, "l", "DUCKDB", None, "2026-08-28"],
        )
        calculated = calculate_technical_daily(_frame(1))
        assert insert_technical_rows(connection, "slice-1", calculated) == 1
        assert insert_technical_rows(connection, "slice-1", calculated) == 1
        different = calculated.copy()
        different["security_id"] = "SZ.000001"
        with pytest.raises(ValueError, match="TECHNICAL_SLICE_IDENTITY_CONFLICT"):
            insert_technical_rows(connection, "slice-1", different)
    finally:
        connection.close()
