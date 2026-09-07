from __future__ import annotations

from market_calendar.trading_calendar import StockTimeline, classify_missing_state


def recent_window_evidence(timeline: StockTimeline, sessions: list[int]) -> dict:
    statuses = [classify_missing_state(timeline, session) for session in sessions]
    valid = statuses.count("BAR")
    total = len(sessions)
    return {
        "recent_valid_bar_count": valid,
        "recent_missing_bar_count": total - valid,
        "recent_trading_coverage_ratio": valid / total if total else 0.0,
        "status_distribution": {status: statuses.count(status) for status in sorted(set(statuses))},
    }


def qualifies_normal_universe(
    timeline: StockTimeline,
    sessions: list[int],
    *,
    min_history_days: int = 120,
    min_recent_coverage_ratio: float = 0.75,
    require_latest_bar: bool = True,
) -> tuple[bool, dict]:
    evidence = recent_window_evidence(timeline, sessions)
    latest_has_bar = bool(sessions) and sessions[-1] in timeline.recent_dates
    qualifies = (
        timeline.current_member
        and timeline.file_exists
        and timeline.structurally_valid
        and timeline.record_count >= min_history_days
        and evidence["recent_trading_coverage_ratio"] >= min_recent_coverage_ratio
        and (latest_has_bar or not require_latest_bar)
    )
    return qualifies, {**evidence, "latest_has_bar": latest_has_bar}

