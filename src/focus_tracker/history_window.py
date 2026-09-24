"""Choose the minimum verified slice range required by a Focus daily plan."""
from __future__ import annotations

from collections.abc import Sequence
from datetime import date

from .materialize import PathRequest


CONTRACT_ID = "FOCUS_HISTORY_WINDOW_V1"


def required_history_start(*, trade_date: date,
                           calendar: Sequence[date],
                           stock_paths: Sequence[PathRequest],
                           previous_sessions: int = 1) -> date:
    """Cover every episode anchor and required preceding master session."""
    if previous_sessions < 1:
        raise ValueError("Focus previous session requirement must be positive")
    if not calendar or tuple(calendar) != tuple(sorted(set(calendar))):
        raise ValueError("Focus master calendar must be strictly increasing")
    try:
        today_position = calendar.index(trade_date)
    except ValueError as exc:
        raise ValueError("Focus trade date absent from master calendar") from exc
    if today_position < previous_sessions:
        raise ValueError("insufficient previous master sessions")
    if any(request.start_trade_date > trade_date or
           request.start_trade_date not in calendar for request in stock_paths):
        raise ValueError("Focus PathRequest anchor absent from master calendar")
    return min([calendar[today_position - previous_sessions]] +
               [request.start_trade_date for request in stock_paths])
