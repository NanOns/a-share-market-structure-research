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


__all__ = ["AnalysisActivationRepository", "DuckDBAnalysisActivationRepository"]
