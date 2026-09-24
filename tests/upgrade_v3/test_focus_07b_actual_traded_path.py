from datetime import date, timedelta
from decimal import Decimal

from src.focus_tracker.materialize import (PathRequest, VerifiedNormalizedSlice,
                                           stock_paths_from_slice)
from src.focus_tracker.outcome_math import stock_outcome_path
from src.focus_tracker.predicate_facts_by_date import build_predicate_facts_by_date
from src.focus_tracker.predicates import Tri, compile_v3_3_invalidation, evaluate
from src.focus_tracker.price_path import reanchor_actual_traded_path


def slice_with_gap(state="CONFIRMED_SUSPENSION", *, gap_day=1):
    days = tuple(date(2026, 9, 21) + timedelta(days=i) for i in range(4))
    rows = {}
    for i, day in enumerate(days):
        actual = i != gap_day
        price = 10 + i
        rows[day] = {"has_actual_bar": actual,
                     "missing_state": "BAR" if actual else state,
                     "raw_open": price, "raw_high": price + 1,
                     "raw_low": price - 1, "raw_close": price,
                     "qfq_mul": 1, "qfq_add": 0,
                     "adjustment_status": "VERIFIED_LOCAL",
                     "adjustment_version": "local-v1",
                     "trade_status_known": not actual and state == "CONFIRMED_SUSPENSION",
                     "is_synthetic_fill": not actual and state == "CONFIRMED_SUSPENSION"}
    return VerifiedNormalizedSlice("a" * 64, days, {"SH.1": rows}), days


def test_resumed_stock_path_uses_traded_bars_and_records_suspension():
    normalized, days = slice_with_gap()
    traded = reanchor_actual_traded_path(sessions=days,
                                         rows=normalized.by_security["SH.1"])
    assert traded.actual_sessions == (days[0], days[2], days[3])
    assert traded.suspended_sessions == (days[1],)
    assert traded.gap_count == 1 and traded.bars is not None
    fact = stock_paths_from_slice(
        normalized=normalized, trade_date=days[-1],
        requests=[PathRequest("SH.1", days[0])])[0]
    assert fact.quality_status == "READY"
    assert fact.return_since_start == "0.3"
    assert (fact.mfe, fact.mae, fact.drawdown_current, fact.mdd_close) == (
        "0.4", "-0.1", "0", "0")
    assert (fact.gap_count, fact.suspended_sessions, fact.unverified_gap_count) == (1, 1, 0)
    assert fact.suspended_dates == (days[1],)
    outcome = stock_outcome_path(normalized=normalized, security_id="SH.1",
                                 calendar=days, anchor_date=days[0], horizon=3)
    assert outcome.path_complete and outcome.forward_return == Decimal("0.3")
    assert (outcome.mfe, outcome.mae, outcome.mdd) == (
        Decimal("0.4"), Decimal("-0.1"), Decimal("0"))
    assert outcome.coverage == Decimal("0.75")
    assert outcome.suspended_sessions == 1
    assert outcome.suspended_dates == (days[1],)


def test_unverified_gap_stays_unavailable_after_trading_resumes():
    normalized, days = slice_with_gap("MISSING_DATA")
    fact = stock_paths_from_slice(
        normalized=normalized, trade_date=days[-1],
        requests=[PathRequest("SH.1", days[0])])[0]
    assert fact.quality_status == "DATA_UNAVAILABLE"
    assert (fact.gap_count, fact.unverified_gap_count) == (1, 1)
    assert fact.unverified_gap_dates == (days[1],)
    outcome = stock_outcome_path(normalized=normalized, security_id="SH.1",
                                 calendar=days, anchor_date=days[0], horizon=3)
    assert not outcome.path_complete and outcome.forward_return is None


def test_suspension_does_not_count_as_consecutive_predicate_day():
    normalized, days = slice_with_gap()
    normalized = VerifiedNormalizedSlice(normalized.artifact_sha256, days[:3],
                                         normalized.by_security)
    facts, _ = build_predicate_facts_by_date(
        normalized=normalized, security_id="SH.1", trade_date=days[2],
        sessions=days[1:3],
        required_fields=frozenset({"has_actual_bar", "close", "structure_break_v3"}),
        structure_break_v3=False)
    result, _ = evaluate(compile_v3_3_invalidation("LAUNCH_CONFIRM", {}),
                         trade_date=days[2], sessions=days[1:3],
                         facts_by_date=facts,
                         frozen_signal={"frozen_phh20": "15"}, frozen_episode={})
    assert result == Tri.UNKNOWN


def test_anchor_or_target_suspension_cannot_make_ready_path():
    for gap_day in (0, 3):
        normalized, days = slice_with_gap(gap_day=gap_day)
        fact = stock_paths_from_slice(
            normalized=normalized, trade_date=days[-1],
            requests=[PathRequest("SH.1", days[0])])[0]
        assert fact.quality_status == "DATA_UNAVAILABLE"


def test_confirmed_suspension_requires_consistent_audited_status_flags():
    normalized, days = slice_with_gap()
    normalized.by_security["SH.1"][days[1]]["trade_status_known"] = False
    import pytest
    with pytest.raises(ValueError, match="status evidence inconsistent"):
        stock_paths_from_slice(normalized=normalized, trade_date=days[-1],
                               requests=[PathRequest("SH.1", days[0])])
