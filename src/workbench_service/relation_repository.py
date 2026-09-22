"""Versioned slow-changing membership relations for the V3 preview path.

This module is intentionally isolated from the legacy membership importer and
read APIs.  It stores direct relation edges as revision intervals and records
small observations when a source is unchanged.
"""

from __future__ import annotations

import hashlib
import json
import re
import uuid
from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Any, Iterable, Mapping, Sequence

import duckdb
from psycopg import sql

from workbench_db.postgres_repository import PostgresRepository


PARSER_CONTRACT = "relation-parser-v3-v1"
DEFAULT_SOURCE_SCOPE_CONTRACT = "direct-members-v3-v1"
VALID_QUALITY = "READY"
INVALID_QUALITY = "INVALID"
_DATE_OR_TASK_TOKEN = re.compile(r"(?:\d{4}[-_]\d{2}[-_]\d{2}|task[-_]|job[-_])", re.IGNORECASE)


class RelationInputError(ValueError):
    """Raised when a relation source cannot safely update the current revision."""


@dataclass(frozen=True)
class RelationEdge:
    source_scope: str
    sector_id: str
    security_id: str
    source_kind: str

    def key(self) -> tuple[str, str, str]:
        return self.sector_id, self.security_id, self.source_kind

    def as_dict(self) -> dict[str, str]:
        return {
            "source_scope": self.source_scope,
            "sector_id": self.sector_id,
            "security_id": self.security_id,
            "source_kind": self.source_kind,
        }


@dataclass(frozen=True)
class RelationDiff:
    added: tuple[RelationEdge, ...]
    removed: tuple[RelationEdge, ...]
    unchanged: tuple[RelationEdge, ...]

    @property
    def changed(self) -> bool:
        return bool(self.added or self.removed)

    def as_dict(self) -> dict[str, list[dict[str, str]]]:
        return {
            "added": [edge.as_dict() for edge in self.added],
            "removed": [edge.as_dict() for edge in self.removed],
            "unchanged": [edge.as_dict() for edge in self.unchanged],
        }


def _text(value: Any, field: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise RelationInputError(f"RELATION_FIELD_MISSING:{field}")
    return text


def make_source_scope(source_id: Any, contract: str = DEFAULT_SOURCE_SCOPE_CONTRACT) -> str:
    """Build a stable namespace that cannot accidentally contain a date/task id."""

    source = _text(source_id, "source_id").upper()
    contract_text = _text(contract, "contract")
    if _DATE_OR_TASK_TOKEN.search(source) or _DATE_OR_TASK_TOKEN.search(contract_text):
        raise RelationInputError("RELATION_SOURCE_SCOPE_NOT_STABLE")
    return f"{source}:{contract_text}"


def validate_source_scope(value: Any) -> str:
    scope = _text(value, "source_scope")
    if _DATE_OR_TASK_TOKEN.search(scope):
        raise RelationInputError("RELATION_SOURCE_SCOPE_NOT_STABLE")
    return scope


def normalize_edges(rows: Iterable[Mapping[str, Any]], source_scope: str) -> tuple[RelationEdge, ...]:
    scope = validate_source_scope(source_scope)
    normalized: dict[tuple[str, str, str], RelationEdge] = {}
    for row in rows:
        if not isinstance(row, Mapping):
            raise RelationInputError("RELATION_ROW_NOT_MAPPING")
        edge = RelationEdge(
            source_scope=scope,
            sector_id=_text(row.get("sector_id"), "sector_id"),
            security_id=_text(row.get("security_id"), "security_id").upper(),
            source_kind=_text(row.get("source_kind", "DIRECT"), "source_kind").upper(),
        )
        normalized[edge.key()] = edge
    if not normalized:
        raise RelationInputError("RELATION_SOURCE_EMPTY")
    return tuple(normalized[key] for key in sorted(normalized))


def normalize_attributes(rows: Iterable[Mapping[str, Any]], source_scope: str) -> tuple[dict[str, str | None], ...]:
    scope = validate_source_scope(source_scope)
    normalized: dict[str, dict[str, str | None]] = {}
    for row in rows:
        if not isinstance(row, Mapping):
            raise RelationInputError("ATTRIBUTE_ROW_NOT_MAPPING")
        sector_id = _text(row.get("sector_id"), "sector_id")
        normalized[sector_id] = {
            "source_scope": scope,
            "sector_id": sector_id,
            "name": _text(row.get("name", row.get("sector_name")), "name"),
            "type": _text(row.get("type", row.get("sector_type")), "type"),
            "role": str(row.get("role") or "").strip() or None,
            "semantic_bucket": str(row.get("semantic_bucket") or "").strip() or None,
        }
    return tuple(normalized[key] for key in sorted(normalized))


def edge_content_hash(source_scope: str, edges: Sequence[RelationEdge], parser_contract: str = PARSER_CONTRACT) -> str:
    payload = {
        "source_scope": validate_source_scope(source_scope),
        "parser_contract": _text(parser_contract, "parser_contract"),
        "edges": [
            {"sector_id": edge.sector_id, "security_id": edge.security_id, "source_kind": edge.source_kind}
            for edge in sorted(edges, key=lambda item: item.key())
        ],
    }
    return _hash_payload(payload)


def attribute_content_hash(source_scope: str, attributes: Sequence[Mapping[str, Any]], parser_contract: str = PARSER_CONTRACT) -> str:
    normalized = normalize_attributes(attributes, source_scope)
    payload = {
        "source_scope": validate_source_scope(source_scope),
        "parser_contract": _text(parser_contract, "parser_contract"),
        "attributes": [dict(item) for item in normalized],
    }
    return _hash_payload(payload)


def _hash_payload(payload: Mapping[str, Any]) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def diff_relation_edges(previous: Iterable[RelationEdge], current: Iterable[RelationEdge]) -> RelationDiff:
    previous_map = {edge.key(): edge for edge in previous}
    current_map = {edge.key(): edge for edge in current}
    added = tuple(current_map[key] for key in sorted(set(current_map) - set(previous_map)))
    removed = tuple(previous_map[key] for key in sorted(set(previous_map) - set(current_map)))
    unchanged = tuple(current_map[key] for key in sorted(set(current_map) & set(previous_map)))
    return RelationDiff(added=added, removed=removed, unchanged=unchanged)


def diff_edges(previous: Iterable[RelationEdge], current: Iterable[RelationEdge]) -> RelationDiff:
    return diff_relation_edges(previous, current)


def _timestamp(value: datetime | str | None) -> datetime:
    if value is None:
        return datetime.now(timezone.utc).replace(tzinfo=None)
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).replace(tzinfo=None) if value.tzinfo else value
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    return parsed.astimezone(timezone.utc).replace(tzinfo=None) if parsed.tzinfo else parsed


def _date(value: date | str | None) -> date | None:
    if value is None or isinstance(value, date) and not isinstance(value, datetime):
        return value
    return date.fromisoformat(str(value))


class MembershipResolver:
    """Batch resolver for a source scope and revision."""

    def __init__(self, connection: duckdb.DuckDBPyConnection):
        self.connection = connection

    def edges_at(self, source_scope: str, revision_no: int) -> tuple[RelationEdge, ...]:
        rows = self.connection.execute(
            """
            SELECT source_scope, sector_id, security_id, source_kind
            FROM relation_edge_intervals
            WHERE source_scope=? AND from_revision<=?
              AND (to_revision IS NULL OR ?<to_revision)
            ORDER BY sector_id, security_id, source_kind
            """,
            [source_scope, revision_no, revision_no],
        ).fetchall()
        return tuple(RelationEdge(*row) for row in rows)

    def members_by_sector(self, source_scope: str, revision_no: int) -> dict[str, tuple[str, ...]]:
        result: dict[str, list[str]] = {}
        for edge in self.edges_at(source_scope, revision_no):
            result.setdefault(edge.sector_id, []).append(edge.security_id)
        return {sector_id: tuple(sorted(set(security_ids))) for sector_id, security_ids in result.items()}


class RelationRepository:
    """Atomic writer for relation revisions and observation-only repeats."""

    def __init__(self, connection: duckdb.DuckDBPyConnection):
        self.connection = connection
        self.resolver = MembershipResolver(connection)

    def current_revision(self, source_scope: str) -> int | None:
        row = self.connection.execute(
            "SELECT max(revision_no) FROM relation_revisions WHERE source_scope=?", [source_scope]
        ).fetchone()
        return int(row[0]) if row and row[0] is not None else None

    def record_observation(
        self,
        *,
        source_scope: str,
        edges: Iterable[Mapping[str, Any]],
        attributes: Iterable[Mapping[str, Any]] = (),
        observed_at: datetime | str | None = None,
        source_effective_date: date | str | None = None,
        source_file_hashes: Mapping[str, Any] | Sequence[str] = (),
        hierarchy_version: str | None = None,
        source_complete: bool = True,
        observation_id: str | None = None,
        manage_transaction: bool = True,
    ) -> dict[str, Any]:
        scope = validate_source_scope(source_scope)
        observation = observation_id or f"relation-observation-{uuid.uuid4().hex}"
        timestamp = _timestamp(observed_at)
        effective_date = _date(source_effective_date)
        hashes_json = json.dumps(source_file_hashes, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
        current = self.current_revision(scope)

        if not source_complete:
            return self._record_invalid_observation(
                observation, scope, timestamp, effective_date, hashes_json, current, hierarchy_version,
                manage_transaction=manage_transaction,
            )

        try:
            normalized_edges = normalize_edges(edges, scope)
        except RelationInputError as exc:
            if str(exc) != "RELATION_SOURCE_EMPTY":
                raise
            return self._record_invalid_observation(
                observation, scope, timestamp, effective_date, hashes_json, current, hierarchy_version,
                manage_transaction=manage_transaction,
            )
        normalized_attributes = normalize_attributes(attributes, scope)
        previous_edges = self.resolver.edges_at(scope, current) if current is not None else ()
        new_hash = edge_content_hash(scope, normalized_edges)
        old_hash = None
        if current is not None:
            old_hash = self.connection.execute(
                "SELECT edge_content_hash FROM relation_revisions WHERE source_scope=? AND revision_no=?", [scope, current]
            ).fetchone()[0]

        if manage_transaction:
            self.connection.execute("BEGIN TRANSACTION")
        try:
            attributes_result = self._prepare_attributes(scope, normalized_attributes)
            if current is not None and old_hash == new_hash:
                revision_no = current
                status = "UNCHANGED"
                diff = diff_relation_edges(previous_edges, normalized_edges)
            else:
                revision_no = (current or 0) + 1
                diff = diff_relation_edges(previous_edges, normalized_edges)
                self._insert_revision(scope, revision_no, current, new_hash)
                for edge in diff.removed:
                    self.connection.execute(
                        """
                        UPDATE relation_edge_intervals
                        SET to_revision=?
                        WHERE source_scope=? AND sector_id=? AND security_id=? AND source_kind=? AND to_revision IS NULL
                        """,
                        [revision_no, edge.source_scope, edge.sector_id, edge.security_id, edge.source_kind],
                    )
                for edge in diff.added:
                    self.connection.execute(
                        "INSERT INTO relation_edge_intervals VALUES (?, ?, ?, ?, NULL, ?)",
                        [edge.source_scope, edge.sector_id, edge.security_id, revision_no, edge.source_kind],
                    )
                status = "UPDATED"
            self._insert_observation(
                observation,
                scope,
                timestamp,
                effective_date,
                hashes_json,
                revision_no,
                attributes_result["attribute_version_id"],
                hierarchy_version,
                VALID_QUALITY,
            )
            if manage_transaction:
                self.connection.execute("COMMIT")
        except Exception:
            if manage_transaction:
                self.connection.execute("ROLLBACK")
            raise
        return {
            "status": status,
            "updated": status == "UPDATED",
            "observation_id": observation,
            "revision_no": revision_no,
            "attribute_revision": attributes_result["attribute_revision"],
            "attribute_version_id": attributes_result["attribute_version_id"],
            "diff": diff.as_dict(),
        }

    def _record_invalid_observation(
        self,
        observation_id: str,
        scope: str,
        observed_at: datetime,
        effective_date: date | None,
        source_file_hashes: str,
        current_revision: int | None,
        hierarchy_version: str | None,
        *,
        manage_transaction: bool = True,
    ) -> dict[str, Any]:
        if manage_transaction:
            self.connection.execute("BEGIN TRANSACTION")
        try:
            self._insert_observation(
                observation_id,
                scope,
                observed_at,
                effective_date,
                source_file_hashes,
                current_revision or 0,
                None,
                hierarchy_version,
                INVALID_QUALITY,
            )
            if manage_transaction:
                self.connection.execute("COMMIT")
        except Exception:
            if manage_transaction:
                self.connection.execute("ROLLBACK")
            raise
        return {"status": INVALID_QUALITY, "updated": False, "observation_id": observation_id, "revision_no": current_revision}

    def _insert_revision(self, scope: str, revision_no: int, previous: int | None, content_hash: str) -> None:
        self.connection.execute(
            "INSERT INTO relation_revisions VALUES (?, ?, ?, ?, ?, ?, ?)",
            [scope, revision_no, f"{scope}:r{revision_no}", previous, content_hash, PARSER_CONTRACT, _timestamp(None)],
        )

    def _insert_observation(
        self,
        observation_id: str,
        scope: str,
        observed_at: datetime,
        effective_date: date | None,
        source_file_hashes: str,
        revision_no: int,
        attribute_version_id: str | None,
        hierarchy_version: str | None,
        quality: str,
    ) -> None:
        self.connection.execute(
            "INSERT INTO relation_observations VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [observation_id, scope, observed_at, effective_date, source_file_hashes, revision_no, attribute_version_id, hierarchy_version, quality],
        )

    def _prepare_attributes(self, scope: str, attributes: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
        if not attributes:
            row = self.connection.execute(
                "SELECT max(attribute_revision) FROM sector_attribute_revisions WHERE source_scope=?", [scope]
            ).fetchone()
            return {"attribute_revision": int(row[0]) if row and row[0] is not None else None, "attribute_version_id": None}
        content_hash = attribute_content_hash(scope, attributes)
        current = self.connection.execute(
            "SELECT attribute_revision FROM sector_attribute_revisions WHERE source_scope=? AND attribute_set_hash=?", [scope, content_hash]
        ).fetchone()
        if current:
            revision_no = int(current[0])
            return {"attribute_revision": revision_no, "attribute_version_id": "attrset-" + content_hash[:24]}
        previous = self.connection.execute(
            "SELECT max(attribute_revision) FROM sector_attribute_revisions WHERE source_scope=?", [scope]
        ).fetchone()[0]
        revision_no = int(previous or 0) + 1
        self.connection.execute(
            "INSERT INTO sector_attribute_revisions VALUES (?, ?, ?)", [scope, revision_no, content_hash]
        )
        if previous is not None:
            self.connection.execute(
                "UPDATE sector_attribute_revision_bindings SET to_attribute_revision=? WHERE source_scope=? AND to_attribute_revision IS NULL",
                [revision_no, scope],
            )
        version_ids: list[str] = []
        for item in attributes:
            version_id = "attr-" + _hash_payload(item)[:24]
            version_ids.append(version_id)
            self.connection.execute(
                """
                INSERT INTO sector_attribute_versions
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (source_scope, sector_id, attribute_version_id) DO NOTHING
                """,
                [scope, item["sector_id"], version_id, item["name"], item["type"], item["role"], item["semantic_bucket"], _hash_payload(item)],
            )
            self.connection.execute(
                "INSERT INTO sector_attribute_revision_bindings VALUES (?, ?, ?, NULL, ?)",
                [scope, item["sector_id"], revision_no, version_id],
            )
        return {"attribute_revision": revision_no, "attribute_version_id": "attrset-" + content_hash[:24]}


class PostgresRelationRepository:
    """PostgreSQL equivalent of the relation revision/observation writer."""

    def __init__(self, repository: PostgresRepository):
        self.repository = repository

    def _connection(self):
        if self.repository.connection is None:
            raise RuntimeError("POSTGRES_REPOSITORY_NOT_OPEN")
        return self.repository.connection

    def _table(self, name: str) -> sql.Identifier:
        return sql.Identifier(self.repository.schema, name)

    def current_revision(self, source_scope: str) -> int | None:
        with self._connection().cursor() as cur:
            cur.execute(sql.SQL("select max(revision_no) from {} where source_scope=%s").format(self._table("relation_revisions")), (source_scope,))
            value = cur.fetchone()[0]
        return int(value) if value is not None else None

    def _edges_at(self, source_scope: str, revision_no: int | None) -> tuple[RelationEdge, ...]:
        if revision_no is None:
            return ()
        query = sql.SQL("select source_scope,sector_id,security_id,source_kind from {} where source_scope=%s and from_revision<=%s and (to_revision is null or %s<to_revision) order by sector_id,security_id,source_kind").format(self._table("relation_edge_intervals"))
        with self._connection().cursor() as cur:
            cur.execute(query, (source_scope, revision_no, revision_no))
            return tuple(RelationEdge(*row) for row in cur.fetchall())

    def record_observation(self, *, source_scope: str, edges: Iterable[Mapping[str, Any]], attributes: Iterable[Mapping[str, Any]] = (), observed_at: datetime | str | None = None, source_effective_date: date | str | None = None, source_file_hashes: Mapping[str, Any] | Sequence[str] = (), hierarchy_version: str | None = None, source_complete: bool = True, observation_id: str | None = None, manage_transaction: bool = True) -> dict[str, Any]:
        scope = validate_source_scope(source_scope)
        observation = observation_id or f"relation-observation-{uuid.uuid4().hex}"
        timestamp = _timestamp(observed_at)
        effective_date = _date(source_effective_date)
        hashes_json = json.dumps(source_file_hashes, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
        current = self.current_revision(scope)
        if not source_complete:
            return self._invalid(observation, scope, timestamp, effective_date, hashes_json, current, hierarchy_version, manage_transaction)
        try:
            normalized_edges = normalize_edges(edges, scope)
        except RelationInputError as exc:
            if str(exc) != "RELATION_SOURCE_EMPTY":
                raise
            return self._invalid(observation, scope, timestamp, effective_date, hashes_json, current, hierarchy_version, manage_transaction)
        normalized_attributes = normalize_attributes(attributes, scope)
        previous_edges = self._edges_at(scope, current)
        new_hash = edge_content_hash(scope, normalized_edges)
        old_hash = None
        if current is not None:
            with self._connection().cursor() as cur:
                cur.execute(sql.SQL("select edge_content_hash from {} where source_scope=%s and revision_no=%s").format(self._table("relation_revisions")), (scope, current))
                old_hash = cur.fetchone()[0]
        def work() -> dict[str, Any]:
            attr_result = self._prepare_attributes(scope, normalized_attributes)
            if current is not None and old_hash == new_hash:
                revision_no = current; status = "UNCHANGED"; diff = diff_relation_edges(previous_edges, normalized_edges)
            else:
                revision_no = (current or 0) + 1; diff = diff_relation_edges(previous_edges, normalized_edges)
                with self._connection().cursor() as cur:
                    cur.execute(sql.SQL("insert into {}(source_scope,revision_no,revision_id,previous_revision_no,edge_content_hash,parser_contract,created_at) values (%s,%s,%s,%s,%s,%s,%s)").format(self._table("relation_revisions")), (scope, revision_no, f"{scope}:r{revision_no}", current, new_hash, PARSER_CONTRACT, timestamp))
                    for edge in diff.removed:
                        cur.execute(sql.SQL("update {} set to_revision=%s where source_scope=%s and sector_id=%s and security_id=%s and source_kind=%s and to_revision is null").format(self._table("relation_edge_intervals")), (revision_no, edge.source_scope, edge.sector_id, edge.security_id, edge.source_kind))
                    for edge in diff.added:
                        cur.execute(sql.SQL("insert into {}(source_scope,sector_id,security_id,from_revision,to_revision,source_kind) values (%s,%s,%s,%s,%s,%s)").format(self._table("relation_edge_intervals")), (edge.source_scope, edge.sector_id, edge.security_id, revision_no, None, edge.source_kind))
                status = "UPDATED"
            with self._connection().cursor() as cur:
                cur.execute(sql.SQL("insert into {}(observation_id,source_scope,observed_at,source_effective_date,source_file_hashes,revision_no,attribute_version_id,hierarchy_version,quality) values (%s,%s,%s,%s,%s::jsonb,%s,%s,%s,%s)").format(self._table("relation_observations")), (observation, scope, timestamp, effective_date, hashes_json, revision_no, attr_result["attribute_version_id"], hierarchy_version, VALID_QUALITY))
            return {"status": status, "updated": status == "UPDATED", "observation_id": observation, "revision_no": revision_no, "attribute_revision": attr_result["attribute_revision"], "attribute_version_id": attr_result["attribute_version_id"], "diff": diff.as_dict()}
        if manage_transaction:
            with self.repository.transaction():
                return work()
        return work()

    def _invalid(self, observation: str, scope: str, timestamp: datetime, effective_date: date | None, hashes_json: str, current: int | None, hierarchy_version: str | None, manage_transaction: bool) -> dict[str, Any]:
        def work() -> None:
            with self._connection().cursor() as cur:
                cur.execute(sql.SQL("insert into {}(observation_id,source_scope,observed_at,source_effective_date,source_file_hashes,revision_no,attribute_version_id,hierarchy_version,quality) values (%s,%s,%s,%s,%s::jsonb,%s,%s,%s,%s)").format(self._table("relation_observations")), (observation, scope, timestamp, effective_date, hashes_json, current or 0, None, hierarchy_version, INVALID_QUALITY))
        if manage_transaction:
            with self.repository.transaction():
                work()
        else:
            work()
        return {"status": INVALID_QUALITY, "updated": False, "observation_id": observation, "revision_no": current}

    def _prepare_attributes(self, scope: str, attributes: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
        with self._connection().cursor() as cur:
            if not attributes:
                cur.execute(sql.SQL("select max(attribute_revision) from {} where source_scope=%s").format(self._table("sector_attribute_revisions")), (scope,))
                value = cur.fetchone()[0]
                return {"attribute_revision": int(value) if value is not None else None, "attribute_version_id": None}
            content_hash = attribute_content_hash(scope, attributes)
            cur.execute(sql.SQL("select attribute_revision from {} where source_scope=%s and attribute_set_hash=%s").format(self._table("sector_attribute_revisions")), (scope, content_hash))
            current = cur.fetchone()
            if current:
                revision_no = int(current[0]); return {"attribute_revision": revision_no, "attribute_version_id": "attrset-" + content_hash[:24]}
            cur.execute(sql.SQL("select max(attribute_revision) from {} where source_scope=%s").format(self._table("sector_attribute_revisions")), (scope,))
            previous = cur.fetchone()[0]
            revision_no = int(previous or 0) + 1
            cur.execute(sql.SQL("insert into {}(source_scope,attribute_revision,attribute_set_hash) values (%s,%s,%s)").format(self._table("sector_attribute_revisions")), (scope, revision_no, content_hash))
            if previous is not None:
                cur.execute(sql.SQL("update {} set to_attribute_revision=%s where source_scope=%s and to_attribute_revision is null").format(self._table("sector_attribute_revision_bindings")), (revision_no, scope))
            for item in attributes:
                version_id = "attr-" + _hash_payload(item)[:24]
                cur.execute(sql.SQL("insert into {}(source_scope,sector_id,attribute_version_id,name,type,role,semantic_bucket,content_hash) values (%s,%s,%s,%s,%s,%s,%s,%s) on conflict(source_scope,sector_id,attribute_version_id) do nothing").format(self._table("sector_attribute_versions")), (scope, item["sector_id"], version_id, item["name"], item["type"], item["role"], item["semantic_bucket"], _hash_payload(item)))
                cur.execute(sql.SQL("insert into {}(source_scope,sector_id,from_attribute_revision,to_attribute_revision,attribute_version_id) values (%s,%s,%s,%s,%s)").format(self._table("sector_attribute_revision_bindings")), (scope, item["sector_id"], revision_no, None, version_id))
            return {"attribute_revision": revision_no, "attribute_version_id": "attrset-" + content_hash[:24]}
