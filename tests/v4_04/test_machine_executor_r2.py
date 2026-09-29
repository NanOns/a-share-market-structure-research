import json
from pathlib import Path

from scripts.v4_04_machine_executor import OPERATORS, declared_operators, execute, execute_rule, rule_keys


ROOT = Path(__file__).resolve().parents[2]
RULES = json.loads((ROOT / "config/v4_04_algorithm_contracts_v2.json").read_text(encoding="utf-8"))["rules"]
PARAMETERS = {item["parameter_id"]: item["value"] for item in json.loads(
    (ROOT / "config/v4_04_parameter_set_v1.json").read_text(encoding="utf-8"))["parameters"]}


def test_declared_operator_and_rule_coverage():
    assert declared_operators(RULES) <= OPERATORS
    assert len(rule_keys(RULES)) == 18
    assert {"TREND_STATE_V1.daily", "TREND_STATE_V1.closed_period", "POSITION_STATE_V1.near_high",
            "POSITION_STATE_V1.drawdown", "MARKET_REGIME_V1.regime_ui",
            "V4_04_DERIVED_PRIMITIVES_V1.ma10"} <= rule_keys(RULES)


def test_operator_positive_negative_threshold_unknown_vectors():
    for operator, left, right, expected in (
        ("SUB", 3, 2, 1), ("EQ", 2, 2, True), ("GE", 2, 2, True),
        ("DIV", 4, 2, 2), ("MUL", 2, 3, 6), ("IN", "A", ["A", "B"], True)):
        node = {"operator": operator, "args": [{"constant": left}, {"constant": right}]}
        assert execute(node, {}, PARAMETERS) == expected
    assert execute({"operator": "DIV", "args": [{"constant": 3}, {"constant": 0}]}, {}, PARAMETERS) is None
    assert execute({"operator": "GT", "args": [{"field": "missing"}, {"constant": 0}]}, {}, PARAMETERS) is None
    assert execute({"operator": "NOT", "args": [{"constant": False}]}, {}, PARAMETERS) is True


def test_each_rule_has_executable_unknown_vector():
    for key in rule_keys(RULES):
        if key == "MARKET_REGIME_V1.regime_ui":
            result = execute_rule(RULES, key, {"path": [{}]}, PARAMETERS)
            assert result[0] == "UNKNOWN"
        else:
            result = execute_rule(RULES, key, {}, PARAMETERS)
            assert result is None or result == "UNKNOWN"


def test_closed_period_threshold_and_unknown():
    key = "TREND_STATE_V1.closed_period"
    base = {"period_view": "CLOSED_ONLY", "period_type": "weekly", "close": 3,
            "ma_current": 2, "ma_previous": 1}
    assert execute_rule(RULES, key, base, PARAMETERS) == "WEEKLY_UP"
    assert execute_rule(RULES, key, {**base, "close": 2}, PARAMETERS) == "WEEKLY_FLAT"
    assert execute_rule(RULES, key, {**base, "period_view": "ASOF_PARTIAL"}, PARAMETERS) == "UNKNOWN"
