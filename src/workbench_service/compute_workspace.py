"""Isolated DuckDB workspace for the daily analytical pipeline.

The online system of record is PostgreSQL.  Analytical builders still use
DuckDB, but they operate on a per-pipeline cache instead of opening the shared
``market_research.duckdb`` file.  The cache is refreshed with the latest PG
publication head before a job starts and is retained only as compute state for
the next isolated job.
"""
from __future__ import annotations

from datetime import date
import json
import os
from pathlib import Path
import shutil
from typing import Any

import duckdb
import psycopg


RELATION_SCOPE = "TDX-MEMBERSHIP:direct-members-v3-v1"
PUBLICATION_CHILDREN = (
    "stock_daily", "sector_daily", "candidate_daily", "market_daily", "structure_details",
    "queue_memberships", "unified_board", "queue_rankings", "publication_artifacts", "publication_memberships",
)
RELATION_TABLES = (
    "relation_revisions", "relation_edge_intervals", "relation_observations",
    "sector_attribute_revisions", "sector_attribute_versions", "sector_attribute_revision_bindings",
)


def compute_database_path(root: str | Path) -> Path:
    return Path(root).resolve() / "runtime" / "compute" / "daily_pipeline.duckdb"


def _json_value(value: Any) -> Any:
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return value


def _pg_rows(pg: psycopg.Connection[Any], table: str, predicate: str, params: tuple[Any, ...]) -> tuple[list[str], list[tuple[Any, ...]]]:
    with pg.cursor() as cursor:
        cursor.execute(f'SELECT * FROM workbench."{table.replace(chr(34), chr(34) * 2)}" WHERE {predicate}', params)
        columns = [str(item.name) for item in (cursor.description or ())]
        rows = [tuple(_json_value(value) for value in row) for row in cursor.fetchall()]
    return columns, rows


def _duck_tables(connection: duckdb.DuckDBPyConnection) -> set[str]:
    return {str(row[0]) for row in connection.execute("select table_name from information_schema.tables where table_schema='main' and table_type='BASE TABLE'").fetchall()}


def _replace_rows(connection: duckdb.DuckDBPyConnection, tables: set[str], table: str, columns: list[str], rows: list[tuple[Any, ...]], predicate: str, predicate_params: list[Any]) -> None:
    if table not in tables:
        return
    safe_table = table.replace('"', '""')
    safe_columns = [f'"{column.replace(chr(34), chr(34) * 2)}"' for column in columns]
    if rows:
        placeholders = ",".join("?" for _ in columns)
        # Immutable publication rows are inserted idempotently.  The head is
        # the one mutable projection: update its trade-date row first, then
        # insert it if the date is new.  Avoid generic ``ON CONFLICT`` because
        # legacy DuckDB tables can expose more than one unique constraint.
        if table == "publication_heads" and "trade_date" in columns and "publication_id" in columns:
            trade_index = columns.index("trade_date")
            publication_index = columns.index("publication_id")
            for row in rows:
                connection.execute('UPDATE "publication_heads" SET "publication_id"=? WHERE "trade_date"=?', [row[publication_index], row[trade_index]])
        connection.executemany(f'INSERT OR IGNORE INTO "{safe_table}" ({",".join(safe_columns)}) VALUES ({placeholders})', rows)


def refresh_from_postgres(database: str | Path, dsn: str | None = None) -> dict[str, Any]:
    """Refresh the current publication and relation rows into an isolated DB."""
    database = Path(database).resolve()
    dsn = dsn or os.environ.get("WORKBENCH_PG_DSN")
    if not dsn:
        raise ValueError("WORKBENCH_PG_DSN_REQUIRED")
    with psycopg.connect(dsn) as pg:
        with pg.cursor() as cursor:
            cursor.execute("select h.publication_id,h.trade_date from workbench.publication_heads h join workbench.publications p using(publication_id) where p.status='SUCCESS' order by h.trade_date desc,p.revision desc limit 1")
            publication = cursor.fetchone()
            if not publication:
                raise RuntimeError("POSTGRES_PUBLICATION_HEAD_MISSING")
            publication_id, trade_date = str(publication[0]), publication[1]
            cursor.execute("select snapshot_id from workbench.publication_analysis_snapshots where publication_id=%s and domain='LOCAL_RECONSTRUCTED'", (publication_id,))
            snapshot = cursor.fetchone()
            snapshot_id = str(snapshot[0]) if snapshot else None
        with duckdb.connect(str(database)) as connection:
            tables = _duck_tables(connection)
            refreshed: dict[str, int] = {}

            def refresh(table: str, predicate: str, pg_params: tuple[Any, ...], duck_predicate: str, duck_params: list[Any]) -> None:
                if table not in tables:
                    return
                columns, rows = _pg_rows(pg, table, predicate, pg_params)
                _replace_rows(connection, tables, table, columns, rows, duck_predicate, duck_params)
                refreshed[table] = len(rows)

            refresh("publications", "publication_id=%s", (publication_id,), "publication_id=?", [publication_id])
            refresh("publication_heads", "trade_date=%s", (trade_date,), "trade_date=?", [trade_date])
            # Publication payload rows are already materialized in the
            # retained compute cache and are not inputs to M8/M10/P12.  Do
            # not copy potentially large queue/structure payloads on every
            # daily run; the PG publication remains the serving source.
            with pg.cursor() as cursor:
                cursor.execute("select observation_id,revision_no,attribute_version_id from workbench.relation_publication_bindings where publication_id=%s and source_scope=%s", (publication_id, RELATION_SCOPE))
                pg_relation = cursor.fetchone()
            local_relation = connection.execute("select observation_id,revision_no,attribute_version_id from relation_publication_bindings where publication_id=? and source_scope=?", [publication_id, RELATION_SCOPE]).fetchone() if "relation_publication_bindings" in tables else None
            refresh("relation_publication_bindings", "publication_id=%s", (publication_id,), "publication_id=?", [publication_id])
            # Relation edges are immutable by revision.  Avoid re-copying the
            # full edge set on every daily run when the publication points to
            # the same observation; copy them only when the binding changed.
            if pg_relation and tuple(str(value) if value is not None else None for value in pg_relation) != tuple(str(value) if value is not None else None for value in (local_relation or ())):
                observation_id, revision_no, attribute_version_id = pg_relation
                refresh("relation_revisions", "source_scope=%s and revision_no=%s", (RELATION_SCOPE, revision_no), "source_scope=? and revision_no=?", [RELATION_SCOPE, revision_no])
                refresh("relation_observations", "observation_id=%s", (observation_id,), "observation_id=?", [observation_id])
                refresh("relation_edge_intervals", "source_scope=%s and from_revision=%s", (RELATION_SCOPE, revision_no), "source_scope=? and from_revision=?", [RELATION_SCOPE, revision_no])
                refresh("sector_attribute_versions", "source_scope=%s and attribute_version_id=%s", (RELATION_SCOPE, attribute_version_id), "source_scope=? and attribute_version_id=?", [RELATION_SCOPE, attribute_version_id])
            if snapshot_id:
                refresh("analysis_snapshots", "snapshot_id=%s", (snapshot_id,), "snapshot_id=?", [snapshot_id])
                refresh("analysis_snapshot_hierarchy", "snapshot_id=%s", (snapshot_id,), "snapshot_id=?", [snapshot_id])
                refresh("analysis_snapshot_audit_status", "snapshot_id=%s", (snapshot_id,), "snapshot_id=?", [snapshot_id])
                refresh("analysis_snapshot_entries", "snapshot_id=%s", (snapshot_id,), "snapshot_id=?", [snapshot_id])
                refresh("publication_analysis_snapshots", "publication_id=%s and domain='LOCAL_RECONSTRUCTED'", (publication_id,), "publication_id=? and domain='LOCAL_RECONSTRUCTED'", [publication_id])
            connection.execute("CHECKPOINT")
    return {"database": str(database), "publication_id": publication_id, "trade_date": str(trade_date), "snapshot_id": snapshot_id, "refreshed_rows": refreshed}


def prepare_compute_workspace(root: str | Path, source_database: str | Path, dsn: str | None = None) -> tuple[Path, dict[str, Any]]:
    """Create/reuse an isolated cache and refresh its PG publication head."""
    root = Path(root).resolve()
    source_database = Path(source_database).resolve()
    target = compute_database_path(root)
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.is_file():
        if not source_database.is_file():
            raise FileNotFoundError(source_database)
        shutil.copy2(source_database, target)
    return target, refresh_from_postgres(target, dsn)


__all__ = ["compute_database_path", "prepare_compute_workspace", "refresh_from_postgres"]
