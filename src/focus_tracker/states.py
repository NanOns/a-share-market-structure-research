"""FOCUS_PATH_STATE_V1 deterministic, explainable path classification."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Mapping

from .predicates import Tri, tri_and, tri_or


CONTRACT_ID = "FOCUS_PATH_STATE_V1"
STOCK_PARAMETERS = {
    "PULLBACK_MIN": Decimal("0.03"),
    "PULLBACK_MAX": Decimal("0.12"),
    "SIDEWAYS_RANGE_MAX": Decimal("0.08"),
    "SECTOR_DIVERGENCE_MIN": Decimal("0.05"),
}
SECTOR_PARAMETERS = {
    "SECTOR_PULLBACK_MIN": Decimal("0.02"),
    "SECTOR_PULLBACK_MAX": Decimal("0.08"),
    "WIDTH_DROP_WARN": Decimal("0.15"),
    "RETENTION_WARN": Decimal("0.50"),
    "MEMBER_JACCARD_MIN": Decimal("0.90"),
    "COVERAGE_MIN": Decimal("0.80"),
}


@dataclass(frozen=True)
class PathDecision:
    current_path_state: str
    validity_state: str
    lifetime_path_tags: tuple[str, ...]
    secondary_tags: tuple[str, ...]
    evidence: dict[str, str]


def _decimal(value: Any) -> Decimal | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        number = Decimal(str(value))
    except (ValueError, ArithmeticError):
        return None
    return number if number.is_finite() else None


def _num(facts: Mapping[str, Any], key: str) -> Decimal | None:
    return _decimal(facts.get(key))


def _truth(value: Any) -> Tri:
    return Tri.TRUE if value is True else Tri.FALSE if value is False else Tri.UNKNOWN


def _validity(invalidation: Tri) -> str:
    return {Tri.TRUE: "INVALIDATED", Tri.FALSE: "VALID",
            Tri.UNKNOWN: "UNKNOWN"}[invalidation]


def _select(predicates: list[tuple[str, Tri]], applicable: frozenset[str]) -> tuple[str, dict[str, str]]:
    # Keep every computed predicate in the audit trail, including facts below
    # the winning branch. Priority selection still fails closed on an earlier U.
    evidence = {name: result.value if name in applicable else "NOT_APPLICABLE"
                for name, result in predicates}
    for name, _ in predicates:
        result = evidence[name]
        if result == Tri.UNKNOWN.value:
            return "DATA_UNAVAILABLE", evidence
        if result == Tri.TRUE.value:
            return name, evidence
    return "UNCLASSIFIED", evidence


def _from_bool(condition: bool | None) -> Tri:
    return Tri.UNKNOWN if condition is None else Tri.TRUE if condition else Tri.FALSE


def _test(left: Decimal | None, op: str, right: Decimal | None) -> Tri:
    if left is None or right is None:
        return Tri.UNKNOWN
    return _from_bool({"LT": left < right, "LE": left <= right,
                       "GT": left > right, "GE": left >= right}[op])


def classify_stock(facts: Mapping[str, Any], *, invalidation: Tri,
                   applicable: frozenset[str],
                   prior_lifetime_tags: frozenset[str] = frozenset()) -> PathDecision:
    """Classify without treating unavailable higher-priority evidence as false."""
    if facts.get("has_actual_bar") is not True:
        return PathDecision("DATA_UNAVAILABLE", _validity(invalidation),
                            tuple(sorted(prior_lifetime_tags)), (), {"actual_bar": "UNKNOWN"})
    close, ma20 = _num(facts, "close"), _num(facts, "ma20")
    dd = _num(facts, "drawdown_current")
    r5, rps_delta = _num(facts, "r5"), _num(facts, "rps20_delta3")
    relative = _num(facts, "relative_to_entry_sector")
    pullback = tri_and([
        _test(dd, "GE", -STOCK_PARAMETERS["PULLBACK_MAX"]),
        _test(dd, "LE", -STOCK_PARAMETERS["PULLBACK_MIN"]),
    ])
    healthy = tri_and([pullback, _test(close, "GE", ma20),
                       _truth(facts.get("structure_break") is False if facts.get("structure_break") is not None else None),
                       _from_bool(invalidation == Tri.FALSE if invalidation != Tri.UNKNOWN else None)])
    unconfirmed = tri_and([pullback,
                           tri_or([_test(close, "LT", ma20),
                                   _truth(facts.get("confirmation") is False if facts.get("confirmation") is not None else None)]),
                           _from_bool(invalidation == Tri.FALSE if invalidation != Tri.UNKNOWN else None)])
    accelerating = tri_and([_truth(facts.get("trend_continue")), _test(r5, "GT", Decimal(0)),
                            _test(rps_delta, "GE", Decimal(0)), _truth(facts.get("primary_sector_current"))])
    divergence = tri_and([_truth(facts.get("primary_sector_current") is False if facts.get("primary_sector_current") is not None else None),
                          _test(abs(relative) if relative is not None else None, "GE", STOCK_PARAMETERS["SECTOR_DIVERGENCE_MIN"])])
    rps3 = facts.get("rps20_last_3")
    rps_weak = None
    if isinstance(rps3, (list, tuple)) and len(rps3) == 3:
        parsed = [_decimal(x) for x in rps3]
        if all(value is not None for value in parsed):
            rps_weak = parsed[0] > parsed[1] > parsed[2]
    weakening = tri_and([tri_or([_test(close, "LT", ma20), _from_bool(rps_weak)]),
                         _from_bool(invalidation == Tri.FALSE if invalidation != Tri.UNKNOWN else None)])
    predicates = [
        ("STRUCTURE_DAMAGED", invalidation),
        ("TOO_EXTENDED", _truth(facts.get("source_extended"))),
        ("PULLBACK_HEALTHY", healthy),
        ("PULLBACK_UNCONFIRMED", unconfirmed),
        ("BREAKOUT_CONFIRMED", _truth(facts.get("launch_confirm"))),
        ("TREND_ACCELERATING", accelerating),
        ("SECTOR_DIVERGENCE", divergence),
        ("WEAKENING", weakening),
        ("WAIT_CONFIRMATION", _from_bool(facts.get("early_or_setup") is True and facts.get("waiting_evaluable") is True
                                            if facts.get("early_or_setup") is not None and facts.get("waiting_evaluable") is not None else None)),
        ("EXITED_FOLLOW_UP", _truth(facts.get("exited"))),
    ]
    state, evidence = _select(predicates, applicable)
    tags = set(prior_lifetime_tags)
    secondary: set[str] = set()
    range5 = _num(facts, "range5_high_low")
    if range5 is not None and range5 <= STOCK_PARAMETERS["SIDEWAYS_RANGE_MAX"] and facts.get("five_consecutive_actual_bars") is True and invalidation == Tri.FALSE:
        secondary.add("SIDEWAYS_RANGE")
    mfe = _num(facts, "mfe")
    if mfe is not None and dd is not None and facts.get("ever_pullback_3pct") is False and mfe >= STOCK_PARAMETERS["PULLBACK_MIN"] and dd >= -STOCK_PARAMETERS["PULLBACK_MIN"]:
        tags.add("HAD_DIRECT_ADVANCE")
    if facts.get("exited") is True:
        secondary.add("LIST_EXITED")
    return PathDecision(state, _validity(invalidation), tuple(sorted(tags)),
                        tuple(sorted(secondary)), evidence)


def classify_sector(facts: Mapping[str, Any], *, invalidation: Tri,
                    applicable: frozenset[str]) -> PathDecision:
    if facts.get("coverage_ready") is not True or facts.get("source_membership") not in {"CURRENT", "EARLY", "NONE"}:
        return PathDecision("DATA_UNAVAILABLE", _validity(invalidation), (), (),
                            {"coverage": "UNKNOWN"})
    sret = _num(facts, "sret1")
    srel = _num(facts, "srel")
    width, prior_width = _num(facts, "swidth"), _num(facts, "prior_swidth")
    signal_width = _num(facts, "signal_swidth")
    retention = _num(facts, "retention")
    sdd = _num(facts, "sdd")
    current = facts.get("source_membership") == "CURRENT"
    early = facts.get("source_membership") == "EARLY"
    accelerating = tri_and([_from_bool(current), _test(sret, "GT", Decimal(0)),
                            _test(srel, "GT", Decimal(0)), _test(width, "GE", prior_width),
                            _test(retention, "GE", SECTOR_PARAMETERS["RETENTION_WARN"])])
    healthy = tri_and([_from_bool(current or early),
                       _test(sdd, "GE", -SECTOR_PARAMETERS["SECTOR_PULLBACK_MAX"]),
                       _test(sdd, "LE", -SECTOR_PARAMETERS["SECTOR_PULLBACK_MIN"]),
                       _test(srel, "GE", Decimal(0)),
                       _from_bool(invalidation == Tri.FALSE if invalidation != Tri.UNKNOWN else None)])
    width_drop = signal_width - width if signal_width is not None and width is not None else None
    diffusion = tri_and([tri_or([_test(width_drop, "GE", SECTOR_PARAMETERS["WIDTH_DROP_WARN"]),
                                 _test(retention, "LT", SECTOR_PARAMETERS["RETENTION_WARN"])]),
                         _from_bool(invalidation == Tri.FALSE if invalidation != Tri.UNKNOWN else None)])
    predicates = [
        ("SECTOR_STRUCTURE_DAMAGED", invalidation),
        ("SECTOR_ACCELERATING", accelerating),
        ("SECTOR_HEALTHY_PULLBACK", healthy),
        ("SECTOR_DIFFUSION_WEAKENING", diffusion),
        ("SECTOR_ROTATION", _truth(facts.get("role_rotation_confirmed"))),
        ("SECTOR_EARLY_WAIT", _from_bool(early and facts.get("waiting_evaluable") is True
                                         if facts.get("waiting_evaluable") is not None else None)),
        ("SECTOR_PERSISTENT", _from_bool(current)),
        ("SECTOR_EXITED_FOLLOW_UP", _truth(facts.get("exited"))),
    ]
    state, evidence = _select(predicates, applicable)
    return PathDecision("SECTOR_UNCLASSIFIED" if state == "UNCLASSIFIED" else state,
                        _validity(invalidation), (),
                        ("LIST_EXITED",) if facts.get("exited") is True else (), evidence)
