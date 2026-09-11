"""Read-only resolver facade for the V3 relation interval store."""

from __future__ import annotations

from typing import Any

import duckdb

from .relation_repository import MembershipResolver, RelationEdge


class VersionedMembershipResolver(MembershipResolver):
    """Resolve a legacy snapshot or publication through its relation binding."""

    def __init__(self, connection: duckdb.DuckDBPyConnection):
        super().__init__(connection)

    def edges_for_snapshot(self, legacy_membership_snapshot_id: str) -> tuple[RelationEdge, ...]:
        row = self.connection.execute(
            """
            SELECT o.source_scope, b.revision_no
            FROM relation_snapshot_bindings b
            JOIN relation_observations o ON o.observation_id=b.observation_id
            WHERE b.legacy_membership_snapshot_id=?
            """,
            [legacy_membership_snapshot_id],
        ).fetchone()
        if not row:
            raise KeyError(f"RELATION_SNAPSHOT_BINDING_NOT_FOUND:{legacy_membership_snapshot_id}")
        return self.edges_at(row[0], int(row[1]))

    def edges_for_publication(self, publication_id: str, source_scope: str) -> tuple[RelationEdge, ...]:
        row = self.connection.execute(
            "SELECT revision_no FROM relation_publication_bindings WHERE publication_id=? AND source_scope=?",
            [publication_id, source_scope],
        ).fetchone()
        if not row:
            raise KeyError(f"RELATION_PUBLICATION_BINDING_NOT_FOUND:{publication_id}:{source_scope}")
        return self.edges_at(source_scope, int(row[0]))

    def member_ids_for_sector(self, source_scope: str, revision_no: int, sector_id: str) -> tuple[str, ...]:
        return self.members_by_sector(source_scope, revision_no).get(str(sector_id), ())
