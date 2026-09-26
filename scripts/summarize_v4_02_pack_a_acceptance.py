from __future__ import annotations

"""Assemble the Pack A acceptance receipt from hash-bound component evidence."""

import hashlib
import json
import os
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / "reports/v4_02"
ARTIFACT_DIR = ROOT / "data/v4/artifact_store/v4_02"
OUTPUT = REPORT_DIR / "V4_02_DATA_PERIOD_MAINLINE_ACCEPTANCE_R1.json"

FILES = {
    "raw": REPORT_DIR / "V4_02_RAW_CANONICAL_FORMAL_ACCEPTANCE_V1.json",
    "calendar": REPORT_DIR / "V4_02_FORMAL_MARKET_CALENDAR_ACCEPTANCE_V2.json",
    "status": REPORT_DIR / "V4_02_DATED_TRADING_STATUS_R6_2_20260926.json",
    "classification": REPORT_DIR / "V4_02_GBBQ_PRICE_IMPACT_CLASSIFICATION_V1.json",
    "adjustment_samples": REPORT_DIR / "V4_02_ADJUSTMENT_REAL_SAMPLES_ACCEPTANCE_20260926.json",
    "periods": REPORT_DIR / "V4_02_FORMAL_PERIODS_R6_2_20260926.json",
    "postcheck": REPORT_DIR / "V4_02_FORMAL_PERIODS_INDEPENDENT_POSTCHECK_20260926.json",
    "temporal": REPORT_DIR / "V4_02_SECTION_3C4_TEMPORAL_LEAKAGE_REPLAY_20260926.json",
    "conflict_audit": ROOT / "docs/audits/V4_02_BAOSTOCK_TDX_STATUS_CONFLICT_AUDIT_20260926.md",
}
MASTER_DOC = Path(r"D:\Users\lps\Desktop\V4_02_ACCELERATED_CLOSURE_MASTER_TASK_R1_20260926.md")
UPGRADE_DOC = Path(r"D:\Users\lps\Desktop\A_SHARE_RESEARCH_SYSTEM_V4_2_2_FINAL_EXECUTABLE_CONTRACT_20260925_codex修改版.md")
UPGRADE_SHA = "744b75906d932d6b11e01a1cd90f6a8de082cc23b673e876e219642620dd30fd"
SOURCE_CUTOFF = "2026-09-24"


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def atomic_json(path: Path, doc: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            json.dump(doc, f, ensure_ascii=False, sort_keys=True, indent=2)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        Path(tmp).unlink(missing_ok=True)


def main() -> int:
    docs = {name: load_json(path) for name, path in FILES.items() if path.suffix == ".json"}
    raw, calendar = docs["raw"], docs["calendar"]
    status, classification = docs["status"], docs["classification"]
    adjustment, periods = docs["adjustment_samples"], docs["periods"]
    postcheck, temporal = docs["postcheck"], docs["temporal"]

    checks = {
        "raw_formal_seal_pass": raw.get("status") == "RAW_CANONICAL_DAILY_PASS",
        "formal_calendar_pass": calendar.get("status") == "FORMAL_MARKET_CALENDAR_PASS",
        "dated_gap_status_has_zero_unknown": status.get("status") == "DATED_TRADING_STATUS_PASS" and status.get("unknown_gap_status_count") == 0,
        "adjustment_categories_classified_and_localized": classification.get("status") == "CLASSIFICATION_COMPLETE_WITH_LOCAL_SEMANTIC_LIMITS",
        "real_suspension_and_recent_listing_samples_pass": adjustment.get("status") == "REAL_ADJUSTMENT_SAMPLES_PASS",
        "formal_period_artifacts_emitted": periods.get("status") == "FORMAL_PERIODS_CANDIDATE_PASS",
        "independent_period_postcheck_pass": postcheck.get("status") == "PASS" and all(postcheck.get("checks", {}).values()),
        "required_temporal_boundary_cases_pass_bounded_sample": temporal.get("status") == "BOUNDED_TEMPORAL_REPLAY_PASS",
    }
    blockers = [
        {"id": "ADJUSTMENT_SOURCE_VISIBILITY_AND_LATE_REVISION_LINEAGE", "status": "OPEN",
         "evidence": "Current GBBQ snapshot supports diagnostic reconstruction; it does not provide historical system-available timestamps or revision history."},
        {"id": "GBBQ_CATEGORY_SEMANTIC_AUTHORITY", "status": "OPEN",
         "evidence": "Category 4, 12, and 15 remain UNKNOWN_PRICE_IMPACT; categories 6, 11, 13, and 14 remain unsupported. Local vendor semantics are not independent primary-source adjudication."},
        {"id": "FULL_SCOPE_SECTION_3C4_REPLAY", "status": "OPEN",
         "evidence": "Eight deletion/perturbation/determinism cases pass over one eligible security in each required board; full R6.2 universe replay remains pending."},
        {"id": "DATED_ISST_COVERAGE_FOR_PRICE_LIMIT_PACK", "status": "OPEN",
         "evidence": "88,011 dated provider status/ST facts cover 982 gap-bearing securities and their bounded query windows; dated isST is not populated for every actual-bar membership row."},
        {"id": "BAOSTOCK_TDX_STATUS_CONFLICTS", "status": "OPEN_SEPARATE_AUDIT",
         "evidence": "Four 2024-06-13 rows have validated local TDX bars while BaoStock tradestatus is 0; local actual-bar precedence is retained and the separate audit remains open."},
    ]
    all_pack_a = all(checks.values()) and not blockers
    pack_a_status = "PASS" if all_pack_a else "BLOCKED"
    period_outputs = periods.get("outputs", {})
    status_output = status.get("output", {})
    receipt = {
        "contract_id": "V4_02_DATA_PERIOD_MAINLINE_ACCEPTANCE_R1",
        "version": "1.0.0",
        "stage": "V4-02 / TASK PACK A",
        "status": pack_a_status,
        "pack_a_status": pack_a_status,
        "observed_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "source_cutoff": SOURCE_CUTOFF,
        "scope": {"required_boards": ["SH_MAIN", "SZ_MAIN", "CHINEXT", "STAR"],
                  "optional_degraded_scope": {"BSE": "EXCLUDED_OPTIONAL_DEGRADED"}},
        "consulted_contracts": {
            "upgrade_document": {"path": str(UPGRADE_DOC), "sha256": UPGRADE_SHA,
                                 "sections": ["3B.6", "3C.1", "3C.2", "3C.3", "3C.4", "5.2", "5.3", "6A", "10N", "78"]},
            "master_task_document": {"path": str(MASTER_DOC), "sha256": sha(MASTER_DOC)},
            "stage_mapping": {"path": "config/v4_02_stage_acceptance_mapping_v2.json",
                              "sha256": sha(ROOT / "config/v4_02_stage_acceptance_mapping_v2.json")},
            "canonical_contract": {"path": "config/v4_02_canonical_daily_pit_contract_v3.json",
                                   "sha256": sha(ROOT / "config/v4_02_canonical_daily_pit_contract_v3.json")},
        },
        "components": {
            "RAW_CANONICAL_DAILY": {"result": raw.get("status"), "formal_seal_receipt": FILES["raw"].relative_to(ROOT).as_posix(),
                                     "artifact": raw.get("artifact"), "receipt_sha256": sha(FILES["raw"])},
            "ADJUSTED_CANONICAL_DAILY": {"result": "CANDIDATE_WITH_PER_SECURITY_FAIL_CLOSED; FORMAL_ACCEPTANCE_OPEN",
                                          "daily_artifact": period_outputs.get("V4_02_ADJUSTED_CANONICAL_DAILY_R6_2_20260926.parquet"),
                                          "quality_counts": postcheck.get("daily_summary", {}).get("quality_counts"),
                                          "category15": classification.get("category15_bounded_adjudication", {}).get("status"),
                                          "classification_receipt_sha256": sha(FILES["classification"]),
                                          "real_sample_receipt_sha256": sha(FILES["adjustment_samples"])},
            "FORMAL_MARKET_CALENDAR": {"result": calendar.get("status"), "receipt_sha256": sha(FILES["calendar"])},
            "TRADING_STATUS_SUSPENSION_RESUMPTION": {
                "result": status.get("status"), "artifact": status_output,
                "classification_counts": status.get("classification_counts"),
                "dated_is_st_coverage": status.get("dated_is_st_coverage"),
                "receipt_sha256": sha(FILES["status"]),
                "separate_conflict_audit": FILES["conflict_audit"].relative_to(ROOT).as_posix()},
            "FORMAL_WEEKLY_MONTHLY": {"result": periods.get("status"), "period_rows": periods.get("period_rows"),
                                       "outputs": period_outputs, "receipt_sha256": sha(FILES["periods"])},
            "CLOSED_ONLY_AS_OF": {"result": "PASS_WITH_BOUNDARY_PARTIALS_AND_PER_SECURITY_QFQ_BLOCKS",
                                  "postcheck_receipt_sha256": sha(FILES["postcheck"])},
            "SECTION_3C_4_TEMPORAL_LEAKAGE": {"result": temporal.get("status"), "case_count": temporal.get("case_count"),
                                              "scope": temporal.get("acceptance_scope"),
                                              "receipt_sha256": sha(FILES["temporal"])},
        },
        "checks": checks,
        "blockers": blockers,
        "acceptance": {"pack_a_pass_requires_all_components": True,
                        "full_scope_temporal_proof": False,
                        "formal_adjustment_semantics_and_historical_revision_lineage": False,
                        "stage_completion_authorized": False,
                        "pack_b_started": False,
                        "v4_03_started": False},
        "artifact_manifest": {
            "dated_status": status_output,
            "daily_qfq_candidate": period_outputs.get("V4_02_ADJUSTED_CANONICAL_DAILY_R6_2_20260926.parquet"),
            "weekly_raw_qfq": period_outputs.get("V4_02_FORMAL_WEEKLY_RAW_QFQ_R6_2_20260926.parquet"),
            "monthly_raw_qfq": period_outputs.get("V4_02_FORMAL_MONTHLY_RAW_QFQ_R6_2_20260926.parquet"),
        },
        "execution_identity": {"base_git_head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
                               "script_sha256": sha(Path(__file__).resolve()),
                               "tdx_root_write_count": 0, "scanner_or_factor_run_count": 0},
        "next_stage": "RESOLVE_PACK_A_OPEN_AUDITS_AND_FULL_SCOPE_TEMPORAL_REPLAY; ONLY_AFTER_PACK_A_PASS_START_PACK_B",
    }
    atomic_json(OUTPUT, receipt)
    print(json.dumps({"status": receipt["status"], "checks": checks, "blockers": len(blockers),
                      "receipt": OUTPUT.relative_to(ROOT).as_posix()}, ensure_ascii=False))
    return 0 if pack_a_status == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
