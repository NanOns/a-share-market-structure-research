"""Rehearse idempotent PostgreSQL writes with a forced rollback."""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from workbench_db.postgres_repository import PostgresRepository  # noqa: E402
from workbench_db.postgres_write_repository import PostgresWriteRepository  # noqa: E402


REPORT = ROOT / "runtime/postgres_migration/20260922/pg_write_boundary_rehearsal_report.json"


class RollbackProbe(Exception):
    pass


def main() -> int:
    job_id = "pg-write-boundary-rollback-probe"
    object_id = "pg-write-boundary-object-probe"
    checks: dict[str, object] = {}
    failures: list[str] = []
    try:
        with PostgresRepository() as repository:
            writer = PostgresWriteRepository(repository)
            try:
                with repository.transaction():
                    writer.upsert_job(job_id=job_id, job_key="pg-write-boundary-key", status="QUEUED", payload={"attempt": 1})
                    writer.upsert_job(job_id=job_id, job_key="pg-write-boundary-key", status="RUNNING", payload={"attempt": 2})
                    writer.upsert_storage_object(storage_object_id=object_id, payload={"kind": "ROLLBACK_PROBE", "state": "ACTIVE"})
                    checks["job_after_idempotent_upsert"] = writer.job(job_id)
                    checks["object_after_upsert"] = writer.storage_object(object_id)
                    raise RollbackProbe()
            except RollbackProbe:
                checks["rollback_exception_caught"] = True
            checks["job_after_rollback"] = writer.job(job_id)
            checks["object_after_rollback"] = writer.storage_object(object_id)
            if checks["job_after_rollback"] is not None or checks["object_after_rollback"] is not None:
                failures.append("rollback_left_business_rows")
            if (checks.get("job_after_idempotent_upsert") or {}).get("status") != "RUNNING":  # type: ignore[union-attr]
                failures.append("job_idempotency")
            if (checks.get("object_after_upsert") or {}).get("payload", {}).get("kind") != "ROLLBACK_PROBE":  # type: ignore[union-attr]
                failures.append("storage_object_upsert")
    except Exception as exc:  # pragma: no cover - report the gate failure
        checks["error"] = f"{type(exc).__name__}:{exc}"
        failures.append("write_boundary_connection")

    report = {
        "contract_version": "PG_WRITE_BOUNDARY_REHEARSAL_V1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "checks": checks,
        "failures": failures,
        "status": "PASS" if not failures else "FAIL",
        "acceptance": "DEGRADED_PASS_TRANSACTIONAL_IDEMPOTENCY_ROLLBACK" if not failures else "BLOCKED",
        "online_switch_performed": False,
        "data_generation_triggered": False,
        "next_stage": "research_write_contract" if not failures else "repair_write_boundary",
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    temporary = REPORT.with_suffix(REPORT.suffix + ".tmp")
    temporary.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    os.replace(temporary, REPORT)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if not failures else 2


if __name__ == "__main__":
    raise SystemExit(main())
