import json
import hashlib
from pathlib import Path

import duckdb
import pytest

from workbench_db.migrations import BASE_SCHEMA_VERSION, MigrationExecutor
from workbench_service.source_catalog import backfill_source_file_catalog, register_source_bundle_catalog


ROOT = Path(__file__).parents[2]


def test_sealed_bundle_catalog_records_metadata_files_idempotently(tmp_path):
    database = tmp_path / "catalog.duckdb"
    connection = duckdb.connect(str(database))
    connection.execute((ROOT / "src/workbench_db/schema.sql").read_text(encoding="utf-8"))
    connection.execute("INSERT INTO schema_migrations VALUES (?, current_timestamp)", [BASE_SCHEMA_VERSION])
    MigrationExecutor(connection).apply()
    package = {"sha256": "a" * 64, "byte_count": 12, "staged_path": "data/input_staging/packages/20260912/hsjday.zip"}
    metadata = {
        "metadata_snapshot_id": "meta-1",
        "files": {
            "T0002/hq_cache/tdxhy.cfg": {"size": 7, "sha256": "b" * 64},
            "T0002/hq_cache/gbbq": {"size": 5, "sha256": "c" * 64},
        },
    }
    bundle = {"source_bundle_id": "bundle-1", "target_trade_date": "2026-09-12", "metadata": metadata}

    assert register_source_bundle_catalog(connection, bundle=bundle, package=package, metadata=metadata)["source_file_count"] == 2
    register_source_bundle_catalog(connection, bundle=bundle, package=package, metadata=metadata)

    assert connection.execute("SELECT count(*) FROM source_packages").fetchone()[0] == 1
    assert connection.execute("SELECT count(*) FROM source_files").fetchone()[0] == 2
    payload = json.loads(connection.execute("SELECT payload_json FROM source_files WHERE relative_path='T0002/hq_cache/tdxhy.cfg'").fetchone()[0])
    assert payload["source_bundle_id"] == "bundle-1"
    assert connection.execute("SELECT count(*) FROM source_bundles").fetchone()[0] == 1
    connection.close()


def test_backfill_source_file_catalog_is_atomic_and_retains_shared_bundle_refs(tmp_path):
    database = tmp_path / "catalog.duckdb"
    connection = duckdb.connect(str(database))
    connection.execute((ROOT / "src/workbench_db/schema.sql").read_text(encoding="utf-8"))
    connection.execute("INSERT INTO schema_migrations VALUES (?, current_timestamp)", [BASE_SCHEMA_VERSION])
    package = {"sha256": "a" * 64, "byte_count": 12, "staged_path": "data/input_staging/packages/20260912/hsjday.zip"}
    metadata = {"metadata_snapshot_id": "meta-1", "files": {"T0002/hq_cache/tdxhy.cfg": {"size": 7, "sha256": "b" * 64}}}
    def bundle(bundle_id: str, trade_date: str) -> dict:
        return {"source_bundle_id": bundle_id, "contract": "source-bundle-v1.0", "target_trade_date": trade_date, "package": package, "metadata": metadata, "read_only": True}
    first = bundle("bundle-1", "2026-09-12")
    unsigned = dict(first); unsigned.pop("source_bundle_id")
    first["source_bundle_id"] = hashlib.sha256(json.dumps(unsigned, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    second = dict(first)
    second["target_trade_date"] = "2026-09-13"
    unsigned = dict(second); unsigned.pop("source_bundle_id")
    second["source_bundle_id"] = hashlib.sha256(json.dumps(unsigned, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    for value in (first, second):
        register_source_bundle_catalog(connection, bundle=value, package=package, metadata=metadata)
    connection.execute("DELETE FROM source_files")
    result = backfill_source_file_catalog(connection, bundles=[first, second])
    assert result["inserted_rows"] == 1
    payload = json.loads(connection.execute("SELECT payload_json FROM source_files").fetchone()[0])
    assert set(payload["source_bundle_ids"]) == {first["source_bundle_id"], second["source_bundle_id"]}
    connection.close()


def test_backfill_source_file_catalog_rolls_back_on_invalid_bundle(tmp_path):
    database = tmp_path / "catalog.duckdb"
    connection = duckdb.connect(str(database))
    connection.execute((ROOT / "src/workbench_db/schema.sql").read_text(encoding="utf-8"))
    connection.execute("INSERT INTO schema_migrations VALUES (?, current_timestamp)", [BASE_SCHEMA_VERSION])
    package = {"sha256": "a" * 64, "byte_count": 12, "staged_path": "data/input_staging/packages/20260912/hsjday.zip"}
    metadata = {"metadata_snapshot_id": "meta-1", "files": {"x": {"size": 1, "sha256": "b" * 64}}}
    valid = {"source_bundle_id": "wrong", "contract": "source-bundle-v1.0", "target_trade_date": "2026-09-12", "package": package, "metadata": metadata, "read_only": True}
    with pytest.raises(ValueError, match="SOURCE_BUNDLE_IDENTITY_INVALID"):
        backfill_source_file_catalog(connection, bundles=[valid])
    assert connection.execute("SELECT count(*) FROM source_files").fetchone()[0] == 0
    connection.close()
