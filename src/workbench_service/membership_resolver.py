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

    def publication_binding(self, publication_id: str, source_scope: str | None = None) -> dict[str, Any] | None:
        """Return the V3 publication binding, falling back to the legacy-ID bridge.

        New publications bind directly through ``relation_publication_bindings``.
        Historical publications are resolved through their immutable
        ``publication_memberships`` -> ``relation_snapshot_bindings`` mapping;
        this keeps the old publication identity while preventing consumers from
        reading the legacy member payload as the relation source.
        """
        filters = "publication_id=?"
        params: list[Any] = [publication_id]
        if source_scope is not None:
            filters += " AND source_scope=?"
            params.append(source_scope)
        rows = self.connection.execute(
            f"""
            SELECT publication_id, source_scope, observation_id, revision_no,
                   attribute_version_id, hierarchy_version, NULL AS legacy_snapshot_id
            FROM relation_publication_bindings
            WHERE {filters}
            ORDER BY source_scope
            """,
            params,
        ).fetchall()
        if len(rows) > 1 and source_scope is None:
            raise KeyError(f"RELATION_PUBLICATION_SOURCE_SCOPE_REQUIRED:{publication_id}")
        row = rows[0] if rows else None
        if row:
            names = (
                "publication_id",
                "source_scope",
                "observation_id",
                "revision_no",
                "attribute_version_id",
                "hierarchy_version",
                "legacy_snapshot_id",
            )
            return dict(zip(names, row))

        legacy_filters = "pm.publication_id=?"
        legacy_params: list[Any] = [publication_id]
        if source_scope is not None:
            legacy_filters += " AND o.source_scope=?"
            legacy_params.append(source_scope)
        rows = self.connection.execute(
            f"""
            SELECT pm.publication_id, o.source_scope, b.observation_id,
                   b.revision_no, b.attribute_version_id, b.hierarchy_version,
                   b.legacy_membership_snapshot_id
            FROM publication_memberships pm
            JOIN relation_snapshot_bindings b
              ON b.legacy_membership_snapshot_id=pm.membership_snapshot_id
            JOIN relation_observations o ON o.observation_id=b.observation_id
            WHERE {legacy_filters}
            ORDER BY o.source_scope
            """,
            legacy_params,
        ).fetchall()
        if len(rows) > 1 and source_scope is None:
            raise KeyError(f"RELATION_PUBLICATION_SOURCE_SCOPE_REQUIRED:{publication_id}")
        row = rows[0] if rows else None
        if not row:
            return None
        names = (
            "publication_id",
            "source_scope",
            "observation_id",
            "revision_no",
            "attribute_version_id",
            "hierarchy_version",
            "legacy_snapshot_id",
        )
        return dict(zip(names, row))

    def edges_for_publication_compat(
        self, publication_id: str, source_scope: str | None = None
    ) -> tuple[RelationEdge, ...]:
        binding = self.publication_binding(publication_id, source_scope)
        if not binding:
            raise KeyError(f"RELATION_PUBLICATION_BINDING_NOT_FOUND:{publication_id}:{source_scope or '*'}")
        return self.edges_at(str(binding["source_scope"]), int(binding["revision_no"]))

    def member_ids_for_sector(self, source_scope: str, revision_no: int, sector_id: str) -> tuple[str, ...]:
        return self.members_by_sector(source_scope, revision_no).get(str(sector_id), ())
