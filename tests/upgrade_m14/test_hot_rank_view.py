from workbench_online.hot_rank_view import build_hot_rank_view


def _batch(batch_id, source_as_of, observed_at, rows, source_id="EASTMONEY_HOT_RANK"):
    return {
        "batch_id": batch_id,
        "source_id": source_id,
        "dataset": "HOT_RANKINGS",
        "list_type": "A_STOCK_HOT_RANK",
        "page": 1,
        "source_as_of": source_as_of,
        "observed_at_utc": observed_at,
        "personal_research_only": True,
        "publication_enabled": False,
        "rows": rows,
    }


def _row(code, rank, security_id=None, source_change=0):
    return {
        "source_code": code,
        "security_id": security_id or f"SH.{code}",
        "platform_rank": rank,
        "source_row_order": rank,
        "rank_change": source_change,
        "security_name": None,
    }


def test_hot_rank_view_keeps_platform_order_and_calculates_previous_capture_delta():
    previous = _batch(
        "b1",
        "2026-09-11 14:00:00",
        "2026-09-11T06:00:01+00:00",
        [_row("000001", 1), _row("000002", 2)],
    )
    current = _batch(
        "b2",
        "2026-09-11 14:10:00",
        "2026-09-11T06:10:01+00:00",
        [_row("000002", 1, source_change=99), _row("000001", 2, source_change=-99)],
    )
    view = build_hot_rank_view([previous, current], source_id="EASTMONEY_HOT_RANK")
    assert view["comparison_status"] == "COMPARABLE"
    assert view["comparison_batch_id"] == "b1"
    assert [row["platform_rank"] for row in view["rows"]] == [1, 2]
    assert [row["previous_rank"] for row in view["rows"]] == [2, 1]
    assert [row["rank_delta"] for row in view["rows"]] == [1, -1]
    assert [row["source_rank_change"] for row in view["rows"]] == [99, -99]


def test_hot_rank_view_blocks_comparison_outside_fifteen_minute_window():
    previous = _batch("b1", "2026-09-11 13:00:00", "2026-09-11T05:00:01+00:00", [_row("000001", 1)])
    current_row = _row("000001", 2)
    current_row["source_row_order"] = 1
    current = _batch("b2", "2026-09-11 13:16:00", "2026-09-11T05:16:01+00:00", [current_row])
    view = build_hot_rank_view([previous, current], source_id="EASTMONEY_HOT_RANK")
    assert view["comparison_status"] == "UNAVAILABLE_COMPARISON_WINDOW_EXCEEDED"
    assert view["comparison_batch_id"] is None
    assert view["rows"][0]["previous_rank"] is None


def test_hot_rank_view_does_not_fabricate_comparison_without_source_time():
    batch = _batch("b1", None, "2026-09-11T06:00:01+00:00", [_row("000001", 1)], source_id="TONGHUASHUN_HOT_RANK")
    view = build_hot_rank_view([batch], source_id="TONGHUASHUN_HOT_RANK")
    assert view["time_semantics"] == "OBSERVED_AT_ONLY"
    assert view["comparison_status"] == "UNAVAILABLE_SOURCE_AS_OF_MISSING"
    assert view["rows"][0]["rank_delta"] is None


def test_hot_rank_view_rejects_duplicate_source_codes():
    batch = _batch(
        "b1",
        "2026-09-11 14:00:00",
        "2026-09-11T06:00:01+00:00",
        [_row("000001", 1), _row("000001", 2)],
    )
    try:
        build_hot_rank_view([batch], source_id="EASTMONEY_HOT_RANK")
    except ValueError as exc:
        assert str(exc) == "HOT_RANK_DUPLICATE_SOURCE_CODE"
    else:
        raise AssertionError("duplicate source codes must be rejected")
