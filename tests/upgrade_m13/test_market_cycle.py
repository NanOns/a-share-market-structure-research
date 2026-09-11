from pathlib import Path

from workbench_analysis.market_cycle import CONTRACT_ID, aggregate_market_point, group_queue_counts, group_sector_state_counts
from workbench_service.app import Api


ROOT = Path(__file__).parents[2]
DB = ROOT / "data/database/market_research.duckdb"


def test_market_breadth_identity_and_field_specific_denominators():
    point = aggregate_market_point("2026-09-09", [
        {"quote_ret1": 0.01, "raw_amount": 10, "adj_close": 11, "ma20": 10, "ma60": None},
        {"quote_ret1": -0.01, "raw_amount": None, "adj_close": 9, "ma20": 10, "ma60": 8},
        {"quote_ret1": 0, "raw_amount": 5, "adj_close": None, "ma20": None, "ma60": None},
        {"quote_ret1": None, "raw_amount": 2, "adj_close": 10, "ma20": 10, "ma60": 10},
    ])
    assert point["up_count"] + point["down_count"] + point["flat_count"] == point["quote_valid_count"] == 3
    assert point["amount_valid_count"] == 3
    assert point["ma20_valid_count"] == 3
    assert point["ma60_valid_count"] == 2
    assert point["limit_up_count"] is None
    assert point["unknown_limit_count"] is None
    assert point["contract_id"] == CONTRACT_ID


def test_market_point_deduplicates_security_rows_before_aggregation():
    point = aggregate_market_point("2026-09-09", [
        {"security_id": "SZ.000001", "quote_ret1": 0.01, "raw_amount": 10, "adj_close": 11, "ma20": 10, "ma60": 10},
        {"security_id": "SZ.000001", "quote_ret1": -0.50, "raw_amount": 999, "adj_close": 1, "ma20": 2, "ma60": 3},
        {"security_id": "SZ.000002", "quote_ret1": -0.01, "raw_amount": 5, "adj_close": 9, "ma20": 10, "ma60": 8},
    ])
    assert point["display_count"] == 2
    assert point["quote_valid_count"] == 2
    assert (point["up_count"], point["down_count"], point["amount_sum"]) == (1, 1, 15)


def test_queue_counts_keep_two_queues_and_deduplicate_unique_stock():
    counts, unique = group_queue_counts([
        {"security_id": "SZ.000001", "queue_name": "STEADY", "hit": True},
        {"security_id": "SZ.000001", "queue_name": "REACCELERATING", "hit": True},
        {"security_id": "SZ.000002", "queue_name": "STEADY", "hit": False},
    ])
    assert counts == {"REACCELERATING": 1, "STEADY": 1}
    assert unique == 1


def test_queue_counts_deduplicate_duplicate_stock_queue_rows():
    counts, unique = group_queue_counts([
        {"security_id": "SZ.000001", "queue_name": "STEADY", "hit": True},
        {"security_id": "SZ.000001", "queue_name": "STEADY", "hit": True},
        {"security_id": "SZ.000001", "queue_name": "REACCELERATING", "hit": True},
    ])
    assert counts == {"REACCELERATING": 1, "STEADY": 1}
    assert unique == 1


def test_sector_state_counts_deduplicate_sector_rows_and_preserve_unknown():
    assert group_sector_state_counts([
        {"sector_id": "industry:bank", "diffusion_state": "EXPANDING"},
        {"sector_id": "industry:bank", "diffusion_state": "CONTRACTING"},
        {"sector_id": "theme:ai", "diffusion_state": None},
    ]) == {"EXPANDING": 1, "UNKNOWN": 1}


def test_market_cycle_api_returns_compact_points_and_metadata():
    api = Api(DB)
    publication_id = api.publications()["items"][0]["publication_id"]
    result = api.market_cycle(publication_id, days=60, basis="RECONSTRUCTED", metrics="breadth,amount,ma,new_high,queues")
    assert result["contract_id"] == CONTRACT_ID
    assert result["points"]
    assert result["snapshot_id"]
    for point in result["points"]:
        assert point["up_count"] + point["down_count"] + point["flat_count"] == point["quote_valid_count"]
        assert point["display_count"] >= point["quote_valid_count"]
        assert "field_coverage" in point
        if point["capabilities"]["queue_state"] == "AVAILABLE":
            assert point["queue_unique_count"] is not None
        else:
            assert point["queue_unique_count"] is None
        assert point["capabilities"]["sector_state"] == "AVAILABLE"
        assert sum(point["sector_state_counts"].values()) > 0
    assert any(point["capabilities"]["queue_state"] == "AVAILABLE" for point in result["points"])


def test_market_cycle_rejects_unknown_metric_and_day_detail_is_snapshot_bound():
    api = Api(DB)
    publication_id = api.publications()["items"][0]["publication_id"]
    try:
        api.market_cycle(publication_id, metrics="breadth,blackbox", basis="RECONSTRUCTED")
    except ValueError as error:
        assert str(error) == "MARKET_METRIC_UNSUPPORTED"
    else:
        raise AssertionError("unknown market metric must be rejected")
    cycle = api.market_cycle(publication_id, days=1, basis="RECONSTRUCTED")
    detail = api.market_day_detail(publication_id, cycle["points"][0]["trade_date"], basis="RECONSTRUCTED")
    assert detail["snapshot_id"] == cycle["snapshot_id"]


def test_market_ui_and_client_contract_are_present():
    app = (ROOT / "src/workbench_service/static/v2/app.js").read_text(encoding="utf-8")
    html = (ROOT / "src/workbench_service/static/v2/index.html").read_text(encoding="utf-8")
    api = (ROOT / "src/workbench_service/static/v2/api.js").read_text(encoding="utf-8")
    assert "marketCycle" in api and "marketDayDetail" in api
    assert "api.marketCycle" in app and "market-page" in html
    assert "up_count" in app and "点击日期" in html
    assert "market-breadth-chart" in html and "market-amount-chart" in html and "market-structure-chart" in html
    assert "renderMarketCharts" in app and "market-chart-hit" in app and "openMarketDetail" in app
    assert "limit_up_count" in app and "limit_down_count" in app
