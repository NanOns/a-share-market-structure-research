"""Bind materialized stock paths to exact episode anchor requests."""
from __future__ import annotations

from collections.abc import Sequence
from datetime import date

from .materialize import PathRequest, StockFact


CONTRACT_ID = "FOCUS_PATH_FACT_INDEX_V1"


def index_stock_path_facts(*, requests: Sequence[PathRequest],
                           facts: Sequence[StockFact]) -> dict[tuple[str, date], StockFact]:
    expected = {(item.security_id, item.start_trade_date) for item in requests}
    if len(expected) != len(requests):
        raise ValueError("duplicate Focus PathRequest")
    actual: dict[tuple[str, date], StockFact] = {}
    for fact in facts:
        key = (fact.security_id, fact.start_trade_date)
        if key in actual:
            raise ValueError("duplicate Focus stock path fact")
        actual[key] = fact
    if set(actual) != expected:
        raise ValueError("Focus path fact set differs from PathRequest set")
    return actual
