"""P12-12 full CURRENT-track leave-one-out recomputation.

Unlike the earlier member-breadth LOO, this removes the target security from
the market reference and every overlapping sector before rebuilding the full
same-type cross section and P1 ranks.
"""
from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Iterable
from typing import Any

import pandas as pd

from workbench_analysis.sector_attention import build_sector_current


CONTRACT_ID = "TODAY_RESEARCH_FULL_CURRENT_LOO_V3_3_CANDIDATE_01"


class FullLooV33Error(RuntimeError):
    pass


def _tri_or(values: Iterable[bool | None]) -> bool | None:
    values = list(values)
    if any(value is True for value in values):
        return True
    return None if any(value is None for value in values) else False


def _hash(values: Iterable[str]) -> str:
    return hashlib.sha256(json.dumps(sorted(set(values)), separators=(",", ":")).encode()).hexdigest()


def _number(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _truth(value: Any) -> bool | None:
    if value is None or pd.isna(value):
        return None
    return bool(value)


def recompute_full_current_loo(
    targets: Iterable[str], members: pd.DataFrame, market_quotes: pd.DataFrame, config: dict[str, Any]
) -> dict[str, dict[str, Any]]:
    required_members = {"sector_id", "security_id", "trade_date", "ret1"}
    required_market = {"security_id", "trade_date", "ret1"}
    if missing := sorted(required_members.difference(members.columns)):
        raise FullLooV33Error("FULL_LOO_MEMBER_COLUMNS_MISSING:" + ",".join(missing))
    if missing := sorted(required_market.difference(market_quotes.columns)):
        raise FullLooV33Error("FULL_LOO_MARKET_COLUMNS_MISSING:" + ",".join(missing))
    source = members.copy()
    source["security_id"] = source["security_id"].astype(str)
    source["sector_id"] = source["sector_id"].astype(str)
    market = market_quotes.copy()
    market["security_id"] = market["security_id"].astype(str)
    if source.duplicated(["sector_id", "security_id", "trade_date"]).any():
        raise FullLooV33Error("FULL_LOO_DUPLICATE_MEMBER")
    if market.duplicated(["security_id", "trade_date"]).any():
        raise FullLooV33Error("FULL_LOO_DUPLICATE_MARKET_SECURITY")
    outputs: dict[str, dict[str, Any]] = {}
    for target in sorted(set(map(str, targets))):
        related = source.loc[source["security_id"].eq(target), ["sector_id", "sector_type"]].drop_duplicates()
        without_target = source.loc[~source["security_id"].eq(target)].copy()
        market_without_target = market.loc[~market["security_id"].eq(target)].copy()
        if market_without_target.empty:
            raise FullLooV33Error("FULL_LOO_MARKET_EMPTY_AFTER_EXCLUSION")
        recomputed = build_sector_current(without_target, market_without_target, config).set_index("sector_id")
        details = []
        for relation in related.sort_values(["sector_type", "sector_id"]).itertuples(index=False):
            if relation.sector_id not in recomputed.index:
                details.append({"sector_id": relation.sector_id, "sector_type": relation.sector_type, "full_track_current": None, "reason": "SECTOR_EMPTY_AFTER_EXCLUSION"})
                continue
            row = recomputed.loc[relation.sector_id]
            checks = row["checks"]["CURRENT"]
            details.append({
                "sector_id": relation.sector_id,
                "sector_type": relation.sector_type,
                "full_track_current": _truth(row["current"]),
                "member_count": int(row["total_member_count"]),
                "quote_valid_count": int(row["quote_valid_count"]),
                "market_quote_coverage": _number(row["market_quote_coverage"]),
                "market_m1": _number(row["market_m1"]),
                "m1": _number(row["m1"]), "b1": _number(row["b1"]),
                "rel1": _number(row["rel1"]), "p1": _number(row["p1"]),
                "positive_count": int(row["positive_count"]),
                "top1_positive_share": _number(row["top1_positive_share"]),
                "known_failed_checks": sorted(key for key, value in checks.items() if value is False),
                "unknown_checks": sorted(key for key, value in checks.items() if value is None),
                "reason": "FULL_TRACK_RECOMPUTED",
            })
        support = _tri_or(detail["full_track_current"] for detail in details) if details else False
        outputs[target] = {
            "contract_id": CONTRACT_ID,
            "support": support,
            "support_method": "FULL_CURRENT_TRACK_LOO_V1",
            "full_track_recomputed_without_target": True,
            "target_removed_from_market_reference": True,
            "target_removed_from_all_overlapping_sectors": True,
            "same_type_cross_section_and_p1_recomputed": True,
            "tested_relations": len(details),
            "supported_relations": sum(detail["full_track_current"] is True for detail in details),
            "unknown_relations": sum(detail["full_track_current"] is None for detail in details),
            "relationship_set_hash": _hash(detail["sector_id"] for detail in details),
            "relations": details,
        }
    return outputs


__all__ = ["CONTRACT_ID", "FullLooV33Error", "recompute_full_current_loo"]
