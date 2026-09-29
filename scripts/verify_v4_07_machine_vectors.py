from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import tempfile
import os
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.v4.base_seed import _validate_frozen_package, evaluate_facts, sha256_file  # noqa: E402


BOOLEAN_FIELDS = {
    "research_universe", "actual_bar", "price_identity_READY", "minimum_liquidity",
    "core_price_damage", "severe_extension",
}


def machine_fact(value: Any, field: str) -> dict[str, Any]:
    if field in BOOLEAN_FIELDS:
        normalized = True if value == "TRUE" else False if value == "FALSE" else None
    else:
        normalized = None if value == "UNKNOWN" else value
    return {"value": normalized, "reason": "MACHINE_VECTOR_UNKNOWN" if normalized is None else None}


def execute_facts(facts: Mapping[str, Mapping[str, Any]], parameter_set: Mapping[str, Any]) -> dict[str, Any]:
    """The machine-vector executor passes the supplied parameter instance to production evaluation."""
    return evaluate_facts(facts, parameter_set)


def execute_vector(
    overrides: Mapping[str, Any],
    parameter_set: Mapping[str, Any],
    base_input: Mapping[str, Any],
) -> dict[str, Any]:
    values = dict(base_input)
    values.update(overrides)
    facts = {key: machine_fact(value, key) for key, value in values.items()}
    result = execute_facts(facts, parameter_set)
    result["seed_paths"] = result["domain_states"]["seed_paths"]
    result.update(result["domain_states"])
    return result


def atomic_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = (json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n").encode("utf-8")
    fd, temporary = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def main() -> int:
    _contract, parameter_set, _fields, _freeze = _validate_frozen_package(ROOT)
    vector_path = ROOT / "config/v4_07_machine_vectors_v1.json"
    vector_set = json.loads(vector_path.read_text(encoding="utf-8"))
    checked = 0
    mismatches = []
    for vector in vector_set["vectors"]:
        if vector["suite"] in {"temporal", "isolation"}:
            continue
        actual = execute_vector(vector["overrides"], parameter_set, vector_set["base_input"])
        checked += 1
        differences = {
            name: {"expected": expected, "actual": actual.get(name)}
            for name, expected in vector["expected"].items()
            if actual.get(name) != expected
        }
        if differences:
            mismatches.append({"vector_id": vector["vector_id"], "differences": differences})
    receipt = {
        "contract_id": "V4_07_R2_MACHINE_VECTOR_COVERAGE_V1",
        "status": "PASS" if not mismatches else "FAIL",
        "checked_vector_count": checked,
        "mismatch_count": len(mismatches),
        "parameter_set_id": parameter_set["parameter_set_id"],
        "parameter_set_sha256": sha256_file(ROOT / "config/v4_07_parameter_set_v1.json"),
        "machine_vectors_sha256": sha256_file(vector_path),
        "mismatches": mismatches,
        "parameter_source": "config/v4_07_parameter_set_v1.json; loaded by frozen package validator",
        "next_stage": "V4_07_R2_INDEPENDENT_POSTCHECK_AND_EXTERNAL_REVIEW",
    }
    atomic_json(ROOT / "reports/v4_07/V4_07_R2_MACHINE_VECTOR_COVERAGE.json", receipt)
    print(json.dumps({"status": receipt["status"], "checked_vector_count": checked, "mismatch_count": len(mismatches)}, sort_keys=True))
    return 0 if not mismatches else 1


if __name__ == "__main__":
    raise SystemExit(main())
