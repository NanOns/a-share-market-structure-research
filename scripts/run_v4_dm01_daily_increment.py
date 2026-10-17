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
from workbench_analysis.baostock_runtime_acceptance import (  # noqa: E402
    runtime_acceptance_error,
)
from workbench_analysis.baostock_supplemental import package_metadata  # noqa: E402
from workbench_analysis.dm01_runtime_r4 import session_gate, validate_registry, BUILDERS, current_parent, calendar, build_candidate, promote, ref, POLICY, HEAD
from workbench_analysis.dm01_sources_r4 import project_source_freeze  # noqa: E402
from common.paths import resolve_baostock_cache_root, resolve_tdx_root  # noqa: E402
from workbench_analysis.operational_daily_executor_v1 import (  # noqa: E402
    _daily_runtime_contract, _load_daily_contract_record_from_pg,
)
from workbench_db.v4_baostock_runtime_acceptance_pg_r1 import load as load_baostock_runtime_pg  # noqa: E402


def _runtime_acceptance(target_date: str) -> tuple[dict | None, str | None]:
    contract = _daily_runtime_contract(ROOT, "BAOSTOCK_SUPPLEMENTAL_SOURCE_V1", "1.1.0",
                                       "config/baostock_supplemental_contract_v1.json")
    settings = contract.get("dm01_daily_updates", {})
    template = settings.get("runtime_acceptance_manifest_template")
    if not template:
        return None, "BAOSTOCK_RUNTIME_ACCEPTANCE_PATH_NOT_CONFIGURED"
    try:
        manifest = load_baostock_runtime_pg(ROOT, target_date, sdk=package_metadata())["manifest"]
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
    if not isinstance(payload, dict):
        payload = {"status": "BLOCKED_CLI_OUTPUT_INVALID"}
    if result.returncode != 0:
        payload = {**payload, "status": payload.get("status") or "BLOCKED_CLI_EXECUTION_FAILED",
                   "exit_code": result.returncode, "stderr": result.stderr[-2000:]}
    return result.returncode, payload


def _read_baostock_daily_update_from_pg(target_date: str, snapshot_id: str,
                                       source_revision: str | None = None) -> dict:
    """Capture exact provider cache bytes once, then consume the PG readback."""
    folder=resolve_baostock_cache_root(ROOT)/"baostock"/target_date.replace("-","")
    snapshot_file=folder/snapshot_id/"daily_update.json"
    raw=snapshot_file.read_bytes()
    logical_path=f"external/baostock_daily/{target_date}/{snapshot_id}/daily_update.json"
    from workbench_db.v4_historical_source_ingress_pg_r1 import ingest_captured_bytes,read_bound
    ingested=ingest_captured_bytes(ROOT,logical_path,raw,
        source_revision=str(source_revision or snapshot_id),
        source_origin='BAOSTOCK_DAILY_CAPTURE_EXPLICIT_PROVIDER_BOUNDARY')
    return json.loads(read_bound(ROOT,logical_path,ingested['source_sha256'])['raw'])


def _run_baostock_daily_capture(target_date: str) -> tuple[dict | None, dict | None, str | None]:
    # The active DM-01 lane uses the adapter that captures exact native response
    # bytes and appends the date-bound acceptance fact to PG before returning.
    smoke_code, smoke = _run_json_cli("scripts/accept_dynamic_daily_baostock_v2.py", "--target-date", target_date)
    if smoke_code != 0 or smoke.get("status") != "ACCEPTED":
        return None, smoke, str(smoke.get("reason") or smoke.get("status") or "BAOSTOCK_RUNTIME_SMOKE_NOT_ACCEPTED")
    manifest, error = _runtime_acceptance(target_date)
    if manifest is None:
        return None, smoke, error
    capture_code, capture = _run_json_cli("scripts/capture_baostock_daily_update.py", "--target-date", target_date)
    if capture_code != 0 or capture.get("status") not in {"BAOSTOCK_DAILY_SNAPSHOT_READY", "NOOP_SOURCE_ALREADY_FROZEN"}:
        return None, smoke, str(capture.get("reason") or capture.get("status") or "BAOSTOCK_DAILY_CAPTURE_NOT_READY")
    try:
        record=_read_baostock_daily_update_from_pg(target_date,str(capture['snapshot_id']),capture.get('source_revision_id'))
    except (OSError, ValueError, KeyError, TypeError) as exc:
        return None, smoke, "BAOSTOCK_DAILY_SNAPSHOT_READBACK_FAILED:" + type(exc).__name__
    return record, smoke, None


def _accepted_gbbq_snapshot(target_date: str, stage_binding: dict | None = None) -> dict | None:
    if (not isinstance(stage_binding, dict)
            or stage_binding.get("contract_id") != "V4_DM01_STAGE_STATE_PG_R1"
            or stage_binding.get("trade_date") != target_date
            or stage_binding.get("stage") != "gbbq_revision_probe"
            or not isinstance(stage_binding.get("binding"), dict)):
        return None
    try:
        from workbench_db.v4_dm01_stage_state_pg_r1 import read_stage
        probe = read_stage(ROOT, stage_binding["binding"], trade_date=target_date,
                           stage="gbbq_revision_probe")
    except (OSError, ValueError, TypeError, KeyError):
        return None
    if probe.get("trade_date") != target_date or probe.get("status") != "REUSE_ACCEPTED_GBBQ_SNAPSHOT":
        return probe
    manifest_path = Path(str(probe.get("accepted_manifest_path") or ""))
    try:
        raw=manifest_path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != probe.get("accepted_manifest_sha256"):
            return {**probe, "status": "BLOCKED_GBBQ_ACCEPTED_MANIFEST_DIGEST_MISMATCH"}
        from workbench_db.v4_historical_source_ingress_pg_r1 import ingest_captured_bytes,read_bound
        logical_path=f"external/tdx_gbbq/{target_date}/{probe.get('accepted_snapshot_id')}/manifest.json"
        ingested=ingest_captured_bytes(ROOT,logical_path,raw,
            source_revision=str(probe.get('accepted_snapshot_id') or probe.get('accepted_manifest_sha256')),
            source_origin='TDX_GBBQ_ACCEPTED_SNAPSHOT_EXPLICIT_READ_ONLY_SOURCE_BOUNDARY')
        manifest = json.loads(read_bound(ROOT,logical_path,ingested['source_sha256'])['raw'])
        if manifest.get("snapshot_id") != probe.get("accepted_snapshot_id"):
            return {**probe, "status": "BLOCKED_GBBQ_ACCEPTED_SNAPSHOT_ID_MISMATCH"}
    except (OSError, ValueError):
        return {**probe, "status": "BLOCKED_GBBQ_ACCEPTED_MANIFEST_UNREADABLE"}
    return {**probe, "status": "REUSE_ACCEPTED_GBBQ_SNAPSHOT"}


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the source-gated V4-DM-01 daily increment entrypoint.")
    parser.add_argument("--target-date", required=True)
    parser.add_argument("--snapshot-root", type=Path, default=ROOT / "data/v4/source_snapshots")
    parser.add_argument("--v402-pg-stage-state", help="Exact accepted V4-02 PG ingress descriptor JSON")
    parser.add_argument("--active-source-policy", action="store_true",
                        help="Run versioned R4 corrected source capture independently of canonical admission.")
    parser.add_argument('--corrected-owner-repair', action='store_true',
                        help='Run the versioned reconstructed owner branch; preserve original PIT and live heads.')
    parser.add_argument('--typed-scope-v2',action='store_true',
                        help='Versioned typed source and corrected-only capture; cannot promote old PIT head.')
    args = parser.parse_args()
    if args.corrected_owner_repair:
        from workbench_analysis.corrected_owner_pipeline import run_corrected_owner_pipeline
        try:
            result=run_corrected_owner_pipeline(ROOT,target_date=args.target_date)
            print(json.dumps(result));return 2 if not result.get('production_admission') else 0
        except (ValueError,OSError,KeyError) as error:
            print(json.dumps(dict(status='BLOCKED_CORRECTED_OWNER_GATE',reason=str(error),data_head_moved=False)));return 2
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
    gbbq_stage_binding = None
    tdx_delta_build = None
    lifecycle_pg_state = None
    special_pg_state = None
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
                    tdx_root=resolve_tdx_root(ROOT),
                )
            except (ValueError, OSError) as error:
                tdx = dict(status='SOURCE_CAPTURE_BLOCKED', reason=str(error), target_date=args.target_date)
        if local.date().isoformat() == args.target_date and local.time() >= datetime.strptime("15:00:00", "%H:%M:%S").time():
            _, gbbq_probe = _run_json_cli("scripts/probe_v4_dm01_gbbq_revision.py", "--target-date", args.target_date)
            gbbq_stage_binding = gbbq_probe.get("pg_stage_state")
        if tdx and tdx.get("status") in {"TDX_PACKAGE_READY", "NOOP_SOURCE_ALREADY_FROZEN"}:
            delta_code, tdx_delta_build = _run_json_cli(
                "scripts/build_dm01_r4_tdx_delta.py", "--target-date", args.target_date,
                "--current-snapshot-id", str(tdx.get("snapshot_id") or ""),
                *(['--typed-scope-v2'] if args.typed_scope_v2 else []),
            )
            if delta_code != 0:
                tdx_delta_build = {**tdx_delta_build, "status": tdx_delta_build.get("status", "BLOCKED_TDX_DELTA_NOT_READY")}
            if delta_code == 0 and tdx_delta_build.get("status") == "READY":
                if args.typed_scope_v2:
                    from workbench_analysis.dm01_corrected_source_capture_v2 import corrected_baostock_capture
                    source,runtime_manifest,bao_error=corrected_baostock_capture(ROOT,args.target_date,args.snapshot_root/'corrected_staging'/args.target_date/'baostock_v2')
                    if source:
                        bao=_read_baostock_daily_update_from_pg(args.target_date,str(source['snapshot_id']),source.get('source_revision_id'))
                        bao_smoke=dict(status='ACCEPTED',scope='CORRECTED_READ_CAPABILITY_ONLY')
                    else:bao_smoke=dict(status='BLOCKED',reason=bao_error)
                    probe_code,gbbq_probe=_run_json_cli('-m','scripts.probe_v4_dm01_gbbq_revision','--target-date',args.target_date)
                    gbbq_stage_binding=gbbq_probe.get('pg_stage_state')
                else:
                    bao, bao_smoke, bao_error = _run_baostock_daily_capture(args.target_date)
                    runtime_manifest, runtime_error = _runtime_acceptance(args.target_date)
            if bao is not None:
                if args.typed_scope_v2:
                    from workbench_analysis.dm01_sources_r4 import lifecycle as corrected_lifecycle
                    try:
                        lifecycle_snapshot=corrected_lifecycle(ROOT,args.target_date,bao,now.isoformat())
                        lifecycle_receipt=dict(status=lifecycle_snapshot['status'],consumer_scope='CORRECTED_ONLY',AS_RECORDED=False)
                    except (ValueError,OSError,KeyError) as error:
                        lifecycle_receipt=dict(status='BLOCKED_CORRECTED_LIFECYCLE',reason=str(error))
                    # Corrected-only staging has no accepted lifecycle PG owner; it
                    # cannot feed the production special-phase stage reader.
                else:
                    lifecycle_snapshot = None
                # Legacy source commands retain their original accepted manifest gate.
            if bao is not None and not args.typed_scope_v2:
                lifecycle_code, lifecycle_receipt = _run_json_cli(
                    "scripts/build_v4_dm01_lifecycle_snapshot.py", "--target-date", args.target_date,
                    "--baostock-snapshot-id", str(bao.get("snapshot_id") or ""),
                )
                lifecycle_pg_state = lifecycle_receipt.get("pg_stage_state")
                if lifecycle_code == 0 and isinstance(lifecycle_pg_state, dict):
                    from workbench_db.v4_dm01_stage_state_pg_r1 import read_stage
                    lifecycle_snapshot = read_stage(ROOT, lifecycle_pg_state["binding"],
                        trade_date=args.target_date, stage="lifecycle_snapshot")
                    if args.v402_pg_stage_state:
                        _, special_phase_receipt = _run_json_cli(
                            "scripts/build_v4_dm01_special_phase_manifest.py", "--target-date", args.target_date,
                            "--lifecycle-pg-stage-state", json.dumps(lifecycle_pg_state, separators=(",", ":")),
                            "--v402-pg-stage-state", args.v402_pg_stage_state,
                        )
                        special_pg_state = special_phase_receipt.get("pg_stage_state")
                        if (isinstance(special_pg_state, dict)
                                and special_pg_state.get("contract_id") == "V4_DM01_STAGE_STATE_PG_R1"
                                and special_pg_state.get("trade_date") == args.target_date
                                and special_pg_state.get("stage") == "special_phase_manifest"):
                            from workbench_db.v4_dm01_stage_state_pg_r1 import read_stage
                            special_phase_snapshot = read_stage(ROOT, special_pg_state["binding"],
                                trade_date=args.target_date, stage="special_phase_manifest")
        readiness = evaluate_daily_source_readiness(
            trade_date=args.target_date,
            observed_at=now.isoformat(),
            official_session_confirmed=True,
            tdx_capture=tdx,
            baostock_capture=bao,
            baostock_capability_accepted=(runtime_manifest is not None and bao_smoke is not None
                                          and bao_smoke.get("status") == "ACCEPTED"),
            gbbq_snapshot=_accepted_gbbq_snapshot(args.target_date, gbbq_stage_binding),
            lifecycle_snapshot=lifecycle_snapshot,
            special_phase_snapshot=special_phase_snapshot,
        )
        if tdx and tdx.get('status') == 'SOURCE_CAPTURE_BLOCKED':
            readiness = dict(readiness, status='SOURCE_CAPTURE_BLOCKED', reason=tdx.get('reason'), head_moved=False)
        elif tdx_delta_build and tdx_delta_build.get('status') != 'READY':
            # A failed upstream transformation means BaoStock was never reached.
            # Do not misreport that as a provider publication delay.
            readiness = dict(readiness, status='BLOCKED_TDX_DELTA_NOT_READY',
                             reason=tdx_delta_build.get('reason') or tdx_delta_build.get('status'),
                             baostock_capture_attempted=False, head_moved=False)
        if (not args.typed_scope_v2 and readiness.get("status") == "SOURCE_FREEZE_READY" and tdx and bao and gbbq_probe
                and builder_registry_result.get('status') != 'BLOCKED_BUILDER_REGISTRY'):
            tdx_capture_path = Path(str(tdx.get("receipt_path") or ""))
            if not all((gbbq_stage_binding, lifecycle_pg_state, special_pg_state)):
                readiness = dict(readiness, status="BLOCKED_DM01_PG_STAGE_BINDING_MISSING",
                                 reason="GBBQ_LIFECYCLE_SPECIAL_PHASE_PG_BINDINGS_REQUIRED", head_moved=False)
                freeze_code, source_freeze = 2, {"reason": "DM01_PG_STAGE_BINDING_MISSING"}
            else:
                freeze_code, source_freeze = _run_json_cli(
                    "scripts/freeze_v4_dm01_daily_sources.py", "--target-date", args.target_date,
                    "--tdx-capture-receipt", str(tdx_capture_path),
                    "--bao-snapshot-id", str(bao.get("snapshot_id") or ""),
                    "--gbbq-pg-stage-state", json.dumps(gbbq_stage_binding, separators=(",", ":")),
                    "--lifecycle-pg-stage-state", json.dumps(lifecycle_pg_state, separators=(",", ":")),
                    "--special-phase-pg-stage-state", json.dumps(special_pg_state, separators=(",", ":")),
                )
            if freeze_code == 0 and source_freeze.get("status") == "SOURCE_FREEZE_READY":
                from workbench_db.v4_dm01_stage_state_pg_r1 import read_stage
                freeze_pg_state = source_freeze.get("pg_stage_state")
                if (not isinstance(freeze_pg_state, dict)
                        or freeze_pg_state.get("contract_id") != "V4_DM01_STAGE_STATE_PG_R1"
                        or freeze_pg_state.get("trade_date") != args.target_date
                        or freeze_pg_state.get("stage") != "daily_source_freeze"):
                    raise ValueError("DAILY_SOURCE_FREEZE_PG_STAGE_BINDING_REQUIRED")
                freeze = read_stage(ROOT, freeze_pg_state["binding"], trade_date=args.target_date,
                    stage="daily_source_freeze")
                bao_path = resolve_baostock_cache_root(ROOT) / 'baostock' / args.target_date.replace('-','') / str(bao['snapshot_id']) / 'daily_update.json'
                settings = _daily_runtime_contract(ROOT, "BAOSTOCK_SUPPLEMENTAL_SOURCE_V1", "1.1.0",
                    "config/baostock_supplemental_contract_v1.json")['dm01_daily_updates']
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
    if args.typed_scope_v2 and tdx_delta_build and tdx_delta_build.get('status')=='READY':
        readiness=dict(readiness,canonical_pit_promotion=False,source_scope_admission='CORRECTED_STAGING_ONLY',
                       corrected_source_status=readiness['status'],status='BLOCKED_SCOPED_SUCCESSOR_ADMISSION',
                       reason='V2_TYPED_SOURCE_CANNOT_ENTER_V1_AS_RECORDED_FREEZE; SCOPED_SUCCESSOR_REVIEW_REQUIRED')
    continuous_contract=_load_daily_contract_record_from_pg('V4_CONTINUOUS_DATA_MAINTENANCE_V2','2.0.0')
    result = {
        "contract_id": "V4_DM01_SOURCE_READINESS_RECEIPT_R2",
        "version": "2.0.0",
        "status": readiness["status"],
        "stage_contract": "V4_CONTINUOUS_DATA_MAINTENANCE_V2",
        "contract_path": "config/v4_continuous_data_maintenance_v2.json",
        "contract_sha256": continuous_contract.raw_sha256,
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
        "typed_source_scope_v2": args.typed_scope_v2,
        "next_stage": ("WIRE_REAL_ACCEPTED_COMPONENT_BUILDERS_AND_INDEPENDENT_ARTIFACT_POSTCHECK"
                       if readiness["status"] == "BLOCKED_COMPONENT_BUILDERS_NOT_WIRED"
                       else "CAPTURE_TDX_AND_BAOSTOCK_AFTER_OFFICIAL_RELEASE; BUILD_ONLY_AFTER_ALL_V2_SOURCE_FAMILIES_READY"),
    }
    from workbench_db.v4_dm01_stage_state_pg_r1 import append_stage
    result["pg_stage_state"] = append_stage(ROOT, args.target_date, "source_readiness", result)
    print(json.dumps(result, ensure_ascii=False))
    return 0 if readiness["status"].startswith("WAIT_") or readiness["status"] in ("PROMOTED_V2", "NOOP_IDENTICAL_PROMOTION") else 2


if __name__ == "__main__":
    raise SystemExit(main())
