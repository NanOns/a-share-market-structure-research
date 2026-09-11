"""Audit or import legacy membership snapshots into the V3 relation store.

Default mode is read-only.  ``--apply`` is reserved for a stopped workbench
service because it applies the pending schema migration and writes relation
bindings to the selected DuckDB file.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from workbench_db.migrations import MigrationExecutor  # noqa: E402
from workbench_service.legacy_relation_import import (  # noqa: E402
    LEGACY_SOURCE_SCOPE,
    LegacyRelationImporter,
    LegacySnapshotAdapter,
    compare_all_imported_snapshots,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--database",
        type=Path,
        default=ROOT / "data/database/market_research.duckdb",
        help="DuckDB path; read-only unless --apply is supplied",
    )
    parser.add_argument("--apply", action="store_true", help="apply migration and import bindings")
    return parser


def main() -> int:
    args = _parser().parse_args()
    database = args.database.resolve()
    if not database.is_file():
        raise SystemExit(f"DATABASE_NOT_FOUND:{database}")
    with duckdb.connect(str(database), read_only=not args.apply) as connection:
        migration = MigrationExecutor(connection).apply() if args.apply else {"status": "READ_ONLY"}
        plans = LegacySnapshotAdapter(connection, LEGACY_SOURCE_SCOPE).plan_all()
        result = {
            "database": str(database),
            "apply": args.apply,
            "migration": migration,
            "source_scope": LEGACY_SOURCE_SCOPE,
            "snapshot_count": len(plans),
            "snapshot_plan": [
                {
                    "snapshot_id": plan.snapshot_id,
                    "trade_date": str(plan.trade_date),
                    "legacy_table_snapshot_version": plan.snapshot_version,
                    "payload_snapshot_version": plan.payload_snapshot_version,
                    "row_count": plan.row_count,
                    "direct_edge_count": len(plan.direct_edges),
                    "attribute_count": len(plan.attributes),
                    "derived_edge_count": plan.legacy_payload_basis["derived_edge_count"],
                    "observed_at": plan.observed_at.isoformat(),
                }
                for plan in plans
            ],
        }
        if args.apply:
            result["import"] = LegacyRelationImporter(connection, LEGACY_SOURCE_SCOPE).import_snapshots()
            result["comparison"] = compare_all_imported_snapshots(connection, source_scope=LEGACY_SOURCE_SCOPE)
        print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2, default=str))
        if args.apply and result["comparison"]["status"] != "PASS":
            return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
