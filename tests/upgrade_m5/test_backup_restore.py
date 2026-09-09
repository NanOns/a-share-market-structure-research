from pathlib import Path

import duckdb
import pytest

from workbench_ops import BackupService, ConfigValidationError


def service(tmp_path):
    (tmp_path/"config").mkdir();(tmp_path/"config/paths.yaml").write_text('tdx:\n  root: "D:/new_tdx"\n',encoding="utf-8")
    db=tmp_path/"data/database/market_research.duckdb";db.parent.mkdir(parents=True)
    with duckdb.connect(str(db)) as c:
        c.execute("CREATE TABLE config_versions (config_revision VARCHAR PRIMARY KEY, payload_json JSON NOT NULL)")
        c.execute("CREATE TABLE backup_catalog (backup_id VARCHAR PRIMARY KEY, payload_json JSON NOT NULL)")
        for table in ("publication_heads","queue_memberships","membership_entries","outcomes"): c.execute(f"CREATE TABLE {table} (id INTEGER)")
        c.execute("INSERT INTO publication_heads VALUES (1)");c.execute("INSERT INTO queue_memberships VALUES (1)");c.execute("INSERT INTO membership_entries VALUES (1)");c.execute("INSERT INTO outcomes VALUES (1)")
    return BackupService(tmp_path,db)


def test_backup_requires_maintenance_window(tmp_path):
    with pytest.raises(ConfigValidationError,match="BACKUP_REQUIRES_DRAINED"):
        service(tmp_path).create_offline_backup(maintenance_window=False)


def test_verified_backup_and_restore_drill(tmp_path):
    ops=service(tmp_path);backup=ops.create_offline_backup(maintenance_window=True)
    assert Path(backup["path"]).is_file() and backup["verification"]["publication_heads"] == 1
    drill=ops.restore_drill(backup["backup_id"],drill_root=tmp_path/"runtime/drills")
    assert drill["status"] == "PASS" and Path(drill["restore_drill_path"]).is_file()
