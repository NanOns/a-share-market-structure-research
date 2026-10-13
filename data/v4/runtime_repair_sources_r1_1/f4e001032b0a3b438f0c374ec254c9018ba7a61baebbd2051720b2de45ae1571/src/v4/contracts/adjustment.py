from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Iterable


@dataclass(frozen=True)
class AffineAction:
    category: int
    ex_date: date
    a: float
    b: float
    source_revision_id: str


def apply_affine(price: float, a: float, b: float) -> float:
    if a <= 0:
        raise ValueError("NON_POSITIVE_ADJUSTMENT_FACTOR")
    return a * price + b


def factors_as_of(actions: Iterable[AffineAction], cutoff: date, supported_categories: set[int]) -> tuple[float, float, str]:
    a_total, b_total = 1.0, 0.0
    for event in sorted((x for x in actions if x.ex_date <= cutoff), key=lambda x: (x.ex_date, x.source_revision_id)):
        if event.category not in supported_categories:
            return 1.0, 0.0, "UNAVAILABLE_UNKNOWN_EVENT_CATEGORY"
        # Compose the newer affine transform with the already accumulated transform.
        a_total, b_total = event.a * a_total, event.a * b_total + event.b
    return a_total, b_total, "AVAILABLE"


def anchor_rebase(value: float, source_a: float, source_b: float, anchor_a: float, anchor_b: float) -> float:
    if source_a <= 0 or anchor_a <= 0:
        raise ValueError("INVALID_COORDINATE_FACTOR")
    raw = (value - source_b) / source_a
    return anchor_a * raw + anchor_b


def forward_to_evaluation_coordinate(value: float, point_a: float, point_b: float, evaluation_a: float, evaluation_b: float) -> float:
    return anchor_rebase(value, point_a, point_b, evaluation_a, evaluation_b)


def complete_technical_window(actual_bars: list[date], as_of: date, required: int) -> str:
    bars = [d for d in actual_bars if d <= as_of]
    return "AVAILABLE" if len(bars) >= required and bars[-1:] == [as_of] else "UNKNOWN_INSUFFICIENT_OR_MISSING_ASOF"
