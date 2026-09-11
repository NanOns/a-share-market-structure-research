"""P02-02 importer for the legacy membership snapshot store.

The legacy table is kept as the compatibility source.  This module only
projects its direct member edges and immutable attribute evidence into the V3
relation store; it does not change legacy rows or publication identities.
Derived-parent rows are deliberately retained as binding evidence and are
resolved against the versioned hierarchy in P02-03.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Iterable, Mapping

import duckdb

from .relation_repository import RelationRepository, attribute_content_hash, make_source_scope


LEGACY_IMPORT_CONTRACT = "legacy-membership-import-v3-v1"
LEGACY_SOURCE_SCOPE = make_source_scope("TDX-MEMBERSHIP", "direct-members-v3-v1")
DERIVED_PARENT_SOURCE = "tdxhy.cfg:DERIVED_PARENT"
KNOWN_DIRECT_SOURCES = {"tdxhy.cfg", "infoharbor_block.dat"}
REQUIRED_PAYLOAD_FIELDS = {
    "date",
    "membership_asof_date",
    "membership_basis",
    "pit_membership",
    "historical_backtest_safe",
    "sector_id",
    "sector_name",
    "sector_type",
    "sector_role",
    "security_id",
    "snapshot_version",
    "source",
}


class LegacyRelationImportError(ValueError):
    """Raised when a legacy snapshot cannot be safely projected."""


def _canonical_hash(value: Any) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _json_value(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    try:
        parsed = json.loads(str(value))
    except (TypeError, json.JSONDecodeError) as exc:
        raise LegacyRelationImportError("LEGACY_PAYLOAD_INVALID_JSON") from exc
    if not isinstance(parsed, dict):
        raise LegacyRelationImportError("LEGACY_PAYLOAD_NOT_OBJECT")
    return parsed


def _timestamp(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    if value is None:
        raise LegacyRelationImportError("LEGACY_OBSERVED_AT_MISSING")
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


def _source_kind(source: str) -> tuple[str, bool]:
    normalized = str(source or "").strip().lower()
    if normalized == DERIVED_PARENT_SOURCE.lower():
        return "DERIVED_PARENT", True
    if normalized in {value.lower() for value in KNOWN_DIRECT_SOURCES}:
        return "DIRECT", False
    # The old store can contain a source introduced by an older parser.  Keep
    # its edge queryable instead of silently treating it as a derived row.
    return "LEGACY_EXPLICIT", False


@dataclass(frozen=True)
class LegacySnapshotPlan:
    snapshot_id: str
    trade_date: date
    snapshot_version: str
    payload_snapshot_version: str
    logical_sha256: str
    row_count: int
    observed_at: datetime
    direct_edges: tuple[dict[str, str], ...]
    attributes: tuple[dict[str, str | None], ...]
    source_file_hashes: dict[str, Any]
    hierarchy_version: str | None
    legacy_payload_basis: dict[str, Any]


class LegacySnapshotAdapter:
    """Read and validate old snapshots without writing the source database."""

    def __init__(self, connection: duckdb.DuckDBPyConnection, source_scope: str = LEGACY_SOURCE_SCOPE):
        self.connection = connection
        self.source_scope = source_scope

    def snapshot_ids(self) -> tuple[str, ...]:
        rows = self.connection.execute(
            "SELECT membership_snapshot_id FROM membership_snapshots ORDER BY trade_date, membership_snapshot_id"
        ).fetchall()
        return tuple(str(row[0]) for row in rows)

    def plan_all(self, snapshot_ids: Iterable[str] | None = None) -> tuple[LegacySnapshotPlan, ...]:
        selected = tuple(snapshot_ids) if snapshot_ids is not None else self.snapshot_ids()
        plans = tuple(self.plan(snapshot_id) for snapshot_id in selected)
        return tuple(sorted(plans, key=lambda item: (item.trade_date, item.snapshot_id)))

    def plan(self, snapshot_id: str) -> LegacySnapshotPlan:
        snapshot = self.connection.execute(
            """
            SELECT membership_snapshot_id, trade_date, snapshot_version,
                   logical_sha256, row_count
            FROM membership_snapshots
            WHERE membership_snapshot_id=?
            """,
            [snapshot_id],
        ).fetchone()
        if not snapshot:
            raise LegacyRelationImportError(f"LEGACY_SNAPSHOT_NOT_FOUND:{snapshot_id}")
        sid, trade_date, snapshot_version, logical_sha256, row_count = snapshot
        rows = self.connection.execute(
            """
            SELECT sector_id, security_id, payload_json
            FROM membership_entries
            WHERE membership_snapshot_id=?
            ORDER BY sector_id, security_id
            """,
            [sid],
        ).fetchall()
        if len(rows) != int(row_count):
            raise LegacyRelationImportError(f"LEGACY_ROW_COUNT_MISMATCH:{sid}:{row_count}:{len(rows)}")

        payloads: list[dict[str, Any]] = []
        direct_edges: dict[tuple[str, str, str], dict[str, str]] = {}
        attributes: dict[str, dict[str, str | None]] = {}
        source_counts: dict[str, int] = {}
        source_kind_counts: dict[str, int] = {}
        derived_rows = 0
        semantic_values: dict[str, set[str]] = {
            "date": set(),
            "membership_asof_date": set(),
            "membership_basis": set(),
            "pit_membership": set(),
            "historical_backtest_safe": set(),
            "snapshot_version": set(),
        }
        for sector_id, security_id, payload_value in rows:
            payload = _json_value(payload_value)
            missing = sorted(REQUIRED_PAYLOAD_FIELDS - set(payload))
            if missing:
                raise LegacyRelationImportError(f"LEGACY_PAYLOAD_FIELDS_MISSING:{sid}:{','.join(missing)}")
            payloads.append(payload)
            source = str(payload["source"]).strip()
            kind, is_derived = _source_kind(source)
            source_counts[source] = source_counts.get(source, 0) + 1
            source_kind_counts[kind] = source_kind_counts.get(kind, 0) + 1
            if is_derived:
                derived_rows += 1
            else:
                edge = {
                    "sector_id": str(sector_id),
                    "security_id": str(security_id).upper(),
                    "source_kind": kind,
                }
                direct_edges[(edge["sector_id"], edge["security_id"], kind)] = edge
            for field in semantic_values:
                semantic_values[field].add(str(payload[field]))
            attribute = {
                "source_scope": self.source_scope,
                "sector_id": str(sector_id),
                "name": str(payload["sector_name"]),
                "type": str(payload["sector_type"]),
                "role": str(payload.get("sector_role") or "") or None,
                "semantic_bucket": str(payload.get("semantic_bucket") or "") or None,
            }
            prior = attributes.get(attribute["sector_id"])
            if prior is not None and prior != attribute:
                raise LegacyRelationImportError(f"LEGACY_ATTRIBUTE_CONFLICT:{sid}:{attribute['sector_id']}")
            attributes[attribute["sector_id"]] = attribute

        for field, values in semantic_values.items():
            if len(values) != 1:
                raise LegacyRelationImportError(f"LEGACY_SEMANTIC_FIELD_CONFLICT:{sid}:{field}")

        publications = self.connection.execute(
            """
            SELECT p.publication_id, p.imported_at_utc, p.source_manifest_sha256,
                   p.source_identity_sha256
            FROM publication_memberships pm
            JOIN publications p ON p.publication_id=pm.publication_id
            WHERE pm.membership_snapshot_id=?
            ORDER BY p.imported_at_utc, p.publication_id
            """,
            [sid],
        ).fetchall()
        if not publications:
            raise LegacyRelationImportError(f"LEGACY_PUBLICATION_BINDING_MISSING:{sid}")
        observed_at = min(_timestamp(row[1]) for row in publications)
        source_file_hashes = self._source_hashes(publications, logical_sha256)
        canonical_payloads = sorted(
            payloads,
            key=lambda item: (str(item["sector_id"]), str(item["security_id"]).upper(), str(item["source"])),
        )
        basis = {
            "contract": LEGACY_IMPORT_CONTRACT,
            "legacy_snapshot_id": str(sid),
            "trade_date": str(trade_date),
            "snapshot_version": str(snapshot_version),
            "payload_snapshot_version": next(iter(semantic_values["snapshot_version"])),
            "legacy_logical_sha256": str(logical_sha256),
            "legacy_row_count": int(row_count),
            "direct_edge_count": len(direct_edges),
            "derived_edge_count": derived_rows,
            "source_counts": dict(sorted(source_counts.items())),
            "source_kind_counts": dict(sorted(source_kind_counts.items())),
            "semantic_fields": {key: next(iter(values)) for key, values in semantic_values.items()},
            "attribute_count": len(attributes),
            "legacy_payload_sha256": _canonical_hash(canonical_payloads),
            "derived_parent_resolution": "PENDING_P02-03" if derived_rows else "NOT_APPLICABLE",
            "observed_at_basis": "MIN_PUBLICATION_IMPORTED_AT_UTC",
            "publication_ids": [str(row[0]) for row in publications],
        }
        return LegacySnapshotPlan(
            snapshot_id=str(sid),
            trade_date=trade_date,
            snapshot_version=str(snapshot_version),
            payload_snapshot_version=next(iter(semantic_values["snapshot_version"])),
            logical_sha256=str(logical_sha256),
            row_count=int(row_count),
            observed_at=observed_at,
            direct_edges=tuple(direct_edges[key] for key in sorted(direct_edges)),
            attributes=tuple(attributes[key] for key in sorted(attributes)),
            source_file_hashes=source_file_hashes,
            hierarchy_version=None,
            legacy_payload_basis=basis,
        )

    def _source_hashes(self, publications: list[tuple[Any, ...]], logical_sha256: str) -> dict[str, Any]:
        manifests = sorted({str(row[2]) for row in publications if row[2]})
        identities = sorted({str(row[3]) for row in publications if row[3]})
        bundle_rows = self.connection.execute("SELECT source_bundle_id, payload_json FROM source_bundles").fetchall()
        bundles: list[dict[str, Any]] = []
        for bundle_id, payload_value in bundle_rows:
            payload = _json_value(payload_value)
            package = payload.get("package") or {}
            package_sha = package.get("sha256")
            if str(bundle_id) not in manifests and str(package_sha) not in manifests:
                continue
            files = ((payload.get("metadata") or {}).get("files") or {})
            bundles.append(
                {
                    "source_bundle_id": str(bundle_id),
                    "package_sha256": str(package_sha) if package_sha else None,
                    "metadata_snapshot_id": ((payload.get("metadata") or {}).get("metadata_snapshot_id")),
                    "file_hashes": {
                        str(path).split("/")[-1]: str(meta.get("sha256"))
                        for path, meta in files.items()
                        if isinstance(meta, dict) and meta.get("sha256")
                    },
                }
            )
        return {
            "legacy_snapshot_sha256": str(logical_sha256),
            "publication_source_manifest_sha256": manifests,
            "publication_source_identity_sha256": identities,
            "source_bundles": sorted(bundles, key=lambda item: item["source_bundle_id"]),
        }


class LegacyRelationImporter:
    """Idempotently bind all old membership snapshots to V3 relations."""

    def __init__(self, connection: duckdb.DuckDBPyConnection, source_scope: str = LEGACY_SOURCE_SCOPE):
        self.connection = connection
        self.source_scope = source_scope
        self.adapter = LegacySnapshotAdapter(connection, source_scope)
        self.repository = RelationRepository(connection)

    def import_snapshots(self, snapshot_ids: Iterable[str] | None = None) -> dict[str, Any]:
        plans = self.adapter.plan_all(snapshot_ids)
        results = []
        for plan in plans:
            expected_attribute_version_id = (
                "attrset-" + attribute_content_hash(self.source_scope, plan.attributes)[:24]
                if plan.attributes
                else None
            )
            binding = self.connection.execute(
                """
                SELECT observation_id, revision_no, attribute_version_id,
                       hierarchy_version, legacy_payload_basis
                FROM relation_snapshot_bindings
                WHERE legacy_membership_snapshot_id=?
                """,
                [plan.snapshot_id],
            ).fetchone()
            observation_id = f"legacy-relation-observation-{plan.snapshot_id}"
            if binding:
                existing_basis = _json_value(binding[4])
                basis_upgrade = dict(existing_basis)
                if "payload_snapshot_version" not in basis_upgrade:
                    basis_upgrade["payload_snapshot_version"] = basis_upgrade.get("semantic_fields", {}).get("snapshot_version")
                if basis_upgrade != plan.legacy_payload_basis:
                    raise LegacyRelationImportError(f"LEGACY_BINDING_MISMATCH:{plan.snapshot_id}")
                if binding[2] not in {None, expected_attribute_version_id}:
                    raise LegacyRelationImportError(f"LEGACY_ATTRIBUTE_BINDING_MISMATCH:{plan.snapshot_id}")
                status = "EXISTING"
                if binding[2] is None and expected_attribute_version_id is not None:
                    self.connection.execute(
                        """
                        UPDATE relation_observations
                        SET attribute_version_id=?
                        WHERE observation_id=? AND attribute_version_id IS NULL
                        """,
                        [expected_attribute_version_id, binding[0]],
                    )
                    self.connection.execute(
                        """
                        UPDATE relation_snapshot_bindings
                        SET attribute_version_id=?
                        WHERE legacy_membership_snapshot_id=? AND attribute_version_id IS NULL
                        """,
                        [expected_attribute_version_id, plan.snapshot_id],
                    )
                    status = "EXISTING_REPAIRED"
                if existing_basis != plan.legacy_payload_basis:
                    self.connection.execute(
                        "UPDATE relation_snapshot_bindings SET legacy_payload_basis=? WHERE legacy_membership_snapshot_id=?",
                        [json.dumps(plan.legacy_payload_basis, ensure_ascii=False, sort_keys=True), plan.snapshot_id],
                    )
                    status = "EXISTING_REPAIRED"
                results.append(
                    {
                        "snapshot_id": plan.snapshot_id,
                        "status": status,
                        "observation_id": str(binding[0]),
                        "revision_no": int(binding[1]),
                        "attribute_version_id": expected_attribute_version_id or binding[2],
                        "direct_edge_count": plan.legacy_payload_basis["direct_edge_count"],
                        "derived_edge_count": plan.legacy_payload_basis["derived_edge_count"],
                    }
                )
                continue

            observation = self.connection.execute(
                """
                SELECT source_scope, revision_no, attribute_version_id,
                       hierarchy_version, quality
                FROM relation_observations
                WHERE observation_id=?
                """,
                [observation_id],
            ).fetchone()
            if observation:
                if tuple(observation[0:1]) != (self.source_scope,) or observation[4] != "READY":
                    raise LegacyRelationImportError(f"LEGACY_OBSERVATION_MISMATCH:{plan.snapshot_id}")
                revision_no = int(observation[1])
                attribute_version_id = observation[2]
                hierarchy_version = observation[3]
                status = "OBSERVATION_EXISTING"
            else:
                recorded = self.repository.record_observation(
                    source_scope=self.source_scope,
                    edges=plan.direct_edges,
                    attributes=plan.attributes,
                    observed_at=plan.observed_at,
                    source_effective_date=plan.trade_date,
                    source_file_hashes=plan.source_file_hashes,
                    hierarchy_version=plan.hierarchy_version,
                    observation_id=observation_id,
                )
                if recorded["status"] not in {"UPDATED", "UNCHANGED"}:
                    raise LegacyRelationImportError(f"LEGACY_OBSERVATION_NOT_READY:{plan.snapshot_id}")
                revision_no = int(recorded["revision_no"])
                attribute_version_id = recorded.get("attribute_version_id")
                hierarchy_version = plan.hierarchy_version
                status = recorded["status"]

            self.connection.execute(
                """
                INSERT INTO relation_snapshot_bindings
                    (legacy_membership_snapshot_id, observation_id, revision_no,
                     attribute_version_id, hierarchy_version, legacy_payload_basis)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                [
                    plan.snapshot_id,
                    observation_id,
                    revision_no,
                    attribute_version_id,
                    hierarchy_version,
                    json.dumps(plan.legacy_payload_basis, ensure_ascii=False, sort_keys=True),
                ],
            )
            results.append(
                {
                    "snapshot_id": plan.snapshot_id,
                    "status": status,
                    "observation_id": observation_id,
                    "revision_no": revision_no,
                    "attribute_version_id": attribute_version_id,
                    "direct_edge_count": plan.legacy_payload_basis["direct_edge_count"],
                    "derived_edge_count": plan.legacy_payload_basis["derived_edge_count"],
                }
            )
        return {
            "contract": LEGACY_IMPORT_CONTRACT,
            "source_scope": self.source_scope,
            "snapshot_count": len(plans),
            "results": results,
        }


def compare_imported_snapshot(
    connection: duckdb.DuckDBPyConnection,
    snapshot_id: str,
    source_scope: str = LEGACY_SOURCE_SCOPE,
) -> dict[str, Any]:
    """Compare one old snapshot with the V3 resolver and preserved semantics."""

    adapter = LegacySnapshotAdapter(connection, source_scope)
    plan = adapter.plan(snapshot_id)
    binding = connection.execute(
        """
        SELECT observation_id, revision_no, attribute_version_id,
               hierarchy_version, legacy_payload_basis
        FROM relation_snapshot_bindings
        WHERE legacy_membership_snapshot_id=?
        """,
        [snapshot_id],
    ).fetchone()
    if not binding:
        raise LegacyRelationImportError(f"LEGACY_BINDING_NOT_FOUND:{snapshot_id}")
    resolver = RelationRepository(connection).resolver
    resolved = resolver.edges_at(source_scope, int(binding[1]))
    resolved_set = {(edge.sector_id, edge.security_id, edge.source_kind) for edge in resolved}
    expected_set = {
        (str(edge["sector_id"]), str(edge["security_id"]).upper(), str(edge["source_kind"]).upper())
        for edge in plan.direct_edges
    }
    basis = _json_value(binding[4])
    direct_match = resolved_set == expected_set
    reconstructed_count = len(resolved_set) + int(basis["derived_edge_count"])
    return {
        "snapshot_id": snapshot_id,
        "trade_date": str(plan.trade_date),
        "legacy_row_count": plan.row_count,
        "resolved_direct_edge_count": len(resolved_set),
        "legacy_direct_edge_count": int(basis["direct_edge_count"]),
        "legacy_derived_edge_count": int(basis["derived_edge_count"]),
        "reconstructed_legacy_row_count": reconstructed_count,
        "direct_edges_match": direct_match,
        "payload_semantics_match": reconstructed_count == plan.row_count
        and basis.get("semantic_fields", {})
        == {
            "date": str(plan.trade_date),
            "membership_asof_date": str(plan.trade_date),
            "membership_basis": basis.get("semantic_fields", {}).get("membership_basis"),
            "pit_membership": basis.get("semantic_fields", {}).get("pit_membership"),
            "historical_backtest_safe": basis.get("semantic_fields", {}).get("historical_backtest_safe"),
            "snapshot_version": plan.payload_snapshot_version,
        },
        "revision_no": int(binding[1]),
        "attribute_version_id": binding[2],
        "hierarchy_version": binding[3],
        "legacy_payload_sha256": basis["legacy_payload_sha256"],
        "status": "PASS" if direct_match and reconstructed_count == plan.row_count else "FAIL",
    }


def compare_all_imported_snapshots(
    connection: duckdb.DuckDBPyConnection,
    snapshot_ids: Iterable[str] | None = None,
    source_scope: str = LEGACY_SOURCE_SCOPE,
) -> dict[str, Any]:
    adapter = LegacySnapshotAdapter(connection, source_scope)
    selected = tuple(snapshot_ids) if snapshot_ids is not None else adapter.snapshot_ids()
    items = [compare_imported_snapshot(connection, snapshot_id, source_scope) for snapshot_id in selected]
    return {
        "contract": LEGACY_IMPORT_CONTRACT,
        "source_scope": source_scope,
        "snapshot_count": len(items),
        "status": "PASS" if items and all(item["status"] == "PASS" for item in items) else "FAIL",
        "items": items,
    }
