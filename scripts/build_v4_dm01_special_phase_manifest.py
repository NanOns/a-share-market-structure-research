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

from workbench_analysis.daily_data_head import write_json_atomic  # noqa: E402
from workbench_analysis.daily_source_manifests import build_special_phase_source_manifest  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Bind accepted V4-02 special-phase sources for one DM-01 session.")
    parser.add_argument("--target-date", required=True)
    args = parser.parse_args()
    now = datetime.now(timezone.utc).replace(microsecond=0)
    local = now.astimezone(ZoneInfo("Asia/Shanghai"))
    lifecycle_path = ROOT / "reports/v4_dm01" / args.target_date / "current_lifecycle_snapshot.json"
    receipt_path = ROOT / "reports/v4_dm01" / args.target_date / "special_phase_source_manifest_receipt_v1.json"
    if local.date().isoformat() == args.target_date and local.time() < time(15, 0):
        result = {"contract_id": "SPECIAL_PHASE_SOURCE_MANIFEST_V1", "status": "WAIT_MARKET_CLOSE",
                  "trade_date": args.target_date, "observed_at": now.isoformat(), "tdx_root_write_count": 0}
    elif not lifecycle_path.is_file():
        result = {"contract_id": "SPECIAL_PHASE_SOURCE_MANIFEST_V1", "status": "WAIT_IDENTITY_LIFECYCLE_SNAPSHOT",
                  "trade_date": args.target_date, "reason": "CURRENT_LIFECYCLE_SNAPSHOT_NOT_AVAILABLE",
                  "expected_lifecycle_path": str(lifecycle_path), "observed_at": now.isoformat(),
                  "tdx_root_write_count": 0}
    else:
        acceptance_path = ROOT / "reports/v4_02/V4_02_FINAL_EXTERNAL_ACCEPTANCE_R6.json"
        acceptance = json.loads(acceptance_path.read_text(encoding="utf-8"))
        stage_path = ROOT / acceptance["evidence"]["manifest"]["path"]
        stage = json.loads(stage_path.read_text(encoding="utf-8"))
        components = stage["components"]
        lifecycle_artifact = json.loads(lifecycle_path.read_text(encoding="utf-8"))
        lifecycle_snapshot = {
            "contract_id": "CURRENT_LIFECYCLE_SNAPSHOT_V1",
            "status": lifecycle_artifact.get("status"),
            "trade_date": lifecycle_artifact.get("trade_date"),
            "artifact_path": lifecycle_path.relative_to(ROOT).as_posix(),
            "artifact_sha256": hashlib.sha256(lifecycle_path.read_bytes()).hexdigest(),
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
            tdx_root=Path("D:/new_tdx"),
        )
        manifest_path = ROOT / "reports/v4_dm01" / args.target_date / "special_phase_source_manifest.json"
        manifest_sha = write_json_atomic(manifest_path, manifest, tdx_root=Path("D:/new_tdx"))
        result = {"contract_id": "SPECIAL_PHASE_SOURCE_MANIFEST_V1", "status": manifest["status"],
                  "trade_date": args.target_date, "manifest_path": str(manifest_path),
                  "manifest_sha256": manifest_sha, "event_status": manifest["event_status"],
                  "active_event_count": manifest["active_event_count"], "tdx_root_write_count": 0}
    receipt_sha = write_json_atomic(receipt_path, result, tdx_root=Path("D:/new_tdx"))
    print(json.dumps({**result, "receipt": str(receipt_path), "receipt_sha256": receipt_sha}, ensure_ascii=False))
    return 0 if result["status"] in {"READY", "WAIT_MARKET_CLOSE", "WAIT_IDENTITY_LIFECYCLE_SNAPSHOT"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
