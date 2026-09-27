from __future__ import annotations

"""Fail-closed previous official close state for dated price-limit evaluation."""

from dataclasses import dataclass
from decimal import Decimal
from typing import Callable, Iterable


@dataclass
class PreviousCloseState:
    value: Decimal | None
    blocked_by: str | None = None

    @classmethod
    def known(cls, value: Decimal | str | int) -> "PreviousCloseState":
        return cls(Decimal(str(value)))

    def apply_actions(
        self,
        actions: Iterable[tuple[str, object | None]],
        transform: Callable[[Decimal, list[object]], Decimal],
    ) -> Decimal | None:
        """Apply a session's price-impact events before evaluating its limit."""
        actions = list(actions)
        if any(disposition in {"UNKNOWN_PRICE_IMPACT", "PRICE_AFFECTING_UNSUPPORTED"}
               for disposition, _ in actions):
            self.value = None
            self.blocked_by = "REFERENCE_CHAIN_BLOCKED_BY_UNSUPPORTED_ACTION"
            return None
        supported = [event for disposition, event in actions
                     if disposition in {"SUPPORTED_PRICE_TRANSFORM", "PRICE_AFFECTING_SUPPORTED"}
                     and event is not None]
        if supported and self.value is not None:
            try:
                self.value = transform(self.value, supported)
                self.blocked_by = None
            except Exception:
                self.value = None
                self.blocked_by = "REFERENCE_STATE_UNAVAILABLE"
        return self.value

    def unknown_reason(self) -> str:
        return self.blocked_by or "REFERENCE_STATE_UNAVAILABLE"

    def observe_actual_close(self, close: Decimal | str | int) -> None:
        """An actual close establishes a trustworthy coordinate for the next session."""
        self.value = Decimal(str(close))
        self.blocked_by = None

    def carry_no_trade(self) -> None:
        """Suspension/no trade leaves the last official close reference unchanged."""
        return None

    def invalidate(self, reason: str = "REFERENCE_STATE_UNAVAILABLE") -> None:
        self.value = None
        self.blocked_by = reason
