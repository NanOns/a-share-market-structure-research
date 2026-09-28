from __future__ import annotations

"""Seal the R8.1 internal stage and joint 00/01/02 reseal receipts."""

import hashlib
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from workbench_analysis.daily_data_head import write_json_atomic  # noqa: E402

OUT_STAGE = Path("reports/v4_01/v4_01_final_stage_receipt_R8_1_20260928.json")
OUT_JOINT = Path("reports/v4_joint/V4_00_01_02_JOINT_FINAL_RECEIPT_R2_20260928.json")
OUT_REVIEW = Path("reports/v4_01/V4_01_R8_1_EXTERNAL_REVIEW_PACKAGE_R1_20260928.md")
TESTS = Path("reports/v4_joint/V4_R8_1_DM01_TEST_RECEIPT_R1_20260928.json")
EVENT = Path("reports/v4_01/V4_01_IDENTITY_EVENT_DISCOVERY_R8_1.json")
ALIAS = Path("reports/v4_01/V4_01_ALIAS_COMPLETENESS_R8_1.json")
POST = Path("reports/v4_01/V4_01_R8_1_INDEPENDENT_POSTCHECK_R1_20260928.json")
PHASE0 = Path("reports/v4_phase0/V4_PHASE0_FINAL_RECEIPT_R5_20260928.json")
R6_EXTERNAL = Path("reports/v4_02/V4_02_FINAL_EXTERNAL_ACCEPTANCE_R6.json")
R7_IDENTITY = Path("data/v4/artifact_store/v4_01/security_entity_map_R7_20260927.json")
R7_UNIVERSE = Path("data/v4/artifact_store/v4_01/v4_01_historical_universe_required_R7_20260927.jsonl.gz")
TASK_CARD = Path("docs/evidence/V4_R8_1_DM01_IMPLEMENTATION_PACK_R1_20260928.md")
REAUDIT = Path("docs/evidence/V4_PRE03_JOINT_R1_EXTERNAL_REAUDIT_20260928.md")


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with (ROOT / path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read(path: Path) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def ref(path: Path) -> dict:
    return {"path": path.as_posix(), "sha256": sha(path)}


def main() -> int:
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    test, event, alias, post = read(TESTS), read(EVENT), read(ALIAS), read(POST)
    phase0, r6 = read(PHASE0), read(R6_EXTERNAL)
    if test.get("status") != "PASS" or event.get("status") != "PASS" or post.get("status") != "PASS":
        raise SystemExit("R8_1_GATE_A_EVIDENCE_NOT_PASS")
    if event.get("unresolved_required_scope_candidate_count") != 0:
        raise SystemExit("R8_1_REQUIRED_SCOPE_UNRESOLVED_CANDIDATES")
    if not event.get("canonical_repair", {}).get("r7_canonical_artifacts_unchanged"):
        raise SystemExit("R8_1_R7_CANONICAL_ARTIFACTS_CHANGED")
    if alias.get("event_discovery_sha256") != sha(EVENT):
        raise SystemExit("R8_1_ALIAS_RECEIPT_BINDING_MISMATCH")
    if phase0.get("phase0_status") != "FULL_PASS":
        raise SystemExit("R8_1_PHASE0_PARENT_NOT_FULL_PASS")
    if r6.get("acceptance_result", {}).get("external_acceptance") != "EXTERNALLY_ACCEPTED":
        raise SystemExit("R8_1_V4_02_PARENT_NOT_EXTERNALLY_ACCEPTED")
    script_sha = sha(Path("scripts/v4_01_identity_event_discovery_r8_1.py"))
    if event.get("execution_identity", {}).get("script_sha256") != script_sha:
        raise SystemExit("R8_1_EVENT_EXECUTION_SCRIPT_HASH_STALE")

    evidence = {
        "implementation_pack": ref(TASK_CARD),
        "external_reaudit": ref(REAUDIT),
        "test_gate": ref(TESTS),
        "identity_event_discovery": ref(EVENT),
        "alias_completeness": ref(ALIAS),
        "independent_postcheck": ref(POST),
        "r7_identity_map": ref(R7_IDENTITY),
        "r7_required_universe": ref(R7_UNIVERSE),
    }
    counts = {
        "candidates": event.get("candidate_count"),
        "candidate_status_counts": event.get("candidate_status_counts"),
        "unresolved_required_scope_candidates": event.get("unresolved_required_scope_candidate_count"),
        "required_sessions": event.get("scope", {}).get("formal_history_window", {}).get("session_count"),
        "required_universe_rows": event.get("scope", {}).get("required_universe_rows_scanned"),
        "test_counts": test.get("counts"),
    }
    stage_receipt = {
        "contract_id": "V4_01_R8_1_FINAL_STAGE_RECEIPT_R1",
        "version": "1.0.0",
        "observed_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "execution_head": head,
        "stage": "V4-01 R8.1 GENERIC IDENTITY EVENT DISCOVERY",
        "status": "PASS",
        "required_scope_status": "PASS",
        "optional_bse_status": "DEGRADED_EXCLUDED_FROM_REQUIRED_SCOPE",
        "external_acceptance": "PENDING_EXTERNAL_REVIEW",
        "contract": {"path": "config/security_identity_event_discovery_v1.json",
                     "sha256": sha(Path("config/security_identity_event_discovery_v1.json"))},
        "stage_contract": {
            "historical_backscan": True,
            "daily_incremental_mode_contracted": True,
            "candidate_signal_union": event.get("signal_counts", {}),
            "weak_signal_merge_prohibited": True,
            "unresolved_required_scope_limit": 0,
            "canonical_identity_mutation": False,
        },
        "evidence": evidence,
        "counts": counts,
        "acceptance_result": {
            "required_scope_unresolved_candidates": 0,
            "r7_canonical_artifacts_unchanged": True,
            "v4_02_cross_stage_postcheck": "PASS",
            "stage_gate": "PASS",
            "external_acceptance": "PENDING_EXTERNAL_REVIEW",
        },
        "next_stage": "AWAIT_EXTERNAL_REVIEW; KEEP_V4_03_BLOCKED",
    }
    write_json_atomic(ROOT / OUT_STAGE, stage_receipt, tdx_root=Path("D:/new_tdx"))
    joint_receipt = {
        "contract_id": "V4_00_01_02_JOINT_FINAL_RECEIPT_R2",
        "version": "1.0.0",
        "observed_at_utc": stage_receipt["observed_at_utc"],
        "execution_head": head,
        "status": "PASS_READY_FOR_EXTERNAL_REVIEW",
        "phase0": {"status": "FULL_PASS", "receipt": ref(PHASE0)},
        "v4_01": {"status": "PASS", "receipt": ref(OUT_STAGE),
                  "r7_canonical_artifacts_unchanged": True},
        "v4_02": {"status": "PASS_WITH_BSE_SCOPE_DEGRADED",
                  "external_acceptance": "EXTERNALLY_ACCEPTED", "receipt": ref(R6_EXTERNAL)},
        "joint_evidence": {"test_gate": ref(TESTS), "r8_1_postcheck": ref(POST)},
        "external_acceptance": "PENDING_EXTERNAL_REVIEW",
        "v4_03_status": "BLOCKED_PENDING_EXTERNAL_REVIEW",
        "next_stage": "EXTERNAL_REAUDIT_OF_R8_1_AND_JOINT_RESEAL",
    }
    write_json_atomic(ROOT / OUT_JOINT, joint_receipt, tdx_root=Path("D:/new_tdx"))
    review = f"""# V4-01 R8.1 Identity Event Discovery — External Review Package

Date: 2026-09-28  
Internal result: **PASS; ready for external review**  
External acceptance: **pending**

## Scope and contract

The R8.1 gate implements versioned historical-backscan and daily-incremental identity-event discovery over the V4-01 Required Scope. Candidate discovery unions official code-change events, dated aliases, adjacent dated roster changes, lifecycle boundaries, persistent retrospective bar aliases, and source-symbol reassignment/code-reuse candidates. Weak name continuity creates candidates only. Discovery does not merge or rewrite canonical identities. Unresolved Required Scope candidates fail the gate.

The prior external finding was that R8 candidate discovery depended too heavily on persistent identical overlapping bars and existing aliases. This package records the generic R8.1 repair and its independent re-audit evidence.

## Evidence and acceptance

- Test receipt: `{TESTS.as_posix()}` (SHA-256 `{sha(TESTS)}`), status `{test['status']}`, counts `{json.dumps(test.get('counts', {}), ensure_ascii=False)}`.
- Candidate receipt: `{EVENT.as_posix()}` (SHA-256 `{sha(EVENT)}`), candidates `{event.get('candidate_count')}`, unresolved Required Scope `{event.get('unresolved_required_scope_candidate_count')}`.
- Independent postcheck: `{POST.as_posix()}` (SHA-256 `{sha(POST)}`), status `{post.get('status')}`.
- Joint reseal: `{OUT_JOINT.as_posix()}` (SHA-256 `{sha(OUT_JOINT)}`).
- R7 canonical identity map and Required Scope universe hashes match the previously accepted R8 evidence; no recanonicalization was required.

Internal acceptance is limited to the R8.1 identity-discovery gate and joint 00/01/02 reseal. No new external acceptance is claimed. The accepted V4-02 R6 artifacts and Phase 0 baseline remain bound as parents. V4-03 remains blocked until external review accepts this package.

## Next stage

Independent external review of candidate completeness, evidence quality, the zero-unresolved Required Scope result, and joint reseal integrity.
"""
    (ROOT / OUT_REVIEW).parent.mkdir(parents=True, exist_ok=True)
    target = ROOT / OUT_REVIEW
    fd, temp_name = tempfile.mkstemp(prefix=target.name + ".", suffix=".tmp", dir=target.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(review)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_name, target)
    except Exception:
        Path(temp_name).unlink(missing_ok=True)
        raise
    print(json.dumps({"status": "PASS", "stage_receipt": OUT_STAGE.as_posix(),
                      "joint_receipt": OUT_JOINT.as_posix(), "external_review": OUT_REVIEW.as_posix()},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
