import pandas as pd

from workbench_analysis.stock_attention import signal_distribution


def test_distribution_separates_true_false_unknown_and_explains_each():
    frame = pd.DataFrame([
        {"security_id": "A", "breakout": True, "setup": False, "recovery": None, "trend_background": False, "structure_break": False,
         "checks": {"BREAKOUT": {"LIQUIDITY": True}, "SETUP": {"LIQUIDITY": False}, "RECOVERY": {"AMOUNT_EXPANSION": None}, "TREND_BACKGROUND": {}, "STRUCTURE_BREAK": {}}},
        {"security_id": "B", "breakout": False, "setup": False, "recovery": None, "trend_background": False, "structure_break": False,
         "checks": {"BREAKOUT": {"NEW_HIGH20": False}, "SETUP": {"RPS5_IMPROVING": False}, "RECOVERY": {"RPS5_IMPROVING": None}, "TREND_BACKGROUND": {}, "STRUCTURE_BREAK": {}}},
    ])
    result = signal_distribution(frame)
    assert result["BREAKOUT"]["true_count"] == 1
    assert result["BREAKOUT"]["false_count"] == 1
    assert result["RECOVERY"]["unknown_count"] == 2
    assert result["BREAKOUT"]["top_rejection_codes"][0] == {"code": "NEW_HIGH20", "count": 1}
    assert result["RECOVERY"]["top_missing_codes"] == [
        {"code": "AMOUNT_EXPANSION", "count": 1},
        {"code": "RPS5_IMPROVING", "count": 1},
    ]
    assert set(result["BREAKOUT"]["examples"]) == {"true", "false", "unknown"}
