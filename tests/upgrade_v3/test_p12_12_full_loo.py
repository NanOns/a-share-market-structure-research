import pandas as pd

from workbench_analysis.full_loo_v3_3 import recompute_full_current_loo


def config():
    return {"thresholds": {"coverage": {"min_sector_members": 5, "min_member_quote_coverage": .7, "min_full_market_quote_coverage": .9, "min_sector_cross_section_coverage": .7}, "current": {"allowed_sector_types": ["INDUSTRY"], "m1_gt": 0, "b1_gte": .6, "rel1_gte": .003, "p1_gte": .8, "min_positive_count": 3, "top1_positive_share_lte": .5, "weak_m1_lt": 0, "weak_b1_lt": .35, "weak_b_delta3_lte": -.2}}}


def frames():
    day = "2026-09-15"
    market = pd.DataFrame([{"security_id": f"S{i}", "trade_date": day, "ret1": value} for i, value in enumerate([.01, .02, .03, .04, .05, .06, -.01, -.02])])
    rows = []
    for sector, ids in {"A": range(0, 6), "B": range(1, 7), "C": range(2, 8), "D": range(0, 7), "E": range(1, 8)}.items():
        for i in ids:
            rows.append({"sector_id": sector, "sector_name": sector, "sector_type": "INDUSTRY", "sector_role": "INDUSTRY", "security_id": f"S{i}", "trade_date": day, "ret1": market.iloc[i].ret1})
    return pd.DataFrame(rows), market


def test_full_loo_removes_target_globally_and_recomputes_cross_section():
    members, market = frames()
    result = recompute_full_current_loo(["S0"], members, market, config())["S0"]
    assert result["full_track_recomputed_without_target"] is True
    assert result["target_removed_from_market_reference"] is True
    assert result["same_type_cross_section_and_p1_recomputed"] is True
    assert result["tested_relations"] == 2
    assert all(row["member_count"] == 5 if row["sector_id"] == "A" else row["member_count"] == 6 for row in result["relations"])


def test_target_with_no_relationship_is_known_false():
    members, market = frames()
    result = recompute_full_current_loo(["OUTSIDE"], members, market, config())["OUTSIDE"]
    assert result["support"] is False and result["tested_relations"] == 0
