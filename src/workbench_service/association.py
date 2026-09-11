"""M11-03 deterministic, explainable stock-to-sector associations."""

from __future__ import annotations

import math
from statistics import median
from typing import Any, Iterable, Mapping

from workbench_service.semantic import NORMAL_ATTRIBUTE, resolve_semantics


CONTRACT_ID = "STOCK_SECTOR_ASSOC_V1"
MIN_COVERAGE = 0.70
MIN_LEAVE_ONE_OUT = 5
MIN_BREADTH = 0.60
MIN_MEMBER_PERCENTILE = 0.80
ALLOWED_PATTERNS = {"CURRENT_STRENGTH", "REACCELERATION"}


def finite(value: object) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _percentile(values: Iterable[object], target: object) -> float | None:
    target_value = finite(target)
    values_float = sorted(value for value in (finite(item) for item in values) if value is not None)
    if target_value is None or not values_float:
        return None
    return sum(value <= target_value for value in values_float) / len(values_float)


def _pattern(sector: Mapping[str, object]) -> str:
    value = str(sector.get("primary_pattern") or sector.get("mainline_class") or "").strip().upper()
    return {"REACCELERATING": "REACCELERATION"}.get(value, value)


def _semantic_bucket(sector: Mapping[str, object]) -> str:
    resolved = resolve_semantics(
        {
            "sector_id": sector.get("sector_id"),
            "sector_name": sector.get("sector_name"),
            "sector_type": sector.get("sector_type"),
            "sector_role": sector.get("sector_role"),
            "sector_valid": sector.get("sector_valid", True),
            "semantic_bucket": sector.get("semantic_bucket", sector.get("bucket")),
        }
    )
    return str(resolved["bucket"])


def evaluate_relation(
    sector: Mapping[str, object],
    security_id: str,
    members: Iterable[Mapping[str, object]],
) -> dict[str, Any]:
    """Evaluate one membership and retain every failed gate as a reason code."""
    members_list = [dict(member) for member in members]
    bucket = _semantic_bucket(sector)
    pattern = _pattern(sector)
    reasons: list[str] = []
    if bucket != NORMAL_ATTRIBUTE:
        reasons.append("SEMANTIC_BUCKET_NOT_NORMAL_ATTRIBUTE")
    if str(sector.get("sector_role") or "").upper() == "EXCLUDE_FROM_THEME_RANK":
        reasons.append("SECTOR_ROLE_EXCLUDED")
    if sector.get("sector_valid") is not True:
        reasons.append("SECTOR_INVALID")
    coverage = finite(sector.get("coverage"))
    if coverage is None or coverage < MIN_COVERAGE:
        reasons.append("COVERAGE_BELOW_0_70_OR_UNKNOWN")
    if pattern not in ALLOWED_PATTERNS:
        reasons.append("PATTERN_NOT_CURRENT_STRENGTH_OR_REACCELERATION")

    target = next((member for member in members_list if str(member.get("security_id")) == str(security_id)), None)
    if target is None:
        reasons.append("TARGET_NOT_MEMBER")
    others = [member for member in members_list if str(member.get("security_id")) != str(security_id)]
    ret20 = [value for value in (finite(member.get("ret20", member.get("RET20"))) for member in others) if value is not None]
    ret5 = [value for value in (finite(member.get("ret5", member.get("RET5"))) for member in others) if value is not None]
    if len(ret20) < MIN_LEAVE_ONE_OUT:
        reasons.append("LEAVE_ONE_OUT_VALID_RET20_LT_5")
    loo_ret20 = median(ret20) if ret20 else None
    loo_breadth20 = sum(value > 0 for value in ret20) / len(ret20) if ret20 else None
    if loo_ret20 is None or loo_ret20 <= 0:
        reasons.append("LEAVE_ONE_OUT_RET20_MEDIAN_NOT_POSITIVE")
    if loo_breadth20 is None or loo_breadth20 < MIN_BREADTH:
        reasons.append("LEAVE_ONE_OUT_BREADTH20_LT_0_60")

    loo_ret5 = median(ret5) if ret5 else None
    loo_breadth5 = sum(value > 0 for value in ret5) / len(ret5) if ret5 else None
    if pattern == "REACCELERATION":
        if len(ret5) < MIN_LEAVE_ONE_OUT:
            reasons.append("REACCELERATION_VALID_RET5_LT_5")
        if loo_ret5 is None or loo_ret5 <= 0:
            reasons.append("REACCELERATION_LEAVE_ONE_OUT_RET5_MEDIAN_NOT_POSITIVE")
        if loo_breadth5 is None or loo_breadth5 < MIN_BREADTH:
            reasons.append("REACCELERATION_LEAVE_ONE_OUT_BREADTH5_LT_0_60")

    target_ret20 = target.get("ret20", target.get("RET20")) if target else None
    member_percentile = _percentile(
        [member.get("ret20", member.get("RET20")) for member in members_list], target_ret20
    )
    if member_percentile is None or member_percentile < MIN_MEMBER_PERCENTILE:
        reasons.append("TARGET_MEMBER_PERCENTILE_LT_0_80_OR_UNKNOWN")

    return {
        "security_id": str(security_id),
        "sector_id": str(sector.get("sector_id") or ""),
        "sector_name": str(sector.get("sector_name") or sector.get("sector_id") or ""),
        "sector_type": str(sector.get("sector_type") or "").upper(),
        "semantic_bucket": bucket,
        "pattern": pattern or None,
        "eligible": not reasons,
        "rejection_reasons": reasons,
        "member_rank": finite(target.get("member_rank")) if target else None,
        "member_rank_valid_count": int(target.get("rank_valid_count") or 0) if target else 0,
        "member_percentile": member_percentile,
        "sector_coverage": coverage,
        "sector_rs5_pct": finite(sector.get("sector_rs5_pct")),
        "sector_rs20_pct": finite(sector.get("sector_rs20_pct")),
        "loo_ret20_median": loo_ret20,
        "loo_breadth20": loo_breadth20,
        "loo_ret5_median": loo_ret5,
        "loo_breadth5": loo_breadth5,
        "evidence": {
            "contract_id": CONTRACT_ID,
            "thresholds": {
                "coverage_min": MIN_COVERAGE,
                "leave_one_out_min_valid_ret20": MIN_LEAVE_ONE_OUT,
                "breadth_min": MIN_BREADTH,
                "member_percentile_min": MIN_MEMBER_PERCENTILE,
            },
            "pattern": pattern or None,
            "rejection_reasons": reasons,
        },
    }


def association_sort_key(row: Mapping[str, object]) -> tuple[object, ...]:
    def descending(value: object) -> float:
        number = finite(value)
        return -number if number is not None else float("inf")

    return (
        0 if row.get("pattern") == "REACCELERATION" else 1,
        descending(row.get("sector_rs5_pct")),
        descending(row.get("sector_rs20_pct")),
        descending(row.get("loo_breadth20")),
        descending(row.get("member_percentile")),
        descending(row.get("sector_coverage")),
        str(row.get("sector_id") or ""),
    )


def rank_associations(rows: Iterable[Mapping[str, object]]) -> list[dict[str, Any]]:
    """Rank eligible rows per stock; rejected rows retain null rank."""
    grouped: dict[str, list[dict[str, Any]]] = {}
    result = [dict(row) for row in rows]
    for row in result:
        if row.get("eligible"):
            grouped.setdefault(str(row.get("security_id")), []).append(row)
    for security_id, eligible in grouped.items():
        for rank, row in enumerate(sorted(eligible, key=association_sort_key)[:3], start=1):
            row["association_rank"] = rank
    for row in result:
        row.setdefault("association_rank", None)
    return result
