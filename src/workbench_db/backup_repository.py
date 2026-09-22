"""Database connection boundary for offline backup and restore operations."""
from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator, Protocol

import duckdb


class BackupRepository(Protocol):
    @contextmanager
    def connect(self, path: str | Path | None = None, *, read_only: bool = False) -> Iterator[Any]: ...

    @contextmanager
    def memory(self) -> Iterator[Any]: ...


class DuckDBBackupRepository:
    """Compatibility adapter; physical copy policy remains in BackupService."""

    def __init__(self, database_path: str | Path):
        self.database_path = Path(database_path).resolve()

    @contextmanager
    def connect(self, path: str | Path | None = None, *, read_only: bool = False) -> Iterator[duckdb.DuckDBPyConnection]:
        target = Path(path).resolve() if path is not None else self.database_path
        with duckdb.connect(str(target), read_only=read_only) as connection:
            yield connection

    @contextmanager
    def memory(self) -> Iterator[duckdb.DuckDBPyConnection]:
        with duckdb.connect() as connection:
            yield connection


__all__ = ["BackupRepository", "DuckDBBackupRepository"]
