from pathlib import Path

from workbench_service.app import API_CONTRACT, Api
from workbench_service.catalog import CATALOG_VERSION, FIELD_CATALOG, ENUM_CATALOG


ROOT = Path(__file__).parents[2]


def test_field_catalog_has_unique_fields_units_and_chinese_enum_mappings():
    ids = [field["field_id"] for field in FIELD_CATALOG]
    assert len(ids) == len(set(ids))
    assert all({"field_id", "label", "type", "unit", "nullable", "description", "sort_supported"} <= field.keys() for field in FIELD_CATALOG)
    assert all(field["label"] and field["description"] and field["unit"] is not None for field in FIELD_CATALOG)
    assert ENUM_CATALOG["queue_name"]["STEADY_QUEUE"] == "稳健趋势队列"
    assert ENUM_CATALOG["research_band"]["CORE_RESEARCH"] == "核心观察"


def test_catalog_endpoint_and_versioned_contract_are_local():
    api = Api(ROOT / "data/database/market_research.duckdb")
    result = api.field_catalog()
    assert result["api_contract"] == API_CONTRACT == "workbench-api-v2.1"
    assert result["catalog_version"] == CATALOG_VERSION
    assert result["language"] == "zh-CN"
    assert {"field_id", "label", "type", "unit", "nullable", "description", "sort_supported"} <= result["items"][0].keys()
    assert result["enums"]["capability"]["NOT_BUILT"] == "尚未生成"
    contract = (ROOT / "docs/M7A_FIELD_CATALOG_CONTRACT_V1.md").read_text(encoding="utf-8")
    assert CATALOG_VERSION in contract and API_CONTRACT in contract


def test_publication_and_identity_analysis_extensions_are_opt_in():
    api = Api(ROOT / "data/database/market_research.duckdb")
    legacy = api.publications()
    extended = api.publications(include_analysis=True)
    assert legacy["items"] and "analysis_capabilities" not in legacy["items"][0]
    assert extended["api_contract"] == API_CONTRACT
    assert {"revision", "production_version", "analysis_capabilities"} <= extended["items"][0].keys()
    identity = api.identity(extended["items"][0]["publication_id"], include_analysis=True)
    assert identity["api_contract"] == API_CONTRACT
    assert {"contracts", "capabilities", "data_quality", "analysis_snapshot_id", "cutoff_date"} <= identity.keys()
    assert identity["capabilities"]["history_analysis"] == "AVAILABLE"


def test_v2_preview_requests_analysis_capabilities():
    api_js = (ROOT / "src/workbench_service/static/v2/api.js").read_text(encoding="utf-8")
    app_js = (ROOT / "src/workbench_service/static/v2/app.js").read_text(encoding="utf-8")
    assert "publications(true)" in app_js and "identity(publication.publication_id,true)" in app_js
    assert "include_analysis:includeAnalysis?'1':undefined" in api_js
