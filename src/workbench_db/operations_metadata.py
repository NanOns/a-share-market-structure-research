"""Operations-status metadata readers for DuckDB compatibility and PG cutover."""
from __future__ import annotations

from pathlib import Path
from typing import Protocol

import duckdb


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


__all__ = ["DuckDBOperationsMetadataReader", "OperationsMetadataReader"]
