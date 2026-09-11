from datetime import date
from pathlib import Path

import duckdb
import pytest

from workbench_db.migrations import BASE_SCHEMA_VERSION, MigrationExecutor
from workbench_service.relation_repository import (
    RelationInputError,
    RelationRepository,
    attribute_content_hash,
    diff_relation_edges,
    edge_content_hash,
    make_source_scope,
    normalize_edges,
)


ROOT = Path(__file__).parents[2]


def _connection(tmp_path):
    connection = duckdb.connect(str(tmp_path / "relation.duckdb"))
    connection.execute((ROOT / "src/workbench_db/schema.sql").read_text(encoding="utf-8"))
    connection.execute("INSERT INTO schema_migrations VALUES (?, current_timestamp)", [BASE_SCHEMA_VERSION])
    MigrationExecutor(connection).apply()
    return connection


def _edges(sector_ids, *, source_kind="DIRECT"):
    return [{"sector_id": sector_id, "security_id": f"SZ.{index:06d}", "source_kind": source_kind} for index, sector_id in enumerate(sector_ids, 1)]


def test_hashes_ignore_observation_date_and_name_but_attribute_hash_changes_on_name():
    scope = make_source_scope("TDX", "direct-members-v3-v1")
    edges = normalize_edges(_edges(["THEME:1", "THEME:2"]), scope)
    assert edge_content_hash(scope, edges) == edge_content_hash(scope, tuple(reversed(edges)))
    assert attribute_content_hash(scope, [{"sector_id": "THEME:1", "name": "A", "type": "THEME"}]) != attribute_content_hash(scope, [{"sector_id": "THEME:1", "name": "B", "type": "THEME"}])
    with pytest.raises(RelationInputError, match="NOT_STABLE"):
        make_source_scope("TDX-2026-09-10", "direct-members-v3-v1")


def test_diff_reports_add_remove_and_source_kind_change():
    scope = make_source_scope("TDX")
    previous = normalize_edges([
        {"sector_id": "S1", "security_id": "SZ.000001", "source_kind": "DIRECT"},
        {"sector_id": "S1", "security_id": "SZ.000002", "source_kind": "DIRECT"},
    ], scope)
    current = normalize_edges([
        {"sector_id": "S1", "security_id": "SZ.000001", "source_kind": "EXPLICIT"},
        {"sector_id": "S1", "security_id": "SZ.000003", "source_kind": "DIRECT"},
    ], scope)
    diff = diff_relation_edges(previous, current)
    assert len(diff.added) == 2
    assert len(diff.removed) == 2
    assert not diff.unchanged


def test_repository_writes_only_changed_intervals_and_resolves_old_revisions(tmp_path):
    connection = _connection(tmp_path)
    try:
        scope = make_source_scope("TDX")
        repository = RelationRepository(connection)
        first = repository.record_observation(
            source_scope=scope,
            edges=_edges(["S1", "S2", "S3"]),
            attributes=[{"sector_id": "S1", "name": "板块1", "type": "INDUSTRY"}],
            source_effective_date=date(2026, 9, 8),
            source_file_hashes={"membership": "a"},
        )
        unchanged = repository.record_observation(
            source_scope=scope,
            edges=_edges(["S1", "S2", "S3"]),
            attributes=[{"sector_id": "S1", "name": "板块1", "type": "INDUSTRY"}],
            source_effective_date=date(2026, 9, 9),
            source_file_hashes={"membership": "b"},
        )
        updated = repository.record_observation(
            source_scope=scope,
            edges=[
                {"sector_id": "S1", "security_id": "SZ.000001", "source_kind": "DIRECT"},
                {"sector_id": "S4", "security_id": "SZ.000004", "source_kind": "DIRECT"},
                {"sector_id": "S5", "security_id": "SZ.000005", "source_kind": "DIRECT"},
                {"sector_id": "S6", "security_id": "SZ.000006", "source_kind": "DIRECT"},
            ],
            attributes=[{"sector_id": "S1", "name": "板块一", "type": "INDUSTRY"}],
            source_effective_date=date(2026, 9, 10),
            source_file_hashes={"membership": "c"},
        )
        assert first["status"] == "UPDATED"
        assert unchanged["status"] == "UNCHANGED"
        assert updated["status"] == "UPDATED"
        assert updated["diff"]["added"] and updated["diff"]["removed"]
        assert [edge.security_id for edge in repository.resolver.edges_at(scope, 1)] == ["SZ.000001", "SZ.000002", "SZ.000003"]
        assert [edge.security_id for edge in repository.resolver.edges_at(scope, 2)] == ["SZ.000001", "SZ.000004", "SZ.000005", "SZ.000006"]
        assert connection.execute("SELECT count(*) FROM relation_revisions WHERE source_scope=?", [scope]).fetchone()[0] == 2
        assert connection.execute("SELECT count(*) FROM relation_observations WHERE source_scope=?", [scope]).fetchone()[0] == 3
        assert connection.execute("SELECT count(*) FROM relation_edge_intervals WHERE source_scope=?", [scope]).fetchone()[0] == 6
    finally:
        connection.close()


def test_invalid_empty_or_incomplete_source_does_not_close_existing_edges(tmp_path):
    connection = _connection(tmp_path)
    try:
        scope = make_source_scope("TDX")
        repository = RelationRepository(connection)
        repository.record_observation(source_scope=scope, edges=_edges(["S1", "S2"]), source_file_hashes={"membership": "a"})
        invalid_empty = repository.record_observation(source_scope=scope, edges=[], source_file_hashes={"membership": "empty"})
        invalid_incomplete = repository.record_observation(source_scope=scope, edges=_edges(["S3"]), source_complete=False, source_file_hashes={"membership": "partial"})
        assert invalid_empty["status"] == "INVALID"
        assert invalid_incomplete["status"] == "INVALID"
        assert repository.current_revision(scope) == 1
        assert [edge.security_id for edge in repository.resolver.edges_at(scope, 1)] == ["SZ.000001", "SZ.000002"]
        assert connection.execute("SELECT count(*) FROM relation_observations WHERE quality='INVALID'").fetchone()[0] == 2
    finally:
        connection.close()
