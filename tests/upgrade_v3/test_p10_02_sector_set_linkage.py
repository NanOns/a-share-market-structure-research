from pathlib import Path

import pytest

from workbench_service.app import Api
from workbench_service.research_context import ResearchContextReader


ROOT = Path(__file__).resolve().parents[2]
DB = ROOT / "data/database/market_research.duckdb"


def _fixture():
    api = Api(DB)
    publication_id = api.publications(include_analysis=True)["items"][0]["publication_id"]
    sectors = api.sector_library(publication_id, page=1, size=4, basis="RECONSTRUCTED")["items"]
    context = ResearchContextReader(lambda: api._con()).resolve_request(publication_id, api._pub(publication_id)[0])
    return api, publication_id, sectors, context


def _request(publication_id, sector_ids, **extra):
    body = {
        "publication_id": publication_id,
        "basis": "RECONSTRUCTED",
        "include_sector_ids": sector_ids,
        "operator": "UNION",
        "exclude_sector_ids": [],
        "filters": {},
        "sort": "security_id.asc",
        "page": 1,
        "page_size": 100,
    }
    body.update(extra)
    return body


def test_p10_02_name_selection_resolves_two_to_four_sectors_server_side():
    api, publication_id, sectors, _ = _fixture()
    selected = sectors[:2]
    result = api.sector_intersection_query(_request(
        publication_id,
        [],
        include_sector_names=[item["sector_name"] for item in selected],
    ))
    assert result["p10_contract_id"] == "V3_P10_SECTOR_SET_LINKAGE_V1_0"
    assert result["include_sector_ids"] == [item["sector_id"] for item in selected]
    assert [item["sector_id"] for item in result["resolved_sector_selections"]["include"]] == result["include_sector_ids"]
    assert result["total"] == result["candidate_total_before_filters"]


def test_p10_02_research_role_filter_runs_after_set_calculation_and_before_paging():
    api, publication_id, sectors, context = _fixture()
    if context["status"] != "READY":
        pytest.skip("当前只读数据库没有 COMPLETE research run")
    selected = [item["sector_id"] for item in sectors[:2]]
    all_members = api.sector_intersection_query(_request(publication_id, selected))
    role_result = api.sector_intersection_query(_request(
        publication_id,
        selected,
        research_context_id=context["context_id"],
        member_role="TODAY_LEADER",
    ))
    with api._con() as connection:
        allowed = {
            str(row[0])
            for row in connection.execute(
                "select distinct security_id from research_sector_member_roles where run_id=? and role=? and sector_id in (?,?)",
                [context["run_id"], "TODAY_LEADER", *selected],
            ).fetchall()
        }
    with api._con() as connection:
        member_set = {
            str(row[0])
            for row in connection.execute(
                """select distinct security_id from member_state_result_daily
                   where slice_id=(select slice_id from analysis_snapshot_entries where snapshot_id=? and domain='member_state' and trade_date=? limit 1)
                     and trade_date=? and member_present=true and sector_id in (?,?)""",
                [all_members["snapshot_id"], all_members["trade_date"], all_members["trade_date"], *selected],
            ).fetchall()
        }
    role_ids = {item["security_id"] for item in role_result["items"]}
    assert role_result["member_role"] == "TODAY_LEADER"
    assert role_ids <= allowed
    assert role_ids <= member_set
    assert role_result["total"] == role_result["candidate_total_before_filters"]


def test_p10_02_old_request_without_new_parameters_preserves_legacy_shape():
    api, publication_id, sectors, _ = _fixture()
    result = api.sector_intersection_query(_request(publication_id, [item["sector_id"] for item in sectors[:2]]))
    assert "research_context_id" not in result
    assert "member_role" not in result
    assert "include_sector_names" not in result
    assert "exclude_sector_names" not in result


def test_p10_02_ui_exposes_name_picker_context_links_and_returnable_selection():
    page = (ROOT / "src/workbench_service/static/v2/index.html").read_text(encoding="utf-8")
    app = (ROOT / "src/workbench_service/static/v2/app.js").read_text(encoding="utf-8")
    router = (ROOT / "src/workbench_service/static/v2/router.js").read_text(encoding="utf-8")
    v3 = (ROOT / "src/workbench_service/static/research-v3.html").read_text(encoding="utf-8")
    for marker in (
        'id="linkage-sector-search"',
        'id="linkage-sector-suggestions"',
        'id="linkage-selected-sectors"',
        'id="linkage-member-role"',
    ):
        assert marker in page
    for marker in (
        "searchLinkageSectors",
        "selectedIncludeSectors",
        "ensureLinkageResearchContext",
        "research_context_id",
        "member_role",
        "router.write",
    ):
        assert marker in app
    assert "context_id" in router and "sector_id" in router
    assert "stockSectorLinks" in v3 and "主板块" in v3 and "备选板块" in v3
