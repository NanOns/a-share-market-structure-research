"""Connection boundary for the incremental research build coordinator."""
from __future__ import annotations

from contextlib import contextmanager
import os
from pathlib import Path
import re
import json
from typing import Any, Iterator, Protocol

import duckdb
import psycopg


class IncrementalWriterRepository(Protocol):
    @contextmanager
    def connect(self) -> Iterator[Any]: ...


class DuckDBIncrementalWriterRepository:
    """Compatibility adapter; the coordinator owns no backend connection."""

    def __init__(self, database_path: str | Path):
        self.database_path = Path(database_path).resolve()

    @contextmanager
    def connect(self) -> Iterator[duckdb.DuckDBPyConnection]:
        with duckdb.connect(str(self.database_path)) as connection:
            yield connection


class _PostgresIncrementalConnection:
    """Small DB-API compatibility surface for the existing domain writers.

    The incremental coordinator and its domain writers intentionally expose a
    DuckDB-shaped ``execute(sql, params)`` boundary.  This adapter translates
    only the qmark placeholders used by that boundary and delegates all SQL,
    transaction, and constraint handling to PostgreSQL.  It is deliberately
    private: callers must use :class:`PostgresIncrementalWriterRepository` so
    the schema/search-path and fail-closed connection contract remain fixed.
    """

    _QMARK = re.compile(r"\?")

    def __init__(self, connection: psycopg.Connection[Any], *, schema: str = "workbench"):
        self._connection = connection
        self.schema = schema

    @classmethod
    def _translate(cls, query: str) -> str:
        return cls._QMARK.sub("%s", query)

    def execute(self, query: str, params: Any = ()) -> Any:
        cursor = self._connection.cursor()
        cursor.execute(self._translate(str(query)), params)
        return _PostgresCursor(cursor)

    def executemany(self, query: str, params_seq: Any) -> Any:
        cursor = self._connection.cursor()
        cursor.executemany(self._translate(str(query)), params_seq)
        return _PostgresCursor(cursor)

    def close(self) -> None:
        # An uncommitted transaction is intentionally rolled back.  The
        # coordinator issues COMMIT only after every writer and binding gate
        # succeeds, so a close on any error is fail-closed.
        if not self._connection.closed:
            self._connection.rollback()
            self._connection.close()


class _PostgresCursor:
    """Cursor proxy preserving DuckDB's JSON-as-text observation semantics."""

    def __init__(self, cursor: Any):
        self._cursor = cursor

    @property
    def description(self) -> Any:
        return self._cursor.description

    def _row(self, row: Any) -> Any:
        if row is None or not self._cursor.description:
            return row
        jsonb_indexes = {
            index for index, item in enumerate(self._cursor.description)
            if getattr(item, "type_code", None) in {114, 3802}
        }
        if not jsonb_indexes:
            return row
        values = list(row)
        for index in jsonb_indexes:
            value = values[index]
            if isinstance(value, (dict, list)):
                values[index] = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return tuple(values)

    def fetchone(self) -> Any:
        return self._row(self._cursor.fetchone())

    def fetchall(self) -> list[Any]:
        return [self._row(row) for row in self._cursor.fetchall()]

    def __getattr__(self, name: str) -> Any:
        return getattr(self._cursor, name)


class PostgresIncrementalWriterRepository:
    """PostgreSQL adapter for the incremental writer's transaction boundary.

    The adapter is opt-in until the complete domain-writer compatibility gate
    is passed.  It never falls back to a DuckDB file when PostgreSQL is
    unavailable.
    """

    def __init__(self, dsn: str | None = None, *, schema: str = "workbench"):
        self.dsn = dsn or os.environ.get("WORKBENCH_PG_DSN") or "host=127.0.0.1 port=5432 dbname=market_research user=postgres"
        self.schema = schema
        self.database_path = Path("__postgresql_incremental_backend__")

    @contextmanager
    def connect(self) -> Iterator[_PostgresIncrementalConnection]:
        connection = psycopg.connect(self.dsn)
        try:
            with connection.cursor() as cursor:
                cursor.execute("select set_config('statement_timeout', %s, false)", ("30s",))
                cursor.execute("set timezone = 'UTC'")
                cursor.execute("set search_path to workbench, public")
            connection.commit()
            yield _PostgresIncrementalConnection(connection, schema=self.schema)
        finally:
            if not connection.closed:
                connection.rollback()
                connection.close()


__all__ = [
    "IncrementalWriterRepository",
    "DuckDBIncrementalWriterRepository",
    "PostgresIncrementalWriterRepository",
]
