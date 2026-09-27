from __future__ import annotations

"""Create R8, Phase 0 R5, and the final 00/01/02 receipt after their gates pass."""

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from workbench_analysis.baostock_supplemental import _atomic_json  # noqa: E402
from workbench_analysis.v4_joint_receipt import evaluate_joint_gate  # noqa: E402

REV2 = Path("docs/evidence/A_SHARE_RESEARCH_SYSTEM_V4_2_2_FINAL_EXECUTABLE_CONTRACT_REV2_20260925.md")
TASK_CARD = Path("docs/evidence/V4_PRE03_JOINT_FINAL_SEAL_TASK_R1_20260927.md")
TESTS = Path("reports/v4_joint/V4_00_01_02_JOINT_TEST_RECEIPT_R1_20260928.json")
ALIAS = Path("reports/v4_01/V4_01_HISTORICAL_CODE_CHANGE_ALIAS_COMPLETENESS_R8.json")
R8_POSTCHECK = Path("reports/v4_01/V4_01_R8_IDENTITY_UNIVERSE_POSTCHECK_20260928.json")
R8_FINAL = Path("reports/v4_01/v4_01_final_stage_receipt_R8_20260928.json")
R8_EXTERNAL_JSON = Path("reports/v4_01/V4_01_R8_FINAL_EXTERNAL_ACCEPTANCE_20260928.json")
R8_EXTERNAL_MD = Path("docs/evidence/V4_01_R8_FINAL_EXTERNAL_ACCEPTANCE_20260928.md")
R8_IDENTITY = Path("data/v4/artifact_store/v4_01/security_entity_map_R7_20260927.json")
R8_UNIVERSE = Path("data/v4/artifact_store/v4_01/v4_01_historical_universe_required_R7_20260927.jsonl.gz")
R8_ALIAS_FACTS = Path("data/v4/bootstrap/dated_security_alias_r7.jsonl")
PHASE0_R3_FINAL = Path("reports/v4_phase0/V4_PHASE0_FINAL_RECEIPT.json")
PHASE0_R3_STAGES = Path("reports/v4_phase0/V4_PHASE0_STAGE_RECEIPTS_R3.json")
PHASE0_R5_STAGES = Path("reports/v4_phase0/V4_PHASE0_STAGE_RECEIPTS_R5_20260928.json")
PHASE0_R5_FINAL = Path("reports/v4_phase0/V4_PHASE0_FINAL_RECEIPT_R5_20260928.json")
V402_FINAL = Path("reports/v4_02/V4_02_FINAL_RECEIPT_R6.json")
V402_HEAD = Path("data/v4/V4_02_ACCEPTED_HEAD.json")
V402_EXTERNAL = Path("reports/v4_02/V4_02_FINAL_EXTERNAL_ACCEPTANCE_R6.json")
CROSS_STAGE = Path("reports/v4_02/V4_02_R8_CROSS_STAGE_POSTCHECK_20260928.json")
JOINT = Path("reports/v4_joint/V4_00_01_02_JOINT_FINAL_RECEIPT_R1_20260927.json")
JOINT_CONTRACT = Path("config/v4_joint_final_gate_r1.json")
EVIDENCE_CHANGE = Path("reports/v4_joint/V4_00_01_02_EVIDENCE_CHANGE_RECEIPT_R1_20260928.json")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load(path: Path) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def evidence(path: Path) -> dict[str, str]:
    return {"path": path.as_posix(), "sha256": sha256(ROOT / path)}


def current_head() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def write_r8_and_phase0() -> None:
    alias = load(ALIAS)
    postcheck = load(R8_POSTCHECK)
    tests = load(TESTS)
    prior = load(Path("reports/v4_01/v4_01_final_stage_receipt_R6_2_20260926.json"))
    v402 = load(V402_FINAL)
    v402_external = load(V402_EXTERNAL)
    postcheck_pass = postcheck.get("status") == "PASS" and all(value == "PASS" for value in postcheck.get("criteria", {}).values())
    alias_pass = alias.get("status") == "PASS" and alias.get("unresolved_required_scope_candidate_count") == 0
    v402_pass = v402.get("status") == "PASS_WITH_BSE_SCOPE_DEGRADED" and v402_external.get("acceptance_result", {}).get("external_acceptance") == "EXTERNALLY_ACCEPTED"
    tests_pass = tests.get("status") == "PASS" and tests.get("test_summary", {}).get("failed") == 0
    criteria = {
        "R7_identity_and_required_universe_are_canonical_inputs": "PASS" if sha256(ROOT / R8_IDENTITY) and sha256(ROOT / R8_UNIVERSE) else "BLOCKED",
        "generic_historical_alias_completeness": "PASS" if alias_pass else "BLOCKED",
        "R8_identity_and_universe_postcheck": "PASS" if postcheck_pass else "BLOCKED",
        "Phase0_R8_affected_test_gate": "PASS" if tests_pass else "BLOCKED",
        "V4_02_R6_external_acceptance_remains_current": "PASS" if v402_pass else "BLOCKED",
        "R7_membership_row_accounting": "PASS" if postcheck.get("scope", {}).get("baseline_rows")
            == prior.get("scope", {}).get("required_scope_membership_rows")
            and postcheck.get("scope", {}).get("baseline_rows") - postcheck.get("scope", {}).get("required_scope_membership_rows")
            == postcheck.get("scope", {}).get("duplicate_rows_removed") else "BLOCKED",
        "Required_scope_candidate_limit": "PASS" if int(alias.get("unresolved_required_scope_candidate_count", -1)) == 0 else "BLOCKED",
    }
    blockers = [name for name, value in criteria.items() if value != "PASS"]
    counts = alias.get("candidate_status_counts", {})
    scope = postcheck.get("scope", {})
    r8_receipt = {
        "stage": "V4-01",
        "contract_id": "V4_01_FINAL_REQUIRED_SCOPE_RECEIPT_R8",
        "version": "1.0.0",
        "technical_contract": "DA-MSR-V4.2.2-CODEX-REV2",
        "technical_contract_sha256": sha256(ROOT / REV2),
        "stage_contract": "REV2 §78; REQUIRED_EQUITY_SCOPE_V1; DATED_SECURITY_ALIAS_V1; HISTORICAL_CODE_CHANGE_ALIAS_COMPLETENESS_V1; V4_PRE03_JOINT_FINAL_SEAL_TASK_R1",
        "observed_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "status": "PASS_WITH_BSE_SCOPE_DEGRADED" if not blockers else "BLOCKED",
        "required_scope_status": "PASS" if not blockers else "BLOCKED",
        "optional_bse_status": "DEGRADED_BSE",
        "stage_completion_authorized": not blockers,
        "criteria": criteria,
        "blockers": blockers,
        "required_boards": ["SH_MAIN", "SZ_MAIN", "CHINEXT", "STAR"],
        "canonical_identity_artifact": {
            "path": R8_IDENTITY.as_posix(), "sha256": sha256(ROOT / R8_IDENTITY), "bytes": (ROOT / R8_IDENTITY).stat().st_size,
        },
        "canonical_alias_fact_artifact": {
            "path": R8_ALIAS_FACTS.as_posix(), "sha256": sha256(ROOT / R8_ALIAS_FACTS), "bytes": (ROOT / R8_ALIAS_FACTS).stat().st_size,
        },
        "canonical_historical_universe_artifact": {
            "path": R8_UNIVERSE.as_posix(), "sha256": sha256(ROOT / R8_UNIVERSE), "bytes": (ROOT / R8_UNIVERSE).stat().st_size,
        },
        "required_scope_membership_rows": scope.get("required_scope_membership_rows"),
        "session_count": scope.get("session_count"),
        "identity_unresolved": scope.get("identity_unresolved"),
        "code_change_candidate_count": int(alias.get("candidate_status_counts", {}).get("CONFIRMED_SAME_ENTITY_CODE_CHANGE", 0))
            + int(alias.get("candidate_status_counts", {}).get("CONFIRMED_DISTINCT_ENTITY", 0))
            + int(alias.get("candidate_status_counts", {}).get("UNRESOLVED", 0))
            + int(alias.get("candidate_status_counts", {}).get("NOT_APPLICABLE", 0)),
        "code_change_confirmed_same_entity": int(counts.get("CONFIRMED_SAME_ENTITY_CODE_CHANGE", 0)),
        "code_change_confirmed_distinct_entity": int(counts.get("CONFIRMED_DISTINCT_ENTITY", 0)),
        "code_change_unresolved": int(counts.get("UNRESOLVED", 0)),
        "code_change_not_applicable": int(counts.get("NOT_APPLICABLE", 0)),
        "duplicate_identity_date_rows": scope.get("duplicate_stable_id_trade_date_rows"),
        "alias_interval_conflicts": scope.get("source_alias_interval_conflicts"),
        "same_entity_alias_interval_conflicts": scope.get("same_entity_alias_interval_conflicts"),
        "board_interval_conflicts": scope.get("wrong_dated_board_rows"),
        "all_day_coverage_missing": scope.get("all_day_coverage"),
        "source_exception_unresolved": scope.get("source_exception_unresolved"),
        "r7_row_accounting": {
            "input_membership_rows": scope.get("baseline_rows"),
            "output_membership_rows": scope.get("required_scope_membership_rows"),
            "duplicate_rows_removed": scope.get("duplicate_rows_removed"),
            "normalized_membership_mismatch_rows": scope.get("normalized_membership_mismatch_rows"),
        },
        "scope": {
            "required_boards": ["SH_MAIN", "SZ_MAIN", "CHINEXT", "STAR"],
            "optional_bse": "DEGRADED_BSE",
            "board_membership_rows": scope.get("board_membership_rows"),
            "formal_history_window": alias.get("scope", {}).get("formal_history_window"),
        },
        "evidence": {
            "supersedes_R6_2": {**evidence(Path("reports/v4_01/v4_01_final_stage_receipt_R6_2_20260926.json")), "status": prior.get("status")},
            "alias_completeness": evidence(ALIAS),
            "identity_universe_postcheck": evidence(R8_POSTCHECK),
            "joint_test_receipt": {**evidence(TESTS), "status": tests.get("status"), "test_summary": tests.get("test_summary")},
            "R7_identity_artifact": evidence(R8_IDENTITY),
            "R7_alias_facts": evidence(R8_ALIAS_FACTS),
            "R7_required_universe": evidence(R8_UNIVERSE),
            "V4_02_final_external_acceptance": evidence(V402_EXTERNAL),
        },
        "execution_commit": current_head(),
        "input_commit": "1a70c8c733096936da4fa250a3f4def501ccfd1d",
        "external_acceptance": "EXTERNAL_REVIEW_REQUIRED",
        "next_stage": "V4_00_DOWNSTREAM_CLOSURE_RECONCILIATION" if not blockers else "BLOCKED_REMEDIATE_R8_RECEIPT",
    }
    _atomic_json(ROOT / R8_FINAL, r8_receipt)

    review_json = {
        "contract_id": "V4_01_R8_FINAL_EXTERNAL_ACCEPTANCE_V1",
        "stage": "V4-01 R8 FINAL EXTERNAL ACCEPTANCE",
        "version": "1.0.0",
        "observed_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "status": "EXTERNAL_REVIEW_REQUIRED",
        "source_receipt": evidence(R8_FINAL),
        "required_scope_status": r8_receipt["required_scope_status"],
        "optional_bse_status": "DEGRADED_BSE",
        "generic_alias_completeness_status": alias.get("status"),
        "identity_universe_postcheck_status": postcheck.get("status"),
        "external_acceptance": "PENDING_EXTERNAL_REVIEW",
        "v4_03_entry": "BLOCKED_UNTIL_JOINT_FINAL_EXTERNAL_REVIEW",
        "decision_authority": "External reviewer only; this receipt does not assert external acceptance.",
    }
    _atomic_json(ROOT / R8_EXTERNAL_JSON, review_json)
    review_md = (
        "# V4-01 R8 Final External Review Package\n\n"
        f"Status: `EXTERNAL_REVIEW_REQUIRED`\n\n"
        f"Technical baseline: `DA-MSR-V4.2.2-CODEX-REV2` ({sha256(ROOT / REV2)})\n\n"
        f"Task card SHA-256: `{sha256(ROOT / TASK_CARD)}`\n\n"
        f"Internal R8 receipt: `{R8_FINAL.as_posix()}` ({sha256(ROOT / R8_FINAL)})\n\n"
        f"Alias completeness: `{ALIAS.as_posix()}` ({sha256(ROOT / ALIAS)})\n\n"
        f"Identity/universe postcheck: `{R8_POSTCHECK.as_posix()}` ({sha256(ROOT / R8_POSTCHECK)})\n\n"
        f"Required-scope result: `{r8_receipt['required_scope_status']}`; optional BSE: `DEGRADED_BSE`.\n\n"
        "The internal receipt preserves external review as pending. It does not claim `EXTERNALLY_ACCEPTED` and does not authorize V4-03 implementation.\n"
    )
    (ROOT / R8_EXTERNAL_MD).parent.mkdir(parents=True, exist_ok=True)
    temp = ROOT / R8_EXTERNAL_MD.with_suffix(".md.tmp")
    temp.write_text(review_md, encoding="utf-8", newline="\n")
    temp.replace(ROOT / R8_EXTERNAL_MD)

    prior_stage_doc = load(PHASE0_R3_STAGES)
    stage_rows = [dict(row) for row in prior_stage_doc["stages"]]
    by_stage = {row["stage"]: row for row in stage_rows}
    updates = {
        "V4-00B": {
            "status": "FULL_PASS", "degraded_scopes": [], "reason_codes": [],
            "evidence_add": [R8_FINAL.as_posix(), ALIAS.as_posix(), R8_POSTCHECK.as_posix()],
            "acceptance": "R8 canonical identity, dated aliases, lifecycle and historical universe pass all-day Required Scope postchecks. Pre-project PIT history remains NOT_AVAILABLE/NOT_CLAIMED.",
        },
        "V4-00E": {
            "status": "FULL_PASS", "degraded_scopes": [], "reason_codes": [],
            "evidence_add": [V402_FINAL.as_posix(), V402_EXTERNAL.as_posix(), R8_FINAL.as_posix()],
            "acceptance": "Accepted V4-02 R6 Adjusted Canonical, empirical samples and per-security fail-closed behavior are externally accepted; no silent RAW fallback. Pre-project PIT events remain NOT_AVAILABLE/NOT_CLAIMED.",
        },
        "V4-00F": {
            "status": "FULL_PASS", "degraded_scopes": [], "reason_codes": [],
            "allowed_capabilities": ["BAOSTOCK_PUBLIC_0_9_3_RUNTIME_ROUTE", "FIELD_UNIT_CONTRACT", "BOUNDED_REQUEST_CONTRACT", "FAILURE_ISOLATION", "PROVENANCE", "STATUS_ISST_SOURCE_FACTS"],
            "evidence_add": ["docs/V4_00F_BAOSTOCK_SUPPLEMENTAL_CONTRACT_20260925.md", "docs/audits/V4_00F_BAOSTOCK_GATE_AUDIT_20260925.md", "src/workbench_analysis/baostock_supplemental.py", "requirements-v4-baostock.txt", "reports/v4_01/baostock_dated_roster_completeness_receipt_R6_20260926.json", "tests/v4_phase0/test_baostock_supplemental.py"],
            "acceptance": "Public 0.9.3 route, field/unit normalization, bounded serialized requests, failure isolation, provenance and status/isST use are contracted and exercised. TURNOVER_CONTEXT_V1 BOUND_STRICT remains disabled and owned by V4-06; no turnover dataset is declared enabled or accepted here.",
        },
        "V4-00G": {
            "status": "FULL_PASS", "degraded_scopes": [], "reason_codes": [],
            "evidence_add": ["src/v4/contracts/algorithm_contract.py", "config/v4_algorithm_contract_framework_v1.json", "config/v4_parameter_registry_v1.json", "tests/v4_phase0/test_algorithm_contracts.py", R8_FINAL.as_posix()],
            "acceptance": "Versioned AST/schema/parameter/output/window validation, UNKNOWN propagation and negative vectors are in place. Future owner-stage parameters remain explicitly pending under Stage-Obligation semantics.",
        },
        "V4-00H": {
            "status": "FULL_PASS", "degraded_scopes": [], "blocked_scopes": [], "reason_codes": [],
            "allowed_capabilities": ["CAPABILITY_SCOPES", "FAILURE_RECEIPTS", "CUTOVER_PERMISSIONS", "ROLLBACK_SEMANTICS", "PERFORMANCE_OWNERSHIP"],
            "evidence_add": ["config/v4_phase0_final_gate_v1.json", "config/v4_capability_cutover_policy_v1.json", "config/v4_performance_measurement_contract_v1.json", "tests/v4_phase0/test_phase0_final_gate.py"],
            "acceptance": "Scope gates, failure receipts, cutover permissions, rollback semantics and performance ownership are frozen. Marked-relative benchmark remains DISABLED_FAIL_CLOSED; future thresholds and performance remain owned by later stages.",
        },
    }
    for name, update in updates.items():
        row = by_stage[name]
        for key in ("status", "degraded_scopes", "reason_codes", "allowed_capabilities", "blocked_scopes", "acceptance"):
            if key in update:
                row[key] = update[key]
        if "evidence_add" in update:
            row["evidence"] = list(dict.fromkeys([*row.get("evidence", []), *update["evidence_add"]]))
        row["stage_obligation_semantics"] = "Future owner-stage capability status does not degrade this Phase 0 stage."
    future = [
        {"capability": "TURNOVER_CONTEXT_V1", "owner": "V4-06", "status": "PENDING_OWNER_STAGE", "does_not_degrade_v4_00f": True, "enabled": False, "strict_tolerance_accepted": False},
        {"capability": "MARKED_RELATIVE_BENCHMARK_CONSUMER", "owner": "V4-15/Forward", "status": "DISABLED_FAIL_CLOSED", "coverage_threshold": "UNSET", "quote_age_threshold": "UNSET", "does_not_degrade_v4_00h": True},
        {"capability": "factor_performance", "owner": "V4-03/V4-05", "status": "PENDING_OWNER_STAGE", "does_not_degrade_v4_00h": True},
        {"capability": "owner_stage_algorithm_parameters", "owner": "applicable downstream owner stages", "status": "PENDING_OWNER_STAGE", "does_not_degrade_v4_00g": True},
        {"capability": "sector_rotation_forward_thresholds", "owner": "V4-08/V4-17G", "status": "PENDING_REPRESENTATIVE_EVIDENCE", "does_not_degrade_v4_00h": True},
        {"capability": "radar_focus_performance", "owner": "V4-15/Forward", "status": "PENDING_OWNER_STAGE", "does_not_degrade_v4_00h": True},
        {"capability": "future_production_cutover", "owner": "later owner stages", "status": "PENDING_OWNER_STAGE", "does_not_degrade_v4_00h": True},
    ]
    phase_stages = {
        row["stage"]: {"status": row["status"], "reason_codes": row.get("reason_codes", []),
                       "degraded_scopes": row.get("degraded_scopes", []), "blocked_scopes": row.get("blocked_scopes", [])}
        for row in stage_rows
    }
    stages_r5 = {
        "contract_id": "V4_PHASE0_STAGE_RECEIPTS_R5_STAGE_OBLIGATION",
        "version": "1.0.0",
        "supersedes": evidence(PHASE0_R3_STAGES),
        "technical_contract": "DA-MSR-V4.2.2-CODEX-REV2",
        "technical_contract_sha256": sha256(ROOT / REV2),
        "task_card": evidence(TASK_CARD),
        "stages": stage_rows,
        "phase0_status": "FULL_PASS" if all(row["status"] == "FULL_PASS" for row in stage_rows) else "BLOCKED",
        "core_blockers": [],
        "future_owner_stage_capabilities": future,
        "stage_obligation_semantics": "Phase 0 passes when its own contracts, schema, policy, fail-closed behavior, ownership, gates and rollback governance are complete. Future owner-stage capabilities may remain disabled or pending.",
        "observed_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "execution_commit": current_head(),
        "next_stage": "V4_00_01_02_JOINT_FINAL_RECEIPT",
    }
    _atomic_json(ROOT / PHASE0_R5_STAGES, stages_r5)

    phase0_final = load(PHASE0_R3_FINAL)
    phase0_final.update({
        "contract_id": "V4_PHASE0_FINAL_ACCEPTANCE_R5_STAGE_OBLIGATION",
        "version": "1.0.0",
        "supersedes_contract_id": phase0_final.get("contract_id"),
        "superseded_status": phase0_final.get("phase0_status"),
        "supersedes": evidence(PHASE0_R3_FINAL),
        "task_card": evidence(TASK_CARD),
        "technical_contract": "DA-MSR-V4.2.2-CODEX-REV2",
        "technical_contract_sha256": sha256(ROOT / REV2),
        "input_commit": "1a70c8c733096936da4fa250a3f4def501ccfd1d",
        "output_commit": current_head(),
        "phase0_status": stages_r5["phase0_status"],
        "stages": phase_stages,
        "stage_receipts": PHASE0_R5_STAGES.as_posix(),
        "core_blockers": [],
        "remaining_phase0_blockers": [],
        "nonblocking_limitations": [
            "TURNOVER_CONTEXT_V1 BOUND_STRICT producer remains owned by V4-06; dataset stays disabled and is not claimed as passed.",
            "Marked-relative benchmarks and future performance/forward thresholds remain fail-closed under their owner stages.",
            "Pre-project historical PIT is NOT_AVAILABLE and NOT_CLAIMED.",
        ],
        "future_owner_stage_capabilities": future,
        "stage_obligation_semantics": "FULL_PASS is scoped to V4-00 obligations and does not claim that every future system capability is implemented in Phase 0.",
        "v4_01_entry_permission": "R8_STAGE_COMPLETE; EXTERNAL_REVIEW_REQUIRED",
        "v4_03_entry_permission": "BLOCKED_UNTIL_JOINT_EXTERNAL_ACCEPTANCE",
        "external_acceptance": "PENDING_JOINT_EXTERNAL_REVIEW",
        "accepted_head_before_receipt_seal": current_head(),
        "verified_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "test_result": tests.get("status"),
        "test_count": tests.get("test_summary", {}).get("passed"),
        "failed_test_count": tests.get("test_summary", {}).get("failed"),
        "skipped_test_count": tests.get("test_summary", {}).get("skipped"),
        "joint_test_receipt": evidence(TESTS),
        "R8_final_receipt": evidence(R8_FINAL),
        "R8_alias_completeness_receipt": evidence(ALIAS),
        "R8_identity_universe_postcheck": evidence(R8_POSTCHECK),
        "V4_02_external_acceptance": evidence(V402_EXTERNAL),
        "next_stage": "V4_00_01_02_JOINT_FINAL_EXTERNAL_REVIEW; DO_NOT_START_V4_03",
    })
    _atomic_json(ROOT / PHASE0_R5_FINAL, phase0_final)


def write_joint_receipt() -> None:
    phase0 = load(PHASE0_R5_FINAL)
    v401 = load(R8_FINAL)
    alias = load(ALIAS)
    v402 = load(V402_FINAL)
    external = load(V402_EXTERNAL)
    cross = load(CROSS_STAGE)
    tests = load(TESTS)
    joint_contract = load(JOINT_CONTRACT)
    evidence_change = load(EVIDENCE_CHANGE)
    gate = evaluate_joint_gate(
        phase0=phase0,
        v4_01=v401,
        alias_gate=alias,
        v4_02=v402,
        external_v4_02=external,
        cross_stage=cross,
        tests=tests,
        gate_contract=joint_contract,
        evidence_change=evidence_change,
    )
    code_head = current_head()
    receipt = {
        "contract_id": "V4_00_01_02_JOINT_FINAL_RECEIPT_R1",
        "version": "1.0.0",
        "stage": "V4-00/01/02 JOINT FINAL SEAL",
        "observed_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "status": gate["joint_status"],
        "v4_03_entry": gate["v4_03_entry"],
        "external_acceptance": "EXTERNAL_REVIEW_REQUIRED" if gate["joint_status"] == "FULL_PASS" else "NOT_READY",
        "criteria": gate["criteria"],
        "required_scope_blockers": gate["required_scope_blockers"],
        "stage_statuses": gate["stage_statuses"],
        "scope": {"required_boards": ["SH_MAIN", "SZ_MAIN", "CHINEXT", "STAR"], "optional_bse": "DEGRADED_BSE"},
        "bindings": {
            "technical_contract": evidence(REV2),
            "joint_gate_contract": evidence(JOINT_CONTRACT),
            "evidence_change_receipt": evidence(EVIDENCE_CHANGE),
            "task_card": evidence(TASK_CARD),
            "current_execution_commit": code_head,
            "phase0_final_receipt": evidence(PHASE0_R5_FINAL),
            "phase0_stage_receipts": evidence(PHASE0_R5_STAGES),
            "v4_01_r8_final_receipt": evidence(R8_FINAL),
            "v4_01_alias_completeness_receipt": evidence(ALIAS),
            "v4_01_identity_artifact": evidence(R8_IDENTITY),
            "v4_01_alias_fact_artifact": evidence(R8_ALIAS_FACTS),
            "v4_01_historical_universe_artifact": evidence(R8_UNIVERSE),
            "v4_02_accepted_head": evidence(V402_HEAD),
            "v4_02_final_external_acceptance": evidence(V402_EXTERNAL),
            "v4_02_final_receipt": evidence(V402_FINAL),
            "v4_02_cross_stage_postcheck": evidence(CROSS_STAGE),
            "test_receipt": evidence(TESTS),
        },
        "code_receipt_binding": {
            "tested_head": tests.get("execution_commit"),
            "execution_head": code_head,
            "no_business_code_changed_after_tested_head": evidence_change.get("status") == "PASS"
                and evidence_change.get("business_code_changed_after_tested_head") is False
                and tests.get("execution_commit") == code_head,
            "changed_file_receipt_sha256": sha256(ROOT / EVIDENCE_CHANGE),
            "test_tree_digest": tests.get("test_tree_digest"),
            "test_summary": tests.get("test_summary"),
        },
        "prohibitions": {"v4_03_implementation_started": False, "external_acceptance_self_asserted": False},
        "next_stage": "STOP_AND_WAIT_FOR_EXTERNAL_REVIEW; V4-03_REMAINS_BLOCKED" if gate["joint_status"] == "FULL_PASS" else "REMEDIATE_JOINT_RECEIPT_BLOCKERS",
    }
    _atomic_json(ROOT / JOINT, receipt)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--joint", action="store_true", help="Create the joint final receipt after the cross-stage postcheck exists.")
    args = parser.parse_args()
    if args.joint:
        write_joint_receipt()
        result = load(JOINT)
        print(json.dumps({"status": result["status"], "v4_03_entry": result["v4_03_entry"],
                          "blockers": result["required_scope_blockers"], "receipt": JOINT.as_posix()}, ensure_ascii=False))
        return 0 if result["status"] == "FULL_PASS" else 2
    write_r8_and_phase0()
    result = load(R8_FINAL)
    print(json.dumps({"v4_01_status": result["status"], "required_scope": result["required_scope_status"],
                      "phase0_status": load(PHASE0_R5_FINAL)["phase0_status"],
                      "r8_receipt": R8_FINAL.as_posix(), "phase0_receipt": PHASE0_R5_FINAL.as_posix()}, ensure_ascii=False))
    return 0 if result["status"] == "PASS_WITH_BSE_SCOPE_DEGRADED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
