from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from workbench_analysis.daily_source_freeze import (  # noqa: E402
    build_source_freeze_manifest_v2,
    file_record,
    source_freeze_complete_v2,
)
from workbench_analysis.baostock_runtime_acceptance import (  # noqa: E402
    runtime_acceptance_error,
)
from workbench_analysis.baostock_supplemental import package_metadata  # noqa: E402
from common.paths import resolve_baostock_cache_root, resolve_tdx_root  # noqa: E402
from workbench_analysis.operational_daily_executor_v1 import (  # noqa: E402
    _daily_runtime_contract, _load_pg_runtime_acceptance,
)


TDX_ROOT = resolve_tdx_root(ROOT)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def row_digest(rows: list[dict]) -> str:
    raw = json.dumps(rows, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description="Freeze the accepted DM-01 source set without promoting any data head.")
    parser.add_argument("--target-date", required=True)
    parser.add_argument("--tdx-capture-receipt", type=Path, required=True)
    parser.add_argument("--bao-snapshot-id", required=True)
    parser.add_argument("--gbbq-pg-stage-state", required=True)
    parser.add_argument("--lifecycle-pg-stage-state", required=True)
    parser.add_argument("--special-phase-pg-stage-state", required=True)
    args = parser.parse_args()
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    try:
        from workbench_analysis.dm01_runtime_r4 import session_gate, calendar as accepted_calendar
        gate = session_gate(args.target_date, now)
        if gate['status'] == 'WAIT_MARKET_CLOSE': raise ValueError('WAIT_MARKET_CLOSE')
        tdx_capture = json.loads(args.tdx_capture_receipt.read_text(encoding="utf-8"))
        if (tdx_capture.get("target_date") != args.target_date or tdx_capture.get("update_date") != args.target_date
                or tdx_capture.get("status") not in {"TDX_PACKAGE_READY", "NOOP_SOURCE_ALREADY_FROZEN"}):
            raise ValueError("FREEZE_TDX_TARGET_PACKAGE_NOT_READY")
        archive = Path(str((tdx_capture.get("download") or {}).get("path") or ""))
        snapshot_id = str(tdx_capture.get("snapshot_id") or "")
        if (not archive.is_file() or archive.parent.name != snapshot_id
                or sha256(archive) != (tdx_capture.get("download") or {}).get("sha256")):
            raise ValueError("FREEZE_TDX_PACKAGE_IDENTITY_MISMATCH")

        delta_receipt_path = archive.parent / "delta" / args.target_date.replace("-", "") / "tdx_delta_build_receipt.json"
        delta_receipt = json.loads(delta_receipt_path.read_text(encoding="utf-8"))
        delta_path = Path(str(delta_receipt.get("delta_path") or ""))
        if (delta_receipt.get("current_snapshot_id") not in (None, snapshot_id)
                or not delta_path.is_file() or sha256(delta_path) != delta_receipt.get("delta_sha256")):
            raise ValueError("FREEZE_TDX_PACKAGE_DELTA_IDENTITY_MISMATCH")
        delta = json.loads(delta_path.read_text(encoding="utf-8"))
        if (delta.get("contract_id") != "TDX_PACKAGE_DELTA_V1" or delta.get("current_snapshot_id") != snapshot_id
                or delta.get("target_date") != args.target_date):
            raise ValueError("FREEZE_TDX_PACKAGE_DELTA_BINDING_MISMATCH")

        bao_path = resolve_baostock_cache_root(ROOT) / "baostock" / args.target_date.replace("-", "") / args.bao_snapshot_id / "daily_update.json"
        bao = json.loads(bao_path.read_text(encoding="utf-8"))
        if (bao.get("snapshot_id") != args.bao_snapshot_id or bao.get("trade_date") != args.target_date
                or bao.get("provider_date") != args.target_date
                or bao.get("status") not in {"BAOSTOCK_DAILY_SNAPSHOT_READY", "NOOP_SOURCE_ALREADY_FROZEN"}
                or len(bao.get("query_operations", [])) != 2):
            raise ValueError("FREEZE_BAOSTOCK_TARGET_SNAPSHOT_MISMATCH")
        daily_rows = bao.get("daily_rows")
        factor_rows = bao.get("adjustment_factor_rows")
        if not isinstance(daily_rows, list) or not daily_rows or not isinstance(factor_rows, list):
            raise ValueError("FREEZE_BAOSTOCK_ROW_LIST_INVALID")
        daily_digest, factor_digest = row_digest(daily_rows), row_digest(factor_rows)
        operations = bao["query_operations"]
        if (operations[0].get("method") != "query_daily_history_k_AStock"
                or operations[1].get("method") != "query_daily_adjust_factor"
                or operations[0].get("response_sha256") != daily_digest
                or operations[1].get("response_sha256") != factor_digest
                or operations[0].get("params", {}).get("date") != args.target_date
                or operations[1].get("params", {}).get("date") != args.target_date):
            raise ValueError("FREEZE_BAOSTOCK_RESPONSE_DIGEST_OR_DATE_MISMATCH")
        expected_bao_snapshot_id = "sha256-" + hashlib.sha256(
            f"{args.target_date}\0{daily_digest}\0{factor_digest}".encode()
        ).hexdigest()
        if expected_bao_snapshot_id != args.bao_snapshot_id:
            raise ValueError("FREEZE_BAOSTOCK_CONTENT_ADDRESSED_ID_MISMATCH")
        runtime_template = _daily_runtime_contract(ROOT, "BAOSTOCK_SUPPLEMENTAL_SOURCE_V1", "1.1.0",
            "config/baostock_supplemental_contract_v1.json")["dm01_daily_updates"]["runtime_acceptance_manifest_template"]
        runtime_path = ROOT / runtime_template.replace("{YYYYMMDD}", args.target_date.replace("-", ""))
        runtime_bundle = _load_pg_runtime_acceptance(ROOT, args.target_date)
        runtime_manifest = runtime_bundle["manifest"]
        runtime_path = runtime_bundle["manifest_path"]
        runtime_error = runtime_acceptance_error(
            runtime_manifest, sdk=package_metadata(), auth_mode=str(runtime_manifest.get("auth_mode") or "")
        )
        if runtime_error or runtime_manifest.get("live_smoke", {}).get("target_date") != args.target_date:
            raise ValueError("FREEZE_BAOSTOCK_RUNTIME_ACCEPTANCE_INVALID:" + str(runtime_error or "TARGET_DATE_MISMATCH"))

        from workbench_db.v4_dm01_stage_state_pg_r1 import read_stage, append_stage
        stage_bindings = {
            "gbbq_revision_probe": json.loads(args.gbbq_pg_stage_state),
            "lifecycle_snapshot": json.loads(args.lifecycle_pg_stage_state),
            "special_phase_manifest": json.loads(args.special_phase_pg_stage_state),
        }
        for stage, binding in stage_bindings.items():
            if (not isinstance(binding, dict) or binding.get("contract_id") != "V4_DM01_STAGE_STATE_PG_R1"
                    or binding.get("trade_date") != args.target_date or binding.get("stage") != stage
                    or not isinstance(binding.get("binding"), dict)):
                raise ValueError("FREEZE_DM01_PG_STAGE_BINDING_REQUIRED:" + stage)
        gbbq_probe = read_stage(ROOT, stage_bindings["gbbq_revision_probe"]["binding"],
            trade_date=args.target_date, stage="gbbq_revision_probe")
        if gbbq_probe.get("trade_date") != args.target_date:
            raise ValueError("FREEZE_GBBQ_TARGET_DATE_MISMATCH")
        if gbbq_probe.get("status") == "REUSE_ACCEPTED_GBBQ_SNAPSHOT":
            gbbq_manifest_path = Path(str(gbbq_probe.get("accepted_manifest_path") or ""))
            expected_gbbq_manifest_sha = gbbq_probe.get("accepted_manifest_sha256")
        elif gbbq_probe.get("status") == "NEW_GBBQ_REVISION_FROZEN_REQUIRES_ADJUSTMENT_IMPACT":
            raise ValueError("FREEZE_GBBQ_NEW_REVISION_REQUIRES_ACCEPTED_ADJUSTMENT_IMPACT")
        else:
            raise ValueError("FREEZE_GBBQ_REVISION_PROBE_NOT_READY:" + str(gbbq_probe.get("status")))
        if not gbbq_manifest_path.is_file() or sha256(gbbq_manifest_path) != expected_gbbq_manifest_sha:
            raise ValueError("FREEZE_GBBQ_ACCEPTED_MANIFEST_DIGEST_MISMATCH")
        gbbq_manifest = json.loads(gbbq_manifest_path.read_text(encoding="utf-8"))
        if gbbq_manifest.get("snapshot_id") != gbbq_probe.get("accepted_snapshot_id"):
            raise ValueError("FREEZE_GBBQ_ACCEPTED_SNAPSHOT_ID_MISMATCH")
        for name, record in (gbbq_manifest.get("files") or {}).items():
            source = gbbq_manifest_path.parent / name
            if (not source.is_file() or sha256(source) != record.get("sha256")
                    or source.stat().st_size != int(record.get("bytes", -1))):
                raise ValueError("FREEZE_GBBQ_ACCEPTED_FILE_INTEGRITY_MISMATCH:" + str(name))
        if args.target_date < str(gbbq_manifest.get("first_eligible_formal_trade_date") or "9999-99-99"):
            raise ValueError("FREEZE_GBBQ_NOT_PIT_ELIGIBLE_FOR_TARGET_DATE")

        cal = accepted_calendar(ROOT)
        calendar_path = ROOT / cal['binding']['path']
        calendar = dict(status='PASS', calendar_revision=cal['publication_id'], official_sessions_after_base_cutoff=cal['session_dates'])
        lifecycle = read_stage(ROOT, stage_bindings["lifecycle_snapshot"]["binding"],
            trade_date=args.target_date, stage="lifecycle_snapshot")
        if lifecycle.get("trade_date") != args.target_date or lifecycle.get("status") not in {"READY", "DEGRADED_PASS"}:
            raise ValueError("FREEZE_CURRENT_LIFECYCLE_SNAPSHOT_NOT_READY")
        special_manifest = read_stage(ROOT, stage_bindings["special_phase_manifest"]["binding"],
            trade_date=args.target_date, stage="special_phase_manifest")
        if (special_manifest.get("trade_date") != args.target_date
                or special_manifest.get("status") not in {"READY", "DEGRADED_PASS"}):
            raise ValueError("FREEZE_SPECIAL_PHASE_MANIFEST_NOT_READY")

        def stage_file_record(binding, payload, source_family):
            locator = binding["binding"]
            return dict(path=locator["path"], sha256=locator["sha256"], bytes=locator["bytes"],
                        source_revision=binding.get("payload_sha256"), source_family=source_family,
                        pg_stage=binding["stage"], pg_payload_sha256=binding.get("payload_sha256"))

        page_capture_record = file_record(
            args.tdx_capture_receipt, source_revision="sha256:" + sha256(args.tdx_capture_receipt),
            source_family="TDX_OFFICIAL_PAGE_AND_INFO_RECEIPT",
        )
        delta_file_record = file_record(
            delta_path, source_revision=str(delta.get("delta_sha256")), source_family="TDX_PACKAGE_DELTA_V1",
        )
        bao_file_record = file_record(
            bao_path, source_revision=str(bao.get("snapshot_id")), source_family="BAOSTOCK_DAILY_UPDATE_V1",
        )
        family_sources = {
            "TDX_PAGE_CAPTURE": page_capture_record,
            "TDX_FULL_PACKAGE": file_record(archive, source_revision=snapshot_id, source_family="TDX_OFFICIAL_FULL_PACKAGE"),
            "TDX_PACKAGE_DELTA": delta_file_record,
            "OFFICIAL_CALENDAR": file_record(
                calendar_path, source_revision=str(calendar.get("calendar_revision")), source_family="OFFICIAL_SESSION_BRIDGE"),
            "BAOSTOCK_DAILY_UPDATE": bao_file_record,
            "BAOSTOCK_ADJUSTMENT_FACTOR": {
                **bao_file_record,
                "source_revision": str(bao.get("query_operations", [{}, {}])[1].get("response_sha256") or bao.get("snapshot_id")),
                "source_family": "BAOSTOCK_ADJUSTMENT_FACTOR_DAILY_V1",
                "field_scope": "adjustment_factor_rows_only",
            },
            "GBBQ": file_record(gbbq_manifest_path, source_revision=str(gbbq_manifest.get("snapshot_id")), source_family="V4_02_GBBQ_FORWARD_SNAPSHOT_V1"),
            "IDENTITY_LIFECYCLE": stage_file_record(stage_bindings["lifecycle_snapshot"], lifecycle, "CURRENT_LIFECYCLE_SNAPSHOT_V1"),
            "SPECIAL_PRICE_PHASE": stage_file_record(stage_bindings["special_phase_manifest"], special_manifest, "SPECIAL_PHASE_SOURCE_MANIFEST_V1"),
        }
        freeze = build_source_freeze_manifest_v2(
            trade_date=args.target_date,
            sources=family_sources,
            changed_tdx_files=delta.get("changed_file_manifest", []),
            observed_at=now,
            ingested_at=now,
            system_available_at=now,
        )
        if not source_freeze_complete_v2(freeze):
            raise ValueError("FREEZE_SOURCE_MANIFEST_INCOMPLETE")
        freeze_stage_binding = append_stage(ROOT, args.target_date, "daily_source_freeze", freeze)
        result = {"contract_id": "V4_DAILY_SOURCE_FREEZE_V2", "status": "SOURCE_FREEZE_READY",
                  "trade_date": args.target_date, "manifest_sha256": freeze.get("manifest_sha256"),
                  "pg_stage_state": freeze_stage_binding,
                  "source_family_count": len(family_sources), "changed_tdx_file_count": len(delta.get("changed_file_manifest", [])),
                  "tdx_root_write_count": 0}
    except (OSError, IndexError, KeyError, TypeError, ValueError) as exc:
        result = {"contract_id": "V4_DAILY_SOURCE_FREEZE_V2", "status": "WAIT_OR_BLOCKED",
                  "trade_date": args.target_date, "reason": str(exc)[:240], "observed_at": now,
                  "tdx_root_write_count": 0}
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result.get("status") == "SOURCE_FREEZE_READY" else 2


if __name__ == "__main__":
    raise SystemExit(main())
