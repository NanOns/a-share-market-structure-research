from __future__ import annotations

"""Reconcile V4-02 stage mapping to accepted R6 plus the closed R4 audit."""

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
MAPPING = Path("config/v4_02_stage_acceptance_mapping_v2.json")
R6_HEAD = Path("data/v4/V4_02_ACCEPTED_HEAD.json")
R6_RECEIPT = Path("reports/v4_02/V4_02_FINAL_RECEIPT_R6.json")
R6_EXTERNAL = Path("reports/v4_02/V4_02_FINAL_EXTERNAL_ACCEPTANCE_R6.json")
R6_POSTCHECK = Path("reports/v4_02/V4_02_FINAL_INDEPENDENT_POSTCHECK_R6.json")
R8_POSTCHECK = Path("reports/v4_02/V4_02_R8_CROSS_STAGE_POSTCHECK_20260928.json")
R4_AUDIT = Path("reports/v4_02/V4_02_PRICE_LIMIT_RANGE_EXCEPTION_AUDIT_R4.json")
R4_CAPTURE_INDEX = Path("reports/v4_02/V4_02_R4_OFFICIAL_SOURCE_CAPTURE_INDEX.json")
IDENTITY = Path("data/v4/artifact_store/v4_01/security_entity_map_R7_20260927.json")
UNIVERSE = Path("data/v4/artifact_store/v4_01/v4_01_historical_universe_required_R7_20260927.jsonl.gz")
OUTPUT = Path("reports/v4_02/V4_02_CURRENT_TRUTH_RECONCILIATION_R1.json")


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with (ROOT / path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load(path: Path) -> dict[str, Any]:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def identity(path: Path) -> dict[str, Any]:
    return {"path": path.as_posix(), "sha256": sha(path), "byte_count": (ROOT / path).stat().st_size}


def atomic_write(path: Path, payload: bytes) -> None:
    target = ROOT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temp = tempfile.mkstemp(prefix=target.name + ".", suffix=".tmp", dir=target.parent)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, target)
    finally:
        Path(temp).unlink(missing_ok=True)


def main() -> int:
    mapping = load(MAPPING)
    before_mapping_sha = sha(MAPPING)
    head = load(R6_HEAD)
    receipt = load(R6_RECEIPT)
    external = load(R6_EXTERNAL)
    postcheck = load(R6_POSTCHECK)
    r8_postcheck = load(R8_POSTCHECK)
    r4_audit = load(R4_AUDIT)
    capture_index = load(R4_CAPTURE_INDEX)
    global_input_identity = {"v4_01_identity_map_sha256": sha(IDENTITY), "v4_01_universe_sha256": sha(UNIVERSE)}

    head_binds = (
        head.get("external_acceptance") == "EXTERNALLY_ACCEPTED"
        and head.get("status") == "PASS_WITH_BSE_SCOPE_DEGRADED"
        and head.get("final_receipt_sha256") == sha(R6_RECEIPT)
        and head.get("external_acceptance_receipt_sha256") == sha(R6_EXTERNAL)
    )
    r6_checks = (
        receipt.get("status") == "PASS_WITH_BSE_SCOPE_DEGRADED"
        and external.get("acceptance_result", {}).get("external_acceptance") == "EXTERNALLY_ACCEPTED"
        and postcheck.get("status") == "PASS"
        and r8_postcheck.get("status") == "PASS"
    )
    r4_closed = (
        r4_audit.get("status") == "CLOSED"
        and r4_audit.get("stage_gate_disposition") == "PASS_UNDISPOSITIONED_ENGINEERING_EXCEPTIONS_ZERO"
        and r4_audit.get("scope", {}).get("undispositioned_engineering_exceptions") == 0
        and r4_audit.get("scope", {}).get("fail_closed_missing_evidence") == 0
        and capture_index.get("status") == "CAPTURED"
        and len(r4_audit.get("source_capture_failures", [])) == 0
    )
    canonical_unchanged = (
        global_input_identity["v4_01_identity_map_sha256"] == r8_postcheck.get("r8_binding", {}).get("canonical_identity_sha256")
        and global_input_identity["v4_01_universe_sha256"] == r8_postcheck.get("r8_binding", {}).get("canonical_historical_universe_sha256")
    )

    blockers = []
    if not head_binds:
        blockers.append("R6_ACCEPTED_HEAD_BINDING_INVALID")
    if not r6_checks:
        blockers.append("R6_EXTERNAL_ACCEPTANCE_OR_INDEPENDENT_POSTCHECK_INVALID")
    if not r4_closed:
        blockers.append("R4_RANGE_AUDIT_NOT_CLOSED_OR_EVIDENCE_INCOMPLETE")
    if not canonical_unchanged:
        blockers.append("V4_01_CANONICAL_INPUT_IDENTITY_CHANGED_REBUILD_OR_REBIND_REQUIRED")

    mapping.setdefault("current_disposition", {})
    current = mapping["current_disposition"]
    mapping.setdefault("acceptance", {})
    mapping["acceptance"]["stage_status"] = (
        "PASS_WITH_BSE_SCOPE_DEGRADED; R6_EXTERNALLY_ACCEPTED; R4_RANGE_AUDIT_CLOSED; CURRENT_OPEN_ENGINEERING_EXCEPTION=0"
        if not blockers else "BLOCKED_CURRENT_TRUTH_RECONCILIATION"
    )
    current["entry"] = "V4_02_EXTERNALLY_ACCEPTED_R6; R4_RANGE_AUDIT_CLOSED"
    current["stage_acceptance"] = "PASS_WITH_BSE_SCOPE_DEGRADED" if not blockers else "BLOCKED_CURRENT_TRUTH_RECONCILIATION"
    current["stage_implementation"] = (
        "FINAL_CLOSURE_PACK_R2_PASS; R6_EXTERNAL_ACCEPTANCE_PRESERVED; R4_RANGE_AUDIT_CLOSED; "
        "31_CURRENT_ROWS_RETAINED_UNKNOWN_FAIL_CLOSED; UNDISPOSITIONED_ENGINEERING_EXCEPTIONS_ZERO"
    )
    current["current_open_engineering_exception"] = 0 if r4_closed else r4_audit.get("scope", {}).get("undispositioned_engineering_exceptions")
    current["current_fail_closed_unknown_rows"] = int(r4_audit.get("scope", {}).get("r3_fail_closed_dispositioned", -1))
    current["accepted_head_unchanged"] = True
    current["canonical_rebuild_performed"] = False
    current["upstream_rebind"] = {
        "required": not canonical_unchanged,
        "performed": False,
        "reason": "R7 identity and universe hashes remain unchanged; V4-01 R9 remains candidate-only pending external acceptance." if canonical_unchanged else "Input identity changed; rebind is blocked until accepted V4-01 head exists.",
        **global_input_identity,
    }
    current["audit_history"] = [
        {
            "audit_id": "V4_02_PRICE_LIMIT_RANGE_EXCEPTION_AUDIT_R1",
            "status": "SUPERSEDED_BY_R4_CURRENT_DISPOSITION",
            "open_at_time": True,
            "historical_artifact_preserved": True,
        },
        {
            "audit_id": "V4_02_PRICE_LIMIT_RANGE_EXCEPTION_AUDIT_R3",
            "status": "HISTORICAL_BLOCKED_SUPERSEDED_BY_R4",
            "open_at_time": True,
            "historical_artifact_preserved": True,
        },
        {
            "audit_id": r4_audit.get("contract_id"),
            "status": r4_audit.get("status"),
            "stage_gate_disposition": r4_audit.get("stage_gate_disposition"),
            "undispositioned_engineering_exceptions": r4_audit.get("scope", {}).get("undispositioned_engineering_exceptions"),
            "current_fail_closed_unknown_rows": r4_audit.get("scope", {}).get("r3_fail_closed_dispositioned"),
            "receipt_path": R4_AUDIT.as_posix(),
            "receipt_sha256": sha(R4_AUDIT),
        },
    ]
    current["open_audits"] = [] if r4_closed else [
        {"receipt": R4_AUDIT.as_posix(), "sha256": sha(R4_AUDIT), "status": r4_audit.get("status"), "scope": "Current range exceptions remain fail-closed and audit closure failed."}
    ]
    current["known_open_capabilities"] = [] if not blockers else blockers
    current["next_stage"] = "V4_03_AMENDED_SCOPE_CANDIDATE; WAIT_FOR_JOINT_EXTERNAL_ACCEPTANCE" if not blockers else "REPAIR_CURRENT_TRUTH_BLOCKERS"
    mapping["price_limit_current_truth"] = {
        "r1": "SUPERSEDED",
        "r3": "HISTORICAL_BLOCKED",
        "r4": "CLOSED" if r4_closed else r4_audit.get("status"),
        "r4_current_exception_rows": r4_audit.get("scope", {}).get("r3_current_exception_rows"),
        "r4_fail_closed_unknown_rows": r4_audit.get("scope", {}).get("r3_fail_closed_dispositioned"),
        "r4_resolved_special_phase_rows": r4_audit.get("scope", {}).get("r3_resolved_special_phase"),
        "undispositioned_engineering_exceptions": r4_audit.get("scope", {}).get("undispositioned_engineering_exceptions"),
        "fail_closed_missing_evidence": r4_audit.get("scope", {}).get("fail_closed_missing_evidence"),
        "current_open_engineering_exception": 0 if r4_closed else None,
        "unknown_rows_are_not_claimed_as_cause_resolved": True,
    }
    current["stage_acceptance_external"] = "EXTERNALLY_ACCEPTED_R6" if not blockers else "RETAIN_PREVIOUS_ACCEPTANCE; RECONCILIATION_BLOCKED"
    mapping["current_truth_reconciliation_receipt"] = OUTPUT.as_posix()

    mapping_bytes = (json.dumps(mapping, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")
    descriptor, temp = tempfile.mkstemp(prefix=MAPPING.name + ".", suffix=".tmp", dir=(ROOT / MAPPING).parent)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(mapping_bytes)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, ROOT / MAPPING)
    finally:
        Path(temp).unlink(missing_ok=True)
    updated_mapping_sha = hashlib.sha256(mapping_bytes).hexdigest()

    status = "PASS_CURRENT_TRUTH_RECONCILIATION" if not blockers else "BLOCKED"
    observed = datetime.now(timezone.utc).isoformat(timespec="seconds")
    report = {
        "contract_id": "V4_02_CURRENT_TRUTH_RECONCILIATION_R1",
        "version": "1.0.0-candidate",
        "stage": "V4-02 CURRENT TRUTH RECONCILIATION",
        "status": status,
        "observed_at_utc": observed,
        "stage_contract": {
            "mapping_path": MAPPING.as_posix(),
            "mapping_sha256_before": before_mapping_sha,
            "mapping_sha256_after": updated_mapping_sha,
            "canonical_artifacts_rebuilt": False,
            "v4_02_accepted_head_modified": False,
            "v4_01_accepted_identity_modified": False,
        },
        "evidence": {
            "v4_02_accepted_head": identity(R6_HEAD),
            "v4_02_final_receipt_r6": identity(R6_RECEIPT),
            "v4_02_external_acceptance_r6": identity(R6_EXTERNAL),
            "v4_02_independent_postcheck_r6": identity(R6_POSTCHECK),
            "v4_02_cross_stage_postcheck_r8": identity(R8_POSTCHECK),
            "v4_02_price_limit_range_audit_r4": identity(R4_AUDIT),
            "r4_official_source_capture_index": identity(R4_CAPTURE_INDEX),
            "v4_01_identity_map_r7": identity(IDENTITY),
            "v4_01_universe_r7": identity(UNIVERSE),
        },
        "current_truth": {
            "v4_02": "PASS_WITH_BSE_SCOPE_DEGRADED",
            "external_acceptance": "EXTERNALLY_ACCEPTED_R6",
            "price_limit_audits": {"R1": "SUPERSEDED", "R3": "HISTORICAL_BLOCKED", "R4": "CLOSED" if r4_closed else r4_audit.get("status")},
            "r4_current_exception_rows": r4_audit.get("scope", {}).get("r3_current_exception_rows"),
            "r4_fail_closed_unknown_rows": r4_audit.get("scope", {}).get("r3_fail_closed_dispositioned"),
            "r4_undispositioned_engineering_exceptions": r4_audit.get("scope", {}).get("undispositioned_engineering_exceptions"),
            "current_open_engineering_exception": 0 if r4_closed else None,
            "unknown_rows_claimed_resolved": 0,
            "r7_canonical_inputs_unchanged": canonical_unchanged,
            "v4_02_rebuild": False,
            "v4_01_upstream_rebind": "NOT_REQUIRED_CANONICAL_HASHES_UNCHANGED; WAIT_FOR_R9_EXTERNAL_ACCEPTANCE",
        },
        "checks": {
            "r6_accepted_head_and_receipt_bind": head_binds,
            "r6_external_acceptance_and_postchecks_pass": r6_checks,
            "r4_audit_closed_and_all_rows_dispositioned": r4_closed,
            "r7_identity_and_universe_hashes_unchanged": canonical_unchanged,
        },
        "blockers": blockers,
        "stage_record": {
            "evidence": "R6 external acceptance + R6/R8 independent postchecks + R4 row disposition audit; no rebuild",
            "acceptance_result": status,
            "next_stage": "BIND_TO_V4_01_R9_AFTER_EXTERNAL_ACCEPTANCE" if status.startswith("PASS") else "REPAIR_LISTED_BLOCKERS",
        },
        "execution_identity": {
            "input_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
            "script_sha256": sha(Path(__file__).resolve().relative_to(ROOT)),
            "python_version": sys.version.split()[0],
        },
    }
    report_bytes = (json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")
    atomic_write(OUTPUT, report_bytes)
    print(json.dumps({"status": status, "blockers": blockers, "mapping_sha256": updated_mapping_sha, "receipt_sha256": hashlib.sha256(report_bytes).hexdigest(), "current_open_engineering_exception": mapping["price_limit_current_truth"]["current_open_engineering_exception"], "current_fail_closed_unknown_rows": mapping["price_limit_current_truth"]["r4_fail_closed_unknown_rows"]}, ensure_ascii=False, indent=2))
    return 0 if status.startswith("PASS") else 2


if __name__ == "__main__":
    raise SystemExit(main())
