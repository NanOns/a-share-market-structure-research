"""Freeze executable native rule schema and independent synthetic vectors."""

import json
import hashlib
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "config/v4_03_native_rule_contracts_r3.json"


def vector(name, category, inputs, expected):
    return {"vector_id": name, "category": category, "input": inputs, "expected_subset": expected}


def main():
    reference = [
        vector("REF_NORMAL", "normal_coverage", {"members": ["A", "B"], "returns": {"A": .1, "B": .2}}, {"reference_return": .15000000000000002, "evaluable_count": 2}),
        vector("REF_MISSING_GATE", "missing_threshold", {"members": ["A", "B"], "returns": {"A": .1}}, {"reference_return": None, "unknown_reason": "MISSING_COVERAGE_EXCEEDED"}),
        vector("REF_N1", "universe_n_lt_2", {"members": ["A"], "returns": {"A": .1}}, {"reference_return": .1, "universe_count": 1}),
        vector("REF_ENDPOINT_UNKNOWN", "endpoint_unavailable", {"members": ["A", "B"], "returns": {"A": None, "B": None}}, {"reference_return": None, "evaluable_count": 0}),
        vector("REF_EVALUABLE_SET", "evaluable_set_identity_change", {"members": ["A", "B", "C"], "returns": {"A": .1, "B": .2, "C": None}}, {"evaluable_members": ["A", "B"], "evaluable_count": 2,
            "evaluable_set_identity": hashlib.sha256(json.dumps(["A", "B"], separators=(",", ":")).encode()).hexdigest()}),
    ]
    path = [
        vector("PATH_NORMAL", "normal_chain", {"daily_returns": [.1, -.05], "start_universe_ids": ["U1", "U1"], "series_version": "S1"}, {"levels": [1.1, 1.045]}),
        vector("PATH_UNKNOWN_SUFFIX", "unknown_suffix", {"daily_returns": [.1, None, .2], "start_universe_ids": ["U1", "U2", "U3"], "series_version": "S1"}, {"levels": [1.1, None, None]}),
        vector("PATH_NEW_VERSION", "new_series_rebase", {"daily_returns": [.2], "start_universe_ids": ["U3"], "series_version": "S2"}, {"levels": [1.2], "series_version": "S2"}),
        vector("PATH_PIT_CHANGE", "pit_universe_change_input", {"daily_returns": [.1, .2], "start_universe_ids": ["U1", "U2"], "series_version": "S1"}, {"levels": [1.1, 1.32], "start_universe_ids": ["U1", "U2"]}),
    ]
    regime = [
        vector("REGIME_ABOVE", "threshold_above", {"breadth": .06, "participation": 1.3, "stress": .06, "prior_stress": .02, "limit_coverage": 1, "index_close": 12, "index_ma20": 11, "index_ma20_t_minus_5": 10}, {"breadth_axis": "IMPROVING", "participation_axis": "EXPANDING", "stress_level": "HIGH", "stress_change": "RISING", "trend_axis": "STRONG"}),
        vector("REGIME_EXACT", "threshold_exact_boundary", {"breadth": .05, "participation": 1.2, "stress": .01, "prior_stress": .01, "limit_coverage": .8, "index_close": 10, "index_ma20": 10, "index_ma20_t_minus_5": 10}, {"breadth_axis": "STABLE", "participation_axis": "EXPANDING", "stress_level": "ELEVATED", "stress_change": "STABLE", "trend_axis": "NEUTRAL"}),
        vector("REGIME_BELOW", "threshold_below", {"breadth": -.06, "participation": .7, "stress": .005, "prior_stress": .01, "limit_coverage": 1, "index_close": 9, "index_ma20": 10, "index_ma20_t_minus_5": 11}, {"breadth_axis": "DETERIORATING", "participation_axis": "THIN", "stress_level": "LOW", "stress_change": "DECLINING", "trend_axis": "WEAK"}),
        vector("REGIME_UNKNOWN", "unknown_and_coverage", {"breadth": None, "participation": None, "stress": .02, "prior_stress": None, "limit_coverage": .5, "index_close": None, "index_ma20": 10, "index_ma20_t_minus_5": 9}, {"breadth_axis": None, "participation_axis": None, "stress_level": None, "stress_change": None, "trend_axis": "UNKNOWN"}),
        vector("REGIME_MIXED", "mixed_trend_neutral", {"breadth": 0, "participation": 1, "stress": 0, "prior_stress": 0, "limit_coverage": 1, "index_close": 9, "index_ma20": 10, "index_ma20_t_minus_5": 9}, {"trend_axis": "NEUTRAL"}),
    ]
    a = {"quote_quality_state": "OBSERVED", "amount_quality_state": "OBSERVED", "amount": 10,
         "ret1_quality_state": "OBSERVED", "ret1": .1, "ma20_quality_state": "OBSERVED", "above_ma20": True}
    b = {"quote_quality_state": "UNKNOWN", "amount_quality_state": "OBSERVED", "amount": 30,
         "ret1_quality_state": "UNKNOWN", "ret1": .2, "ma20_quality_state": "OBSERVED", "above_ma20": False}
    sector = [
        vector("SECTOR_LOCAL", "field_local_denominator", {"members": ["A", "B"], "rows": {"A": a, "B": b}}, {"raw_quote_coverage": .5, "amount_evaluable_count": 2, "positive_breadth_denominator": 1, "ma20_width_denominator": 2}),
        vector("SECTOR_EMPTY", "empty_member_set", {"members": [], "rows": {}}, {"member_count": 0, "raw_quote_coverage": None, "amount_median_primitive": None}),
        vector("SECTOR_PARTIAL", "partial_evaluable_rows", {"members": ["A", "B", "C"], "rows": {"A": a}}, {"input_row_count": 1, "raw_quote_coverage": 1/3}),
        vector("SECTOR_REORDER", "member_reorder_invariance", {"members": ["B", "A", "B"], "rows": {"A": a, "B": b}}, {"member_count": 2, "amount_median_primitive": 20}),
        vector("SECTOR_CHANGE", "member_change", {"members": ["A"], "rows": {"A": a, "B": b}}, {"member_count": 1, "amount_median_primitive": 10}),
        vector("SECTOR_MISSING_ID", "missing_membership_identity", {"members": [], "rows": {}}, {"error": "accepted PIT sector membership identity missing"}),
    ]
    for item in sector:
        if item["vector_id"] != "SECTOR_MISSING_ID":
            item["input"]["membership_snapshot_id"] = "SYNTHETIC_PIT_MEMBERSHIP_V1"
    contracts = [
        {"contract_id": "MARKET_RELATIVE_REFERENCE_V1", "rule": {"operator": "PIT_EQUAL_WEIGHT_REFERENCE", "missing_gate_parameter_id": "V4_03_MARKET_REFERENCE_MAX_MISSING_FRACTION"}, "vectors": reference},
        {"contract_id": "V4_03_MARKET_REFERENCE_PATH_V1", "rule": {"operator": "UNKNOWN_SUFFIX_PATH", "base_level": 1.0, "rebase_requires_new_series_version": True}, "vectors": path},
        {"contract_id": "MARKET_REGIME_V1_PRIMITIVES", "rule": {"operator": "MARKET_REGIME_AXES", "trend_producer": "MARKET_REGIME_TREND_WEAK_ERRATUM_V1"}, "vectors": regime},
        {"contract_id": "V4_03_SECTOR_NATIVE_PRIMITIVE_V1", "rule": {"operator": "SECTOR_FIELD_LOCAL_PRIMITIVES", "membership_identity_required_for_publication": True}, "vectors": sector},
    ]
    payload = {"contract_id": "V4_03_NATIVE_DETERMINISTIC_RULE_SCHEMA_R3", "version": "1.0.0",
               "amendment": "Native aggregate/stateful rules use this executable deterministic schema because RULE_AST_V2 cannot express path state or set-identity objects without changing existing 1.1 contracts.",
               "governing_task": "docs/audits/V4_03_R3_EXTERNAL_BLOCKER_CLOSURE_TASK_20260928.md",
               "contracts": contracts}
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    tmp = OUTPUT.with_suffix(OUTPUT.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    os.replace(tmp, OUTPUT)
    print(sum(len(c["vectors"]) for c in contracts))


if __name__ == "__main__":
    main()
