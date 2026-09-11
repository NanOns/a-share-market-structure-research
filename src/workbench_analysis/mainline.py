"""M10 deterministic mainline state classification.

The classifier is deliberately tri-state: a missing required input is UNKNOWN,
never False.  It emits every predicate and the conflict explanation so the
published class can be audited without a hidden score.
"""

from __future__ import annotations

import json
import hashlib
import math
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping

import pandas as pd


CONTRACT_VERSION = "MAINLINE_STATE_V2_3_PREVIEW"
FORMAL_CONTRACT_VERSION = "MAINLINE_STATE_V2_4_PREVIEW"
SUPPORTED_CONTRACTS = frozenset({CONTRACT_VERSION, FORMAL_CONTRACT_VERSION})
HISTORY_BASIS = "RECONSTRUCTED"
COMPARISON_EPSILON = 1e-12
DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[2] / "config/mainline-v2.3-preview.yaml"
_DEFAULT_CONFIG_CACHE: dict[str, Any] | None = None


class MainlineError(ValueError):
    pass


def _finite(value: Any) -> bool:
    try:
        return value is not None and math.isfinite(float(value))
    except (TypeError, ValueError):
        return False


def _number(value: Any) -> float | None:
    return float(value) if _finite(value) else None


def _tri_all(values: list[bool | None]) -> bool | None:
    if not values:
        return None
    if any(value is False for value in values):
        return False
    return None if any(value is None for value in values) else True


def _tri_any(values: list[bool | None]) -> bool | None:
    if not values:
        return None
    if any(value is True for value in values):
        return True
    return None if any(value is None for value in values) else False


def _comparison(current: float | None, previous: float | None, threshold: float, direction: str) -> bool | None:
    if current is None or previous is None:
        return None
    delta = current - previous
    return delta >= threshold - COMPARISON_EPSILON if direction == "up" else delta <= threshold + COMPARISON_EPSILON


def _strictly_down(current: float | None, previous: float | None, epsilon: float) -> bool | None:
    if current is None or previous is None:
        return None
    return current - previous < -epsilon


def _load_config(config: Mapping[str, Any] | str | Path | None) -> dict[str, Any]:
    global _DEFAULT_CONFIG_CACHE
    if config is None:
        if _DEFAULT_CONFIG_CACHE is None:
            with DEFAULT_CONFIG_PATH.open("r", encoding="utf-8") as handle:
                _DEFAULT_CONFIG_CACHE = json.load(handle)
        value = deepcopy(_DEFAULT_CONFIG_CACHE)
    elif isinstance(config, Mapping):
        value = dict(config)
    else:
        with Path(config).open("r", encoding="utf-8") as handle:
            value = json.load(handle)
    if not isinstance(value, dict) or value.get("contract_id") not in SUPPORTED_CONTRACTS:
        raise MainlineError("MAINLINE_CONFIG_CONTRACT_UNSUPPORTED")
    thresholds = value.get("thresholds")
    classes = value.get("classes")
    if not isinstance(thresholds, dict) or not isinstance(classes, list):
        raise MainlineError("MAINLINE_CONFIG_INVALID")
    value["thresholds"] = {str(key): float(raw) for key, raw in thresholds.items()}
    value["classes"] = [str(item) for item in classes]
    return value


def config_hash(config: Mapping[str, Any] | str | Path | None = None) -> str:
    value = _load_config(config)
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def mainline_history_policy(config: Mapping[str, Any] | str | Path | None = None) -> dict[str, float | int]:
    cfg = _load_config(config)
    threshold = cfg["thresholds"]
    return {
        "observation_min": int(threshold["observation_minimum_valid_observations"]),
        "fast_min": int(threshold["fast_minimum_valid_observations"]),
        "stable_min": int(threshold["stable_minimum_valid_observations"]),
        "long_evidence_min": int(threshold["long_evidence_valid_observations"]),
        "coverage_min": float(threshold["current_coverage_min"]),
        "new_prior_window_days": int(threshold["new_prior_window_days"]),
    }


def _normalise_cycle(cycle: pd.DataFrame) -> pd.DataFrame:
    required = {
        "sector_id", "trade_date", "sector_rs20_pct", "coverage",
        "breadth_ret1_common", "breadth_ret1_common_change_1d", "breadth_ret1_common_change_3d",
    }
    missing = sorted(required - set(cycle.columns))
    if missing:
        raise MainlineError("SECTOR_CYCLE_COLUMNS_MISSING:" + ",".join(missing))
    result = cycle.copy()
    result["sector_id"] = result["sector_id"].astype(str)
    result["trade_date"] = pd.to_datetime(result["trade_date"], errors="raise").dt.date
    if result.duplicated(["sector_id", "trade_date"]).any():
        raise MainlineError("SECTOR_CYCLE_DUPLICATE_SECTOR_DATE")
    for column in (
        "sector_rs20_pct", "coverage", "breadth_ret1", "breadth_ret1_common",
        "breadth_ret1_common_change_1d", "breadth_ret1_common_change_3d", "amount_vs_prior20",
        "sector_amount_vs_prior20", "sector_amount_ratio_delta_3sessions_common",
    ):
        if column not in result:
            result[column] = None
        result[column] = pd.to_numeric(result[column], errors="coerce")
    return result.sort_values(["sector_id", "trade_date"], kind="mergesort").reset_index(drop=True)


def _normalise_members(member_states: pd.DataFrame | None) -> pd.DataFrame:
    if member_states is None or member_states.empty:
        return pd.DataFrame(columns=["sector_id", "trade_date", "strong_state", "member_change_kind"])
    required = {"sector_id", "trade_date"}
    missing = sorted(required - set(member_states.columns))
    if missing:
        raise MainlineError("MEMBER_STATE_COLUMNS_MISSING:" + ",".join(missing))
    result = member_states.copy()
    result["sector_id"] = result["sector_id"].astype(str)
    result["trade_date"] = pd.to_datetime(result["trade_date"], errors="raise").dt.date
    if "strong_state" not in result:
        result["strong_state"] = None
    if "member_change_kind" not in result:
        result["member_change_kind"] = None
    return result


def _member_metrics(member_states: pd.DataFrame, sector_id: str, current_date: Any, previous_date: Any) -> dict[str, Any]:
    current = member_states[(member_states.sector_id == sector_id) & (member_states.trade_date == current_date)]
    previous = member_states[(member_states.sector_id == sector_id) & (member_states.trade_date == previous_date)]
    if current.empty or previous.empty:
        return {"retention_rate": None, "entered_count": None, "exited_count": None, "member_comparable": None}

    # Retention is defined on the common membership set C, not on all
    # previous strong members.  A removed previous member is not comparable
    # on the current date and must therefore not depress the denominator.
    if "security_id" not in current.columns or "security_id" not in previous.columns:
        raise MainlineError("MEMBER_STATE_COLUMNS_MISSING:security_id")
    current_present = current if "member_present" not in current.columns else current[current["member_present"].eq(True)]
    previous_present = previous if "member_present" not in previous.columns else previous[previous["member_present"].eq(True)]
    current_by_security = current_present.drop_duplicates("security_id", keep="last").set_index("security_id")
    previous_by_security = previous_present.drop_duplicates("security_id", keep="last").set_index("security_id")
    common_ids = sorted(set(current_by_security.index) & set(previous_by_security.index))
    current_common = current_by_security.loc[common_ids] if common_ids else current_by_security.iloc[0:0]
    previous_common = previous_by_security.loc[common_ids] if common_ids else previous_by_security.iloc[0:0]
    current_strong = current_common["strong_state"].map(lambda value: value if isinstance(value, bool) else None)
    previous_strong = previous_common["strong_state"].map(lambda value: value if isinstance(value, bool) else None)
    previous_all_strong = previous_by_security["strong_state"].map(lambda value: value if isinstance(value, bool) else None)
    comparable = current_strong.notna() & previous_strong.notna()
    comparable_previous_strong = int((comparable & previous_strong.eq(True)).sum())
    retained = int((comparable & current_strong.eq(True) & previous_strong.eq(True)).sum())
    retention = retained / comparable_previous_strong if comparable_previous_strong else None
    entered = current["member_change_kind"].eq("ENTERED")
    exited = current["member_change_kind"].eq("EXITED")
    return {
        "retention_rate": retention,
        "entered_count": int(entered.sum()),
        "exited_count": int(exited.sum()),
        "member_comparable": bool(comparable.all()) if common_ids else None,
    }


def _window_metrics(values: list[float | None], threshold: float) -> tuple[dict[str, int | None], int | None]:
    known = [value for value in values if value is not None]
    counts: dict[str, int | None] = {}
    for width in (5, 10, 20, 30):
        window = values[-width:]
        counts[str(width)] = (
            int(sum(value >= threshold for value in window))
            if len(values) >= width and all(value is not None for value in window)
            else None
        )
    consecutive = 0
    for value in reversed(values):
        if value is None:
            break
        if value >= threshold:
            consecutive += 1
        else:
            break
    return counts, consecutive if known else None


def classify_mainline_row(
    history: pd.DataFrame,
    *,
    member_states: pd.DataFrame | None = None,
    config: Mapping[str, Any] | str | Path | None = None,
) -> dict[str, Any]:
    """Classify the latest row of one sector history with tri-state predicates."""
    cycle = _normalise_cycle(history)
    if cycle.empty:
        raise MainlineError("MAINLINE_HISTORY_EMPTY")
    cfg = _load_config(config)
    cfg_hash = config_hash(config)
    threshold = cfg["thresholds"]
    sector_id = str(cycle.iloc[-1]["sector_id"])
    dates = list(cycle["trade_date"])
    percentiles = [_number(value) for value in cycle["sector_rs20_pct"]]
    breadth = [_number(value) for value in cycle["breadth_ret1_common"]]
    formal_amount = cfg["contract_id"] == FORMAL_CONTRACT_VERSION
    amounts = [
        _number(value)
        for value in (cycle["sector_amount_vs_prior20"] if formal_amount else cycle["amount_vs_prior20"])
    ]
    amount_deltas = [_number(value) for value in cycle["sector_amount_ratio_delta_3sessions_common"]]
    current = cycle.iloc[-1]
    current_p = percentiles[-1]
    current_b = breadth[-1]
    current_a = amounts[-1]
    comparison_index = max(0, len(cycle) - 1 - int(threshold["comparison_days"]))
    prior_p = percentiles[comparison_index] if len(cycle) > int(threshold["comparison_days"]) else None
    prior_a = amounts[comparison_index] if len(cycle) > int(threshold["comparison_days"]) else None
    current_amount_delta = amount_deltas[-1] if formal_amount else (
        None if prior_a is None or current_a is None else current_a - prior_a
    )
    current_b_change_1d = _number(current.get("breadth_ret1_common_change_1d"))
    current_b_change_3d = _number(current.get("breadth_ret1_common_change_3d"))
    on_list, consecutive = _window_metrics(percentiles, threshold["percentile_listed"])
    members = _normalise_members(member_states)
    metrics = _member_metrics(members, sector_id, dates[-1], dates[-2] if len(dates) > 1 else None)
    predicates: dict[str, bool | None] = {}
    missing: list[str] = []
    valid_observations = len([value for value in percentiles if value is not None])
    observation_ok = valid_observations >= int(threshold["observation_minimum_valid_observations"])
    fast_history_ok = valid_observations >= int(threshold["fast_minimum_valid_observations"])
    stable_history_ok = valid_observations >= int(threshold["stable_minimum_valid_observations"])
    coverage_ok = _number(current.get("coverage"))
    predicates["history_minimum_3_observations"] = observation_ok
    predicates["history_minimum_5_observations"] = fast_history_ok
    predicates["history_minimum_10_observations"] = stable_history_ok
    predicates["current_coverage_ge_080"] = None if coverage_ok is None else coverage_ok >= threshold["current_coverage_min"]
    if not observation_ok:
        missing.append("sector_rs20_pct_3_observations")
    if not fast_history_ok:
        missing.append("sector_rs20_pct_5_observations")
    if not stable_history_ok:
        missing.append("sector_rs20_pct_10_observations")
    if predicates["current_coverage_ge_080"] is not True:
        missing.append("coverage")
    fading_history = percentiles[-(int(threshold["fading_lookback_days"]) + 1):-1]
    predicates["fading_was_listed"] = (
        any(value is not None and value >= threshold["percentile_listed"] for value in fading_history)
        if fading_history
        else None
    )
    predicates["fading_current_below_060"] = None if current_p is None else current_p < threshold["percentile_fading"]
    predicates["fading_percentile_delta_le_neg_015"] = _comparison(current_p, prior_p, threshold["fading_percentile_delta_max"], "down")
    fading_decline_epsilon = float(threshold["fading_decline_epsilon"])
    predicates["fading_breadth_declined"] = None if current_b_change_3d is None else current_b_change_3d < -fading_decline_epsilon
    predicates["fading_amount_declined"] = (
        None if current_amount_delta is None else current_amount_delta < -fading_decline_epsilon
    ) if formal_amount else _strictly_down(current_a, prior_a, fading_decline_epsilon)
    predicates["fading"] = _tri_all([
        predicates["fading_was_listed"],
        predicates["fading_current_below_060"],
        predicates["fading_percentile_delta_le_neg_015"],
        predicates["fading_breadth_declined"],
        predicates["fading_amount_declined"],
    ])

    predicates["contraction_current_ge_080"] = None if current_p is None else current_p >= threshold["percentile_listed"]
    predicates["contraction_breadth_declined"] = None if current_b_change_3d is None else current_b_change_3d <= threshold["contraction_breadth_delta_max"] + COMPARISON_EPSILON
    predicates["contraction_retention_lt_050"] = None if metrics["retention_rate"] is None else metrics["retention_rate"] < threshold["contraction_retention_max"]
    predicates["high_level_contraction"] = _tri_all([predicates["contraction_current_ge_080"], _tri_any([predicates["contraction_breadth_declined"], predicates["contraction_retention_lt_050"]])])

    predicates["reaccelerating_on_list_10_ge_3"] = None if on_list["10"] is None else on_list["10"] >= threshold["reaccelerating_on_list_10_min"]
    predicates["reaccelerating_current_ge_080"] = predicates["contraction_current_ge_080"]
    predicates["reaccelerating_percentile_improved"] = _comparison(current_p, prior_p, threshold["reaccelerating_percentile_delta_min"], "up")
    predicates["reaccelerating_breadth_improved"] = None if current_b_change_3d is None else current_b_change_3d >= threshold["reaccelerating_breadth_delta_min"] - COMPARISON_EPSILON
    predicates["reaccelerating_amount_ge_120"] = None if current_a is None else current_a >= threshold["reaccelerating_amount_min"]
    predicates["reaccelerating"] = _tri_all([
        predicates["reaccelerating_on_list_10_ge_3"],
        predicates["reaccelerating_current_ge_080"],
        predicates["reaccelerating_percentile_improved"],
        predicates["reaccelerating_breadth_improved"],
        predicates["reaccelerating_amount_ge_120"],
    ])

    predicates["sustained_on_list_5_ge_3"] = None if on_list["5"] is None else on_list["5"] >= threshold["sustained_on_list_5_min"]
    predicates["sustained_consecutive_ge_2"] = None if consecutive is None else consecutive >= threshold["sustained_consecutive_min"]
    predicates["sustained_current_ge_080"] = predicates["contraction_current_ge_080"]
    predicates["sustained_breadth_ge_050"] = None if current_b is None else current_b >= threshold["sustained_breadth_min"]
    predicates["sustained_retention_ge_060"] = None if metrics["retention_rate"] is None else metrics["retention_rate"] >= threshold["sustained_retention_min"]
    predicates["sustained"] = _tri_all([
        predicates["sustained_on_list_5_ge_3"],
        predicates["sustained_consecutive_ge_2"],
        predicates["sustained_current_ge_080"],
        predicates["sustained_breadth_ge_050"],
        predicates["sustained_retention_ge_060"],
    ])

    predicates["new_current_ge_080"] = predicates["contraction_current_ge_080"]
    prior_window_days = int(threshold["new_prior_window_days"])
    recent_prior = percentiles[-(prior_window_days + 1):-1]
    predicates["new_prior_on_list_5_le_1"] = (
        None
        if on_list["5"] is None
        else sum(value is not None and value >= threshold["percentile_listed"] for value in recent_prior)
        <= threshold["new_prior_on_list_5_max"]
    )
    predicates["new_breadth_ge_055"] = None if current_b is None else current_b >= threshold["new_breadth_min"]
    predicates["new_amount_ge_110"] = None if current_a is None else current_a >= threshold["new_amount_min"]
    predicates["new_entered_gt_exited"] = None if metrics["entered_count"] is None or metrics["exited_count"] is None else metrics["entered_count"] > metrics["exited_count"]
    predicates["new"] = _tri_all([
        predicates["new_current_ge_080"],
        predicates["new_prior_on_list_5_le_1"],
        predicates["new_breadth_ge_055"],
        predicates["new_amount_ge_110"],
        predicates["new_entered_gt_exited"],
    ])

    predicates["broadening_current_ge_070"] = None if current_p is None else current_p >= threshold["percentile_broadening"]
    predicates["broadening_entered_gt_exited"] = predicates["new_entered_gt_exited"]
    predicates["broadening_breadth_improved"] = None if current_b_change_1d is None else current_b_change_1d >= threshold["broadening_breadth_delta_min"] - COMPARISON_EPSILON
    predicates["broadening"] = _tri_all([
        predicates["broadening_current_ge_070"],
        predicates["broadening_entered_gt_exited"],
        predicates["broadening_breadth_improved"],
    ])

    states = [("FADING", predicates["fading"]), ("HIGH_LEVEL_CONTRACTION", predicates["high_level_contraction"]), ("REACCELERATING", predicates["reaccelerating"]), ("SUSTAINED", predicates["sustained"]), ("NEW", predicates["new"]), ("BROADENING", predicates["broadening"])]
    # REACCELERATING has an explicit 10-day predicate.  It must not be treated
    # as an unknown higher-priority state during the 5-9 day fast tier, or it
    # would incorrectly block NEW/BROADENING.
    fast_states = [(name, value) for name, value in states if name in {"NEW", "BROADENING"}]
    stable_states = states
    eligible_states = stable_states if stable_history_ok else fast_states if fast_history_ok else []
    true_state = next((name for name, state in eligible_states if state is True), None)
    true_index = next((index for index, (_, state) in enumerate(eligible_states) if state is True), None)
    unknown_before_true = [name for index, (name, state) in enumerate(eligible_states) if state is None and (true_index is None or index < true_index)]
    if not observation_ok or predicates["current_coverage_ge_080"] is not True:
        mainline_class = "DATA_INSUFFICIENT"
        conflict = "OBSERVATION_HISTORY_NOT_REACHED" if not observation_ok else "BASE_INPUT_UNKNOWN"
    elif not eligible_states:
        mainline_class = "OBSERVING"
        conflict = "FAST_HISTORY_NOT_REACHED"
    elif unknown_before_true:
        # A lower-priority class must not be promoted when a higher-priority
        # predicate is unknown.  This is distinct from OBSERVING: the latter
        # means all eligible predicates are known and none is satisfied.
        mainline_class = "DATA_INSUFFICIENT"
        conflict = "UNKNOWN_HIGHER_PRIORITY"
    elif true_state:
        mainline_class = true_state
        conflict = None
    else:
        mainline_class = "OBSERVING"
        conflict = "STABLE_HISTORY_NOT_REACHED" if not stable_history_ok else None

    if conflict == "UNKNOWN_HIGHER_PRIORITY":
        unknown_field_map = {
            "fading_was_listed": "recent_listing_history",
            "fading_percentile_delta_le_neg_015": "sector_rs20_pct_comparison_3d",
            "fading_breadth_declined": "breadth_ret1_comparison_3d",
            "fading_amount_declined": "sector_amount_ratio_delta_3sessions_common" if formal_amount else "amount_vs_prior20_comparison_3d",
            "contraction_retention_lt_050": "retention_rate",
            "reaccelerating_on_list_10_ge_3": "on_list_days_10",
            "reaccelerating_amount_ge_120": "sector_amount_vs_prior20" if formal_amount else "current_amount_vs_prior20",
            "sustained_on_list_5_ge_3": "on_list_days_5",
            "sustained_retention_ge_060": "retention_rate",
            "new_amount_ge_110": "sector_amount_vs_prior20" if formal_amount else "current_amount_vs_prior20",
            "new_entered_gt_exited": "member_change_counts",
            "broadening_entered_gt_exited": "member_change_counts",
            "broadening_breadth_improved": "breadth_ret1_previous_day",
        }
        for predicate_name, field_name in unknown_field_map.items():
            if predicates.get(predicate_name) is None:
                missing.append(field_name)

    return {
        "sector_id": sector_id,
        "trade_date": str(current["trade_date"]),
        "sector_name": str(current.get("sector_name", sector_id)),
        "sector_type": str(current.get("sector_type", "OTHER")),
        "mainline_class": mainline_class,
        "observation_days": len(dates),
        "valid_observation_days": len([value for value in percentiles if value is not None]),
        "on_list_days": on_list,
        "consecutive_on_list": consecutive,
        "current_percentile": current_p,
        "current_breadth": current_b,
        # The legacy field is intentionally left empty for v2.4.  This makes
        # it impossible for a consumer to mistake the old member-median proxy
        # for formal amount A or to coalesce it as a fallback.
        "current_amount_vs_prior20": None if formal_amount else current_a,
        "current_sector_amount_vs_prior20": current_a if formal_amount else None,
        "percentile_change_3d": None if prior_p is None or current_p is None else current_p - prior_p,
        "breadth_change_3d": current_b_change_3d,
        "amount_change_3d": current_amount_delta,
        "sector_amount_ratio_delta_3sessions_common": current_amount_delta if formal_amount else None,
        "sector_amount_quality_codes": current.get("amount_quality_codes") if formal_amount else None,
        "sector_amount_basis": current.get("amount_basis") if formal_amount else None,
        "sector_amount_membership_snapshot_id": current.get("amount_membership_snapshot_id") if formal_amount else None,
        "sector_amount_comparison_evidence": current.get("amount_comparison_evidence") if formal_amount else None,
        "sector_amount_contract_id": current.get("amount_contract_id") if formal_amount else None,
        "retention_rate": metrics["retention_rate"],
        "entered_count": metrics["entered_count"],
        "exited_count": metrics["exited_count"],
        "predicates": predicates,
        "missing_fields": sorted(set(missing)),
        "conflict_resolution": conflict,
        "history_basis": cfg.get("history_basis", HISTORY_BASIS),
        "contract_id": cfg["contract_id"],
        "config_hash": cfg_hash,
        "config": cfg,
    }


def build_mainline_state_daily(
    sector_cycle: pd.DataFrame,
    *,
    member_states: pd.DataFrame | None = None,
    config: Mapping[str, Any] | str | Path | None = None,
    previous_frame: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Classify every available sector/date and preserve all explanations.

    ``previous_frame`` is the last published M10 frame, when available.  It
    lets a new publication distinguish a model/basis change from a market
    transition on the current cutoff date.
    """
    cycle = _normalise_cycle(sector_cycle)
    members = _normalise_members(member_states)
    member_groups = {sector_id: group for sector_id, group in members.groupby("sector_id", sort=False)}
    rows: list[dict[str, Any]] = []
    for sector_id, group in cycle.groupby("sector_id", sort=True):
        sector_members = member_groups.get(sector_id, members.iloc[0:0])
        for index in range(1, len(group) + 1):
            current_history = group.iloc[:index].copy()
            current_date = current_history.iloc[-1]["trade_date"]
            current_members = sector_members[sector_members.trade_date <= current_date]
            rows.append(classify_mainline_row(current_history, member_states=current_members, config=config))
    result = pd.DataFrame(rows)
    if result.empty:
        return result
    result = apply_mainline_transitions(result, previous_frame=previous_frame)
    result["predicates"] = result["predicates"].map(lambda value: json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    result["missing_fields"] = result["missing_fields"].map(lambda value: json.dumps(value, ensure_ascii=False, separators=(",", ":")))
    result["config"] = result["config"].map(lambda value: json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    return result.sort_values(["trade_date", "sector_id"], kind="mergesort").reset_index(drop=True)


def apply_mainline_transitions(frame: pd.DataFrame, previous_frame: pd.DataFrame | None = None) -> pd.DataFrame:
    """Add previous class and identity-aware transition reasons.

    A class change is a market-state transition only when the classification
    contract and historical basis are unchanged.  A changed contract/config
    takes precedence over a basis change because the model itself changed.
    """
    result = frame.copy()
    if result.empty:
        result["previous_class"] = pd.Series(dtype="object")
        result["transition"] = pd.Series(dtype="object")
        return result
    result = result.sort_values(["sector_id", "trade_date"], kind="mergesort").reset_index(drop=True)
    grouped = result.groupby("sector_id", sort=False)
    result["previous_class"] = grouped["mainline_class"].shift(1)
    result["_previous_contract_id"] = grouped["contract_id"].shift(1)
    result["_previous_config_hash"] = grouped["config_hash"].shift(1)
    result["_previous_history_basis"] = grouped["history_basis"].shift(1)

    def transition(row: pd.Series) -> str | None:
        if pd.isna(row["previous_class"]):
            return None
        if row["contract_id"] != row["_previous_contract_id"] or row["config_hash"] != row["_previous_config_hash"]:
            return "MODEL_CHANGE"
        if row["history_basis"] != row["_previous_history_basis"]:
            return "BASIS_CHANGE"
        return "UNCHANGED" if row["previous_class"] == row["mainline_class"] else row["mainline_class"]

    result["transition"] = pd.Series(
        [transition(row) for _, row in result.iterrows()],
        index=result.index,
        dtype="object",
    )
    result.loc[result["previous_class"].isna(), "transition"] = None

    if previous_frame is not None and not previous_frame.empty:
        prior = previous_frame.copy()
        required = {"sector_id", "trade_date", "mainline_class", "contract_id", "config_hash", "history_basis"}
        if required.issubset(prior.columns):
            prior["trade_date"] = pd.to_datetime(prior["trade_date"], errors="raise").dt.date
            prior = prior.sort_values(["sector_id", "trade_date"], kind="mergesort")
            prior = prior.groupby("sector_id", sort=False).tail(1).set_index("sector_id")
            latest_date = result["trade_date"].max()
            current_indices = result.index[result["trade_date"] == latest_date]
            for index in current_indices:
                sector_id = result.at[index, "sector_id"]
                if sector_id not in prior.index:
                    continue
                previous = prior.loc[sector_id]
                result.at[index, "previous_class"] = previous["mainline_class"]
                if result.at[index, "contract_id"] != previous["contract_id"] or result.at[index, "config_hash"] != previous["config_hash"]:
                    result.at[index, "transition"] = "MODEL_CHANGE"
                elif result.at[index, "history_basis"] != previous["history_basis"]:
                    result.at[index, "transition"] = "BASIS_CHANGE"
                elif result.at[index, "previous_class"] == result.at[index, "mainline_class"]:
                    result.at[index, "transition"] = "UNCHANGED"
                else:
                    result.at[index, "transition"] = result.at[index, "mainline_class"]
    return result.drop(columns=["_previous_contract_id", "_previous_config_hash", "_previous_history_basis"])


def rows_for_storage(frame: pd.DataFrame, slice_id: str) -> list[tuple[Any, ...]]:
    columns = (
        "sector_id", "trade_date", "sector_name", "sector_type", "mainline_class", "previous_class",
        "transition", "observation_days", "valid_observation_days", "on_list_days", "consecutive_on_list",
        "current_percentile", "current_breadth", "current_amount_vs_prior20", "percentile_change_3d",
        "breadth_change_3d", "amount_change_3d", "retention_rate", "entered_count", "exited_count",
        "predicates", "missing_fields", "conflict_resolution", "history_basis", "contract_id", "config_hash",
        "current_sector_amount_vs_prior20", "sector_amount_ratio_delta_3sessions_common",
        "sector_amount_quality_codes", "sector_amount_basis", "sector_amount_membership_snapshot_id",
        "sector_amount_comparison_evidence", "sector_amount_contract_id",
    )
    rows = []
    for _, row in frame.iterrows():
        values = []
        for column in columns:
            value = row.get(column)
            if column in {"on_list_days", "predicates", "missing_fields", "sector_amount_quality_codes", "sector_amount_comparison_evidence"} and not isinstance(value, str):
                value = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            if pd.isna(value) if not isinstance(value, (dict, list)) else False:
                value = None
            values.append(value)
        rows.append(tuple([slice_id, *values]))
    return rows


def insert_mainline_rows(connection: Any, slice_id: str, frame: pd.DataFrame) -> int:
    rows = rows_for_storage(frame, slice_id)
    existing = connection.execute("select * from mainline_daily where slice_id=?", [slice_id]).fetchall()
    if existing:
        existing_values = [tuple(row) for row in existing]
        if existing_values != rows:
            raise MainlineError("MAINLINE_SLICE_IDENTITY_CONFLICT")
        return len(rows)
    if rows:
        columns = (
            "slice_id", "sector_id", "trade_date", "sector_name", "sector_type", "mainline_class", "previous_class",
            "transition", "observation_days", "valid_observation_days", "on_list_days", "consecutive_on_list",
            "current_percentile", "current_breadth", "current_amount_vs_prior20", "percentile_change_3d",
            "breadth_change_3d", "amount_change_3d", "retention_rate", "entered_count", "exited_count",
            "predicates", "missing_fields", "conflict_resolution", "history_basis", "contract_id", "config_hash",
            "current_sector_amount_vs_prior20", "sector_amount_ratio_delta_3sessions_common",
            "sector_amount_quality_codes", "sector_amount_basis", "sector_amount_membership_snapshot_id",
            "sector_amount_comparison_evidence", "sector_amount_contract_id",
        )
        connection.executemany(
            f"insert into mainline_daily ({','.join(columns)}) values ({','.join('?' for _ in columns)})",
            rows,
        )
    return len(rows)
