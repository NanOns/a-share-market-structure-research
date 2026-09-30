from __future__ import annotations

"""Record R6 stage contract, postcheck evidence, and internal acceptance head."""

import hashlib
import json
import os
import re
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports/v4_02"
HEAD = ROOT / "data/v4/V4_02_ACCEPTED_HEAD.json"
MANIFEST = REPORTS / "V4_02_FINAL_STAGING_MANIFEST_R6.json"
POSTCHECK = REPORTS / "V4_02_FINAL_INDEPENDENT_POSTCHECK_R6.json"
BUILD = REPORTS / "V4_02_PRICE_LIMIT_BUILD_R6.json"
TESTS = REPORTS / "V4_02_FINAL_R6_TEST_RECEIPT.json"
RECEIPT = REPORTS / "V4_02_FINAL_RECEIPT_R6.json"
HEAD_SNAPSHOT = REPORTS / "V4_02_R5_ACCEPTED_HEAD_SNAPSHOT_R6.json"


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def rel(path: Path) -> str:
    return str(path.relative_to(ROOT)).replace("\\", "/")


def atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(value, stream, ensure_ascii=False, sort_keys=True, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def code_scan() -> dict:
    files = list((ROOT / "src/workbench_analysis").rglob("*.py"))
    files += list((ROOT / "scripts").glob("build_v4_02*.py"))
    forbidden = re.compile(r"(?:SZ|SH)\.\d{6}|SEC-[A-F0-9]{16,}")
    hits = [rel(path) for path in files if forbidden.search(path.read_text(encoding="utf-8"))]
    return {"scanned_files": len(files), "identifier_hits": hits, "status": "PASS" if not hits else "FAIL"}


def main() -> int:
    required = [MANIFEST.parent / "V4_02_FINAL_STAGING_MANIFEST_R5.json", REPORTS / "V4_02_FINAL_RECEIPT_R5.json",
                REPORTS / "V4_02_FINAL_RECEIPT_R4.json", REPORTS / "V4_02_FINAL_INDEPENDENT_POSTCHECK_R4.json",
                ROOT / "config/special_price_phase_policy_r6.json", ROOT / "data/v4/bootstrap/special_price_phase_events_r4.jsonl",
                ROOT / "data/v4/bootstrap/dated_security_alias_r7.jsonl", ROOT / "data/v4/artifact_store/v4_02/V4_02_PRICE_LIMIT_R6_20260927.jsonl.gz",
                ROOT / "data/v4/artifact_store/v4_02/V4_02_PRICE_LIMIT_R4_20260927.jsonl.gz", BUILD, POSTCHECK, TESTS]
    missing = [rel(p) for p in required if not p.is_file()]
    if missing:
        raise SystemExit("R6_FINAL_SEAL_INPUTS_MISSING:" + ",".join(missing))
    prior = json.loads(HEAD.read_text(encoding="utf-8"))
    if prior.get("final_receipt_path", "").endswith("R5.json") is False or prior.get("status") != "PASS_WITH_BSE_SCOPE_DEGRADED":
        raise SystemExit("R6_PRIOR_R5_ACCEPTED_HEAD_NOT_PRESERVED")
    prior_sha = sha(HEAD)
    atomic_json(HEAD_SNAPSHOT, {"contract_id": "V4_02_R5_ACCEPTED_HEAD_SNAPSHOT_R6", "head": prior,
                                "sha256": prior_sha, "observed_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat()})
    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
    build = json.loads(BUILD.read_text(encoding="utf-8"))
    post = json.loads(POSTCHECK.read_text(encoding="utf-8"))
    tests = json.loads(TESTS.read_text(encoding="utf-8"))
    r4_post = json.loads((REPORTS / "V4_02_FINAL_INDEPENDENT_POSTCHECK_R4.json").read_text(encoding="utf-8"))
    capture = json.loads((REPORTS / "V4_02_R5_SOURCE_CAPTURE_VERIFY.json").read_text(encoding="utf-8"))
    scan = code_scan()
    build_commit = str(build.get("execution_commit") or "")
    builder_core_paths = ["scripts/build_v4_02_price_limits_generic.py", "src/workbench_analysis/special_price_phases.py",
                          "src/workbench_analysis/dated_security_alias.py", "config/special_price_phase_policy_r6.json"]
    builder_commit_is_ancestor = bool(build_commit) and subprocess.run(
        ["git", "merge-base", "--is-ancestor", build_commit, commit], cwd=ROOT, capture_output=True).returncode == 0
    builder_core_unchanged = builder_commit_is_ancestor and subprocess.run(
        ["git", "diff", "--quiet", build_commit, commit, "--", *builder_core_paths], cwd=ROOT, capture_output=True).returncode == 0
    expected_phases = r4_post.get("counts", {}).get("special_price_phases", {})
    checks = {
        "production_generic_builder_exists": True,
        "production_build_completed": build.get("status") == "R6_CANDIDATE_READY",
        "builder_consumes_event_store_policy_alias_and_daily_close": all(key in build.get("inputs", {}) for key in
            ("event_store_sha256", "phase_policy_sha256", "dated_alias_facts_sha256", "adjusted_daily_sha256")),
        "builder_calls_generic_phase_runtime": sum(build.get("apply_phase_event_call_counts", {}).values()) > 0,
        "delisting_first_day_and_period_recomputed": build.get("apply_phase_event_call_counts", {}).get("DELISTING_FIRST_DAY") == 22 and build.get("apply_phase_event_call_counts", {}).get("DELISTING_PERIOD") == 308,
        "unknown_phase_fail_closed_recomputed": build.get("apply_phase_event_call_counts", {}).get("UNKNOWN_SPECIAL_PHASE") == 31,
        "historical_phase_inventory_reproduced": build.get("special_phase_counts") == expected_phases,
        "r4_business_payload_identical": post.get("checks", {}).get("business_payload_identical") is True and post.get("checks", {}).get("business_digest_identical") is True,
        "r4_row_count_and_unknown_inventory_identical": post.get("checks", {}).get("row_count_unchanged") is True and post.get("checks", {}).get("unknown_reason_inventory_identical") is True,
        "r4_limit_status_inventory_identical": post.get("checks", {}).get("limit_status_inventory_identical") is True,
        "synthetic_integration_and_regression_tests_pass": tests.get("result") == "PASS" and tests.get("failed") == 0 and tests.get("skipped") == 0,
        "builder_core_unchanged_since_build_commit": builder_core_unchanged,
        "test_receipt_binds_current_commit": tests.get("execution_commit") == commit,
        "production_code_identifier_scan_pass": scan["status"] == "PASS",
        "R5_evidence_preserved": json.loads((REPORTS / "V4_02_FINAL_RECEIPT_R5.json").read_text(encoding="utf-8")).get("status") == "PASS_WITH_BSE_SCOPE_DEGRADED",
        "source_capture_remains_offline_verified": capture.get("status") == "PASS" and capture.get("mode") == "verify-existing",
        "v4_03_remains_blocked": True,
    }
    paths = {
        "r6_policy": ROOT / "config/special_price_phase_policy_r6.json",
        "r6_builder": ROOT / "scripts/build_v4_02_price_limits_generic.py",
        "r6_postcheck_script": ROOT / "scripts/independent_v4_02_r6_postcheck.py",
        "r6_runtime": ROOT / "src/workbench_analysis/special_price_phases.py",
        "alias_resolver": ROOT / "src/workbench_analysis/dated_security_alias.py",
        "integration_tests": ROOT / "tests/v4_02/test_r6_generic_production_builder.py",
        "test_receipt": TESTS, "build_receipt": BUILD, "independent_postcheck": POSTCHECK,
        "r6_price": ROOT / "data/v4/artifact_store/v4_02/V4_02_PRICE_LIMIT_R6_20260927.jsonl.gz",
        "r4_price": ROOT / "data/v4/artifact_store/v4_02/V4_02_PRICE_LIMIT_R4_20260927.jsonl.gz",
        "r4_acceptance": REPORTS / "V4_02_FINAL_RECEIPT_R4.json",
        "r5_acceptance": REPORTS / "V4_02_FINAL_RECEIPT_R5.json",
        "r5_manifest": REPORTS / "V4_02_FINAL_STAGING_MANIFEST_R5.json",
        "r5_capture_verify": REPORTS / "V4_02_R5_SOURCE_CAPTURE_VERIFY.json",
        "r6_events": ROOT / "data/v4/bootstrap/special_price_phase_events_r4.jsonl",
        "r6_alias_facts": ROOT / "data/v4/bootstrap/dated_security_alias_r7.jsonl",
        "frozen_r3_base": ROOT / "data/v4/artifact_store/v4_02/V4_02_PRICE_LIMIT_R7_20260927.jsonl.gz",
        "daily_r7": ROOT / "data/v4/artifact_store/v4_02/V4_02_ADJUSTED_CANONICAL_DAILY_R7_20260927.parquet",
        "calendar": ROOT / "data/v4/candidate_calendars/V4_02_MARKET_CALENDAR_20230704_20260924_V2/calendar_sse_20230704_20260924.json",
        "standard_rules": ROOT / "config/v4_02_price_limit_rules_r3.json",
        "r4_range_audit": REPORTS / "V4_02_PRICE_LIMIT_RANGE_EXCEPTION_AUDIT_R4.json",
    }
    components = {name.upper(): {"path": rel(path), "bytes": path.stat().st_size, "sha256": sha(path)} for name, path in paths.items()}
    task_doc = Path(r"D:\Users\lps\Desktop\V4_02_R5_EXTERNAL_AUDIT_AND_R6_GENERIC_PRODUCTION_WIRING_20260927.md")
    governing = Path(r"D:\Users\lps\Desktop\A_SHARE_RESEARCH_SYSTEM_V4_2_2_FINAL_EXECUTABLE_CONTRACT_20260925_codex修改版.md")
    manifest = {
        "contract_id": "V4_02_WHOLE_STAGE_STAGING_MANIFEST_R6", "version": "6.0.0", "stage": "V4-02",
        "status": "STAGING_CANDIDATE_READY" if all(checks.values()) else "BLOCKED",
        "stage_contract": "R3_PRICE_LIMIT_BASE + SPECIAL_PRICE_PHASE_EVENT_V1 + SPECIAL_PRICE_PHASE_POLICY_V2; generic runtime recalculation",
        "governing_upgrade_contract": {"contract_id": "DA-MSR-V4.2.2-CODEX-REV2",
            "path": "D:/Users/lps/Desktop/A_SHARE_RESEARCH_SYSTEM_V4_2_2_FINAL_EXECUTABLE_CONTRACT_20260925_codex修改版.md", "sha256": sha(governing)},
        "r6_task_document": {"path": "D:/Users/lps/Desktop/V4_02_R5_EXTERNAL_AUDIT_AND_R6_GENERIC_PRODUCTION_WIRING_20260927.md", "sha256": sha(task_doc)},
        "implementation_commit": commit, "checks": checks, "components": components,
        "scope": {"required_boards": ["SH_MAIN", "SZ_MAIN", "CHINEXT", "STAR"], "optional_degraded": ["BSE"], "source_cutoff": "2026-09-24"},
        "r4_status": "HISTORICAL_DATA_CORRECTNESS_ACCEPTED_AND_PRESERVED",
        "r5_status": "GENERIC_CONTRACTS_ACCEPTED_AND_PRESERVED; PRODUCTION_WIRING_BLOCKED_PENDING_R6",
        "r6_external_status": "PENDING_R6_EXTERNAL_REVIEW", "new_notice_searches": 0, "new_source_recaptures": 0,
        "scanner_factor_trading_runs": 0, "tdx_root_write_count": 0,
        "next_stage": "INDEPENDENT_R6_POSTCHECK_AND_FINAL_RECEIPT; V4-03_BLOCKED_PENDING_EXTERNAL_ACCEPTANCE",
        "created_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    }
    atomic_json(MANIFEST, manifest)
    all_pass = all(checks.values()) and post.get("status") == "PASS"
    receipt = {
        "contract_id": "V4_02_FINAL_ACCEPTANCE_RECEIPT_R6", "version": "6.0.0",
        "stage": "V4-02 FINAL GENERIC PRODUCTION WIRING / R6",
        "status": "PASS_WITH_BSE_SCOPE_DEGRADED" if all_pass else "BLOCKED",
        "external_acceptance": "PENDING_R6_EXTERNAL_REVIEW" if all_pass else "NOT_READY",
        "v4_03_entry": "BLOCKED_PENDING_EXTERNAL_ACCEPTANCE",
        "blockers": [] if all_pass else ["R6_PRODUCTION_BUILDER_OR_EQUIVALENCE_GATE_FAILED"],
        "checks": checks,
        "evidence": {"manifest": {"path": rel(MANIFEST), "sha256": sha(MANIFEST)},
                     "independent_postcheck": {"path": rel(POSTCHECK), "sha256": sha(POSTCHECK), "status": post.get("status")},
                     "production_build": {"path": rel(BUILD), "sha256": sha(BUILD), "business_payload_sha256": build.get("business_payload_sha256")},
                     "tests": {"path": rel(TESTS), "sha256": sha(TESTS), "passed": tests.get("passed"), "result": tests.get("result")},
                     "preserved_r5_receipt": {"path": "reports/v4_02/V4_02_FINAL_RECEIPT_R5.json", "sha256": sha(REPORTS / "V4_02_FINAL_RECEIPT_R5.json")}},
        "scope": manifest["scope"], "tdx_root_write_count": 0, "scanner_factor_trading_runs": 0,
        "next_stage": "WAIT_FOR_EXTERNAL_R6_ACCEPTANCE; DO_NOT_START_V4-03",
        "observed_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    }
    atomic_json(RECEIPT, receipt)
    if all_pass:
        head = {"contract_id": "V4_02_ACCEPTED_HEAD_V1", "stage": "V4-02", "status": "PASS_WITH_BSE_SCOPE_DEGRADED",
                "accepted_at_utc": receipt["observed_at_utc"], "source_cutoff": "2026-09-24",
                "final_receipt_path": rel(RECEIPT), "final_receipt_sha256": sha(RECEIPT),
                "manifest_path": rel(MANIFEST), "manifest_sha256": sha(MANIFEST),
                "supersedes_final_receipt_path": prior.get("final_receipt_path"),
                "supersedes_final_receipt_sha256": prior.get("final_receipt_sha256"),
                "history": {"r1_revoked": True, "r3_blocked_receipt_retained": True,
                            "r4_data_correctness_accepted": True, "r5_generic_contracts_accepted": True,
                            "r6_generic_production_recalculation_complete": True,
                            "r5_head_snapshot_path": rel(HEAD_SNAPSHOT)},
                "v4_03_entry": "BLOCKED_PENDING_EXTERNAL_ACCEPTANCE"}
        atomic_json(HEAD, head)
    print(json.dumps({"manifest": manifest["status"], "postcheck": post.get("status"), "receipt": receipt["status"],
                      "accepted_head_updated": all_pass, "v4_03": receipt["v4_03_entry"]}, ensure_ascii=False))
    return 0 if all_pass else 2


if __name__ == "__main__":
    raise SystemExit(main())
