"""Shared immutable contract checks for V4-05 promotion and V4-06 entry."""
from __future__ import annotations

from hashlib import sha256
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
START_HEAD = "06f1c0fd4a60e4f37e5f93fe729c84a04205c16b"
GLOBAL_HEAD = "data/v4/V4_STAGE_ACCEPTED_HEAD.json"
ACCEPTED_HEAD = "data/v4/V4_05_ACCEPTED_HEAD.json"
PROMOTION_TASK = "docs/evidence/V4_05_ACCEPTED_HEAD_PROMOTION_V4_06_ENTRY_TASK_20260929.md"
EXTERNAL_ACCEPTANCE = "docs/evidence/V4_05_REPLAY_GATE_A_R4_2_FINAL_EXTERNAL_ACCEPTANCE_20260929.md"
CANDIDATE_MANIFEST = "reports/v4_05/V4_05_R4_2_STAGE_CANDIDATE_MANIFEST.json"
EXACT_BINDING = "reports/v4_05/V4_05_R4_2_EXACT_CANDIDATE_LEDGER_BINDING.json"
POSTGRES_LEDGER = "reports/v4_05/V4_05_R4_2_POSTGRES_REVISION_LEDGER_IDEMPOTENCY.json"
CLEAN_RUNTIME = "reports/v4_05/V4_05_R4_2_CLEAN_CHECKOUT_RUNTIME.json"
INDEPENDENT_POSTCHECK = "reports/v4_05/V4_05_R4_2_INDEPENDENT_POSTCHECK.json"
PROMOTION_PREFLIGHT = "reports/v4_joint/V4_05_ACCEPTED_HEAD_PROMOTION_PREFLIGHT_R1.json"
PROMOTION_VALIDATION = "reports/v4_joint/V4_05_ACCEPTED_HEAD_PROMOTION_VALIDATION_R1.json"
PROMOTION_RECEIPT = "reports/v4_joint/V4_05_ACCEPTED_HEAD_PROMOTION_RECEIPT_R1.json"

DECISION = "V4_05_EXTERNAL_ACCEPTANCE_PASS_R4_2"
CANDIDATE = "V4_05_DATA_FACTOR_REPLAY_DEGRADED_PASS_CANDIDATE_R4_2"
CORE_LOGICAL_DIGEST = "d195518796acc64015174eac8f9bb8721a27095311ece00baedf8c12b0633e74"
SNAPSHOT_ID = "92773afba01ac100c9165190423d0228c2b5f9a42549ef8f4d955eba904c3cdb"
HISTORICAL_BLOCK = "BLOCKED_NO_FIRST_AVAILABILITY_EVIDENCE"
V408_BLOCK = "BLOCKED_UNTIL_ACCEPTED_PIT_MEMBERSHIP_BASELINE_AND_RECONSTRUCTION"

CAPABILITIES = {
    "DATA_FACTOR_REPLAY_PASS": "DEGRADED_PASS",
    "CURRENT_FORWARD_ADJUSTED_PRICE": "FULL_PASS",
    "WEEKLY_PERIOD": "DEGRADED_PASS",
    "MONTHLY_PERIOD": "DEGRADED_PASS",
    "PURE_CORE_FACTORS": "DEGRADED_PASS",
    "MARKET_REFERENCE": "FULL_PASS",
    "MARKET_REGIME": "DEGRADED_PASS",
    "CURRENT_FORWARD_STOCK_CORE": "DEGRADED_PASS",
    "HISTORICAL_AS_RECORDED_ADJUSTED_PRICE": HISTORICAL_BLOCK,
}

ARTIFACTS = {
    "period_asof": {
        "path": "reports/v4_05/staging/V4_05_R4_1_PERIOD_ASOF.jsonl.gz",
        "sha256": "e54674e8459e1258610639d76fac7a5f7b6093a4013f912b8937fb6fa96c2233",
        "receipt": "reports/v4_05/V4_05_R4_1_PERIOD_ASOF.json",
    },
    "full_scope_factors": {
        "path": "reports/v4_05/staging/V4_05_R4_1_FULL_SCOPE_FACTORS.jsonl.gz",
        "sha256": "17ae571629b76399e32d9e8a243268ea1fac619e1c5168d307bfd8ebf1494c48",
        "logical_digest": "0cfe708567935726f0ad51ae4bb47237ec7aee556db3437c12f21f0c623bd0d2",
        "receipt": "reports/v4_05/V4_05_R4_1_FULL_SCOPE_FACTORS_RECEIPT.json",
    },
    "core_profile": {
        "path": "reports/v4_05/staging/V4_05_R4_1_FULL_MARKET_CORE_PROFILE.jsonl.gz",
        "sha256": "9a6ebedc715bc4b310ecf76c77e01cb6dfe9dadc17d335b5fc9afbcc2f6f3fa0",
        "logical_digest": CORE_LOGICAL_DIGEST,
        "receipt": "reports/v4_05/V4_05_R4_1_CORE_PROFILE_REPLAY.json",
    },
}

R4_1_PROOFS = {
    "canonical_hash_policy": "reports/v4_05/V4_05_R4_1_CANONICAL_HASH_POLICY.json",
    "accepted_head_hash_validation": "reports/v4_05/V4_05_R4_1_ACCEPTED_HEAD_HASH_VALIDATION.json",
    "clean_clone_determinism": "reports/v4_05/V4_05_R4_1_CLEAN_CLONE_DETERMINISM.json",
    "published_lfs_restore": "reports/v4_05/V4_05_R4_1_PUBLISHED_LFS_RESTORE.json",
}

R4_1_RECEIPTS = {
    "period_asof": ARTIFACTS["period_asof"]["receipt"],
    "full_scope_factors": ARTIFACTS["full_scope_factors"]["receipt"],
    "core_profile": ARTIFACTS["core_profile"]["receipt"],
    "market_reference": "reports/v4_05/V4_05_R4_1_MARKET_REFERENCE.json",
    "market_regime": "reports/v4_05/V4_05_R4_1_MARKET_REGIME.json",
    "market_snapshot_identity": "reports/v4_05/V4_05_R4_1_MARKET_SNAPSHOT_IDENTITY.json",
}

EVIDENCE_PATHS = {
    "promotion_task": PROMOTION_TASK,
    "external_acceptance": EXTERNAL_ACCEPTANCE,
    "candidate_manifest": CANDIDATE_MANIFEST,
    "r4_1_candidate_manifest": "reports/v4_05/V4_05_R4_1_STAGE_CANDIDATE_MANIFEST.json",
    "exact_candidate_ledger_binding": EXACT_BINDING,
    "postgres_revision_ledger": POSTGRES_LEDGER,
    "clean_checkout_runtime": CLEAN_RUNTIME,
    "independent_postcheck": INDEPENDENT_POSTCHECK,
    "r4_2_closure": "reports/v4_05/V4_05_R4_2_CLOSURE.md",
    "r4_1_canonical_hash_policy": R4_1_PROOFS["canonical_hash_policy"],
    "r4_1_accepted_head_hash_validation": R4_1_PROOFS["accepted_head_hash_validation"],
    "r4_1_clean_clone_determinism": R4_1_PROOFS["clean_clone_determinism"],
    "r4_1_published_lfs_restore": R4_1_PROOFS["published_lfs_restore"],
    **{f"r4_1_{name}_receipt": path for name, path in R4_1_RECEIPTS.items()},
}


def file_identity(relative: str) -> dict:
    path = (ROOT / relative).resolve()
    if not path.is_relative_to(ROOT.resolve()) or not path.is_file():
        raise ValueError(f"required evidence path missing or outside repository: {relative}")
    digest = sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return {"path": relative, "sha256": digest.hexdigest(), "byte_count": path.stat().st_size}


def verify_binding(item: dict) -> bool:
    actual = file_identity(item["path"])
    return (actual["sha256"] == item.get("sha256") and
            ("byte_count" not in item or actual["byte_count"] == item["byte_count"]))


def load_json(relative: str) -> dict:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True, encoding="utf-8").strip()


def git_bytes(*args: str) -> bytes:
    return subprocess.check_output(["git", *args], cwd=ROOT)


def atomic_json(relative: str, value: dict) -> None:
    path = ROOT / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_bytes((json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8"))
    temp.replace(path)


def authority_checks() -> dict:
    """Verify reviewed external authority, receipts, exact outputs, and frozen values."""
    external = (ROOT / EXTERNAL_ACCEPTANCE).read_text(encoding="utf-8")
    normalized_external = external.replace("`", "")
    task = (ROOT / PROMOTION_TASK).read_text(encoding="utf-8")
    manifest = load_json(CANDIDATE_MANIFEST)
    exact = load_json(EXACT_BINDING)
    postgres = load_json(POSTGRES_LEDGER)
    clean = load_json(CLEAN_RUNTIME)
    postcheck = load_json(INDEPENDENT_POSTCHECK)
    market_reference = load_json(R4_1_RECEIPTS["market_reference"])
    market_regime = load_json(R4_1_RECEIPTS["market_regime"])
    snapshot = load_json(R4_1_RECEIPTS["market_snapshot_identity"])
    proofs = {key: load_json(path) for key, path in R4_1_PROOFS.items()}

    remote_lines = git("ls-remote", "origin", "refs/heads/codex/v4-system-reform").splitlines()
    remote_head = remote_lines[0].split()[0] if remote_lines else ""
    baseline_global = json.loads(git_bytes("show", f"{START_HEAD}:{GLOBAL_HEAD}").decode("utf-8"))
    current_head = git("rev-parse", "HEAD")

    artifact_identities = {}
    artifact_checks = True
    expected_receipt_status = {
        "period_asof": "PASS_WITH_FIELD_LOCAL_UNKNOWN",
        "full_scope_factors": "DEGRADED_PASS_PRIOR_RPS_BOOTSTRAP_UNKNOWN",
        "core_profile": "DEGRADED_PASS_FIELD_LOCAL_UNKNOWN",
    }
    for name, expected in ARTIFACTS.items():
        actual = file_identity(expected["path"])
        artifact_identities[name] = actual
        artifact_checks = artifact_checks and actual["sha256"] == expected["sha256"]
        receipt = load_json(expected["receipt"])
        artifact_checks = artifact_checks and receipt.get("status") == expected_receipt_status[name]
        artifact_checks = artifact_checks and receipt.get("artifact_sha256") == expected["sha256"]
        if "logical_digest" in expected:
            artifact_checks = artifact_checks and receipt.get("logical_digest") == expected["logical_digest"]

    reference_values = {str(h): market_reference["horizons"][str(h)]["reference_return"] for h in (1, 3, 5)}
    expected_reference_values = {
        "1": -0.022314506957301243,
        "3": -0.03792535346523633,
        "5": -0.01769091161662751,
    }
    exact_comparisons = exact.get("exact_binding_comparisons", {})
    ledger_cases = postgres.get("cases", {}).get("cases", postgres.get("cases", {}))
    case_pass = (
        ledger_cases.get("I01_identical_replay", {}).get("status") == "PASS" and
        ledger_cases.get("I02_changed_source_revision", {}).get("status") == "PASS" and
        bool(ledger_cases.get("I03_negative_guards")) and
        all(row.get("rejected") for row in ledger_cases.get("I03_negative_guards", {}).values()) and
        bool(ledger_cases.get("I04_transaction_rollback")) and
        all(row.get("passed") for row in ledger_cases.get("I04_transaction_rollback", ())) and
        ledger_cases.get("I05_prior_state_freeze", {}).get("publication_head_unchanged") is True and
        all(ledger_cases.get("I05_prior_state_freeze", {}).get(key, {}).get("rejected") is True for key in (
            "replace_prior_publication_head", "delete_prior_publication_head",
            "change_prior_state_head", "change_prior_state_logical_digest"))
    )
    lfs_inputs = clean.get("lfs_restore", {}).get("inputs", {})
    r4_1_lfs = proofs["published_lfs_restore"].get("restored_artifacts", {})
    r4_1_lfs_paths = [ARTIFACTS[name]["path"] for name in ("core_profile", "full_scope_factors", "period_asof")]
    clean_commit_is_ancestor = subprocess.run(
        ["git", "merge-base", "--is-ancestor", clean.get("implementation_commit", ""), START_HEAD],
        cwd=ROOT, capture_output=True,
    ).returncode == 0
    lfs_ok = (clean.get("lfs_restore", {}).get("status") == "PASS" and
              bool(lfs_inputs) and all(item.get("matches") is True for item in lfs_inputs.values()) and
              clean.get("clone_source") == git("remote", "get-url", "origin") and
              clean.get("implementation_commit") == manifest.get("implementation_commit") and
              clean_commit_is_ancestor and
              all(path in r4_1_lfs and
                  r4_1_lfs[path].get("pointer_matches_artifact") is True and
                  r4_1_lfs[path].get("clone_matches_pointer") is True for path in r4_1_lfs_paths))

    expected_scope_in_external = all(
        f"{capability} = {status}" in normalized_external for capability, status in CAPABILITIES.items()
    )
    evidence_checks = all(verify_binding(file_identity(path)) for path in EVIDENCE_PATHS.values())
    r4_1_proofs_pass = all(proof.get("status") == "PASS" for proof in proofs.values())

    return {
        "reviewed_starting_head": current_head == START_HEAD and remote_head == START_HEAD,
        "external_acceptance_decision_exact": DECISION in external and START_HEAD in external,
        "external_acceptance_scope_complete": expected_scope_in_external,
        "promotion_task_matches_stage": all(token in task for token in (
            "V4_05_ACCEPTED_HEAD_PROMOTION_PASS_R1", "v4_06_entry = AUTHORIZED_SUPPLEMENTAL_ENRICHMENT")),
        "candidate_manifest_authority": manifest.get("status") == CANDIDATE and
            manifest.get("external_acceptance") == "PENDING" and
            manifest.get("all_exact_bindings_match") is True and manifest.get("old_r4_binding_count") == 0,
        "r4_2_exact_binding": exact.get("status") == "PASS" and
            exact.get("all_exact_bindings_match") is True and exact.get("old_r4_binding_count") == 0 and
            all(value is True for value in exact_comparisons.values()) and len(exact_comparisons) >= 10,
        "postgresql_g08": postgres.get("status") == "PASS" and
            "18.6" in postgres.get("postgres_version", "") and
            postgres.get("applied_migration_count") == 12 and
            postgres.get("production_connection_used") is False and case_pass and
            postgres.get("actual_state_head", {}).get("logical_digest") == CORE_LOGICAL_DIGEST and
            postgres.get("actual_publication_head", {}).get("state_logical_digest") == CORE_LOGICAL_DIGEST,
        "r4_2_runtime": clean.get("status") == "PASS" and
            clean.get("exact_candidate_binding_test", {}).get("passed") is True and
            clean.get("postgres_ledger_run", {}).get("status") == "PASS" and
            clean.get("postgres_ledger_run", {}).get("all_exact_bindings_match") is True and
            clean.get("postgres_ledger_run", {}).get("old_r4_binding_count") == 0,
        "r4_2_independent_postcheck": postcheck.get("status") == "PASS" and
            postcheck.get("external_acceptance") == "PENDING" and
            all(postcheck.get("checks", {}).values()),
        "r4_1_canonical_hash_and_head_validation":
            proofs["canonical_hash_policy"].get("status") == "PASS" and
            proofs["accepted_head_hash_validation"].get("status") == "PASS",
        "r4_1_clean_clone_determinism_and_published_lfs":
            proofs["clean_clone_determinism"].get("status") == "PASS" and
            proofs["published_lfs_restore"].get("status") == "PASS" and lfs_ok,
        "accepted_artifact_hashes": artifact_checks,
        "market_snapshot_reference_and_regime":
            snapshot.get("status") == "PASS" and snapshot.get("target_trade_date") == "2026-09-28" and
            snapshot.get("target_market_snapshot_id") == SNAPSHOT_ID and
            market_reference.get("status") == "PASS" and market_reference.get("target_market_snapshot_id") == SNAPSHOT_ID and
            reference_values == expected_reference_values and
            market_reference["horizons"]["1"].get("output_digest") == "80d8ac5cc69e8ae4d165f89324e45d0cc7e49a81d13339b31ff8fbec5e578554" and
            market_regime.get("status") == "DEGRADED_PASS" and
            market_regime.get("target_row", {}).get("trend_axis") == "UNKNOWN" and
            market_regime.get("identity", {}).get("market_snapshot_id") == SNAPSHOT_ID,
        "all_required_evidence_paths_integral": evidence_checks,
    }, {
        "baseline_global_head": baseline_global,
        "candidate_manifest": manifest,
        "exact_binding": exact,
        "postgres": postgres,
        "clean_runtime": clean,
        "postcheck": postcheck,
        "proofs": proofs,
        "market_reference_values": reference_values,
        "artifact_identities": artifact_identities,
        "remote_head": remote_head,
        "current_head": current_head,
    }


def global_transition_check(global_head: dict, baseline: dict) -> bool:
    allowed = {
        "accepted_stage_range", "version", "v4_05_entry", "v4_05_status",
        "v4_05_external_acceptance", "v4_05_binding", "v4_06_entry", "v4_06_status", "v4_07_entry",
    }
    if any(global_head.get(key) != value for key, value in baseline.items() if key not in allowed):
        return False
    if any(key not in allowed for key in set(global_head) - set(baseline)):
        return False
    return (
        global_head.get("accepted_stage_range") == "V4_00_TO_V4_05_ACCEPTED" and
        global_head.get("v4_05_status") == "DATA_FACTOR_REPLAY_DEGRADED_PASS" and
        global_head.get("v4_05_external_acceptance") == "EXTERNALLY_ACCEPTED" and
        global_head.get("v4_05_entry") == "COMPLETED_EXTERNALLY_ACCEPTED" and
        global_head.get("v4_08_sector_entry") == V408_BLOCK and
        global_head.get("historical_as_recorded_adjusted_price") == HISTORICAL_BLOCK
    )


def validate(phase: str = "final") -> dict:
    if phase not in {"pre-entry", "final"}:
        raise ValueError("phase must be pre-entry or final")
    checks, detail = authority_checks()
    accepted_path = ROOT / ACCEPTED_HEAD
    global_path = ROOT / GLOBAL_HEAD
    accepted = load_json(ACCEPTED_HEAD) if accepted_path.is_file() else {}
    global_head = load_json(GLOBAL_HEAD)
    baseline = detail["baseline_global_head"]

    expected_capabilities = CAPABILITIES
    actual_artifacts = {
        name: ({**identity, "logical_digest": ARTIFACTS[name]["logical_digest"]}
               if "logical_digest" in ARTIFACTS[name] else identity)
        for name, identity in detail["artifact_identities"].items()
    }
    manifest_identity = file_identity(CANDIDATE_MANIFEST)
    expected_evidence = {name: file_identity(path) for name, path in EVIDENCE_PATHS.items()}

    accepted_head_checks = (
        accepted.get("contract_id") == "V4_05_ACCEPTED_HEAD_V1" and
        accepted.get("stage") == "V4-05" and
        accepted.get("status") == "DATA_FACTOR_REPLAY_DEGRADED_PASS" and
        accepted.get("external_acceptance") == "EXTERNALLY_ACCEPTED" and
        accepted.get("external_acceptance_decision") == DECISION and
        accepted.get("accepted_candidate") == CANDIDATE and
        accepted.get("target_trade_date") == "2026-09-28" and
        accepted.get("capabilities") == expected_capabilities and
        accepted.get("historical_as_recorded_adjusted_price") == HISTORICAL_BLOCK and
        accepted.get("accepted_manifest") == manifest_identity and
        accepted.get("accepted_artifacts") == actual_artifacts and
        accepted.get("market_snapshot_id") == SNAPSHOT_ID and
        accepted.get("market_reference_values") == detail["market_reference_values"] and
        accepted.get("market_regime_trend_axis") == "UNKNOWN" and
        accepted.get("ledger_state_logical_digest") == CORE_LOGICAL_DIGEST
    )
    evidence_bindings = accepted.get("evidence_bindings", {})
    evidence_binding_checks = (
        evidence_bindings == expected_evidence and
        all(verify_binding(item) for item in evidence_bindings.values())
    )
    head_binding = file_identity(ACCEPTED_HEAD)
    global_binding = global_head.get("v4_05_binding", {})
    global_v405_binding = (
        global_binding == head_binding and verify_binding(global_binding)
    )
    no_business_successor_outputs = all(not (ROOT / relative).exists() for relative in (
        "data/v4/V4_06_ACCEPTED_HEAD.json", "data/v4/V4_07_ACCEPTED_HEAD.json",
        "data/v4/V4_08_ACCEPTED_HEAD.json", "reports/v4_06", "reports/v4_07", "reports/v4_08",
    ))

    checks.update({
        "accepted_head_complete": accepted_head_checks,
        "accepted_head_evidence_bindings_valid": evidence_binding_checks,
        "global_head_binds_v4_05": global_v405_binding,
        "global_head_only_advanced_through_v4_05": global_transition_check(global_head, baseline),
        "historical_adjusted_price_blocker_retained":
            accepted.get("historical_as_recorded_adjusted_price") == HISTORICAL_BLOCK and
            global_head.get("historical_as_recorded_adjusted_price") == HISTORICAL_BLOCK,
        "v4_08_blocker_retained": global_head.get("v4_08_sector_entry") == V408_BLOCK,
        "v4_07_v4_08_not_started_and_no_successor_artifacts":
            global_head.get("v4_07_entry") in ((None, "NOT_STARTED") if phase == "pre-entry" else ("NOT_STARTED",)) and
            no_business_successor_outputs,
    })
    if phase == "pre-entry":
        checks["v4_06_not_authorized_before_promotion_validation"] = "v4_06_entry" not in global_head
    else:
        checks["v4_06_only_authorized_after_promotion_validation"] = (
            global_head.get("v4_06_entry") == "AUTHORIZED_SUPPLEMENTAL_ENRICHMENT" and
            global_head.get("v4_06_status", "NOT_STARTED") == "NOT_STARTED" and no_business_successor_outputs
        )

    overall = all(checks.values())
    return {
        "contract_id": "V4_05_ACCEPTED_HEAD_PROMOTION_VALIDATION_R1",
        "phase": phase,
        "status": "PASS" if overall else "FAIL",
        "external_acceptance_decision": DECISION,
        "reviewed_starting_head": START_HEAD,
        "promotion_validation_head": detail["current_head"],
        "accepted_head": head_binding,
        "global_head": file_identity(GLOBAL_HEAD),
        "candidate_manifest": manifest_identity,
        "accepted_artifacts": actual_artifacts,
        "exact_candidate_ledger_binding": {
            "all_exact_bindings_match": detail["exact_binding"].get("all_exact_bindings_match"),
            "old_r4_binding_count": detail["exact_binding"].get("old_r4_binding_count"),
            "state_logical_digest": detail["postgres"].get("actual_state_head", {}).get("logical_digest"),
        },
        "checks": checks,
        "stage_record": {
            "stage_contract": "V4_05_ACCEPTED_HEAD_PROMOTION_V4_06_ENTRY_TASK_20260929",
            "acceptance_result": "V4_05_ACCEPTED_HEAD_PROMOTION_PASS_R1" if overall else "FAIL",
            "evidence": "Independent byte/hash validation of external acceptance, exact candidate, PostgreSQL G08, R4.1 proofs, LFS restore, accepted/global heads and successor gates.",
            "next_stage": "V4-06 Supplemental Enrichment authorized; implementation not started" if overall else "REPAIR_PROMOTION_BLOCKERS",
        },
    }
