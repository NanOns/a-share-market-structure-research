"""Rehearse PostgreSQL HISTORY_ANALYSIS job state, events and rollback."""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from workbench_db.postgres_history_job_repository import PostgresHistoryJobRepository
from workbench_db.postgres_repository import PostgresRepository


ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "runtime/postgres_migration/20260922/pg_history_job_repository_rehearsal_report.json"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dsn", default=None)
    parser.add_argument("--report", type=Path, default=REPORT)
    args = parser.parse_args()
    dsn = args.dsn or os.environ.get("WORKBENCH_PG_DSN") or "host=127.0.0.1 port=5432 dbname=market_research user=postgres"
    token = uuid4().hex[:12]
    job_id = f"job-history-pg-probe-{token}"
    job_key = f"history-pg-probe-{token}"
    rollback_id = f"job-history-pg-rollback-{token}"
    payload = {"contract": "history-job-state-v1.0", "job_kind": "HISTORY_ANALYSIS", "request_identity": token, "request": {"slice_ids": ["probe-slice"]}}
    checks: dict[str, object] = {}
    failures: list[str] = []
    try:
        with PostgresRepository(dsn) as base:
            repository = PostgresHistoryJobRepository(base)
            with repository.transaction():
                repository.upsert_job(job_id=job_id, job_key=job_key, status="QUEUED", payload=payload)
                repository.upsert_attempt(job_id=job_id, attempt=1, status="QUEUED", payload={"attempt": 1, "progress": {"stage": "QUEUED"}})
                first_sequence = repository.append_event(job_id=job_id, attempt=1, status="QUEUED", details={"job_kind": "HISTORY_ANALYSIS"})
                repository.update_job(job_id, status="RUNNING", payload={**payload, "progress": {"stage": "RUNNING"}})
                repository.update_attempt(job_id, 1, status="RUNNING", payload={"attempt": 1, "progress": {"stage": "RUNNING"}})
                second_sequence = repository.append_event(job_id=job_id, attempt=1, status="RUNNING")
            loaded = repository.job(job_id)
            latest = repository.latest_attempt(job_id)
            events = repository.events(job_id)
            checks["job_roundtrip"] = loaded is not None and loaded["status"] == "RUNNING" and loaded["payload"].get("job_kind") == "HISTORY_ANALYSIS"
            checks["attempt_roundtrip"] = latest is not None and latest["status"] == "RUNNING"
            checks["event_sequence"] = [event["sequence"] for event in events] == [first_sequence, second_sequence] and first_sequence == 1 and second_sequence == 2
            checks["active_job_filter"] = job_id in repository.active_history_jobs()
            try:
                with repository.transaction():
                    repository.upsert_job(job_id=rollback_id, job_key=f"rollback-{token}", status="QUEUED", payload=payload)
                    repository.upsert_attempt(job_id=rollback_id, attempt=1, status="QUEUED", payload={"attempt": 1})
                    repository.append_event(job_id=rollback_id, attempt=1, status="QUEUED")
                    raise RuntimeError("ROLLBACK_PROBE")
            except RuntimeError as exc:
                checks["rollback_error"] = str(exc)
            checks["rollback_clean"] = repository.job(rollback_id) is None
            repository.delete_job(job_id)
            checks["cleanup"] = repository.job(job_id) is None and not repository.events(job_id)
    except Exception as exc:  # pragma: no cover - reports external database state
        checks["error"] = f"{type(exc).__name__}:{exc}"
        failures.append("postgres_history_job_repository")
    for key in ("job_roundtrip", "attempt_roundtrip", "event_sequence", "active_job_filter", "rollback_clean", "cleanup"):
        if checks.get(key) is not True:
            failures.append(key)
    report = {
        "contract_version": "PG_HISTORY_JOB_REPOSITORY_V1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "checks": checks,
        "failures": sorted(set(failures)),
        "online_switch_performed": False,
        "data_generation_triggered": False,
        "acceptance": "DEGRADED_PASS_HISTORY_JOB_REPOSITORY" if not failures else "BLOCKED",
        "next_stage": "wire_history_job_service_to_postgres_adapter_after_end_to_end_rehearsal" if not failures else "repair_history_job_repository",
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.report.with_suffix(args.report.suffix + ".tmp")
    temporary.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True, default=str), encoding="utf-8")
    os.replace(temporary, args.report)
    print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
    return 0 if not failures else 2


if __name__ == "__main__":
    raise SystemExit(main())
