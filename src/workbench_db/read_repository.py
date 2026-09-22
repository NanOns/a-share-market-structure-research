"""Backend-neutral read repository boundary for pre-cutover projections."""
from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator, Protocol

import duckdb


class PublicationReadRepository(Protocol):
    """Stable read contract shared by DuckDB and PostgreSQL adapters."""

    def publication_heads(self, *, include_analysis: bool = False) -> dict[str, Any]: ...

    def research_security_names(self, publication_id: str) -> dict[str, str]: ...

    def sector_metadata(self, publication_id: str) -> list[dict[str, str]]: ...

    def relation_edges_for_publication(self, publication_id: str) -> list[tuple[Any, ...]]: ...


class DuckDBReadRepository:
    """Read-only implementation used for shadow comparisons and rollback."""

    def __init__(self, database_path: str | Path):
        self.database_path = Path(database_path).resolve()
        self.connection: duckdb.DuckDBPyConnection | None = None

    def open(self) -> "DuckDBReadRepository":
        self.connection = duckdb.connect(str(self.database_path), read_only=True)
        return self

    def close(self) -> None:
        if self.connection is not None:
            self.connection.close()
        self.connection = None

    def __enter__(self) -> "DuckDBReadRepository":
        return self.open()

    def __exit__(self, *_: object) -> None:
        self.close()

    @contextmanager
    def _cursor(self) -> Iterator[duckdb.DuckDBPyConnection]:
        if self.connection is None:
            raise RuntimeError("DUCKDB_READ_REPOSITORY_NOT_OPEN")
        yield self.connection

    def publication_heads(self, *, include_analysis: bool = False) -> dict[str, Any]:
        with self._cursor() as con:
            rows = con.execute(
                """select cast(h.trade_date as varchar),h.publication_id
                   from publication_heads h join publications p using(publication_id)
                  where p.status='SUCCESS'
                    and (p.production_version not like 'm4-%' or exists (
                        select 1 from publication_analysis_snapshots a
                         where a.publication_id=p.publication_id and a.domain='LOCAL_RECONSTRUCTED'))
                  order by h.trade_date desc"""
            ).fetchall()
        items = [{"trade_date": str(day), "publication_id": str(publication_id)} for day, publication_id in rows]
        if include_analysis:
            # Analysis enrichment is intentionally owned by the PG adapter in
            # the current shadow stage; callers must compare the basic head
            # projection before enabling the nested capability contract.
            for item in items:
                item["analysis_capabilities"] = None
        return {"items": items, "latest_publication_id": items[0]["publication_id"] if items else None}

    def research_security_names(self, publication_id: str) -> dict[str, str]:
        with self._cursor() as con:
            rows = con.execute(
                "select security_id,security_name from stock_daily where publication_id=? and security_name is not null",
                [publication_id],
            ).fetchall()
        return {str(security_id): str(name) for security_id, name in rows}

    def sector_metadata(self, publication_id: str) -> list[dict[str, str]]:
        with self._cursor() as con:
            rows = con.execute(
                "select sector_id,sector_name,sector_type from sector_daily where publication_id=? order by sector_id",
                [publication_id],
            ).fetchall()
        return [{"sector_id": str(sector_id), "sector_name": str(name or sector_id), "sector_type": str(kind or "LOCAL")} for sector_id, name, kind in rows]

    def relation_edges_for_publication(self, publication_id: str) -> list[tuple[Any, ...]]:
        with self._cursor() as con:
            return con.execute(
                """select b.publication_id,b.source_scope,b.revision_no,e.sector_id,e.security_id,e.source_kind,e.from_revision,e.to_revision
                     from relation_publication_bindings b join relation_edge_intervals e on e.source_scope=b.source_scope
                      and e.from_revision<=b.revision_no and (e.to_revision is null or b.revision_no<e.to_revision)
                    where b.publication_id=? order by b.source_scope,e.sector_id,e.security_id,e.source_kind""",
                [publication_id],
            ).fetchall()


__all__ = ["DuckDBReadRepository", "PublicationReadRepository"]
