"""Build output-schema and identity contracts for V4-03 native primitives."""

import hashlib
import json
import os
from pathlib import Path

from src.v4.contracts.algorithm_contract import validate_output_field


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "config/v4_03_native_contract_registry_v1.json"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


def schema(field_id, data_type, unit, producer, as_of, policy):
    row = {"field_id": field_id, "type": data_type, "unit": unit,
           "producer_contract_id": producer, "producer_version": "1.0.0",
           "requiredness": "REQUIRED", "nullable": True, "as_of": as_of,
           "quality_state": "OBSERVED|UNKNOWN", "missing_policy": policy,
           "display_label": field_id}
    row["output_digest"] = digest(row)
    validate_output_field(row)
    return row


def contract(contract_id, outputs, *, inputs, time_semantics, identity_fields,
             window_contract, algorithm, quality, consumer, publication):
    return {"contract_id": contract_id, "contract_version": "1.0.0",
            "parameter_set_id": "V4_03_CORE_FACTOR_PARAMETER_SET_V1",
            "producer": {"producer_contract_id": contract_id, "version": "1.0.0"},
            "inputs": inputs, "time_semantics": time_semantics,
            "window_contract": window_contract, "algorithm": algorithm,
            "quality_contract": quality, "identity_fields": identity_fields,
            "input_digest_semantics": "SHA256 of canonical sorted input identities, values, source artifact digests, and contract version",
            "outputs": outputs, "consumer_stage": consumer,
            "publication_permission": publication}


def input_field(field_id, data_type, unit, source):
    return {"field_id": field_id, "type": data_type, "unit": unit, "source": source, "required": True}


def main():
    scope_path = ROOT / "config/v4_03_native_scope_map_v1.json"
    extension_path = ROOT / "config/v4_algorithm_contract_framework_v1_2_0.json"
    native_path = ROOT / "src/v4/factors/native.py"
    relative_path = ROOT / "src/v4/factors/relative.py"
    params_path = ROOT / "config/v4_03_parameter_registry_v1.json"
    scope = json.loads(scope_path.read_text(encoding="utf-8"))
    source_ids = {"native_sha256": sha(native_path), "relative_sha256": sha(relative_path),
                  "scope_map_sha256": sha(scope_path), "framework_extension_sha256": sha(extension_path),
                  "parameter_registry_sha256": sha(params_path)}
    producer = "MARKET_RELATIVE_REFERENCE_V1"
    market_ref_fields = [
        schema("reference_return", "float64", "return_fraction", producer, "fixed_market_session_t", "UNKNOWN_if_missing_fraction_exceeds_registered_limit"),
        schema("universe_count", "integer", "members", producer, "fixed_market_session_t", "retain_zero_count_and_quality"),
        schema("evaluable_count", "integer", "members", producer, "fixed_market_session_t", "retain_zero_count_and_quality"),
        schema("missing_count", "integer", "members", producer, "fixed_market_session_t", "retain_zero_count_and_quality"),
        schema("coverage", "float64", "fraction", producer, "fixed_market_session_t", "null_only_when_universe_empty"),
        schema("evaluable_set_identity", "string", "sha256", producer, "fixed_market_session_t", "required_identity"),
        schema("window_identity", "string", "sha256", producer, "fixed_market_session_t", "required_identity"),
        schema("adjustment_basis_id", "string", "sha256_or_versioned_set_id", producer, "fixed_market_session_t", "required_identity"),
        schema("input_source_digest", "string", "sha256", producer, "fixed_market_session_t", "required_identity")]
    contracts = [contract(
        producer, market_ref_fields,
        inputs=[input_field("endpoint_return", "float64", "return_fraction", "V4_02_ACCEPTED_ADJUSTED_DAILY"),
                input_field("pit_start_universe", "member_set", "security_ids", "V4_01_ACCEPTED_HISTORICAL_UNIVERSE")],
        time_semantics="fixed start_session=t-N and end_session=t; endpoint does not shift",
        identity_fields=["market_calendar_id", "start_session", "end_session", "start_universe_snapshot_id", "evaluable_set_identity", "adjustment_basis_id", "input_source_digest"],
        window_contract="CROSS_SECTION_SESSION_WINDOW_V1",
        algorithm={"expression": "equal_weight_mean(endpoint_return for evaluable members in the PIT universe at start_session)",
                   "missing_gate_parameter_id": "V4_03_MARKET_REFERENCE_MAX_MISSING_FRACTION",
                   "endpoint_reference_is_daily_path": False},
        quality={"evaluable_rule": "finite return and verified same-security adjustment identity at both fixed endpoints",
                 "unknown_reason": "EMPTY_START_UNIVERSE or MISSING_COVERAGE_EXCEEDED when missing_fraction > registered threshold",
                 "do_not_substitute_current_survivors": True},
        consumer="V4-04", publication="V4_03_PRIMITIVE_ONLY")]

    path_contract_id = "V4_03_MARKET_REFERENCE_PATH_V1"
    path_fields = [
        schema("market_return_1", "float64", "return_fraction", path_contract_id, "fixed_market_session_t", "UNKNOWN_suffix_after_missing_daily_return"),
        schema("path_level", "float64", "index_level", path_contract_id, "fixed_market_session_t", "UNKNOWN_suffix_after_missing_daily_return"),
        schema("universe_count", "integer", "members", path_contract_id, "fixed_market_session_t", "retain_zero_count_and_quality"),
        schema("evaluable_count", "integer", "members", path_contract_id, "fixed_market_session_t", "retain_zero_count_and_quality"),
        schema("coverage", "float64", "fraction", path_contract_id, "fixed_market_session_t", "null_only_when_universe_empty"),
        schema("start_universe_snapshot_id", "string", "sha256", path_contract_id, "fixed_market_session_t", "required_identity"),
        schema("window_identity", "string", "sha256", path_contract_id, "fixed_market_session_t", "required_identity"),
        schema("input_source_digest", "string", "sha256", path_contract_id, "fixed_market_session_t", "required_identity")]
    contracts.append(contract(
        path_contract_id, path_fields,
        inputs=[input_field("endpoint_return_1", "float64", "return_fraction", "MARKET_RELATIVE_REFERENCE_V1"),
                input_field("pit_start_universe", "member_set", "security_ids", "V4_01_ACCEPTED_HISTORICAL_UNIVERSE")],
        time_semantics="one row per fixed market session, daily rebalanced equal-weight research index",
        identity_fields=["market_calendar_id", "start_session", "end_session", "start_universe_snapshot_id", "evaluable_set_identity", "adjustment_basis_id", "input_source_digest", "series_version"],
        window_contract="CROSS_SECTION_SESSION_WINDOW_V1",
        algorithm={"expression": "level[t] = level[t-1] * (1 + equal_weight_mean(ret1[t]))",
                   "base_level": 1.0, "path_identity": "DAILY_REBALANCED_RESEARCH_INDEX",
                   "rebase_policy": "UNKNOWN_SUFFIX_UNTIL_NEW_SERIES_VERSION"},
        quality={"daily_return_universe": "PIT universe at the interval start", "missing_gate_parameter_id": "V4_03_MARKET_REFERENCE_MAX_MISSING_FRACTION",
                 "unknown_reason": "unknown daily return breaks all later path rows in this series version"},
        consumer="V4-04", publication="V4_03_HISTORICAL_PATH_ONLY"))

    trend_path = ROOT / "config/v4_03_market_regime_trend_amendment_v1.json"
    trend = json.loads(trend_path.read_text(encoding="utf-8"))
    regime_id = "MARKET_REGIME_V1_PRIMITIVES"
    regime_fields = [schema(name, "enum", "axis_state", regime_id, "fixed_market_session_t", "UNKNOWN_when_required_input_unknown")
                     for name in ("breadth_axis", "participation_axis", "stress_level", "stress_change", "trend_axis")]
    contracts.append(contract(
        regime_id, regime_fields,
        inputs=[input_field("breadth", "float64", "fraction", "V4_03_MARKET_NATIVE_INPUTS"),
                input_field("participation", "float64", "ratio", "V4_03_MARKET_NATIVE_INPUTS"),
                input_field("limit_coverage", "float64", "fraction", "V4_02_ACCEPTED_PRICE_LIMIT_FACTS"),
                input_field("stress_ratio", "float64", "fraction", "V4_03_MARKET_NATIVE_INPUTS"),
                input_field("prior_stress_ratio", "float64", "fraction", "V4_03_MARKET_NATIVE_INPUTS"),
                input_field("trend_close", "float64", "adjusted_price", "V4_02_ACCEPTED_ADJUSTED_DAILY"),
                input_field("trend_ma20", "float64", "adjusted_price", "V4_03_CORE_FACTOR_DAILY_V1"),
                input_field("trend_ma20_t_minus_5", "float64", "adjusted_price", "V4_03_CORE_FACTOR_DAILY_V1")],
        time_semantics="fixed market session t; trend comparison additionally consumes t-5",
        identity_fields=["trade_date", "market_calendar_id", "market_snapshot_id", "adjustment_basis_id", "input_source_digest", "parameter_set_id"],
        window_contract="CROSS_SECTION_SESSION_WINDOW_V1",
        algorithm={"rule_table": {"breadth_axis": {"gt_positive_threshold": "IMPROVING", "lt_negative_threshold": "DETERIORATING", "otherwise": "STABLE"},
                                   "participation_axis": {"gte_expanding_threshold": "EXPANDING", "lt_thin_threshold": "THIN", "otherwise": "NORMAL"},
                                   "stress_level": {"minimum_limit_coverage_parameter_id": "V4_03_MARKET_LIMIT_COVERAGE_MINIMUM", "gte_high_threshold": "HIGH", "gte_elevated_threshold": "ELEVATED", "otherwise": "LOW"},
                                   "stress_change": {"gt_prior": "RISING", "lt_prior": "DECLINING", "equal": "STABLE"},
                                   "trend_axis": {"amendment_contract_id": trend["contract_id"], "amendment_version": trend["version"], "amendment_sha256": sha(trend_path)}},
                   "formal_regime_ui_published": False},
        quality={"field_local_unknown": True, "regime_ui_publication": "NOT_PUBLISHED_V4_03"},
        consumer="V4-04", publication="V4_03_PRIMITIVE_ONLY"))

    sector_id = "V4_03_SECTOR_NATIVE_PRIMITIVE_V1"
    sector_field_specs = [
        ("member_set_identity", "string", "sha256"), ("member_count", "integer", "members"),
        ("input_row_count", "integer", "rows"), ("raw_quote_evaluable_count", "integer", "members"),
        ("raw_quote_coverage", "float64", "fraction"), ("amount_evaluable_count", "integer", "members"),
        ("amount_median_primitive", "float64", "raw_CNY"), ("positive_breadth_numerator", "integer", "members"),
        ("positive_breadth_denominator", "integer", "members"), ("ma20_width_numerator", "integer", "members"),
        ("ma20_width_denominator", "integer", "members"), ("amount_concentration_evaluable_count", "integer", "members"),
        ("amount_concentration_numerator", "float64", "raw_CNY"), ("amount_concentration_denominator", "float64", "raw_CNY")]
    sector_fields = [schema(name, kind, unit, sector_id, "fixed_market_session_t", "metric_specific_field_local_unknown_policy")
                     for name, kind, unit in sector_field_specs]
    contracts.append(contract(
        sector_id, sector_fields,
        inputs=[input_field("pit_sector_members", "member_set", "security_ids", "EXPLICIT_ACCEPTED_SECTOR_MEMBERSHIP_INPUT_REQUIRED"),
                input_field("quote_quality_state", "quality_enum", "quality", "FIELD_LOCAL_INPUT"),
                input_field("amount_quality_state", "quality_enum", "quality", "FIELD_LOCAL_INPUT"),
                input_field("ret1_quality_state", "quality_enum", "quality", "FIELD_LOCAL_INPUT"),
                input_field("ma20_quality_state", "quality_enum", "quality", "FIELD_LOCAL_INPUT"),
                input_field("amount", "float64", "raw_CNY", "V4_02_ACCEPTED_RAW_DAILY"),
                input_field("ret1", "float64", "return_fraction", "V4_03_CORE_FACTOR_DAILY_V1"),
                input_field("above_ma20", "boolean", "boolean", "V4_03_CORE_FACTOR_DAILY_V1")],
        time_semantics="fixed market session t with historical accepted sector membership snapshot",
        identity_fields=["trade_date", "market_calendar_id", "sector_membership_snapshot_id", "member_set_identity", "adjustment_basis_id", "input_source_digest"],
        window_contract="CROSS_SECTION_SESSION_WINDOW_V1",
        algorithm={"member_set_normalization": "sorted unique security IDs",
                   "field_quality_rules": json.loads(scope_path.read_text(encoding="utf-8"))["sector_metric_evaluability"],
                   "row_level_quality_gate": "PROHIBITED",
                   "qualification_or_rank_operations": "NONE"},
        quality={"quality_is_field_local": True, "empty_field_set": "UNKNOWN with explicit reason; count outputs remain zero",
                 "publication_permission": "NOT_V4_08_SECTOR_FACTORS"},
        consumer="V4-08", publication="NOT_V4_08_SECTOR_FACTORS"))

    for item in contracts:
        item["source_digest"] = digest({"contract": item, "source_ids": source_ids})
        item["source_ids"] = source_ids
    payload = {"contract_id": "V4_03_NATIVE_CONTRACT_REGISTRY_V1", "version": "1.0.0",
               "framework_extension": "V4_ALGORITHM_CONTRACT_FRAMEWORK_V1@1.2.0",
               "framework_extension_sha256": source_ids["framework_extension_sha256"],
               "scope_map_sha256": source_ids["scope_map_sha256"],
               "contract_count": len(contracts), "contracts": contracts,
               "sector_full_market_materialization": scope["sector_materialization"],
               "status": "CONTRACTS_BOUND_SECTOR_FULL_MARKET_INPUT_BLOCKED"}
    temp = OUTPUT.with_suffix(".json.tmp")
    temp.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    os.replace(temp, OUTPUT)
    print(f"{len(contracts)} native contracts generated; sector input gate={scope['sector_materialization']['status']}")


if __name__ == "__main__":
    main()
