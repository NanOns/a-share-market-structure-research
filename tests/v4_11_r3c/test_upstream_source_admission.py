"""Independent arithmetic/time/source probes; fixtures are engineering only."""
from copy import deepcopy
from decimal import Decimal
import json
from pathlib import Path
from statistics import fmean

import pytest

from src.v4.confirmation_d2_upstream_r3 import derive

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def calculation():
    head = json.loads((ROOT / "data/v4/V4_DATA_ACCEPTED_HEAD.json").read_bytes())
    calendar = json.loads((ROOT / head["calendar"]["path"]).read_bytes())["session_dates"]
    dates = calendar[calendar.index("2026-09-30")-26:calendar.index("2026-09-30")+1]
    slots = []
    for index, day in enumerate(dates):
        close = 10.0 + .05 * index
        slots.append(dict(date=day, has_actual_bar=True, raw_actual_bar=True,
            open=close-.03, high=close+.20, low=close-.20, close=close,
            amount=30_000_000.0+index*100_000, volume=3_000_000.0+index*10_000,
            mul="1", add="0"))
    return dict(security_id="fixture-upstream-entity", trade_date=dates[-1], window=slots,
        values={"rps5_delta3": .01}, scope="ENGINEERING_FIXTURE_NOT_MARKET_ACCEPTANCE")


@pytest.mark.parametrize("multipliers,additions", [
    ((1, "1.0000", Decimal("1E+0")), (0, "0.000", "0E-15")),
    (("1.2500", "1.25", Decimal("1.250E+0")), ("-2.5000", "-2.50", -2.5)),
])
def test_numerically_equal_coordinates_do_not_make_a_mixed_adjustment_window(calculation, multipliers, additions):
    variant = deepcopy(calculation)
    for index,row in enumerate(variant["window"]):
        row["mul"] = multipliers[index % len(multipliers)]
        row["add"] = additions[index % len(additions)]
    _, evidence = derive(variant, ROOT)
    ma20 = evidence["core_factors"]["ma20"]
    assert ma20["value"] == pytest.approx(fmean(r["close"] for r in variant["window"][-20:]))
    assert ma20["unknown_reason"] is None
    assert evidence["seed_facts"]["ma20_t_minus_1"]["value"] == pytest.approx(fmean(r["close"] for r in variant["window"][-21:-1]))


def test_signed_zero_is_numerically_the_same_additive_coordinate(calculation):
    for index,row in enumerate(calculation["window"]):
        row["add"] = "-0.0000" if index % 2 else "0.000"
    _, evidence = derive(calculation, ROOT)
    assert evidence["core_factors"]["ma20"]["unknown_reason"] is None
    assert evidence["core_factors"]["ma20"]["value"] == pytest.approx(fmean(r["close"] for r in calculation["window"][-20:]))


def test_distinct_high_precision_coordinates_must_not_be_rounded_into_one_identity(calculation):
    # Both have more than the default Decimal context's 28 significant digits;
    # they are distinct source coordinates even if binary-float prices coincide.
    left = "1.00000000000000000000000000001"
    right = "1.00000000000000000000000000002"
    assert Decimal(left) != Decimal(right)
    for index,row in enumerate(calculation["window"]):
        row["mul"] = left if index % 2 else right
    _, evidence = derive(calculation, ROOT)
    assert evidence["core_factors"]["ma20"]["value"] is None
    assert evidence["core_factors"]["ma20"]["unknown_reason"] == "MIXED_ADJUSTMENT_IDENTITY"


@pytest.mark.parametrize("accepted_status,expected_state,ma20_known", [
    ("SUSPENDED", "CONFIRMED_SUSPENSION", True),
    (None, "UNKNOWN", False),
    ("UNKNOWN", "UNKNOWN", False),
    ("MISSING", "UNKNOWN", False),
])
def test_only_explicit_accepted_suspension_can_bridge_an_actual_bar_window(calculation, accepted_status, expected_state, ma20_known):
    slot = calculation["window"][-8]
    slot.update(has_actual_bar=False, raw_actual_bar=False)
    key = (calculation["security_id"], slot["date"])
    states = {} if accepted_status is None else {key: accepted_status}
    _, evidence = derive(calculation, ROOT, states)
    state = next(r for r in evidence["observation_states"] if r["trade_date"] == slot["date"])
    assert state["state"] == expected_state
    assert state["accepted_trading_status"] == accepted_status
    ma20 = evidence["core_factors"]["ma20"]
    if ma20_known:
        actual = [r for r in calculation["window"] if r["has_actual_bar"]][-20:]
        assert ma20["value"] == pytest.approx(fmean(r["close"] for r in actual))
        assert ma20["actual_count"] == 20 and ma20["suspended_count"] == 1
        assert ma20["calendar_span"] == 21
    else:
        assert ma20["value"] is None and ma20["unknown_reason"] == "UNEXPLAINED_DATA_GAP"


def test_raw_bar_with_unavailable_adjustment_is_not_reclassified_as_suspension(calculation):
    slot = calculation["window"][-8]
    slot.update(has_actual_bar=False, raw_actual_bar=True)
    _, evidence = derive(calculation, ROOT, {(calculation["security_id"], slot["date"]): "SUSPENDED"})
    state = next(r for r in evidence["observation_states"] if r["trade_date"] == slot["date"])
    assert state["state"] == "ADJUSTMENT_UNKNOWN"
    assert evidence["core_factors"]["ma20"]["value"] is None
    assert evidence["core_factors"]["ma20"]["unknown_reason"] == "ADJUSTMENT_UNKNOWN"


def test_prior_close_and_ma20_exclude_the_target_session(calculation):
    expected_close = calculation["window"][-2]["close"]
    expected_ma20 = fmean(r["close"] for r in calculation["window"][-21:-1])
    _, baseline = derive(calculation, ROOT)
    changed = deepcopy(calculation)
    changed["window"][-1].update(open=1_000.0, high=1_001.0, low=999.0, close=1_000.0,
        amount=8_000_000_000.0, volume=800_000_000.0)
    _, perturbed = derive(changed, ROOT)
    for evidence in (baseline, perturbed):
        assert evidence["seed_facts"]["close_t_minus_1"]["value"] == expected_close
        assert evidence["seed_facts"]["ma20_t_minus_1"]["value"] == pytest.approx(expected_ma20)
    assert perturbed["core_factors"]["ma20"]["value"] != baseline["core_factors"]["ma20"]["value"]
    assert perturbed["core_factors"]["ma20"]["window_end_trade_date"] == calculation["trade_date"]


def test_immediate_prior_session_gap_is_not_replaced_by_last_observed_close(calculation):
    prior = calculation["window"][-2]
    prior.update(has_actual_bar=False, raw_actual_bar=False)
    _, evidence = derive(calculation, ROOT, {(calculation["security_id"], prior["date"]): "SUSPENDED"})
    assert evidence["seed_facts"]["close_t_minus_1"]["value"] is None
    assert evidence["seed_facts"]["ma20_t_minus_1"]["value"] is not None
