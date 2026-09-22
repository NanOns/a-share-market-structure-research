"""Run an isolated PostgreSQL cutover rehearsal without changing online config."""
from __future__ import annotations

import argparse
import json
import os
import socket
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from src.workbench_db.postgres_repository import PostgresRepository
DEFAULT_REPORT = ROOT / "runtime/postgres_migration/20260922/cutover_rehearsal_report.json"


def http_json(url: str) -> tuple[int | None, object, str | None]:
    try:
        with urllib.request.urlopen(url, timeout=5) as response:
            raw = response.read()
            return response.status, json.loads(raw.decode("utf-8")), None
    except (urllib.error.URLError, TimeoutError, ValueError, OSError) as exc:
        return None, None, f"{type(exc).__name__}:{exc}"


def atomic_write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    os.replace(tmp, path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dsn", default=None)
    parser.add_argument("--service-url", default="http://127.0.0.1:28765")
    parser.add_argument("--report", default=str(DEFAULT_REPORT))
    args = parser.parse_args()
    checks: dict[str, object] = {}
    failures: list[str] = []

    try:
        with PostgresRepository(args.dsn) as repo:
            settings = repo.fetch("select current_database(), current_schema(), current_setting('TimeZone'), current_setting('statement_timeout')")
            checks["repository_session"] = {"database": settings[0][0], "schema": settings[0][1], "timezone": settings[0][2], "statement_timeout": settings[0][3]}
            if settings[0][2] != "UTC" or settings[0][3] != "30s":
                failures.append("repository_session_contract")
            counts = repo.table_counts(("publications", "research_candidates_v3_3", "online_batches", "online_quote_entries"))
            checks["key_table_counts"] = counts
            if counts["publications"] <= 0 or counts["research_candidates_v3_3"] <= 0:
                failures.append("key_table_counts")
            disposition = repo.fetch("select disposition, count(*) from workbench_meta.consumer_catalog group by disposition order by disposition")
            checks["consumer_dispositions"] = {row[0]: int(row[1]) for row in disposition}
            if checks["consumer_dispositions"].get("MIGRATE_TO_PG") != 19 or checks["consumer_dispositions"].get("UNCLASSIFIED", 0) != 0:
                failures.append("consumer_catalog_gate")
            # Transaction rehearsal: prove a write can be rolled back without
            # touching a business table or leaving metadata behind.
            with repo.transaction() as connection:
                with connection.cursor() as cur:
                    cur.execute("create temporary table cutover_rehearsal_events (event_id text primary key, created_at timestamptz not null) on commit drop")
                    cur.execute("insert into cutover_rehearsal_events values (%s, now())", ("rollback-probe",))
                    cur.execute("select count(*) from cutover_rehearsal_events")
                    checks["transaction_probe_before_rollback"] = int(cur.fetchone()[0])
                    connection.rollback()
            # The context manager starts a fresh transaction for this check;
            # temporary tables are transaction-scoped and therefore absent.
            with repo.connection.cursor() as cur:  # type: ignore[union-attr]
                cur.execute("select to_regclass('pg_temp.cutover_rehearsal_events')")
                checks["transaction_probe_after_rollback"] = cur.fetchone()[0]
            if checks["transaction_probe_after_rollback"] is not None:
                failures.append("transaction_rollback")
    except Exception as exc:
        checks["repository_error"] = f"{type(exc).__name__}:{exc}"
        failures.append("repository_connection")

    for path in ("/api/operations/status", "/api/publications?include_analysis=0"):
        status, body, error = http_json(args.service_url.rstrip("/") + path)
        checks[f"service{path}"] = {"status": status, "error": error, "body_type": type(body).__name__, "body_head": (body[:1] if isinstance(body, list) else body if isinstance(body, dict) else None)}
        if status != 200 or error is not None:
            failures.append(f"service:{path}")

    report = {
        "contract_version": "PG_CUTOVER_REHEARSAL_V1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "dsn_target": "market_research@127.0.0.1:5432 (password omitted)",
        "online_switch_performed": False,
        "data_generation_triggered": False,
        "checks": checks,
        "failures": failures,
        "status": "PASS" if not failures else "FAIL",
        "next_stage": "application_adapter_integration_and_config_rollback" if not failures else "repair_rehearsal_failures",
    }
    atomic_write(Path(args.report), report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if not failures else 2


if __name__ == "__main__":
    raise SystemExit(main())
