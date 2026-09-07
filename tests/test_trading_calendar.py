from __future__ import annotations

from collections import Counter

from market_calendar.trading_calendar import (
    StockTimeline,
    align_recent_bars,
    build_master_calendar,
    classify_missing_state,
)


def test_calendar_alignment_and_closed_weekend() -> None:
    rows = build_master_calendar(
        primary_index_dates={"SH.000001": {20260904}, "SZ.399001": {20260904}},
        a_stock_bar_counts=Counter({20260904: 100}),
        stock_intervals=[(20260904, 20260904)] * 100,
    )
    assert rows[0]["calendar_date"] == 20260904
    assert rows[0]["is_market_open"]
    assert rows[0]["index_confirmation_count"] == 2


def test_suspended_day_gets_explicit_synthetic_fill() -> None:
    timeline = StockTimeline("SH.600000", 20260901, 20260903, 2, frozenset({20260901, 20260903}))
    assert classify_missing_state(timeline, 20260902) == "SUSPENDED"
    rows = align_recent_bars(
        [20260901, 20260902, 20260903],
        {
            20260901: {"close": 10, "volume": 100, "amount": 1000},
            20260903: {"close": 11, "volume": 120, "amount": 1320},
        },
        timeline,
    )
    assert rows[1]["is_synthetic_fill"]
    assert not rows[1]["tradable"]
    assert rows[1]["aligned_close"] == 10
    assert rows[1]["aligned_return"] == 0


def test_missing_states_are_distinct() -> None:
    missing_file = StockTimeline("SH.600000", None, None, 0, frozenset(), file_exists=False)
    assert classify_missing_state(missing_file, 20260904) == "FILE_MISSING"
    current = StockTimeline("SH.600000", 20260901, 20260903, 2, frozenset({20260901, 20260903}))
    assert classify_missing_state(current, 20260801) == "NOT_LISTED_YET"
    assert classify_missing_state(current, 20260904) == "MISSING_DATA"
    inactive = StockTimeline(
        "SH.600000", 20260901, 20260903, 2, frozenset({20260901, 20260903}), current_member=False
    )
    assert classify_missing_state(inactive, 20260904) == "DELISTED_OR_INACTIVE"

