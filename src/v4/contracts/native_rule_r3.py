"""Independent deterministic interpreter for V4-03 native rule schema R3."""

from __future__ import annotations

import math
import hashlib
import json
from statistics import median


def _finite(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def execute(rule: dict, inputs: dict, parameters: dict) -> dict:
    op = rule["operator"]
    if op == "PIT_EQUAL_WEIGHT_REFERENCE":
        members = sorted(set(inputs["members"]))
        values = {sid: inputs["returns"].get(sid) for sid in members}
        valid = {sid: x for sid, x in values.items() if _finite(x)}
        n, k = len(members), len(valid)
        threshold = parameters[rule["missing_gate_parameter_id"]]
        reason = "EMPTY_START_UNIVERSE" if not n else "MISSING_COVERAGE_EXCEEDED" if (n-k)/n > threshold else None
        return {"reference_return": sum(valid.values())/k if k and reason is None else None,
                "universe_count": n, "evaluable_count": k, "missing_count": n-k,
                "coverage": k/n if n else None, "evaluable_members": sorted(valid),
                "evaluable_set_identity": hashlib.sha256(json.dumps(sorted(valid), separators=(",", ":")).encode()).hexdigest(),
                "unknown_reason": reason}
    if op == "UNKNOWN_SUFFIX_PATH":
        if len(inputs["daily_returns"]) != len(inputs["start_universe_ids"]):
            raise ValueError("path PIT identities missing")
        level, broken, result = rule["base_level"], False, []
        for ret in inputs["daily_returns"]:
            if not _finite(ret) or ret <= -1:
                broken = True
            level = None if broken else level * (1 + ret)
            result.append(level)
        return {"levels": result, "quality_states": ["UNKNOWN" if x is None else "OBSERVED" for x in result],
                "series_version": inputs["series_version"], "start_universe_ids": inputs["start_universe_ids"]}
    if op == "MARKET_REGIME_AXES":
        b, p, s, old, coverage = (inputs.get(k) for k in ("breadth", "participation", "stress", "prior_stress", "limit_coverage"))
        close, ma, prior_ma = (inputs.get(k) for k in ("index_close", "index_ma20", "index_ma20_t_minus_5"))
        breadth = ("IMPROVING" if b > parameters["market_breadth_axis"] else "DETERIORATING" if b < -parameters["market_breadth_axis"] else "STABLE") if _finite(b) else None
        participation = ("EXPANDING" if p >= parameters["market_participation_expanding"] else "THIN" if p < parameters["market_participation_thin"] else "NORMAL") if _finite(p) else None
        stress = ("HIGH" if s >= parameters["market_stress_high"] else "ELEVATED" if s >= parameters["market_stress_elevated"] else "LOW") if _finite(s) and _finite(coverage) and coverage >= parameters["market_stress_min_limit_coverage"] else None
        change = ("RISING" if s > old else "DECLINING" if s < old else "STABLE") if _finite(s) and _finite(old) else None
        trend = "UNKNOWN" if not all(_finite(x) for x in (close, ma, prior_ma)) else "STRONG" if close > ma > prior_ma else "WEAK" if close < ma < prior_ma else "NEUTRAL"
        return {"breadth_axis": breadth, "participation_axis": participation, "stress_level": stress,
                "stress_change": change, "trend_axis": trend}
    if op == "SECTOR_FIELD_LOCAL_PRIMITIVES":
        if not inputs.get("membership_snapshot_id"):
            raise ValueError("accepted PIT sector membership identity missing")
        names = sorted(set(inputs["members"]))
        rows = {sid: inputs["rows"][sid] for sid in names if sid in inputs["rows"]}
        quotes = [r for r in rows.values() if r.get("quote_quality_state") == "OBSERVED"]
        amounts = [r["amount"] for r in rows.values() if r.get("amount_quality_state") == "OBSERVED" and _finite(r.get("amount"))]
        returns = [r["ret1"] for r in rows.values() if r.get("ret1_quality_state") == "OBSERVED" and _finite(r.get("ret1"))]
        ma = [r["above_ma20"] for r in rows.values() if r.get("ma20_quality_state") == "OBSERVED" and isinstance(r.get("above_ma20"), bool)]
        return {"member_count": len(names), "input_row_count": len(rows), "raw_quote_evaluable_count": len(quotes),
                "raw_quote_coverage": len(quotes)/len(names) if names else None,
                "amount_evaluable_count": len(amounts), "amount_median_primitive": median(amounts) if amounts else None,
                "positive_breadth_numerator": sum(x > 0 for x in returns), "positive_breadth_denominator": len(returns),
                "ma20_width_numerator": sum(ma), "ma20_width_denominator": len(ma),
                "amount_concentration_evaluable_count": len(amounts),
                "amount_concentration_numerator": max(amounts) if amounts else None,
                "amount_concentration_denominator": sum(amounts) if amounts else None}
    raise ValueError(f"unsupported native operator {op}")
