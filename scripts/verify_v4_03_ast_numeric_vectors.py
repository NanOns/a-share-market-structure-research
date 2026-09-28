"""Independently execute every frozen V4-03 algorithm AST numeric vector."""

import hashlib
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.v4.contracts.algorithm_contract_numeric_v12 import validate_contract_with_vectors_v12

OUTPUT = ROOT / "reports/v4_03/V4_03_AST_NUMERIC_VECTOR_ACCEPTANCE_R2.json"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def main():
    base_path = ROOT / "config/v4_algorithm_contract_framework_v1.json"
    extension_path = ROOT / "config/v4_algorithm_contract_framework_v1_2_0.json"
    registry_path = ROOT / "config/v4_03_parameter_registry_v1.json"
    contracts_path = ROOT / "config/v4_03_algorithm_contracts_v1.json"
    base, extension, registry, payload = map(load, (base_path, extension_path, registry_path, contracts_path))
    fixture_path = ROOT / payload["numeric_fixture_path"]
    fixture = load(fixture_path)
    fixture_sha = sha(fixture_path)
    if fixture_sha != payload["numeric_fixture_sha256"]:
        raise RuntimeError("numeric fixture digest differs from the contract set")
    vector_count = 0
    field_ids = []
    for contract in payload["contracts"]:
        vector_count += validate_contract_with_vectors_v12(
            contract, registry, base, extension, sha(extension_path), fixture, fixture_sha)
        field_ids.append(contract["outputs"][0]["field_id"])
    if len(field_ids) != len(set(field_ids)) or len(field_ids) != 47 or vector_count != 94:
        raise RuntimeError("47 unique fields and 94 numeric vectors are mandatory")
    receipt = {
        "contract_id": "V4_03_AST_NUMERIC_VECTOR_ACCEPTANCE_R2",
        "status": "PASS_DIAGNOSTIC_CONTRACT_NUMERIC_VECTORS",
        "framework_extension_sha256": sha(extension_path),
        "parameter_registry_sha256": sha(registry_path),
        "contract_set_sha256": sha(contracts_path),
        "fixture_sha256": fixture_sha,
        "contract_count": len(field_ids),
        "positive_numeric_vector_count": len(field_ids),
        "negative_unknown_vector_count": len(field_ids),
        "vector_count": vector_count,
        "field_ids": sorted(field_ids),
        "comparison": "boolean exact; numeric relative/absolute tolerance 1e-12; UNKNOWN exact",
        "reference_origin": "Independent synthetic fixture expectations from independent_v4_03_full_scope_postcheck.py; AST evaluated by algorithm_contract_numeric_v12.py without factor producer imports",
        "stage_acceptance": "NOT_GRANTED",
        "next_stage": "Continue full-history/PIT/native evidence; keep V4-04 blocked",
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    temp = OUTPUT.with_suffix(OUTPUT.suffix + ".tmp")
    temp.write_text(json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temp, OUTPUT)
    print(json.dumps({"status": receipt["status"], "contracts": len(field_ids), "vectors": vector_count}))


if __name__ == "__main__":
    main()
