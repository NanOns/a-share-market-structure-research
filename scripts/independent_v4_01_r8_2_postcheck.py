from __future__ import annotations

"""Independent evidence and fail-closed checks for the R8.2 resolution policy."""

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from workbench_analysis.daily_data_head import write_json_atomic  # noqa: E402

POLICY = Path("config/identity_relation_evidence_policy_v1.json")
EVENT = Path("reports/v4_01/V4_01_IDENTITY_EVENT_DISCOVERY_R8_2.json")
QUEUE = Path("reports/v4_01/V4_01_R8_2_UNRESOLVED_AUDIT_QUEUE.json")
OUT = Path("reports/v4_01/V4_01_R8_2_INDEPENDENT_POSTCHECK_R1_20260928.json")
R7_IDENTITY = Path("data/v4/artifact_store/v4_01/security_entity_map_R7_20260927.json")
R7_UNIVERSE = Path("data/v4/artifact_store/v4_01/v4_01_historical_universe_required_R7_20260927.jsonl.gz")
PRIOR_R8 = Path("reports/v4_01/V4_01_HISTORICAL_CODE_CHANGE_ALIAS_COMPLETENESS_R8.json")
STAGE_OUT = Path("reports/v4_01/v4_01_final_stage_receipt_R8_2_20260928.json")
TEST_RECEIPT = Path("reports/v4_joint/V4_R8_2_DM01_TEST_RECEIPT_R1_20260928.json")
DISCOVERY_SCRIPT = Path("scripts/v4_01_identity_event_discovery_r8_2.py")


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with (ROOT / path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read(path: Path) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def aware(value: object) -> bool:
    try:
        return datetime.fromisoformat(str(value or "").replace("Z", "+00:00")).utcoffset() is not None
    except ValueError:
        return False


def main() -> int:
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    policy, report, queue, tests = read(POLICY), read(EVENT), read(QUEUE), read(TEST_RECEIPT)
    checks: dict[str, str] = {}
    problems: list[str] = []

    def check(name: str, passed: bool, reason: str) -> None:
        checks[name] = "PASS" if passed else "BLOCKED"
        if not passed:
            problems.append(reason)

    check("versioned_policy_bound",
          report.get("identity_relation_policy") == {"contract_id": policy.get("contract_id"),
                                                       "version": policy.get("version")}
          and report.get("evidence", {}).get("relation_policy", {}).get("sha256") == sha(POLICY),
          "R8_2_POLICY_BINDING_MISMATCH")
    check("execution_and_regression_receipts_bound",
          report.get("execution_identity", {}).get("script_sha256") == sha(DISCOVERY_SCRIPT)
          and tests.get("status") == "PASS"
          and tests.get("counts", {}).get("failed") == 0
          and tests.get("counts", {}).get("errors") == 0,
          "R8_2_EXECUTION_OR_TEST_RECEIPT_INVALID")
    check("r7_canonical_artifacts_unchanged",
          report.get("canonical_repair", {}).get("r7_canonical_artifacts_unchanged") is True
          and report.get("canonical_repair", {}).get("r7_canonical_artifact_hashes") == {
              "identity_map_sha256": sha(R7_IDENTITY), "required_universe_sha256": sha(R7_UNIVERSE)}
          and report.get("canonical_repair", {}).get("r7_canonical_artifact_hashes") ==
              report.get("canonical_repair", {}).get("prior_r8_canonical_artifact_hashes"),
          "R8_2_R7_CANONICAL_HASH_MISMATCH")

    confirmed_same = confirmed_distinct = 0
    evidence_errors: list[str] = []
    for event in report.get("events", []):
        status = event.get("resolution_status")
        evidence_rows = event.get("resolution_evidence", [])
        if status not in {"CONFIRMED_SAME_ENTITY_CODE_CHANGE", "CONFIRMED_DISTINCT_ENTITY"}:
            continue
        if len(evidence_rows) != 1:
            evidence_errors.append(str(event.get("candidate_id")))
            continue
        evidence = evidence_rows[0]
        expected_relation = "SAME_ENTITY" if status == "CONFIRMED_SAME_ENTITY_CODE_CHANGE" else "DISTINCT_ENTITY"
        digest = str(evidence.get("source_capture_sha256") or "").lower()
        source_path = Path(str(evidence.get("source_capture_path") or ""))
        expected_classes = ({"OFFICIAL_CODE_CHANGE_NOTICE", "VERSIONED_ACCEPTED_IDENTITY_ALIAS"}
                            if expected_relation == "SAME_ENTITY" else
                            {"OFFICIAL_DISTINCT_ISSUER_IDENTITY", "VERSIONED_ACCEPTED_LIFECYCLE_IDENTITY"})
        common_ok = (
            evidence.get("entity_relation") == expected_relation
            and evidence.get("evidence_class") in expected_classes
            and evidence.get("source_ref")
            and source_path.is_file()
            and sha(source_path) == digest
            and _all_hex_digest(digest)
            and evidence.get("effective_date")
            and aware(evidence.get("observed_at"))
            and aware(evidence.get("system_available_at"))
            and sorted(str(value).upper() for value in evidence.get("source_security_keys", []))
                == sorted(str(value).upper() for value in event.get("source_keys", []))
        )
        if expected_relation == "SAME_ENTITY":
            specific_ok = bool(evidence.get("canonical_security_id")) and bool(report.get("evidence", {}).get("official_code_change_notice", {}).get("sha256") == digest)
            confirmed_same += 1
        else:
            security_ids = set(evidence.get("security_ids", []))
            issuer_ids = set(evidence.get("issuer_ids", []))
            specific_ok = len(security_ids) == 2 and len(issuer_ids) == 2
            confirmed_distinct += 1
        if not common_ok or not specific_ok:
            evidence_errors.append(str(event.get("candidate_id")))

    check("confirmed_relations_have_policy_evidence", not evidence_errors,
          "R8_2_CONFIRMED_RELATION_EVIDENCE_INVALID")
    weak_distinct = [event.get("candidate_id") for event in report.get("events", [])
                     if event.get("resolution_status") == "CONFIRMED_DISTINCT_ENTITY"
                     and event.get("resolution_reason") != "POLICY_ACCEPTED_HASH_VERIFIED_DISTINCT_ISSUER_EVIDENCE"]
    check("weak_signals_never_confirm_distinct", not weak_distinct,
          "R8_2_WEAK_SIGNAL_CONFIRMED_DISTINCT")

    unresolved = [event for event in report.get("events", [])
                  if event.get("required_scope_affected") and event.get("resolution_status") == "UNRESOLVED"]
    unresolved_ids = sorted(event.get("candidate_id") for event in unresolved)
    queued_ids = sorted(event.get("candidate_id") for event in queue.get("events", []))
    owner_gate = "BLOCKED" if unresolved else "PASS"
    check("required_scope_unresolved_fails_gate",
          report.get("status") == owner_gate
          and int(report.get("unresolved_required_scope_candidate_count", -1)) == len(unresolved)
          and unresolved_ids == queued_ids,
          "R8_2_REQUIRED_SCOPE_GATE_OR_QUEUE_MISMATCH")
    check("generic_logic_has_no_security_fixture_branch",
          "300114" not in (ROOT / "src/workbench_analysis/security_identity_event_discovery.py").read_text("utf-8")
          and "302132" not in (ROOT / "src/workbench_analysis/security_identity_event_discovery.py").read_text("utf-8"),
          "R8_2_SECURITY_SPECIFIC_ALGORITHM_BRANCH")
    check("discovery_and_queue_receipts_exist",
          report.get("candidate_count") == len(report.get("events", []))
          and queue.get("candidate_count") == len(unresolved)
          and report.get("evidence", {}).get("task_card", {}).get("sha256") == sha(
              Path("docs/evidence/V4_R8_1_DM01_EXTERNAL_AUDIT_AND_R2_INCREMENTAL_WIRING_20260928.md")),
          "R8_2_RECEIPT_COUNTS_OR_TASK_BINDING_INVALID")

    status = "PASS" if all(value == "PASS" for value in checks.values()) else "BLOCKED"
    receipt = {
        "contract_id": "V4_01_R8_2_INDEPENDENT_POSTCHECK_R1",
        "version": "1.0.0",
        "observed_at_utc": now,
        "status": status,
        "owner_stage_result": owner_gate,
        "external_acceptance": "PENDING_EXTERNAL_AUDIT",
        "checks": checks,
        "counts": {"candidates": report.get("candidate_count"),
                   "confirmed_same": confirmed_same, "confirmed_distinct": confirmed_distinct,
                   "unresolved_required_scope": len(unresolved)},
        "r7_canonical_hashes": report.get("canonical_repair", {}).get("r7_canonical_artifact_hashes"),
        "problems": problems,
        "next_stage": "EXTERNAL_R8_2_AUDIT_AND_OFFICIAL_DISTINCT_EVIDENCE_TRIAGE",
    }
    write_json_atomic(ROOT / OUT, receipt, tdx_root=Path("D:/new_tdx"))
    stage = {
        "contract_id": "V4_01_R8_2_FINAL_STAGE_RECEIPT_R1",
        "version": "1.0.0",
        "observed_at_utc": now,
        "stage": "V4-01 R8.2 IDENTITY RELATION EVIDENCE POLICY",
        "status": owner_gate,
        "required_scope_status": owner_gate,
        "external_acceptance": "PENDING_EXTERNAL_AUDIT",
        "stage_contract": {"relation_policy_id": policy.get("contract_id"),
                           "relation_policy_version": policy.get("version"),
                           "weak_candidate_signals_can_confirm_relation": False,
                           "required_scope_unresolved_limit": 0,
                           "canonical_identity_mutation": False},
        "evidence": {
            "policy": {"path": POLICY.as_posix(), "sha256": sha(POLICY)},
            "event_discovery": {"path": EVENT.as_posix(), "sha256": sha(EVENT)},
            "unresolved_queue": {"path": QUEUE.as_posix(), "sha256": sha(QUEUE)},
            "test_gate": {"path": TEST_RECEIPT.as_posix(), "sha256": sha(TEST_RECEIPT)},
            "independent_postcheck": {"path": OUT.as_posix(), "sha256": sha(OUT)},
            "r7_identity_map": {"path": R7_IDENTITY.as_posix(), "sha256": sha(R7_IDENTITY)},
            "r7_required_universe": {"path": R7_UNIVERSE.as_posix(), "sha256": sha(R7_UNIVERSE)},
        },
        "acceptance_result": {"gate_a_internal_postcheck": status,
                              "gate_a_owner_gate": owner_gate,
                              "external_acceptance": "PENDING_EXTERNAL_AUDIT"},
        "next_stage": receipt["next_stage"] if owner_gate == "BLOCKED"
            else "AWAIT_EXTERNAL_AUDIT_BEFORE_DM01_PROMOTION_OR_V4_03",
        "v4_03_status": "BLOCKED",
    }
    write_json_atomic(ROOT / STAGE_OUT, stage, tdx_root=Path("D:/new_tdx"))
    print(json.dumps({"postcheck": status, "owner_gate": owner_gate,
                      "unresolved_required_scope": len(unresolved),
                      "postcheck_receipt": OUT.as_posix(), "stage_receipt": STAGE_OUT.as_posix()}, ensure_ascii=False))
    return 0 if status == "PASS" else 2


def _all_hex_digest(value: str) -> bool:
    return len(value) == 64 and all(ch in "0123456789abcdef" for ch in value)


if __name__ == "__main__":
    raise SystemExit(main())
