"""M9-01 deterministic sector-day vectors and cycle state metrics.

The vector remains separate from board-index quotation.  When the M9 member
state and high-state inputs are supplied, this module also materialises the
documented strong-member, high-count, retention, and diffusion fields.  It
does not build representatives or mainline classes.
"""

from __future__ import annotations

import json
from typing import Any

import numpy as np
import pandas as pd

from .immutable import immutable_slice_state


CONTRACT_VERSION = "SECTOR_CYCLE_V1_5_QFQ_WIDTH_RS_ONLY"
HISTORY_BASIS = "RECONSTRUCTED"
DIFFUSION_COVERAGE_MIN = 0.70
HIGH_WINDOWS = (20, 30, 60, 100)


class SectorCycleError(ValueError):
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


def _median(series: pd.Series) -> float | None:
    values = pd.to_numeric(series, errors="coerce")
    values = values[np.isfinite(values)]
    return float(values.median()) if len(values) else None


def _percentile(values: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(values, errors="coerce")
    result = pd.Series(np.nan, index=values.index, dtype="float64")
    valid = numeric.notna() & np.isfinite(numeric)
    n = int(valid.sum())
    if n:
        result.loc[valid] = numeric.loc[valid].rank(method="average", ascending=True) / n
    return result


def _window_stats(group: pd.DataFrame, *, threshold: float = 0.8) -> str:
    """Summarise the available sector history without filling missing days."""
    ordered = group.sort_values("trade_date", kind="mergesort").reset_index(drop=True)
    percentiles = pd.to_numeric(ordered["sector_rs20_pct"], errors="coerce")
    amounts = pd.to_numeric(ordered["amount_vs_prior20"], errors="coerce")
    breadth = pd.to_numeric(ordered["breadth_ret1"], errors="coerce")
    values: dict[str, dict[str, Any]] = {}
    for width in (5, 10, 20, 30):
        window_p = percentiles.tail(width)
        window_a = amounts.tail(width)
        window_b = breadth.tail(width)
        valid_p = window_p.dropna()
        on_list = window_p.dropna().ge(threshold)
        consecutive = 0
        for value in reversed(window_p.tolist()):
            if pd.isna(value):
                break
            if float(value) >= threshold:
                consecutive += 1
            else:
                break
        valid_a = window_a.dropna()
        valid_b = window_b.dropna()
        values[str(width)] = {
            "valid_days": int(len(valid_p)),
            "window_complete": bool(len(ordered) >= width and len(valid_p) == width),
            "on_list_days": int(on_list.sum()),
            "consecutive_on_list": int(consecutive) if len(valid_p) else None,
            "rank_pct_mean": float(valid_p.mean()) if len(valid_p) else None,
            "rank_pct_first": float(valid_p.iloc[0]) if len(valid_p) else None,
            "rank_pct_last": float(valid_p.iloc[-1]) if len(valid_p) else None,
            "breadth_change": float(valid_b.iloc[-1] - valid_b.iloc[0]) if len(valid_b) >= 2 else None,
            "amount_change": float(valid_a.iloc[-1] - valid_a.iloc[0]) if len(valid_a) >= 2 else None,
            "amount_basis": "MEMBER_MEDIAN_STOCK_AMOUNT_VS_PRIOR20",
        }
    return json.dumps(values, ensure_ascii=False, sort_keys=True)


def _normalise(frame: pd.DataFrame, required: tuple[str, ...], label: str) -> pd.DataFrame:
    missing = [column for column in required if column not in frame.columns]
    if missing:
        raise SectorCycleError(f"{label}_COLUMNS_MISSING:" + ",".join(missing))
    result = frame.copy()
    result["trade_date"] = pd.to_datetime(result["trade_date"], errors="raise").dt.date
    if result["trade_date"].isna().any():
        raise SectorCycleError(f"{label}_DATE_INVALID")
    if "security_id" in result:
        result["security_id"] = result["security_id"].astype(str)
    return result


def _validate_cutoff(frame: pd.DataFrame, cutoff: Any | None) -> None:
    if cutoff is not None and (frame["trade_date"] > pd.Timestamp(cutoff).date()).any():
        raise SectorCycleError("FUTURE_SECTOR_CYCLE_INPUT")


def _common_breadth(
    current: pd.DataFrame,
    previous: pd.DataFrame | None,
) -> tuple[float | None, int | None, float | None, int | None]:
    """Return current width and change on one identical common-valid set."""
    if previous is None or current.empty or previous.empty:
        return None, None, None, None
    current_by_security = current.drop_duplicates("security_id", keep="last").set_index("security_id")
    previous_by_security = previous.drop_duplicates("security_id", keep="last").set_index("security_id")
    common_ids = sorted(set(current_by_security.index) & set(previous_by_security.index))
    if not common_ids:
        return None, 0, None, 0
    current_ret1 = pd.to_numeric(current_by_security.loc[common_ids, "member_ret1"], errors="coerce")
    previous_ret1 = pd.to_numeric(previous_by_security.loc[common_ids, "member_ret1"], errors="coerce")
    valid = current_ret1.notna() & previous_ret1.notna() & np.isfinite(current_ret1) & np.isfinite(previous_ret1)
    valid_count = int(valid.sum())
    if not valid_count:
        return None, 0, None, 0
    current_width = float((current_ret1.loc[valid] > 0).mean())
    previous_width = float((previous_ret1.loc[valid] > 0).mean())
    return current_width, valid_count, current_width - previous_width, valid_count


def _normalise_member_states(frame: pd.DataFrame | None) -> dict[tuple[str, Any], pd.DataFrame] | None:
    """Index M9 member states by sector/date without treating unknown as false."""
    if frame is None:
        return None
    source = _normalise(
        frame,
        ("sector_id", "security_id", "trade_date", "member_present", "strong_state"),
        "MEMBER_STATE",
    )
    source["sector_id"] = source["sector_id"].astype(str)
    if source.duplicated(["sector_id", "security_id", "trade_date"]).any():
        raise SectorCycleError("MEMBER_STATE_DUPLICATE_SECTOR_SECURITY_DATE")
    source["_member_present"] = source["member_present"].map(_tri)
    source["_strong_state"] = source["strong_state"].map(_tri)
    return {
        (str(sector_id), trade_date): group.copy()
        for (sector_id, trade_date), group in source.groupby(["sector_id", "trade_date"], sort=False)
    }


def _normalise_highs(frame: pd.DataFrame | None) -> dict[tuple[str, Any], pd.Series] | None:
    """Index the wide high output; each security/date must be unique."""
    if frame is None:
        return None
    source = _normalise(frame, ("security_id", "trade_date"), "HIGH")
    source["security_id"] = source["security_id"].astype(str)
    columns = [f"new_high_{width}" for width in HIGH_WINDOWS if f"new_high_{width}" in source.columns]
    if not columns:
        raise SectorCycleError("HIGH_COLUMNS_MISSING:new_high_20/new_high_30/new_high_60/new_high_100")
    if source.duplicated(["security_id", "trade_date"]).any():
        raise SectorCycleError("HIGH_DUPLICATE_SECURITY_DATE")
    return {
        (str(security_id), trade_date): row
        for (security_id, trade_date), row in source.set_index(["security_id", "trade_date"]).iterrows()
    }


def _cycle_state_metrics(
    sector_id: str,
    trade_date: Any,
    previous_date: Any | None,
    member_states: dict[tuple[str, Any], pd.DataFrame] | None,
    highs: dict[tuple[str, Any], pd.Series] | None,
) -> dict[str, Any]:
    """Apply the M9 formulas to one sector/date, preserving tri-state inputs."""
    fields: dict[str, Any] = {
        "strong_count": None,
        "comparable_count": None,
        "previous_strong_total": None,
        "comparable_previous_strong": None,
        "retained_count": None,
        "entered_count": None,
        "exited_count": None,
        "uncomparable_count": None,
        "retention_rate": None,
        "comparison_coverage": None,
        "diffusion_state": "DATA_UNAVAILABLE",
    }
    for width in HIGH_WINDOWS:
        fields[f"high{width}_count"] = None
        fields[f"high{width}_valid_count"] = None

    if member_states is None:
        return fields
    current = member_states.get((str(sector_id), trade_date))
    if current is None:
        return fields

    current_members = current[current["_member_present"].eq(True)]
    fields["strong_count"] = int(current_members["_strong_state"].eq(True).sum())

    if highs is not None:
        for width in HIGH_WINDOWS:
            column = f"new_high_{width}"
            valid_count = 0
            high_count = 0
            for security_id in current_members["security_id"].astype(str).tolist():
                high_row = highs.get((security_id, trade_date))
                value = _tri(high_row.get(column)) if high_row is not None and column in high_row else None
                if value is not None:
                    valid_count += 1
                    high_count += int(value)
            fields[f"high{width}_count"] = high_count
            fields[f"high{width}_valid_count"] = valid_count

    # The first observed day has no fabricated yesterday.  All comparison
    # fields stay NULL and the diffusion state is explicitly unavailable.
    if previous_date is None:
        return fields
    previous = member_states.get((str(sector_id), previous_date))
    if previous is None:
        return fields
    previous_members = previous[previous["_member_present"].eq(True)]
    if previous_members.empty:
        return fields

    current_by_id = current_members.drop_duplicates("security_id", keep="last").set_index("security_id")
    previous_by_id = previous_members.drop_duplicates("security_id", keep="last").set_index("security_id")
    common_ids = sorted(set(current_by_id.index) & set(previous_by_id.index))
    comparable = [
        security_id
        for security_id in common_ids
        if current_by_id.loc[security_id, "_strong_state"] is not None
        and previous_by_id.loc[security_id, "_strong_state"] is not None
    ]
    comparable_frame = current_by_id.loc[comparable] if comparable else current_by_id.iloc[0:0]
    previous_comparable = previous_by_id.loc[comparable] if comparable else previous_by_id.iloc[0:0]
    comparable_count = len(comparable)
    previous_strong_total = int(previous_members["_strong_state"].eq(True).sum())
    comparable_previous_strong = int(previous_comparable["_strong_state"].eq(True).sum())
    retained_count = int(
        (comparable_frame["_strong_state"].eq(True) & previous_comparable["_strong_state"].eq(True)).sum()
    )
    entered_count = int(
        (comparable_frame["_strong_state"].eq(True) & previous_comparable["_strong_state"].eq(False)).sum()
    )
    exited_count = int(
        (comparable_frame["_strong_state"].eq(False) & previous_comparable["_strong_state"].eq(True)).sum()
    )
    previous_member_count = len(previous_members)
    coverage = comparable_count / previous_member_count if previous_member_count else None
    fields.update({
        "comparable_count": comparable_count,
        "previous_strong_total": previous_strong_total,
        "comparable_previous_strong": comparable_previous_strong,
        "retained_count": retained_count,
        "entered_count": entered_count,
        "exited_count": exited_count,
        # This is the prior strong population that cannot be compared; it is
        # deliberately not the count of all added/deleted/unknown members.
        "uncomparable_count": previous_strong_total - comparable_previous_strong,
        "retention_rate": retained_count / comparable_previous_strong if comparable_previous_strong else None,
        "comparison_coverage": coverage,
    })
    if coverage < DIFFUSION_COVERAGE_MIN:
        fields["diffusion_state"] = "UNKNOWN"
    elif entered_count > exited_count:
        fields["diffusion_state"] = "EXPANSION"
    elif entered_count < exited_count:
        fields["diffusion_state"] = "CONTRACTION"
    else:
        fields["diffusion_state"] = "STABLE"
    return fields


def build_sector_cycle_daily(
    technical: pd.DataFrame,
    memberships: pd.DataFrame,
    *,
    cutoff: Any | None = None,
    board_quotes: pd.DataFrame | None = None,
    member_states: pd.DataFrame | None = None,
    highs: pd.DataFrame | None = None,
    history_basis: str = HISTORY_BASIS,
) -> pd.DataFrame:
    """Build one explainable vector per sector and trading date.

    ``memberships`` is the point-in-time membership input.  A security is
    counted once per sector/date, while a security shared by different sectors
    remains present in each sector.  ``board_quotes`` is optional and is kept
    separate from member distribution statistics.
    """
    if history_basis != HISTORY_BASIS:
        raise SectorCycleError("SECTOR_CYCLE_REQUIRES_RECONSTRUCTED_HISTORY")
    tech = _normalise(technical, ("security_id", "trade_date"), "TECHNICAL")
    members = _normalise(memberships, ("security_id", "trade_date", "sector_id"), "MEMBERSHIP")
    _validate_cutoff(tech, cutoff)
    _validate_cutoff(members, cutoff)
    if tech.duplicated(["security_id", "trade_date"]).any():
        raise SectorCycleError("TECHNICAL_DUPLICATE_SECURITY_DATE")
    if members.duplicated(["sector_id", "security_id", "trade_date"]).any():
        duplicate = members[members.duplicated(["sector_id", "security_id", "trade_date"], keep=False)]
        stable_columns = [column for column in ("sector_name", "sector_type", "sector_role") if column in duplicate.columns]
        if stable_columns and duplicate.groupby(["sector_id", "security_id", "trade_date"])[stable_columns].nunique(dropna=False).max().max() > 1:
            raise SectorCycleError("MEMBERSHIP_DUPLICATE_CONFLICT")
        members = members.drop_duplicates(["sector_id", "security_id", "trade_date"], keep="first")
    if board_quotes is not None:
        quotes = _normalise(board_quotes, ("sector_id", "trade_date"), "BOARD_QUOTE")
        _validate_cutoff(quotes, cutoff)
        if quotes.duplicated(["sector_id", "trade_date"]).any():
            raise SectorCycleError("BOARD_QUOTE_DUPLICATE_SECTOR_DATE")
    else:
        quotes = pd.DataFrame(columns=["sector_id", "trade_date", "board_quote_ret1", "board_quote_source"])
    state_groups = _normalise_member_states(member_states)
    high_groups = _normalise_highs(highs)

    join_columns = ["security_id", "trade_date"]
    merged = members.merge(tech, on=join_columns, how="left", suffixes=("", "_technical"))
    if "sector_type" not in merged:
        merged["sector_type"] = "OTHER"
    merged["sector_type"] = merged["sector_type"].fillna("OTHER").astype(str)
    if "sector_name" not in merged:
        merged["sector_name"] = merged["sector_id"].astype(str)
    merged["sector_name"] = merged["sector_name"].fillna(merged["sector_id"]).astype(str)

    def column(*names: str) -> pd.Series:
        for name in names:
            if name in merged:
                return pd.to_numeric(merged[name], errors="coerce")
        return pd.Series(np.nan, index=merged.index, dtype="float64")

    merged["member_ret1"] = column("ret1", "RET1", "quote_ret1")
    merged["member_ret5"] = column("ret5", "RET5")
    merged["member_ret20"] = column("ret20", "RET20")
    merged["member_rs5"] = column("rs5", "stock_rs5")
    merged["member_rs20"] = column("rs20", "stock_rs20")
    merged["member_amount"] = column("raw_amount", "amount", "turnover_amount")
    merged["member_amount_vs_prior20"] = column("amount_vs_prior20", "amount_vs_prior_20")
    merged["member_ma20"] = column("ma20")
    merged["member_adj_close"] = column("adj_close")

    rows: list[dict[str, Any]] = []
    sector_dates = {
        sector_id: sorted(group.trade_date.unique())
        for sector_id, group in merged.groupby("sector_id", sort=False)
    }
    sector_groups = {
        (sector_id, trade_date): group.copy()
        for (sector_id, trade_date), group in merged.groupby(["sector_id", "trade_date"], sort=True)
    }
    for (sector_id, trade_date), group in merged.groupby(["sector_id", "trade_date"], sort=True):
        group = group.copy()
        sector_type = str(group["sector_type"].iloc[0])
        sector_name = str(group["sector_name"].iloc[0])
        quote = quotes[(quotes.sector_id == sector_id) & (quotes.trade_date == trade_date)]
        board_ret = quote.iloc[0].get("board_quote_ret1") if len(quote) else None
        board_source = quote.iloc[0].get("board_quote_source") if len(quote) and "board_quote_source" in quote else None
        ret1_valid = group.member_ret1.map(_finite)
        ret20_valid = group.member_ret20.map(_finite)
        amount_valid = group.member_amount.map(_finite) & group.member_amount.gt(0)
        amount_ratio_valid = group.member_amount_vs_prior20.map(_finite) & group.member_amount_vs_prior20.gt(0)
        ma_valid = group.member_ma20.map(_finite) & group.member_adj_close.map(_finite)
        dates = sector_dates[sector_id]
        date_index = dates.index(trade_date)
        previous_group = sector_groups.get((sector_id, dates[date_index - 1])) if date_index else None
        previous_3d_group = sector_groups.get((sector_id, dates[date_index - 3])) if date_index >= 3 else None
        common_width, common_valid_count, common_change_1d, common_change_1d_valid_count = _common_breadth(group, previous_group)
        _, _, common_change_3d, common_change_3d_valid_count = _common_breadth(group, previous_3d_group)
        # Relative strength cannot be substituted with absolute return.
        rs5 = group.member_rs5
        # RS20 is an independent factor.  A missing RS20 observation must stay
        # unknown; RET20 is not a valid substitute for the sector RS20 vector.
        rs20 = group.member_rs20
        vector_rs5 = _median(rs5)
        vector_rs20 = _median(rs20)
        cycle_metrics = _cycle_state_metrics(
            str(sector_id),
            trade_date,
            dates[date_index - 1] if date_index else None,
            state_groups,
            high_groups,
        )
        rows.append({
            "sector_id": str(sector_id), "trade_date": trade_date, "sector_name": sector_name,
            "sector_type": sector_type, "history_basis": history_basis, "contract_id": CONTRACT_VERSION,
            "board_quote_ret1": float(board_ret) if _finite(board_ret) else None,
            "board_quote_source": str(board_source) if board_source is not None else None,
            "member_ret1_median": _median(group.member_ret1), "member_ret5_median": _median(group.member_ret5),
            "member_ret20_median": _median(group.member_ret20),
            "member_amount_sum": float(group.loc[amount_valid, "member_amount"].sum()) if amount_valid.any() else None,
            "amount_valid_count": int(amount_valid.sum()), "total_member_count": int(len(group)),
            "quote_valid_count": int(ret1_valid.sum()), "factor_valid_count": int(ret20_valid.sum()),
            "coverage": float(ret20_valid.sum() / len(group)) if len(group) else None,
            "breadth_ret1": float((group.loc[ret1_valid, "member_ret1"] > 0).mean()) if ret1_valid.any() else None,
            "breadth_ret1_common": common_width,
            "breadth_ret1_common_valid_count": common_valid_count,
            "breadth_ret1_common_change_1d": common_change_1d,
            "breadth_ret1_common_change_1d_valid_count": common_change_1d_valid_count,
            "breadth_ret1_common_change_3d": common_change_3d,
            "breadth_ret1_common_change_3d_valid_count": common_change_3d_valid_count,
            "breadth_ma20": float((group.loc[ma_valid, "member_adj_close"] > group.loc[ma_valid, "member_ma20"]).mean()) if ma_valid.any() else None,
            "sector_rs5": vector_rs5, "sector_rs20": vector_rs20,
            # Historical PIT membership is not available before the preview
            # dates, so a sector-level prior-20 amount ratio is explicitly the
            # median of the member stock ratios, not a fabricated sector index.
            "amount_vs_prior20": _median(group.loc[amount_ratio_valid, "member_amount_vs_prior20"]),
            "rank": None, "rank_change": None,
            "window_stats": "{}",
            **cycle_metrics,
        })
    result = pd.DataFrame(rows)
    if result.empty:
        return result
    result["sector_rs5_pct"] = result.groupby(["trade_date", "sector_type"], group_keys=False)["sector_rs5"].transform(_percentile)
    result["sector_rs20_pct"] = result.groupby(["trade_date", "sector_type"], group_keys=False)["sector_rs20"].transform(_percentile)
    result["rank"] = result.groupby(["trade_date", "sector_type"], group_keys=False)["sector_rs20"].rank(method="average", ascending=False, na_option="keep")
    result["rank"] = result["rank"].where(result["rank"].notna(), None)
    result["rank_change"] = result.sort_values(["sector_id", "trade_date"]).groupby("sector_id")["rank"].shift(1) - result["rank"]
    result = result.sort_values(["trade_date", "sector_type", "rank" , "sector_id"], na_position="last", kind="mergesort").reset_index(drop=True)
    stats_by_key = {
        key: _window_stats(group)
        for key, group in result.groupby(["sector_id", "sector_type"], sort=False)
    }
    result["window_stats"] = [stats_by_key[(row.sector_id, row.sector_type)] for row in result.itertuples()]
    return result


def rows_for_storage(frame: pd.DataFrame, slice_id: str) -> list[tuple[Any, ...]]:
    # Columns are appended by forward migrations. Keep the legacy vector
    # immutable and materialise formal amount-A fields under new names.
    columns = ("sector_id", "trade_date", "sector_name", "sector_type", "history_basis", "contract_id", "board_quote_ret1", "board_quote_source", "member_ret1_median", "member_ret5_median", "member_ret20_median", "member_amount_sum", "amount_valid_count", "total_member_count", "quote_valid_count", "factor_valid_count", "coverage", "breadth_ret1", "breadth_ma20", "sector_rs5", "sector_rs20", "sector_rs5_pct", "sector_rs20_pct", "amount_vs_prior20", "rank", "rank_change", "window_stats", "breadth_ret1_common", "breadth_ret1_common_valid_count", "breadth_ret1_common_change_1d", "breadth_ret1_common_change_1d_valid_count", "breadth_ret1_common_change_3d", "breadth_ret1_common_change_3d_valid_count", "strong_count", "high20_count", "high30_count", "high60_count", "high100_count", "high20_valid_count", "high30_valid_count", "high60_valid_count", "high100_valid_count", "comparable_count", "previous_strong_total", "comparable_previous_strong", "retained_count", "entered_count", "exited_count", "uncomparable_count", "retention_rate", "comparison_coverage", "diffusion_state", "member_amount_ratio_median_vs_prior20", "sector_amount_vs_prior20", "sector_amount_comparable_sum", "sector_amount_prior20_mean", "amount_comparable_member_count", "amount_target_member_count", "amount_comparable_coverage", "amount_window_coverage", "amount_window_target_member_max", "amount_target_denominator_source", "amount_window_denominator_source", "amount_basis", "amount_quality_codes", "amount_excluded_member_ids", "amount_member_set_hash", "amount_membership_snapshot_id", "amount_window_start", "amount_window_end", "amount_contract_id", "sector_amount_ratio_delta_3sessions_common", "amount_comparison_date", "amount_comparison_current_a", "amount_comparison_prior_a", "amount_comparison_current_sum", "amount_comparison_current_prior20_mean", "amount_comparison_prior_sum", "amount_comparison_prior_prior20_mean", "amount_comparison_member_set_hash", "amount_comparison_current_coverage", "amount_comparison_prior_coverage", "amount_comparison_window_coverage", "amount_comparison_window_start", "amount_comparison_window_end", "amount_comparison_quality_codes", "amount_comparison_excluded_member_ids", "amount_comparison_evidence")
    def storage(value: Any) -> Any:
        try:
            return None if pd.isna(value) else value.item() if hasattr(value, "item") else value
        except (TypeError, ValueError):
            return value
    json_columns = {"window_stats", "amount_quality_codes", "amount_excluded_member_ids", "amount_comparison_quality_codes", "amount_comparison_excluded_member_ids", "amount_comparison_evidence"}
    def value_for(row: pd.Series, column: str) -> Any:
        value = row.get(column)
        if value is None or not isinstance(value, (dict, list, tuple, set)) and pd.isna(value):
            return None
        if column in json_columns and value is not None and not isinstance(value, str):
            value = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
        return storage(value)
    return [tuple([slice_id] + [value_for(row, column) for column in columns]) for _, row in frame.iterrows()]


def insert_sector_cycle_rows(connection: Any, slice_id: str, frame: pd.DataFrame) -> int:
    rows = rows_for_storage(frame, slice_id)
    existing = connection.execute("select * from sector_cycle_daily where slice_id=?", [slice_id]).fetchall()
    try:
        present = immutable_slice_state(existing, rows, key_indexes=(1, 2), conflict_code="SECTOR_CYCLE_SLICE_IDENTITY_CONFLICT")
    except ValueError as exc:
        raise SectorCycleError(str(exc)) from exc
    if present:
        return len(rows)
    if rows:
        placeholders = ",".join("?" for _ in rows[0])
        columns = ("slice_id", "sector_id", "trade_date", "sector_name", "sector_type", "history_basis", "contract_id", "board_quote_ret1", "board_quote_source", "member_ret1_median", "member_ret5_median", "member_ret20_median", "member_amount_sum", "amount_valid_count", "total_member_count", "quote_valid_count", "factor_valid_count", "coverage", "breadth_ret1", "breadth_ma20", "sector_rs5", "sector_rs20", "sector_rs5_pct", "sector_rs20_pct", "amount_vs_prior20", "rank", "rank_change", "window_stats", "breadth_ret1_common", "breadth_ret1_common_valid_count", "breadth_ret1_common_change_1d", "breadth_ret1_common_change_1d_valid_count", "breadth_ret1_common_change_3d", "breadth_ret1_common_change_3d_valid_count", "strong_count", "high20_count", "high30_count", "high60_count", "high100_count", "high20_valid_count", "high30_valid_count", "high60_valid_count", "high100_valid_count", "comparable_count", "previous_strong_total", "comparable_previous_strong", "retained_count", "entered_count", "exited_count", "uncomparable_count", "retention_rate", "comparison_coverage", "diffusion_state", "member_amount_ratio_median_vs_prior20", "sector_amount_vs_prior20", "sector_amount_comparable_sum", "sector_amount_prior20_mean", "amount_comparable_member_count", "amount_target_member_count", "amount_comparable_coverage", "amount_window_coverage", "amount_window_target_member_max", "amount_target_denominator_source", "amount_window_denominator_source", "amount_basis", "amount_quality_codes", "amount_excluded_member_ids", "amount_member_set_hash", "amount_membership_snapshot_id", "amount_window_start", "amount_window_end", "amount_contract_id", "sector_amount_ratio_delta_3sessions_common", "amount_comparison_date", "amount_comparison_current_a", "amount_comparison_prior_a", "amount_comparison_current_sum", "amount_comparison_current_prior20_mean", "amount_comparison_prior_sum", "amount_comparison_prior_prior20_mean", "amount_comparison_member_set_hash", "amount_comparison_current_coverage", "amount_comparison_prior_coverage", "amount_comparison_window_coverage", "amount_comparison_window_start", "amount_comparison_window_end", "amount_comparison_quality_codes", "amount_comparison_excluded_member_ids", "amount_comparison_evidence")
        connection.executemany(f"insert into sector_cycle_daily ({','.join(columns)}) values ({placeholders})", rows)
    return len(rows)
