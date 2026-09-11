"""Versioned Decimal limit-state service for M8C-02.

No current legal rule values are bundled here.  Callers must supply the
audited, effective-dated local rule table.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_DOWN, ROUND_HALF_EVEN, ROUND_HALF_UP, ROUND_UP
import json
from typing import Any, Iterable, Mapping

import pandas as pd


CONTRACT_VERSION = "LIMIT_RULES_V1_1"
ROUNDING = {"DOWN": ROUND_DOWN, "UP": ROUND_UP, "HALF_UP": ROUND_HALF_UP, "HALF_EVEN": ROUND_HALF_EVEN}


class LimitRuleError(ValueError):
    pass


def _decimal(value: Any, field: str) -> Decimal:
    try:
        result = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise LimitRuleError(f"{field}_INVALID") from exc
    if not result.is_finite():
        raise LimitRuleError(f"{field}_INVALID")
    return result


def _day(value: Any, field: str = "date") -> date:
    try:
        return pd.Timestamp(value).date()
    except (TypeError, ValueError) as exc:
        raise LimitRuleError(f"{field}_INVALID") from exc


def _flag(value: Any, field: str) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        normalized = value.strip().upper()
        if normalized in {"TRUE", "1", "YES"}:
            return True
        if normalized in {"FALSE", "0", "NO", ""}:
            return False
        raise LimitRuleError(f"{field}_INVALID")
    try:
        return bool(value) if not pd.isna(value) else False
    except (TypeError, ValueError) as exc:
        raise LimitRuleError(f"{field}_INVALID") from exc


@dataclass(frozen=True)
class LimitRuleVersion:
    rule_id: str
    exchange: str
    board: str
    risk_status: str
    valid_from: date
    valid_to: date | None
    limit_ratio: Decimal | None
    tick: Decimal
    rounding_mode: str
    special_period_policy: Mapping[str, Any]
    source_ref: str
    rule_verified: bool = False
    source_sha256: str = ""
    audit_status: str = "PENDING_REVIEW"
    audit_reason: str = ""
    audited_at: Any = None

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "LimitRuleVersion":
        rule_id = str(value.get("rule_id") or "")
        source_ref = str(value.get("source_ref") or "")
        if not rule_id or not source_ref:
            raise LimitRuleError("RULE_ID_AND_SOURCE_REQUIRED")
        valid_from = _day(value.get("valid_from"), "valid_from")
        valid_to = _day(value["valid_to"], "valid_to") if value.get("valid_to") is not None else None
        if valid_to is not None and valid_to < valid_from:
            raise LimitRuleError("RULE_VALID_RANGE_INVALID")
        ratio = None if value.get("limit_ratio") is None else _decimal(value.get("limit_ratio"), "limit_ratio")
        if ratio is not None and not (Decimal("0") <= ratio < Decimal("1")):
            raise LimitRuleError("LIMIT_RATIO_INVALID")
        tick = _decimal(value.get("tick"), "tick")
        if tick <= 0:
            raise LimitRuleError("TICK_INVALID")
        rounding_mode = str(value.get("rounding_mode") or "").upper()
        if rounding_mode not in ROUNDING:
            raise LimitRuleError("ROUNDING_MODE_UNSUPPORTED")
        policy = value.get("special_period_policy") or {}
        if isinstance(policy, str):
            try:
                policy = json.loads(policy)
            except (TypeError, ValueError, json.JSONDecodeError) as exc:
                raise LimitRuleError("SPECIAL_PERIOD_POLICY_INVALID") from exc
        if not isinstance(policy, Mapping):
            raise LimitRuleError("SPECIAL_PERIOD_POLICY_INVALID")
        rule_verified = _flag(value.get("rule_verified"), "RULE_VERIFIED")
        source_sha256 = str(value.get("source_sha256") or "")
        if rule_verified and not source_sha256:
            raise LimitRuleError("VERIFIED_RULE_SOURCE_HASH_REQUIRED")
        audit_status = str(value.get("audit_status") or ("VERIFIED" if rule_verified else "PENDING_REVIEW")).upper()
        if audit_status not in {"VERIFIED", "PENDING_REVIEW", "REJECTED"}:
            raise LimitRuleError("AUDIT_STATUS_INVALID")
        return cls(rule_id, str(value.get("exchange") or ""), str(value.get("board") or ""), str(value.get("risk_status") or ""), valid_from, valid_to, ratio, tick, rounding_mode, dict(policy), source_ref, rule_verified, source_sha256, audit_status, str(value.get("audit_reason") or ""), value.get("audited_at"))


def validate_rule_versions(rules: Iterable[LimitRuleVersion | Mapping[str, Any]]) -> tuple[LimitRuleVersion, ...]:
    normalized = tuple(rule if isinstance(rule, LimitRuleVersion) else LimitRuleVersion.from_mapping(rule) for rule in rules)
    if len({rule.rule_id for rule in normalized}) != len(normalized):
        raise LimitRuleError("RULE_ID_DUPLICATE")
    for index, left in enumerate(normalized):
        for right in normalized[index + 1 :]:
            same_key = (left.exchange, left.board, left.risk_status) == (right.exchange, right.board, right.risk_status)
            left_end = left.valid_to or date.max
            right_end = right.valid_to or date.max
            if same_key and left.valid_from <= right_end and right.valid_from <= left_end:
                raise LimitRuleError("RULE_EFFECTIVE_RANGE_OVERLAP")
    return tuple(sorted(normalized, key=lambda rule: (rule.exchange, rule.board, rule.risk_status, rule.valid_from, rule.rule_id)))


def round_to_tick(value: Decimal, tick: Decimal, rounding_mode: str) -> Decimal:
    """Round a Decimal price to an explicit tick using the rule's mode."""
    if tick <= 0 or rounding_mode not in ROUNDING:
        raise LimitRuleError("ROUNDING_ARGUMENT_INVALID")
    units = (value / tick).quantize(Decimal("1"), rounding=ROUNDING[rounding_mode])
    return units * tick


def compute_limit_prices(previous_close: Any, rule: LimitRuleVersion) -> tuple[Decimal, Decimal]:
    previous = _decimal(previous_close, "quote_prev_close")
    if previous <= 0:
        raise LimitRuleError("QUOTE_PREV_CLOSE_NONPOSITIVE")
    if rule.limit_ratio is None:
        raise LimitRuleError("LIMIT_RULE_NOT_APPLICABLE")
    up = round_to_tick(previous * (Decimal("1") + rule.limit_ratio), rule.tick, rule.rounding_mode)
    down = round_to_tick(previous * (Decimal("1") - rule.limit_ratio), rule.tick, rule.rounding_mode)
    # The exchange rules require at least one minimum-price-unit movement when
    # the rounded boundary would collapse onto the previous close.
    if abs(up - previous) < rule.tick:
        up = previous + rule.tick
    if abs(previous - down) < rule.tick:
        down = previous - rule.tick
    if down <= 0 or up <= 0 or down >= up:
        raise LimitRuleError("LIMIT_PRICE_RANGE_INVALID")
    return up, down


class LimitStateService:
    """Resolve an effective rule and evaluate a close without tolerances."""

    def __init__(self, rules: Iterable[LimitRuleVersion | Mapping[str, Any]]):
        self.rules = validate_rule_versions(rules)

    def resolve(self, trade_date: Any, exchange: str, board: str, risk_status: str) -> LimitRuleVersion | None:
        day = _day(trade_date, "trade_date")
        matches = [rule for rule in self.rules if (rule.exchange, rule.board, rule.risk_status) == (str(exchange), str(board), str(risk_status)) and rule.valid_from <= day and (rule.valid_to is None or day <= rule.valid_to)]
        if len(matches) > 1:
            raise LimitRuleError("RULE_EFFECTIVE_RANGE_OVERLAP")
        return matches[0] if matches else None

    def evaluate(self, row: Mapping[str, Any]) -> dict[str, Any]:
        trade_date = _day(row.get("trade_date"), "trade_date")
        base = {"contract_id": CONTRACT_VERSION, "trade_date": trade_date, "security_id": row.get("security_id"), "reference_basis": "UNKNOWN", "rule_id": None, "rule_verified": False, "limit_up_price": None, "limit_down_price": None, "limit_state": "UNKNOWN", "streak_known": False, "reason": None}
        try:
            suspended = _flag(row.get("suspended"), "SUSPENDED")
        except LimitRuleError as exc:
            base["reason"] = str(exc)
            return base
        if suspended:
            base.update(reference_basis="SUSPENDED", limit_state="SUSPENDED", streak_known=True, reason="SUSPENDED")
            return base
        if str(row.get("reference_status") or "UNKNOWN").upper() != "KNOWN":
            base["reason"] = "REFERENCE_PRICE_UNKNOWN"
            return base
        try:
            rule = self.resolve(trade_date, row.get("exchange"), row.get("board"), row.get("risk_status"))
        except LimitRuleError as exc:
            base["reason"] = str(exc)
            return base
        if rule is None:
            base["reason"] = "RULE_NOT_FOUND"
            return base
        base["rule_id"] = rule.rule_id
        base["rule_verified"] = rule.rule_verified
        if not rule.rule_verified or rule.audit_status != "VERIFIED":
            base.update(reference_basis="RULE_VERSIONED", reason="RULE_NOT_VERIFIED")
            return base
        listing_phase = str(row.get("listing_phase") or "").strip().upper()
        if not listing_phase:
            listing_phase = "UNKNOWN"
        no_limit_phases = {
            str(value).strip().upper()
            for value in rule.special_period_policy.get("no_limit_listing_phases", ())
        }
        if listing_phase and listing_phase in no_limit_phases:
            base.update(reference_basis="RULE_VERSIONED", reason="NO_PRICE_LIMIT_SPECIAL_PERIOD")
            return base
        if listing_phase in {"UNKNOWN", "UNAVAILABLE"}:
            base.update(reference_basis="RULE_VERSIONED", reason="LISTING_PHASE_UNKNOWN")
            return base
        if rule.special_period_policy.get("limit_state") in {"NO_LIMIT", "UNKNOWN"} or rule.limit_ratio is None:
            base.update(reference_basis="RULE_VERSIONED", reason="NO_APPLICABLE_LIMIT_RULE")
            return base
        try:
            ex_rights_value = row.get("ex_rights_reference_unknown")
            if ex_rights_value is None or str(ex_rights_value).strip().upper() in {"", "UNKNOWN", "UNAVAILABLE"}:
                ex_rights_unknown = True
            else:
                ex_rights_unknown = _flag(ex_rights_value, "EX_RIGHTS_REFERENCE_UNKNOWN")
        except LimitRuleError as exc:
            base["reason"] = str(exc)
            return base
        if ex_rights_unknown:
            base.update(reference_basis="RULE_VERSIONED", reason="EX_RIGHTS_REFERENCE_UNKNOWN")
            return base
        try:
            up, down = compute_limit_prices(row.get("quote_prev_close"), rule)
            close = _decimal(row.get("close"), "close")
        except LimitRuleError as exc:
            base.update(reference_basis="RULE_VERSIONED", reason=str(exc))
            return base
        if close <= 0:
            base.update(reference_basis="RULE_VERSIONED", reason="CLOSE_NONPOSITIVE")
            return base
        if round_to_tick(close, rule.tick, "DOWN") != close:
            base.update(reference_basis="RULE_VERSIONED", reason="CLOSE_TICK_INVALID")
            return base
        if close < down or close > up:
            base.update(reference_basis="RULE_VERSIONED", reason="CLOSE_OUTSIDE_LIMIT_RANGE")
            return base
        state = "LIMIT_UP" if close == up else "LIMIT_DOWN" if close == down else "NOT_LIMIT"
        base.update(reference_basis="RULE_VERSIONED", limit_up_price=up, limit_down_price=down, limit_state=state, streak_known=True)
        return base

    def evaluate_many(self, rows: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
        return [self.evaluate(row) for row in rows]
