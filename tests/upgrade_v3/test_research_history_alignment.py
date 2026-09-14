import json
from pathlib import Path

import pandas as pd

from workbench_service.research_builder import _common_member_ma20_delta, _exact_cycle_delta
from workbench_analysis.sector_cycle import CONTRACT_VERSION


CONFIG = json.loads((Path(__file__).parents[2] / "config/research_attention_v3.yaml").read_text(encoding="utf-8"))


def test_calendar_t_minus_three_is_not_third_available_materialization():
    cycle = pd.DataFrame([
        {"sector_id": "A", "sector_type": "INDUSTRY", "trade_date": pd.Timestamp(day).date(),
         "contract_id": CONTRACT_VERSION, "q5": q5}
        for day, q5 in (("2026-09-04", .1), ("2026-09-10", .5), ("2026-09-11", .8))
    ])
    result = _exact_cycle_delta(cycle, "2026-09-11", "2026-09-08", CONFIG)
    assert pd.isna(result.iloc[0].dq5_3)


def test_ma20_change_uses_same_valid_members_on_both_dates():
    current = pd.DataFrame({"sector_id": "A", "security_id": [f"S{i}" for i in range(6)]})
    prior = current.copy()
    technical = pd.DataFrame([
        {"security_id": f"S{i}", "date": day, "adj_close": close, "ma20": 10.0}
        for day, closes in (("2026-09-08", [9, 9, 9, 9, 9, 9]),
                            ("2026-09-11", [11, 11, 9, 9, 9, None]))
        for i, close in enumerate(closes)
    ])
    value = _common_member_ma20_delta(current, prior, technical, "2026-09-11", "2026-09-08", .7)
    assert value.iloc[0].ma20_delta3 == .4
