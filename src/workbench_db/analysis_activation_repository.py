"""Backend boundary for historical analysis snapshot activation.

The activation service performs a multi-table transaction.  This module owns
only opening that transaction's database connection so a PostgreSQL
implementation can replace the DuckDB compatibility adapter without leaking
the physical backend into the service orchestration code.
"""
from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, Protocol, Any

import duckdb

from .config_store import default_database_path
from .postgres_repository import PostgresRepository


class AnalysisActivationRepository(Protocol):
    @contextmanager
    def connect(self) -> Iterator[Any]: ...


class DuckDBAnalysisActivationRepository:
    """Compatibility connection adapter used before the PG cutover."""

    def __init__(self, root: str | Path, database_path: str | Path | None = None):
        root = Path(root).resolve()
        self.database_path = (
            Path(database_path).resolve()
            if database_path is not None
            else default_database_path(root)
        )

    @contextmanager
    def connect(self) -> Iterator[duckdb.DuckDBPyConnection]:
        with duckdb.connect(str(self.database_path)) as connection:
            yield connection


class _PostgresActivationConnection:
    """Small SQL compatibility facade for the activation service.

    The service owns the multi-table transaction but uses DuckDB's ``?``
    placeholders.  This facade translates only placeholders and keeps all
    identifiers unqualified through a controlled schema search path.
    """

    def __init__(self, connection: Any):
        self.connection = connection

    def execute(self, query: str, params: Any = ()) -> Any:
        text = str(query).strip()
        lowered = text.lower()
        if lowered in {"begin transaction", "begin"}:
            self.connection.execute("BEGIN")
            return self.connection.cursor()
        if lowered == "commit":
            self.connection.commit()
            return self.connection.cursor()
        if lowered == "rollback":
            self.connection.rollback()
            return self.connection.cursor()
        cursor = self.connection.cursor()
        cursor.execute(text.replace("?", "%s"), tuple(params or ()))
        return cursor


class PostgresAnalysisActivationRepository:
    """PostgreSQL connection boundary for snapshot activation rehearsal."""

    def __init__(self, dsn: str | None = None, *, schema: str = "workbench"):
        self.dsn = dsn
        self.schema = schema
        self.database_path = None

    @contextmanager
    def connect(self) -> Iterator[_PostgresActivationConnection]:
        with PostgresRepository(self.dsn, schema=self.schema) as repository:
            if repository.connection is None:
                raise RuntimeError("POSTGRES_REPOSITORY_NOT_OPEN")
            with repository.connection.cursor() as cursor:
                cursor.execute("select set_config('search_path', %s, false)", (self.schema,))
            repository.connection.commit()
            yield _PostgresActivationConnection(repository.connection)


__all__ = ["AnalysisActivationRepository", "DuckDBAnalysisActivationRepository", "PostgresAnalysisActivationRepository"]
