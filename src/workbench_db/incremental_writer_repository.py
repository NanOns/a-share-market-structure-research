"""Connection boundary for the incremental research build coordinator."""
from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator, Protocol

import duckdb


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


__all__ = ["IncrementalWriterRepository", "DuckDBIncrementalWriterRepository"]
