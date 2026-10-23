import pytest

from workbench_analysis.r43_structure_replay import conserve_lifecycle_status_rows


def test_lifecycle_only_new_or_no_history_identity_is_retained_without_a_bar():
    lifecycle = [
        {"security_id": "sid-traded", "trade_date": "2026-10-22", "status": "ACTUAL_TRADED"},
        {"security_id": "sid-new", "trade_date": "2026-10-22", "status": "SUSPENDED"},
        {"security_id": "sid-unknown", "trade_date": "2026-10-22", "status": "UNKNOWN_SOURCE_VALUE"},
    ]
    projected = conserve_lifecycle_status_rows(
        [{"security_id": "sid-traded", "trade_date": "2026-10-22",
          "status": "ACTUAL_TRADED", "actual_bar_present": True}],
        lifecycle,
        trade_date="2026-10-22",
        raw_rows=[],
    )

    by_id = {row["security_id"]: row for row in projected}
    assert set(by_id) == {"sid-traded", "sid-new", "sid-unknown"}
    assert by_id["sid-new"]["status"] == "SUSPENDED"
    assert by_id["sid-new"]["actual_bar_present"] is False
    assert by_id["sid-new"]["lifecycle_only"] is True
    assert by_id["sid-unknown"]["status"] == "UNKNOWN"
    assert by_id["sid-unknown"]["actual_bar_present"] is False
    assert by_id["sid-traded"]["status"] == "ACTUAL_TRADED"
    assert by_id["sid-traded"]["actual_bar_present"] is False
    assert by_id["sid-traded"]["reason"] == "RAW_BAR_RECEIPT_NOT_FOUND_FOR_DATE_AND_SECURITY"


def test_lifecycle_only_actual_traded_requires_same_day_same_security_raw_bar():
    lifecycle = [{"security_id": "sid-a", "trade_date": "2026-10-22", "status": "ACTUAL_TRADED"}]
    raw = [{"security_id": "sid-a", "trade_date": "2026-10-22"}]
    projected = conserve_lifecycle_status_rows([], lifecycle, trade_date="2026-10-22", raw_rows=raw)
    assert projected[0]["actual_bar_present"] is True


def test_raw_bar_presence_is_independent_of_lifecycle_status():
    lifecycle = [{"security_id": "sid-a", "trade_date": "2026-10-22", "status": "SUSPENDED"}]
    raw = [{"security_id": "sid-a", "trade_date": "2026-10-22"}]
    projected = conserve_lifecycle_status_rows([], lifecycle, trade_date="2026-10-22", raw_rows=raw)
    assert projected[0]["status"] == "SUSPENDED"
    assert projected[0]["actual_bar_present"] is True
    assert projected[0]["status_conflict"] is True


@pytest.mark.parametrize("raw", [
    [{"security_id": "sid-other", "trade_date": "2026-10-22"}],
    [{"security_id": "sid-a", "trade_date": "2026-10-21"}],
])
def test_lifecycle_only_actual_traded_rejects_wrong_security_or_day_raw_bar(raw):
    lifecycle = [{"security_id": "sid-a", "trade_date": "2026-10-22", "status": "ACTUAL_TRADED"}]
    projected = conserve_lifecycle_status_rows([], lifecycle, trade_date="2026-10-22", raw_rows=raw if raw[0]["trade_date"] == "2026-10-22" else [])
    assert projected[0]["status"] == "ACTUAL_TRADED"
    assert projected[0]["actual_bar_present"] is False


def test_raw_receipt_with_wrong_date_is_rejected():
    lifecycle = [{"security_id": "sid-a", "trade_date": "2026-10-22", "status": "ACTUAL_TRADED"}]
    with pytest.raises(ValueError, match="LIFECYCLE_RAW_BAR_IDENTITY_DUPLICATE_OR_DATE_MISMATCH"):
        conserve_lifecycle_status_rows([], lifecycle, trade_date="2026-10-22",
            raw_rows=[{"security_id": "sid-a", "trade_date": "2026-10-21"}])


def test_lifecycle_projection_rejects_duplicate_source_identities():
    lifecycle = [
        {"security_id": "sid-a", "trade_date": "2026-10-22", "status": "SUSPENDED"},
        {"security_id": "sid-a", "trade_date": "2026-10-22", "status": "ACTUAL_TRADED"},
    ]
    try:
        conserve_lifecycle_status_rows([], lifecycle, trade_date="2026-10-22")
    except ValueError as exc:
        assert str(exc) == "LIFECYCLE_SOURCE_IDENTITY_DUPLICATE_OR_DATE_MISMATCH"
    else:
        raise AssertionError("duplicate security identity must fail closed")


def test_lifecycle_projection_rejects_status_from_another_date():
    with pytest.raises(ValueError, match="LIFECYCLE_STATUS_DATE_MISMATCH"):
        conserve_lifecycle_status_rows(
            [{"security_id": "sid-old", "trade_date": "2026-10-21",
              "status": "ACTUAL_TRADED", "actual_bar_present": True}],
            [{"security_id": "sid-old", "trade_date": "2026-10-22", "status": "ACTUAL_TRADED"}],
            trade_date="2026-10-22",
        )


def test_lifecycle_projection_normalizes_unsupported_status_and_clears_bar_claim():
    projected = conserve_lifecycle_status_rows(
        [{"security_id": "sid-unknown", "trade_date": "2026-10-22",
          "status": "UNRECOGNIZED", "actual_bar_present": True}],
        [{"security_id": "sid-unknown", "trade_date": "2026-10-22", "status": "UNRECOGNIZED"}],
        trade_date="2026-10-22",
    )
    assert projected[0]["status"] == "UNKNOWN"
    assert projected[0]["actual_bar_present"] is False
