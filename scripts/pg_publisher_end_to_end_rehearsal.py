"""Rehearse the OneClickPublisher PostgreSQL path end to end.

This is an isolated migration acceptance probe.  It writes one uniquely
identified publication, relation observation/binding and signal outcome to
PostgreSQL, checks the status projection and then removes every probe row.
It never changes the configured online backend and never runs production
generation.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from workbench_db.postgres_publication_writer import PostgresPublicationWriter  # noqa: E402
from workbench_db.postgres_repository import PostgresRepository  # noqa: E402
from workbench_db.publication_repository import PostgresPublicationBackendFactory  # noqa: E402
from workbench_publish import OneClickPublisher, PublicationRequest, SimulatedCrash  # noqa: E402


ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "runtime/postgres_migration/20260922/pg_publisher_end_to_end_rehearsal_report.json"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dsn", default=None)
    parser.add_argument("--report", type=Path, default=REPORT)
    args = parser.parse_args()
    dsn = args.dsn or os.environ.get("WORKBENCH_PG_DSN") or "host=127.0.0.1 port=5432 dbname=market_research user=postgres"
    token = uuid4().hex[:12]
    bundle_id = f"pg-publisher-probe-bundle-{token}"
    publication_id = f"pg-publisher-probe-{token}"
    observation_id = f"pg-publisher-probe-observation-{token}"
    security_id = f"PROBE.{token}"
    trade_date = date(2026, 9, 22)
    prior_head: str | None = None
    checks: dict[str, object] = {}
    failures: list[str] = []
    request = PublicationRequest(
        trade_date=trade_date,
        source_bundle_id=bundle_id,
        economic_model_id="pg-publisher-probe-model-v1",
        computation_contract_id="pg-publisher-probe-compute-v1",
        release_id=publication_id,
        stocks=({"security_id": security_id, "security_name": "PG probe", "primary_pattern": "TEST"},),
        observations=({"observation_id": observation_id, "security_id": security_id, "signal": "PROBE"},),
        outcomes=({"observation_id": observation_id, "horizon": 1, "target_revision": 1, "status": "PROBE"},),
    )
    try:
        with PostgresRepository(dsn) as snapshot:
            with snapshot.connection.cursor() as cur:  # type: ignore[union-attr]
                cur.execute("select publication_id from workbench.publication_heads where trade_date=%s", (trade_date,))
                row = cur.fetchone()
                prior_head = str(row[0]) if row else None
        factory = PostgresPublicationBackendFactory(dsn)
        publisher = OneClickPublisher(
            ROOT,
            bundle_verifier=lambda _: {"status": "PASS", "source_bundle_id": bundle_id},
            postgres_backend_factory=factory,
        )
        try:
            publisher.run(request, crash_at="before_commit")
        except SimulatedCrash:
            checks["crash_before_commit"] = True
        status_before_recovery = OneClickPublisher(ROOT, bundle_verifier=lambda _: {"status": "PASS", "source_bundle_id": bundle_id}, postgres_backend_factory=factory)
        checks["interrupted_status"] = status_before_recovery.status("job-" + request.job_key[:32]).get("status") == "INTERRUPTED"
        recovered = status_before_recovery.recover_interrupted()
        result = recovered[0] if recovered else {}
        checks["publisher_recovery"] = result.get("status") == "SUCCESS" and result.get("publication_id") == publication_id
        checks["publisher_run"] = checks["publisher_recovery"]
        status_publisher = OneClickPublisher(ROOT, bundle_verifier=lambda _: {"status": "PASS", "source_bundle_id": bundle_id}, postgres_backend_factory=factory)
        checks["publisher_status"] = status_publisher.status(result["job_id"]).get("status") == "SUCCESS"
        with PostgresRepository(dsn) as repository:
            writer = PostgresPublicationWriter(repository)
            loaded = writer.publication(publication_id)
            checks["publication_roundtrip"] = bool(loaded and loaded["status"] == "SUCCESS")
            with repository.connection.cursor() as cur:  # type: ignore[union-attr]
                cur.execute("select count(*) from workbench.stock_daily where publication_id=%s", (publication_id,))
                checks["stock_row"] = int(cur.fetchone()[0]) == 1
                cur.execute("select count(*) from workbench.observations where observation_id=%s", (observation_id,))
                checks["observation_row"] = int(cur.fetchone()[0]) == 1
                cur.execute("select count(*) from workbench.outcomes where observation_id=%s", (observation_id,))
                checks["outcome_row"] = int(cur.fetchone()[0]) == 1
                cur.execute("select publication_id from workbench.publication_heads where trade_date=%s", (trade_date,))
                checks["head_binding"] = cur.fetchone()[0] == publication_id
            with repository.transaction() as connection:
                with connection.cursor() as cur:
                    for table, column, value in (
                        ("outcomes", "observation_id", observation_id),
                        ("observations", "observation_id", observation_id),
                        ("stock_daily", "publication_id", publication_id),
                    ):
                        cur.execute(f"delete from workbench.{table} where {column}=%s", (value,))
                    if prior_head:
                        cur.execute("update workbench.publication_heads set publication_id=%s where trade_date=%s", (prior_head, trade_date))
                    else:
                        cur.execute("delete from workbench.publication_heads where trade_date=%s", (trade_date,))
                    cur.execute("delete from workbench.publications where publication_id=%s", (publication_id,))
                    cur.execute("delete from workbench.job_events where job_id=%s", (result["job_id"],))
                    cur.execute("delete from workbench.job_attempts where job_id=%s", (result["job_id"],))
                    cur.execute("delete from workbench.jobs where job_id=%s", (result["job_id"],))
            checks["cleanup"] = writer.publication(publication_id) is None
    except Exception as exc:  # pragma: no cover - external database state
        checks["error"] = f"{type(exc).__name__}:{exc}"
        failures.append("pg_publisher_end_to_end")
    for key in ("crash_before_commit", "interrupted_status", "publisher_recovery", "publisher_run", "publisher_status", "publication_roundtrip", "stock_row", "observation_row", "outcome_row", "head_binding", "cleanup"):
        if checks.get(key) is not True:
            failures.append(key)
    report = {
        "contract_version": "PG_PUBLISHER_END_TO_END_V1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "checks": checks,
        "failures": sorted(set(failures)),
        "online_switch_performed": False,
        "data_generation_triggered": False,
        "acceptance": "DEGRADED_PASS_PG_PUBLISHER_END_TO_END" if not failures else "BLOCKED",
        "next_stage": "wire_application_publisher_factory_after_maintenance_cutover" if not failures else "repair_pg_publisher_end_to_end",
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.report.with_suffix(args.report.suffix + ".tmp")
    temporary.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True, default=str), encoding="utf-8")
    os.replace(temporary, args.report)
    print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
    return 0 if not failures else 2


if __name__ == "__main__":
    raise SystemExit(main())
