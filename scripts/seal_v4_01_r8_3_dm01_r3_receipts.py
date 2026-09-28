from __future__ import annotations

"""Seal separate R8.3 Gate A, DM-01 Gate B, and joint R3 receipts."""

import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DISCOVERY = Path("reports/v4_01/V4_01_IDENTITY_EVENT_DISCOVERY_R8_3.json")
INDEX_REPORT = Path("reports/v4_01/V4_01_OFFICIAL_CODE_CHANGE_EVENT_INDEX_R8_3.json")
POST_A = Path("reports/v4_01/V4_01_R8_3_INDEPENDENT_POSTCHECK.json")
TESTS = Path("reports/v4_joint/V4_R8_3_DM01_TEST_RECEIPT_R1_20260928.json")
DM01_POST = Path("reports/v4_dm01/V4_DM01_INDEPENDENT_POSTCHECK_R1_20260928.json")
DM01_RUN = Path("reports/v4_dm01/2026-09-28/run_summary.json")
DM01_E2E = Path("reports/v4_dm01/2026-09-28/initial_e2e_receipt.json")
DATA_HEAD = Path("data/v4/V4_DATA_ACCEPTED_HEAD.json")
STAGE_HEAD = Path("data/v4/V4_STAGE_ACCEPTED_HEAD.json")
DEV_HEAD = Path("data/v4/V4_DEV_BASELINE_HEAD.json")
STAGE_A = Path("reports/v4_01/v4_01_final_stage_receipt_R8_3_20260928.json")
GATE_B = Path("reports/v4_dm01/V4_DM01_GATE_B_RECEIPT_R8_3_R1_20260928.json")
JOINT = Path("reports/v4_joint/V4_00_01_02_JOINT_FINAL_RECEIPT_R3_20260928.json")


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with (ROOT / path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read(path: Path) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def ref(path: Path) -> dict[str, str]:
    return {"path": path.as_posix(), "sha256": sha(path)}


def atomic(path: Path, payload: dict) -> None:
    target = ROOT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=target.name + ".", suffix=".tmp", dir=target.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(payload, stream, ensure_ascii=False, sort_keys=True, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_name, target)
    except Exception:
        Path(temp_name).unlink(missing_ok=True)
        raise


def main() -> int:
    discovery, index, post_a, tests = read(DISCOVERY), read(INDEX_REPORT), read(POST_A), read(TESTS)
    dm01_post, dm01_run, e2e = read(DM01_POST), read(DM01_RUN), read(DM01_E2E)
    data_head = read(DATA_HEAD)
    phase0 = read(Path("reports/v4_phase0/V4_PHASE0_FINAL_RECEIPT_R5_20260928.json"))
    v402 = read(Path("reports/v4_02/V4_02_FINAL_EXTERNAL_ACCEPTANCE_R6.json"))
    if tests.get("status") != "PASS" or post_a.get("status") != "PASS" or dm01_post.get("status") != "PASS":
        raise SystemExit("R8_3_OR_DM01_TEST_OR_INDEPENDENT_POSTCHECK_NOT_PASS")
    if discovery.get("gate_a_status") != "BLOCKED" or index.get("coverage_status") != "BLOCKED":
        raise SystemExit("R8_3_GATE_A_STATUS_MISMATCH")
    if dm01_run.get("status") != "PASS_NOOP_ALREADY_ACCEPTED" or data_head.get("accepted_trade_date") != "2026-09-24":
        raise SystemExit("DM01_NOOP_OR_HEAD_CUTOFF_MISMATCH")
    if (phase0.get("phase0_status") != "FULL_PASS"
            or v402.get("acceptance_result", {}).get("external_acceptance") != "EXTERNALLY_ACCEPTED"
            or v402.get("stage_contract", {}).get("required_scope_result") != "PASS"):
        raise SystemExit("JOINT_PARENT_STAGE_ACCEPTANCE_MISMATCH")

    receipt_time = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    stage_a = {
        "contract_id": "V4_01_R8_3_FINAL_STAGE_RECEIPT",
        "version": "1.0.0",
        "observed_at_utc": receipt_time,
        "stage": "V4-01 R8.3 ATOMIC BOUNDARIES AND CANDIDATE LINKAGE PRECISION",
        "status": "BLOCKED",
        "stage_contract": {
            "linkage_contract_id": "SECURITY_IDENTITY_EVENT_LINKAGE_V1",
            "official_event_index_contract_id": "OFFICIAL_SECURITY_CODE_CHANGE_EVENT_INDEX_V1",
            "required_scope_unresolved_candidate_limit": 0,
            "unlinked_boundary_anomaly_limit": 0,
            "official_index_coverage_required": True,
            "canonical_identity_mutation": False,
        },
        "acceptance_result": {
            "tests": tests.get("status"),
            "independent_algorithm_postcheck": post_a.get("status"),
            "identity_discovery": discovery.get("identity_discovery_status"),
            "official_event_index_coverage": index.get("coverage_status"),
            "owner_gate": discovery.get("gate_a_status"),
            "external_acceptance": "PENDING_EXTERNAL_AUDIT",
        },
        "counts": {
            "candidate_count": discovery.get("candidate_count"),
            "confirmed_same_entity": discovery.get("candidate_status_counts", {}).get("CONFIRMED_SAME_ENTITY_CODE_CHANGE", 0),
            "unresolved_required_scope_candidates": discovery.get("unresolved_required_scope_candidate_count"),
            "atomic_boundary_events": discovery.get("boundary_event_count"),
            "unlinked_boundary_anomalies": discovery.get("unlinked_boundary_anomaly_count"),
            "official_event_rows": index.get("event_count"),
            "unresolved_official_source_windows": len(index.get("unresolved_source_windows", [])),
        },
        "evidence": {path.as_posix(): ref(path) for path in (
            DISCOVERY, INDEX_REPORT, POST_A, TESTS,
            Path("config/security_identity_event_linkage_v1.json"),
            Path("config/official_security_code_change_event_index_v1.json"),
            Path("data/v4/source_evidence/official_code_change_event_index/official_security_code_change_events_v1.jsonl"),
            Path("data/v4/source_evidence/official_code_change_event_index/coverage_receipt_v1.json"),
        )},
        "r7_canonical_artifacts_unchanged": discovery.get("canonical_repair", {}).get("r7_canonical_artifacts_unchanged"),
        "next_stage": "COMPLETE_OFFICIAL_INDEX_FULL_WINDOW_COVERAGE_THEN_RESEAL_GATE_A",
        "v4_03_status": "BLOCKED",
    }
    atomic(STAGE_A, stage_a)

    local_coverage = e2e.get("local_tdx_coverage_discovery", {})
    gate_b = {
        "contract_id": "V4_DM01_GATE_B_RECEIPT_R8_3_R1",
        "version": "1.0.0",
        "observed_at_utc": receipt_time,
        "owner_stage": "V4-DM-01 REAL INCREMENTAL WIRING",
        "status": "FRAMEWORK_PASS_ONLY",
        "gate_b_status": "BLOCKED",
        "bootstrap_noop_status": dm01_run.get("status"),
        "independent_framework_postcheck": dm01_post.get("status"),
        "production_incremental_builders": "NOT_WIRED_FAIL_CLOSED",
        "real_session_e2e": "NOT_RUN_NO_NEW_COMPLETED_SESSION",
        "source_readiness": {
            "latest_completed_official_session": e2e.get("latest_completed_session"),
            "not_completed_sessions": dm01_run.get("not_completed_sessions"),
            "local_tdx_latest_tail_date": local_coverage.get("latest_tail_date"),
            "files_after_accepted_cutoff": local_coverage.get("file_count_after_bootstrap_cutoff"),
            "tail_date_is_complete_session": local_coverage.get("tail_date_means_complete_market_session"),
            "source_freeze_receipts": e2e.get("source_freeze_receipts"),
            "per_session_build_receipts": e2e.get("per_session_build_receipts"),
        },
        "head_state": {
            "accepted_trade_date": data_head.get("accepted_trade_date"),
            "data_head_sha256": sha(DATA_HEAD),
            "stage_head_sha256": sha(STAGE_HEAD),
            "dev_baseline_head_sha256": sha(DEV_HEAD),
            "data_head_moved": e2e.get("data_head_moved_after_bootstrap"),
        },
        "tdx_root_write_count": e2e.get("tdx_root_write_count"),
        "evidence": {path.as_posix(): ref(path) for path in (DM01_RUN, DM01_E2E, DM01_POST, TESTS,
                                                               DATA_HEAD, STAGE_HEAD, DEV_HEAD)},
        "next_stage": "WIRE_ACCEPTED_INCREMENTAL_COMPONENT_RUNTIMES_AND_RUN_ONE_SOURCE_READY_SESSION",
        "v4_03_status": "BLOCKED",
    }
    atomic(GATE_B, gate_b)

    joint = {
        "contract_id": "V4_00_01_02_JOINT_FINAL_RECEIPT_R3",
        "version": "1.0.0",
        "observed_at_utc": receipt_time,
        "status": "BLOCKED",
        "stage_status": {
            "V4_00": phase0.get("phase0_status"),
            "V4_01_R8_3": "BLOCKED_OFFICIAL_INDEX_COVERAGE",
            "V4_02": ("PASS_EXTERNALLY_ACCEPTED"
                      if v402.get("acceptance_result", {}).get("external_acceptance") == "EXTERNALLY_ACCEPTED"
                      and v402.get("stage_contract", {}).get("required_scope_result") == "PASS" else "BLOCKED"),
            "V4_DM01": "FRAMEWORK_PASS_ONLY_PRODUCTION_BUILDERS_NOT_WIRED",
            "V4_03": "BLOCKED",
        },
        "gate_a": {"status": "BLOCKED", "tests": tests.get("status"),
                    "independent_postcheck": post_a.get("status"),
                    "identity_discovery": discovery.get("identity_discovery_status"),
                    "official_index_coverage": index.get("coverage_status"),
                    "unresolved_candidates": discovery.get("unresolved_required_scope_candidate_count")},
        "gate_b": {"status": "BLOCKED", "framework_noop": dm01_run.get("status"),
                    "independent_postcheck": dm01_post.get("status"),
                    "production_incremental_builders": "NOT_WIRED_FAIL_CLOSED",
                    "real_session_e2e": "NOT_RUN_NO_NEW_COMPLETED_SESSION"},
        "external_acceptance": "PENDING_EXTERNAL_AUDIT",
        "evidence": {"gate_a_stage_receipt": ref(STAGE_A), "gate_b_receipt": ref(GATE_B),
                     "test_receipt": ref(TESTS), "gate_a_postcheck": ref(POST_A),
                     "gate_b_postcheck": ref(DM01_POST), "official_index_coverage": ref(INDEX_REPORT),
                     "phase0_receipt": ref(Path("reports/v4_phase0/V4_PHASE0_FINAL_RECEIPT_R5_20260928.json")),
                     "v4_02_external_acceptance": ref(Path("reports/v4_02/V4_02_FINAL_EXTERNAL_ACCEPTANCE_R6.json"))},
        "next_stage": "COMPLETE_R8_3_OFFICIAL_COVERAGE_AND_DM01_REAL_BUILDER_WIRING",
    }
    atomic(JOINT, joint)
    print(json.dumps({"gate_a": stage_a["status"], "gate_b": gate_b["gate_b_status"],
                      "joint": joint["status"], "test_counts": tests.get("counts"),
                      "stage_a": STAGE_A.as_posix(), "gate_b_receipt": GATE_B.as_posix(),
                      "joint_receipt": JOINT.as_posix()}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
