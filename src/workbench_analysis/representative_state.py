"""M9-03 deterministic sector representative state machine."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from .immutable import immutable_slice_state


CONTRACT_VERSION = "SECTOR_REPRESENTATIVE_STATE_V1_0"
HISTORY_BASIS = "RECONSTRUCTED"


class RepresentativeStateError(ValueError):
    pass


def _finite(value: Any) -> bool:
    try:
        return value is not None and bool(np.isfinite(float(value)))
    except (TypeError, ValueError):
        return False


def _normalise(states: pd.DataFrame) -> pd.DataFrame:
    required = ("sector_id", "security_id", "trade_date", "member_present", "strong_state")
    missing = [column for column in required if column not in states]
    if missing:
        raise RepresentativeStateError("MEMBER_STATE_COLUMNS_MISSING:" + ",".join(missing))
    result = states.copy()
    result["trade_date"] = pd.to_datetime(result["trade_date"], errors="raise").dt.date
    result["sector_id"] = result["sector_id"].astype(str)
    result["security_id"] = result["security_id"].astype(str)
    if result.duplicated(["sector_id", "security_id", "trade_date"]).any():
        raise RepresentativeStateError("REPRESENTATIVE_DUPLICATE_MEMBER_STATE")
    return result


def _ranked(group: pd.DataFrame) -> list[dict[str, Any]]:
    current = group[group["member_present"].fillna(False) & group["strong_state"].eq(True)].copy()
    if current.empty:
        return []
    if "member_rank" not in current:
        current["member_rank"] = np.nan
    if "ret20" not in current:
        current["ret20"] = np.nan
    current["_rank_missing"] = current["member_rank"].isna()
    current["_ret_missing"] = pd.to_numeric(current["ret20"], errors="coerce").isna()
    current["_ret20"] = pd.to_numeric(current["ret20"], errors="coerce")
    current = current.sort_values(["_rank_missing", "member_rank", "_ret_missing", "_ret20", "security_id"], ascending=[True, True, True, False, True], kind="mergesort")
    return current.to_dict("records")


def build_representative_state_daily(states: pd.DataFrame, *, cutoff: Any | None = None, history_basis: str = HISTORY_BASIS) -> pd.DataFrame:
    """Build candidate/confirmation state without back-writing prior dates."""
    if history_basis != HISTORY_BASIS:
        raise RepresentativeStateError("REPRESENTATIVE_REQUIRES_RECONSTRUCTED_HISTORY")
    source = _normalise(states)
    if cutoff is not None and (source["trade_date"] > pd.Timestamp(cutoff).date()).any():
        raise RepresentativeStateError("FUTURE_REPRESENTATIVE_INPUT")
    rows: list[dict[str, Any]] = []
    for sector_id, sector in source.groupby("sector_id", sort=True):
        dates = sorted(sector["trade_date"].unique())
        confirmed = None
        confirmed_since = None
        candidate = None
        candidate_since = None
        candidate_streak = 0
        previous_date = None
        for trade_date in dates:
            day = sector[sector["trade_date"] == trade_date]
            ranked = _ranked(day)
            first = ranked[0]["security_id"] if ranked else None
            second = ranked[1]["security_id"] if len(ranked) > 1 else None
            rank_gap = None
            if len(ranked) > 1:
                first_value = ranked[0].get("ret20")
                second_value = ranked[1].get("ret20")
                if _finite(first_value) and _finite(second_value):
                    rank_gap = float(first_value) - float(second_value)
            previous_confirmed = confirmed
            event = None
            if first is None:
                candidate = None
                candidate_since = None
                candidate_streak = 0
            elif first == confirmed:
                candidate = None
                candidate_since = None
                candidate_streak = 0
            elif first == candidate:
                candidate_streak += 1
                if candidate_streak >= 2:
                    confirmed = first
                    confirmed_since = trade_date
                    event = "INITIAL_CONFIRMATION" if previous_confirmed is None else "CONFIRMED_REPLACEMENT"
            else:
                candidate = first
                candidate_since = trade_date
                candidate_streak = 1
            rows.append({"sector_id": sector_id, "trade_date": trade_date, "ranked_first_id": first, "ranked_second_id": second, "rank_gap": rank_gap, "confirmed_id": confirmed, "candidate_id": candidate, "candidate_since": candidate_since, "candidate_streak": candidate_streak, "confirmed_since": confirmed_since, "confirmation_event": event, "previous_confirmed_id": previous_confirmed, "stale": bool(confirmed is not None and first is None), "representative_rank_basis": "member_rank_then_ret20_then_security_id", "history_basis": history_basis, "contract_id": CONTRACT_VERSION})
            previous_date = trade_date
    return pd.DataFrame(rows).sort_values(["trade_date", "sector_id"], kind="mergesort").reset_index(drop=True) if rows else pd.DataFrame()


def rows_for_storage(frame: pd.DataFrame, slice_id: str) -> list[tuple[Any, ...]]:
    columns = ("sector_id", "trade_date", "ranked_first_id", "ranked_second_id", "rank_gap", "confirmed_id", "candidate_id", "candidate_since", "candidate_streak", "confirmed_since", "confirmation_event", "previous_confirmed_id", "stale", "representative_rank_basis", "history_basis", "contract_id")
    return [tuple(None if pd.isna(value) else value for value in [slice_id] + [row.get(column) for column in columns]) for _, row in frame.iterrows()]


def insert_representative_rows(connection: Any, slice_id: str, frame: pd.DataFrame) -> int:
    rows = rows_for_storage(frame, slice_id)
    existing = connection.execute("select * from representative_state_daily where slice_id=?", [slice_id]).fetchall()
    try:
        present = immutable_slice_state(existing, rows, key_indexes=(1, 2), conflict_code="REPRESENTATIVE_SLICE_IDENTITY_CONFLICT")
    except ValueError as exc:
        raise RepresentativeStateError(str(exc)) from exc
    if present:
        return len(rows)
    connection.executemany("insert into representative_state_daily values (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", rows)
    return len(rows)
