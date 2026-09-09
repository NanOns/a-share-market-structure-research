"""Historical daily coverage and market aggregation inputs (M8B-03)."""

from __future__ import annotations

import json
from typing import Any, Iterable

import numpy as np
import pandas as pd

from .structures import QUEUE_NAMES, STRUCTURE_BASIS


CONTRACT_VERSION = "HISTORICAL_COVERAGE_V2_1_RECONSTRUCTED"


class CoverageAdapterError(ValueError):
    pass


def _dates(frame: pd.DataFrame, name: str = "trade_date") -> pd.Series:
    if name not in frame.columns:
        raise CoverageAdapterError(f"COVERAGE_INPUT_COLUMNS_MISSING:{name}")
    return pd.to_datetime(frame[name], errors="raise").dt.date


def _finite(series: pd.Series) -> pd.Series:
    values = pd.to_numeric(series, errors="coerce")
    return values.notna() & np.isfinite(values)


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def _queue_counts(structures: pd.DataFrame) -> tuple[dict[str, int], int, int, int]:
    counts = {queue: 0 for queue in QUEUE_NAMES}
    if structures.empty:
        return counts, 0, 0, 0
    hits = structures[structures["hit"].eq(True)]
    for queue, count in hits["queue_name"].value_counts().items():
        if queue in counts:
            counts[queue] = int(count)
    unknown = int(structures["hit"].isna().sum())
    known = int(structures["hit"].notna().sum())
    unique = int(hits["security_id"].nunique())
    return counts, unknown, known, unique


def build_historical_coverage(
    technical: pd.DataFrame,
    memberships: pd.DataFrame,
    structures: pd.DataFrame,
    *,
    cutoff: Any,
    price_basis: str = "TDX_NATIVE_QFQ",
    history_basis: str = STRUCTURE_BASIS,
    expected_security_ids: Iterable[str] | None = None,
    observed_membership_dates: Iterable[Any] | None = None,
) -> pd.DataFrame:
    """Build one auditable coverage row per input date.

    Absence of structure rows is reported as NOT_BUILT; a present row with no
    hits is AVAILABLE with zero hits.  No metric is backfilled across dates.
    """
    if history_basis != STRUCTURE_BASIS:
        raise CoverageAdapterError("COVERAGE_REQUIRES_RECONSTRUCTED_BASIS")
    if price_basis not in {"RAW", "TDX_NATIVE_QFQ"}:
        raise CoverageAdapterError("PRICE_BASIS_UNSUPPORTED")
    frames = {"technical": technical.copy(), "memberships": memberships.copy(), "structures": structures.copy()}
    for name, frame in frames.items():
        frame["trade_date"] = _dates(frame)
        if "security_id" not in frame.columns:
            raise CoverageAdapterError(f"{name.upper()}_INPUT_COLUMNS_MISSING:security_id")
    cutoff_date = pd.Timestamp(cutoff).date()
    if any((frame["trade_date"] > cutoff_date).any() for frame in frames.values()):
        raise CoverageAdapterError("COVERAGE_INPUT_AFTER_CUTOFF")
    if frames["technical"][["security_id", "trade_date"]].duplicated().any():
        raise CoverageAdapterError("COVERAGE_TECHNICAL_DUPLICATE_SECURITY_DATE")
    if frames["structures"][["security_id", "trade_date", "queue_name"]].duplicated().any():
        raise CoverageAdapterError("COVERAGE_STRUCTURE_DUPLICATE_KEY")
    expected = set(str(value) for value in expected_security_ids) if expected_security_ids is not None else set(frames["technical"]["security_id"].astype(str))
    observed = {pd.Timestamp(value).date() for value in (observed_membership_dates or ())}
    input_dates = sorted(set().union(*(set(frame["trade_date"]) for frame in frames.values())))
    rows: list[dict[str, Any]] = []
    for trade_date in input_dates:
        tech = frames["technical"].loc[frames["technical"]["trade_date"].eq(trade_date)]
        members = frames["memberships"].loc[frames["memberships"]["trade_date"].eq(trade_date)]
        structure = frames["structures"].loc[frames["structures"]["trade_date"].eq(trade_date)]
        price = _finite(tech["raw_close" if price_basis == "RAW" and "raw_close" in tech else "adj_close" if "adj_close" in tech else "raw_close"])
        quote_valid = int(price.sum())
        factor_valid = int(tech["validity"].eq("VALID").sum()) if "validity" in tech.columns else int(_finite(tech["ret20"]).sum()) if "ret20" in tech.columns else 0
        member_ids = set(members["security_id"].dropna().astype(str))
        member_snapshot = None
        if "membership_snapshot_id" in members and members["membership_snapshot_id"].notna().any():
            member_snapshot = str(members["membership_snapshot_id"].dropna().iloc[0])
        counts, unknown, known, unique_hits = _queue_counts(structure)
        quality: list[str] = []
        if expected_security_ids is None:
            quality.append("EXPECTED_UNIVERSE_NOT_SUPPLIED")
        if not len(members):
            quality.append("MEMBERSHIP_UNAVAILABLE")
        if not len(structure):
            quality.append("STRUCTURE_NOT_BUILT")
        if len(structure) and unknown:
            quality.append("STRUCTURE_UNKNOWN_PRESENT")
        rows.append({
            "trade_date": trade_date,
            "contract_id": CONTRACT_VERSION,
            "history_basis": history_basis,
            "real_observation": False,
            "observation_compatible": False,
            "membership_basis": history_basis,
            "membership_observation_class": "AS_OBSERVED" if trade_date in observed else "RECONSTRUCTED",
            "membership_snapshot_id": member_snapshot,
            "price_basis": price_basis,
            "expected_security_count": len(expected),
            "technical_row_count": int(len(tech)),
            "quote_valid_count": quote_valid,
            "quote_coverage": quote_valid / len(expected) if expected else None,
            "factor_valid_count": factor_valid,
            "factor_coverage": factor_valid / len(expected) if expected else None,
            "member_count": len(member_ids),
            "member_sector_count": int(members["sector_id"].nunique()) if "sector_id" in members.columns else 0,
            "membership_capability": "AVAILABLE" if len(members) else "UNAVAILABLE",
            "structure_capability": "AVAILABLE" if len(structure) else "NOT_BUILT",
            "structure_known_row_count": known,
            "structure_unknown_row_count": unknown,
            "structure_unique_hit_security_count": unique_hits,
            "queue_hit_counts_json": _json(counts),
            "quality_codes": _json(sorted(set(quality))),
        })
    return pd.DataFrame(rows).sort_values("trade_date", kind="mergesort").reset_index(drop=True) if rows else pd.DataFrame()


def coverage_summary(frame: pd.DataFrame) -> dict[str, Any]:
    """Return a compact summary suitable for a verification receipt."""
    if frame.empty:
        return {"contract_id": CONTRACT_VERSION, "date_count": 0, "history_basis": STRUCTURE_BASIS}
    return {
        "contract_id": CONTRACT_VERSION,
        "date_count": int(len(frame)),
        "start_date": str(frame["trade_date"].min()),
        "end_date": str(frame["trade_date"].max()),
        "history_basis": str(frame["history_basis"].iloc[0]),
        "real_observation": bool(frame["real_observation"].any()),
        "structure_not_built_dates": int(frame["structure_capability"].eq("NOT_BUILT").sum()),
        "membership_unavailable_dates": int(frame["membership_capability"].eq("UNAVAILABLE").sum()),
    }
