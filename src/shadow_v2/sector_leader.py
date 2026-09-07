from __future__ import annotations

import math

RULESET_ID = "sector-leader-v2-shadow-v1.1-quality-coverage"
PRICE_BEHAVIOR_STYLE_IS_NOT_INDEPENDENT_SECTOR_EVIDENCE = True


def quality_class(value, valid_count, valid_ratio, min_count=5, min_ratio=0.70):
    if (not _finite(value) or not _finite(valid_count) or not _finite(valid_ratio)
            or int(valid_count) < min_count or float(valid_ratio) < min_ratio):
        return "QUALITY_DATA_INSUFFICIENT"
    if float(value) >= 0.75:
        return "STRONG_SUPPORT"
    if float(value) >= 0.50:
        return "MODERATE_SUPPORT"
    return "WEAK_SUPPORT"


def support_counts(classes):
    return sum(x == "STRONG_SUPPORT" for x in classes), sum(x in ("STRONG_SUPPORT", "MODERATE_SUPPORT") for x in classes)


def semantic_category(sector_type, style_class=None):
    if sector_type in ("INDUSTRY", "THEME"):
        return "ECONOMIC_SECTOR"
    if sector_type != "STYLE":
        return "UNKNOWN_STYLE"
    if style_class == "PRICE_BEHAVIOR":
        return "PRICE_BEHAVIOR_STYLE"
    if style_class in ("EVENT", "STATUS", "OTHER"):
        return "NON_PRICE_STYLE"
    return "UNKNOWN_STYLE"


def primary_sort_key(relation):
    semantic_order = {"ECONOMIC_SECTOR": 0, "NON_PRICE_STYLE": 1, "UNKNOWN_STYLE": 2, "PRICE_BEHAVIOR_STYLE": 3}
    return (0 if relation.get("quality_evidence_sufficient") else 1,
            semantic_order[relation["sector_semantic"]], 0 if relation["reacceleration"] else 1,
            -float(relation["sector_rs20_pct"]), -float(relation["member_rs20_pct"]), relation["sector_id"])


def choose_primary(relations):
    return min(relations, key=primary_sort_key) if relations else None


def classify(v1_sector_leader, semantic, quality_classes):
    if not bool(v1_sector_leader):
        return "OUTSIDE_V1_SECTOR_LEADER", False
    if semantic in (None, "UNKNOWN_STYLE") or any(x == "QUALITY_DATA_INSUFFICIENT" for x in quality_classes):
        return "DATA_INSUFFICIENT", False
    if semantic == "PRICE_BEHAVIOR_STYLE":
        return "STYLE_SELF_REINFORCED", False
    strong, nonweak = support_counts(quality_classes)
    if strong >= 2 and nonweak >= 3:
        return "LEADER_CORE", True
    if strong >= 1 and nonweak >= 2:
        return "LEADER_SUPPORTED", True
    return "RETURN_LEADER_ONLY", False


def _finite(value):
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError):
        return False
