"""Pure, explainable P12-03 scanner over versioned P12-02 facts."""

from __future__ import annotations

from collections.abc import Mapping
import math
from typing import Any

CONTRACT_ID = "TODAY_RESEARCH_SCANNER_V3_3_CANDIDATE_01"
SCENARIOS = ("LAUNCH", "PULLBACK", "RECOVERY_TURN", "TREND_CONTINUE")
PARAMETER_CONTRACT = {
    "launch": {"clv_gte": .60, "amr20_mean_prior_gte": 1.20},
    "recovery_turn": {"clv_gte": .55, "amr20_mean_prior_gte": 1.05,
                      "close_to_ma20_gte": .98, "rps5_delta3_gt": 0.0,
                      "prior5_below_ma20_count_gte": 2},
    "trend_continue": {"clv_gte": .55, "rps20_gte": .70,
                       "amr20_mean_prior_min": .80, "amr20_mean_prior_max": 2.50},
    "support": {"trend_continue_requires_current_loo": True},
}


def _bool(value: Any) -> bool | None:
    return value if type(value) is bool else None


def _num(row: Mapping[str, Any], key: str) -> float | None:
    try:
        value = float(row.get(key))
    except (TypeError, ValueError):
        return None
    return value if math.isfinite(value) else None


def _cmp(row: Mapping[str, Any], key: str, predicate) -> bool | None:
    value = _num(row, key)
    return None if value is None else bool(predicate(value))


def tri_and(values) -> bool | None:
    values = list(values)
    if any(value is False for value in values):
        return False
    return None if any(value is None for value in values) else True


def tri_or(values) -> bool | None:
    values = list(values)
    if any(value is True for value in values):
        return True
    return None if any(value is None for value in values) else False


def _scenario(checks: Mapping[str, bool | None]) -> dict[str, Any]:
    value = tri_and(checks.values())
    return {"eligible": value,
            "known_failed_checks": sorted(key for key, item in checks.items() if item is False),
            "unknown_checks": sorted(key for key, item in checks.items() if item is None),
            "checks": dict(checks),
            "quality": "READY" if not any(item is None for item in checks.values()) else "PARTIAL"}


def scan_today_research(row: Mapping[str, Any]) -> dict[str, Any]:
    """Evaluate four independent stock scenarios and SETUP_WATCH."""
    common = {
        "NORMAL_UNIVERSE": _bool(row.get("normal_universe")),
        "ACTUAL_BAR": _bool(row.get("actual_bar")),
        "WINDOW_VALID": _bool(row.get("window_valid")),
        "LIQ20": _bool(row.get("liq20")),
        "INPUT_IDENTITY_COMPATIBLE": _bool(row.get("input_identity_compatible")),
    }
    safety = {
        "NOT_STRUCTURE_BREAK": None if _bool(row.get("structure_break_v3")) is None else not row["structure_break_v3"],
        "NOT_EXTENDED": None if _bool(row.get("extended_v3")) is None else not row["extended_v3"],
        "NOT_FIRST_DAY_DAMAGE": None if _bool(row.get("first_day_damage")) is None else not row["first_day_damage"],
        "NOT_SEVERE_DROP": None if _bool(row.get("severe_drop")) is None else not row["severe_drop"],
    }
    base = {**common, **safety}
    launch_checks = {**base,
        "BREAKOUT_V3": _bool(row.get("breakout_v3")),
        "CLOSE_ABOVE_PHC20": _cmp(row, "break_margin_close20", lambda x: x > 0),
        "POSITIVE_RET1": _cmp(row, "ret1_adj", lambda x: x > 0),
        "CLV_GTE_060": _cmp(row, "clv", lambda x: x >= .60),
        "AMR20_GTE_120": _cmp(row, "amr20_mean_prior", lambda x: x >= 1.20),
        "NO_INTRADAY_REJECT_HIGH20": None if _bool(row.get("intraday_reject_high20")) is None else not row["intraday_reject_high20"],
    }
    pullback_checks = {**base, "PULLBACK_EPISODE_CONFIRMED": _bool(row.get("pullback_episode_confirmed"))}
    r5 = tri_and((_bool(row.get("recovery_v3")), _bool(row.get("reclaim_ma5"))))
    r20 = tri_and((_bool(row.get("reclaim_ma20")),
                   _cmp(row, "prior5_below_ma20_count", lambda x: x >= 2),
                   _bool(row.get("ma20_nondeclining_3"))))
    recovery_checks = {**base,
        "R5_OR_R20": tri_or((r5, r20)),
        "POSITIVE_RET1": _cmp(row, "ret1_adj", lambda x: x > 0),
        "CLV_GTE_055": _cmp(row, "clv", lambda x: x >= .55),
        "RPS5_DELTA3_POSITIVE": _cmp(row, "rps5_delta3", lambda x: x > 0),
        "AMR20_GTE_105": _cmp(row, "amr20_mean_prior", lambda x: x >= 1.05),
        "CLOSE_GTE_098_MA20": _cmp(row, "close_to_ma20", lambda x: x >= .98),
    }
    continue_stock_checks = {**base,
        "TREND_BACKGROUND": _bool(row.get("trend_background_v3")),
        "CLOSE_GTE_MA5": _cmp(row, "close_to_ma5", lambda x: x >= 1),
        "MA5_GTE_MA20": _cmp(row, "ma5_to_ma20", lambda x: x >= 1),
        "SLOPE20_POSITIVE": _cmp(row, "slope20", lambda x: x > 0),
        "RPS20_GTE_070": _cmp(row, "rps20", lambda x: x >= .70),
        "POSITIVE_RET1": _cmp(row, "ret1_adj", lambda x: x > 0),
        "CLOSE_ABOVE_PRIOR_HIGH": _bool(row.get("close_above_prior_high")),
        "CLV_GTE_055": _cmp(row, "clv", lambda x: x >= .55),
        "AMR20_IN_080_250": _cmp(row, "amr20_mean_prior", lambda x: .80 <= x <= 2.50),
    }
    launch = _scenario(launch_checks)
    pullback = _scenario(pullback_checks)
    recovery = _scenario(recovery_checks)
    trend_stock = _scenario(continue_stock_checks)
    trend = _scenario({**continue_stock_checks,
                       "CURRENT_WITH_LOO_BREADTH_SUPPORT": _bool(row.get("current_with_loo_breadth_support"))})
    confirmed = tri_or((launch["eligible"], pullback["eligible"], recovery["eligible"], trend["eligible"]))
    # SETUP_WATCH is explicitly an observation state. Unknown evidence in a
    # different scenario remains visible there, but only a known confirmation
    # suppresses this watch state.
    known_confirmed = any(item["eligible"] is True for item in (launch, pullback, recovery, trend))
    setup_checks = {**base, "SETUP_V3": _bool(row.get("setup_v3")),
                    "NO_KNOWN_CONFIRMED_SCENARIO": not known_confirmed}
    setup = _scenario(setup_checks)
    waiting = []
    if setup["eligible"] is True:
        for name, value in (("CLOSE_ABOVE_FROZEN_PHC20", launch_checks["CLOSE_ABOVE_PHC20"]),
                            ("AMR20_GTE_120", launch_checks["AMR20_GTE_120"]),
                            ("CLV_GTE_060", launch_checks["CLV_GTE_060"])):
            if value is not True:
                waiting.append(name)
    high_break = _bool(row.get("break_high20"))
    launch_type = ("HIGH_PLATFORM_BREAK" if launch["eligible"] is True and high_break is True else
                   "CLOSE_PLATFORM_BREAK" if launch["eligible"] is True and high_break is False else None)
    return {"contract_id": CONTRACT_ID, "security_id": row.get("security_id"),
            "trade_date": row.get("trade_date"), "launch": {**launch, "type": launch_type},
            "pullback": pullback, "recovery_turn": {**recovery, "r5": r5, "r20": r20},
            "trend_continue_stock_only": trend_stock, "trend_continue": trend,
            "setup_watch": {**setup, "waiting_for": waiting},
            "confirmed_any": confirmed}
