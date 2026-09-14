from __future__ import annotations

import json
import time
from datetime import datetime, timedelta, timezone

import pytest

from workbench_online.base import FetchResult, OnlineFetchPolicy
from workbench_online.p09_products import (
    EVENT_POOLS,
    HOT_RANK_MODES,
    P09OnlineProducts,
    P09ProductError,
    _url,
    _capabilities,
)


def _result(payload, url="https://test.invalid"):
    body = json.dumps(payload, ensure_ascii=False).encode()
    now = datetime.now(timezone.utc).isoformat()
    return FetchResult(now, now, 200, "application/json", body, url)


class FakeFetcher:
    def __init__(self, payloads=None, *, error=False):
        self.payloads = payloads or {}
        self.calls = []
        self.error = error

    def __call__(self, url, policy, **kwargs):
        assert policy.retries == 0
        assert policy.max_response_bytes <= 2_000_000
        self.calls.append(url)
        if self.error:
            raise TimeoutError("simulated")
        for key, payload in self.payloads.items():
            if key in url:
                return _result(payload, url)
        return _result({"status_code": 0, "data": {"stock_list": [{"code": "600001", "name": "甲", "order": 1}] }}, url)


def test_ext02_and_ext05_normalize_event_fields_without_raw_payload():
    fake = FakeFetcher({
        "lower_limit_pool": {"data": {"info": [{"code": "600001", "name": "甲", "latest": 10, "change_rate": -10}]}},
        "pool/detail": {"data": {"items": [{"symbol": "SH.600001", "stock_chi_name": "甲", "m_days_n_boards_days": 9, "m_days_n_boards_boards": 5}]}},
    })
    service = P09OnlineProducts(fetcher=fake, policy=OnlineFetchPolicy(timeout_seconds=3, max_response_bytes=1000))
    down = service.view(service.fetch("EXT02", {"date": "20260911"}))
    pool = service.events_pools(pool_type="limit_up", trade_date="2026-09-11")
    assert down["status"] == "AVAILABLE"
    assert down["items"][0]["ret1"] == -10
    assert pool["pools"]["limit_up"]["items"][0]["n_boards"] == 5
    assert down["storage"]["raw_payload_persisted"] is False


def test_ext03_ext04_join_counts_unique_members_and_limit_up_separately():
    fake = FakeFetcher({
        "surge_stock/plates": {"data": {"plates": [{"id": 7, "name": "机器人"}]}},
        "surge_stock/stocks": {"data": {"items": [{"topic_id": 7, "code": "600001", "uplimit": True}, {"topic_id": 7, "code": "600001", "uplimit": False}, {"topic_id": 7, "code": "000001", "uplimit": False}]}},
    })
    result = P09OnlineProducts(fetcher=fake).topics(trade_date="2026-09-11")
    assert result["status"] == "AVAILABLE"
    assert result["topic_count"] == 1
    assert result["unique_limit_up_member_count"] == 1
    assert result["items"][0]["unique_member_count"] == 2
    assert result["items"][0]["limit_up_member_count"] == 1


def test_dragon_topic_estimate_is_separate_from_verified_amount_and_deduplicated():
    fake = FakeFetcher({
        "surge_stock/plates": {"data": {"plates": [{"id": 7, "name": "机器人"}, {"id": 8, "name": "算力"}]}},
        "surge_stock/stocks": {"data": {"items": [
            {"topic_id": 7, "code": "600001", "circulation_value": 2_000_000_000, "turnover_ratio": 0.05},
            {"topic_id": 7, "code": "600001", "circulation_value": 2_000_000_000, "turnover_ratio": 0.05},
            {"topic_id": 8, "code": "600001", "circulation_value": 2_000_000_000, "turnover_ratio": 0.05},
            {"topic_id": 8, "code": "600002", "circulation_value": 1_000_000_000, "turnover_ratio": 0.10},
            {"topic_id": 8, "code": "600003", "circulation_value": 1_000_000_000, "turnover_ratio": None},
        ]}},
    })
    result = P09OnlineProducts(fetcher=fake).topics(trade_date="2026-09-11")
    assert [item["dragon_estimated_amount_yi"] for item in result["items"]] == [1.0, 2.0]
    assert result["dragon_estimated_amount_yi"] == 2.0
    assert result["dragon_estimated_valid_count"] == 2
    assert result["amount_sum"] is None


def test_topic_array_mismatch_fails_closed():
    fake = FakeFetcher({
        "surge_stock/plates": {"data": {"plates": [{"id": 7, "name": "机器人"}]}},
        "surge_stock/stocks": {"data": {"fields": ["topic_id", "code"], "stock_array": [[7]]}},
    })
    result = P09OnlineProducts(fetcher=fake).topics(trade_date="2026-09-11")
    assert result["status"] in {"DEGRADED", "UNAVAILABLE"}
    assert result["source_status"]["EXT04"] == "UNAVAILABLE"


def test_hot_rankings_are_four_request_time_views_and_never_persisted():
    fake = FakeFetcher({"hot_list_data": {"status_code": 0, "data": {"stock_list": [{"code": "600001", "name": "甲", "order": 3, "hot_rank_chg": 1}]}}})
    result = P09OnlineProducts(fetcher=fake).hot_rankings()
    assert set(result["lists"]) == {f"{period}_{kind}" for period, kind in HOT_RANK_MODES}
    assert all(view["items"][0]["platform_rank"] == 3 for view in result["lists"].values())
    assert result["persistence"] == "FORBIDDEN_REQUEST_TIME_ONLY"
    assert result["raw_payload_persisted"] is False and result["rows_persisted"] is False


def test_hot_plate_and_topic_contracts_preserve_source_order():
    fake = FakeFetcher({
        "plate?": {"status_code": 0, "data": {"plate_list": [{"code": "P1", "name": "概念", "hot_value": 9}]}},
        "topic?": {"status_code": 0, "data": {"topic_list": [{"title": "话题", "subtitle": "摘要"}]}},
    })
    service = P09OnlineProducts(fetcher=fake)
    assert service.hot_plates()["items"][0]["source_row_order"] == 1
    assert service.hot_topics()["items"][0]["topic_title"] == "话题"


def test_source_failure_is_independent_and_explicit():
    result = P09OnlineProducts(fetcher=FakeFetcher(error=True)).hot_rankings()
    assert result["status"] == "UNAVAILABLE"
    assert all(view["status"] == "UNAVAILABLE" for view in result["lists"].values())
    assert all(view["empty_state"]["code"] for view in result["lists"].values())


def test_partial_batch_is_degraded_not_available():
    class Partial(FakeFetcher):
        def __call__(self, url, policy, **kwargs):
            if "skyrocket" in url:
                raise TimeoutError("one source failed")
            return super().__call__(url, policy, **kwargs)

    result = P09OnlineProducts(fetcher=Partial()).hot_rankings()
    assert result["status"] == "DEGRADED"
    assert result["lists"]["hour_skyrocket"]["status"] == "UNAVAILABLE"


def test_global_batch_budget_returns_without_waiting_for_all_sources(monkeypatch):
    import workbench_online.p09_products as products

    class Slow:
        def __call__(self, url, policy, **kwargs):
            time.sleep(0.25)
            return _result({"status_code": 0, "data": {"stock_list": [{"code": "600001", "name": "甲", "order": 1}]}} , url)

    monkeypatch.setattr(products, "P09_MAX_TOTAL_SECONDS", 0.05)
    started = time.monotonic()
    result = products.P09OnlineProducts(fetcher=Slow()).batch([("EXT07", {}) for _ in range(6)])
    assert time.monotonic() - started < 0.2
    assert len(result) == 6
    assert all(item.status == "UNAVAILABLE" for item in result)


def test_invalid_pool_and_source_are_contract_errors():
    with pytest.raises(P09ProductError, match="POOL_TYPE_INVALID"):
        P09OnlineProducts(fetcher=FakeFetcher()).events_pools(pool_type="made_up")
    with pytest.raises(P09ProductError, match="SOURCE_NOT_IN_P09_TARGET_CHAIN"):
        P09OnlineProducts(fetcher=FakeFetcher()).fetch("EXT11")
    with pytest.raises(P09ProductError, match="HOT_RANK_MODE_INVALID"):
        P09OnlineProducts(fetcher=FakeFetcher()).hot_rankings(modes=[("minute", "normal")])


def test_source_date_contract_conversions_are_explicit():
    assert "date=20260911" in _url("EXT02", {"date": "2026-09-11"})
    assert "date=1789056000" in _url("EXT03", {"date": "20260911"})
    assert "date=2026-09-11" in _url("EXT05", {"date": "20260911"})
    assert "date=20260911" in _url("EXT06", {"date": "2026-09-11"})


def test_ext05_current_beijing_day_uses_live_endpoint_but_history_stays_scoped():
    today = datetime.now(timezone(timedelta(hours=8))).date()
    live = _url("EXT05", {"pool_name": "limit_up", "date": today.isoformat()})
    historical = _url("EXT05", {"pool_name": "limit_up", "date": (today - timedelta(days=3)).isoformat()})
    assert "pool_name=limit_up" in live and "date=" not in live
    assert "date=" in historical


def test_seven_pool_enum_is_versioned_and_complete():
    assert len(EVENT_POOLS) == 7
    assert EVENT_POOLS == ("super_stock", "limit_up", "limit_up_broken", "yesterday_limit_up", "limit_down", "new_stock", "nearly_new")


def test_limit_up_time_sort_precedes_pagination_and_missing_time_has_stable_fallback():
    fake = FakeFetcher({"pool/detail": {"data": [
        {"symbol": "LATE", "first_limit_up": 1789360000, "limit_up_days": 1},
        {"symbol": "MISSING_LOW", "first_limit_up": 0, "limit_up_days": 1, "change_percent": 0.10},
        {"symbol": "EARLY", "first_limit_up": 1789350000, "limit_up_days": 1},
        {"symbol": "MISSING_HIGH", "first_limit_up": 0, "limit_up_days": 3, "change_percent": 0.09},
    ]}})
    service = P09OnlineProducts(fetcher=fake, capabilities={"EXT05": "CURRENT_PROBE"})
    first = service.events_pools(pool_type="limit_up", page=1, page_size=2, sort="LIMIT_TIME")["pools"]["limit_up"]
    second = service.events_pools(pool_type="limit_up", page=2, page_size=2, sort="LIMIT_TIME")["pools"]["limit_up"]
    assert [row["source_code"] for row in first["items"]] == ["EARLY", "LATE"]
    assert [row["source_code"] for row in second["items"]] == ["MISSING_HIGH", "MISSING_LOW"]
    assert first["sort"]["mode"] == "LIMIT_TIME"
    with pytest.raises(P09ProductError, match="POOL_SORT_INVALID"):
        service.events_pools(pool_type="super_stock", sort="LIMIT_TIME")


def test_disabled_capability_never_calls_network():
    fake = FakeFetcher()
    service = P09OnlineProducts(fetcher=fake, capabilities={"EXT02": "UNAVAILABLE"})
    result = service.fetch("EXT02")
    assert result.status == "UNAVAILABLE"
    assert result.error_code == "SOURCE_CAPABILITY_DISABLED"
    assert fake.calls == []


def test_runtime_capability_contract_matches_reprobe_and_opens_ext06():
    capabilities = _capabilities()
    assert {key for key in capabilities if ":" not in key} == {"EXT02", "EXT03", "EXT04", "EXT05", "EXT06", "EXT07", "EXT08", "EXT09"}
    assert all(f"EXT05:{pool}" in capabilities for pool in EVENT_POOLS)
    assert all(f"EXT07:{period}:{kind}" in capabilities for period, kind in HOT_RANK_MODES)
    assert {"EXT08:concept", "EXT08:industry"} <= set(capabilities)


def test_ext06_longzijue_overview_groups_are_exposed_without_guessing_turnover_unit():
    fake = FakeFetcher({"market_state/v1/overview": {"status_code": 0, "data": {
        "turnover": {"now": "2万亿", "pre": "1.6万亿"},
        "north_flow": {"now": "0.0亿", "pre": None},
        "rise_fall": {"rise": 643, "fall": 4870, "deuce": 37, "limit_up": 40, "limit_down": 21},
    }}})
    result = P09OnlineProducts(fetcher=fake, capabilities={"EXT06": "CURRENT_PROBE"}).fetch("EXT06", {"date": "2026-09-11"})
    assert result.status == "AVAILABLE"
    assert result.normalized["rise_fall"]["fall"] == 4870
    assert result.normalized["turnover_display"]["now"] == "2万亿"
    assert result.normalized["north_flow_display"] == {"now": "0.0亿"}


def test_dragon_yesterday_pool_promotion_uses_source_transition_fields_and_keeps_unknown_out():
    fake = FakeFetcher({"pool/detail": {"data": {"items": [
        {"symbol": "600001.SS", "stock_chi_name": "甲", "yesterday_limit_up_days": 1, "limit_up_days": 2, "change_percent": 0.10},
        {"symbol": "600002.SS", "stock_chi_name": "乙", "yesterday_limit_up_days": 2, "limit_up_days": 0, "change_percent": -0.02},
        {"symbol": "600003.SS", "stock_chi_name": "丙", "yesterday_limit_up_days": 1, "limit_up_days": 0},
    ]}}})
    result = P09OnlineProducts(fetcher=fake, capabilities={"EXT05": "CURRENT_PROBE"}).promotion(trade_date="2026-09-11")
    assert result["status"] == "AVAILABLE"
    assert (result["success_count"], result["not_promoted_count"], result["unknown_count"], result["eligible_count"]) == (1, 1, 1, 2)
    assert result["rate"] == 0.5


def test_topic_join_uses_all_rows_before_display_paging():
    members = [{"topic_id": 7, "code": f"600{i:03d}", "uplimit": True} for i in range(47)]
    fake = FakeFetcher({
        "surge_stock/plates": {"data": {"plates": [{"id": 7, "name": "机器人"}]}},
        "surge_stock/stocks": {"data": {"items": members}},
    })
    result = P09OnlineProducts(fetcher=fake, capabilities={"EXT03": "CURRENT_PROBE", "EXT04": "CURRENT_PROBE"}).topics(trade_date="2026-09-11")
    assert result["status"] == "AVAILABLE"
    assert result["items"][0]["unique_member_count"] == 47
    assert result["items"][0]["limit_up_member_count"] == 47
    assert result["unique_limit_up_member_count"] == 47
    assert result["global_unique_member_count"] == 47
    assert result["membership_count"] == 47
    assert result["amount_sum"] is None and result["amount_coverage"] == "SOURCE_FIELD_OR_UNIT_UNVERIFIED"


def test_verified_source_time_and_date_mismatch_fail_closed():
    fake = FakeFetcher({
        "surge_stock/plates": {"data": {"items": [{"id": 7, "name": "机器人"}], "timestamp": 1789056000, "manual_updated_at": 1789141800}},
        "lower_limit_pool": {"data": {"date": "20260910", "info": [{"code": "600001", "name": "甲"}]}},
    })
    service = P09OnlineProducts(fetcher=fake, capabilities={"EXT03": "CURRENT_PROBE", "EXT02": "CURRENT_PROBE"})
    plate = service.fetch("EXT03", {"date": "2026-09-11"})
    assert plate.source_trade_date == "2026-09-11"
    assert plate.source_as_of is not None
    down = service.fetch("EXT02", {"date": "2026-09-11"})
    assert down.status == "UNAVAILABLE"
    assert down.error_code == "SOURCE_DATE_MISMATCH"


def test_source_field_semantics_and_external_link_validation():
    fake = FakeFetcher({
        "surge_stock/stocks": {"data": {"items": [{"topic_id": 7, "code": "600001", "up_limit": "false", "description": "来源说明"}]}},
        "pool/detail": {"data": [{"symbol": "SH.600001", "stock_chi_name": "甲", "surge_reason": {"stock_reason": "源原因"}}]},
        "plate?": {"data": {"plate_list": [{"code": "P1", "name": "概念", "rate": 12, "order": 3}]}},
        "topic?": {"data": {"topic_list": [{"title": "话题", "hot_value": 8, "jump_url": "javascript:alert(1)"}]}},
    })
    service = P09OnlineProducts(fetcher=fake, capabilities={"EXT04": "CURRENT_PROBE", "EXT05": "CURRENT_PROBE", "EXT08": "CURRENT_PROBE", "EXT09": "CURRENT_PROBE"})
    assert service.fetch("EXT04").normalized[0]["is_limit_up"] is False
    assert service.fetch("EXT04").normalized[0]["source_description"] == "来源说明"
    assert service.fetch("EXT05", {"pool_name": "limit_up"}).normalized[0]["source_reason"] == "源原因"
    plate = service.hot_plates()["items"][0]
    assert plate["source_rate"] == 12 and plate["hot_value"] is None and plate["platform_rank"] == 3
    topic = service.hot_topics()["items"][0]
    assert topic["hot_value"] == 8 and topic["safe_external_url"] is None


def test_hot_topic_empty_second_page_is_valid_and_full_page_invites_next():
    class Pages(FakeFetcher):
        def __call__(self, url, policy, **kwargs):
            if "page=2" in url:
                return _result({"status_code": 0, "data": {"topic_list": []}}, url)
            return _result({"status_code": 0, "data": {"topic_list": [{"title": f"话题{i}"} for i in range(30)]}}, url)

    service = P09OnlineProducts(fetcher=Pages(), capabilities={"EXT09": "CURRENT_PROBE"})
    first = service.hot_topics(page=1)
    second = service.hot_topics(page=2)
    assert first["has_more"] is True
    assert first["coverage"]["complete_pagination"] is False
    assert second["status"] == "AVAILABLE" and second["items"] == [] and second["has_more"] is False

