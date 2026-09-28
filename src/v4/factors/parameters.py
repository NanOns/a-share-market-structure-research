"""Versioned V4-03 parameter source. Values are never inferred from legacy code."""

import json
from pathlib import Path


PARAMETER_PATH = Path(__file__).resolve().parents[3] / "config" / "v4_03_parameter_set_v1.json"
PARAMETERS = json.loads(PARAMETER_PATH.read_text(encoding="utf-8"))
assert PARAMETERS["parameter_set_id"] == "V4_03_CORE_FACTOR_PARAMETER_SET_V1"


def contract_literal(name: str) -> float:
    return PARAMETERS["contract_literals"][name]


def candidate_threshold(name: str) -> float:
    return PARAMETERS["engineering_candidate_thresholds"][name]
