"""V3 P05-02 independent stock signal classification.

This module consumes P05-01 feature rows only.  It has no sector, shortlist,
database, network, or publication lookup dependency.
"""

from __future__ import annotations

import math
from typing import Any, Mapping

import pandas as pd


CONTRACT_ID = "STOCK_ATTENTION_PREVIEW_1"
SIGNALS = ("BREAKOUT", "SETUP", "RECOVERY", "TREND_BACKGROUND", "STRUCTURE_BREAK")

# Auditable C20-02 map. FIXED entries are exact V3 predicates rather than
# hidden defaults. Config entries must exist in the supplied v3.1 bundle.
PREDICATE_CONTRACT = {
    "EXTENDED": {
        "bias20": "risk.bias20_gte",
        "extension_z20": "risk.extension_z20_gte",
    },
    "BREAKOUT": {
        "liquidity20": "BREAKOUT.requires_liquidity",
        "close_gt_prior_high20": "FIXED_STRICT_GT",
        "close_gte_ma20": "FIXED_GTE",
        "amount_vs_prior20": "BREAKOUT.amount_vs_prior20_gte",
        "position_complete": "BREAKOUT.requires_position_fields",
        "not_extended": "BREAKOUT.reject_extended",
    },
    "SETUP": {
        "liquidity20": "SETUP.requires_liquidity",
        "close_to_ma20": "SETUP.close_to_ma20_min/max",
        "ma20_delta3": "SETUP.ma20_delta3_gte",
        "dist_high20": "SETUP.dist_high20_min/max",
        "range_contraction": "SETUP.range5_to_range20_lte",
        "rps5_delta3": "SETUP.rps5_delta3_gte",
        "position_complete": "SETUP.requires_position_fields",
        "not_extended": "SETUP.reject_extended",
    },
    "RECOVERY": {
        "liquidity20": "RECOVERY.requires_liquidity",
        "ma20_delta3": "FIXED_GTE_ZERO",
        "previous_below_ma5": "RECOVERY.requires_previous_close_below_ma5",
        "current_above_ma5": "FIXED_STRICT_GT",
        "close_to_ma20": "RECOVERY.close_to_ma20_gte",
        "rps5_delta3": "RECOVERY.rps5_delta3_gt",
        "amount_vs_prior20": "RECOVERY.amount_vs_prior20_gte",
        "position_complete": "RECOVERY.requires_position_fields",
        "not_extended": "RECOVERY.reject_extended",
    },
    "TREND_BACKGROUND": {
        "close_gte_ma20": "TREND_BACKGROUND.close_gte_ma20",
        "ma20_delta5": "TREND_BACKGROUND.ma20_delta5_gt",
        "rps20": "TREND_BACKGROUND.rps20_gte",
    },
    "STRUCTURE_BREAK": {
        "current_below_ma20": "STRUCTURE_BREAK.close_to_ma20_lt",
        "previous_below_ma20": "STRUCTURE_BREAK.consecutive_valid_sessions",
    },
}


class StockAttentionError(ValueError):
    pass


def _number(row: Mapping[str, Any], name: str) -> float | None:
    try:
        value = float(row.get(name))
    except (TypeError, ValueError):
        return None
    return value if math.isfinite(value) else None


def _and(values: list[bool | None]) -> bool | None:
    if any(value is False for value in values):
        return False
    if any(value is None for value in values):
        return None
    return True


def _cmp(row: Mapping[str, Any], field: str, op, threshold: float) -> bool | None:
    value = _number(row, field)
    return None if value is None else bool(op(value, float(threshold)))


def _ratio(row: Mapping[str, Any], numerator: str, denominator: str) -> float | None:
    left, right = _number(row, numerator), _number(row, denominator)
    return None if left is None or right is None or right <= 0 else left / right


def _boolean(value: Any) -> bool | None:
    if value is None or (not isinstance(value, (bool,)) and pd.isna(value)):
        return None
    return bool(value) if isinstance(value, (bool,)) or type(value).__name__ == "bool_" else None


def _required_config(config: Mapping[str, Any]) -> Mapping[str, Any]:
    try:
        signals = config["thresholds"]["stock_signals"]
        for signal in SIGNALS:
            if signal not in signals:
                raise KeyError(signal)
        return signals
    except (KeyError, TypeError) as exc:
        raise StockAttentionError(f"STOCK_SIGNAL_CONFIG_REQUIRED:{exc}") from exc


def classify_stock_attention(row: Mapping[str, Any], config: Mapping[str, Any]) -> dict[str, Any]:
    thresholds = _required_config(config)
    risk = thresholds["risk"]
    extended = _and([
        _cmp(row, "bias20", lambda a, b: a >= b, risk["bias20_gte"]),
        _cmp(row, "extension_z20", lambda a, b: a >= b, risk["extension_z20_gte"]),
    ])

    liquidity = _boolean(row.get("liquidity20"))
    close_ma20 = _ratio(row, "close", "ma20")
    ma20, ma20_p1, ma20_p3, ma20_p5 = (_number(row, name) for name in ("ma20", "ma20_prior1", "ma20_prior3", "ma20_prior5"))
    close, close_p1 = _number(row, "close"), _number(row, "close_prior1")
    ma5, ma5_p1 = _number(row, "ma5"), _number(row, "ma5_prior1")
    range5, range20 = _number(row, "range5"), _number(row, "range20")

    def known_not_extended() -> bool | None:
        return None if extended is None else not extended

    b = thresholds["BREAKOUT"]
    breakout_checks = {
        "LIQUIDITY": liquidity if b["requires_liquidity"] else True,
        "NEW_HIGH20": _cmp(row, "dist_high20", lambda a, z: a > z, 0),
        "ABOVE_MA20": None if close_ma20 is None else close_ma20 >= 1,
        "AMOUNT_EXPANSION": _cmp(row, "amount_vs_prior20", lambda a, z: a >= z, b["amount_vs_prior20_gte"]),
        "NOT_EXTENDED": known_not_extended() if b["reject_extended"] else True,
    }
    s = thresholds["SETUP"]
    setup_checks = {
        "LIQUIDITY": liquidity if s["requires_liquidity"] else True,
        "CLOSE_TO_MA20": None if close_ma20 is None else s["close_to_ma20_min"] <= close_ma20 <= s["close_to_ma20_max"],
        "MA20_NONDECLINING_3": None if ma20 is None or ma20_p3 is None else ma20 - ma20_p3 >= s["ma20_delta3_gte"],
        "NEAR_PRIOR_HIGH20": None if _number(row, "dist_high20") is None else s["dist_high20_min"] <= _number(row, "dist_high20") <= s["dist_high20_max"],
        "RANGE_CONTRACTION": None if range5 is None or range20 is None or range20 <= 0 else range5 <= s["range5_to_range20_lte"] * range20,
        "RPS5_IMPROVING": _cmp(row, "rps5_delta3", lambda a, z: a >= z, s["rps5_delta3_gte"]),
        "NOT_EXTENDED": known_not_extended() if s["reject_extended"] else True,
    }
    r = thresholds["RECOVERY"]
    recovery_checks = {
        "LIQUIDITY": liquidity if r["requires_liquidity"] else True,
        "MA20_NONDECLINING_3": None if ma20 is None or ma20_p3 is None else ma20 >= ma20_p3,
        "PREVIOUS_BELOW_MA5": None if close_p1 is None or ma5_p1 is None else close_p1 <= ma5_p1,
        "CURRENT_ABOVE_MA5": None if close is None or ma5 is None else close > ma5,
        "ABOVE_MA20_FLOOR": None if close_ma20 is None else close_ma20 >= r["close_to_ma20_gte"],
        "RPS5_IMPROVING": _cmp(row, "rps5_delta3", lambda a, z: a > z, r["rps5_delta3_gt"]),
        "AMOUNT_EXPANSION": _cmp(row, "amount_vs_prior20", lambda a, z: a >= z, r["amount_vs_prior20_gte"]),
        "NOT_EXTENDED": known_not_extended() if r["reject_extended"] else True,
    }
    t = thresholds["TREND_BACKGROUND"]
    trend_checks = {
        "ABOVE_MA20": None if close_ma20 is None else close_ma20 >= 1,
        "MA20_RISING_5": None if ma20 is None or ma20_p5 is None else ma20 > ma20_p5,
        "RPS20": _cmp(row, "rps20", lambda a, z: a >= z, t["rps20_gte"]),
    }
    k = thresholds["STRUCTURE_BREAK"]["close_to_ma20_lt"]
    structure_checks = {
        "CURRENT_BELOW_MA20": None if close_ma20 is None else close_ma20 < k,
        "PREVIOUS_BELOW_MA20": None if close_p1 is None or ma20_p1 is None or ma20_p1 <= 0 else close_p1 / ma20_p1 < k,
    }
    checks = {"BREAKOUT": breakout_checks, "SETUP": setup_checks, "RECOVERY": recovery_checks, "TREND_BACKGROUND": trend_checks, "STRUCTURE_BREAK": structure_checks}
    values = {name: _and(list(group.values())) for name, group in checks.items()}
    reason_codes = [name for name in SIGNALS if values[name] is True]
    if extended is True:
        reason_codes.append("EXTENDED")
    unknown = sorted(name for name in SIGNALS if values[name] is None)
    return {
        "contract_id": CONTRACT_ID,
        "security_id": row.get("security_id"),
        "trade_date": row.get("trade_date"),
        "extended": extended,
        **{name.lower(): values[name] for name in SIGNALS},
        "focus_trigger": _and([not values["STRUCTURE_BREAK"] if values["STRUCTURE_BREAK"] is not None else None, _or(values["BREAKOUT"], values["RECOVERY"])]),
        "checks": checks,
        "reason_codes": reason_codes,
        "unknown_signals": unknown,
        "quality": "READY" if not unknown else "PARTIAL",
    }


def _or(left: bool | None, right: bool | None) -> bool | None:
    if left is True or right is True:
        return True
    if left is None or right is None:
        return None
    return False


def classify_stock_frame(features: pd.DataFrame, config: Mapping[str, Any]) -> pd.DataFrame:
    return pd.DataFrame(classify_stock_attention(row, config) for row in features.to_dict("records"))


def signal_distribution(signals: pd.DataFrame, *, example_limit: int = 3) -> dict[str, Any]:
    """Summarise P05 signals without creating another stock-result dataset."""
    if example_limit < 1:
        raise StockAttentionError("EXAMPLE_LIMIT_POSITIVE_REQUIRED")
    summary: dict[str, Any] = {}
    for signal in SIGNALS:
        column = signal.lower()
        values = signals[column]
        true_rows = signals[values.eq(True)]
        false_rows = signals[values.eq(False)]
        unknown_rows = signals[values.isna()]
        rejected: dict[str, int] = {}
        missing: dict[str, int] = {}
        for row in false_rows.to_dict("records"):
            for code, value in (row.get("checks", {}).get(signal.upper(), {}) or {}).items():
                if value is False:
                    rejected[code] = rejected.get(code, 0) + 1
        for row in unknown_rows.to_dict("records"):
            for code, value in (row.get("checks", {}).get(signal.upper(), {}) or {}).items():
                if value is None:
                    missing[code] = missing.get(code, 0) + 1
        def examples(frame: pd.DataFrame) -> list[dict[str, Any]]:
            return [
                {"security_id": item.get("security_id"), "trade_date": item.get("trade_date"), "checks": item.get("checks", {}).get(signal.upper(), {})}
                for item in frame.sort_values("security_id", kind="mergesort").head(example_limit).to_dict("records")
            ]
        summary[signal] = {
            "true_count": int(values.eq(True).sum()),
            "false_count": int(values.eq(False).sum()),
            "unknown_count": int(values.isna().sum()),
            "top_rejection_codes": [{"code": key, "count": value} for key, value in sorted(rejected.items(), key=lambda item: (-item[1], item[0]))],
            "top_missing_codes": [{"code": key, "count": value} for key, value in sorted(missing.items(), key=lambda item: (-item[1], item[0]))],
            "examples": {"true": examples(true_rows), "false": examples(false_rows), "unknown": examples(unknown_rows)},
        }
    return summary


__all__ = ["CONTRACT_ID", "PREDICATE_CONTRACT", "SIGNALS", "StockAttentionError", "classify_stock_attention", "classify_stock_frame", "signal_distribution"]
