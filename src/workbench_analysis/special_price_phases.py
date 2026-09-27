from __future__ import annotations

"""Contract-driven special price phase event store and runtime dispatcher."""

import json
from dataclasses import dataclass
from decimal import Decimal, ROUND_CEILING, ROUND_DOWN, ROUND_HALF_DOWN, ROUND_HALF_EVEN, ROUND_HALF_UP, ROUND_UP
from enum import Enum
from pathlib import Path
from typing import Iterable, Mapping


class SpecialPricePhase(str, Enum):
    REGULAR = "REGULAR"
    IPO_FIRST_5_TRADING_DAYS = "IPO_FIRST_5_TRADING_DAYS"
    DELISTING_FIRST_DAY = "DELISTING_FIRST_DAY"
    DELISTING_PERIOD = "DELISTING_PERIOD"
    RELISTING_FIRST_DAY = "RELISTING_FIRST_DAY"
    SPECIAL_REFERENCE_RESET = "SPECIAL_REFERENCE_RESET"
    UNKNOWN_SPECIAL_PHASE = "UNKNOWN_SPECIAL_PHASE"


@dataclass(frozen=True)
class SpecialPhaseEvent:
    event_id: str
    security_id: str
    trade_date: str
    phase: SpecialPricePhase
    phase_effective_from: str
    phase_effective_to: str | None
    exchange: str
    board_scope: str
    event_type: str
    source_ref: str
    source_capture_path: str
    source_capture_sha256: str
    observed_at: str
    system_available_at: str
    official_reference_price: str | None = None
    official_reference_formula: Mapping[str, object] | None = None
    quality: str = ""
    contract_id: str = ""
    revision: int = 0
    source_security_key: str = ""

    @classmethod
    def from_mapping(cls, row: Mapping[str, object]) -> "SpecialPhaseEvent":
        phase = SpecialPricePhase(str(row.get("phase") or ""))
        event = cls(
            event_id=str(row.get("event_id") or ""), security_id=str(row.get("security_id") or ""),
            trade_date=_iso(row.get("trade_date")), phase=phase,
            phase_effective_from=_iso(row.get("phase_effective_from", row.get("effective_date"))),
            phase_effective_to=_iso_nullable(row.get("phase_effective_to")),
            exchange=str(row.get("exchange") or ""), board_scope=str(row.get("board_scope", row.get("board")) or ""),
            event_type=str(row.get("event_type") or ""), source_ref=str(row.get("source_ref") or ""),
            source_capture_path=str(row.get("source_capture_path") or ""),
            source_capture_sha256=str(row.get("source_capture_sha256") or ""),
            observed_at=str(row.get("observed_at") or ""),
            system_available_at=str(row.get("system_available_at") or row.get("observed_at") or ""),
            official_reference_price=(str(row["official_reference_price"]) if row.get("official_reference_price") is not None else None),
            official_reference_formula=(row.get("official_reference_formula") if isinstance(row.get("official_reference_formula"), Mapping) else None),
            quality=str(row.get("quality") or ""), contract_id=str(row.get("contract_id") or ""),
            revision=int(row.get("revision") or 1), source_security_key=str(row.get("source_security_key") or ""),
        )
        if not all((event.event_id, event.security_id, event.trade_date, event.phase_effective_from,
                    event.exchange, event.board_scope, event.event_type, event.source_ref,
                    event.source_capture_path, event.observed_at, event.system_available_at,
                    event.quality, event.contract_id)):
            raise ValueError("SPECIAL_PHASE_EVENT_REQUIRED_FIELD_MISSING")
        if event.phase_effective_to and event.phase_effective_to < event.phase_effective_from:
            raise ValueError("SPECIAL_PHASE_EVENT_INTERVAL_INVALID")
        if len(event.source_capture_sha256) != 64 or any(c not in "0123456789abcdefABCDEF" for c in event.source_capture_sha256):
            raise ValueError("SPECIAL_PHASE_EVENT_CAPTURE_HASH_INVALID")
        if event.revision < 1:
            raise ValueError("SPECIAL_PHASE_EVENT_REVISION_INVALID")
        return event


def _iso(value: object) -> str:
    text = str(value or "").strip().replace("/", "-")
    if len(text) == 8 and text.isdigit():
        text = f"{text[:4]}-{text[4:6]}-{text[6:]}"
    if len(text) != 10 or text[4] != "-" or text[7] != "-":
        raise ValueError("SPECIAL_PHASE_DATE_INVALID")
    return text


def _iso_nullable(value: object) -> str | None:
    return None if value is None or str(value).strip() == "" else _iso(value)


class SpecialPhaseEventStore:
    def __init__(self, events: Iterable[SpecialPhaseEvent | Mapping[str, object]]):
        self.events = tuple(x if isinstance(x, SpecialPhaseEvent) else SpecialPhaseEvent.from_mapping(x) for x in events)
        event_ids = [x.event_id for x in self.events]
        if len(event_ids) != len(set(event_ids)):
            raise ValueError("SPECIAL_PHASE_EVENT_ID_DUPLICATE")

    @classmethod
    def from_jsonl(cls, path: str | Path) -> "SpecialPhaseEventStore":
        with Path(path).open("r", encoding="utf-8") as stream:
            return cls(json.loads(line) for line in stream if line.strip())

    def for_security(self, security_id: str) -> tuple[SpecialPhaseEvent, ...]:
        return tuple(x for x in self.events if x.security_id == security_id)


class PhasePolicyRegistry:
    def __init__(self, contract: Mapping[str, object]):
        self.contract = dict(contract)
        self.policies = tuple(contract.get("policies", ()))
        if not self.policies:
            raise ValueError("SPECIAL_PHASE_POLICIES_EMPTY")
        self.formula_contract = dict(contract.get("formula_contract", {}))

    @classmethod
    def from_json(cls, path: str | Path) -> "PhasePolicyRegistry":
        return cls(json.loads(Path(path).read_text(encoding="utf-8")))

    def policy_for(self, phase: SpecialPricePhase | str, trade_date: str, board_scope: str | None = None) -> Mapping[str, object] | None:
        name = phase.value if isinstance(phase, SpecialPricePhase) else str(phase)
        day = _iso(trade_date)
        rows = [p for p in self.policies if p.get("phase") == name and str(p.get("valid_from", "0001-01-01")) <= day
                and (p.get("valid_to") is None or day <= str(p["valid_to"]))
                and (p.get("board_scope") is None or p.get("board_scope") == board_scope)]
        if len(rows) > 1:
            raise ValueError("SPECIAL_PHASE_POLICY_AMBIGUOUS")
        return rows[0] if rows else None

    def delisting_sessions(self, trade_date: str, board_scope: str) -> int:
        policy = self.policy_for(SpecialPricePhase.DELISTING_PERIOD, trade_date, board_scope)
        if policy is None:
            # Period length is an effective-dated phase parameter. Board policy
            # rows carry the same duration to keep policy selection auditable.
            candidates = [p for p in self.policies if p.get("phase") == SpecialPricePhase.DELISTING_PERIOD.value
                          and p.get("valid_from", "0001-01-01") <= _iso(trade_date)
                          and (p.get("valid_to") is None or _iso(trade_date) <= str(p["valid_to"]))]
            if not candidates:
                raise ValueError("DELISTING_PERIOD_POLICY_UNAVAILABLE")
            policy = candidates[0]
        return int(policy["trading_sessions_including_first_day"])


def resolve_event_phase(store: SpecialPhaseEventStore, security_id: str, trade_date: str,
                        sessions: Iterable[str], policies: PhasePolicyRegistry,
                        board_scope: str | None = None) -> tuple[SpecialPricePhase, SpecialPhaseEvent | None]:
    day = _iso(trade_date)
    session_days = [_iso(x) for x in sessions]
    if day not in session_days:
        return SpecialPricePhase.UNKNOWN_SPECIAL_PHASE, None
    index = session_days.index(day)
    candidates: list[tuple[int, int, SpecialPricePhase, SpecialPhaseEvent]] = []
    for event in store.for_security(security_id):
        start = _iso(event.phase_effective_from)
        if event.phase == SpecialPricePhase.DELISTING_FIRST_DAY:
            if start not in session_days:
                continue
            offset = index - session_days.index(start)
            duration = policies.delisting_sessions(day, board_scope or event.board_scope)
            if offset == 0:
                candidates.append((session_days.index(start), event.revision, event.phase, event))
            elif 0 < offset < duration:
                candidates.append((session_days.index(start), event.revision, SpecialPricePhase.DELISTING_PERIOD, event))
            continue
        if event.phase == SpecialPricePhase.IPO_FIRST_5_TRADING_DAYS and event.phase_effective_to is None:
            if start not in session_days:
                continue
            offset = index - session_days.index(start)
            policy = policies.policy_for(event.phase, day, board_scope or event.board_scope)
            duration = int((policy or {}).get("trading_sessions_including_first_day", 0))
            if 0 <= offset < duration:
                candidates.append((session_days.index(start), event.revision, event.phase, event))
            continue
        end = _iso(event.phase_effective_to) if event.phase_effective_to else start
        if start <= day <= end:
            candidates.append((session_days.index(start) if start in session_days else index, event.revision, event.phase, event))
    if not candidates:
        return SpecialPricePhase.REGULAR, None
    candidates.sort(key=lambda x: (x[0], x[1]), reverse=True)
    if len(candidates) > 1 and candidates[0][:2] == candidates[1][:2] and candidates[0][2] != candidates[1][2]:
        return SpecialPricePhase.UNKNOWN_SPECIAL_PHASE, None
    return candidates[0][2], candidates[0][3]


_ROUNDING = {"HALF_UP": ROUND_HALF_UP, "HALF_DOWN": ROUND_HALF_DOWN, "HALF_EVEN": ROUND_HALF_EVEN,
             "DOWN": ROUND_DOWN, "UP": ROUND_UP, "CEILING": ROUND_CEILING}


def evaluate_decimal_formula(formula: Mapping[str, object], contract: Mapping[str, object] | None = None) -> Decimal:
    limits = dict(contract or {})
    max_depth = int(limits.get("maximum_depth", 32))
    max_nodes = int(limits.get("maximum_nodes", 128))
    count = 0

    def visit(node: object, depth: int) -> Decimal:
        nonlocal count
        count += 1
        if count > max_nodes or depth > max_depth or not isinstance(node, Mapping):
            raise ValueError("SPECIAL_REFERENCE_FORMULA_LIMIT_EXCEEDED")
        op = str(node.get("op") or "")
        if op == "CONST":
            return Decimal(str(node["value"]))
        if op not in {"ADD", "SUB", "MUL", "DIV"}:
            raise ValueError("SPECIAL_REFERENCE_FORMULA_OPERATOR_INVALID")
        left, right = visit(node.get("left"), depth + 1), visit(node.get("right"), depth + 1)
        if op == "ADD": return left + right
        if op == "SUB": return left - right
        if op == "MUL": return left * right
        if right == 0: raise ValueError("SPECIAL_REFERENCE_FORMULA_DIVIDE_BY_ZERO")
        return left / right

    return visit(formula, 0)


def official_reference(event: SpecialPhaseEvent | None, formula_contract: Mapping[str, object] | None = None) -> Decimal | None:
    if event is None:
        return None
    try:
        if event.official_reference_price is not None:
            value = Decimal(event.official_reference_price)
        elif event.official_reference_formula:
            value = evaluate_decimal_formula(event.official_reference_formula, formula_contract)
        else:
            return None
        return value if value > 0 else None
    except (ArithmeticError, KeyError, TypeError, ValueError):
        return None


def special_limit_prices(reference: str | Decimal, policy: Mapping[str, object]) -> tuple[Decimal, Decimal]:
    price, ratio, tick = Decimal(str(reference)), Decimal(str(policy["limit_ratio"])), Decimal(str(policy["tick"]))
    mode = _ROUNDING.get(str(policy.get("rounding_mode") or ""))
    if price <= 0 or ratio <= 0 or ratio >= 1 or tick <= 0 or mode is None:
        raise ValueError("SPECIAL_LIMIT_POLICY_INVALID")
    places = max(0, -tick.as_tuple().exponent)

    def round_price(value: Decimal) -> Decimal:
        return (value / tick).quantize(Decimal("1"), rounding=mode) * tick

    up, down = round_price(price * (Decimal(1) + ratio)), round_price(price * (Decimal(1) - ratio))
    min_move = tick * int(policy.get("minimum_price_movement_ticks", 1))
    up = max(up, price + min_move)
    down = min(down, price - min_move)
    quant = Decimal(1).scaleb(-places)
    up, down = up.quantize(quant), down.quantize(quant)
    if down <= 0 or up <= down:
        raise ValueError("SPECIAL_LIMIT_PRICE_RANGE_INVALID")
    return up, down


def apply_phase_event(row: Mapping[str, object], phase: SpecialPricePhase, event: SpecialPhaseEvent | None,
                      policies: PhasePolicyRegistry, *, close: str | Decimal | None = None,
                      regular_rule: Mapping[str, object] | None = None) -> dict:
    result = dict(row)
    day, board = _iso(result.get("trade_date")), str(result.get("board_scope") or (event.board_scope if event else ""))
    policy = policies.policy_for(phase, day, board)
    result["special_price_phase"] = phase.value
    if event is not None:
        result.update(special_phase_source_ref=event.source_ref,
                      special_phase_source_capture_sha256=event.source_capture_sha256,
                      special_phase_effective_date=event.phase_effective_from,
                      special_phase_observed_at=event.observed_at)
    if phase in {SpecialPricePhase.DELISTING_FIRST_DAY, SpecialPricePhase.RELISTING_FIRST_DAY, SpecialPricePhase.IPO_FIRST_5_TRADING_DAYS}:
        result.update(limit_status="NO_LIMIT", reason=f"{phase.value}_NO_LIMIT", reference_basis="OFFICIAL_SPECIAL_PHASE",
                      limit_up_price=None, limit_down_price=None, rule_id=(policy or {}).get("policy_id"))
        return result
    if phase == SpecialPricePhase.UNKNOWN_SPECIAL_PHASE:
        result.update(limit_status="UNKNOWN", reason=(policy or {}).get("reason", "SPECIAL_PHASE_EVIDENCE_UNAVAILABLE"),
                      limit_up_price=None, limit_down_price=None)
        return result
    if phase == SpecialPricePhase.REGULAR:
        return result
    if phase == SpecialPricePhase.DELISTING_PERIOD:
        if policy is None or policy.get("action") != "APPLY_LIMIT":
            result.update(limit_status="UNKNOWN", reason="DELISTING_PERIOD_POLICY_UNAVAILABLE", limit_up_price=None, limit_down_price=None)
            return result
        reference = result.get("reference_price")
        if reference is None or close is None:
            result.update(limit_status="UNKNOWN", reason="DELISTING_PERIOD_REFERENCE_UNAVAILABLE", limit_up_price=None,
                          limit_down_price=None, risk_status=policy.get("risk_status_override", "NORMAL"))
            return result
        up, down = special_limit_prices(str(reference), policy)
        last = Decimal(str(close))
        tick = Decimal(str(policy["tick"]))
        if last <= 0:
            result.update(limit_status="UNKNOWN", reason="CLOSE_NONPOSITIVE", limit_up_price=None, limit_down_price=None,
                          risk_status=policy.get("risk_status_override", "NORMAL"), rule_id=policy.get("rule_id"))
        elif (last / tick).quantize(Decimal("1"), rounding=ROUND_DOWN) * tick != last:
            result.update(limit_status="UNKNOWN", reason="CLOSE_TICK_INVALID", limit_up_price=None, limit_down_price=None,
                          risk_status=policy.get("risk_status_override", "NORMAL"), rule_id=policy.get("rule_id"))
        elif last > up or last < down:
            result.update(limit_status="UNKNOWN", reason="CLOSE_OUTSIDE_LIMIT_RANGE", limit_up_price=None, limit_down_price=None,
                          risk_status=policy.get("risk_status_override", "NORMAL"), rule_id=policy.get("rule_id"))
        else:
            state = "LIMIT_UP" if last == up else "LIMIT_DOWN" if last == down else "NOT_LIMIT"
            result.update(limit_status=state, reason=None, limit_up_price=str(up), limit_down_price=str(down),
                          risk_status=policy.get("risk_status_override", "NORMAL"), reference_basis="DELISTING_PERIOD_OFFICIAL_RULE",
                          rule_id=policy.get("rule_id"))
        return result
    if phase == SpecialPricePhase.SPECIAL_REFERENCE_RESET:
        reference = official_reference(event, policies.formula_contract)
        if reference is None:
            result.update(limit_status="UNKNOWN", reason=(policy or {}).get("missing_reference_reason", "SPECIAL_REFERENCE_PRICE_UNAVAILABLE"),
                          limit_up_price=None, limit_down_price=None)
            return result
        if policy is None or policy.get("action") != "USE_OFFICIAL_REFERENCE_WITH_STANDARD_BOARD_RULE" or regular_rule is None:
            result.update(limit_status="UNKNOWN", reason="SPECIAL_REFERENCE_LIMIT_POLICY_UNAVAILABLE", limit_up_price=None, limit_down_price=None)
            return result
        merged = dict(regular_rule)
        up, down = special_limit_prices(reference, merged)
        result.update(reference_price=str(reference), reference_basis="OFFICIAL_SPECIAL_REFERENCE", rule_id=merged.get("rule_id"))
        if close is None:
            result.update(limit_status="UNKNOWN", reason="SPECIAL_REFERENCE_CLOSE_UNAVAILABLE", limit_up_price=None, limit_down_price=None)
            return result
        last, tick = Decimal(str(close)), Decimal(str(merged["tick"]))
        if last <= 0:
            result.update(limit_status="UNKNOWN", reason="CLOSE_NONPOSITIVE", limit_up_price=None, limit_down_price=None)
        elif (last / tick).quantize(Decimal("1"), rounding=ROUND_DOWN) * tick != last:
            result.update(limit_status="UNKNOWN", reason="CLOSE_TICK_INVALID", limit_up_price=None, limit_down_price=None)
        elif last < down or last > up:
            result.update(limit_status="UNKNOWN", reason="CLOSE_OUTSIDE_LIMIT_RANGE", limit_up_price=None, limit_down_price=None)
        else:
            result.update(limit_status="LIMIT_UP" if last == up else "LIMIT_DOWN" if last == down else "NOT_LIMIT",
                          reason=None, limit_up_price=str(up), limit_down_price=str(down))
        return result
    result.update(limit_status="UNKNOWN", reason="SPECIAL_PHASE_EVIDENCE_UNAVAILABLE", limit_up_price=None, limit_down_price=None)
    return result
