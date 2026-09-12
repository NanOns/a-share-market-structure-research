import hashlib
import json
from pathlib import Path

import duckdb

from workbench_ops import BackupService


def _service(tmp_path):
    (tmp_path / "config").mkdir()
    (tmp_path / "config/paths.yaml").write_text('tdx:\n  root: "D:/new_tdx"\n', encoding="utf-8")
    database = tmp_path / "data/database/market_research.duckdb"
    database.parent.mkdir(parents=True)
    with duckdb.connect(str(database)) as connection:
        connection.execute("CREATE TABLE config_versions (config_revision VARCHAR PRIMARY KEY, payload_json JSON NOT NULL)")
        connection.execute("CREATE TABLE backup_catalog (backup_id VARCHAR PRIMARY KEY, payload_json JSON NOT NULL)")
    return BackupService(tmp_path, database), database


def _sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def test_audit_reconciles_database_manifest_and_objects_without_writing_catalog(tmp_path):
    service, database = _service(tmp_path)
    root = tmp_path / "data/backups"
    root.mkdir(parents=True)
    backup_id = "backup-good"
    database_file = root / (backup_id + ".duckdb")
    database_file.write_bytes(b"database")
    object_root = root / (backup_id + ".objects")
    object_file = object_root / "data/analysis_objects/item.parquet"
    object_file.parent.mkdir(parents=True)
    object_file.write_bytes(b"object")
    manifest = {
        "contract_version": "history-backup-manifest-v1.0",
        "backup_id": backup_id,
        "database": {"path": str(database_file), "sha256": _sha(database_file)},
        "objects_root": str(object_root),
        "objects": [{"storage_object_id": "item", "relative_path": "data/analysis_objects/item.parquet", "sha256": _sha(object_file), "size_bytes": object_file.stat().st_size}],
    }
    manifest["manifest_sha256"] = hashlib.sha256(_canonical(manifest).encode()).hexdigest()
    manifest_file = root / (backup_id + ".manifest.json")
    manifest_file.write_text(_canonical(manifest), encoding="utf-8")
    record = {"backup_id": backup_id, "path": str(database_file), "sha256": _sha(database_file), "manifest_path": str(manifest_file), "objects_root": str(object_root), "state": "VERIFIED"}
    orphan = root / "backup-orphan.duckdb"
    orphan.write_bytes(b"orphan")
    with duckdb.connect(str(database)) as connection:
        connection.execute("INSERT INTO backup_catalog VALUES (?, ?)", [backup_id, _canonical(record)])

    result = service.audit_catalog_physical_chain()

    assert result["chain_pass_count"] == 1
    assert result["chain_incomplete_count"] == 0
    assert result["orphan_physical_database_files"] == [orphan.name]
    with duckdb.connect(str(database), read_only=True) as connection:
        assert connection.execute("SELECT count(*) FROM backup_catalog").fetchone()[0] == 1


def test_audit_marks_missing_database_and_keeps_orphan_objects_visible(tmp_path):
    service, database = _service(tmp_path)
    root = tmp_path / "data/backups"
    root.mkdir(parents=True)
    backup_id = "backup-incomplete"
    object_root = root / (backup_id + ".objects")
    object_root.mkdir()
    record = {"backup_id": backup_id, "path": str(root / (backup_id + ".duckdb")), "sha256": "a" * 64, "manifest_path": str(root / (backup_id + ".manifest.json")), "objects_root": str(object_root), "state": "VERIFIED"}
    with duckdb.connect(str(database)) as connection:
        connection.execute("INSERT INTO backup_catalog VALUES (?, ?)", [backup_id, _canonical(record)])

    result = service.audit_catalog_physical_chain()

    assert result["chain_pass_count"] == 0
    assert result["chain_incomplete_count"] == 1
    assert result["records"][0]["database_status"] == "MISSING"
    assert result["records"][0]["manifest_status"] == "MISSING"
