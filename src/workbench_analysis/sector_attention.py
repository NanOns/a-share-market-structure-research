"""V3 P06 current-strength sector aggregation.

This is deliberately separate from the legacy sector-cycle rank: CURRENT is
an end-of-session member-quote fact, ranked only within normal sectors of the
same type.  It has no database side effects.
"""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from workbench_analysis.sector_amount import CONTRACT_VERSION as AMOUNT_CONTRACT_ID
from workbench_service.semantic import NORMAL_ATTRIBUTE, resolve_semantics


CONTRACT_ID = "SECTOR_CURRENT_PREVIEW_1"
POTENTIAL_CONTRACT_ID = "SECTOR_POTENTIAL_PREVIEW_1"
MEMBER_ROLE_CONTRACT_ID = "SECTOR_MEMBER_ROLES_PREVIEW_1"


class SectorAttentionError(ValueError):
    pass


def _finite(value: Any) -> bool:
    try:
        return value is not None and bool(np.isfinite(float(value)))
    except (TypeError, ValueError):
        return False


def _tri_all(checks: dict[str, bool | None]) -> bool | None:
    values = list(checks.values())
    if any(value is False for value in values):
        return False
    return True if values and all(value is True for value in values) else None


def _truth(value: Any) -> bool | None:
    if value is None or pd.isna(value):
        return None
    if isinstance(value, str):
        text = value.strip().upper()
        if text in {"TRUE", "1", "YES"}:
            return True
        if text in {"FALSE", "0", "NO"}:
            return False
        return None
    return bool(value)


def _sector_semantics(group: pd.DataFrame) -> tuple[str, bool]:
    """Resolve one immutable sector record; conflicting metadata fails closed."""
    fields = [column for column in ("sector_name", "sector_type", "sector_role", "semantic_bucket", "sector_valid") if column in group]
    if fields and any(group[column].nunique(dropna=False) > 1 for column in fields):
        raise SectorAttentionError("SECTOR_METADATA_CONFLICT:" + str(group["sector_id"].iloc[0]))
    record = group.iloc[0].to_dict()
    semantic = resolve_semantics(record)
    return str(record.get("sector_type") or "UNKNOWN").upper(), bool(semantic["normal_rank_eligible"])


def build_sector_current(
    members: pd.DataFrame,
    market_quotes: pd.DataFrame,
    config: dict[str, Any],
    *,
    amount_features: pd.DataFrame | None = None,
    comparison_features: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Aggregate fixed members and evaluate V3 CURRENT and independent W.

    ``market_quotes`` must be a unique all-A quote universe for the same
    session.  It is intentionally an explicit input: concatenating sector
    memberships would double-count stocks shared by sectors.
    """
    required = {"sector_id", "security_id", "trade_date", "ret1"}
    missing = sorted(required.difference(members.columns))
    if missing:
        raise SectorAttentionError("MEMBER_COLUMNS_MISSING:" + ",".join(missing))
    market_required = {"security_id", "trade_date", "ret1"}
    missing = sorted(market_required.difference(market_quotes.columns))
    if missing:
        raise SectorAttentionError("MARKET_COLUMNS_MISSING:" + ",".join(missing))
    source = members.copy()
    source["sector_id"] = source["sector_id"].astype(str)
    source["security_id"] = source["security_id"].astype(str)
    source["trade_date"] = pd.to_datetime(source["trade_date"], errors="raise").dt.date
    if source.duplicated(["sector_id", "security_id", "trade_date"]).any():
        raise SectorAttentionError("DUPLICATE_SECTOR_MEMBER_QUOTE")
    dates = source["trade_date"].unique()
    if len(dates) != 1:
        raise SectorAttentionError("CURRENT_REQUIRES_ONE_TRADE_DATE")
    trade_date = dates[0]
    market = market_quotes.copy()
    market["security_id"] = market["security_id"].astype(str)
    market["trade_date"] = pd.to_datetime(market["trade_date"], errors="raise").dt.date
    market = market[market["trade_date"].eq(trade_date)].copy()
    if market.empty or market.duplicated(["security_id", "trade_date"]).any():
        raise SectorAttentionError("MARKET_UNIVERSE_INVALID")
    thresholds = config["thresholds"]
    coverage_cfg = thresholds["coverage"]
    current_cfg = thresholds["current"]
    market_ret = pd.to_numeric(market["ret1"], errors="coerce")
    market_valid = market_ret.map(_finite)
    market_coverage = float(market_valid.mean()) if len(market) else None
    market_m1 = float(market_ret[market_valid].median()) if market_valid.any() else None
    market_ok = market_coverage is not None and market_coverage >= float(coverage_cfg["min_full_market_quote_coverage"])

    rows: list[dict[str, Any]] = []
    for sector_id, group in source.groupby("sector_id", sort=True):
        sector_type, normal = _sector_semantics(group)
        ret = pd.to_numeric(group["ret1"], errors="coerce")
        valid = ret.map(_finite)
        n = int(len(group))
        quote_count = int(valid.sum())
        quote_coverage = float(quote_count / n) if n else None
        m1 = float(ret[valid].median()) if quote_count else None
        b1 = float((ret[valid] > 0).mean()) if quote_count else None
        positive_count = int((ret[valid] > 0).sum()) if quote_count else 0
        rel1 = m1 - market_m1 if m1 is not None and market_m1 is not None else None
        rows.append({
            "sector_id": str(sector_id), "trade_date": trade_date, "sector_type": sector_type,
            "normal_rank_eligible": normal, "total_member_count": n,
            "quote_valid_count": quote_count, "quote_coverage": quote_coverage,
            "market_quote_coverage": market_coverage, "market_m1": market_m1,
            "m1": m1, "b1": b1, "rel1": rel1, "positive_count": positive_count,
            "top1_positive_share": None if not positive_count else float(ret[valid].clip(lower=0).max() / ret[valid].clip(lower=0).sum()),
        })
    result = pd.DataFrame(rows)
    result["p1"] = np.nan
    result["type_cross_section_coverage"] = np.nan
    for sector_type, indexes in result.groupby("sector_type", sort=False).groups.items():
        index = list(indexes)
        normal_mask = result.loc[index, "normal_rank_eligible"]
        total_normal = int(normal_mask.sum())
        valid_mask = normal_mask & result.loc[index, "rel1"].map(_finite)
        valid_count = int(valid_mask.sum())
        coverage = float(valid_count / total_normal) if total_normal else None
        result.loc[index, "type_cross_section_coverage"] = coverage
        if valid_count >= 5 and coverage is not None and coverage >= float(coverage_cfg["min_sector_cross_section_coverage"]):
            values = result.loc[index, "rel1"]
            ranks = values[valid_mask].rank(method="average", ascending=True) / valid_count
            result.loc[ranks.index, "p1"] = ranks
    if amount_features is not None:
        amount = amount_features.copy()
        required_amount = {"sector_id", "trade_date", "sector_amount_vs_prior20", "amount_contract_id"}
        missing = sorted(required_amount.difference(amount.columns))
        if missing:
            raise SectorAttentionError("AMOUNT_COLUMNS_MISSING:" + ",".join(missing))
        amount["sector_id"] = amount["sector_id"].astype(str)
        amount["trade_date"] = pd.to_datetime(amount["trade_date"], errors="raise").dt.date
        amount = amount[amount["trade_date"].eq(trade_date)]
        if amount.duplicated(["sector_id", "trade_date"]).any():
            raise SectorAttentionError("DUPLICATE_SECTOR_AMOUNT")
        amount["amount_A"] = amount["sector_amount_vs_prior20"].where(amount["amount_contract_id"].eq(AMOUNT_CONTRACT_ID))
        result = result.merge(amount[["sector_id", "amount_A"]], on="sector_id", how="left")
    else:
        result["amount_A"] = np.nan
    if comparison_features is not None:
        comparison = comparison_features.copy()
        required_comparison = {"sector_id", "trade_date", "b_delta3"}
        missing = sorted(required_comparison.difference(comparison.columns))
        if missing:
            raise SectorAttentionError("COMPARISON_COLUMNS_MISSING:" + ",".join(missing))
        comparison["sector_id"] = comparison["sector_id"].astype(str)
        comparison["trade_date"] = pd.to_datetime(comparison["trade_date"], errors="raise").dt.date
        comparison = comparison[comparison["trade_date"].eq(trade_date)]
        if comparison.duplicated(["sector_id", "trade_date"]).any():
            raise SectorAttentionError("DUPLICATE_SECTOR_COMPARISON")
        result = result.merge(comparison[["sector_id", "b_delta3"]], on="sector_id", how="left")
    else:
        result["b_delta3"] = np.nan

    checks_all: list[dict[str, dict[str, bool | None]]] = []
    current_values: list[bool | None] = []
    weak_values: list[bool | None] = []
    for row in result.itertuples(index=False):
        checks = {
            "NORMAL_ATTRIBUTE": bool(row.normal_rank_eligible),
            "MIN_MEMBERS": row.total_member_count >= int(coverage_cfg["min_sector_members"]),
            "QUOTE_COVERAGE": None if not _finite(row.quote_coverage) else row.quote_coverage >= float(coverage_cfg["min_member_quote_coverage"]),
            "MARKET_COVERAGE": market_ok,
            "TYPE_CROSS_SECTION": None if not _finite(row.type_cross_section_coverage) else row.type_cross_section_coverage >= float(coverage_cfg["min_sector_cross_section_coverage"]),
            "M1_POSITIVE": None if not _finite(row.m1) else row.m1 > float(current_cfg["m1_gt"]),
            "BREADTH": None if not _finite(row.b1) else row.b1 >= float(current_cfg["b1_gte"]),
            "RELATIVE_STRENGTH": None if not _finite(row.rel1) else row.rel1 >= float(current_cfg["rel1_gte"]),
            "P1": None if not _finite(row.p1) else row.p1 >= float(current_cfg["p1_gte"]),
            "MIN_POSITIVE_COUNT": row.positive_count >= int(current_cfg["min_positive_count"]),
            "NOT_SINGLE_STOCK_DRIVEN": None if not _finite(row.top1_positive_share) else row.top1_positive_share <= float(current_cfg["top1_positive_share_lte"]),
        }
        # The full-market reference is a publication gate, rather than one
        # ordinary rejection predicate.  Without it p1 is not an observable
        # fact, so no sector is allowed to be published as CURRENT (including
        # sectors that separately have a known negative member return).
        current = None if not market_ok else _tri_all(checks)
        weak_a = None if not _finite(row.m1) or not _finite(row.b1) else row.m1 < float(current_cfg["weak_m1_lt"]) and row.b1 < float(current_cfg["weak_b1_lt"])
        weak_b = None if not _finite(row.m1) or not _finite(row.b_delta3) else row.m1 < float(current_cfg["weak_m1_lt"]) and row.b_delta3 <= float(current_cfg["weak_b_delta3_lte"])
        weak = True if weak_a is True or weak_b is True else False if weak_a is False and weak_b is False else None
        checks_all.append({"CURRENT": checks, "W": {"NEGATIVE_NARROW_BREADTH": weak_a, "NEGATIVE_BREADTH_DELTA3": weak_b}})
        current_values.append(current)
        weak_values.append(weak)
    result["current"] = current_values
    result["weak"] = weak_values
    result["checks"] = checks_all
    result["reason_codes"] = [
        (["UNKNOWN_MARKET_COVERAGE"] if not market_ok else []) +
        [name for name, value in checks["CURRENT"].items() if value is False and not (name == "MARKET_COVERAGE" and not market_ok)] +
        ["UNKNOWN_" + name for name, value in checks["CURRENT"].items() if value is None]
        for checks in checks_all
    ]
    result["contract_id"] = CONTRACT_ID
    return result.sort_values(["current", "p1", "b1", "rel1", "amount_A", "sector_id"], ascending=[False, False, False, False, False, True], na_position="last", kind="mergesort").reset_index(drop=True)


def aggregate_early_width(member_signals: pd.DataFrame) -> pd.DataFrame:
    """Aggregate all member-level P05 signals without shortlist feedback."""
    required = {"sector_id", "security_id", "setup", "recovery", "extended", "close", "ma20"}
    missing = sorted(required.difference(member_signals.columns))
    if missing:
        raise SectorAttentionError("EARLY_WIDTH_COLUMNS_MISSING:" + ",".join(missing))
    source = member_signals.copy()
    if source.duplicated(["sector_id", "security_id"]).any():
        raise SectorAttentionError("EARLY_WIDTH_DUPLICATE_MEMBER")
    rows = []
    for sector_id, group in source.groupby("sector_id", sort=True):
        setup = group["setup"].map(_truth)
        recovery = group["recovery"].map(_truth)
        extended = group["extended"].map(_truth)
        position = group["close"].map(_finite) & group["ma20"].map(_finite)
        jointly_evaluable = setup.notna() & recovery.notna()
        setup_evaluable = setup.notna()
        risk_evaluable = extended.notna()
        early_hits = (setup.eq(True) | recovery.eq(True)) & jointly_evaluable
        rows.append({
            "sector_id": str(sector_id),
            "early_evaluable_count": int(jointly_evaluable.sum()),
            "early_count": int(early_hits.sum()),
            "early_width": float(early_hits.sum() / jointly_evaluable.sum()) if jointly_evaluable.any() else None,
            "setup_evaluable_count": int(setup_evaluable.sum()),
            "setup_count": int(setup.eq(True).sum()),
            "position_complete_count": int(position.sum()),
            "risk_evaluable_count": int(risk_evaluable.sum()),
            "extended_count": int(extended.eq(True).sum()),
            "extended_share": float(extended.eq(True).sum() / risk_evaluable.sum()) if risk_evaluable.any() else None,
        })
    return pd.DataFrame(rows)


def build_sector_potential(features: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    """Evaluate V3's three POTENTIAL branches from fixed, pre-aggregated facts.

    The caller supplies only current/previous common-member facts and a
    `prior_current_within10` trivalent history fact.  No old candidate, role,
    or card/shortlist output is accepted as an input.
    """
    required = {"sector_id", "current", "weak", "normal_rank_eligible", "total_member_count", "m1", "ma20_width", "extended_share", "risk_evaluable_count", "dq5_3", "b_delta3", "ma20_delta3", "early_width", "early_count", "amount_A", "q20", "setup_count", "setup_evaluable_count", "rel1", "prior_current_within10"}
    missing = sorted(required.difference(features.columns))
    if missing:
        raise SectorAttentionError("POTENTIAL_COLUMNS_MISSING:" + ",".join(missing))
    cfg = config["thresholds"]
    coverage = cfg["coverage"]
    common = cfg["potential_common"]
    branch = cfg["potential_branches"]
    records = []
    for row in features.to_dict("records"):
        def check(value: Any, predicate) -> bool | None:
            return predicate(float(value)) if _finite(value) else None
        risk_coverage = float(row["risk_evaluable_count"] / row["total_member_count"]) if _finite(row["risk_evaluable_count"]) and _finite(row["total_member_count"]) and float(row["total_member_count"]) else None
        base = {
            "NORMAL_ATTRIBUTE": bool(row["normal_rank_eligible"]),
            "MIN_MEMBERS": int(row["total_member_count"]) >= int(coverage["min_sector_members"]),
            "NON_CURRENT": False if _truth(row["current"]) is True else True if _truth(row["current"]) is False else None,
            "NOT_WEAK": False if _truth(row["weak"]) is True else True if _truth(row["weak"]) is False else None,
            "M1_FLOOR": check(row["m1"], lambda x: x >= common["m1_gte"]),
            "MA20_WIDTH_FLOOR": check(row["ma20_width"], lambda x: x >= common["ma20_width_gte"]),
            # No risk observations are unavailable evidence, not a known
            # unsafe population.  A nonzero but sub-threshold coverage is a
            # known insufficient sample and remains a false common gate.
            "RISK_COVERAGE": None if risk_coverage is None or risk_coverage == 0 else check(risk_coverage, lambda x: x >= coverage["min_risk_coverage"]),
            "NOT_MAJORITY_EXTENDED": None if risk_coverage is None or risk_coverage == 0 else check(row["extended_share"], lambda x: x <= common["extended_member_share_lte"]),
        }
        breadth = {**base,
            "DQ5_3": check(row["dq5_3"], lambda x: x >= branch["BREADTH_BUILD"]["dq5_3_gte"]),
            "B_DELTA3": check(row["b_delta3"], lambda x: x >= branch["BREADTH_BUILD"]["b_delta3_gte"]),
            "MA20_DELTA3": check(row["ma20_delta3"], lambda x: x >= branch["BREADTH_BUILD"]["ma20_delta3_gte"]),
            "EARLY_WIDTH": check(row["early_width"], lambda x: x >= branch["BREADTH_BUILD"]["early_width_gte"]),
            "EARLY_COUNT": int(row["early_count"]) >= int(common["min_early_watch_count"]),
            "AMOUNT_A": check(row["amount_A"], lambda x: x >= branch["BREADTH_BUILD"]["amount_A_gte"])}
        setup_minimum = max(int(branch["BASE_BUILD"]["setup_count_min"]), int(np.ceil(branch["BASE_BUILD"]["setup_count_ratio"] * float(row["setup_evaluable_count"])))) if _finite(row["setup_evaluable_count"]) else None
        base_build = {**base,
            "Q20": check(row["q20"], lambda x: x >= branch["BASE_BUILD"]["q20_gte"]),
            "MA20_WIDTH": check(row["ma20_width"], lambda x: x >= branch["BASE_BUILD"]["ma20_width_gte"]),
            "MA20_DELTA3": check(row["ma20_delta3"], lambda x: x >= branch["BASE_BUILD"]["ma20_delta3_gte"]),
            "SETUP_COUNT": None if setup_minimum is None else int(row["setup_count"]) >= setup_minimum,
            "AMOUNT_A_RANGE": check(row["amount_A"], lambda x: branch["BASE_BUILD"]["amount_A_min"] <= x <= branch["BASE_BUILD"]["amount_A_max"]),
            "B_DELTA3": check(row["b_delta3"], lambda x: x >= branch["BASE_BUILD"]["b_delta3_gte"])}
        recovery = {**base,
            "PRIOR_CURRENT": _truth(row["prior_current_within10"]),
            "REL1": check(row["rel1"], lambda x: x > branch["RECOVERY_BUILD"]["rel1_gt"]),
            "B_DELTA3": check(row["b_delta3"], lambda x: x >= branch["RECOVERY_BUILD"]["b_delta3_gte"]),
            "MA20_DELTA3": check(row["ma20_delta3"], lambda x: x >= branch["RECOVERY_BUILD"]["ma20_delta3_gte"]),
            "AMOUNT_A": check(row["amount_A"], lambda x: x >= branch["RECOVERY_BUILD"]["amount_A_gte"]),
            "SETUP_OR_RECOVERY_COUNT": int(row["early_count"]) >= int(branch["RECOVERY_BUILD"]["recovery_or_setup_count_min"])}
        branches = {"BREADTH_BUILD": _tri_all(breadth), "BASE_BUILD": _tri_all(base_build), "RECOVERY_BUILD": _tri_all(recovery)}
        eligible = True if any(value is True for value in branches.values()) else False if all(value is False for value in branches.values()) else None
        primary = next((name for name in ("RECOVERY_BUILD", "BREADTH_BUILD", "BASE_BUILD") if branches[name] is True), None)
        records.append({**row, "risk_coverage": risk_coverage, "potential_eligible": eligible, "primary_branch": primary, "branch_checks": {"BREADTH_BUILD": breadth, "BASE_BUILD": base_build, "RECOVERY_BUILD": recovery}, "branch_results": branches, "contract_id": POTENTIAL_CONTRACT_ID})
    return pd.DataFrame(records)


def progress_potential_episode(sequence: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    """Advance one sector's potential episode without looking ahead.

    Rows must be one master-calendar session each.  A missing qualification is
    DATA_GAP, not a false observation; its age still advances.  The returned
    signal fields are only the state known on that row, so future confirmation
    cannot rewrite the first signal.
    """
    required = {"trade_date", "potential_eligible", "current", "weak", "ma20_width", "extended_share", "risk_coverage"}
    missing = sorted(required.difference(sequence.columns))
    if missing:
        raise SectorAttentionError("EPISODE_COLUMNS_MISSING:" + ",".join(missing))
    source = sequence.copy().sort_values("trade_date", kind="mergesort").reset_index(drop=True)
    if source["trade_date"].duplicated().any():
        raise SectorAttentionError("EPISODE_DUPLICATE_TRADE_DATE")
    common = config["thresholds"]["potential_common"]
    output: list[dict[str, Any]] = []
    active = False
    first_seen = None
    last_qualified = None
    age = 0
    monitor_used = False
    episode_no = 0
    prior_episode = False
    nonhit = 0
    for row in source.to_dict("records"):
        date_value = str(row["trade_date"])
        eligible = _truth(row["potential_eligible"])
        current = _truth(row["current"])
        weak = _truth(row["weak"])
        risk_coverage = row.get("risk_coverage")
        invalid_reason = None
        if weak is True:
            invalid_reason = "W"
        elif _finite(row.get("ma20_width")) and float(row["ma20_width"]) < .35:
            invalid_reason = "MA20_WIDTH_BELOW_035"
        elif _finite(risk_coverage) and float(risk_coverage) >= config["thresholds"]["coverage"]["min_risk_coverage"] and _finite(row.get("extended_share")) and float(row["extended_share"]) > common["extended_member_share_lte"]:
            invalid_reason = "MAJORITY_EXTENDED"
        state = None
        end_reason = None
        if not active:
            if eligible is True and (not prior_episode or nonhit >= int(common["min_reset_nonhit_sessions"])):
                active = True
                prior_episode = True
                nonhit = 0
                episode_no += 1
                first_seen = date_value
                last_qualified = date_value
                age = 1
                monitor_used = False
                state = "CONFIRMED" if current is True else "QUALIFIED"
            elif eligible is None:
                state = "DATA_GAP"
            else:
                nonhit += 1
                state = "NO_EPISODE"
        else:
            age += 1
            if current is True:
                state, end_reason, active = "CONFIRMED", "CURRENT_CONFIRMED", False
                nonhit = 0
            elif invalid_reason:
                state, end_reason, active = "INVALIDATED", invalid_reason, False
                nonhit = 0
            elif eligible is None:
                state = "DATA_GAP"
            elif eligible is False:
                if age >= int(config["windows"]["lifecycle_max_sessions"]):
                    state, end_reason, active = "EXPIRED", "MAX_AGE_5", False
                    nonhit = 0
                elif not monitor_used:
                    state, monitor_used = "MONITORING", True
                else:
                    state, end_reason, active = "CONDITION_LOST", "SECOND_NONHIT", False
                    nonhit = 0
            else:
                state = "QUALIFIED"
                last_qualified = date_value
                monitor_used = False
        output.append({
            "trade_date": date_value, "state": state, "episode_no": episode_no if (active or state not in {"NO_EPISODE", "DATA_GAP"}) else None,
            "first_seen_date": first_seen, "last_qualified_date": last_qualified,
            "age_sessions": age if (active or state in {"QUALIFIED", "MONITORING", "DATA_GAP", "CONDITION_LOST", "EXPIRED", "INVALIDATED", "CONFIRMED"}) else 0,
            "end_reason": end_reason, "potential_eligible": eligible, "current": current,
        })
    return pd.DataFrame(output)


def build_sector_member_roles(
    members: pd.DataFrame,
    sector_states: pd.DataFrame,
    config: dict[str, Any],
) -> pd.DataFrame:
    """Assign P07-01 roles from a complete fixed member set.

    The function returns ALL_MEMBERS for query-time pagination plus only
    eligible rows for the three compact roles.  It never substitutes a
    long-term rank for today's quote rank and never backfills a missing early
    member with a historical leader.
    """
    required = {"sector_id", "security_id", "ret1", "amount_vs_prior20", "rps5_delta3", "bias20", "extended", "structure_break", "position_complete", "liquidity20", "breakout", "recovery", "setup"}
    missing = sorted(required.difference(members.columns))
    if missing:
        raise SectorAttentionError("ROLE_MEMBER_COLUMNS_MISSING:" + ",".join(missing))
    if "sector_id" not in sector_states.columns:
        raise SectorAttentionError("ROLE_STATE_SECTOR_ID_REQUIRED")
    state_columns = [column for column in ("sector_id", "current", "potential_eligible", "potential_state") if column in sector_states.columns]
    states = sector_states[state_columns].drop_duplicates("sector_id")
    source = members.copy().merge(states, on="sector_id", how="left", validate="many_to_one")
    if source.duplicated(["sector_id", "security_id"]).any():
        raise SectorAttentionError("ROLE_DUPLICATE_SECTOR_MEMBER")
    source["sector_id"] = source["sector_id"].astype(str)
    source["security_id"] = source["security_id"].astype(str)
    limits = config["thresholds"]["roles"]
    records: list[dict[str, Any]] = []
    for sector_id, group in source.groupby("sector_id", sort=True):
        group = group.copy()
        ret = pd.to_numeric(group["ret1"], errors="coerce")
        valid = ret.map(_finite)
        quote_count = int(valid.sum())
        member_count = int(len(group))
        today_rank = pd.Series(np.nan, index=group.index, dtype="float64")
        if quote_count:
            today_rank.loc[valid] = ret[valid].rank(method="average", ascending=False)
        percentile = pd.Series(np.nan, index=group.index, dtype="float64")
        if quote_count:
            percentile.loc[valid] = (quote_count - today_rank.loc[valid] + 1) / quote_count
        group["_today_rank"] = today_rank
        group["_today_percentile"] = percentile
        group["_current"] = group["current"].map(_truth) if "current" in group else None
        group["_potential"] = group["potential_eligible"].map(_truth) if "potential_eligible" in group else None
        group["_today_ok"] = valid & ret.gt(0) & percentile.ge(float(limits["TODAY_LEADER"]["board_percentile_gte"]))
        group["_current_ok"] = (
            group["_current"].eq(True) &
            (group["breakout"].map(_truth).eq(True) | group["recovery"].map(_truth).eq(True)) &
            group["structure_break"].map(_truth).eq(False) &
            group["position_complete"].map(_truth).eq(True) &
            group["extended"].map(_truth).eq(False)
        )
        group["_early_ok"] = (
            group["_potential"].eq(True) &
            (group["setup"].map(_truth).eq(True) | group["recovery"].map(_truth).eq(True)) &
            group["structure_break"].map(_truth).eq(False) &
            group["position_complete"].map(_truth).eq(True) &
            group["extended"].map(_truth).eq(False)
        )
        common = {"sector_id": str(sector_id), "member_count": member_count, "quote_valid_count": quote_count, "contract_id": MEMBER_ROLE_CONTRACT_ID}
        all_sorted = group.assign(_ret=ret).sort_values(["_ret", "security_id"], ascending=[False, True], na_position="last", kind="mergesort")
        for rank, (_, row) in enumerate(all_sorted.iterrows(), start=1):
            records.append({**common, "security_id": str(row["security_id"]), "role": "ALL_MEMBERS", "role_rank": rank, "today_rank": None if pd.isna(row["_today_rank"]) else int(row["_today_rank"]), "role_reason_codes": ["BOUND_MEMBER", "QUOTE_UNKNOWN" if pd.isna(row["_today_rank"]) else "TODAY_QUOTE"], "evidence": {"ret1": None if pd.isna(row["ret1"]) else float(row["ret1"])}})
        role_specs = {
            "TODAY_LEADER": ("_today_ok", ["_today_percentile", "ret1", "amount_vs_prior20", "security_id"], [False, False, False, True]),
            "CURRENT_RESEARCH": ("_current_ok", ["breakout", "amount_vs_prior20", "rps5_delta3", "security_id"], [False, False, False, True]),
            "EARLY_WATCH": ("_early_ok", ["setup", "rps5_delta3", "bias20", "amount_vs_prior20", "security_id"], [False, False, False, False, True]),
        }
        for role, (mask_name, sort_columns, ascending) in role_specs.items():
            candidates = group[group[mask_name]].copy()
            if role == "TODAY_LEADER":
                candidates = candidates.sort_values(sort_columns, ascending=ascending, na_position="last", kind="mergesort")
            elif role == "CURRENT_RESEARCH":
                candidates = candidates.sort_values(sort_columns, ascending=ascending, na_position="last", kind="mergesort")
            else:
                candidates["_abs_bias"] = pd.to_numeric(candidates["bias20"], errors="coerce").abs()
                candidates = candidates.sort_values(["setup", "rps5_delta3", "_abs_bias", "amount_vs_prior20", "security_id"], ascending=[False, False, False, False, True], na_position="last", kind="mergesort")
            preview_limit = int(limits[role]["preview_limit"])
            for rank, (_, row) in enumerate(candidates.head(preview_limit).iterrows(), start=1):
                reason = ["ROLE_ELIGIBLE", role]
                if _truth(row.get("extended")) is True:
                    reason.append("EXTENDED_FACT_ONLY")
                records.append({**common, "security_id": str(row["security_id"]), "role": role, "role_rank": rank, "today_rank": None if pd.isna(row["_today_rank"]) else int(row["_today_rank"]), "role_reason_codes": reason, "evidence": {"ret1": None if pd.isna(row["ret1"]) else float(row["ret1"]), "breakout": _truth(row.get("breakout")), "recovery": _truth(row.get("recovery")), "setup": _truth(row.get("setup")), "extended": _truth(row.get("extended"))}})
    return pd.DataFrame(records)


__all__ = ["CONTRACT_ID", "POTENTIAL_CONTRACT_ID", "MEMBER_ROLE_CONTRACT_ID", "SectorAttentionError", "aggregate_early_width", "build_sector_current", "build_sector_potential", "build_sector_member_roles", "progress_potential_episode"]
