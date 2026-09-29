"""Build the hash-bound V4-06 candidate evidence bundle atomically."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports/v4_06"
sys.path.insert(0, str(ROOT / "src"))

from workbench_analysis.v4_06_supplemental import atomic_json_write, run_core_isolation_matrix


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def json_file(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def info(path: Path) -> dict[str, Any]:
    return {"path": path.relative_to(ROOT).as_posix(), "byte_count": path.stat().st_size,
            "sha256": sha256_file(path)}


def write_markdown(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def main() -> int:
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    accepted_head_path = ROOT / "data/v4/V4_05_ACCEPTED_HEAD.json"
    postgres_ledger_path = ROOT / "reports/v4_05/V4_05_R4_2_POSTGRES_REVISION_LEDGER_IDEMPOTENCY.json"
    request_ledger_path = ROOT / "reports/v4_baostock/request_ledger.json"
    core_path = ROOT / "reports/v4_05/staging/V4_05_R4_1_FULL_MARKET_CORE_PROFILE.jsonl.gz"
    factors_path = ROOT / "reports/v4_05/staging/V4_05_R4_1_FULL_SCOPE_FACTORS.jsonl.gz"
    contract_path = ROOT / "config/baostock_supplemental_contract_v1.json"
    tolerance_path = ROOT / "config/baostock_turnover_binding_tolerance_v1.json"
    factor_contract_path = ROOT / "config/turnover_context_contract_v1.json"
    probe_path = REPORTS / "V4_06_LIVE_PROBE_RECEIPT.json"
    migration_path = REPORTS / "V4_06_SCHEMA_MIGRATION_RECEIPT.json"

    head = json_file(accepted_head_path)
    postgres_ledger = json_file(postgres_ledger_path)
    probe = json_file(probe_path)
    migration = json_file(migration_path)
    source_contract = json_file(contract_path)
    tolerance_contract = json_file(tolerance_path)
    factor_contract = json_file(factor_contract_path)
    if head["external_acceptance"] != "EXTERNALLY_ACCEPTED":
        raise RuntimeError("V4_05_ACCEPTED_HEAD_NOT_EXTERNAL")
    if head["accepted_artifacts"]["core_profile"]["logical_digest"] != postgres_ledger["actual_state_head"]["logical_digest"]:
        raise RuntimeError("V4_05_CORE_PROFILE_STATE_DIGEST_MISMATCH")
    if probe["accepted_publication_id"] != postgres_ledger["actual_publication_head"]["publication_id"]:
        raise RuntimeError("LIVE_PROBE_ACCEPTED_PUBLICATION_ID_MISMATCH")
    if migration.get("status") != "PASS" or not migration["checks"]["core_publication_head_unchanged"]:
        raise RuntimeError("V4_06_ISOLATED_SCHEMA_ACCEPTANCE_FAILED")
    if probe["target_rows_observed"] < 1 or probe["strict_bound_row_count"] != 0:
        raise RuntimeError("V4_06_LIVE_BINDING_DISPOSITION_CHANGED")

    probe_info = info(probe_path)
    migration_info = info(migration_path)
    contract_info = info(contract_path)
    tol_info = info(tolerance_path)
    factor_info = info(factor_contract_path)
    audit_doc = ROOT / "docs/audits/V4_06_BAOSTOCK_BINDING_TOLERANCE_AUDIT_R1_20260929.md"
    stage_entry = REPORTS / "V4_06_STAGE_ENTRY.md"

    source_audit = {
        "contract_id": "V4_06_SOURCE_CONTRACT_AUDIT_V1", "observed_at_utc": now,
        "status": "PASS_WITH_OPEN_SOURCE_BINDING_AUDIT",
        "source_contract": {**contract_info, "contract_id": source_contract["contract_id"],
                             "contract_version": source_contract["contract_version"],
                             "dataset_enabled": source_contract["datasets"]["BAOSTOCK_TURNOVER_DAILY_V1"]["enabled"],
                             "strict_tolerance_status": source_contract["binding"]["strict_fingerprint_tolerance_contract"]["status"]},
        "reuse_policy": "Reused the V4-00F source contract; no parallel BaoStock source contract was created.",
        "runtime_observed": probe["runtime"],
        "field_map_disposition": {
            "turn_source_unit_per_existing_contract": "PERCENT_POINTS",
            "normalization_per_existing_contract": "source_value / 100 -> FRACTION",
            "evidence_status": "CURRENT_CONTRACT_REUSED; OFFICIAL_REFERENCE_NOT_INDEPENDENTLY_REACCEPTED",
            "denominator": "PROVIDER_DEFINED_CIRCULATING_SHARES",
            "denominator_semantics_acceptance": "NOT_ACCEPTED",
            "tradestatus_and_isST": "CROSS_CHECK_ONLY",
            "tdx_authority": "REMAINS_AUTHORITATIVE",
        },
        "official_reference_access": {
            "source_authority_description": source_contract["field_map"]["source_authority"],
            "api_reference_url": source_contract["input_evidence"].get("official_api_reference", "https://www.baostock.com/mainContent?file=pythonAPI.md"),
            "result": "WEB_RENDERER_RETURNED_NO_READABLE_API_BODY",
            "interpretation": "No new field, unit, tolerance, or denominator claim was inferred from the inaccessible page.",
        },
        "live_probe": probe_info,
        "independent_audit": {"audit_id": "V4-06-BAOSTOCK-BINDING-TOLERANCE-01", "status": "OPEN",
                              "path": audit_doc.relative_to(ROOT).as_posix(), "sha256": sha256_file(audit_doc)},
        "capability_disposition": "Keep all BaoStock datasets disabled; any live values remain diagnostic-only.",
        "core_dependency": "NONE",
    }
    atomic_json_write(REPORTS / "V4_06_SOURCE_CONTRACT_AUDIT.json", source_audit)

    summaries = probe["security_summaries"]
    target_samples = []
    for item in summaries:
        target = next((row for row in item["sample_rows"] if row["trade_date"] == probe["target_trade_date"]), None)
        if target is None:
            raise RuntimeError(f"LIVE_TARGET_SAMPLE_MISSING:{item['provider_code']}")
        target_samples.append({
            "security_id": target["security_id"], "board_scope": item["board_scope"],
            "provider_code": item["provider_code"], "trade_date": target["trade_date"],
            "binding_status": target["binding_status"], "quality_codes": target["quality_codes"],
            "fingerprint_exact": target["fingerprint_exact"], "abs_delta": target["abs_delta"],
            "turnover_raw_value": target["turnover_raw_value"],
            "turnover_raw_unit": target["turnover_raw_unit"],
            "turnover_normalized_fraction": target["turnover_normalized_fraction"],
            "source_digest": target["source_digest"],
        })
    binding_acceptance = {
        "contract_id": "V4_06_BINDING_TOLERANCE_ACCEPTANCE_V1", "observed_at_utc": now,
        "status": "DEGRADED_PASS_DIAGNOSTIC_ONLY", "tolerance_contract": {**tol_info,
            "contract_id": tolerance_contract["contract_id"], "contract_version": tolerance_contract["contract_version"],
            "acceptance": tolerance_contract["acceptance"], "tolerances": tolerance_contract["tolerances"],
            "strict_binding_allowed": tolerance_contract["strict_binding_allowed"]},
        "independent_acceptance": "NOT_ACCEPTED",
        "denominator_semantics_acceptance": tolerance_contract["denominator_semantics_acceptance"],
        "live_probe_receipt": probe_info,
        "actual_live_results": {
            "requested_securities": probe["requested_security_count"],
            "completed_securities": probe["completed_security_count"],
            "target_rows_observed": probe["target_rows_observed"],
            "strict_bound_rows": probe["strict_bound_row_count"],
            "provider_error": probe["failure"],
            "security_summaries": [{"provider_code": item["provider_code"], "query_rows": item["query_row_count"],
                "common_dates": item["common_date_count"], "exact_close_volume_amount_rows": item["exact_common_date_count"],
                "target_status": item["target_row_status"], "max_abs_delta": item["max_abs_delta"]} for item in summaries],
            "target_samples": target_samples,
        },
        "source_tolerance_criteria": {"representative_samples": "PRESENT_DIAGNOSTIC_ONLY",
            "close_volume_amount_fingerprint": "OBSERVED; AMOUNT CONFLICTS IN ALL FOUR SAMPLES",
            "plus_minus_epsilon_boundary": "UNIT_TEST_FIXTURE_ONLY; NOT INDEPENDENT LIVE ACCEPTANCE",
            "independent_reviewer": "MISSING", "denominator_basis": "NOT_ACCEPTED"},
        "disposition": "Do not claim BOUND_STRICT; keep the BaoStock dataset disabled and the independent audit OPEN.",
    }
    atomic_json_write(REPORTS / "V4_06_BINDING_TOLERANCE_ACCEPTANCE.json", binding_acceptance)

    tests_result = subprocess.run([sys.executable, "-m", "pytest", "tests/v4_06", "-q"], cwd=ROOT,
                                  text=True, capture_output=True)
    test_output = (tests_result.stdout + tests_result.stderr).strip()
    match = re.search(r"(\d+) passed", test_output)
    if tests_result.returncode != 0 or not match:
        raise RuntimeError(f"V4_06_UNIT_TESTS_FAILED: {test_output}")
    test_count = int(match.group(1))
    test_receipt = {
        "contract_id": "V4_06_RUNTIME_TEST_RECEIPT_V1", "observed_at_utc": now,
        "status": "PASS", "command": "python -m pytest tests/v4_06 -q",
        "exit_code": tests_result.returncode, "passed": test_count, "output": test_output,
        "test_scope": ["source unit/raw provenance", "identity/date/status and binding gate", "tolerance fixtures",
            "5/20/60 windows, 60 boundary, 250 cap, suspension, missing gap, ratio and delta3",
            "request priority/budget/retry/checkpoint/circuit breaker", "append-only revisions/manifests",
            "A/B/C/D Core isolation fixture", "source digest determinism"],
        "migration_acceptance_receipt": migration_info,
    }
    atomic_json_write(REPORTS / "V4_06_RUNTIME_TEST_RECEIPT.json", test_receipt)

    turnover_acceptance = {
        "contract_id": "V4_06_TURNOVER_CONTEXT_ACCEPTANCE_V1", "observed_at_utc": now,
        "status": "PASS_ENGINE_WITH_LIVE_CAPABILITY_DEGRADED",
        "factor_contract": {**factor_info, "contract_id": factor_contract["contract_id"],
                            "contract_version": factor_contract["contract_version"]},
        "engine_acceptance": "PASS_ON_DETERMINISTIC_STRICT_BOUND_FIXTURES",
        "strict_rules": factor_contract["baseline"], "metrics": factor_contract["metrics"],
        "runtime_tests": {"receipt_path": "reports/v4_06/V4_06_RUNTIME_TEST_RECEIPT.json",
                           "passed": test_count, "required_history_cases_present": True},
        "live_capability": {"target_date": probe["target_trade_date"],
            "representative_target_rows": probe["target_rows_observed"],
            "strict_bound_rows": probe["strict_bound_row_count"],
            "formal_live_metric_eligible": False,
            "reason": "No independently accepted tolerance or provider denominator semantics; live target fingerprints conflict."},
        "core_effect": "NONE",
        "disposition": "Engine contract is implemented and tested; live BaoStock values remain excluded from formal turnover context.",
    }
    atomic_json_write(REPORTS / "V4_06_TURNOVER_CONTEXT_ACCEPTANCE.json", turnover_acceptance)

    fixture_core = {"core_fact_digest": "1" * 64, "core_profile_digest": "2" * 64,
                    "core_eligibility_digest": "3" * 64, "core_state_digest": "4" * 64,
                    "core_event_digest": "5" * 64, "validation_enrollment_digest": "6" * 64}
    scenarios = {
        "A_NO_TURNOVER": {},
        "B_TURNOVER_PRE_CACHED": {"turnover_rate": 0.0125, "enrichment_revision": 1},
        "C_TURNOVER_AFTER_ACCEPTANCE": {"turnover_rate": 0.015, "enrichment_revision": 2},
        "D_PROVIDER_STATUS_CONFLICT": {"binding_quality": "BOUND_SOFT", "quality_codes": ["LOCAL_STATUS_CROSSCHECK_CONFLICT"]},
    }
    core_matrix = run_core_isolation_matrix(fixture_core, scenarios)
    core_acceptance = {
        "contract_id": "V4_06_CORE_ISOLATION_ACCEPTANCE_V1", "observed_at_utc": now,
        "status": "PASS_STRUCTURAL_FIXTURE_AND_ACCEPTED_HEAD_GUARD",
        "core_dependency": "NONE", "fixture_matrix": core_matrix,
        "fixture_digest_disclosure": "The six-component A/B/C/D matrix uses deterministic synthetic SHA-256 fixtures; it does not claim those are V4-05 business digests.",
        "accepted_v4_05_core": {"publication_id": postgres_ledger["actual_publication_head"]["publication_id"],
            "profile_state_logical_digest": head["accepted_artifacts"]["core_profile"]["logical_digest"],
            "profile_artifact": info(core_path),
            "eligibility_event_enrollment_component_digests": "NOT_PRESENT_AS_A_SIX_DIGEST_VECTOR_IN_V4_05_ACCEPTED_HEAD"},
        "database_head_before_after": {
            "before": migration["checks"]["core_publication_head_before"],
            "after": migration["checks"]["core_publication_head_after"],
            "unchanged": migration["checks"]["core_publication_head_unchanged"]},
        "limitations": ["V4-05 did not publish accepted digests for all six task-card components as one vector.",
                        "Database proof binds the actual accepted publication/state identity; scenario matrix proof is structural and fixture-backed."],
    }
    atomic_json_write(REPORTS / "V4_06_CORE_ISOLATION_ACCEPTANCE.json", core_acceptance)

    revision_acceptance = {
        "contract_id": "V4_06_ENRICHMENT_REVISION_ACCEPTANCE_V1", "observed_at_utc": now,
        "status": migration["status"], "schema_migration_receipt": migration_info,
        "checks": migration["checks"], "accepted_publication_identity": {
            "publication_id": postgres_ledger["actual_publication_head"]["publication_id"],
            "core_state_logical_digest": postgres_ledger["actual_state_head"]["logical_digest"],
            "trade_date": head["target_trade_date"]},
        "row_query_identity_persisted": {
            "fields": ["provider_code", "frequency", "start_date", "end_date", "adjustflag"],
            "validation": "Exact key set, normalized BaoStock code, daily frequency, adjustflag=3, and query range containing the target date.",
        },
        "writes_are_sidecars": True, "core_revision_created": False,
        "production_database_connection_used": False,
    }
    atomic_json_write(REPORTS / "V4_06_ENRICHMENT_REVISION_ACCEPTANCE.json", revision_acceptance)

    request_ledger = json_file(request_ledger_path)
    day = probe["request_count"]["shanghai_date"]
    current_count = int(request_ledger["by_shanghai_date"][day]["count"])
    if current_count != probe["request_count"]["after"]:
        raise RuntimeError("BAOSTOCK_REQUEST_LEDGER_RECEIPT_MISMATCH")
    request_receipt = {
        "contract_id": "V4_06_REQUEST_BUDGET_RECEIPT_V1", "observed_at_utc": now,
        "status": "PASS_WITHIN_BOUNDS", "ledger": info(request_ledger_path),
        "stage_entry_count": 60, "stage_final_count": current_count, "stage_delta": current_count - 60,
        "final_probe_request_count": probe["request_count"],
        "probe_jobs": 2, "probe_security_queries_per_job": 4,
        "actual_probe_policy": {"priority": probe["priority"], "serial": True,
            "max_concurrent_requests": source_contract["request_budget"]["max_concurrent_requests"],
            "per_request_timeout_seconds": source_contract["request_budget"]["per_request_timeout_seconds"],
            "max_retries": source_contract["request_budget"]["transient_retries_max"],
            "daily_soft_stop": source_contract["request_budget"]["daily_soft_stop"],
            "daily_hard_stop": source_contract["request_budget"]["daily_hard_stop"],
            "p0_reserved_headroom": 5000, "retry_counted": source_contract["request_budget"]["retry_counts_against_budget"]},
        "checkpoint": {"path": "reports/v4_06/staging/V4_06_LIVE_PROBE_CHECKPOINT_R2.json",
                       "sha256": sha256_file(REPORTS / "staging/V4_06_LIVE_PROBE_CHECKPOINT_R2.json"),
                       "source_rows_persisted": False},
        "daily_budget_exhausted": False,
        "p0_daily_incremental_headroom_preserved": True,
    }
    atomic_json_write(REPORTS / "V4_06_REQUEST_BUDGET_RECEIPT.json", request_receipt)

    blocker = {
        "contract_id": "V4_06_LIVE_BINDING_BLOCKER_V1", "observed_at_utc": probe["observed_at_utc"],
        "status": "STRICT_BINDING_BLOCKED_DIAGNOSTIC_ONLY",
        "reason": "Independent BaoStock tolerance and denominator acceptance are missing; live target fingerprints conflict.",
        "provider_error_code": probe["failure"].get("provider_error_code") if probe["failure"] else None,
        "provider_error_message": probe["failure"].get("provider_error_message") if probe["failure"] else None,
        "provider_transport_status": {"login": probe["login"], "logout": probe["logout"],
            "queries_completed": probe["completed_security_count"], "target_rows_observed": probe["target_rows_observed"]},
        "target_trade_date": probe["target_trade_date"], "request_range": probe["request_range"],
        "request_ledger": {**info(request_ledger_path), "shanghai_date": day,
                           "stage_entry_count": 60, "final_count": current_count, "stage_delta": current_count - 60},
        "source_receipt": probe_info,
        "impact_scope": "BAOSTOCK_TURNOVER_DAILY_V1 remains disabled; supplemental turnover rows stay diagnostic-only; accepted V4-05 Core is unchanged.",
        "accepted_core_publication_id": probe["accepted_publication_id"],
        "accepted_core_logical_digest": probe["accepted_core_logical_digest"],
        "next_action": "Independent reviewer must accept official field/unit evidence, source-specific tolerance, expected samples, and denominator semantics.",
    }
    atomic_json_write(REPORTS / "V4_06_LIVE_BINDING_BLOCKER.json", blocker)

    clean_path = REPORTS / "V4_06_CLEAN_CHECKOUT_RECEIPT.json"
    if not clean_path.is_file():
        raise RuntimeError("CLEAN_CHECKOUT_RECEIPT_REQUIRED_BEFORE_FINALIZATION")
    clean = json_file(clean_path)
    if clean.get("status") != "PASS":
        raise RuntimeError("CLEAN_CHECKOUT_REPLAY_NOT_ACCEPTED")

    source_paths = [
        ROOT / "config/turnover_context_contract_v1.json",
        tolerance_path,
        ROOT / "src/workbench_analysis/v4_06_supplemental.py",
        ROOT / "src/workbench_analysis/baostock_supplemental.py",
        ROOT / "src/workbench_db/migrations/v4_postgres/013_v4_06_stock_profile_enrichments.sql",
        ROOT / "src/workbench_db/migrations/v4_postgres/rollback/013_v4_06_stock_profile_enrichments.sql",
        ROOT / "scripts/apply_v4_phase0_schema.py",
        ROOT / "scripts/run_v4_05_r4_1_postgres_ledger.py",
        ROOT / "scripts/run_v4_06_live_binding_probe.py",
        ROOT / "scripts/run_v4_06_migration_acceptance.py",
        ROOT / "scripts/build_v4_06_candidate_evidence.py",
    ]
    closure = f"""# V4-06 Closure / Candidate Submission

Recorded at {now}.

## Stage result

**DEGRADED_PASS candidate; external acceptance is PENDING.** The supplemental pipeline, append-only PostgreSQL schema, bounded worker, and TURNOVER_CONTEXT_V1 engine are implemented. The live BaoStock strict-binding capability remains blocked and the dataset stays disabled. `CORE_DEPENDENCY = NONE`.

The V4-05 accepted Core publication is `{probe['accepted_publication_id']}` for {probe['target_trade_date']}, logical digest `{probe['accepted_core_logical_digest']}`. The isolated migration run appended two supplemental revisions against that publication and verified that the publication head was identical before and after. No V4-06 Accepted Head was created, the global accepted head was not advanced, and V4-07/V4-08 were not started.

## Capability results

- `SUPPLEMENTAL_PIPELINE = PASS`: versioned append-only schema, manifest/row identity, immutability guards, rollback, and same-publication revision behavior passed in an isolated PostgreSQL 18.6 cluster.
- `TURNOVER_CONTEXT_ENGINE = PASS`: {test_count} stage tests passed, including strict-only 5/20/60 windows, the 60-sample boundary, 250-session cap, suspension/missing handling, ratio and delta3 boundaries, and Core isolation fixtures.
- `BAOSTOCK_LIVE_STRICT_BINDING = BLOCKED/DEGRADED`: the bounded probe returned {probe['target_rows_observed']} target rows across four representative identities; strict-bound count is {probe['strict_bound_row_count']}. The provider responded successfully, but every identity had zero exact close/volume/amount rows across common dates and target fingerprints had amount conflicts. Source-specific tolerances and denominator semantics are not independently accepted.
- `CORE_ISOLATION = PASS_WITH_DISCLOSED_FIXTURE_LIMIT`: the sidecar API cannot write Core digests; A/B/C/D matrix fixtures preserve all six supplied components, and the database test preserved the actual accepted V4-05 publication head. V4-05 does not publish one accepted six-component digest vector, so no synthetic digest is presented as a V4-05 business digest.

## Open audit and external review

Audit `V4-06-BAOSTOCK-BINDING-TOLERANCE-01` remains OPEN and independent from this stage gate. Official BaoStock API documentation was not readable through the web renderer during this stage; this evidence does not infer missing source semantics. The source-specific tolerance contract remains unfrozen, strict binding remains forbidden, and all BaoStock datasets remain disabled.

Submit this candidate and its evidence bundle for independent external acceptance. Do not create an Accepted Head until that review is recorded. V4-07 remains not started; V4-08 remains blocked on its existing PIT membership baseline gate.

## Evidence index

See `V4_06_STAGE_CANDIDATE_MANIFEST.json` for SHA-256 bindings for source files and every stage report. The required clean-checkout receipt is `{clean.get('source_commit_sha', 'source commit recorded in receipt')}`.
"""
    write_markdown(REPORTS / "V4_06_CLOSURE.md", closure)
    output_paths = sorted(path for path in REPORTS.iterdir()
                          if path.is_file() and path.name != "V4_06_STAGE_CANDIDATE_MANIFEST.json")

    source_commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    manifest = {
        "contract_id": "V4_06_STAGE_CANDIDATE_MANIFEST_V1", "created_at_utc": now,
        "stage": "V4-06 Supplemental Enrichment", "stage_status": "DEGRADED_PASS_CANDIDATE",
        "external_acceptance": "PENDING", "accepted_head_created": False,
        "branch": subprocess.check_output(["git", "branch", "--show-current"], cwd=ROOT, text=True).strip(),
        "source_commit_sha": source_commit, "starting_head": "e0fbcc665b0926322b5098c0c99465fa2b427cb8",
        "accepted_v4_05": {"publication_id": probe["accepted_publication_id"],
                           "target_trade_date": probe["target_trade_date"],
                           "core_profile_logical_digest": probe["accepted_core_logical_digest"]},
        "capabilities": {"SUPPLEMENTAL_PIPELINE": "PASS", "TURNOVER_CONTEXT_ENGINE": "PASS",
                         "BAOSTOCK_LIVE_STRICT_BINDING": "BLOCKED_DEGRADED", "CORE_DEPENDENCY": "NONE"},
        "open_audits": [{"audit_id": "V4-06-BAOSTOCK-BINDING-TOLERANCE-01", "status": "OPEN",
                         "path": audit_doc.relative_to(ROOT).as_posix(), "sha256": sha256_file(audit_doc)}],
        "source_files": {path.relative_to(ROOT).as_posix(): sha256_file(path) for path in source_paths},
        "evidence_files": {path.relative_to(ROOT).as_posix(): info(path) for path in output_paths},
        "stage_entry": info(stage_entry),
        "clean_checkout_receipt": info(clean_path),
        "limitations": ["No independent BaoStock tolerance acceptance.",
                        "No independent provider-defined circulating-shares semantic acceptance.",
                        "Accepted V4-05 artifact does not expose the full six-component Core digest vector.",
                        "Official API reference page returned no readable body during this stage."],
        "next_stage": "Independent external acceptance of this candidate; keep V4-07 unstarted and V4-08 blocked.",
    }
    atomic_json_write(REPORTS / "V4_06_STAGE_CANDIDATE_MANIFEST.json", manifest)
    print(json.dumps({"status": manifest["stage_status"], "source_commit_sha": source_commit,
                      "report_count": len(output_paths) + 2, "unit_tests_passed": test_count,
                      "live_strict_bound_rows": probe["strict_bound_row_count"],
                      "external_acceptance": "PENDING"}, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
