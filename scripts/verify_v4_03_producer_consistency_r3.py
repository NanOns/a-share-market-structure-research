"""Check V4-03 producer identities, including the separate trend erratum."""

import gzip
import hashlib
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "reports/v4_03/V4_03_CONTRACT_PRODUCER_CONSISTENCY_R3.json"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check(scope, registry, schema, contracts, runtime_row, stock_runtime=None):
    failures = []
    native_outputs = {field["field_id"]: field["producer_contract_id"]
                      for contract in registry["contracts"] for field in contract["outputs"]}
    trend_scope = next(item["producer_contract_id"] for item in scope["market_primitives"] if item["field_id"] == "trend_axis")
    trend_runtime = runtime_row["producer_contracts"]["trend_axis"]
    trend_refs = [item for item in registry["contracts"] if item["contract_id"] == "MARKET_REGIME_V1_PRIMITIVES"][0]["algorithm"]["rule_table"]["trend_axis"]
    trend_registry = trend_refs["amendment_contract_id"]
    if "trend_axis" in native_outputs or len({trend_scope, trend_runtime, trend_registry}) != 1:
        failures.append("trend_axis_has_multiple_or_mismatched_producers")
    for field in ("breadth_axis", "participation_axis", "stress_level", "stress_change"):
        if native_outputs.get(field) != runtime_row["producer_contracts"].get(field):
            failures.append(f"native_producer_mismatch:{field}")
    by_contract = {c["outputs"][0]["field_id"]: c["producer"]["producer_contract_id"] for c in contracts["contracts"]}
    schema_map = {f["field_id"]: f["producer_contract_id"] for f in schema["fields"]}
    if set(schema_map) != set(by_contract) or len(schema_map) != 47:
        failures.append("stock_schema_contract_field_set_mismatch")
    for field, producer in schema_map.items():
        if by_contract.get(field) != producer:
            failures.append(f"stock_schema_contract_producer_mismatch:{field}")
        if stock_runtime is not None:
            observed = stock_runtime["fields"].get(field, {}).get("contract_id")
            expected_runtime = "CORE_FACTOR_V1" if producer.startswith("CORE_FACTOR_V1.") else producer
            if observed != expected_runtime:
                failures.append(f"stock_runtime_producer_mismatch:{field}")
    return failures, {"trend_scope": trend_scope, "trend_registry_reference": trend_registry,
                      "trend_runtime": trend_runtime, "stock_fields": len(schema_map)}


def main():
    scope_path = ROOT / "config/v4_03_native_scope_map_v1.json"
    registry_path = ROOT / "config/v4_03_native_contract_registry_v1.json"
    schema_path = ROOT / "config/v4_03_output_schema_v1.json"
    contracts_path = ROOT / "config/v4_03_algorithm_contracts_v1.json"
    candidate_path = ROOT / "reports/v4_03/staging/V4_03_MARKET_REGIME_NATIVE_CANDIDATE_R3.jsonl.gz"
    scope, registry, schema, contracts = [json.loads(p.read_text(encoding="utf-8"))
                                           for p in (scope_path, registry_path, schema_path, contracts_path)]
    runtime_row = json.loads(next(gzip.open(candidate_path, "rt", encoding="utf-8")))
    stock_path = ROOT / "reports/v4_03/staging/V4_03_FULL_SCOPE_CANDIDATE_R3.jsonl.gz"
    stock_runtime = json.loads(next(gzip.open(stock_path, "rt", encoding="utf-8")))
    failures, identities = check(scope, registry, schema, contracts, runtime_row, stock_runtime)
    report = {"contract_id": "V4_03_CONTRACT_PRODUCER_CONSISTENCY_R3", "status": "PASS" if not failures else "FAIL",
              "governing_task": "docs/audits/V4_03_R3_EXTERNAL_BLOCKER_CLOSURE_TASK_20260928.md",
              "identities": identities, "failures": failures,
              "source_hashes": {"native_scope": sha(scope_path), "native_registry": sha(registry_path),
                                "stock_schema": sha(schema_path), "stock_contracts": sha(contracts_path),
                                "regime_candidate": sha(candidate_path), "full_scope_candidate": sha(stock_path)},
              "stage_acceptance": "NOT_GRANTED"}
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    tmp = OUTPUT.with_suffix(OUTPUT.suffix + ".tmp")
    tmp.write_text(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, OUTPUT)
    if failures:
        raise RuntimeError(failures)
    print(json.dumps({"status": report["status"], "trend_producer": identities["trend_scope"]}))


if __name__ == "__main__":
    main()
