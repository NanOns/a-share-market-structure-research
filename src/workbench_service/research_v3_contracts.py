"""Load and validate the frozen V3 P00-03 contract assets.

The repository already stores several generated YAML files as JSON-compatible
YAML.  P00-03 follows that convention so the contract bundle can be checked
with the standard library and does not introduce a parser dependency.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
import re
from datetime import date, datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "config/research_attention_v3.yaml"
SCHEMA_PATH = ROOT / "config/research_v3_schema.yaml"
REASON_PATH = ROOT / "config/research_v3_reasons.yaml"
FIXTURE_PATH = ROOT / "tests/fixtures/research_v3_p00_03.json"

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class ContractValidationError(ValueError):
    """Raised when a frozen V3 contract object is invalid."""


def _load_json_compatible_yaml(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ContractValidationError(f"CONTRACT_ASSET_INVALID:{path.name}") from exc
    if not isinstance(value, dict):
        raise ContractValidationError(f"CONTRACT_ASSET_OBJECT_REQUIRED:{path.name}")
    return value


def load_contract_bundle(root: str | Path | None = None) -> dict[str, Any]:
    base = Path(root).resolve() if root else ROOT
    return {
        "config": _load_json_compatible_yaml(base / "config/research_attention_v3.yaml"),
        "schema": _load_json_compatible_yaml(base / "config/research_v3_schema.yaml"),
        "reasons": _load_json_compatible_yaml(base / "config/research_v3_reasons.yaml"),
        "fixtures": _load_json_compatible_yaml(base / "tests/fixtures/research_v3_p00_03.json"),
    }


def canonical_hash(value: Any) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def parameter_hash(config: dict[str, Any]) -> str:
    payload = copy.deepcopy(config)
    payload.pop("parameter_hash", None)
    return canonical_hash(payload)


def _valid_date(value: Any) -> bool:
    if not isinstance(value, str) or not _DATE_RE.fullmatch(value):
        return False
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return True


def _valid_timestamp(value: Any) -> bool:
    if not isinstance(value, str) or len(value) < 11 or value[10] != "T":
        return False
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return False
    return parsed.tzinfo is not None and parsed.utcoffset() is not None


def _finite_number(value: Any) -> bool:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    if isinstance(value, int):
        return True
    try:
        return math.isfinite(value)
    except (OverflowError, TypeError, ValueError):
        return False


def _type_matches(value: Any, type_name: str, schema: dict[str, Any]) -> bool:
    if type_name == "string":
        return isinstance(value, str)
    if type_name == "date":
        return _valid_date(value)
    if type_name == "timestamp":
        return _valid_timestamp(value)
    if type_name == "number":
        return _finite_number(value)
    if type_name == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if type_name == "boolean":
        return isinstance(value, bool)
    if type_name == "object":
        return isinstance(value, dict)
    if type_name == "scalar":
        return value is None or isinstance(value, (str, bool)) or _finite_number(value)
    if type_name.startswith("enum:"):
        enum_name = type_name.split(":", 1)[1]
        return value in schema["enums"].get(enum_name, [])
    if type_name.startswith("array:"):
        return isinstance(value, list)
    if type_name.startswith("object:"):
        return isinstance(value, dict)
    raise ContractValidationError(f"SCHEMA_TYPE_UNKNOWN:{type_name}")


def _validate_page_envelope_semantics(value: dict[str, Any], bundle: dict[str, Any]) -> None:
    """Validate the V3 pagination vocabulary without breaking old readers.

    ``total_eligible`` is the legacy spelling.  V3 uses ``eligible_total``;
    accepting either lets the compatibility reader survive while requiring a
    single, non-contradictory eligibility count at the contract boundary.
    """

    eligible = value.get("eligible_total")
    legacy = value.get("total_eligible")
    if "eligible_total" in value and eligible is None:
        raise ContractValidationError("NULL_NOT_ALLOWED:PageEnvelope:eligible_total")
    if "total_eligible" in value and legacy is None:
        raise ContractValidationError("NULL_NOT_ALLOWED:PageEnvelope:total_eligible")
    if eligible is None and legacy is None:
        raise ContractValidationError("PAGE_ELIGIBLE_TOTAL_REQUIRED")
    if eligible is not None and legacy is not None and eligible != legacy:
        raise ContractValidationError("PAGE_ELIGIBLE_TOTAL_ALIAS_MISMATCH")
    for field_name, minimum in (("returned_count", 0), ("total", 0), ("page", 1), ("page_size", 1)):
        field_value = value.get(field_name)
        if isinstance(field_value, int) and not isinstance(field_value, bool) and field_value < minimum:
            raise ContractValidationError(f"PAGE_RANGE_INVALID:{field_name}")
    for field_name in ("eligible_total", "total_eligible", "display_limit"):
        field_value = value.get(field_name)
        if field_value is not None and (not isinstance(field_value, int) or isinstance(field_value, bool) or field_value < 0):
            raise ContractValidationError(f"PAGE_RANGE_INVALID:{field_name}")


def _validate_page_context(value: Any, bundle: dict[str, Any]) -> None:
    if value is None:
        return
    if not isinstance(value, dict):
        raise ContractValidationError("TYPE_INVALID:PageEnvelope:context:object")
    status = value.get("status")
    if status == "READY":
        for object_name in ("ResearchContextReady", "Context"):
            try:
                validate_object(value, object_name, bundle)
                return
            except ContractValidationError:
                continue
        raise ContractValidationError("PAGE_CONTEXT_READY_INVALID")
    if status == "NOT_BUILT":
        validate_object(value, "ResearchContextNotBuilt", bundle)
        return
    if status in {"EMPTY", "UNAVAILABLE", "PARTIAL"}:
        # A page may carry a non-ready context with an explicit capability
        # state; no fake run/snapshot is allowed for these states.
        validate_object(value, "ResearchContextNotBuilt", bundle)
        return
    raise ContractValidationError(f"PAGE_CONTEXT_STATUS_INVALID:{status}")


def validate_object(value: Any, object_name: str, bundle: dict[str, Any]) -> dict[str, Any]:
    schema = bundle["schema"]
    definition = schema["objects"].get(object_name)
    if definition is None:
        raise ContractValidationError(f"SCHEMA_OBJECT_UNKNOWN:{object_name}")
    if not isinstance(value, dict):
        raise ContractValidationError(f"OBJECT_REQUIRED:{object_name}")
    expected_context_status = {
        "Context": "READY",
        "ResearchContextReady": "READY",
        "ResearchContextNotBuilt": "NOT_BUILT",
    }.get(object_name)
    if expected_context_status is not None and value.get("status") != expected_context_status:
        raise ContractValidationError(f"CONTEXT_STATUS_INVALID:{object_name}:{value.get('status')}")
    if object_name == "PageEnvelope":
        _validate_page_envelope_semantics(value, bundle)
    required = set(definition.get("required", []))
    properties = definition.get("properties", {})
    missing = sorted(required - set(value))
    if missing:
        raise ContractValidationError(f"REQUIRED_FIELD_MISSING:{object_name}:{','.join(missing)}")
    if definition.get("additional_properties") is False:
        unknown = sorted(set(value) - set(properties))
        if unknown:
            raise ContractValidationError(f"UNKNOWN_FIELD:{object_name}:{','.join(unknown)}")
    for field_name, field in properties.items():
        if field_name not in value:
            continue
        field_value = value[field_name]
        if field_value is None:
            if not field.get("nullable", False):
                raise ContractValidationError(f"NULL_NOT_ALLOWED:{object_name}:{field_name}")
            continue
        type_name = field["type"]
        if not _type_matches(field_value, type_name, schema):
            raise ContractValidationError(f"TYPE_INVALID:{object_name}:{field_name}:{type_name}")
        if type_name.startswith("array:"):
            child = type_name.split(":", 1)[1]
            if child.startswith("string") and not all(isinstance(item, str) for item in field_value):
                raise ContractValidationError(f"ARRAY_ITEM_INVALID:{object_name}:{field_name}")
            if child in schema["objects"]:
                for item in field_value:
                    validate_object(item, child, bundle)
        if type_name.startswith("object:"):
            child = type_name.split(":", 1)[1]
            if child in schema["objects"]:
                validate_object(field_value, child, bundle)
    if object_name == "PageEnvelope":
        _validate_page_context(value.get("context"), bundle)
    return value


def validate_request(endpoint: str, value: dict[str, Any], bundle: dict[str, Any] | None = None) -> dict[str, Any]:
    bundle = bundle or load_contract_bundle()
    definition = bundle["schema"]["requests"].get(endpoint)
    if definition is None:
        raise ContractValidationError(f"REQUEST_SCHEMA_UNKNOWN:{endpoint}")
    request_schema = {"schema": {**bundle["schema"], "objects": {endpoint: definition}}}
    request_bundle = {**bundle, **request_schema}
    return validate_object(value, endpoint, request_bundle)


def validate_reason(value: dict[str, Any], bundle: dict[str, Any] | None = None) -> dict[str, Any]:
    bundle = bundle or load_contract_bundle()
    validate_object(value, "Reason", bundle)
    entries = {item["code"]: item for item in bundle["reasons"].get("reasons", [])}
    catalog = entries.get(value["code"])
    if catalog is None:
        raise ContractValidationError(f"REASON_CODE_UNKNOWN:{value['code']}")
    if value["label"] != catalog["label"]:
        raise ContractValidationError(f"REASON_LABEL_MISMATCH:{value['code']}")
    return value


def validate_fixture_bundle(bundle: dict[str, Any] | None = None) -> dict[str, Any]:
    bundle = bundle or load_contract_bundle()
    fixtures = bundle["fixtures"]
    if fixtures.get("is_synthetic") is not True or fixtures.get("not_market_data") is not True:
        raise ContractValidationError("FIXTURE_MUST_BE_SYNTHETIC")
    cases = fixtures.get("cases")
    if not isinstance(cases, list) or not cases:
        raise ContractValidationError("FIXTURE_CASES_REQUIRED")
    reason_codes = {item["code"] for item in bundle["reasons"].get("reasons", [])}
    ids: set[str] = set()
    for case in cases:
        fixture_id = case.get("fixture_id")
        if not isinstance(fixture_id, str) or fixture_id in ids:
            raise ContractValidationError("FIXTURE_ID_INVALID_OR_DUPLICATE")
        ids.add(fixture_id)
        if case.get("kind") not in {"SECTOR", "STOCK"}:
            raise ContractValidationError(f"FIXTURE_KIND_INVALID:{fixture_id}")
        expected = case.get("expected", {})
        if not isinstance(expected, dict):
            raise ContractValidationError(f"FIXTURE_EXPECTED_OBJECT_REQUIRED:{fixture_id}")
        unknown_reasons = set(expected.get("reason_codes", [])) - reason_codes
        if unknown_reasons:
            raise ContractValidationError(f"FIXTURE_REASON_UNKNOWN:{fixture_id}")
    return fixtures


def validate_contract_bundle(bundle: dict[str, Any] | None = None) -> dict[str, Any]:
    bundle = bundle or load_contract_bundle()
    config = bundle["config"]
    if config.get("parameter_hash") != parameter_hash(config):
        raise ContractValidationError("PARAMETER_HASH_MISMATCH")
    if config.get("algorithm_version") != "RESEARCH_V3_PREVIEW_6_CURRENT_FOCUS_COMPLETE":
        raise ContractValidationError("ALGORITHM_VERSION_UNEXPECTED")
    if config["capabilities"]["HOT_RANKINGS"]["persist_payload"] or config["capabilities"]["HOT_RANKINGS"]["persist_rows"] or config["capabilities"]["HOT_RANKINGS"]["persist_batches"]:
        raise ContractValidationError("HOT_RANK_PERSISTENCE_FORBIDDEN")
    for name in (
        "Context", "ResearchContextReady", "ResearchContextNotBuilt", "OnlineContext",
        "Reason", "SectorCard", "MemberRow", "PageEnvelope",
    ):
        if name not in bundle["schema"].get("objects", {}):
            raise ContractValidationError(f"SCHEMA_OBJECT_MISSING:{name}")
    validate_fixture_bundle(bundle)
    return bundle
