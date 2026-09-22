"""Backend-neutral metadata catalog for offline backup artifacts."""
from __future__ import annotations

import json
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator, Mapping, Protocol

import duckdb
from psycopg import sql

from .postgres_repository import PostgresRepository


def _json(value: Mapping[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def _payload(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else json.loads(value or "{}")


class BackupCatalogRepository(Protocol):
    def upsert(self, backup_id: str, payload: Mapping[str, Any]) -> None: ...
    def get(self, backup_id: str) -> dict[str, Any] | None: ...
    def rows(self) -> list[tuple[str, dict[str, Any]]]: ...


class DuckDBBackupCatalogRepository:
    def __init__(self, database_path: str | Path):
        self.database_path = Path(database_path).resolve()

    def upsert(self, backup_id: str, payload: Mapping[str, Any]) -> None:
        with duckdb.connect(str(self.database_path)) as connection:
            connection.execute("insert into backup_catalog values (?, ?) on conflict do nothing", [backup_id, _json(payload)])

    def get(self, backup_id: str) -> dict[str, Any] | None:
        with duckdb.connect(str(self.database_path), read_only=True) as connection:
            row = connection.execute("select payload_json from backup_catalog where backup_id=?", [backup_id]).fetchone()
        return _payload(row[0]) if row else None

    def rows(self) -> list[tuple[str, dict[str, Any]]]:
        with duckdb.connect(str(self.database_path), read_only=True) as connection:
            result = connection.execute("select backup_id,payload_json from backup_catalog order by backup_id").fetchall()
        return [(str(row[0]), _payload(row[1])) for row in result]


class PostgresBackupCatalogRepository:
    def __init__(self, repository: PostgresRepository):
        self.repository = repository

    def _connection(self):
        if self.repository.connection is None:
            raise RuntimeError("POSTGRES_REPOSITORY_NOT_OPEN")
        return self.repository.connection

    def upsert(self, backup_id: str, payload: Mapping[str, Any]) -> None:
        query = sql.SQL("insert into {}.backup_catalog(backup_id,payload_json) values (%s,%s::jsonb) on conflict(backup_id) do nothing").format(sql.Identifier(self.repository.schema))
        with self.repository.transaction() as connection:
            with connection.cursor() as cur:
                cur.execute(query, (backup_id, _json(payload)))

    def get(self, backup_id: str) -> dict[str, Any] | None:
        query = sql.SQL("select payload_json from {}.backup_catalog where backup_id=%s").format(sql.Identifier(self.repository.schema))
        with self._connection().cursor() as cur:
            cur.execute(query, (backup_id,))
            row = cur.fetchone()
        return _payload(row[0]) if row else None

    def rows(self) -> list[tuple[str, dict[str, Any]]]:
        query = sql.SQL("select backup_id,payload_json from {}.backup_catalog order by backup_id").format(sql.Identifier(self.repository.schema))
        with self._connection().cursor() as cur:
            cur.execute(query)
            result = cur.fetchall()
        return [(str(row[0]), _payload(row[1])) for row in result]


__all__ = ["BackupCatalogRepository", "DuckDBBackupCatalogRepository", "PostgresBackupCatalogRepository"]
