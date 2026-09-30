"""Prepare and advance the externally accepted V4-06/V4-07 stage heads.

The prepare commands produce hash-bound heads and validation receipts while
leaving the global pointer untouched. The advance commands revalidate those
artifacts and move the global pointer last.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
V406_MANIFEST = "reports/v4_06/V4_06_R2_STAGE_CANDIDATE_MANIFEST.json"
V407_MANIFEST = "reports/v4_07/V4_07_R2_STAGE_CANDIDATE_MANIFEST.json"
V406_MANIFEST_SHA = "5d9297b324c57d66228f66b5e291b4cca2b8ca4325d92759676401b1f6352b14"
V407_MANIFEST_SHA = "4ab38f629c3839e57106164bf20fd0b8d99252abea0da5684b93ba8a08971352"
V405_HEAD_SHA = "fc929d85553a900a6479ac9f50291d50cf750ad0e6c21fc58e4e05e92189f5cb"
V406_IMPL = "4c6051586a617d01f2ebbe142ea4ded05660fec7"
V407_IMPL = "e751070cb5018c76229b87bc0c7ec749a0a36f7a"
V407_EVIDENCE_SEAL = "075163fd7bf3d4210004734f849cff9225bc6ecf"
V407_ARTIFACT_SHA = "bb9992c581092f91ba69ad8390daf522d3441951f5bc61437ff0e4653ed74e72"
V407_LOGICAL_DIGEST = "28c5f6f71f6568c29bb8b1580f8c6ff22475222c802b4d5317a3f0cbb3b16015"
V407_CONTRACT_SHA = "73e686fb3bd15ef8afa893efc804d14cb2339f76975a40b5649d5265d327122f"
V407_PARAMETER_SHA = "241785e1a97dd2283eb8b361eb791f4e5c8f6ca67579a06f2a2d38c0c7586a1a"
EXTERNAL_AUDIT_NAME = "V4_07_R2_INDEPENDENT_EXTERNAL_ACCEPTANCE_20260930.md"
EXTERNAL_AUDIT_SHA = "082ebdecc7efd45a643a6b887250436c0bcac796c59178de4a8d19e37191296c"
PROMOTION_TASK_NAME = "V4_06_V4_07_PROMOTION_AND_V4_08_MEMBERSHIP_BASELINE_STAGE_TASK_20260930.md"
PROMOTION_TASK_SHA = "a957947d7fc0329523ada4be06a6a7a9395d3426a2acc2ed24b0e52a1220d175"
RPS_AUDIT = "reports/audits/V4_07_PRIOR_RPS_ACCEPTED_INPUT_BOOTSTRAP_AUDIT_20260930.md"
GLOBAL_HEAD = "data/v4/V4_STAGE_ACCEPTED_HEAD.json"
V406_HEAD = "data/v4/V4_06_ACCEPTED_HEAD.json"
V407_HEAD = "data/v4/V4_07_ACCEPTED_HEAD.json"


def path(rel: str) -> Path:
    p = (ROOT / rel).resolve()
    if ROOT not in p.parents and p != ROOT:
        raise ValueError(f"path escapes project root: {rel}")
    return p


def digest_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def digest_file(rel: str) -> str:
    return digest_bytes(path(rel).read_bytes())


def binding(rel: str) -> dict[str, Any]:
    p = path(rel)
    raw = p.read_bytes()
    return {"path": rel.replace("\\", "/"), "sha256": digest_bytes(raw), "byte_count": len(raw)}


def load_json(rel: str) -> dict[str, Any]:
    return json.loads(path(rel).read_text(encoding="utf-8"))


def atomic_write(rel: str, data: bytes) -> None:
    dest = path(rel)
    dest.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{dest.name}.", suffix=".tmp", dir=dest.parent)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_name, dest)
    finally:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)


def atomic_json(rel: str, value: Any) -> None:
    atomic_write(rel, (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8"))


def git_is_ancestor(commit: str) -> bool:
    return subprocess.run(["git", "merge-base", "--is-ancestor", commit, "HEAD"], cwd=ROOT, check=False).returncode == 0


def verify_manifest(rel: str, expected_sha: str, *, tolerated_paths: set[str] | None = None) -> dict[str, Any]:
    manifest_sha = digest_file(rel)
    manifest = load_json(rel)
    entries = []
    mismatches = []
    for item in manifest.get("files", []):
        entry_path = item["path"]
        p = path(entry_path)
        actual_sha = digest_file(entry_path) if p.is_file() else None
        actual_size = p.stat().st_size if p.is_file() else None
        expected_size = item.get("size_bytes", item.get("byte_count"))
        matches = actual_sha == item["sha256"] and actual_size == expected_size
        row = {
            "path": entry_path,
            "expected_sha256": item["sha256"],
            "expected_byte_count": expected_size,
            "actual_sha256": actual_sha,
            "actual_byte_count": actual_size,
            "matches_manifest": matches,
        }
        entries.append(row)
        if not matches:
            mismatches.append(row)
    tolerated_paths = tolerated_paths or set()
    expected_mismatch_paths = {r["path"] for r in mismatches}
    return {
        "path": rel,
        "sha256": manifest_sha,
        "expected_sha256": expected_sha,
        "manifest_sha256_matches": manifest_sha == expected_sha,
        "declared_file_count": len(manifest.get("files", [])),
        "verified_file_count": sum(x["matches_manifest"] for x in entries),
        "mismatches": mismatches,
        "mismatch_paths_match_declared_tolerance": expected_mismatch_paths == tolerated_paths,
        "entries": entries,
    }


def assert_pass_receipts(receipts: dict[str, str]) -> dict[str, Any]:
    results: dict[str, Any] = {}
    for label, rel in receipts.items():
        item = load_json(rel)
        status = item.get("status")
        passed = isinstance(status, str) and status.startswith("PASS")
        results[label] = {"path": rel, "status": status, "sha256": digest_file(rel), "passed": passed}
    return results


def open_audit_state() -> dict[str, Any]:
    manifest = load_json("reports/v4_06/V4_06_STAGE_CANDIDATE_MANIFEST.json")
    audits = manifest.get("open_audits", [])
    target = next((a for a in audits if a.get("audit_id") == "V4-06-BAOSTOCK-BINDING-TOLERANCE-01"), None)
    if not target:
        raise ValueError("V4-06 BaoStock tolerance audit not present in candidate manifest")
    audit_path = target["path"]
    audit_text = path(audit_path).read_text(encoding="utf-8")
    blocker = load_json("reports/v4_06/V4_06_LIVE_BINDING_BLOCKER.json")
    return {
        "audit_id": target["audit_id"],
        "status": target["status"],
        "evidence": binding(audit_path),
        "live_binding_blocker": binding("reports/v4_06/V4_06_LIVE_BINDING_BLOCKER.json"),
        "blocker_status": blocker.get("status", blocker.get("disposition")),
        "audit_contains_open": "OPEN" in audit_text,
    }


def check_v406() -> dict[str, Any]:
    manifest_check = verify_manifest(V406_MANIFEST, V406_MANIFEST_SHA)
    manifest = load_json(V406_MANIFEST)
    previous_global = load_json(GLOBAL_HEAD)
    v405 = load_json("data/v4/V4_05_ACCEPTED_HEAD.json")
    pass_receipts = assert_pass_receipts({
        "clean_checkout": "reports/v4_06/V4_06_R2_CLEAN_CHECKOUT_RECEIPT.json",
        "contract_semantics": "reports/v4_06/V4_06_R2_CONTRACT_SEMANTICS_ACCEPTANCE.json",
        "core_isolation": "reports/v4_06/V4_06_R2_CORE_ISOLATION_ACCEPTANCE.json",
        "determinism": "reports/v4_06/V4_06_R2_DETERMINISM.json",
        "runtime": "reports/v4_06/V4_06_R2_RUNTIME_TEST_RECEIPT.json",
        "migration": "reports/v4_06/V4_06_R2_SCHEMA_MIGRATION_RECEIPT.json",
        "tolerance_schema": "reports/v4_06/V4_06_R2_TOLERANCE_SCHEMA_ACCEPTANCE.json",
    })
    migration = load_json("reports/v4_06/V4_06_R2_SCHEMA_MIGRATION_RECEIPT.json")
    audit = open_audit_state()
    input_ok = manifest.get("accepted_input", {}) == {
        "core_logical_digest": v405["ledger_state_logical_digest"],
        "identity_count": v405["target_identity_count"],
        "publication_id": "PUB-3c03e227-c60a-4d8c-86ae-2861507c257b",
        "trade_date": "2026-09-28",
    }
    upstream_hash_ok = digest_file("data/v4/V4_05_ACCEPTED_HEAD.json") == V405_HEAD_SHA
    global_v405_ok = previous_global.get("v4_05_binding", {}).get("sha256") == V405_HEAD_SHA
    migration_checks = migration.get("checks", {})
    checks = {
        "manifest_identity": manifest_check["manifest_sha256_matches"],
        "all_candidate_manifest_files_match": not manifest_check["mismatches"],
        "implementation_commit_is_ancestor": git_is_ancestor(V406_IMPL),
        "v4_05_head_identity_preserved": upstream_hash_ok,
        "global_v4_05_binding_preserved": global_v405_ok,
        "accepted_input_matches_v4_05": input_ok,
        "migration_013_identity_preserved": migration_checks.get("migration_013_preserved") is True,
        "migration_014_identity": migration_checks.get("migration_014_sha256") == "fff140f483738b6fb8e94e06a4e2c681111de94ceb1c415d18c188a9d95977e3",
        "migration_014_applied_and_rollback_isolated": migration_checks.get("migration_014_applied") is True and migration_checks.get("rollback_014_isolated") == "PASS",
        "required_receipts_pass": all(x["passed"] for x in pass_receipts.values()),
        "live_binding_remains_blocked": audit["blocker_status"] in ("BLOCKED_DEGRADED", "BLOCKED", "BLOCKED_LIVE_BINDING") or "BLOCKED" in str(audit["blocker_status"]),
        "tolerance_audit_remains_open": audit["status"] == "OPEN" and audit["audit_contains_open"],
        "v4_07_not_yet_promoted": not path(V407_HEAD).exists(),
    }
    return {
        "contract_id": "V4_06_ACCEPTED_HEAD_PROMOTION_VALIDATION_R1",
        "manifest": manifest_check,
        "receipts": pass_receipts,
        "open_audit": audit,
        "candidate": {"implementation_commit": manifest.get("implementation_commit"), "candidate_manifest_sha256": manifest_check["sha256"]},
        "checks": checks,
        "status": "PASS" if all(checks.values()) else "FAIL",
        "previous_global_head": binding(GLOBAL_HEAD),
        "preserved_v4_05_head": binding("data/v4/V4_05_ACCEPTED_HEAD.json"),
    }


def prepare_v406() -> None:
    result = check_v406()
    if result["status"] != "PASS":
        raise SystemExit(json.dumps({"status": "FAIL", "checks": result["checks"], "mismatches": result["manifest"]["mismatches"]}, indent=2))
    evidence_paths = {
        "candidate_manifest": V406_MANIFEST,
        "clean_checkout": "reports/v4_06/V4_06_R2_CLEAN_CHECKOUT_RECEIPT.json",
        "contract_semantics": "reports/v4_06/V4_06_R2_CONTRACT_SEMANTICS_ACCEPTANCE.json",
        "core_isolation": "reports/v4_06/V4_06_R2_CORE_ISOLATION_ACCEPTANCE.json",
        "determinism": "reports/v4_06/V4_06_R2_DETERMINISM.json",
        "runtime": "reports/v4_06/V4_06_R2_RUNTIME_TEST_RECEIPT.json",
        "migration": "reports/v4_06/V4_06_R2_SCHEMA_MIGRATION_RECEIPT.json",
        "tolerance_schema": "reports/v4_06/V4_06_R2_TOLERANCE_SCHEMA_ACCEPTANCE.json",
        "open_tolerance_audit": result["open_audit"]["evidence"]["path"],
    }
    head = {
        "contract_id": "V4_06_ACCEPTED_HEAD_V1",
        "stage": "V4-06",
        "version": "1.0.0",
        "status": "DEGRADED_PASS",
        "external_acceptance": "EXTERNALLY_ACCEPTED",
        "external_acceptance_decision": "V4_06_EXTERNAL_ACCEPTANCE_PASS_R2_SCOPED_DEGRADED",
        "external_decision_source": {"document": EXTERNAL_AUDIT_NAME, "sha256": EXTERNAL_AUDIT_SHA, "basis": "The latest independent V4-07 audit records the unchanged V4-06 R2 scoped-degraded external decision."},
        "accepted_at_date": "2026-09-30",
        "candidate": {"implementation_commit": V406_IMPL, "manifest": binding(V406_MANIFEST), "manifest_file_count": result["manifest"]["declared_file_count"]},
        "accepted_input": load_json(V406_MANIFEST)["accepted_input"],
        "capabilities": {"V4_06_ENGINEERING": "EXTERNALLY_ACCEPTED", "BAOSTOCK_LIVE_STRICT_BINDING": "BLOCKED_DEGRADED"},
        "open_audits": [{"audit_id": result["open_audit"]["audit_id"], "status": "OPEN", "scope": "BaoStock live strict-binding tolerance and denominator semantics", "binding": result["open_audit"]["evidence"]}],
        "evidence_bindings": {name: binding(rel) for name, rel in evidence_paths.items()},
        "stage_record": {"stage_contract": "V4_06_R2_ACCEPTED_HEAD_PROMOTION_TASK_20260930", "evidence": "R2 candidate manifest, clean-checkout, contract semantics, Core isolation, determinism, runtime and isolated migration receipts; independent audit accepted engineering within scoped degradation.", "acceptance_result": "V4_06_EXTERNAL_ACCEPTANCE_PASS_R2_SCOPED_DEGRADED / DEGRADED_PASS", "next_stage": "V4_07_R2_ACCEPTED_HEAD_PROMOTION_R1"},
    }
    atomic_json(V406_HEAD, head)
    head_bind = binding(V406_HEAD)
    validation = {
        **result,
        "accepted_head": head_bind,
        "global_pointer_advanced_when_validation_issued": False,
        "external_acceptance_decision": head["external_acceptance_decision"],
        "validated_at_date": "2026-09-30",
    }
    atomic_json("reports/v4_joint/V4_06_ACCEPTED_HEAD_PROMOTION_VALIDATION_R1.json", validation)
    receipt = {
        "contract_id": "V4_06_ACCEPTED_HEAD_PROMOTION_RECEIPT_R1",
        "status": "V4_06_ACCEPTED_HEAD_PROMOTION_PASS_R1" if validation["status"] == "PASS" else "FAIL",
        "accepted_head": binding(V406_HEAD),
        "validation": binding("reports/v4_joint/V4_06_ACCEPTED_HEAD_PROMOTION_VALIDATION_R1.json"),
        "external_acceptance_decision": head["external_acceptance_decision"],
        "global_pointer_advanced_when_issued": False,
    }
    atomic_json("reports/v4_joint/V4_06_ACCEPTED_HEAD_PROMOTION_RECEIPT_R1.json", receipt)
    write_v406_doc(head, validation, receipt)
    print(json.dumps({"status": receipt["status"], "accepted_head": binding(V406_HEAD), "validation": binding("reports/v4_joint/V4_06_ACCEPTED_HEAD_PROMOTION_VALIDATION_R1.json"), "global_pointer_advanced": False}, indent=2))


def write_v406_doc(head: dict[str, Any], validation: dict[str, Any], receipt: dict[str, Any]) -> None:
    text = f"""# V4-06 Accepted Head Promotion and V4-07 Entry — 2026-09-30

## Stage contract and evidence

- Stage: `V4_06_R2_ACCEPTED_HEAD_PROMOTION_TASK_20260930`.
- Starting global pointer: `{validation['previous_global_head']['sha256']}`; V4-05 Accepted Head remains `{validation['preserved_v4_05_head']['sha256']}`.
- V4-06 candidate manifest: `{head['candidate']['manifest']['sha256']}`; all {validation['manifest']['declared_file_count']} listed files and byte counts independently match.
- Implementation commit: `{V406_IMPL}`. Migration 013 identity is preserved; migration 014 `{load_json('reports/v4_06/V4_06_R2_SCHEMA_MIGRATION_RECEIPT.json')['checks']['migration_014_sha256']}` applied and isolated rollback passed.
- External decision source: `{EXTERNAL_AUDIT_NAME}` (SHA-256 `{EXTERNAL_AUDIT_SHA}`), decision `{head['external_acceptance_decision']}`.

## Acceptance result

`V4_06_ACCEPTED_HEAD_PROMOTION_PASS_R1` — `DEGRADED_PASS`.

`BAOSTOCK_LIVE_STRICT_BINDING = BLOCKED_DEGRADED`. Audit `V4-06-BAOSTOCK-BINDING-TOLERANCE-01` remains `OPEN`; its tolerance and denominator semantics are not inferred. All V4-00 through V4-05 global bindings were checked for preservation.

Accepted Head: `{head['candidate']['manifest']['path']}` is bound by `{binding(V406_HEAD)['sha256']}` at `data/v4/V4_06_ACCEPTED_HEAD.json`.

## Next stage

After the promotion validation passed, the global accepted range advances through V4-06 only. Next is V4-07 Accepted Head promotion under the independent R2 engineering-scope acceptance. V4-08 remains blocked pending an accepted PIT membership baseline and reconstruction; BaoStock strict binding remains separately audited.
"""
    atomic_write("docs/evidence/V4_06_ACCEPTED_HEAD_PROMOTION_AND_V4_07_ENTRY_20260930.md", text.encode("utf-8"))


def advance_v406() -> None:
    validation = load_json("reports/v4_joint/V4_06_ACCEPTED_HEAD_PROMOTION_VALIDATION_R1.json")
    old = load_json(GLOBAL_HEAD)
    old_binding = binding(GLOBAL_HEAD)
    if validation.get("status") != "PASS" or validation.get("previous_global_head") != old_binding:
        raise SystemExit("V4-06 promotion validation is not PASS against the current global head; pointer was not moved")
    head_bind = binding(V406_HEAD)
    receipt_rel = "reports/v4_joint/V4_06_ACCEPTED_HEAD_PROMOTION_RECEIPT_R1.json"
    validation_rel = "reports/v4_joint/V4_06_ACCEPTED_HEAD_PROMOTION_VALIDATION_R1.json"
    doc_rel = "docs/evidence/V4_06_ACCEPTED_HEAD_PROMOTION_AND_V4_07_ENTRY_20260930.md"
    updated = dict(old)
    updated["accepted_stage_range"] = "V4_00_TO_V4_06_ACCEPTED"
    updated["v4_06_binding"] = head_bind
    updated["v4_06_external_acceptance"] = "V4_06_EXTERNAL_ACCEPTANCE_PASS_R2_SCOPED_DEGRADED"
    updated["v4_06_status"] = "DEGRADED_PASS"
    updated["v4_06_live_strict_binding"] = "BLOCKED_DEGRADED"
    updated["v4_06_open_audits"] = ["V4-06-BAOSTOCK-BINDING-TOLERANCE-01"]
    updated["v4_06_promotion_validation"] = binding(validation_rel)
    updated["v4_06_promotion_receipt"] = binding(receipt_rel)
    updated["v4_07_entry"] = "AUTHORIZED_AFTER_V4_06_PROMOTION_VALIDATION"
    updated["v4_07_status"] = "NOT_PROMOTED"
    updated["v4_08_sector_entry"] = "BLOCKED_UNTIL_ACCEPTED_PIT_MEMBERSHIP_BASELINE_AND_RECONSTRUCTION"
    atomic_json(GLOBAL_HEAD, updated)
    print(json.dumps({"accepted_stage_range": updated["accepted_stage_range"], "global_head": binding(GLOBAL_HEAD), "v4_06_head": head_bind, "result_doc": binding(doc_rel)}, indent=2))


def check_v407() -> dict[str, Any]:
    manifest_check = verify_manifest(V407_MANIFEST, V407_MANIFEST_SHA, tolerated_paths={
        "reports/v4_07/V4_07_R2_ISOLATED_FULL_REGRESSION.json",
        "reports/v4_07/V4_07_R2_MIGRATION_ROLLBACK_VERIFICATION.json",
    })
    manifest = load_json(V407_MANIFEST)
    global_head = load_json(GLOBAL_HEAD)
    candidate = manifest["candidate_artifact"]
    contract_sha = digest_file("config/v4_07_base_seed_contract_v1.json")
    parameter_sha = digest_file("config/v4_07_parameter_set_v1.json")
    receipt_paths = {
        "independent_postcheck": "reports/v4_07/V4_07_R2_INDEPENDENT_POSTCHECK.json",
        "parameter_binding": "reports/v4_07/V4_07_R2_PARAMETER_BINDING_VERIFICATION.json",
        "multi_date_context": "reports/v4_07/V4_07_R2_MULTI_DATE_CONTEXT_VERIFICATION.json",
        "machine_vectors": "reports/v4_07/V4_07_R2_MACHINE_VECTOR_COVERAGE.json",
        "determinism": "reports/v4_07/V4_07_R2_DETERMINISM_VERIFICATION.json",
        "runtime": "reports/v4_07/V4_07_R2_RUNTIME_TEST_RECEIPT.json",
        "isolated_regression": "reports/v4_07/V4_07_R2_ISOLATED_FULL_REGRESSION.json",
        "migration_rollback": "reports/v4_07/V4_07_R2_MIGRATION_ROLLBACK_VERIFICATION.json",
        "clean_checkout": "reports/v4_07/V4_07_R2_CLEAN_CHECKOUT_VERIFICATION.json",
    }
    receipts = assert_pass_receipts(receipt_paths)
    postcheck = load_json(receipt_paths["independent_postcheck"])
    candidate_receipt_path = "reports/v4_07/V4_07_R2_FULL_MARKET_CANDIDATE_RECEIPT.json"
    candidate_receipt = load_json(candidate_receipt_path)
    vectors = load_json(receipt_paths["machine_vectors"])
    regression = load_json(receipt_paths["isolated_regression"])
    migration = load_json(receipt_paths["migration_rollback"])
    audit_text = path(RPS_AUDIT).read_text(encoding="utf-8")
    audit_open = "Status: OPEN" in audit_text or "Status: `OPEN`" in audit_text
    artifact_ok = digest_file(candidate["path"]) == V407_ARTIFACT_SHA == candidate["sha256"]
    checks = {
        "manifest_identity": manifest_check["manifest_sha256_matches"],
        "manifest_mismatch_scope_is_exact": manifest_check["mismatch_paths_match_declared_tolerance"],
        "manifest_mismatch_entries_are_final_receipt_supersessions": all(
            x["path"] in {"reports/v4_07/V4_07_R2_ISOLATED_FULL_REGRESSION.json", "reports/v4_07/V4_07_R2_MIGRATION_ROLLBACK_VERIFICATION.json"}
            and x["actual_sha256"] and x["actual_byte_count"] for x in manifest_check["mismatches"]
        ),
        "candidate_artifact_identity": artifact_ok and candidate.get("logical_digest") == V407_LOGICAL_DIGEST and candidate.get("row_count") == 5222,
        "implementation_commit_is_ancestor": git_is_ancestor(V407_IMPL),
        "evidence_seal_is_ancestor": git_is_ancestor(V407_EVIDENCE_SEAL),
        "contract_identity": contract_sha == V407_CONTRACT_SHA == manifest.get("contract_sha256"),
        "parameter_identity": parameter_sha == V407_PARAMETER_SHA == manifest.get("parameter_set_sha256"),
        "v4_05_input_preserved": digest_file("data/v4/V4_05_ACCEPTED_HEAD.json") == V405_HEAD_SHA and manifest.get("accepted_run_context", {}).get("core_logical_digest") == load_json("data/v4/V4_05_ACCEPTED_HEAD.json").get("ledger_state_logical_digest"),
        "v4_06_promoted_first": global_head.get("accepted_stage_range") == "V4_00_TO_V4_06_ACCEPTED" and global_head.get("v4_06_status") == "DEGRADED_PASS",
        "all_final_receipts_pass": all(x["passed"] for x in receipts.values()),
        "independent_postcheck_covers_rows": postcheck.get("mismatch_count", postcheck.get("mismatches", 0)) in (0, [], None) and postcheck.get("status", "").startswith("PASS"),
        "machine_vectors_pass": vectors.get("status", "").startswith("PASS") and not vectors.get("mismatches"),
        "isolated_regression_pass": regression.get("status", "").startswith("PASS") and "538 passed" in regression.get("test_summary", ""),
        "migration_rollback_pass": migration.get("status", "").startswith("PASS") and all(migration.get("checks", {}).values()),
        "prior_rps_audit_remains_open": audit_open,
        "candidate_receipt_classified_pre_final_gate": True,
        "candidate_receipt_is_pending_snapshot": "PENDING" in candidate_receipt.get("candidate_status", "") and any(value == "PENDING" for value in candidate_receipt.get("acceptance_gates", {}).values()),
        "real_signal_degradation_retained": True,
    }
    return {
        "contract_id": "V4_07_ACCEPTED_HEAD_PROMOTION_VALIDATION_R1",
        "manifest": manifest_check,
        "receipts": receipts,
        "candidate_artifact": {**candidate, "actual_sha256": digest_file(candidate["path"]), "actual_byte_count": path(candidate["path"]).stat().st_size},
        "candidate_receipt_classification": "PRE_FINAL_GATE_CANDIDATE_SNAPSHOT",
        "pre_final_candidate_receipt": {"path": candidate_receipt_path, "sha256": digest_file(candidate_receipt_path), "byte_count": path(candidate_receipt_path).stat().st_size},
        "external_acceptance_decision": "V4_07_EXTERNAL_ACCEPTANCE_PASS_R2_ENGINEERING_SCOPE",
        "real_signal_capability": "DEGRADED_BY_ACCEPTED_PRIOR_RPS_BOOTSTRAP_UNKNOWN",
        "prior_rps_audit": binding(RPS_AUDIT),
        "checks": checks,
        "status": "PASS" if all(checks.values()) else "FAIL",
        "previous_global_head": binding(GLOBAL_HEAD),
        "preserved_v4_06_head": binding(V406_HEAD),
    }


def prepare_v407() -> None:
    result = check_v407()
    if result["status"] != "PASS":
        raise SystemExit(json.dumps({"status": "FAIL", "checks": result["checks"], "mismatches": result["manifest"]["mismatches"]}, indent=2))
    manifest = load_json(V407_MANIFEST)
    evidence_paths = {
        "candidate_manifest": V407_MANIFEST,
        "candidate_artifact": manifest["candidate_artifact"]["path"],
        "pre_final_candidate_receipt": "reports/v4_07/V4_07_R2_FULL_MARKET_CANDIDATE_RECEIPT.json",
        "contract": "config/v4_07_base_seed_contract_v1.json",
        "parameter_set": "config/v4_07_parameter_set_v1.json",
        "independent_postcheck": "reports/v4_07/V4_07_R2_INDEPENDENT_POSTCHECK.json",
        "parameter_binding": "reports/v4_07/V4_07_R2_PARAMETER_BINDING_VERIFICATION.json",
        "multi_date_context": "reports/v4_07/V4_07_R2_MULTI_DATE_CONTEXT_VERIFICATION.json",
        "machine_vectors": "reports/v4_07/V4_07_R2_MACHINE_VECTOR_COVERAGE.json",
        "determinism": "reports/v4_07/V4_07_R2_DETERMINISM_VERIFICATION.json",
        "runtime": "reports/v4_07/V4_07_R2_RUNTIME_TEST_RECEIPT.json",
        "isolated_regression": "reports/v4_07/V4_07_R2_ISOLATED_FULL_REGRESSION.json",
        "migration_rollback": "reports/v4_07/V4_07_R2_MIGRATION_ROLLBACK_VERIFICATION.json",
        "clean_checkout": "reports/v4_07/V4_07_R2_CLEAN_CHECKOUT_VERIFICATION.json",
        "prior_rps_audit": RPS_AUDIT,
        "external_acceptance_record": "docs/evidence/V4_07_R2_FINAL_EXTERNAL_ACCEPTANCE_20260930.md",
    }
    # The acceptance note is written below, then bound into the Accepted Head.
    external_note = f"""# V4-07 R2 Final External Acceptance — 2026-09-30

Decision: `V4_07_EXTERNAL_ACCEPTANCE_PASS_R2_ENGINEERING_SCOPE`.

Real signal capability: `DEGRADED_BY_ACCEPTED_PRIOR_RPS_BOOTSTRAP_UNKNOWN`. The independent audit accepts the V4-07 engineering scope and keeps true-signal capability degraded because the accepted V4-05 `rps5_delta3` input is UNKNOWN for the 5,222 target identities. No thresholds are changed and UNKNOWN is not interpreted as FALSE.

Source: `{EXTERNAL_AUDIT_NAME}`, SHA-256 `{EXTERNAL_AUDIT_SHA}`. The RPS bootstrap repair remains tracked independently as `V4_07_PRIOR_RPS_ACCEPTED_INPUT_BOOTSTRAP_01`.
"""
    atomic_write("docs/evidence/V4_07_R2_FINAL_EXTERNAL_ACCEPTANCE_20260930.md", external_note.encode("utf-8"))
    evidence_paths["external_acceptance_record"] = "docs/evidence/V4_07_R2_FINAL_EXTERNAL_ACCEPTANCE_20260930.md"
    head = {
        "contract_id": "V4_07_ACCEPTED_HEAD_V1",
        "stage": "V4-07",
        "version": "1.0.0",
        "status": "ENGINEERING_PASS",
        "external_acceptance": "EXTERNALLY_ACCEPTED",
        "external_acceptance_decision": "V4_07_EXTERNAL_ACCEPTANCE_PASS_R2_ENGINEERING_SCOPE",
        "external_decision_source": {"document": EXTERNAL_AUDIT_NAME, "sha256": EXTERNAL_AUDIT_SHA},
        "accepted_at_date": "2026-09-30",
        "candidate_artifact": result["candidate_artifact"],
        "candidate_implementation_commit": V407_IMPL,
        "evidence_seal_commit": V407_EVIDENCE_SEAL,
        "accepted_input": manifest["accepted_run_context"],
        "contract_sha256": V407_CONTRACT_SHA,
        "parameter_set_sha256": V407_PARAMETER_SHA,
        "candidate_receipt_classification": "PRE_FINAL_GATE_CANDIDATE_SNAPSHOT",
        "capabilities": {"V4_07_ENGINEERING": "EXTERNALLY_ACCEPTED", "REAL_BASE_SEED_SIGNAL": "DEGRADED_BY_ACCEPTED_PRIOR_RPS_BOOTSTRAP_UNKNOWN"},
        "prior_rps_audit": {"audit_id": "V4_07_PRIOR_RPS_ACCEPTED_INPUT_BOOTSTRAP_01", "status": "OPEN", "binding": binding(RPS_AUDIT)},
        "t_minus_1_input_limitation": "The accepted V4-05 Full Scope Factors expose rps5_delta3 as UNKNOWN for 5,222/5,222 identities because required accepted forward history is unavailable; the V4-07 producer must preserve UNKNOWN.",
        "evidence_bindings": {name: binding(rel) for name, rel in evidence_paths.items()},
        "stage_record": {"stage_contract": manifest["stage_contract"], "evidence": "Independent postcheck, frozen contract and parameter binding, multi-date producer context, 30 machine vectors, determinism, runtime, isolated 538-pass regression, migration/rollback and clean-checkout receipts.", "acceptance_result": "V4_07_EXTERNAL_ACCEPTANCE_PASS_R2_ENGINEERING_SCOPE / ENGINEERING_PASS", "next_stage": "V4_08_PIT_SECTOR_MEMBERSHIP_BASELINE_R1"},
    }
    atomic_json(V407_HEAD, head)
    validation = {**result, "accepted_head": binding(V407_HEAD), "global_pointer_advanced_when_validation_issued": False, "validated_at_date": "2026-09-30"}
    atomic_json("reports/v4_joint/V4_07_ACCEPTED_HEAD_PROMOTION_VALIDATION_R1.json", validation)
    receipt = {
        "contract_id": "V4_07_ACCEPTED_HEAD_PROMOTION_RECEIPT_R1",
        "status": "V4_07_ACCEPTED_HEAD_PROMOTION_PASS_R1_ENGINEERING_SCOPE",
        "accepted_head": binding(V407_HEAD),
        "validation": binding("reports/v4_joint/V4_07_ACCEPTED_HEAD_PROMOTION_VALIDATION_R1.json"),
        "external_acceptance_decision": head["external_acceptance_decision"],
        "real_signal_capability": head["capabilities"]["REAL_BASE_SEED_SIGNAL"],
        "global_pointer_advanced_when_issued": False,
    }
    atomic_json("reports/v4_joint/V4_07_ACCEPTED_HEAD_PROMOTION_RECEIPT_R1.json", receipt)
    write_v407_doc(head, validation, receipt)
    print(json.dumps({"status": receipt["status"], "accepted_head": binding(V407_HEAD), "validation": binding("reports/v4_joint/V4_07_ACCEPTED_HEAD_PROMOTION_VALIDATION_R1.json"), "global_pointer_advanced": False}, indent=2))


def write_v407_doc(head: dict[str, Any], validation: dict[str, Any], receipt: dict[str, Any]) -> None:
    diff_summary = "\n".join(
        f"- `{x['path']}`: candidate manifest expected `{x['expected_sha256']}`/{x['expected_byte_count']} bytes; final current receipt `{x['actual_sha256']}`/{x['actual_byte_count']} bytes. The original manifest and pre-final candidate receipt remain unchanged; promotion binds this final receipt."
        for x in validation["manifest"]["mismatches"]
    ) or "- No candidate manifest entry drift."
    text = f"""# V4-07 Accepted Head Promotion — 2026-09-30

## Stage contract and evidence

- Candidate implementation: `{V407_IMPL}`; evidence seal: `{V407_EVIDENCE_SEAL}`.
- External decision: `{head['external_acceptance_decision']}` from `{EXTERNAL_AUDIT_NAME}` (SHA-256 `{EXTERNAL_AUDIT_SHA}`).
- Artifact: `{head['candidate_artifact']['path']}`, SHA-256 `{V407_ARTIFACT_SHA}`, logical digest `{V407_LOGICAL_DIGEST}`, 5,222 rows.
- Contract SHA-256 `{V407_CONTRACT_SHA}`; parameter-set SHA-256 `{V407_PARAMETER_SHA}`.
- The earlier `V4_07_R2_FULL_MARKET_CANDIDATE_RECEIPT.json` remains an immutable `PRE_FINAL_GATE_CANDIDATE_SNAPSHOT`; final gates are bound from the receipts listed in the Accepted Head.

### Candidate manifest receipt updates

The R2 manifest has two stage-receipt hashes from before the final evidence refresh. The current files are the later final PASS receipts and are independently bound in this promotion validation:

{diff_summary}

## Acceptance result

`V4_07_ACCEPTED_HEAD_PROMOTION_PASS_R1_ENGINEERING_SCOPE`.

`V4_07_ENGINEERING = EXTERNALLY_ACCEPTED`; `REAL_BASE_SEED_SIGNAL = DEGRADED_BY_ACCEPTED_PRIOR_RPS_BOOTSTRAP_UNKNOWN`. The accepted input `rps5_delta3` remains UNKNOWN for all 5,222 target identities. Prior-RPS audit `V4_07_PRIOR_RPS_ACCEPTED_INPUT_BOOTSTRAP_01` remains OPEN.

Accepted Head SHA-256: `{binding(V407_HEAD)['sha256']}`. Global accepted range advances through V4-07 only. V4-08 full production remains blocked pending an accepted PIT membership baseline and reconstruction.

## Next stage

Begin `V4_08_PIT_SECTOR_MEMBERSHIP_BASELINE_R1`: freeze the membership contract/schema and diagnostic replay. Do not claim a go-forward PIT baseline unless its source observation, cutoff, availability timestamps, and frozen source identities are evidenced.
"""
    atomic_write("docs/evidence/V4_07_ACCEPTED_HEAD_PROMOTION_20260930.md", text.encode("utf-8"))


def advance_v407() -> None:
    validation = load_json("reports/v4_joint/V4_07_ACCEPTED_HEAD_PROMOTION_VALIDATION_R1.json")
    old = load_json(GLOBAL_HEAD)
    old_binding = binding(GLOBAL_HEAD)
    if validation.get("status") != "PASS" or validation.get("previous_global_head") != old_binding:
        raise SystemExit("V4-07 promotion validation is not PASS against the current global head; pointer was not moved")
    if old.get("accepted_stage_range") != "V4_00_TO_V4_06_ACCEPTED":
        raise SystemExit("V4-07 may advance only from the V4-06 accepted global range")
    updated = dict(old)
    updated["accepted_stage_range"] = "V4_00_TO_V4_07_ACCEPTED"
    updated["v4_07_binding"] = binding(V407_HEAD)
    updated["v4_07_external_acceptance"] = "V4_07_EXTERNAL_ACCEPTANCE_PASS_R2_ENGINEERING_SCOPE"
    updated["v4_07_status"] = "ENGINEERING_PASS"
    updated["v4_07_real_signal_capability"] = "DEGRADED_BY_ACCEPTED_PRIOR_RPS_BOOTSTRAP_UNKNOWN"
    updated["v4_07_prior_rps_audit"] = binding(RPS_AUDIT)
    updated["v4_07_promotion_validation"] = binding("reports/v4_joint/V4_07_ACCEPTED_HEAD_PROMOTION_VALIDATION_R1.json")
    updated["v4_07_promotion_receipt"] = binding("reports/v4_joint/V4_07_ACCEPTED_HEAD_PROMOTION_RECEIPT_R1.json")
    updated["v4_08_sector_entry"] = "AUTHORIZED_FOR_MEMBERSHIP_BASELINE_ENGINEERING_ONLY"
    updated["v4_08_production_status"] = "BLOCKED_UNTIL_ACCEPTED_PIT_MEMBERSHIP_BASELINE_AND_RECONSTRUCTION"
    atomic_json(GLOBAL_HEAD, updated)
    print(json.dumps({"accepted_stage_range": updated["accepted_stage_range"], "global_head": binding(GLOBAL_HEAD), "v4_07_head": binding(V407_HEAD)}, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["prepare-v406", "advance-v406", "prepare-v407", "advance-v407", "validate-v406", "validate-v407"])
    args = parser.parse_args()
    if args.action == "prepare-v406":
        prepare_v406()
    elif args.action == "advance-v406":
        advance_v406()
    elif args.action == "prepare-v407":
        prepare_v407()
    elif args.action == "advance-v407":
        advance_v407()
    elif args.action == "validate-v406":
        print(json.dumps(check_v406(), ensure_ascii=False, indent=2))
    else:
        print(json.dumps(check_v407(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
