import json
from pathlib import Path

import pytest

from workbench_db.owner import DatabaseOwner, DatabaseOwnerBusy
from workbench_db.repository import WorkbenchRepository


def test_single_owner_blocks_second_handle(tmp_path):
    first = DatabaseOwner(tmp_path / "test.duckdb").acquire()
    try:
        with pytest.raises(DatabaseOwnerBusy):
            DatabaseOwner(tmp_path / "test.duckdb").acquire()
    finally:
        first.release()


def test_schema_and_repository_allowlist(tmp_path):
    with WorkbenchRepository(tmp_path, tmp_path / "test.duckdb") as repository:
        assert repository.table_count("publications") == 0
        with pytest.raises(ValueError, match="TABLE_NOT_ALLOWED"):
            repository.table_count("not_a_table")
        version = repository.connection.execute("SELECT version FROM schema_migrations").fetchone()[0]
        assert version == "workbench-schema-v1.0"


def test_success_shortcut_rejects_incomplete_existing_publication(tmp_path):
    release = tmp_path / "release"
    release.mkdir()
    (release / "PRODUCTION_RECEIPT.json").write_text(
        json.dumps({"status": "SUCCESS", "run_id": "run-1", "cutoff_date": "20260907"}), encoding="utf-8"
    )
    with WorkbenchRepository(tmp_path, tmp_path / "test.duckdb") as repository:
        repository.connection.execute(
            "INSERT INTO publications VALUES (?, DATE '2026-09-07', 1, 'SUCCESS', NULL, NULL, NULL, NULL, NULL, NULL, ?, current_timestamp)",
            ["run-1", str(release)],
        )
        with pytest.raises(ValueError, match="EXISTING_PUBLICATION_ARTIFACT_MISMATCH"):
            repository.import_publication(release, revision=1)


def test_head_acceptance_query_rejects_non_success_head(tmp_path):
    with WorkbenchRepository(tmp_path, tmp_path / "test.duckdb") as repository:
        repository.connection.execute(
            "INSERT INTO publications VALUES ('run-1', DATE '2026-09-07', 1, 'IMPORTING', NULL, NULL, NULL, NULL, NULL, NULL, 'x', current_timestamp)"
        )
        repository.connection.execute("INSERT INTO publication_heads VALUES (DATE '2026-09-07', 'run-1')")
        accepted = repository.connection.execute(
            "SELECT count(*)=1 AND bool_and(p.status='SUCCESS') AND bool_and(h.trade_date=p.trade_date) "
            "FROM publication_heads h JOIN publications p USING(publication_id)"
        ).fetchone()[0]
        assert not accepted
