"""Versioned V4-03 parameter source. Values are never inferred from legacy code."""

import json
from pathlib import Path


PARAMETER_PATH = Path(__file__).resolve().parents[3] / "config" / "v4_03_parameter_set_v1.json"
PARAMETERS = json.loads(PARAMETER_PATH.read_text(encoding="utf-8"))
assert PARAMETERS["parameter_set_id"] == "V4_03_CORE_FACTOR_PARAMETER_SET_V1"
REGISTRY_PATH = PARAMETER_PATH.with_name("v4_03_parameter_registry_v1.json")
REGISTRY = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
REGISTRY_VALUES = {item["parameter_id"]: item["value"] for item in REGISTRY["entries"]}

LITERALS = {
    "core_price_damage_atr_multiple": "V4_03_CORE_PRICE_DAMAGE_ATR_MULTIPLE",
    "market_reference_max_missing_fraction": "V4_03_MARKET_REFERENCE_MAX_MISSING_FRACTION",
}
THRESHOLDS = {
    "market_breadth_axis": "V4_03_MARKET_BREADTH_AXIS_THRESHOLD",
    "market_participation_expanding": "V4_03_MARKET_PARTICIPATION_EXPANDING_THRESHOLD",
    "market_participation_thin": "V4_03_MARKET_PARTICIPATION_THIN_THRESHOLD",
    "market_stress_min_limit_coverage": "V4_03_MARKET_LIMIT_COVERAGE_MINIMUM",
    "market_stress_elevated": "V4_03_MARKET_STRESS_ELEVATED_THRESHOLD",
    "market_stress_high": "V4_03_MARKET_STRESS_HIGH_THRESHOLD",
}


def contract_literal(name: str) -> float:
    value = REGISTRY_VALUES[LITERALS[name]]
    if value != PARAMETERS["contract_literals"][name]:
        raise ValueError(f"parameter registry mismatch: {name}")
    return value


def candidate_threshold(name: str) -> float:
    value = REGISTRY_VALUES[THRESHOLDS[name]]
    if value != PARAMETERS["engineering_candidate_thresholds"][name]:
        raise ValueError(f"parameter registry mismatch: {name}")
    return value
