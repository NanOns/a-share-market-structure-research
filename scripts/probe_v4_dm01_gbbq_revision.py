from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, time, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from workbench_analysis.daily_data_head import write_json_atomic  # noqa: E402
from workbench_analysis.gbbq_source_revision_probe import probe_gbbq_source_revision  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Probe current TDX GBBQ revision after the Shanghai market close.")
    parser.add_argument("--target-date", required=True)
    args = parser.parse_args()
    now = datetime.now(timezone.utc).replace(microsecond=0)
    from workbench_analysis.dm01_runtime_r4 import session_gate, calendar
    gate = session_gate(args.target_date, now.isoformat())
    local_now = now.astimezone(ZoneInfo("Asia/Shanghai"))
    if gate['status'] == 'WAIT_MARKET_CLOSE':
        result = {"contract_id": "GBBQ_SOURCE_REVISION_PROBE_V1", "status": "WAIT_MARKET_CLOSE",
                  "trade_date": args.target_date, "observed_at": now.isoformat(), "tdx_root_write_count": 0}
    else:
        calendar = calendar(ROOT)
        accepted_root = ROOT / "data/v4/source_snapshot_store/gbbq/sha256-775d82c58b5b46ec1d21478f86ba8ef90302691982e68d5c4cfcd51fddda666e"
        result = probe_gbbq_source_revision(
            target_date=args.target_date,
            current_source_root=Path("D:/new_tdx/vipdoc/cw"),
            accepted_snapshot_root=accepted_root,
            output_snapshot_root=ROOT / "data/v4/source_snapshot_store",
            observed_at=now.isoformat(),
            official_sessions_after_target=[
                day for day in calendar.get("session_dates", []) if day > args.target_date
            ],
            tdx_root=Path("D:/new_tdx"),
        )
    receipt_path = ROOT / "reports/v4_dm01" / args.target_date / "gbbq_revision_probe_receipt_v1.json"
    digest = write_json_atomic(receipt_path, result, tdx_root=Path("D:/new_tdx"))
    print(json.dumps({"status": result["status"], "target_date": args.target_date,
                      "receipt": str(receipt_path), "receipt_sha256": digest,
                      "tdx_root_write_count": result.get("tdx_root_write_count", 0)}, ensure_ascii=False))
    return 0 if result["status"] in {"REUSE_ACCEPTED_GBBQ_SNAPSHOT", "WAIT_MARKET_CLOSE"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
