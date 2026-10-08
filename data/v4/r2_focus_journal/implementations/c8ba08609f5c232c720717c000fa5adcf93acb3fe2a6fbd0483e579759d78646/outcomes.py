"""FOCUS_ANCHOR_OUTCOME_V2 fixed-date, sealed-input settlement states."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import re
from typing import Sequence

from .price_path import due_date


CONTRACT_ID = "FOCUS_ANCHOR_OUTCOME_V2"
TERMINAL = frozenset({"OBSERVED", "DATA_GAP", "SUSPENDED", "DELISTED"})


@dataclass(frozen=True)
class OutcomeDecision:
    status: str
    target_trade_date: date | None
    terminal: bool
    reason_code: str


def classify_outcome(*, calendar: Sequence[date], anchor_date: date,
                     horizon: int, as_of_date: date,
                     target_input_accepted: bool,
                     target_input_sealed: bool,
                     anchor_actual_bar: bool,
                     target_data_state: str | None,
                     audited_suspension: bool = False,
                     audited_delisting: bool = False,
                     gap_audit_digest: str | None = None,
                     path_complete: bool = False,
                     source_revised: bool = False) -> OutcomeDecision:
    target = due_date(calendar, anchor_date, horizon)
    if source_revised:
        return OutcomeDecision("SOURCE_REVISED", target, False, "TARGET_REPLAN_REQUIRED")
    if target is None or as_of_date < target:
        return OutcomeDecision("PENDING", target, False, "NOT_DUE")
    if not target_input_accepted or not target_input_sealed:
        return OutcomeDecision("PENDING", target, False, "TARGET_INPUT_UNSEALED")
    if audited_delisting:
        return OutcomeDecision("DELISTED", target, True, "AUDITED_DELISTING")
    if audited_suspension:
        return OutcomeDecision("SUSPENDED", target, True, "AUDITED_TARGET_SUSPENSION")
    if target_data_state == "BAR" and anchor_actual_bar and path_complete:
        return OutcomeDecision("OBSERVED", target, True, "COMPLETE_ACTUAL_PATH")
    if gap_audit_digest and re.fullmatch(r"[0-9a-f]{64}", gap_audit_digest):
        if target_data_state == "BAR" and not path_complete:
            return OutcomeDecision("DATA_GAP", target, True,
                                   "AUDITED_INTERMEDIATE_PATH_GAP")
        if target_data_state != "BAR" or not anchor_actual_bar:
            return OutcomeDecision("DATA_GAP", target, True,
                                   "AUDITED_NON_OBSERVABLE_TARGET")
    return OutcomeDecision("PENDING", target, False, "TARGET_STATUS_UNRESOLVED")


def followup_complete(*, source_membership_exited: bool,
                      outcome_statuses: Sequence[str],
                      pending_revision: bool, unaudited_gap: bool) -> bool:
    return (source_membership_exited and bool(outcome_statuses)
            and all(status in TERMINAL for status in outcome_statuses)
            and not pending_revision and not unaudited_gap)
