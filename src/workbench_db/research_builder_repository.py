"""Connection boundary for the end-to-end research builder."""
from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator, Protocol

import duckdb


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


__all__ = ["ResearchBuilderRepository", "DuckDBResearchBuilderRepository"]
