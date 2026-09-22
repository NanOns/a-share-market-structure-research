"""Rehearse PostgreSQL sealed-slice metadata and dependency rollback."""
from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from workbench_db.postgres_repository import PostgresRepository
from workbench_db.slice_repository import PostgresSliceRepository


ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "runtime/postgres_migration/20260922/pg_slice_repository_rehearsal_report.json"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dsn", default=None)
    args = parser.parse_args()
    dsn = args.dsn or os.environ.get("WORKBENCH_PG_DSN") or "host=127.0.0.1 port=5432 dbname=market_research user=postgres"
    token = uuid4().hex[:12]
    base = f"slice-pg-slice-probe-{token}"
    dependent = f"slice-pg-slice-dependent-{token}"
    rollback = f"slice-pg-slice-rollback-{token}"
    base_object = f"analysis-obj-pg-slice-probe-{token}"
    dependent_object = f"analysis-obj-pg-slice-dependent-{token}"
    rollback_object = f"analysis-obj-pg-slice-rollback-{token}"
    now = datetime.now(timezone.utc)
    common = dict(domain="probe", trade_date="2026-09-22", contract_id="probe-v1", input_hash="a" * 64, dependency_hash="b" * 64, basis={"source_manifest_sha256": "c" * 64}, row_count=1, storage_kind="PARQUET", created_at=now)
    checks: dict[str, object] = {}
    with PostgresRepository(dsn) as base_repository:
        repository = PostgresSliceRepository(base_repository)
        repository.seal(slice_id=base, logical_hash="d" * 64, storage_object_id=base_object, object_payload={"logical_hash": "d" * 64}, dependencies=[], **common)
        checks["base_visible"] = repository.existing(base) is not None
        repository.seal(slice_id=dependent, logical_hash="e" * 64, storage_object_id=dependent_object, object_payload={"logical_hash": "e" * 64}, dependencies=[{"input_domain": "probe", "input_date": "2026-09-22", "input_slice_id": base}], **{**common, "input_hash": "f" * 64, "dependency_hash": "0" * 64})
        checks["dependent_visible"] = repository.existing(dependent) is not None
        try:
            repository.seal(slice_id=rollback, logical_hash="1" * 64, storage_object_id=rollback_object, object_payload={"logical_hash": "1" * 64}, dependencies=[], **{**common, "input_hash": "2" * 64, "dependency_hash": "3" * 64, "basis": {"daily_basis": {"universe_basis": "probe"}}})
        except ValueError as exc:
            checks["rollback_error"] = str(exc)
        checks["rollback_clean"] = repository.existing(rollback) is None
        with base_repository.transaction() as connection:
            with connection.cursor() as cur:
                cur.execute("delete from workbench.analysis_slice_dependencies where slice_id in (%s,%s)", (dependent, rollback))
                cur.execute("delete from workbench.analysis_slices where slice_id in (%s,%s)", (base, dependent))
                cur.execute("delete from workbench.storage_objects where storage_object_id in (%s,%s,%s)", (base_object, dependent_object, rollback_object))
    checks["dependency_and_rollback"] = checks.get("base_visible") is True and checks.get("dependent_visible") is True and checks.get("rollback_clean") is True
    report = {
        "contract_version": "PG_SLICE_REPOSITORY_V1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "online_switch_performed": False,
        "data_generation_triggered": False,
        "checks": checks,
        "acceptance": "DEGRADED_PASS_SLICE_REPOSITORY" if checks["dependency_and_rollback"] else "BLOCKED",
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    temporary = REPORT.with_suffix(REPORT.suffix + ".tmp")
    temporary.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    os.replace(temporary, REPORT)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["acceptance"] != "BLOCKED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
