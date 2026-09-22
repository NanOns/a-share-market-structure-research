"""Connection provider boundary for the HTTP/API layer."""
from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator, Protocol

import duckdb
import os
import psycopg


class ApiConnectionProvider(Protocol):
    @contextmanager
    def connect(self, *, read_only: bool = False) -> Iterator[Any]: ...

    @contextmanager
    def memory(self) -> Iterator[Any]: ...


class DuckDBApiConnectionProvider:
    def __init__(self, database_path: str | Path):
        self.database_path = Path(database_path).resolve()

    @contextmanager
    def connect(self, *, read_only: bool = False) -> Iterator[duckdb.DuckDBPyConnection]:
        with duckdb.connect(str(self.database_path), read_only=read_only) as connection:
            yield connection

    @contextmanager
    def memory(self) -> Iterator[duckdb.DuckDBPyConnection]:
        with duckdb.connect() as connection:
            yield connection


class PostgresDuckDBApiConnectionProvider:
    """Expose the PostgreSQL workbench schema through DuckDB's SQL surface.

    The HTTP API is still written against DuckDB's parameterized SQL contract.
    DuckDB's postgres_scanner lets us preserve that contract while the data is
    read from PostgreSQL.  Each request gets an isolated in-memory connection;
    no local DuckDB file is opened and no fallback to the old file is allowed.
    """

    def __init__(self, dsn: str | None = None, *, schema: str = "workbench"):
        self.dsn = dsn or os.environ.get("WORKBENCH_PG_DSN")
        if not self.dsn:
            raise ValueError("WORKBENCH_PG_DSN_REQUIRED")
        self.schema = schema

    def _open(self) -> duckdb.DuckDBPyConnection:
        connection = duckdb.connect(":memory:")
        try:
            connection.execute("INSTALL postgres_scanner")
            connection.execute("LOAD postgres_scanner")
            escaped = self.dsn.replace("'", "''")
            connection.execute(f"ATTACH '{escaped}' AS pg (TYPE POSTGRES, SCHEMA '{self.schema}')")
            with psycopg.connect(self.dsn) as pg:
                with pg.cursor() as cur:
                    cur.execute("select table_name from information_schema.tables where table_schema=%s and table_type='BASE TABLE' order by table_name", (self.schema,))
                    tables = cur.fetchall()
            for (table,) in tables:
                safe = str(table).replace('"', '""')
                connection.execute(f'create view "{safe}" as select * from pg."{safe}"')
            return connection
        except Exception:
            connection.close()
            raise

    @contextmanager
    def connect(self, *, read_only: bool = False) -> Iterator[duckdb.DuckDBPyConnection]:
        connection = self._open()
        try:
            yield connection
        finally:
            connection.close()

    @contextmanager
    def memory(self) -> Iterator[duckdb.DuckDBPyConnection]:
        with duckdb.connect() as connection:
            yield connection


__all__ = ["ApiConnectionProvider", "DuckDBApiConnectionProvider", "PostgresDuckDBApiConnectionProvider"]
