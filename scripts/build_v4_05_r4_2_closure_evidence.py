"""Assemble and independently check the R4.2 exact ledger binding evidence."""
from __future__ import annotations

from hashlib import sha256
import json
import os
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "reports/v4_05"
STAGE = "V4_05_REPLAY_GATE_A_R4_2_EXACT_LEDGER_BINDING"
CANDIDATE = "V4_05_DATA_FACTOR_REPLAY_DEGRADED_PASS_CANDIDATE_R4_2"
R4_1_MANIFEST = "reports/v4_05/V4_05_R4_1_STAGE_CANDIDATE_MANIFEST.json"
PG_REPORT = "reports/v4_05/V4_05_R4_2_POSTGRES_REVISION_LEDGER_IDEMPOTENCY.json"
CLEAN_REPORT = "reports/v4_05/V4_05_R4_2_CLEAN_CHECKOUT_RUNTIME.json"
R4_DIFF = "reports/v4_05/V4_05_R4_1_R4_DIFF.json"
EXACT_EXPECTED = {
    "CORE_PROFILE": {
        "artifact_path": "reports/v4_05/staging/V4_05_R4_1_FULL_MARKET_CORE_PROFILE.jsonl.gz",
        "artifact_sha256": "9a6ebedc715bc4b310ecf76c77e01cb6dfe9dadc17d335b5fc9afbcc2f6f3fa0",
        "logical_digest": "d195518796acc64015174eac8f9bb8721a27095311ece00baedf8c12b0633e74",
        "receipt_path": "reports/v4_05/V4_05_R4_1_CORE_PROFILE_REPLAY.json",
    },
    "FULL_SCOPE_FACTORS": {
        "artifact_path": "reports/v4_05/staging/V4_05_R4_1_FULL_SCOPE_FACTORS.jsonl.gz",
        "artifact_sha256": "17ae571629b76399e32d9e8a243268ea1fac619e1c5168d307bfd8ebf1494c48",
        "logical_digest": "0cfe708567935726f0ad51ae4bb47237ec7aee556db3437c12f21f0c623bd0d2",
        "receipt_path": "reports/v4_05/V4_05_R4_1_FULL_SCOPE_FACTORS_RECEIPT.json",
    },
    "PERIOD_ASOF": {
        "artifact_path": "reports/v4_05/staging/V4_05_R4_1_PERIOD_ASOF.jsonl.gz",
        "artifact_sha256": "e54674e8459e1258610639d76fac7a5f7b6093a4013f912b8937fb6fa96c2233",
        "receipt_path": "reports/v4_05/V4_05_R4_1_PERIOD_ASOF.json",
    },
    "MARKET_REFERENCE": {
        "receipt_path": "reports/v4_05/V4_05_R4_1_MARKET_REFERENCE.json",
        "one_session_output_digest": "80d8ac5cc69e8ae4d165f89324e45d0cc7e49a81d13339b31ff8fbec5e578554",
    },
    "MARKET_REGIME": {"receipt_path": "reports/v4_05/V4_05_R4_1_MARKET_REGIME.json"},
    "MARKET_SNAPSHOT_IDENTITY": {"receipt_path": "reports/v4_05/V4_05_R4_1_MARKET_SNAPSHOT_IDENTITY.json"},
}
OLD_R4_BASELINE_FILES = (
    "V4_05_R4_CORE_PROFILE_REPLAY.json",
    "V4_05_R4_FULL_SCOPE_FACTORS_RECEIPT.json",
    "V4_05_R4_MARKET_REFERENCE.json",
    "V4_05_R4_PERIOD_ASOF.json",
)
PROTECTED_HEADS = (
    "data/v4/V4_STAGE_ACCEPTED_HEAD.json",
    "data/v4/V4_01_ACCEPTED_HEAD.json",
    "data/v4/V4_02_ACCEPTED_HEAD.json",
    "data/v4/V4_02_GO_FORWARD_PIT_ACCEPTED_HEAD.json",
    "data/v4/V4_03_ACCEPTED_HEAD_AMENDED_R1.json",
    "data/v4/V4_04_ACCEPTED_HEAD.json",
)


def load(relative: str) -> dict:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def file_identity(path: Path) -> dict:
    h = sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return {"sha256": h.hexdigest(), "byte_count": path.stat().st_size}


def canonical_json_sha(path: Path) -> str:
    value = json.loads(path.read_bytes().decode("utf-8-sig"))
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
                         allow_nan=False).encode("utf-8")
    return sha256(encoded).hexdigest()


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


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, check=True, capture_output=True,
                          text=True).stdout.strip()


def payload_text(value: object) -> str:
    if isinstance(value, dict):
        return " ".join(payload_text(item) for item in value.values())
    if isinstance(value, (list, tuple)):
        return " ".join(payload_text(item) for item in value)
    return str(value)


def build_exact_binding(pg: dict, manifest: dict, manifest_sha: str) -> dict:
    actual_rows = pg["baseline_source_manifest"]
    actual = {row["source_key"]: row for row in actual_rows}
    receipts = {}
    for source_key, expected in EXACT_EXPECTED.items():
        path = ROOT / expected["receipt_path"]
        receipt = json.loads(path.read_text(encoding="utf-8"))
        receipts[source_key] = {"path": expected["receipt_path"],
                                "raw_sha256": file_identity(path)["sha256"],
                                "canonical_json_sha256": canonical_json_sha(path),
                                "logical_digest": receipt.get("logical_digest"),
                                "artifact_path": expected.get("artifact_path", expected["receipt_path"]),
                                "artifact_sha256": expected.get("artifact_sha256", file_identity(path)["sha256"])}
        if source_key in {"CORE_PROFILE", "FULL_SCOPE_FACTORS", "PERIOD_ASOF"}:
            receipt["artifact_sha256"] = file_identity(ROOT / expected["artifact_path"])["sha256"]
            if source_key in {"CORE_PROFILE", "FULL_SCOPE_FACTORS"}:
                if receipt["logical_digest"] != expected["logical_digest"]:
                    raise AssertionError(f"{source_key} logical digest differs from frozen R4.1 identity")
        elif source_key == "MARKET_REFERENCE":
            receipts[source_key]["one_session_output_digest"] = receipt["horizons"]["1"]["output_digest"]
        manifest_entry_path = expected.get("artifact_path", expected["receipt_path"])
        manifest_entry = manifest["artifact_and_evidence_hashes"].get(manifest_entry_path)
        disk = file_identity(ROOT / manifest_entry_path)
        if manifest_entry != disk:
            raise AssertionError(f"R4.1 candidate manifest is stale for {source_key}: {manifest_entry_path}")

    comparisons = {
        "candidate_manifest_sha_matches_postgres_run": pg["candidate_manifest_path"] == R4_1_MANIFEST
            and pg["candidate_manifest_sha256"] == manifest_sha
            and pg["exact_candidate_binding"]["candidate_manifest_sha256"] == manifest_sha,
        "CORE_PROFILE ledger digest is R4.1 artifact SHA": actual["CORE_PROFILE"]["digest"]
            == EXACT_EXPECTED["CORE_PROFILE"]["artifact_sha256"],
        "FULL_SCOPE_FACTORS ledger digest is R4.1 artifact SHA": actual["FULL_SCOPE_FACTORS"]["digest"]
            == EXACT_EXPECTED["FULL_SCOPE_FACTORS"]["artifact_sha256"],
        "PERIOD_ASOF ledger digest is R4.1 artifact SHA": actual["PERIOD_ASOF"]["digest"]
            == EXACT_EXPECTED["PERIOD_ASOF"]["artifact_sha256"],
        "MARKET_REFERENCE ledger digest is canonical R4.1 identity": actual["MARKET_REFERENCE"]["digest"]
            == receipts["MARKET_REFERENCE"]["canonical_json_sha256"],
        "MARKET_REFERENCE output digest is R4.1 exact": actual["MARKET_REFERENCE"]["payload"]["output_digests"]["1"]
            == EXACT_EXPECTED["MARKET_REFERENCE"]["one_session_output_digest"],
        "MARKET_REGIME ledger identity is R4.1": actual["MARKET_REGIME"]["digest"]
            == receipts["MARKET_REGIME"]["canonical_json_sha256"],
        "MARKET_SNAPSHOT_IDENTITY ledger identity is R4.1": actual["MARKET_SNAPSHOT_IDENTITY"]["digest"]
            == receipts["MARKET_SNAPSHOT_IDENTITY"]["canonical_json_sha256"],
        "state head logical digest equals R4.1 Core Profile": pg["actual_state_head"]["logical_digest"]
            == EXACT_EXPECTED["CORE_PROFILE"]["logical_digest"],
        "publication head state logical digest equals R4.1 Core Profile": pg["actual_publication_head"]["state_logical_digest"]
            == EXACT_EXPECTED["CORE_PROFILE"]["logical_digest"],
    }
    old_count = sum(old in payload_text(row["payload"])
                    for row in actual_rows for old in OLD_R4_BASELINE_FILES)
    all_exact = all(comparisons.values()) and old_count == 0 \
        and pg["exact_candidate_binding"]["all_exact_bindings_match"] \
        and pg["exact_candidate_binding"]["old_r4_binding_count"] == 0
    cases = pg["cases"]["cases"]
    i_case_statuses = {
        "I01_identical_replay": cases["I01_identical_replay"]["status"],
        "I02_changed_source_revision": cases["I02_changed_source_revision"]["status"],
        "I03_negative_guards": "PASS" if all(item["rejected"] for item in cases["I03_negative_guards"].values()) else "FAIL",
        "I04_transaction_rollback": "PASS" if all(item["passed"] for item in cases["I04_transaction_rollback"]) else "FAIL",
        "I05_prior_state_freeze": "PASS" if cases["I05_prior_state_freeze"]["publication_head_unchanged"]
            and all(cases["I05_prior_state_freeze"][key]["rejected"] for key in (
                "replace_prior_publication_head", "delete_prior_publication_head",
                "change_prior_state_head", "change_prior_state_logical_digest")) else "FAIL",
    }
    result = {
        "contract_id": "V4_05_R4_2_EXACT_CANDIDATE_LEDGER_BINDING_V1",
        "status": "PASS" if all_exact else "FAIL",
        "candidate_manifest": {"path": R4_1_MANIFEST, "sha256": manifest_sha,
                               "candidate_status": manifest["status"],
                               "external_acceptance": manifest["external_acceptance"]},
        "r4_1_candidate_receipt_identities": receipts,
        "actual_postgresql": {
            "postgres_version": pg["postgres_version"],
            "isolated_connection_identity": pg["isolated_connection_identity"],
            "production_connection_used": pg["production_connection_used"],
            "applied_migration_count": pg["applied_migration_count"],
            "publication_id": pg["actual_publication_head"]["publication_id"],
            "baseline_source_manifest_sha256": pg["baseline_source_manifest_sha256"],
            "consumed_source_identities": actual_rows,
            "state_head": pg["actual_state_head"],
            "publication_head": pg["actual_publication_head"],
            "G08_cases": i_case_statuses,
        },
        "exact_binding_comparisons": comparisons,
        "all_exact_bindings_match": all_exact,
        "old_r4_binding_count": old_count,
        "stage_record": {"stage_contract": STAGE,
                         "acceptance_result": "PASS_CANDIDATE_PENDING_EXTERNAL_AUDIT" if all_exact else "FAIL",
                         "evidence": "Exact R4.1 candidate manifest, receipt/artifact identities and PostgreSQL consumed-source rows plus both ledger heads independently compared.",
                         "next_stage": "INDEPENDENT_EXTERNAL_AUDIT_R4_2"},
    }
    atomic_json(REPORT / "V4_05_R4_2_EXACT_CANDIDATE_LEDGER_BINDING.json", result)
    if not all_exact:
        raise RuntimeError("exact R4.1 candidate identities did not bind in PostgreSQL")
    return result


def build_runtime_receipt(pg: dict, clean: dict, exact: dict) -> dict:
    summary = clean["postgres_ledger_run"]["runtime_suite"]["summary"]
    match = re.fullmatch(r"(\d+) passed, (\d+) skipped in (.+)", summary)
    if not match:
        raise ValueError(f"unrecognized full pytest summary: {summary}")
    result = {
        "contract_id": "V4_05_R4_2_RUNTIME_TEST_RECEIPT_V1",
        "status": "PASS" if clean["status"] == "PASS" and pg["status"] == "PASS"
            and exact["all_exact_bindings_match"] else "FAIL",
        "implementation_commit": clean["implementation_commit"],
        "fresh_clone_head": clean["clean_checkout_head"],
        "exact_candidate_binding_test": clean["exact_candidate_binding_test"],
        "full_required_pytest_suite": {
            "command": ["python", "scripts/run_v4_05_r4_1_postgres_ledger.py"],
            "summary": summary, "passed": int(match.group(1)), "skipped": int(match.group(2)),
            "duration": match.group(3),
            "tests_v4_phase0_test_postgres_schema_ran": clean["postgres_ledger_run"]["runtime_suite"]["tests_v4_phase0_test_postgres_schema_ran"],
            "skipped_test_names_and_reasons": clean["postgres_ledger_run"]["runtime_suite"]["skipped_test_names_and_reasons"],
        },
        "formal_postgresql_I01_I05": {
            "status": clean["postgres_ledger_run"]["status"],
            "version": clean["postgres_ledger_run"]["postgres_version"],
            "applied_migration_count": clean["postgres_ledger_run"]["applied_migration_count"],
            "isolated_connection_identity": clean["postgres_ledger_run"]["isolated_connection_identity"],
            "production_connection_used": clean["postgres_ledger_run"]["production_connection_used"],
            "cases": clean["postgres_ledger_run"]["cases"],
            "cleanup": clean["postgres_ledger_run"]["cleanup"],
            "all_exact_bindings_match": clean["postgres_ledger_run"]["all_exact_bindings_match"],
            "old_r4_binding_count": clean["postgres_ledger_run"]["old_r4_binding_count"],
        },
        "primary_checkout_postgresql_run": {"status": pg["status"],
            "summary": pg["runtime_test_receipt"]["summary"],
            "all_exact_bindings_match": pg["exact_candidate_binding"]["all_exact_bindings_match"]},
        "stage_record": {"stage_contract": STAGE,
                         "acceptance_result": "PASS" if clean["status"] == "PASS" else "FAIL",
                         "evidence": "Fresh clone exact-candidate guard, formal PostgreSQL I01-I05, full pytest suite and explicit skipped-test disclosure.",
                         "next_stage": "INDEPENDENT_EXTERNAL_AUDIT_R4_2"},
    }
    atomic_json(REPORT / "V4_05_R4_2_RUNTIME_TEST_RECEIPT.json", result)
    return result


def build() -> dict:
    pg = load(PG_REPORT)
    clean = load(CLEAN_REPORT)
    manifest_path = ROOT / R4_1_MANIFEST
    manifest = load(R4_1_MANIFEST)
    manifest_sha = file_identity(manifest_path)["sha256"]
    exact = build_exact_binding(pg, manifest, manifest_sha)
    runtime = build_runtime_receipt(pg, clean, exact)
    diff = load(R4_DIFF)
    current_head = git("rev-parse", "HEAD")
    start = "f1e3d2ee4721e4880c043e8ca949e7c1e47dce41"
    protected = {}
    for relative in PROTECTED_HEADS:
        initial = git("rev-parse", f"{start}:{relative}")
        present = git("rev-parse", f"HEAD:{relative}")
        tracked_diff = subprocess.run(["git", "diff", "--quiet", "HEAD", "--", relative], cwd=ROOT).returncode == 0
        protected[relative] = {"starting_git_blob": initial, "current_git_blob": present,
                               "worktree_unchanged": tracked_diff,
                               "unchanged": initial == present and tracked_diff}
    accepted_head_absent = not (ROOT / "data/v4/V4_05_ACCEPTED_HEAD.json").exists()
    head_discipline = accepted_head_absent and all(item["unchanged"] for item in protected.values())
    cases = clean["postgres_ledger_run"]["cases"]
    exact_test_pass = clean["exact_candidate_binding_test"]["passed"]
    i_cases_pass = clean["postgres_ledger_run"]["status"] == "PASS" and all(
        value == "PASS" for value in cases.values())
    checks = {
        "exact_R4_1_candidate_cross_binding": exact["all_exact_bindings_match"]
            and exact["old_r4_binding_count"] == 0,
        "fresh_clone_exact_test_and_full_runtime": exact_test_pass and i_cases_pass
            and runtime["status"] == "PASS",
        "official_postgres_migrations_isolated": clean["postgres_ledger_run"]["applied_migration_count"] == 12
            and clean["postgres_ledger_run"]["production_connection_used"] is False
            and clean["postgres_ledger_run"]["cleanup"]["succeeded"],
        "R4_business_values_frozen": diff["business_field_changes"] == 0 and diff["state_changes"] == 0
            and diff["unexpected_business_value_drift"] == 0 and diff["target_identities"] == 5222
            and diff["frozen_values"]["market_regime_trend_axis"]["r4_1"] == "UNKNOWN",
        "Accepted_Head_discipline": head_discipline,
        "external_acceptance_pending": manifest["external_acceptance"] == "PENDING",
        "required_skips_disclosed": len(runtime["full_required_pytest_suite"]["skipped_test_names_and_reasons"])
            == runtime["full_required_pytest_suite"]["skipped"],
    }
    overall = all(checks.values())
    postcheck = {
        "contract_id": "V4_05_R4_2_INDEPENDENT_POSTCHECK_V1",
        "status": "PASS" if overall else "FAIL",
        "candidate_status": CANDIDATE if overall else "BLOCKED_R4_2_POSTCHECK_FAILURE",
        "external_acceptance": "PENDING", "implementation_commit": clean["implementation_commit"],
        "evidence_assembly_head": current_head,
        "checks": checks,
        "exact_candidate_binding": {"all_exact_bindings_match": exact["all_exact_bindings_match"],
                                     "old_r4_binding_count": exact["old_r4_binding_count"],
                                     "candidate_manifest_sha256": manifest_sha,
                                     "state_logical_digest": exact["actual_postgresql"]["state_head"]["logical_digest"]},
        "business_freeze": {"target_trade_date": diff["target_trade_date"],
                            "target_identities": diff["target_identities"],
                            "business_field_changes": diff["business_field_changes"],
                            "state_changes": diff["state_changes"],
                            "unexpected_business_value_drift": diff["unexpected_business_value_drift"],
                            "market_reference_1_3_5": diff["frozen_values"]["market_reference_1_3_5"],
                            "market_regime_trend_axis": diff["frozen_values"]["market_regime_trend_axis"]["r4_1"]},
        "protected_heads": protected,
        "v4_05_accepted_head_absent": accepted_head_absent,
        "stage_record": {"stage_contract": STAGE,
                         "acceptance_result": "PASS_CANDIDATE_PENDING_EXTERNAL_AUDIT" if overall else "FAIL",
                         "evidence": "Exact binding receipt, clean clone suite, formal PostgreSQL identity, frozen business diff and unchanged accepted-head hashes.",
                         "next_stage": "INDEPENDENT_EXTERNAL_AUDIT_R4_2"},
    }
    atomic_json(REPORT / "V4_05_R4_2_INDEPENDENT_POSTCHECK.json", postcheck)

    stage_entry = f"""# V4-05 R4.2 Stage Entry

## Contract and scope

- Contract: `{STAGE}`.
- Starting HEAD: `{start}`.
- Implementation commit: `{clean['implementation_commit']}`.
- Governing task: `docs/evidence/V4_05_REPLAY_GATE_A_R4_2_EXACT_LEDGER_BINDING_TASK_20260929.md`.
- Latest R4.1 external audit: `docs/evidence/V4_05_REPLAY_GATE_A_R4_1_EXTERNAL_AUDIT_20260929.md`.
- Sole scope: close `POSTGRES_LEDGER_TESTED_R4_NOT_R4_1_EXACT_IDENTITY`; R4.1 business artifacts and B05 remain frozen.

## Exact binding results

- R4.1 candidate manifest: `{R4_1_MANIFEST}`; SHA-256 `{manifest_sha}`.
- PostgreSQL ledger binds Core Profile `{EXACT_EXPECTED['CORE_PROFILE']['artifact_sha256']}`, Factors `{EXACT_EXPECTED['FULL_SCOPE_FACTORS']['artifact_sha256']}`, Period `{EXACT_EXPECTED['PERIOD_ASOF']['artifact_sha256']}`, and the canonical R4.1 Market Reference identity.
- Actual state and publication head logical digest: `{exact['actual_postgresql']['state_head']['logical_digest']}`.
- `all_exact_bindings_match={str(exact['all_exact_bindings_match']).lower()}`; `old_r4_binding_count={exact['old_r4_binding_count']}`.

## Runtime and acceptance

- Fresh pushed-commit clone: `{clean['status']}`; exact binding test `{clean['exact_candidate_binding_test']['stdout']}`.
- Formal PostgreSQL 18.6, 12 migrations, isolated connection; I01–I05 passed, production connection used: `{str(clean['postgres_ledger_run']['production_connection_used']).lower()}`.
- Full suite: `{runtime['full_required_pytest_suite']['summary']}`; PostgreSQL schema tests ran; skipped test names/reasons appear in `V4_05_R4_2_RUNTIME_TEST_RECEIPT.json`.
- R4 business drift remains zero; 5,222 target identities and `trend_axis=UNKNOWN`.
- Candidate state: `{CANDIDATE}`; external acceptance remains `PENDING`.
- No V4-05 Accepted Head was created; protected heads are unchanged; V4-06/V4-07 remain unauthorized.
- Next stage: `INDEPENDENT_EXTERNAL_AUDIT_R4_2`.
"""
    atomic_text(REPORT / "V4_05_R4_2_STAGE_ENTRY.md", stage_entry)

    closure = f"""# V4-05 R4.2 Exact Ledger Binding Candidate

Stage: `{STAGE}`

Candidate: `{CANDIDATE}`

Exact candidate binding: `{'PASS' if exact['all_exact_bindings_match'] else 'FAIL'}`

External acceptance: `PENDING`

## R4.1 identity is now what G08 tested

- Candidate manifest `{R4_1_MANIFEST}` SHA-256: `{manifest_sha}`.
- Core Profile artifact SHA `{EXACT_EXPECTED['CORE_PROFILE']['artifact_sha256']}`; logical digest `{EXACT_EXPECTED['CORE_PROFILE']['logical_digest']}`.
- Full Scope Factors artifact SHA `{EXACT_EXPECTED['FULL_SCOPE_FACTORS']['artifact_sha256']}`; logical digest `{EXACT_EXPECTED['FULL_SCOPE_FACTORS']['logical_digest']}`.
- Period artifact SHA `{EXACT_EXPECTED['PERIOD_ASOF']['artifact_sha256']}`.
- Market Reference one-session output digest `{EXACT_EXPECTED['MARKET_REFERENCE']['one_session_output_digest']}`; ledger source digest uses canonical R4.1 JSON identity.
- PostgreSQL consumed-source evidence reports `old_r4_binding_count={exact['old_r4_binding_count']}` and `all_exact_bindings_match={str(exact['all_exact_bindings_match']).lower()}`.
- State head and publication head both bind Core Profile logical digest `{exact['actual_postgresql']['state_head']['logical_digest']}`.

## Regression and runtime

An automated regression test asserts that the G08 baseline source manifest refers only to R4.1 receipts/artifacts. A fresh clone of `{clean['implementation_commit']}` restored the required R4.1 LFS artifacts, passed the exact-binding test, ran PostgreSQL 18.6 with 12 formal migrations and I01–I05, and completed the required pytest suite: `{runtime['full_required_pytest_suite']['summary']}`.

## Candidate boundary

R4.1 business values and B05 remain frozen. The current forward capability remains `DEGRADED_PASS`; historical as-recorded adjusted price remains blocked for missing first-availability evidence. No V4-05 Accepted Head was created or modified, and V4-06/V4-07 were not started. The next stage is independent external audit for R4.2.

See `V4_05_R4_2_EXACT_CANDIDATE_LEDGER_BINDING.json`, `V4_05_R4_2_RUNTIME_TEST_RECEIPT.json`, `V4_05_R4_2_CLEAN_CHECKOUT_RUNTIME.json`, and `V4_05_R4_2_INDEPENDENT_POSTCHECK.json` for detailed evidence.
"""
    atomic_text(REPORT / "V4_05_R4_2_CLOSURE.md", closure)

    evidence_paths = (
        R4_1_MANIFEST, PG_REPORT, CLEAN_REPORT, R4_DIFF,
        "reports/v4_05/V4_05_R4_2_EXACT_CANDIDATE_LEDGER_BINDING.json",
        "reports/v4_05/V4_05_R4_2_RUNTIME_TEST_RECEIPT.json",
        "reports/v4_05/V4_05_R4_2_INDEPENDENT_POSTCHECK.json",
        "reports/v4_05/V4_05_R4_2_STAGE_ENTRY.md",
        "reports/v4_05/V4_05_R4_2_CLOSURE.md",
        "docs/evidence/V4_05_REPLAY_GATE_A_R4_2_EXACT_LEDGER_BINDING_TASK_20260929.md",
        "docs/evidence/V4_05_REPLAY_GATE_A_R4_1_EXTERNAL_AUDIT_20260929.md",
        "scripts/run_v4_05_r4_1_postgres_ledger.py",
        "scripts/run_v4_05_r4_2_clean_checkout_runtime.py",
        "scripts/build_v4_05_r4_2_closure_evidence.py",
        "tests/v4_05/test_v4_05_r4_2_exact_candidate_binding.py",
    )
    manifest = {
        "contract_id": "V4_05_R4_2_STAGE_CANDIDATE_MANIFEST_V1",
        "status": CANDIDATE if overall else "BLOCKED_R4_2_POSTCHECK_FAILURE",
        "external_acceptance": "PENDING", "starting_head": start,
        "implementation_commit": clean["implementation_commit"], "assembled_on_head": current_head,
        "candidate_manifest_path": R4_1_MANIFEST, "candidate_manifest_sha256": manifest_sha,
        "all_exact_bindings_match": exact["all_exact_bindings_match"],
        "old_r4_binding_count": exact["old_r4_binding_count"],
        "artifact_and_evidence_hashes": {path: file_identity(ROOT / path) for path in evidence_paths},
        "manifest_self_hash_omitted": True,
        "business_state": {"current_forward_stock_core": "DEGRADED_PASS",
                           "historical_as_recorded_adjusted_price": "BLOCKED_NO_FIRST_AVAILABILITY_EVIDENCE",
                           **postcheck["business_freeze"]},
        "accepted_head_discipline": {"v4_05_accepted_head_created": False,
                                     "protected_heads_unchanged": head_discipline,
                                     "v4_06_or_v4_07_started": False},
        "stage_record": {"stage_contract": STAGE,
                         "acceptance_result": "PASS_CANDIDATE_PENDING_EXTERNAL_AUDIT" if overall else "FAIL",
                         "evidence": "Exact R4.1 source binding in the formal PostgreSQL ledger, fresh-clone runtime suite, and independent head/business postcheck.",
                         "next_stage": "INDEPENDENT_EXTERNAL_AUDIT_R4_2"},
    }
    atomic_json(REPORT / "V4_05_R4_2_STAGE_CANDIDATE_MANIFEST.json", manifest)
    if not overall:
        raise RuntimeError("R4.2 independent postcheck failed")
    return {"status": "PASS", "candidate": CANDIDATE,
            "exact_bindings": exact["all_exact_bindings_match"],
            "old_r4_binding_count": exact["old_r4_binding_count"],
            "runtime": runtime["full_required_pytest_suite"]["summary"],
            "external_acceptance": "PENDING", "manifest_items": len(evidence_paths)}


if __name__ == "__main__":
    print(json.dumps(build(), ensure_ascii=False, sort_keys=True))
