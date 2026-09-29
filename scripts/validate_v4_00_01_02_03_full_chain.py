from __future__ import annotations

"""Validate 00-03 evidence for external-review readiness without self-acceptance."""

import hashlib
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
V400_RECEIPT = Path("reports/v4_phase0/V4_00_CURRENT_AUTHORITY_NORMALIZATION_R1.json")
PHASE0_RECEIPT = Path("reports/v4_phase0/V4_PHASE0_FINAL_RECEIPT_R5_20260928.json")
GLOBAL_HEAD = Path("data/v4/V4_STAGE_ACCEPTED_HEAD.json")
V401_CANDIDATE = Path("reports/v4_01/V4_01_FINAL_STAGE_CANDIDATE_R10.json")
V401_HEAD_CANDIDATE = Path("data/v4/V4_01_ACCEPTED_HEAD_CANDIDATE.json")
V401_SCAN = Path("reports/v4_01/V4_01_FULL_SCOPE_SOURCE_FINGERPRINT_SCAN_R1.json")
V401_RESOLUTION = Path("reports/v4_01/V4_01_IDENTITY_RELATION_RESOLUTION_R2.json")
V401_POSTCHECK = Path("reports/v4_01/V4_01_IDENTITY_COMPLETENESS_GATE_V2_POSTCHECK_R2.json")
V401_GATE = Path("config/v4_01_identity_completeness_gate_v2.json")
V401_IDENTITY = Path("data/v4/artifact_store/v4_01/security_entity_map_R7_20260927.json")
V401_UNIVERSE = Path("data/v4/artifact_store/v4_01/v4_01_historical_universe_required_R7_20260927.jsonl.gz")
V402_CURRENT = Path("reports/v4_02/V4_02_CURRENT_TRUTH_RECONCILIATION_R2.json")
V402_MAPPING = Path("config/v4_02_stage_acceptance_mapping_v2.json")
V402_HEAD = Path("data/v4/V4_02_ACCEPTED_HEAD.json")
V402_R4_AUDIT = Path("reports/v4_02/V4_02_PRICE_LIMIT_RANGE_EXCEPTION_AUDIT_R4.json")
V402_R6_EXTERNAL = Path("reports/v4_02/V4_02_FINAL_EXTERNAL_ACCEPTANCE_R6.json")
V402_R8_POSTCHECK = Path("reports/v4_02/V4_02_R8_CROSS_STAGE_POSTCHECK_20260928.json")
V402_R6_BUILD = Path("reports/v4_02/V4_02_PRICE_LIMIT_BUILD_R6.json")
V402_MANIFEST = Path("reports/v4_02/V4_02_FINAL_STAGING_MANIFEST_R6.json")
V403_RESEAL = Path("reports/v4_03/V4_03_FOUNDATION_RESEAL_CANDIDATE_R1.json")
V403_AMENDMENT = Path("reports/v4_03/V4_03_SECTOR_OWNERSHIP_AMENDMENT_R1.json")
V403_DISPOSITION = Path("reports/v4_03/V4_03_STAGE_DISPOSITION_R3.json")
V403_HEAD = Path("data/v4/V4_03_ACCEPTED_HEAD.json")
V403_NATIVE = Path("reports/v4_03/V4_03_NATIVE_CONTRACT_ACCEPTANCE_R3.json")
V403_PRODUCER = Path("reports/v4_03/V4_03_CONTRACT_PRODUCER_CONSISTENCY_R3.json")
V403_VECTOR = Path("reports/v4_03/V4_03_AST_GOLDEN_VECTOR_ACCEPTANCE_R3.json")
V403_SECTOR_BOUNDARY = Path("reports/v4_03/V4_03_SECTOR_NATIVE_BOUNDARY_ACCEPTANCE_R1.json")
TEST_RECEIPT = Path("reports/v4_joint/V4_00_01_02_03_FULL_CHAIN_TEST_RECEIPT_R2.json")
TEST_ATTEMPT_FAILED = Path("reports/v4_joint/V4_00_01_02_03_FULL_CHAIN_TEST_ATTEMPT_R1_FAILED.json")
OUTPUT_VALIDATION = Path("reports/v4_joint/V4_00_01_02_03_FULL_CHAIN_VALIDATION_R2.json")
OUTPUT_FINAL = Path("reports/v4_joint/V4_00_01_02_03_FULL_CHAIN_FINAL_RECEIPT_R2.json")
EXTERNAL_AUDIT = Path("docs/evidence/V4_00_01_02_03_FOUNDATION_CANDIDATE_EXTERNAL_AUDIT_R1_20260929.md")
REPAIR_TASK = Path("docs/evidence/V4_00_01_02_03_FOUNDATION_FINAL_REPAIR_TASK_R3_20260929.md")
EXTERNAL_REVIEW_HEAD = "ecfcc3209404df5ccc7daaf6af905459cc075542"


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with (ROOT / path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load(path: Path) -> dict[str, Any]:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def evidence(path: Path) -> dict[str, Any]:
    return {"path": path.as_posix(), "sha256": sha(path), "byte_count": (ROOT / path).stat().st_size}


def atomic_json(path: Path, value: dict[str, Any]) -> bytes:
    target = ROOT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")
    fd, temp = tempfile.mkstemp(prefix=target.name + ".", suffix=".tmp", dir=target.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, target)
    finally:
        Path(temp).unlink(missing_ok=True)
    return payload


def git_text(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def is_ancestor(ancestor: str, descendant: str) -> bool:
    return subprocess.run(
        ["git", "merge-base", "--is-ancestor", ancestor, descendant],
        cwd=ROOT,
        capture_output=True,
        check=False,
    ).returncode == 0


def evidence_diff(test_commit: str, final_evidence_commit: str) -> dict[str, Any]:
    paths = [
        item.replace("\\", "/")
        for item in git_text("diff", "--name-only", f"{test_commit}..{final_evidence_commit}").splitlines()
        if item
    ]

    def allowed(path: str) -> bool:
        if path.startswith(("reports/", "docs/evidence/", "docs/audits/")):
            return True
        if path.startswith("data/v4/") and path.endswith(".json"):
            name = Path(path).name.upper()
            return "CANDIDATE" in name or name.endswith("_CANDIDATE.JSON")
        return False

    blocked = [path for path in paths if not allowed(path)]
    return {
        "paths": paths,
        "blocked_paths": blocked,
        "only_evidence_allowlist": not blocked,
        "allowlist": ["reports/**", "docs/evidence/**", "docs/audits/**", "data/v4/*CANDIDATE*.json"],
    }


def main() -> int:
    v400 = load(V400_RECEIPT)
    phase0 = load(PHASE0_RECEIPT)
    global_head = load(GLOBAL_HEAD)
    v401 = load(V401_CANDIDATE)
    v401_head = load(V401_HEAD_CANDIDATE)
    v401_scan = load(V401_SCAN)
    v401_resolution = load(V401_RESOLUTION)
    v401_postcheck = load(V401_POSTCHECK)
    v402_current = load(V402_CURRENT)
    v402_mapping = load(V402_MAPPING)
    v402_head = load(V402_HEAD)
    v402_r4 = load(V402_R4_AUDIT)
    v402_external = load(V402_R6_EXTERNAL)
    v402_r8 = load(V402_R8_POSTCHECK)
    v402_build = load(V402_R6_BUILD)
    v403_reseal = load(V403_RESEAL)
    v403_amendment = load(V403_AMENDMENT)
    v403_disposition = load(V403_DISPOSITION)
    v403_head = load(V403_HEAD)
    v403_native = load(V403_NATIVE)
    v403_producer = load(V403_PRODUCER)
    v403_vector = load(V403_VECTOR)
    v403_sector = load(V403_SECTOR_BOUNDARY)
    tests = load(TEST_RECEIPT)

    tested_code_commit = str(tests.get("execution_identity", {}).get("tested_code_commit") or "")
    final_evidence_commit = git_text("rev-parse", "HEAD")
    evidence_changes = evidence_diff(tested_code_commit, final_evidence_commit) if tested_code_commit else {
        "paths": [], "blocked_paths": ["MISSING_TESTED_CODE_COMMIT"], "only_evidence_allowlist": False,
        "allowlist": ["reports/**", "docs/evidence/**", "docs/audits/**", "data/v4/*CANDIDATE*.json"],
    }
    external_audit_text = (ROOT / EXTERNAL_AUDIT).read_text(encoding="utf-8")
    skip_receipt = tests.get("skip_details", {})
    skip_items = skip_receipt.get("items", [])
    required_scope_skip_count = int(skip_receipt.get("required_scope_skip_count", -1))
    unexplained_skip_count = int(skip_receipt.get("unexplained_skip_count", -1))

    identity_sha = sha(V401_IDENTITY)
    universe_sha = sha(V401_UNIVERSE)
    required = {
        "V4_00_current_phase0_full_pass": v400.get("status") == "FULL_PASS" and phase0.get("phase0_status") == "FULL_PASS",
        "V4_00_scoped_external_acceptance_evidence": v400.get("v4_00_external_acceptance") == "ACCEPTED_SCOPE_SPECIFIC",
        "V4_00_joint_pending_state_preserved": phase0.get("external_acceptance") == "PENDING_JOINT_EXTERNAL_REVIEW",
        "V4_01_candidate_review_ready_evidence": v401.get("status") == "FULL_PASS_CANDIDATE" and v401.get("external_acceptance") == "PENDING_EXTERNAL_REVIEW" and v401.get("gate_contract_external_acceptance") == "ACCEPTED_BY_EXTERNAL_AUDIT_20260929",
        "V4_01_scan_scope_pass": v401_scan.get("status") == "PASS_TDX_FIRST_SCAN" and v401_scan.get("scope", {}).get("accepted_r7_rows_scanned") == 4035729,
        "V4_01_resolution_union_exact_and_zero_unresolved": v401_resolution.get("status") == "RESOLVED_CANDIDATE" and v401_resolution.get("summary", {}).get("required_scope_unresolved_count") == 0 and v401_resolution.get("summary", {}).get("required_scope_candidate_count") == v401_resolution.get("summary", {}).get("resolution_count") and v401_resolution.get("resolution_coverage", {}).get("status") == "PASS" and v401_resolution.get("resolution_coverage", {}).get("candidate_union_keys") == v401_resolution.get("resolution_coverage", {}).get("resolution_keys"),
        "V4_01_independent_postcheck_pass": v401_postcheck.get("status") == "PASS_INDEPENDENT_POSTCHECK" and all(v401_postcheck.get("checks", {}).values()),
        "V4_01_candidate_binds_unchanged_r7": v401_head.get("canonical_identity", {}).get("sha256") == identity_sha and v401_head.get("historical_universe", {}).get("sha256") == universe_sha and v401_head.get("canonical_identity", {}).get("changed") is False,
        "V4_02_r6_external_acceptance_preserved": v402_head.get("external_acceptance") == "EXTERNALLY_ACCEPTED" and v402_external.get("acceptance_result", {}).get("external_acceptance") == "EXTERNALLY_ACCEPTED",
        "V4_02_r4_range_audit_closed": v402_current.get("status") == "PASS_CURRENT_TRUTH_RECONCILIATION" and v402_r4.get("status") == "CLOSED" and v402_current.get("current_truth", {}).get("current_open_engineering_exception") == 0,
        "V4_02_r6_total_unknown_equals_r6_build": v402_current.get("current_truth", {}).get("r6_price_limit_total_unknown_rows") == 77 and v402_build.get("unknown_rows") == 77,
        "V4_02_unknown_subsets_separately_disclosed": v402_current.get("current_truth", {}).get("r6_unknown_special_phase_rows") == 31 and v402_current.get("current_truth", {}).get("r4_fail_closed_exception_subset_rows") == 31 and v402_current.get("current_truth", {}).get("undispositioned_engineering_exceptions") == 0 and v402_current.get("current_truth", {}).get("unknown_rows_claimed_resolved") == 0,
        "V4_02_upstream_r7_hashes_match": v402_r8.get("r8_binding", {}).get("canonical_identity_sha256") == identity_sha and v402_r8.get("r8_binding", {}).get("canonical_historical_universe_sha256") == universe_sha,
        "V4_03_upstream_hashes_unchanged": v403_reseal.get("status") == "PASS_WITH_SECTOR_SCOPE_DEGRADED_CANDIDATE" and v403_reseal.get("upstream", {}).get("existing_v4_03_head_upstream_identities_match") is True,
        "V4_03_stock_market_candidate_capabilities_pass": all(v403_reseal.get("capabilities", {}).get(name) == "PASS_CANDIDATE" for name in ("STOCK_CORE", "RELATIVE_RPS", "MARKET_REFERENCE", "MARKET_REGIME")),
        "V4_03_sector_contract_passes_but_materialization_stays_blocked": v403_native.get("status") == "PASS" and v403_producer.get("status") == "PASS" and v403_vector.get("status") == "PASS" and v403_sector.get("status") == "BLOCKED_ACCEPTED_SECTOR_MEMBERSHIP_INPUT_MISSING" and v403_sector.get("full_market_artifact") == "NOT_PRODUCED",
        "V4_03_owner_amendment_external_acceptance_bound": v403_amendment.get("external_amendment_acceptance") == "ACCEPTED_BY_EXTERNAL_AUDIT_20260929" and v403_reseal.get("external_amendment_acceptance") == "ACCEPTED_BY_EXTERNAL_AUDIT_20260929",
        "V4_02_mapping_current_truth_matches_r6_and_r4": v402_mapping.get("price_limit_current_truth", {}).get("r4") == "CLOSED" and v402_mapping.get("price_limit_current_truth", {}).get("r6_price_limit_total_unknown_rows") == 77 and v402_mapping.get("price_limit_current_truth", {}).get("r6_unknown_special_phase_rows") == 31 and v402_mapping.get("price_limit_current_truth", {}).get("r4_fail_closed_exception_subset_rows") == 31 and v402_mapping.get("current_disposition", {}).get("open_audits") == [] and "current_fail_closed_unknown_rows" not in v402_mapping.get("current_disposition", {}),
        "combined_clean_code_commit_tests_pass": tests.get("status") == "PASS" and tests.get("return_code") == 0 and tests.get("git_status", {}).get("clean_at_test_start") is True and tests.get("git_status", {}).get("clean_after_tests_before_receipt") is True and tests.get("execution_identity", {}).get("working_tree_clean_at_test_start") is True,
        "required_scope_tests_have_no_skip_and_optional_skips_are_explained": required_scope_skip_count == 0 and unexplained_skip_count == 0 and int(skip_receipt.get("count", -1)) == int(tests.get("counts", {}).get("skipped", 0)),
        "tested_code_commit_is_ancestor_of_final_evidence_commit": bool(tested_code_commit) and is_ancestor(tested_code_commit, final_evidence_commit),
        "final_evidence_commit_contains_only_allowlisted_evidence_changes": evidence_changes["only_evidence_allowlist"],
        "external_review_head_is_ancestor_of_tested_code": EXTERNAL_REVIEW_HEAD in external_audit_text and bool(tested_code_commit) and is_ancestor(EXTERNAL_REVIEW_HEAD, tested_code_commit),
        "external_audit_accepts_gate_contract_and_sector_amendment": "V4_01_IDENTITY_COMPLETENESS_GATE_V2_CONTRACT = EXTERNAL_ACCEPTANCE_PASS" in external_audit_text and "V4_03_SECTOR_OWNERSHIP_AMENDMENT_V1 = EXTERNAL_ACCEPTANCE_PASS" in external_audit_text,
        "global_accepted_head_not_promoted": global_head.get("phase0_status") == "FULL_PASS" and not (ROOT / "data/v4/V4_01_ACCEPTED_HEAD.json").exists(),
        "no_canonical_artifacts_or_tdx_root_mutated": v401_head.get("constraints", {}).get("canonical_identity_mutation") is False and v403_reseal.get("existing_accepted_head_modified") is False and tests.get("tdx_root_write_count") == 0,
    }
    blockers = [name for name, passed in required.items() if not passed]
    status = "FULL_PASS_CANDIDATE" if not blockers else "BLOCKED"
    pending = [
        "V4_01_GATE_V2_IMPLEMENTATION_FINAL_EXTERNAL_REVIEW",
        "JOINT_00_01_02_03_FINAL_EXTERNAL_ACCEPTANCE",
    ]
    observed = datetime.now(timezone.utc).isoformat(timespec="seconds")
    validation = {
        "contract_id": "V4_00_01_02_03_FULL_CHAIN_VALIDATION_R2",
        "version": "2.0.0-candidate",
        "validator_mode": "CANDIDATE_EXTERNAL_REVIEW_READINESS",
        "stage": "V4-00..V4-03 FULL-CHAIN CANDIDATE VALIDATION",
        "status": status,
        "external_review_ready": status == "FULL_PASS_CANDIDATE",
        "accepted_chain_status": "NOT_GRANTED_PENDING_EXTERNAL_ACCEPTANCE",
        "observed_at_utc": observed,
        "checks": required,
        "blockers": blockers,
        "pending_external_acceptance": pending,
        "v4_04_entry": "PENDING_FINAL_EXTERNAL_ACCEPTANCE",
        "v4_08_sector_rotation": "BLOCKED_UNTIL_ACCEPTED_PIT_MEMBERSHIP_BASELINE_AND_RECONSTRUCTION",
        "allowed_non_blocking": {
            "BSE_OPTIONAL_DEGRADED": True,
            "INCREMENTAL_UPDATE_DEFERRED_NON_BLOCKING": True,
            "SOURCE_FINGERPRINT_CALIBRATION_DEFERRED_NON_BLOCKING_RESEARCH": True,
            "V4_05_NOT_STARTED": True,
            "V4_06_NOT_STARTED": True,
            "V4_08_MEMBERSHIP_ROTATION_NOT_STARTED_OR_BLOCKED": True,
            "SCANNER_TRADING_FOCUS_NOT_STARTED": True,
        },
        "canonical_changes": {
            "v4_01_identity_map_changed": False,
            "v4_01_universe_changed": False,
            "v4_02_rebuilt": False,
            "v4_03_rebuilt": False,
            "v4_03_scope_amendment_created_as_candidate": True,
        },
        "execution_counts": {"scanner_runs": 0, "trading_runs": 0, "tdx_root_writes": 0},
        "evidence": {
            path.as_posix(): evidence(path)
            for path in (
                V400_RECEIPT, PHASE0_RECEIPT, V401_CANDIDATE, V401_HEAD_CANDIDATE, V401_SCAN, V401_RESOLUTION, V401_POSTCHECK,
                V402_CURRENT, V402_MAPPING, V402_HEAD, V402_R4_AUDIT, V402_R6_EXTERNAL, V402_R8_POSTCHECK, V402_MANIFEST,
                V403_RESEAL, V403_AMENDMENT, V403_DISPOSITION, V403_HEAD, V403_NATIVE, V403_PRODUCER, V403_VECTOR,
                V403_SECTOR_BOUNDARY, V402_R6_BUILD, TEST_RECEIPT, TEST_ATTEMPT_FAILED, EXTERNAL_AUDIT, REPAIR_TASK,
            )
        },
        "stage_record": {
            "stage_contract": "V4-00..V4-03 foundation final repair task R3 and candidate external audit R1",
            "evidence": "Exact V4-01 candidate union resolution, independently checked V4-02 count reconciliation, accepted V4-03 amendment, clean-code test receipt, and evidence commit allowlist binding",
            "acceptance_result": status,
            "next_stage": "REQUEST_FINAL_EXTERNAL_ACCEPTANCE; KEEP_GLOBAL_HEAD_UNPROMOTED_AND_V4_04_PENDING" if status == "FULL_PASS_CANDIDATE" else "REPAIR_BLOCKERS",
        },
        "execution_identity": {
            "tested_code_commit": tested_code_commit,
            "final_evidence_commit": final_evidence_commit,
            "external_review_head": EXTERNAL_REVIEW_HEAD,
            "tested_code_ancestor_of_final_evidence": bool(tested_code_commit) and is_ancestor(tested_code_commit, final_evidence_commit),
            "evidence_diff_allowlist": evidence_changes,
            "script_sha256": sha(Path(__file__).resolve().relative_to(ROOT)),
            "python_version": sys.version.split()[0],
        },
    }
    validation_bytes = atomic_json(OUTPUT_VALIDATION, validation)
    validation_sha = hashlib.sha256(validation_bytes).hexdigest()

    final = {
        "contract_id": "V4_00_01_02_03_FULL_CHAIN_FINAL_RECEIPT_R2",
        "version": "2.0.0-candidate",
        "stage": "V4-00..V4-03 FOUNDATION FULL-CHAIN CANDIDATE",
        "status": status,
        "tested_code_commit": tested_code_commit,
        "final_evidence_commit": final_evidence_commit,
        "external_review_head": EXTERNAL_REVIEW_HEAD,
        "external_audit": evidence(EXTERNAL_AUDIT),
        "external_review_ready": status == "FULL_PASS_CANDIDATE",
        "final_external_acceptance": "NOT_GRANTED",
        "v4_04_entry": "PENDING_FINAL_EXTERNAL_ACCEPTANCE",
        "v4_00": {
            "status": v400.get("status"),
            "external_acceptance": v400.get("v4_00_external_acceptance"),
            "authority_receipt": evidence(V400_RECEIPT),
        },
        "v4_01": {
            "status": v401.get("status"),
            "external_acceptance": v401.get("external_acceptance"),
            "gate_contract_external_acceptance": v401.get("gate_contract_external_acceptance"),
            "accepted_head": "CANDIDATE_ONLY",
            "identity_sha256": identity_sha,
            "universe_sha256": universe_sha,
            "scan": evidence(V401_SCAN),
            "resolution": evidence(V401_RESOLUTION),
            "postcheck": evidence(V401_POSTCHECK),
        },
        "v4_02": {
            "status": v402_head.get("status"),
            "external_acceptance": v402_head.get("external_acceptance"),
            "current_open_engineering_exception": v402_current.get("current_truth", {}).get("current_open_engineering_exception"),
            "r6_price_limit_total_unknown_rows": v402_current.get("current_truth", {}).get("r6_price_limit_total_unknown_rows"),
            "r6_unknown_special_phase_rows": v402_current.get("current_truth", {}).get("r6_unknown_special_phase_rows"),
            "r4_fail_closed_exception_subset_rows": v402_current.get("current_truth", {}).get("r4_fail_closed_exception_subset_rows"),
            "undispositioned_engineering_exceptions": v402_current.get("current_truth", {}).get("undispositioned_engineering_exceptions"),
            "unknown_rows_claimed_resolved": v402_current.get("current_truth", {}).get("unknown_rows_claimed_resolved"),
            "current_truth": evidence(V402_CURRENT),
            "accepted_head": evidence(V402_HEAD),
        },
        "v4_03": {
            "status": v403_reseal.get("status"),
            "capabilities": v403_reseal.get("capabilities"),
            "ownership_amendment": evidence(V403_AMENDMENT),
            "amendment_external_acceptance": v403_amendment.get("external_amendment_acceptance"),
            "accepted_head_unchanged": True,
        },
        "deferred_non_blocking": validation["allowed_non_blocking"],
        "future_owner_capabilities": {"V4_08_SECTOR_ROTATION": "BLOCKED_UNTIL_ACCEPTED_PIT_MEMBERSHIP", "V4_04": "PENDING_FINAL_EXTERNAL_ACCEPTANCE"},
        "test_receipt": evidence(TEST_RECEIPT),
        "superseded_test_attempt": {
            **evidence(TEST_ATTEMPT_FAILED),
            "status": load(TEST_ATTEMPT_FAILED).get("status"),
            "result_disposition": "SUPERSEDED_BY_FULL_PASSING_RERUN; stale test fixture/API expectations corrected; production V4-00 code was not changed",
        },
        "chain_validator_receipt": {"path": OUTPUT_VALIDATION.as_posix(), "sha256": validation_sha},
        "canonical_artifact_changes": validation["canonical_changes"],
        "scanner_trading_tdx_counts": validation["execution_counts"],
        "pending_external_acceptance": pending,
        "blockers": blockers,
        "next_stage": "FINAL_EXTERNAL_ACCEPTANCE; NO_GLOBAL_ACCEPTED_HEAD_PROMOTION; V4_04_PENDING" if status == "FULL_PASS_CANDIDATE" else "REPAIR_BLOCKERS",
        "stage_record": validation["stage_record"],
    }
    final_bytes = atomic_json(OUTPUT_FINAL, final)
    print(json.dumps({
        "status": status,
        "external_review_ready": status == "FULL_PASS_CANDIDATE",
        "checks_passed": sum(required.values()),
        "checks_total": len(required),
        "blockers": blockers,
        "validation_sha256": validation_sha,
        "final_receipt_sha256": hashlib.sha256(final_bytes).hexdigest(),
        "external_acceptance": "NOT_GRANTED",
        "v4_04_entry": "PENDING_FINAL_EXTERNAL_ACCEPTANCE",
    }, ensure_ascii=False, indent=2))
    return 0 if status == "FULL_PASS_CANDIDATE" else 2


if __name__ == "__main__":
    raise SystemExit(main())
