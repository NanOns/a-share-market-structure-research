"""Record the application-side PostgreSQL cutover boundary.

This is deliberately a preflight, not a switch.  It turns the static
consumer scan into an auditable migration table so no DuckDB direct-connect
point can be mistaken for an already migrated application component.
"""
from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import psycopg


ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "runtime/postgres_migration/20260922/application_cutover_inventory.json"


def adapter_contract(path: str) -> tuple[str, str]:
    if path == "config/workbench.yaml":
        return "CONFIG_INJECTION", "replace engine/path with validated backend config only during maintenance window"
    if path.startswith("src/workbench_ops/"):
        return "OPERATIONS_REPOSITORY", "config/storage/backup/maintenance must use parameterized PG operations APIs"
    if path in {"src/workbench_service/app.py", "src/workbench_publish/service.py"}:
        return "WORKBENCH_REPOSITORY + OPERATIONS_REPOSITORY", "HTTP and publisher layers must not expose DuckDB connections"
    if path in {"src/workbench_service/incremental_writer.py", "src/workbench_service/research_builder.py", "src/workbench_service/v3_daily_entry.py", "src/workbench_service/result_objects.py", "src/workbench_service/slice_coordinator.py", "src/workbench_service/analysis_activation.py"}:
        return "RESEARCH_REPOSITORY", "result/run/slice writes require PG transaction and idempotency boundary"
    if path in {"src/workbench_service/source_freezer.py", "src/workbench_service/today_research_bundle.py", "src/workbench_service/turnover_enrichment_service.py"}:
        return "ARTIFACT_CATALOG + RESEARCH_REPOSITORY", "managed artifacts remain files; database references go through catalog/repository"
    if path == "src/workbench_service/history_jobs.py":
        return "OPERATIONS_REPOSITORY + RESEARCH_REPOSITORY", "job state and research data require separate PG transactions"
    if path == "src/workbench_db/repository.py":
        return "WORKBENCH_REPOSITORY + RELATION_REPOSITORY", "DuckDB repository implementation must be replaced behind stable boundary"
    return "UNMAPPED_ADAPTER", "no safe adapter mapping; keep cutover blocked"


def atomic_write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    os.replace(tmp, path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dsn", default=None)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    if not args.apply:
        raise SystemExit("Refusing to write migration inventory without --apply")
    dsn = args.dsn or os.environ.get("PG_DSN") or "host=127.0.0.1 port=5432 dbname=market_research user=postgres"
    now = datetime.now(timezone.utc)
    with psycopg.connect(dsn) as pg:
        with pg.cursor() as cur:
            cur.execute("""
                create table if not exists workbench_meta.migration_consumer_cutovers (
                    consumer_id text primary key,
                    relative_path text not null,
                    adapter_contract text not null,
                    current_backend text not null,
                    target_backend text not null,
                    status text not null,
                    evidence text not null,
                    rollback_contract text not null,
                    reviewed_at timestamptz not null
                )
            """)
            cur.execute("select consumer_id,relative_path,matched_contract,disposition from workbench_meta.consumer_catalog where disposition='MIGRATE_TO_PG' order by relative_path")
            consumers = cur.fetchall()
            rows = []
            for consumer_id, path, matched, disposition in consumers:
                contract, evidence = adapter_contract(path)
                status = "NOT_MIGRATED" if contract != "UNMAPPED_ADAPTER" else "BLOCKED_UNMAPPED"
                rows.append({"consumer_id": consumer_id, "relative_path": path, "matched_contract": matched, "adapter_contract": contract, "current_backend": "DUCKDB", "target_backend": "POSTGRESQL", "status": status, "evidence": evidence})
                cur.execute("""
                    insert into workbench_meta.migration_consumer_cutovers
                    (consumer_id,relative_path,adapter_contract,current_backend,target_backend,status,evidence,rollback_contract,reviewed_at)
                    values (%s,%s,%s,'DUCKDB','POSTGRESQL',%s,%s,%s,%s)
                    on conflict (consumer_id) do update set relative_path=excluded.relative_path,adapter_contract=excluded.adapter_contract,current_backend=excluded.current_backend,target_backend=excluded.target_backend,status=excluded.status,evidence=excluded.evidence,rollback_contract=excluded.rollback_contract,reviewed_at=excluded.reviewed_at
                """, (consumer_id, path, contract, status, evidence, "stop PG writes; export PG-only delta or restore pre-cutover state with explicit data-gap receipt", now))
        pg.commit()
    unmapped = [row["relative_path"] for row in rows if row["status"] == "BLOCKED_UNMAPPED"]
    report = {
        "contract_version": "PG_APPLICATION_CUTOVER_INVENTORY_V1",
        "generated_at_utc": now.isoformat(),
        "online_switch_performed": False,
        "data_generation_triggered": False,
        "consumer_count": len(rows),
        "all_consumer_rows_recorded": len(rows) == 19,
        "unmapped_consumers": unmapped,
        "status_counts": {status: sum(row["status"] == status for row in rows) for status in sorted({row["status"] for row in rows})},
        "consumers": rows,
        "acceptance": "DEGRADED_PASS_PRECUTOVER_INVENTORY" if len(rows) == 19 and not unmapped else "BLOCKED",
        "next_stage": "implement repository adapters and isolated config rollback" if not unmapped else "map unmapped direct consumers before adapter work",
    }
    atomic_write(REPORT, report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["acceptance"] != "BLOCKED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
