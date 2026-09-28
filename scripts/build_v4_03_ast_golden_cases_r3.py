"""Freeze independently calculated edge expectations for R3 AST verification."""

import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "config/v4_03_ast_numeric_fixture_v1.json"
OUTPUT = ROOT / "config/v4_03_ast_golden_cases_r3.json"


def main():
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    bars = fixture["history"]
    last_five = [x["bar"]["close"] for x in bars[-5:]]
    cases = []

    def add(name, category, field, operations, expected):
        cases.append({"case_id": name, "category": category, "field_id": field,
                      "operations": operations, "expected": expected})

    add("TECH_EXACT_5", "technical_exact_n_actual", "ma5", [["tail", 5]], sum(last_five) / 5)
    add("TECH_ONE_SHORT", "technical_one_short", "ma5", [["tail", 4]], None)
    add("TECH_CONFIRMED_SUSPENSION", "technical_confirmed_suspension", "ma5", [["tail", 5], ["insert_state", 2, "CONFIRMED_SUSPENSION"]], sum(last_five) / 5)
    add("TECH_RESUME_AFTER_SUSPENSION", "technical_resume", "ma5", [["tail", 5], ["insert_state", 4, "CONFIRMED_SUSPENSION"]], sum(last_five) / 5)
    add("TECH_T0_SUSPENDED_CURRENT", "technical_t0_suspension", "ma5", [["set_state", -1, "CONFIRMED_SUSPENSION"]], None)
    add("TECH_T0_SUSPENDED_PRIOR", "technical_t0_prior_only", "prior_high5", [["set_state", -1, "CONFIRMED_SUSPENSION"]], max(x["bar"]["high"] for x in bars[-6:-1]))
    add("TECH_UNEXPLAINED_GAP", "technical_unexplained_gap", "ma5", [["tail", 5], ["insert_state", 2, "UNEXPLAINED_GAP"]], None)
    add("TECH_MIXED_ADJUSTMENT", "adjustment_basis_mismatch", "ma5", [["set_bar", -2, "basis", "OTHER_QFQ"]], None)
    add("TECH_SOURCE_REVISION_MISMATCH", "source_revision_mismatch", "ma5", [["set_bar", -2, "source", "e" * 64]], None)
    add("TECH_NONPOSITIVE_REQUIRED_PRICE", "nonpositive_required_price", "ret1", [["set_bar", -2, "close", 0]], None)
    add("TECH_ZERO_DENOMINATOR", "zero_denominator", "ret1", [["set_bar", -2, "close", 0]], None)
    add("TECH_FLAT_RANGE", "flat_range", "clv", [["set_bar", -1, "high", 100], ["set_bar", -1, "low", 100]], None)
    zero_amount_ops = [["set_bar", i, "amount", 0] for i in range(-6, -1)]
    add("TECH_AMOUNT_DENOMINATOR_ZERO", "amount_volume_zero_denominator", "amount_ratio5", zero_amount_ops, None)
    add("TECH_VOLUME_DENOMINATOR_ZERO", "volume_zero_denominator", "volume_ratio5",
        [["set_bar", i, "volume", 0] for i in range(-6, -1)], None)
    add("AST_LOG_NONPOSITIVE", "log_invalid_input", "__LOG_OPERATOR__", [["set_bar", -1, "close", 0]], None)
    add("CROSS_EXACT_PRIOR_SESSION", "cross_section_exact_session_endpoint", "rps5_delta1", [],
        fixture["relative"]["field_series"]["rps5"][-1] - fixture["relative"]["field_series"]["rps5"][-2])
    add("CROSS_INTERMEDIATE_CONFIRMED_SUSPENSION", "cross_section_intermediate_suspension", "ret3",
        [["tail", 4], ["insert_state", 2, "CONFIRMED_SUSPENSION"]], bars[-1]["bar"]["close"] / bars[-3]["bar"]["close"] - 1)
    add("CROSS_INTERMEDIATE_GAP", "cross_section_intermediate_gap", "ret3",
        [["tail", 4], ["insert_state", 2, "UNEXPLAINED_GAP"]], None)
    add("REL_ENDPOINT_MISSING", "cross_section_endpoint_missing", "rel_market_1", [["set_scalar", "market_reference_return_1", None]], None)
    add("REL_INPUT_LOCAL_UNKNOWN", "unknown_node_propagation", "rel_market_1", [["set_scalar", "ret1", None]], None)
    add("RANK_STRICT_ORDER", "ranking_strict_order", "rps5", [["set_cross", "ret5", {"SEC-A": 2, "SEC-B": 1, "SEC-C": 3, "SEC-D": 4}]], 100 / 3)
    add("RANK_FULL_TIE", "ranking_full_tie", "rps5", [["set_cross", "ret5", {"SEC-A": 1, "SEC-B": 1, "SEC-C": 1, "SEC-D": 1}]], 50)
    add("RANK_PARTIAL_TIE", "ranking_partial_tie", "rps5", [["set_cross", "ret5", {"SEC-A": 2, "SEC-B": 1, "SEC-C": 2, "SEC-D": 3}]], 50)
    add("RANK_MISSING_MEMBER", "ranking_missing_member", "rps5", [["set_cross", "ret5", {"SEC-A": 2, "SEC-B": None, "SEC-C": 3, "SEC-D": 4}]], 0)
    add("RANK_TARGET_MISSING", "ranking_target_missing", "rps5", [["set_cross", "ret5", {"SEC-A": None, "SEC-B": 1, "SEC-C": 2, "SEC-D": 3}]], None)
    add("RANK_N_LT_2", "ranking_n_lt_2", "rps5", [["set_members", ["SEC-A"]], ["set_cross", "ret5", {"SEC-A": 1}]], None)
    add("RANK_MEMBER_CHANGED", "ranking_membership_change", "rps5", [["set_members", ["SEC-A", "SEC-B"]], ["set_cross", "ret5", {"SEC-A": 2, "SEC-B": 1}]], 100)
    add("RANK_REORDER_INVARIANT", "ranking_reorder_invariance", "rps5", [["set_members", ["SEC-D", "SEC-C", "SEC-B", "SEC-A"]], ["set_cross", "ret5", {"SEC-A": 2, "SEC-B": 1, "SEC-C": 3, "SEC-D": 4}]], 100 / 3)
    add("RANK_PARTIAL_EVALUABLE", "cross_section_partial_evaluable", "rps5", [["set_cross", "ret5", {"SEC-A": 1, "SEC-B": None, "SEC-C": None, "SEC-D": 2}]], 0)
    add("DELTA_PRIOR_ENDPOINT_MISSING", "cross_section_prior_endpoint_missing", "rps5_delta1", [["set_series", "rps5", [None]]], None)
    manifest = {"contract_id": "V4_03_AST_GOLDEN_CASES_R3", "version": "1.0.0",
                "governing_task": "docs/audits/V4_03_R3_EXTERNAL_BLOCKER_CLOSURE_TASK_20260928.md",
                "reference_method": "independent arithmetic from fixed fixture; no AST interpreter used to derive expected values",
                "cases": cases}
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    tmp = OUTPUT.with_suffix(OUTPUT.suffix + ".tmp")
    tmp.write_text(json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    os.replace(tmp, OUTPUT)
    print(len(cases))


if __name__ == "__main__":
    main()
