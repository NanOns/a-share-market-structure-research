"""Compatibility connection boundary for storage governance fallbacks."""
from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator, Protocol

import duckdb

from .config_store import default_database_path


class StorageConnectionRepository(Protocol):
    @contextmanager
    def connect(self, *, read_only: bool = False) -> Iterator[Any]: ...


class DuckDBStorageConnectionRepository:
    def __init__(self, root: str | Path, database_path: str | Path | None = None):
        root = Path(root).resolve()
        self.database_path = (
            Path(database_path).resolve()
            if database_path is not None
            else default_database_path(root)
        )

    @contextmanager
    def connect(self, *, read_only: bool = False) -> Iterator[duckdb.DuckDBPyConnection]:
        with duckdb.connect(str(self.database_path), read_only=read_only) as connection:
            yield connection


__all__ = ["StorageConnectionRepository", "DuckDBStorageConnectionRepository"]
