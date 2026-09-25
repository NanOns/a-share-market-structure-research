from __future__ import annotations

from datetime import datetime
from enum import Enum
import math
import re
from typing import Any, Mapping


class ContractValidationError(ValueError):
    pass


class Truth(str, Enum):
    TRUE = "TRUE"
    FALSE = "FALSE"
    UNKNOWN = "UNKNOWN"


AST_NODES = {"AND", "OR", "NOT", "COMPARE", "ARITHMETIC", "FIELD_REF", "PARAM_REF", "ENUM_LITERAL", "MATH_LITERAL"}
COMPARE_OPERATORS = {"GT", "GTE", "LT", "LTE", "EQ", "NE", "IN", "IS_NULL", "IS_NOT_NULL"}
ARITHMETIC_OPERATORS = {"ADD", "SUB", "MUL", "DIV", "MIN", "MAX"}
WINDOWS = {"TECHNICAL_BAR_WINDOW_V1", "CROSS_SECTION_SESSION_WINDOW_V1", "FORWARD_SESSION_WINDOW_V1"}
WINDOW_IDENTITIES = {
    "TECHNICAL_BAR_WINDOW_V1": {"security_id", "source_snapshot_id", "trade_date", "adjustment_basis_id"},
    "CROSS_SECTION_SESSION_WINDOW_V1": {"market_calendar_id", "start_session", "end_session", "universe_snapshot_id", "adjustment_basis_id"},
    "FORWARD_SESSION_WINDOW_V1": {"market_calendar_id", "frozen_t0", "horizon_n", "evaluation_basis_id"},
}
MATH_CONSTANTS = {"PI", "E"}
PARAMETER_STATUSES = {"ENGINEERING_CANDIDATE", "SHADOW_FROZEN", "PROVISIONAL", "SUPPORTED", "RETIRED"}
PARAMETER_REQUIRED_FIELDS = {
    "parameter_id", "contract_scope", "value", "unit", "minimum", "maximum",
    "inclusive_boundaries", "status", "reason", "introduced_version", "approved_at",
    "supersedes", "owner_stage",
}
OUTPUT_FIELD_KEYS = {
    "field_id", "type", "unit", "producer_contract_id", "producer_version",
    "requiredness", "nullable", "as_of", "quality_state", "missing_policy",
    "output_digest", "display_label",
}
SECTION_SCHEMAS = {
    "inputs": {"type": "array", "item_required": ["field_id", "type", "unit", "source", "required"], "item_allowed": ["field_id", "type", "unit", "source", "required"]},
    "as_of": {"type": "object", "required": ["field_id", "timestamp_semantics"], "allowed": ["field_id", "timestamp_semantics"]},
    "quality_requirements": {"type": "object", "required": ["acceptable_states", "unknown_action"], "allowed": ["acceptable_states", "unknown_action"]},
    "rounding": {"type": "object", "required": ["mode", "precision"], "allowed": ["mode", "precision"]},
    "mutual_exclusion": {"type": "array", "item_type": "array_of_distinct_strings"},
    "identity_fields": {"type": "array", "item_type": "unique_nonempty_strings"},
    "unknown_policy": {"type": "object", "required": ["action", "reason_code"], "allowed": ["action", "reason_code"]},
    "independent_vectors": {"type": "array", "item_required": ["vector_id", "input", "expected", "source_digest"], "item_allowed": ["vector_id", "input", "expected", "source_digest"]},
    "enum_contracts": {"type": "object", "value_required": ["version", "values"], "value_allowed": ["version", "values"]},
}
SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")


def _string(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ContractValidationError(f"NONEMPTY_STRING_REQUIRED:{name}")
    return value


def _object(value: Any, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ContractValidationError(f"OBJECT_REQUIRED:{name}")
    return value


def _finite_number(value: Any, name: str, *, nullable: bool = False) -> float | None:
    if value is None and nullable:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
        raise ContractValidationError(f"FINITE_NUMBER_REQUIRED:{name}")
    return float(value)


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


def validate_parameter_registry(registry: Mapping[str, Any], framework: Mapping[str, Any] | None = None) -> dict[str, Mapping[str, Any]]:
    if registry.get("contract_id") != "PARAMETER_REGISTRY_V1":
        raise ContractValidationError("PARAMETER_REGISTRY_CONTRACT_ID_MISMATCH")
    _string(registry.get("registry_version"), "registry_version")
    _string(registry.get("parameter_set_id"), "parameter_set_id")
    entries = registry.get("entries")
    if not isinstance(entries, list):
        raise ContractValidationError("PARAMETER_ENTRIES_REQUIRED")
    expected_fields = PARAMETER_REQUIRED_FIELDS
    expected_statuses = PARAMETER_STATUSES
    if framework is not None:
        parameter_contract = _object(framework.get("parameter_instance_contract"), "parameter_instance_contract")
        expected_fields = set(parameter_contract.get("required_fields", []))
        expected_statuses = set(parameter_contract.get("statuses", []))
        if expected_fields != PARAMETER_REQUIRED_FIELDS or expected_statuses != PARAMETER_STATUSES:
            raise ContractValidationError("FRAMEWORK_PARAMETER_SCHEMA_MISMATCH")

    result: dict[str, Mapping[str, Any]] = {}
    for index, entry in enumerate(entries):
        if not isinstance(entry, Mapping):
            raise ContractValidationError(f"PARAMETER_ENTRY_OBJECT_REQUIRED:{index}")
        missing = expected_fields - set(entry)
        if missing:
            raise ContractValidationError(f"PARAMETER_REQUIRED_FIELDS_MISSING:{index}:{','.join(sorted(missing))}")
        pid = _string(entry.get("parameter_id"), f"entries[{index}].parameter_id")
        if pid in result:
            raise ContractValidationError(f"DUPLICATE_PARAMETER_ID:{pid}")
        for key in ("contract_scope", "unit", "inclusive_boundaries", "reason", "introduced_version", "owner_stage"):
            _string(entry.get(key), f"{pid}.{key}")
        status = entry.get("status")
        if status not in expected_statuses:
            raise ContractValidationError(f"UNKNOWN_PARAMETER_STATUS:{pid}:{status}")
        value = _finite_number(entry.get("value"), f"{pid}.value", nullable=True)
        minimum = _finite_number(entry.get("minimum"), f"{pid}.minimum", nullable=True)
        maximum = _finite_number(entry.get("maximum"), f"{pid}.maximum", nullable=True)
        if minimum is not None and maximum is not None and minimum > maximum:
            raise ContractValidationError(f"PARAMETER_BOUNDS_INVERTED:{pid}")
        if value is not None and ((minimum is not None and value < minimum) or (maximum is not None and value > maximum)):
            raise ContractValidationError(f"PARAMETER_OUT_OF_BOUNDS:{pid}")
        if entry.get("approved_at") is not None:
            raw = _string(entry["approved_at"], f"{pid}.approved_at")
            try:
                datetime.fromisoformat(raw.replace("Z", "+00:00"))
            except ValueError as exc:
                raise ContractValidationError(f"PARAMETER_APPROVAL_TIMESTAMP_INVALID:{pid}") from exc
        elif status in {"SHADOW_FROZEN", "PROVISIONAL", "SUPPORTED"}:
            raise ContractValidationError(f"APPROVAL_TIMESTAMP_REQUIRED:{pid}")
        if entry.get("supersedes") is not None:
            _string(entry["supersedes"], f"{pid}.supersedes")
        if status == "RETIRED" and value is not None:
            raise ContractValidationError(f"RETIRED_PARAMETER_HAS_ACTIVE_VALUE:{pid}")
        result[pid] = entry
    return result


def validate_framework_document(framework: Mapping[str, Any], registry: Mapping[str, Any] | None = None) -> None:
    if framework.get("contract_id") != "V4_ALGORITHM_CONTRACT_FRAMEWORK_V1":
        raise ContractValidationError("FRAMEWORK_CONTRACT_ID_MISMATCH")
    _string(framework.get("version"), "framework.version")
    ast = _object(framework.get("rule_ast"), "rule_ast")
    if set(ast.get("node_types", [])) != AST_NODES:
        raise ContractValidationError("FRAMEWORK_AST_NODE_SET_MISMATCH")
    if set(ast.get("compare_operators", [])) != COMPARE_OPERATORS:
        raise ContractValidationError("FRAMEWORK_COMPARE_OPERATOR_SET_MISMATCH")
    if set(ast.get("arithmetic_operators", [])) != ARITHMETIC_OPERATORS:
        raise ContractValidationError("FRAMEWORK_ARITHMETIC_OPERATOR_SET_MISMATCH")
    expected_fields = ["contract_id", "contract_version", "parameter_set_id", "inputs", "producer", "as_of", "quality_requirements", "ast", "window_refs", "rounding", "mutual_exclusion", "outputs", "identity_fields", "unknown_policy", "independent_vectors", "source_digest", "enum_contracts"]
    if ast.get("required_contract_fields") != expected_fields:
        raise ContractValidationError("FRAMEWORK_REQUIRED_CONTRACT_FIELDS_MISMATCH")
    truth = ast.get("kleene", {})
    required_truth = {"FALSE_AND_UNKNOWN": "FALSE", "TRUE_AND_UNKNOWN": "UNKNOWN", "TRUE_OR_UNKNOWN": "TRUE", "FALSE_OR_UNKNOWN": "UNKNOWN", "NOT_UNKNOWN": "UNKNOWN"}
    if not isinstance(truth, Mapping) or any(truth.get(key) != value for key, value in required_truth.items()):
        raise ContractValidationError("FRAMEWORK_KLEENE_TABLE_MISMATCH")
    if "never coerce null/unknown to pass" not in ast.get("hard_safety", ""):
        raise ContractValidationError("UNKNOWN_MUST_FAIL_CLOSED")

    schema = _object(framework.get("schema_contract"), "schema_contract")
    if schema.get("version") != "ALGORITHM_OUTPUT_SCHEMA_V1":
        raise ContractValidationError("OUTPUT_SCHEMA_VERSION_MISMATCH")
    if set(schema.get("required_field_metadata", [])) != OUTPUT_FIELD_KEYS:
        raise ContractValidationError("FRAMEWORK_OUTPUT_METADATA_MISMATCH")
    if schema.get("required_and_nullable_are_independent") is not True or schema.get("unknown_keys") != "REJECT":
        raise ContractValidationError("FRAMEWORK_OUTPUT_POLICY_MISMATCH")

    parameter_contract = _object(framework.get("parameter_instance_contract"), "parameter_instance_contract")
    if set(parameter_contract.get("required_fields", [])) != PARAMETER_REQUIRED_FIELDS:
        raise ContractValidationError("FRAMEWORK_PARAMETER_FIELDS_MISMATCH")
    if set(parameter_contract.get("statuses", [])) != PARAMETER_STATUSES:
        raise ContractValidationError("FRAMEWORK_PARAMETER_STATUSES_MISMATCH")

    section_schema = _object(framework.get("contract_section_schema"), "contract_section_schema")
    if section_schema != SECTION_SCHEMAS:
        raise ContractValidationError("FRAMEWORK_CONTRACT_SECTION_SCHEMA_MISMATCH")
    enums = _object(framework.get("enum_literal_contract"), "enum_literal_contract")
    if set(enums.get("required_identity_fields", [])) != {"enum_id", "enum_version", "value"}:
        raise ContractValidationError("FRAMEWORK_ENUM_LITERAL_IDENTITY_MISMATCH")

    windows = _object(framework.get("window_contracts"), "window_contracts")
    if set(windows) != WINDOWS:
        raise ContractValidationError("FRAMEWORK_WINDOW_SET_MISMATCH")
    for name, required_identity in WINDOW_IDENTITIES.items():
        identity = windows[name].get("identity")
        if not isinstance(identity, list) or not required_identity.issubset(identity):
            raise ContractValidationError(f"FRAMEWORK_WINDOW_IDENTITY_MISMATCH:{name}")
    if registry is not None:
        validate_parameter_registry(registry, framework)


def validate_output_field(field: Mapping[str, Any]) -> None:
    if not isinstance(field, Mapping):
        raise ContractValidationError("OUTPUT_FIELD_MUST_BE_OBJECT")
    unknown = set(field) - OUTPUT_FIELD_KEYS
    missing = OUTPUT_FIELD_KEYS - set(field)
    if unknown:
        raise ContractValidationError(f"UNKNOWN_OUTPUT_FIELD_KEYS:{','.join(sorted(unknown))}")
    if missing:
        raise ContractValidationError(f"OUTPUT_FIELD_METADATA_MISSING:{','.join(sorted(missing))}")
    if field.get("requiredness") not in {"REQUIRED", "OPTIONAL"}:
        raise ContractValidationError("OUTPUT_REQUIREDNESS_INVALID")
    if not isinstance(field.get("nullable"), bool):
        raise ContractValidationError("OUTPUT_NULLABLE_MUST_BE_EXPLICIT")
    for name in ("field_id", "type", "unit", "producer_contract_id", "producer_version", "as_of", "quality_state", "missing_policy", "output_digest", "display_label"):
        _string(field.get(name), f"output.{name}")
    if not SHA256_RE.fullmatch(field["output_digest"]):
        raise ContractValidationError("OUTPUT_DIGEST_INVALID")


def _validate_enum_contracts(enum_contracts: Any) -> Mapping[str, Any]:
    enums = _object(enum_contracts, "enum_contracts")
    for enum_id, item in enums.items():
        _string(enum_id, "enum_id")
        enum_item = _object(item, f"enum_contracts.{enum_id}")
        if set(enum_item) != {"version", "values"}:
            raise ContractValidationError(f"ENUM_CONTRACT_KEYS_INVALID:{enum_id}")
        _string(item.get("version"), f"enum_contracts.{enum_id}.version")
        values = item.get("values")
        if not isinstance(values, list) or not values or any(not isinstance(v, str) or not v for v in values) or len(values) != len(set(values)):
            raise ContractValidationError(f"ENUM_VALUES_INVALID:{enum_id}")
    return enums


def validate_ast(node: Mapping[str, Any], parameters: Mapping[str, Mapping[str, Any]], *, formal_consumer: bool = True, enum_contracts: Mapping[str, Any] | None = None, allowed_fields: set[str] | None = None) -> None:
    if not isinstance(node, Mapping):
        raise ContractValidationError("AST_NODE_MUST_BE_OBJECT")
    kind = node.get("type")
    if kind not in AST_NODES:
        raise ContractValidationError(f"UNKNOWN_AST_NODE:{kind}")
    allowed_keys = {
        "AND": {"type", "args"}, "OR": {"type", "args"}, "NOT": {"type", "args"},
        "COMPARE": {"type", "operator", "args"}, "ARITHMETIC": {"type", "operator", "args"},
        "FIELD_REF": {"type", "field_id"}, "PARAM_REF": {"type", "parameter_id"},
        "ENUM_LITERAL": {"type", "enum_id", "enum_version", "value"},
        "MATH_LITERAL": {"type", "constant_id"},
    }[kind]
    if set(node) - allowed_keys:
        raise ContractValidationError(f"AST_UNKNOWN_KEYS:{kind}:{','.join(sorted(set(node)-allowed_keys))}")
    args = node.get("args", [])
    if kind in {"AND", "OR", "NOT", "COMPARE", "ARITHMETIC"}:
        if not isinstance(args, list):
            raise ContractValidationError(f"AST_ARGS_ARRAY_REQUIRED:{kind}")
        op = node.get("operator")
        if kind == "NOT" and len(args) != 1:
            raise ContractValidationError("INVALID_AST_ARITY:NOT")
        if kind in {"AND", "OR"} and len(args) < 2:
            raise ContractValidationError(f"INVALID_AST_ARITY:{kind}")
        if kind == "COMPARE":
            if op not in COMPARE_OPERATORS:
                raise ContractValidationError(f"UNKNOWN_COMPARE_OPERATOR:{op}")
            valid_arity = (len(args) == 1 if op in {"IS_NULL", "IS_NOT_NULL"} else len(args) == 2 if op != "IN" else len(args) >= 2)
            if not valid_arity:
                raise ContractValidationError(f"INVALID_COMPARE_ARITY:{op}:{len(args)}")
        if kind == "ARITHMETIC":
            if op not in ARITHMETIC_OPERATORS:
                raise ContractValidationError(f"UNKNOWN_ARITHMETIC_OPERATOR:{op}")
            valid_arity = len(args) >= 2 if op in {"MIN", "MAX"} else len(args) == 2
            if not valid_arity:
                raise ContractValidationError(f"INVALID_ARITHMETIC_ARITY:{op}:{len(args)}")
        for child in args:
            validate_ast(child, parameters, formal_consumer=formal_consumer, enum_contracts=enum_contracts, allowed_fields=allowed_fields)
    elif "args" in node:
        raise ContractValidationError(f"AST_LEAF_HAS_ARGS:{kind}")

    if kind == "FIELD_REF":
        field_id = _string(node.get("field_id"), "field_id")
        if allowed_fields is not None and field_id not in allowed_fields:
            raise ContractValidationError(f"AST_FIELD_NOT_DECLARED:{field_id}")
    elif kind == "PARAM_REF":
        pid = node.get("parameter_id")
        if pid not in parameters:
            raise ContractValidationError(f"UNKNOWN_PARAMETER:{pid}")
        parameter = parameters[pid]
        if parameter.get("status") == "RETIRED":
            raise ContractValidationError(f"RETIRED_PARAMETER:{pid}")
        if formal_consumer and (parameter.get("value") is None or parameter.get("status") == "ENGINEERING_CANDIDATE"):
            raise ContractValidationError(f"PARAMETER_NOT_FORMAL:{pid}")
    elif kind == "MATH_LITERAL":
        if node.get("constant_id") not in MATH_CONSTANTS:
            raise ContractValidationError("MATH_CONSTANT_ID_UNKNOWN")
    elif kind == "ENUM_LITERAL":
        enums = _validate_enum_contracts(enum_contracts)
        enum_id = _string(node.get("enum_id"), "enum_id")
        enum_version = _string(node.get("enum_version"), "enum_version")
        if enum_id not in enums:
            raise ContractValidationError(f"ENUM_ID_UNDECLARED:{enum_id}")
        declared = enums[enum_id]
        if declared.get("version") != enum_version or node.get("value") not in declared.get("values", []):
            raise ContractValidationError(f"ENUM_IDENTITY_OR_VERSION_MISMATCH:{enum_id}:{enum_version}")


def _validate_contract_sections(contract: Mapping[str, Any]) -> None:
    for key, schema in SECTION_SCHEMAS.items():
        value = contract.get(key)
        if schema["type"] == "object":
            obj = _object(value, key)
            if "allowed" in schema and set(obj) - set(schema["allowed"]):
                raise ContractValidationError(f"CONTRACT_SECTION_UNKNOWN_KEYS:{key}")
            for required in schema.get("required", []):
                if required not in obj:
                    raise ContractValidationError(f"CONTRACT_SECTION_FIELD_MISSING:{key}.{required}")
            if key == "as_of":
                _string(obj.get("field_id"), "as_of.field_id")
                _string(obj.get("timestamp_semantics"), "as_of.timestamp_semantics")
            if key == "quality_requirements":
                states = obj.get("acceptable_states")
                if not isinstance(states, list) or not states or any(not isinstance(x, str) or not x for x in states) or len(states) != len(set(states)):
                    raise ContractValidationError("QUALITY_ACCEPTABLE_STATES_INVALID")
                if obj.get("unknown_action") not in {"UNKNOWN", "REJECT"}:
                    raise ContractValidationError("QUALITY_UNKNOWN_ACTION_INVALID")
        elif schema["type"] == "array":
            if not isinstance(value, list):
                raise ContractValidationError(f"CONTRACT_SECTION_ARRAY_REQUIRED:{key}")
            if key == "inputs":
                if not value:
                    raise ContractValidationError("CONTRACT_INPUTS_REQUIRED")
                for index, item in enumerate(value):
                    if not isinstance(item, Mapping) or not set(schema["item_required"]).issubset(item) or set(item) - set(schema["item_allowed"]):
                        raise ContractValidationError(f"CONTRACT_INPUT_SCHEMA_INVALID:{index}")
                    for field in ("field_id", "type", "unit", "source"):
                        _string(item.get(field), f"inputs[{index}].{field}")
                    if not isinstance(item.get("required"), bool):
                        raise ContractValidationError(f"CONTRACT_INPUT_REQUIRED_FLAG_INVALID:{index}")
            elif key == "mutual_exclusion":
                for index, group in enumerate(value):
                    if not isinstance(group, list) or len(group) < 2 or any(not isinstance(x, str) or not x for x in group) or len(group) != len(set(group)):
                        raise ContractValidationError(f"MUTUAL_EXCLUSION_GROUP_INVALID:{index}")
            elif key == "identity_fields":
                if not value or any(not isinstance(x, str) or not x for x in value) or len(value) != len(set(value)):
                    raise ContractValidationError("IDENTITY_FIELDS_INVALID")
            elif key == "independent_vectors":
                if not value:
                    raise ContractValidationError("INDEPENDENT_VECTORS_REQUIRED")
                seen = set()
                for index, vector in enumerate(value):
                    if not isinstance(vector, Mapping) or not set(schema["item_required"]).issubset(vector) or set(vector) - set(schema["item_allowed"]):
                        raise ContractValidationError(f"INDEPENDENT_VECTOR_SCHEMA_INVALID:{index}")
                    vid = _string(vector["vector_id"], f"independent_vectors[{index}].vector_id")
                    if vid in seen:
                        raise ContractValidationError(f"DUPLICATE_VECTOR_ID:{vid}")
                    seen.add(vid)
                    if not SHA256_RE.fullmatch(str(vector["source_digest"])):
                        raise ContractValidationError(f"VECTOR_SOURCE_DIGEST_INVALID:{vid}")
        elif key == "enum_contracts":
            _validate_enum_contracts(value)
    producer = _object(contract.get("producer"), "producer")
    _string(producer.get("producer_contract_id"), "producer.producer_contract_id")
    _string(producer.get("version"), "producer.version")
    rounding = contract["rounding"]
    if set(rounding) - set(SECTION_SCHEMAS["rounding"]["allowed"]):
        raise ContractValidationError("ROUNDING_UNKNOWN_KEYS")
    if rounding.get("mode") not in {"NONE", "HALF_UP", "HALF_EVEN", "TRUNCATE"}:
        raise ContractValidationError("ROUNDING_MODE_INVALID")
    precision = rounding.get("precision")
    if precision is not None and (isinstance(precision, bool) or not isinstance(precision, int) or precision < 0):
        raise ContractValidationError("ROUNDING_PRECISION_INVALID")
    unknown_policy = contract["unknown_policy"]
    if set(unknown_policy) - set(SECTION_SCHEMAS["unknown_policy"]["allowed"]):
        raise ContractValidationError("UNKNOWN_POLICY_UNKNOWN_KEYS")
    if unknown_policy.get("action") not in {"UNKNOWN", "REJECT", "DIAGNOSTIC_ONLY"}:
        raise ContractValidationError("UNKNOWN_POLICY_ACTION_INVALID")
    _string(unknown_policy.get("reason_code"), "unknown_policy.reason_code")


def validate_contract(contract: Mapping[str, Any], parameters: Mapping[str, Mapping[str, Any]], *, formal_consumer: bool = True) -> None:
    required = ("contract_id", "contract_version", "parameter_set_id", "inputs", "producer", "as_of", "quality_requirements", "ast", "window_refs", "rounding", "mutual_exclusion", "outputs", "identity_fields", "unknown_policy", "independent_vectors", "source_digest", "enum_contracts")
    for key in required:
        if key not in contract:
            raise ContractValidationError(f"CONTRACT_FIELD_MISSING:{key}")
    for key in ("contract_id", "contract_version", "parameter_set_id"):
        _string(contract.get(key), key)
    _validate_contract_sections(contract)
    if not SHA256_RE.fullmatch(str(contract["source_digest"])):
        raise ContractValidationError("CONTRACT_SOURCE_DIGEST_INVALID")
    refs = contract["window_refs"]
    if not isinstance(refs, list) or not refs:
        raise ContractValidationError("UNKNOWN_WINDOW_CONTRACT")
    for ref in refs:
        if not isinstance(ref, Mapping) or ref.get("contract_id") not in WINDOWS:
            raise ContractValidationError("UNKNOWN_WINDOW_CONTRACT")
        identity = ref.get("identity")
        if not isinstance(identity, Mapping) or not WINDOW_IDENTITIES[ref["contract_id"]].issubset(identity.keys()):
            raise ContractValidationError("WINDOW_CONTRACT_IDENTITY_INCOMPLETE")
    outputs = contract["outputs"]
    if not isinstance(outputs, list) or not outputs:
        raise ContractValidationError("CONTRACT_OUTPUTS_REQUIRED")
    for field in outputs:
        validate_output_field(field)
    allowed_fields = {item["field_id"] for item in contract["inputs"]}
    validate_ast(contract["ast"], parameters, formal_consumer=formal_consumer, enum_contracts=contract["enum_contracts"], allowed_fields=allowed_fields)
