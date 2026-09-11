from workbench_service.universe import (
    WORKBENCH_SCOPE_SQL,
    WORKBENCH_STATISTICAL_SCOPE_SQL,
    is_workbench_statistical_security_id,
    is_workbench_visible_security_id,
    workbench_display_scope,
    workbench_statistical_scope,
)
from workbench_service.app import Api
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_display_scope_includes_star_and_bj_with_statistical_scope() -> None:
    scope = workbench_display_scope()
    assert scope["show_star_stocks"] is True
    assert scope["excluded_board_prefixes"] == []
    assert is_workbench_visible_security_id("SH.688001")
    assert is_workbench_visible_security_id("SH.689001")
    assert is_workbench_visible_security_id("BJ.830001")
    assert is_workbench_visible_security_id("SH.600000")
    assert is_workbench_visible_security_id("SZ.300001")
    stats = workbench_statistical_scope()
    assert stats["include_star_stocks"] is True
    assert stats["include_bj_stocks"] is True
    assert stats["excluded_board_prefixes"] == []
    assert is_workbench_statistical_security_id("SH.688001")
    assert is_workbench_statistical_security_id("SH.689001")
    assert is_workbench_statistical_security_id("BJ.830001")


def test_sql_scope_keeps_a_share_identity_and_includes_star_and_bj() -> None:
    sql = WORKBENCH_SCOPE_SQL.format(id="security_id")
    assert "regexp_matches(security_id" in sql
    assert "upper(security_id) like 'SH.688%'" not in sql
    assert "upper(security_id) like 'SH.689%'" not in sql
    assert "upper(security_id) like 'BJ.4%'" not in sql


def test_statistical_sql_is_independent_from_stock_display_scope() -> None:
    sql = WORKBENCH_STATISTICAL_SCOPE_SQL.format(id="security_id")
    assert "regexp_matches(security_id" in sql
    assert "upper(security_id) like 'SH.688%'" not in sql
    assert "upper(security_id) like 'SH.689%'" not in sql


def test_api_separates_full_stock_query_from_stock_facing_pages() -> None:
    api = Api(ROOT / "data/database/market_research.duckdb", root=ROOT)
    publication_id = api.publications()["items"][0]["publication_id"]

    # Full-market lookup remains available, including STAR rows.
    all_stock = api.stocks(publication_id, "SH.688", 1, 1)
    assert all_stock["items"]
    assert all_stock["items"][0]["security_id"].startswith("SH.688")

    # Stock-facing technical results apply the user display scope.
    technical = api.technical(publication_id, page=1, size=100, basis="RECONSTRUCTED")
    assert all(is_workbench_visible_security_id(row["security_id"]) for row in technical["items"])

    # Market aggregation uses the independent statistical scope.
    market = api.market_cycle(publication_id, days=1, basis="RECONSTRUCTED", metrics="amount")
    assert market["statistical_scope"]["include_star_stocks"] is True
    assert market["points"][0]["amount_sum"] is not None
