from workbench_online.lh_list_capability import build_lh_list_view, unavailable_lh_list_view


def test_lh_list_is_fail_closed_without_verified_source():
    view = build_lh_list_view([], source_status="UNAVAILABLE", trade_date="2026-09-11")
    assert view["capability_status"] == "UNAVAILABLE"
    assert view["unavailable_reason"] == "NO_VERIFIED_LH_SOURCE"
    assert view["items"] == []
    assert view["batch_id"] is None


def test_lh_list_requires_trade_date_not_after_publication():
    item = {
        "evidence_id": "lh1", "source_id": "licensed-source", "security_id": "SZ.000001", "source_code": "000001",
        "trade_date": "2026-09-12", "published_at": "2026-09-11T10:00:00+00:00",
        "first_seen_at": "2026-09-11T10:01:00+00:00", "raw_ref": "raw/lh1", "source_url": "https://example.invalid/lh1",
        "seat_name": "席位", "buy_amount": None, "sell_amount": None, "amount_unit": "CNY",
    }
    try:
        build_lh_list_view([item], source_status="ENABLED")
    except ValueError as exc:
        assert str(exc) == "LH_TRADE_DATE_AFTER_PUBLICATION"
    else:
        raise AssertionError("future trade date must be rejected")


def test_lh_list_rejects_evidence_after_as_of():
    item = {
        "evidence_id": "lh1", "source_id": "licensed-source", "security_id": "SZ.000001", "source_code": "000001",
        "trade_date": "2026-09-11", "published_at": "2026-09-11T10:00:00+00:00",
        "first_seen_at": "2026-09-11T10:01:00+00:00", "raw_ref": "raw/lh1", "source_url": "https://example.invalid/lh1",
        "seat_name": "席位", "buy_amount": None, "sell_amount": None, "amount_unit": "CNY",
    }
    try:
        build_lh_list_view([item], source_status="ENABLED", as_of="2026-09-11T10:00:30+00:00")
    except ValueError as exc:
        assert str(exc) == "LH_AFTER_AS_OF"
    else:
        raise AssertionError("evidence after as_of must be rejected")


def test_lh_list_requires_seat_trade_fields_and_amount_unit():
    item = {
        "evidence_id": "lh1", "source_id": "licensed-source", "security_id": "SZ.000001", "source_code": "000001",
        "trade_date": "2026-09-11", "published_at": "2026-09-11T10:00:00+00:00",
        "first_seen_at": "2026-09-11T10:01:00+00:00", "raw_ref": "raw/lh1", "source_url": "https://example.invalid/lh1",
    }
    try:
        build_lh_list_view([item], source_status="ENABLED")
    except ValueError as exc:
        assert str(exc) == "LH_SCHEMA_INVALID"
    else:
        raise AssertionError("seat and trade fields must be required")


def test_lh_list_rejects_non_http_source_url():
    item = {
        "evidence_id": "lh1", "source_id": "licensed-source", "security_id": "SZ.000001", "source_code": "000001",
        "trade_date": "2026-09-11", "published_at": "2026-09-11T10:00:00+00:00",
        "first_seen_at": "2026-09-11T10:01:00+00:00", "raw_ref": "raw/lh1", "source_url": "javascript:bad",
        "seat_name": "席位", "buy_amount": None, "sell_amount": None, "amount_unit": "CNY",
    }
    try:
        build_lh_list_view([item], source_status="ENABLED")
    except ValueError as exc:
        assert str(exc) == "LH_SOURCE_URL_INVALID"
    else:
        raise AssertionError("non-http source URL must be rejected")


def test_lh_unavailable_view_keeps_trade_date_and_as_of_explicit():
    view = unavailable_lh_list_view(trade_date="2026-09-11", as_of="2026-09-11T12:00:00+00:00")
    assert view["trade_date"] == "2026-09-11"
    assert view["as_of"] == "2026-09-11T12:00:00+00:00"
    assert view["items"] == []
