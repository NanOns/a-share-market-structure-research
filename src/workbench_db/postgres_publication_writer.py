"""Transactional PostgreSQL writer for publication metadata and daily rows."""
from __future__ import annotations

import json
from contextlib import contextmanager
from datetime import date
from typing import Any, Iterator, Mapping, Sequence

from psycopg import sql

from .postgres_repository import PostgresRepository


ALLOWED_TABLES = {
    "stock_daily": {"publication_id", "security_id", "trade_date", "security_name", "primary_pattern", "payload_json"},
    "sector_daily": {"publication_id", "sector_id", "trade_date", "sector_name", "sector_type", "primary_pattern", "display_rank", "payload_json"},
    "candidate_daily": {"publication_id", "security_id", "trade_date", "security_name", "primary_pattern", "research_priority", "payload_json"},
    "structure_details": {"publication_id", "queue_name", "security_id", "trade_date", "payload_json"},
    "queue_memberships": {"publication_id", "queue_name", "security_id", "queue_tier", "source_v2_class", "payload_json"},
    "unified_board": {"publication_id", "security_id", "trade_date", "payload_json"},
    "queue_rankings": {"publication_id", "security_id", "payload_json"},
    "market_daily": {"publication_id", "trade_date", "payload_json"},
}


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


class PostgresPublicationWriter:
    def __init__(self, repository: PostgresRepository):
        self.repository = repository

    def _connection(self):
        if self.repository.connection is None:
            raise RuntimeError("POSTGRES_REPOSITORY_NOT_OPEN")
        return self.repository.connection

    def _table(self, name: str) -> sql.Identifier:
        return sql.Identifier(self.repository.schema, name)

    @contextmanager
    def transaction(self) -> Iterator["PostgresPublicationWriter"]:
        with self.repository.transaction():
            yield self

    def next_revision(self, trade_date: date | str) -> int:
        query = sql.SQL("select coalesce(max(revision),0)+1 from {} where trade_date=%s").format(self._table("publications"))
        with self._connection().cursor() as cur:
            cur.execute(query, (trade_date,))
            return int(cur.fetchone()[0])

    def publication(self, publication_id: str) -> dict[str, Any] | None:
        query = sql.SQL("select publication_id,trade_date,revision,status,source_revision_id,production_version,source_manifest_sha256,source_identity_sha256,computation_identity_sha256,render_identity_sha256,source_path,imported_at_utc from {} where publication_id=%s").format(self._table("publications"))
        with self._connection().cursor() as cur:
            cur.execute(query, (publication_id,))
            row = cur.fetchone()
        if not row:
            return None
        keys = ("publication_id", "trade_date", "revision", "status", "source_revision_id", "production_version", "source_manifest_sha256", "source_identity_sha256", "computation_identity_sha256", "render_identity_sha256", "source_path", "imported_at_utc")
        return dict(zip(keys, row))

    def insert_publication(self, *, publication_id: str, trade_date: date | str, revision: int, status: str, source_revision_id: int | None, production_version: str | None, source_manifest_sha256: str | None, source_identity_sha256: str | None, computation_identity_sha256: str | None, render_identity_sha256: str | None, source_path: str, imported_at_utc: Any) -> None:
        query = sql.SQL("insert into {}(publication_id,trade_date,revision,status,source_revision_id,production_version,source_manifest_sha256,source_identity_sha256,computation_identity_sha256,render_identity_sha256,source_path,imported_at_utc) values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)").format(self._table("publications"))
        with self._connection().cursor() as cur:
            cur.execute(query, (publication_id, trade_date, revision, status, source_revision_id, production_version, source_manifest_sha256, source_identity_sha256, computation_identity_sha256, render_identity_sha256, source_path, imported_at_utc))

    def bulk_insert(self, table: str, columns: Sequence[str], rows: Sequence[Mapping[str, Any]]) -> None:
        allowed = ALLOWED_TABLES.get(table)
        if not allowed or not columns or any(column not in allowed for column in columns):
            raise ValueError("PUBLICATION_TABLE_OR_COLUMN_NOT_ALLOWED")
        if not rows:
            return
        value_parts: list[sql.Composed] = []
        params: list[Any] = []
        for row in rows:
            placeholders: list[sql.Composed] = []
            for column in columns:
                value = row.get(column)
                if column == "payload_json":
                    placeholders.append(sql.SQL("%s::jsonb")); params.append(_json(value if isinstance(value, Mapping) else json.loads(value or "{}")))
                else:
                    placeholders.append(sql.SQL("%s")); params.append(value)
            value_parts.append(sql.SQL("(") + sql.SQL(",").join(placeholders) + sql.SQL(")"))
        query = sql.SQL("insert into {}({}) values {}").format(self._table(table), sql.SQL(",").join(sql.Identifier(column) for column in columns), sql.SQL(",").join(value_parts))
        with self._connection().cursor() as cur:
            cur.execute(query, params)

    def set_head(self, trade_date: date | str, publication_id: str) -> None:
        query = sql.SQL("insert into {}(trade_date,publication_id) values (%s,%s) on conflict(trade_date) do update set publication_id=excluded.publication_id").format(self._table("publication_heads"))
        with self._connection().cursor() as cur:
            cur.execute(query, (trade_date, publication_id))

    def mark_publication_success(self, publication_id: str) -> None:
        query = sql.SQL("update {} set status='SUCCESS' where publication_id=%s").format(self._table("publications"))
        with self._connection().cursor() as cur:
            cur.execute(query, (publication_id,))


__all__ = ["PostgresPublicationWriter"]
