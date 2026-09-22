"""Persistence boundaries for the one-click publication service.

The publisher still has a DuckDB compatibility implementation, but the
application service must not know how that repository is opened or how job
status is read.  PostgreSQL can be introduced by supplying implementations
of the two protocols without changing publication orchestration code.
"""
from __future__ import annotations

import json
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator, Protocol

import duckdb

from .config_store import default_database_path
from .repository import WorkbenchRepository


class PublicationRepositoryFactory(Protocol):
    @contextmanager
    def open(self, *, timeout_seconds: float = 15.0) -> Iterator[WorkbenchRepository]: ...


class DuckDBPublicationRepositoryFactory:
    """Compatibility factory for the current local publisher backend."""

    def __init__(self, root: str | Path, database_path: str | Path | None = None):
        self.root = Path(root).resolve()
        self.database_path = (
            Path(database_path).resolve()
            if database_path is not None
            else default_database_path(self.root)
        )

    @contextmanager
    def open(self, *, timeout_seconds: float = 15.0) -> Iterator[WorkbenchRepository]:
        deadline = time.monotonic() + timeout_seconds
        while True:
            repository = WorkbenchRepository(self.root, self.database_path)
            try:
                repository.open()
                try:
                    yield repository
                finally:
                    repository.close()
                return
            except duckdb.IOException as exc:
                message = str(exc).lower()
                lock_error = any(marker in message for marker in (
                    "another process", "used by another process", "cannot open file",
                    "being used", "process cannot access", "另一个程序", "进程正在使用",
                ))
                if not lock_error or time.monotonic() >= deadline:
                    raise
                time.sleep(0.2)


class PublicationStatusReader(Protocol):
    def read(self, job_id: str) -> dict[str, Any]: ...


class DuckDBPublicationStatusReader:
    """Read persisted job status without exposing DuckDB to the service."""

    def __init__(self, root: str | Path, database_path: str | Path | None = None):
        root = Path(root).resolve()
        self.database_path = (
            Path(database_path).resolve()
            if database_path is not None
            else default_database_path(root)
        )

    def read(self, job_id: str) -> dict[str, Any]:
        with duckdb.connect(str(self.database_path), read_only=True) as connection:
            row = connection.execute(
                "SELECT status,payload_json FROM jobs WHERE job_id=?", [job_id]
            ).fetchone()
            if not row:
                raise KeyError("JOB_NOT_FOUND")
            event = connection.execute(
                "SELECT payload_json,event_time_utc FROM job_events "
                "WHERE job_id=? ORDER BY attempt DESC,sequence DESC LIMIT 1",
                [job_id],
            ).fetchone()
        details = json.loads(row[1])
        return {
            "job_id": job_id,
            "status": row[0],
            "publication_id": details.get("publication_id"),
            "details": details,
            "progress": json.loads(event[0]) if event else {"status": row[0]},
            "updated_at_utc": event[1].isoformat() if event else None,
        }


__all__ = [
    "PublicationRepositoryFactory",
    "DuckDBPublicationRepositoryFactory",
    "PublicationStatusReader",
    "DuckDBPublicationStatusReader",
]
