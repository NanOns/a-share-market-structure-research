"""PostgreSQL repository boundary used during shadow reads and cutover.

The existing DuckDB repository remains the legacy/offline path until the
cutover gate passes.  This adapter intentionally exposes parameterized reads
and transaction boundaries without leaking PostgreSQL SQL into HTTP handlers.
"""
from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Any, Iterator, Sequence

import psycopg
from psycopg import sql


DEFAULT_DSN = "host=127.0.0.1 port=5432 dbname=market_research user=postgres"


class PostgresRepository:
    def __init__(self, dsn: str | None = None, *, schema: str = "workbench", statement_timeout_ms: int = 30_000):
        self.dsn = dsn or os.environ.get("WORKBENCH_PG_DSN") or DEFAULT_DSN
        self.schema = schema
        self.statement_timeout_ms = statement_timeout_ms
        self.connection: psycopg.Connection[Any] | None = None

    def open(self) -> "PostgresRepository":
        self.connection = psycopg.connect(self.dsn)
        with self.connection.cursor() as cur:
            # SET does not accept a bind placeholder in PostgreSQL.  Use
            # set_config so the timeout remains parameterized and cannot be
            # changed by a DSN/identifier injection.
            cur.execute("select set_config('statement_timeout', %s, false)", (f"{self.statement_timeout_ms}ms",))
            cur.execute("set timezone = 'UTC'")
        self.connection.commit()
        return self

    def close(self) -> None:
        if self.connection is not None:
            self.connection.close()
        self.connection = None

    def __enter__(self) -> "PostgresRepository":
        return self.open()

    def __exit__(self, *_: object) -> None:
        self.close()

    @contextmanager
    def transaction(self) -> Iterator[psycopg.Connection[Any]]:
        if self.connection is None:
            raise RuntimeError("POSTGRES_REPOSITORY_NOT_OPEN")
        try:
            yield self.connection
            self.connection.commit()
        except Exception:
            self.connection.rollback()
            raise

    def count(self, table: str) -> int:
        if self.connection is None:
            raise RuntimeError("POSTGRES_REPOSITORY_NOT_OPEN")
        with self.connection.cursor() as cur:
            cur.execute(sql.SQL("select count(*) from {}.{}").format(sql.Identifier(self.schema), sql.Identifier(table)))
            return int(cur.fetchone()[0])

    def fetch(self, query: str, params: Sequence[Any] = ()) -> list[tuple[Any, ...]]:
        if self.connection is None:
            raise RuntimeError("POSTGRES_REPOSITORY_NOT_OPEN")
        with self.connection.cursor() as cur:
            cur.execute(query, params)
            return list(cur.fetchall())

    def table_counts(self, tables: Sequence[str]) -> dict[str, int]:
        return {table: self.count(table) for table in tables}

    def research_security_names(self, publication_id: str) -> dict[str, str]:
        """Read the registered V3.3 security-name projection for one publication.

        Bundle JSON remains an immutable managed artifact; PostgreSQL only
        supplies the relational name projection used to decorate the read
        model.  The publication key prevents a name from another snapshot
        being reused.
        """
        if self.connection is None:
            raise RuntimeError("POSTGRES_REPOSITORY_NOT_OPEN")
        query = sql.SQL(
            "select security_id,security_name from {schema}.stock_daily "
            "where publication_id=%s and security_name is not null"
        ).format(schema=sql.Identifier(self.schema))
        with self.connection.cursor() as cur:
            cur.execute(query, (publication_id,))
            return {str(security_id): str(name) for security_id, name in cur.fetchall()}

    def publication_heads(self, *, include_analysis: bool = False) -> dict[str, Any]:
        """Return the public publication head projection used by the API."""
        if self.connection is None:
            raise RuntimeError("POSTGRES_REPOSITORY_NOT_OPEN")
        query = sql.SQL(
            "select cast(h.trade_date as text),h.publication_id,p.revision,p.production_version "
            "from {schema}.publication_heads h join {schema}.publications p using(publication_id) "
            "where p.status='SUCCESS' and (p.production_version not like 'm4-%%' or exists "
            "(select 1 from {schema}.publication_analysis_snapshots a where a.publication_id=p.publication_id and a.domain='LOCAL_RECONSTRUCTED')) "
            "order by h.trade_date desc"
        ).format(schema=sql.Identifier(self.schema))
        with self.connection.cursor() as cur:
            cur.execute(query)
            rows = cur.fetchall()
        items: list[dict[str, Any]] = []
        for trade_date, publication_id, revision, production_version in rows:
            item: dict[str, Any] = {"trade_date": str(trade_date), "publication_id": str(publication_id)}
            if include_analysis:
                item.update({"revision": revision, "production_version": production_version})
            items.append(item)
        result: dict[str, Any] = {"items": items, "latest_publication_id": items[0]["publication_id"] if items else None}
        if include_analysis:
            result["api_contract"] = "WORKBENCH_PUBLICATIONS_API_V1"
        return result

    def sector_metadata(self, publication_id: str) -> list[dict[str, str]]:
        """Return the stable sector identity projection for one publication."""
        if self.connection is None:
            raise RuntimeError("POSTGRES_REPOSITORY_NOT_OPEN")
        query = sql.SQL("select sector_id,sector_name,sector_type from {}.sector_daily where publication_id=%s order by sector_id").format(sql.Identifier(self.schema))
        with self.connection.cursor() as cur:
            cur.execute(query, (publication_id,))
            return [{"sector_id": str(sector_id), "sector_name": str(sector_name or sector_id), "sector_type": str(sector_type or "LOCAL")} for sector_id, sector_name, sector_type in cur.fetchall()]
