"""M10 sector amount A independent calculator.

This module is the stage-B implementation from chapter 27 of the M7-M15
implementation plan.  It deliberately does not consume or write the M9/M10
tables yet.  The formal metric is a common-member aggregate amount ratio:

    S(U, u) = sum(raw_amount[i, u] for i in U)
    D(U, t) = mean(S(U, u) for u in the 20 calendar sessions before t)
    A(s, t) = S(U, t) / D(U, t)

The same fixed member set U is used for the numerator and the denominator.
The separate member-level median is not used here; later stages may expose it
as an explicitly named diagnostic field.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import hashlib
import math
from typing import Any, Iterable, Sequence

import pandas as pd


CONTRACT_VERSION = "SECTOR_AMOUNT_COMMON_AGG_V1"
OBSERVED = "OBSERVED"
RECONSTRUCTED = "RECONSTRUCTED"
DEFAULT_MIN_COMPARABLE_MEMBERS = 5
DEFAULT_MIN_COMPARABLE_COVERAGE = 0.80
CONFIRMED_ZERO_STATUSES = frozenset({
    "CONFIRMED_ZERO",
    "NO_TRADE_CONFIRMED",
    "SUSPENDED_CONFIRMED",
})
UNKNOWN_STATUSES = frozenset({"UNKNOWN", "INVALID", "MISSING", "QUALITY_FAILED"})


class SectorAmountError(ValueError):
    """Raised when the stage-B input contract is structurally invalid."""


@dataclass(frozen=True)
class SectorAmountWindowPlan:
    """Calendar-position plan for one target session."""

    trade_date: date
    prior_dates: tuple[date, ...]
    history_dates: tuple[date, ...]
    comparison_date: date | None
    comparison_history_dates: tuple[date, ...]
    comparison_union_dates: tuple[date, ...]

    @property
    def has_primary_history(self) -> bool:
        return len(self.prior_dates) == 20 and len(self.history_dates) == 21

    @property
    def has_comparison_history(self) -> bool:
        return (
            self.comparison_date is not None
            and len(self.comparison_history_dates) == 21
            and len(self.comparison_union_dates) == 24
        )


def _as_date(value: Any) -> date:
    try:
        return pd.Timestamp(value).date()
    except (TypeError, ValueError, pd.errors.ParserError) as exc:
        raise SectorAmountError(f"NO_CALENDAR:INVALID_DATE:{value}") from exc


def _calendar_dates(calendar: Iterable[Any]) -> tuple[date, ...]:
    try:
        values = tuple(_as_date(value) for value in calendar)
    except TypeError as exc:
        raise SectorAmountError("NO_CALENDAR:NOT_ITERABLE") from exc
    if not values or len(set(values)) != len(values) or values != tuple(sorted(values)):
        raise SectorAmountError("NO_CALENDAR:UNSORTED_OR_DUPLICATE")
    return values


def plan_sector_amount_window(calendar: Sequence[Any], trade_date: Any) -> SectorAmountWindowPlan:
    """Plan primary and 3-session comparison windows by master-calendar position.

    The function never reaches farther back to compensate for a missing row.
    A target before the 20-session warm-up still receives a plan, but its
    primary result must carry ``INSUFFICIENT_HISTORY``.  The comparison date is
    exactly three positions earlier in the supplied master calendar.
    """

    dates = _calendar_dates(calendar)
    target = _as_date(trade_date)
    if target not in dates:
        raise SectorAmountError("NO_CALENDAR:TARGET_NOT_FOUND")
    index = dates.index(target)
    prior_dates = dates[max(0, index - 20):index]
    history_dates = prior_dates + (target,)
    comparison_date = dates[index - 3] if index >= 3 else None
    comparison_history_dates: tuple[date, ...] = ()
    comparison_union_dates: tuple[date, ...] = ()
    if comparison_date is not None:
        comparison_index = index - 3
        comparison_prior = dates[max(0, comparison_index - 20):comparison_index]
        comparison_history_dates = comparison_prior + (comparison_date,)
        comparison_union_dates = tuple(sorted(set(history_dates).union(comparison_history_dates)))
    return SectorAmountWindowPlan(
        trade_date=target,
        prior_dates=prior_dates,
        history_dates=history_dates,
        comparison_date=comparison_date,
        comparison_history_dates=comparison_history_dates,
        comparison_union_dates=comparison_union_dates,
    )


def _finite(value: Any) -> bool:
    try:
        return value is not None and bool(pd.notna(value)) and math.isfinite(float(value))
    except (TypeError, ValueError):
        return False


def _truthy(value: Any) -> bool:
    if isinstance(value, str):
        return value.strip().upper() in {"1", "TRUE", "YES", "Y"}
    return bool(value) if value is not None and not pd.isna(value) else False


def _normalise_status(value: Any) -> str | None:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    text = str(value).strip().upper()
    return text or None


def _quality_failed(row: pd.Series) -> bool:
    for column in ("amount_quality_code", "amount_quality", "amount_data_quality"):
        if column not in row.index:
            continue
        value = row.get(column)
        if value is None or (isinstance(value, float) and math.isnan(value)):
            continue
        text = str(value).strip().upper()
        if text and text not in {"OK", "VALID", "CONFIRMED"}:
            return True
    if "is_synthetic_fill" in row.index and _truthy(row.get("is_synthetic_fill")):
        return True
    return False


def _amount_state(row: pd.Series | None) -> tuple[bool, float | None, str]:
    """Return (valid, value, reason) for one security/session amount.

    Positive finite amounts are valid by default.  Zero is valid only when an
    explicit confirmation says it means no trade or a confirmed suspension;
    otherwise zero is unknown rather than a value to be filled into a sum.
    """

    if row is None:
        return False, None, "MISSING"
    if _quality_failed(row):
        return False, None, "QUALITY_FAILED"
    value = row.get("raw_amount")
    status = _normalise_status(row.get("amount_status")) if "amount_status" in row.index else None
    confirmed_zero = any(
        _truthy(row.get(column))
        for column in ("amount_zero_confirmed", "is_confirmed_zero", "no_trade_confirmed", "suspended_confirmed")
        if column in row.index
    )
    if status in UNKNOWN_STATUSES:
        return False, None, status
    if not _finite(value):
        return False, None, "INVALID"
    numeric = float(value)
    if numeric > 0:
        return True, numeric, "VALID"
    if numeric == 0 and (confirmed_zero or status in CONFIRMED_ZERO_STATUSES):
        return True, 0.0, "CONFIRMED_ZERO"
    return False, None, "INVALID"


def _hash_members(member_ids: Iterable[str]) -> str:
    payload = "\n".join(sorted({str(value) for value in member_ids}))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _normalise_amounts(amounts: pd.DataFrame, calendar: tuple[date, ...], cutoff: Any | None) -> pd.DataFrame:
    required = {"security_id", "trade_date", "raw_amount"}
    missing = sorted(required.difference(amounts.columns))
    if missing:
        raise SectorAmountError("AMOUNT_INPUT_COLUMNS_MISSING:" + ",".join(missing))
    result = amounts.copy()
    result["security_id"] = result["security_id"].astype(str)
    result["trade_date"] = result["trade_date"].map(_as_date)
    calendar_set = set(calendar)
    if not set(result["trade_date"]).issubset(calendar_set):
        raise SectorAmountError("NO_CALENDAR:AMOUNT_DATE_NOT_IN_CALENDAR")
    if cutoff is not None and any(value > _as_date(cutoff) for value in result["trade_date"]):
        raise SectorAmountError("FUTURE_SECTOR_AMOUNT_INPUT")
    if result.duplicated(["security_id", "trade_date"]).any():
        raise SectorAmountError("AMOUNT_DUPLICATE_SECURITY_DATE")
    return result.set_index(["security_id", "trade_date"], drop=False)


def _normalise_memberships(
    memberships: pd.DataFrame,
    calendar: tuple[date, ...],
    mode: str,
    membership_snapshot: pd.DataFrame | None,
) -> tuple[dict[tuple[str, date], frozenset[str]], dict[str, frozenset[str]]]:
    source = membership_snapshot if mode == RECONSTRUCTED and membership_snapshot is not None else memberships
    required = {"sector_id", "security_id"}
    missing = sorted(required.difference(source.columns))
    if missing:
        raise SectorAmountError("MEMBERSHIP_INPUT_COLUMNS_MISSING:" + ",".join(missing))
    result = source.copy()
    result["sector_id"] = result["sector_id"].astype(str)
    result["security_id"] = result["security_id"].astype(str)
    if mode == OBSERVED:
        if "trade_date" not in result.columns:
            raise SectorAmountError("MEMBERSHIP_HISTORY_MISSING:TRADE_DATE_REQUIRED")
        result["trade_date"] = result["trade_date"].map(_as_date)
        if not set(result["trade_date"]).issubset(set(calendar)):
            raise SectorAmountError("NO_CALENDAR:MEMBERSHIP_DATE_NOT_IN_CALENDAR")
        if result.duplicated(["sector_id", "security_id", "trade_date"]).any():
            raise SectorAmountError("MEMBERSHIP_DUPLICATE_SECTOR_SECURITY_DATE")
        dated = {
            (sector_id, trade_date): frozenset(group["security_id"])
            for (sector_id, trade_date), group in result.groupby(["sector_id", "trade_date"], sort=False)
        }
        return dated, {}
    if "trade_date" in result.columns:
        dates = {_as_date(value) for value in result["trade_date"].dropna()}
        if len(dates) > 1:
            raise SectorAmountError("MEMBERSHIP_SNAPSHOT_NOT_FIXED")
    if result.duplicated(["sector_id", "security_id"]).any():
        raise SectorAmountError("MEMBERSHIP_DUPLICATE_SNAPSHOT_MEMBER")
    fixed = {
        sector_id: frozenset(group["security_id"])
        for sector_id, group in result.groupby("sector_id", sort=False)
    }
    return {}, fixed


def _members_for(
    dated: dict[tuple[str, date], frozenset[str]],
    fixed: dict[str, frozenset[str]],
    mode: str,
    sector_id: str,
    trade_date: date,
) -> frozenset[str] | None:
    return fixed.get(sector_id) if mode == RECONSTRUCTED else dated.get((sector_id, trade_date))


def _row_lookup(amounts: pd.DataFrame, security_id: str, trade_date: date) -> pd.Series | None:
    try:
        value = amounts.loc[(security_id, trade_date)]
    except KeyError:
        return None
    if isinstance(value, pd.DataFrame):
        raise SectorAmountError("AMOUNT_DUPLICATE_SECURITY_DATE")
    return value


def _sum_for_members(
    amounts: pd.DataFrame,
    members: Iterable[str],
    trade_date: date,
) -> tuple[float, int, set[str], dict[str, str]]:
    total = 0.0
    valid_count = 0
    invalid: set[str] = set()
    reasons: dict[str, str] = {}
    for security_id in sorted(set(members)):
        valid, value, reason = _amount_state(_row_lookup(amounts, security_id, trade_date))
        if valid:
            total += float(value)
            valid_count += 1
        else:
            invalid.add(security_id)
            reasons[security_id] = reason
    return total, valid_count, invalid, reasons


def _candidate_members(
    sector_id: str,
    dates: Sequence[date],
    dated: dict[tuple[str, date], frozenset[str]],
    fixed: dict[str, frozenset[str]],
    mode: str,
) -> tuple[frozenset[str], bool, list[int]]:
    groups: list[frozenset[str]] = []
    missing_positions: list[int] = []
    for index, trade_date in enumerate(dates):
        members = _members_for(dated, fixed, mode, sector_id, trade_date)
        if members is None:
            missing_positions.append(index)
        else:
            groups.append(members)
    if not groups:
        return frozenset(), True, missing_positions
    candidate = groups[0]
    for group in groups[1:]:
        candidate = candidate.intersection(group)
    return frozenset(candidate), bool(missing_positions), missing_positions


def _coverage(numerator: int, denominator: int) -> float | None:
    return float(numerator / denominator) if denominator > 0 else None


def _quality_codes(
    *,
    has_history: bool,
    membership_missing: bool,
    invalid_amount: bool,
    comparable_count: int,
    current_coverage: float | None,
    window_coverage: float | None,
    baseline_nonpositive: bool,
    min_members: int,
    min_coverage: float,
) -> list[str]:
    codes: set[str] = set()
    if not has_history:
        codes.add("INSUFFICIENT_HISTORY")
    if membership_missing:
        codes.add("MEMBERSHIP_HISTORY_MISSING")
    if invalid_amount:
        codes.add("INVALID_AMOUNT")
    if comparable_count < min_members:
        codes.add("LOW_MEMBER_COUNT")
    if current_coverage is None or current_coverage < min_coverage:
        codes.add("LOW_COVERAGE")
    if window_coverage is None or window_coverage < min_coverage:
        codes.add("LOW_COVERAGE")
    if baseline_nonpositive:
        codes.add("NONPOSITIVE_BASELINE")
    return sorted(codes)


def _build_primary_row(
    *,
    sector_id: str,
    trade_date: date,
    plan: SectorAmountWindowPlan,
    amounts: pd.DataFrame,
    dated: dict[tuple[str, date], frozenset[str]],
    fixed: dict[str, frozenset[str]],
    mode: str,
    min_members: int,
    min_coverage: float,
    membership_snapshot_id: str | None,
) -> dict[str, Any]:
    current_members = _members_for(dated, fixed, mode, sector_id, trade_date)
    target_members = current_members or frozenset()
    target_count = len(target_members)
    member_sum, amount_valid_count, current_invalid, _ = _sum_for_members(amounts, target_members, trade_date)
    candidate, membership_missing, _ = _candidate_members(sector_id, plan.history_dates, dated, fixed, mode)
    valid_members = set(candidate)
    invalid_amount_members: set[str] = set()
    sums: dict[date, float] = {}
    for window_date in plan.history_dates:
        total, _, invalid, _ = _sum_for_members(amounts, valid_members, window_date)
        if invalid:
            invalid_amount_members.update(invalid)
    valid_members.difference_update(invalid_amount_members)
    comparable_count = len(valid_members)
    current_coverage = _coverage(comparable_count, target_count)
    target_counts = [
        len(_members_for(dated, fixed, mode, sector_id, window_date) or frozenset())
        for window_date in plan.history_dates
    ]
    max_target_count = max(target_counts, default=0)
    window_coverage = _coverage(comparable_count, max_target_count)
    invalid_for_quality = bool(invalid_amount_members or current_invalid)
    baseline_nonpositive = False
    comparable_sum: float | None = None
    prior_mean: float | None = None
    amount_value: float | None = None
    if plan.has_primary_history and valid_members:
        for window_date in plan.history_dates:
            total, _, invalid, _ = _sum_for_members(amounts, valid_members, window_date)
            if invalid:
                invalid_amount_members.update(invalid)
            sums[window_date] = total
        comparable_sum = sums.get(trade_date)
        if plan.prior_dates and all(window_date in sums for window_date in plan.prior_dates):
            prior_mean = sum(sums[window_date] for window_date in plan.prior_dates) / 20
            baseline_nonpositive = prior_mean <= 0
    quality_codes = _quality_codes(
        has_history=plan.has_primary_history,
        membership_missing=membership_missing,
        invalid_amount=invalid_for_quality,
        comparable_count=comparable_count,
        current_coverage=current_coverage,
        window_coverage=window_coverage,
        baseline_nonpositive=baseline_nonpositive,
        min_members=min_members,
        min_coverage=min_coverage,
    )
    if not quality_codes and comparable_sum is not None and prior_mean is not None and prior_mean > 0:
        amount_value = comparable_sum / prior_mean
    excluded = sorted(set(target_members).difference(valid_members))
    return {
        "sector_id": sector_id,
        "trade_date": trade_date,
        "sector_amount_vs_prior20": amount_value,
        "sector_amount_comparable_sum": comparable_sum,
        "sector_amount_prior20_mean": prior_mean,
        "member_amount_sum": member_sum if amount_valid_count else None,
        "amount_valid_count": amount_valid_count,
        "amount_target_member_count": target_count,
        "amount_comparable_member_count": comparable_count,
        "amount_comparable_coverage": current_coverage,
        "amount_window_coverage": window_coverage,
        "amount_window_target_member_max": max_target_count,
        "amount_target_denominator_source": "CURRENT_TARGET_MEMBERS",
        "amount_window_denominator_source": "MAX_H21_TARGET_MEMBERS",
        "amount_member_set_hash": _hash_members(valid_members),
        "amount_window_start": plan.history_dates[0] if plan.history_dates else None,
        "amount_window_end": plan.history_dates[-1] if plan.history_dates else trade_date,
        "amount_basis": (
            "OBSERVED_COMMON_MEMBER_AGGREGATE"
            if mode == OBSERVED
            else "RECONSTRUCTED_FIXED_SNAPSHOT_COMMON_MEMBER_AGGREGATE"
        ),
        "amount_quality_codes": quality_codes,
        "amount_excluded_member_ids": excluded,
        "amount_membership_snapshot_id": membership_snapshot_id,
        "amount_contract_id": CONTRACT_VERSION,
    }


def _comparison_for_row(
    *,
    row: dict[str, Any],
    sector_id: str,
    trade_date: date,
    plan: SectorAmountWindowPlan,
    amounts: pd.DataFrame,
    dated: dict[tuple[str, date], frozenset[str]],
    fixed: dict[str, frozenset[str]],
    mode: str,
    min_members: int,
    min_coverage: float,
) -> None:
    empty = {
        "amount_comparison_date": plan.comparison_date,
        "sector_amount_ratio_delta_3sessions_common": None,
        "amount_comparison_current_a": None,
        "amount_comparison_prior_a": None,
        "amount_comparison_current_sum": None,
        "amount_comparison_current_prior20_mean": None,
        "amount_comparison_prior_sum": None,
        "amount_comparison_prior_prior20_mean": None,
        "amount_comparison_member_set_hash": _hash_members(()),
        "amount_comparison_current_coverage": None,
        "amount_comparison_prior_coverage": None,
        "amount_comparison_window_coverage": None,
        "amount_comparison_window_start": plan.comparison_union_dates[0] if plan.comparison_union_dates else None,
        "amount_comparison_window_end": plan.comparison_union_dates[-1] if plan.comparison_union_dates else None,
        "amount_comparison_quality_codes": ["INSUFFICIENT_HISTORY"] if not plan.has_comparison_history else [],
        "amount_comparison_excluded_member_ids": [],
        "amount_comparison_evidence": {
            "comparison_date": plan.comparison_date,
            "quality_codes": ["INSUFFICIENT_HISTORY"] if not plan.has_comparison_history else [],
        },
    }
    row.update(empty)
    if not plan.has_comparison_history or plan.comparison_date is None:
        return
    comparison_date = plan.comparison_date
    current_members = _members_for(dated, fixed, mode, sector_id, trade_date) or frozenset()
    prior_members = _members_for(dated, fixed, mode, sector_id, comparison_date) or frozenset()
    candidate, membership_missing, _ = _candidate_members(
        sector_id,
        plan.comparison_union_dates,
        dated,
        fixed,
        mode,
    )
    valid_members = set(candidate)
    invalid_amount_members: set[str] = set()
    sums: dict[date, float] = {}
    for window_date in plan.comparison_union_dates:
        total, _, invalid, _ = _sum_for_members(amounts, valid_members, window_date)
        if invalid:
            invalid_amount_members.update(invalid)
        sums[window_date] = total
    valid_members.difference_update(invalid_amount_members)
    for window_date in plan.comparison_union_dates:
        total, _, invalid, _ = _sum_for_members(amounts, valid_members, window_date)
        if invalid:
            invalid_amount_members.update(invalid)
        sums[window_date] = total
    comparable_count = len(valid_members)
    current_coverage = _coverage(comparable_count, len(current_members))
    prior_coverage = _coverage(comparable_count, len(prior_members))
    all_target_counts = [
        len(_members_for(dated, fixed, mode, sector_id, window_date) or frozenset())
        for window_date in plan.comparison_union_dates
    ]
    window_coverage = _coverage(comparable_count, max(all_target_counts, default=0))
    current_mean = sum(sums[window_date] for window_date in plan.prior_dates) / 20
    prior_mean = sum(sums[window_date] for window_date in plan.comparison_history_dates[:-1]) / 20
    current_sum = sums[trade_date]
    prior_sum = sums[comparison_date]
    baseline_nonpositive = current_mean <= 0 or prior_mean <= 0
    codes = _quality_codes(
        has_history=True,
        membership_missing=membership_missing,
        invalid_amount=bool(invalid_amount_members),
        comparable_count=comparable_count,
        current_coverage=current_coverage,
        window_coverage=window_coverage,
        baseline_nonpositive=baseline_nonpositive,
        min_members=min_members,
        min_coverage=min_coverage,
    )
    current_a = None if current_mean <= 0 else current_sum / current_mean
    prior_a = None if prior_mean <= 0 else prior_sum / prior_mean
    if not codes and current_a is not None and prior_a is not None:
        row["sector_amount_ratio_delta_3sessions_common"] = current_a - prior_a
    row.update({
        "amount_comparison_current_a": current_a if not codes else None,
        "amount_comparison_prior_a": prior_a if not codes else None,
        "amount_comparison_current_sum": current_sum,
        "amount_comparison_current_prior20_mean": current_mean,
        "amount_comparison_prior_sum": prior_sum,
        "amount_comparison_prior_prior20_mean": prior_mean,
        "amount_comparison_member_set_hash": _hash_members(valid_members),
        "amount_comparison_current_coverage": current_coverage,
        "amount_comparison_prior_coverage": prior_coverage,
        "amount_comparison_window_coverage": window_coverage,
        "amount_comparison_quality_codes": codes,
        "amount_comparison_excluded_member_ids": sorted(set(current_members).union(prior_members).difference(valid_members)),
        "amount_comparison_evidence": {
            "comparison_date": comparison_date,
            "current_a": current_a if not codes else None,
            "prior_a": prior_a if not codes else None,
            "current_sum": current_sum,
            "current_prior20_mean": current_mean,
            "prior_sum": prior_sum,
            "prior_prior20_mean": prior_mean,
            "member_set_hash": _hash_members(valid_members),
            "current_coverage": current_coverage,
            "prior_coverage": prior_coverage,
            "window_coverage": window_coverage,
            "quality_codes": codes,
            "membership_snapshot_id": row.get("amount_membership_snapshot_id"),
        },
    })


def _build_reconstructed_target_rows_fast(
    amounts: pd.DataFrame,
    memberships: pd.DataFrame,
    calendar_dates: tuple[date, ...],
    *,
    membership_snapshot: pd.DataFrame | None,
    membership_snapshot_id: str | None,
    cutoff: Any | None,
    min_members: int,
    min_coverage: float,
    target_dates: set[date],
) -> pd.DataFrame:
    """Build fixed-snapshot target rows without repeated MultiIndex lookups.

    The generic implementation is intentionally easy to audit and remains the
    reference path.  Preview-sized reconstructed builds use this equivalent
    path: it caches the amount state for each security/session once, then
    evaluates each H21/24 window from that cache.
    """
    dated, fixed = _normalise_memberships(
        memberships, calendar_dates, RECONSTRUCTED, membership_snapshot
    )
    plans = {trade_date: plan_sector_amount_window(calendar_dates, trade_date) for trade_date in target_dates}
    needed_dates: set[date] = set()
    for plan in plans.values():
        needed_dates.update(plan.history_dates)
        needed_dates.update(plan.comparison_union_dates)

    amount_input = amounts.copy()
    amount_input["security_id"] = amount_input["security_id"].astype(str)
    amount_input["trade_date"] = amount_input["trade_date"].map(_as_date)
    if cutoff is not None and any(value > _as_date(cutoff) for value in amount_input["trade_date"]):
        raise SectorAmountError("FUTURE_SECTOR_AMOUNT_INPUT")
    amount_input = amount_input[amount_input["trade_date"].isin(needed_dates)].copy()
    if amount_input.duplicated(["security_id", "trade_date"]).any():
        raise SectorAmountError("AMOUNT_DUPLICATE_SECURITY_DATE")
    amount_states: dict[tuple[str, date], tuple[bool, float | None, str]] = {}
    for _, source_row in amount_input.iterrows():
        state = _amount_state(source_row)
        amount_states[(str(source_row["security_id"]), source_row["trade_date"])] = state

    def state(security_id: str, trade_date: date) -> tuple[bool, float | None, str]:
        return amount_states.get((str(security_id), trade_date), (False, None, "MISSING"))

    def sum_for(security_ids: set[str], trade_date: date) -> tuple[float, int, set[str]]:
        total = 0.0
        valid_count = 0
        invalid: set[str] = set()
        for security_id in security_ids:
            valid, value, _ = state(security_id, trade_date)
            if valid:
                total += float(value)
                valid_count += 1
            else:
                invalid.add(security_id)
        return total, valid_count, invalid

    rows: list[dict[str, Any]] = []
    for trade_date in sorted(target_dates):
        plan = plans[trade_date]
        for sector_id in sorted(fixed):
            target_members = set(fixed[sector_id])
            target_count = len(target_members)
            member_sum, amount_valid_count, current_invalid = sum_for(target_members, trade_date)
            valid_members = {
                security_id
                for security_id in target_members
                if all(state(security_id, window_date)[0] for window_date in plan.history_dates)
            }
            invalid_amount_members = target_members.difference(valid_members)
            comparable_count = len(valid_members)
            current_coverage = _coverage(comparable_count, target_count)
            window_coverage = current_coverage
            sums = {window_date: sum_for(valid_members, window_date)[0] for window_date in plan.history_dates}
            comparable_sum = sums.get(trade_date) if plan.has_primary_history else None
            prior_mean = (
                sum(sums[window_date] for window_date in plan.prior_dates) / 20
                if plan.has_primary_history and all(window_date in sums for window_date in plan.prior_dates)
                else None
            )
            baseline_nonpositive = prior_mean is not None and prior_mean <= 0
            quality_codes = _quality_codes(
                has_history=plan.has_primary_history,
                membership_missing=False,
                invalid_amount=bool(invalid_amount_members or current_invalid),
                comparable_count=comparable_count,
                current_coverage=current_coverage,
                window_coverage=window_coverage,
                baseline_nonpositive=baseline_nonpositive,
                min_members=min_members,
                min_coverage=min_coverage,
            )
            amount_value = (
                comparable_sum / prior_mean
                if not quality_codes and comparable_sum is not None and prior_mean is not None and prior_mean > 0
                else None
            )
            row: dict[str, Any] = {
                "sector_id": sector_id,
                "trade_date": trade_date,
                "sector_amount_vs_prior20": amount_value,
                "sector_amount_comparable_sum": comparable_sum,
                "sector_amount_prior20_mean": prior_mean,
                "member_amount_sum": member_sum if amount_valid_count else None,
                "amount_valid_count": amount_valid_count,
                "amount_target_member_count": target_count,
                "amount_comparable_member_count": comparable_count,
                "amount_comparable_coverage": current_coverage,
                "amount_window_coverage": window_coverage,
                "amount_window_target_member_max": target_count,
                "amount_target_denominator_source": "CURRENT_TARGET_MEMBERS",
                "amount_window_denominator_source": "MAX_H21_TARGET_MEMBERS",
                "amount_member_set_hash": _hash_members(valid_members),
                "amount_window_start": plan.history_dates[0] if plan.history_dates else None,
                "amount_window_end": plan.history_dates[-1] if plan.history_dates else trade_date,
                "amount_basis": "RECONSTRUCTED_FIXED_SNAPSHOT_COMMON_MEMBER_AGGREGATE",
                "amount_quality_codes": quality_codes,
                "amount_excluded_member_ids": sorted(target_members.difference(valid_members)),
                "amount_membership_snapshot_id": membership_snapshot_id,
                "amount_contract_id": CONTRACT_VERSION,
            }
            _comparison_for_fast_row(
                row, sector_id, trade_date, plan, fixed, state, sum_for,
                min_members, min_coverage,
            )
            rows.append(row)
    return pd.DataFrame(rows, columns=_sector_amount_columns())


def _comparison_for_fast_row(
    row: dict[str, Any],
    sector_id: str,
    trade_date: date,
    plan: SectorAmountWindowPlan,
    fixed: dict[str, frozenset[str]],
    state: Any,
    sum_for: Any,
    min_members: int,
    min_coverage: float,
) -> None:
    row.update({
        "amount_comparison_date": plan.comparison_date,
        "sector_amount_ratio_delta_3sessions_common": None,
        "amount_comparison_current_a": None,
        "amount_comparison_prior_a": None,
        "amount_comparison_current_sum": None,
        "amount_comparison_current_prior20_mean": None,
        "amount_comparison_prior_sum": None,
        "amount_comparison_prior_prior20_mean": None,
        "amount_comparison_member_set_hash": _hash_members(()),
        "amount_comparison_current_coverage": None,
        "amount_comparison_prior_coverage": None,
        "amount_comparison_window_coverage": None,
        "amount_comparison_window_start": plan.comparison_union_dates[0] if plan.comparison_union_dates else None,
        "amount_comparison_window_end": plan.comparison_union_dates[-1] if plan.comparison_union_dates else None,
        "amount_comparison_quality_codes": ["INSUFFICIENT_HISTORY"] if not plan.has_comparison_history else [],
        "amount_comparison_excluded_member_ids": [],
        "amount_comparison_evidence": {
            "comparison_date": plan.comparison_date,
            "quality_codes": ["INSUFFICIENT_HISTORY"] if not plan.has_comparison_history else [],
            "membership_snapshot_id": row.get("amount_membership_snapshot_id"),
        },
    })
    if not plan.has_comparison_history or plan.comparison_date is None:
        return
    current_members = set(fixed.get(sector_id, frozenset()))
    prior_members = current_members
    valid_members = {
        security_id
        for security_id in current_members
        if all(state(security_id, window_date)[0] for window_date in plan.comparison_union_dates)
    }
    sums = {window_date: sum_for(valid_members, window_date)[0] for window_date in plan.comparison_union_dates}
    comparable_count = len(valid_members)
    current_coverage = _coverage(comparable_count, len(current_members))
    prior_coverage = current_coverage
    window_coverage = current_coverage
    current_mean = sum(sums[window_date] for window_date in plan.prior_dates) / 20
    prior_mean = sum(sums[window_date] for window_date in plan.comparison_history_dates[:-1]) / 20
    current_sum = sums[trade_date]
    prior_sum = sums[plan.comparison_date]
    baseline_nonpositive = current_mean <= 0 or prior_mean <= 0
    codes = _quality_codes(
        has_history=True,
        membership_missing=False,
        invalid_amount=bool(current_members.difference(valid_members)),
        comparable_count=comparable_count,
        current_coverage=current_coverage,
        window_coverage=window_coverage,
        baseline_nonpositive=baseline_nonpositive,
        min_members=min_members,
        min_coverage=min_coverage,
    )
    current_a = None if current_mean <= 0 else current_sum / current_mean
    prior_a = None if prior_mean <= 0 else prior_sum / prior_mean
    row.update({
        "sector_amount_ratio_delta_3sessions_common": current_a - prior_a if not codes and current_a is not None and prior_a is not None else None,
        "amount_comparison_current_a": current_a if not codes else None,
        "amount_comparison_prior_a": prior_a if not codes else None,
        "amount_comparison_current_sum": current_sum,
        "amount_comparison_current_prior20_mean": current_mean,
        "amount_comparison_prior_sum": prior_sum,
        "amount_comparison_prior_prior20_mean": prior_mean,
        "amount_comparison_member_set_hash": _hash_members(valid_members),
        "amount_comparison_current_coverage": current_coverage,
        "amount_comparison_prior_coverage": prior_coverage,
        "amount_comparison_window_coverage": window_coverage,
        "amount_comparison_quality_codes": codes,
        "amount_comparison_excluded_member_ids": sorted(current_members.difference(valid_members)),
        "amount_comparison_evidence": {
            "comparison_date": plan.comparison_date,
            "current_a": current_a if not codes else None,
            "prior_a": prior_a if not codes else None,
            "current_sum": current_sum,
            "current_prior20_mean": current_mean,
            "prior_sum": prior_sum,
            "prior_prior20_mean": prior_mean,
            "member_set_hash": _hash_members(valid_members),
            "current_coverage": current_coverage,
            "prior_coverage": prior_coverage,
            "window_coverage": window_coverage,
            "quality_codes": codes,
            "membership_snapshot_id": row.get("amount_membership_snapshot_id"),
        },
    })


def _sector_amount_columns() -> list[str]:
    return [
        "sector_id", "trade_date", "sector_amount_vs_prior20", "sector_amount_comparable_sum",
        "sector_amount_prior20_mean", "member_amount_sum", "amount_valid_count",
        "amount_target_member_count", "amount_comparable_member_count", "amount_comparable_coverage",
        "amount_window_coverage", "amount_window_target_member_max", "amount_target_denominator_source",
        "amount_window_denominator_source", "amount_member_set_hash", "amount_window_start",
        "amount_window_end", "amount_basis", "amount_quality_codes", "amount_excluded_member_ids",
        "amount_membership_snapshot_id", "amount_contract_id", "amount_comparison_date",
        "sector_amount_ratio_delta_3sessions_common", "amount_comparison_current_a",
        "amount_comparison_prior_a", "amount_comparison_current_sum", "amount_comparison_current_prior20_mean",
        "amount_comparison_prior_sum", "amount_comparison_prior_prior20_mean", "amount_comparison_member_set_hash",
        "amount_comparison_current_coverage", "amount_comparison_prior_coverage", "amount_comparison_window_coverage",
        "amount_comparison_window_start", "amount_comparison_window_end", "amount_comparison_quality_codes",
        "amount_comparison_excluded_member_ids", "amount_comparison_evidence",
    ]


def build_sector_amount_daily(
    amounts: pd.DataFrame,
    memberships: pd.DataFrame,
    calendar: Sequence[Any],
    *,
    mode: str = OBSERVED,
    membership_snapshot: pd.DataFrame | None = None,
    membership_snapshot_id: str | None = None,
    cutoff: Any | None = None,
    target_dates: Sequence[Any] | None = None,
    min_comparable_members: int = DEFAULT_MIN_COMPARABLE_MEMBERS,
    min_comparable_coverage: float = DEFAULT_MIN_COMPARABLE_COVERAGE,
) -> pd.DataFrame:
    """Build independent sector amount rows for every available target date.

    ``OBSERVED`` intersects the dated membership sets across each H21 window.
    ``RECONSTRUCTED`` uses one fixed ``membership_snapshot`` (or the supplied
    ``memberships`` as that snapshot) for every date.  This function returns
    evidence even when a quality gate fails, but the formal ratio is NULL.
    """

    mode = str(mode).upper()
    if mode not in {OBSERVED, RECONSTRUCTED}:
        raise SectorAmountError("INVALID_MEMBERSHIP_MODE")
    if not isinstance(min_comparable_members, int) or min_comparable_members < 1:
        raise SectorAmountError("INVALID_MIN_COMPARABLE_MEMBERS")
    if not _finite(min_comparable_coverage) or not 0 < float(min_comparable_coverage) <= 1:
        raise SectorAmountError("INVALID_MIN_COMPARABLE_COVERAGE")
    calendar_dates = _calendar_dates(calendar)
    required_amount_columns = {"security_id", "trade_date", "raw_amount"}
    if not required_amount_columns.issubset(amounts.columns):
        missing = sorted(required_amount_columns.difference(amounts.columns))
        raise SectorAmountError("AMOUNT_INPUT_COLUMNS_MISSING:" + ",".join(missing))
    requested_dates = None if target_dates is None else {_as_date(value) for value in target_dates}
    if requested_dates is not None:
        missing_targets = sorted(requested_dates.difference(calendar_dates))
        if missing_targets:
            raise SectorAmountError("NO_CALENDAR:TARGET_NOT_FOUND")
        # Only the H21/24-session dates needed by requested targets are
        # materialised.  The calendar remains complete, so this is a storage
        # optimisation and cannot change a window, denominator, or quality
        # decision.
        needed_dates: set[date] = set()
        for requested in requested_dates:
            plan = plan_sector_amount_window(calendar_dates, requested)
            needed_dates.update(plan.history_dates)
            needed_dates.update(plan.comparison_union_dates)
        amount_input = amounts.copy()
        amount_input["trade_date"] = amount_input["trade_date"].map(_as_date)
        amount_input = amount_input[amount_input["trade_date"].isin(needed_dates)].copy()
    else:
        amount_input = amounts
    if mode == RECONSTRUCTED and requested_dates is not None:
        return _build_reconstructed_target_rows_fast(
            amount_input,
            memberships,
            calendar_dates,
            membership_snapshot=membership_snapshot,
            membership_snapshot_id=membership_snapshot_id,
            cutoff=cutoff,
            min_members=min_comparable_members,
            min_coverage=float(min_comparable_coverage),
            target_dates=requested_dates,
        )
    amount_frame = _normalise_amounts(amount_input, calendar_dates, cutoff)
    dated, fixed = _normalise_memberships(memberships, calendar_dates, mode, membership_snapshot)
    if mode == OBSERVED:
        target_date_set = requested_dates
        targets = sorted(
            (key for key in dated if target_date_set is None or key[1] in target_date_set),
            key=lambda item: (item[1], item[0]),
        )
    else:
        target_date_set = requested_dates
        targets = [
            (sector_id, trade_date)
            for trade_date in calendar_dates
            if target_date_set is None or trade_date in target_date_set
            for sector_id in sorted(fixed)
        ]
    rows: list[dict[str, Any]] = []
    for sector_id, trade_date in targets:
        plan = plan_sector_amount_window(calendar_dates, trade_date)
        row = _build_primary_row(
            sector_id=sector_id,
            trade_date=trade_date,
            plan=plan,
            amounts=amount_frame,
            dated=dated,
            fixed=fixed,
            mode=mode,
            min_members=min_comparable_members,
            min_coverage=float(min_comparable_coverage),
            membership_snapshot_id=membership_snapshot_id,
        )
        _comparison_for_row(
            row=row,
            sector_id=sector_id,
            trade_date=trade_date,
            plan=plan,
            amounts=amount_frame,
            dated=dated,
            fixed=fixed,
            mode=mode,
            min_members=min_comparable_members,
            min_coverage=float(min_comparable_coverage),
        )
        rows.append(row)
    columns = [
        "sector_id", "trade_date", "sector_amount_vs_prior20", "sector_amount_comparable_sum",
        "sector_amount_prior20_mean", "member_amount_sum", "amount_valid_count",
        "amount_target_member_count", "amount_comparable_member_count", "amount_comparable_coverage",
        "amount_window_coverage", "amount_window_target_member_max", "amount_target_denominator_source",
        "amount_window_denominator_source", "amount_member_set_hash", "amount_window_start",
        "amount_window_end", "amount_basis", "amount_quality_codes", "amount_excluded_member_ids",
        "amount_membership_snapshot_id",
        "amount_contract_id", "amount_comparison_date", "sector_amount_ratio_delta_3sessions_common",
        "amount_comparison_current_a", "amount_comparison_prior_a", "amount_comparison_current_sum",
        "amount_comparison_current_prior20_mean", "amount_comparison_prior_sum",
        "amount_comparison_prior_prior20_mean", "amount_comparison_member_set_hash",
        "amount_comparison_current_coverage", "amount_comparison_prior_coverage",
        "amount_comparison_window_coverage", "amount_comparison_window_start",
        "amount_comparison_window_end", "amount_comparison_quality_codes",
        "amount_comparison_excluded_member_ids", "amount_comparison_evidence",
    ]
    return pd.DataFrame(rows, columns=columns)
