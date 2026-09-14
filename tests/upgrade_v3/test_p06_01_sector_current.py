import json
from pathlib import Path

import pandas as pd

from workbench_analysis.sector_attention import aggregate_early_width, build_sector_current, build_sector_potential


ROOT = Path(__file__).parents[2]
CONFIG = json.loads((ROOT / "config/research_attention_v3.yaml").read_text(encoding="utf-8"))


def _input():
    rows, market = [], []
    # Five normal same-type sectors provide the required p1 rank universe.
    values = {"A": .04, "B": .03, "C": .02, "D": .01, "E": -.01}
    for sector, ret in values.items():
        for number in range(5):
            security = f"{sector}{number}"
            rows.append({"sector_id": sector, "sector_name": sector, "sector_type": "INDUSTRY", "security_id": security, "trade_date": "2026-09-10", "ret1": ret})
            market.append({"security_id": security, "trade_date": "2026-09-10", "ret1": 0.0})
    return pd.DataFrame(rows), pd.DataFrame(market)


def test_current_is_same_type_relative_member_quote_fact_not_long_term_rank():
    members, market = _input()
    output = build_sector_current(members, market, CONFIG)
    by_id = output.set_index("sector_id")
    assert bool(by_id.loc["A", "current"]) is True
    assert by_id.loc["A", "p1"] == 1.0
    # A high historical rank has no path into CURRENT; today's negative m1 fails.
    assert bool(by_id.loc["E", "current"]) is False
    assert "M1_POSITIVE" in by_id.loc["E", "reason_codes"]


def test_current_excludes_style_sectors_even_when_their_numbers_pass():
    members, market = _input()
    members["sector_type"] = "STYLE"
    output = build_sector_current(members, market, CONFIG).set_index("sector_id")
    assert bool(output.loc["A", "current"]) is False
    assert output.loc["A", "checks"]["CURRENT"]["ALLOWED_SECTOR_TYPE"] is False
    assert "ALLOWED_SECTOR_TYPE" in output.loc["A", "reason_codes"]


def test_concentration_and_downward_breadth_are_not_waived_by_amount_or_rank():
    members, market = _input()
    members.loc[(members.sector_id == "A") & (members.security_id == "A0"), "ret1"] = .50
    members.loc[(members.sector_id == "A") & (members.security_id != "A0"), "ret1"] = .001
    output = build_sector_current(members, market, CONFIG).set_index("sector_id")
    assert bool(output.loc["A", "current"]) is False
    assert "NOT_SINGLE_STOCK_DRIVEN" in output.loc["A", "reason_codes"]
    assert bool(output.loc["E", "weak"]) is True


def test_weak_second_branch_uses_bound_common_member_breadth_delta():
    members, market = _input()
    comparison = pd.DataFrame([
        {"sector_id": sector, "trade_date": "2026-09-10", "b_delta3": (-.21 if sector == "E" else 0.0)}
        for sector in ("A", "B", "C", "D", "E")
    ])
    output = build_sector_current(members, market, CONFIG, comparison_features=comparison).set_index("sector_id")
    assert output.loc["E", "checks"]["W"]["NEGATIVE_BREADTH_DELTA3"] is True
    assert bool(output.loc["E", "weak"]) is True


def test_weak_second_branch_uses_bound_common_member_breadth_delta():
    members, market = _input()
    members.loc[members.sector_id == "D", "ret1"] = -.001
    comparison = pd.DataFrame([
        {"sector_id": sector, "trade_date": "2026-09-10", "b_delta3": (-.20 if sector == "D" else 0.0)}
        for sector in ("A", "B", "C", "D", "E")
    ])
    output = build_sector_current(members, market, CONFIG, comparison_features=comparison).set_index("sector_id")
    assert bool(output.loc["D", "weak"]) is True
    assert output.loc["D", "checks"]["W"]["NEGATIVE_BREADTH_DELTA3"] is True


def test_market_coverage_failure_is_unknown_not_a_silent_pass():
    members, market = _input()
    market.loc[market.index[:10], "ret1"] = None
    output = build_sector_current(members, market, CONFIG)
    assert output["current"].isna().all()
    assert all("UNKNOWN_MARKET_COVERAGE" in value for value in output["reason_codes"])


def test_potential_breadth_uses_full_member_signals_and_is_mutually_exclusive_with_current():
    signals = pd.DataFrame([
        {"sector_id": "A", "security_id": str(index), "setup": index < 2, "recovery": False, "extended": False, "close": 10, "ma20": 10}
        for index in range(5)
    ])
    early = aggregate_early_width(signals).iloc[0].to_dict()
    assert early["early_width"] == .4
    features = pd.DataFrame([{**early, "current": False, "weak": False, "normal_rank_eligible": True,
        "total_member_count": 5, "m1": 0, "ma20_width": .5, "extended_share": 0, "risk_evaluable_count": 5,
        "dq5_3": .11, "b_delta3": .11, "ma20_delta3": .06, "amount_A": 1.06, "q20": .1,
        "rel1": 0, "prior_current_within10": False}])
    output = build_sector_potential(features, CONFIG).iloc[0]
    assert bool(output["potential_eligible"]) is True
    assert output["primary_branch"] == "BREADTH_BUILD"
    output = build_sector_potential(features.assign(current=True), CONFIG).iloc[0]
    assert bool(output["potential_eligible"]) is False


def test_potential_missing_risk_or_common_history_is_unknown_not_false():
    features = pd.DataFrame([{"sector_id": "A", "current": False, "weak": False, "normal_rank_eligible": True,
        "total_member_count": 5, "m1": 0, "ma20_width": .5, "extended_share": None, "risk_evaluable_count": 0,
        "dq5_3": .11, "b_delta3": .11, "ma20_delta3": .06, "early_width": .2, "early_count": 2,
        "amount_A": 1.06, "q20": .5, "setup_count": 2, "setup_evaluable_count": 5,
        "rel1": .01, "prior_current_within10": None}])
    output = build_sector_potential(features, CONFIG).iloc[0]
    assert output["potential_eligible"] is None
