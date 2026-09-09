"""Run the M7B-07 backup, restore-drill, and cleanup-preview checks."""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from workbench_ops import BackupService, StorageGovernance


def atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2), encoding="utf-8")
    temporary.replace(path)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run M7B-07 recovery and cleanup checks")
    parser.add_argument("--root", default=".")
    parser.add_argument("--database", default=None)
    parser.add_argument("--as-of", required=True)
    parser.add_argument("--drill-root", default=None)
    parser.add_argument("--receipt", default="reports/upgrade_m7/m7b_07_recovery_receipt.json")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    database = Path(args.database).resolve() if args.database else root / "data/database/market_research.duckdb"
    backup = BackupService(root, database)
    record = backup.create_history_backup(maintenance_window=True)
    drill_root = Path(args.drill_root).resolve() if args.drill_root else root / "runtime/restore_drills/m7b_07"
    restore = backup.restore_drill(record["backup_id"], drill_root=drill_root)
    cleanup = StorageGovernance(root, database).preview_cleanup(as_of=date.fromisoformat(args.as_of))
    receipt = {
        "contract_version": "history-recovery-receipt-v1.0",
        "step": "M7B-07",
        "database": str(database),
        "backup": record,
        "restore": restore,
        "cleanup_preview": cleanup,
    }
    atomic_json(root / args.receipt, receipt)
    print(json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
