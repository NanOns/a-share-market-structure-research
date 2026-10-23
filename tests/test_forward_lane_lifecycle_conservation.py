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
    )

    by_id = {row["security_id"]: row for row in projected}
    assert set(by_id) == {"sid-traded", "sid-new", "sid-unknown"}
    assert by_id["sid-new"]["status"] == "SUSPENDED"
    assert by_id["sid-new"]["actual_bar_present"] is False
    assert by_id["sid-new"]["lifecycle_only"] is True
    assert by_id["sid-unknown"]["status"] == "UNKNOWN"
    assert by_id["sid-unknown"]["actual_bar_present"] is False


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
