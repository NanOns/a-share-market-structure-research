"""Rehearse the PostgreSQL transaction boundary for incremental writes.

This probe intentionally writes one synthetic ``analysis_slices`` row and
rolls it back.  It validates the qmark-compatible DB-API surface used by the
existing domain writers without running a production build or changing the
active service configuration.
"""
from __future__ import annotations

import argparse
import json
import os
import uuid
from datetime import date, datetime, timezone
from pathlib import Path

import pandas as pd

from workbench_analysis.technical import TECHNICAL_RESULT_COLUMNS, insert_technical_result_rows
from workbench_db.incremental_writer_repository import PostgresIncrementalWriterRepository
from workbench_service.incremental_writer import IncrementalBuildCoordinator, SnapshotBinding


ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "runtime/postgres_migration/20260922/pg_incremental_writer_repository_rehearsal_report.json"


def atomic_write(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True, default=str), encoding="utf-8")
    os.replace(temporary, path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dsn", default=None)
    args = parser.parse_args()
    dsn = args.dsn or os.environ.get("WORKBENCH_PG_DSN") or "host=127.0.0.1 port=5432 dbname=market_research user=postgres"
    slice_id = "pg-incremental-rehearsal-" + uuid.uuid4().hex
    checks: dict[str, object] = {}
    failures: list[str] = []

    try:
        repository = PostgresIncrementalWriterRepository(dsn)
        with repository.connect() as connection:
            connection.execute("BEGIN TRANSACTION")
            connection.execute(
                "INSERT INTO analysis_slices VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                [slice_id, "technical", date(2099, 1, 1), "probe-contract-v1", "input-hash", "dependency-hash", '{"probe":true}', 0, "logical-hash", "DUCKDB", None, datetime.now(timezone.utc)],
            )
            row = connection.execute("SELECT slice_id,domain,cast(trade_date as varchar),basis_json FROM analysis_slices WHERE slice_id=?", [slice_id]).fetchone()
            checks["insert_visible_before_rollback"] = bool(row and str(row[0]) == slice_id and str(row[1]) == "technical" and str(row[2]) == "2099-01-01")
            checks["json_round_trip"] = bool(row and (row[3] == {"probe": True} or '"probe": true' in str(row[3]) or '"probe":true' in str(row[3])))
            connection.execute("ROLLBACK")
        with repository.connect() as connection:
            checks["rollback_left_no_row"] = connection.execute("SELECT 1 FROM analysis_slices WHERE slice_id=?", [slice_id]).fetchone() is None

        # Replay one existing technical result through the same writer used by
        # the coordinator, but bind it to a synthetic slice and roll the whole
        # transaction back.  This proves JSONB/NULL/date adaptation without
        # inserting a production row or running a build.
        with repository.connect() as connection:
            source = connection.execute(
                """select s.slice_id,b.result_object_id,s.row_count,s.domain,s.trade_date,
                          s.contract_id,s.input_hash,s.dependency_hash,s.basis_json,
                          s.logical_hash,s.storage_kind
                     from analysis_slices s join analysis_slice_result_bindings b using(slice_id)
                    where s.domain='technical' order by s.trade_date desc limit 1"""
            ).fetchone()
            if not source:
                failures.append("technical_source_slice_missing")
            else:
                source_slice, result_object_id, row_count, domain, trade_date, contract_id, input_hash, dependency_hash, basis_json, logical_hash, storage_kind = source
                columns = ",".join(TECHNICAL_RESULT_COLUMNS)
                rows = connection.execute(
                    f"select {columns} from technical_result_rows where result_object_id=? order by security_id,trade_date",
                    [result_object_id],
                ).fetchall()
                frame = pd.DataFrame(rows, columns=TECHNICAL_RESULT_COLUMNS)
                frame["date"] = frame["trade_date"]
                probe_slice = "pg-tech-writer-probe-" + uuid.uuid4().hex
                connection.execute("BEGIN TRANSACTION")
                connection.execute(
                    "INSERT INTO analysis_slices VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                    [probe_slice, domain, trade_date, contract_id, input_hash, dependency_hash, basis_json, row_count, logical_hash, storage_kind, None, datetime.now(timezone.utc)],
                )
                written = insert_technical_result_rows(connection, probe_slice, frame)
                checks["technical_writer_replay_rows"] = int(written) == int(row_count)
                snapshot_id = "pg-snapshot-probe-" + uuid.uuid4().hex
                publication_id = connection.execute("select publication_id from publications where status='SUCCESS' order by trade_date desc, revision desc limit 1").fetchone()[0]
                binding = SnapshotBinding(
                    snapshot_id=snapshot_id,
                    publication_id=str(publication_id),
                    binding_domain="LOCAL_RECONSTRUCTED",
                    cutoff_date=str(trade_date),
                    query_start=str(trade_date),
                    config_hash="probe-config-hash",
                    manifest_hash="probe-manifest-hash",
                    expected_task_keys=("probe-task",),
                )
                IncrementalBuildCoordinator._bind_snapshot(
                    connection,
                    binding,
                    [(("probe-task",), "technical", str(trade_date), probe_slice)],
                )
                checks["snapshot_binding_visible_before_rollback"] = connection.execute(
                    "select 1 from publication_analysis_snapshots where publication_id=? and domain=? and snapshot_id=?",
                    [str(publication_id), "LOCAL_RECONSTRUCTED", snapshot_id],
                ).fetchone() is not None
                connection.execute("ROLLBACK")
    except Exception as exc:  # pragma: no cover - external database evidence
        checks["error"] = f"{type(exc).__name__}:{exc}"
        failures.append("postgres_incremental_transaction")

    for name in ("insert_visible_before_rollback", "json_round_trip", "rollback_left_no_row", "technical_writer_replay_rows", "snapshot_binding_visible_before_rollback"):
        if checks.get(name) is not True:
            failures.append(name)
    report = {
        "contract_version": "PG_INCREMENTAL_WRITER_REPOSITORY_V1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "dsn_target": "market_research@127.0.0.1:5432 (password omitted)",
        "online_switch_performed": False,
        "data_generation_triggered": False,
        "checks": checks,
        "failures": sorted(set(failures)),
        "status": "PASS" if not failures else "BLOCKED",
        "acceptance": "DEGRADED_PASS_INCREMENTAL_WRITER_REPOSITORY" if not failures else "BLOCKED",
        "next_stage": "rehearse_each_domain_writer_and_snapshot_binding" if not failures else "repair_incremental_writer_repository",
    }
    atomic_write(REPORT, report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if not failures else 2


if __name__ == "__main__":
    raise SystemExit(main())
