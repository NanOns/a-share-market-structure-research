from workbench_service.association import CONTRACT_ID, evaluate_relation, rank_associations


def sector(sector_id="THEME:1", name="种业", pattern="CURRENT_STRENGTH", rs5=0.90, rs20=0.88, bucket=None):
    return {
        "sector_id": sector_id,
        "sector_name": name,
        "sector_type": "THEME",
        "sector_role": "THEME",
        "sector_valid": True,
        "coverage": 0.90,
        "primary_pattern": pattern,
        "semantic_bucket": bucket,
        "sector_rs5_pct": rs5,
        "sector_rs20_pct": rs20,
    }


def members(target_ret=0.30, others=(0.05, 0.06, 0.07, 0.08, 0.09, 0.10), target="SH.600001"):
    rows = [{"security_id": target, "member_rank": 1, "rank_valid_count": 7, "ret5": 0.08, "ret20": target_ret}]
    rows.extend(
        {"security_id": f"SH.6000{index + 10}", "member_rank": index + 2, "rank_valid_count": 7, "ret5": value / 2, "ret20": value}
        for index, value in enumerate(others)
    )
    return rows


def test_leave_one_out_rejects_target_self_reinforcement_with_reason():
    result = evaluate_relation(sector(), "SH.600001", members(target_ret=0.80, others=(-.08, -.06, -.04, -.03, -.02, -.01)))

    assert result["eligible"] is False
    assert "LEAVE_ONE_OUT_RET20_MEDIAN_NOT_POSITIVE" in result["rejection_reasons"]
    assert "LEAVE_ONE_OUT_BREADTH20_LT_0_60" in result["rejection_reasons"]
    assert result["evidence"]["contract_id"] == CONTRACT_ID


def test_valid_relation_is_ranked_and_limited_to_primary_plus_two_alternatives():
    rows = []
    for index in range(4):
        item = evaluate_relation(
            sector(sector_id=f"THEME:{index}", name=f"概念{index}", rs5=0.90 - index * 0.01),
            "SH.600001",
            members(),
        )
        rows.append(item)

    ranked = rank_associations(rows)
    assert [row["association_rank"] for row in ranked] == [1, 2, 3, None]
    assert [row["sector_id"] for row in ranked[:3]] == ["THEME:0", "THEME:1", "THEME:2"]


def test_non_normal_semantic_bucket_is_rejected_and_never_ranked():
    result = evaluate_relation(
        sector(sector_id="STYLE:LIMIT_UP", name="涨停", bucket="PRICE_BEHAVIOR_TAG"),
        "SH.600001",
        members(),
    )

    assert result["eligible"] is False
    assert "SEMANTIC_BUCKET_NOT_NORMAL_ATTRIBUTE" in result["rejection_reasons"]
    assert rank_associations([result])[0]["association_rank"] is None


def test_reacceleration_requires_independent_five_day_support():
    rows = members()
    for row in rows[1:]:
        row["ret5"] = -0.01
    result = evaluate_relation(sector(pattern="REACCELERATION"), "SH.600001", rows)

    assert result["eligible"] is False
    assert "REACCELERATION_LEAVE_ONE_OUT_RET5_MEDIAN_NOT_POSITIVE" in result["rejection_reasons"]
