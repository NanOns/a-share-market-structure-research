from datetime import date

import numpy as np
import pandas as pd
import pytest

from workbench_analysis.chart import ChartCache, build_chart_points, chart_cache_key


def _frame():
    dates = pd.date_range("2026-01-01", periods=65, freq="B")
    return pd.DataFrame({
        "date": dates,
        "raw_open": np.arange(65, dtype=float) + 9,
        "raw_high": np.arange(65, dtype=float) + 11,
        "raw_low": np.arange(65, dtype=float) + 8,
        "raw_close": np.arange(65, dtype=float) + 10,
        "adj_open": (np.arange(65, dtype=float) + 9) * 2,
        "adj_high": (np.arange(65, dtype=float) + 11) * 2,
        "adj_low": (np.arange(65, dtype=float) + 8) * 2,
        "adj_close": (np.arange(65, dtype=float) + 10) * 2,
        "raw_volume": 1000.0,
        "raw_amount": 100.0,
    })


def test_raw_and_adjusted_chart_use_one_consistent_anchor():
    frame = _frame()
    raw = build_chart_points(frame, cutoff=date(2026, 4, 1), days=5, price_basis="RAW", fields=("ohlc", "ma"))
    adjusted = build_chart_points(frame, cutoff=date(2026, 4, 1), days=5, price_basis="ADJUSTED", fields=("ohlc", "ma"))
    assert raw["chart_basis"] == "RAW_UNADJUSTED"
    assert adjusted["chart_basis"] == "TDX_NATIVE_QFQ@2026-04-01"
    assert raw["points"][-1]["close"] * 2 == pytest.approx(adjusted["points"][-1]["close"])
    assert raw["points"][-1]["ma5"] * 2 == pytest.approx(adjusted["points"][-1]["ma5"])


def test_missing_master_session_is_explicit_gap_and_breaks_ma():
    frame = _frame()
    missing_date = frame.iloc[-2]["date"].date()
    frame = frame[frame["date"].dt.date != missing_date]
    expected = list(pd.date_range("2026-03-25", "2026-04-01", freq="B").date)
    result = build_chart_points(frame, cutoff=date(2026, 4, 1), days=5, fields=("ohlc", "ma"), expected_dates=expected)
    gap = next(point for point in result["points"] if point["date"] == missing_date.isoformat())
    assert gap["gap"] is True
    assert gap["gap_reason"] == "NO_SECURITY_ROW"
    assert gap["close"] is None
    assert result["gaps"]


def test_chart_rejects_future_input_and_cache_key_separates_basis_and_fields():
    with pytest.raises(ValueError, match="FUTURE_CHART_INPUT"):
        build_chart_points(_frame(), cutoff=date(2026, 3, 1))
    raw_key = chart_cache_key("snapshot", "SH.600000", "RAW", None, 20, ("ohlc",))
    adjusted_key = chart_cache_key("snapshot", "SH.600000", "ADJUSTED", "2026-04-01", 20, ("ohlc",))
    assert raw_key != adjusted_key
    cache = ChartCache(max_entries=1)
    cache.put(raw_key, {"value": 1})
    assert cache.get(raw_key) == {"value": 1}
    cache.put(adjusted_key, {"value": 2})
    assert cache.get(raw_key) is None
    assert cache.get(adjusted_key) == {"value": 2}
