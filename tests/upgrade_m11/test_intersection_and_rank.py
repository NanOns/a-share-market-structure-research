from pathlib import Path

import pytest

from workbench_service.app import Api
from workbench_service.intersection import CONTRACT_ID
from workbench_service.universe import is_a_share_security_id


ROOT = Path(__file__).parents[2]
DB = ROOT / "data/database/market_research.duckdb"


def _context():
    api = Api(DB)
    publication_id = api.publications(include_analysis=True)["items"][0]["publication_id"]
    snapshot_id = api._analysis_bindings(publication_id)["LOCAL_RECONSTRUCTED"]["snapshot_id"]
    with api._con() as connection:
        trade_date = str(connection.execute(
            "select max(trade_date) from analysis_snapshot_entries where snapshot_id=? and domain='member_state'",
            [snapshot_id],
        ).fetchone()[0])
        sector_ids = [row[0] for row in connection.execute(
            """select sector_id from sector_member_state_daily
               where slice_id=(select slice_id from analysis_snapshot_entries where snapshot_id=? and domain='member_state' and trade_date=? order by trade_date desc limit 1)
                 and trade_date=? and member_present=true
               group by sector_id order by count(*) desc, sector_id limit 3""",
            [snapshot_id, trade_date, trade_date],
        ).fetchall()]
        sets = {}
        for sector_id in sector_ids:
            sets[sector_id] = {
                row[0] for row in connection.execute(
                    """select security_id from sector_member_state_daily
                       where slice_id=(select slice_id from analysis_snapshot_entries where snapshot_id=? and domain='member_state' and trade_date=? order by trade_date desc limit 1)
                         and trade_date=? and sector_id=? and member_present=true""",
                    [snapshot_id, trade_date, trade_date, sector_id],
                ).fetchall()
                if is_a_share_security_id(row[0])
            }
    return api, publication_id, snapshot_id, trade_date, sector_ids, sets


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


def test_union_and_intersection_match_membership_truth_and_are_traceable():
    api, publication_id, snapshot_id, trade_date, sector_ids, sets = _context()
    union = api.sector_intersection_query(_request(publication_id, sector_ids[:2]))
    expected_union = sets[sector_ids[0]] | sets[sector_ids[1]]
    assert union["contract_id"] == CONTRACT_ID
    assert union["trade_date"] == trade_date
    assert union["candidate_total_before_filters"] == len(expected_union)
    assert union["total"] == len(expected_union)
    assert [item["security_id"] for item in union["items"]] == sorted(expected_union)[:100]
    assert all(set(item["matched_sector_ids"]) <= set(sector_ids[:2]) for item in union["items"])
    assert union["source"]["snapshot_id"] == snapshot_id
    assert union["source"]["filter_slice_ids"]["technical"]

    intersection = api.sector_intersection_query(_request(
        publication_id,
        sector_ids[:2],
        operator="INTERSECTION",
    ))
    expected_intersection = sets[sector_ids[0]] & sets[sector_ids[1]]
    assert intersection["total"] == len(expected_intersection)
    assert all(set(item["matched_sector_ids"]) == set(sector_ids[:2]) for item in intersection["items"])


def test_exclude_has_priority_and_duplicate_include_is_idempotent():
    api, publication_id, _, _, sector_ids, sets = _context()
    excluded = api.sector_intersection_query(_request(
        publication_id,
        sector_ids[:2],
        exclude_sector_ids=[sector_ids[2]],
    ))
    expected = (sets[sector_ids[0]] | sets[sector_ids[1]]) - sets[sector_ids[2]]
    assert excluded["total"] == len(expected)

    normal = api.sector_intersection_query(_request(publication_id, sector_ids[:2]))
    duplicate = api.sector_intersection_query(_request(publication_id, [sector_ids[0], sector_ids[0], sector_ids[1]]))
    assert duplicate["total"] == normal["total"]
    assert [item["security_id"] for item in duplicate["items"]] == [item["security_id"] for item in normal["items"]]


def test_null_and_empty_array_filters_are_explicit_and_four_sector_limit_is_enforced():
    api, publication_id, _, _, sector_ids, _ = _context()
    empty_bands = api.sector_intersection_query(_request(publication_id, sector_ids[:2], filters={"bands": []}))
    huge_amount = api.sector_intersection_query(_request(publication_id, sector_ids[:2], filters={"amount_vs_prior20_min": 1e99}))
    assert empty_bands["total"] == 0
    assert huge_amount["total"] == 0

    with pytest.raises(ValueError, match="INCLUDE_SECTOR_IDS_MAX_4"):
        api.sector_intersection_query(_request(publication_id, sector_ids[:2] + ["A", "B", "C"]))
