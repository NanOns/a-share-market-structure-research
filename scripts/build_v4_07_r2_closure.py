from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import tempfile
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ACCEPTED_ROOT = Path(os.environ.get("V4_07_ACCEPTED_INPUTS_ROOT", str(ROOT))).resolve()

EVIDENCE_PATHS = (
    "reports/v4_07/V4_07_R2_STAGE_ENTRY.md",
    "reports/v4_07/V4_07_R2_FULL_MARKET_CANDIDATE_RECEIPT.json",
    "reports/v4_07/V4_07_R2_INDEPENDENT_POSTCHECK.json",
    "reports/v4_07/V4_07_R2_MACHINE_VECTOR_COVERAGE.json",
    "reports/v4_07/V4_07_R2_PARAMETER_BINDING_VERIFICATION.json",
    "reports/v4_07/V4_07_R2_MULTI_DATE_CONTEXT_VERIFICATION.json",
    "reports/v4_07/V4_07_R2_DETERMINISM_VERIFICATION.json",
    "reports/v4_07/V4_07_R2_RUNTIME_TEST_RECEIPT.json",
    "reports/v4_07/V4_07_R2_ISOLATED_FULL_REGRESSION.json",
    "reports/v4_07/V4_07_R2_MIGRATION_ROLLBACK_VERIFICATION.json",
    "reports/v4_07/V4_07_R2_CLEAN_CHECKOUT_VERIFICATION.json",
    "reports/audits/V4_07_PRIOR_RPS_ACCEPTED_INPUT_BOOTSTRAP_AUDIT_20260930.md",
    "docs/evidence/V4_06_R2_ACCEPTED_HEAD_PROMOTION_TASK_20260930.md",
    "src/v4/base_seed.py",
    "scripts/run_v4_07_base_seed.py",
    "scripts/verify_v4_07_base_seed.py",
    "scripts/verify_v4_07_machine_vectors.py",
    "scripts/verify_v4_07_r2_parameter_binding.py",
    "scripts/verify_v4_07_r2_context_generalization.py",
    "scripts/verify_v4_07_r2_determinism.py",
    "scripts/record_v4_07_r2_runtime_tests.py",
    "scripts/verify_v4_07_r2_clean_checkout.py",
    "scripts/build_v4_07_r2_closure.py",
    "tests/v4_07/test_base_seed.py",
    "config/v4_07_base_seed_contract_v1.json",
    "config/v4_07_parameter_set_v1.json",
    "config/v4_07_field_registry_v1.json",
    "config/v4_07_machine_vectors_v1.json",
    "reports/v4_07/V4_07_CONTRACT_FREEZE_RECEIPT.json",
    "src/workbench_db/migrations/v4_postgres/015_v4_07_base_seed_results.sql",
    "src/workbench_db/migrations/v4_postgres/rollback/015_v4_07_base_seed_results.sql",
    "reports/v4_07/staging/V4_07_BASE_SEED_CANDIDATE_R2.jsonl.gz",
)


def file_sha(path: Path) -> str:
    sha = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            sha.update(chunk)
    return sha.hexdigest()


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def atomic_write(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def main() -> int:
    candidate = read_json(ROOT / "reports/v4_07/V4_07_R2_FULL_MARKET_CANDIDATE_RECEIPT.json")
    independent = read_json(ROOT / "reports/v4_07/V4_07_R2_INDEPENDENT_POSTCHECK.json")
    machine = read_json(ROOT / "reports/v4_07/V4_07_R2_MACHINE_VECTOR_COVERAGE.json")
    parameters = read_json(ROOT / "reports/v4_07/V4_07_R2_PARAMETER_BINDING_VERIFICATION.json")
    contexts = read_json(ROOT / "reports/v4_07/V4_07_R2_MULTI_DATE_CONTEXT_VERIFICATION.json")
    determinism = read_json(ROOT / "reports/v4_07/V4_07_R2_DETERMINISM_VERIFICATION.json")
    runtime = read_json(ROOT / "reports/v4_07/V4_07_R2_RUNTIME_TEST_RECEIPT.json")
    regression = read_json(ROOT / "reports/v4_07/V4_07_R2_ISOLATED_FULL_REGRESSION.json")
    migration = read_json(ROOT / "reports/v4_07/V4_07_R2_MIGRATION_ROLLBACK_VERIFICATION.json")
    clean_checkout = read_json(ROOT / "reports/v4_07/V4_07_R2_CLEAN_CHECKOUT_VERIFICATION.json")
    candidate_file = (ROOT / candidate["artifact_path"]).resolve()
    if not candidate_file.is_relative_to(ROOT.resolve()):
        raise ValueError("candidate receipt artifact path is not inside the repository")
    if file_sha(candidate_file) != candidate["artifact_sha256"]:
        raise ValueError("candidate artifact SHA-256 does not match its receipt")
    if independent.get("status") != "PASS_INDEPENDENT_SOURCE_RECOMPUTE" or independent.get("mismatch_count") != 0:
        raise ValueError("independent source recompute is not PASS")
    if independent.get("candidate_logical_digest") != candidate.get("logical_artifact_digest"):
        raise ValueError("candidate and independent logical digests differ")
    if machine.get("status") != "PASS" or machine.get("mismatch_count") != 0:
        raise ValueError("machine vector gate is not PASS")
    if parameters.get("status") != "PASS_PARAMETER_INSTANCE_DRIVES_ALL_EXECUTORS":
        raise ValueError("parameter binding verification is not PASS")
    if not parameters.get("formal_parameter_config_unchanged"):
        raise ValueError("formal parameter package changed during fixture perturbation")
    if contexts.get("status") != "PASS_CONTEXT_DRIVEN_MULTI_DATE_PRODUCER":
        raise ValueError("multi-date context verification is not PASS")
    if determinism.get("status") != "PASS_IDENTICAL_CONTEXT_REPLAY":
        raise ValueError("determinism gate is not PASS")
    if runtime.get("status") != "PASS" or regression.get("status") != "PASS_ISOLATED_FULL_REGRESSION":
        raise ValueError("runtime or isolated full regression is not PASS")
    if migration.get("status") != "PASS_ISOLATED_MIGRATION_AND_ROLLBACK":
        raise ValueError("migration and rollback gate is not PASS")
    if clean_checkout.get("status") != "PASS_CLEAN_CHECKOUT_REPLAY":
        raise ValueError("clean-checkout replay is not PASS")

    stage_head_path = ACCEPTED_ROOT / "data/v4/V4_STAGE_ACCEPTED_HEAD.json"
    accepted_head_path = ACCEPTED_ROOT / "data/v4/V4_05_ACCEPTED_HEAD.json"
    stage_head = read_json(stage_head_path)
    if stage_head.get("v4_07_entry") != "NOT_STARTED":
        raise ValueError("V4-07 accepted entry unexpectedly moved during candidate work")
    if stage_head.get("v4_08_sector_entry") != "BLOCKED_UNTIL_ACCEPTED_PIT_MEMBERSHIP_BASELINE_AND_RECONSTRUCTION":
        raise ValueError("V4-08 PIT membership blocker changed")
    if (ROOT / "data/v4/V4_07_ACCEPTED_HEAD.json").exists():
        raise ValueError("V4-07 Accepted Head exists; R2 candidate must not promote")

    created_at = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    result = {
        "contract_id": "V4_07_R2_STAGE_RESULT_V1",
        "stage_contract": "V4_06_R2_CONTRACT_REPAIR_AND_V4_07_BASE_SEED_STAGE_TASK_20260929",
        "status": "V4_07_R2_CANDIDATE_PASS_PENDING_EXTERNAL_ACCEPTANCE_SIGNAL_CAPABILITY_DEGRADED",
        "external_acceptance": "PENDING",
        "starting_head": "131d437e5ad9124e3a60648c5a9ce4c9cf7d39e4",
        "target_trade_date": candidate["target_trade_date"],
        "publication_id": candidate["publication_id"],
        "accepted_core_logical_digest": candidate["source_core_logical_digest"],
        "accepted_identity_count": candidate["accepted_identity_count"],
        "candidate_row_count": candidate["row_count"],
        "candidate_artifact_sha256": candidate["artifact_sha256"],
        "candidate_logical_digest": candidate["logical_artifact_digest"],
        "state_counts": candidate["state_counts"],
        "parameter_binding_status": parameters["status"],
        "multi_date_context_status": contexts["status"],
        "independent_recompute_status": independent["status"],
        "independent_mismatch_count": independent["mismatch_count"],
        "full_regression_summary": regression["test_summary"],
        "isolated_postgresql_version": regression["postgres_version"],
        "migration_rollback_status": migration["status"],
        "clean_checkout_status": clean_checkout["status"],
        "real_signal_capability": "DEGRADED_BY_ACCEPTED_PRIOR_RPS_BOOTSTRAP_UNKNOWN",
        "prior_rps_audit_item": "V4_07_PRIOR_RPS_ACCEPTED_INPUT_BOOTSTRAP_01",
        "v4_06_promotion_task": "V4_06_R2_ACCEPTED_HEAD_PROMOTION_TASK_20260930",
        "v4_07_accepted_head_created": False,
        "v4_05_accepted_head_sha256": file_sha(accepted_head_path),
        "global_stage_head_sha256": file_sha(stage_head_path),
        "v4_08_remains_blocked": True,
        "created_at_utc": created_at,
        "next_stage": "V4_07_R2_INDEPENDENT_EXTERNAL_ACCEPTANCE",
    }
    result_path = ROOT / "reports/v4_07/V4_07_R2_STAGE_RESULT.json"
    atomic_write(result_path, (json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n").encode())

    closure = f"""# V4-07 R2 Candidate Closure

## Result

- Candidate state: {result["status"]}.
- External acceptance: PENDING. This evidence closes the implementation stage and does not self-approve V4-07.
- Candidate artifact: reports/v4_07/staging/V4_07_BASE_SEED_CANDIDATE_R2.jsonl.gz.
- Accepted run: {candidate["target_trade_date"]}; publication {candidate["publication_id"]}; Core digest {candidate["source_core_logical_digest"]}; {candidate["accepted_identity_count"]} identities.
- Candidate SHA-256: {candidate["artifact_sha256"]}.
- Candidate logical digest: {candidate["logical_artifact_digest"]}.
- Output states: TRUE={candidate["state_counts"].get("TRUE", 0)}, FALSE={candidate["state_counts"].get("FALSE", 0)}, UNKNOWN={candidate["state_counts"].get("UNKNOWN", 0)}.

## External audit repairs

- S01 PASS: production evaluator, machine-vector executor, and independent verifier consume an explicit parameter-set instance. Fixture perturbations 3→2.5, 3→4, and 10→11 moved the relevant predicates; formal config SHA stayed {parameters["formal_parameter_set_sha256_after"]}.
- S02 PASS: accepted date, publication identities, source digests, identity count, and board counts flow through a validated accepted run context. Synthetic T/T+1 contexts returned row counts {[item["output_row_count"] for item in contexts["synthetic_accepted_contexts"]]}, with date/publication/digest isolation and no future-row effect.
- Independent verifier recomputed {independent["checked_rows"]} rows with {independent["mismatch_count"]} mismatches and produced the same logical digest.
- Identical accepted-context replay passed. Machine vectors: {machine["checked_vector_count"]} checked, {machine["mismatch_count"]} mismatches.
- Focused V4-07 runtime: {runtime["output"].splitlines()[-1]}.
- Isolated full regression: {regression["test_summary"]} on {regression["postgres_version"]}; disposable PostgreSQL cluster cleaned up. Migration 015 apply/rollback: {migration["status"]}.
- Clean checkout replay: {clean_checkout["status"]} at {clean_checkout["checkout_head"]}; candidate bytes and logical digest match the R2 receipt.

## Scoped capability limitation

The accepted V4-05 input still reports rps5_delta3 UNKNOWN for all {candidate["accepted_identity_count"]} identities because of BOOTSTRAP_INSUFFICIENT_FORWARD_HISTORY. Accepted T-1 close/MA20 fields remain absent. No threshold relaxation, turnover substitution, raw-history reconstruction, or unaccepted RPS fallback was used. Real Base Seed signal capability remains degraded and is tracked separately in reports/audits/V4_07_PRIOR_RPS_ACCEPTED_INPUT_BOOTSTRAP_AUDIT_20260930.md.

## Promotion and next stage

- No V4-07 Accepted Head was created. The global accepted range and V4-05 accepted inputs remain unchanged; V4-08 remains blocked by its PIT membership requirement.
- A separate V4-06 promotion task is prepared at docs/evidence/V4_06_R2_ACCEPTED_HEAD_PROMOTION_TASK_20260930.md. It preserves the open BaoStock live-binding audit and does not execute promotion here.
- Next V4-07 stage: independent external R2 acceptance review.

## Evidence index

- V4_07_R2_STAGE_RESULT.json
- V4_07_R2_STAGE_CANDIDATE_MANIFEST.json
- V4_07_R2_PARAMETER_BINDING_VERIFICATION.json
- V4_07_R2_MULTI_DATE_CONTEXT_VERIFICATION.json
- V4_07_R2_MACHINE_VECTOR_COVERAGE.json
- V4_07_R2_INDEPENDENT_POSTCHECK.json
- V4_07_R2_DETERMINISM_VERIFICATION.json
- V4_07_R2_RUNTIME_TEST_RECEIPT.json
- V4_07_R2_ISOLATED_FULL_REGRESSION.json
- V4_07_R2_MIGRATION_ROLLBACK_VERIFICATION.json
- V4_07_R2_CLEAN_CHECKOUT_VERIFICATION.json
"""
    closure_path = ROOT / "reports/v4_07/V4_07_R2_CLOSURE.md"
    atomic_write(closure_path, closure.encode("utf-8"))

    manifest_files = []
    for relative in EVIDENCE_PATHS + (
        "reports/v4_07/V4_07_R2_STAGE_RESULT.json",
        "reports/v4_07/V4_07_R2_CLOSURE.md",
    ):
        path = ROOT / relative
        if not path.is_file():
            raise FileNotFoundError(f"R2 manifest input is missing: {relative}")
        manifest_files.append({
            "path": relative,
            "sha256": file_sha(path),
            "byte_count": path.stat().st_size,
        })
    manifest = {
        "contract_id": "V4_07_R2_STAGE_CANDIDATE_MANIFEST_V1",
        "stage_contract": result["stage_contract"],
        "candidate_status": result["status"],
        "external_acceptance": "PENDING",
        "created_at_utc": created_at,
        "starting_head": result["starting_head"],
        "accepted_run_context": {
            "trade_date": result["target_trade_date"],
            "publication_id": result["publication_id"],
            "core_logical_digest": result["accepted_core_logical_digest"],
            "identity_count": result["accepted_identity_count"],
            "expected_board_counts": candidate["board_counts"],
        },
        "candidate_artifact": {
            "path": "reports/v4_07/staging/V4_07_BASE_SEED_CANDIDATE_R2.jsonl.gz",
            "sha256": result["candidate_artifact_sha256"],
            "logical_digest": result["candidate_logical_digest"],
            "row_count": result["candidate_row_count"],
        },
        "parameter_set_sha256": parameters["formal_parameter_set_sha256_after"],
        "contract_sha256": candidate["source_bindings"]["contract_sha256"],
        "v4_05_accepted_head_sha256": result["v4_05_accepted_head_sha256"],
        "global_stage_head_sha256": result["global_stage_head_sha256"],
        "accepted_head_mutation": False,
        "v4_07_accepted_head_created": False,
        "files": manifest_files,
        "scoped_file_count": len(manifest_files),
        "next_stage": "V4_07_R2_INDEPENDENT_EXTERNAL_ACCEPTANCE",
    }
    manifest_path = ROOT / "reports/v4_07/V4_07_R2_STAGE_CANDIDATE_MANIFEST.json"
    atomic_write(manifest_path, (json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n").encode())
    print(json.dumps({
        "status": result["status"],
        "manifest_file_count": len(manifest_files),
        "candidate_logical_digest": result["candidate_logical_digest"],
        "full_regression": result["full_regression_summary"],
    }, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
