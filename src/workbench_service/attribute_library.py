"""Read-only M11-01 sector attribute library response helpers."""

from __future__ import annotations

import json
from typing import Any, Mapping

from workbench_service.semantic import CONTRACT_ID as SEMANTIC_CONTRACT_ID, resolve_semantics


CONTRACT_ID = "M11_ATTRIBUTE_LIBRARY_V1_0"
BUCKET_LABELS = {
    "NORMAL_ATTRIBUTE": "正常属性",
    "PRICE_BEHAVIOR_TAG": "价格行为标签",
    "EVENT_TAG": "事件标签",
    "STATUS_TAG": "状态标签",
    "UNKNOWN_TAG": "未解析标签",
}


def _json_object(value: object) -> dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)
    if not value:
        return {}
    try:
        parsed = json.loads(str(value))
    except (TypeError, json.JSONDecodeError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _int_or_zero(value: object) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def build_source_metadata(*, snapshot_id: str, as_of_trade_date: object, base_slice: Mapping[str, object], member_slice: Mapping[str, object]) -> dict[str, Any]:
    """Build the stable source block shared by API23 and API27."""
    base_basis = _json_object(base_slice.get("basis_json"))
    member_basis = _json_object(member_slice.get("basis_json"))
    return {
        "source_kind": "M7A_SEMANTIC_SNAPSHOT",
        "snapshot_id": snapshot_id,
        "as_of_trade_date": str(as_of_trade_date),
        "semantic_contract_id": SEMANTIC_CONTRACT_ID,
        "sector_base_slice_id": base_slice.get("slice_id"),
        "sector_base_contract_id": base_slice.get("contract_id"),
        "sector_base_input_hash": base_slice.get("input_hash"),
        "sector_base_logical_hash": base_slice.get("logical_hash"),
        "member_state_slice_id": member_slice.get("slice_id"),
        "member_state_contract_id": member_slice.get("contract_id"),
        "member_state_input_hash": member_slice.get("input_hash"),
        "member_state_logical_hash": member_slice.get("logical_hash"),
        "membership_snapshot_id": base_basis.get("membership_snapshot_id") or member_basis.get("membership_snapshot_id"),
        "history_basis": base_basis.get("history_basis") or member_basis.get("history_basis") or "UNKNOWN",
        "source": base_basis.get("source") or member_basis.get("source") or "LOCAL_DUCKDB_ANALYSIS_SLICES",
    }


def sector_attribute_item(row: Mapping[str, object], source: Mapping[str, object]) -> dict[str, Any]:
    """Convert one sector-base row to the M11 attribute DTO."""
    semantic = resolve_semantics({
        "sector_id": row.get("sector_id"),
        "sector_name": row.get("sector_name"),
        "sector_type": row.get("sector_type"),
        "sector_role": row.get("sector_role"),
        "sector_valid": row.get("sector_valid"),
        "semantic_bucket": row.get("bucket"),
    })
    total = _int_or_zero(row.get("total_member_count"))
    valid = _int_or_zero(row.get("factor_valid_count"))
    return {
        "sector_id": str(row.get("sector_id") or ""),
        "sector_name": str(row.get("sector_name") or row.get("sector_id") or ""),
        "sector_type": str(row.get("sector_type") or "").upper(),
        "sector_role": row.get("sector_role"),
        "semantic_bucket": semantic["bucket"],
        "semantic_bucket_label": BUCKET_LABELS[semantic["bucket"]],
        "is_attribute": bool(semantic["is_attribute"]),
        "is_market_tag": bool(semantic["is_market_tag"]),
        "normal_rank_eligible": bool(semantic["normal_rank_eligible"]),
        "total_member_count": total,
        "valid_count": valid,
        "factor_valid_count": valid,
        "quote_valid_count": _int_or_zero(row.get("quote_valid_count")),
        "coverage": row.get("coverage"),
        "sector_valid": bool(row.get("sector_valid")),
        "semantic_version": semantic["semantic_version"],
        "semantic_rule_id": semantic["rule_id"],
        "semantic_reason": semantic["reason"],
        "keyword_hint": semantic["keyword_hint"],
        "semantic_override": bool(semantic["override"]),
        "source": dict(source),
    }


def membership_item(row: Mapping[str, object], sector: Mapping[str, object], source: Mapping[str, object]) -> dict[str, Any]:
    """Build one stock-to-sector membership DTO without association fields."""
    return {
        "sector_id": sector["sector_id"],
        "sector_name": sector["sector_name"],
        "sector_type": sector["sector_type"],
        "semantic_bucket": sector["semantic_bucket"],
        "semantic_bucket_label": sector["semantic_bucket_label"],
        "is_attribute": sector["is_attribute"],
        "is_market_tag": sector["is_market_tag"],
        "normal_rank_eligible": sector["normal_rank_eligible"],
        "total_member_count": sector["total_member_count"],
        "valid_count": sector["valid_count"],
        "coverage": sector["coverage"],
        "sector_valid": sector["sector_valid"],
        "member_present": bool(row.get("member_present")),
        "member_rank": row.get("member_rank"),
        "rank_valid_count": _int_or_zero(row.get("rank_valid_count")),
        "membership_basis": source.get("history_basis"),
        "source": dict(source),
    }
