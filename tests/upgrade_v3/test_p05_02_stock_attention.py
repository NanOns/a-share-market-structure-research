import json
from pathlib import Path

import pytest

from workbench_analysis.stock_attention import PREDICATE_CONTRACT, classify_stock_attention


ROOT = Path(__file__).parents[2]
CONFIG = json.loads((ROOT / "config/research_attention_v3.yaml").read_text(encoding="utf-8"))


def base(**updates):
    row = {
        "security_id": "A", "trade_date": "2026-09-10",
        "close": 10.0, "close_prior1": 9.9,
        "ma5": 9.95, "ma5_prior1": 10.0,
        "ma20": 10.0, "ma20_prior1": 10.0, "ma20_prior3": 9.95, "ma20_prior5": 9.9,
        "bias20": 0.0, "extension_z20": 0.0,
        "dist_high20": -0.03, "range5": .02, "range20": .10,
        "amount_vs_prior20": 1.1, "liquidity20": True,
        "rps5_delta3": .08, "rps20": .8,
    }
    row.update(updates)
    return row


def test_setup_accepts_micro_decline_and_all_predicates_are_explained():
    result = classify_stock_attention(base(ret1=-.001), CONFIG)
    assert result["setup"] is True
    assert "SETUP" in result["reason_codes"]
    assert set(result["checks"]["SETUP"]) == {"LIQUIDITY", "CLOSE_TO_MA20", "MA20_NONDECLINING_3", "NEAR_PRIOR_HIGH20", "RANGE_CONTRACTION", "RPS5_IMPROVING", "NOT_EXTENDED"}
    assert PREDICATE_CONTRACT["SETUP"]["liquidity20"] == "SETUP.requires_liquidity"


def test_liquidity_is_required_for_setup_and_recovery():
    result = classify_stock_attention(base(liquidity20=False), CONFIG)
    assert result["setup"] is False
    assert result["recovery"] is False
    unknown = classify_stock_attention(base(liquidity20=None), CONFIG)
    assert unknown["setup"] is None
    assert unknown["recovery"] is None


def test_breakout_boundary_and_new_high_not_automatically_extended():
    threshold = CONFIG["thresholds"]["stock_signals"]["BREAKOUT"]["amount_vs_prior20_gte"]
    exact = classify_stock_attention(base(dist_high20=.001, amount_vs_prior20=threshold), CONFIG)
    assert exact["breakout"] is True
    assert exact["extended"] is False
    below = classify_stock_attention(base(dist_high20=.001, amount_vs_prior20=threshold - 1e-12), CONFIG)
    assert below["breakout"] is False
    missing = classify_stock_attention(base(dist_high20=.001, amount_vs_prior20=None), CONFIG)
    assert missing["breakout"] is None


def test_extended_rejects_research_but_not_trend_fact():
    result = classify_stock_attention(base(dist_high20=.02, amount_vs_prior20=1.3, bias20=.20, extension_z20=1.8), CONFIG)
    assert result["extended"] is True
    assert result["breakout"] is False
    assert result["focus_trigger"] is False
    assert result["trend_background"] is True


def test_recovery_and_two_session_structure_break_are_strict():
    recovery = classify_stock_attention(base(), CONFIG)
    assert recovery["recovery"] is True
    one_day = classify_stock_attention(base(close=9.7, ma20=10.0, close_prior1=9.9, ma20_prior1=10.0), CONFIG)
    assert one_day["structure_break"] is False
    two_days = classify_stock_attention(base(close=9.7, ma20=10.0, close_prior1=9.7, ma20_prior1=10.0), CONFIG)
    assert two_days["structure_break"] is True


def test_trend_background_does_not_create_focus_and_null_is_unknown():
    trend = classify_stock_attention(base(dist_high20=-.2, rps5_delta3=-.1), CONFIG)
    assert trend["trend_background"] is True
    assert trend["focus_trigger"] is False
    partial = classify_stock_attention(base(ma20=None), CONFIG)
    assert partial["setup"] is None
    assert partial["quality"] == "PARTIAL"
