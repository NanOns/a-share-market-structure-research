"""Versioned RULE_AST_V2 validator; RULE_AST_V1 remains unchanged."""

from __future__ import annotations

from typing import Any, Mapping

from .algorithm_contract import (
    ContractValidationError,
    WINDOWS,
    WINDOW_IDENTITIES,
    _validate_contract_sections,
    validate_output_field,
    validate_parameter_registry,
)


NODE_TYPES = {"FIELD_REF", "PARAM_REF", "MATH_LITERAL", "ARITHMETIC", "COMPARE", "AND", "OR", "NOT", "LAG", "WINDOW_AGGREGATE", "WINDOW_RANK", "TRANSFORM", "CROSS_SECTION"}
AGGREGATES = {"MEAN", "SUM", "MIN", "MAX", "COUNT", "POP_STDDEV"}
TRANSFORMS = {"LOG", "SIMPLE_RETURN", "ABS", "DIFFERENCE"}
CROSS_SECTION_OPS = {"MIDRANK", "MEAN", "MEDIAN", "COUNT", "COUNT_TRUE", "SUM", "MIN", "MAX"}
WINDOW_RANK_OPS = {"MIDRANK_PERCENTILE"}


def validate_ast_v2(node: Mapping[str, Any], parameters: Mapping[str, Mapping[str, Any]], *,
                    allowed_fields: set[str], window_refs: Mapping[str, Mapping[str, Any]],
                    enum_contracts: Mapping[str, Any] | None = None) -> None:
    if not isinstance(node, Mapping):
        raise ContractValidationError("AST_V2_NODE_OBJECT_REQUIRED")
    kind = node.get("type")
    if kind not in NODE_TYPES:
        raise ContractValidationError(f"AST_V2_UNKNOWN_NODE:{kind}")
    leaf_keys = {
        "FIELD_REF": {"type", "field_id", "value_type"},
        "PARAM_REF": {"type", "parameter_id"},
        "MATH_LITERAL": {"type", "constant_id"},
    }
    if kind in leaf_keys:
        if set(node) != leaf_keys[kind]:
            raise ContractValidationError(f"AST_V2_LEAF_SCHEMA:{kind}")
        if kind == "FIELD_REF":
            if node["field_id"] not in allowed_fields:
                raise ContractValidationError(f"AST_V2_UNDECLARED_FIELD:{node['field_id']}")
            if node["value_type"] not in {"NUMBER", "BOOLEAN", "SESSION_SERIES", "MEMBER_SET", "QUALITY_STATE"}:
                raise ContractValidationError("AST_V2_FIELD_TYPE_INVALID")
        elif kind == "PARAM_REF":
            parameter = parameters.get(node["parameter_id"])
            if parameter is None or parameter.get("status") == "RETIRED" or parameter.get("value") is None:
                raise ContractValidationError(f"AST_V2_PARAMETER_NOT_ACTIVE:{node['parameter_id']}")
        elif node["constant_id"] not in {"PI", "E"}:
            raise ContractValidationError("AST_V2_MATH_CONSTANT_INVALID")
        return

    if kind == "LAG":
        if set(node) != {"type", "source", "offset", "direction"}:
            raise ContractValidationError("AST_V2_LAG_SCHEMA")
        if node["direction"] != "PRIOR_ONLY":
            raise ContractValidationError("AST_V2_FUTURE_OFFSET_PROHIBITED")
        offset = node["offset"]
        if not isinstance(offset, Mapping) or offset.get("type") != "PARAM_REF":
            raise ContractValidationError("AST_V2_LAG_OFFSET_MUST_REFERENCE_PARAMETER")
        parameter = parameters.get(offset.get("parameter_id"))
        if parameter is None or isinstance(parameter.get("value"), bool) or not isinstance(parameter.get("value"), (int, float)) or parameter["value"] <= 0:
            raise ContractValidationError("AST_V2_LAG_OFFSET_MUST_BE_POSITIVE_PARAMETER")
        validate_ast_v2(offset, parameters, allowed_fields=allowed_fields,
                         window_refs=window_refs, enum_contracts=enum_contracts)
        validate_ast_v2(node["source"], parameters, allowed_fields=allowed_fields,
                         window_refs=window_refs, enum_contracts=enum_contracts)
        return

    if kind == "WINDOW_AGGREGATE":
        required = {"type", "operator", "source", "window_contract_id", "window_size", "include_current", "missing_policy"}
        if set(node) != required:
            raise ContractValidationError("AST_V2_WINDOW_AGGREGATE_SCHEMA")
        if node["operator"] not in AGGREGATES:
            raise ContractValidationError("AST_V2_AGGREGATE_OPERATOR_INVALID")
        ref = window_refs.get(node["window_contract_id"])
        if ref is None or node["window_contract_id"] not in WINDOWS:
            raise ContractValidationError("AST_V2_WINDOW_CONTRACT_UNKNOWN")
        if not WINDOW_IDENTITIES[node["window_contract_id"]].issubset(ref["identity"].keys()):
            raise ContractValidationError("AST_V2_WINDOW_IDENTITY_INCOMPLETE")
        if node["window_contract_id"] == "FORWARD_SESSION_WINDOW_V1":
            raise ContractValidationError("AST_V2_FORWARD_WINDOW_FORBIDDEN_FOR_CORE")
        if not isinstance(node["include_current"], bool):
            raise ContractValidationError("AST_V2_INCLUDE_CURRENT_REQUIRED")
        if node["missing_policy"] != "PROPAGATE_UNKNOWN_NO_DROP_NO_SHORTEN":
            raise ContractValidationError("AST_V2_WINDOW_MISSING_POLICY_INVALID")
        size = node["window_size"]
        if not isinstance(size, Mapping) or size.get("type") != "PARAM_REF":
            raise ContractValidationError("AST_V2_WINDOW_SIZE_MUST_REFERENCE_PARAMETER")
        parameter = parameters.get(size.get("parameter_id"))
        if parameter is None or isinstance(parameter.get("value"), bool) or not isinstance(parameter.get("value"), (int, float)) or parameter["value"] <= 0:
            raise ContractValidationError("AST_V2_WINDOW_SIZE_PARAMETER_INVALID")
        validate_ast_v2(size, parameters, allowed_fields=allowed_fields,
                         window_refs=window_refs, enum_contracts=enum_contracts)
        validate_ast_v2(node["source"], parameters, allowed_fields=allowed_fields,
                         window_refs=window_refs, enum_contracts=enum_contracts)
        return

    if kind == "TRANSFORM":
        if set(node) != {"type", "operator", "args"} or node["operator"] not in TRANSFORMS:
            raise ContractValidationError("AST_V2_TRANSFORM_SCHEMA_OR_OPERATOR")
        if not isinstance(node["args"], list) or len(node["args"]) != (2 if node["operator"] in {"SIMPLE_RETURN", "DIFFERENCE"} else 1):
            raise ContractValidationError("AST_V2_TRANSFORM_ARITY")
        for child in node["args"]:
            validate_ast_v2(child, parameters, allowed_fields=allowed_fields,
                             window_refs=window_refs, enum_contracts=enum_contracts)
        return

    if kind == "WINDOW_RANK":
        required = {"type", "operator", "source", "target_ref", "window_contract_id", "window_size", "include_target", "tie_policy", "missing_policy"}
        if set(node) != required or node["operator"] not in WINDOW_RANK_OPS:
            raise ContractValidationError("AST_V2_WINDOW_RANK_SCHEMA_OR_OPERATOR")
        if node["window_contract_id"] != "TECHNICAL_BAR_WINDOW_V1" or node["window_contract_id"] not in window_refs:
            raise ContractValidationError("AST_V2_WINDOW_RANK_CONTRACT_INVALID")
        if node["target_ref"] not in allowed_fields or not isinstance(node["include_target"], bool):
            raise ContractValidationError("AST_V2_WINDOW_RANK_TARGET_INVALID")
        if node["tie_policy"] != "MIDRANK_PERCENTILE_V1" or node["missing_policy"] != "PROPAGATE_UNKNOWN_NO_DROP_NO_SHORTEN":
            raise ContractValidationError("AST_V2_WINDOW_RANK_POLICY_INVALID")
        size = node["window_size"]
        if not isinstance(size, Mapping) or size.get("type") != "PARAM_REF" or size.get("parameter_id") not in parameters:
            raise ContractValidationError("AST_V2_WINDOW_RANK_SIZE_PARAMETER_REQUIRED")
        parameter = parameters[size["parameter_id"]]
        if isinstance(parameter.get("value"), bool) or not isinstance(parameter.get("value"), (int, float)) or parameter["value"] <= 0:
            raise ContractValidationError("AST_V2_WINDOW_RANK_SIZE_PARAMETER_INVALID")
        validate_ast_v2(size, parameters, allowed_fields=allowed_fields,
                         window_refs=window_refs, enum_contracts=enum_contracts)
        validate_ast_v2(node["source"], parameters, allowed_fields=allowed_fields,
                         window_refs=window_refs, enum_contracts=enum_contracts)
        return

    if kind == "CROSS_SECTION":
        required = {"type", "operator", "source", "universe_ref", "evaluable_policy", "tie_policy"}
        allowed = required | {"quality_ref"}
        if not required.issubset(node) or set(node) - allowed or node["operator"] not in CROSS_SECTION_OPS:
            raise ContractValidationError("AST_V2_CROSS_SECTION_SCHEMA_OR_OPERATOR")
        if node["universe_ref"] not in allowed_fields:
            raise ContractValidationError("AST_V2_PIT_UNIVERSE_INPUT_UNDECLARED")
        same_date_policy = "SAME_DATE_PIT_EVALUABLE_EXCLUDE_UNKNOWN_RETAIN_COUNTS"
        field_quality_policy = "FIELD_LOCAL_QUALITY_OBSERVED_EXCLUDE_UNKNOWN_RETAIN_COUNTS"
        if node["evaluable_policy"] not in {same_date_policy, field_quality_policy}:
            raise ContractValidationError("AST_V2_CROSS_SECTION_QUALITY_POLICY_INVALID")
        if node["evaluable_policy"] == field_quality_policy and node.get("quality_ref") not in allowed_fields:
            raise ContractValidationError("AST_V2_FIELD_LOCAL_QUALITY_REF_UNDECLARED")
        if "quality_ref" in node and node["quality_ref"] not in allowed_fields:
            raise ContractValidationError("AST_V2_CROSS_SECTION_QUALITY_REF_UNDECLARED")
        if node["operator"] == "MIDRANK" and node["tie_policy"] != "MIDRANK_PERCENTILE_V1":
            raise ContractValidationError("AST_V2_MIDRANK_TIE_POLICY_INVALID")
        if node["operator"] != "MIDRANK" and node["tie_policy"] != "NOT_APPLICABLE":
            raise ContractValidationError("AST_V2_NONRANK_TIE_POLICY_INVALID")
        validate_ast_v2(node["source"], parameters, allowed_fields=allowed_fields,
                         window_refs=window_refs, enum_contracts=enum_contracts)
        return

    if kind in {"ARITHMETIC", "COMPARE", "AND", "OR", "NOT"}:
        required = {"type", "operator", "args"}
        if set(node) != required or not isinstance(node["args"], list):
            raise ContractValidationError(f"AST_V2_SCALAR_NODE_SCHEMA:{kind}")
        allowed = {"ARITHMETIC": {"ADD", "SUB", "MUL", "DIV", "MIN", "MAX"},
                   "COMPARE": {"GT", "GTE", "LT", "LTE", "EQ", "NE"},
                   "AND": {"AND"}, "OR": {"OR"}, "NOT": {"NOT"}}[kind]
        if node["operator"] not in allowed:
            raise ContractValidationError(f"AST_V2_SCALAR_OPERATOR_INVALID:{kind}")
        arity = len(node["args"])
        if (kind == "NOT" and arity != 1) or (kind in {"AND", "OR"} and arity < 2) or (kind in {"ARITHMETIC", "COMPARE"} and arity != 2):
            raise ContractValidationError(f"AST_V2_SCALAR_ARITY:{kind}")
        for child in node["args"]:
            validate_ast_v2(child, parameters, allowed_fields=allowed_fields,
                             window_refs=window_refs, enum_contracts=enum_contracts)
        return


def validate_contract_v12(contract: Mapping[str, Any], registry: Mapping[str, Any], base_framework: Mapping[str, Any],
                          framework_extension: Mapping[str, Any], framework_extension_sha256: str) -> None:
    required = {"contract_id", "contract_version", "parameter_set_id", "inputs", "producer", "as_of", "quality_requirements", "ast", "window_refs", "rounding", "mutual_exclusion", "outputs", "identity_fields", "unknown_policy", "independent_vectors", "source_digest", "enum_contracts", "ast_version", "framework_extension_id", "framework_extension_version", "framework_extension_sha256"}
    if not required.issubset(contract):
        raise ContractValidationError(f"AST_V2_CONTRACT_FIELDS_MISSING:{','.join(sorted(required-set(contract)))}")
    if (contract["ast_version"] != "RULE_AST_V2" or registry.get("parameter_set_id") != contract["parameter_set_id"]
            or framework_extension.get("contract_id") != "V4_ALGORITHM_CONTRACT_FRAMEWORK_V1"
            or framework_extension.get("version") != "1.2.0"
            or framework_extension.get("algorithm_ast", {}).get("version") != "RULE_AST_V2"
            or set(framework_extension.get("algorithm_ast", {}).get("cross_section_operators", [])) != CROSS_SECTION_OPS
            or framework_extension.get("compatibility", {}).get("base_version") != base_framework.get("version")
            or framework_extension.get("compatibility", {}).get("base_is_immutable") is not True
            or base_framework.get("version") != "1.1.0"
            or contract["framework_extension_id"] != framework_extension["contract_id"]
            or contract["framework_extension_version"] != framework_extension["version"]
            or contract["framework_extension_sha256"] != framework_extension_sha256):
        raise ContractValidationError("AST_V2_CONTRACT_VERSION_OR_PARAMETER_SET_MISMATCH")
    if not isinstance(framework_extension_sha256, str) or len(framework_extension_sha256) != 64:
        raise ContractValidationError("AST_V2_FRAMEWORK_EXTENSION_DIGEST_INVALID")
    parameters = validate_parameter_registry(registry, base_framework)
    _validate_contract_sections(contract)
    if not isinstance(contract["source_digest"], str) or len(contract["source_digest"]) != 64:
        raise ContractValidationError("AST_V2_SOURCE_DIGEST_INVALID")
    for output in contract["outputs"]:
        validate_output_field(output)
    if not isinstance(contract["window_refs"], list) or not contract["window_refs"]:
        raise ContractValidationError("AST_V2_WINDOW_REFS_REQUIRED")
    window_refs = {}
    for ref in contract["window_refs"]:
        if not isinstance(ref, Mapping) or set(ref) != {"contract_id", "identity"} or ref["contract_id"] not in WINDOWS:
            raise ContractValidationError("AST_V2_WINDOW_REF_SCHEMA_INVALID")
        if ref["contract_id"] == "FORWARD_SESSION_WINDOW_V1":
            raise ContractValidationError("AST_V2_FORWARD_WINDOW_FORBIDDEN_FOR_CORE")
        identity = ref["identity"]
        if not isinstance(identity, Mapping) or not WINDOW_IDENTITIES[ref["contract_id"]].issubset(identity.keys()):
            raise ContractValidationError("AST_V2_WINDOW_REF_IDENTITY_INCOMPLETE")
        if ref["contract_id"] in window_refs:
            raise ContractValidationError("AST_V2_DUPLICATE_WINDOW_REF")
        window_refs[ref["contract_id"]] = ref
    allowed_fields = {item["field_id"] for item in contract["inputs"]}
    validate_ast_v2(contract["ast"], parameters, allowed_fields=allowed_fields, window_refs=window_refs,
                    enum_contracts=contract["enum_contracts"])
