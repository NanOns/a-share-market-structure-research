import hashlib
import json

import duckdb

from workbench_ops import BackupService


def _canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def _service(tmp_path):
    (tmp_path / "config").mkdir()
    (tmp_path / "config/paths.yaml").write_text('tdx:\n  root: "D:/new_tdx"\n', encoding="utf-8")
    database = tmp_path / "data/database/market_research.duckdb"
    database.parent.mkdir(parents=True)
    with duckdb.connect(str(database)) as connection:
        connection.execute("CREATE TABLE config_versions (config_revision VARCHAR PRIMARY KEY, payload_json JSON NOT NULL)")
        connection.execute("CREATE TABLE backup_catalog (backup_id VARCHAR PRIMARY KEY, payload_json JSON NOT NULL)")
        connection.execute("CREATE TABLE storage_objects (storage_object_id VARCHAR PRIMARY KEY, payload_json JSON NOT NULL)")
    return BackupService(tmp_path, database), database


def test_orphan_manifest_links_to_active_storage_object_but_stays_user_decision(tmp_path):
    service, database = _service(tmp_path)
    root = tmp_path / "data/backups"
    root.mkdir(parents=True)
    backup_id = "backup-orphan-manifest"
    object_root = root / (backup_id + ".objects")
    object_file = object_root / "data/analysis_objects/item.parquet"
    object_file.parent.mkdir(parents=True)
    object_file.write_bytes(b"object")
    object_hash = hashlib.sha256(object_file.read_bytes()).hexdigest()
    object_id = "analysis-object"
    with duckdb.connect(str(database)) as connection:
        connection.execute(
            "INSERT INTO storage_objects VALUES (?, ?)",
            [object_id, _canonical({"storage_object_id": object_id, "state": "ACTIVE", "referenced": True, "physical_sha256": object_hash, "relative_path": "data/analysis_objects/item.parquet", "size_bytes": object_file.stat().st_size, "registered_at_utc": "2026-09-09T02:29:43Z", "storage_kind": "PARQUET"})],
        )
    manifest = {
        "contract_version": "history-backup-manifest-v1.0",
        "backup_id": backup_id,
        "created_at_utc": "2026-09-09T02:57:18Z",
        "database": {"path": str(root / (backup_id + ".duckdb")), "sha256": "d" * 64},
        "objects_root": str(object_root),
        "objects": [{"storage_object_id": object_id, "relative_path": "data/analysis_objects/item.parquet", "sha256": object_hash, "size_bytes": object_file.stat().st_size}],
    }
    manifest["manifest_sha256"] = hashlib.sha256(_canonical(manifest).encode()).hexdigest()
    (root / (backup_id + ".manifest.json")).write_text(_canonical(manifest), encoding="utf-8")

    result = service.audit_orphan_provenance({
        "contract_version": "v3-p04-03-backup-chain-audit-v1.0",
        "orphan_physical_database_files": [],
        "orphan_physical_manifest_files": [backup_id + ".manifest.json"],
        "orphan_physical_object_dirs": [backup_id + ".objects"],
    })

    item = result["items"][0]
    assert item["provenance_class"] == "UNREGISTERED_MANIFEST_WITH_REGISTERED_OBJECT_EVIDENCE"
    assert item["manifest_status"] == "PASS"
    assert item["object_results"][0]["hash_status"] == "PASS"
    assert item["object_results"][0]["storage_object_match"]["state"] == "ACTIVE"
    assert item["retention"]["recommendation"] == "RETAIN_UNTIL_OWNER_CONFIRMED"
    assert item["retention"]["deletion_allowed"] is False
    with duckdb.connect(str(database), read_only=True) as connection:
        assert connection.execute("SELECT count(*) FROM backup_catalog").fetchone()[0] == 0


def test_orphan_database_self_hash_is_evidence_not_catalog_ownership(tmp_path):
    service, database = _service(tmp_path)
    root = tmp_path / "data/backups"
    root.mkdir(parents=True)
    payload = b"orphan database evidence"
    digest = hashlib.sha256(payload).hexdigest()
    name = "backup-20260910T122818Z-" + digest[:12] + ".duckdb"
    (root / name).write_bytes(payload)

    result = service.audit_orphan_provenance({
        "contract_version": "v3-p04-03-backup-chain-audit-v1.0",
        "orphan_physical_database_files": [name],
        "orphan_physical_manifest_files": [],
        "orphan_physical_object_dirs": [],
    })

    item = result["items"][0]
    assert item["provenance_class"] == "UNOWNED_PHYSICAL_DATABASE"
    assert item["provenance_status"] == "SELF_HASH_CONSISTENT_BUT_NOT_CATALOGED"
    assert item["filename_sha256_prefix_matches"] is True
    assert item["catalog_backup_ids_by_sha256"] == []
    assert result["retention_policy"]["fixed_retention_required"] is True
    assert result["retention_policy"]["deletion_allowed"] is False
