import json
from datetime import date
from pathlib import Path

import duckdb

from workbench_db.migrations import BASE_SCHEMA_VERSION, MigrationExecutor
from workbench_service.legacy_relation_import import (
    LEGACY_SOURCE_SCOPE,
    LegacyRelationImporter,
    compare_all_imported_snapshots,
)
from workbench_service.membership_resolver import VersionedMembershipResolver


ROOT = Path(__file__).parents[2]


def _connection(tmp_path):
    connection = duckdb.connect(str(tmp_path / "legacy-relation.duckdb"))
    connection.execute((ROOT / "src/workbench_db/schema.sql").read_text(encoding="utf-8"))
    connection.execute("INSERT INTO schema_migrations VALUES (?, current_timestamp)", [BASE_SCHEMA_VERSION])
    MigrationExecutor(connection).apply()
    return connection


def _payload(trade_date: str, sector_id: str, security_id: str, *, source: str = "tdxhy.cfg", name: str = "行业"):
    return {
        "date": trade_date,
        "historical_backtest_safe": False,
        "membership_asof_date": trade_date,
        "membership_basis": "CURRENT_TDX_MEMBERSHIP",
        "pit_membership": False,
        "sector_code": sector_id.split(":", 1)[-1],
        "sector_id": sector_id,
        "sector_name": name,
        "sector_role": "INDUSTRY",
        "sector_type": "INDUSTRY",
        "security_id": security_id,
        "snapshot_version": "sector-membership-snapshot-v1.0",
        "source": source,
    }


def _insert_snapshot(connection, snapshot_id, trade_date, rows, publication_id):
    connection.execute(
        "INSERT INTO membership_snapshots VALUES (?, ?, ?, ?, ?)",
        [snapshot_id, trade_date, "sector-membership-snapshot-v1.0", f"logical-{snapshot_id}", len(rows)],
    )
    for row in rows:
        connection.execute(
            "INSERT INTO membership_entries VALUES (?, ?, ?, ?)",
            [snapshot_id, row["sector_id"], row["security_id"], json.dumps(row, ensure_ascii=False)],
        )
    connection.execute(
        """
        INSERT INTO publications
            (publication_id, trade_date, revision, status, source_revision_id,
             production_version, source_manifest_sha256, source_identity_sha256,
             computation_identity_sha256, render_identity_sha256, source_path,
             imported_at_utc)
        VALUES (?, ?, ?, 'SUCCESS', NULL, 'test', ?, ?, NULL, NULL, ?, ?)
        """,
        [publication_id, trade_date, 1, f"manifest-{publication_id}", f"identity-{publication_id}", "test", f"{trade_date} 23:00:00"],
    )
    connection.execute("INSERT INTO publication_memberships VALUES (?, ?)", [publication_id, snapshot_id])


def test_imports_legacy_snapshots_and_preserves_date_and_derived_basis(tmp_path):
    connection = _connection(tmp_path)
    try:
        first = [
            _payload("2026-09-08", "INDUSTRY:T0101", "SZ.000001"),
            _payload("2026-09-08", "INDUSTRY:T0102", "SZ.000002", name="另一行业"),
        ]
        second = [dict(row) for row in first]
        second[0] = dict(second[0], date="2026-09-09", membership_asof_date="2026-09-09")
        second[1] = dict(second[1], date="2026-09-09", membership_asof_date="2026-09-09")
        third = [
            *[
                dict(row, date="2026-09-10", membership_asof_date="2026-09-10")
                for row in first
            ],
            _payload("2026-09-10", "INDUSTRY:T01", "SZ.000001", source="tdxhy.cfg:DERIVED_PARENT", name="父行业"),
        ]
        _insert_snapshot(connection, "snapshot-20260908", "2026-09-08", first, "publication-20260908")
        _insert_snapshot(connection, "snapshot-20260909", "2026-09-09", second, "publication-20260909")
        _insert_snapshot(connection, "snapshot-20260910", "2026-09-10", third, "publication-20260910")

        result = LegacyRelationImporter(connection).import_snapshots()
        assert result["snapshot_count"] == 3
        assert connection.execute("SELECT count(*) FROM relation_snapshot_bindings").fetchone()[0] == 3
        assert connection.execute("SELECT count(*) FROM relation_observations").fetchone()[0] == 3
        assert connection.execute("SELECT count(*) FROM relation_revisions").fetchone()[0] == 1
        assert connection.execute("SELECT count(*) FROM relation_edge_intervals").fetchone()[0] == 2

        comparison = compare_all_imported_snapshots(connection)
        assert comparison["status"] == "PASS"
        assert all(item["payload_semantics_match"] for item in comparison["items"])
        assert {item["revision_no"] for item in comparison["items"]} == {1}
        assert comparison["items"][-1]["legacy_derived_edge_count"] == 1

        resolver = VersionedMembershipResolver(connection)
        assert resolver.edges_for_snapshot("snapshot-20260908") == resolver.edges_for_snapshot("snapshot-20260909")
        assert len(resolver.edges_for_snapshot("snapshot-20260910")) == 2
        observations = connection.execute(
            "SELECT source_effective_date FROM relation_observations ORDER BY source_effective_date"
        ).fetchall()
        assert [row[0] for row in observations] == [date(2026, 9, 8), date(2026, 9, 9), date(2026, 9, 10)]

        second_run = LegacyRelationImporter(connection).import_snapshots()
        assert {item["status"] for item in second_run["results"]} == {"EXISTING"}
        assert connection.execute("SELECT count(*) FROM relation_revisions").fetchone()[0] == 1
        assert connection.execute("SELECT count(*) FROM relation_observations").fetchone()[0] == 3
    finally:
        connection.close()
