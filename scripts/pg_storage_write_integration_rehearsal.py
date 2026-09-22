"""Rehearse PostgreSQL storage metadata injection without switching the service."""
from __future__ import annotations

import argparse
import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from workbench_db.postgres_repository import PostgresRepository  # noqa: E402
from workbench_db.postgres_write_repository import PostgresWriteRepository  # noqa: E402
from workbench_ops.storage import StorageGovernance  # noqa: E402


DEFAULT_REPORT = ROOT / "runtime/postgres_migration/20260922/pg_storage_write_integration_rehearsal_report.json"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()
    marker = uuid.uuid4().hex
    root = ROOT / "runtime/pg_storage_rehearsal"
    failures: list[str] = []
    checks: dict[str, object] = {}
    try:
        with PostgresRepository() as repository:
            writer = PostgresWriteRepository(repository)
            storage = StorageGovernance(ROOT, storage_repository=writer)
            with repository.transaction():
                object_id = storage.register(root / f"object-{marker}", kind="rehearsal", successful_date="2099-01-01")
            first = writer.storage_object(object_id)
            with repository.transaction():
                storage.register(root / f"object-{marker}", kind="rehearsal", successful_date="2099-01-01", referenced=True)
            second = writer.storage_object(object_id)
            checks["object_id"] = object_id
            checks["roundtrip"] = bool(first and second and first["payload"].get("referenced") is False and second["payload"].get("referenced") is True)
            checks["visible_count"] = len([item for item in writer.storage_objects() if item["storage_object_id"] == object_id])
            lease_id = "lease-" + marker
            with repository.transaction():
                storage.acquire_lease(lease_id=lease_id, object_ids=[object_id], owner="pg-rehearsal", ttl_seconds=300)
            active_lease = writer.lease(lease_id)
            checks["lease_roundtrip"] = bool(active_lease and active_lease["payload"].get("state") == "ACTIVE")
            with repository.transaction():
                storage.release_lease(lease_id=lease_id, owner="pg-rehearsal")
            released_lease = writer.lease(lease_id)
            checks["lease_release"] = bool(released_lease and released_lease["payload"].get("state") == "RELEASED")
            cleanup_id = "cleanup-" + marker
            cleanup_payload = {"cleanup_job_id": cleanup_id, "state": "PLANNED", "eligible_object_ids": [object_id]}
            with repository.transaction():
                writer.upsert_cleanup_job(cleanup_job_id=cleanup_id, payload=cleanup_payload)
            cleanup_job = writer.cleanup_job(cleanup_id)
            checks["cleanup_plan_roundtrip"] = bool(cleanup_job and cleanup_job["payload"].get("state") == "PLANNED")
            with repository.transaction():
                with repository.connection.cursor() as cursor:  # type: ignore[union-attr]
                    cursor.execute("delete from workbench.storage_objects where storage_object_id=%s", (object_id,))
                    cursor.execute("delete from workbench.leases where lease_id=%s", (lease_id,))
                    cursor.execute("delete from workbench.cleanup_jobs where cleanup_job_id=%s", (cleanup_id,))
            checks["cleanup"] = writer.storage_object(object_id) is None
    except Exception as exc:  # pragma: no cover - report external service state
        checks["error"] = f"{type(exc).__name__}:{exc}"
        failures.append("postgres_storage_repository")
    if checks.get("roundtrip") is not True:
        failures.append("roundtrip")
    if checks.get("cleanup") is not True:
        failures.append("cleanup")
    if checks.get("lease_roundtrip") is not True or checks.get("lease_release") is not True:
        failures.append("lease_boundary")
    if checks.get("cleanup_plan_roundtrip") is not True:
        failures.append("cleanup_plan_boundary")
    report = {
        "contract_version": "PG_STORAGE_WRITE_INTEGRATION_REHEARSAL_V1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "checks": checks,
        "failures": sorted(set(failures)),
        "status": "PASS" if not failures else "FAIL",
        "acceptance": "DEGRADED_PASS_STORAGE_WRITE_INTEGRATION" if not failures else "BLOCKED",
        "online_switch_performed": False,
        "data_generation_triggered": False,
        "next_stage": "migrate_remaining_storage_metadata_readers_and_writers" if not failures else "repair_storage_repository_boundary",
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.report.with_suffix(args.report.suffix + ".tmp")
    temporary.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(args.report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
