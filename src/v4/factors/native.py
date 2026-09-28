"""V4-03 market and sector input primitives; no profile or V4-08 publication."""

from __future__ import annotations

from hashlib import sha256
import json
from statistics import median
from typing import Mapping, Sequence

from .parameters import candidate_threshold


MARKET_REGIME_PARAMETER_SET_ID = "V4_03_CORE_FACTOR_PARAMETER_SET_V1"


def market_axis_primitives(*, breadth: float | None, participation: float | None,
                           limit_coverage: float | None, stress_ratio: float | None,
                           prior_stress_ratio: float | None) -> dict:
    """Deterministic axes other than trend; final regime UI remains V4-04."""
    breadth_boundary = candidate_threshold("market_breadth_axis")
    participation_high = candidate_threshold("market_participation_expanding")
    participation_low = candidate_threshold("market_participation_thin")
    stress_coverage = candidate_threshold("market_stress_min_limit_coverage")
    stress_high = candidate_threshold("market_stress_high")
    stress_elevated = candidate_threshold("market_stress_elevated")
    breadth_axis = ("IMPROVING" if breadth > breadth_boundary else "DETERIORATING" if breadth < -breadth_boundary else "STABLE") if breadth is not None else None
    participation_axis = ("EXPANDING" if participation >= participation_high else "THIN" if participation < participation_low else "NORMAL") if participation is not None else None
    stress_level = ("HIGH" if stress_ratio >= stress_high else "ELEVATED" if stress_ratio >= stress_elevated else "LOW") if stress_ratio is not None and limit_coverage is not None and limit_coverage >= stress_coverage else None
    stress_change = ("RISING" if stress_ratio > prior_stress_ratio else "DECLINING" if stress_ratio < prior_stress_ratio else "STABLE") if stress_ratio is not None and prior_stress_ratio is not None else None
    return {"contract_id": "MARKET_REGIME_V1_PRIMITIVES", "parameter_set_id": MARKET_REGIME_PARAMETER_SET_ID,
            "breadth_axis": breadth_axis, "participation_axis": participation_axis,
            "stress_level": stress_level, "stress_change": stress_change,
            "trend_axis": None, "trend_axis_blocker": "CONTRACT_CONFLICT_MARKET_REGIME_TREND_WEAK_AST",
            "regime_ui_publication": "NOT_PUBLISHED_V4_03"}


def historical_market_path(daily_ret1: Sequence[tuple[str, float | None]]) -> list[dict]:
    """Continuous ret1 chain; a missing day breaks the path until a new base."""
    result, level = [], 1.0
    for date, ret in daily_ret1:
        if ret is None or ret <= -1:
            level = None
        elif level is not None:
            level *= 1 + ret
        result.append({"trade_date": date, "level": level,
                       "quality_state": "OBSERVED" if level is not None else "UNKNOWN",
                       "path_identity": "DAILY_REBALANCED_RESEARCH_INDEX"})
    return result


def sector_native(members: Sequence[str], evaluable: Mapping[str, Mapping[str, object]]) -> dict:
    """Unqualified aggregate numerators and denominators only."""
    names = sorted(set(members))
    present = {s: evaluable[s] for s in names if s in evaluable and evaluable[s].get("quality_state") == "OBSERVED"}
    amounts = [x.get("amount") for x in present.values() if x.get("amount") is not None]
    positive = [x.get("ret1") for x in present.values() if x.get("ret1") is not None]
    above_ma20 = [x.get("above_ma20") for x in present.values() if x.get("above_ma20") is not None]
    return {
        "contract_id": "V4_03_SECTOR_NATIVE_PRIMITIVE_V1",
        "publication_permission": "NOT_V4_08_SECTOR_FACTORS",
        "member_set_identity": sha256(json.dumps(names, separators=(",", ":")).encode()).hexdigest(),
        "member_count": len(names), "evaluable_count": len(present),
        "raw_quote_coverage": len(present) / len(names) if names else None,
        "amount_median_primitive": median(amounts) if amounts else None,
        "positive_breadth_numerator": sum(x > 0 for x in positive),
        "positive_breadth_denominator": len(positive),
        "ma20_width_numerator": sum(bool(x) for x in above_ma20),
        "ma20_width_denominator": len(above_ma20),
        "amount_concentration_numerator": max(amounts) if amounts else None,
        "amount_concentration_denominator": sum(amounts) if amounts else None,
    }


def common_members(left: Sequence[str], right: Sequence[str]) -> dict:
    a, b = set(left), set(right)
    return {"common": sorted(a & b), "entered": sorted(b - a), "exited": sorted(a - b)}
