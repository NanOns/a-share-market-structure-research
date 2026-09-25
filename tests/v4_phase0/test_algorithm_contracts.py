import copy
import json
from pathlib import Path

import pytest

from v4.contracts.algorithm_contract import (
    ARITHMETIC_OPERATORS, COMPARE_OPERATORS, ContractValidationError, Truth,
    kleene, safe_divide, validate_ast, validate_contract, validate_framework_document,
    validate_output_field, validate_parameter_registry,
)

ROOT = Path(__file__).resolve().parents[2]


def framework():
    return json.loads((ROOT / "config/v4_algorithm_contract_framework_v1.json").read_text("utf-8"))


def registry():
    return json.loads((ROOT / "config/v4_parameter_registry_v1.json").read_text("utf-8"))


def test_frozen_framework_and_full_parameter_registry_are_executable():
    doc = framework()
    params = registry()
    validate_framework_document(doc, params)
    assert len(validate_parameter_registry(params, doc)) == len(params["entries"])


@pytest.mark.parametrize(("op", "a", "b", "expected"), [
    ("AND", Truth.TRUE, Truth.UNKNOWN, Truth.UNKNOWN),
    ("AND", Truth.FALSE, Truth.UNKNOWN, Truth.FALSE),
    ("OR", Truth.TRUE, Truth.UNKNOWN, Truth.TRUE),
    ("OR", Truth.FALSE, Truth.UNKNOWN, Truth.UNKNOWN),
])
def test_kleene_binary_truth(op, a, b, expected):
    assert kleene(op, a, b) == expected


def test_not_unknown_and_zero_denominator_remain_unknown():
    assert kleene("NOT", Truth.UNKNOWN) == Truth.UNKNOWN
    assert safe_divide(1, 0) is None


def test_parameter_required_fields_and_framework_status_enum_match():
    data = registry()
    framework_doc = framework()
    params = validate_parameter_registry(data, framework_doc)
    for entry in data["entries"]:
        assert {"parameter_id", "contract_scope", "value", "unit", "minimum", "maximum", "inclusive_boundaries", "status", "reason", "introduced_version", "approved_at", "supersedes", "owner_stage"} <= set(entry)
        assert entry["status"] in framework_doc["parameter_instance_contract"]["statuses"]
    del data["entries"][0]["approved_at"]
    with pytest.raises(ContractValidationError, match="PARAMETER_REQUIRED_FIELDS_MISSING"):
        validate_parameter_registry(data, framework_doc)


def test_unknown_and_retired_parameters_fail_closed():
    params = validate_parameter_registry(registry())
    with pytest.raises(ContractValidationError, match="UNKNOWN_PARAMETER"):
        validate_ast({"type": "PARAM_REF", "parameter_id": "missing"}, params)
    params["old"] = {"parameter_id": "old", "status": "RETIRED", "value": None}
    with pytest.raises(ContractValidationError, match="RETIRED_PARAMETER"):
        validate_ast({"type": "PARAM_REF", "parameter_id": "old"}, params)


def test_candidate_parameter_and_numeric_literal_bypass_fail():
    params = validate_parameter_registry(registry())
    with pytest.raises(ContractValidationError, match="PARAMETER_NOT_FORMAL"):
        validate_ast({"type": "PARAM_REF", "parameter_id": "V4_MINIMUM_SHADOW_SESSIONS"}, params)
    with pytest.raises(ContractValidationError, match="MATH_CONSTANT_ID_UNKNOWN"):
        validate_ast({"type": "MATH_LITERAL", "constant_id": "0.8"}, params)


def test_compare_operator_and_arity_are_fully_validated():
    params = validate_parameter_registry(registry())
    left = {"type": "FIELD_REF", "field_id": "x"}
    right = {"type": "FIELD_REF", "field_id": "y"}
    assert COMPARE_OPERATORS == set(framework()["rule_ast"]["compare_operators"])
    for op in COMPARE_OPERATORS:
        count = 1 if op in {"IS_NULL", "IS_NOT_NULL"} else 2
        validate_ast({"type": "COMPARE", "operator": op, "args": [left] + [right] * (count - 1)}, params)
    with pytest.raises(ContractValidationError, match="UNKNOWN_COMPARE_OPERATOR"):
        validate_ast({"type": "COMPARE", "operator": "NOT_A_REAL_OPERATOR", "args": [left, right]}, params)
    with pytest.raises(ContractValidationError, match="INVALID_COMPARE_ARITY"):
        validate_ast({"type": "COMPARE", "operator": "EQ", "args": [left]}, params)


def test_arithmetic_operator_and_arity_are_fully_validated():
    params = validate_parameter_registry(registry())
    operands = [{"type": "FIELD_REF", "field_id": "x"}, {"type": "FIELD_REF", "field_id": "y"}]
    assert ARITHMETIC_OPERATORS == set(framework()["rule_ast"]["arithmetic_operators"])
    for op in ARITHMETIC_OPERATORS:
        validate_ast({"type": "ARITHMETIC", "operator": op, "args": operands}, params)
    with pytest.raises(ContractValidationError, match="UNKNOWN_ARITHMETIC_OPERATOR"):
        validate_ast({"type": "ARITHMETIC", "operator": "DIVIDE_MAGIC", "args": operands}, params)
    with pytest.raises(ContractValidationError, match="INVALID_ARITHMETIC_ARITY"):
        validate_ast({"type": "ARITHMETIC", "operator": "ADD", "args": operands[:1]}, params)


def test_enum_literal_identity_and_version_are_checked():
    params = validate_parameter_registry(registry())
    enum_contracts = {"QUALITY_V1": {"version": "1.2.0", "values": ["OBSERVED", "UNKNOWN"]}}
    validate_ast({"type": "ENUM_LITERAL", "enum_id": "QUALITY_V1", "enum_version": "1.2.0", "value": "OBSERVED"}, params, enum_contracts=enum_contracts)
    with pytest.raises(ContractValidationError, match="ENUM_IDENTITY_OR_VERSION_MISMATCH"):
        validate_ast({"type": "ENUM_LITERAL", "enum_id": "QUALITY_V1", "enum_version": "1.0.0", "value": "OBSERVED"}, params, enum_contracts=enum_contracts)
    with pytest.raises(ContractValidationError, match="ENUM_ID_UNDECLARED"):
        validate_ast({"type": "ENUM_LITERAL", "enum_id": "UNDECLARED", "enum_version": "1", "value": "x"}, params, enum_contracts=enum_contracts)


def test_output_metadata_uses_framework_requiredness_schema():
    field = {"field_id": "f", "type": "number", "unit": "CNY", "producer_contract_id": "P", "producer_version": "1", "requiredness": "REQUIRED", "nullable": True, "as_of": "trade_date", "quality_state": "OBSERVED", "missing_policy": "UNKNOWN", "output_digest": "a" * 64, "display_label": "F"}
    validate_output_field(field)
    with pytest.raises(ContractValidationError, match="OUTPUT_REQUIREDNESS_INVALID"):
        validate_output_field({**field, "requiredness": "MAYBE"})
    with pytest.raises(ContractValidationError, match="UNKNOWN_OUTPUT_FIELD_KEYS"):
        validate_output_field({**field, "required": True})


def _valid_contract():
    return {
        "contract_id": "EXAMPLE_V1", "contract_version": "1.0.0", "parameter_set_id": "PSET-1",
        "inputs": [{"field_id": "x", "type": "number", "unit": "CNY", "source": "S", "required": True}],
        "producer": {"producer_contract_id": "PRODUCER_V1", "version": "1.0.0"},
        "as_of": {"field_id": "trade_date", "timestamp_semantics": "EXCHANGE_SESSION_CLOSE"},
        "quality_requirements": {"acceptable_states": ["OBSERVED"], "unknown_action": "UNKNOWN"},
        "ast": {"type": "COMPARE", "operator": "GT", "args": [{"type": "FIELD_REF", "field_id": "x"}, {"type": "MATH_LITERAL", "constant_id": "PI"}]},
        "window_refs": [{"contract_id": "TECHNICAL_BAR_WINDOW_V1", "identity": {"security_id": "SH.600000", "source_snapshot_id": "S1", "trade_date": "2026-09-25", "adjustment_basis_id": "RAW"}}],
        "rounding": {"mode": "NONE", "precision": None}, "mutual_exclusion": [],
        "outputs": [{"field_id": "y", "type": "boolean", "unit": "enum", "producer_contract_id": "PRODUCER_V1", "producer_version": "1.0.0", "requiredness": "REQUIRED", "nullable": False, "as_of": "trade_date", "quality_state": "OBSERVED", "missing_policy": "UNKNOWN", "output_digest": "b" * 64, "display_label": "Y"}],
        "identity_fields": ["security_id", "trade_date"],
        "unknown_policy": {"action": "UNKNOWN", "reason_code": "INPUT_NOT_EVALUABLE"},
        "independent_vectors": [{"vector_id": "V1", "input": {"x": 4}, "expected": True, "source_digest": "c" * 64}],
        "source_digest": "d" * 64, "enum_contracts": {},
    }


def test_full_contract_sections_and_malformed_sections_are_validated():
    params = validate_parameter_registry(registry())
    contract = _valid_contract()
    validate_contract(contract, params, formal_consumer=False)
    malformed = copy.deepcopy(contract)
    malformed["inputs"] = [{"field_id": "x"}]
    with pytest.raises(ContractValidationError, match="CONTRACT_INPUT_SCHEMA_INVALID"):
        validate_contract(malformed, params, formal_consumer=False)
    malformed = copy.deepcopy(contract)
    malformed["unknown_policy"] = {"action": "ALLOW", "reason_code": "bad"}
    with pytest.raises(ContractValidationError, match="UNKNOWN_POLICY_ACTION_INVALID"):
        validate_contract(malformed, params, formal_consumer=False)
    malformed = copy.deepcopy(contract)
    malformed["ast"]["args"][0]["field_id"] = "undeclared_input"
    with pytest.raises(ContractValidationError, match="AST_FIELD_NOT_DECLARED"):
        validate_contract(malformed, params, formal_consumer=False)


def test_framework_schema_conflicts_are_rejected():
    doc = framework()
    doc["rule_ast"]["compare_operators"].append("FAKE")
    with pytest.raises(ContractValidationError, match="FRAMEWORK_COMPARE_OPERATOR_SET_MISMATCH"):
        validate_framework_document(doc, registry())
