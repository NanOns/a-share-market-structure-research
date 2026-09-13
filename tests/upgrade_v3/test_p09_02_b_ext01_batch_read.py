from __future__ import annotations

import json

from workbench_online.base import FetchResult, OnlineFetchPolicy
from workbench_online.event_batch import read_ext01_batch


def _page(page: int, *, has_more: bool, rows: list[dict]) -> bytes:
    return json.dumps(
        {
            "status_code": 0,
            "data": {
                "page": {"page": page, "page_size": 20, "total": 21, "has_more": has_more},
                "msg": "",
                "trade_status": 1,
                "limit_up_count": {"today": {"num": 3}},
                "limit_down_count": {"today": {"num": 0}},
                "info": rows,
            },
        }
    ).encode("utf-8")


def _row(code: str, *, price: str = "10.12") -> dict:
    return {
        "code": code,
        "name": f"SYNTHETIC_{code}",
        "latest": price,
        "change_rate": "10.02",
        "amount": "--",
        "order_amount": "--",
        "currency_value": "--",
        "turnover_rate": "--",
        "open_num": 0,
        "reason_type": "synthetic",
        "first_limit_up_time": 1757554260,
        "last_limit_up_time": 0,
        "market_id": 17,
    }


def test_ext01_batch_read_paginates_and_dedupes_same_bundle_without_claiming_raw_storage():
    calls: list[str] = []
    pages = {
        1: _page(1, has_more=True, rows=[_row("600000"), _row("000001")]),
        2: _page(2, has_more=False, rows=[_row("000001"), _row("300001")]),
    }

    def fake_fetcher(url: str, policy: OnlineFetchPolicy) -> FetchResult:
        calls.append(url)
        page = int(url.split("page=", 1)[1].split("&", 1)[0])
        return FetchResult(
            f"2026-09-12T17:28:0{page}+00:00",
            f"2026-09-12T17:28:0{page}+00:00",
            200,
            "application/json",
            pages[page],
            url,
        )

    result = read_ext01_batch(trade_date="20260911", fetcher=fake_fetcher)

    assert result.status == "AVAILABLE"
    assert result.batch_id and result.batch_id.startswith("v3evt-")
    assert result.coverage["complete_pagination"] is True
    assert result.coverage["successful_pages"] == [1, 2]
    assert result.coverage["unique_row_count"] == 3
    assert result.duplicate_count == 1
    assert result.conflict_count == 0
    assert len(result.rows) == 3
    assert all(row.batch_id == result.batch_id for row in result.rows)
    assert result.header is not None and result.header.batch_id == result.batch_id
    assert result.header.counts["source_limit_count"] == 3
    assert result.network_calls == 2
    assert len(calls) == 2
    assert all("limit=200" in url for url in calls)
    assert all("raw" not in key for key in result.to_record())
    assert all("body" not in page.to_record() for page in result.pages)


def test_ext01_batch_read_marks_later_page_failure_as_degraded_partial_not_empty_success():
    calls: list[int] = []

    def fake_fetcher(url: str, policy: OnlineFetchPolicy) -> FetchResult:
        page = int(url.split("page=", 1)[1].split("&", 1)[0])
        calls.append(page)
        if page == 2:
            raise TimeoutError("synthetic timeout")
        return FetchResult(
            "2026-09-12T17:28:09+00:00",
            "2026-09-12T17:28:09+00:00",
            200,
            "application/json",
            _page(1, has_more=True, rows=[_row("600000")]),
            url,
        )

    result = read_ext01_batch(trade_date="20260911", fetcher=fake_fetcher)

    assert result.status == "DEGRADED"
    assert result.rows and result.rows[0].source_code == "SH:600000"
    assert result.coverage["complete_pagination"] is False
    assert result.coverage["failed_pages"] == [2]
    assert "PARTIAL_PAGE_FAILURE" in result.failure_codes
    assert result.header is not None and "BATCH_PARTIAL_OR_UNVERIFIED" in result.header.quality_codes
    assert calls == [1, 2]


def test_ext01_batch_read_fails_closed_when_first_page_is_unavailable():
    def fake_fetcher(url: str, policy: OnlineFetchPolicy) -> FetchResult:
        return FetchResult(
            "2026-09-12T17:28:09+00:00",
            "2026-09-12T17:28:09+00:00",
            403,
            "text/html",
            b"denied",
            url,
        )

    result = read_ext01_batch(trade_date="20260911", fetcher=fake_fetcher)

    assert result.status == "UNAVAILABLE"
    assert result.header is None
    assert result.rows == ()
    assert result.coverage["complete_pagination"] is False
    assert result.failure_codes == ("HTTP_STATUS_403",)
    assert result.next_stage == "P09-01-B-LZ-EXT03"
