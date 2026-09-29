from __future__ import annotations

import copy
import hashlib
import inspect
import json
from pathlib import Path
import sys
import tempfile
import os
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.verify_v4_07_base_seed import independent_eval, parameter_values_from_document  # noqa: E402
from scripts.verify_v4_07_machine_vectors import execute_facts, machine_fact  # noqa: E402
from src.v4.base_seed import _eval, _validate_frozen_package, evaluate_facts, sha256_file  # noqa: E402


PARAMETER_CHANGES = (
    {
        "parameter_id": "V4_07_POSITION_BIAS20_ATR_MAX",
        "from": 3,
        "to": 2.5,
        "overrides": {"bias20_atr": 2.75, "delta3": 10.5},
        "predicate": "position_ok",
    },
    {
        "parameter_id": "V4_07_DELTA3_IMPROVING_MIN_POINTS",
        "from": 3,
        "to": 4,
        "overrides": {"bias20_atr": 2.0, "delta3": 3.5},
        "predicate": "relative_change_improving",
    },
    {
        "parameter_id": "V4_07_DELTA3_STRONG_MIN_POINTS",
        "from": 10,
        "to": 11,
        "overrides": {"bias20_atr": 2.0, "delta3": 10.5},
        "predicate": "relative_change_strong",
    },
)


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


def make_facts(overrides: dict[str, Any]) -> dict[str, dict[str, Any]]:
    vectors = json.loads((ROOT / "config/v4_07_machine_vectors_v1.json").read_text(encoding="utf-8"))
    values = dict(vectors["base_input"])
    values.update(overrides)
    return {key: machine_fact(value, key) for key, value in values.items()}


def main() -> int:
    _contract, formal_parameter_set, _fields, _freeze = _validate_frozen_package(ROOT)
    parameter_path = ROOT / "config/v4_07_parameter_set_v1.json"
    formal_sha_before = sha256_file(parameter_path)
    results = []
    for case in PARAMETER_CHANGES:
        facts = make_facts(case["overrides"])
        fixture = copy.deepcopy(formal_parameter_set)
        item = next(parameter for parameter in fixture["parameters"] if parameter["parameter_id"] == case["parameter_id"])
        item["value"] = case["to"]

        formal_machine = execute_facts(facts, formal_parameter_set)
        formal_production = evaluate_facts(facts, formal_parameter_set)
        formal_independent = independent_eval(facts, parameter_values_from_document(formal_parameter_set))
        fixture_machine = execute_facts(facts, fixture)
        fixture_production = evaluate_facts(facts, fixture)
        fixture_independent = independent_eval(facts, parameter_values_from_document(fixture))
        before = formal_production["domain_states"][case["predicate"]]
        after = fixture_production["domain_states"][case["predicate"]]
        if before != "TRUE" or after != "FALSE":
            raise AssertionError(f"parameter perturbation did not move {case['parameter_id']} predicate across its boundary")
        if formal_machine != formal_production or fixture_machine != fixture_production:
            raise AssertionError("machine executor and production evaluator diverged")
        if formal_independent != formal_production or fixture_independent != fixture_production:
            raise AssertionError("independent verifier and production evaluator diverged")
        results.append({
            "parameter_id": case["parameter_id"],
            "formal_value": case["from"],
            "fixture_value": case["to"],
            "predicate": case["predicate"],
            "formal_state": before,
            "perturbed_state": after,
            "machine_equals_production": True,
            "independent_equals_production": True,
            "formal_config_changed": formal_parameter_set["parameters"] != fixture["parameters"],
        })
    formal_sha_after = sha256_file(parameter_path)
    if formal_sha_after != formal_sha_before:
        raise AssertionError("formal parameter config changed during perturbation checks")
    evaluator_source = inspect.getsource(_eval)
    if any(literal in evaluator_source for literal in ("3.0", "10.0")):
        raise AssertionError("production evaluator contains a parameter threshold literal fallback")
    independent_source = Path(inspect.getsourcefile(independent_eval)).read_text(encoding="utf-8")
    independent_imports_production = "from src.v4.base_seed import" in independent_source
    if independent_imports_production:
        raise AssertionError("independent verifier imports the production evaluator")
    report = {
        "contract_id": "V4_07_R2_PARAMETER_BINDING_VERIFICATION_V1",
        "status": "PASS_PARAMETER_INSTANCE_DRIVES_ALL_EXECUTORS",
        "parameter_set_id": formal_parameter_set["parameter_set_id"],
        "formal_parameter_set_sha256_before": formal_sha_before,
        "formal_parameter_set_sha256_after": formal_sha_after,
        "formal_parameter_config_unchanged": formal_sha_before == formal_sha_after,
        "production_evaluator_threshold_literals_found": False,
        "independent_verifier_imports_production_evaluator": independent_imports_production,
        "cases": results,
        "next_stage": "V4_07_R2_INDEPENDENT_POSTCHECK_AND_EXTERNAL_REVIEW",
    }
    atomic_json(ROOT / "reports/v4_07/V4_07_R2_PARAMETER_BINDING_VERIFICATION.json", report)
    print(json.dumps({"status": report["status"], "case_count": len(results), "formal_config_unchanged": True}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
