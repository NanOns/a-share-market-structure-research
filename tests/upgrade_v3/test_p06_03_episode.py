import json
from pathlib import Path

import pandas as pd

from workbench_analysis.sector_attention import progress_potential_episode


ROOT = Path(__file__).parents[2]
CONFIG = json.loads((ROOT / "config/research_attention_v3.yaml").read_text(encoding="utf-8"))


def _rows(values, **common):
    result = []
    for index, value in enumerate(values, start=1):
        result.append({"trade_date": f"2026-09-{index:02d}", "potential_eligible": value, "current": False, "weak": False, "ma20_width": .5, "extended_share": 0, "risk_coverage": .8, **common})
    return pd.DataFrame(result)


def test_episode_first_signal_is_not_backwritten_and_confirms_current():
    output = progress_potential_episode(_rows([True, True, True, True, True, True], current=False), CONFIG)
    assert output.iloc[0]["state"] == "QUALIFIED"
    assert output.iloc[0]["first_seen_date"] == "2026-09-01"
    assert output.iloc[1]["first_seen_date"] == "2026-09-01"
    source = _rows([True, True], current=False)
    source.loc[1, "current"] = True
    confirmed = progress_potential_episode(source, CONFIG)
    assert confirmed.iloc[1]["state"] == "CONFIRMED"
    assert confirmed.iloc[1]["end_reason"] == "CURRENT_CONFIRMED"


def test_episode_has_one_monitoring_day_then_condition_lost_and_requires_two_day_reset():
    output = progress_potential_episode(_rows([True, False, False, True, False, False, True]), CONFIG)
    assert list(output["state"][:3]) == ["QUALIFIED", "MONITORING", "CONDITION_LOST"]
    assert output.iloc[3]["state"] == "NO_EPISODE"
    assert output.iloc[6]["state"] == "QUALIFIED"
    assert output.iloc[6]["episode_no"] == 2


def test_data_gap_advances_age_without_becoming_failure_and_hard_invalidation_wins():
    gap = progress_potential_episode(_rows([True, None, None, True]), CONFIG)
    assert list(gap["state"]) == ["QUALIFIED", "DATA_GAP", "DATA_GAP", "QUALIFIED"]
    invalid = progress_potential_episode(_rows([True, True], weak=False, ma20_width=.2), CONFIG)
    assert invalid.iloc[1]["state"] == "INVALIDATED"
    assert invalid.iloc[1]["end_reason"] == "MA20_WIDTH_BELOW_035"


def test_ten_session_sequence_expires_on_fifth_qualified_age_without_resetting():
    output = progress_potential_episode(_rows([True, True, True, True, False, False, False, False, False, False]), CONFIG)
    assert len(output) == 10
    assert output.iloc[4]["state"] == "EXPIRED"
    assert output.iloc[4]["age_sessions"] == 5
    assert output.iloc[4]["end_reason"] == "MAX_AGE_5"
