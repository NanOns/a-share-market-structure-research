"""Rehearse PostgreSQL result-object metadata idempotency and rollback."""
from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from workbench_db.postgres_repository import PostgresRepository
from workbench_db.result_object_repository import PostgresResultObjectRepository


ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "runtime/postgres_migration/20260922/pg_result_object_repository_rehearsal_report.json"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dsn", default=None)
    args = parser.parse_args()
    dsn = args.dsn or os.environ.get("WORKBENCH_PG_DSN") or "host=127.0.0.1 port=5432 dbname=market_research user=postgres"
    token = uuid4().hex[:12]
    slice_id = f"slice-pg-result-probe-{token}"
    object_id = f"result-obj-pg-result-probe-{token}"
    created_at = datetime.now(timezone.utc)
    body = {
        "slice_id": slice_id,
        "result_object_id": object_id,
        "domain": "probe",
        "schema_version": "probe-v1",
        "semantic_contract": "probe",
        "value_hash": "a" * 64,
        "logical_hash": "b" * 64,
        "row_count": 1,
        "storage_kind": "PARQUET",
        "created_at": created_at,
        "object_path": "runtime/probe.parquet",
        "relative_path": "runtime/probe.parquet",
        "columns": ["security_id"],
        "primary_key": ["security_id"],
        "value_semantics": {},
        "basis": {"source_manifest_sha256": "c" * 64},
        "identity_evidence": {"value_hash": "a" * 64},
        "dependencies": [],
        "trade_date": "2026-09-22",
        "contract_id": "probe",
        "input_hash": "d" * 64,
        "dependency_hash": "e" * 64,
        "daily_basis": None,
    }
    checks: dict[str, object] = {}
    with PostgresRepository(dsn) as base:
        repository = PostgresResultObjectRepository(base)
        checks["first_persist_reused"] = repository.persist(**body)
        checks["second_persist_reused"] = repository.persist(**body)
        rollback_token = uuid4().hex[:12]
        rollback_body = {**body, "slice_id": f"slice-pg-result-rollback-{rollback_token}", "result_object_id": f"result-obj-pg-result-rollback-{rollback_token}", "value_hash": "f" * 64, "logical_hash": "e" * 64, "daily_basis": {"universe_basis": "probe"}}
        try:
            repository.persist(**rollback_body)
        except ValueError as exc:
            checks["rollback_error"] = str(exc)
        with base.transaction() as connection:
            with connection.cursor() as cur:
                cur.execute("select count(*) from workbench.analysis_slices where slice_id in (%s,%s)", (slice_id, rollback_body["slice_id"]))
                checks["visible_slice_count_before_cleanup"] = int(cur.fetchone()[0])
                cur.execute("delete from workbench.analysis_slice_result_bindings where slice_id=%s", (slice_id,))
                cur.execute("delete from workbench.analysis_slices where slice_id=%s", (slice_id,))
                cur.execute("delete from workbench.storage_objects where storage_object_id=%s", (object_id,))
                cur.execute("delete from workbench.analysis_result_objects where result_object_id=%s", (object_id,))
    checks["rollback_clean"] = checks.get("visible_slice_count_before_cleanup") == 1
    checks["idempotency"] = checks.get("first_persist_reused") is False and checks.get("second_persist_reused") is True
    report = {
        "contract_version": "PG_RESULT_OBJECT_REPOSITORY_V1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "online_switch_performed": False,
        "data_generation_triggered": False,
        "checks": checks,
        "acceptance": "DEGRADED_PASS_RESULT_OBJECT_REPOSITORY" if checks["idempotency"] and checks["rollback_clean"] else "BLOCKED",
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    temporary = REPORT.with_suffix(REPORT.suffix + ".tmp")
    temporary.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    os.replace(temporary, REPORT)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["acceptance"] != "BLOCKED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
