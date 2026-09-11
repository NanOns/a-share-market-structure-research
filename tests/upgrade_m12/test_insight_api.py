from pathlib import Path

import pytest

from workbench_service.app import Api


ROOT = Path(__file__).parents[2]
DB = ROOT / "data/database/market_research.duckdb"


def _context():
    api = Api(DB)
    publication_id = api.publications()["items"][0]["publication_id"]
    with api._con() as connection:
        snapshot_id = connection.execute(
            "select snapshot_id from publication_analysis_snapshots where publication_id=? and domain=?",
            [publication_id, "LOCAL_RECONSTRUCTED"],
        ).fetchone()[0]
        security_id = connection.execute(
            """select security_id from stock_technical_daily t
                 join analysis_snapshot_entries e on e.snapshot_id=? and e.domain='technical'
                   and e.slice_id=t.slice_id and e.trade_date=t.trade_date
                limit 1""",
            [snapshot_id],
        ).fetchone()[0]
    return api, publication_id, snapshot_id, security_id


def test_api29_default_is_compact_and_traceable():
    api, publication_id, snapshot_id, security_id = _context()
    result = api.stock_insight(publication_id, security_id, basis="RECONSTRUCTED")
    assert result["status"] == "AVAILABLE"
    assert result["snapshot_id"] == snapshot_id
    assert set(result["item"]) == {"overview", "technical", "sector_context"}
    assert "points" not in result["item"]
    assert result["item"]["technical"]["contract_id"]
    assert result["item"]["sector_context"]["contract_id"] == "STOCK_SECTOR_ASSOC_V1"
    assert "data_quality" in result and "basis_metadata" in result


def test_api29_include_is_explicit_and_cache_key_includes_shape():
    api, publication_id, _, security_id = _context()
    overview = api.stock_insight(publication_id, security_id, include="overview", days=5, basis="RECONSTRUCTED")
    technical = api.stock_insight(publication_id, security_id, include="overview,technical", days=20, basis="RECONSTRUCTED")
    assert set(overview["item"]) == {"overview"}
    assert set(technical["item"]) == {"overview", "technical"}
    assert overview["query_hash"] != technical["query_hash"]


def test_api29_cache_isolated_by_requested_basis():
    api, publication_id, _, security_id = _context()
    auto = api.stock_insight(publication_id, security_id, include="overview", days=20, basis="AUTO")
    reconstructed = api.stock_insight(publication_id, security_id, include="overview", days=20, basis="RECONSTRUCTED")
    assert auto["requested_basis"] == "AUTO"
    assert reconstructed["requested_basis"] == "RECONSTRUCTED"
    assert auto["query_hash"] != reconstructed["query_hash"]


def test_api15_groups_include_m11_association_evidence():
    api, publication_id, _, _ = _context()
    with api._con() as connection:
        structure = connection.execute(
            """select h.queue_name from historical_structure_daily h
                 join analysis_snapshot_entries e on e.snapshot_id=? and e.domain='structure'
                   and e.slice_id=h.slice_id and e.trade_date=h.trade_date
                where h.security_id is not null limit 1""",
            [api._analysis_context(publication_id, "RECONSTRUCTED")["selected"]["snapshot_id"]],
        ).fetchone()
        security_id = connection.execute(
            """select h.security_id from historical_structure_daily h
                 join analysis_snapshot_entries e on e.snapshot_id=? and e.domain='structure'
                   and e.slice_id=h.slice_id and e.trade_date=h.trade_date
                where h.queue_name=? limit 1""",
            [api._analysis_context(publication_id, "RECONSTRUCTED")["selected"]["snapshot_id"], structure[0]],
        ).fetchone()[0]
    result = api.evidence(publication_id, structure[0], security_id, format="groups", basis="RECONSTRUCTED")
    groups = result["item"]["groups"]
    association = next(group for group in groups if group["group_id"] == "m11_association")
    assert association["contract_id"] == "STOCK_SECTOR_ASSOC_V1"
    assert "items" in association
    assert all("evidence_json" in item for item in association["items"])


def test_api29_rejects_unknown_include():
    api, publication_id, _, security_id = _context()
    with pytest.raises(ValueError, match="INSIGHT_INCLUDE_UNSUPPORTED"):
        api.stock_insight(publication_id, security_id, include="overview,all", basis="RECONSTRUCTED")


def test_api29_contract_and_client_wrapper_are_present():
    contract = (ROOT / "docs/M12_STOCK_INSIGHT_CONTRACT_V1.md").read_text(encoding="utf-8")
    api_js = (ROOT / "src/workbench_service/static/v2/api.js").read_text(encoding="utf-8")
    assert "M12_STOCK_INSIGHT_V1" in contract
    assert "GET /api/stocks/{security_id}/insight" in contract
    assert "stockInsight" in api_js
