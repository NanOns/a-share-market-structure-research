from datetime import date

import pytest

from src.focus_tracker.materialize import PathRequest, StockFact
from src.focus_tracker.path_fact_index import index_stock_path_facts


TODAY = date(2026, 9, 24)
FIRST = date(2026, 9, 23)


def fact(start):
    return StockFact("SH.600000", TODAY, start, "READY", "BAR", "10.00",
                     "0", "0", "0", "0", "0", "v1", "a" * 64)


def test_continuing_episode_uses_original_start_key():
    request = PathRequest("SH.600000", FIRST)
    indexed = index_stock_path_facts(requests=[request], facts=[fact(FIRST)])
    assert indexed[("SH.600000", FIRST)].start_trade_date == FIRST
    assert ("SH.600000", TODAY) not in indexed


def test_multiple_anchors_for_same_security_stay_distinct():
    requests = [PathRequest("SH.600000", FIRST), PathRequest("SH.600000", TODAY)]
    indexed = index_stock_path_facts(requests=requests,
                                     facts=[fact(TODAY), fact(FIRST)])
    assert set(indexed) == {("SH.600000", FIRST), ("SH.600000", TODAY)}


def test_missing_or_duplicate_fact_fails_before_observation():
    request = PathRequest("SH.600000", FIRST)
    with pytest.raises(ValueError, match="differs"):
        index_stock_path_facts(requests=[request], facts=[fact(TODAY)])
    with pytest.raises(ValueError, match="duplicate Focus stock path fact"):
        index_stock_path_facts(requests=[request], facts=[fact(FIRST), fact(FIRST)])
