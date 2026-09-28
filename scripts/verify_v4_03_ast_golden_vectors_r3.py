"""Execute named edge-case vectors against the existing RULE_AST_V2 contracts."""

from copy import deepcopy
import hashlib
import json
import math
import os
from pathlib import Path

from src.v4.contracts.algorithm_contract_numeric_v12 import NumericContext

ROOT = Path(__file__).resolve().parents[1]
CASES = ROOT / "config/v4_03_ast_golden_cases_r3.json"
REPORT = ROOT / "reports/v4_03/V4_03_AST_GOLDEN_VECTOR_ACCEPTANCE_R3.json"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


def atomic(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def mutate(fixture, operations):
    out = deepcopy(fixture)
    for op in operations:
        kind = op[0]
        if kind == "tail":
            out["history"] = out["history"][-op[1]:]
        elif kind == "insert_state":
            out["history"].insert(op[1], {"trade_date": "2026-03-30-SYNTHETIC", "state": op[2], "bar": None})
        elif kind == "set_state":
            out["history"][op[1]]["state"] = op[2]
            if op[2] != "ACTUAL":
                out["history"][op[1]]["bar"] = None
        elif kind == "set_bar":
            out["history"][op[1]]["bar"][op[2]] = op[3]
        elif kind == "set_scalar":
            out["relative"]["target_scalar"][op[1]] = op[2]
        elif kind == "set_members":
            out["relative"]["pit_universe"] = op[1]
        elif kind == "set_cross":
            out["relative"]["cross_section"][op[1]] = op[2]
        elif kind == "set_series":
            out["relative"]["field_series"][op[1]] = op[2]
        else:
            raise ValueError(kind)
    return out


def run():
    contracts_path = ROOT / "config/v4_03_algorithm_contracts_v1.json"
    registry_path = ROOT / "config/v4_03_parameter_registry_v1.json"
    framework_path = ROOT / "config/v4_algorithm_contract_framework_v1_2_0.json"
    contracts = json.loads(contracts_path.read_text(encoding="utf-8"))
    fixture_path = ROOT / contracts["numeric_fixture_path"]
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    params = {x["parameter_id"]: x["value"] for x in registry["entries"]}
    case_payload = json.loads(CASES.read_text(encoding="utf-8"))
    by_field = {x["outputs"][0]["field_id"]: x for x in contracts["contracts"]}
    failures, coverage, results = [], {}, []
    for case in case_payload["cases"]:
        contract = by_field.get(case["field_id"])
        context = NumericContext(mutate(fixture, case["operations"]), params)
        if contract is None and case["field_id"] == "__LOG_OPERATOR__":
            ast = {"type": "TRANSFORM", "operator": "LOG", "args": [{"type": "FIELD_REF", "field_id": "close"}]}
            mode = "TECHNICAL_BAR_WINDOW_V1"
        else:
            ast = contract["ast"]
            mode = contract["window_refs"][0]["contract_id"]
        actual = context.eval(ast, len(context.history) - 1, mode)
        expected = case["expected"]
        good = actual is None and expected is None or isinstance(actual, (int, float)) and isinstance(expected, (int, float)) and math.isclose(actual, expected, rel_tol=1e-12, abs_tol=1e-12)
        if not good:
            failures.append({"case_id": case["case_id"], "actual": actual, "expected": expected})
        coverage.setdefault(case["category"], []).append(case["case_id"])
        results.append({"case_id": case["case_id"], "field_id": case["field_id"], "category": case["category"], "passed": good})
    source_identity_change = digest(mutate(fixture, [["set_bar", -2, "source", "e" * 64]])) != digest(fixture)
    if not source_identity_change:
        failures.append({"case_id": "SOURCE_IDENTITY_DIGEST_CHANGE", "actual": "unchanged", "expected": "changed"})
    coverage["input_source_identity_digest_change"] = ["SOURCE_IDENTITY_DIGEST_CHANGE"]
    report = {"contract_id": "V4_03_AST_GOLDEN_VECTOR_ACCEPTANCE_R3", "status": "PASS" if not failures else "FAIL",
              "vector_extension_version": "1.0.0",
              "governing_task": "docs/audits/V4_03_R3_EXTERNAL_BLOCKER_CLOSURE_TASK_20260928.md",
              "contract_set_sha256": sha(contracts_path), "framework_sha256": sha(framework_path),
              "numeric_executor_sha256": sha(ROOT / "src/v4/contracts/algorithm_contract_numeric_v12.py"),
              "parameter_registry_sha256": sha(registry_path), "fixture_sha256": sha(fixture_path),
              "case_manifest_sha256": sha(CASES), "contract_count": len(by_field),
              "vector_count": len(results) + contracts["numeric_vector_count"],
              "r3_edge_vector_count": len(results), "case_category_count": len(coverage),
              "passed_count": sum(x["passed"] for x in results), "failed_count": len(failures),
              "per_category_coverage": coverage, "results": results, "failures": failures,
              "comparison": "numeric abs/rel tolerance 1e-12; UNKNOWN exact",
              "negative_tamper_detection": "tested in tests/v4_03/test_ast_golden_r3.py",
              "source_identity_digest_change_detected": source_identity_change,
              "stage_acceptance": "NOT_GRANTED"}
    atomic(REPORT, report)
    if failures:
        raise RuntimeError(f"{len(failures)} golden vectors failed")
    print(json.dumps({"status": report["status"], "edge_vectors": len(results), "categories": len(coverage)}))


if __name__ == "__main__":
    run()
