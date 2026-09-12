import json
from pathlib import Path

import duckdb

from workbench_db.migrations import BASE_SCHEMA_VERSION, MigrationExecutor
from workbench_service.source_catalog import register_source_bundle_catalog


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
