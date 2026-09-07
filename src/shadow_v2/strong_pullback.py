from __future__ import annotations

import math

RULESET_ID = "strong-pullback-v2-shadow-v1.1-latest-peak-exclusive-segments"
VOLUME_NOT_CONTRACTED_IS_NOT_AUTOMATIC_EXCLUSION = True


def segment_status(days_since_peak):
    if not _finite(days_since_peak):
        return "SEGMENT_DATA_INSUFFICIENT"
    days = int(days_since_peak)
    if days == 0:
        return "NO_PULLBACK_SEGMENT"
    if days == 1:
        return "EARLY_PULLBACK"
    return "ESTABLISHED_PULLBACK"


def depth_status(drawdown):
    if not _finite(drawdown):
        return "DEPTH_DATA_INSUFFICIENT"
    value = float(drawdown)
    if value > -0.03:
        return "DEPTH_TOO_SHALLOW"
    if value < -0.18:
        return "DEPTH_TOO_DEEP"
    return "DEPTH_IN_V1_BAND"


def volume_status(advance_mean, pullback_mean, ratio):
    if not all(_finite(v) for v in (advance_mean, pullback_mean, ratio)):
        return "VOLUME_DATA_INSUFFICIENT"
    return "VOLUME_CONTRACTED" if float(ratio) < 1.0 else "VOLUME_NOT_CONTRACTED"


def classify(v1_strong_pullback, segment, depth, volume):
    if not bool(v1_strong_pullback):
        return "OUTSIDE_V1_STRONG_PULLBACK", False, False
    if "DATA_INSUFFICIENT" in segment or "DATA_INSUFFICIENT" in depth or "DATA_INSUFFICIENT" in volume:
        return "DATA_INSUFFICIENT", False, False
    if depth != "DEPTH_IN_V1_BAND":
        return "DEPTH_MISMATCH", False, False
    if segment != "ESTABLISHED_PULLBACK":
        return "EARLY_PULLBACK", False, False
    if volume == "VOLUME_CONTRACTED":
        return "PULLBACK_CORE", True, True
    return "PULLBACK_STRUCTURE_ONLY", True, False


def _finite(value):
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError):
        return False
