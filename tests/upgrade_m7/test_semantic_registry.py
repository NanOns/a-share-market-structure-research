from __future__ import annotations

from workbench_service.semantic import (
    CONTRACT_ID,
    NORMAL_ATTRIBUTE,
    UNKNOWN_TAG,
    resolve_semantics,
)


def test_known_type_is_a_normal_attribute() -> None:
    result = resolve_semantics({"sector_id": "INDUSTRY:T0101", "sector_type": "INDUSTRY", "sector_name": "行业"})
    assert result["semantic_version"] == CONTRACT_ID
    assert result["bucket"] == NORMAL_ATTRIBUTE
    assert result["is_attribute"] is True
    assert result["is_market_tag"] is False
    assert result["normal_rank_eligible"] is True


def test_keyword_is_only_a_review_hint_and_cannot_enter_normal_rank() -> None:
    result = resolve_semantics(
        {"sector_id": "THEME:880001", "sector_type": "THEME", "sector_name": "昨日首板强势"}
    )
    assert result["bucket"] == UNKNOWN_TAG
    assert result["keyword_hint"] == "PRICE_BEHAVIOR_TAG"
    assert result["reason"] == "KEYWORD_CANDIDATE_REQUIRES_ID_REVIEW"
    assert result["normal_rank_eligible"] is False


def test_exact_sector_id_override_wins_over_keyword_hint() -> None:
    result = resolve_semantics(
        {"sector_id": "THEME:880001", "sector_type": "THEME", "sector_name": "昨日首板强势"},
        {"THEME:880001": {"bucket": "NORMAL_ATTRIBUTE", "role": "THEME", "rule_id": "MANUAL_V1", "reason": "经复核为稳定属性"}},
    )
    assert result["bucket"] == NORMAL_ATTRIBUTE
    assert result["override"] is True
    assert result["rule_id"] == "MANUAL_V1"
    assert result["normal_rank_eligible"] is True


def test_excluded_role_remains_separate_from_attribute_class() -> None:
    result = resolve_semantics(
        {"sector_id": "THEME:880002", "sector_type": "THEME", "sector_role": "EXCLUDE_FROM_THEME_RANK", "sector_valid": True}
    )
    assert result["bucket"] == NORMAL_ATTRIBUTE
    assert result["is_attribute"] is True
    assert result["normal_rank_eligible"] is False


def test_unknown_sector_type_is_visible_but_not_a_normal_attribute() -> None:
    result = resolve_semantics({"sector_id": "OTHER:1", "sector_type": "OTHER", "sector_name": "未分类"})
    assert result["bucket"] == UNKNOWN_TAG
    assert result["is_market_tag"] is True
    assert result["normal_rank_eligible"] is False
