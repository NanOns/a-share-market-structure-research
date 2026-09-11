from pathlib import Path

from workbench_service.app import Api
from workbench_service.attribute_library import CONTRACT_ID, BUCKET_LABELS, sector_attribute_item


ROOT = Path(__file__).parents[2]
DB = ROOT / "data/database/market_research.duckdb"


def _api_and_publication():
    api = Api(DB)
    publication = api.publications(include_analysis=True)["items"][0]
    return api, publication["publication_id"]


def test_m11_01_contract_and_client_wrappers_are_present():
    contract = (ROOT / "docs/M11_ATTRIBUTE_LIBRARY_CONTRACT_V1.md").read_text(encoding="utf-8")
    api_js = (ROOT / "src/workbench_service/static/v2/api.js").read_text(encoding="utf-8")
    assert CONTRACT_ID in contract
    assert "GET /api/sector-library" in contract
    assert "GET /api/stocks/{security_id}/memberships" in contract
    assert "sectorLibrary" in api_js
    assert "stockMemberships" in api_js


def test_sector_library_filters_by_type_and_preserves_traceability():
    api, publication_id = _api_and_publication()
    result = api.sector_library(publication_id, sector_type="THEME", size=3)

    assert result["contract_id"] == CONTRACT_ID
    assert result["total"] >= len(result["items"]) >= 1
    assert result["bucket_counts"]
    assert result["source"]["source_kind"] == "M7A_SEMANTIC_SNAPSHOT"
    assert result["source"]["snapshot_id"] == result["snapshot_id"]
    assert result["source"]["sector_base_slice_id"]
    assert result["source"]["member_state_slice_id"]
    assert all(item["sector_type"] == "THEME" for item in result["items"])
    assert all({"sector_id", "sector_name", "semantic_bucket", "total_member_count", "valid_count", "source"} <= item.keys() for item in result["items"])

    selected = result["items"][0]
    searched = api.sector_library(publication_id, q=selected["sector_id"], size=10)
    assert searched["total"] >= 1
    assert searched["items"][0]["sector_id"] == selected["sector_id"]


def test_stock_memberships_use_same_snapshot_and_keep_tags_out_of_association():
    api, publication_id = _api_and_publication()
    library = api.sector_library(publication_id, size=1)
    sector_id = library["items"][0]["sector_id"]
    with api._con() as connection:
        security_id = connection.execute(
            """select security_id from sector_member_state_daily
               where slice_id=(select slice_id from analysis_snapshot_entries where snapshot_id=? and domain='member_state' and trade_date=? order by trade_date desc limit 1)
                 and trade_date=? and sector_id=? and member_present=true limit 1""",
            [library["snapshot_id"], library["as_of_trade_date"], library["as_of_trade_date"], sector_id],
        ).fetchone()[0]

    result = api.stock_memberships(publication_id, security_id, size=2)
    assert result["contract_id"] == CONTRACT_ID
    assert result["total"] >= len(result["items"]) >= 1
    assert result["source"]["snapshot_id"] == library["snapshot_id"]
    assert all("strength_association_contract" not in item for item in result["items"])
    assert all(item["source"]["snapshot_id"] == result["snapshot_id"] for item in result["items"])
    assert sum(group["total"] for group in result["groups"]) >= len(result["items"])


def test_explicit_semantic_tag_is_not_a_normal_attribute():
    item = sector_attribute_item(
        {
            "sector_id": "STYLE:LIMIT_UP",
            "sector_name": "涨停",
            "sector_type": "STYLE",
            "sector_role": "STYLE",
            "bucket": "PRICE_BEHAVIOR_TAG",
            "sector_valid": True,
            "total_member_count": 2,
            "quote_valid_count": 2,
            "factor_valid_count": 2,
            "coverage": 1.0,
        },
        {"snapshot_id": "fixture"},
    )
    assert item["semantic_bucket"] == "PRICE_BEHAVIOR_TAG"
    assert item["is_attribute"] is False
    assert item["is_market_tag"] is True
    assert set(BUCKET_LABELS) >= {item["semantic_bucket"]}
