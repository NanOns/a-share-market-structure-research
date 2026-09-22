"""Rehearse PostgreSQL publication metadata and bulk-row transaction."""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from workbench_db.postgres_repository import PostgresRepository  # noqa: E402
from workbench_db.postgres_publication_writer import PostgresPublicationWriter  # noqa: E402


ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "runtime/postgres_migration/20260922/pg_publication_writer_rehearsal_report.json"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dsn", default=None)
    parser.add_argument("--report", type=Path, default=REPORT)
    args = parser.parse_args()
    dsn = args.dsn or os.environ.get("WORKBENCH_PG_DSN") or "host=127.0.0.1 port=5432 dbname=market_research user=postgres"
    token = uuid4().hex[:12]
    publication_id = f"pub-pg-writer-probe-{token}"
    rollback_id = f"pub-pg-writer-rollback-{token}"
    trade_date = date(2026, 9, 22)
    checks: dict[str, object] = {}
    failures: list[str] = []
    try:
        with PostgresRepository(dsn) as base:
            writer = PostgresPublicationWriter(base)
            with writer.transaction():
                revision = writer.next_revision(trade_date)
                writer.insert_publication(publication_id=publication_id, trade_date=trade_date, revision=revision, status="IMPORTING", source_revision_id=None, production_version="probe", source_manifest_sha256="a" * 64, source_identity_sha256="b" * 64, computation_identity_sha256="c" * 64, render_identity_sha256="d" * 64, source_path="runtime/probe", imported_at_utc=datetime.now(timezone.utc))
                writer.bulk_insert("stock_daily", ("publication_id", "security_id", "trade_date", "security_name", "primary_pattern", "payload_json"), [{"publication_id": publication_id, "security_id": f"probe-{token}", "trade_date": trade_date, "security_name": "probe", "primary_pattern": "TEST", "payload_json": {"probe": True}}])
                writer.insert_artifact(publication_id=publication_id, artifact_name="probe.csv", source_path="runtime/probe.csv", file_sha256="e" * 64, logical_digest_version="probe-v1", logical_sha256="f" * 64, row_count=1, columns=("security_id",), primary_key=("security_id",))
                observation_id = f"obs-pg-writer-{token}"
                writer.insert_observation(observation_id=observation_id, publication_id=publication_id, payload={"probe": True})
                writer.insert_outcome(observation_id=observation_id, horizon=5, target_revision=revision, payload={"return": 0.1})
                writer.insert_outcome(observation_id=observation_id, horizon=5, target_revision=revision, payload={"return": 0.1})
                writer.mark_publication_success(publication_id)
                writer.set_head(trade_date, publication_id)
            loaded = writer.publication(publication_id)
            checks["publication_roundtrip"] = loaded is not None and loaded["status"] == "SUCCESS" and loaded["publication_id"] == publication_id
            with base.connection.cursor() as cur:  # type: ignore[union-attr]
                cur.execute("select count(*) from workbench.stock_daily where publication_id=%s", (publication_id,))
                checks["bulk_row_count"] = int(cur.fetchone()[0]) == 1
                cur.execute("select count(*) from workbench.publication_artifacts where publication_id=%s", (publication_id,))
                checks["artifact_row_count"] = int(cur.fetchone()[0]) == 1
                cur.execute("select count(*) from workbench.outcomes where observation_id=%s", (observation_id,))
                checks["outcome_row_count"] = int(cur.fetchone()[0]) == 1
                cur.execute("select publication_id from workbench.publication_heads where trade_date=%s", (trade_date,))
                checks["head_binding"] = cur.fetchone()[0] == publication_id
            try:
                with writer.transaction():
                    writer.insert_publication(publication_id=rollback_id, trade_date=date(2026, 9, 23), revision=writer.next_revision(date(2026, 9, 23)), status="IMPORTING", source_revision_id=None, production_version="probe", source_manifest_sha256="e" * 64, source_identity_sha256="f" * 64, computation_identity_sha256="0" * 64, render_identity_sha256="1" * 64, source_path="runtime/probe", imported_at_utc=datetime.now(timezone.utc))
                    raise RuntimeError("ROLLBACK_PROBE")
            except RuntimeError as exc:
                checks["rollback_error"] = str(exc)
            checks["rollback_clean"] = writer.publication(rollback_id) is None
            with base.transaction() as connection:
                with connection.cursor() as cur:
                    cur.execute("delete from workbench.publication_heads where trade_date=%s", (trade_date,))
                    cur.execute("delete from workbench.stock_daily where publication_id=%s", (publication_id,))
                    cur.execute("delete from workbench.outcomes where observation_id=%s", (observation_id,))
                    cur.execute("delete from workbench.observations where observation_id=%s", (observation_id,))
                    cur.execute("delete from workbench.publication_artifacts where publication_id=%s", (publication_id,))
                    cur.execute("delete from workbench.publications where publication_id=%s", (publication_id,))
            checks["cleanup"] = writer.publication(publication_id) is None
    except Exception as exc:  # pragma: no cover - reports external database state
        checks["error"] = f"{type(exc).__name__}:{exc}"
        failures.append("postgres_publication_writer")
    for key in ("publication_roundtrip", "bulk_row_count", "artifact_row_count", "outcome_row_count", "head_binding", "rollback_clean", "cleanup"):
        if checks.get(key) is not True:
            failures.append(key)
    report = {"contract_version": "PG_PUBLICATION_WRITER_V1", "generated_at_utc": datetime.now(timezone.utc).isoformat(), "checks": checks, "failures": sorted(set(failures)), "online_switch_performed": False, "data_generation_triggered": False, "acceptance": "DEGRADED_PASS_PUBLICATION_WRITER" if not failures else "BLOCKED", "next_stage": "integrate_postgres_publication_writer_with_relation_binding_and_publisher_recovery" if not failures else "repair_postgres_publication_writer"}
    args.report.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.report.with_suffix(args.report.suffix + ".tmp")
    temporary.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True, default=str), encoding="utf-8")
    os.replace(temporary, args.report)
    print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
    return 0 if not failures else 2


if __name__ == "__main__":
    raise SystemExit(main())
