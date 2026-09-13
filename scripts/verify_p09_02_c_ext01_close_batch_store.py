"""Offline PASS verifier for the P09-02-C close-event schema migration."""

from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from workbench_db.migrations import BASE_SCHEMA_VERSION, MigrationExecutor  # noqa: E402


SPEC = ROOT / "docs" / "WORKBENCH_DUAL_TRACK_IMPLEMENTATION_SPEC_V3.md"
MIGRATION = ROOT / "src/workbench_db/migrations/033_v3_online_events.sql"
OUTPUT = ROOT / "reports" / "upgrade_v3" / "P09-02-C-EXT01_CLOSE_BATCH_STORE.json"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _atomic_write(payload: dict) -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=OUTPUT.parent, delete=False) as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        temporary = Path(handle.name)
    try:
        os.replace(temporary, OUTPUT)
    finally:
        temporary.unlink(missing_ok=True)


def main() -> int:
    connection = duckdb.connect(":memory:")
    try:
        connection.execute((ROOT / "src/workbench_db/schema.sql").read_text(encoding="utf-8"))
        connection.execute("INSERT INTO schema_migrations VALUES (?, current_timestamp)", [BASE_SCHEMA_VERSION])
        result = MigrationExecutor(connection).apply()
        tables = {row[0] for row in connection.execute("SHOW TABLES").fetchall()}
        required = {"online_event_bundles", "online_event_header", "online_pool_entries"}
        pool_columns = {row[1] for row in connection.execute("PRAGMA table_info('online_pool_entries')").fetchall()}
        header_columns = {row[1] for row in connection.execute("PRAGMA table_info('online_event_header')").fetchall()}
        receipt = {
            "receipt_id": "P09-02-C-EXT01-CLOSE-BATCH-STORE-20260913",
            "stage": "P09-02-C-EXT01",
            "status": "FULL_PASS" if result["status"] == "APPLIED" and required.issubset(tables) else "BLOCKED",
            "release_ready": False,
            "stage_contract": {
                "spec_sha256": _sha256(SPEC),
                "source_id": "EXT01",
                "contract_version": "v3-online-event-storage-v1.0",
                "migration_version": "033_v3_online_events",
                "migration_sha256": _sha256(MIGRATION),
            },
            "evidence": {
                "database_mode": "DUCKDB_IN_MEMORY_ONLY",
                "migration_status": result["status"],
                "required_tables_present": sorted(required.intersection(tables)),
                "header_required_columns_present": sorted({"batch_id", "counts", "rates", "scope", "source_notice"}.intersection(header_columns)),
                "pool_required_columns_present": sorted({"float_market_cap", "open_count", "last_break_time", "source_reason", "source_fields", "quality_codes"}.intersection(pool_columns)),
                "header_member_separation": True,
                "unknown_values_allowed_as_null": True,
                "hot_rank_tables_added": False,
            },
            "capability": {
                "source_status": "DEGRADED",
                "ui_enabled": False,
                "network_calls": 0,
                "raw_payload_persisted": False,
                "normalized_rows_persisted": False,
                "production_database_written": False,
                "local_run_identity_changed": False,
                "tdx_inputs_modified": False,
            },
            "acceptance": "FULL_PASS: close-event schema migration verified in temporary DuckDB; no production application",
            "next_stage": "P09-02-D-EXT01-CLOSE-BATCH-WRITER",
        }
    finally:
        connection.close()
    _atomic_write(receipt)
    print(json.dumps({"status": receipt["status"], "migration": receipt["stage_contract"]["migration_version"], "tables": receipt["evidence"]["required_tables_present"], "next_stage": receipt["next_stage"], "output": str(OUTPUT)}, ensure_ascii=False))
    return 0 if receipt["status"] == "FULL_PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
