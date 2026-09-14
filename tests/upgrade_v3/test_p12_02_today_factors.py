from __future__ import annotations

import math

from workbench_analysis.today_research_factors_v3_3 import (
    calculate_today_facts,
    comparable_rps_delta,
)


def _bars(*, days: int = 22, close: float = 10.0) -> list[dict]:
    return [
        {"date": f"2026-01-{i + 1:02d}", "price_basis": "TDX_NATIVE_AFFINE_QFQ",
         "anchor_cutoff": f"2026-01-{days:02d}", "session_index": i,
         "has_actual_bar": True, "is_synthetic_fill": False,
         "open": close, "high": 11.0, "low": 9.0, "close": close,
         "raw_open": close, "raw_close": close,
         "amount": 100.0, "volume": 10.0}
        for i in range(days)
    ]


def test_platform_mean_median_and_ddof_are_distinct() -> None:
    bars = _bars()
    bars[-2]["amount"] = 300.0
    bars[-1].update(close=10.5, high=11.2, amount=220.0, raw_close=10.5)
    facts = calculate_today_facts(bars)
    assert facts["phc20"] == 10.0
    assert facts["phh20"] == 11.0
    assert math.isclose(facts["break_margin_close20"], 0.05)
    assert math.isclose(facts["break_margin_high20"], 10.5 / 11 - 1)
    assert facts["break_high20"] is False
    assert facts["intraday_reject_high20"] is True
    assert math.isclose(facts["amr20_mean_prior"], 2.0)
    assert math.isclose(facts["amr20_median_prior"], 2.2)
    assert facts["sigma20_v3"] < facts["vol20_sample"]
    assert facts["liq20"] is False
    assert facts["ret20_adj"] is not None


def test_known_absolute_drop_survives_unknown_prior_sigma() -> None:
    bars = _bars(days=21)
    bars[-1].update(close=9.0, raw_close=9.0)
    facts = calculate_today_facts(bars)
    assert facts["sigma20_prior"] is None
    assert facts["relative_severe_drop"] is None
    assert facts["absolute_severe_drop"] is True
    assert facts["severe_drop"] is True


def test_missing_session_is_not_compressed_and_price_basis_fails_closed() -> None:
    bars = _bars()
    bars[-5]["has_actual_bar"] = False
    facts = calculate_today_facts(bars)
    assert facts["phc20"] is None
    assert facts["amr20_mean_prior"] is None
    assert facts["quality"] == "PARTIAL"
    bars[-1]["price_basis"] = "RAW"
    try:
        calculate_today_facts(bars)
    except ValueError as exc:
        assert str(exc) == "MIXED_PRICE_BASIS"
    else:
        raise AssertionError("mixed basis was accepted")


def test_rps_cross_section_gate() -> None:
    before = {str(i) for i in range(100)}
    stable = {str(i) for i in range(1, 101)}
    result = comparable_rps_delta(0.8, 0.7, stable, before)
    assert result["delta"] is None
    assert math.isclose(result["diagnostic_delta"], 0.1)
    result = comparable_rps_delta(0.8, 0.7, stable, before,
                                  today_basis="PIT_ASOF", prior_basis="PIT_ASOF")
    assert math.isclose(result["delta"], 0.1)
    assert result["comparable"] is True
    assert result["formal_comparable"] is True
    replaced = {str(i) for i in range(50, 150)}
    result = comparable_rps_delta(0.8, 0.7, replaced, before)
    assert result["delta"] is None
    assert result["comparable"] is False


def test_prior_sigma_floor_and_flat_bar_are_explicit() -> None:
    bars = _bars()
    bars[-1].update(open=9.5, high=9.5, low=9.5, close=9.5,
                    raw_open=9.5, raw_close=9.5)
    facts = calculate_today_facts(bars)
    assert facts["sigma20_prior"] == 0
    assert facts["absolute_severe_drop"] is False
    assert facts["relative_severe_drop"] is True
    assert facts["severe_drop"] is True
    assert facts["clv"] is None
    assert facts["weak_close"] is None


def test_return_window_requires_every_master_session() -> None:
    bars = _bars()
    bars[-3]["has_actual_bar"] = False
    facts = calculate_today_facts(bars)
    assert facts["ret3_adj"] is None
    assert facts["accel_log5_20"] is None


def test_legacy_pullback_amount_diagnostic_is_separate_from_prior_gate() -> None:
    bars = _bars()
    bars[-3]["amount"] = 60.0
    bars[-2]["amount"] = 60.0
    bars[-1]["amount"] = 120.0
    facts = calculate_today_facts(bars, liquidity20_amount_gte=90)
    assert facts["liq20"] is True
    assert facts["amr20_mean_prior"] != facts["pb_amr3_5_diagnostic"]
    assert math.isclose(facts["pb_amr3_5_diagnostic"], 0.8)


def test_factor_anchor_and_calendar_gap_are_rejected() -> None:
    bars = _bars()
    bars[4]["anchor_cutoff"] = "2026-01-04"
    try:
        calculate_today_facts(bars)
    except ValueError as exc:
        assert str(exc) == "FACTOR_PRICE_ANCHOR_MISMATCH"
    else:
        raise AssertionError("mixed price anchor was accepted")
    bars = _bars()
    bars[4]["session_index"] = 9
    try:
        calculate_today_facts(bars)
    except ValueError as exc:
        assert str(exc) == "FACTOR_MASTER_SESSION_GAP"
    else:
        raise AssertionError("compressed master session was accepted")
