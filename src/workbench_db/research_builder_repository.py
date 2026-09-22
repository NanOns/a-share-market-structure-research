"""Connection boundary for the end-to-end research builder."""
from __future__ import annotations

from contextlib import contextmanager
import os
from pathlib import Path
import re
from typing import Any, Iterator, Protocol

import duckdb
import psycopg

from .api_connection import PostgresDuckDBApiConnectionProvider


class ResearchBuilderRepository(Protocol):
    @contextmanager
    def connect(self) -> Iterator[Any]: ...


class DuckDBResearchBuilderRepository:
    """Compatibility adapter for the local-close DuckDB research builder."""

    def __init__(self, database_path: str | Path):
        self.database_path = Path(database_path).resolve()

    @contextmanager
    def connect(self) -> Iterator[duckdb.DuckDBPyConnection]:
        with duckdb.connect(str(self.database_path)) as connection:
            yield connection


class _PostgresResearchBuilderConnection:
    """Hybrid compute/read and PostgreSQL write connection.

    SELECT/Parquet queries stay in an isolated in-memory DuckDB connection;
    DDL/DML and transaction commands are sent to PostgreSQL.  This preserves
    DuckDB's analytical SQL surface without opening the shared database file,
    while research-run state and result rows commit in PostgreSQL.
    """

    _QMARK = re.compile(r"\?")

    def __init__(self, analytical: duckdb.DuckDBPyConnection, pg: psycopg.Connection[Any]):
        self._analytical = analytical
        self._pg = pg
        self._pg_in_transaction = False

    @classmethod
    def _translate(cls, query: str) -> str:
        return cls._QMARK.sub("%s", str(query))

    @staticmethod
    def _kind(query: str) -> str:
        stripped = str(query).lstrip()
        return (stripped.split(None, 1)[0] if stripped else "").upper()

    @staticmethod
    def _uses_research_state(query: str) -> bool:
        # ResearchRunStore reads must stay on psycopg.  DuckDB's timestamptz
        # conversion is optional in this runtime (and can require pytz),
        # while PostgreSQL is the system of record for these rows.
        return bool(re.search(r"\bresearch_[a-z0-9_]+\b", str(query), flags=re.IGNORECASE))

    def execute(self, query: str, params: Any = ()) -> Any:
        kind = self._kind(query)
        if kind in {"SELECT", "WITH", "PRAGMA", "EXPLAIN", "DESCRIBE", "SHOW"} and not self._uses_research_state(query):
            return self._analytical.execute(query, params)
        if kind == "BEGIN":
            self._pg.execute("BEGIN")
            self._pg_in_transaction = True
            return _PostgresResearchBuilderCursor(self._pg.cursor())
        if kind in {"COMMIT", "END"}:
            self._pg.commit()
            self._pg_in_transaction = False
            return _PostgresResearchBuilderCursor(self._pg.cursor())
        if kind == "ROLLBACK":
            self._pg.rollback()
            self._pg_in_transaction = False
            return _PostgresResearchBuilderCursor(self._pg.cursor())
        cursor = self._pg.cursor()
        cursor.execute(self._translate(query), params)
        if not self._pg_in_transaction:
            self._pg.commit()
        return _PostgresResearchBuilderCursor(cursor)

    def close(self) -> None:
        if not self._pg.closed:
            self._pg.rollback()
            self._pg.close()
        self._analytical.close()


class _PostgresResearchBuilderCursor:
    """DuckDB-shaped cursor proxy for research state reads."""

    def __init__(self, cursor: Any):
        self._cursor = cursor

    @property
    def description(self) -> Any:
        return self._cursor.description

    def _row(self, row: Any) -> Any:
        if row is None or not self._cursor.description:
            return row
        # Keep JSONB values text-compatible with the DuckDB repository.
        jsonb_indexes = {
            index for index, item in enumerate(self._cursor.description)
            if getattr(item, "type_code", None) in {114, 3802}
        }
        if not jsonb_indexes:
            return row
        import json
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

    def fetch_df(self) -> Any:
        import pandas as pd
        rows = self.fetchall()
        columns = [item.name for item in (self._cursor.description or ())]
        return pd.DataFrame(rows, columns=columns)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._cursor, name)


class PostgresResearchBuilderRepository:
    """Research builder repository with isolated DuckDB analytics and PG writes."""

    def __init__(self, dsn: str | None = None, *, schema: str = "workbench"):
        self.dsn = dsn or os.environ.get("WORKBENCH_PG_DSN")
        if not self.dsn:
            raise ValueError("WORKBENCH_PG_DSN_REQUIRED")
        self.schema = schema
        self.database_path = Path("__postgresql_research_builder_backend__")

    @contextmanager
    def connect(self) -> Iterator[_PostgresResearchBuilderConnection]:
        analytical_provider = PostgresDuckDBApiConnectionProvider(self.dsn, schema=self.schema)
        analytical = analytical_provider._open()
        pg = psycopg.connect(self.dsn)
        try:
            with pg.cursor() as cursor:
                cursor.execute("select set_config('statement_timeout', %s, false)", ("30s",))
                cursor.execute("set timezone = 'UTC'")
                cursor.execute("set search_path to workbench, public")
            pg.commit()
            yield _PostgresResearchBuilderConnection(analytical, pg)
        finally:
            if not pg.closed:
                pg.rollback()
                pg.close()
            analytical.close()


__all__ = ["ResearchBuilderRepository", "DuckDBResearchBuilderRepository", "PostgresResearchBuilderRepository"]
