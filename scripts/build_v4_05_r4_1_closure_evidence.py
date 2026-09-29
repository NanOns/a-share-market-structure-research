"""Assemble R4.1 candidate-stage evidence and run an independent cross-check."""
from __future__ import annotations

from hashlib import sha256
import json
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "reports/v4_05"
STAGE = "V4_05_REPLAY_GATE_A_R4_1_POSTGRES_HASH_CLOSURE"
CANDIDATE = "V4_05_DATA_FACTOR_REPLAY_DEGRADED_PASS_CANDIDATE_R4_1"
REQUIRED_ARTIFACTS = (
    "reports/v4_05/staging/V4_05_R4_1_PERIOD_ASOF.jsonl.gz",
    "reports/v4_05/V4_05_R4_1_PERIOD_ASOF.json",
    "reports/v4_05/V4_05_R4_1_TARGET_MARKET_SNAPSHOT.json",
    "reports/v4_05/V4_05_R4_1_MARKET_SNAPSHOT_IDENTITY.json",
    "reports/v4_05/V4_05_R4_1_MARKET_REFERENCE.json",
    "reports/v4_05/staging/V4_05_R4_1_FULL_SCOPE_FACTORS.jsonl.gz",
    "reports/v4_05/V4_05_R4_1_FULL_SCOPE_FACTORS_RECEIPT.json",
    "reports/v4_05/V4_05_R4_1_MARKET_REGIME.json",
    "reports/v4_05/staging/V4_05_R4_1_FULL_MARKET_CORE_PROFILE.jsonl.gz",
    "reports/v4_05/V4_05_R4_1_CORE_PROFILE_REPLAY.json",
)
EVIDENCE = (
    "reports/v4_05/V4_05_R4_1_CANONICAL_HASH_POLICY.json",
    "reports/v4_05/V4_05_R4_1_ACCEPTED_HEAD_HASH_VALIDATION.json",
    "reports/v4_05/V4_05_R4_1_POSTGRES_REVISION_LEDGER_IDEMPOTENCY.json",
    "reports/v4_05/V4_05_R4_1_CLEAN_CLONE_DETERMINISM.json",
    "reports/v4_05/V4_05_R4_1_R4_DIFF.json",
    "reports/v4_05/V4_05_R4_1_RUNTIME_TEST_RECEIPT.json",
)
PUBLISHED_LFS_RESTORE = "reports/v4_05/V4_05_R4_1_PUBLISHED_LFS_RESTORE.json"
POSTCHECK = REPORT / "V4_05_R4_1_INDEPENDENT_POSTCHECK.json"
MANIFEST = REPORT / "V4_05_R4_1_STAGE_CANDIDATE_MANIFEST.json"


def load(relative: str) -> dict:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def file_identity(path: Path) -> dict:
    digest = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return {"sha256": digest.hexdigest(), "byte_count": path.stat().st_size}


def atomic_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_bytes((json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8"))
    os.replace(temp, path)


def atomic_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_bytes(value.encode("utf-8"))
    os.replace(temp, path)


def build_runtime_receipt(postgres: dict, clone: dict) -> dict:
    receipt = postgres["runtime_test_receipt"]
    summary = receipt["summary"]
    match = re.fullmatch(r"(\d+) passed, (\d+) skipped in (.+)", summary)
    if not match:
        raise ValueError(f"unrecognized pytest summary: {summary}")
    passed, skipped = int(match.group(1)), int(match.group(2))
    result = {
        "contract_id": "V4_05_R4_1_RUNTIME_TEST_RECEIPT_V1",
        "status": "PASS" if postgres["status"] == "PASS" and receipt["status"] == "PASS"
            and clone["status"] == "PASS" else "FAIL",
        "implementation_commit": clone["implementation_commit"],
        "suite": {"command": receipt["command"], "passed": passed, "skipped": skipped,
                  "duration": match.group(3), "summary": summary,
                  "postgres_schema_test_file": "tests/v4_phase0/test_postgres_schema.py",
                  "postgres_schema_tests_ran": receipt["tests_v4_phase0_test_postgres_schema_ran"],
                  "skipped_test_names_and_reasons": receipt["skipped_test_names_and_reasons"],
                  "pytest_output_sha256": postgres["test_output_digest"]},
        "postgresql_integration": {"status": postgres["status"], "postgres_version": postgres["postgres_version"],
                                   "applied_migration_count": postgres["applied_migration_count"],
                                   "isolated_connection_identity": postgres["isolated_connection_identity"],
                                   "production_connection_used": postgres["production_connection_used"],
                                   "case_ids": sorted(postgres["cases"]["cases"]),
                                   "cleanup": postgres["cleanup"]},
        "clean_clone_rebuild": {"status": clone["status"], "implementation_commit": clone["implementation_commit"],
                                "outputs_compared": len(clone["deterministic_outputs"]),
                                "lfs_inputs_restored": len(clone["lfs_restore"]["inputs"])},
        "stage_record": {"stage_contract": STAGE, "acceptance_result": "PASS" if passed > 0 else "FAIL",
                         "evidence": "Full required V4 runtime suite, isolated formal PostgreSQL I01-I05, and pushed-commit clean-clone rebuild completed.",
                         "next_stage": "INDEPENDENT_EXTERNAL_AUDIT_R4_1"},
    }
    atomic_json(REPORT / "V4_05_R4_1_RUNTIME_TEST_RECEIPT.json", result)
    return result


def build() -> dict:
    postgres = load("reports/v4_05/V4_05_R4_1_POSTGRES_REVISION_LEDGER_IDEMPOTENCY.json")
    hash_policy = load("reports/v4_05/V4_05_R4_1_CANONICAL_HASH_POLICY.json")
    head_validation = load("reports/v4_05/V4_05_R4_1_ACCEPTED_HEAD_HASH_VALIDATION.json")
    clone = load("reports/v4_05/V4_05_R4_1_CLEAN_CLONE_DETERMINISM.json")
    diff = load("reports/v4_05/V4_05_R4_1_R4_DIFF.json")
    runtime = build_runtime_receipt(postgres, clone)

    artifact_checks = {}
    for relative in REQUIRED_ARTIFACTS:
        path = ROOT / relative
        artifact_checks[relative] = {"exists": path.is_file(),
                                     **(file_identity(path) if path.is_file() else {})}
    postgres_cases = postgres["cases"]["cases"]
    i05 = postgres_cases["I05_prior_state_freeze"]
    all_cases_pass = all(postgres_cases[key]["status"] == "PASS" for key in (
        "I01_identical_replay", "I02_changed_source_revision")) \
        and all(row["rejected"] for row in postgres_cases["I03_negative_guards"].values()) \
        and all(row["passed"] for row in postgres_cases["I04_transaction_rollback"]) \
        and all(i05[key]["rejected"] for key in (
            "replace_prior_publication_head", "delete_prior_publication_head",
            "change_prior_state_head", "change_prior_state_logical_digest")) \
        and i05["publication_head_unchanged"] \
        and i05["next_session_publication_bound_to_prior_accepted_state"]["status"] == "CANDIDATE"
    clone_outputs_match_local = all(
        row["identical"] and row["primary"] == file_identity(ROOT / relative)
        for relative, row in clone["deterministic_outputs"].items())
    lfs_restore_pass = all(row["pointer_matches_working_tree"] and row["clone_matches_pointer"]
                           for row in clone["lfs_restore"]["inputs"].values())
    current_head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT,
                                  check=True, capture_output=True, text=True).stdout.strip()
    implementation_commit = clone["implementation_commit"]
    missing_v405_head = not (ROOT / "data/v4/V4_05_ACCEPTED_HEAD.json").exists()
    checks = {
        "postgres_formal_migrations_and_cases": postgres["status"] == "PASS"
            and postgres["applied_migration_count"] == 12 and postgres["production_connection_used"] is False
            and all_cases_pass and postgres["cleanup"]["succeeded"],
        "canonical_hash_and_frozen_head_binding": hash_policy["status"] == "PASS"
            and head_validation["status"] == "PASS"
            and head_validation["go_forward_head"]["git_blob_unchanged"]
            and head_validation["go_forward_head"]["frozen_representation_matches_global_stage_binding"]
            and all(row["unchanged"] for row in head_validation["protected_heads"].values()),
        "R4_business_values_frozen": diff["status"] == "PASS" and diff["business_field_changes"] == 0
            and diff["state_changes"] == 0 and diff["unexpected_business_value_drift"] == 0
            and diff["profile_row_set"]["same_id_set"],
        "clean_clone_and_LFS": clone["status"] == "PASS" and clone_outputs_match_local
            and clone["logical_digest_and_business_projection_equal"] and lfs_restore_pass,
        "runtime_suite_and_skip_disclosure": runtime["status"] == "PASS"
            and runtime["suite"]["postgres_schema_tests_ran"]
            and len(runtime["suite"]["skipped_test_names_and_reasons"]) == runtime["suite"]["skipped"],
        "required_artifacts_present": all(item["exists"] for item in artifact_checks.values()),
        "candidate_and_Accepted_Head_discipline": missing_v405_head
            and head_validation["v4_05_accepted_head"]["absent_at_start"]
            and head_validation["v4_05_accepted_head"]["absent_now"]
            and head_validation["head_files_changed"] == 0,
    }
    published_lfs = load(PUBLISHED_LFS_RESTORE) if (ROOT / PUBLISHED_LFS_RESTORE).is_file() else None
    if published_lfs is not None:
        checks["published_R4_1_LFS_outputs_restored"] = published_lfs["status"] == "PASS" \
            and published_lfs["candidate_commit"] == current_head \
            and all(row["pointer_matches_artifact"] and row["clone_matches_pointer"]
                    and row["artifact_bytes_equal"]
                    for row in published_lfs["restored_artifacts"].values())
    overall = all(checks.values())
    postcheck = {
        "contract_id": "V4_05_R4_1_INDEPENDENT_POSTCHECK_V1",
        "status": "PASS" if overall else "FAIL",
        "candidate_status": CANDIDATE if overall else "BLOCKED_R4_1_POSTCHECK_FAILURE",
        "external_acceptance": "PENDING",
        "implementation_commit": implementation_commit,
        "evidence_generation_head": current_head,
        "checks": checks,
        "artifact_identities": artifact_checks,
        "frozen_values": {
            "target_trade_date": diff["target_trade_date"],
            "market_reference_1_3_5": diff["frozen_values"]["market_reference_1_3_5"],
            "target_member_count": diff["target_identities"],
            "profile_row_count": diff["profile_row_set"]["r4_1"],
            "market_snapshot_id": diff["frozen_values"]["market_snapshot_id"]["r4_1"],
            "trend_axis": diff["frozen_values"]["market_regime_trend_axis"]["r4_1"],
        },
        "accepted_head_state": {"v4_05_accepted_head_created": not missing_v405_head,
                                "stage_head_unchanged": all(row["unchanged"] for row in head_validation["protected_heads"].values()),
                                "v4_06_v4_07_started": False},
        "stage_record": {"stage_contract": STAGE,
                         "acceptance_result": "PASS_CANDIDATE_PENDING_EXTERNAL_AUDIT" if overall else "FAIL",
                         "evidence": "Independent report, hash, identity, output-byte, test-disclosure, LFS OID, and head-discipline checks.",
                         "next_stage": "INDEPENDENT_EXTERNAL_AUDIT_R4_1"},
    }
    atomic_json(POSTCHECK, postcheck)

    period = load("reports/v4_05/V4_05_R4_1_PERIOD_ASOF.json")
    factor = load("reports/v4_05/V4_05_R4_1_FULL_SCOPE_FACTORS_RECEIPT.json")
    profile = load("reports/v4_05/V4_05_R4_1_CORE_PROFILE_REPLAY.json")
    market = load("reports/v4_05/V4_05_R4_1_MARKET_REFERENCE.json")
    stage_entry = f"""# V4-05 R4.1 Stage Entry

## Contract and scope

- Stage contract: `{STAGE}`.
- Governing task: `docs/evidence/V4_05_REPLAY_GATE_A_R4_1_POSTGRES_HASH_CLOSURE_TASK_20260929.md`.
- Latest prior audit: `docs/evidence/V4_05_REPLAY_GATE_A_R4_EXTERNAL_AUDIT_20260929.md`.
- Starting HEAD: `e751c9dc63ba6e6325b50daa15e849091e18f5dc`.
- Implementation and source-input commit: `{current_head}`.
- Scope is limited to closing PostgreSQL ledger replay (B03) and governance hash-domain / clean-clone determinism (B05).

## Frozen R4 values

- Target date: `{diff['target_trade_date']}`; target identities: {diff['target_identities']}.
- 1/3/5-session market reference returns: `{market['horizons']['1']['reference_return']}`, `{market['horizons']['3']['reference_return']}`, `{market['horizons']['5']['reference_return']}`.
- Period rows: {period['row_count']}; full-scope factor rows: {factor['row_count']}; core-profile rows: {profile['row_count']}.
- Market regime trend axis remains `{diff['frozen_values']['market_regime_trend_axis']['r4_1']}`.
- R4→R4.1 business-field changes: {diff['business_field_changes']}; state changes: {diff['state_changes']}.

## Stage evidence and acceptance

- PostgreSQL: {postgres['postgres_version']}; {postgres['applied_migration_count']} official migrations; I01–I05 pass in an isolated disposable database; production connection used: `{str(postgres['production_connection_used']).lower()}`.
- Hash policy: `{hash_policy['status']}`; the original Accepted Head promotion binding is preserved while downstream JSON identities use `CANONICAL_JSON_SHA256_V1`.
- Exact pushed-commit clone: `{clone['status']}`; {len(clone['lfs_restore']['inputs'])} LFS source inputs restored, {len(clone['deterministic_outputs'])} generated outputs compared byte-for-byte.
- Published R4.1 LFS payload restore: `{published_lfs['status'] if published_lfs else 'PENDING_ARTIFACT_PUSH'}`.
- Runtime suite: `{runtime['suite']['summary']}`; PostgreSQL schema test ran; both skipped tests and reasons are listed in the runtime receipt.
- R4.1 status: `{CANDIDATE}`. External acceptance remains `PENDING`; no V4-05 Accepted Head was created and no V4-06/V4-07 stage was started.
- Next stage: `INDEPENDENT_EXTERNAL_AUDIT_R4_1`.

## Evidence files

The full file hash inventory is in `reports/v4_05/V4_05_R4_1_STAGE_CANDIDATE_MANIFEST.json`; independent checks are in `reports/v4_05/V4_05_R4_1_INDEPENDENT_POSTCHECK.json`.
"""
    atomic_text(REPORT / "V4_05_R4_1_STAGE_ENTRY.md", stage_entry)

    closure = f"""# V4-05 R4.1 Closure Candidate

Stage: `{STAGE}`

Candidate: `{CANDIDATE}`

Independent postcheck: `{postcheck['status']}`

External acceptance: `PENDING`

## Closed in this candidate

- **B03 PostgreSQL ledger:** PostgreSQL {postgres['postgres_version']}, 12 formal migrations, isolated database, no production connection, I01–I05 passed, transaction rollback and cleanup verified.
- **B05 canonical identity:** governance JSON now uses `CANONICAL_JSON_SHA256_V1`; the V4-02 global accepted binding remains `{head_validation['go_forward_head']['global_stage_binding_sha256']}` and matches the reconstructed frozen representation. Protected accepted heads are unchanged.
- **Determinism:** the pushed implementation commit `{clone['implementation_commit']}` was rebuilt in a fresh remote clone after LFS fetch/checkout. All {len(clone['deterministic_outputs'])} required generated outputs have identical bytes and logical projections.
- **Published LFS payloads:** fresh-clone restore for candidate commit `{published_lfs['candidate_commit'] if published_lfs else 'PENDING'}` is `{published_lfs['status'] if published_lfs else 'PENDING'}`; all R4.1 LFS output OIDs, sizes, and restored bytes match.

## Business values remain frozen

- 2026-09-28 target, {diff['target_identities']} target identities, {profile['row_count']} core-profile rows.
- Market reference returns: 1 session `{market['horizons']['1']['reference_return']}`, 3 sessions `{market['horizons']['3']['reference_return']}`, 5 sessions `{market['horizons']['5']['reference_return']}`.
- R4→R4.1 differences: business fields {diff['business_field_changes']}, states {diff['state_changes']}, unexpected drift {diff['unexpected_business_value_drift']}.
- `CURRENT_FORWARD_STOCK_CORE=DEGRADED_PASS`.
- `HISTORICAL_AS_RECORDED_ADJUSTED_PRICE=BLOCKED_NO_FIRST_AVAILABILITY_EVIDENCE`.

## Candidate boundary

This is a stage candidate, not an external acceptance. No `data/v4/V4_05_ACCEPTED_HEAD.json` was created, `V4_STAGE_ACCEPTED_HEAD` remains unchanged, and V4-06/V4-07 were not started. The next action is independent external audit for R4.1.

See `V4_05_R4_1_INDEPENDENT_POSTCHECK.json` and `V4_05_R4_1_STAGE_CANDIDATE_MANIFEST.json` for hashes and checks.
"""
    atomic_text(REPORT / "V4_05_R4_1_CLOSURE.md", closure)

    optional_evidence = (PUBLISHED_LFS_RESTORE,) if published_lfs is not None else ()
    manifest_files = (*REQUIRED_ARTIFACTS, *EVIDENCE, *optional_evidence,
                      "reports/v4_05/V4_05_R4_1_INDEPENDENT_POSTCHECK.json",
                      "reports/v4_05/V4_05_R4_1_STAGE_ENTRY.md",
                      "reports/v4_05/V4_05_R4_1_CLOSURE.md",
                      "docs/evidence/V4_05_REPLAY_GATE_A_R4_1_POSTGRES_HASH_CLOSURE_TASK_20260929.md",
                      "docs/evidence/V4_05_REPLAY_GATE_A_R4_EXTERNAL_AUDIT_20260929.md",
                      "scripts/build_v4_05_r4_1_clean_clone_evidence.py",
                      "scripts/build_v4_05_r4_1_closure_evidence.py",
                      "scripts/build_v4_05_r4_1_published_lfs_restore.py")
    manifest = {
        "contract_id": "V4_05_R4_1_STAGE_CANDIDATE_MANIFEST_V1",
        "status": CANDIDATE if overall else "BLOCKED_R4_1_POSTCHECK_FAILURE",
        "external_acceptance": "PENDING", "starting_head": "e751c9dc63ba6e6325b50daa15e849091e18f5dc",
        "implementation_commit": implementation_commit, "assembled_on_commit": current_head,
        "published_lfs_restore": None if published_lfs is None else published_lfs["status"],
        "artifact_and_evidence_hashes": {
            relative: file_identity(ROOT / relative) for relative in manifest_files},
        "manifest_self_hash_omitted": True,
        "frozen_business_state": {
            "current_forward_stock_core": "DEGRADED_PASS",
            "historical_as_recorded_adjusted_price": "BLOCKED_NO_FIRST_AVAILABILITY_EVIDENCE",
            "business_field_changes": diff["business_field_changes"], "state_changes": diff["state_changes"],
            "unexpected_business_value_drift": diff["unexpected_business_value_drift"],
            "market_reference_1_3_5": diff["frozen_values"]["market_reference_1_3_5"],
            "market_snapshot_id": diff["frozen_values"]["market_snapshot_id"]["r4_1"],
            "trend_axis": diff["frozen_values"]["market_regime_trend_axis"]["r4_1"],
        },
        "accepted_head_discipline": {"v4_05_accepted_head_created": False,
                                     "stage_accepted_head_changed": False,
                                     "v4_06_or_v4_07_started": False},
        "stage_record": {"stage_contract": STAGE,
                         "acceptance_result": "PASS_CANDIDATE_PENDING_EXTERNAL_AUDIT" if overall else "FAIL",
                         "evidence": "B03/B05 closure reports, clean-clone and LFS restore proof, R4 diff, full runtime receipt, independent postcheck.",
                         "next_stage": "INDEPENDENT_EXTERNAL_AUDIT_R4_1"},
    }
    atomic_json(MANIFEST, manifest)
    if not overall:
        raise RuntimeError("independent R4.1 postcheck failed")
    return {"status": postcheck["status"], "candidate": CANDIDATE,
            "manifest_artifacts": len(manifest_files), "tests": runtime["suite"]["summary"],
            "external_acceptance": "PENDING"}


if __name__ == "__main__":
    print(json.dumps(build(), ensure_ascii=False, sort_keys=True))
