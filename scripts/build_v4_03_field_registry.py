"""Expand the V4-03 scope freeze into one explicit metadata row per field."""

import hashlib
import json
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCOPE = ROOT / "config/v4_03_field_scope_map_v1.json"
OUTPUT = ROOT / "config/v4_03_field_registry_v1.json"
SCHEMA_OUTPUT = ROOT / "config/v4_03_output_schema_v1.json"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def describe(field):
    if field.startswith("rps"):
        return ("RPS_MIDRANK_V1" if "delta" not in field else "RPS_DELTA_V1", "percentage_points", "PIT historical universe, accepted adjusted daily")
    if field.startswith("rel_market"):
        return ("MARKET_RELATIVE_REFERENCE_V1", "return_fraction", "PIT start universe, accepted adjusted daily")
    if field.startswith("ret"):
        return ("CORE_FACTOR_V1.RET", "return_fraction", "accepted adjusted daily, trading status, exchange calendar")
    if field.startswith("vol") and not field.startswith("volume") and field != "vol_ratio":
        return ("CORE_FACTOR_V1.VOL", "log_return_std", "accepted adjusted daily, trading status, exchange calendar")
    if field in {"hh_progress", "ll_progress", "core_price_damage"}:
        return ("CORE_FACTOR_V1." + field.upper(), "boolean", "accepted adjusted daily, trading status")
    if field.startswith("amount"):
        return ("CORE_FACTOR_V1.AMOUNT_RATIO", "ratio", "accepted raw CNY amount, trading status")
    if field.startswith("volume"):
        return ("CORE_FACTOR_V1.VOLUME_RATIO", "ratio", "accepted raw volume, trading status")
    if field == "prior60_percentile":
        return ("CORE_FACTOR_V1.PRIOR60_PERCENTILE", "percentile_points", "accepted adjusted daily, trading status")
    if field.startswith("ma") or field.startswith("hhv") or field.startswith("llv") or field.startswith("prior_high") or field.startswith("prior_low") or field.startswith("atr") and field != "atr_ratio" or field == "tr":
        return ("CORE_FACTOR_V1.PRICE_TECHNICAL", "adjusted_price", "accepted adjusted daily, trading status")
    if field.startswith("slope"):
        return ("CORE_FACTOR_V1.SLOPE", "dimensionless", "accepted adjusted daily, trading status")
    return ("CORE_FACTOR_V1." + field.upper(), "ratio", "accepted adjusted daily, trading status")


def main():
    scope = json.loads(SCOPE.read_text(encoding="utf-8"))
    manifest = json.loads((ROOT / "reports/v4_02/V4_02_FINAL_STAGING_MANIFEST_R6.json").read_text(encoding="utf-8"))
    source = manifest["components"]["DAILY_R7"]["sha256"]
    result = []
    schema_fields = []
    for field, window in sorted(scope["produced_fields"].items()):
        family, unit, dataset = describe(field)
        cross = window == "CROSS_SECTION_SESSION_WINDOW_V1"
        row = {
            "field_id": field, "formula_family": family,
            "producer_contract_id": family, "owner_stage": "V4-03",
            "input_dataset": dataset, "price_basis": "raw_amount" if field.startswith("amount") else "accepted_raw_volume" if field.startswith("volume") else "verified_affine_adjusted_OHLC",
            "window_contract": window, "as_of": "fixed_market_session_t" if cross else "actual_bar_asof_t",
            "data_type": "boolean" if unit == "boolean" else "float64", "unit": unit,
            "requiredness": "REQUIRED", "nullable": True,
            "unknown_policy": "field_local_UNKNOWN_with_reason_no_imputation",
            "publication_permission": "V4_03_PRIMITIVE_ONLY",
            "consumer_stage": "V4-04",
            "source_digest_identity": source,
            "parameter_set_id": scope["parameter_set_id"]}
        result.append(row)
        schema_field = {
            "field_id": field, "type": "boolean" if unit == "boolean" else "float64",
            "unit": unit, "producer_contract_id": family, "producer_version": "1.0.0",
            "requiredness": "REQUIRED", "nullable": True,
            "as_of": "fixed_market_session_t" if cross else "actual_bar_asof_t",
            "quality_state": "OBSERVED|UNKNOWN",
            "missing_policy": "field_local_UNKNOWN_with_reason_no_imputation",
            "display_label": field}
        schema_field["output_digest"] = hashlib.sha256(
            json.dumps(schema_field, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
        schema_fields.append(schema_field)
    payload = {"contract_id": "V4_03_FIELD_REGISTRY_V1", "version": "1.0.0",
               "scope_map_sha256": sha(SCOPE), "frozen_dev_baseline_sha256": sha(ROOT / scope["input_head"]),
               "field_count": len(result), "fields": result,
               "deferred_fields": scope["deferred_fields"]}
    temp = OUTPUT.with_suffix(".json.tmp")
    temp.write_bytes((json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8"))
    os.replace(temp, OUTPUT)
    framework_path = ROOT / "config/v4_algorithm_contract_framework_v1_2_0.json"
    schema_payload = {"contract_id": "V4_03_OUTPUT_SCHEMA_V1", "version": "1.0.0",
                      "framework_contract_id": "V4_ALGORITHM_CONTRACT_FRAMEWORK_V1",
                      "framework_stage_id": "V4-00G-SCOPED-CORRECTIVE-REVISION-R1",
                      "framework_version": json.loads(framework_path.read_text(encoding="utf-8"))["version"],
                      "framework_sha256": sha(framework_path), "field_count": len(schema_fields),
                      "fields": schema_fields,
                      "digest_semantics": "output_digest is the stable digest of the field schema identity; actual artifact values bind their own row and output digests"}
    from src.v4.contracts.algorithm_contract import validate_output_field
    for field in schema_fields:
        validate_output_field(field)
    temp = SCHEMA_OUTPUT.with_suffix(".json.tmp")
    temp.write_bytes((json.dumps(schema_payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8"))
    os.replace(temp, SCHEMA_OUTPUT)
    print(f"{len(result)} field metadata rows")


if __name__ == "__main__":
    main()
