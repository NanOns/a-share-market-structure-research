from datetime import date, timedelta
import json
from pathlib import Path

import pytest

from scripts.v4_04_machine_executor_r4 import execute_rule
from scripts.v4_04_machine_vectors_r4 import run as run_vectors
from src.v4.profile_core import compression, drawdown, participation, relative, severe_extension, State, trend
from src.v4.profile_primitives import derive_daily


ROOT = Path(__file__).resolve().parents[2]
RULES = json.loads((ROOT / "config/v4_04_algorithm_contracts_v3.json").read_text(encoding="utf-8"))["rules"]
PARAMETERS = {item["parameter_id"]: item["value"] for item in json.loads(
    (ROOT / "config/v4_04_parameter_set_v1.json").read_text(encoding="utf-8"))["parameters"]}


@pytest.mark.parametrize("amount,expected", [(20_000_000.0, True), (19_000_000.0, False)])
def test_liquidity_is_independent_of_unknown_amount_ratio(amount, expected):
    calendar = [(date(2026, 1, 1) + timedelta(days=i)).isoformat() for i in range(21)]
    bars = [dict(trade_date=day, qfq_close=10.0, qfq_high=11.0, qfq_low=9.0,
                 adjusted_quality="READY", amount=amount) for day in calendar]
    statuses = [(day, "ACTUAL_TRADED") for day in calendar]
    fields = {"amount_ratio20": {"value": None, "quality_state": "UNKNOWN"}}
    liquid = derive_daily(bars, fields, statuses, calendar[-1], calendar)["minimum_liquidity"]
    assert liquid.quality == "OBSERVED" and liquid.value is expected
    inputs = dict(range_ratio=.5, atr_ratio=.8, vol_ratio=.8,
                  amount_ratio20=None, minimum_liquidity=liquid.value)
    assert compression(inputs).value == "UNKNOWN"
    broken = [(day, "UNKNOWN" if day == calendar[9] else status) for day, status in statuses]
    assert derive_daily(bars, fields, broken, calendar[-1], calendar)["minimum_liquidity"].quality == "UNKNOWN"


def test_machine_enum_unknown_matches_production():
    base = dict(rps5=50, rps20=50, rps20_delta3=10, rel_market_1=0, rel_market_5=0)
    for comp, ma in (("UNKNOWN", "MIXED"), ("NORMAL", "UNKNOWN")):
        assert relative(base, comp, ma).value == "UNKNOWN"
        assert execute_rule(RULES, "RELATIVE_STATE_V1", {**base, "compression_state": comp,
                           "ma_structure_state": ma}, PARAMETERS) == "UNKNOWN"
    risk = State("UNKNOWN", "EXTENSION_RISK_V1", {}, "REQUIRED_INPUT_UNKNOWN")
    assert severe_extension(risk).value is None
    assert execute_rule(RULES, "EXTENSION_RISK_V1.severe",
                        {"core_extension_risk": "UNKNOWN"}, PARAMETERS) is None
    inputs = dict(amount_ratio20=1.2, ret1=.01, clv=None)
    assert participation(inputs).value == "UNKNOWN"
    assert execute_rule(RULES, "AMOUNT_VOLUME_STATE_V1.participation",
                        {**inputs, "clv": "UNKNOWN"}, PARAMETERS) == "UNKNOWN"
    trend_inputs = dict(close=110, ma20=100, ma60=95, slope20=.2, slope60=.2,
                        hh_progress=True, ll_progress=False, core_price_damage="UNKNOWN", atr20=2)
    assert trend(trend_inputs).value == "UNKNOWN"
    assert execute_rule(RULES, "TREND_STATE_V1.daily", trend_inputs, PARAMETERS) == "UNKNOWN"


@pytest.mark.parametrize("horizon", [20, 60])
@pytest.mark.parametrize("close,expected", [(9.51, "SHALLOW"), (9.5, "SHALLOW"),
                                             (9.49, "MODERATE"), (8.51, "MODERATE"),
                                             (8.5, "MODERATE"), (8.49, "DEEP")])
def test_inclusive_drawdown_boundaries_match_machine_and_production(horizon, close, expected):
    assert drawdown({"close": close, f"hhv{horizon}": 10}, horizon).value == expected
    assert execute_rule(RULES, "POSITION_STATE_V1.drawdown", {"close": close, "hhvN": 10}, PARAMETERS) == expected


def test_semantic_vector_coverage():
    receipt = run_vectors(write_receipt=False)
    assert receipt["status"] == receipt["semantic_categories_status"] == "PASS"
    assert receipt["rules_missing_vector_coverage"] == []
    assert all(receipt[name] > 0 for name in (
        "branch_specific_unknown_vectors", "enum_unknown_vectors",
        "stateful_hysteresis_vectors", "inclusive_boundary_vectors"))
