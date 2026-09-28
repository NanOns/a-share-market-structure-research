from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from workbench_analysis.baostock_daily_update_source import capture_baostock_daily_update  # noqa: E402
from workbench_analysis.baostock_supplemental import BaoStockClient, BaoStockError, RequestBudget  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Capture BaoStock DailyUpdates through the bounded shared client.")
    parser.add_argument("--target-date", required=True)
    parser.add_argument("--ledger", type=Path, default=ROOT / "reports/v4_baostock/request_ledger.json")
    parser.add_argument("--snapshot-root", type=Path, default=ROOT / "data/v4/source_snapshots")
    parser.add_argument("--hard-limit", type=int, default=45_000)
    parser.add_argument("--soft-limit", type=int, default=40_000)
    args = parser.parse_args()
    try:
        date.fromisoformat(args.target_date)
        source_contract = json.loads((ROOT / "config/baostock_supplemental_contract_v1.json").read_text(encoding="utf-8"))
        if source_contract.get("request_budget", {}).get("production_network_enabled") is not True:
            print(json.dumps({
                "status": "WAIT_BAOSTOCK_DAILY_UPDATE",
                "reason": "BAOSTOCK_ACTIVATION_GATE_OPEN",
                "activation_gate": source_contract.get("request_budget", {}).get("activation_gate"),
            }, ensure_ascii=False))
            return 2
        budget = RequestBudget(args.ledger, hard_limit=args.hard_limit, soft_limit=args.soft_limit)
        with BaoStockClient(budget) as client:
            result = capture_baostock_daily_update(
                trade_date=args.target_date,
                client=client,
                snapshot_root=args.snapshot_root,
                tdx_root=Path("D:/new_tdx"),
            )
        print(json.dumps({key: result.get(key) for key in (
            "status", "trade_date", "snapshot_id", "source_revision_id", "request_count"
        )}, ensure_ascii=False))
        return 0 if result.get("status") in {"BAOSTOCK_DAILY_SNAPSHOT_READY", "NOOP_SOURCE_ALREADY_FROZEN"} else 2
    except (BaoStockError, ValueError) as exc:
        # BaoStockClient sanitizes provider text before it reaches this boundary.
        print(json.dumps({"status": "WAIT_BAOSTOCK_DAILY_UPDATE", "reason": str(exc)}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
