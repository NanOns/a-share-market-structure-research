from market_calendar.trading_calendar import StockTimeline
from normalize.universe_recent import qualifies_normal_universe, recent_window_evidence


def test_recent_window_uses_master_sessions() -> None:
    sessions = [20260831, 20260901, 20260902, 20260903, 20260904]
    timeline = StockTimeline(
        "SZ.000001",
        20200101,
        20260904,
        1200,
        frozenset({20260831, 20260901, 20260903, 20260904}),
    )
    qualifies, evidence = qualifies_normal_universe(
        timeline, sessions, min_recent_coverage_ratio=0.75
    )
    assert qualifies
    assert evidence["recent_valid_bar_count"] == 4
    assert evidence["status_distribution"]["SUSPENDED"] == 1


def test_latest_missing_bar_excludes_current_scan() -> None:
    sessions = [20260903, 20260904]
    timeline = StockTimeline("SZ.000001", 20200101, 20260903, 1200, frozenset({20260903}))
    qualifies, evidence = qualifies_normal_universe(timeline, sessions, min_recent_coverage_ratio=0.5)
    assert not qualifies
    assert not evidence["latest_has_bar"]

