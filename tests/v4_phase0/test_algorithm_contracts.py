import json
from pathlib import Path

import pytest

from v4.contracts.algorithm_contract import (
    ContractValidationError, Truth, kleene, safe_divide, validate_ast,
    validate_contract, validate_framework_document, validate_output_field, validate_parameter_registry,
)

ROOT = Path(__file__).resolve().parents[2]


def registry():
    return json.loads((ROOT / "config/v4_parameter_registry_v1.json").read_text("utf-8"))


def test_frozen_framework_json_matches_executable_contract():
    doc=json.loads((ROOT/"config/v4_algorithm_contract_framework_v1.json").read_text("utf-8"))
    validate_framework_document(doc)


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


def test_requiredness_nullable_independent_and_unknown_schema_keys_rejected():
    field={"field_id":"f","type":"number","unit":"CNY","producer_contract_id":"P","producer_version":"1","required":True,"nullable":True,"missing_policy":"UNKNOWN"}
    validate_output_field(field)
    with pytest.raises(ContractValidationError,match="UNKNOWN_OUTPUT_FIELD_KEYS"):
        validate_output_field({**field,"mystery":"x"})


def test_unknown_and_retired_parameters_fail_closed():
    params = validate_parameter_registry(registry())
    with pytest.raises(ContractValidationError, match="UNKNOWN_PARAMETER"):
        validate_ast({"type": "PARAM_REF", "parameter_id": "missing"}, params)
    params["old"] = {"parameter_id": "old", "status": "RETIRED", "value": 1}
    with pytest.raises(ContractValidationError, match="RETIRED_PARAMETER"):
        validate_ast({"type": "PARAM_REF", "parameter_id": "old"}, params)


def test_candidate_parameter_and_numeric_literal_bypass_fail():
    params = validate_parameter_registry(registry())
    with pytest.raises(ContractValidationError, match="PARAMETER_NOT_FORMAL"):
        validate_ast({"type": "PARAM_REF", "parameter_id": "V4_MINIMUM_SHADOW_SESSIONS"}, params)
    with pytest.raises(ContractValidationError, match="NUMERIC_LITERAL_BYPASSES"):
        validate_ast({"type": "MATH_LITERAL", "value": 0.8}, params)


def test_unknown_ast_window_producer_and_contract_fields_fail():
    params = validate_parameter_registry(registry())
    with pytest.raises(ContractValidationError, match="UNKNOWN_AST_NODE"):
        validate_ast({"type": "MAGIC"}, params)
    contract = {k: True for k in ("contract_id", "contract_version", "parameter_set_id", "inputs", "producer", "as_of", "quality_requirements", "ast", "window_refs", "rounding", "mutual_exclusion", "outputs", "identity_fields", "unknown_policy", "independent_vectors", "source_digest")}
    contract.update(producer={}, window_refs=["WINDOW_UNKNOWN"])
    with pytest.raises(ContractValidationError, match="PRODUCER_METADATA_MISSING"):
        validate_contract(contract, params, formal_consumer=False)
    contract["producer"] = {"producer_contract_id": "p", "version": "1"}
    with pytest.raises(ContractValidationError, match="UNKNOWN_WINDOW_CONTRACT"):
        validate_contract(contract, params, formal_consumer=False)
    contract["window_refs"]=[{"contract_id":"TECHNICAL_BAR_WINDOW_V1","identity":{"security_id":"SH.600000"}}]
    with pytest.raises(ContractValidationError, match="WINDOW_CONTRACT_IDENTITY_INCOMPLETE"):
        validate_contract(contract, params, formal_consumer=False)
