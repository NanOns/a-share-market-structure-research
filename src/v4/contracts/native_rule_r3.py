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
        change_s = inputs.get("stress_change_current", s)
        change = ("RISING" if change_s > old else "DECLINING" if change_s < old else "STABLE") if _finite(change_s) and _finite(old) else None
        trend = "UNKNOWN" if not all(_finite(x) for x in (close, ma, prior_ma)) else "STRONG" if close > ma > prior_ma else "WEAK" if close < ma < prior_ma else "NEUTRAL"
        return {"breadth_axis": breadth, "participation_axis": participation, "stress_level": stress,
                "stress_change": change, "trend_axis": trend}
    if op == "MARKET_REGIME_REV2_RAW":
        current = set(inputs["members_t"])
        prior3 = set(inputs["members_t_minus_3"])
        common3 = current & prior3
        ret_now, ret_old = inputs["ret1_t"], inputs["ret1_t_minus_3"]
        eligible3 = sorted(sid for sid in common3 if _finite(ret_now.get(sid)) and _finite(ret_old.get(sid)))
        breadth_now = sum(ret_now[sid] > 0 for sid in eligible3)/len(eligible3) if eligible3 else None
        breadth_old = sum(ret_old[sid] > 0 for sid in eligible3)/len(eligible3) if eligible3 else None
        breadth = breadth_now-breadth_old if eligible3 else None
        ratios = []
        for sid in current:
            amount = inputs["amount_t"].get(sid)
            history = inputs["prior20_actual_amounts"].get(sid, [])
            if inputs["prior20_window_valid"].get(sid) is True and _finite(amount) and amount >= 0 and len(history) == rule["prior_actual_bar_count"] and all(_finite(x) and x >= 0 for x in history):
                mean = sum(history)/len(history)
                if mean > 0:
                    ratios.append(amount/mean)
        participation = median(ratios) if ratios else None
        valid_status = set(rule["valid_limit_statuses"])
        now = {sid: status for sid, status in inputs["limit_t"].items() if sid in current and status in valid_status}
        coverage = len(now)/len(current) if current else None
        stress = sum(x == "LIMIT_DOWN" for x in now.values())/len(now) if now else None
        common1 = current & set(inputs["members_t_minus_1"])
        prior = inputs["limit_t_minus_1"]
        eligible1 = sorted(sid for sid in common1 if sid in now and prior.get(sid) in valid_status)
        stress_now = sum(now[sid] == "LIMIT_DOWN" for sid in eligible1)/len(eligible1) if eligible1 else None
        stress_old = sum(prior[sid] == "LIMIT_DOWN" for sid in eligible1)/len(eligible1) if eligible1 else None
        axes = execute({"operator": "MARKET_REGIME_AXES"}, {"breadth": breadth, "participation": participation,
                       "stress": stress, "prior_stress": stress_old, "stress_change_current": stress_now,
                       "limit_coverage": coverage, "index_close": inputs.get("index_close"),
                       "index_ma20": inputs.get("index_ma20"), "index_ma20_t_minus_5": inputs.get("index_ma20_t_minus_5")}, parameters)
        return {"breadth_common_count": len(common3), "breadth_evaluable_count": len(eligible3),
                "breadth_delta3": breadth, "participation_evaluable_count": len(ratios),
                "participation_median_amount_ratio20": participation,
                "stress_common_count": len(common1), "stress_evaluable_count": len(eligible1),
                "stress_same_member_current_ratio": stress_now, "stress_same_member_prior_ratio": stress_old, **axes}
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
