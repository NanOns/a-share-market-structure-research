from datetime import datetime
from pathlib import Path

import duckdb
import pandas as pd

from workbench_analysis.hierarchy import (
    CONTRACT_VERSION,
    HierarchyMembershipResolver,
    build_hierarchy_nodes,
    ensure_hierarchy,
    hierarchy_semantic_digest,
)
from workbench_db.migrations import BASE_SCHEMA_VERSION, MigrationExecutor


ROOT = Path(__file__).parents[2]


def _connection(tmp_path):
    connection = duckdb.connect(str(tmp_path / "hierarchy.duckdb"))
    connection.execute((ROOT / "src/workbench_db/schema.sql").read_text(encoding="utf-8"))
    connection.execute("INSERT INTO schema_migrations VALUES (?, current_timestamp)", [BASE_SCHEMA_VERSION])
    MigrationExecutor(connection).apply()
    return connection


def _memberships(*, names=None):
    names = names or {}
    return pd.DataFrame(
        [
            {"sector_type": "INDUSTRY", "sector_id": "INDUSTRY:P", "sector_code": "P", "sector_name": names.get("P", "父")},
            {"sector_type": "INDUSTRY", "sector_id": "INDUSTRY:P01", "sector_code": "P01", "sector_name": names.get("P01", "叶一")},
            {"sector_type": "INDUSTRY", "sector_id": "INDUSTRY:P02", "sector_code": "P02", "sector_name": names.get("P02", "叶二")},
            {"sector_type": "THEME", "sector_id": "THEME:X", "sector_code": "X", "sector_name": names.get("X", "概念")},
        ]
    )


def _insert_tree(connection, version="tree-v3"):
    connection.execute(
        "INSERT INTO tdx_sector_hierarchy_versions VALUES (?, ?, ?, ?, ?, ?, ?)",
        [version, CONTRACT_VERSION, "tree-source", "{}", "tree-source-digest", datetime(2026, 9, 10), datetime(2026, 9, 10)],
    )
    rows = [
        (version, "INDUSTRY", "INDUSTRY:P", "P", "父", None, None, "ROOT", "TEST", "tree-source", "tree-source-digest", CONTRACT_VERSION),
        (version, "INDUSTRY", "INDUSTRY:P01", "P01", "叶一", "INDUSTRY:P", "父", "LEAF", "TEST", "tree-source", "tree-source-digest", CONTRACT_VERSION),
        (version, "INDUSTRY", "INDUSTRY:P02", "P02", "叶二", "INDUSTRY:P", "父", "LEAF", "TEST", "tree-source", "tree-source-digest", CONTRACT_VERSION),
        (version, "THEME", "THEME:X", "X", "概念", None, None, "FLAT", "TEST", "tree-source", "tree-source-digest", CONTRACT_VERSION),
    ]
    connection.executemany("INSERT INTO tdx_sector_hierarchy_nodes VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", rows)
    return version


def test_semantic_version_ignores_observation_identity_and_names():
    first_version, first_nodes, first_source_digest = build_hierarchy_nodes(
        _memberships(), source_hashes={"tdxhy.cfg": "hash-a"}, source_path="source-a/tdxhy.cfg"
    )
    second_version, second_nodes, second_source_digest = build_hierarchy_nodes(
        _memberships(names={"P": "改名父", "P01": "改名叶一"}),
        source_hashes={"tdxhy.cfg": "hash-b"},
        source_path="source-b/tdxhy.cfg",
    )

    assert first_version == second_version
    assert first_source_digest != second_source_digest
    assert first_nodes[["sector_type", "sector_id", "parent_sector_id", "hierarchy_level_code", "relation_basis"]].to_dict("records") == second_nodes[["sector_type", "sector_id", "parent_sector_id", "hierarchy_level_code", "relation_basis"]].to_dict("records")
    assert hierarchy_semantic_digest(first_nodes.to_dict("records")) == hierarchy_semantic_digest(second_nodes.to_dict("records"))
    assert hierarchy_semantic_digest(first_nodes.to_dict("records"), "CONTRACT_OTHER") != hierarchy_semantic_digest(first_nodes.to_dict("records"), CONTRACT_VERSION)


def test_ensure_hierarchy_reuses_semantic_tree_when_source_observation_changes(tmp_path):
    connection = _connection(tmp_path)
    try:
        first = ensure_hierarchy(
            connection,
            _memberships(),
            source_hashes={"tdxhy.cfg": "hash-a"},
            source_path="source-a/tdxhy.cfg",
            now=datetime(2026, 9, 10),
        )
        second = ensure_hierarchy(
            connection,
            _memberships(names={"P": "改名父"}),
            source_hashes={"tdxhy.cfg": "hash-b"},
            source_path="source-b/tdxhy.cfg",
            now=datetime(2026, 9, 11),
        )

        assert first[0] == second[0]
        assert first[1] != second[1]
        assert first[2] == second[2] == 4
        assert connection.execute("SELECT count(*) FROM tdx_sector_hierarchy_versions").fetchone()[0] == 1
        assert connection.execute("SELECT count(*) FROM tdx_sector_hierarchy_nodes").fetchone()[0] == 4
    finally:
        connection.close()


def test_parent_members_union_direct_and_derived_without_duplicates(tmp_path):
    connection = _connection(tmp_path)
    try:
        version = _insert_tree(connection)
        scope = "TDX-MEMBERSHIP:direct-members-v3-v1"
        connection.executemany(
            "INSERT INTO relation_edge_intervals VALUES (?, ?, ?, ?, NULL, ?)",
            [
                (scope, "INDUSTRY:P01", "SZ.000001", 1, "DIRECT"),
                (scope, "INDUSTRY:P01", "SZ.SHARED", 1, "DIRECT"),
                (scope, "INDUSTRY:P02", "SZ.SHARED", 1, "DIRECT"),
                (scope, "INDUSTRY:P02", "SZ.000002", 1, "DIRECT"),
                (scope, "INDUSTRY:P", "SZ.SHARED", 1, "DIRECT"),
                (scope, "INDUSTRY:P", "SZ.000003", 1, "DIRECT"),
                (scope, "INDUSTRY:P", "SZ.000004", 1, "LEGACY_EXPLICIT"),
            ],
        )

        resolver = HierarchyMembershipResolver(connection)
        members = resolver.parent_members(scope, 1, version, "INDUSTRY:P")
        assert [(item.security_id, item.source_kinds) for item in members] == [
            ("SZ.000001", ("DERIVED",)),
            ("SZ.000002", ("DERIVED",)),
            ("SZ.000003", ("DIRECT",)),
            ("SZ.000004", ("LEGACY_EXPLICIT",)),
            ("SZ.SHARED", ("DERIVED", "DIRECT")),
        ]
        assert len({item.security_id for item in members}) == 5
        assert resolver.parent_members(scope, 1, version, "THEME:X") == ()
        assert resolver.parent_members(scope, 1, version, "INDUSTRY:P", display_security_ids={"sz.shared"})[0].security_id == "SZ.SHARED"
        assert len(resolver._cache) == 1
        assert resolver.cache_key(scope, 1, version) == (scope, 1, version, "hierarchy-parent-members-v3-v1", "ALL")
        assert resolver.cache_key(scope, 1, version, display_universe_version="DISPLAY_V2")[-1] == "DISPLAY_V2"
        resolver.parent_members(scope, 1, version, "INDUSTRY:P", display_universe_version="DISPLAY_V2")
        assert len(resolver._cache) == 2
    finally:
        connection.close()


def test_parent_members_cache_is_namespaced_by_source_scope(tmp_path):
    connection = _connection(tmp_path)
    try:
        version = _insert_tree(connection)
        scope_a = "SOURCE-A:direct-members-v3-v1"
        scope_b = "SOURCE-B:direct-members-v3-v1"
        connection.executemany(
            "INSERT INTO relation_edge_intervals VALUES (?, ?, ?, ?, NULL, ?)",
            [
                (scope_a, "INDUSTRY:P01", "SZ.A", 1, "DIRECT"),
                (scope_b, "INDUSTRY:P01", "SZ.B", 1, "DIRECT"),
            ],
        )
        resolver = HierarchyMembershipResolver(connection)
        assert [item.security_id for item in resolver.parent_members(scope_a, 1, version, "INDUSTRY:P")] == ["SZ.A"]
        assert [item.security_id for item in resolver.parent_members(scope_b, 1, version, "INDUSTRY:P")] == ["SZ.B"]
        assert len(resolver._cache) == 2
    finally:
        connection.close()
