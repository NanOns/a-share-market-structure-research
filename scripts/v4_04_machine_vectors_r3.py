"""Golden vectors for every frozen V4-04 machine rule and branch."""

from __future__ import annotations

from collections import defaultdict
from hashlib import sha256
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.v4_04_machine_executor import execute_rule, rule_keys

ALGORITHM = ROOT / "config/v4_04_algorithm_contracts_v2.json"
PARAMETERS = ROOT / "config/v4_04_parameter_set_v1.json"
OUT = ROOT / "reports/v4_04/V4_04_MACHINE_VECTOR_COVERAGE_R3.json"


def vectors():
    result = defaultdict(list)
    def add(key, expected, evidence, kind="branch"):
        result[key].append((expected, evidence, kind))
    trend = dict(close=100, ma20=100, ma60=95, slope20=0, slope60=0,
                 hh_progress=False, ll_progress=False, core_price_damage=False)
    for patch, expected in [
        ({"close": 90, "slope20": -.2, "slope60": -.2, "ll_progress": True}, "DOWNTREND_STRONG"),
        ({"close": 110, "slope20": .2, "slope60": .2, "hh_progress": True}, "UPTREND_STRONG"),
        ({"close": 90, "slope20": -.2}, "DOWNTREND"),
        ({"close": 110, "slope20": .2}, "UPTREND"),
        ({"close": 90, "slope20": -.1}, "SIDEWAYS_WEAK"),
        ({"close": 110, "slope20": .1}, "SIDEWAYS_STRONG"),
        ({}, "SIDEWAYS")]:
        add("TREND_STATE_V1.daily", expected, {**trend, **patch}, "threshold")
    for period in ("weekly", "monthly"):
        base = dict(period_type=period, period_view="CLOSED_ONLY", close=3, ma_current=2, ma_previous=1)
        key = "TREND_STATE_V1.closed_period"
        add(key, period.upper() + "_UP", base, "threshold")
        add(key, period.upper() + "_DOWN", {**base, "close": 1, "ma_current": 2, "ma_previous": 3}, "threshold")
        add(key, period.upper() + "_FLAT", {**base, "close": 2}, "threshold")
        add(key, "UNKNOWN", {**base, "period_view": "ASOF_PARTIAL"}, "unknown")
    for bias, pos, expected in [(3, .1, "EXTENDED"), (0, .8, "HIGH_ZONE"), (0, .6, "MID_HIGH"),
                                (0, .4, "MID_ZONE"), (0, .2, "MID_LOW"), (0, .1999, "LOW_ZONE")]:
        add("POSITION_STATE_V1", expected, dict(bias20_atr=bias, pos60=pos), "threshold")
    for close, expected in [(11, "ABOVE_PRIOR_HIGH"), (9, "NEAR"), (8.999, "BELOW")]:
        add("POSITION_STATE_V1.near_high", expected, dict(close=close, prior_highN=10, atr20=2), "threshold")
    for close, expected in [(9.51, "SHALLOW"), (9.5, "MODERATE"),
                            (8.51, "MODERATE"), (8.5, "DEEP"), (8.49, "DEEP")]:
        add("POSITION_STATE_V1.drawdown", expected, dict(close=close, hhvN=10), "threshold")
    for a, b, c, s, expected in [(12, 11, 10, .01, "BULL_ALIGNED"), (8, 9, 10, -.01, "BEAR_ALIGNED"),
                                 (12, 13, 10, 0, "BULL_TRANSITION"), (8, 7, 10, 0, "BEAR_TRANSITION"),
                                 (10, 10, 10, 0, "MIXED")]:
        add("MA_STRUCTURE_V1", expected, dict(ma5=a, ma10=b, ma20=c, slope20=s), "threshold")
    for atr, vol, ran, amount, liquid, expected in [
        (1.5, .5, .3, .5, True, "EXPANDING_EXTREME"),
        (1.1, .5, .3, .5, True, "EXPANDING"),
        (.7, .7, .35, .8, True, "COMPRESSING_STRONG"),
        (.9, .9, .6, 2, True, "COMPRESSING"),
        (1, 1, 1, 1, True, "NORMAL")]:
        add("COMPRESSION_STATE_V1", expected, dict(atr_ratio=atr, vol_ratio=vol, range_ratio=ran,
                                                    amount_ratio20=amount, minimum_liquidity=liquid), "threshold")
    for delta, rps, rel, comp, ma, expected in [
        (10, 50, 0, "COMPRESSING", "MIXED", "ACTIVE_EMERGENCE"),
        (0, 50, .1, "NORMAL", "MIXED", "PASSIVE_RESILIENCE"),
        (1, 80, 0, "NORMAL", "MIXED", "LEADING_ACCELERATING"),
        (-3, 80, 0, "NORMAL", "MIXED", "LEADING_STABLE"),
        (4, 50, 0, "NORMAL", "MIXED", "IMPROVING"),
        (-4, 50, 0, "NORMAL", "MIXED", "WEAKENING"),
        (0, 19, 0, "NORMAL", "MIXED", "LAGGING"),
        (0, 50, 0, "NORMAL", "MIXED", "NEUTRAL")]:
        add("RELATIVE_STATE_V1", expected, dict(rps20_delta3=delta, rps20=rps, rel_market_1=rel,
                                                 compression_state=comp, ma_structure_state=ma), "threshold")
    for ratio, expected in [(.4999, "VERY_DRY"), (.5, "CONTRACTED"), (.8, "NORMAL"),
                            (1.2, "EXPANDED"), (2, "VERY_EXPANDED")]:
        add("AMOUNT_VOLUME_STATE_V1.ratio", expected, {"ratio20": ratio}, "threshold")
    for amount, ret, clv, expected in [
        (1.2, -.01, .8, "HIGH_PARTICIPATION_REVERSAL"),
        (1.2, .01, .7, "HIGH_PARTICIPATION_EFFECTIVE_ADVANCE"),
        (1.2, .01, .699, "HIGH_PARTICIPATION_LOW_EFFICIENCY"),
        (.799, .01, .5, "LOW_PARTICIPATION_ADVANCE"),
        (.799, -.01, .5, "LOW_PARTICIPATION_DECLINE"),
        (1, 0, .5, "NORMAL_PARTICIPATION")]:
        add("AMOUNT_VOLUME_STATE_V1.participation", expected,
            dict(amount_ratio20=amount, ret1=ret, clv=clv), "threshold")
    for bias, ret5, amount, ret1, expected in [
        (4, 0, 1, 0, "EXTREME"), (3, 0, 1, 0, "HIGH"),
        (1, .4, 2, 0, "HIGH"), (2, 0, 1, 0, "MEDIUM"), (1, 0, 1, 0, "LOW")]:
        add("EXTENSION_RISK_V1", expected, dict(bias20_atr=bias, ret5=ret5, atr20=1,
                                                 close=10, amount_ratio20=amount, ret1=ret1), "threshold")
    for risk, expected in [("EXTREME", True), ("HIGH", False), ("LOW", False)]:
        add("EXTENSION_RISK_V1.severe", expected, {"core_extension_risk": risk}, "threshold")
    primitive = "V4_04_DERIVED_PRIMITIVES_V1."
    add(primitive + "ma10", 5.5, {"accepted_QFQ_close": list(range(1, 11))}, "threshold")
    add(primitive + "ma10", 6.5, {"accepted_QFQ_close": list(range(1, 12))}, "branch")
    for amount, expected in [(20_000_000, True), (19_999_999, False)]:
        add(primitive + "minimum_liquidity", expected,
            {"accepted_raw_CNY_amount": [amount] * 20 + [0]}, "threshold")
    for close, expected in [(10, .5), (0, 0), (20, 1)]:
        add(primitive + "pos250", expected, dict(close=close, HHV250=20, LLV250=0), "threshold")
    for close, expected in [(12, 1), (10, 0), (8, -1)]:
        add(primitive + "bias20_atr", expected, dict(close=close, ma20=10, atr20=2), "threshold")
    add(primitive + "bias20_atr", None, dict(close=12, ma20=10, atr20=0), "unknown")
    for close, expected in [(8, 1), (10, 0), (12, -1)]:
        add(primitive + "dist_high20_atr", expected, dict(close=close, prior_high20=10, atr20=2), "threshold")
    add(primitive + "dist_high20_atr", None, dict(close=8, prior_high20=10, atr20=0), "unknown")
    add(primitive + "pos250", None, dict(close=10, HHV250=5, LLV250=5), "unknown")
    add(primitive + "ma10", None, {"accepted_QFQ_close": list(range(1, 10))}, "unknown")
    add(primitive + "minimum_liquidity", None, {"accepted_raw_CNY_amount": [20_000_000] * 19 + [0]}, "unknown")
    regime = "MARKET_REGIME_V1.regime_ui"
    def axes(trend, breadth, stress, change):
        return dict(trend_axis=trend, breadth_axis=breadth, participation_axis="NORMAL",
                    stress_level=stress, stress_change=change)
    for label, row in [
        ("CAPITULATION", axes("WEAK", "STABLE", "HIGH", "RISING")),
        ("RECOVERY_ATTEMPT", axes("WEAK", "IMPROVING", "LOW", "DECLINING")),
        ("RISK_ON", axes("STRONG", "STABLE", "LOW", "FLAT")),
        ("RISK_OFF", axes("WEAK", "STABLE", "LOW", "FLAT")),
        ("NEUTRAL", axes("MIXED", "STABLE", "LOW", "FLAT"))]:
        add(regime, label, {"path": [row, row]}, "branch")
    add(regime, "UNKNOWN", {"path": [axes("UNKNOWN", "STABLE", "LOW", "FLAT")]}, "unknown")
    add(regime, "UNKNOWN", {"path": [axes("STRONG", "STABLE", "LOW", "FLAT")]}, "threshold")
    return result


def run(write_receipt: bool = False) -> dict:
    rules = json.loads(ALGORITHM.read_text(encoding="utf-8"))["rules"]
    parameters = {x["parameter_id"]: x["value"] for x in json.loads(PARAMETERS.read_text(encoding="utf-8"))["parameters"]}
    cases = vectors()
    names = rule_keys(rules)
    if names != set(cases):
        raise ValueError(f"vector rule set mismatch: {sorted(names ^ set(cases))}")
    branch_count = 0
    branches_tested = {}
    threshold_vectors = unknown_vectors = 0
    missing = []
    for key in sorted(names):
        node = rules["V4_04_DERIVED_PRIMITIVES_V1"][key.split(".", 1)[1]] if key.startswith("V4_04_DERIVED_PRIMITIVES_V1.") else rules[key]
        branch_node = node if node.get("operator") == "FIRST_TRUE" else node.get("branches") if isinstance(node.get("branches"), dict) else node.get("candidate") if node.get("operator") == "HYSTERETIC_FIRST_TRUE" else None
        expected_branches = {x["value"] for x in branch_node["branches"]} if branch_node else set()
        if key == "TREND_STATE_V1.closed_period":
            expected_branches = {f"{period}_{direction}" for period in ("WEEKLY", "MONTHLY")
                                 for direction in ("UP", "DOWN", "FLAT")}
        elif key == "EXTENSION_RISK_V1.severe":
            expected_branches = {True, False}
        seen = set()
        has_unknown = has_threshold = False
        for expected, evidence, kind in cases[key]:
            got = execute_rule(rules, key, evidence, parameters)
            if key == "MARKET_REGIME_V1.regime_ui":
                got = got[0]
            if got != expected:
                raise ValueError(f"machine vector mismatch {key}: {expected!r} != {got!r}; {evidence!r}")
            if expected in expected_branches:
                seen.add(expected)
            if kind == "threshold":
                threshold_vectors += 1
                has_threshold = True
            if kind == "unknown":
                unknown_vectors += 1
                has_unknown = True
        # Every rule gets an explicit unknown vector below; the branch data above must remain complete.
        unknown_evidence = {"path": [{}]} if key == "MARKET_REGIME_V1.regime_ui" else {}
        unknown = execute_rule(rules, key, unknown_evidence, parameters)
        if key == "MARKET_REGIME_V1.regime_ui":
            unknown = unknown[0]
        if unknown not in ("UNKNOWN", None):
            raise ValueError(f"missing UNKNOWN propagation: {key}")
        unknown_vectors += 1
        has_unknown = True
        branch_count += len(expected_branches) if expected_branches else 1
        branches_tested[key] = sorted(seen, key=str) if expected_branches else ["VALUE_AND_UNKNOWN"]
        if seen != expected_branches or not has_unknown or not has_threshold:
            missing.append(key)
    receipt = {"contract_id": "V4_04_MACHINE_VECTOR_COVERAGE_R3", "status": "PASS" if not missing else "FAIL",
               "machine_rule_count": len(names), "branch_count": branch_count,
               "branches_tested": branches_tested, "threshold_vectors": threshold_vectors,
               "unknown_vectors": unknown_vectors,
               "rules_with_full_vector_coverage": sorted(names - set(missing)),
               "rules_missing_vector_coverage": missing,
               "algorithm_sha256": sha256(ALGORITHM.read_bytes()).hexdigest(),
               "parameter_sha256": sha256(PARAMETERS.read_bytes()).hexdigest()}
    if write_receipt:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        tmp = OUT.with_suffix(".json.tmp")
        tmp.write_bytes((json.dumps(receipt, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode())
        os.replace(tmp, OUT)
    if missing:
        raise ValueError(f"machine vector coverage incomplete: {missing}")
    return receipt


if __name__ == "__main__":
    print(json.dumps(run(write_receipt=True), ensure_ascii=False))
