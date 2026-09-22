"""Rehearse BackupService with a PostgreSQL backup catalog.

The physical DuckDB backup is a tiny schema-only probe.  The test verifies
that BackupService can register/read catalog metadata from PostgreSQL and
complete a restore drill without touching production backup files.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
from pathlib import Path
from uuid import uuid4

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from workbench_db.backup_catalog_repository import PostgresBackupCatalogRepository  # noqa: E402
from workbench_db.postgres_repository import PostgresRepository  # noqa: E402
from workbench_ops.backup import BackupService  # noqa: E402


ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "runtime/postgres_migration/20260922/pg_backup_service_catalog_rehearsal_report.json"


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--dsn", default=None); parser.add_argument("--report", type=Path, default=REPORT); args = parser.parse_args()
    dsn = args.dsn or os.environ.get("WORKBENCH_PG_DSN") or "host=127.0.0.1 port=5432 dbname=market_research user=postgres"
    token = uuid4().hex[:12]
    probe_root = ROOT / "runtime/postgres_migration/20260922" / f"backup_service_probe_{token}"
    database_path = probe_root / "probe.duckdb"
    drill_root = probe_root / "restore"
    backup_id = f"backup-pg-service-probe-{token}"
    checks: dict[str, object] = {}; failures: list[str] = []
    try:
        probe_root.mkdir(parents=True, exist_ok=True)
        with duckdb.connect(str(database_path)) as connection:
            connection.execute((ROOT / "src/workbench_db/schema.sql").read_text(encoding="utf-8"))
            verification = BackupService._verify(connection)
        digest = hashlib.sha256(database_path.read_bytes()).hexdigest()
        record = {"backup_id": backup_id, "path": str(database_path), "sha256": digest, "created_at_utc": "2026-09-22T00:00:00+00:00", "source_database": str(database_path), "verification": verification, "state": "VERIFIED"}
        with PostgresRepository(dsn) as repository:
            catalog = PostgresBackupCatalogRepository(repository)
            service = BackupService(ROOT, database_path, catalog=catalog)
            catalog.upsert(backup_id, record)
            checks["catalog_roundtrip"] = catalog.get(backup_id) == record
            checks["catalog_rows"] = any(row_id == backup_id and payload == record for row_id, payload in catalog.rows())
            restored = service.restore_drill(backup_id, drill_root=drill_root)
            checks["restore_drill"] = restored["status"] == "PASS" and Path(restored["restore_drill_path"]).is_file()
            with repository.transaction() as connection:
                with connection.cursor() as cur:
                    cur.execute("delete from workbench.backup_catalog where backup_id=%s", (backup_id,))
            checks["cleanup"] = catalog.get(backup_id) is None
    except Exception as exc:  # pragma: no cover - external database/filesystem state
        checks["error"] = f"{type(exc).__name__}:{exc}"; failures.append("pg_backup_service_catalog")
    finally:
        if probe_root.exists():
            shutil.rmtree(probe_root, ignore_errors=True)
    for key in ("catalog_roundtrip", "catalog_rows", "restore_drill", "cleanup"):
        if checks.get(key) is not True: failures.append(key)
    report = {"contract_version": "PG_BACKUP_SERVICE_CATALOG_V1", "generated_at_utc": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(), "checks": checks, "failures": sorted(set(failures)), "online_switch_performed": False, "data_generation_triggered": False, "acceptance": "DEGRADED_PASS_PG_BACKUP_SERVICE_CATALOG" if not failures else "BLOCKED", "next_stage": "wire_backup_service_catalog_factory_after_maintenance_cutover" if not failures else "repair_pg_backup_service_catalog"}
    args.report.parent.mkdir(parents=True, exist_ok=True); temporary = args.report.with_suffix(args.report.suffix + ".tmp"); temporary.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True, default=str), encoding="utf-8"); os.replace(temporary, args.report); print(json.dumps(report, ensure_ascii=False, indent=2, default=str)); return 0 if not failures else 2


if __name__ == "__main__": raise SystemExit(main())
