"""Independent historical adapter for technical -> sector-base -> scanner flow.

This module deliberately does not call a formal daily publisher.  It accepts
date-aligned historical inputs, calculates only deterministic derived frames,
and leaves publication/activation to the existing snapshot services.
"""

from __future__ import annotations

import hashlib
from typing import Any, Iterable

import numpy as np
import pandas as pd

from scanner.sector_scanner import add_percentiles, scan as scan_sectors
from sector.roles import sector_role


CONTRACT_VERSION = "HISTORICAL_SECTOR_ADAPTER_V1_0"
HISTORY_BASIS = "RECONSTRUCTED"
CURRENT_MEMBERSHIP_BASIS = "CURRENT_TDX_MEMBERSHIP"
WINDOWS = (5, 10, 20, 60)


class HistoryAdapterError(ValueError):
    """Raised when historical inputs cannot be aligned without fabrication."""


def _date_series(frame: pd.DataFrame, name: str) -> pd.Series:
    if name not in frame.columns:
        raise HistoryAdapterError(f"HISTORY_INPUT_COLUMNS_MISSING:{name}")
    return pd.to_datetime(frame[name], errors="raise").dt.date


def _first_column(frame: pd.DataFrame, names: Iterable[str]) -> str | None:
    return next((name for name in names if name in frame.columns), None)


def _numeric(frame: pd.DataFrame, names: Iterable[str]) -> pd.Series:
    name = _first_column(frame, names)
    if name is None:
        return pd.Series(np.nan, index=frame.index, dtype="float64")
    return pd.to_numeric(frame[name], errors="coerce")


def _finite(series: pd.Series) -> pd.Series:
    values = pd.to_numeric(series, errors="coerce")
    return values.notna() & np.isfinite(values)


def _normal_security_mask(frame: pd.DataFrame) -> pd.Series:
    if "universe_status" in frame.columns:
        return frame["universe_status"].eq("IN_NORMAL_UNIVERSE")
    if "display_eligible" in frame.columns:
        return frame["display_eligible"].eq(True)
    return pd.Series(True, index=frame.index)


def _stable_membership_id(memberships: pd.DataFrame) -> str:
    keys = memberships[["trade_date", "sector_id", "security_id"]].astype(str).sort_values(
        ["trade_date", "sector_id", "security_id"], kind="mergesort"
    )
    payload = "\n".join("|".join(row) for row in keys.itertuples(index=False, name=None))
    return "reconstructed-membership-" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:24]


def guard_history_inputs(
    technical: pd.DataFrame,
    memberships: pd.DataFrame,
    cutoff: Any,
    *,
    membership_basis: str = HISTORY_BASIS,
) -> tuple[pd.DataFrame, pd.DataFrame, Any]:
    """Validate dates and prevent current-membership historical backfill."""
    cutoff_date = pd.Timestamp(cutoff).date()
    if membership_basis not in {HISTORY_BASIS, "OBSERVED", CURRENT_MEMBERSHIP_BASIS}:
        raise HistoryAdapterError("MEMBERSHIP_BASIS_UNSUPPORTED")
    stocks = technical.copy()
    members = memberships.copy()
    stocks["trade_date"] = _date_series(stocks, "date" if "date" in stocks.columns else "trade_date")
    members["trade_date"] = _date_series(members, "trade_date")
    if "security_id" not in stocks.columns or "security_id" not in members.columns:
        raise HistoryAdapterError("HISTORY_INPUT_COLUMNS_MISSING:security_id")
    if "sector_id" not in members.columns:
        if {"sector_type", "sector_code"} <= set(members.columns):
            members["sector_id"] = members["sector_type"].astype(str).str.upper() + ":" + members["sector_code"].astype(str)
        else:
            raise HistoryAdapterError("HISTORY_INPUT_COLUMNS_MISSING:sector_id")
    if stocks[["security_id", "trade_date"]].duplicated().any():
        raise HistoryAdapterError("TECHNICAL_DUPLICATE_SECURITY_DATE")
    members = members.drop_duplicates(["trade_date", "sector_id", "security_id"], keep="last")
    if (stocks["trade_date"] > cutoff_date).any() or (members["trade_date"] > cutoff_date).any():
        raise HistoryAdapterError("HISTORY_INPUT_AFTER_CUTOFF")
    if membership_basis == CURRENT_MEMBERSHIP_BASIS and (members["trade_date"] < cutoff_date).any():
        raise HistoryAdapterError("CURRENT_SNAPSHOT_ONLY_NO_HISTORY_OR_FUTURE")
    stock_dates = set(stocks["trade_date"])
    member_dates = set(members["trade_date"])
    missing = sorted(stock_dates - member_dates)
    if missing:
        raise HistoryAdapterError("MEMBERSHIP_DATE_MISSING:" + ",".join(str(value) for value in missing))
    if membership_basis == HISTORY_BASIS and not member_dates:
        raise HistoryAdapterError("MEMBERSHIP_DATE_MISSING")
    return stocks.sort_values(["trade_date", "security_id"], kind="mergesort").reset_index(drop=True), members.sort_values(
        ["trade_date", "sector_id", "security_id"], kind="mergesort"
    ).reset_index(drop=True), cutoff_date


def add_cross_sectional_rs(technical: pd.DataFrame) -> pd.DataFrame:
    """Add date-local RS and average-tie RPS without changing return columns."""
    required = {"security_id", "trade_date"}
    missing = sorted(required.difference(technical.columns))
    if missing:
        raise HistoryAdapterError("TECHNICAL_INPUT_COLUMNS_MISSING:" + ",".join(missing))
    result = technical.copy()
    normal = _normal_security_mask(result)
    for width in WINDOWS:
        returns = _numeric(result, (f"ret{width}", f"RET{width}"))
        valid = normal & _finite(returns)
        market = returns.where(valid).groupby(result["trade_date"]).transform("median")
        result[f"market_ret{width}_median"] = market
        result[f"rs{width}"] = (returns - market).where(valid & _finite(market))
        counts = valid.groupby(result["trade_date"]).transform("sum").astype("Int64")
        result[f"rps{width}_valid_n"] = counts
        ranks = returns.where(valid).groupby(result["trade_date"]).rank(method="average", pct=True)
        result[f"rps{width}"] = ranks.where(counts >= 100)
        result[f"RET{width}"] = returns
    return result.sort_values(["trade_date", "security_id"], kind="mergesort").reset_index(drop=True)


def _sector_type(row: pd.Series) -> str:
    value = str(row.get("sector_type", "")).lower()
    return {"industry": "INDUSTRY", "concept": "THEME", "style": "STYLE"}.get(value, str(row.get("sector_type", "STRUCTURAL_TAG")).upper())


def _aggregate(values: pd.Series, operation: str = "median") -> tuple[float | None, int]:
    finite = pd.to_numeric(values, errors="coerce")
    finite = finite[_finite(finite)]
    if finite.empty:
        return None, 0
    return float(getattr(finite, operation)()), int(finite.size)


def build_sector_base(
    technical: pd.DataFrame,
    memberships: pd.DataFrame,
    *,
    membership_basis: str = HISTORY_BASIS,
    membership_snapshot_id: str | None = None,
    semantic_version: str | None = None,
) -> pd.DataFrame:
    """Aggregate date-aligned stock factors into scanner-compatible sector rows."""
    if "trade_date" not in technical.columns or "trade_date" not in memberships.columns:
        raise HistoryAdapterError("HISTORY_DATE_ALIGNMENT_REQUIRED")
    members = memberships.copy()
    members["sector_id"] = members["sector_id"].astype(str)
    joined = members.merge(technical, on=["trade_date", "security_id"], how="left", validate="many_to_one", suffixes=("", "_technical"))
    rows: list[dict[str, Any]] = []
    snapshot_id = membership_snapshot_id or (str(members["membership_snapshot_id"].dropna().iloc[0]) if "membership_snapshot_id" in members and members["membership_snapshot_id"].notna().any() else _stable_membership_id(members))
    for (trade_date, sector_id), group in joined.groupby(["trade_date", "sector_id"], sort=True):
        ids = sorted(set(group["security_id"].dropna().astype(str)))
        meta = group.iloc[0]
        stype = _sector_type(meta)
        name = str(meta.get("sector_name", sector_id))
        role = sector_role(stype.lower(), name)
        total = len(ids)
        ret20 = _numeric(group, ("ret20", "RET20"))
        valid_member = _normal_security_mask(group) & _finite(ret20)
        valid_count = int(valid_member.sum())
        coverage = valid_count / total if total else 0.0
        minimum_total = 5 if role == "INDUSTRY" else 8
        sector_valid = role != "EXCLUDE_FROM_THEME_RANK" and total >= minimum_total and valid_count >= 5 and coverage >= 0.70
        row: dict[str, Any] = {
            "trade_date": trade_date,
            "sector_id": sector_id,
            "sector_name": name,
            "sector_type": stype,
            "sector_role": role,
            "membership_basis": membership_basis,
            "pit_membership": False,
            "historical_backtest_safe": False,
            "membership_snapshot_id": snapshot_id,
            "semantic_version": semantic_version or str(meta.get("semantic_version") or "UNAVAILABLE"),
            "total_member_count": total,
            "valid_member_count": valid_count,
            "invalid_member_count": total - valid_count,
            "quote_valid_count": int((_finite(_numeric(group, ("raw_close", "adj_close"))) & _normal_security_mask(group)).sum()),
            "factor_valid_count": valid_count,
            "coverage": coverage,
            "sector_valid": sector_valid,
            "invalid_reason": "" if sector_valid else "|".join(filter(None, ["MIN_TOTAL_MEMBERS" if total < minimum_total else "", "MIN_VALID_MEMBERS" if valid_count < 5 else "", "LOW_COVERAGE" if coverage < 0.70 else "", "EXCLUDED_ROLE" if role == "EXCLUDE_FROM_THEME_RANK" else ""])),
            "sector_factor_version": CONTRACT_VERSION,
            "quality_flag": "OK" if sector_valid else "DATA_INSUFFICIENT",
            "base_pattern": "NONE",
            "base_predicates": {},
        }
        for width in WINDOWS:
            ret = _numeric(group, (f"ret{width}", f"RET{width}"))
            rs = _numeric(group, (f"rs{width}", f"RS{width}"))
            value, count = _aggregate(ret.where(valid_member))
            row[f"sector_ret{width}_median"] = value
            row[f"sector_ret{width}_median__valid_count"] = count
            row[f"sector_ret{width}_median__valid_ratio"] = count / total if total else 0.0
            value, count = _aggregate(rs.where(valid_member))
            row[f"sector_rs{width}"] = value
            row[f"sector_rs{width}__valid_count"] = count
            row[f"sector_rs{width}__valid_ratio"] = count / total if total else 0.0
        ret5 = _numeric(group, ("ret5", "RET5"))
        ret20 = _numeric(group, ("ret20", "RET20"))
        row["sector_breadth_ret5_pos"] = float((ret5[valid_member] > 0).mean()) if valid_member.any() else None
        row["sector_breadth_ret20_pos"] = float((ret20[valid_member] > 0).mean()) if valid_member.any() else None
        row["sector_breadth_ret60_pos"] = None
        common = valid_member & _finite(ret5) & _finite(ret20)
        row["breadth_5_20_common_valid_count"] = int(common.sum())
        row["breadth_5_20_common_valid_ratio"] = float(common.sum() / total) if total else 0.0
        row["breadth_ret5_pos_common"] = float((ret5[common] > 0).mean()) if common.any() else None
        row["breadth_ret20_pos_common"] = float((ret20[common] > 0).mean()) if common.any() else None
        row["breadth_5_minus_20_common"] = (row["breadth_ret5_pos_common"] - row["breadth_ret20_pos_common"]) if common.any() else None
        row["sector_pos60_median"], _ = _aggregate(_numeric(group, ("pos60", "POS60")).where(valid_member))
        row["sector_mdd20_median"], _ = _aggregate(_numeric(group, ("mdd20", "MDD20")).where(valid_member))
        amount = _numeric(group, ("amount_ratio_5_20", "amount_ratio_5_20_member"))
        row["sector_amount_ratio_median"], _ = _aggregate(amount.where(valid_member))
        required = {
            "current_strength": (("ret20", "RET20"), ("pos60", "POS60"), ("mdd20", "MDD20")),
            "stabilization": (("ret5", "RET5"), ("rs20", "RS20"), ("amount_ratio_5_20", "amount_ratio_5_20_member")),
            "reacceleration": (("ret5", "RET5"), ("ret20", "RET20"), ("rs5", "RS5"), ("rs20", "RS20"), ("rs60", "RS60"), ("amount_ratio_5_20", "amount_ratio_5_20_member")),
        }
        for scanner, fields in required.items():
            ok = pd.Series(True, index=group.index)
            for candidates in fields:
                source = _numeric(group, candidates)
                ok &= _finite(source)
            row[f"{scanner}_joint_valid_count"] = int(ok.sum())
            row[f"{scanner}_joint_valid_ratio"] = float(ok.sum() / total) if total else 0.0
        rows.append(row)
    result = pd.DataFrame(rows)
    if result.empty:
        return result
    result = result.sort_values(["trade_date", "sector_type", "sector_id"], kind="mergesort").reset_index(drop=True)
    result = add_percentiles(result)
    result["sector_rs20_pct"] = result["sector_rs20_pct_recomputed"]
    return result


def run_historical_sector_pipeline(
    technical: pd.DataFrame,
    memberships: pd.DataFrame,
    *,
    cutoff: Any,
    membership_basis: str = HISTORY_BASIS,
    membership_snapshot_id: str | None = None,
    semantic_version: str | None = None,
) -> dict[str, Any]:
    """Run the independent historical sector pipeline and return audit frames."""
    if membership_basis == CURRENT_MEMBERSHIP_BASIS:
        raise HistoryAdapterError("HISTORY_ADAPTER_REQUIRES_EXPLICIT_HISTORICAL_MEMBERSHIP")
    stocks, members, cutoff_date = guard_history_inputs(technical, memberships, cutoff, membership_basis=membership_basis)
    stocks = add_cross_sectional_rs(stocks)
    base = build_sector_base(stocks, members, membership_basis=membership_basis, membership_snapshot_id=membership_snapshot_id, semantic_version=semantic_version)
    scanned = scan_sectors(base) if not base.empty else base.copy()
    if not scanned.empty:
        scanned["membership_basis"] = membership_basis
        scanned["history_basis"] = membership_basis
        scanned["pit_membership"] = False
        scanned["historical_backtest_safe"] = False
    return {
        "contract_id": CONTRACT_VERSION,
        "history_basis": membership_basis,
        "cutoff_date": cutoff_date.isoformat(),
        "input_dates": sorted({value.isoformat() for value in stocks["trade_date"]}),
        "membership_dates": sorted({value.isoformat() for value in members["trade_date"]}),
        "cross_sectional": stocks,
        "sector_base": base,
        "sector_scanner": scanned,
        "audit": {
            "formal_snapshot_guard_preserved": True,
            "current_membership_historical_backfill": False,
            "scanner_contract": "sector-scanner-contract-v1.2-evidence-binding",
            "null_policy": "unknown remains NULL; scanner gates do not treat NULL as FALSE",
        },
    }


def serializable_summary(result: dict[str, Any]) -> dict[str, Any]:
    """Return a small JSON-safe receipt summary without serializing full frames."""
    return {
        key: value
        for key, value in result.items()
        if key not in {"cross_sectional", "sector_base", "sector_scanner"}
    } | {
        "cross_sectional_rows": len(result["cross_sectional"]),
        "sector_base_rows": len(result["sector_base"]),
        "sector_scanner_rows": len(result["sector_scanner"]),
    }
