"""Read-only maintenance-window preflight for PostgreSQL cutover."""
from __future__ import annotations

import json
import os
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import psycopg

ROOT = Path(__file__).resolve().parents[1]
REPORT_ROOT = ROOT / "runtime/postgres_migration/20260922"
REPORT = REPORT_ROOT / "pg_maintenance_cutover_preflight.json"


REQUIRED_REPORTS = {
    "shadow_read": "shadow_read_report.json",
    "api_shadow": "api_shadow_read_report.json",
    "cutover_rehearsal": "cutover_rehearsal_report.json",
    "application_inventory": "application_cutover_inventory.json",
    "relation_edges": "relation_edges_pg_shadow_report.json",
    "adapter_integration": "pg_adapter_integration_rehearsal_report.json",
    "read_contract": "workbench_read_contract_shadow_report.json",
    "write_boundary": "pg_write_boundary_rehearsal_report.json",
    "research_write": "pg_research_write_contract_rehearsal_report.json",
    "artifact_contract": "pg_operations_artifact_contract_rehearsal_report.json",
    "adapter_injection": "pg_cutover_adapter_injection_harness_report.json",
    "config_store": "pg_config_store_rehearsal_report.json",
    "storage_write": "pg_storage_write_integration_rehearsal_report.json",
    "online_time_contract": "pg_online_time_contract_rehearsal_report.json",
    "result_object_repository": "pg_result_object_repository_rehearsal_report.json",
    "slice_repository": "pg_slice_repository_rehearsal_report.json",
    "history_job_repository": "pg_history_job_repository_rehearsal_report.json",
    "backup_catalog_repository": "pg_backup_catalog_repository_rehearsal_report.json",
    "publication_status_reader": "pg_publication_status_reader_rehearsal_report.json",
    "publication_writer": "pg_publication_writer_rehearsal_report.json",
    "relation_repository": "pg_relation_repository_rehearsal_report.json",
    "publisher_end_to_end": "pg_publisher_end_to_end_rehearsal_report.json",
    "history_job_service": "pg_history_job_service_rehearsal_report.json",
    "analysis_activation": "pg_analysis_activation_rehearsal_report.json",
}


def load_report(path: Path) -> dict[str, object]:
    if not path.is_file():
        return {"status": "MISSING", "path": str(path)}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {"status": "INVALID"}
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        return {"status": "INVALID", "error": f"{type(exc).__name__}:{exc}"}


def service_status() -> dict[str, object]:
    try:
        with urllib.request.urlopen("http://127.0.0.1:28765/api/operations/status", timeout=5) as response:
            body = json.loads(response.read().decode("utf-8"))
            return {"http_status": response.status, "service_state": body.get("service_state"), "backend_path": body.get("database_path"), "pid": body.get("service_pid")}
    except Exception as exc:  # pragma: no cover - report external service state
        return {"http_status": None, "error": f"{type(exc).__name__}:{exc}"}


def main() -> int:
    blockers: list[str] = []
    checks: dict[str, object] = {}
    checks["reports"] = {name: {"status": report.get("status") or report.get("acceptance"), "acceptance": report.get("acceptance")} for name, filename in REQUIRED_REPORTS.items() for report in [load_report(REPORT_ROOT / filename)]}
    for name, report in checks["reports"].items():  # type: ignore[union-attr]
        if report["status"] not in {"PASS", "DEGRADED_PASS", "DEGRADED_PASS_EMPTY_SOURCE", "DEGRADED_PASS_PRECUTOVER_INVENTORY", "DEGRADED_PASS_PRECUTOVER_ADAPTER_AND_ROLLBACK", "DEGRADED_PASS_READ_BOUNDARY_SHADOW", "DEGRADED_PASS_TRANSACTIONAL_IDEMPOTENCY_ROLLBACK", "DEGRADED_PASS_RESEARCH_IDENTITY_IDEMPOTENCY_ROLLBACK", "DEGRADED_PASS_MANAGED_ROOT_ARTIFACT_ROLLBACK", "DEGRADED_PASS_ISOLATED_ADAPTER_INJECTION_503", "DEGRADED_PASS_CONFIG_STORE", "DEGRADED_PASS_STORAGE_WRITE_INTEGRATION", "DEGRADED_PASS_ONLINE_TIME_CONTRACT", "DEGRADED_PASS_RESULT_OBJECT_REPOSITORY", "DEGRADED_PASS_SLICE_REPOSITORY", "DEGRADED_PASS_HISTORY_JOB_REPOSITORY", "DEGRADED_PASS_BACKUP_CATALOG_REPOSITORY", "DEGRADED_PASS_PUBLICATION_STATUS_READER", "DEGRADED_PASS_PUBLICATION_WRITER", "DEGRADED_PASS_RELATION_REPOSITORY", "DEGRADED_PASS_PG_PUBLISHER_END_TO_END", "DEGRADED_PASS_PG_HISTORY_JOB_SERVICE", "DEGRADED_PASS_PG_ANALYSIS_ACTIVATION"}:
            blockers.append(f"report:{name}:{report['status']}")

    dsn = os.environ.get("WORKBENCH_PG_DSN") or "host=127.0.0.1 port=5432 dbname=market_research user=postgres"
    try:
        with psycopg.connect(dsn) as pg:
            with pg.cursor() as cur:
                cur.execute("select status,count(*) from workbench_meta.migration_table_catalog group by status order by status")
                checks["table_migration"] = {str(status): int(count) for status, count in cur.fetchall()}
                cur.execute("select status,count(*) from workbench_meta.migration_consumer_cutovers group by status order by status")
                checks["consumer_cutover"] = {str(status): int(count) for status, count in cur.fetchall()}
                cur.execute("select status,count(*) from workbench_meta.timestamp_semantics_catalog group by status order by status")
                checks["timestamp_semantics"] = {str(status): int(count) for status, count in cur.fetchall()}
                cur.execute("select availability,count(*) from workbench_meta.artifact_catalog group by availability order by availability")
                checks["artifact_availability"] = {str(status): int(count) for status, count in cur.fetchall()}
                cur.execute("select count(*) from workbench_meta.migration_table_catalog where status='DATA_COPIED'")
                checks["table_catalog_data_copied"] = int(cur.fetchone()[0])
                cur.execute("select count(*) from workbench_meta.migration_consumer_cutovers where status='NOT_MIGRATED'")
                checks["consumer_not_migrated"] = int(cur.fetchone()[0])
                cur.execute("select count(*) from workbench_meta.timestamp_semantics_catalog where status='PENDING_REVIEW'")
                checks["timestamp_pending_review"] = int(cur.fetchone()[0])
    except Exception as exc:
        checks["postgres_metadata_error"] = f"{type(exc).__name__}:{exc}"
        blockers.append("postgres_metadata_unavailable")

    checks["service"] = service_status()
    if checks["table_catalog_data_copied"] != 103:
        blockers.append("table_catalog_not_complete")
    if checks["consumer_not_migrated"] != 0:
        blockers.append("application_consumers_not_migrated")
    if checks["timestamp_pending_review"] != 0:
        blockers.append("timestamp_semantics_pending")
    if checks["service"].get("http_status") != 200 or checks["service"].get("service_state") != "READY":  # type: ignore[union-attr]
        blockers.append("service_not_ready")
    if "duckdb" in str(checks["service"].get("backend_path", "")).lower():  # type: ignore[union-attr]
        blockers.append("service_backend_still_duckdb")

    report = {
        "contract_version": "PG_MAINTENANCE_CUTOVER_PREFLIGHT_V1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "checks": checks,
        "blockers": sorted(set(blockers)),
        "online_switch_performed": False,
        "data_generation_triggered": False,
        "status": "FULL_PASS" if not blockers else "BLOCKED",
        "acceptance": "READY_FOR_AUTHORIZED_MAINTENANCE_WINDOW" if not blockers else "BLOCKED_PRECUTOVER_HARD_GATES",
        "next_stage": "authorized_maintenance_window_cutover" if not blockers else ("complete_application_adapter_migration" if checks.get("timestamp_pending_review") == 0 else "complete_application_adapter_migration_and_timestamp_contracts"),
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    temporary = REPORT.with_suffix(REPORT.suffix + ".tmp")
    temporary.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True, default=str), encoding="utf-8")
    os.replace(temporary, REPORT)
    print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
    return 0 if not blockers else 2


if __name__ == "__main__":
    raise SystemExit(main())
