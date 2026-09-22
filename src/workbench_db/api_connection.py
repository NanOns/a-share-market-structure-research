"""Connection provider boundary for the HTTP/API layer."""
from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator, Protocol

import duckdb


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


__all__ = ["ApiConnectionProvider", "DuckDBApiConnectionProvider"]
