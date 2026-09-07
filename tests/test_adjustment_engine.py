from __future__ import annotations

from decimal import Decimal

import pytest

from adjustment.engine import (
    ActionType,
    CorporateAction,
    adjust_ohlc,
    compose_forward_adjustment,
    event_transform,
)


def test_cash_dividend_sample() -> None:
    action = CorporateAction(
        effective_date=20260101,
        cash_dividend_per_10=Decimal("2"),
        action_type=ActionType.CASH_DIVIDEND,
    )
    transform = event_transform(action)
    assert transform.price_mul == Decimal("1")
    assert transform.apply(Decimal("20")) == Decimal("19.8")


def test_share_bonus_sample() -> None:
    action = CorporateAction(
        effective_date=20260101,
        bonus_shares_per_10=Decimal("5"),
        action_type=ActionType.SHARE_BONUS,
    )
    assert event_transform(action).apply(Decimal("30")) == Decimal("20")


def test_rights_issue_sample() -> None:
    action = CorporateAction(
        effective_date=20260101,
        rights_shares_per_10=Decimal("2"),
        rights_price=Decimal("8"),
        action_type=ActionType.RIGHTS_ISSUE,
    )
    assert event_transform(action).apply(Decimal("20")) == Decimal("18")


def test_multiple_actions_are_affine_and_ohlc_consistent() -> None:
    actions = [
        CorporateAction(20260101, cash_dividend_per_10=Decimal("1")),
        CorporateAction(20260701, bonus_shares_per_10=Decimal("2")),
    ]
    transform = compose_forward_adjustment(actions)
    adjusted = adjust_ohlc(
        {field: Decimal(value) for field, value in {"open": "10", "high": "12", "low": "9", "close": "11"}.items()},
        actions,
    )
    assert adjusted["high"] == transform.apply(Decimal("12"))
    assert adjusted["low"] == transform.apply(Decimal("9"))
    assert adjusted["high"] >= adjusted["open"] >= adjusted["low"]


def test_no_action_control_is_identity() -> None:
    transform = compose_forward_adjustment([])
    assert transform.apply(Decimal("12.34")) == Decimal("12.34")


def test_unknown_action_is_rejected() -> None:
    with pytest.raises(ValueError, match="unknown"):
        event_transform(CorporateAction(20260101, action_type=ActionType.UNKNOWN))

