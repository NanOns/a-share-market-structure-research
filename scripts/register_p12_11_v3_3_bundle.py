from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import duckdb

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from workbench_db.migrations import MigrationExecutor
from workbench_service.research_registry_v3_3 import register_active_bundle


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", type=Path, default=ROOT / "data/database/market_research.duckdb")
    parser.add_argument("--pointer", type=Path, default=ROOT / "data/current/ACTIVE_RESEARCH_BUNDLE_V3_3.json")
    args = parser.parse_args()
    with duckdb.connect(str(args.database)) as connection:
        migration = MigrationExecutor(connection).apply()
        registration = register_active_bundle(connection, args.pointer)
    print(json.dumps({"migration": migration, "registration": registration}, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
