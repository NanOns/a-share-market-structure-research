import threading
import time
from pathlib import Path

import workbench_service.online_hot_rank as hot_rank
from workbench_online.base import FetchResult
from workbench_service.online_hot_rank import build_hot_rank_direct_response


ROOT = Path(__file__).parents[2]


def _result(source: str) -> FetchResult:
    return FetchResult(
        requested_at_utc="2026-09-12T01:00:00+00:00",
        received_at_utc="2026-09-12T01:00:01+00:00",
        status_code=200,
        content_type="application/json",
        body=source.encode("utf-8"),
        url="https://example.test/hot-rank",
    )


def _rows(start: int, count: int) -> list[dict]:
    return [
        {
            "source_code": f"{index:06d}",
            "security_id": f"SZ.{index:06d}",
            "platform_rank": index,
            "rank_change": 0,
            "security_name": f"来源-{index}",
            "source_row_order": index,
        }
        for index in range(start, start + count)
    ]


def test_local_pagination_slices_before_quote_and_keeps_total():
    quote_ids = []

    def full_source(policy):
        rows = _rows(1, 100)
        return _result("full"), {
            "source_id": "TONGHUASHUN_HOT_RANK",
            "list_type": "HOUR_NORMAL",
            "source_as_of": None,
            "time_semantics": "OBSERVED_AT_ONLY_SOURCE_AS_OF_MISSING",
            "upstream_paged": False,
            "upstream_total": 100,
            "rows": rows,
        }

    def quote_fetcher(ids, policy):
        quote_ids.extend(ids)
        return _result("quotes"), []

    response = build_hot_rank_direct_response(
        root=ROOT,
        source="TONGHUASHUN_HOT_RANK",
        page=2,
        page_size=20,
        fetchers={"TONGHUASHUN_HOT_RANK": full_source},
        quote_fetcher=quote_fetcher,
    )

    assert response["total"] == 100
    assert response["returned_count"] == 20
    assert response["has_more"] is True
    assert [item["platform_rank"] for item in response["items"]] == list(range(21, 41))
    assert [item["platform_rank"] for item in response["items"]] == [int(value.split(".")[-1]) for value in quote_ids]


def test_upstream_page_is_not_offset_again():
    def upstream_page(policy, *, page=1):
        assert page == 2
        return _result("upstream"), {
            "source_id": "EASTMONEY_HOT_RANK",
            "list_type": "A_STOCK_HOT_RANK",
            "source_as_of": "2026-09-12 15:00:00",
            "time_semantics": "SOURCE_EXACT_TIME",
            "upstream_paged": True,
            "upstream_total": None,
            "upstream_has_more": None,
            "rows": _rows(51, 20),
        }

    response = build_hot_rank_direct_response(
        root=ROOT,
        source="EASTMONEY_HOT_RANK",
        page=2,
        page_size=20,
        fetchers={"EASTMONEY_HOT_RANK": upstream_page},
    )

    assert response["total"] is None
    assert response["items"][0]["platform_rank"] == 51
    assert response["returned_count"] == 20


def test_all_sources_run_independently_and_report_partial_failure():
    def failed_source(policy, *, page=1):
        raise ValueError("SOURCE_A_DOWN")

    def healthy_source(policy):
        return _result("healthy"), {
            "source_id": "TONGHUASHUN_HOT_RANK",
            "list_type": "HOUR_NORMAL",
            "source_as_of": None,
            "time_semantics": "OBSERVED_AT_ONLY_SOURCE_AS_OF_MISSING",
            "upstream_paged": False,
            "upstream_total": 1,
            "rows": _rows(1, 1),
        }

    response = build_hot_rank_direct_response(
        root=ROOT,
        source="ALL",
        page_size=20,
        fetchers={
            "EASTMONEY_HOT_RANK": failed_source,
            "TONGHUASHUN_HOT_RANK": healthy_source,
        },
    )
    views = {view["source_id"]: view for view in response["source_views"]}

    assert response["status"] == "PARTIAL"
    assert views["EASTMONEY_HOT_RANK"]["status"] == "UNAVAILABLE"
    assert views["EASTMONEY_HOT_RANK"]["error_code"] == "SOURCE_A_DOWN"
    assert views["TONGHUASHUN_HOT_RANK"]["status"] == "READY"
    assert len(views["TONGHUASHUN_HOT_RANK"]["items"]) == 1


def test_all_sources_are_submitted_concurrently():
    started_count = 0
    started_lock = threading.Lock()
    both_started = threading.Event()

    def source(policy, **kwargs):
        nonlocal started_count
        with started_lock:
            started_count += 1
            if started_count == 2:
                both_started.set()
        if not both_started.wait(timeout=0.5):
            raise ValueError("NOT_CONCURRENT")
        return _result("parallel"), {
            "source_id": "EASTMONEY_HOT_RANK",
            "list_type": "A_STOCK_HOT_RANK",
            "source_as_of": None,
            "time_semantics": "SOURCE_EXACT_TIME",
            "upstream_paged": True,
            "upstream_total": None,
            "rows": _rows(1, 1),
        }

    response = build_hot_rank_direct_response(
        root=ROOT,
        source="ALL",
        fetchers={"EASTMONEY_HOT_RANK": source, "TONGHUASHUN_HOT_RANK": source},
    )

    assert response["status"] == "READY"
    assert all(view["status"] == "READY" for view in response["source_views"])


def test_total_timeout_fails_only_the_slow_source(monkeypatch):
    monkeypatch.setattr(hot_rank, "ONLINE_TOTAL_TIMEOUT_SECONDS", 0.02)

    def slow_source(policy, **kwargs):
        time.sleep(0.2)
        return _result("slow"), {"rows": _rows(1, 1), "upstream_paged": True}

    response = build_hot_rank_direct_response(
        root=ROOT,
        source="ALL",
        fetchers={"EASTMONEY_HOT_RANK": slow_source, "TONGHUASHUN_HOT_RANK": slow_source},
    )

    assert response["status"] == "UNAVAILABLE"
    assert all(view["error_code"] == "UPSTREAM_TIMEOUT" for view in response["source_views"])
