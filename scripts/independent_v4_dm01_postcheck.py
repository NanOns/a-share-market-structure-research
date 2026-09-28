from __future__ import annotations

"""Independent verification of the V4-DM-01 bootstrap and no-op run."""

import hashlib
import html
import json
import re
import sys
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from workbench_analysis.daily_data_head import CAPABILITIES, write_json_atomic  # noqa: E402

CONTRACT = Path("config/v4_continuous_data_maintenance_v1.json")
HEAD_CONTRACT = Path("config/v4_data_accepted_head_v1.json")
BRIDGE = Path("config/v4_dm01_bridge_calendar_v1.json")
CAPTURE_MANIFEST = Path("data/v4/source_evidence/calendar_amendments_2026/capture_20260926T071911Z/capture_manifest.json")
PHASE0 = Path("reports/v4_phase0/V4_PHASE0_FINAL_RECEIPT_R5_20260928.json")
R8_STAGE = Path("reports/v4_01/v4_01_final_stage_receipt_R8_1_20260928.json")
R8_POSTCHECK = Path("reports/v4_01/V4_01_R8_1_INDEPENDENT_POSTCHECK_R1_20260928.json")
R8_EVENT = Path("reports/v4_01/V4_01_IDENTITY_EVENT_DISCOVERY_R8_1.json")
R6_EXTERNAL = Path("reports/v4_02/V4_02_FINAL_EXTERNAL_ACCEPTANCE_R6.json")
R6_HEAD = Path("data/v4/V4_02_ACCEPTED_HEAD.json")
R6_MANIFEST = Path("reports/v4_02/V4_02_FINAL_STAGING_MANIFEST_R6.json")
R7_IDENTITY = Path("data/v4/artifact_store/v4_01/security_entity_map_R7_20260927.json")
R7_UNIVERSE = Path("data/v4/artifact_store/v4_01/v4_01_historical_universe_required_R7_20260927.jsonl.gz")
TDX_ARCHIVE = Path("data/v4/raw_archive/b6b88d777c74f302376513bad35e9c0e35284a65bc2d9826be25accf4d58807f/hsjday.zip")
STAGE_HEAD = Path("data/v4/V4_STAGE_ACCEPTED_HEAD.json")
DATA_HEAD = Path("data/v4/V4_DATA_ACCEPTED_HEAD.json")
DEV_HEAD = Path("data/v4/V4_DEV_BASELINE_HEAD.json")
BOOTSTRAP_MANIFEST = Path("data/v4/bootstrap/V4_DM01_BOOTSTRAP_MANIFEST_R1.json")
OUT_DIR = Path("reports/v4_dm01")
OUT = OUT_DIR / "V4_DM01_INDEPENDENT_POSTCHECK_R1_20260928.json"
SHANGHAI = ZoneInfo("Asia/Shanghai")
BASE_CUTOFF = "2026-09-24"


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with (ROOT / path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read(path: Path) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def check(checks: dict[str, str], problems: list[str], name: str, passed: bool, problem: str) -> None:
    checks[name] = "PASS" if passed else "BLOCKED"
    if not passed:
        problems.append(problem)


def independent_sessions(start: str, end: str, closures: list[dict]) -> list[str]:
    closed: set[date] = set()
    for row in closures:
        left, right = date.fromisoformat(row["start"]), date.fromisoformat(row["end"])
        cursor = left
        while cursor <= right:
            closed.add(cursor)
            cursor += timedelta(days=1)
    result = []
    cursor, stop = date.fromisoformat(start), date.fromisoformat(end)
    while cursor <= stop:
        if cursor.weekday() < 5 and cursor not in closed:
            result.append(cursor.isoformat())
        cursor += timedelta(days=1)
    return result


def notice_has_required_dates(path: Path) -> bool:
    source = (ROOT / path).read_text(encoding="utf-8")
    normalized = re.sub(r"\s+", "", re.sub(r"<[^>]+>", " ", html.unescape(source)))
    return all(day in normalized for day in ("9月25日", "9月27日", "9月28日", "10月1日", "10月7日", "10月8日"))


def main() -> int:
    now = datetime.now(timezone.utc)
    local_now = now.astimezone(SHANGHAI)
    checks: dict[str, str] = {}
    problems: list[str] = []
    summary_path = ROOT / "reports" / "v4_dm01" / local_now.date().isoformat() / "run_summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    calendar_ref = summary["calendar_bridge"]
    bootstrap_ref = summary["bootstrap_receipt"]
    session_ref = summary["session_discovery_receipt"]
    e2e_ref = summary["initial_e2e_receipt"]
    calendar = read(Path(calendar_ref["path"]))
    bootstrap_receipt = read(Path(bootstrap_ref["path"]))
    session = read(Path(session_ref["path"]))
    e2e = read(Path(e2e_ref["path"]))
    stage_head, dev_head, data_head = read(STAGE_HEAD), read(DEV_HEAD), read(DATA_HEAD)
    bootstrap_manifest = read(BOOTSTRAP_MANIFEST)
    bridge = read(BRIDGE)
    capture = read(CAPTURE_MANIFEST)

    check(checks, problems, "runner_receipt_hashes_bind_files",
          all(sha(Path(ref["path"])) == ref["sha256"] for ref in
              (calendar_ref, bootstrap_ref, session_ref, e2e_ref)),
          "DM01_RUN_RECEIPT_HASH_MISMATCH")

    source_by_id = {row.get("source_id"): row for row in capture.get("sources", [])}
    source_checks = []
    for item in bridge["official_sources"]:
        row = source_by_id.get(item["source_id"])
        path = Path(item["source_capture_path"])
        source_checks.append(bool(row)
                             and sha(path) == row.get("sha256")
                             and int(row.get("http_status", 0)) == 200
                             and row.get("final_url") == item["source_url"]
                             and notice_has_required_dates(path))
    check(checks, problems, "official_exchange_notice_captures_verified",
          len(source_checks) == len(bridge["official_sources"]) and all(source_checks),
          "DM01_OFFICIAL_CALENDAR_CAPTURE_MISMATCH")

    horizon = calendar["scope"]["end_date"]
    expected_new = [day for day in independent_sessions(BASE_CUTOFF, horizon,
                                                        bridge["official_sources"][0]["closure_ranges"])
                    if day > BASE_CUTOFF]
    actual_new = calendar.get("official_sessions_after_base_cutoff", [])
    check(checks, problems, "official_session_expansion_matches_notices",
          actual_new == expected_new and not calendar.get("bar_presence_used_to_infer_session", True),
          "DM01_SESSION_SET_NOT_OFFICIAL_OR_BAR_DERIVED")
    expected_latest = BASE_CUTOFF
    completed = [day for day in [BASE_CUTOFF, *actual_new]
                 if date.fromisoformat(day) < local_now.date()
                 or (date.fromisoformat(day) == local_now.date()
                     and local_now.time().replace(tzinfo=None) >= time(15, 0))]
    if completed:
        expected_latest = max(completed)
    check(checks, problems, "latest_completed_session_uses_exchange_close",
          calendar.get("latest_completed_official_session") == expected_latest
          and summary.get("latest_data_cutoff") == BASE_CUTOFF,
          "DM01_COMPLETION_CUTOFF_OR_DATA_HEAD_MISMATCH")

    phase0, r8_stage, r8_post = read(PHASE0), read(R8_STAGE), read(R8_POSTCHECK)
    r6 = read(R6_EXTERNAL)
    check(checks, problems, "accepted_parent_stage_bindings_valid",
          phase0.get("phase0_status") == "FULL_PASS"
          and r8_stage.get("required_scope_status") == "PASS"
          and r8_post.get("status") == "PASS"
          and r6.get("acceptance_result", {}).get("external_acceptance") == "EXTERNALLY_ACCEPTED"
          and r6.get("stage_contract", {}).get("required_scope_result") == "PASS"
          and read(R6_HEAD).get("external_acceptance") == "EXTERNALLY_ACCEPTED",
          "DM01_PARENT_STAGE_NOT_ACCEPTED")

    bindings = bootstrap_receipt.get("parent_bindings", {})
    expected_inputs = {
        "phase0": PHASE0, "v4_01_r8_1": R8_STAGE, "v4_01_r8_1_postcheck": R8_POSTCHECK,
        "v4_01_identity_map": R7_IDENTITY, "v4_01_universe": R7_UNIVERSE,
        "v4_02_accepted_head": R6_HEAD, "v4_02_manifest": R6_MANIFEST,
        "tdx_archive": TDX_ARCHIVE,
    }
    parent_hashes_ok = all(bindings.get(name, {}).get("sha256") == sha(path)
                           for name, path in expected_inputs.items())
    check(checks, problems, "bootstrap_parent_hashes_verified", parent_hashes_ok,
          "DM01_PARENT_HASH_MISMATCH")
    event_payload = read(R8_EVENT)
    event_r7 = event_payload.get("canonical_repair", {}).get("r7_canonical_artifact_hashes", {})
    event_postcheck_ok = (
        event_payload.get("status") == "PASS"
        and event_payload.get("unresolved_required_scope_candidate_count") == 0
        and event_r7.get("identity_map_sha256") == sha(R7_IDENTITY)
        and event_r7.get("required_universe_sha256") == sha(R7_UNIVERSE)
        and event_payload.get("canonical_repair", {}).get("r7_canonical_artifacts_unchanged") is True
    )
    check(checks, problems, "r8_1_canonical_reseal_parent_unchanged", event_postcheck_ok,
          "DM01_R8_1_BASELINE_OR_R7_CANONICAL_HASH_CHANGED")

    stage_sha, dev_sha, data_sha = sha(STAGE_HEAD), sha(DEV_HEAD), sha(DATA_HEAD)
    manifest_sha = sha(BOOTSTRAP_MANIFEST)
    head_ok = (
        bootstrap_manifest.get("status") == "CANDIDATE_MANIFEST_READY"
        and bootstrap_manifest.get("large_historical_files_copied") is False
        and bootstrap_manifest.get("stage_00_01_02_modified") is False
        and bootstrap_manifest.get("v4_03_implementation_started") is False
        and bootstrap_manifest.get("tdx_root_write_count") == 0
        and stage_head.get("source_cutoffs") == {"V4-01": BASE_CUTOFF, "V4-02": BASE_CUTOFF}
        and stage_head.get("data_head_must_not_move_this_pointer") is True
        and dev_head.get("immutable_after_initialization") is True
        and dev_head.get("data_head_updates_move_this_pointer") is False
        and dev_head.get("created_from_input_commit") == "8941119dba4fb8c75d98699f8fa92c3406de9811"
        and data_head.get("accepted_trade_date") == BASE_CUTOFF
        and data_head.get("manifest_sha256") == manifest_sha
        and data_head.get("stage_accepted_head_sha256") == stage_sha
        and data_head.get("dev_baseline_sha256") == dev_sha
        and bootstrap_manifest.get("stage_accepted_head", {}).get("sha256") == stage_sha
        and bootstrap_receipt.get("stage_head", {}).get("sha256") == stage_sha
        and bootstrap_receipt.get("dev_baseline_head", {}).get("sha256") == dev_sha
        and bootstrap_receipt.get("data_head", {}).get("sha256") == data_sha
    )
    check(checks, problems, "three_head_bootstrap_and_immutability", head_ok,
          "DM01_HEAD_BINDING_OR_IMMUTABILITY_MISMATCH")
    caps = data_head.get("component_permissions", {})
    check(checks, problems, "all_capabilities_present_and_fail_closed",
          set(caps) == set(CAPABILITIES)
          and all(isinstance(caps[name], dict) and caps[name].get("status") in {"FULL_PASS", "DEGRADED_PASS"}
                  for name in CAPABILITIES)
          and caps.get("ADJUSTED_DAILY", {}).get("status") == "DEGRADED_PASS"
          and caps.get("PRICE_LIMIT", {}).get("status") == "DEGRADED_PASS"
          and caps.get("SPECIAL_PHASE", {}).get("status") == "DEGRADED_PASS",
          "DM01_CAPABILITY_STATUS_INVALID")

    no_new_session = expected_latest == BASE_CUTOFF
    no_op_ok = (
        summary.get("status") == "PASS_NOOP_ALREADY_ACCEPTED"
        and e2e.get("status") == "PASS_NOOP_ALREADY_ACCEPTED"
        and session.get("processed_sessions") == []
        and session.get("blocked_sessions") == []
        and e2e.get("data_head_moved_after_bootstrap") is False
        and e2e.get("source_freeze_receipts") == []
        and e2e.get("per_session_build_receipts") == []
    )
    fail_closed_ok = (
        summary.get("status") == "BLOCKED_SOURCE_NOT_READY"
        and e2e.get("status") == "BLOCKED_SOURCE_NOT_READY"
        and session.get("processed_sessions") == []
        and bool(session.get("blocked_sessions"))
        and e2e.get("data_head_moved_after_bootstrap") is False
        and data_head.get("accepted_trade_date") == BASE_CUTOFF
    )
    check(checks, problems, "noop_or_source_not_ready_policy_applied",
          (no_new_session and no_op_ok) or (not no_new_session and fail_closed_ok),
          "DM01_SOURCE_GAP_PROMOTED_OR_NOOP_MISSTATED")

    check(checks, problems, "stage_scope_and_tdx_write_guards",
          summary.get("tdx_root_write_count") == 0
          and e2e.get("tdx_root_write_count") == 0
          and e2e.get("stage_00_01_02_modified") is False
          and e2e.get("v4_03_implementation_started") is False,
          "DM01_PROHIBITED_SCOPE_OR_TDX_WRITE_REPORTED")

    status = "PASS" if all(value == "PASS" for value in checks.values()) else "BLOCKED"
    receipt = {
        "contract_id": "V4_DM01_INDEPENDENT_POSTCHECK_R1",
        "version": "1.0.0",
        "observed_at_utc": now.replace(microsecond=0).isoformat(),
        "status": status,
        "owner_stage_result": summary.get("status"),
        "checks": checks,
        "counts": {
            "official_sessions_after_base_cutoff": len(actual_new),
            "processed_sessions": len(session.get("processed_sessions", [])),
            "blocked_sessions": len(session.get("blocked_sessions", [])),
            "capabilities": len(caps),
        },
        "cutoffs": {"bootstrap": BASE_CUTOFF, "accepted_data_head": data_head.get("accepted_trade_date"),
                    "latest_completed_session": expected_latest},
        "head_hashes": {"stage_accepted_head_sha256": stage_sha, "dev_baseline_sha256": dev_sha,
                        "data_accepted_head_sha256": data_sha, "bootstrap_manifest_sha256": manifest_sha},
        "run_summary": {"path": summary_path.relative_to(ROOT).as_posix(), "sha256": sha(summary_path)},
        "problems": problems,
        "next_stage": "SEAL_DM01_FINAL_RECEIPT_AND_EXTERNAL_REVIEW" if status == "PASS" else "REPAIR_DM01_POSTCHECK_BLOCKERS",
    }
    written_sha = write_json_atomic(ROOT / OUT, receipt, tdx_root=Path("D:/new_tdx"))
    print(json.dumps({"status": status, "owner_stage_result": summary.get("status"),
                      "checks": checks, "receipt": OUT.as_posix(), "sha256": written_sha}, ensure_ascii=False))
    return 0 if status == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
