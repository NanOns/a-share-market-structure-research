"""Migrate the strength domain to V3 result-object rows.

Read-only mode audits the legacy strength slices. ``--apply`` applies the
versioned schema migration and imports every strength slice in one database
transaction. The legacy table is never deleted or rewritten.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from workbench_analysis.strength import migrate_strength_slice
from workbench_db.migrations import MigrationExecutor


def _audit(connection: duckdb.DuckDBPyConnection) -> dict[str, object]:
    tables = {row[0] for row in connection.execute("SHOW TABLES").fetchall()}
    if "analysis_slices" not in tables or "stock_strength_daily" not in tables:
        return {"strength_slice_count": 0, "legacy_row_count": 0, "status": "SCHEMA_INCOMPLETE"}
    slice_count, legacy_row_count = connection.execute(
        "SELECT count(*), coalesce(sum(row_count), 0) FROM analysis_slices WHERE domain='strength'"
    ).fetchone()
    actual_row_count = connection.execute(
        """
        SELECT count(*) FROM stock_strength_daily legacy
        JOIN analysis_slices slices USING (slice_id)
        WHERE slices.domain='strength'
        """
    ).fetchone()[0]
    result = {
        "strength_slice_count": int(slice_count),
        "legacy_declared_row_count": int(legacy_row_count),
        "legacy_actual_row_count": int(actual_row_count),
    }
    if "strength_result_rows" in tables:
        result.update({
            "result_row_count": connection.execute("SELECT count(*) FROM strength_result_rows").fetchone()[0],
            "result_object_count": connection.execute("SELECT count(*) FROM analysis_result_objects WHERE domain='strength'").fetchone()[0],
            "strength_binding_count": connection.execute("""
                SELECT count(*) FROM analysis_slice_result_bindings b
                JOIN analysis_slices s USING (slice_id)
                WHERE s.domain='strength'
            """).fetchone()[0],
            "view_row_count": connection.execute("SELECT count(*) FROM strength_result_daily").fetchone()[0],
        })
    result["status"] = "PASS" if int(legacy_row_count) == int(actual_row_count) else "BLOCKED"
    return result


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
        before = _audit(connection)
        if args.apply:
            slice_ids = [row[0] for row in connection.execute(
                "SELECT slice_id FROM analysis_slices WHERE domain='strength' ORDER BY slice_id"
            ).fetchall()]
            connection.execute("BEGIN TRANSACTION")
            try:
                imported = [migrate_strength_slice(connection, slice_id) for slice_id in slice_ids]
                connection.execute("COMMIT")
            except Exception:
                connection.execute("ROLLBACK")
                raise
            after = _audit(connection)
            result = {
                "status": "APPLIED",
                "migration": migration,
                "before": before,
                "after": after,
                "imported_slice_count": len(imported),
                "imported_object_count": len({item["result_object_id"] for item in imported}),
                "reused_slice_count": sum(bool(item["reused"]) for item in imported),
            }
        else:
            result = {"status": "READ_ONLY", "migration": migration, "audit": before}
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
