from datetime import date

from src.focus_tracker.predicates import Tri, compile_v3_3_invalidation, evaluate


D1 = date(2026, 9, 21)
D2 = date(2026, 9, 22)


def _result(kind, facts):
    ast = compile_v3_3_invalidation("RECOVERY_TURN", {"reclaimed_ma_kind": kind})
    return evaluate(ast, trade_date=D2, sessions=[D1, D2],
                    facts_by_date=facts, frozen_signal={}, frozen_episode={})[0], ast


def test_recovery_uses_the_signal_day_frozen_ma_kind():
    facts = {
        D1: {"has_actual_bar": True, "close": 9, "dynamic_ma5": 10, "dynamic_ma20": 8},
        D2: {"has_actual_bar": True, "close": 9, "dynamic_ma5": 10,
             "dynamic_ma20": 8, "rps20_delta3": -1},
    }
    ma5, ast5 = _result("MA5", facts)
    ma20, ast20 = _result("MA20", facts)
    assert ma5 == Tri.TRUE
    assert ma20 == Tri.FALSE
    assert ast5["args"][0]["predicate"]["anchor"] == "dynamic_ma5"
    assert ast20["args"][0]["predicate"]["anchor"] == "dynamic_ma20"


def test_recovery_missing_frozen_ma_kind_fails_closed():
    facts = {
        D1: {"has_actual_bar": True, "close": 9, "dynamic_ma5": 10, "dynamic_ma20": 10},
        D2: {"has_actual_bar": True, "close": 9, "dynamic_ma5": 10,
             "dynamic_ma20": 10, "rps20_delta3": -1},
    }
    result, ast = _result(None, facts)
    assert result == Tri.UNKNOWN
    assert ast["reclaimed_ma_kind"] == "UNAVAILABLE_MA"
