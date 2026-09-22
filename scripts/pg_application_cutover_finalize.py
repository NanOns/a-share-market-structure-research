"""Finalize and record the PostgreSQL application-boundary switch.

This command does not generate data.  It only verifies the already-running
service/configuration and records an auditable completion receipt.
"""
from __future__ import annotations

import json
import os
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import psycopg


ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "runtime/postgres_migration/20260922/pg_application_cutover_completion.json"


def service_status() -> dict[str, object]:
    try:
        with urllib.request.urlopen("http://127.0.0.1:28765/api/operations/status", timeout=5) as response:
            payload = json.loads(response.read().decode("utf-8"))
            return {
                "http_status": response.status,
                "service_state": payload.get("service_state"),
                "backend": payload.get("backend"),
                "database_path": payload.get("database_path"),
                "active_job_count": payload.get("active_job_count"),
                "service_pid": payload.get("service_pid"),
            }
    except Exception as exc:  # pragma: no cover - external service evidence
        return {"http_status": None, "error": f"{type(exc).__name__}:{exc}"}


def main() -> int:
    dsn = os.environ.get("WORKBENCH_PG_DSN") or "host=127.0.0.1 port=5432 dbname=market_research user=postgres"
    checks: dict[str, object] = {}
    blockers: list[str] = []
    config_path = ROOT / "config/workbench.yaml"
    config_text = config_path.read_text(encoding="utf-8")
    checks["config"] = {
        "engine_postgresql": 'engine: "postgresql"' in config_text,
        "cutover_active": 'cutover_state: "ACTIVE"' in config_text,
        "dsn_env_configured": 'dsn_env: "WORKBENCH_PG_DSN"' in config_text,
    }
    if not all(checks["config"].values()):  # type: ignore[union-attr]
        blockers.append("config_not_active_postgresql")

    try:
        with psycopg.connect(dsn) as connection:
            with connection.cursor() as cursor:
                cursor.execute("select status,count(*) from workbench_meta.migration_consumer_cutovers group by status order by status")
                checks["consumer_cutovers"] = {str(status): int(count) for status, count in cursor.fetchall()}
                cursor.execute("select count(*) from workbench_meta.migration_consumer_cutovers where status='NOT_MIGRATED'")
                checks["not_migrated_count"] = int(cursor.fetchone()[0])
                cursor.execute("select count(*) from workbench_meta.migration_table_catalog where status='DATA_COPIED'")
                checks["data_copied_count"] = int(cursor.fetchone()[0])
                cursor.execute("select count(*) from workbench_meta.timestamp_semantics_catalog where status='PENDING_REVIEW'")
                checks["timestamp_pending_count"] = int(cursor.fetchone()[0])
    except Exception as exc:  # pragma: no cover - external database evidence
        checks["postgres_error"] = f"{type(exc).__name__}:{exc}"
        blockers.append("postgres_metadata_unavailable")

    if checks.get("not_migrated_count") != 0:
        blockers.append("application_consumers_not_migrated")
    if checks.get("data_copied_count") != 103:
        blockers.append("table_catalog_not_complete")
    if checks.get("timestamp_pending_count") != 0:
        blockers.append("timestamp_semantics_pending")

    checks["service"] = service_status()
    service = checks["service"]
    if service.get("http_status") != 200 or service.get("service_state") != "READY":
        blockers.append("service_not_ready")
    if str(service.get("backend", "")).lower() != "postgresql" or "postgresql" not in str(service.get("database_path", "")).lower():
        blockers.append("service_backend_not_postgresql")
    if service.get("active_job_count") not in (0, None):
        blockers.append("active_jobs_present")

    report = {
        "contract_version": "PG_APPLICATION_CUTOVER_COMPLETION_V1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "checks": checks,
        "blockers": sorted(set(blockers)),
        "online_switch_performed": not blockers,
        "data_generation_triggered": False,
        "status": "FULL_PASS" if not blockers else "BLOCKED",
        "acceptance": "POSTGRES_APPLICATION_CUTOVER_COMPLETE" if not blockers else "BLOCKED_POSTCUTOVER_VERIFICATION",
        "next_stage": "post_cutover_monitoring" if not blockers else "repair_cutover_blockers",
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    temporary = REPORT.with_suffix(REPORT.suffix + ".tmp")
    temporary.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    os.replace(temporary, REPORT)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if not blockers else 2


if __name__ == "__main__":
    raise SystemExit(main())
