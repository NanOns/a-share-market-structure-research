"""Rehearse HistoryJobService against the PostgreSQL job repository.

The source-manifest verifier is replaced only inside this isolated probe so
the service state machine can be tested against an existing migrated
publication without creating or changing production artifacts.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from workbench_db.postgres_history_job_repository import PostgresHistoryJobRepository  # noqa: E402
from workbench_db.postgres_repository import PostgresRepository  # noqa: E402
from workbench_service.history_jobs import HistoryJobService  # noqa: E402


ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "runtime/postgres_migration/20260922/pg_history_job_service_rehearsal_report.json"


class ProbeHistoryJobService(HistoryJobService):
    def _manifest_for(self, publication_id: str):  # type: ignore[override]
        with self._repository.transaction() as store:
            cutoff, _ = store.publication_source_identity(publication_id)
        return ({"manifest_sha256": "p" * 64, "window": {"output_days": 250}}, cutoff, "runtime/probe/source_manifest.json")


def wait_terminal(service: HistoryJobService, job_id: str, timeout: float = 10.0) -> dict:
    deadline = time.monotonic() + timeout
    latest = service.status(job_id)
    while latest["status"] in {"QUEUED", "RUNNING"} and time.monotonic() < deadline:
        time.sleep(0.03)
        latest = service.status(job_id)
    return latest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dsn", default=None)
    parser.add_argument("--report", type=Path, default=REPORT)
    args = parser.parse_args()
    dsn = args.dsn or os.environ.get("WORKBENCH_PG_DSN") or "host=127.0.0.1 port=5432 dbname=market_research user=postgres"
    token = uuid4().hex[:12]
    checks: dict[str, object] = {}
    failures: list[str] = []
    job_ids: list[str] = []
    try:
        with PostgresRepository(dsn) as base:
            with base.connection.cursor() as cur:  # type: ignore[union-attr]
                cur.execute("select publication_id from workbench.publications where status='SUCCESS' order by trade_date desc,revision desc limit 1")
                publication_id = str(cur.fetchone()[0])
                cur.execute("select slice_id,domain from workbench.analysis_slices where domain='mainline' order by slice_id limit 2")
                slices = cur.fetchall()
            if len(slices) < 2:
                raise RuntimeError("PG_HISTORY_PROBE_SLICES_MISSING")
            slice_ids = [str(row[0]) for row in slices]
            domain = str(slices[0][1])
            repository = PostgresHistoryJobRepository(base)

            request = {
                "base_publication_id": publication_id,
                "basis": "RECONSTRUCTED",
                "output_days": 1,
                "domains": [domain],
                "contract_bundle_id": "pg-history-probe-v1",
                "idempotency_key": f"success-{token}",
                "slice_ids": [slice_ids[0]],
            }
            service = ProbeHistoryJobService(ROOT, repository=repository)
            first = service.submit(request)
            job_ids.append(first["job_id"])
            final = wait_terminal(service, first["job_id"])
            checks["service_success"] = final["status"] == "SUCCESS" and final["completed_slice_ids"] == [slice_ids[0]]
            repeated = service.submit(request)
            checks["idempotent_submit"] = repeated["job_id"] == first["job_id"] and repeated.get("reused_submission") is True

            started = threading.Event()

            def worker(_slice_id: str, _request: dict) -> None:
                started.set()
                time.sleep(0.25)

            cancel_request = {**request, "idempotency_key": f"cancel-{token}", "slice_ids": slice_ids}
            cancelling = ProbeHistoryJobService(ROOT, repository=repository, worker=worker)
            pending = cancelling.submit(cancel_request)
            job_ids.append(pending["job_id"])
            checks["cancel_worker_started"] = started.wait(5)
            running = cancelling.status(pending["job_id"])
            cancelled = cancelling.cancel(pending["job_id"], expected_attempt=running["attempt"])
            final_cancel = wait_terminal(cancelling, pending["job_id"])
            checks["cancel_at_boundary"] = cancelled["job_id"] == pending["job_id"] and final_cancel["status"] == "CANCELLED" and final_cancel["completed_slice_ids"] == [slice_ids[0]]
            checks["pg_event_projection"] = bool(final_cancel.get("latest_event") and final_cancel["latest_event"].get("status") == "CANCELLED")

            with base.transaction():
                for job_id in job_ids:
                    repository.delete_job(job_id)
            checks["cleanup"] = all(repository.job(job_id) is None and not repository.events(job_id) for job_id in job_ids)
    except Exception as exc:  # pragma: no cover - external database state
        checks["error"] = f"{type(exc).__name__}:{exc}"
        failures.append("pg_history_job_service")
    for key in ("service_success", "idempotent_submit", "cancel_worker_started", "cancel_at_boundary", "pg_event_projection", "cleanup"):
        if checks.get(key) is not True:
            failures.append(key)
    report = {
        "contract_version": "PG_HISTORY_JOB_SERVICE_V1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "checks": checks,
        "failures": sorted(set(failures)),
        "online_switch_performed": False,
        "data_generation_triggered": False,
        "acceptance": "DEGRADED_PASS_PG_HISTORY_JOB_SERVICE" if not failures else "BLOCKED",
        "next_stage": "wire_history_job_service_factory_after_maintenance_cutover" if not failures else "repair_pg_history_job_service",
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.report.with_suffix(args.report.suffix + ".tmp")
    temporary.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True, default=str), encoding="utf-8")
    os.replace(temporary, args.report)
    print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
    return 0 if not failures else 2


if __name__ == "__main__":
    raise SystemExit(main())
