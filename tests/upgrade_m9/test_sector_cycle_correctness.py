import pandas as pd

from workbench_analysis.sector_cycle import build_sector_cycle_daily


def test_ma20_width_uses_adjusted_close_and_rs_does_not_fall_back_to_return():
    day = "2026-09-11"
    technical = pd.DataFrame([
        {"security_id": f"S{i}", "trade_date": day, "adj_close": close,
         "ma20": 10.0, "ret1": 0.01, "ret5": 0.2, "rs5": None}
        for i, close in enumerate((11.0, 12.0, 9.0, 10.0, None))
    ])
    members = pd.DataFrame([
        {"sector_id": "A", "security_id": f"S{i}", "trade_date": day}
        for i in range(5)
    ])
    row = build_sector_cycle_daily(technical, members).iloc[0]
    assert row["breadth_ma20"] == 0.5
    assert pd.isna(row["sector_rs5"])
