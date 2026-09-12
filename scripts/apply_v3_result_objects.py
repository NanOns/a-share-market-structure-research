"""Audit or apply the P03-01 result-object schema migration.

Default mode is read-only. ``--apply`` is reserved for a stopped workbench
service after a verified backup; it creates only the result-object/binding
tables and does not rewrite existing analysis domains.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from workbench_db.migrations import MigrationExecutor


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, default=ROOT / "data/database/market_research.duckdb")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    database = args.database.resolve()
    if not database.is_file():
        raise SystemExit(f"DATABASE_NOT_FOUND:{database}")
    with duckdb.connect(str(database), read_only=not args.apply) as connection:
        migration = MigrationExecutor(connection).apply() if args.apply else {"status": "READ_ONLY"}
        tables = set(row[0] for row in connection.execute("SHOW TABLES").fetchall())
        result = {
            "database": str(database),
            "apply": bool(args.apply),
            "migration": migration,
            "result_object_tables": sorted(tables & {"analysis_result_objects", "analysis_slice_result_bindings"}),
            "result_object_count": connection.execute("SELECT count(*) FROM analysis_result_objects").fetchone()[0] if "analysis_result_objects" in tables else 0,
            "binding_count": connection.execute("SELECT count(*) FROM analysis_slice_result_bindings").fetchone()[0] if "analysis_slice_result_bindings" in tables else 0,
            "analysis_slice_count": connection.execute("SELECT count(*) FROM analysis_slices").fetchone()[0] if "analysis_slices" in tables else 0,
        }
        print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
