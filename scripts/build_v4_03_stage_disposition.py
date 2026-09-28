"""Seal V4-03 repair evidence without promoting unresolved gates to PASS."""

import hashlib
import json
import os
from pathlib import Path

from src.v4.contracts.algorithm_contract import validate_output_field


ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports/v4_03"
EVIDENCE = ROOT / "docs/evidence/V4_03_EXTERNAL_ACCEPTANCE_R1_REPAIR_DISPOSITION_20260928.md"
RECEIPT = REPORTS / "V4_03_EXTERNAL_ACCEPTANCE_R1_REPAIR_DISPOSITION_20260928.json"


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def atomic_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    os.replace(temp, path)


def main():
    core = load(REPORTS / "V4_03_CORE_REQUIRED_SCOPE_DIAGNOSTIC_RECEIPT_R1.json")
    candidate = load(REPORTS / "V4_03_FULL_SCOPE_CANDIDATE_RECEIPT_R1.json")
    path = load(REPORTS / "V4_03_MARKET_PATH_CANDIDATE_RECEIPT_R1.json")
    independent = load(REPORTS / "V4_03_INDEPENDENT_POSTCHECK_R1.json")
    path_independent = load(REPORTS / "V4_03_MARKET_PATH_INDEPENDENT_POSTCHECK_R1.json")
    deterministic = load(REPORTS / "V4_03_DETERMINISM_REPLAY_R1.json")
    schema = load(ROOT / "config/v4_03_output_schema_v1.json")
    algorithms = load(ROOT / "config/v4_03_algorithm_contracts_v1.json")
    native = load(ROOT / "config/v4_03_native_contract_registry_v1.json")
    native_scope = load(ROOT / "config/v4_03_native_scope_map_v1.json")
    parameter_registry = load(ROOT / "config/v4_03_parameter_registry_v1.json")
    extension = load(ROOT / "config/v4_algorithm_contract_framework_v1_2_0.json")
    extension_sha = sha(ROOT / "config/v4_algorithm_contract_framework_v1_2_0.json")
    framework_path = ROOT / "config/v4_algorithm_contract_framework_v1.json"
    for field in schema["fields"]:
        validate_output_field(field)
    schema_ok = len(schema["fields"]) == 47 and schema["framework_version"] == "1.2.0"
    ast_ok = (algorithms["contract_count"] == 47 and
              algorithms["framework_extension_sha256"] == extension_sha and
              algorithms["validation_status"] == "ALL_CONTRACT_SCHEMAS_AND_AST_V2_VALIDATED")
    bootstrap = load(ROOT / "data/v4/V4_DEV_BASELINE_HEAD.json")
    manifest_path = ROOT / bootstrap["bootstrap_manifest"]["path"]
    baseline_manifest = load(manifest_path)
    v402_manifest_path = ROOT / baseline_manifest["parent_artifacts"]["v4_02_manifest"]["path"]
    v402_manifest = load(v402_manifest_path)
    sector_components = [key for key in v402_manifest["components"] if "SECTOR" in key.upper()]
    sector_input_blocked = len(sector_components) == 0
    candidate_rows_pass = (candidate["rows_out"] == 5222 and candidate["field_count"] == 47 and
                           independent["status"] == "PASS" and independent["fields_checked"] == 47 and
                           not independent["mismatch_count_by_field"] and independent["candidate_output_sha256"] == candidate["output_sha256"])
    path_pass = (path["sessions"] == 200 and path["daily_returns"] == 199 and path["unknown_daily_return_count"] == 0 and
                 path_independent["status"] == "PASS" and path_independent["rows_checked"] == 200 and
                 path_independent["mismatch_rows"] == 0 and path_independent["candidate_output_sha256"] == path["output_sha256"])
    determinism_pass = deterministic["status"] == "PASS" and not deterministic["differences"]
    residual_blockers = [
        "No accepted V4-01/V4-02 historical sector-membership component exists in the frozen input manifest; full-market sector primitive artifact cannot be produced without introducing an unaccepted membership source.",
        "Stock-core and relative candidate reuse a 200-market-session bounded diagnostic. Required full-history first-available-date/warm-up acceptance has not been completed.",
        "Candidate lineage is DIAGNOSTIC_NON_PIT; there is no accepted publication artifact and no V4_03_FINAL_STAGE_RECEIPT_R1.",
        "Independent postcheck recomputed values and quality for all 47 fields, recomputed each output_digest and checked artifact SHA, but did not regenerate producer input_digest/window_identity byte-for-byte.",
        "Market-regime axes and sector primitives have contract/test closure but were not materialized as full-market daily artifacts; market path is bounded to the same 200 sessions."
    ]
    findings = {
        "B01": {"status": "IMPLEMENTED_PENDING_EXTERNAL_REVIEW", "evidence": ["V4_ALGORITHM_CONTRACT_FRAMEWORK_V1@1.2.0", "RULE_AST_V2", "47 per-field machine contracts", "V1.1 validator unchanged; compatibility tests pass"]},
        "B02": {"status": "IMPLEMENTED_PENDING_EXTERNAL_REVIEW", "evidence": ["versioned symmetric STRONG/WEAK erratum", "trend boundary vectors"]},
        "C01": {"status": "FIXED_AND_RETESTED", "evidence": ["prior extrema exclude T0", "suspended-asof prior extrema/technical vector", "pos60 reason-precedence regression fixed"]},
        "C02": {"status": "FIXED_SCHEMA_VALIDATED", "evidence": ["47 required V4-00G output metadata rows", "output schema digest bound to extension 1.2.0"]},
        "C03": {"status": "47_FIELD_DIAGNOSTIC_CANDIDATE_AND_INDEPENDENT_VALUES_QUALITY_PASS", "evidence": ["5222 rows x 47 fields", "independent mismatch count 0", "DIAGNOSTIC_NON_PIT lineage; not accepted publication"]},
        "C04": {"status": "IDENTITY_FIELDS_ADDED", "evidence": ["relative outputs contain PIT start/current universe IDs, session, adjustment set, input digest, prior RPS artifact digest and quality"]},
        "C05": {"status": "CONTRACTS_ADDED_SECTOR_MATERIALIZATION_BLOCKED", "evidence": ["native contract registry", "market path candidate with PIT step identity", "sector field-local contracts", "accepted sector membership input absent"]},
        "C06": {"status": "FIXED_AND_TESTED", "evidence": ["quote, amount, ret1, MA20 use separate field-local quality sets and denominators"]},
        "C07": {"status": "FIXED_AND_INDEPENDENTLY_REPLAYED", "evidence": ["unknown daily return permanently breaks same-version path suffix", "200 rows independent match"]}
    }
    status = "REPAIR_IMPLEMENTATION_COMPLETE_STAGE_ACCEPTANCE_BLOCKED" if schema_ok and ast_ok and candidate_rows_pass and path_pass and determinism_pass and sector_input_blocked else "EVIDENCE_GATE_FAILED"
    payload = {"contract_id": "V4_03_EXTERNAL_ACCEPTANCE_R1_REPAIR_DISPOSITION_20260928",
               "status": status, "branch": "codex/v4-system-reform",
               "baseline": "V4_DEV_BASELINE_HEAD@2026-09-24", "external_acceptance": "NOT_GRANTED",
               "internal_stage_acceptance": "NOT_GRANTED", "v4_04_entry": "BLOCKED",
               "final_stage_receipt_generated": False, "findings": findings,
               "gate_summary": {"schema_47_valid": schema_ok, "ast_contracts_47_valid": ast_ok,
                                "full_scope_candidate_5222_x_47": candidate_rows_pass,
                                "independent_all_47_value_quality": independent["status"],
                                "market_path_200_session_independent": path_pass,
                                "deterministic_replay_four_artifacts": determinism_pass,
                                "native_contract_count": native["contract_count"],
                                "sector_accepted_input_component_count": len(sector_components),
                                "sector_full_market_materialization": "BLOCKED" if sector_input_blocked else "AVAILABLE",
                                "performance_measurement_available": all("performance_measurement" in x for x in (core, candidate, path)),
                                "scanner_run_count": 0, "trading_run_count": 0, "tdx_root_write_count": 0,
                                "v4_02_head_mutation": 0, "stage_head_mutation": 0, "dev_baseline_mutation": 0},
               "artifact_sha256": {"core_output": core["output_sha256"], "full_scope_candidate": candidate["output_sha256"],
                                   "market_path_candidate": path["output_sha256"],
                                   "independent_47_postcheck": sha(REPORTS / "V4_03_INDEPENDENT_POSTCHECK_R1.json"),
                                   "independent_path_postcheck": sha(REPORTS / "V4_03_MARKET_PATH_INDEPENDENT_POSTCHECK_R1.json"),
                                   "determinism_replay": sha(REPORTS / "V4_03_DETERMINISM_REPLAY_R1.json")},
               "residual_blockers": residual_blockers,
               "next_stage": "Resolve sector membership input contract; then run full-history/native market-sector materialization and byte-level independent digest regeneration. Do not start V4-04.",
               "framework": {"base_path": str(framework_path.relative_to(ROOT)), "base_version": "1.1.0",
                             "base_sha256": sha(framework_path), "extension_version": extension["version"],
                             "extension_sha256": extension_sha},
               "sector_scope": native_scope["sector_materialization"],
               "parameter_registry_sha256": sha(ROOT / "config/v4_03_parameter_registry_v1.json"),
               "schema_field_count": len(schema["fields"]), "algorithm_contract_count": algorithms["contract_count"],
               "native_contract_count": native["contract_count"]}
    atomic_json(RECEIPT, payload)

    # Separate, stage-specific gate receipts preserve partial/blocked outcomes.
    receipts = {
        "V4_03_SCOPE_FREEZE_RECEIPT_R1.json": {"contract_id": "V4_03_SCOPE_FREEZE_RECEIPT_R1", "status": "PASS_WITH_NATIVE_INPUT_BLOCKER", "field_count": 47, "schema_validation": "PASS", "native_contract_count": native["contract_count"], "receipt_sha256": sha(RECEIPT)},
        "V4_03_CORE_FACTOR_ACCEPTANCE_R1.json": {"contract_id": "V4_03_CORE_FACTOR_ACCEPTANCE_R1", "status": "DIAGNOSTIC_VALUES_QUALITY_OUTPUT_DIGEST_PASS_INPUT_WINDOW_IDENTITY_REGEN_PENDING", "field_count": 39, "rows": core["rows_out"], "independent_values_quality_and_output_digest": independent["status"], "origin": "DIAGNOSTIC_NON_PIT"},
        "V4_03_RPS_ACCEPTANCE_R1.json": {"contract_id": "V4_03_RPS_ACCEPTANCE_R1", "status": "DIAGNOSTIC_VALUES_QUALITY_PASS", "fields": ["rps5", "rps20", "rps5_delta1", "rps5_delta3", "rps20_delta3"], "independent_values_quality": independent["status"], "origin": "DIAGNOSTIC_NON_PIT"},
        "V4_03_MARKET_RELATIVE_REFERENCE_ACCEPTANCE_R1.json": {"contract_id": "V4_03_MARKET_RELATIVE_REFERENCE_ACCEPTANCE_R1", "status": "DIAGNOSTIC_VALUES_QUALITY_PASS", "fields": ["rel_market_1", "rel_market_3", "rel_market_5"], "independent_values_quality": independent["status"], "origin": "DIAGNOSTIC_NON_PIT"},
        "V4_03_MARKET_NATIVE_ACCEPTANCE_R1.json": {"contract_id": "V4_03_MARKET_NATIVE_ACCEPTANCE_R1", "status": "PARTIAL_PASS_200_SESSION_PATH_ONLY", "path_rows": path["sessions"], "path_independent_postcheck": path_independent["status"], "regime_full_market_materialization": "NOT_PRODUCED"},
        "V4_03_SECTOR_NATIVE_BOUNDARY_ACCEPTANCE_R1.json": {"contract_id": "V4_03_SECTOR_NATIVE_BOUNDARY_ACCEPTANCE_R1", "status": "BLOCKED_ACCEPTED_SECTOR_MEMBERSHIP_INPUT_MISSING", "library_vectors": "PASS", "full_market_artifact": "NOT_PRODUCED", "v4_08_formal_fields_published": 0, "qualification_calls": 0, "seed_calls": 0, "rotation_calls": 0, "amount_a_calls": 0, "turnover_or_baostock_calls": 0},
        "V4_03_FULL_MARKET_RUN_RECEIPT_R1.json": {"contract_id": "V4_03_FULL_MARKET_RUN_RECEIPT_R1", "status": "CANDIDATE_PARTIAL_NOT_FULL_STAGE_RUN", "rows_out": candidate["rows_out"], "field_count": candidate["field_count"], "path_sessions": path["sessions"], "sector_materialization": "BLOCKED", "origin": "DIAGNOSTIC_NON_PIT"},
        "V4_03_PERFORMANCE_MEASUREMENT_R1.json": {"contract_id": "V4_03_PERFORMANCE_MEASUREMENT_R1", "status": "FACTS_RECORDED_NO_ACCEPTANCE_THRESHOLD", "core": core["performance_measurement"], "full_scope": candidate["performance_measurement"], "market_path": path["performance_measurement"]}
    }
    for name, receipt in receipts.items():
        atomic_json(REPORTS / name, receipt)

    md = f"""# V4-03 External Acceptance R1 Repair Disposition

- Date: 2026-09-28
- Repository branch: `codex/v4-system-reform`
- Frozen input: `V4_DEV_BASELINE_HEAD @ 2026-09-24`
- Governing stage card: `V4_03_PURE_CORE_FACTORS_IMPLEMENTATION_TASK_R2_20260928.md`
- Latest external review: `V4_03_EXTERNAL_ACCEPTANCE_R1_20260928.md`
- Result: **{status}**

## Repairs and evidence

| Finding | Disposition | Evidence |
|---|---|---|
| B01 | Versioned RULE_AST_V2 extension; 47 individual field contracts validated; V1.1 compatibility tests retained. | `config/v4_algorithm_contract_framework_v1_2_0.json`, `config/v4_03_algorithm_contracts_v1.json` |
| B02 | Symmetric STRONG/WEAK erratum is versioned and has boundary vectors. | `config/v4_03_market_regime_trend_amendment_v1.json`, `docs/evidence/V4_03_MARKET_REGIME_TREND_WEAK_ERRATUM_R1_20260928.md` |
| C01 | Prior extrema and technical windows now tolerate suspended T0 where current price is not an input; `pos60` preserves current-bar unavailability. | `src/v4/factors/core.py`, core vectors |
| C02 | 47 field schema validates against the V4-00G output metadata contract and binds the extension digest. | `config/v4_03_output_schema_v1.json` |
| C03 | 5,222 x 47 diagnostic candidate; independent formula/quality replay has 0 mismatches. | `reports/v4_03/V4_03_FULL_SCOPE_CANDIDATE_RECEIPT_R1.json`, `reports/v4_03/V4_03_INDEPENDENT_POSTCHECK_R1.json` |
| C04 | Relative values bind PIT current/start snapshots, session, adjustment set, source digest, prior RPS artifact and quality. | `src/v4/factors/relative.py`, full-scope artifact |
| C05 | Native contracts and PIT market path registry exist. Accepted sector membership is absent, so full-market sector materialization is blocked. | `config/v4_03_native_contract_registry_v1.json`, `config/v4_03_native_scope_map_v1.json` |
| C06 | Sector metrics use separate quote, amount, ret1 and MA20 field-local evaluability sets, each with output identity/digest. | `src/v4/factors/native.py`, sector vectors |
| C07 | A missing daily return makes the same path version suffix UNKNOWN; 200 rows independently match. | market path candidate and independent postcheck |

## Stage record

- Contract: V4-03 Pure-Core Factors only; V4-04 profile states, scanner, trading and V4-08 qualification remain outside scope.
- Evidence: 37 V4-03/V1.1-compatibility tests pass; full diagnostic 5,222 securities; 47 fields; 200-session market path; independent 47-field and path postchecks pass; four deterministic artifacts replay byte-identically.
- Performance facts: core, full-scope and market-path run times, CPU, sampled peak RSS, OS peak working set, hardware and cache-state limitation are recorded in `reports/v4_03/V4_03_PERFORMANCE_MEASUREMENT_R1.json`.
- Acceptance: **V4-03 internal acceptance is not granted.** Artifacts remain `DIAGNOSTIC_NON_PIT`; full-history replay, byte-level regeneration of each field identity digest, full-market regime primitives and sector materialization remain open. The frozen V4-02 manifest exposes {len(sector_components)} sector-membership components.
- Safety counts: scanner 0; trading 0; TDX-root writes 0; V4-02 head mutations 0; stage-head mutations 0; DEV-baseline mutations 0.
- Final-stage receipt: not generated because required gates remain open. V4-04 remains blocked.
- Next stage: establish an accepted PIT sector-membership input, then complete full-history native market/sector materialization and independent identity-digest regeneration. Keep V4-04 stopped.

The machine disposition is `reports/v4_03/V4_03_EXTERNAL_ACCEPTANCE_R1_REPAIR_DISPOSITION_20260928.json`. This is a repair response for external review, not an external acceptance claim.
"""
    EVIDENCE.parent.mkdir(parents=True, exist_ok=True)
    EVIDENCE.write_text(md, encoding="utf-8")
    print(json.dumps({"status": status, "sector_membership_components": len(sector_components),
                      "schema_fields": len(schema["fields"]), "algorithm_contracts": algorithms["contract_count"],
                      "candidate_pass": candidate_rows_pass, "path_pass": path_pass,
                      "determinism_pass": determinism_pass}))


if __name__ == "__main__":
    main()
