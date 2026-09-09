import hashlib
import json
from datetime import date, timedelta, timezone, datetime
from pathlib import Path

import duckdb

from workbench_ops import BackupService, StorageGovernance


def _root(tmp_path):
    (tmp_path / "config").mkdir()
    (tmp_path / "config/paths.yaml").write_text('tdx:\n  root: "D:/new_tdx"\n', encoding="utf-8")
    db = tmp_path / "data/database/market_research.duckdb"
    db.parent.mkdir(parents=True)
    with duckdb.connect(str(db)) as con:
        con.execute("CREATE TABLE config_versions (config_revision VARCHAR PRIMARY KEY, payload_json JSON NOT NULL)")
        con.execute("CREATE TABLE backup_catalog (backup_id VARCHAR PRIMARY KEY, payload_json JSON NOT NULL)")
        con.execute("CREATE TABLE storage_objects (storage_object_id VARCHAR PRIMARY KEY, payload_json JSON NOT NULL)")
        con.execute("CREATE TABLE leases (lease_id VARCHAR PRIMARY KEY, payload_json JSON NOT NULL)")
        con.execute("CREATE TABLE cleanup_jobs (cleanup_job_id VARCHAR PRIMARY KEY, payload_json JSON NOT NULL)")
        con.execute("CREATE TABLE jobs (job_id VARCHAR PRIMARY KEY, job_key VARCHAR, status VARCHAR NOT NULL, payload_json JSON)")
        for table in ("publication_heads", "queue_memberships", "membership_entries", "outcomes"):
            con.execute(f"CREATE TABLE {table} (id INTEGER)")
            con.execute(f"INSERT INTO {table} VALUES (1)")
    return db


def test_history_backup_restores_database_and_referenced_object(tmp_path):
    db = _root(tmp_path)
    obj = tmp_path / "data/analysis_objects/slice.parquet"
    obj.parent.mkdir(parents=True)
    obj.write_bytes(b"immutable-slice")
    digest = hashlib.sha256(obj.read_bytes()).hexdigest()
    payload = {"storage_object_id": "slice-1", "path": str(obj), "relative_path": "data/analysis_objects/slice.parquet", "physical_sha256": digest, "referenced": True, "state": "ACTIVE"}
    with duckdb.connect(str(db)) as con:
        con.execute("INSERT INTO storage_objects VALUES (?, ?)", ["slice-1", json.dumps(payload)])
    service = BackupService(tmp_path, db)
    record = service.create_history_backup(maintenance_window=True)
    assert record["object_count"] == 1 and Path(record["manifest_path"]).is_file()
    result = service.restore_drill(record["backup_id"], drill_root=tmp_path / "runtime/drill")
    assert result["status"] == "PASS" and result["object_count"] == 1
    restored = Path(result["restored_objects"][0]["path"])
    assert restored.read_bytes() == b"immutable-slice"
    with duckdb.connect(result["restore_drill_path"], read_only=True) as con:
        assert con.execute("SELECT count(*) FROM publication_heads").fetchone()[0] == 1


def test_cleanup_preview_protects_active_lease_and_preparing_job(tmp_path):
    db = _root(tmp_path)
    storage = StorageGovernance(tmp_path, db)
    lease_path = tmp_path / "reports/lease-object"
    job_path = tmp_path / "reports/job-object"
    lease_path.mkdir(parents=True)
    job_path.mkdir(parents=True)
    lease_id = storage.register(lease_path, kind="slice", successful_date="2026-09-01")
    job_id = storage.register(job_path, kind="slice", successful_date="2026-09-01")
    storage.acquire_lease(lease_id="lease-1", object_ids=[lease_id], owner="reader", ttl_seconds=300)
    with duckdb.connect(str(db)) as con:
        con.execute("INSERT INTO jobs VALUES (?, ?, ?, ?)", ["job-1", "job-key", "RUNNING", json.dumps({"job_kind": "HISTORY_ANALYSIS", "pending_storage_object_ids": [job_id]})])
    plan = storage.preview_cleanup(as_of=date(2026, 9, 8))
    protected = {entry["object"]["storage_object_id"]: entry["reason"] for entry in plan["protected"]}
    assert protected[lease_id] == "ACTIVE_LEASE"
    assert protected[job_id] == "ACTIVE_JOB_REFERENCE"
    storage.release_lease(lease_id="lease-1", owner="reader")
    with duckdb.connect(str(db)) as con:
        con.execute("UPDATE jobs SET status='SUCCESS'")
    plan = storage.preview_cleanup(as_of=date(2026, 9, 8))
    assert {item["storage_object_id"] for item in plan["eligible"]} == {lease_id, job_id}
