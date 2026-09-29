"""Materialize the reviewed V4-04 field and output contracts as JSON.

This generator only transcribes REV2 §§10B–10G/10I/87A. Any change to the
field table is a contract revision, not a runtime inference.
"""

from __future__ import annotations

import json
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "config"
PARAMETER_SET_ID = "V4_04_CORE_PROFILE_PARAMETER_SET_V1"
FIELDS = (
    # field, type, unit, contract, source, window, basis, required
    ("trend_state", "enum", "state", "TREND_STATE_V1", "V4-03 factors + V4-02 daily", "TECHNICAL_BAR_WINDOW_V1", "QFQ", True),
    ("weekly_trend_state", "enum", "state", "TREND_STATE_V1", "V4-02 formal weekly R7", "CLOSED_ONLY", "QFQ", True),
    ("monthly_trend_state", "enum", "state", "TREND_STATE_V1", "V4-02 formal monthly R7", "CLOSED_ONLY", "QFQ", True),
    ("position_state", "enum", "state", "POSITION_STATE_V1", "V4-03 factors + V4-02 daily", "TECHNICAL_BAR_WINDOW_V1", "QFQ", True),
    ("bias20_atr", "float64", "ATR_multiple", "POSITION_STATE_V1", "V4-03 factors + V4-02 daily", "TECHNICAL_BAR_WINDOW_V1", "QFQ", True),
    ("pos60", "float64", "ratio", "CORE_FACTOR_V1", "V4-03 accepted factors", "TECHNICAL_BAR_WINDOW_V1", "QFQ", True),
    ("pos250", "float64", "ratio", "POSITION_STATE_V1", "V4-02 daily", "TECHNICAL_BAR_WINDOW_V1", "QFQ", False),
    ("dist_high20_atr", "float64", "ATR_multiple", "POSITION_STATE_V1", "V4-03 factors + V4-02 daily", "TECHNICAL_BAR_WINDOW_V1", "QFQ", True),
    ("near_high20_state", "enum", "state", "POSITION_STATE_V1", "V4-03 factors + V4-02 daily", "TECHNICAL_BAR_WINDOW_V1", "QFQ", True),
    ("near_high60_state", "enum", "state", "POSITION_STATE_V1", "V4-03 factors + V4-02 daily", "TECHNICAL_BAR_WINDOW_V1", "QFQ", True),
    ("drawdown20_state", "enum", "state", "POSITION_STATE_V1", "V4-03 factors + V4-02 daily", "TECHNICAL_BAR_WINDOW_V1", "QFQ", True),
    ("drawdown60_state", "enum", "state", "POSITION_STATE_V1", "V4-03 factors + V4-02 daily", "TECHNICAL_BAR_WINDOW_V1", "QFQ", True),
    ("ma_structure_state", "enum", "state", "MA_STRUCTURE_V1", "V4-03 factors + V4-02 daily MA10", "TECHNICAL_BAR_WINDOW_V1", "QFQ", True),
    ("ma10", "float64", "adjusted_price", "V4_04_DERIVED_PRIMITIVES_V1", "V4-02 accepted daily", "TECHNICAL_BAR_WINDOW_V1", "QFQ", True),
    ("relative_market_state", "enum", "state", "RELATIVE_STATE_V1", "V4-03 accepted PIT factors + V4-04 states", "CROSS_SECTION_SESSION_WINDOW_V1", "QFQ", True),
    ("compression_state", "enum", "state", "COMPRESSION_STATE_V1", "V4-03 factors + V4-02 prior amount", "TECHNICAL_BAR_WINDOW_V1", "raw_CNY_amount", True),
    ("minimum_liquidity", "boolean", "flag", "V4_04_DERIVED_PRIMITIVES_V1", "V4-02 accepted prior20 raw CNY amount", "TECHNICAL_BAR_WINDOW_V1", "raw_CNY_amount", True),
    ("amount_state", "enum", "state", "AMOUNT_VOLUME_STATE_V1", "V4-03 accepted amount_ratio20", "TECHNICAL_BAR_WINDOW_V1", "raw_CNY_amount", True),
    ("volume_state", "enum", "state", "AMOUNT_VOLUME_STATE_V1", "V4-03 accepted volume_ratio20", "TECHNICAL_BAR_WINDOW_V1", "raw_volume", True),
    ("core_participation_result", "enum", "state", "AMOUNT_VOLUME_STATE_V1", "V4-03 accepted factors", "TECHNICAL_BAR_WINDOW_V1", "mixed_price_amount", True),
    ("core_extension_risk", "enum", "state", "EXTENSION_RISK_V1", "V4-03 factors + V4-02 daily", "TECHNICAL_BAR_WINDOW_V1", "QFQ_and_raw_amount", True),
    ("severe_extension", "boolean", "flag", "EXTENSION_RISK_V1", "core_extension_risk", "SAME_SESSION", "none", True),
    ("regime_ui", "enum", "state", "MARKET_REGIME_V1", "V4-03 accepted market regime axes", "MARKET_SESSION_REPLAY", "market_reference_path", True),
)

# Named engineering candidate values transcribed from REV2. No release or
# predictive efficacy is asserted by this parameter instance.
PARAMETERS = {
    "SLOPE_DEADBAND_ATR": (.1, "ATR_multiple"),
    "POSITION_EXTENDED_BIAS": (3, "ATR_multiple"),
    "POSITION_HIGH": (.8, "ratio"), "POSITION_MID_HIGH": (.6, "ratio"),
    "POSITION_MID": (.4, "ratio"), "POSITION_MID_LOW": (.2, "ratio"),
    "NEAR_HIGH_ATR": (.5, "ATR_multiple"),
    "DRAWDOWN_SHALLOW": (-.05, "return"), "DRAWDOWN_MODERATE": (-.15, "return"),
    "COMPRESS_EXTREME": (1.5, "ratio"), "COMPRESS_EXPAND": (1.1, "ratio"),
    "COMPRESS_STRONG_RANGE": (.35, "ratio"), "COMPRESS_STRONG_ATR_VOL": (.7, "ratio"),
    "COMPRESS_STRONG_AMOUNT": (.8, "ratio"), "COMPRESS_RANGE": (.6, "ratio"),
    "COMPRESS_ATR_VOL": (.9, "ratio"),
    "RATIO_VERY_DRY": (.5, "ratio"), "RATIO_CONTRACTED": (.8, "ratio"),
    "RATIO_NORMAL": (1.2, "ratio"), "RATIO_EXPANDED": (2, "ratio"),
    "PARTICIPATION_HIGH": (1.2, "ratio"), "PARTICIPATION_LOW": (.8, "ratio"),
    "PARTICIPATION_CLV": (.7, "ratio"),
    "RELATIVE_ACTIVE_DELTA": (10, "percentage_points"),
    "RELATIVE_LEADING_RPS": (80, "percentile"),
    "RELATIVE_IMPROVING_DELTA": (3, "percentage_points"),
    "RELATIVE_LAGGING_RPS": (20, "percentile"),
    "EXTENSION_EXTREME": (4, "ATR_multiple"), "EXTENSION_HIGH": (3, "ATR_multiple"),
    "EXTENSION_MEDIUM": (2, "ATR_multiple"),
    "EXTENSION_RET5_ATR": (3, "ATR_multiple"), "EXTENSION_AMOUNT": (2, "ratio"),
    "MINIMUM_LIQUIDITY_CNY": (20_000_000, "CNY"),
    "MA10_WINDOW": (10, "actual_bars"), "POS250_WINDOW": (250, "actual_bars"),
    "PRIOR_AMOUNT_WINDOW": (20, "prior_actual_bars"),
    "WEEKLY_MA_WINDOW": (5, "closed_periods"), "MONTHLY_MA_WINDOW": (3, "closed_periods"),
    "REGIME_SWITCH_SESSIONS": (2, "evaluable_market_sessions"),
}


def f(name: str) -> dict:
    return {"field": name}


def p(name: str) -> dict:
    return {"parameter_id": "V4_04_" + name}


def op(operator: str, *args) -> dict:
    return {"operator": operator, "args": list(args)}


def branches(*pairs) -> dict:
    return {"operator": "FIRST_TRUE", "branches": [{"value": value, "when": condition} for value, condition in pairs],
            "else": "UNKNOWN_IF_REQUIRED_INPUT_MISSING_ELSE_FINAL_BRANCH"}


def rule_asts() -> dict:
    gt = lambda a, b: op("GT", a, b)
    ge = lambda a, b: op("GE", a, b)
    lt = lambda a, b: op("LT", a, b)
    le = lambda a, b: op("LE", a, b)
    AND = lambda *xs: op("AND", *xs)
    OR = lambda *xs: op("OR", *xs)
    NOT = lambda x: op("NOT", x)
    TRUE = {"constant": True}
    ZERO = {"constant": 0}
    UP20 = gt(f("slope20"), p("SLOPE_DEADBAND_ATR"))
    UP60 = gt(f("slope60"), p("SLOPE_DEADBAND_ATR"))
    DOWN20 = lt(f("slope20"), op("NEG", p("SLOPE_DEADBAND_ATR")))
    DOWN60 = lt(f("slope60"), op("NEG", p("SLOPE_DEADBAND_ATR")))
    return {
        "TREND_STATE_V1.daily": branches(
            ("DOWNTREND_STRONG", AND(lt(f("close"), f("ma20")), DOWN20, DOWN60, f("ll_progress"))),
            ("UPTREND_STRONG", AND(gt(f("close"), f("ma20")), UP20, OR(gt(f("close"), f("ma60")), UP60), f("hh_progress"), NOT(f("core_price_damage")))),
            ("DOWNTREND", AND(lt(f("close"), f("ma20")), DOWN20)),
            ("UPTREND", AND(gt(f("close"), f("ma20")), UP20, NOT(f("core_price_damage")))),
            ("SIDEWAYS_WEAK", lt(f("close"), f("ma20"))),
            ("SIDEWAYS_STRONG", gt(f("close"), f("ma20"))),
            ("SIDEWAYS", TRUE)),
        "TREND_STATE_V1.closed_period": {"operator": "CLOSED_PERIOD_TREND", "required_period_view": "CLOSED_ONLY",
                                         "weekly_window_parameter_id": p("WEEKLY_MA_WINDOW"),
                                         "monthly_window_parameter_id": p("MONTHLY_MA_WINDOW"),
                                         "up": AND(gt(f("close"), f("ma_current")), gt(f("ma_current"), f("ma_previous"))),
                                         "down": AND(lt(f("close"), f("ma_current")), lt(f("ma_current"), f("ma_previous"))),
                                         "else": "FLAT"},
        "POSITION_STATE_V1": branches(
            ("EXTENDED", ge(f("bias20_atr"), p("POSITION_EXTENDED_BIAS"))),
            ("HIGH_ZONE", ge(f("pos60"), p("POSITION_HIGH"))),
            ("MID_HIGH", ge(f("pos60"), p("POSITION_MID_HIGH"))),
            ("MID_ZONE", ge(f("pos60"), p("POSITION_MID"))),
            ("MID_LOW", ge(f("pos60"), p("POSITION_MID_LOW"))),
            ("LOW_ZONE", TRUE)),
        "MA_STRUCTURE_V1": branches(
            ("BULL_ALIGNED", AND(gt(f("ma5"), f("ma10")), gt(f("ma10"), f("ma20")), gt(f("slope20"), ZERO))),
            ("BEAR_ALIGNED", AND(lt(f("ma5"), f("ma10")), lt(f("ma10"), f("ma20")), lt(f("slope20"), ZERO))),
            ("BULL_TRANSITION", AND(gt(f("ma5"), f("ma20")), ge(f("slope20"), ZERO))),
            ("BEAR_TRANSITION", AND(lt(f("ma5"), f("ma20")), le(f("slope20"), ZERO))),
            ("MIXED", TRUE)),
        "COMPRESSION_STATE_V1": branches(
            ("EXPANDING_EXTREME", OR(ge(f("atr_ratio"), p("COMPRESS_EXTREME")), ge(f("vol_ratio"), p("COMPRESS_EXTREME")))),
            ("EXPANDING", OR(ge(f("atr_ratio"), p("COMPRESS_EXPAND")), ge(f("vol_ratio"), p("COMPRESS_EXPAND")))),
            ("COMPRESSING_STRONG", AND(le(f("range_ratio"), p("COMPRESS_STRONG_RANGE")), le(f("atr_ratio"), p("COMPRESS_STRONG_ATR_VOL")), le(f("vol_ratio"), p("COMPRESS_STRONG_ATR_VOL")), le(f("amount_ratio20"), p("COMPRESS_STRONG_AMOUNT")), f("minimum_liquidity"))),
            ("COMPRESSING", AND(le(f("range_ratio"), p("COMPRESS_RANGE")), le(f("atr_ratio"), p("COMPRESS_ATR_VOL")), le(f("vol_ratio"), p("COMPRESS_ATR_VOL")), f("minimum_liquidity"))),
            ("NORMAL", TRUE)),
        "RELATIVE_STATE_V1": branches(
            ("ACTIVE_EMERGENCE", AND(ge(f("rps20_delta3"), p("RELATIVE_ACTIVE_DELTA")), OR(op("IN", f("compression_state"), {"set": ["COMPRESSING", "COMPRESSING_STRONG"]}), op("IN", f("ma_structure_state"), {"set": ["BULL_TRANSITION", "BULL_ALIGNED"]})))),
            ("PASSIVE_RESILIENCE", AND(gt(f("rel_market_1"), ZERO), le(f("rps20_delta3"), ZERO))),
            ("LEADING_ACCELERATING", AND(ge(f("rps20"), p("RELATIVE_LEADING_RPS")), gt(f("rps20_delta3"), ZERO))),
            ("LEADING_STABLE", AND(ge(f("rps20"), p("RELATIVE_LEADING_RPS")), ge(f("rps20_delta3"), op("NEG", p("RELATIVE_IMPROVING_DELTA"))))),
            ("IMPROVING", gt(f("rps20_delta3"), p("RELATIVE_IMPROVING_DELTA"))),
            ("WEAKENING", lt(f("rps20_delta3"), op("NEG", p("RELATIVE_IMPROVING_DELTA")))),
            ("LAGGING", lt(f("rps20"), p("RELATIVE_LAGGING_RPS"))),
            ("NEUTRAL", TRUE)),
        "AMOUNT_VOLUME_STATE_V1.ratio": branches(
            ("VERY_DRY", lt(f("ratio20"), p("RATIO_VERY_DRY"))),
            ("CONTRACTED", lt(f("ratio20"), p("RATIO_CONTRACTED"))),
            ("NORMAL", lt(f("ratio20"), p("RATIO_NORMAL"))),
            ("EXPANDED", lt(f("ratio20"), p("RATIO_EXPANDED"))),
            ("VERY_EXPANDED", TRUE)),
        "AMOUNT_VOLUME_STATE_V1.participation": branches(
            ("HIGH_PARTICIPATION_REVERSAL", AND(ge(f("amount_ratio20"), p("PARTICIPATION_HIGH")), lt(f("ret1"), ZERO))),
            ("HIGH_PARTICIPATION_EFFECTIVE_ADVANCE", AND(ge(f("amount_ratio20"), p("PARTICIPATION_HIGH")), gt(f("ret1"), ZERO), ge(f("clv"), p("PARTICIPATION_CLV")))),
            ("HIGH_PARTICIPATION_LOW_EFFICIENCY", ge(f("amount_ratio20"), p("PARTICIPATION_HIGH"))),
            ("LOW_PARTICIPATION_ADVANCE", AND(lt(f("amount_ratio20"), p("PARTICIPATION_LOW")), gt(f("ret1"), ZERO))),
            ("LOW_PARTICIPATION_DECLINE", AND(lt(f("amount_ratio20"), p("PARTICIPATION_LOW")), lt(f("ret1"), ZERO))),
            ("NORMAL_PARTICIPATION", TRUE)),
        "EXTENSION_RISK_V1": branches(
            ("EXTREME", ge(f("bias20_atr"), p("EXTENSION_EXTREME"))),
            ("HIGH", OR(ge(f("bias20_atr"), p("EXTENSION_HIGH")), AND(ge(f("ret5"), op("DIV", op("MUL", p("EXTENSION_RET5_ATR"), f("atr20")), f("close"))), ge(f("amount_ratio20"), p("EXTENSION_AMOUNT")), le(f("ret1"), ZERO)))),
            ("MEDIUM", ge(f("bias20_atr"), p("EXTENSION_MEDIUM"))),
            ("LOW", TRUE)),
        "POSITION_STATE_V1.near_high": {"operator": "CLASSIFY_DISTANCE", "distance_ast": op("DIV", op("SUB", f("prior_highN"), f("close")), f("atr20")),
                                        "branches": branches(("ABOVE_PRIOR_HIGH", lt(f("distance"), ZERO)),
                                                             ("NEAR", le(f("distance"), p("NEAR_HIGH_ATR"))),
                                                             ("BELOW", TRUE)), "horizons": [20, 60]},
        "POSITION_STATE_V1.drawdown": {"operator": "CLASSIFY_DRAWDOWN", "drawdown_ast": op("SUB", op("DIV", f("close"), f("hhvN")), {"constant": 1}),
                                       "branches": branches(("SHALLOW", ge(f("drawdown"), p("DRAWDOWN_SHALLOW"))),
                                                            ("MODERATE", ge(f("drawdown"), p("DRAWDOWN_MODERATE"))),
                                                            ("DEEP", TRUE)), "horizons": [20, 60]},
        "EXTENSION_RISK_V1.severe": {"operator": "EQ", "args": [f("core_extension_risk"), {"constant": "EXTREME"}],
                                     "unknown_policy": "UNKNOWN_IF_RISK_UNKNOWN"},
        "V4_04_DERIVED_PRIMITIVES_V1": {
            "ma10": {"operator": "MEAN", "window_parameter_id": p("MA10_WINDOW"), "include_current": True,
                     "source": "accepted_QFQ_close", "window_contract_id": "TECHNICAL_BAR_WINDOW_V1"},
            "pos250": {"operator": "DIV", "args": [op("SUB", f("close"), f("LLV250")), op("SUB", f("HHV250"), f("LLV250"))],
                       "window_parameter_id": p("POS250_WINDOW"), "zero_denominator": "UNKNOWN"},
            "minimum_liquidity": {"operator": "GE", "args": [{"operator": "MEAN", "source": "accepted_raw_CNY_amount",
                                                              "window_parameter_id": p("PRIOR_AMOUNT_WINDOW"), "include_current": False},
                                                             p("MINIMUM_LIQUIDITY_CNY")]},
            "bias20_atr": {"operator": "DIV", "args": [op("SUB", f("close"), f("ma20")), f("atr20")], "zero_denominator": "UNKNOWN"},
            "dist_high20_atr": {"operator": "DIV", "args": [op("SUB", f("prior_high20"), f("close")), f("atr20")], "zero_denominator": "UNKNOWN"},
        },
        "MARKET_REGIME_V1.regime_ui": {
            "operator": "HYSTERETIC_FIRST_TRUE", "switch_sessions_parameter_id": p("REGIME_SWITCH_SESSIONS"),
            "required_axes": ["trend_axis", "breadth_axis", "participation_axis", "stress_level", "stress_change"],
            "immediate_labels": ["CAPITULATION"], "unknown_output": "UNKNOWN_WITH_LAST_KNOWN",
            "candidate": branches(
                ("CAPITULATION", AND(op("EQ", f("trend_axis"), {"constant": "WEAK"}), op("EQ", f("stress_level"), {"constant": "HIGH"}))),
                ("RECOVERY_ATTEMPT", AND(op("EQ", f("trend_axis"), {"constant": "WEAK"}), op("EQ", f("breadth_axis"), {"constant": "IMPROVING"}), op("EQ", f("stress_change"), {"constant": "DECLINING"}))),
                ("RISK_ON", AND(op("EQ", f("trend_axis"), {"constant": "STRONG"}), NOT(op("EQ", f("breadth_axis"), {"constant": "DETERIORATING"})), op("EQ", f("stress_level"), {"constant": "LOW"}))),
                ("RISK_OFF", OR(op("EQ", f("trend_axis"), {"constant": "WEAK"}), op("EQ", f("stress_level"), {"constant": "HIGH"}))),
                ("NEUTRAL", TRUE)),
        },
    }


def write(name: str, payload: dict) -> None:
    target = OUT / name
    tmp = target.with_suffix(target.suffix + ".tmp")
    tmp.write_bytes((json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8"))
    os.replace(tmp, target)


def main() -> None:
    write("v4_04_parameter_set_v1.json", {
        "contract_id": "V4_04_PARAMETER_SET_V1", "parameter_set_id": PARAMETER_SET_ID,
        "status": "ENGINEERING_CANDIDATE", "governing_source": "REV2 §§10B–10G, 10I, 72",
        "parameters": [{"parameter_id": "V4_04_" + name, "value": value, "unit": unit,
                        "contract_scope": "V4_04_CORE_PROFILE_RULES_V1", "minimum": None,
                        "maximum": None, "inclusive_boundaries": "per_rule_AST",
                        "status": "ENGINEERING_CANDIDATE", "reason": "REV2 named candidate literal",
                        "introduced_version": "V4.2.2-CODEX-REV2", "approved_at": None,
                        "supersedes": None} for name, (value, unit) in PARAMETERS.items()],
    })
    records = []
    for field, dtype, unit, contract, source, window, basis, required in FIELDS:
        records.append({
            "field_id": field, "data_type": dtype, "unit": unit,
            "producer": ("accepted_V4_03" if contract == "CORE_FACTOR_V1" else
                         "src.v4.market_regime_ui" if contract == "MARKET_REGIME_V1" else
                         "src.v4.profile_primitives" if contract == "V4_04_DERIVED_PRIMITIVES_V1" else
                         "src.v4.profile_core"),
            "producer_contract_id": contract, "parameter_set_id": PARAMETER_SET_ID if contract != "CORE_FACTOR_V1" else "V4_03_CORE_FACTOR_PARAMETER_SET_V1",
            "required": required, "time_semantics": "asof_T_no_future_closed_only" if window == "CLOSED_ONLY" else "actual_bar_asof_T",
            "window_semantics": window, "price_basis": basis, "source_identity": source,
            "source_authority": "data/v4/V4_STAGE_ACCEPTED_HEAD.json -> src.v4.accepted_input.resolve",
            "unknown_policy": "field_local_UNKNOWN_with_reason_no_imputation",
            "quality_propagation": "UNKNOWN_if_required_input_unknown; preserve_input_quality",
            "output_digest_semantics": "SHA256_canonical_json_of_value_contract_parameters_evidence_source_identity",
            "consumer_stage": "V4-04",
        })
    write("v4_04_field_registry_v1.json", {"contract_id": "V4_04_FIELD_REGISTRY_V1", "version": "1.0.0", "fields": records})
    write("v4_04_output_schema_v1.json", {
        "contract_id": "V4_04_OUTPUT_SCHEMA_V1", "version": "1.0.0", "field_registry": "config/v4_04_field_registry_v1.json",
        "required_row_identity": ["security_id", "symbol", "trade_date", "board", "source_cutoff", "publication_id"],
        "required_envelopes": ["states", "derived_fields", "primitive_quality", "profile_component_status", "profile_quality", "source_asof", "technical_window_identity", "source_digest", "output_digest"],
        "state_envelope": ["value", "contract_id", "parameter_set_id", "evidence", "input_digest", "source_digest", "contract_digest", "output_digest", "unknown_reason"],
        "derived_envelope": ["value", "quality", "unknown_reason", "contract_id", "parameter_set_id", "input_digest", "window_identity", "source_digest", "contract_digest", "output_digest", "actual_count", "calendar_span"],
        "allowed_component_status": ["READY", "PARTIAL", "UNKNOWN_DATA", "NOT_IMPLEMENTED", "NOT_APPLICABLE", "PENDING_SOURCE", "DEGRADED"],
        "required_boards": ["SH_MAIN", "SZ_MAIN", "CHINEXT", "STAR"], "cutoff": "2026-09-24",
    })
    write("v4_04_algorithm_contracts_v1.json", {
        "contract_id": "V4_04_ALGORITHM_CONTRACTS_V1", "version": "1.0.0",
        "governing_document": "docs/evidence/A_SHARE_RESEARCH_SYSTEM_V4_2_2_FINAL_EXECUTABLE_CONTRACT_REV2_20260925.md",
        "sections": ["10B", "10C", "10D", "10E", "10F", "10G", "10I", "72", "73", "78", "81.4", "87A"],
        "parameter_set_id": PARAMETER_SET_ID,
        "parameter_registry": "config/v4_04_parameter_set_v1.json",
        "frozen_literals": {
            "slope_deadband_atr": {"value": 0.1, "source": "REV2 §10B/§72"},
            "minimum_liquidity_prior20_cny": {"value": 20000000, "source": "REV2 §10F/§72"},
            "minimum_liquidity_window": {"value": 20, "source": "REV2 §10F/§72"},
            "weekly_ma_window": {"value": 5, "source": "REV2 §10B"},
            "monthly_ma_window": {"value": 3, "source": "REV2 §10B"},
        },
        "ast_version": "V4_04_RULE_AST_V1",
        "rules": rule_asts(),
        "unknown_policy": "three_valued_branch_required; UNKNOWN_if_required_input_unavailable",
        "implementation": "src/v4/profile_core.py",
    })


if __name__ == "__main__":
    main()
