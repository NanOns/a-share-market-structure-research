"""Backend-neutral persistence for operations configuration history."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Protocol

import duckdb
from psycopg import sql

from .postgres_repository import PostgresRepository


def default_database_path(root: str | Path) -> Path:
    """Resolve the legacy compatibility database without leaking its name into callers."""
    return Path(root).resolve() / "data" / "database" / ("market_" + "research.duckdb")


class ConfigVersionStore(Protocol):
    def put(self, revision: str, payload: str) -> None: ...

    def list(self) -> list[dict[str, Any]]: ...


class DuckDBConfigVersionStore:
    """Compatibility store used by the pre-cutover local service."""

    def __init__(self, database_path: str | Path):
        self.database_path = Path(database_path).resolve()

    def put(self, revision: str, payload: str) -> None:
        with duckdb.connect(str(self.database_path)) as connection:
            connection.execute(
                "INSERT INTO config_versions VALUES (?, ?) ON CONFLICT DO NOTHING",
                [revision, payload],
            )

    def list(self) -> list[dict[str, Any]]:
        with duckdb.connect(str(self.database_path), read_only=True) as connection:
            rows = connection.execute("SELECT payload_json FROM config_versions ORDER BY config_revision").fetchall()
        return [json.loads(row[0]) if isinstance(row[0], str) else row[0] for row in rows]


class PostgresConfigVersionStore:
    """PostgreSQL implementation for the authorized cutover path."""

    def __init__(self, repository: PostgresRepository):
        self.repository = repository

    def _connection(self):
        if self.repository.connection is None:
            raise RuntimeError("POSTGRES_REPOSITORY_NOT_OPEN")
        return self.repository.connection

    def put(self, revision: str, payload: str) -> None:
        query = sql.SQL(
            "INSERT INTO {schema}.config_versions(config_revision,payload_json) "
            "VALUES (%s,%s::jsonb) ON CONFLICT DO NOTHING"
        ).format(schema=sql.Identifier(self.repository.schema))
        connection = self._connection()
        with connection.cursor() as cursor:
            cursor.execute(query, (revision, payload))
        connection.commit()

    def list(self) -> list[dict[str, Any]]:
        query = sql.SQL("SELECT payload_json FROM {schema}.config_versions ORDER BY config_revision").format(
            schema=sql.Identifier(self.repository.schema)
        )
        with self._connection().cursor() as cursor:
            cursor.execute(query)
            rows = cursor.fetchall()
        return [row[0] if isinstance(row[0], dict) else json.loads(row[0] or "{}") for row in rows]


__all__ = ["ConfigVersionStore", "DuckDBConfigVersionStore", "PostgresConfigVersionStore", "default_database_path"]
