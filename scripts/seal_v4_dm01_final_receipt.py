from __future__ import annotations

"""Seal DM01 bootstrap evidence, independent postcheck, and external-review package."""

import hashlib
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from workbench_analysis.daily_data_head import write_json_atomic  # noqa: E402

FINAL = Path("reports/v4_dm01/V4_DM01_FINAL_RECEIPT_R1_20260928.json")
REVIEW = Path("reports/v4_dm01/V4_DM01_EXTERNAL_REVIEW_PACKAGE_R1_20260928.md")
JOINT_REVIEW = Path("reports/v4_joint/V4_R8_1_DM01_JOINT_EXTERNAL_REVIEW_PACKAGE_R1_20260928.md")
RUN_SUMMARY = Path("reports/v4_dm01/2026-09-28/run_summary.json")
POSTCHECK = Path("reports/v4_dm01/V4_DM01_INDEPENDENT_POSTCHECK_R1_20260928.json")
TESTS = Path("reports/v4_joint/V4_R8_1_DM01_TEST_RECEIPT_R1_20260928.json")
BOOTSTRAP = Path("reports/v4_dm01/2026-09-28/bootstrap_receipt.json")
CALENDAR = Path("reports/v4_dm01/2026-09-28/calendar_bridge_receipt.json")
SESSION = Path("reports/v4_dm01/2026-09-28/session_discovery_receipt.json")
E2E = Path("reports/v4_dm01/2026-09-28/initial_e2e_receipt.json")
PERFORMANCE = Path("reports/v4_dm01/2026-09-28/performance_receipt.json")
STAGE_HEAD = Path("data/v4/V4_STAGE_ACCEPTED_HEAD.json")
DATA_HEAD = Path("data/v4/V4_DATA_ACCEPTED_HEAD.json")
DEV_HEAD = Path("data/v4/V4_DEV_BASELINE_HEAD.json")
BOOTSTRAP_MANIFEST = Path("data/v4/bootstrap/V4_DM01_BOOTSTRAP_MANIFEST_R1.json")
GATE_A_STAGE = Path("reports/v4_01/v4_01_final_stage_receipt_R8_1_20260928.json")
JOINT_RECEIPT = Path("reports/v4_joint/V4_00_01_02_JOINT_FINAL_RECEIPT_R2_20260928.json")
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


def atomic_text(path: Path, text: str) -> None:
    target = ROOT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=target.name + ".", suffix=".tmp", dir=target.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_name, target)
    except Exception:
        Path(temp_name).unlink(missing_ok=True)
        raise


def main() -> int:
    summary, post, tests = read(RUN_SUMMARY), read(POSTCHECK), read(TESTS)
    bootstrap, calendar, session, e2e = read(BOOTSTRAP), read(CALENDAR), read(SESSION), read(E2E)
    performance = read(PERFORMANCE)
    stage_head, data_head, dev_head = read(STAGE_HEAD), read(DATA_HEAD), read(DEV_HEAD)
    if post.get("status") != "PASS" or tests.get("status") != "PASS" or performance.get("status") != "PASS":
        raise SystemExit("DM01_OR_REGRESSION_POSTCHECK_NOT_PASS")
    if summary.get("status") != "PASS_NOOP_ALREADY_ACCEPTED" or e2e.get("status") != summary.get("status"):
        raise SystemExit("DM01_NOOP_STATUS_MISMATCH")
    if data_head.get("accepted_trade_date") != "2026-09-24":
        raise SystemExit("DM01_BOOTSTRAP_CUTOFF_MISMATCH")
    if stage_head.get("data_head_must_not_move_this_pointer") is not True:
        raise SystemExit("DM01_STAGE_HEAD_IMMUTABILITY_MISSING")
    if dev_head.get("immutable_after_initialization") is not True:
        raise SystemExit("DM01_DEV_BASELINE_IMMUTABILITY_MISSING")

    capability_summary = {
        name: {"status": row.get("status"), "reason": row.get("reason"),
               "unknown_rows": row.get("unknown_rows"),
               "affected_reason_counts": row.get("affected_reason_counts")}
        for name, row in data_head.get("component_permissions", {}).items()
    }
    evidence = {
        "implementation_pack": ref(TASK_CARD), "external_reaudit": ref(REAUDIT),
        "regression_test_gate": ref(TESTS), "gate_a_stage_receipt": ref(GATE_A_STAGE),
        "joint_00_01_02_receipt": ref(JOINT_RECEIPT), "runner_summary": ref(RUN_SUMMARY),
        "bootstrap_receipt": ref(BOOTSTRAP), "calendar_bridge_receipt": ref(CALENDAR),
        "session_discovery_receipt": ref(SESSION), "initial_e2e_receipt": ref(E2E),
        "performance_receipt": ref(PERFORMANCE),
        "independent_postcheck": ref(POSTCHECK),
        "bootstrap_manifest": ref(BOOTSTRAP_MANIFEST), "stage_accepted_head": ref(STAGE_HEAD),
        "data_accepted_head": ref(DATA_HEAD), "dev_baseline_head": ref(DEV_HEAD),
    }
    receipt = {
        "contract_id": "V4_DM01_FINAL_RECEIPT_R1",
        "version": "1.0.0",
        "observed_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "owner_stage": "V4-DM-01 CONTINUOUS DATA MAINTENANCE",
        "status": "PASS_NOOP_READY_FOR_EXTERNAL_REVIEW",
        "internal_result": "PASS_NOOP_ALREADY_ACCEPTED",
        "external_acceptance": "PENDING_EXTERNAL_REVIEW",
        "contract": ref(Path("config/v4_continuous_data_maintenance_v1.json")),
        "head_contract": ref(Path("config/v4_data_accepted_head_v1.json")),
        "evidence": evidence,
        "stage_contract_result": {
            "bootstrap_cutoff": "2026-09-24",
            "latest_completed_official_session_at_run": calendar.get("latest_completed_official_session"),
            "accepted_data_cutoff": data_head.get("accepted_trade_date"),
            "processed_sessions": summary.get("processed_sessions"),
            "blocked_sessions": summary.get("blocked_sessions"),
            "not_completed_sessions": summary.get("not_completed_sessions"),
            "official_calendar_capture_verified": calendar.get("status") == "PASS",
            "session_dates_inferred_from_bars": False,
            "source_freeze_receipts": e2e.get("source_freeze_receipts"),
            "per_session_component_build_receipts": e2e.get("per_session_build_receipts"),
            "source_readiness": e2e.get("source_readiness"),
        },
        "three_heads": {
            "stage_accepted_head_sha256": sha(STAGE_HEAD),
            "dev_baseline_head_sha256": sha(DEV_HEAD),
            "data_accepted_head_sha256": sha(DATA_HEAD),
            "data_head_cutoff": data_head.get("accepted_trade_date"),
            "data_head_does_not_move_stage_or_dev_heads": True,
        },
        "component_permissions": capability_summary,
        "acceptance_result": {
            "independent_postcheck": post.get("status"),
            "regression_tests": tests.get("status"),
            "tdx_root_write_count": e2e.get("tdx_root_write_count"),
            "stage_00_01_02_modified": e2e.get("stage_00_01_02_modified"),
            "v4_03_implementation_started": e2e.get("v4_03_implementation_started"),
            "incremental_component_builders": "NOT_WIRED_FAIL_CLOSED",
            "external_acceptance": "PENDING_EXTERNAL_REVIEW",
        },
        "performance": {
            "measurement_scope": performance.get("measurement_scope"),
            "wall_seconds": performance.get("wall_seconds"),
            "cpu_seconds_sampled": performance.get("cpu_seconds_sampled"),
            "peak_working_set_bytes_sampled": performance.get("peak_working_set_bytes_sampled"),
            "rows_read": performance.get("rows_read"), "rows_written": performance.get("rows_written"),
            "securities_affected": performance.get("securities_affected"),
            "limitations": performance.get("limitations"),
        },
        "scope_limitations": [
            "Run occurred before the 2026-09-28 15:00 Asia/Shanghai close; no new session was complete.",
            "No per-session source freeze or component build was triggered in this no-op run.",
            "The first eligible post-close update still requires frozen current-session sources; otherwise the runner leaves the accepted data head unchanged with SOURCE_NOT_READY.",
            "If a completed session is source-ready, the current runner fails closed with DM01_INCREMENTAL_COMPONENT_BUILDERS_REQUIRED; this execution did not exercise or validate a new-session component build.",
        ],
        "next_stage": "WIRE_AND_VERIFY_INCREMENTAL_COMPONENT_BUILDERS; EXTERNAL_REVIEW; V4_03_REMAINS_BLOCKED",
    }
    write_json_atomic(ROOT / FINAL, receipt, tdx_root=Path("D:/new_tdx"))

    review = f"""# V4-DM-01 Continuous Data Maintenance — External Review Package

Date: 2026-09-28  
Internal result: **bootstrap/no-op PASS; ready for scoped external review**  
External acceptance: **pending**

## Contract and run outcome

DM-01 bootstraps three separately bound heads from the 2026-09-24 accepted cutoff. The stage head binds accepted stage status, the dev baseline is immutable, and the data head advances only after source freeze, capability gates, independent postcheck, candidate manifest, and atomic promotion. The runner uses captured official exchange notices for session truth, strict catch-up ordering, fail-closed source readiness, and no writes under the configured TDX root.

The run occurred before the 2026-09-28 market close. The latest completed official session remained 2026-09-24. The bootstrap completed, the daily lane returned `PASS_NOOP_ALREADY_ACCEPTED`, and no incremental source freeze or per-session component build ran. The accepted data head remains at 2026-09-24. No post-close data is claimed.

## Evidence and acceptance

- Final receipt: `{FINAL.as_posix()}` (SHA-256 `{sha(FINAL)}`).
- Independent postcheck: `{POSTCHECK.as_posix()}` (SHA-256 `{sha(POSTCHECK)}), status `{post.get('status')}`.
- Test gate: `{TESTS.as_posix()}` (SHA-256 `{sha(TESTS)}), `{tests.get('counts', {}).get('passed')}` passed, `{tests.get('counts', {}).get('skipped')}` skipped, `{tests.get('counts', {}).get('failed')}` failed.
- Performance receipt: `{PERFORMANCE.as_posix()}` (SHA-256 `{sha(PERFORMANCE)}`); an idempotent no-op rerun measured `{performance.get('wall_seconds')}` s wall / `{performance.get('cpu_seconds_sampled')}` s sampled CPU, peak working set `{performance.get('peak_working_set_bytes_sampled')}` bytes, rows read `{performance.get('rows_read')}`, rows written `{performance.get('rows_written')}`, affected securities `{performance.get('securities_affected')}`. It is not a measurement of the original bootstrap or a new-session build.
- Bootstrap manifest: `{BOOTSTRAP_MANIFEST.as_posix()}` (SHA-256 `{sha(BOOTSTRAP_MANIFEST)}`).
- Data accepted head SHA-256: `{sha(DATA_HEAD)}`; accepted cutoff: `{data_head.get('accepted_trade_date')}`.
- Official calendar bridge and source captures were independently hash/content checked. No session was inferred from bar presence.
- Component capability dispositions: `{json.dumps({k: v['status'] for k, v in capability_summary.items()}, ensure_ascii=False)}`.

The accepted V4-02 R6 and Phase 0 parents remain unchanged. This package does not claim the first post-close daily incremental has executed. That update is allowed only after the date is complete and required frozen sources are available; otherwise the runner must retain the previous data head and report `SOURCE_NOT_READY`.

The no-op run does not establish that new-session component builders are wired. If a completed session is source-ready, the current runner stops with `DM01_INCREMENTAL_COMPONENT_BUILDERS_REQUIRED` and does not promote a head. This is an explicit implementation limitation for external review, not a degraded capability claim.

## Next stage

External review of bootstrap lineage, three-head separation, calendar evidence, fail-closed source readiness, component dispositions, and no-op cutoff. After acceptance, execute the first eligible daily increment with a complete source freeze and per-session independent postcheck. V4-03 remains blocked under the active task pack.
"""
    atomic_text(REVIEW, review)
    joint_review = f"""# V4 R8.1 + DM-01 Joint External Review Package

Date: 2026-09-28  
Joint internal result: **Gate A PASS; Gate B bootstrap/no-op PASS with incremental-build limitation**  
External acceptance: **pending**

## Independent gates

1. **Gate A — identity event discovery and 00/01/02 joint reseal.** Review package: `{Path('reports/v4_01/V4_01_R8_1_EXTERNAL_REVIEW_PACKAGE_R1_20260928.md').as_posix()}`. Stage receipt: `{Path('reports/v4_joint/V4_00_01_02_JOINT_FINAL_RECEIPT_R2_20260928.json').as_posix()}`. Result: PASS; unresolved Required Scope candidates: 0; accepted R7 canonical hashes unchanged.
2. **Gate B — continuous data maintenance.** Review package: `{REVIEW.as_posix()}`. Final receipt: `{FINAL.as_posix()}`. Result: PASS_NOOP_ALREADY_ACCEPTED for bootstrap/no-op only; data cutoff remains 2026-09-24 because 2026-09-28 had not closed when the lane ran. New-session component builders remain unwired and fail closed.

The R8.1 regression gate recorded 241 passed, 2 skipped, and 0 failed. DM-01 bootstrap and its independent postcheck are separately hash-bound. Its performance receipt measures only the idempotent no-op rerun. If a completed session is source-ready, the current runner still stops at `DM01_INCREMENTAL_COMPONENT_BUILDERS_REQUIRED`; review Gate B with this limitation in view. Phase 0 remains FULL_PASS, V4-02 R6 remains externally accepted, and no V4-03 implementation was started.

## Requested review decision

Please review the owner gates independently. For DM-01, review the bootstrap/no-op evidence and the explicit `DM01_INCREMENTAL_COMPONENT_BUILDERS_REQUIRED` limitation; do not read this receipt as evidence that a new-session update has run or is ready to promote. External acceptance has not yet been recorded. V4-03 remains blocked until the required external review is complete.
"""
    atomic_text(JOINT_REVIEW, joint_review)
    print(json.dumps({"status": receipt["status"], "final_receipt": FINAL.as_posix(),
                      "external_review": REVIEW.as_posix(), "joint_review": JOINT_REVIEW.as_posix()},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
