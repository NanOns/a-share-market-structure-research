"""Versioned semantic identity for accepted technical result rows."""
from __future__ import annotations

import json
from typing import Any, Mapping, Sequence

from workbench_analysis.technical import (TECHNICAL_RESULT_COLUMNS,
                                          TECHNICAL_RESULT_PRIMARY_KEY,
                                          TECHNICAL_RESULT_SCHEMA_VERSION,
                                          TECHNICAL_RESULT_SEMANTIC_CONTRACT)
from workbench_service.result_objects import result_value_hash


CONTRACT_ID = "TECHNICAL_RESULT_CANONICAL_IDENTITY_V2"
JSON_COLUMNS = ("quality_codes", "basis_json")


def _canonical_json(value: Any) -> str:
    parsed = json.loads(value) if isinstance(value, str) else value
    if not isinstance(parsed, (dict, list)):
        raise ValueError("technical JSON evidence must be object or array")
    return json.dumps(parsed, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False)


def canonical_technical_identity(records: Sequence[Mapping[str, Any]]) -> tuple[str, str, int]:
    """Hash the full object after parsing both text JSON and JSONB values."""
    normalized = []
    for record in records:
        row = {column: record[column] for column in TECHNICAL_RESULT_COLUMNS}
        for column in JSON_COLUMNS:
            row[column] = _canonical_json(row[column])
        normalized.append(row)
    semantics = {
        "identity_contract_id": CONTRACT_ID,
        "json_policy": "PARSE_THEN_SORTED_COMPACT_JSON",
        "null_policy": "EXPLICIT_NULLS_PRESERVED",
        "business_key": list(TECHNICAL_RESULT_PRIMARY_KEY),
        "contract_ids": sorted({str(row["contract_id"]) for row in normalized}),
        "price_bases": sorted({str(row["price_basis"]) for row in normalized}),
        "quality_field": "quality_codes",
        "basis_field": "basis_json",
    }
    return result_value_hash(
        domain="technical", schema_version=TECHNICAL_RESULT_SCHEMA_VERSION,
        semantic_contract=TECHNICAL_RESULT_SEMANTIC_CONTRACT,
        columns=TECHNICAL_RESULT_COLUMNS,
        primary_key=TECHNICAL_RESULT_PRIMARY_KEY,
        rows=normalized, value_semantics=semantics)
