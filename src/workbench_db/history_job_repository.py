"""Database connection boundary for the history-analysis job state machine."""
from __future__ import annotations

import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator, Protocol

import duckdb

from .config_store import default_database_path


class HistoryJobRepository(Protocol):
    @contextmanager
    def connect(self) -> Iterator[Any]: ...


class DuckDBHistoryJobRepository:
    """Compatibility adapter with bounded lock retry for local jobs."""

    def __init__(self, root: str | Path, database_path: str | Path | None = None):
        root = Path(root).resolve()
        self.database_path = (
            Path(database_path).resolve()
            if database_path is not None
            else default_database_path(root)
        )

    @contextmanager
    def connect(self) -> Iterator[duckdb.DuckDBPyConnection]:
        last_error: duckdb.IOException | None = None
        for _ in range(50):
            try:
                with duckdb.connect(str(self.database_path)) as connection:
                    yield connection
                return
            except duckdb.IOException as exc:
                last_error = exc
                time.sleep(0.02)
        assert last_error is not None
        raise last_error


__all__ = ["HistoryJobRepository", "DuckDBHistoryJobRepository"]
