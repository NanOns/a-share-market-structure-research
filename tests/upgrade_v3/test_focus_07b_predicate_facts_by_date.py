from datetime import date, timedelta

import pytest

from src.focus_tracker.materialize import VerifiedNormalizedSlice
from src.focus_tracker.predicate_facts_by_date import (
    build_predicate_facts_by_date, reanchor_frozen_price)
from src.focus_tracker.predicates import Tri, compile_v3_3_invalidation, evaluate


def normalized(*, missing=None, mixed=False):
    days = tuple(date(2026, 9, 1) + timedelta(days=i) for i in range(5))
    rows = {}
    for i, day in enumerate(days):
        rows[day] = {"raw_close": 10 + i, "has_actual_bar": day != missing,
                     "qfq_mul": 2 if i == 0 else 1, "qfq_add": 0,
                     "adjustment_version": "other" if mixed and i == 0 else "v1",
                     "adjustment_status": "VERIFIED_LOCAL"}
    return VerifiedNormalizedSlice("a" * 64, days, {"SH.1": rows}), days


def test_minimal_window_prices_ma_and_frozen_basis():
    source, days = normalized()
    facts, checksum = build_predicate_facts_by_date(
        normalized=source, security_id="SH.1", trade_date=days[-1],
        sessions=days, required_fields=frozenset({"has_actual_bar", "close", "dynamic_ma5"}))
    assert len(checksum) == 64
    assert facts[days[0]]["close"] == "20.00"
    assert facts[days[-1]]["dynamic_ma5"] == "14.00"
    assert reanchor_frozen_price(normalized=source, security_id="SH.1",
                                 signal_day=days[0], trade_date=days[-1], value="11") == "22.00"


def test_missing_actual_bar_never_forward_fills():
    source, days = normalized(missing=date(2026, 9, 3))
    facts, _ = build_predicate_facts_by_date(
        normalized=source, security_id="SH.1", trade_date=days[-1],
        sessions=days, required_fields=frozenset({"has_actual_bar", "close", "dynamic_ma5"}))
    assert facts[days[2]]["has_actual_bar"] is False
    assert facts[days[2]]["close"] is None
    assert facts[days[-1]]["dynamic_ma5"] is None


def test_gap_session_state_is_explicit_and_distinguishes_source_coverage():
    source, days = normalized(missing=date(2026, 9, 3))
    suspended_day = days[2]
    row = source.by_security["SH.1"][suspended_day]
    row["missing_state"] = "CONFIRMED_SUSPENSION"
    row["trade_status_known"] = True
    row["is_synthetic_fill"] = True
    source.by_security["SH.1"].pop(days[-1])
    facts, _ = build_predicate_facts_by_date(
        normalized=source, security_id="SH.1", trade_date=days[-1],
        sessions=[suspended_day, days[-1]],
        required_fields=frozenset({"has_actual_bar", "session_state"}))
    assert facts[suspended_day]["session_state"] == "SUSPENDED"
    assert facts[days[-1]]["session_state"] == "SOURCE_UNAVAILABLE"


def test_rps_history_is_unavailable_and_identity_mismatch_fails():
    source, days = normalized()
    facts, _ = build_predicate_facts_by_date(
        normalized=source, security_id="SH.1", trade_date=days[-1],
        sessions=days[-2:], required_fields=frozenset({"rps20_delta3"}))
    assert all(item["rps20_delta3"] is None for item in facts.values())
    mismatched, days = normalized(mixed=True)
    with pytest.raises(ValueError, match="identity mismatch"):
        build_predicate_facts_by_date(
            normalized=mismatched, security_id="SH.1", trade_date=days[-1],
            sessions=days, required_fields=frozenset({"close"}))


def test_pre_signal_day_cannot_satisfy_two_day_invalidation():
    source, days = normalized()
    facts, _ = build_predicate_facts_by_date(
        normalized=source, security_id="SH.1", trade_date=days[-1],
        sessions=days[-1:], required_fields=frozenset({"has_actual_bar", "close",
                                                       "structure_break_v3"}),
        structure_break_v3=False)
    result, evidence = evaluate(
        compile_v3_3_invalidation("LAUNCH_CONFIRM", {}),
        trade_date=days[-1], sessions=days[-1:], facts_by_date=facts,
        frozen_signal={"frozen_phh20": "15"}, frozen_episode={})
    assert result == Tri.UNKNOWN
    assert evidence["children"][1]["reason"] == "INSUFFICIENT_CALENDAR_SESSIONS"


def test_second_episode_day_uses_both_actual_bars():
    source, days = normalized()
    fields = frozenset({"has_actual_bar", "close", "structure_break_v3"})
    facts, _ = build_predicate_facts_by_date(
        normalized=source, security_id="SH.1", trade_date=days[-1],
        sessions=days[-2:], required_fields=fields, structure_break_v3=False)
    ast = compile_v3_3_invalidation("LAUNCH_CONFIRM", {})
    result, _ = evaluate(ast, trade_date=days[-1], sessions=days[-2:],
                         facts_by_date=facts, frozen_signal={"frozen_phh20": "15"},
                         frozen_episode={})
    assert result == Tri.TRUE
    missing, _ = normalized(missing=days[-2])
    gap_facts, _ = build_predicate_facts_by_date(
        normalized=missing, security_id="SH.1", trade_date=days[-1],
        sessions=days[-2:], required_fields=fields, structure_break_v3=False)
    gap_result, _ = evaluate(ast, trade_date=days[-1], sessions=days[-2:],
                             facts_by_date=gap_facts,
                             frozen_signal={"frozen_phh20": "15"}, frozen_episode={})
    assert gap_result == Tri.UNKNOWN
