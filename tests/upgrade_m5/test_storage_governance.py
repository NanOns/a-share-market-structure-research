from datetime import date, datetime, timedelta, timezone

import duckdb
import pytest

from workbench_ops import ConfigValidationError, StorageGovernance


def service(tmp_path):
    (tmp_path / "config").mkdir()
    (tmp_path / "config/paths.yaml").write_text('tdx:\n  root: "D:/new_tdx"\n', encoding="utf-8")
    db=tmp_path/"data/database/market_research.duckdb";db.parent.mkdir(parents=True)
    with duckdb.connect(str(db)) as con:
        con.execute("CREATE TABLE config_versions (config_revision VARCHAR PRIMARY KEY, payload_json JSON NOT NULL)")
        con.execute("CREATE TABLE storage_objects (storage_object_id VARCHAR PRIMARY KEY, payload_json JSON NOT NULL)")
        con.execute("CREATE TABLE cleanup_jobs (cleanup_job_id VARCHAR PRIMARY KEY, payload_json JSON NOT NULL)")
    return StorageGovernance(tmp_path,db)


def test_cleanup_preview_only_selects_old_unreferenced_unleased_objects(tmp_path):
    ops=service(tmp_path)
    old=tmp_path/"reports/old";old.mkdir(parents=True)
    fresh=tmp_path/"reports/fresh";fresh.mkdir()
    referenced=tmp_path/"reports/referenced";referenced.mkdir()
    leased=tmp_path/"reports/leased";leased.mkdir()
    ops.register(old,kind="cache",successful_date="2026-09-01")
    ops.register(fresh,kind="cache",successful_date="2026-09-07")
    ops.register(referenced,kind="cache",successful_date="2026-09-01",referenced=True)
    ops.register(leased,kind="cache",successful_date="2026-09-01",lease_until_utc=(datetime.now(timezone.utc)+timedelta(days=1)).isoformat())
    plan=ops.preview_cleanup(as_of=date(2026,9,8))
    assert len(plan["eligible"]) == 1 and plan["eligible"][0]["path"] == str(old.resolve())
    assert old.is_dir()  # preview cannot delete
    assert {x["reason"] for x in plan["protected"]} == {"RETENTION_WINDOW","DATABASE_REFERENCED","ACTIVE_LEASE"}


def test_quarantine_can_be_restored_or_confirmed_deleted(tmp_path):
    ops=service(tmp_path);item=tmp_path/"reports/old";item.mkdir(parents=True);(item/"x.txt").write_text("x")
    ops.register(item,kind="cache",successful_date="2026-09-01")
    plan=ops.preview_cleanup(as_of=date(2026,9,8));job=plan["cleanup_job_id"]
    assert ops.quarantine(job)["state"] == "QUARANTINED" and not item.exists()
    assert ops.restore_quarantine(job)["state"] == "RESTORED" and (item/"x.txt").is_file()
    plan=ops.preview_cleanup(as_of=date(2026,9,8));job=plan["cleanup_job_id"]
    ops.quarantine(job)
    assert ops.delete_quarantine(job)["state"] == "DELETED" and not item.exists()


def test_database_and_wal_are_never_cleanup_candidates(tmp_path):
    ops=service(tmp_path)
    with pytest.raises(ConfigValidationError,match="STORAGE_PATH_PROTECTED"):
        ops.register(ops.database_path,kind="database",successful_date="2020-01-01")
    with duckdb.connect(str(ops.database_path)) as con:
        con.execute("INSERT INTO storage_objects VALUES ('db', ?)", ['{"storage_object_id":"db","path":"'+str(ops.database_path).replace('\\','/')+'","kind":"database","successful_date":"2020-01-01","state":"ACTIVE"}'])
    plan=ops.preview_cleanup(as_of=date(2026,9,8))
    assert not plan["eligible"] and plan["protected"]
