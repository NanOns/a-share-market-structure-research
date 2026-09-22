"""Connection provider boundary for the HTTP/API layer."""
from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator, Protocol

import duckdb
import os
import psycopg


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


class PostgresDuckDBApiConnectionProvider:
    """Expose the PostgreSQL workbench schema through DuckDB's SQL surface.

    The HTTP API is still written against DuckDB's parameterized SQL contract.
    DuckDB's postgres_scanner lets us preserve that contract while the data is
    read from PostgreSQL.  Each request gets an isolated in-memory connection;
    no local DuckDB file is opened and no fallback to the old file is allowed.
    """

    def __init__(self, dsn: str | None = None, *, schema: str = "workbench"):
        self.dsn = dsn or os.environ.get("WORKBENCH_PG_DSN")
        if not self.dsn:
            raise ValueError("WORKBENCH_PG_DSN_REQUIRED")
        self.schema = schema

    def _open(self) -> duckdb.DuckDBPyConnection:
        connection = duckdb.connect(":memory:")
        try:
            connection.execute("INSTALL postgres_scanner")
            connection.execute("LOAD postgres_scanner")
            escaped = self.dsn.replace("'", "''")
            connection.execute(f"ATTACH '{escaped}' AS pg (TYPE POSTGRES, SCHEMA '{self.schema}')")
            with psycopg.connect(self.dsn) as pg:
                with pg.cursor() as cur:
                    cur.execute("select table_name from information_schema.tables where table_schema=%s and table_type='BASE TABLE' order by table_name", (self.schema,))
                    tables = cur.fetchall()
            for (table,) in tables:
                safe = str(table).replace('"', '""')
                connection.execute(f'create view "{safe}" as select * from pg."{safe}"')
            # The v2 compatibility/API readers still address the versioned
            # result domains through their historical ``*_result_daily``
            # relation names.  PostgreSQL stores the migrated physical rows
            # in ``*_result_rows`` and binds them to a slice through
            # ``analysis_slice_result_bindings``.  Expose the same stable
            # reader surface in this request-scoped DuckDB connection so the
            # legacy pages do not silently degrade (or 500) after cutover.
            # These are read-only views; no fallback to the shared DuckDB
            # catalog is permitted.
            compatibility_views = {
                "technical_result_daily": (
                    "technical_result_rows",
                    "security_id,trade_date,contract_id,price_basis,raw_close,adj_close,quote_ret1,raw_amount,raw_volume,"
                    "ma5,ma10,ma20,ma60,ret5,ret10,ret20,ret60,rs5,rs10,rs20,rs60,amount_ma5,amount_ma10,amount_ma20,"
                    "amount_ratio20,amount_vs_prior20,volume_vs_prior20,amount_class,ma_alignment,validity,quality_codes,basis_json",
                ),
                "strength_result_daily": (
                    "strength_result_rows",
                    "security_id,trade_date,contract_id,price_basis,ret5,ret10,ret20,ret60,rs5,rs10,rs20,rs60,"
                    "rps5,rps10,rps20,rps60,rps_valid_universe_count5,rps_valid_universe_count10,"
                    "rps_valid_universe_count20,rps_valid_universe_count60,quality_codes,basis_json",
                ),
                "high_result_daily": (
                    "high_result_rows",
                    "security_id,trade_date,window,contract_id,price_basis,prior_max_close,new_high,at_prior_high,streak,"
                    "is_left_censored,dist_prior_high,valid_n,quality_codes,basis_json",
                ),
                "historical_structure_result_daily": (
                    "structure_result_rows",
                    "security_id,trade_date,queue_name,hit,tier,source_class,research_band,queue_rank,tier_rank,transition,"
                    "structure_basis,contract_id,evidence,quality_codes",
                ),
                "structure_summary_result_daily": (
                    "structure_summary_result_rows",
                    "security_id,trade_date,queues_json,research_band,research_band_quality,unique_hit_count,queue_contract",
                ),
            }
            for view_name, (source_table, columns) in compatibility_views.items():
                if source_table in {str(table) for (table,) in tables} and "analysis_slice_result_bindings" in {str(table) for (table,) in tables}:
                    safe_view = view_name.replace('"', '""')
                    connection.execute(
                        f'create view "{safe_view}" as '
                        f'select b.slice_id,r.{columns.replace(",", ",r.")} '
                        f'from "analysis_slice_result_bindings" b '
                        f'join "{source_table}" r on r.result_object_id=b.result_object_id'
                    )
            return connection
        except Exception:
            connection.close()
            raise

    @contextmanager
    def connect(self, *, read_only: bool = False) -> Iterator[duckdb.DuckDBPyConnection]:
        connection = self._open()
        try:
            yield connection
        finally:
            connection.close()

    @contextmanager
    def memory(self) -> Iterator[duckdb.DuckDBPyConnection]:
        with duckdb.connect() as connection:
            yield connection


__all__ = ["ApiConnectionProvider", "DuckDBApiConnectionProvider", "PostgresDuckDBApiConnectionProvider"]
