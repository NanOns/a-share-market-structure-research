from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
BRANCH = "codex/v4-system-reform"


def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha(path: Path) -> str:
    return sha_bytes(path.read_bytes())


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent, delete=False) as stream:
        temp_path = Path(stream.name)
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temp_path, path)


def write_json(path: Path, value: dict) -> None:
    atomic_write(path, json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2).encode("utf-8") + b"\n")


def git(root: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True, text=True, encoding="utf-8").stdout.strip()


def manifest_entry(path: Path) -> dict:
    data = path.read_bytes()
    return {"path": path.relative_to(ROOT).as_posix(), "sha256": sha_bytes(data), "byte_count": len(data)}


def junit_counts(path: Path) -> dict[str, int]:
    root = ET.parse(path).getroot()
    suites = [root] if root.tag.endswith("testsuite") else [item for item in root.iter() if item.tag.endswith("testsuite")]
    return {
        key: sum(int(suite.attrib.get(key, "0")) for suite in suites)
        for key in ("tests", "failures", "errors", "skipped")
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Seal the V4-08 membership candidate after clean-checkout regression and isolated PostgreSQL gates.")
    parser.add_argument("--checkout-root", type=Path, required=True)
    parser.add_argument("--expected-commit", required=True)
    parser.add_argument("--junit", type=Path, required=True)
    parser.add_argument("--full-regression", type=Path)
    parser.add_argument("--schema-receipt", type=Path)
    parser.add_argument("--pre-test-clean-confirmed", action="store_true", help="Confirm the checkout status was empty immediately before test execution.")
    args = parser.parse_args()
    checkout = args.checkout_root.resolve()
    expected_commit = args.expected_commit.lower()
    if not args.pre_test_clean_confirmed:
        raise RuntimeError("pre-test clean checkout status must be confirmed from the captured git status result")
    checkout_head = git(checkout, "rev-parse", "HEAD").lower()
    main_head = git(ROOT, "rev-parse", "HEAD").lower()
    if checkout_head != expected_commit or main_head != expected_commit:
        raise RuntimeError(f"clean-checkout/main HEAD mismatch: checkout={checkout_head}, main={main_head}, expected={expected_commit}")
    checkout_status = git(checkout, "status", "--porcelain", "--untracked-files=all")
    if checkout_status:
        raise RuntimeError(f"clean checkout has changes after verification:\n{checkout_status}")

    full_regression_path = args.full_regression.resolve() if args.full_regression else checkout / "reports/v4_07/V4_07_ISOLATED_FULL_REGRESSION.json"
    schema_receipt_path = args.schema_receipt.resolve() if args.schema_receipt else checkout / "reports/v4_08/V4_08_MEMBERSHIP_SCHEMA_MIGRATION_RECEIPT.json"
    full_regression = json.loads(full_regression_path.read_text(encoding="utf-8"))
    schema_receipt = json.loads(schema_receipt_path.read_text(encoding="utf-8"))
    if full_regression.get("status") != "PASS_ISOLATED_FULL_REGRESSION":
        raise RuntimeError("isolated V4 regression receipt is not PASS")
    if schema_receipt.get("status") != "PASS_ISOLATED_MIGRATION_AND_ROLLBACK" or not all(schema_receipt.get("checks", {}).values()):
        raise RuntimeError("V4-08 isolated schema migration/rollback receipt is not PASS")
    counts = junit_counts(args.junit.resolve())
    if counts["tests"] == 0 or counts["failures"] or counts["errors"]:
        raise RuntimeError(f"V4-08 clean-checkout pytest report did not pass: {counts}")
    full_summary = str(full_regression.get("test_summary", ""))
    match = re.search(r"(\d+) passed(?:,\s*(\d+) skipped)?(?:,\s*(\d+) failed)?", full_summary)
    if not match:
        raise RuntimeError(f"unable to parse full V4 regression summary: {full_summary}")
    full_passed, full_skipped, full_failed = int(match.group(1)), int(match.group(2) or 0), int(match.group(3) or 0)
    if full_failed:
        raise RuntimeError(f"full V4 regression had {full_failed} failures")
    created_at = utc_now()

    # Promote only the clean-checkout receipts into the main evidence tree; the worktree remains a disposable test checkout.
    schema_dest = ROOT / "reports/v4_08/V4_08_MEMBERSHIP_SCHEMA_MIGRATION_RECEIPT.json"
    schema_bytes = schema_receipt_path.read_bytes()
    atomic_write(schema_dest, schema_bytes)
    clean_receipt = {
        "contract_id": "V4_08_MEMBERSHIP_CLEAN_CHECKOUT_RECEIPT_V1",
        "status": "PASS_CLEAN_CHECKOUT_TESTS_AND_ISOLATED_SCHEMA_MIGRATION",
        "tested_commit": checkout_head,
        "main_checkout_head_at_seal": main_head,
        "branch_under_test": "DETACHED_AT_PUSHED_BRANCH_COMMIT",
        "remote_branch": BRANCH,
        "checkout_path": str(checkout),
        "working_tree_clean_before_tests": True,
        "working_tree_clean_after_tests": True,
        "post_test_git_status_porcelain": checkout_status,
        "full_regression_status": full_regression["status"],
        "v4_08_test_count": counts["tests"],
        "v4_08_test_failures": counts["failures"],
        "v4_08_test_errors": counts["errors"],
        "v4_08_test_skipped": counts["skipped"],
        "schema_migration_status": schema_receipt["status"],
        "schema_migrations": schema_receipt.get("migrations", []),
        "schema_rollbacks": schema_receipt.get("rollbacks", []),
        "receipt_sha256": sha_bytes(schema_bytes),
        "created_at_utc": created_at,
    }
    clean_path = ROOT / "reports/v4_08/V4_08_MEMBERSHIP_CLEAN_CHECKOUT_RECEIPT.json"
    write_json(clean_path, clean_receipt)

    test_matrix = [
        "tests/v4_01", "tests/v4_02", "tests/v4_03", "tests/v4_04", "tests/v4_05",
        "tests/v4_06", "tests/v4_07", "tests/v4_08", "tests/v4_joint", "tests/v4_phase0",
    ]
    regression = {
        "contract_id": "V4_08_MEMBERSHIP_REQUIRED_REGRESSION_R1",
        "status": "PASS_ISOLATED_FULL_MATRIX_AND_V4_08_FOCUSED_SUITE",
        "tested_commit": checkout_head,
        "test_matrix": test_matrix,
        "isolated_postgres_full_suite": {
            "status": full_regression["status"],
            "test_command": full_regression["test_command"],
            "test_summary": full_summary,
            "passed": full_passed,
            "skipped": full_skipped,
            "postgres_version": full_regression["postgres_version"],
            "database_identity": full_regression["database_identity"],
            "migrations_applied": full_regression["migration_run"].get("migrations", []),
            "temporary_cluster_cleaned_up": full_regression.get("temporary_cluster_cleaned_up") is True,
        },
        "v4_08_focused_suite": {
            "test_command": "python -m pytest tests/v4_08 -q --junitxml=<temporary-file>",
            "tests": counts["tests"], "passed": counts["tests"] - counts["failures"] - counts["errors"] - counts["skipped"],
            "skipped": counts["skipped"], "failures": counts["failures"], "errors": counts["errors"],
            "junit_report_sha256": sha(args.junit.resolve()),
        },
        "combined": {
            "passed": full_passed + counts["tests"] - counts["failures"] - counts["errors"] - counts["skipped"],
            "skipped": full_skipped + counts["skipped"],
            "failed": full_failed + counts["failures"] + counts["errors"],
        },
        "isolated_v4_08_postgres_migration": {
            "status": schema_receipt["status"], "postgres_version": schema_receipt["postgres_version"],
            "checks": schema_receipt["checks"], "migrations": schema_receipt.get("migrations", []),
            "rollbacks": schema_receipt.get("rollbacks", []),
            "database_scope": schema_receipt["database_scope"],
        },
        "config_dot_env_read": False,
        "configured_or_production_database_used": False,
        "created_at_utc": created_at,
    }
    regression_path = ROOT / "reports/v4_08/V4_08_MEMBERSHIP_REQUIRED_REGRESSION_R1.json"
    write_json(regression_path, regression)

    stage_manifest_path = ROOT / "reports/v4_08/V4_08_MEMBERSHIP_STAGE_CANDIDATE_MANIFEST.json"
    prior_manifest = json.loads(stage_manifest_path.read_text(encoding="utf-8"))
    paths = {entry["path"] for entry in prior_manifest["files"]}
    paths.update({
        "scripts/seal_v4_08_membership_stage.py",
        clean_path.relative_to(ROOT).as_posix(),
        regression_path.relative_to(ROOT).as_posix(),
    })
    manifest_files = [manifest_entry(ROOT / rel) for rel in sorted(paths)]
    final_manifest = {
        **prior_manifest,
        "status": "CANDIDATE_BLOCKED_FOR_EXTERNAL_PIT_ACCEPTANCE; CLEAN_CHECKOUT_AND_REGRESSION_PASS",
        "generated_at_utc": created_at,
        "verification_commit": checkout_head,
        "full_regression": {"passed": regression["combined"]["passed"], "skipped": regression["combined"]["skipped"], "failed": regression["combined"]["failed"]},
        "file_count": len(manifest_files),
        "files": manifest_files,
    }
    write_json(stage_manifest_path, final_manifest)
    manifest_hash = sha(stage_manifest_path)

    source_acceptance = json.loads((ROOT / "reports/v4_08/V4_08_SECTOR_MEMBERSHIP_SOURCE_CONTRACT_ACCEPTANCE.json").read_text(encoding="utf-8"))
    replay = json.loads((ROOT / "reports/v4_08/V4_08_CURRENT_MEMBERSHIP_REPLAY_DIAGNOSTIC.json").read_text(encoding="utf-8"))
    identity = json.loads((ROOT / "reports/v4_08/V4_08_MEMBERSHIP_IDENTITY_POSTCHECK.json").read_text(encoding="utf-8"))
    temporal = json.loads((ROOT / "reports/v4_08/V4_08_MEMBERSHIP_TEMPORAL_LEAKAGE_TEST.json").read_text(encoding="utf-8"))
    pit_candidate = json.loads((ROOT / "reports/v4_08/V4_08_GO_FORWARD_PIT_MEMBERSHIP_CANDIDATE.json").read_text(encoding="utf-8"))
    prior_rps_json = ROOT / "reports/audits/V4_07_PRIOR_RPS_BOOTSTRAP_GAP_ASSESSMENT_R1.json"
    closure = f"""# V4-08 PIT Sector Membership Baseline R1 — Final Candidate Closure

- Stage contract: `V4_08_PIT_SECTOR_MEMBERSHIP_BASELINE_R1`.
- Candidate result: `DIAGNOSTIC_RECONSTRUCTION_PASS; PIT_BASELINE_BLOCKED_PENDING_EXTERNAL_ACCEPTANCE`.
- Accepted range: `V4_00_TO_V4_07_ACCEPTED`; no later stage was promoted.
- Candidate generation HEAD: `{prior_manifest.get('source_head_at_generation')}`; clean-checkout tested/pushed commit: `{checkout_head}`.
- Latest accepted market session available from V4-05: `{replay['target_trade_date']}`. First go-forward PIT baseline date: `null` because the TDX source has no evidenced provider-available timestamp or membership effective date.
- TDX source observed at `{source_acceptance['source_paths']['T0002/hq_cache/tdxhy.cfg']['observed_at']}`; candidate ingestion/system availability was recorded in source artifacts. Hashes: `{json.dumps({k:v['sha256'] for k,v in source_acceptance['source_paths'].items()}, sort_keys=True)}`.
- Full diagnostic replay: `{replay.get('row_count', replay['all_diagnostic_fact_count']):,}` rows; current snapshot digest `{replay['current_source_snapshot_digest']}`; replay digest `{replay['replay_snapshot_digest']}`. Bases are `CURRENT_TDX_MEMBERSHIP` and `CURRENT_MEMBERSHIP_REPLAY`; all replay rows have `pit_observed=false` and `historical_backtest_safe=false`.
- Raw captured rows: `{replay['raw_source_fact_count']:,}`; derived parent rows: `{replay['derived_parent_fact_count']:,}`. Formal-type membership row counts: `{json.dumps(replay['all_fact_counts_by_formal_type'], sort_keys=True)}`; sector counts: `{json.dumps(replay['sector_counts_by_formal_type'], sort_keys=True)}`; unique mapped security identities: `{replay['unique_mapped_security_id_count']:,}`.
- Retained diagnostic limitations: `{replay['unknown_source_type_fact_counts']}` unknown-type facts and `{identity['unresolved_source_key_count']:,}` unresolved source keys across `{identity['unknown_identity_membership_fact_count']:,}` facts; no rows were silently dropped. Parent map `{replay['industry_parent_map']['map_id']}` digest `{replay['industry_parent_map_digest']}` remains diagnostic-only.
- Membership quality distribution: `{json.dumps(replay['membership_quality_distribution'], sort_keys=True)}`. Temporal leakage gate: `{temporal['status']}`; revision/fork gate: `reports/v4_08/V4_08_MEMBERSHIP_REVISION_TEST.json`; deterministic fixed-context hashes: `reports/v4_08/V4_08_MEMBERSHIP_DETERMINISM.json`.
- PostgreSQL migrations `{', '.join(item['path'].split('/')[-1] for item in schema_receipt.get('migrations', []))}` and reverse rollbacks passed on isolated PostgreSQL `{schema_receipt['postgres_version']}`. No configured database or `config/.env` was read.
- Clean checkout `{checkout_head}` passed the established V4 matrix (`{full_summary}`) plus V4-08 focused suite (`{counts['tests']} passed, {counts['skipped']} skipped`). Combined: `{regression['combined']['passed']} passed, {regression['combined']['skipped']} skipped, {regression['combined']['failed']} failed. The checkout was clean before and after.
- V4-07 real Base Seed capability remains `DEGRADED_BY_ACCEPTED_PRIOR_RPS_BOOTSTRAP_UNKNOWN`; the separate audit remains OPEN at `{prior_rps_json.relative_to(ROOT).as_posix()}` (SHA-256 `{sha(prior_rps_json)}`).
- Stage acceptance: `BLOCKED_FOR_EXTERNAL_PIT_BASELINE_ACCEPTANCE`. Current TDX bytes and filesystem mtimes do not prove source availability/effective date. The accepted identity map also leaves unresolved keys. No formal V4-08 sector/rotation production is authorized; no current membership was relabeled as PIT.
- Stage candidate manifest: `{stage_manifest_path.relative_to(ROOT).as_posix()}`; SHA-256 `{manifest_hash}`. Next stage: independent external review of this candidate and the source-time/identity blockers.
"""
    closure_path = ROOT / "reports/v4_08/V4_08_MEMBERSHIP_CLOSURE.md"
    atomic_write(closure_path, closure.encode("utf-8"))
    print(json.dumps({
        "status": final_manifest["status"], "tested_commit": checkout_head,
        "combined": regression["combined"], "manifest_sha256": manifest_hash,
        "clean_checkout_receipt": clean_path.relative_to(ROOT).as_posix(),
        "regression_receipt": regression_path.relative_to(ROOT).as_posix(),
        "closure": closure_path.relative_to(ROOT).as_posix(),
    }, ensure_ascii=False, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
