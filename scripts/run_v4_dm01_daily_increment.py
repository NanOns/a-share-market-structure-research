from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from workbench_analysis.daily_source_orchestrator import evaluate_daily_source_readiness  # noqa: E402
from workbench_analysis.tdx_official_daily_source import capture_tdx_official_daily_package  # noqa: E402
from workbench_analysis.daily_data_head import write_json_atomic  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the source-gated V4-DM-01 daily increment entrypoint.")
    parser.add_argument("--target-date", required=True)
    parser.add_argument("--snapshot-root", type=Path, default=ROOT / "data/v4/source_snapshots")
    parser.add_argument("--receipt-dir", type=Path, default=ROOT / "reports/v4_dm01")
    args = parser.parse_args()
    now = datetime.now(timezone.utc).replace(microsecond=0)
    local = now.astimezone(ZoneInfo("Asia/Shanghai"))
    official_sessions = json.loads((ROOT / "reports/v4_dm01/2026-09-28/calendar_bridge_receipt.json").read_text(encoding="utf-8")).get("official_sessions_after_base_cutoff", [])
    if args.target_date not in official_sessions:
        readiness = {"status": "BLOCKED_OFFICIAL_SESSION_NOT_VERIFIED", "trade_date": args.target_date}
        tdx = None
    else:
        # Before close the state machine returns without opening a source request.
        if local.date().isoformat() == args.target_date and local.time() < datetime.strptime("15:00:00", "%H:%M:%S").time():
            tdx = None
        else:
            tdx = capture_tdx_official_daily_package(
                target_date=args.target_date,
                snapshot_root=args.snapshot_root,
                tdx_root=Path("D:/new_tdx"),
            )
        readiness = evaluate_daily_source_readiness(
            trade_date=args.target_date,
            observed_at=now.isoformat(),
            official_session_confirmed=True,
            tdx_capture=tdx,
            baostock_capture=None,
            baostock_capability_accepted=False,
            gbbq_snapshot=None,
            lifecycle_snapshot=None,
            special_phase_snapshot=None,
        )
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
        "baostock_capture": None,
        "source_freeze": None,
        "component_builds": [],
        "data_head_moved": False,
        "stage_accepted_head_moved": False,
        "dev_baseline_head_moved": False,
        "tdx_root_write_count": 0,
        "next_stage": "CAPTURE_TDX_AND_BAOSTOCK_AFTER_OFFICIAL_RELEASE; BUILD_ONLY_AFTER_ALL_V2_SOURCE_FAMILIES_READY",
    }
    receipt_dir = args.receipt_dir / args.target_date
    path = receipt_dir / "source_readiness_receipt_r2.json"
    digest = write_json_atomic(path, result, tdx_root=Path("D:/new_tdx"))
    print(json.dumps({"status": readiness["status"], "target_date": args.target_date,
                      "receipt": str(path), "receipt_sha256": digest}, ensure_ascii=False))
    return 0 if readiness["status"].startswith("WAIT_") else 2


if __name__ == "__main__":
    raise SystemExit(main())
