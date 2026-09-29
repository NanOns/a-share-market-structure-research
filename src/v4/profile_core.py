"""Pure V4-04 Core Profile state rules (REV2 §§10B–10G, 10I).

Inputs are already PIT classified factor values. Missing inputs remain UNKNOWN;
the caller must provide accepted input identities before publication.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Mapping


CONTRACT_VERSION = "V4_04_CORE_PROFILE_RULES_V1"


@dataclass(frozen=True)
class State:
    value: str
    contract_id: str
    evidence: dict[str, float | bool | None]
    unknown_reason: str | None = None


def _number(inputs: Mapping[str, object], key: str) -> float | None:
    raw = inputs.get(key)
    if isinstance(raw, bool) or not isinstance(raw, (int, float)):
        return None
    value = float(raw)
    return value if isfinite(value) else None


def _state(value: str, contract: str, inputs: Mapping[str, object], keys: tuple[str, ...],
           reason: str | None = None) -> State:
    return State(value, contract, {key: inputs[key] if isinstance(inputs.get(key), bool)
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
    rules = (
        (c < ma20 and s20 < -0.1 and s60 < -0.1 and ll, "DOWNTREND_STRONG"),
        (c > ma20 and s20 > 0.1 and (c > ma60 or s60 > 0.1) and hh and not damage, "UPTREND_STRONG"),
        (c < ma20 and s20 < -0.1, "DOWNTREND"),
        (c > ma20 and s20 > 0.1 and not damage, "UPTREND"),
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
    value = ("EXTENDED" if bias >= 3 else "HIGH_ZONE" if pos >= .8 else
             "MID_HIGH" if pos >= .6 else "MID_ZONE" if pos >= .4 else
             "MID_LOW" if pos >= .2 else "LOW_ZONE")
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
    keys = ("range_ratio", "atr_ratio", "vol_ratio", "amount_ratio20")
    if not _required(inputs, keys) or not isinstance(inputs.get("minimum_liquidity"), bool):
        return _state("UNKNOWN", contract, inputs, keys, "REQUIRED_INPUT_UNKNOWN")
    ran, atr, vol, amount = (_number(inputs, x) for x in keys)
    liquid = inputs["minimum_liquidity"]
    value = ("EXPANDING_EXTREME" if atr >= 1.5 or vol >= 1.5 else
             "EXPANDING" if atr >= 1.1 or vol >= 1.1 else
             "COMPRESSING_STRONG" if ran <= .35 and atr <= .7 and vol <= .7 and amount <= .8 and liquid else
             "COMPRESSING" if ran <= .6 and atr <= .9 and vol <= .9 and liquid else "NORMAL")
    return _state(value, contract, inputs, keys)


def ratio_state(inputs: Mapping[str, object], key: str) -> State:
    contract = "AMOUNT_VOLUME_STATE_V1"
    if not _required(inputs, (key,)):
        return _state("UNKNOWN", contract, inputs, (key,), "REQUIRED_INPUT_UNKNOWN")
    ratio = _number(inputs, key)
    value = ("VERY_DRY" if ratio < .5 else "CONTRACTED" if ratio < .8 else
             "NORMAL" if ratio < 1.2 else "EXPANDED" if ratio < 2 else "VERY_EXPANDED")
    return _state(value, contract, inputs, (key,))


def participation(inputs: Mapping[str, object]) -> State:
    contract = "AMOUNT_VOLUME_STATE_V1"
    keys = ("amount_ratio20", "ret1", "clv")
    if not _required(inputs, keys[:2]):
        return _state("UNKNOWN", contract, inputs, keys, "REQUIRED_INPUT_UNKNOWN")
    amount, ret = (_number(inputs, x) for x in keys[:2])
    clv = _number(inputs, "clv")
    if amount >= 1.2 and ret < 0:
        value = "HIGH_PARTICIPATION_REVERSAL"
    elif amount >= 1.2 and ret > 0 and clv is None:
        return _state("UNKNOWN", contract, inputs, keys, "CLV_REQUIRED_FOR_BRANCH")
    elif amount >= 1.2 and ret > 0 and clv >= .7:
        value = "HIGH_PARTICIPATION_EFFECTIVE_ADVANCE"
    elif amount >= 1.2:
        value = "HIGH_PARTICIPATION_LOW_EFFICIENCY"
    elif amount < .8 and ret > 0:
        value = "LOW_PARTICIPATION_ADVANCE"
    elif amount < .8 and ret < 0:
        value = "LOW_PARTICIPATION_DECLINE"
    else:
        value = "NORMAL_PARTICIPATION"
    return _state(value, contract, inputs, keys)


def relative(inputs: Mapping[str, object], compression_state: str, ma_state: str) -> State:
    contract = "RELATIVE_STATE_V1"
    keys = ("rps5", "rps20", "rps20_delta3", "rel_market_1", "rel_market_5")
    if not _required(inputs, keys) or "UNKNOWN" in (compression_state, ma_state):
        return _state("UNKNOWN", contract, inputs, keys, "REQUIRED_INPUT_UNKNOWN")
    _, rps20, delta, rel1, _ = (_number(inputs, x) for x in keys)
    active = delta >= 10 and (compression_state in {"COMPRESSING", "COMPRESSING_STRONG"} or ma_state in {"BULL_TRANSITION", "BULL_ALIGNED"})
    value = ("ACTIVE_EMERGENCE" if active else
             "PASSIVE_RESILIENCE" if rel1 > 0 and delta <= 0 else
             "LEADING_ACCELERATING" if rps20 >= 80 and delta > 0 else
             "LEADING_STABLE" if rps20 >= 80 and delta >= -3 else
             "IMPROVING" if delta > 3 else "WEAKENING" if delta < -3 else
             "LAGGING" if rps20 < 20 else "NEUTRAL")
    return _state(value, contract, inputs, keys)


def extension_risk(inputs: Mapping[str, object]) -> State:
    contract = "EXTENSION_RISK_V1"
    keys = ("bias20_atr", "ret5", "atr20", "close", "amount_ratio20", "ret1")
    bias = _number(inputs, "bias20_atr")
    if bias is not None and bias >= 4:
        return _state("EXTREME", contract, inputs, keys)
    if bias is not None and bias >= 3:
        return _state("HIGH", contract, inputs, keys)
    if bias is None or not _required(inputs, keys[1:]) or _number(inputs, "close") <= 0:
        return _state("UNKNOWN", contract, inputs, keys, "REQUIRED_INPUT_UNKNOWN")
    ret5, atr, close, amount, ret1 = (_number(inputs, x) for x in keys[1:])
    value = "HIGH" if ret5 >= 3 * atr / close and amount >= 2 and ret1 <= 0 else "MEDIUM" if bias >= 2 else "LOW"
    return _state(value, contract, inputs, keys)
