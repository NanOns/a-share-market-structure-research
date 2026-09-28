import copy
import json
from pathlib import Path

import pytest

from src.v4.contracts.algorithm_contract import ContractValidationError, validate_framework_document
from src.v4.contracts.algorithm_contract_v12 import validate_ast_v2, validate_contract_v12
from src.v4.contracts.algorithm_contract_numeric_v12 import validate_contract_with_vectors_v12


ROOT = Path(__file__).resolve().parents[2]


def load(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def mean_contract():
    framework = load("config/v4_algorithm_contract_framework_v1.json")
    extension = load("config/v4_algorithm_contract_framework_v1_2_0.json")
    extension_sha = __import__("hashlib").sha256((ROOT / "config/v4_algorithm_contract_framework_v1_2_0.json").read_bytes()).hexdigest()
    params = load("config/v4_03_parameter_registry_v1.json")
    schema = load("config/v4_03_output_schema_v1.json")
    output = next(x for x in schema["fields"] if x["field_id"] == "ma20")
    return framework, params, {
        "contract_id": "CORE_MA20_V1", "contract_version": "1.0.0",
        "parameter_set_id": params["parameter_set_id"], "ast_version": "RULE_AST_V2",
        "framework_extension_id": extension["contract_id"],
        "framework_extension_version": extension["version"],
        "framework_extension_sha256": extension_sha,
        "inputs": [{"field_id": "close", "type": "SESSION_SERIES", "unit": "adjusted_price",
                    "source": "V4_02_ACCEPTED_ADJUSTED_DAILY", "required": True}],
        "producer": {"producer_contract_id": "CORE_FACTOR_V1.MA", "version": "1.0.0"},
        "as_of": {"field_id": "trade_date", "timestamp_semantics": "market_session_t"},
        "quality_requirements": {"acceptable_states": ["OBSERVED"], "unknown_action": "UNKNOWN"},
        "ast": {"type": "WINDOW_AGGREGATE", "operator": "MEAN",
                "source": {"type": "FIELD_REF", "field_id": "close", "value_type": "SESSION_SERIES"},
                "window_contract_id": "TECHNICAL_BAR_WINDOW_V1",
                "window_size": {"type": "PARAM_REF", "parameter_id": "V4_03_WINDOW_SIZE_20"},
                "include_current": True, "missing_policy": "PROPAGATE_UNKNOWN_NO_DROP_NO_SHORTEN"},
        "window_refs": [{"contract_id": "TECHNICAL_BAR_WINDOW_V1",
                         "identity": {"security_id": "SEC-1", "source_snapshot_id": "SRC-1",
                                      "trade_date": "2026-09-24", "adjustment_basis_id": "QFQ-1"}}],
        "rounding": {"mode": "NONE", "precision": None}, "mutual_exclusion": [],
        "outputs": [output], "identity_fields": ["security_id", "trade_date", "adjustment_basis_id"],
        "unknown_policy": {"action": "UNKNOWN", "reason_code": "REQUIRED_INPUT_OR_WINDOW_UNKNOWN"},
        "independent_vectors": [{"vector_id": "MA20_EXACT_WINDOW", "input": {"close": list(range(1, 21))},
                                 "expected": {"value": 10.5, "quality_state": "OBSERVED"},
                                 "source_digest": "a" * 64}],
        "source_digest": "b" * 64, "enum_contracts": {}}, extension, extension_sha


def test_v12_window_aggregate_contract_validates_and_v11_stays_valid():
    framework, params, contract, extension, extension_sha = mean_contract()
    validate_framework_document(framework)
    validate_contract_v12(contract, params, framework, extension, extension_sha)


def test_v12_rejects_future_lag_and_forward_window():
    framework, params, contract, extension, extension_sha = mean_contract()
    contract["ast"] = {"type": "LAG", "source": {"type": "FIELD_REF", "field_id": "close", "value_type": "SESSION_SERIES"},
                       "offset": {"type": "PARAM_REF", "parameter_id": "V4_03_WINDOW_SIZE_5"},
                       "direction": "FUTURE"}
    with pytest.raises(ContractValidationError, match="FUTURE_OFFSET"):
        validate_contract_v12(contract, params, framework, extension, extension_sha)

    _, _, contract, extension, extension_sha = mean_contract()
    contract["ast"]["window_contract_id"] = "FORWARD_SESSION_WINDOW_V1"
    contract["window_refs"].append({"contract_id": "FORWARD_SESSION_WINDOW_V1",
                                    "identity": {"market_calendar_id": "CAL", "frozen_t0": "2026-09-24",
                                                 "horizon_n": 5, "evaluation_basis_id": "QFQ"}})
    with pytest.raises(ContractValidationError, match="FORWARD_WINDOW_FORBIDDEN"):
        validate_contract_v12(contract, params, framework, extension, extension_sha)


def test_v12_rejects_unregistered_window_literals():
    framework, params, contract, extension, extension_sha = mean_contract()
    contract["ast"]["window_size"] = 20
    with pytest.raises(ContractValidationError, match="WINDOW_SIZE_MUST_REFERENCE_PARAMETER"):
        validate_contract_v12(contract, params, framework, extension, extension_sha)


def test_v12_binds_contract_to_exact_extension_digest():
    framework, params, contract, extension, extension_sha = mean_contract()
    contract["framework_extension_sha256"] = "0" * 64
    with pytest.raises(ContractValidationError, match="VERSION_OR_PARAMETER_SET"):
        validate_contract_v12(contract, params, framework, extension, extension_sha)


def test_v12_field_local_cross_section_quality_is_explicit():
    framework = load("config/v4_algorithm_contract_framework_v1.json")
    extension = load("config/v4_algorithm_contract_framework_v1_2_0.json")
    params = load("config/v4_03_parameter_registry_v1.json")
    from src.v4.contracts.algorithm_contract import validate_parameter_registry
    parameter_map = validate_parameter_registry(params, framework)
    node = {"type": "CROSS_SECTION", "operator": "MEDIAN",
            "source": {"type": "FIELD_REF", "field_id": "amount", "value_type": "NUMBER"},
            "universe_ref": "pit_sector_members",
            "evaluable_policy": "FIELD_LOCAL_QUALITY_OBSERVED_EXCLUDE_UNKNOWN_RETAIN_COUNTS",
            "quality_ref": "amount_quality_state", "tie_policy": "NOT_APPLICABLE"}
    fields = {"amount", "pit_sector_members", "amount_quality_state"}
    validate_ast_v2(node, parameter_map, allowed_fields=fields, window_refs={})
    del node["quality_ref"]
    with pytest.raises(ContractValidationError, match="FIELD_LOCAL_QUALITY_REF_UNDECLARED"):
        validate_ast_v2(node, parameter_map, allowed_fields=fields, window_refs={})


def test_all_47_serialized_field_contracts_validate_and_reject_undeclared_input():
    framework = load("config/v4_algorithm_contract_framework_v1.json")
    extension = load("config/v4_algorithm_contract_framework_v1_2_0.json")
    extension_sha = __import__("hashlib").sha256((ROOT / "config/v4_algorithm_contract_framework_v1_2_0.json").read_bytes()).hexdigest()
    params = load("config/v4_03_parameter_registry_v1.json")
    payload = load("config/v4_03_algorithm_contracts_v1.json")
    fixture_path = ROOT / payload["numeric_fixture_path"]
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    fixture_sha = __import__("hashlib").sha256(fixture_path.read_bytes()).hexdigest()
    assert fixture_sha == payload["numeric_fixture_sha256"]
    assert payload["contract_count"] == 47
    assert payload["numeric_vector_count"] == 94
    for contract in payload["contracts"]:
        assert validate_contract_with_vectors_v12(contract, params, framework, extension,
                                                  extension_sha, fixture, fixture_sha) == 2
        mutated = copy.deepcopy(contract)
        stack = [mutated["ast"]]
        while stack:
            node = stack.pop()
            if isinstance(node, dict) and node.get("type") == "FIELD_REF":
                node["field_id"] = "UNDECLARED_NEGATIVE_VECTOR"
                break
            if isinstance(node, dict):
                stack.extend(x for x in node.values() if isinstance(x, (dict, list)))
            elif isinstance(node, list):
                stack.extend(x for x in node if isinstance(x, (dict, list)))
        else:
            raise AssertionError(f"no field reference in {contract['contract_id']}")
        with pytest.raises(ContractValidationError, match="AST_V2_UNDECLARED_FIELD"):
            validate_contract_v12(mutated, params, framework, extension, extension_sha)


def test_numeric_validator_rejects_falsified_expected_value_and_missing_negative_vector():
    framework = load("config/v4_algorithm_contract_framework_v1.json")
    extension = load("config/v4_algorithm_contract_framework_v1_2_0.json")
    extension_sha = __import__("hashlib").sha256((ROOT / "config/v4_algorithm_contract_framework_v1_2_0.json").read_bytes()).hexdigest()
    params = load("config/v4_03_parameter_registry_v1.json")
    payload = load("config/v4_03_algorithm_contracts_v1.json")
    fixture_path = ROOT / payload["numeric_fixture_path"]
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    fixture_sha = __import__("hashlib").sha256(fixture_path.read_bytes()).hexdigest()
    ma20 = next(c for c in payload["contracts"] if c["outputs"][0]["field_id"] == "ma20")
    wrong = copy.deepcopy(ma20)
    wrong["independent_vectors"][0]["expected"]["value"] += 1
    with pytest.raises(ContractValidationError, match="AST_V2_VECTOR_VALUE_MISMATCH"):
        validate_contract_with_vectors_v12(wrong, params, framework, extension, extension_sha,
                                           fixture, fixture_sha)
    missing = copy.deepcopy(ma20)
    missing["independent_vectors"].pop()
    with pytest.raises(ContractValidationError, match="AST_V2_POSITIVE_NEGATIVE_VECTORS_REQUIRED"):
        validate_contract_with_vectors_v12(missing, params, framework, extension, extension_sha,
                                           fixture, fixture_sha)
