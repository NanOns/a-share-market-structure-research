"""V4-04-only derivations over accepted canonical observations."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from statistics import fmean
from typing import Mapping, Sequence

from .profile_core import P


CONTRACT_ID = "V4_04_DERIVED_PRIMITIVES_V1"
PARAMETER_SET_ID = "V4_04_CORE_PROFILE_PARAMETER_SET_V1"


@dataclass(frozen=True)
class Derived:
    value: float | bool | None
    quality: str
    unknown_reason: str | None
    contract_id: str
    parameter_set_id: str
    input_digest: str
    window_identity: str
    actual_count: int
    calendar_span: int
    window_start_trade_date: str | None = None
    window_end_trade_date: str | None = None
    suspended_count: int = 0
    window_contract_id: str = "TECHNICAL_BAR_WINDOW_V1"
    field_window_mapping_id: str = "V4_04_FIELD_WINDOW_MAPPING_V1"


def _hash(value: object) -> str:
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


def _result(value: float | bool | None, reason: str | None, inputs: object,
            actual_count: int, calendar_span: int, start: str | None = None,
            end: str | None = None, suspended_count: int = 0) -> Derived:
    return Derived(value if reason is None else None, "OBSERVED" if reason is None else "UNKNOWN", reason,
                   CONTRACT_ID, PARAMETER_SET_ID, _hash(inputs), _hash([CONTRACT_ID, inputs]),
                   actual_count, calendar_span, start, end, suspended_count)


def _factor(factors: Mapping[str, Mapping], name: str) -> float | bool | None:
    item = factors.get(name, {})
    return item.get("value") if item.get("quality_state") == "OBSERVED" else None


def technical_window_status(rows: Sequence[Mapping], statuses: Sequence[str | tuple[str, str]],
                            calendar: Sequence[str] | None) -> tuple[bool, int, int, list]:
    """Validate the calendar span of an actual-bar window, including missing rows."""
    if not rows:
        return False, 0, 0, []
    start, end = str(rows[0]["trade_date"]), str(rows[-1]["trade_date"])
    actual_dates = [str(row["trade_date"]) for row in rows]
    dated = [(str(x[0]), x[1]) for x in statuses if isinstance(x, tuple) and start <= str(x[0]) <= end]
    if dated:
        expected = [date for date in calendar if start <= date <= end] if calendar is not None else [x[0] for x in dated]
        by_date = dict(dated)
        valid = (len(dated) == len(by_date) == len(expected) and
                 set(by_date) == set(expected) and
                 set(actual_dates) == {date for date, status in dated if status == "ACTUAL_TRADED"} and
                 all(status in ("ACTUAL_TRADED", "SUSPENDED") for _, status in dated))
        return valid, len(expected), sum(status == "SUSPENDED" for _, status in dated), dated
    if calendar is not None:
        expected = [date for date in calendar if start <= date <= end]
        return False, len(expected), 0, []
    # Legacy date-free fixtures cannot prove missing calendar rows; production supplies dated rows and calendar.
    values = list(statuses)
    return (len(values) >= len(rows) and all(x in ("ACTUAL_TRADED", "SUSPENDED") for x in values),
            len(rows), 0, values)


def derive_daily(bars: Sequence[Mapping], factors: Mapping[str, Mapping],
                 statuses: Sequence[str | tuple[str, str]], asof: str,
                 calendar: Sequence[str] | None = None) -> dict[str, Derived]:
    """Bars ascend by date and contain only actual sessions through asof.

    Statuses cover the same calendar span as the 250-bar window. Any unexplained
    status fails the long-window diagnostic closed.
    """
    bars = [bar for bar in bars if str(bar["trade_date"]) <= asof]
    latest = bars[-1] if bars else None
    current = latest is not None and str(latest["trade_date"]) == asof and latest.get("adjusted_quality") == "READY"
    close = float(latest["qfq_close"]) if current and latest.get("qfq_close") is not None else None
    output: dict[str, Derived] = {}
    status_values = [x[1] if isinstance(x, tuple) else x for x in statuses]
    def bounds(rows):
        return (str(rows[0]["trade_date"]), str(rows[-1]["trade_date"])) if rows else (None, None)
    def span(rows):
        start, end = bounds(rows)
        dated = [entry[1] for entry in statuses if isinstance(entry, tuple) and start <= entry[0] <= end] if start else []
        return (len(dated), dated.count("SUSPENDED")) if dated else (len(rows), 0)

    ma10_window = int(P["MA10_WINDOW"])
    ma10_rows = bars[-ma10_window:]
    ma10_status_ok, ma10_span, ma10_suspended, ma10_status_evidence = technical_window_status(ma10_rows, statuses, calendar)
    ma10_ok = (current and len(ma10_rows) == ma10_window and ma10_status_ok and
               all(row.get("adjusted_quality") == "READY" and row.get("qfq_close") is not None for row in ma10_rows))
    output["ma10"] = _result(fmean(float(x["qfq_close"]) for x in ma10_rows) if ma10_ok else None,
                              None if ma10_ok else "MA10_WINDOW_OR_ENDPOINT_UNAVAILABLE",
                              {"bars": [(x.get("trade_date"), x.get("qfq_close"), x.get("adjusted_quality")) for x in ma10_rows],
                               "statuses": ma10_status_evidence, "calendar_span": ma10_span},
                              len(ma10_rows), ma10_span, *bounds(ma10_rows), ma10_suspended)

    pos_window = int(P["POS250_WINDOW"])
    pos_rows = bars[-pos_window:]
    long_status_ok, pos_span, pos_suspended, pos_status_evidence = technical_window_status(pos_rows, statuses, calendar)
    pos_ok = (current and len(pos_rows) == pos_window and long_status_ok and
              all(x.get("adjusted_quality") == "READY" and x.get("qfq_high") is not None and x.get("qfq_low") is not None for x in pos_rows))
    high = max(float(x["qfq_high"]) for x in pos_rows) if pos_ok else None
    low = min(float(x["qfq_low"]) for x in pos_rows) if pos_ok else None
    den = high - low if pos_ok else None
    reason = None if pos_ok and den > 0 else "POS250_WINDOW_OR_DENOMINATOR_UNAVAILABLE"
    output["pos250"] = _result((close - low) / den if reason is None else None, reason,
                                [(x.get("trade_date"), x.get("qfq_high"), x.get("qfq_low"), x.get("adjusted_quality"))
                                 for x in pos_rows] + pos_status_evidence, len(pos_rows), pos_span,
                                *bounds(pos_rows), pos_suspended)

    atr = _factor(factors, "atr20")
    ma20 = _factor(factors, "ma20")
    prior_high20 = _factor(factors, "prior_high20")
    ratio_ok = close is not None and isinstance(atr, (int, float)) and atr > 0
    for field, numerator in (("bias20_atr", None if ma20 is None else close - ma20 if close is not None else None),
                             ("dist_high20_atr", None if prior_high20 is None else prior_high20 - close if close is not None else None)):
        ok = ratio_ok and numerator is not None
        output[field] = _result(numerator / atr if ok else None, None if ok else "ATR_OR_PRICE_INPUT_UNAVAILABLE",
                                {"close": close, "atr20": atr, "numerator": numerator}, 1, 1,
                                str(latest["trade_date"]) if latest else None, asof)

    prior_window = int(P["PRIOR_AMOUNT_WINDOW"])
    prior_rows = bars[-prior_window-1:-1] if current else []
    liquid_status_ok, liquid_span, liquid_suspended, liquid_status_evidence = technical_window_status(prior_rows, statuses, calendar)
    liquid_ok = (current and len(prior_rows) == prior_window and liquid_status_ok and
                 all(isinstance(x.get("amount"), (int, float)) for x in prior_rows))
    mean_amount = fmean(float(x["amount"]) for x in prior_rows) if liquid_ok else None
    output["minimum_liquidity"] = _result(mean_amount >= P["MINIMUM_LIQUIDITY_CNY"] if liquid_ok else None,
                                            None if liquid_ok else "PRIOR20_AMOUNT_UNAVAILABLE",
                                            {"bars": [(x.get("trade_date"), x.get("amount")) for x in prior_rows],
                                             "statuses": liquid_status_evidence, "calendar_span": liquid_span},
                                            len(prior_rows), liquid_span, *bounds(prior_rows), liquid_suspended)
    return output


def derive_closed_period(periods: Sequence[Mapping], window: int, asof: str) -> dict[str, object]:
    """Use only the last window+1 formally closed, ready QFQ periods."""
    if window not in (int(P["MONTHLY_MA_WINDOW"]), int(P["WEEKLY_MA_WINDOW"])):
        raise ValueError("unsupported formal period window")
    eligible = [x for x in periods if str(x["period_last_session"]) <= asof and x.get("period_view") == "CLOSED_ONLY"]
    recent = eligible[-window - 1:]
    key = "ma5" if window == 5 else "ma3"
    if (len(recent) != window + 1 or any(x.get("period_status") != "CLOSED_ONLY_READY" or
            x.get("price_basis") != "QFQ" or x.get("close") is None for x in recent)):
        return {"period_view": "UNKNOWN", "close": None, key: None, f"previous_{key}": None}
    closes = [float(x["close"]) for x in recent]
    return {"period_view": "CLOSED_ONLY", "close": closes[-1], key: fmean(closes[-window:]),
            f"previous_{key}": fmean(closes[-window - 1:-1])}
