from datetime import date

import pytest

from v4.contracts.adjustment import AffineAction, anchor_rebase, apply_affine, complete_technical_window, factors_as_of, forward_to_evaluation_coordinate


def test_cash_dividend_stock_split_rights_combo_and_control_vectors():
    # Affine vectors are contract-level known answers, in a common price unit.
    assert apply_affine(10.0, 1.0, -0.5) == 9.5  # cash dividend
    assert apply_affine(10.0, 0.5, 0.0) == 5.0   # 1:1 stock dividend/split
    assert apply_affine(10.0, 0.6, 0.0) == 6.0   # rights theoretical ex-right coordinate
    combined = apply_affine(10.0, 0.6, -0.3)
    assert combined == pytest.approx(5.7)
    assert apply_affine(10.0, 1.0, 0.0) == 10.0  # no-action control


def test_future_ex_date_is_excluded_and_unknown_category_fails_closed():
    actions = [
        AffineAction(1, date(2026, 1, 2), 1, -0.5, "cash"),
        AffineAction(15, date(2026, 2, 2), 0.5, 0, "unknown"),
    ]
    a, b, status = factors_as_of(actions, date(2026, 1, 31), {1})
    assert (a, b, status) == (1, -0.5, "AVAILABLE")
    a, b, status = factors_as_of(actions, date(2026, 2, 3), {1})
    assert status == "UNAVAILABLE_UNKNOWN_EVENT_CATEGORY"
    assert (a, b) == (1, 0)


def test_suspension_resume_recent_listing_anchor_and_forward_coordinates():
    # A confirmed suspension is represented by absent actual bars; it does not extend a fixed window.
    bars = [date(2026, 1, 1), date(2026, 1, 2), date(2026, 1, 5)]
    assert complete_technical_window(bars, date(2026, 1, 5), 3) == "AVAILABLE"
    assert complete_technical_window(bars[:2], date(2026, 1, 5), 3) == "UNKNOWN_INSUFFICIENT_OR_MISSING_ASOF"
    assert anchor_rebase(7.0, 0.5, 0.0, 1.0, -0.5) == 13.5
    points = [10.0, 11.0, 12.0]
    common = [forward_to_evaluation_coordinate(x, 0.5, 0.0, 1.0, -0.5) for x in points]
    assert common == [19.5, 21.5, 23.5]
