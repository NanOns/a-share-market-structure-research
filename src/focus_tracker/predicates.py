"""FOCUS_INVALIDATION_AST_V2 three-valued predicate evaluator."""
from __future__ import annotations

import math
from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Any, Mapping, Sequence

from .contracts import digest
from .session_gap_semantics import (CONTRACT_ID as SESSION_GAP_CONTRACT,
                                    SessionState, state_from_predicate_facts)


CONTRACT_ID = "FOCUS_INVALIDATION_AST_V2"


def compile_v3_3_invalidation(category: str, signal_facts: Mapping[str, Any]) -> dict[str, Any]:
    """Freeze the final V2.1 tracker thesis; absent anchors remain UNKNOWN.

    Price thresholds in the returned AST are identifiers. The fact materializer
    must reanchor their actual value to the observation day's price basis.
    """
    structure_break = {"op": "EQ", "field": "structure_break_v3",
                       "mode": "CURRENT_FIELD", "value": True}
    if category == "LAUNCH_CONFIRM":
        other = {"op": "CONSECUTIVE", "sessions": 2, "predicate":
                 {"op": "LT", "field": "close", "mode": "CURRENT_FIELD",
                  "anchor": "frozen_phh20", "anchor_mode": "FROZEN_SIGNAL_VALUE"}}
    elif category == "STRONG_PULLBACK":
        other = {"op": "LT", "field": "close", "mode": "CURRENT_FIELD",
                 "anchor": "frozen_pullback_invalid_low", "anchor_mode": "FROZEN_SIGNAL_VALUE"}
    elif category == "TREND_CONTINUE":
        other = {"op": "LT", "field": "close", "mode": "CURRENT_FIELD",
                 "anchor": "frozen_trend_key_low", "anchor_mode": "FROZEN_SIGNAL_VALUE"}
    elif category == "RECOVERY_TURN":
        recovered = signal_facts.get("reclaimed_ma_kind")
        # Bind the dynamic operand to the signal day's frozen MA identity.
        # A missing identity must remain UNKNOWN even if another MA is present.
        anchor = ({"MA5": "dynamic_ma5", "MA20": "dynamic_ma20"}.get(recovered)
                  if isinstance(recovered, str) else None)
        other = {"op": "AND", "args": [
            {"op": "CONSECUTIVE", "sessions": 2, "predicate":
                {"op": "LT", "field": "close", "mode": "CURRENT_FIELD",
                 "anchor": anchor or "unavailable_reclaimed_ma",
                 "anchor_mode": "DERIVED_DYNAMIC_FIELD"}},
            {"op": "LE", "field": "rps20_delta3", "mode": "DERIVED_DYNAMIC_FIELD", "value": 0},
        ], "reclaimed_ma_kind": recovered if anchor else "UNAVAILABLE_MA"}
        return other
    else:
        raise ValueError("unsupported V3.3 category")
    return {"op": "OR", "args": [structure_break, other]}


class Tri(str, Enum):
    TRUE = "TRUE"
    FALSE = "FALSE"
    UNKNOWN = "UNKNOWN"


def tri_and(values: Sequence[Tri]) -> Tri:
    if Tri.FALSE in values:
        return Tri.FALSE
    return Tri.UNKNOWN if Tri.UNKNOWN in values else Tri.TRUE


def tri_or(values: Sequence[Tri]) -> Tri:
    if Tri.TRUE in values:
        return Tri.TRUE
    return Tri.UNKNOWN if Tri.UNKNOWN in values else Tri.FALSE


def tri_not(value: Tri) -> Tri:
    return {Tri.TRUE: Tri.FALSE, Tri.FALSE: Tri.TRUE,
            Tri.UNKNOWN: Tri.UNKNOWN}[value]


def _number(value: Any) -> Decimal | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, float) and not math.isfinite(value):
        return None
    try:
        number = Decimal(str(value))
    except (ArithmeticError, ValueError):
        return None
    return number if number.is_finite() else None


def _compare(actual: Any, expected: Any, op: str) -> Tri:
    if actual is None or expected is None:
        return Tri.UNKNOWN
    if op == "EQ":
        return Tri.TRUE if type(actual) is type(expected) and actual == expected else Tri.FALSE
    left, right = _number(actual), _number(expected)
    if left is None or right is None:
        return Tri.UNKNOWN
    match = {"LT": left < right, "LE": left <= right,
             "GT": left > right, "GE": left >= right}.get(op)
    if match is None:
        raise ValueError("unsupported comparison")
    return Tri.TRUE if match else Tri.FALSE


def evaluate(ast: Mapping[str, Any], *, trade_date: date,
             sessions: Sequence[date], facts_by_date: Mapping[date, Mapping[str, Any]],
             frozen_signal: Mapping[str, Any], frozen_episode: Mapping[str, Any]) -> tuple[Tri, dict[str, Any]]:
    """Evaluate without skipping an absent market session.

    The caller supplies the frozen primary calendar prefix ending at
    ``trade_date``. `has_actual_bar` must be explicitly true for consecutive
    predicates; inferred gaps and synthetic fills are never actual bars.
    """
    if not sessions or sessions[-1] != trade_date or len(set(sessions)) != len(sessions):
        raise ValueError("invalid frozen calendar window")

    def visit(node: Mapping[str, Any], on_date: date) -> tuple[Tri, dict[str, Any]]:
        op = node.get("op")
        if op in {"AND", "OR"}:
            args = node.get("args")
            if not isinstance(args, list) or not args:
                raise ValueError("empty logical expression")
            children = [visit(child, on_date) for child in args]
            result = tri_and([x[0] for x in children]) if op == "AND" else tri_or([x[0] for x in children])
            return result, {"op": op, "result": result.value,
                            "children": [x[1] for x in children]}
        if op == "NOT":
            result, child = visit(node["arg"], on_date)
            inverse = tri_not(result)
            return inverse, {"op": op, "result": inverse.value, "child": child}
        if op == "CONSECUTIVE":
            count = node.get("sessions")
            if not isinstance(count, int) or isinstance(count, bool) or count < 1:
                raise ValueError("invalid consecutive session count")
            position = sessions.index(on_date)
            window = sessions[max(0, position - count + 1):position + 1]
            if len(window) != count:
                return Tri.UNKNOWN, {"op": op, "result": Tri.UNKNOWN.value,
                                     "reason": "INSUFFICIENT_CALENDAR_SESSIONS"}
            children = []
            for day in window:
                session_state = state_from_predicate_facts(facts_by_date.get(day, {}))
                if session_state != SessionState.ACTUAL_BAR:
                    children.append({"date": day.isoformat(), "result": Tri.UNKNOWN.value,
                                     "reason": session_state.value})
                else:
                    _, evidence = visit(node["predicate"], day)
                    children.append(evidence)
            # A missing actual bar makes the complete consecutive predicate U,
            # even if another day would make ordinary AND false.
            missing_states = {state.value for state in SessionState
                              if state != SessionState.ACTUAL_BAR}
            if any(child.get("reason") in missing_states for child in children):
                result = Tri.UNKNOWN
            else:
                result = tri_and([Tri(child["result"]) for child in children])
            return result, {"op": op, "result": result.value, "children": children}
        if op not in {"EQ", "LT", "LE", "GT", "GE"}:
            raise ValueError("unsupported focus AST operation")
        field = node.get("field")
        mode = node.get("mode")
        if not isinstance(field, str) or mode not in {
            "CURRENT_FIELD", "FROZEN_SIGNAL_VALUE", "FROZEN_EPISODE_VALUE",
            "DERIVED_DYNAMIC_FIELD",
        }:
            raise ValueError("invalid operand declaration")
        source = (facts_by_date.get(on_date, {}) if mode in
                  {"CURRENT_FIELD", "DERIVED_DYNAMIC_FIELD"} else
                  frozen_signal if mode == "FROZEN_SIGNAL_VALUE" else frozen_episode)
        actual = source.get(field)
        expected = node.get("value")
        if "anchor" in node:
            anchor = node["anchor"]
            anchor_mode = node.get("anchor_mode")
            if anchor_mode == "FROZEN_SIGNAL_VALUE":
                expected = frozen_signal.get(anchor)
            elif anchor_mode == "FROZEN_EPISODE_VALUE":
                expected = frozen_episode.get(anchor)
            elif anchor_mode == "DERIVED_DYNAMIC_FIELD":
                expected = facts_by_date.get(on_date, {}).get(anchor)
            else:
                raise ValueError("invalid anchor mode")
        result = _compare(actual, expected, op)
        return result, {"op": op, "field": field, "mode": mode,
                        "date": on_date.isoformat(), "actual": actual,
                        "expected": expected, "result": result.value,
                        "reason": "MISSING_OR_INVALID_OPERAND" if result == Tri.UNKNOWN else None}

    result, evidence = visit(ast, trade_date)
    evidence["contract_id"] = CONTRACT_ID
    evidence["session_gap_contract_id"] = SESSION_GAP_CONTRACT
    evidence["ast_digest"] = digest(dict(ast))
    return result, evidence
