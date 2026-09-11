import json
from pathlib import Path

from workbench_service.app import Api


ROOT = Path(__file__).resolve().parents[2]


def _api_and_latest():
    api = Api(ROOT / "data/database/market_research.duckdb")
    publication = api.publications(True)["items"][0]
    return api, publication


def test_api30_is_snapshot_bound_and_keeps_fixed_sector_groups():
    api, publication = _api_and_latest()
    result = api.dashboard(publication["publication_id"], True, "RECONSTRUCTED")
    item = result["item"]

    assert result["contract_id"] == "M15_OVERVIEW_V1_0"
    assert item["publication_id"] == publication["publication_id"]
    assert item["snapshot_id"] == result["snapshot_id"]
    assert item["resolved_basis"] == "RECONSTRUCTED"
    assert len(item["market_summary"]["cards"]) == 6
    assert set(item["strong_sectors"]) == {"INDUSTRY", "THEME"}
    assert all(len(group["items"]) <= 10 for group in item["strong_sectors"].values())
    assert all(row["sector_type"] in {"INDUSTRY", "THEME"}
               for group in item["strong_sectors"].values() for row in group["items"])


def test_api30_representatives_are_unique_and_keep_all_sector_sources():
    api, publication = _api_and_latest()
    item = api.dashboard(publication["publication_id"], True, "RECONSTRUCTED")["item"]
    representatives = item["representatives"]
    ids = [row["security_id"] for row in representatives["items"]]

    assert len(ids) == len(set(ids))
    assert all(row["source_sector_count"] == len(row["sector_sources"])
               for row in representatives["items"])


def test_api31_keeps_priority_pagination_and_contract():
    api, publication = _api_and_latest()
    result = api.candidates(publication["publication_id"], "", 1, 50,
                            include_analysis=True, basis="RECONSTRUCTED")

    assert result["contract_id"] == "M15_PRIORITY_RESEARCH_V1_0"
    assert result["stock_row_contract"] == "StockRow_V1_0"
    assert result["page"] == 1 and result["page_size"] == 50
    assert len(result["items"]) <= 50
    priorities = {"A+": 0, "A": 1, "B": 2, "C": 3}
    values = [priorities.get(row.get("research_priority"), 9)
              for row in result["items"]]
    assert values == sorted(values)


def test_api30_rejects_future_overview_date():
    api, publication = _api_and_latest()
    try:
        api.dashboard(publication["publication_id"], True, "RECONSTRUCTED", "2999-01-01")
    except ValueError as error:
        assert str(error) == "DATE_AFTER_CUTOFF"
    else:
        raise AssertionError("future overview date must fail closed")


def test_overview_contract_and_ui_mount_are_declared():
    contract = (ROOT / "docs/M15_01_OVERVIEW_CONTRACT_V1.md").read_text(encoding="utf-8")
    index = (ROOT / "src/workbench_service/static/v2/index.html").read_text(encoding="utf-8")
    api = (ROOT / "src/workbench_service/static/v2/api.js").read_text(encoding="utf-8")
    app = (ROOT / "src/workbench_service/static/v2/app.js").read_text(encoding="utf-8")

    assert "M15_OVERVIEW_V1_0" in contract
    for element_id in ("overview-analysis", "overview-market-cards", "overview-sector-groups",
                       "overview-mainline-counts", "overview-representatives",
                       "overview-priority-table", "overview-priority-prev", "overview-priority-next"):
        assert f'id="{element_id}"' in index
    assert "dashboard:function" in api and "candidates:function" in api
    assert "function loadOverviewAnalysis()" in app
    assert "include_analysis: '1'" in app
    assert "textContent" in app
