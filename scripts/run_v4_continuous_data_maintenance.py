from __future__ import annotations

"""Bootstrap and run the V4-DM-01 daily lane through the latest completed session."""

import hashlib
import html
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from workbench_analysis.continuous_data_maintenance import (  # noqa: E402
    latest_completed_session,
    official_weekday_sessions,
    plan_catch_up,
    source_readiness,
)
from workbench_analysis.daily_data_head import (  # noqa: E402
    CAPABILITIES,
    build_data_head,
    canonical_digest,
    read_json,
    write_json_atomic,
)

CONTRACT = Path("config/v4_continuous_data_maintenance_v1.json")
HEAD_CONTRACT = Path("config/v4_data_accepted_head_v1.json")
BRIDGE_CONTRACT = Path("config/v4_dm01_bridge_calendar_v1.json")
PHASE0_RECEIPT = Path("reports/v4_phase0/V4_PHASE0_FINAL_RECEIPT_R5_20260928.json")
R8_STAGE_RECEIPT = Path("reports/v4_01/v4_01_final_stage_receipt_R8_1_20260928.json")
R8_POSTCHECK = Path("reports/v4_01/V4_01_R8_1_INDEPENDENT_POSTCHECK_R1_20260928.json")
R8_EVENT = Path("reports/v4_01/V4_01_IDENTITY_EVENT_DISCOVERY_R8_1.json")
V402_HEAD = Path("data/v4/V4_02_ACCEPTED_HEAD.json")
V402_MANIFEST = Path("reports/v4_02/V4_02_FINAL_STAGING_MANIFEST_R6.json")
CALENDAR_CONTRACT = Path("config/v4_official_exchange_calendar_v2.json")
CLOSURES_CONTRACT = Path("config/v4_official_exchange_calendar_expected_closures_v2.json")
AMENDMENTS_CONTRACT = Path("config/v4_official_calendar_amendments_2026_v1.json")
CAPTURE_MANIFEST = Path(
    "data/v4/source_evidence/calendar_amendments_2026/capture_20260926T071911Z/capture_manifest.json"
)
IDENTITY_R7 = Path("data/v4/artifact_store/v4_01/security_entity_map_R7_20260927.json")
UNIVERSE_R7 = Path("data/v4/artifact_store/v4_01/v4_01_historical_universe_required_R7_20260927.jsonl.gz")
TDX_ARCHIVE = Path(
    "data/v4/raw_archive/b6b88d777c74f302376513bad35e9c0e35284a65bc2d9826be25accf4d58807f/hsjday.zip"
)
STAGE_HEAD = Path("data/v4/V4_STAGE_ACCEPTED_HEAD.json")
DATA_HEAD = Path("data/v4/V4_DATA_ACCEPTED_HEAD.json")
DEV_HEAD = Path("data/v4/V4_DEV_BASELINE_HEAD.json")
BOOTSTRAP_MANIFEST = Path("data/v4/bootstrap/V4_DM01_BOOTSTRAP_MANIFEST_R1.json")
SHANGHAI = ZoneInfo("Asia/Shanghai")
BASE_CUTOFF = "2026-09-24"
INPUT_HEAD = "8941119dba4fb8c75d98699f8fa92c3406de9811"
TDX_ROOT = Path("D:/new_tdx")
TDX_ARCHIVE_SHA256 = "b6b88d777c74f302376513bad35e9c0e35284a65bc2d9826be25accf4d58807f"


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with (ROOT / path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read(path: Path) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def atomic(path: Path, payload: dict) -> str:
    return write_json_atomic(ROOT / path, payload, tdx_root=TDX_ROOT)


def notice_text_matches(path: Path) -> bool:
    source = (ROOT / path).read_text(encoding="utf-8")
    text = html.unescape(source)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", "", text)
    return all(value in text for value in ("9月25日", "9月27日", "9月28日", "10月1日", "10月7日", "10月8日"))


def build_calendar_bridge(now: datetime) -> tuple[dict, list[str]]:
    bridge = read(BRIDGE_CONTRACT)
    capture = read(CAPTURE_MANIFEST)
    sources_by_id = {row.get("source_id"): row for row in capture.get("sources", [])}
    source_rows = []
    relevant_hashes = []
    for source in bridge["official_sources"]:
        row = sources_by_id.get(source["source_id"])
        if not row:
            raise SystemExit("DM01_RELEVANT_OFFICIAL_CALENDAR_CAPTURE_MISSING")
        actual_sha = sha(Path(source["source_capture_path"]))
        if (actual_sha != row.get("sha256") or int(row.get("http_status", 0)) != 200
                or str(row.get("final_url")) != source["source_url"]
                or not notice_text_matches(Path(source["source_capture_path"]))):
            raise SystemExit("DM01_RELEVANT_OFFICIAL_CALENDAR_CAPTURE_INVALID")
        relevant_hashes.append(actual_sha)
        source_rows.append({
            "source_id": source["source_id"],
            "market": source["market"],
            "source_url": source["source_url"],
            "published_date": source["published_date"],
            "source_capture_path": source["source_capture_path"],
            "source_capture_sha256": actual_sha,
            "retrieved_at_utc": row["retrieved_at_utc"],
            "closure_ranges": source["closure_ranges"],
            "notice_content_date_crosscheck": "PASS",
        })
    sse = bridge["official_sources"][0]["closure_ranges"]
    szse = bridge["official_sources"][1]["closure_ranges"]
    if sse != szse:
        raise SystemExit("DM01_EXCHANGE_CALENDAR_CLOSURE_CONFLICT")
    revision_material = "|".join(
        [sha(BRIDGE_CONTRACT), sha(CAPTURE_MANIFEST), *sorted(relevant_hashes)]
    )
    revision = hashlib.sha256(revision_material.encode()).hexdigest()
    closure_ranges = sse
    local_now = now.astimezone(SHANGHAI)
    horizon_end = min(local_now.date().isoformat(), "2026-10-07")
    sessions = official_weekday_sessions(
        BASE_CUTOFF, horizon_end,
        official_closures=closure_ranges,
        source_revision="sha256:" + revision,
        source_sha256=revision,
    )
    accepted_dates: set[str] = set()
    with __import__("gzip").open(ROOT / UNIVERSE_R7, "rt", encoding="utf-8") as stream:
        for line in stream:
            if line.strip():
                accepted_dates.add(json.loads(line)["trade_date"])
    merged_sessions = sorted(accepted_dates | set(sessions))
    completed = latest_completed_session(merged_sessions, now=now)
    calendar_receipt = {
        "contract_id": "V4_DM01_OFFICIAL_CALENDAR_BRIDGE_RECEIPT_R1",
        "version": "1.0.0",
        "status": "PASS",
        "scope": {"start_date": BASE_CUTOFF, "end_date": horizon_end,
                  "required_boards": bridge["coverage"]["boards"]},
        "calendar_revision": "sha256:" + revision,
        "source_capture_manifest": {
            "path": CAPTURE_MANIFEST.as_posix(),
            "sha256": sha(CAPTURE_MANIFEST),
            "captured_at_utc": capture.get("observed_at_utc"),
            "as_of_date": capture.get("as_of_date"),
        },
        "sources": source_rows,
        "closure_ranges_cross_checked": sse,
        "official_sessions_after_base_cutoff": [
            day for day in sessions if day > BASE_CUTOFF
        ],
        "latest_completed_official_session": completed,
        "runtime_local": local_now.isoformat(),
        "runtime_rule": "A session is complete only at/after 15:00 Asia/Shanghai.",
        "bar_presence_used_to_infer_session": False,
        "broader_calendar_status": read(CALENDAR_CONTRACT).get("status"),
        "broader_calendar_limitation": (
            "This receipt independently verifies the captured 2026-09-17 exchange notices "
            "needed for the 2026-09-24 to 2026-09-28 bridge; it does not reseal the full "
            "2023-2026 official calendar."
        ),
    }
    return calendar_receipt, merged_sessions


def component_permissions() -> dict:
    return {
        "RAW_DAILY": {"status": "FULL_PASS", "source_receipt": "V4-02 R6 accepted", "cutoff": BASE_CUTOFF},
        "IDENTITY_UNIVERSE": {"status": "FULL_PASS", "source_receipt": "V4-01 R8.1 internal PASS", "cutoff": BASE_CUTOFF},
        "TRADING_STATUS": {"status": "FULL_PASS", "source_receipt": "V4-02 R6 accepted", "cutoff": BASE_CUTOFF},
        "ISST": {"status": "FULL_PASS", "source_receipt": "V4-02 R6 accepted", "cutoff": BASE_CUTOFF},
        "ADJUSTED_DAILY": {
            "status": "DEGRADED_PASS", "source_receipt": "V4-02 R6 accepted",
            "cutoff": BASE_CUTOFF,
            "reason": "Unsupported price-affecting actions remain per-security fail-closed.",
            "affected_reason_counts": {"CORPORATE_ACTION_REFERENCE_UNSUPPORTED": 38,
                                       "REFERENCE_CHAIN_BLOCKED_BY_UNSUPPORTED_ACTION": 1},
        },
        "PERIOD_RAW": {"status": "FULL_PASS", "source_receipt": "V4-02 R6 accepted", "cutoff": BASE_CUTOFF},
        "PERIOD_ADJUSTED": {
            "status": "DEGRADED_PASS", "source_receipt": "V4-02 R6 accepted",
            "cutoff": BASE_CUTOFF, "reason": "Adjusted readiness follows per-security adjustment disposition.",
        },
        "PRICE_LIMIT": {
            "status": "DEGRADED_PASS", "source_receipt": "V4-02 R6 accepted",
            "cutoff": BASE_CUTOFF,
            "reason": "Unsupported references remain explicit UNKNOWN in required-scope rows.",
            "unknown_rows": 77,
        },
        "SPECIAL_PHASE": {
            "status": "DEGRADED_PASS", "source_receipt": "V4-02 R6 accepted",
            "cutoff": BASE_CUTOFF,
            "reason": "Unknown special phase remains fail-closed under accepted policy.",
            "unknown_rows": 31,
        },
    }


def accepted_stage_bindings() -> dict:
    phase0 = read(PHASE0_RECEIPT)
    r8_stage = read(R8_STAGE_RECEIPT)
    r8_post = read(R8_POSTCHECK)
    v402_head = read(V402_HEAD)
    if phase0.get("phase0_status") != "FULL_PASS":
        raise SystemExit("DM01_PHASE0_BASELINE_NOT_FULL_PASS")
    if r8_stage.get("required_scope_status") != "PASS" or r8_post.get("status") != "PASS":
        raise SystemExit("DM01_R8_1_BASELINE_NOT_PASS")
    if v402_head.get("external_acceptance") != "EXTERNALLY_ACCEPTED":
        raise SystemExit("DM01_V4_02_BASELINE_NOT_EXTERNALLY_ACCEPTED")
    archive_sha256 = sha(TDX_ARCHIVE)
    if archive_sha256 != TDX_ARCHIVE_SHA256:
        raise SystemExit("DM01_ACCEPTED_TDX_PACKAGE_HASH_MISMATCH")
    return {
        "phase0": {"path": PHASE0_RECEIPT.as_posix(), "sha256": sha(PHASE0_RECEIPT)},
        "v4_01_r8_1": {"path": R8_STAGE_RECEIPT.as_posix(), "sha256": sha(R8_STAGE_RECEIPT),
                       "external_acceptance": "PENDING_EXTERNAL_REVIEW"},
        "v4_01_r8_1_postcheck": {"path": R8_POSTCHECK.as_posix(), "sha256": sha(R8_POSTCHECK)},
        "v4_01_identity_map": {"path": IDENTITY_R7.as_posix(), "sha256": sha(IDENTITY_R7)},
        "v4_01_universe": {"path": UNIVERSE_R7.as_posix(), "sha256": sha(UNIVERSE_R7)},
        "v4_02_accepted_head": {"path": V402_HEAD.as_posix(), "sha256": sha(V402_HEAD)},
        "v4_02_manifest": {"path": V402_MANIFEST.as_posix(), "sha256": sha(V402_MANIFEST)},
        "tdx_archive": {"path": TDX_ARCHIVE.as_posix(),
                        "sha256": archive_sha256,
                        "cutoff": BASE_CUTOFF},
    }


def initialize_bootstrap(bindings: dict) -> dict:
    present = [path.exists() for path in (STAGE_HEAD, DEV_HEAD, DATA_HEAD, BOOTSTRAP_MANIFEST)]
    if any(present):
        if all(present):
            data = read(DATA_HEAD)
            return {"status": "ALREADY_BOOTSTRAPPED", "accepted_trade_date": data.get("accepted_trade_date"),
                    "data_head_sha256": sha(DATA_HEAD), "stage_head_sha256": sha(STAGE_HEAD),
                    "dev_baseline_sha256": sha(DEV_HEAD), "bootstrap_manifest_sha256": sha(BOOTSTRAP_MANIFEST)}
        raise SystemExit("DM01_PARTIAL_BOOTSTRAP_POINTERS_FAIL_CLOSED")

    r8 = read(R8_STAGE_RECEIPT)
    r6 = read(Path("reports/v4_02/V4_02_FINAL_EXTERNAL_ACCEPTANCE_R6.json"))
    phase0 = read(PHASE0_RECEIPT)
    stage_payload = {
        "contract_id": "V4_STAGE_ACCEPTED_HEAD_V1",
        "version": "1.0.0",
        "status": "READY_FOR_EXTERNAL_REVIEW",
        "technical_baseline": "DA-MSR-V4.2.2-CODEX-REV2",
        "phase0_status": phase0["phase0_status"],
        "v4_01_status": r8["status"],
        "v4_01_external_acceptance": r8.get("external_acceptance", "PENDING_EXTERNAL_REVIEW"),
        "v4_02_status": (
            "PASS" if r6.get("acceptance_result", {}).get("external_acceptance") == "EXTERNALLY_ACCEPTED"
            and r6.get("stage_contract", {}).get("required_scope_result") == "PASS" else "BLOCKED"
        ),
        "v4_02_external_acceptance": "EXTERNALLY_ACCEPTED",
        "source_cutoffs": {"V4-01": BASE_CUTOFF, "V4-02": BASE_CUTOFF},
        "bindings": bindings,
        "data_head_must_not_move_this_pointer": True,
        "dev_baseline_input_head": INPUT_HEAD,
    }
    stage_sha = atomic(STAGE_HEAD, stage_payload)
    bootstrap_payload = {
        "contract_id": "V4_DM01_BOOTSTRAP_MANIFEST_R1",
        "version": "1.0.0",
        "status": "CANDIDATE_MANIFEST_READY",
        "bootstrap_cutoff": BASE_CUTOFF,
        "stage_accepted_head": {"path": STAGE_HEAD.as_posix(), "sha256": stage_sha},
        "parent_artifacts": bindings,
        "component_cutoffs": {name: BASE_CUTOFF for name in CAPABILITIES},
        "large_historical_files_copied": False,
        "writes": ["manifest and pointer metadata only"],
        "stage_00_01_02_modified": False,
        "v4_03_implementation_started": False,
        "tdx_root_write_count": 0,
    }
    bootstrap_sha = atomic(BOOTSTRAP_MANIFEST, bootstrap_payload)
    dev_payload = {
        "contract_id": "V4_DEV_BASELINE_HEAD_V1",
        "version": "1.0.0",
        "baseline_id": "V4_DEV_BASELINE_R1_20260928",
        "created_from_input_commit": INPUT_HEAD,
        "accepted_data_cutoff": BASE_CUTOFF,
        "bootstrap_manifest": {"path": BOOTSTRAP_MANIFEST.as_posix(), "sha256": bootstrap_sha},
        "stage_accepted_head_sha256": stage_sha,
        "immutable_after_initialization": True,
        "data_head_updates_move_this_pointer": False,
    }
    dev_sha = atomic(DEV_HEAD, dev_payload)
    source_revision = canonical_digest({
        "contract_sha256": sha(CONTRACT), "bootstrap_manifest_sha256": bootstrap_sha,
        "stage_accepted_head_sha256": stage_sha,
    })
    candidate = build_data_head(
        trade_date=BASE_CUTOFF,
        source_revision=source_revision,
        canonical_data_revision=source_revision,
        manifest_path=BOOTSTRAP_MANIFEST.as_posix(),
        manifest_sha256=bootstrap_sha,
        parent_head_sha256=None,
        stage_accepted_head_sha256=stage_sha,
        dev_baseline_sha256=dev_sha,
        component_permissions=component_permissions(),
    )
    data_sha = atomic(DATA_HEAD, candidate)
    return {"status": "BOOTSTRAPPED", "accepted_trade_date": BASE_CUTOFF,
            "data_head_sha256": data_sha, "stage_head_sha256": stage_sha,
            "dev_baseline_sha256": dev_sha, "bootstrap_manifest_sha256": bootstrap_sha}


def main() -> int:
    now = datetime.now(timezone.utc)
    calendar_receipt, official_sessions = build_calendar_bridge(now)
    bindings = accepted_stage_bindings()
    bootstrap_result = initialize_bootstrap(bindings)
    current_head = read(DATA_HEAD)
    last_accepted = str(current_head.get("accepted_trade_date") or "")
    latest_complete = calendar_receipt.get("latest_completed_official_session")
    if latest_complete is None:
        latest_complete = last_accepted
    if latest_complete < last_accepted:
        latest_complete = last_accepted
    plan = plan_catch_up(
        official_sessions=official_sessions,
        last_accepted_trade_date=last_accepted,
        target_cutoff=latest_complete,
    )
    blocked = []
    ready = list(plan["promotable_sessions"])
    if ready:
        readiness = source_readiness(
            trade_date=ready[0],
            tdx_available_through=BASE_CUTOFF,
            accepted_package_available_through=BASE_CUTOFF,
            calendar_session_confirmed=True,
        )
        if readiness["status"] != "READY":
            blocked = ready
            ready = []
            plan["status"] = "BLOCKED_SOURCE_NOT_READY"
            plan["promotable_sessions"] = []
            plan["blocked_sessions"] = blocked
        else:
            raise SystemExit("DM01_INCREMENTAL_COMPONENT_BUILDERS_REQUIRED")

    run_date = datetime.now(SHANGHAI).date().isoformat()
    run_dir = Path(f"reports/v4_dm01/{run_date}")
    calendar_path = run_dir / "calendar_bridge_receipt.json"
    calendar_sha = atomic(calendar_path, calendar_receipt)
    bootstrap_path = run_dir / "bootstrap_receipt.json"
    bootstrap_receipt = {
        "contract_id": "V4_DM01_BOOTSTRAP_RECEIPT_R1",
        "version": "1.0.0",
        "status": bootstrap_result["status"],
        "bootstrap_cutoff": BASE_CUTOFF,
        "parent_bindings": bindings,
        "bootstrap_manifest": {"path": BOOTSTRAP_MANIFEST.as_posix(), "sha256": sha(BOOTSTRAP_MANIFEST)},
        "stage_head": {"path": STAGE_HEAD.as_posix(), "sha256": sha(STAGE_HEAD)},
        "dev_baseline_head": {"path": DEV_HEAD.as_posix(), "sha256": sha(DEV_HEAD)},
        "data_head": {"path": DATA_HEAD.as_posix(), "sha256": sha(DATA_HEAD)},
        "large_historical_files_copied": False,
        "tdx_root_write_count": 0,
    }
    bootstrap_receipt_sha = atomic(bootstrap_path, bootstrap_receipt)
    session_receipt = {
        "contract_id": "V4_DM01_SESSION_DISCOVERY_RECEIPT_R1",
        "version": "1.0.0",
        "status": "PASS" if plan["status"] == "READY" else "BLOCKED",
        "calendar_receipt": {"path": calendar_path.as_posix(), "sha256": calendar_sha},
        "official_sessions_after_base_cutoff": calendar_receipt["official_sessions_after_base_cutoff"],
        "target_cutoff": latest_complete,
        "candidate_sessions": plan["candidate_sessions"],
        "processed_sessions": ready,
        "blocked_sessions": blocked,
        "not_completed_sessions": [
            day for day in calendar_receipt["official_sessions_after_base_cutoff"]
            if latest_complete < day
        ],
        "ordering": {"strict": plan["strictly_sequential"], "skip_after_blocked_forbidden": True},
        "session_truth_source": calendar_receipt["calendar_revision"],
    }
    session_path = run_dir / "session_discovery_receipt.json"
    session_sha = atomic(session_path, session_receipt)
    adjustment_path = run_dir / "adjustment_impact_receipt.json"
    adjustment_sha = atomic(adjustment_path, {
        "contract_id": "V4_DM01_ADJUSTMENT_IMPACT_RECEIPT_R1",
        "status": "NO_NEW_SESSION_NO_IMPACT",
        "impact_set": [],
        "full_market_historical_rebuild": False,
    })
    period_path = run_dir / "period_impact_receipt.json"
    period_sha = atomic(period_path, {
        "contract_id": "V4_DM01_PERIOD_IMPACT_RECEIPT_R1",
        "status": "NO_NEW_SESSION_NO_PERIOD_CHANGE",
        "period_revisions": [],
        "closed_raw_periods_mutated": False,
    })
    blocked_source = any(
        day in blocked for day in plan.get("candidate_sessions", [])
    )
    e2e_status = "BLOCKED_SOURCE_NOT_READY" if blocked_source else "PASS_NOOP_ALREADY_ACCEPTED"
    e2e = {
        "contract_id": "V4_DM01_INITIAL_E2E_RECEIPT_R1",
        "version": "1.0.0",
        "status": e2e_status,
        "bootstrap_cutoff": BASE_CUTOFF,
        "latest_completed_session": latest_complete,
        "processed_sessions": ready,
        "blocked_sessions": blocked,
        "source_freeze_receipts": [],
        "per_session_build_receipts": [],
        "adjustment_impact_receipt": {"path": adjustment_path.as_posix(), "sha256": adjustment_sha},
        "period_impact_receipt": {"path": period_path.as_posix(), "sha256": period_sha},
        "bootstrap_receipt": {"path": bootstrap_path.as_posix(), "sha256": bootstrap_receipt_sha},
        "session_discovery_receipt": {"path": session_path.as_posix(), "sha256": session_sha},
        "data_head_sha256": sha(DATA_HEAD),
        "data_head_moved_after_bootstrap": bool(ready),
        "source_readiness": (
            source_readiness(trade_date=blocked[0], tdx_available_through=BASE_CUTOFF,
                             accepted_package_available_through=BASE_CUTOFF,
                             calendar_session_confirmed=True)
            if blocked else {"status": "NO_NEW_COMPLETED_SESSION"}
        ),
        "component_permissions": component_permissions(),
        "stage_00_01_02_modified": False,
        "v4_03_implementation_started": False,
        "tdx_root_write_count": 0,
    }
    e2e_path = run_dir / "initial_e2e_receipt.json"
    e2e_sha = atomic(e2e_path, e2e)
    summary = {
        "contract_id": "V4_DM01_RUN_SUMMARY_R1",
        "version": "1.0.0",
        "status": e2e_status,
        "contract": {"path": CONTRACT.as_posix(), "sha256": sha(CONTRACT)},
        "head_contract": {"path": HEAD_CONTRACT.as_posix(), "sha256": sha(HEAD_CONTRACT)},
        "calendar_bridge": {"path": calendar_path.as_posix(), "sha256": calendar_sha},
        "bootstrap_receipt": {"path": bootstrap_path.as_posix(), "sha256": bootstrap_receipt_sha},
        "session_discovery_receipt": {"path": session_path.as_posix(), "sha256": session_sha},
        "initial_e2e_receipt": {"path": e2e_path.as_posix(), "sha256": e2e_sha},
        "bootstrap_cutoff": BASE_CUTOFF,
        "latest_data_cutoff": current_head.get("accepted_trade_date"),
        "processed_sessions": ready,
        "blocked_sessions": blocked,
        "not_completed_sessions": session_receipt["not_completed_sessions"],
        "calendar_status": calendar_receipt["status"],
        "tdx_root_write_count": 0,
        "next_stage": "DM01_INDEPENDENT_POSTCHECK_AND_FINAL_RECEIPT",
    }
    run_summary_path = run_dir / "run_summary.json"
    run_summary_sha = atomic(run_summary_path, summary)
    print(json.dumps({
        "status": e2e_status,
        "bootstrap": bootstrap_result["status"],
        "latest_completed_session": latest_complete,
        "processed_sessions": ready,
        "blocked_sessions": blocked,
        "not_completed_sessions": session_receipt["not_completed_sessions"],
        "summary": run_summary_path.as_posix(),
        "summary_sha256": run_summary_sha,
    }, ensure_ascii=False))
    return 0 if e2e_status == "PASS_NOOP_ALREADY_ACCEPTED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
