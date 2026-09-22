"""Rehearse StorageGovernance with PostgreSQL metadata writes."""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from datetime import date
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from workbench_db.postgres_repository import PostgresRepository  # noqa: E402
from workbench_db.postgres_write_repository import PostgresWriteRepository  # noqa: E402
from workbench_ops.storage import StorageGovernance  # noqa: E402


ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "runtime/postgres_migration/20260922/pg_storage_governance_rehearsal_report.json"


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--dsn", default=None); parser.add_argument("--report", type=Path, default=REPORT); args = parser.parse_args()
    dsn = args.dsn or os.environ.get("WORKBENCH_PG_DSN") or "host=127.0.0.1 port=5432 dbname=market_research user=postgres"
    token = uuid4().hex[:12]
    object_id = f"obj-pg-storage-probe-{token}"
    lease_id = f"lease-pg-storage-probe-{token}"
    checks: dict[str, object] = {}; failures: list[str] = []
    try:
        with PostgresRepository(dsn) as repository:
            writer = PostgresWriteRepository(repository)
            storage = StorageGovernance(ROOT, storage_repository=writer)
            path = ROOT / "data" / f"pg-storage-probe-{token}.bin"
            payload = {"storage_object_id": object_id, "path": str(path), "kind": "PROBE", "successful_date": date.today().isoformat(), "referenced": False, "lease_until_utc": None, "state": "ACTIVE", "registered_at_utc": "2026-09-22T00:00:00+00:00"}
            writer.upsert_storage_object(storage_object_id=object_id, payload=payload)
            checks["register_roundtrip"] = any(item["storage_object_id"] == object_id and item["payload"] == payload for item in writer.storage_objects())
            lease = storage.acquire_lease(lease_id=lease_id, object_ids=[object_id], owner="pg-storage-probe", ttl_seconds=60)
            checks["lease_acquire"] = lease["owner"] == "pg-storage-probe" and writer.lease(lease_id) is not None
            released = storage.release_lease(lease_id=lease_id, owner="pg-storage-probe")
            checks["lease_release"] = released["state"] == "RELEASED"
            plan = storage.preview_cleanup(as_of=date.today())
            checks["cleanup_plan"] = plan["state"] == "PLANNED" and bool(plan["cleanup_job_id"])
            checks["payload_projection"] = object_id in {item["storage_object_id"] for item in writer.storage_objects()}
            with repository.transaction() as connection:
                with connection.cursor() as cur:
                    cur.execute("delete from workbench.cleanup_jobs where cleanup_job_id=%s", (plan["cleanup_job_id"],))
                    cur.execute("delete from workbench.leases where lease_id=%s", (lease_id,))
                    cur.execute("delete from workbench.storage_objects where storage_object_id=%s", (object_id,))
            checks["cleanup"] = writer.storage_object(object_id) is None and writer.lease(lease_id) is None
    except Exception as exc:  # pragma: no cover - external database state
        checks["error"] = f"{type(exc).__name__}:{exc}"; failures.append("pg_storage_governance")
    finally:
        (ROOT / "data" / f"pg-storage-probe-{token}.bin").unlink(missing_ok=True)
    for key in ("register_roundtrip", "lease_acquire", "lease_release", "cleanup_plan", "payload_projection", "cleanup"):
        if checks.get(key) is not True:
            failures.append(key)
    report = {"contract_version": "PG_STORAGE_GOVERNANCE_V1", "generated_at_utc": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(), "checks": checks, "failures": sorted(set(failures)), "online_switch_performed": False, "data_generation_triggered": False, "acceptance": "DEGRADED_PASS_PG_STORAGE_GOVERNANCE" if not failures else "BLOCKED", "next_stage": "wire_storage_governance_factory_after_maintenance_cutover" if not failures else "repair_pg_storage_governance"}
    args.report.parent.mkdir(parents=True, exist_ok=True); temporary = args.report.with_suffix(args.report.suffix + ".tmp"); temporary.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True, default=str), encoding="utf-8"); os.replace(temporary, args.report); print(json.dumps(report, ensure_ascii=False, indent=2, default=str)); return 0 if not failures else 2


if __name__ == "__main__": raise SystemExit(main())
