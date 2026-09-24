"""FOCUS_SESSION_GAP_SEMANTICS_V1: classify and apply missing-session evidence."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping, Sequence


CONTRACT_ID = "FOCUS_SESSION_GAP_SEMANTICS_V1"


class SessionState(str, Enum):
    ACTUAL_BAR = "ACTUAL_BAR"
    SUSPENDED = "SUSPENDED"
    DATA_GAP = "DATA_GAP"
    SOURCE_UNAVAILABLE = "SOURCE_UNAVAILABLE"


@dataclass(frozen=True)
class GapAssessment:
    operation: str
    usable: bool
    reason: str | None
    states: tuple[str, ...]
    suspended_positions: tuple[int, ...]
    unavailable_positions: tuple[int, ...]


def classify_session_state(row: Mapping[str, Any] | None, *,
                           source_available: bool = True) -> SessionState:
    """Map normalized row status to an explicit session state, fail-closed."""
    if not source_available:
        return SessionState.SOURCE_UNAVAILABLE
    if row is None:
        return SessionState.SOURCE_UNAVAILABLE
    missing = row.get("missing_state")
    actual = row.get("has_actual_bar") is True
    if missing == "CONFIRMED_SUSPENSION":
        if (actual or row.get("trade_status_known") is not True or
                row.get("is_synthetic_fill") is not True):
            raise ValueError("confirmed suspension status evidence inconsistent")
        return SessionState.SUSPENDED
    if actual:
        if missing not in (None, "BAR"):
            raise ValueError("actual bar conflicts with missing-state evidence")
        return SessionState.ACTUAL_BAR
    if missing in {"FILE_MISSING", "NOT_LISTED_YET", "DELISTED_OR_INACTIVE"}:
        return SessionState.SOURCE_UNAVAILABLE
    return SessionState.DATA_GAP


def assess_gap_sequence(*, operation: str,
                        states: Sequence[SessionState | str]) -> GapAssessment:
    """Apply session-gap policy for consecutive, rolling, or price-path use."""
    if operation not in {"CONSECUTIVE", "ROLLING", "PATH"}:
        raise ValueError("unsupported gap operation")
    normalized = tuple(SessionState(value).value for value in states)
    if not normalized:
        return GapAssessment(operation, False, "EMPTY_SESSION_WINDOW", (), (), ())
    suspended = tuple(i for i, value in enumerate(normalized)
                      if value == SessionState.SUSPENDED.value)
    unavailable = tuple(i for i, value in enumerate(normalized)
                        if value != SessionState.ACTUAL_BAR.value)
    if operation in {"CONSECUTIVE", "ROLLING"}:
        if unavailable:
            state = normalized[unavailable[0]]
            return GapAssessment(operation, False, state, normalized,
                                 suspended, unavailable)
        return GapAssessment(operation, True, None, normalized, (), ())
    if (normalized[0] != SessionState.ACTUAL_BAR.value or
            normalized[-1] != SessionState.ACTUAL_BAR.value):
        return GapAssessment(operation, False, "PATH_ENDPOINT_UNAVAILABLE",
                             normalized, suspended, unavailable)
    if any(value not in {SessionState.ACTUAL_BAR.value,
                         SessionState.SUSPENDED.value} for value in normalized):
        return GapAssessment(operation, False, "PATH_CONTAINS_UNVERIFIED_GAP",
                             normalized, suspended, unavailable)
    return GapAssessment(operation, True, None, normalized, suspended, ())


def state_from_predicate_facts(facts: Mapping[str, Any]) -> SessionState:
    """Read explicit evaluator state; retain safe compatibility with old fixtures."""
    state = facts.get("session_state")
    if state is not None:
        return SessionState(state)
    return (SessionState.ACTUAL_BAR if facts.get("has_actual_bar") is True
            else SessionState.DATA_GAP)
