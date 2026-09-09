"""M9-02 point-in-time strong-member states and comparison sets."""

from __future__ import annotations

import json
from typing import Any

import numpy as np
import pandas as pd

from .immutable import immutable_slice_state


CONTRACT_VERSION = "SECTOR_MEMBER_STATE_V1_0"
HISTORY_BASIS = "RECONSTRUCTED"


class MemberStateError(ValueError):
    pass


def _finite(value: Any) -> bool:
    try:
        return value is not None and bool(np.isfinite(float(value)))
    except (TypeError, ValueError):
        return False


def _tri(value: Any) -> bool | None:
    if value is None or pd.isna(value):
        return None
    if isinstance(value, str):
        value = value.strip().upper()
        if value in {"TRUE", "1", "YES"}:
            return True
        if value in {"FALSE", "0", "NO"}:
            return False
        return None
    return bool(value)


def _normalise(frame: pd.DataFrame, required: tuple[str, ...], label: str) -> pd.DataFrame:
    missing = [column for column in required if column not in frame.columns]
    if missing:
        raise MemberStateError(f"{label}_COLUMNS_MISSING:" + ",".join(missing))
    result = frame.copy()
    result["trade_date"] = pd.to_datetime(result["trade_date"], errors="raise").dt.date
    result["security_id"] = result["security_id"].astype(str)
    return result


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def _structure_state(frame: pd.DataFrame) -> dict[tuple[str, Any], bool | None]:
    if frame is None or frame.empty:
        return {}
    source = _normalise(frame, ("security_id", "trade_date", "hit"), "STRUCTURE")
    result = {}
    for key, group in source.groupby(["security_id", "trade_date"], sort=False):
        values = [_tri(value) for value in group["hit"]]
        result[key] = True if True in values else None if None in values else False
    return result


def _high_state(frame: pd.DataFrame) -> dict[tuple[str, Any], bool | None]:
    if frame is None or frame.empty:
        return {}
    source = _normalise(frame, ("security_id", "trade_date"), "HIGH")
    columns = [column for column in ("new_high_20", "new_high_30", "new_high_60", "new_high_100") if column in source]
    if not columns:
        raise MemberStateError("HIGH_COLUMNS_MISSING:new_high_20/new_high_30/new_high_60/new_high_100")
    result = {}
    for key, group in source.groupby(["security_id", "trade_date"], sort=False):
        values = [_tri(value) for value in group.iloc[0][columns]]
        result[key] = True if True in values else None if None in values else False
    return result


def build_sector_member_state_daily(
    technical: pd.DataFrame,
    memberships: pd.DataFrame,
    *,
    structures: pd.DataFrame | None = None,
    highs: pd.DataFrame | None = None,
    cutoff: Any | None = None,
    history_basis: str = HISTORY_BASIS,
) -> pd.DataFrame:
    """Return one state row for every sector/member/date in the union timeline."""
    if history_basis != HISTORY_BASIS:
        raise MemberStateError("MEMBER_STATE_REQUIRES_RECONSTRUCTED_HISTORY")
    tech = _normalise(technical, ("security_id", "trade_date"), "TECHNICAL")
    members = _normalise(memberships, ("sector_id", "security_id", "trade_date"), "MEMBERSHIP")
    if cutoff is not None:
        cutoff_date = pd.Timestamp(cutoff).date()
        if (tech.trade_date > cutoff_date).any() or (members.trade_date > cutoff_date).any():
            raise MemberStateError("FUTURE_MEMBER_STATE_INPUT")
    if tech.duplicated(["security_id", "trade_date"]).any():
        raise MemberStateError("TECHNICAL_DUPLICATE_SECURITY_DATE")
    key = ["sector_id", "security_id", "trade_date"]
    if members.duplicated(key).any():
        raise MemberStateError("MEMBERSHIP_DUPLICATE_CONFLICT")
    joined = members.merge(tech, on=["security_id", "trade_date"], how="left", suffixes=("", "_technical"))
    def numeric(*names: str) -> pd.Series:
        for name in names:
            if name in joined:
                return pd.to_numeric(joined[name], errors="coerce")
        return pd.Series(np.nan, index=joined.index, dtype="float64")
    ret20 = numeric("ret20", "RET20")
    rs20 = numeric("rs20", "stock_rs20")
    rps20 = numeric("rps20", "rps20_pct")
    rank_metric = rs20.where(rs20.notna(), ret20)
    joined["_rank_metric"] = rank_metric
    joined["_rps20"] = rps20
    joined["_ret20"] = ret20
    joined["_rank"] = joined.groupby(["sector_id", "trade_date"])["_rank_metric"].rank(method="average", ascending=False, na_option="keep")
    joined["_rank_valid_count"] = joined.groupby(["sector_id", "trade_date"])["_rank_metric"].transform(lambda values: int(values.notna().sum()))
    joined["_member_percentile"] = (joined["_rank_valid_count"] - joined["_rank"] + 1) / joined["_rank_valid_count"].replace(0, np.nan)
    structure = _structure_state(structures)
    high = _high_state(highs)
    rows: list[dict[str, Any]] = []
    for _, row in joined.iterrows():
        pair = (row.security_id, row.trade_date)
        data_valid = _finite(row._ret20) or _finite(row._rank_metric)
        market_rps = _tri(float(row._rps20) >= .80) if _finite(row._rps20) else None
        sector_percentile = _tri(float(row._member_percentile) >= .80) if _finite(row._member_percentile) else None
        structure_hit = structure.get(pair)
        high_hit = high.get(pair)
        structure_or_high = True if structure_hit is True or high_hit is True else None if structure_hit is None or high_hit is None else False
        predicates = {"data_valid": data_valid, "market_rps20_ge_080": market_rps, "sector_member_percentile_ge_080": sector_percentile, "structure_or_high": structure_or_high}
        known = [value for value in predicates.values() if value is not None]
        strong = True if len(known) == len(predicates) and all(known) else False if len(known) == len(predicates) else None
        rows.append({"sector_id": str(row.sector_id), "security_id": str(row.security_id), "trade_date": row.trade_date, "member_present": True, "member_rank": float(row._rank) if _finite(row._rank) else None, "rank_valid_count": int(row._rank_valid_count), "member_percentile": float(row._member_percentile) if _finite(row._member_percentile) else None, "strong_state": strong, "strong_predicates": _json(predicates), "structure_hit": structure_hit, "high_hit": high_hit, "member_change_kind": None, "strength_change_kind": None, "previous_rank": None, "rank_delta": None, "queue_refs": _json([]), "high_refs": _json([]), "history_basis": history_basis, "contract_id": CONTRACT_VERSION})
    result = pd.DataFrame(rows)
    if result.empty:
        return result
    dates = sorted(result.trade_date.unique())
    by_key = result.set_index(["sector_id", "security_id", "trade_date"])
    state_rows = []
    for current_date in dates:
        previous_date = dates[dates.index(current_date) - 1] if dates.index(current_date) else None
        current_keys = set(result.loc[result.trade_date == current_date, ["sector_id", "security_id"]].itertuples(index=False, name=None))
        previous_keys = set(result.loc[result.trade_date == previous_date, ["sector_id", "security_id"]].itertuples(index=False, name=None)) if previous_date else set()
        for sector_id, security_id in sorted(current_keys | previous_keys):
            current = by_key.loc[(sector_id, security_id, current_date)] if (sector_id, security_id, current_date) in by_key.index else None
            previous = by_key.loc[(sector_id, security_id, previous_date)] if previous_date and (sector_id, security_id, previous_date) in by_key.index else None
            if current is None:
                current = {"sector_id": sector_id, "security_id": security_id, "trade_date": current_date, "member_present": False, "member_rank": None, "rank_valid_count": 0, "member_percentile": None, "strong_state": None, "strong_predicates": _json({}), "structure_hit": None, "high_hit": None, "previous_rank": previous["member_rank"], "rank_delta": None, "queue_refs": _json([]), "high_refs": _json([]), "history_basis": HISTORY_BASIS, "contract_id": CONTRACT_VERSION}
            else:
                current = current.to_dict()
                current["sector_id"] = sector_id
                current["security_id"] = security_id
                current["trade_date"] = current_date
                current["previous_rank"] = previous["member_rank"] if previous is not None else None
                current["rank_delta"] = (current["previous_rank"] - current["member_rank"]) if _finite(current["previous_rank"]) and _finite(current["member_rank"]) else None
            if previous_date is None:
                change = "UNKNOWN"
            elif previous is None:
                change = "ADDED" if current["member_present"] else "REMOVED"
            elif not current["member_present"]:
                change = "REMOVED"
            elif not previous["member_present"]:
                change = "ADDED"
            elif current["strong_state"] is None or previous["strong_state"] is None:
                change = "UNKNOWN"
            elif current["strong_state"] and previous["strong_state"]:
                change = "RETAINED"
            elif current["strong_state"] and not previous["strong_state"]:
                change = "ENTERED"
            elif not current["strong_state"] and previous["strong_state"]:
                change = "EXITED"
            else:
                change = "UNCHANGED"
            current["member_change_kind"] = change
            current["strength_change_kind"] = change if change in {"RETAINED", "ENTERED", "EXITED", "UNKNOWN", "UNCHANGED"} else None
            state_rows.append(current)
    return pd.DataFrame(state_rows).sort_values(["trade_date", "sector_id", "member_rank", "security_id"], na_position="last", kind="mergesort").reset_index(drop=True)


def build_membership_changes(states: pd.DataFrame) -> pd.DataFrame:
    """Extract only actual set additions/removals; first observations are excluded."""
    if states.empty:
        return pd.DataFrame(columns=["sector_id", "security_id", "trade_date", "change_type", "basis_version", "reason"])
    result = states[states.member_change_kind.isin(["ADDED", "REMOVED"])].copy()
    result["change_type"] = result["member_change_kind"]
    result["basis_version"] = CONTRACT_VERSION
    result["reason"] = result["change_type"].map({"ADDED": "CURRENT_MEMBER_NOT_IN_PREVIOUS_DATE", "REMOVED": "PREVIOUS_MEMBER_NOT_IN_CURRENT_DATE"})
    return result[["sector_id", "security_id", "trade_date", "change_type", "basis_version", "reason"]].reset_index(drop=True)


def rows_for_storage(frame: pd.DataFrame, slice_id: str) -> list[tuple[Any, ...]]:
    columns = ("sector_id", "security_id", "trade_date", "member_present", "member_rank", "rank_valid_count", "member_percentile", "strong_state", "strong_predicates", "structure_hit", "high_hit", "member_change_kind", "strength_change_kind", "previous_rank", "rank_delta", "queue_refs", "high_refs", "history_basis", "contract_id")
    return [tuple([slice_id] + [row.get(column) for column in columns]) for _, row in frame.iterrows()]


def change_rows_for_storage(frame: pd.DataFrame, slice_id: str) -> list[tuple[Any, ...]]:
    return [(slice_id, row.sector_id, row.security_id, row.trade_date, row.change_type, row.basis_version, row.reason) for row in frame.itertuples()]


def insert_member_state_rows(connection: Any, slice_id: str, frame: pd.DataFrame) -> int:
    """Insert an immutable member-state slice, rejecting identity conflicts."""
    rows = rows_for_storage(frame, slice_id)
    existing = connection.execute(
        "select * from sector_member_state_daily where slice_id=?", [slice_id]
    ).fetchall()
    if immutable_slice_state(existing, rows, key_indexes=(1, 2, 3), conflict_code="MEMBER_STATE_SLICE_IDENTITY_CONFLICT"):
        return len(rows)
    connection.executemany(
        "insert into sector_member_state_daily values (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        rows,
    )
    return len(rows)


def insert_membership_change_rows(connection: Any, slice_id: str, frame: pd.DataFrame) -> int:
    """Insert an immutable membership-change slice, rejecting identity conflicts."""
    rows = change_rows_for_storage(frame, slice_id)
    existing = connection.execute(
        "select * from sector_membership_changes where slice_id=?", [slice_id]
    ).fetchall()
    if immutable_slice_state(existing, rows, key_indexes=(1, 2, 3, 4), conflict_code="MEMBERSHIP_CHANGE_SLICE_IDENTITY_CONFLICT"):
        return len(rows)
    if not rows:
        return 0
    connection.executemany(
        "insert into sector_membership_changes values (?,?,?,?,?,?,?)",
        rows,
    )
    return len(rows)
