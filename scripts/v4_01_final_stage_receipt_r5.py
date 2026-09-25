from __future__ import annotations

"""Seal the V4-01 R5 gate from machine receipts and the frozen R5 audit."""

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


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load(rel: str) -> tuple[dict, dict]:
    path = ROOT / rel
    doc = json.loads(path.read_text("utf-8"))
    return doc, {"path": rel, "sha256": sha256(path)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="reports/v4_01/v4_01_final_stage_receipt_R5_20260925.json")
    args = parser.parse_args()
    r4, r4_evidence = load("reports/v4_01/v4_01_stage_receipt_R4_20260925.json")
    selection, selection_evidence = load("reports/v4_01/v4_01_source_selection_receipt_R4_20260925.json")
    roster, roster_evidence = load("reports/v4_01/baostock_dated_roster_receipt_R5_20260925.json")
    identity, identity_evidence = load("reports/v4_01/security_entity_map_receipt_R5_20260925.json")
    bse, bse_evidence = load("reports/v4_01/bse_source_closure_receipt_R5_20260925.json")
    lifecycle, lifecycle_evidence = load("reports/v4_01/security_lifecycle_materialization_receipt_R5_20260925.json")
    universe, universe_evidence = load("reports/v4_01/historical_evaluable_universe_receipt_R5_20260925.json")
    exceptions, exceptions_evidence = load("reports/v4_01/source_exception_classification_R5_20260925.json")
    lineage, lineage_evidence = load("reports/v4_01/lineage_policy_receipt_R5_20260925.json")
    tests, tests_evidence = load("reports/v4_01/v4_01_test_receipt_R5_20260925.json")
    audit_path = ROOT / "D:\\Users\\lps\\Desktop\\V4_01_R4_EXTERNAL_AUDIT_AND_R5_FINALIZATION_20260925.md"
    audit = audit_path if audit_path.exists() else ROOT / "docs/audits/V4_01_R5_EXECUTION_EVIDENCE_20260925.md"
    audit_accepts_selection = "Source Selection：本轮认可通过" in audit.read_text("utf-8")
    code_head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()

    criteria = {
        "raw_archive_and_snapshot_integrity": "PASS" if (
            r4.get("evidence", {}).get("zip_extraction_verification", {}).get("status") == "PASS"
            and r4.get("evidence", {}).get("local_tdx_snapshot", {}).get("status") == "PASS") else "BLOCKED",
        "source_priority_and_00d_overlap": "PASS" if (
            selection.get("00d_integration", {}).get("status") == "PASS" and audit_accepts_selection) else "BLOCKED",
        "stable_security_identity": "PASS" if identity.get("status") == "PASS" else "BLOCKED",
        "exact_dated_rosters": "PASS" if roster.get("status") == "BUILT" and roster.get("input", {}).get("session_count") == 786 else "BLOCKED",
        "official_bse_lifecycle_and_aliases": "PASS" if bse.get("status") == "PASS" else "BLOCKED",
        "formal_revisionable_lifecycle_facts": "PASS" if lifecycle.get("status") == "PASS" else "BLOCKED",
        "historical_universe": "PASS" if universe.get("status") == "PASS" else "BLOCKED",
        "source_exception_closure": "PASS" if exceptions.get("status") == "PASS" else "BLOCKED",
        "lineage_policy": "PASS" if lineage.get("status") == "PASS" else "BLOCKED",
        "final_test_receipt_bound_to_code_head": "PASS" if (
            tests.get("status") == "PASS" and tests.get("tested_head") == code_head) else "BLOCKED",
    }
    blockers = [key for key, value in criteria.items() if value != "PASS"]
    v4_02_ownership = ["adjusted_canonical", "formal_calendar", "formal_trading_status", "weekly_monthly_periods",
                       "as_of", "temporal_leakage", "price_limit"]
    evidence = {"R4_stage_receipt": r4_evidence, "R4_source_selection_receipt": selection_evidence,
                "R5_roster_receipt": roster_evidence, "R5_identity_map_receipt": identity_evidence,
                "R5_BSE_closure_receipt": bse_evidence, "R5_lifecycle_materialization_receipt": lifecycle_evidence,
                "R5_historical_universe_receipt": universe_evidence, "R5_exception_receipt": exceptions_evidence,
                "R5_lineage_receipt": lineage_evidence, "R5_test_receipt": tests_evidence,
                "R5_audit_source": {"path": str(audit), "sha256": sha256(audit_path) if audit_path.exists() else sha256(audit)}}
    stage_code_diff = subprocess.run(["git", "diff", "--quiet", "HEAD", "--"], cwd=ROOT).returncode
    receipt = {"stage": "V4-01", "stage_contract": "DA-MSR-V4.2.2-CODEX-REV2 §§3B.1-3B.6, §7.10, §78; R5 finalization contract",
               "contract_id": "V4_01_FINAL_STAGE_RECEIPT_R5", "version": "1.0.0",
               "observed_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
               "status": "PASS" if not blockers else "BLOCKED", "stage_completion_authorized": not blockers,
               "degraded_pass_allowed": False, "criteria": criteria, "blockers": blockers,
               "v4_02_owned_scopes_excluded_from_v4_01_gate": v4_02_ownership,
               "v4_02_status": "BLOCKED_NOT_STARTED", "v4_03_status": "BLOCKED",
               "external_online_model_acceptance": "PENDING_SEPARATE_REVIEW",
               "evidence": evidence,
               "execution_identity": {"validated_code_head": code_head,
                                      "working_tree_clean_for_stage_code": stage_code_diff == 0},
               "next_stage": "V4_01_REMEDIATE_EXPLICIT_BLOCKERS" if blockers else "V4_02_START_AFTER_EXTERNAL_ACCEPTANCE"}
    _atomic_json(ROOT / args.output, receipt)
    print(json.dumps({"status": receipt["status"], "blockers": blockers, "receipt": args.output}, ensure_ascii=False))
    return 0 if not blockers else 2


if __name__ == "__main__":
    raise SystemExit(main())
