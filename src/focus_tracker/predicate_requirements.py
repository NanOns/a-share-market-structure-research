"""Static, versioned lookback requirements for Focus invalidation ASTs."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


CONTRACT_ID = "FOCUS_PREDICATE_REQUIREMENTS_V2"
COMPARE = frozenset({"EQ", "LT", "LE", "GT", "GE"})
FACT_MODES = frozenset({"CURRENT_FIELD", "DERIVED_DYNAMIC_FIELD"})
FROZEN_MODES = frozenset({"FROZEN_SIGNAL_VALUE", "FROZEN_EPISODE_VALUE"})
# Source-history length for a value derived on one evaluation day. The next
# stage materializes these histories; keeping the requirement here prevents a
# one-day slice from being mistaken for complete predicate coverage.
DERIVED_FIELD_SESSIONS = {"rps20_delta3": 4, "dynamic_ma5": 5,
                          "dynamic_ma20": 20}


@dataclass(frozen=True)
class PredicateRequirements:
    required_sessions: int
    required_fields: frozenset[str]
    required_frozen_facts: frozenset[str]
    contract_id: str = CONTRACT_ID


def plan_predicate_requirements(ast: Mapping[str, Any]) -> PredicateRequirements:
    """Return minimum master-calendar window and all required operands.

    A consecutive expression nested inside another needs overlapping windows:
    N consecutive days of an M-day child require N + M - 1 sessions.
    """
    def visit(node: Mapping[str, Any]) -> tuple[int, set[str], set[str]]:
        if not isinstance(node, Mapping):
            raise ValueError("predicate node must be an object")
        op = node.get("op")
        if op in {"AND", "OR"}:
            args = node.get("args")
            if not isinstance(args, list) or not args:
                raise ValueError("empty logical predicate")
            children = [visit(child) for child in args]
            frozen = set().union(*(item[2] for item in children))
            if "reclaimed_ma_kind" in node:
                frozen.add("reclaimed_ma_kind")
            return (max(item[0] for item in children),
                    set().union(*(item[1] for item in children)), frozen)
        if op == "NOT":
            return visit(node.get("arg"))
        if op == "CONSECUTIVE":
            count = node.get("sessions")
            if not isinstance(count, int) or isinstance(count, bool) or count < 1:
                raise ValueError("invalid consecutive session count")
            span, fields, frozen = visit(node.get("predicate"))
            fields.add("has_actual_bar")
            fields.add("session_state")
            return count + span - 1, fields, frozen
        if op not in COMPARE:
            raise ValueError("unsupported predicate operation")
        field, mode = node.get("field"), node.get("mode")
        if not isinstance(field, str) or not field:
            raise ValueError("predicate field missing")
        if mode not in FACT_MODES | FROZEN_MODES:
            raise ValueError("unsupported predicate field mode")
        fields = {field} if mode in FACT_MODES else set()
        frozen = {field} if mode in FROZEN_MODES else set()
        if "anchor" in node:
            anchor, anchor_mode = node["anchor"], node.get("anchor_mode")
            if not isinstance(anchor, str) or not anchor:
                raise ValueError("predicate anchor missing")
            if anchor_mode == "DERIVED_DYNAMIC_FIELD":
                fields.add(anchor)
            elif anchor_mode in FROZEN_MODES:
                frozen.add(anchor)
            else:
                raise ValueError("unsupported predicate anchor mode")
        return max((DERIVED_FIELD_SESSIONS.get(name, 1) for name in fields), default=1), fields, frozen

    span, fields, frozen = visit(ast)
    return PredicateRequirements(span, frozenset(fields), frozenset(frozen))
