"""Rehearse the PostgreSQL publication job-status reader."""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from workbench_db.postgres_repository import PostgresRepository  # noqa: E402
from workbench_db.publication_repository import PostgresPublicationStatusReader  # noqa: E402


ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "runtime/postgres_migration/20260922/pg_publication_status_reader_rehearsal_report.json"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dsn", default=None)
    parser.add_argument("--report", type=Path, default=REPORT)
    args = parser.parse_args()
    dsn = args.dsn or os.environ.get("WORKBENCH_PG_DSN") or "host=127.0.0.1 port=5432 dbname=market_research user=postgres"
    token = uuid4().hex[:12]
    job_id = f"job-publisher-status-probe-{token}"
    checks: dict[str, object] = {}
    failures: list[str] = []
    try:
        with PostgresRepository(dsn) as base:
            reader = PostgresPublicationStatusReader(base)
            payload = {"contract": "m4-one-click-publication-contract-v1.1", "publication_id": f"pub-probe-{token}", "request": {"probe": True}}
            event = {"status": "COMMITTING", "publication_id": payload["publication_id"]}
            with base.transaction() as connection:
                with connection.cursor() as cur:
                    cur.execute("insert into workbench.jobs(job_id,job_key,status,payload_json) values (%s,%s,%s,%s::jsonb)", (job_id, f"publisher-probe-{token}", "RUNNING", json.dumps(payload)))
                    cur.execute("insert into workbench.job_events(job_id,attempt,sequence,event_time_utc,payload_json) values (%s,%s,%s,%s,%s::jsonb)", (job_id, 1, 1, datetime.now(timezone.utc), json.dumps(event)))
            result = reader.read(job_id)
            checks["roundtrip"] = result["job_id"] == job_id and result["status"] == "RUNNING" and result["publication_id"] == payload["publication_id"]
            checks["event_projection"] = result["progress"] == event and result["updated_at_utc"] is not None
            with base.transaction() as connection:
                with connection.cursor() as cur:
                    cur.execute("delete from workbench.job_events where job_id=%s", (job_id,))
                    cur.execute("delete from workbench.jobs where job_id=%s", (job_id,))
            checks["cleanup"] = False
            try:
                reader.read(job_id)
            except KeyError:
                checks["cleanup"] = True
    except Exception as exc:  # pragma: no cover - reports external database state
        checks["error"] = f"{type(exc).__name__}:{exc}"
        failures.append("postgres_publication_status_reader")
    for key in ("roundtrip", "event_projection", "cleanup"):
        if checks.get(key) is not True:
            failures.append(key)
    report = {"contract_version": "PG_PUBLICATION_STATUS_READER_V1", "generated_at_utc": datetime.now(timezone.utc).isoformat(), "checks": checks, "failures": sorted(set(failures)), "online_switch_performed": False, "data_generation_triggered": False, "acceptance": "DEGRADED_PASS_PUBLICATION_STATUS_READER" if not failures else "BLOCKED", "next_stage": "wire_postgres_publication_status_reader_with_publication_writer_rehearsal" if not failures else "repair_publication_status_reader"}
    args.report.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.report.with_suffix(args.report.suffix + ".tmp")
    temporary.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True, default=str), encoding="utf-8")
    os.replace(temporary, args.report)
    print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
    return 0 if not failures else 2


if __name__ == "__main__":
    raise SystemExit(main())
