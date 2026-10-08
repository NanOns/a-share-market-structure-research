from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]

from workbench_analysis.daily_source_orchestrator import evaluate_daily_source_readiness  # noqa: E402
from workbench_analysis.tdx_official_daily_source import capture_tdx_official_daily_package  # noqa: E402
from workbench_analysis.daily_data_head import write_json_atomic  # noqa: E402
from workbench_analysis.baostock_runtime_acceptance import (  # noqa: E402
    load_runtime_acceptance_manifest,
    runtime_acceptance_error,
)
from workbench_analysis.baostock_supplemental import package_metadata  # noqa: E402
from workbench_analysis.dm01_runtime_r4 import session_gate, validate_registry, BUILDERS, current_parent, calendar, build_candidate, promote, ref, POLICY, HEAD
from workbench_analysis.dm01_sources_r4 import project_source_freeze  # noqa: E402


def _runtime_acceptance(target_date: str) -> tuple[dict | None, str | None]:
    contract = json.loads((ROOT / "config/baostock_supplemental_contract_v1.json").read_text(encoding="utf-8"))
    settings = contract.get("dm01_daily_updates", {})
    template = settings.get("runtime_acceptance_manifest_template")
    if not template:
        return None, "BAOSTOCK_RUNTIME_ACCEPTANCE_PATH_NOT_CONFIGURED"
    manifest_path = ROOT / str(template).replace("{YYYYMMDD}", target_date.replace("-", ""))
    try:
        manifest = load_runtime_acceptance_manifest(manifest_path, project_root=ROOT, tdx_root=Path("D:/new_tdx"))
    except ValueError as exc:
        return None, str(exc)
    error = runtime_acceptance_error(manifest, sdk=package_metadata(), auth_mode=str(manifest.get("auth_mode") or ""))
    if error:
        return None, error
    if manifest.get("live_smoke", {}).get("target_date") != target_date:
        return None, "BAOSTOCK_RUNTIME_ACCEPTANCE_TARGET_DATE_MISMATCH"
    return manifest, None


def _run_json_cli(*args: str) -> tuple[int, dict]:
    result = subprocess.run([sys.executable, '-X', 'utf8', *args], cwd=ROOT, capture_output=True, text=True, encoding='utf8', timeout=900)
    lines = [line for line in result.stdout.splitlines() if line.strip()]
    try:
        payload = json.loads(lines[-1]) if lines else {}
    except ValueError:
        payload = {"status": "BLOCKED_CLI_OUTPUT_INVALID", "stderr": result.stderr[-300:]}
    return result.returncode, payload


def _run_baostock_daily_capture(target_date: str) -> tuple[dict | None, dict | None, str | None]:
    smoke_code, smoke = _run_json_cli("scripts/accept_v4_dm01_baostock_runtime.py", "--target-date", target_date)
    if smoke_code != 0 or smoke.get("status") != "ACCEPTED":
        return None, smoke, str(smoke.get("reason") or smoke.get("status") or "BAOSTOCK_RUNTIME_SMOKE_NOT_ACCEPTED")
    manifest, error = _runtime_acceptance(target_date)
    if manifest is None:
        return None, smoke, error
    capture_code, capture = _run_json_cli("scripts/capture_baostock_daily_update.py", "--target-date", target_date)
    if capture_code != 0 or capture.get("status") not in {"BAOSTOCK_DAILY_SNAPSHOT_READY", "NOOP_SOURCE_ALREADY_FROZEN"}:
        return None, smoke, str(capture.get("reason") or capture.get("status") or "BAOSTOCK_DAILY_CAPTURE_NOT_READY")
    folder = ROOT / "data/v4/source_snapshots/baostock" / target_date.replace("-", "")
    snapshot_file = folder / capture["snapshot_id"] / "daily_update.json"
    try:
        record = json.loads(snapshot_file.read_text(encoding="utf-8"))
    except (OSError, ValueError, KeyError) as exc:
        return None, smoke, "BAOSTOCK_DAILY_SNAPSHOT_READBACK_FAILED:" + type(exc).__name__
    return record, smoke, None


def _accepted_gbbq_snapshot(target_date: str) -> dict | None:
    probe_path = ROOT / "reports/v4_dm01" / target_date / "gbbq_revision_probe_receipt_v1.json"
    try:
        probe = json.loads(probe_path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return None
    if probe.get("trade_date") != target_date or probe.get("status") != "REUSE_ACCEPTED_GBBQ_SNAPSHOT":
        return probe
    manifest_path = Path(str(probe.get("accepted_manifest_path") or ""))
    try:
        if hashlib.sha256(manifest_path.read_bytes()).hexdigest() != probe.get("accepted_manifest_sha256"):
            return {**probe, "status": "BLOCKED_GBBQ_ACCEPTED_MANIFEST_DIGEST_MISMATCH"}
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("snapshot_id") != probe.get("accepted_snapshot_id"):
            return {**probe, "status": "BLOCKED_GBBQ_ACCEPTED_SNAPSHOT_ID_MISMATCH"}
    except (OSError, ValueError):
        return {**probe, "status": "BLOCKED_GBBQ_ACCEPTED_MANIFEST_UNREADABLE"}
    return {**probe, "status": "REUSE_ACCEPTED_GBBQ_SNAPSHOT"}


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the source-gated V4-DM-01 daily increment entrypoint.")
    parser.add_argument("--target-date", required=True)
    parser.add_argument("--snapshot-root", type=Path, default=ROOT / "data/v4/source_snapshots")
    parser.add_argument("--receipt-dir", type=Path, default=ROOT / "reports/v4_dm01")
    parser.add_argument("--active-source-policy", action="store_true",
                        help="Run versioned R4 corrected source capture independently of canonical admission.")
    args = parser.parse_args()
    now = datetime.now(timezone.utc).replace(microsecond=0)
    local = now.astimezone(ZoneInfo("Asia/Shanghai"))
    try:
        gate = session_gate(args.target_date, now.isoformat(), ROOT)
        if gate['status'] == 'WAIT_MARKET_CLOSE':
            print(json.dumps(gate)); return 0
    except (ValueError, OSError, KeyError) as error:
        print(json.dumps(dict(status='BLOCKED',reason=str(error),source_requests=0,data_head_moved=False))); return 2
    official_sessions = calendar(ROOT)['session_dates']
    try:
        builder_registry_result = validate_registry(BUILDERS, ROOT)
    except (ValueError, OSError, KeyError) as error:
        # A stale producer seal blocks building, not independent source capture.
        builder_registry_result = dict(status='BLOCKED_BUILDER_REGISTRY', reason=str(error))
    acquisition = None
    if args.active_source_policy and args.target_date in official_sessions:
        from workbench_analysis.market_source_acquisition import acquire
        try:
            acquisition = acquire(ROOT, [args.target_date], args.receipt_dir / args.target_date / 'active_source_capture')
        except (ValueError, OSError) as error:
            acquisition = dict(status='SOURCE_CAPTURE_BLOCKED', reason=str(error))
    candidate_result = None
    promotion_result = None
    bao = None
    bao_smoke = None
    bao_error = None
    runtime_manifest = None
    runtime_error = None
    gbbq_probe = None
    tdx_delta_build = None
    lifecycle_snapshot = None
    lifecycle_receipt = None
    special_phase_snapshot = None
    special_phase_receipt = None
    source_freeze = None
    if args.target_date not in official_sessions:
        readiness = {"status": "BLOCKED_OFFICIAL_SESSION_NOT_VERIFIED", "trade_date": args.target_date}
        tdx = None
    else:
        # Before close the state machine returns without opening a source request.
        if local.date().isoformat() == args.target_date and local.time() < datetime.strptime("15:00:00", "%H:%M:%S").time():
            tdx = None
        else:
            try:
                tdx = capture_tdx_official_daily_package(
                    target_date=args.target_date,
                    snapshot_root=args.snapshot_root,
                    tdx_root=Path("D:/new_tdx"),
                )
            except (ValueError, OSError) as error:
                tdx = dict(status='SOURCE_CAPTURE_BLOCKED', reason=str(error), target_date=args.target_date)
        if local.date().isoformat() == args.target_date and local.time() >= datetime.strptime("15:00:00", "%H:%M:%S").time():
            _run_json_cli("scripts/probe_v4_dm01_gbbq_revision.py", "--target-date", args.target_date)
            gbbq_probe_path = ROOT / "reports/v4_dm01" / args.target_date / "gbbq_revision_probe_receipt_v1.json"
            if gbbq_probe_path.is_file():
                gbbq_probe = json.loads(gbbq_probe_path.read_text(encoding="utf-8"))
        if tdx and tdx.get("status") in {"TDX_PACKAGE_READY", "NOOP_SOURCE_ALREADY_FROZEN"}:
            delta_code, tdx_delta_build = _run_json_cli(
                "scripts/build_dm01_r4_tdx_delta.py", "--target-date", args.target_date,
                "--current-snapshot-id", str(tdx.get("snapshot_id") or ""),
            )
            if delta_code != 0:
                tdx_delta_build = {**tdx_delta_build, "status": tdx_delta_build.get("status", "BLOCKED_TDX_DELTA_NOT_READY")}
            if delta_code == 0 and tdx_delta_build.get("status") == "READY":
                bao, bao_smoke, bao_error = _run_baostock_daily_capture(args.target_date)
                runtime_manifest, runtime_error = _runtime_acceptance(args.target_date)
            if bao is not None:
                lifecycle_code, lifecycle_receipt = _run_json_cli(
                    "scripts/build_v4_dm01_lifecycle_snapshot.py", "--target-date", args.target_date,
                    "--baostock-snapshot-id", str(bao.get("snapshot_id") or ""),
                )
                lifecycle_path = ROOT / "reports/v4_dm01" / args.target_date / "current_lifecycle_snapshot.json"
                if lifecycle_code == 0 and lifecycle_path.is_file():
                    lifecycle_snapshot = json.loads(lifecycle_path.read_text(encoding="utf-8"))
                    _run_json_cli("scripts/build_v4_dm01_special_phase_manifest.py", "--target-date", args.target_date)
                    special_receipt_path = ROOT / "reports/v4_dm01" / args.target_date / "special_phase_source_manifest_receipt_v1.json"
                    if special_receipt_path.is_file():
                        special_phase_receipt = json.loads(special_receipt_path.read_text(encoding="utf-8"))
                        if special_phase_receipt.get("status") in {"READY", "DEGRADED_PASS"}:
                            special_manifest_path = Path(str(special_phase_receipt.get("manifest_path") or ""))
                            if special_manifest_path.is_file():
                                special_phase_snapshot = json.loads(special_manifest_path.read_text(encoding="utf-8"))
        readiness = evaluate_daily_source_readiness(
            trade_date=args.target_date,
            observed_at=now.isoformat(),
            official_session_confirmed=True,
            tdx_capture=tdx,
            baostock_capture=bao,
            baostock_capability_accepted=(runtime_manifest is not None and bao_smoke is not None
                                          and bao_smoke.get("status") == "ACCEPTED"),
            gbbq_snapshot=_accepted_gbbq_snapshot(args.target_date),
            lifecycle_snapshot=lifecycle_snapshot,
            special_phase_snapshot=special_phase_snapshot,
        )
        if tdx and tdx.get('status') == 'SOURCE_CAPTURE_BLOCKED':
            readiness = dict(readiness, status='SOURCE_CAPTURE_BLOCKED', reason=tdx.get('reason'), head_moved=False)
        if (readiness.get("status") == "SOURCE_FREEZE_READY" and tdx and bao and gbbq_probe
                and builder_registry_result.get('status') != 'BLOCKED_BUILDER_REGISTRY'):
            tdx_capture_path = Path(str(tdx.get("receipt_path") or ""))
            gbbq_probe_path = ROOT / "reports/v4_dm01" / args.target_date / "gbbq_revision_probe_receipt_v1.json"
            freeze_code, source_freeze = _run_json_cli(
                "scripts/freeze_v4_dm01_daily_sources.py", "--target-date", args.target_date,
                "--tdx-capture-receipt", str(tdx_capture_path),
                "--bao-snapshot-id", str(bao.get("snapshot_id") or ""),
                "--gbbq-probe-receipt", str(gbbq_probe_path),
            )
            if freeze_code == 0 and source_freeze.get("status") == "SOURCE_FREEZE_READY":
                freeze_path = Path(source_freeze['manifest_path'])
                freeze = json.loads(freeze_path.read_bytes())
                bao_path = ROOT / 'data/v4/source_snapshots/baostock' / args.target_date.replace('-','') / str(bao['snapshot_id']) / 'daily_update.json'
                settings = json.loads((ROOT/'config/baostock_supplemental_contract_v1.json').read_bytes())['dm01_daily_updates']
                runtime_path = ROOT / settings['runtime_acceptance_manifest_template'].replace('{YYYYMMDD}',args.target_date.replace('-',''))
                try:
                    freeze,parent,cal,identity = project_source_freeze(ROOT,freeze,ref(ROOT,tdx_capture_path),ref(ROOT,bao_path),ref(ROOT,runtime_path))
                    candidate_result = build_candidate(parent=parent,freeze=freeze,cal=cal,identity=identity,root=ROOT,builders=BUILDERS)
                    promotion_result = promote(candidate_result['candidate'],expected_parent_sha=parent['binding']['sha256'],root=ROOT)
                    readiness = dict(readiness,status=promotion_result['status'])
                except (ValueError,OSError,KeyError,TypeError) as error:
                    readiness = dict(readiness,status='BLOCKED_R4_ALL_NINE_OR_PROMOTION',reason=str(error),head_moved=False)
            else:
                readiness = {**readiness, "status": "BLOCKED_SOURCE_FREEZE_V2_INVALID",
                             "source_freeze_error": source_freeze.get("reason") or source_freeze.get("status"),
                             "head_moved": False}
    if readiness.get('status') == 'SOURCE_FREEZE_READY' and builder_registry_result.get('status') == 'BLOCKED_BUILDER_REGISTRY':
        readiness = dict(readiness, status='BLOCKED_BUILDER_REGISTRY', reason=builder_registry_result['reason'])
    result = {
        "contract_id": "V4_DM01_SOURCE_READINESS_RECEIPT_R2",
        "version": "2.0.0",
        "status": readiness["status"],
        "stage_contract": "V4_CONTINUOUS_DATA_MAINTENANCE_V2",
        "contract_path": "config/v4_continuous_data_maintenance_v2.json",
        "contract_sha256": hashlib.sha256((ROOT / "config/v4_continuous_data_maintenance_v2.json").read_bytes()).hexdigest(),
        "target_date": args.target_date,
        "observed_at": now.isoformat(),
        "source_readiness": readiness,
        "tdx_page_capture": tdx,
        "active_source_capture": ({k: v for k, v in acquisition.items() if k not in ('local', 'queries')}
                                  if acquisition else None),
        "baostock_capture": bao,
        "baostock_runtime_acceptance": runtime_manifest,
        "baostock_runtime_error": runtime_error,
        "baostock_live_smoke": bao_smoke,
        "baostock_capture_error": bao_error,
        "gbbq_revision_probe": gbbq_probe,
        "tdx_delta_build": tdx_delta_build,
        "lifecycle_snapshot": lifecycle_snapshot,
        "lifecycle_snapshot_receipt": lifecycle_receipt,
        "special_phase_snapshot": special_phase_snapshot,
        "special_phase_source_receipt": special_phase_receipt,
        "source_freeze": source_freeze,
        "accepted_builder_registry": builder_registry_result,
        "component_builds": candidate_result,
        "promotion": promotion_result,
        "data_head_moved": bool(promotion_result and promotion_result["status"]=="PROMOTED_V2"),
        "stage_accepted_head_moved": False,
        "dev_baseline_head_moved": False,
        "tdx_root_write_count": 0,
        "next_stage": ("WIRE_REAL_ACCEPTED_COMPONENT_BUILDERS_AND_INDEPENDENT_ARTIFACT_POSTCHECK"
                       if readiness["status"] == "BLOCKED_COMPONENT_BUILDERS_NOT_WIRED"
                       else "CAPTURE_TDX_AND_BAOSTOCK_AFTER_OFFICIAL_RELEASE; BUILD_ONLY_AFTER_ALL_V2_SOURCE_FAMILIES_READY"),
    }
    receipt_dir = args.receipt_dir / args.target_date
    path = receipt_dir / "source_readiness_receipt_r2.json"
    digest = write_json_atomic(path, result, tdx_root=Path("D:/new_tdx"))
    print(json.dumps({"status": readiness["status"], "target_date": args.target_date,
                      "receipt": str(path), "receipt_sha256": digest}, ensure_ascii=False))
    return 0 if readiness["status"].startswith("WAIT_") or readiness["status"] in ("PROMOTED_V2", "NOOP_IDENTICAL_PROMOTION") else 2


if __name__ == "__main__":
    raise SystemExit(main())
