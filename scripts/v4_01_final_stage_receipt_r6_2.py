from __future__ import annotations

"""Seal the R6.2 normalized Required Scope while keeping BSE optional and isolated."""

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
from workbench_analysis.v4_01_required_scope import all_day_required_roster_coverage_passes  # noqa: E402


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load(path: str) -> tuple[dict, dict]:
    p = ROOT / path
    return json.loads(p.read_text(encoding="utf-8")), {"path": path, "sha256": sha256(p)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", default="reports/v4_01/v4_01_final_stage_receipt_R6_2_20260926.json")
    args = ap.parse_args()
    r4, r4_ev = load("reports/v4_01/v4_01_stage_receipt_R4_20260925.json")
    selection, selection_ev = load("reports/v4_01/v4_01_source_selection_receipt_R4_20260925.json")
    roster, roster_ev = load("reports/v4_01/baostock_dated_roster_completeness_receipt_R6_20260926.json")
    scope, scope_ev = load("reports/v4_01/required_scope_gates_receipt_R6_20260926.json")
    universe, universe_ev = load("reports/v4_01/historical_evaluable_universe_receipt_R6_2_20260926.json")
    lineage, lineage_ev = load("reports/v4_01/lineage_policy_receipt_R5_20260925.json")
    tests, tests_ev = load("reports/v4_01/v4_01_test_receipt_R6_2_20260926.json")
    boundary, boundary_ev = load("reports/v4_01/V4_01_LIFECYCLE_BOUNDARY_RESOLUTION_R6_2.json")
    materialization, materialization_ev = load("reports/v4_01/security_lifecycle_materialization_receipt_R6_2_20260926.json")
    provider_contract_path = ROOT / "config/v4_provider_lifecycle_fact_v1.json"
    interval_contract_path = ROOT / "config/v4_security_membership_interval_v1.json"
    universe_contract_path = ROOT / "config/v4_required_historical_universe_r6_2_v1.json"
    all_day = {**boundary.get("all_day_coverage", {}), "status": boundary.get("status")}
    evidence_doc = ROOT / "docs/audits/V4_01_R6_REQUIRED_SCOPE_EXECUTION_20260926.md"
    prior_audit = ROOT / "docs/audits/V4_01_R5_EXECUTION_EVIDENCE_20260925.md"
    code_head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()

    raw_pass = (r4.get("evidence", {}).get("zip_extraction_verification", {}).get("status") == "PASS"
                and r4.get("evidence", {}).get("local_tdx_snapshot", {}).get("status") == "PASS")
    selection_pass = (selection.get("00d_integration", {}).get("status") == "PASS"
                      and "R4 `CANONICAL_SOURCE_SELECTION_V1`" in prior_audit.read_text(encoding="utf-8"))
    board_rows = scope.get("required_scope", {})
    required_boards = ("SH_MAIN", "SZ_MAIN", "CHINEXT", "STAR")
    identity_pass = all(board_rows.get(board, {}).get("identity", {}).get("status") == "PASS"
                        and board_rows[board]["identity"].get("unresolved_identity_rows") == 0
                        for board in required_boards)
    lifecycle_pass = all(board_rows.get(board, {}).get("lifecycle", {}).get("status") == "PASS"
                         and board_rows[board]["lifecycle"].get("missing_fact_rows") == 0
                         and board_rows[board]["lifecycle"].get("source_revision_binding_violations") == 0
                         and board_rows[board]["lifecycle"].get("timestamp_rule_violations") == 0
                         for board in required_boards)
    criteria = {
        "raw_archive_and_local_snapshot": "PASS" if raw_pass else "BLOCKED",
        "canonical_source_selection_and_00d": "PASS" if selection_pass else "BLOCKED",
        "required_scope_exact_dated_rosters": "PASS" if roster.get("status") == "PASS"
            and roster.get("summary", {}).get("session_count") == 786
            and roster.get("summary", {}).get("accepted_suspicious_day_count") == roster.get("summary", {}).get("suspicious_day_count") else "BLOCKED",
        "required_scope_lifecycle_boundary_resolution": "PASS" if boundary.get("status") == "PASS"
            and boundary.get("resolution", {}).get("unresolved_boundary_count") == 0
            and boundary.get("resolution", {}).get("provider_outdate_in_window_count")
                == boundary.get("resolution", {}).get("resolved_by_same_day_presence", 0)
                   + boundary.get("resolution", {}).get("resolved_by_prior_membership", 0) else "BLOCKED",
        "required_scope_all_day_lifecycle_coverage": "PASS" if all_day_required_roster_coverage_passes(all_day, 786) else "BLOCKED",
        "required_scope_append_only_normalized_membership_materialization": "PASS" if materialization.get("status") == "PASS"
            and materialization.get("provider_facts", {}).get("database_revision_rows") == 8981
            and materialization.get("provider_facts", {}).get("raw_provider_value_mismatch_count") == 0
            and materialization.get("provider_facts", {}).get("source_revision_binding_violation_count") == 0
            and materialization.get("provider_facts", {}).get("append_only_trigger_present") is True
            and materialization.get("intervals", {}).get("current_fact_count")
                == materialization.get("intervals", {}).get("current_interval_artifact_row_count")
            and materialization.get("lifecycle_revisions", {}).get("database_normalized_revision_rows") == 129
            and materialization.get("intervals", {}).get("source_revision_binding_violation_count") == 0
            and materialization.get("lifecycle_revisions", {}).get("supersession_binding_violation_count") == 0 else "BLOCKED",
        "required_scope_stable_identity_by_board": "PASS" if identity_pass else "BLOCKED",
        "required_scope_lifecycle_facts_by_board": "PASS" if lifecycle_pass else "BLOCKED",
        "required_scope_historical_universe": "PASS" if universe.get("status") == "PASS"
            and universe.get("required_scope", {}).get("identity_unresolved") == 0 else "BLOCKED",
        "required_scope_source_exception_closure": "PASS" if scope.get("source_exception_gate", {}).get("status") == "PASS"
            and scope.get("source_exception_gate", {}).get("unexplained_required_a_stock_exception_count") == 0 else "BLOCKED",
        "lineage_policy": "PASS" if lineage.get("status") == "PASS" else "BLOCKED",
        "required_scope_normalized_interval_roster_match": "PASS" if universe.get("summary", {}).get("normalized_interval_membership_mismatch_count") == 0 else "BLOCKED",
        "bse_explicitly_isolated_as_optional_degraded": "PASS" if scope.get("optional_scope", {}).get("BSE", {}).get("status") == "DEGRADED_BSE"
            and not scope.get("optional_scope", {}).get("BSE", {}).get("required_scope_blocking", True)
            and universe.get("optional_bse_scope", {}).get("status") == "DEGRADED_BSE" else "BLOCKED",
        "tests_pass_and_bound_to_code_head": "PASS" if tests.get("status") == "PASS"
            and tests.get("tested_head") == code_head else "BLOCKED",
    }
    blockers = [key for key, value in criteria.items() if value != "PASS"]
    bse_degraded = criteria["bse_explicitly_isolated_as_optional_degraded"] == "PASS"
    receipt = {
        "stage": "V4-01", "contract_id": "V4_01_FINAL_REQUIRED_SCOPE_RECEIPT_R6_2", "version": "1.2.0",
        "stage_contract": "DA-MSR-V4.2.2-CODEX-REV2 §78; REQUIRED_EQUITY_SCOPE_V1; SECURITY_MEMBERSHIP_INTERVAL_V1; DATED_ROSTER_MEMBERSHIP_BOUNDARY_V1; R6.2 lifecycle boundary normalization",
        "observed_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "status": ("PASS_WITH_BSE_SCOPE_DEGRADED" if not blockers and bse_degraded else
                   "PASS" if not blockers else "BLOCKED"),
        "required_scope_status": "PASS" if not blockers else "BLOCKED",
        "stage_completion_authorized": not blockers,
        "generic_degraded_pass_allowed": False, "explicit_bse_scope_degradation_allowed": True,
        "criteria": criteria, "blockers": blockers,
        "scope": {"required_boards": list(required_boards), "optional_bse": "DEGRADED_BSE",
                  "required_scope_universe_digest": universe.get("required_scope", {}).get("daily_digest_root"),
                  "required_scope_membership_rows": universe.get("required_scope", {}).get("membership_rows"),
                  "board_statistics": universe.get("required_scope", {}).get("boards"),
                  "bse_optional_row_count": universe.get("optional_bse_scope", {}).get("candidate_and_roster_membership_rows"),
                  "pending_classification_row_count": universe.get("pending_classification", {}).get("row_count")},
        "evidence": {"R4_stage": r4_ev, "R4_source_selection": selection_ev, "R6_roster_completeness": roster_ev,
                     "R6_scope_gates": scope_ev, "R6_required_universe": universe_ev,
                     "R5_lineage_policy": lineage_ev, "R6_1_tests": tests_ev,
                     "R6_2_lifecycle_boundary_resolution": boundary_ev,
                     "R6_2_append_only_lifecycle_materialization": materialization_ev,
                     "R6_2_provider_lifecycle_fact_contract": {"path": "config/v4_provider_lifecycle_fact_v1.json", "sha256": sha256(provider_contract_path)},
                     "R6_2_membership_interval_contract": {"path": "config/v4_security_membership_interval_v1.json", "sha256": sha256(interval_contract_path)},
                     "R6_2_historical_universe_contract": {"path": "config/v4_required_historical_universe_r6_2_v1.json", "sha256": sha256(universe_contract_path)},
                     "R6_execution_record": {"path": str(evidence_doc.relative_to(ROOT)), "sha256": sha256(evidence_doc)},
                     "R5_audit_confirmation": {"path": str(prior_audit.relative_to(ROOT)), "sha256": sha256(prior_audit)}},
        "external_online_model_acceptance": "PENDING_SEPARATE_REVIEW",
        "v4_02_status": "BLOCKED_PENDING_EXTERNAL_ACCEPTANCE" if not blockers else "BLOCKED_NOT_STARTED",
        "v4_03_status": "BLOCKED",
        "execution_identity": {"validated_code_head": code_head,
                               "working_tree_clean_for_code": subprocess.run(
                                   ["git", "diff", "--quiet", "HEAD", "--", "src", "scripts", "config", "tests"],
                                   cwd=ROOT).returncode == 0},
        "next_stage": "V4_01_EXTERNAL_ONLINE_MODEL_ACCEPTANCE" if not blockers else "V4_01_REMEDIATE_R6_2_BLOCKERS",
    }
    _atomic_json(ROOT / args.output, receipt)
    print(json.dumps({"status": receipt["status"], "required_scope_status": receipt["required_scope_status"],
                      "criteria": criteria, "blockers": blockers, "receipt": args.output}, ensure_ascii=False))
    return 0 if not blockers else 2


if __name__ == "__main__":
    raise SystemExit(main())
