"""V4-03 market and sector input primitives; no profile or V4-08 publication."""

from __future__ import annotations

from hashlib import sha256
import json
import math
from statistics import median
from typing import Mapping, Sequence

from .parameters import candidate_threshold


MARKET_REGIME_PARAMETER_SET_ID = "V4_03_CORE_FACTOR_PARAMETER_SET_V1"


def market_axis_primitives(*, breadth: float | None, participation: float | None,
                           limit_coverage: float | None, stress_ratio: float | None,
                           prior_stress_ratio: float | None, trade_date: str,
                           market_calendar_id: str, market_snapshot_id: str,
                             adjustment_basis_id: str, input_source_digest: str,
                             stress_change_current_ratio: float | None = None,
                             stress_change_current_provided: bool = False) -> dict:
    """Deterministic axes other than trend; final regime UI remains V4-04."""
    breadth_boundary = candidate_threshold("market_breadth_axis")
    participation_high = candidate_threshold("market_participation_expanding")
    participation_low = candidate_threshold("market_participation_thin")
    stress_coverage = candidate_threshold("market_stress_min_limit_coverage")
    stress_high = candidate_threshold("market_stress_high")
    stress_elevated = candidate_threshold("market_stress_elevated")
    breadth_known = isinstance(breadth, (int, float)) and not isinstance(breadth, bool) and math.isfinite(breadth)
    participation_known = isinstance(participation, (int, float)) and not isinstance(participation, bool) and math.isfinite(participation)
    coverage_known = isinstance(limit_coverage, (int, float)) and not isinstance(limit_coverage, bool) and math.isfinite(limit_coverage)
    stress_known = isinstance(stress_ratio, (int, float)) and not isinstance(stress_ratio, bool) and math.isfinite(stress_ratio)
    prior_stress_known = isinstance(prior_stress_ratio, (int, float)) and not isinstance(prior_stress_ratio, bool) and math.isfinite(prior_stress_ratio)
    breadth_axis = ("IMPROVING" if breadth > breadth_boundary else "DETERIORATING" if breadth < -breadth_boundary else "STABLE") if breadth_known else None
    participation_axis = ("EXPANDING" if participation >= participation_high else "THIN" if participation < participation_low else "NORMAL") if participation_known else None
    stress_level = ("HIGH" if stress_ratio >= stress_high else "ELEVATED" if stress_ratio >= stress_elevated else "LOW") if stress_known and coverage_known and limit_coverage >= stress_coverage else None
    change_current = stress_change_current_ratio if stress_change_current_provided else stress_ratio
    change_current_known = isinstance(change_current, (int, float)) and not isinstance(change_current, bool) and math.isfinite(change_current)
    stress_change = ("RISING" if change_current > prior_stress_ratio else "DECLINING" if change_current < prior_stress_ratio else "STABLE") if change_current_known and prior_stress_known else None
    identity = {"trade_date": trade_date, "market_calendar_id": market_calendar_id,
                "market_snapshot_id": market_snapshot_id, "adjustment_basis_id": adjustment_basis_id,
                "input_source_digest": input_source_digest}
    if any(not isinstance(v, str) or not v for v in identity.values()):
        raise ValueError("market axes require complete session/source/coordinate identity")
    if len(input_source_digest) != 64 or any(c not in "0123456789abcdef" for c in input_source_digest.lower()):
        raise ValueError("market axis input source digest must be SHA-256")
    output = {"contract_id": "MARKET_REGIME_V1_PRIMITIVES", "contract_version": "1.0.0",
            "parameter_set_id": MARKET_REGIME_PARAMETER_SET_ID, "as_of": trade_date,
            "identity": identity,
            "breadth_axis": breadth_axis, "participation_axis": participation_axis,
            "stress_level": stress_level, "stress_change": stress_change,
            "regime_ui_publication": "NOT_PUBLISHED_V4_03",
            "field_quality": {"breadth_axis": {"quality_state": "OBSERVED" if breadth_known else "UNKNOWN", "unknown_reason": None if breadth_known else "BREADTH_UNKNOWN_OR_NONFINITE"},
                              "participation_axis": {"quality_state": "OBSERVED" if participation_known else "UNKNOWN", "unknown_reason": None if participation_known else "PARTICIPATION_UNKNOWN_OR_NONFINITE"},
                              "stress_level": {"quality_state": "OBSERVED" if stress_level is not None else "UNKNOWN", "unknown_reason": None if stress_level is not None else "STRESS_INPUT_OR_COVERAGE_UNKNOWN"},
                              "stress_change": {"quality_state": "OBSERVED" if stress_change is not None else "UNKNOWN", "unknown_reason": None if stress_change is not None else "STRESS_CHANGE_INPUT_UNKNOWN"}}}
    output["input_digest"] = sha256(json.dumps([identity, breadth, participation, limit_coverage,
                                                  stress_ratio, prior_stress_ratio, stress_change_current_ratio,
                                                  stress_change_current_provided], sort_keys=True,
                                               separators=(",", ":"), default=str).encode()).hexdigest()
    output["output_digest"] = sha256(json.dumps(output, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()
    return output


def market_trend_axis(*, index_close: float | None, index_ma20: float | None,
                      index_ma20_t_minus_5: float | None, trade_date: str,
                      market_calendar_id: str, market_snapshot_id: str,
                      adjustment_basis_id: str, input_source_digest: str) -> dict:
    """Trend-axis rule from MARKET_REGIME_TREND_WEAK_ERRATUM_V1."""
    values = (index_close, index_ma20, index_ma20_t_minus_5)
    if any(v is None or not math.isfinite(v) for v in values):
        axis, reason = "UNKNOWN", "REQUIRED_TREND_INPUT_UNKNOWN"
    elif index_close > index_ma20 and index_ma20 > index_ma20_t_minus_5:
        axis, reason = "STRONG", None
    elif index_close < index_ma20 and index_ma20 < index_ma20_t_minus_5:
        axis, reason = "WEAK", None
    else:
        axis, reason = "NEUTRAL", None
    identity = {"trade_date": trade_date, "market_calendar_id": market_calendar_id,
                "market_snapshot_id": market_snapshot_id, "adjustment_basis_id": adjustment_basis_id,
                "input_source_digest": input_source_digest}
    if any(not isinstance(v, str) or not v for v in identity.values()):
        raise ValueError("trend axis requires complete session/source/coordinate identity")
    if len(input_source_digest) != 64 or any(c not in "0123456789abcdef" for c in input_source_digest.lower()):
        raise ValueError("trend input source digest must be SHA-256")
    output = {"contract_id": "MARKET_REGIME_TREND_WEAK_ERRATUM_V1",
            "contract_version": "1.0.0", "trend_axis": axis,
            "quality_state": "UNKNOWN" if reason else "OBSERVED", "unknown_reason": reason,
            "regime_ui_publication": "NOT_PUBLISHED_V4_03", "identity": identity,
            "parameter_set_id": MARKET_REGIME_PARAMETER_SET_ID}
    output["input_digest"] = sha256(json.dumps([identity, *values], sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()
    output["output_digest"] = sha256(json.dumps(output, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()
    return output


def historical_market_path(daily_ret1: Sequence[tuple[str, float | None]], *,
                           start_sessions: Sequence[str], start_universe_snapshot_ids: Sequence[str],
                           market_calendar_id: str, input_source_digest: str,
                           series_version: str = "DAILY_REBALANCED_RESEARCH_INDEX_V1") -> list[dict]:
    """A missing day invalidates this entire series suffix; rebase requires a new version."""
    if len(daily_ret1) != len(start_sessions) or len(daily_ret1) != len(start_universe_snapshot_ids):
        raise ValueError("market path needs one start session and PIT universe identity per return")
    if not market_calendar_id or not series_version or not input_source_digest or any(not x for x in start_sessions) or any(not x for x in start_universe_snapshot_ids):
        raise ValueError("market path identity is incomplete")
    if len(input_source_digest) != 64 or any(c not in "0123456789abcdef" for c in input_source_digest.lower()):
        raise ValueError("market path input source digest must be SHA-256")
    result, level = [], 1.0
    broken = False
    for index, (date, ret) in enumerate(daily_ret1):
        if ret is None or ret <= -1:
            level = None
            broken = True
        elif not broken and level is not None:
            level *= 1 + ret
        row = {"contract_id": "V4_03_MARKET_REFERENCE_PATH_V1", "contract_version": "1.0.0",
               "parameter_set_id": MARKET_REGIME_PARAMETER_SET_ID,
               "trade_date": date, "start_session": start_sessions[index], "end_session": date,
               "level": level, "daily_return": ret,
               "quality_state": "OBSERVED" if level is not None else "UNKNOWN",
               "unknown_reason": None if level is not None else "DAILY_RETURN_UNKNOWN_BREAKS_SERIES_SUFFIX",
               "path_identity": "DAILY_REBALANCED_RESEARCH_INDEX", "series_version": series_version,
               "rebase_policy": "UNKNOWN_SUFFIX_UNTIL_NEW_SERIES_VERSION",
               "market_calendar_id": market_calendar_id,
               "start_universe_snapshot_id": start_universe_snapshot_ids[index],
               "input_source_digest": input_source_digest}
        row["window_identity"] = sha256(json.dumps([market_calendar_id, start_sessions[index], date,
                                                     start_universe_snapshot_ids[index], series_version],
                                                    separators=(",", ":")).encode()).hexdigest()
        row["input_digest"] = sha256(json.dumps([input_source_digest, start_sessions[index], date, ret,
                                                 start_universe_snapshot_ids[index], series_version],
                                                separators=(",", ":"), default=str).encode()).hexdigest()
        row["output_digest"] = sha256(json.dumps(row, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()
        result.append(row)
    return result


def sector_native(members: Sequence[str], evaluable: Mapping[str, Mapping[str, object]], *,
                  trade_date: str, market_calendar_id: str,
                  sector_membership_snapshot_id: str, adjustment_basis_id: str,
                  input_source_digest: str) -> dict:
    """Unqualified metrics with separate quote, amount, ret1 and MA20 sets."""
    required_identity = (trade_date, market_calendar_id, sector_membership_snapshot_id,
                         adjustment_basis_id, input_source_digest)
    if any(not isinstance(item, str) or not item for item in required_identity):
        raise ValueError("sector native output requires complete time/source/PIT identity")
    if len(input_source_digest) != 64 or any(c not in "0123456789abcdef" for c in input_source_digest.lower()):
        raise ValueError("sector native input source digest must be SHA-256")
    names = sorted(set(members))
    rows = {s: evaluable[s] for s in names if s in evaluable}
    quotes = {s: x for s, x in rows.items() if x.get("quote_quality_state") == "OBSERVED"}
    amounts = [x["amount"] for x in rows.values()
               if x.get("amount_quality_state") == "OBSERVED" and isinstance(x.get("amount"), (int, float))
               and not isinstance(x.get("amount"), bool) and math.isfinite(x["amount"])]
    returns = [x["ret1"] for x in rows.values()
               if x.get("ret1_quality_state") == "OBSERVED" and isinstance(x.get("ret1"), (int, float))
               and not isinstance(x.get("ret1"), bool) and math.isfinite(x["ret1"])]
    above_ma20 = [x["above_ma20"] for x in rows.values()
                  if x.get("ma20_quality_state") == "OBSERVED" and isinstance(x.get("above_ma20"), bool)]
    output = {
        "contract_id": "V4_03_SECTOR_NATIVE_PRIMITIVE_V1",
        "contract_version": "1.0.0",
        "parameter_set_id": MARKET_REGIME_PARAMETER_SET_ID,
        "as_of": {"trade_date": trade_date, "semantics": "fixed_market_session_t"},
        "market_calendar_id": market_calendar_id,
        "sector_membership_snapshot_id": sector_membership_snapshot_id,
        "adjustment_basis_id": adjustment_basis_id,
        "input_source_digest": input_source_digest,
        "publication_permission": "NOT_V4_08_SECTOR_FACTORS",
        "quality_semantics": "each metric uses its own explicit field-local quality state",
        "member_set_identity": sha256(json.dumps(names, separators=(",", ":")).encode()).hexdigest(),
        "member_count": len(names), "input_row_count": len(rows),
        "raw_quote_evaluable_count": len(quotes),
        "raw_quote_coverage": len(quotes) / len(names) if names else None,
        "amount_evaluable_count": len(amounts),
        "amount_median_primitive": median(amounts) if amounts else None,
        "positive_breadth_numerator": sum(x > 0 for x in returns),
        "positive_breadth_denominator": len(returns),
        "ma20_width_numerator": sum(bool(x) for x in above_ma20),
        "ma20_width_denominator": len(above_ma20),
        "amount_concentration_evaluable_count": len(amounts),
        "amount_concentration_numerator": max(amounts) if amounts else None,
        "amount_concentration_denominator": sum(amounts) if amounts else None,
        "downstream_scope": {"consumer_stage": "V4-08", "sector_ranking_permitted": False,
                             "sector_qualification_permitted": False, "seed_permitted": False,
                             "rotation_permitted": False},
        "field_quality": {
            "raw_quote_coverage": {"quality_state": "OBSERVED" if names else "UNKNOWN",
                                    "unknown_reason": None if names else "EMPTY_MEMBER_SET"},
            "amount_median_primitive": {"quality_state": "OBSERVED" if amounts else "UNKNOWN",
                                        "unknown_reason": None if amounts else "NO_EVALUABLE_AMOUNT"},
            "positive_breadth_counts": {"quality_state": "OBSERVED", "unknown_reason": None},
            "ma20_width_counts": {"quality_state": "OBSERVED", "unknown_reason": None},
            "amount_concentration": {"quality_state": "OBSERVED" if amounts else "UNKNOWN",
                                     "unknown_reason": None if amounts else "NO_EVALUABLE_AMOUNT"},
        },
    }
    output["input_digest"] = sha256(json.dumps({"identity": required_identity, "members": names,
                                               "rows": [(sid, dict(rows[sid])) for sid in sorted(rows)]},
                                              sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()
    output["output_digest"] = sha256(json.dumps(output, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()
    return output


def common_members(left: Sequence[str], right: Sequence[str]) -> dict:
    a, b = set(left), set(right)
    return {"common": sorted(a & b), "entered": sorted(b - a), "exited": sorted(a - b)}
