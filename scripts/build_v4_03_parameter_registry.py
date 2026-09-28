"""Create framework-compatible, explicitly non-final V4-03 parameter registry."""

import json
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "config/v4_03_parameter_registry_v1.json"


def entry(pid, value, unit, reason, minimum=None, maximum=None):
    return {"parameter_id": pid, "contract_scope": "V4-03 / CORE_FACTOR_V1 and native primitives",
            "value": value, "unit": unit, "minimum": minimum, "maximum": maximum,
            "inclusive_boundaries": "contract-defined; see reason", "status": "ENGINEERING_CANDIDATE",
            "reason": reason, "introduced_version": "V4_ALGORITHM_CONTRACT_FRAMEWORK_V1@1.2.0",
            "approved_at": None, "supersedes": None, "owner_stage": "V4-03"}


def main():
    entries = []
    for n in (1, 3, 5, 10, 20, 60, 70):
        entries.append(entry(f"V4_03_WINDOW_SIZE_{n}", n, "market_sessions_or_actual_bars",
                             "Formula horizon explicitly stated by REV2 or V4-03 R2 task.", 1, None))
    entries.extend([
        entry("V4_03_ONE", 1, "dimensionless", "Arithmetic identity used by simple-return formulas.", 1, 1),
        entry("V4_03_ZERO", 0, "dimensionless", "Zero threshold in REV2 core price damage comparison.", 0, 0),
        entry("V4_03_RPS_TIE_HALF", 0.5, "dimensionless", "REV2 RPS midrank tie adjustment.", 0, 1),
        entry("V4_03_CORE_PRICE_DAMAGE_ATR_MULTIPLE", 0.5, "ATR_multiple", "REV2 CORE_FACTOR_V1 literal; identity registered for AST use.", 0, None),
        entry("V4_03_MARKET_REFERENCE_MAX_MISSING_FRACTION", 0.2, "fraction", "REV2 §49A.1 missing exceeds 20 percent -> UNKNOWN.", 0, 1),
        entry("V4_03_MARKET_BREADTH_AXIS_THRESHOLD", 0.05, "return_fraction", "REV2 MARKET_REGIME_V1 threshold.", 0, 1),
        entry("V4_03_MARKET_PARTICIPATION_EXPANDING_THRESHOLD", 1.2, "ratio", "REV2 MARKET_REGIME_V1 threshold.", 0, None),
        entry("V4_03_MARKET_PARTICIPATION_THIN_THRESHOLD", 0.8, "ratio", "REV2 MARKET_REGIME_V1 threshold.", 0, None),
        entry("V4_03_MARKET_LIMIT_COVERAGE_MINIMUM", 0.8, "fraction", "REV2 MARKET_REGIME_V1 threshold.", 0, 1),
        entry("V4_03_MARKET_STRESS_ELEVATED_THRESHOLD", 0.01, "fraction", "REV2 MARKET_REGIME_V1 threshold.", 0, 1),
        entry("V4_03_MARKET_STRESS_HIGH_THRESHOLD", 0.05, "fraction", "REV2 MARKET_REGIME_V1 threshold.", 0, 1),
    ])
    registry = {"contract_id": "PARAMETER_REGISTRY_V1", "registry_version": "1.0.0",
                "stage_id": "V4-03", "parameter_set_id": "V4_03_CORE_FACTOR_PARAMETER_SET_V1",
                "status": "REGISTERED_CANDIDATES_NOT_RELEASE_VALUES", "values_are_formal": False,
                "value_domain": "FINITE_NUMBER_OR_NULL", "non_numeric_value_policy_ref": "V4_PARAMETER_NON_NUMERIC_POLICY_R3",
                "entries": entries}
    payload = json.dumps(registry, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    temp = OUTPUT.with_suffix(".json.tmp")
    temp.write_bytes(payload.encode("utf-8"))
    os.replace(temp, OUTPUT)
    print(f"{len(entries)} V4-03 parameter entries")


if __name__ == "__main__":
    main()
