from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from workbench_analysis.baostock_daily_update_source import capture_baostock_daily_update  # noqa: E402
from workbench_analysis.baostock_supplemental import BaoStockClient, BaoStockError, RequestBudget, package_metadata  # noqa: E402
from workbench_analysis.baostock_runtime_acceptance import load_runtime_acceptance_manifest  # noqa: E402


def load_source_contract():
    """Resolve the active BaoStock source contract through the approved PG registry."""
    from workbench_analysis.operational_daily_executor_v1 import _daily_runtime_contract
    return _daily_runtime_contract(
        "BAOSTOCK_SUPPLEMENTAL_SOURCE_V1",
        "1.1.0",
    )


def load_runtime_acceptance(project_root, target_date, manifest_path):
    """Read date-bound runtime approval from PG; FILE is an explicit dev override."""
    import os
    source = os.environ.get("V4_BAOSTOCK_RUNTIME_ACCEPTANCE_SOURCE", "PG")
    if source == "PG":
        from workbench_db.v4_baostock_runtime_acceptance_pg_r1 import load
        return load(project_root, target_date, sdk=package_metadata())["manifest"]
    if source == "FILE":
        return load_runtime_acceptance_manifest(manifest_path, project_root=project_root)
    raise ValueError("BAOSTOCK_RUNTIME_ACCEPTANCE_SOURCE_UNSUPPORTED")


def main() -> int:
    parser = argparse.ArgumentParser(description="Capture BaoStock DailyUpdates through the bounded shared client.")
    parser.add_argument("--target-date", required=True)
    parser.add_argument("--ledger", type=Path, default=None,
                        help="Override BAOSTOCK_CACHE_ROOT/request_ledger.json")
    parser.add_argument("--snapshot-root", type=Path, default=None,
                        help="Override BAOSTOCK_CACHE_ROOT/config/paths.yaml")
    parser.add_argument("--hard-limit", type=int, default=45_000)
    parser.add_argument("--soft-limit", type=int, default=40_000)
    args = parser.parse_args()
    try:
        from common.paths import resolve_baostock_cache_root
        cache_root = resolve_baostock_cache_root(ROOT, args.snapshot_root)
        ledger_path = args.ledger or cache_root / "request_ledger.json"
        date.fromisoformat(args.target_date)
        source_contract = load_source_contract()
        dm01_contract = source_contract.get("dm01_daily_updates", {})
        if dm01_contract.get("runtime_acceptance_contract") != "BAOSTOCK_DAILY_UPDATE_RUNTIME_ACCEPTANCE_V1":
            print(json.dumps({
                "status": "WAIT_BAOSTOCK_DAILY_UPDATE",
                "reason": "BAOSTOCK_DM01_RUNTIME_ACCEPTANCE_CONTRACT_INVALID",
            }, ensure_ascii=False))
            return 2
        manifest_path = ROOT / dm01_contract["runtime_acceptance_manifest_template"].replace(
            "{YYYYMMDD}", args.target_date.replace("-", "")
        )
        runtime_manifest = load_runtime_acceptance(ROOT, args.target_date, manifest_path)
        if runtime_manifest.get("live_smoke", {}).get("target_date") != args.target_date:
            print(json.dumps({"status": "WAIT_BAOSTOCK_DAILY_UPDATE",
                              "reason": "BAOSTOCK_RUNTIME_ACCEPTANCE_TARGET_DATE_MISMATCH"}, ensure_ascii=False))
            return 2
        budget = RequestBudget(ledger_path, hard_limit=args.hard_limit, soft_limit=args.soft_limit)
        with BaoStockClient(budget, auth_mode=runtime_manifest["auth_mode"],
                            runtime_acceptance_manifest=runtime_manifest) as client:
            result = capture_baostock_daily_update(
                trade_date=args.target_date,
                client=client,
                snapshot_root=cache_root,
                runtime_acceptance_manifest=runtime_manifest,
            )
        print(json.dumps({key: result.get(key) for key in (
            "status", "trade_date", "snapshot_id", "source_revision_id", "request_count"
        )}, ensure_ascii=False))
        return 0 if result.get("status") in {"BAOSTOCK_DAILY_SNAPSHOT_READY", "NOOP_SOURCE_ALREADY_FROZEN"} else 2
    except (BaoStockError, ValueError, RuntimeError) as exc:
        # BaoStockClient sanitizes provider text before it reaches this boundary.
        print(json.dumps({"status": "WAIT_BAOSTOCK_DAILY_UPDATE", "reason": str(exc)}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
