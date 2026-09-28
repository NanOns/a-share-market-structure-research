"""Validate and execute all four V4-03 native deterministic rule contracts."""

import hashlib
import json
import math
import os
from pathlib import Path

from src.v4.contracts.native_rule_r3 import execute

ROOT = Path(__file__).resolve().parents[1]
RULES = ROOT / "config/v4_03_native_rule_contracts_r3.json"
REGISTRY = ROOT / "config/v4_03_native_contract_registry_v1.json"
OUTPUT = ROOT / "reports/v4_03/V4_03_NATIVE_CONTRACT_ACCEPTANCE_R3.json"
OPS = {"PIT_EQUAL_WEIGHT_REFERENCE", "UNKNOWN_SUFFIX_PATH", "MARKET_REGIME_AXES", "SECTOR_FIELD_LOCAL_PRIMITIVES"}
EXPECTED_OPERATOR = {"MARKET_RELATIVE_REFERENCE_V1": "PIT_EQUAL_WEIGHT_REFERENCE",
                     "V4_03_MARKET_REFERENCE_PATH_V1": "UNKNOWN_SUFFIX_PATH",
                     "MARKET_REGIME_V1_PRIMITIVES": "MARKET_REGIME_AXES",
                     "V4_03_SECTOR_NATIVE_PRIMITIVE_V1": "SECTOR_FIELD_LOCAL_PRIMITIVES"}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def equal(actual, expected):
    if isinstance(actual, float) and isinstance(expected, float):
        return math.isclose(actual, expected, rel_tol=1e-12, abs_tol=1e-12)
    if isinstance(actual, list) and isinstance(expected, list):
        return len(actual) == len(expected) and all(equal(a, b) for a, b in zip(actual, expected))
    return actual == expected


def main():
    payload = json.loads(RULES.read_text(encoding="utf-8"))
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    if {x["contract_id"] for x in payload["contracts"]} != {x["contract_id"] for x in registry["contracts"]}:
        raise RuntimeError("native rule/registry contracts differ")
    if payload["version"] != "1.0.0" or len(payload["contracts"]) != 4:
        raise RuntimeError("native rule schema version or count mismatch")
    params = {x["parameter_id"]: x["value"] for x in json.loads((ROOT / "config/v4_03_parameter_registry_v1.json").read_text(encoding="utf-8"))["entries"]}
    params.update(json.loads((ROOT / "config/v4_03_parameter_set_v1.json").read_text(encoding="utf-8"))["engineering_candidate_thresholds"])
    failures, categories, count = [], {}, 0
    for contract in payload["contracts"]:
        rule = contract["rule"]
        if rule["operator"] not in OPS or rule["operator"] != EXPECTED_OPERATOR[contract["contract_id"]]:
            raise RuntimeError("unsupported native rule operator")
        for vector in contract["vectors"]:
            count += 1
            categories.setdefault(contract["contract_id"], []).append(vector["category"])
            try:
                actual = execute(rule, vector["input"], params)
            except ValueError as exc:
                actual = {"error": str(exc)}
            expected = vector["expected_subset"]
            if any(key not in actual or not equal(actual[key], value) for key, value in expected.items()):
                failures.append({"contract_id": contract["contract_id"], "vector_id": vector["vector_id"], "actual": actual})
    receipt = {"contract_id": "V4_03_NATIVE_CONTRACT_ACCEPTANCE_R3", "status": "PASS" if not failures else "FAIL",
               "governing_task": "docs/audits/V4_03_R3_EXTERNAL_BLOCKER_CLOSURE_TASK_20260928.md",
               "rule_schema_sha256": sha(RULES), "native_registry_sha256": sha(REGISTRY),
               "interpreter_sha256": sha(ROOT / "src/v4/contracts/native_rule_r3.py"),
               "parameter_registry_sha256": sha(ROOT / "config/v4_03_parameter_registry_v1.json"),
               "contract_count": len(payload["contracts"]), "vector_count": count,
               "passed_count": count-len(failures), "failed_count": len(failures),
               "per_contract_categories": categories, "failures": failures,
               "interpreter": "src/v4/contracts/native_rule_r3.py; no production native/relative factor imports",
               "stage_acceptance": "NOT_GRANTED"}
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    tmp = OUTPUT.with_suffix(OUTPUT.suffix + ".tmp")
    tmp.write_text(json.dumps(receipt, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    os.replace(tmp, OUTPUT)
    if failures:
        raise RuntimeError(f"{len(failures)} native vectors failed")
    print(json.dumps({"status": receipt["status"], "contracts": receipt["contract_count"], "vectors": count}))


if __name__ == "__main__":
    main()
