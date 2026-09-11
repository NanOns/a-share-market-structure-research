from __future__ import annotations

from datetime import date, datetime, timezone

import duckdb
import pytest

from workbench_service.semantic import (
    CONTRACT_ID,
    NORMAL_ATTRIBUTE,
    UNKNOWN_TAG,
    build_semantic_version_rows,
    insert_semantic_version_rows,
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


def test_semantic_snapshot_rows_are_idempotent_and_immutable() -> None:
    connection = duckdb.connect(":memory:")
    connection.execute(
        """
        create table sector_semantic_versions (
            version_id varchar not null,
            sector_id varchar not null,
            bucket varchar not null,
            rule_id varchar not null,
            reason varchar not null,
            valid_from date,
            observed_at timestamp not null,
            override boolean not null,
            source_id varchar not null,
            primary key (version_id, sector_id)
        )
        """
    )
    source = [{"sector_id": "INDUSTRY:1", "sector_type": "INDUSTRY", "sector_name": "行业"}]
    rows = build_semantic_version_rows(
        source,
        observed_at=datetime(2026, 9, 9, tzinfo=timezone.utc),
        source_id="LOCAL_SEMANTIC_REGISTRY",
        valid_from=date(2026, 9, 7),
    )
    assert insert_semantic_version_rows(connection, rows) == 1
    assert insert_semantic_version_rows(connection, rows) == 0

    # The observation window can advance without changing the semantic rule;
    # the existing immutable version must be reused rather than blocking the
    # next daily analysis build.
    shifted = [dict(rows[0], valid_from=date(2026, 9, 10))]
    assert insert_semantic_version_rows(connection, shifted) == 0

    changed = [dict(rows[0], bucket=UNKNOWN_TAG)]
    with pytest.raises(ValueError, match="SEMANTIC_VERSION_IMMUTABLE_CONFLICT"):
        insert_semantic_version_rows(connection, changed)
    connection.close()
