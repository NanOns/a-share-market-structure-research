"""Explicit backend provider used by the precutover adapter harness."""
from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Callable, Iterator, Literal

import duckdb
import psycopg

from .postgres_repository import PostgresRepository
from .read_repository import DuckDBReadRepository, PublicationReadRepository


BackendName = Literal["duckdb", "postgresql"]


class RepositoryUnavailable(RuntimeError):
    """The selected backend could not be opened; no fallback is permitted."""


class BackendRepositoryProvider:
    def __init__(self, *, backend: BackendName, duckdb_path: str | None = None, postgres_dsn: str | None = None):
        self.backend = backend
        self.duckdb_path = duckdb_path
        self.postgres_dsn = postgres_dsn

    @contextmanager
    def session(self) -> Iterator[PublicationReadRepository]:
        try:
            if self.backend == "duckdb":
                if not self.duckdb_path:
                    raise RepositoryUnavailable("DUCKDB_PATH_REQUIRED")
                with DuckDBReadRepository(self.duckdb_path) as repository:
                    yield repository
            elif self.backend == "postgresql":
                with PostgresRepository(self.postgres_dsn) as repository:
                    yield repository
            else:
                raise RepositoryUnavailable("BACKEND_UNSUPPORTED")
        except RepositoryUnavailable:
            raise
        except (psycopg.Error, duckdb.Error, OSError) as exc:
            raise RepositoryUnavailable(f"{self.backend.upper()}_UNAVAILABLE") from exc

    def read(self, operation: Callable[[PublicationReadRepository], Any]) -> Any:
        with self.session() as repository:
            return operation(repository)


class AdapterHttpGateway:
    """Map backend-open failures to the fail-closed 503 contract."""

    def __init__(self, provider: BackendRepositoryProvider):
        self.provider = provider

    def read(self, operation: Callable[[PublicationReadRepository], Any]) -> dict[str, Any]:
        try:
            return {"status": 200, "body": self.provider.read(operation)}
        except RepositoryUnavailable as exc:
            return {"status": 503, "body": {"code": "POSTGRES_UNAVAILABLE" if self.provider.backend == "postgresql" else "DUCKDB_UNAVAILABLE", "backend": self.provider.backend, "detail": str(exc)}}


__all__ = ["AdapterHttpGateway", "BackendRepositoryProvider", "RepositoryUnavailable"]
