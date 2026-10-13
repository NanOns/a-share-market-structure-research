"""V4-04 explanatory UI projection of accepted V4-03 market axes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

from .profile_core import P


CONTRACT_ID = "MARKET_REGIME_V1"
REQUIRED = ("trend_axis", "breadth_axis", "participation_axis", "stress_level", "stress_change")


@dataclass(frozen=True)
class RegimeUI:
    value: str
    candidate: str
    last_known: str | None
    consecutive_count: int
    evidence: dict
    unknown_reason: str | None
    contract_id: str = CONTRACT_ID


def candidate(row: Mapping) -> str:
    if any(row.get(key) in (None, "UNKNOWN") for key in REQUIRED):
        return "UNKNOWN"
    trend, breadth, stress, change = (row[key] for key in ("trend_axis", "breadth_axis", "stress_level", "stress_change"))
    if trend == "WEAK" and stress == "HIGH":
        return "CAPITULATION"
    if trend == "WEAK" and breadth == "IMPROVING" and change == "DECLINING":
        return "RECOVERY_ATTEMPT"
    if trend == "STRONG" and breadth != "DETERIORATING" and stress == "LOW":
        return "RISK_ON"
    if trend == "WEAK" or stress == "HIGH":
        return "RISK_OFF"
    return "NEUTRAL"


def project(path: Sequence[Mapping]) -> dict[str, RegimeUI]:
    """Replay in market-session order; UNKNOWN shows last-known without claiming today."""
    accepted: str | None = None
    pending: str | None = None
    count = 0
    result = {}
    previous_date = None
    threshold = int(P["REGIME_SWITCH_SESSIONS"])
    for row in path:
        date = row["trade_date"]
        if previous_date is not None and date <= previous_date:
            raise ValueError("market regime path must be unique and ascending")
        previous_date = date
        label = candidate(row)
        if label == "UNKNOWN":
            pending, count = None, 0
            value, reason = "UNKNOWN", "REQUIRED_MARKET_AXIS_UNKNOWN"
        elif label == "CAPITULATION":
            accepted, pending, count = label, None, 0
            value, reason = label, None
        elif label == accepted:
            pending, count = None, 0
            value, reason = label, None
        else:
            count = count + 1 if pending == label else 1
            pending = label
            if count >= threshold:
                accepted, pending, count = label, None, 0
                value, reason = label, None
            else:
                value, reason = accepted or "UNKNOWN", None if accepted else "HYSTERESIS_PENDING_NO_ACCEPTED_LABEL"
        evidence = {key: row.get(key) for key in REQUIRED}
        evidence.update({"candidate": label, "last_known": accepted,
                         "consecutive_count": count, "market_input_digest": row.get("output_digest")})
        result[date] = RegimeUI(value, label, accepted, count, evidence, reason)
    return result
