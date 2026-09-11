from workbench_online.base import FetchResult
from pathlib import Path

from workbench_service.online_hot_rank import build_hot_rank_direct_response


ROOT = Path(__file__).parents[2]


def _result(source: str) -> FetchResult:
    return FetchResult(
        requested_at_utc="2026-09-11T07:10:00+00:00",
        received_at_utc="2026-09-11T07:10:01+00:00",
        status_code=200,
        content_type="application/json",
        body=source.encode("utf-8"),
        url="https://example.test/hot-rank",
    )


def _eastmoney(policy, *, page=1):
    rows = [
        {
            "source_code": f"{index:06d}",
            "security_id": f"SZ.{index:06d}",
            "platform_rank": index,
            "rank_change": index - 1,
            "security_name": None,
            "source_row_order": index,
            "source_exact_time": "2026-09-11 15:10:00",
        }
        for index in range(1, 21)
    ]
    return _result("eastmoney"), {
        "source_id": "EASTMONEY_HOT_RANK",
        "list_type": "A_STOCK_HOT_RANK",
        "source_as_of": "2026-09-11 15:10:00",
        "time_semantics": "SOURCE_EXACT_TIME",
        "rows": rows,
    }


def _ths(policy):
    rows = [
        {
            "source_code": f"{index:06d}",
            "security_id": f"SH.{index:06d}",
            "platform_rank": index,
            "rank_change": 0,
            "security_name": "来源名称",
            "source_row_order": index,
        }
        for index in range(1, 11)
    ]
    return _result("ths"), {
        "source_id": "TONGHUASHUN_HOT_RANK",
        "list_type": "HOUR_NORMAL",
        "source_as_of": None,
        "time_semantics": "OBSERVED_AT_ONLY_SOURCE_AS_OF_MISSING",
        "rows": rows,
    }


FETCHERS = {"EASTMONEY_HOT_RANK": _eastmoney, "TONGHUASHUN_HOT_RANK": _ths}


def test_direct_hot_rank_returns_ephemeral_rows_with_local_names():
    response = build_hot_rank_direct_response(
        source="EASTMONEY_HOT_RANK",
        root=ROOT,
        page=1,
        page_size=5,
        fetchers=FETCHERS,
        name_lookup=lambda ids: {security_id: f"本地-{security_id}" for security_id in ids},
    )
    assert response["api_contract"] == "M14_HOT_RANK_API_V2_0"
    assert response["storage_scope"] == "EPHEMERAL_ONLINE"
    assert response["local_snapshot_mutated"] is False
    assert response["source_as_of"] == "2026-09-11 15:10:00"
    assert [item["platform_rank"] for item in response["items"]] == [1, 2, 3, 4, 5]
    assert response["items"][0]["security_name"] == "本地-SZ.000001"
    assert response["items"][0]["mapping_status"] == "MAPPED"


def test_direct_hot_rank_keeps_source_views_separate_and_does_not_compare():
    response = build_hot_rank_direct_response(
        source="ALL",
        root=ROOT,
        co_listed=True,
        page_size=2,
        fetchers=FETCHERS,
        name_lookup=lambda ids: {},
    )
    assert response["co_listed"] is True
    assert {view["source_id"] for view in response["source_views"]} == {"EASTMONEY_HOT_RANK", "TONGHUASHUN_HOT_RANK"}
    assert all(view["mode"] == "LATEST" for view in response["source_views"])
    assert all("comparison_batch_id" not in view for view in response["source_views"])


def test_direct_hot_rank_marks_unmapped_rows_without_reordering():
    response = build_hot_rank_direct_response(
        source="EASTMONEY_HOT_RANK",
        root=ROOT,
        page_size=3,
        fetchers=FETCHERS,
        name_lookup=lambda ids: {},
    )
    assert [item["platform_rank"] for item in response["items"]] == [1, 2, 3]
    assert all(item["mapping_status"] == "UNMAPPED" for item in response["items"])
