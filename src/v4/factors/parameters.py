"""Versioned V4-03 parameter source. Values are never inferred from legacy code."""

import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
from workbench_db.v4_historical_source_ingress_pg_r1 import read_path_bytes
# Runtime parameter content is selected by the approved immutable source
# bindings carried by V4_OPERATIONAL_DAILY_EXACT_RELEASE_POLICY_V2. Resolve
# those exact content-addressed paths from PostgreSQL; the mutable checkout
# config path is not a storage locator.
PARAMETER_SOURCE_PATH = (
    "data/v4/runtime_repair_sources_r1_1/"
    "2f3cc8ae2fdf4bffc098dc1a0dc90bf05bbb12557b45ea8ddc50048410314e18/"
    "config/v4_03_parameter_set_v1.json"
)
PARAMETER_SOURCE_SHA256 = "2f3cc8ae2fdf4bffc098dc1a0dc90bf05bbb12557b45ea8ddc50048410314e18"
PARAMETER_PATH = read_path_bytes(
    PROJECT_ROOT, PARAMETER_SOURCE_PATH, expected_sha256=PARAMETER_SOURCE_SHA256
)
PARAMETERS = json.loads(PARAMETER_PATH.read_text(encoding="utf-8"))
assert PARAMETERS["parameter_set_id"] == "V4_03_CORE_FACTOR_PARAMETER_SET_V1"
REGISTRY_SOURCE_PATH = (
    "data/v4/runtime_repair_sources_r1_1/"
    "c3cda61e604948935061b077f0f57777ac9dc9917263cab2217ca3c2ac9f28e3/"
    "config/v4_03_parameter_registry_v1.json"
)
REGISTRY_SOURCE_SHA256 = "c3cda61e604948935061b077f0f57777ac9dc9917263cab2217ca3c2ac9f28e3"
REGISTRY_PATH = read_path_bytes(
    PROJECT_ROOT, REGISTRY_SOURCE_PATH, expected_sha256=REGISTRY_SOURCE_SHA256
)
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
