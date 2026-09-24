from datetime import date, timedelta

import pytest

from src.focus_tracker.history_window import required_history_start
from src.focus_tracker.materialize import PathRequest


CALENDAR = tuple(date(2026, 8, 3) + timedelta(days=day) for day in range(53))
TODAY = CALENDAR[-1]


def test_long_episode_start_is_not_truncated_to_fixed_days():
    start = CALENDAR[0]
    result = required_history_start(
        trade_date=TODAY, calendar=CALENDAR,
        stock_paths=[PathRequest("SH.600000", start)])
    assert result == start
    assert (TODAY - result).days > 14


def test_previous_session_is_kept_when_no_stock_path_exists():
    result = required_history_start(trade_date=TODAY, calendar=CALENDAR,
                                    stock_paths=[])
    assert result == CALENDAR[-2]


def test_required_lookback_can_extend_before_episode_start():
    result = required_history_start(
        trade_date=TODAY, calendar=CALENDAR,
        stock_paths=[PathRequest("SH.600000", TODAY)], previous_sessions=3)
    assert result == CALENDAR[-4]


def test_missing_anchor_or_previous_session_fails_closed():
    with pytest.raises(ValueError, match="anchor absent"):
        required_history_start(
            trade_date=TODAY, calendar=CALENDAR,
            stock_paths=[PathRequest("SH.600000", date(2026, 7, 1))])
    with pytest.raises(ValueError, match="insufficient previous"):
        required_history_start(trade_date=CALENDAR[0], calendar=CALENDAR,
                               stock_paths=[])
