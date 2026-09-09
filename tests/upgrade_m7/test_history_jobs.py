import json
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

import duckdb
import pytest

from workbench_db.migrations import BASE_SCHEMA_VERSION, MigrationExecutor
from workbench_service.history_jobs import HistoryJobError, HistoryJobService
from workbench_service.source_freezer import atomic_write_manifest, build_source_manifest


ROOT = Path(__file__).parents[2]


def _setup(tmp_path):
    database = tmp_path / "jobs.duckdb"
    con = duckdb.connect(str(database))
    con.execute((ROOT / "src/workbench_db/schema.sql").read_text(encoding="utf-8"))
    con.execute("insert into schema_migrations values (?, current_timestamp)", [BASE_SCHEMA_VERSION])
    MigrationExecutor(con).apply()
    source_file = tmp_path / "frozen-input.txt"
    source_file.write_text("frozen", encoding="utf-8")
    manifest = build_source_manifest(
        publication_id="pub-1", cutoff_date="2026-09-07", source_revision_id=1,
        source_identity_sha256="b" * 64, source_snapshot_manifest_sha256="c" * 64,
        source_bundle_id="bundle-1", observed_at="2026-09-07T08:00:00+00:00",
        window_plan={"output_start": "2026-08-01", "output_end": "2026-09-07", "read_start": "2026-05-01", "read_end": "2026-09-07", "output_days": 30, "required_history": 100},
        inputs=[{"path": "frozen-input.txt", "kind": "file", "role": "fixture", "sha256": __import__("hashlib").sha256(b"frozen").hexdigest(), "observed_at": "2026-09-07T08:00:00+00:00", "effective_date": "2026-09-07", "date_scope": {"as_of": "2026-09-07"}}],
    )
    report = tmp_path / "reports/upgrade_m7/source_manifest_20260907.json"
    atomic_write_manifest(report, manifest)
    con.execute("insert into publications values (?,?,?,?,?,?,?,?,?,?,?,?)", ["pub-1", "2026-09-07", 1, "SUCCESS", 1, "test", None, "b" * 64, None, None, "fixture", datetime.now(timezone.utc)])
    for index in range(3):
        con.execute("insert into analysis_slices values (?,?,?,?,?,?,?,?,?,?,?,?)", [f"slice-{index}", "quote_input", "2026-09-07", "quote-v1", f"input-{index}", "dependency", "{}", 1, f"logical-{index}", "PARQUET", f"obj-{index}", datetime.now(timezone.utc)])
    con.close()
    return database


def _request(slice_ids=None):
    return {"base_publication_id": "pub-1", "basis": "RECONSTRUCTED", "output_days": 30, "domains": ["quote_input"], "contract_bundle_id": "test-bundle", "idempotency_key": "request-1", "slice_ids": slice_ids or []}


def test_submit_is_idempotent_and_success_keeps_slices(tmp_path):
    database = _setup(tmp_path)
    service = HistoryJobService(tmp_path, database)
    first = service.submit(_request(["slice-0"]))
    deadline = time.monotonic() + 5
    while service.status(first["job_id"])["status"] in {"QUEUED", "RUNNING"} and time.monotonic() < deadline:
        time.sleep(0.02)
    final = service.status(first["job_id"])
    second = service.submit(_request(["slice-0"]))
    assert final["status"] == "SUCCESS" and final["completed_slice_ids"] == ["slice-0"]
    assert second["job_id"] == first["job_id"] and second["reused_submission"] is True
    with duckdb.connect(str(database), read_only=True) as con:
        assert con.execute("select count(*) from analysis_slices").fetchone()[0] == 3
        assert con.execute("select count(*) from job_events where job_id=?", [first["job_id"]]).fetchone()[0] >= 3


def test_cancel_at_batch_boundary_does_not_delete_completed_slice(tmp_path):
    database = _setup(tmp_path)
    started = threading.Event()

    def worker(_slice_id, _request):
        started.set()
        time.sleep(0.15)

    service = HistoryJobService(tmp_path, database, worker=worker)
    result = service.submit(_request(["slice-0", "slice-1", "slice-2"]))
    assert started.wait(5)
    running = service.status(result["job_id"])
    cancelled = service.cancel(result["job_id"], expected_attempt=running["attempt"])
    deadline = time.monotonic() + 5
    while service.status(result["job_id"])["status"] in {"QUEUED", "RUNNING"} and time.monotonic() < deadline:
        time.sleep(0.02)
    final = service.status(result["job_id"])
    assert final["status"] == "CANCELLED"
    with duckdb.connect(str(database), read_only=True) as con:
        assert con.execute("select count(*) from analysis_slices").fetchone()[0] == 3
    assert cancelled["job_id"] == result["job_id"]


def test_missing_manifest_fails_closed(tmp_path):
    database = _setup(tmp_path)
    (tmp_path / "reports/upgrade_m7/source_manifest_20260907.json").unlink()
    with pytest.raises(HistoryJobError, match="SOURCE_MANIFEST_NOT_FOUND"):
        HistoryJobService(tmp_path, database).submit(_request())
