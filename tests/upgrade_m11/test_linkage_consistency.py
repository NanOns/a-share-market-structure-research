from pathlib import Path

from workbench_service.app import Api


ROOT = Path(__file__).parents[2]
DB = ROOT / "data/database/market_research.duckdb"


def _context():
    api = Api(DB)
    publication = api.publications(include_analysis=True)["items"][0]
    publication_id = publication["publication_id"]
    snapshot_id = api._analysis_bindings(publication_id)["LOCAL_RECONSTRUCTED"]["snapshot_id"]
    with api._con() as connection:
        sector_id, security_id = connection.execute(
            """select m.sector_id,m.security_id
                 from sector_member_state_daily m
                 join analysis_snapshot_entries e on e.snapshot_id=? and e.domain='member_state'
                   and e.slice_id=m.slice_id and e.trade_date=m.trade_date
                where m.member_present=true and m.member_rank is not null
                order by m.sector_id,m.member_rank,m.security_id limit 1""",
            [snapshot_id],
        ).fetchone()
    return api, publication_id, snapshot_id, sector_id, security_id


def test_forward_and_reverse_linkage_reuse_same_member_rank_and_count():
    api, publication_id, snapshot_id, sector_id, security_id = _context()
    forward = api.linkage(publication_id, sector_id, security_id, size=10, basis="RECONSTRUCTED")
    reverse = api.linkage(publication_id, None, security_id, size=100, basis="RECONSTRUCTED")
    row = next(item for item in reverse["items"] if item["sector_id"] == sector_id)
    assert forward["snapshot_id"] == reverse["snapshot_id"] == snapshot_id
    assert forward["items"][0]["sector_member_rank"] == row["sector_member_rank"]
    assert forward["items"][0]["sector_member_count"] == row["sector_member_count"]
    assert forward["items"][0]["association_contract_id"] == "STOCK_SECTOR_ASSOC_V1"


def test_query_filter_does_not_renumber_sector_member_rank():
    api, publication_id, _, sector_id, security_id = _context()
    full = api.linkage(publication_id, sector_id, None, size=100, basis="RECONSTRUCTED")
    filtered = api.linkage(publication_id, sector_id, None, size=100, q=security_id, basis="RECONSTRUCTED")
    expected = next(item for item in full["items"] if item["security_id"] == security_id)
    assert filtered["total"] == 1
    assert filtered["items"][0]["sector_member_rank"] == expected["sector_member_rank"]


def test_linkage_history_is_date_ordered_and_traceable():
    api, publication_id, snapshot_id, sector_id, _ = _context()
    result = api.linkage_history(publication_id, sector_id, days=2, size=20, basis="RECONSTRUCTED")
    assert result["snapshot_id"] == snapshot_id
    assert result["history_basis"] == "RECONSTRUCTED"
    assert result["returned_range"]["dates"] == sorted(result["returned_range"]["dates"], reverse=True)
    assert result["items"]
    assert all("status" in item and "member_change" in item["status"] for item in result["items"])


def test_linkage_contract_and_client_wrappers_are_present():
    contract = (ROOT / "docs/M11_LINKAGE_CONSISTENCY_CONTRACT_V1.md").read_text(encoding="utf-8")
    api_js = (ROOT / "src/workbench_service/static/v2/api.js").read_text(encoding="utf-8")
    assert "M11_LINKAGE_CONSISTENCY_V1" in contract
    assert "GET /api/linkage/history" in contract
    assert "linkageHistory" in api_js
