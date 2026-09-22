"""Operations-status metadata readers for DuckDB compatibility and PG cutover."""
from __future__ import annotations

from pathlib import Path
from typing import Protocol

import duckdb
from psycopg import sql
from .postgres_repository import PostgresRepository


class OperationsMetadataReader(Protocol):
    def metadata_counts(self) -> dict[str, int]: ...


class DuckDBOperationsMetadataReader:
    def __init__(self, root: str | Path, database_path: str | Path | None = None):
        root = Path(root).resolve()
        self.database_path = Path(database_path).resolve() if database_path else root / "data/database/market_research.duckdb"

    def metadata_counts(self) -> dict[str, int]:
        with duckdb.connect(str(self.database_path), read_only=True) as connection:
            return {
                "active_jobs": int(connection.execute("SELECT count(*) FROM jobs WHERE status IN ('QUEUED','RUNNING','INTERRUPTED')").fetchone()[0]),
                "storage_objects": int(connection.execute("SELECT count(*) FROM storage_objects").fetchone()[0]),
                "backup_catalog": int(connection.execute("SELECT count(*) FROM backup_catalog").fetchone()[0]),
            }


class PostgresOperationsMetadataReader:
    """Read service-health counters from the PostgreSQL workbench schema."""

    def __init__(self, repository: PostgresRepository):
        self.repository = repository

    def metadata_counts(self) -> dict[str, int]:
        if self.repository.connection is None:
            raise RuntimeError("POSTGRES_REPOSITORY_NOT_OPEN")
        schema = sql.Identifier(self.repository.schema)
        with self.repository.connection.cursor() as cur:
            counts: dict[str, int] = {}
            cur.execute(sql.SQL("select count(*) from {}.jobs where status in ('QUEUED','RUNNING','INTERRUPTED')").format(schema))
            counts["active_jobs"] = int(cur.fetchone()[0])
            cur.execute(sql.SQL("select count(*) from {}.storage_objects").format(schema))
            counts["storage_objects"] = int(cur.fetchone()[0])
            cur.execute(sql.SQL("select count(*) from {}.backup_catalog").format(schema))
            counts["backup_catalog"] = int(cur.fetchone()[0])
        return counts


__all__ = ["DuckDBOperationsMetadataReader", "PostgresOperationsMetadataReader", "OperationsMetadataReader"]
