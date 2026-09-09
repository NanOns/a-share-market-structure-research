"""Apply M7B-01 schema 007 after an offline backup window."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from workbench_db import WorkbenchRepository
from workbench_ops import BackupService


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply M7B-01 history identity schema")
    parser.add_argument("--root", default=".")
    parser.add_argument("--database")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    database = Path(args.database).resolve() if args.database else root / "data/database/market_research.duckdb"
    backup = BackupService(root, database).create_offline_backup(maintenance_window=True)
    with WorkbenchRepository(root, database) as repository:
        migration = repository.migration_receipt
    receipt = {"step": "M7B-01", "database": str(database), "backup": backup, "migration": migration}
    print(json.dumps(receipt, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
