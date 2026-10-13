from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import Iterable


TEN = Decimal("10")


class ActionType(str, Enum):
    CASH_DIVIDEND = "CASH_DIVIDEND"
    SHARE_BONUS = "SHARE_BONUS_OR_CAPITALIZATION"
    RIGHTS_ISSUE = "RIGHTS_ISSUE"
    COMBINED = "COMBINED"
    UNKNOWN = "UNKNOWN_ACTION_TYPE"


@dataclass(frozen=True)
class CorporateAction:
    effective_date: int
    cash_dividend_per_10: Decimal = Decimal("0")
    rights_shares_per_10: Decimal = Decimal("0")
    rights_price: Decimal = Decimal("0")
    bonus_shares_per_10: Decimal = Decimal("0")
    action_type: ActionType = ActionType.COMBINED

    def validate(self) -> None:
        if self.action_type is ActionType.UNKNOWN:
            raise ValueError("unknown corporate action cannot be applied")
        values = (
            self.cash_dividend_per_10,
            self.rights_shares_per_10,
            self.rights_price,
            self.bonus_shares_per_10,
        )
        if any(value < 0 for value in values):
            raise ValueError("corporate action parameters must be non-negative")
        if TEN + self.rights_shares_per_10 + self.bonus_shares_per_10 <= 0:
            raise ValueError("invalid share denominator")


@dataclass(frozen=True)
class AffineTransform:
    price_mul: Decimal = Decimal("1")
    price_add: Decimal = Decimal("0")

    def apply(self, value: Decimal) -> Decimal:
        return self.price_mul * value + self.price_add

    def then(self, later: "AffineTransform") -> "AffineTransform":
        """Compose self followed by a later event transform."""
        return AffineTransform(
            price_mul=later.price_mul * self.price_mul,
            price_add=later.price_mul * self.price_add + later.price_add,
        )


def event_transform(action: CorporateAction) -> AffineTransform:
    """Return pre-event raw price -> event-date theoretical ex-price transform.

    The local units follow the upstream mootdx formula: cash dividend, rights
    shares, and bonus shares are quoted per 10 existing shares.
    """
    action.validate()
    denominator = TEN + action.rights_shares_per_10 + action.bonus_shares_per_10
    return AffineTransform(
        price_mul=TEN / denominator,
        price_add=(action.rights_shares_per_10 * action.rights_price - action.cash_dividend_per_10)
        / denominator,
    )


def compose_forward_adjustment(actions: Iterable[CorporateAction]) -> AffineTransform:
    transform = AffineTransform()
    for action in sorted(actions, key=lambda item: item.effective_date):
        transform = transform.then(event_transform(action))
    return transform


def adjust_ohlc(
    ohlc: dict[str, Decimal], actions: Iterable[CorporateAction]
) -> dict[str, Decimal]:
    transform = compose_forward_adjustment(actions)
    return {field: transform.apply(ohlc[field]) for field in ("open", "high", "low", "close")}


def adjustment_history_changed(before_sha256: str, after_sha256: str) -> bool:
    return before_sha256 != after_sha256

