from datetime import date, timedelta

import numpy as np
import pandas as pd
import pytest

from workbench_analysis.research_features import ResearchFeatureContext, ResearchFeatureError, build_stock_research_features


def sessions(count=110):
    out, cursor = [], date(2026, 1, 2)
    while len(out) < count:
        if cursor.weekday() < 5:
            out.append(cursor.isoformat())
        cursor += timedelta(days=1)
    return out


def context(days):
    return ResearchFeatureContext("run", "pub", "snapshot", "revision", "calendar", days[-1])


def raw(days, closes=None):
    closes = closes or [10 + index * .1 for index in range(len(days))]
    return pd.DataFrame({
        "security_id": "A", "trade_date": days, "adj_close": closes,
        "raw_close": closes, "raw_amount": 30_000_000.0,
        "has_actual_bar": True, "tradable": True, "data_observed": True,
        "is_synthetic_fill": False, "price_basis": "TDX_NATIVE_QFQ",
    })


def strength(days):
    return pd.DataFrame({"security_id": "A", "trade_date": days, "rps5": np.linspace(.2, .9, len(days)), "rps20": .8})


def test_manual_raw_windows_units_and_bound_identity():
    days = sessions()
    source = raw(days)
    row = build_stock_research_features(source, strength(days), days, context(days)).iloc[0]
    close = source.adj_close.astype(float)
    assert row.run_id == "run" and row.snapshot_id == "snapshot"
    assert row.bias20 == pytest.approx(close.iloc[-1] / close.iloc[-20:].mean() - 1)
    assert row.dist_high20 == pytest.approx(close.iloc[-1] / close.iloc[-21:-1].max() - 1)
    assert row.range5 == pytest.approx(close.iloc[-5:].max() / close.iloc[-5:].min() - 1)
    assert row.sigma20 == pytest.approx(np.log(close / close.shift()).iloc[-20:].std(ddof=0))
    assert row.amount_vs_prior20 == pytest.approx(1.0)
    assert bool(row.liquidity20) and bool(row.high100_input_complete)
    assert row.ret5 != row.rps5


def test_missing_calendar_day_does_not_compress_and_future_is_ignored():
    days = sessions()
    source = raw(days).loc[lambda value: value.trade_date.ne(days[-10])]
    future = (date.fromisoformat(days[-1]) + timedelta(days=1)).isoformat()
    source = pd.concat([source, raw([future], [9999.0])], ignore_index=True)
    row = build_stock_research_features(source, strength(days), days, context(days)).iloc[0]
    assert row.close != 9999.0
    assert pd.isna(row.ma20) and pd.isna(row.sigma20) and pd.isna(row.range20)
    assert not bool(row.high100_input_complete)


def test_suspension_zero_volatility_and_ex_right_use_fail_closed_or_adjusted_price():
    days = sessions()
    suspended = raw(days, [10.0] * len(days))
    suspended.loc[suspended.index[-1], "tradable"] = False
    row = build_stock_research_features(suspended, strength(days), days, context(days)).iloc[0]
    assert pd.isna(row.close) and pd.isna(row.extension_z20)
    adjusted = [10 + index * .02 for index in range(len(days))]
    ex_right = raw(days, adjusted)
    ex_right.loc[ex_right.index[-1], "raw_close"] = 5.0
    row = build_stock_research_features(ex_right, strength(days), days, context(days)).iloc[0]
    assert row.close == pytest.approx(adjusted[-1]) and row.dist_high20 > 0


def test_turnover_and_price_basis_fail_closed():
    days = sessions()
    source = raw(days)
    source["turnover"] = .03
    with pytest.raises(ResearchFeatureError, match="TURNOVER_BASIS_REQUIRED"):
        build_stock_research_features(source, strength(days), days, context(days))
    source["turnover_basis"] = "SOURCE"
    source.loc[source.index[-1], "price_basis"] = "RAW"
    row = build_stock_research_features(source, strength(days), days, context(days)).iloc[0]
    assert pd.isna(row.close) and "PRICE_BASIS_MISMATCH" in row.quality_codes


def test_context_duplicate_and_cutoff_guards():
    days = sessions()
    with pytest.raises(ResearchFeatureError, match="CONTEXT_ID_REQUIRED"):
        ResearchFeatureContext("", "pub", "snapshot", "revision", "calendar", days[-1])
    duplicated = pd.concat([raw(days), raw(days[-1:])])
    with pytest.raises(ResearchFeatureError, match="RAW_DUPLICATE_KEY"):
        build_stock_research_features(duplicated, strength(days), days, context(days))
