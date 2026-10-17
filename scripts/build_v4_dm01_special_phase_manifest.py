from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, time, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from workbench_analysis.daily_source_manifests import build_special_phase_source_manifest  # noqa: E402
from common.paths import resolve_tdx_root  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Bind accepted V4-02 special-phase sources for one DM-01 session.")
    parser.add_argument("--target-date", required=True)
    parser.add_argument("--lifecycle-pg-stage-state", required=True,
                        help="Exact date-bound PG stage descriptor emitted by the lifecycle producer")
    parser.add_argument("--v402-pg-stage-state", required=True,
                        help="Exact date-bound PG stage descriptor for accepted V4-02 ingress")
    args = parser.parse_args()
    now = datetime.now(timezone.utc).replace(microsecond=0)
    from workbench_analysis.dm01_runtime_r4 import session_gate
    gate = session_gate(args.target_date, now.isoformat())
    local = now.astimezone(ZoneInfo("Asia/Shanghai"))
    try:
        lifecycle_binding = json.loads(args.lifecycle_pg_stage_state)
        if (not isinstance(lifecycle_binding, dict)
                or lifecycle_binding.get("contract_id") != "V4_DM01_STAGE_STATE_PG_R1"
                or lifecycle_binding.get("trade_date") != args.target_date
                or lifecycle_binding.get("stage") != "lifecycle_snapshot"):
            raise ValueError("LIFECYCLE_PG_STAGE_STATE_BINDING_REQUIRED")
        from workbench_db.v4_dm01_stage_state_pg_r1 import read_stage, append_stage
        lifecycle_artifact = read_stage(ROOT, lifecycle_binding["binding"],
            trade_date=args.target_date, stage="lifecycle_snapshot")
        v402_binding = json.loads(args.v402_pg_stage_state)
        if (not isinstance(v402_binding, dict)
                or v402_binding.get("contract_id") != "V4_DM01_V402_ACCEPTANCE_INGRESS_R1"
                or v402_binding.get("trade_date") != args.target_date
                or v402_binding.get("stage") != "v402_acceptance"):
            raise ValueError("V402_PG_STAGE_STATE_BINDING_REQUIRED")
        v402_ingress = read_stage(ROOT, v402_binding["binding"],
            trade_date=args.target_date, stage="v402_acceptance")
        if (v402_ingress.get("contract_id") != "V4_DM01_V402_ACCEPTANCE_INGRESS_R1"
                or v402_ingress.get("trade_date") != args.target_date
                or not isinstance(v402_ingress.get("acceptance"), dict)
                or not isinstance(v402_ingress.get("stage_manifest"), dict)
                or not isinstance(v402_ingress.get("acceptance_source_sha256"), str)
                or not isinstance(v402_ingress.get("stage_manifest_source_sha256"), str)):
            raise ValueError("V402_PG_STAGE_STATE_PAYLOAD_INVALID")
        v402_binding["acceptance_source_sha256"] = v402_ingress["acceptance_source_sha256"]
        v402_binding["stage_manifest_source_sha256"] = v402_ingress["stage_manifest_source_sha256"]
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("LIFECYCLE_PG_STAGE_STATE_UNAVAILABLE") from exc
    if gate['status'] == 'WAIT_MARKET_CLOSE':
        result = {"contract_id": "SPECIAL_PHASE_SOURCE_MANIFEST_V1", "status": "WAIT_MARKET_CLOSE",
                  "trade_date": args.target_date, "observed_at": now.isoformat(), "tdx_root_write_count": 0}
    elif lifecycle_artifact.get("trade_date") != args.target_date:
        result = {"contract_id": "SPECIAL_PHASE_SOURCE_MANIFEST_V1", "status": "WAIT_IDENTITY_LIFECYCLE_SNAPSHOT",
                  "trade_date": args.target_date, "reason": "CURRENT_LIFECYCLE_SNAPSHOT_DATE_MISMATCH",
                  "observed_at": now.isoformat(),
                  "tdx_root_write_count": 0}
    else:
        acceptance_path = ROOT / "data/v4/V4_02_ACCEPTED_HEAD.json"
        stage_path = ROOT / "data/v4/V4_02_ACCEPTED_HEAD.json"
        acceptance = v402_ingress["acceptance"]
        stage = v402_ingress["stage_manifest"]
        components = stage["components"]
        lifecycle_snapshot = {
            "contract_id": "CURRENT_LIFECYCLE_SNAPSHOT_V1",
            "status": lifecycle_artifact.get("status"),
            "trade_date": lifecycle_artifact.get("trade_date"),
            "artifact_sha256": hashlib.sha256(json.dumps(lifecycle_artifact, sort_keys=True,
                separators=(",", ":")).encode("utf-8")).hexdigest(),
            "source_revision": lifecycle_artifact.get("source_revision"),
            "active_security_ids": lifecycle_artifact.get("active_security_ids", []),
        }
        manifest = build_special_phase_source_manifest(
            trade_date=args.target_date,
            project_root=ROOT,
            v402_external_acceptance_path=acceptance_path,
            v402_stage_manifest_path=stage_path,
            event_store_path=ROOT / components["R6_EVENTS"]["path"],
            policy_path=ROOT / components["R6_POLICY"]["path"],
            lifecycle_snapshot=lifecycle_snapshot,
            observed_at=now.isoformat(),
            tdx_root=resolve_tdx_root(ROOT),
            v402_external_acceptance=acceptance,
            v402_stage_manifest=stage,
            v402_pg_binding=v402_binding,
            lifecycle_pg_binding=lifecycle_binding,
        )
        manifest_sha = hashlib.sha256(json.dumps(manifest, sort_keys=True,
            separators=(",", ":")).encode("utf-8")).hexdigest()
        result = {"contract_id": "SPECIAL_PHASE_SOURCE_MANIFEST_V1", "status": manifest["status"],
                  "trade_date": args.target_date,
                  "manifest_sha256": manifest_sha, "event_status": manifest["event_status"],
                  "active_event_count": manifest["active_event_count"], "tdx_root_write_count": 0}
    stage_payload = manifest if "manifest" in locals() else result
    result["pg_stage_state"] = append_stage(ROOT, args.target_date, "special_phase_manifest", stage_payload)
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["status"] in {"READY", "WAIT_MARKET_CLOSE", "WAIT_IDENTITY_LIFECYCLE_SNAPSHOT"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
