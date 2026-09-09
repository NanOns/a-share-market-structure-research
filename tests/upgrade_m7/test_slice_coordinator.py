from datetime import date
from pathlib import Path

import duckdb
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from workbench_db.migrations import BASE_SCHEMA_VERSION, MigrationExecutor
from workbench_service.slice_coordinator import SliceCoordinationError, SliceCoordinator, iter_security_batches


ROOT = Path(__file__).parents[2]


def _database(tmp_path):
    path = tmp_path / "slice.duckdb"
    con = duckdb.connect(str(path))
    con.execute((ROOT / "src/workbench_db/schema.sql").read_text(encoding="utf-8"))
    con.execute("insert into schema_migrations values (?, current_timestamp)", [BASE_SCHEMA_VERSION])
    MigrationExecutor(con).apply()
    con.close()
    return path


def _basis():
    return {
        "source_manifest_sha256": "a" * 64,
        "source_bundle_id": "bundle-1",
        "daily_basis": {
            "universe_basis": "CURRENT_SNAPSHOT_ONLY",
            "membership_snapshot_id": None,
            "price_basis": "FORWARD_ADJUSTED",
            "adjustment_as_of": "2026-09-07",
            "source_observed_at": "2026-09-07T08:00:00+00:00",
            "coverage": 1.0,
            "capabilities_json": {"quote_input": "OBSERVED"},
        },
    }


def test_same_content_is_reused_and_sealed_once(tmp_path):
    database = _database(tmp_path)
    coordinator = SliceCoordinator(tmp_path, database)
    rows = [{"security_id": "SH.600000", "date": "2026-09-07", "close": 10.2}, {"security_id": "SH.600000", "date": "2026-09-06", "close": 10.1}]
    first = coordinator.coordinate(domain="quote_input", trade_date="2026-09-07", contract_id="quote-v1", rows=rows, basis=_basis())
    second = coordinator.coordinate(domain="quote_input", trade_date="2026-09-07", contract_id="quote-v1", rows=list(reversed(rows)), basis=_basis())
    assert first["reused"] is False
    assert second["reused"] is True
    with duckdb.connect(str(database), read_only=True) as con:
        assert con.execute("select count(*) from analysis_slices").fetchone()[0] == 1
        assert con.execute("select count(*) from storage_objects").fetchone()[0] == 1
        assert con.execute("select count(*) from analysis_daily_basis").fetchone()[0] == 1


def test_dependency_hash_changes_slice_and_missing_dependency_fails_closed(tmp_path):
    database = _database(tmp_path)
    coordinator = SliceCoordinator(tmp_path, database)
    basis = _basis()
    upstream = coordinator.coordinate(domain="raw", trade_date="2026-09-07", contract_id="raw-v1", rows=[{"security_id": "SH.600000", "date": "2026-09-07", "close": 10.2}], basis=basis)
    dependent = coordinator.coordinate(domain="technical", trade_date="2026-09-07", contract_id="technical-v1", rows=[{"security_id": "SH.600000", "date": "2026-09-07", "ma5": 10.0}], dependencies=[{"input_domain": "raw", "input_date": "2026-09-07", "input_slice_id": upstream["slice_id"]}], basis=basis)
    assert dependent["slice_id"] != upstream["slice_id"]
    with pytest.raises(SliceCoordinationError, match="SLICE_DEPENDENCY_NOT_FOUND"):
        coordinator.coordinate(domain="technical", trade_date="2026-09-07", contract_id="technical-v1", rows=[{"security_id": "SH.600000", "date": "2026-09-07", "ma5": 10.0}], dependencies=[{"input_domain": "raw", "input_date": "2026-09-07", "input_slice_id": "slice-missing"}], basis=basis)


def test_security_batch_reader_filters_date_and_security(tmp_path):
    path = tmp_path / "input.parquet"
    table = pa.table({"security_id": ["SH.1", "SH.1", "SH.2"], "date": [date(2026, 9, 7), date(2026, 9, 6), date(2026, 9, 7)], "close": [1.0, 0.9, 2.0]})
    pq.write_table(table, path)
    batches = list(iter_security_batches(path, trade_date="2026-09-07", security_ids=["SH.1", "SH.2"], batch_size=1))
    assert [(item["security_id"], len(item["rows"])) for item in batches] == [("SH.1", 1), ("SH.2", 1)]
