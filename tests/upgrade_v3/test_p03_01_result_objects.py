from pathlib import Path

import duckdb

from workbench_db.migrations import BASE_SCHEMA_VERSION, MigrationExecutor
from workbench_service.result_objects import ResultObjectCoordinator, read_result_rows


ROOT = Path(__file__).parents[2]


def _database(tmp_path):
    database = tmp_path / "result-objects.duckdb"
    connection = duckdb.connect(str(database))
    connection.execute((ROOT / "src/workbench_db/schema.sql").read_text(encoding="utf-8"))
    connection.execute("INSERT INTO schema_migrations VALUES (?, current_timestamp)", [BASE_SCHEMA_VERSION])
    receipt = MigrationExecutor(connection).apply()
    assert receipt["status"] == "APPLIED"
    connection.close()
    return database


def _rows():
    return [
        {"security_id": "SH.600001", "trade_date": "2026-09-10", "value": 1.2, "quality_codes": "[]"},
        {"security_id": "SZ.000001", "trade_date": "2026-09-10", "value": None, "quality_codes": "[\"MISSING\"]"},
    ]


def _coordinate(coordinator, *, basis, rows=None, value_semantics=None, domain="technical"):
    return coordinator.coordinate(
        domain=domain,
        trade_date="2026-09-10",
        contract_id="technical-v3",
        schema_version="technical-result-schema-v1",
        semantic_contract="TECHNICAL_RESULT_V3",
        rows=rows or _rows(),
        primary_key=("security_id", "trade_date"),
        value_semantics=value_semantics or {"null_policy": "EXPLICIT", "amount_unit": "YUAN"},
        basis=basis,
    )


def test_same_value_different_slice_identity_shares_one_verified_object(tmp_path):
    database = _database(tmp_path)
    coordinator = ResultObjectCoordinator(tmp_path, database)
    first = _coordinate(coordinator, basis={"source_manifest_sha256": "a" * 64, "source_bundle_id": "bundle-a"})
    second = _coordinate(coordinator, basis={"source_manifest_sha256": "b" * 64, "source_bundle_id": "bundle-b"})
    retry = _coordinate(coordinator, basis={"source_manifest_sha256": "a" * 64, "source_bundle_id": "bundle-a"})

    assert first["reused"] is False
    assert second["reused"] is False
    assert retry["reused"] is True
    assert first["slice_id"] != second["slice_id"]
    assert first["result_object_id"] == second["result_object_id"]
    with duckdb.connect(str(database), read_only=True) as connection:
        assert connection.execute("SELECT count(*) FROM analysis_slices").fetchone()[0] == 2
        assert connection.execute("SELECT count(*) FROM analysis_result_objects").fetchone()[0] == 1
        assert connection.execute("SELECT count(*) FROM analysis_slice_result_bindings").fetchone()[0] == 2
        assert connection.execute("SELECT count(*) FROM storage_objects").fetchone()[0] == 1
        assert read_result_rows(connection, tmp_path, first["slice_id"]) == read_result_rows(connection, tmp_path, second["slice_id"])


def test_quality_or_semantic_contract_change_does_not_share_object(tmp_path):
    database = _database(tmp_path)
    coordinator = ResultObjectCoordinator(tmp_path, database)
    first = _coordinate(coordinator, basis={"source_manifest_sha256": "a" * 64}, value_semantics={"null_policy": "EXPLICIT"})
    second = _coordinate(coordinator, basis={"source_manifest_sha256": "b" * 64}, value_semantics={"null_policy": "IMPLICIT"})
    third = _coordinate(coordinator, basis={"source_manifest_sha256": "c" * 64}, rows=[* _rows(), {"security_id": "SH.000002", "trade_date": "2026-09-10", "value": 2.0, "quality_codes": "[]"}])

    assert len({first["result_object_id"], second["result_object_id"], third["result_object_id"]}) == 3
    with duckdb.connect(str(database), read_only=True) as connection:
        assert connection.execute("SELECT count(*) FROM analysis_result_objects").fetchone()[0] == 3


def test_missing_result_binding_fails_closed(tmp_path):
    database = _database(tmp_path)
    with duckdb.connect(str(database), read_only=True) as connection:
        try:
            read_result_rows(connection, tmp_path, "slice-missing")
        except ValueError as error:
            assert str(error) == "RESULT_BINDING_NOT_FOUND"
        else:
            raise AssertionError("missing result binding must fail closed")
