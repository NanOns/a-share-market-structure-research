"""Rehearse PostgreSQL backup-catalog metadata round-trip and cleanup."""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from workbench_db.backup_catalog_repository import PostgresBackupCatalogRepository  # noqa: E402
from workbench_db.postgres_repository import PostgresRepository  # noqa: E402


ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "runtime/postgres_migration/20260922/pg_backup_catalog_repository_rehearsal_report.json"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dsn", default=None)
    parser.add_argument("--report", type=Path, default=REPORT)
    args = parser.parse_args()
    dsn = args.dsn or os.environ.get("WORKBENCH_PG_DSN") or "host=127.0.0.1 port=5432 dbname=market_research user=postgres"
    token = uuid4().hex[:12]
    backup_id = f"backup-pg-catalog-probe-{token}"
    rollback_id = f"backup-pg-catalog-rollback-{token}"
    record = {"backup_id": backup_id, "path": f"runtime/probe/{backup_id}.duckdb", "sha256": "a" * 64, "state": "VERIFIED", "verification": {"publication_heads": 1}}
    checks: dict[str, object] = {}
    failures: list[str] = []
    try:
        with PostgresRepository(dsn) as base:
            catalog = PostgresBackupCatalogRepository(base)
            catalog.upsert(backup_id, record)
            catalog.upsert(backup_id, {**record, "state": "CONFLICTING_REPLAY"})
            loaded = catalog.get(backup_id)
            checks["roundtrip"] = loaded == record
            checks["idempotent_replay"] = loaded is not None and loaded.get("state") == "VERIFIED"
            checks["listed"] = any(item_id == backup_id and payload == record for item_id, payload in catalog.rows())
            try:
                with base.transaction() as connection:
                    with connection.cursor() as cur:
                        cur.execute("insert into workbench.backup_catalog(backup_id,payload_json) values (%s,%s::jsonb)", (rollback_id, json.dumps({"backup_id": rollback_id})))
                    raise RuntimeError("ROLLBACK_PROBE")
            except RuntimeError as exc:
                checks["rollback_error"] = str(exc)
            checks["rollback_clean"] = catalog.get(rollback_id) is None
            with base.transaction() as connection:
                with connection.cursor() as cur:
                    cur.execute("delete from workbench.backup_catalog where backup_id=%s", (backup_id,))
            checks["cleanup"] = catalog.get(backup_id) is None
    except Exception as exc:  # pragma: no cover - reports external database state
        checks["error"] = f"{type(exc).__name__}:{exc}"
        failures.append("postgres_backup_catalog_repository")
    for key in ("roundtrip", "idempotent_replay", "listed", "rollback_clean", "cleanup"):
        if checks.get(key) is not True:
            failures.append(key)
    report = {"contract_version": "PG_BACKUP_CATALOG_REPOSITORY_V1", "generated_at_utc": datetime.now(timezone.utc).isoformat(), "checks": checks, "failures": sorted(set(failures)), "online_switch_performed": False, "data_generation_triggered": False, "acceptance": "DEGRADED_PASS_BACKUP_CATALOG_REPOSITORY" if not failures else "BLOCKED", "next_stage": "inject_backup_catalog_into_backup_service_after_restore_rehearsal" if not failures else "repair_backup_catalog_repository"}
    args.report.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.report.with_suffix(args.report.suffix + ".tmp")
    temporary.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True, default=str), encoding="utf-8")
    os.replace(temporary, args.report)
    print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
    return 0 if not failures else 2


if __name__ == "__main__":
    raise SystemExit(main())
