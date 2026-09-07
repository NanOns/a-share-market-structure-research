from __future__ import annotations

import math

RULESET_ID = "steady-trend-v2-shadow-v1.0"
LIMIT_UP_IS_NOT_AN_EXCLUSION = True


def continuity_class(value, valid_count, valid_ratio):
    if not _finite(value) or not _finite(valid_count) or not _finite(valid_ratio):
        return "CONTINUITY_DATA_INSUFFICIENT"
    if int(valid_count) < 15 or float(valid_ratio) < 0.75:
        return "CONTINUITY_DATA_INSUFFICIENT"
    value = float(value)
    if value >= 0.60:
        return "CONTINUITY_STRONG"
    if value >= 0.50:
        return "CONTINUITY_MODERATE"
    return "CONTINUITY_WEAK"


def pulse_class(value):
    if not _finite(value):
        return "PULSE_DATA_INSUFFICIENT"
    value = float(value)
    if value <= 0.35:
        return "PULSE_LOW"
    if value <= 0.50:
        return "PULSE_MODERATE"
    return "PULSE_HIGH"


def classify(v1_steady_trend, continuity, pulse):
    if not bool(v1_steady_trend):
        return "OUTSIDE_V1_STEADY", False
    if continuity == "CONTINUITY_DATA_INSUFFICIENT" or pulse == "PULSE_DATA_INSUFFICIENT":
        return "DATA_INSUFFICIENT", False
    if pulse == "PULSE_HIGH":
        return "PULSE_DOMINATED", False
    if continuity == "CONTINUITY_STRONG":
        return "STEADY_CORE", True
    if continuity == "CONTINUITY_MODERATE":
        return "STEADY_ACCEPTABLE", True
    return "CONTINUITY_WEAK", False


def _finite(value):
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError):
        return False
