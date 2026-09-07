from __future__ import annotations

import math

RULESET_ID = "breakout-prep-v2-shadow-v1.0"
LATE_EXTENSION_IS_NOT_AUTOMATIC_EXCLUSION = True


def range_status(recent, prior, ratio):
    if not all(_finite(value) for value in (recent, prior, ratio)) or float(prior) <= 0:
        return "RANGE_DATA_INSUFFICIENT"
    return "RANGE_CONTRACTED" if float(ratio) < 1.0 else "RANGE_NOT_CONTRACTED"


def vol_status(recent, prior, ratio):
    if not all(_finite(value) for value in (recent, prior, ratio)) or float(prior) <= 0:
        return "VOL_DATA_INSUFFICIENT"
    return "VOL_CONTRACTED" if float(ratio) < 1.0 else "VOL_NOT_CONTRACTED"


def classify(v1_breakout_prep, range_evidence, vol_evidence):
    if not bool(v1_breakout_prep):
        return "OUTSIDE_V1_BREAKOUT_PREP", False
    if "DATA_INSUFFICIENT" in range_evidence or "DATA_INSUFFICIENT" in vol_evidence:
        return "DATA_INSUFFICIENT", False
    range_contracted = range_evidence == "RANGE_CONTRACTED"
    vol_contracted = vol_evidence == "VOL_CONTRACTED"
    if range_contracted and vol_contracted:
        return "BREAKOUT_CORE", True
    if range_contracted:
        return "BREAKOUT_RANGE_ONLY", True
    if vol_contracted:
        return "BREAKOUT_VOL_ONLY", False
    return "NEAR_HIGH_NO_CONTRACTION", False


def _finite(value):
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError):
        return False
