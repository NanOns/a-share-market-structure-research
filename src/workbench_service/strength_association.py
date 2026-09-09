"""Explainable stock-to-sector strength association for the read-only workbench.

Contract: ``stock-strength-sector-association-v1.0``.
This is descriptive co-strength evidence, not a causal or probability claim.
"""
from __future__ import annotations

import math
from statistics import median


CONTRACT_VERSION = "stock-strength-sector-association-v1.0"
PRICE_WORDS = ("强势", "弱势", "涨停", "跌停", "首板", "连板", "多板", "断板", "新高", "新低", "异动", "上榜", "振荡", "换手", "活跃", "情绪", "融资")
EVENT_WORDS = ("重组", "增持", "减持", "回购", "解禁", "复牌", "要约", "转让", "调研", "上市")
STATUS_WORDS = ("亏损", "绩优", "微利", "风险提示", "高负债", "高商誉", "高质押")
EXCLUDED_ROLES = {"EXCLUDE_FROM_THEME_RANK"}


def _finite(value):
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError):
        return False


def semantic_bucket(sector):
    """Separate stable memberships from circular price/event/status labels."""
    name = str(sector.get("sector_name") or "")
    if any(word in name for word in PRICE_WORDS):
        return "PRICE_BEHAVIOR_TAG"
    if any(word in name for word in EVENT_WORDS):
        return "EVENT_TAG"
    if any(word in name for word in STATUS_WORDS):
        return "STATUS_TAG"
    if sector.get("sector_type") in {"INDUSTRY", "THEME", "STYLE"}:
        return "NORMAL_ATTRIBUTE"
    return "UNKNOWN_TAG"


def _percentile(values, target):
    finite = sorted(float(value) for value in values if _finite(value))
    if not finite or not _finite(target):
        return None
    less_or_equal = sum(value <= float(target) for value in finite)
    return less_or_equal / len(finite)


def evaluate_relation(sector, security_id, members):
    """Evaluate one membership with a leave-one-stock-out independence guard."""
    bucket = semantic_bucket(sector)
    if bucket != "NORMAL_ATTRIBUTE":
        return {"eligible": False, "bucket": bucket, "sector_name": sector.get("sector_name")}
    if sector.get("sector_role") in EXCLUDED_ROLES or not bool(sector.get("sector_valid", True)):
        return {"eligible": False, "bucket": bucket, "sector_name": sector.get("sector_name")}
    if not _finite(sector.get("coverage")) or float(sector["coverage"]) < 0.70:
        return {"eligible": False, "bucket": bucket, "sector_name": sector.get("sector_name")}
    pattern = str(sector.get("primary_pattern") or "")
    if pattern not in {"CURRENT_STRENGTH", "REACCELERATION"}:
        return {"eligible": False, "bucket": bucket, "sector_name": sector.get("sector_name")}

    target = next((row for row in members if row.get("security_id") == security_id), None)
    others = [row for row in members if row.get("security_id") != security_id]
    ret20 = [float(row["RET20"]) for row in others if _finite(row.get("RET20"))]
    ret5 = [float(row["RET5"]) for row in others if _finite(row.get("RET5"))]
    if target is None or len(ret20) < 5:
        return {"eligible": False, "bucket": bucket, "sector_name": sector.get("sector_name")}
    loo_ret20 = median(ret20)
    loo_breadth20 = sum(value > 0 for value in ret20) / len(ret20)
    loo_ret5 = median(ret5) if len(ret5) >= 5 else None
    loo_breadth5 = sum(value > 0 for value in ret5) / len(ret5) if len(ret5) >= 5 else None
    independent = loo_ret20 > 0 and loo_breadth20 >= 0.60
    if pattern == "REACCELERATION":
        independent = independent and loo_ret5 is not None and loo_ret5 > 0 and loo_breadth5 >= 0.60
    member_pct = _percentile([row.get("RET20") for row in members], target.get("RET20"))
    eligible = bool(independent and member_pct is not None and member_pct >= 0.80)
    reason = (
        f"剔除该股后：20日涨幅中位数{loo_ret20:.1%}，上涨成员占比{loo_breadth20:.1%}；"
        f"该股板块内20日强度前{max(1, round((1-member_pct)*100))}%"
    )
    return {
        "eligible": eligible,
        "bucket": bucket,
        "sector_id": sector.get("sector_id"),
        "sector_name": sector.get("sector_name"),
        "sector_type": sector.get("sector_type"),
        "pattern": pattern,
        "member_percentile": member_pct,
        "loo_ret20_median": loo_ret20,
        "loo_breadth20": loo_breadth20,
        "loo_ret5_median": loo_ret5,
        "loo_breadth5": loo_breadth5,
        "reason": reason,
        "sort_key": (
            0 if pattern == "REACCELERATION" else 1,
            -float(sector.get("sector_rs5_pct")) if _finite(sector.get("sector_rs5_pct")) else 0,
            -float(sector.get("sector_rs20_pct")) if _finite(sector.get("sector_rs20_pct")) else 0,
            -loo_breadth20,
            -member_pct,
            -float(sector.get("coverage")),
            str(sector.get("sector_id") or ""),
        ),
    }


def choose_association(security_id, relations):
    evaluated = [evaluate_relation(sector, security_id, members) for sector, members in relations]
    eligible = sorted((row for row in evaluated if row.get("eligible")), key=lambda row: row["sort_key"])
    tags = sorted({str(row.get("sector_name")) for row in evaluated if row.get("bucket") != "NORMAL_ATTRIBUTE" and row.get("sector_name")})
    if not eligible:
        return {
            "strength_sector_name": None,
            "strength_sector_type": None,
            "strength_sector_reason": "暂无可确认的强势关联板块",
            "other_strength_sectors": [],
            "market_tags": tags,
            "strength_association_contract": CONTRACT_VERSION,
        }
    primary = eligible[0]
    return {
        "strength_sector_name": primary["sector_name"],
        "strength_sector_type": primary["sector_type"],
        "strength_sector_reason": primary["reason"],
        "other_strength_sectors": [row["sector_name"] for row in eligible[1:3]],
        "market_tags": tags,
        "strength_association_contract": CONTRACT_VERSION,
    }
