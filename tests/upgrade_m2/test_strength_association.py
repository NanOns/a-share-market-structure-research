from workbench_service.strength_association import (
    CONTRACT_VERSION,
    choose_association,
    semantic_bucket,
)


def sector(name="种业", sector_id="THEME:1", sector_type="THEME", pattern="CURRENT_STRENGTH", rs5=.9, rs20=.9):
    return {
        "sector_id": sector_id,
        "sector_name": name,
        "sector_type": sector_type,
        "sector_role": sector_type,
        "sector_valid": True,
        "coverage": .9,
        "primary_pattern": pattern,
        "sector_rs5_pct": rs5,
        "sector_rs20_pct": rs20,
    }


def members(target="SH.600001", target_ret=.30, others=(.05, .06, .07, .08, .09, .10)):
    rows = [{"security_id": target, "RET5": .08, "RET20": target_ret}]
    rows += [{"security_id": f"SH.6000{i+10}", "RET5": value / 2, "RET20": value} for i, value in enumerate(others)]
    return rows


def test_price_behavior_is_tag_and_never_primary():
    relations = [
        (sector("近期强势", "STYLE:1", "STYLE", rs5=1, rs20=1), members()),
        (sector("种业", "THEME:1", "THEME", rs5=.8, rs20=.8), members()),
    ]
    result = choose_association("SH.600001", relations)
    assert semantic_bucket(relations[0][0]) == "PRICE_BEHAVIOR_TAG"
    assert result["strength_sector_name"] == "种业"
    assert result["market_tags"] == ["近期强势"]


def test_first_board_multi_board_and_sentiment_names_are_price_tags():
    for name in ("昨日首板", "最近多板", "最近情绪"):
        assert semantic_bucket(sector(name, sector_type="STYLE")) == "PRICE_BEHAVIOR_TAG"


def test_stronger_concept_can_beat_industry_without_fixed_type_priority():
    relations = [
        (sector("农业", "INDUSTRY:1", "INDUSTRY", rs5=.75, rs20=.8), members()),
        (sector("转基因", "THEME:2", "THEME", rs5=.95, rs20=.9), members()),
    ]
    assert choose_association("SH.600001", relations)["strength_sector_name"] == "转基因"


def test_leave_one_out_rejects_self_reinforced_sector_and_does_not_fallback_to_tag():
    weak_others = (-.08, -.06, -.04, -.03, -.02, -.01)
    result = choose_association("SH.600001", [
        (sector("农业"), members(target_ret=.80, others=weak_others)),
        (sector("近期强势", "STYLE:1", "STYLE"), members()),
    ])
    assert result["strength_sector_name"] is None
    assert result["strength_sector_reason"] == "暂无可确认的强势关联板块"
    assert result["market_tags"] == ["近期强势"]
    assert result["strength_association_contract"] == CONTRACT_VERSION


def test_selection_is_deterministic_and_limits_alternatives():
    relations = [(sector(f"概念{i}", f"THEME:{i}", rs5=.9-i*.01), members()) for i in range(5)]
    first = choose_association("SH.600001", relations)
    second = choose_association("SH.600001", list(reversed(relations)))
    assert first == second
    assert len(first["other_strength_sectors"]) == 2
