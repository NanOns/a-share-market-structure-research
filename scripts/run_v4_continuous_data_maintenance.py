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
)
from workbench_analysis.daily_source_orchestrator import evaluate_daily_source_readiness  # noqa: E402
from workbench_analysis.daily_source_freeze import source_freeze_complete_v2  # noqa: E402
from workbench_analysis.baostock_runtime_acceptance import (  # noqa: E402
    load_runtime_acceptance_manifest,
    runtime_acceptance_error,
)
from workbench_analysis.baostock_supplemental import package_metadata  # noqa: E402
from workbench_analysis.daily_data_head import (  # noqa: E402
    CAPABILITIES,
    build_data_head,
    canonical_digest,
    read_json,
    write_json_atomic,
)
from tdx.day_reader import read_edge_records  # noqa: E402

CONTRACT = Path("config/v4_continuous_data_maintenance_v1.json")
DAILY_CONTRACT = Path("config/v4_continuous_data_maintenance_v2.json")
SOURCE_FREEZE_CONTRACT = Path("config/v4_daily_source_freeze_v2.json")
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


def discover_local_tdx_coverage() -> dict:
    """Diagnostic only; this local-client scan never gates daily source readiness."""
    latest_by_file: dict[str, int] = {}
    invalid = 0
    for market in ("sh", "sz"):
        folder = TDX_ROOT / "vipdoc" / market / "lday"
        if not folder.is_dir():
            continue
        for path in folder.glob(f"{market}[0-9][0-9][0-9][0-9][0-9][0-9].day"):
            try:
                _, last = read_edge_records(path)
                datetime.strptime(str(last.trade_date), "%Y%m%d")
                latest_by_file[path.name] = int(last.trade_date)
            except (OSError, ValueError):
                invalid += 1
    max_date = max(latest_by_file.values(), default=None)
    return {
        "root": str(TDX_ROOT),
        "read_only": True,
        "eligible_daily_file_count": len(latest_by_file),
        "invalid_or_unreadable_daily_file_count": invalid,
        "latest_tail_date": (datetime.strptime(str(max_date), "%Y%m%d").date().isoformat()
                             if max_date is not None else None),
        "file_count_at_latest_tail_date": sum(value == max_date for value in latest_by_file.values()),
        "file_count_after_bootstrap_cutoff": sum(value > int(BASE_CUTOFF.replace("-", ""))
                                                  for value in latest_by_file.values()),
        "tail_date_means_complete_market_session": False,
        "readiness_role": "LOCAL_CLIENT_DIAGNOSTIC_ONLY",
    }


def discover_official_tdx_capture(trade_date: str) -> dict | None:
    """Resolve the newest immutable official page/package capture for a session."""
    folder = ROOT / "data/v4/source_snapshots/tdx" / trade_date.replace("-", "")
    candidates = []
    if not folder.is_dir():
        return None
    for receipt_path in folder.glob("capture-*/capture_receipt.json"):
        try:
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if receipt.get("target_date") == trade_date:
            candidates.append((str(receipt.get("observed_at") or ""), receipt))
    if not candidates:
        return None
    receipt = max(candidates, key=lambda item: item[0])[1]
    if receipt.get("status") not in {"TDX_PACKAGE_READY", "NOOP_SOURCE_ALREADY_FROZEN"}:
        return receipt
    download = receipt.get("download") or {}
    package_path = Path(str(download.get("path") or ""))
    if not package_path.is_file() or receipt.get("zip_validation", {}).get("crc_integrity") != "PASS":
        return {**receipt, "status": "WAIT_TDX_PUBLICATION", "reason": "PACKAGE_OR_CRC_EVIDENCE_MISSING"}
    digest = hashlib.sha256()
    with package_path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    if digest.hexdigest() != download.get("sha256"):
        return {**receipt, "status": "WAIT_TDX_PUBLICATION", "reason": "PACKAGE_HASH_MISMATCH"}
    return receipt


def discover_baostock_daily_capture(trade_date: str) -> dict | None:
    """Resolve a frozen date-level batch snapshot; no row-wise fallback is allowed."""
    folder = ROOT / "data/v4/source_snapshots/baostock" / trade_date.replace("-", "")
    if not folder.is_dir():
        return None
    candidates = []
    for snapshot in folder.glob("sha256-*/daily_update.json"):
        try:
            record = json.loads(snapshot.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if (record.get("trade_date") == trade_date and record.get("provider_date") == trade_date
                and record.get("status") in {"BAOSTOCK_DAILY_SNAPSHOT_READY", "NOOP_SOURCE_ALREADY_FROZEN"}
                and record.get("daily_rows") and "adjustment_factor_rows" in record):
            candidates.append(record)
    return max(candidates, key=lambda item: str(item.get("received_at") or "")) if candidates else None


def discover_baostock_runtime_acceptance(trade_date: str) -> tuple[dict | None, str | None]:
    """Accept only an exact-date live smoke receipt bound to this installed SDK/auth mode."""
    contract = read(Path("config/baostock_supplemental_contract_v1.json"))
    settings = contract.get("dm01_daily_updates", {})
    template = settings.get("runtime_acceptance_manifest_template")
    if settings.get("runtime_acceptance_contract") != "BAOSTOCK_DAILY_UPDATE_RUNTIME_ACCEPTANCE_V1" or not template:
        return None, "RUNTIME_ACCEPTANCE_CONTRACT_INVALID"
    path = ROOT / str(template).replace("{YYYYMMDD}", trade_date.replace("-", ""))
    try:
        manifest = load_runtime_acceptance_manifest(path, project_root=ROOT)
    except ValueError as exc:
        return None, str(exc)
    auth_mode = str(manifest.get("auth_mode") or "")
    error = runtime_acceptance_error(manifest, sdk=package_metadata(), auth_mode=auth_mode)
    if error:
        return None, error
    if manifest.get("live_smoke", {}).get("target_date") != trade_date:
        return None, "RUNTIME_ACCEPTANCE_TARGET_DATE_MISMATCH"
    return manifest, None


def discover_accepted_gbbq_snapshot(trade_date: str) -> dict | None:
    probe_path = ROOT / "reports/v4_dm01" / trade_date / "gbbq_revision_probe_receipt_v1.json"
    try:
        probe = json.loads(probe_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if probe.get("trade_date") != trade_date or probe.get("status") != "REUSE_ACCEPTED_GBBQ_SNAPSHOT":
        return probe
    manifest_path = Path(str(probe.get("accepted_manifest_path") or ""))
    try:
        if sha(manifest_path) != probe.get("accepted_manifest_sha256"):
            return {**probe, "status": "BLOCKED_GBBQ_ACCEPTED_MANIFEST_DIGEST_MISMATCH"}
        manifest = read(manifest_path)
        if manifest.get("snapshot_id") != probe.get("accepted_snapshot_id"):
            return {**probe, "status": "BLOCKED_GBBQ_ACCEPTED_SNAPSHOT_ID_MISMATCH"}
    except (OSError, ValueError):
        return {**probe, "status": "BLOCKED_GBBQ_ACCEPTED_MANIFEST_UNREADABLE"}
    return {**probe, "status": "REUSE_ACCEPTED_GBBQ_SNAPSHOT"}


def discover_lifecycle_snapshot(trade_date: str) -> dict | None:
    artifact = ROOT / "reports/v4_dm01" / trade_date / "current_lifecycle_snapshot.json"
    receipt_path = ROOT / "reports/v4_dm01" / trade_date / "current_lifecycle_snapshot_receipt.json"
    try:
        data = read(artifact)
        receipt = read(receipt_path)
    except (OSError, ValueError):
        return None
    if (data.get("trade_date") != trade_date or data.get("contract_id") != "CURRENT_LIFECYCLE_SNAPSHOT_V1"
            or data.get("status") not in {"READY", "DEGRADED_PASS"}
            or receipt.get("artifact_sha256") != sha(artifact)):
        return None
    return data


def discover_special_phase_snapshot(trade_date: str) -> dict | None:
    receipt_path = ROOT / "reports/v4_dm01" / trade_date / "special_phase_source_manifest_receipt_v1.json"
    try:
        receipt = read(receipt_path)
        artifact = Path(str(receipt.get("manifest_path") or ""))
        data = read(artifact)
    except (OSError, ValueError):
        return None
    if (receipt.get("trade_date") != trade_date or receipt.get("status") not in {"READY", "DEGRADED_PASS"}
            or data.get("trade_date") != trade_date or data.get("status") not in {"READY", "DEGRADED_PASS"}
            or sha(artifact) != receipt.get("manifest_sha256")):
        return None
    return data


def discover_source_freeze(trade_date: str) -> dict | None:
    path = ROOT / "reports/v4_dm01" / trade_date / "daily_source_freeze_v2.json"
    try:
        manifest = read(path)
    except (OSError, ValueError):
        return None
    if manifest.get("trade_date") != trade_date or not source_freeze_complete_v2(manifest):
        return None
    return manifest


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
    local_tdx_coverage = discover_local_tdx_coverage()
    component_builder_block = False
    official_tdx_capture = None
    baostock_capture = None
    baostock_runtime_acceptance = None
    baostock_runtime_rejection = None
    gbbq_capture = None
    lifecycle = None
    special_phase = None
    source_freeze = None
    source_readiness_result = {"status": "NO_NEW_COMPLETED_SESSION"}
    source_wait_status = None
    if ready:
        target = ready[0]
        official_tdx_capture = discover_official_tdx_capture(target)
        baostock_capture = discover_baostock_daily_capture(target)
        baostock_runtime_acceptance, baostock_runtime_rejection = discover_baostock_runtime_acceptance(target)
        gbbq_capture = discover_accepted_gbbq_snapshot(target)
        lifecycle = discover_lifecycle_snapshot(target)
        special_phase = discover_special_phase_snapshot(target)
        source_readiness_result = evaluate_daily_source_readiness(
            trade_date=target,
            observed_at=now.isoformat(),
            official_session_confirmed=True,
            tdx_capture=official_tdx_capture,
            baostock_capture=baostock_capture,
            baostock_capability_accepted=baostock_runtime_acceptance is not None,
            gbbq_snapshot=gbbq_capture,
            lifecycle_snapshot=lifecycle,
            special_phase_snapshot=special_phase,
        )
        source_freeze = discover_source_freeze(target) if source_readiness_result.get("status") == "SOURCE_FREEZE_READY" else None
        if source_readiness_result.get("status") == "SOURCE_FREEZE_READY" and source_freeze is None:
            source_readiness_result = {**source_readiness_result, "status": "WAIT_DAILY_SOURCE_FREEZE_V2",
                                       "reason": "COMPLETE_HASH_VERIFIED_SOURCE_FREEZE_NOT_AVAILABLE"}
        if source_readiness_result["status"] != "SOURCE_FREEZE_READY":
            blocked = ready
            ready = []
            source_wait_status = source_readiness_result["status"]
            plan["status"] = source_wait_status
            plan["promotable_sessions"] = []
            plan["blocked_sessions"] = blocked
        else:
            # Builder contracts do not promote placeholders. Keep the target held
            # and emit an auditable blocker until all production component builders
            # are bound to the accepted V4-01/V4-02 runtime.
            component_builder_block = True
            blocked = ready
            ready = []
            plan["status"] = "BLOCKED_COMPONENT_BUILDERS_NOT_WIRED"
            plan["promotable_sessions"] = []
            plan["blocked_sessions"] = blocked

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
        "status": "PASS" if plan["status"] in {"READY", "SOURCE_FREEZE_READY"} else "WAITING" if source_wait_status else "BLOCKED",
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
    blocked_source = bool(blocked and source_wait_status)
    e2e_status = (source_wait_status if blocked_source else
                  "BLOCKED_COMPONENT_BUILDERS_NOT_WIRED" if component_builder_block else
                  "PASS_NOOP_ALREADY_ACCEPTED")
    source_freeze_receipts = []
    if source_freeze is not None:
        source_freeze_path = ROOT / "reports/v4_dm01" / target / "daily_source_freeze_v2.json"
        source_freeze_receipts.append({"path": source_freeze_path.as_posix(), "sha256": sha(source_freeze_path)})
    tdx_delta_receipt = None
    if official_tdx_capture and official_tdx_capture.get("snapshot_id"):
        package_path = Path(str((official_tdx_capture.get("download") or {}).get("path") or ""))
        candidate = package_path.parent / "delta" / target.replace("-", "") / "tdx_delta_build_receipt.json"
        if candidate.is_file():
            tdx_delta_receipt = {"path": candidate.as_posix(), "sha256": sha(candidate)}
    e2e = {
        "contract_id": "V4_DM01_INITIAL_E2E_RECEIPT_R1",
        "version": "1.0.0",
        "status": e2e_status,
        "bootstrap_cutoff": BASE_CUTOFF,
        "latest_completed_session": latest_complete,
        "processed_sessions": ready,
        "blocked_sessions": blocked,
        "source_freeze_receipts": source_freeze_receipts,
        "per_session_build_receipts": [],
        "adjustment_impact_receipt": {"path": adjustment_path.as_posix(), "sha256": adjustment_sha},
        "period_impact_receipt": {"path": period_path.as_posix(), "sha256": period_sha},
        "bootstrap_receipt": {"path": bootstrap_path.as_posix(), "sha256": bootstrap_receipt_sha},
        "session_discovery_receipt": {"path": session_path.as_posix(), "sha256": session_sha},
        "data_head_sha256": sha(DATA_HEAD),
        "data_head_moved_after_bootstrap": bool(ready),
        "source_readiness": source_readiness_result,
        "official_tdx_package_capture": official_tdx_capture,
        "tdx_delta_build_receipt": tdx_delta_receipt,
        "baostock_daily_capture": baostock_capture,
        "gbbq_revision_probe": discover_accepted_gbbq_snapshot(target) if ready or blocked else None,
        "lifecycle_snapshot": lifecycle,
        "special_phase_source_manifest": special_phase,
        "baostock_runtime_acceptance": (None if baostock_runtime_acceptance is None else {
            "contract_id": baostock_runtime_acceptance.get("contract_id"),
            "manifest_sha256": baostock_runtime_acceptance.get("manifest_sha256"),
            "auth_mode": baostock_runtime_acceptance.get("auth_mode"),
            "runtime": baostock_runtime_acceptance.get("runtime"),
        }),
        "baostock_runtime_rejection": baostock_runtime_rejection,
        "local_tdx_coverage_discovery": {**local_tdx_coverage, "readiness_role": "LOCAL_CLIENT_DIAGNOSTIC_ONLY"},
        "incremental_component_builders": "NOT_WIRED_FAIL_CLOSED",
        "stage_contract": {"path": DAILY_CONTRACT.as_posix(), "sha256": sha(DAILY_CONTRACT)},
        "source_freeze_contract": {"path": SOURCE_FREEZE_CONTRACT.as_posix(), "sha256": sha(SOURCE_FREEZE_CONTRACT)},
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
        "contract": {"path": DAILY_CONTRACT.as_posix(), "sha256": sha(DAILY_CONTRACT)},
        "bootstrap_contract": {"path": CONTRACT.as_posix(), "sha256": sha(CONTRACT)},
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
    return 0 if e2e_status in {"PASS_NOOP_ALREADY_ACCEPTED", "WAIT_MARKET_CLOSE", "WAIT_TDX_PUBLICATION",
                               "WAIT_BAOSTOCK_DAILY_UPDATE", "WAIT_GBBQ_SNAPSHOT_IF_REQUIRED",
                               "WAIT_IDENTITY_LIFECYCLE_SNAPSHOT", "WAIT_SPECIAL_PHASE_SNAPSHOT"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
