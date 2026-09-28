from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from workbench_analysis.tdx_official_daily_source import capture_tdx_official_daily_package  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Capture the official TDX daily page and validated package if published.")
    parser.add_argument("--target-date", default=datetime.now(ZoneInfo("Asia/Shanghai")).date().isoformat())
    parser.add_argument("--snapshot-root", type=Path, default=ROOT / "data/v4/source_snapshots")
    parser.add_argument("--timeout", type=int, default=30)
    args = parser.parse_args()
    try:
        result = capture_tdx_official_daily_package(
            target_date=args.target_date,
            snapshot_root=args.snapshot_root,
            tdx_root=Path("D:/new_tdx"),
            timeout=args.timeout,
        )
        print(json.dumps({
            "status": result["status"],
            "target_date": result["target_date"],
            "update_date": result["update_date"],
            "page_sha256": result["page_sha256"],
            "update_info_sha256": result["update_info_sha256"],
            "snapshot_id": result["snapshot_id"],
            "receipt_path": result["receipt_path"],
        }, ensure_ascii=False))
        return 0 if result["status"] in {"WAIT_TDX_PUBLICATION", "TDX_PACKAGE_READY", "NOOP_SOURCE_ALREADY_FROZEN"} else 2
    except Exception as exc:
        print(json.dumps({"status": "BLOCKED_TDX_SOURCE_CAPTURE", "reason": str(exc)}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
