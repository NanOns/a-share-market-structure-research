from workbench_online.quotes_capability import build_quote_view, unavailable_quote_view


def test_quote_capability_is_not_verified_and_does_not_use_hot_rank_rows():
    view = build_quote_view([{"code": "000001", "rank": 1}], source_status="NOT_VERIFIED", security_ids=["SZ.000001"])
    assert view["capability_status"] == "NOT_VERIFIED"
    assert view["unavailable_reason"] == "NO_VERIFIED_QUOTE_SOURCE"
    assert view["items"] == []
    assert view["batch_id"] is None


def test_quote_as_of_requires_no_future_quote():
    item = {
        "source_id": "licensed-source", "source_code": "000001", "security_id": "SZ.000001",
        "quote_time": "2026-09-11T03:01:00+00:00", "price": 10, "ret1": 0.01,
        "amount": 100, "volume": 10, "quote_state": "VALID", "price_unit": "CNY",
        "amount_unit": "CNY", "volume_unit": "SHARES",
    }
    try:
        build_quote_view([item], source_status="ENABLED", as_of="2026-09-11T03:00:00+00:00")
    except ValueError as exc:
        assert str(exc) == "QUOTE_AFTER_AS_OF"
    else:
        raise AssertionError("future quote must be rejected")


def test_quote_requires_explicit_units_and_mapping_identity():
    item = {
        "source_id": "licensed-source", "source_code": "000001", "security_id": "",
        "quote_time": "2026-09-11T03:00:00+00:00", "price": 10, "ret1": 0.01,
        "amount": 100, "volume": 10, "quote_state": "VALID", "price_unit": "CNY",
        "amount_unit": "", "volume_unit": "SHARES",
    }
    try:
        build_quote_view([item], source_status="ENABLED")
    except ValueError as exc:
        assert str(exc) == "QUOTE_IDENTITY_OR_UNIT_MISSING"
    else:
        raise AssertionError("missing identity/unit must be rejected")


def test_unavailable_quote_view_has_explicit_empty_state():
    view = unavailable_quote_view(security_ids=["SH.600000"], as_of="2026-09-11T03:00:00+00:00")
    assert view["dataset"] == "QUOTES_LATEST"
    assert view["source_as_of"] is None
    assert view["items"] == []
