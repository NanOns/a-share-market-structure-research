"""Pure V4-04 Core Profile state rules (REV2 §§10B–10G, 10I).

Inputs are already PIT classified factor values. Missing inputs remain UNKNOWN;
the caller must provide accepted input identities before publication.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from math import isfinite
from pathlib import Path
from typing import Mapping


CONTRACT_VERSION = "V4_04_CORE_PROFILE_RULES_V1"
_parameter_file = Path(__file__).resolve().parents[2] / "config/v4_04_parameter_set_v1.json"
_parameter_data = json.loads(_parameter_file.read_text(encoding="utf-8"))
if _parameter_data["parameter_set_id"] != "V4_04_CORE_PROFILE_PARAMETER_SET_V1":
    raise ValueError("V4-04 parameter set identity mismatch")
P = {entry["parameter_id"].removeprefix("V4_04_"): entry["value"]
     for entry in _parameter_data["parameters"]}


@dataclass(frozen=True)
class State:
    value: str | bool | None
    contract_id: str
    evidence: dict[str, float | bool | str | None]
    unknown_reason: str | None = None


def _number(inputs: Mapping[str, object], key: str) -> float | None:
    raw = inputs.get(key)
    if isinstance(raw, bool) or not isinstance(raw, (int, float)):
        return None
    value = float(raw)
    return value if isfinite(value) else None


def _state(value: str, contract: str, inputs: Mapping[str, object], keys: tuple[str, ...],
           reason: str | None = None) -> State:
    return State(value, contract, {key: inputs[key] if isinstance(inputs.get(key), (bool, str))
                                   else _number(inputs, key) for key in keys}, reason)


def _required(inputs: Mapping[str, object], keys: tuple[str, ...]) -> bool:
    return all(_number(inputs, key) is not None for key in keys)


def trend(inputs: Mapping[str, object]) -> State:
    contract = "TREND_STATE_V1"
    keys = ("close", "ma20", "ma60", "slope20", "slope60", "hh_progress", "ll_progress", "core_price_damage", "atr20")
    numeric_keys = ("close", "ma20", "ma60", "slope20", "slope60", "atr20")
    if (not _required(inputs, numeric_keys) or
            not all(isinstance(inputs.get(key), bool) for key in ("hh_progress", "ll_progress", "core_price_damage"))):
        return _state("UNKNOWN", contract, inputs, keys, "REQUIRED_INPUT_UNKNOWN")
    c, ma20, ma60 = (_number(inputs, x) for x in ("close", "ma20", "ma60"))
    s20, s60 = (_number(inputs, x) for x in ("slope20", "slope60"))
    hh, ll = bool(inputs["hh_progress"]), bool(inputs["ll_progress"])
    damage = inputs["core_price_damage"]
    deadband = P["SLOPE_DEADBAND_ATR"]
    rules = (
        (c < ma20 and s20 < -deadband and s60 < -deadband and ll, "DOWNTREND_STRONG"),
        (c > ma20 and s20 > deadband and (c > ma60 or s60 > deadband) and hh and not damage, "UPTREND_STRONG"),
        (c < ma20 and s20 < -deadband, "DOWNTREND"),
        (c > ma20 and s20 > deadband and not damage, "UPTREND"),
        (c < ma20, "SIDEWAYS_WEAK"),
        (c > ma20, "SIDEWAYS_STRONG"),
    )
    return _state(next((label for passed, label in rules if passed), "SIDEWAYS"), contract, inputs, keys)


def position(inputs: Mapping[str, object]) -> State:
    contract = "POSITION_STATE_V1"
    keys = ("bias20_atr", "pos60")
    if not _required(inputs, keys):
        return _state("UNKNOWN", contract, inputs, keys, "REQUIRED_INPUT_UNKNOWN")
    bias, pos = (_number(inputs, x) for x in keys)
    value = ("EXTENDED" if bias >= P["POSITION_EXTENDED_BIAS"] else "HIGH_ZONE" if pos >= P["POSITION_HIGH"] else
             "MID_HIGH" if pos >= P["POSITION_MID_HIGH"] else "MID_ZONE" if pos >= P["POSITION_MID"] else
             "MID_LOW" if pos >= P["POSITION_MID_LOW"] else "LOW_ZONE")
    return _state(value, contract, inputs, keys)


def ma_structure(inputs: Mapping[str, object]) -> State:
    contract = "MA_STRUCTURE_V1"
    keys = ("ma5", "ma10", "ma20", "slope20")
    if not _required(inputs, keys):
        return _state("UNKNOWN", contract, inputs, keys, "REQUIRED_INPUT_UNKNOWN")
    ma5, ma10, ma20, slope = (_number(inputs, x) for x in keys)
    value = ("BULL_ALIGNED" if ma5 > ma10 > ma20 and slope > 0 else
             "BEAR_ALIGNED" if ma5 < ma10 < ma20 and slope < 0 else
             "BULL_TRANSITION" if ma5 > ma20 and slope >= 0 else
             "BEAR_TRANSITION" if ma5 < ma20 and slope <= 0 else "MIXED")
    return _state(value, contract, inputs, keys)


def compression(inputs: Mapping[str, object]) -> State:
    contract = "COMPRESSION_STATE_V1"
    numeric_keys = ("range_ratio", "atr_ratio", "vol_ratio", "amount_ratio20")
    keys = numeric_keys + ("minimum_liquidity",)
    if not _required(inputs, numeric_keys) or not isinstance(inputs.get("minimum_liquidity"), bool):
        return _state("UNKNOWN", contract, inputs, keys, "REQUIRED_INPUT_UNKNOWN")
    ran, atr, vol, amount = (_number(inputs, x) for x in numeric_keys)
    liquid = inputs["minimum_liquidity"]
    value = ("EXPANDING_EXTREME" if atr >= P["COMPRESS_EXTREME"] or vol >= P["COMPRESS_EXTREME"] else
             "EXPANDING" if atr >= P["COMPRESS_EXPAND"] or vol >= P["COMPRESS_EXPAND"] else
             "COMPRESSING_STRONG" if ran <= P["COMPRESS_STRONG_RANGE"] and atr <= P["COMPRESS_STRONG_ATR_VOL"] and vol <= P["COMPRESS_STRONG_ATR_VOL"] and amount <= P["COMPRESS_STRONG_AMOUNT"] and liquid else
             "COMPRESSING" if ran <= P["COMPRESS_RANGE"] and atr <= P["COMPRESS_ATR_VOL"] and vol <= P["COMPRESS_ATR_VOL"] and liquid else "NORMAL")
    return _state(value, contract, inputs, keys)


def ratio_state(inputs: Mapping[str, object], key: str) -> State:
    contract = "AMOUNT_VOLUME_STATE_V1"
    if key not in ("amount_ratio20", "volume_ratio20"):
        raise ValueError("ratio_state only accepts amount_ratio20 or volume_ratio20")
    if not _required(inputs, (key,)):
        return _state("UNKNOWN", contract, inputs, (key,), "REQUIRED_INPUT_UNKNOWN")
    ratio = _number(inputs, key)
    value = ("VERY_DRY" if ratio < P["RATIO_VERY_DRY"] else "CONTRACTED" if ratio < P["RATIO_CONTRACTED"] else
             "NORMAL" if ratio < P["RATIO_NORMAL"] else "EXPANDED" if ratio < P["RATIO_EXPANDED"] else "VERY_EXPANDED")
    return _state(value, contract, inputs, (key,))


def participation(inputs: Mapping[str, object]) -> State:
    contract = "AMOUNT_VOLUME_STATE_V1"
    keys = ("amount_ratio20", "ret1", "clv")
    if not _required(inputs, keys[:2]):
        return _state("UNKNOWN", contract, inputs, keys, "REQUIRED_INPUT_UNKNOWN")
    amount, ret = (_number(inputs, x) for x in keys[:2])
    clv = _number(inputs, "clv")
    if amount >= P["PARTICIPATION_HIGH"] and ret < 0:
        value = "HIGH_PARTICIPATION_REVERSAL"
    elif amount >= P["PARTICIPATION_HIGH"] and ret > 0 and clv is None:
        return _state("UNKNOWN", contract, inputs, keys, "CLV_REQUIRED_FOR_BRANCH")
    elif amount >= P["PARTICIPATION_HIGH"] and ret > 0 and clv >= P["PARTICIPATION_CLV"]:
        value = "HIGH_PARTICIPATION_EFFECTIVE_ADVANCE"
    elif amount >= P["PARTICIPATION_HIGH"]:
        value = "HIGH_PARTICIPATION_LOW_EFFICIENCY"
    elif amount < P["PARTICIPATION_LOW"] and ret > 0:
        value = "LOW_PARTICIPATION_ADVANCE"
    elif amount < P["PARTICIPATION_LOW"] and ret < 0:
        value = "LOW_PARTICIPATION_DECLINE"
    else:
        value = "NORMAL_PARTICIPATION"
    return _state(value, contract, inputs, keys)


def relative(inputs: Mapping[str, object], compression_state: str, ma_state: str) -> State:
    contract = "RELATIVE_STATE_V1"
    keys = ("rps5", "rps20", "rps20_delta3", "rel_market_1", "rel_market_5")
    evidence = dict(inputs, compression_state=compression_state, ma_structure_state=ma_state)
    keys += ("compression_state", "ma_structure_state")
    if not _required(inputs, keys[:-2]) or "UNKNOWN" in (compression_state, ma_state):
        return _state("UNKNOWN", contract, evidence, keys, "REQUIRED_INPUT_UNKNOWN")
    _, rps20, delta, rel1, _ = (_number(inputs, x) for x in keys[:-2])
    active = delta >= P["RELATIVE_ACTIVE_DELTA"] and (compression_state in {"COMPRESSING", "COMPRESSING_STRONG"} or ma_state in {"BULL_TRANSITION", "BULL_ALIGNED"})
    value = ("ACTIVE_EMERGENCE" if active else
             "PASSIVE_RESILIENCE" if rel1 > 0 and delta <= 0 else
             "LEADING_ACCELERATING" if rps20 >= P["RELATIVE_LEADING_RPS"] and delta > 0 else
             "LEADING_STABLE" if rps20 >= P["RELATIVE_LEADING_RPS"] and delta >= -P["RELATIVE_IMPROVING_DELTA"] else
             "IMPROVING" if delta > P["RELATIVE_IMPROVING_DELTA"] else "WEAKENING" if delta < -P["RELATIVE_IMPROVING_DELTA"] else
             "LAGGING" if rps20 < P["RELATIVE_LAGGING_RPS"] else "NEUTRAL")
    return _state(value, contract, evidence, keys)


def near_high(inputs: Mapping[str, object], horizon: int) -> State:
    if horizon not in (20, 60):
        raise ValueError("horizon must be 20 or 60")
    keys = (f"prior_high{horizon}", "close", "atr20")
    contract = "POSITION_STATE_V1"
    if not _required(inputs, keys) or _number(inputs, "atr20") <= 0:
        return _state("UNKNOWN", contract, inputs, keys, "REQUIRED_INPUT_UNKNOWN_OR_ZERO_ATR")
    distance = (_number(inputs, keys[0]) - _number(inputs, "close")) / _number(inputs, "atr20")
    return _state("ABOVE_PRIOR_HIGH" if distance < 0 else "NEAR" if distance <= P["NEAR_HIGH_ATR"] else "BELOW", contract, inputs, keys)


def drawdown(inputs: Mapping[str, object], horizon: int) -> State:
    if horizon not in (20, 60):
        raise ValueError("horizon must be 20 or 60")
    keys = ("close", f"hhv{horizon}")
    contract = "POSITION_STATE_V1"
    if not _required(inputs, keys) or _number(inputs, keys[1]) <= 0:
        return _state("UNKNOWN", contract, inputs, keys, "REQUIRED_INPUT_UNKNOWN_OR_ZERO_HIGH")
    price_ratio = _number(inputs, "close") / _number(inputs, keys[1])
    return _state("SHALLOW" if price_ratio >= 1 + P["DRAWDOWN_SHALLOW"] else
                  "MODERATE" if price_ratio >= 1 + P["DRAWDOWN_MODERATE"] else "DEEP",
                  contract, inputs, keys)


def closed_period_trend(inputs: Mapping[str, object], period: str) -> State:
    if period not in ("weekly", "monthly"):
        raise ValueError("period must be weekly or monthly")
    ma = "ma5" if period == "weekly" else "ma3"
    keys = ("period_view", "close", ma, f"previous_{ma}")
    contract = "TREND_STATE_V1"
    if inputs.get("period_view") != "CLOSED_ONLY" or not _required(inputs, keys[1:]):
        return _state("UNKNOWN", contract, inputs, keys, "CLOSED_PERIOD_OR_INPUT_UNAVAILABLE")
    close, current, previous = (_number(inputs, x) for x in keys[1:])
    value = ("WEEKLY_UP" if close > current and current > previous else
             "WEEKLY_DOWN" if close < current and current < previous else "WEEKLY_FLAT") if period == "weekly" else (
             "MONTHLY_UP" if close > current and current > previous else
             "MONTHLY_DOWN" if close < current and current < previous else "MONTHLY_FLAT")
    return _state(value, contract, inputs, keys)


def extension_risk(inputs: Mapping[str, object]) -> State:
    contract = "EXTENSION_RISK_V1"
    keys = ("bias20_atr", "ret5", "atr20", "close", "amount_ratio20", "ret1")
    bias = _number(inputs, "bias20_atr")
    if bias is not None and bias >= P["EXTENSION_EXTREME"]:
        return _state("EXTREME", contract, inputs, keys)
    if bias is not None and bias >= P["EXTENSION_HIGH"]:
        return _state("HIGH", contract, inputs, keys)
    if bias is None or not _required(inputs, keys[1:]) or _number(inputs, "close") <= 0:
        return _state("UNKNOWN", contract, inputs, keys, "REQUIRED_INPUT_UNKNOWN")
    ret5, atr, close, amount, ret1 = (_number(inputs, x) for x in keys[1:])
    value = "HIGH" if ret5 >= P["EXTENSION_RET5_ATR"] * atr / close and amount >= P["EXTENSION_AMOUNT"] and ret1 <= 0 else "MEDIUM" if bias >= P["EXTENSION_MEDIUM"] else "LOW"
    return _state(value, contract, inputs, keys)


def severe_extension(risk: State) -> State:
    if risk.contract_id != "EXTENSION_RISK_V1":
        raise ValueError("risk contract mismatch")
    if risk.value == "UNKNOWN":
        return State(None, "EXTENSION_RISK_V1", {"core_extension_risk": "UNKNOWN"}, risk.unknown_reason)
    return State(risk.value == "EXTREME", "EXTENSION_RISK_V1",
                 {"core_extension_risk": risk.value})
