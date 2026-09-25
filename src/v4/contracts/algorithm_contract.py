from __future__ import annotations

from enum import Enum
from typing import Any, Mapping


class ContractValidationError(ValueError):
    pass


class Truth(str, Enum):
    TRUE = "TRUE"
    FALSE = "FALSE"
    UNKNOWN = "UNKNOWN"


AST_NODES = {"AND", "OR", "NOT", "COMPARE", "ARITHMETIC", "FIELD_REF", "PARAM_REF", "ENUM_LITERAL", "MATH_LITERAL"}
WINDOWS = {"TECHNICAL_BAR_WINDOW_V1", "CROSS_SECTION_SESSION_WINDOW_V1", "FORWARD_SESSION_WINDOW_V1"}
WINDOW_IDENTITIES = {
    "TECHNICAL_BAR_WINDOW_V1": {"security_id", "source_snapshot_id", "trade_date", "adjustment_basis_id"},
    "CROSS_SECTION_SESSION_WINDOW_V1": {"market_calendar_id", "start_session", "end_session", "universe_snapshot_id", "adjustment_basis_id"},
    "FORWARD_SESSION_WINDOW_V1": {"market_calendar_id", "frozen_t0", "horizon_n", "evaluation_basis_id"},
}
MATH_CONSTANTS = {"PI": 3.141592653589793, "E": 2.718281828459045}


def kleene(op: str, *values: Truth | str) -> Truth:
    vals = tuple(Truth(v) for v in values)
    op = op.upper()
    if op == "NOT" and len(vals) == 1:
        return {Truth.TRUE: Truth.FALSE, Truth.FALSE: Truth.TRUE, Truth.UNKNOWN: Truth.UNKNOWN}[vals[0]]
    if op == "AND" and len(vals) >= 2:
        if Truth.FALSE in vals:
            return Truth.FALSE
        return Truth.UNKNOWN if Truth.UNKNOWN in vals else Truth.TRUE
    if op == "OR" and len(vals) >= 2:
        if Truth.TRUE in vals:
            return Truth.TRUE
        return Truth.UNKNOWN if Truth.UNKNOWN in vals else Truth.FALSE
    raise ContractValidationError(f"INVALID_TRUTH_OPERATOR_OR_ARITY:{op}:{len(vals)}")


def safe_divide(numerator: float | None, denominator: float | None) -> float | None:
    if numerator is None or denominator is None or denominator == 0:
        return None
    return numerator / denominator


def validate_parameter_registry(registry: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    entries = registry.get("entries")
    if not isinstance(entries, list):
        raise ContractValidationError("PARAMETER_ENTRIES_REQUIRED")
    result: dict[str, Mapping[str, Any]] = {}
    for entry in entries:
        pid = entry.get("parameter_id")
        if not isinstance(pid, str) or not pid or pid in result:
            raise ContractValidationError(f"INVALID_OR_DUPLICATE_PARAMETER_ID:{pid}")
        status = entry.get("status")
        if status not in {"ENGINEERING_CANDIDATE_UNSET", "ENGINEERING_CANDIDATE_FROM_REV2", "ENGINEERING_CANDIDATE", "SHADOW_FROZEN", "PROVISIONAL", "SUPPORTED", "RETIRED"}:
            raise ContractValidationError(f"UNKNOWN_PARAMETER_STATUS:{pid}:{status}")
        value = entry.get("value")
        if value is not None and isinstance(value, (int, float)):
            lo, hi = entry.get("minimum"), entry.get("maximum")
            if lo is not None and value < lo or hi is not None and value > hi:
                raise ContractValidationError(f"PARAMETER_OUT_OF_BOUNDS:{pid}")
        result[pid] = entry
    return result


def validate_framework_document(framework: Mapping[str, Any]) -> None:
    if framework.get("contract_id")!="V4_ALGORITHM_CONTRACT_FRAMEWORK_V1":
        raise ContractValidationError("FRAMEWORK_CONTRACT_ID_MISMATCH")
    ast=framework.get("rule_ast",{})
    if set(ast.get("node_types",[]))!=AST_NODES:
        raise ContractValidationError("FRAMEWORK_AST_NODE_SET_MISMATCH")
    truth=ast.get("kleene",{})
    required={"FALSE_AND_UNKNOWN":"FALSE","TRUE_AND_UNKNOWN":"UNKNOWN","TRUE_OR_UNKNOWN":"TRUE","FALSE_OR_UNKNOWN":"UNKNOWN","NOT_UNKNOWN":"UNKNOWN"}
    if any(truth.get(key)!=value for key,value in required.items()):
        raise ContractValidationError("FRAMEWORK_KLEENE_TABLE_MISMATCH")
    if ast.get("hard_safety","").find("never coerce null/unknown to pass")<0:
        raise ContractValidationError("UNKNOWN_MUST_FAIL_CLOSED")
    windows=framework.get("window_contracts",{})
    if set(windows)!=WINDOWS:
        raise ContractValidationError("FRAMEWORK_WINDOW_SET_MISMATCH")
    for name,required_identity in WINDOW_IDENTITIES.items():
        identity=windows[name].get("identity")
        if not isinstance(identity,list) or not required_identity.issubset(identity):
            raise ContractValidationError(f"FRAMEWORK_WINDOW_IDENTITY_MISMATCH:{name}")


def validate_ast(node: Mapping[str, Any], parameters: Mapping[str, Mapping[str, Any]], *, formal_consumer: bool = True) -> None:
    if not isinstance(node, Mapping):
        raise ContractValidationError("AST_NODE_MUST_BE_OBJECT")
    kind = node.get("type")
    if kind not in AST_NODES:
        raise ContractValidationError(f"UNKNOWN_AST_NODE:{kind}")
    if kind == "PARAM_REF":
        pid = node.get("parameter_id")
        if pid not in parameters:
            raise ContractValidationError(f"UNKNOWN_PARAMETER:{pid}")
        parameter = parameters[pid]
        if parameter.get("status") == "RETIRED":
            raise ContractValidationError(f"RETIRED_PARAMETER:{pid}")
        if formal_consumer and (parameter.get("value") is None or str(parameter.get("status", "")).startswith("ENGINEERING_CANDIDATE")):
            raise ContractValidationError(f"PARAMETER_NOT_FORMAL:{pid}")
    if kind == "MATH_LITERAL":
        if node.get("constant_id") not in MATH_CONSTANTS or "value" in node:
            raise ContractValidationError("NUMERIC_LITERAL_BYPASSES_PARAMETER_REGISTRY")
    if kind == "FIELD_REF" and not node.get("field_id"):
        raise ContractValidationError("FIELD_ID_REQUIRED")
    for child in node.get("args", []):
        validate_ast(child, parameters, formal_consumer=formal_consumer)
    arity=node.get("args", [])
    if kind == "NOT" and len(arity)!=1:
        raise ContractValidationError("INVALID_AST_ARITY:NOT")
    if kind in {"AND", "OR"} and len(arity)<2:
        raise ContractValidationError(f"INVALID_AST_ARITY:{kind}")


def validate_output_field(field: Mapping[str, Any]) -> None:
    allowed={"field_id","type","unit","producer_contract_id","producer_version","required","nullable","as_of","quality_state","missing_policy","output_digest","display_label"}
    unknown=set(field)-allowed
    if unknown:
        raise ContractValidationError(f"UNKNOWN_OUTPUT_FIELD_KEYS:{','.join(sorted(unknown))}")
    required = field.get("required")
    nullable = field.get("nullable")
    if not isinstance(required, bool) or not isinstance(nullable, bool):
        raise ContractValidationError("REQUIRED_AND_NULLABLE_MUST_BE_EXPLICIT")
    for name in ("field_id", "type", "unit", "producer_contract_id", "producer_version", "missing_policy"):
        if not field.get(name):
            raise ContractValidationError(f"OUTPUT_FIELD_METADATA_MISSING:{name}")


def validate_contract(contract: Mapping[str, Any], parameters: Mapping[str, Mapping[str, Any]], *, formal_consumer: bool = True) -> None:
    required = ("contract_id", "contract_version", "parameter_set_id", "inputs", "producer", "as_of", "quality_requirements", "ast", "window_refs", "rounding", "mutual_exclusion", "outputs", "identity_fields", "unknown_policy", "independent_vectors", "source_digest")
    for key in required:
        if key not in contract:
            raise ContractValidationError(f"CONTRACT_FIELD_MISSING:{key}")
    if not contract["producer"].get("producer_contract_id") or not contract["producer"].get("version"):
        raise ContractValidationError("PRODUCER_METADATA_MISSING")
    refs = contract["window_refs"]
    if not isinstance(refs, list):
        raise ContractValidationError("UNKNOWN_WINDOW_CONTRACT")
    for ref in refs:
        if not isinstance(ref, Mapping) or ref.get("contract_id") not in WINDOWS:
            raise ContractValidationError("UNKNOWN_WINDOW_CONTRACT")
        identity=ref.get("identity")
        if not isinstance(identity, Mapping) or not WINDOW_IDENTITIES[ref["contract_id"]].issubset(identity.keys()):
            raise ContractValidationError("WINDOW_CONTRACT_IDENTITY_INCOMPLETE")
    validate_ast(contract["ast"], parameters, formal_consumer=formal_consumer)
    for field in contract["outputs"]:
        validate_output_field(field)
