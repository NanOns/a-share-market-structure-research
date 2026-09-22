"""Copy the frozen DuckDB snapshot into a PostgreSQL legacy schema.

This is the first migration pass.  It deliberately preserves source table and
column names in ``legacy`` and does not pretend that the legacy copy is the
final application schema.  The source must be a frozen read-only snapshot and
the target credentials are supplied through the environment (PGPASSWORD or a
full PG* connection set); no secret is accepted on the command line.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import duckdb
import psycopg
from psycopg import sql


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT / "runtime/postgres_migration/20260922/market_research.source.duckdb"


def qident(value: str) -> sql.Identifier:
    return sql.Identifier(value)


def duck_ident(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def pg_type(duck_type: str) -> str:
    t = duck_type.upper()
    if t == "BIGINT":
        return "bigint"
    if t == "INTEGER":
        return "integer"
    if t == "DOUBLE":
        return "double precision"
    if t == "BOOLEAN":
        return "boolean"
    if t == "DATE":
        return "date"
    if t == "TIMESTAMP":
        return "timestamp without time zone"
    if t == "JSON":
        return "jsonb"
    if t.startswith("DECIMAL("):
        return t.lower()
    return "text"


def placeholder(duck_type: str) -> sql.SQL:
    return sql.SQL("%s::jsonb") if duck_type.upper() == "JSON" else sql.SQL("%s")


def normalize_row(row: tuple[Any, ...], cols: list[tuple[str, str, bool]]) -> tuple[Any, ...]:
    """Make DuckDB JSON text acceptable to PostgreSQL jsonb.

    DuckDB permits non-standard JSON constants such as NaN and Infinity in
    some reconstructed result payloads.  PostgreSQL deliberately rejects
    those tokens, so the migration contract maps them to JSON null and keeps
    the original source digest in the table catalog.
    """
    values: list[Any] = []
    for value, (_, dtype, _) in zip(row, cols):
        if value is not None and dtype.upper() == "JSON":
            if isinstance(value, (dict, list)):
                value = json.dumps(value, ensure_ascii=False, allow_nan=False)
            else:
                parsed = json.loads(str(value), parse_constant=lambda _: None)
                value = json.dumps(parsed, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
        values.append(value)
    return tuple(values)


def source_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--schema", default="legacy")
    parser.add_argument("--dsn", default=None, help="optional libpq DSN without password")
    parser.add_argument("--table", action="append", dest="tables", help="repeat to migrate selected tables")
    parser.add_argument("--batch-size", type=int, default=2000)
    parser.add_argument("--plan", action="store_true", help="print the plan and do not write PostgreSQL")
    parser.add_argument("--resume", action="store_true", help="skip tables already marked COMPLETE")
    return parser.parse_args()


def columns(con: duckdb.DuckDBPyConnection, table: str) -> list[tuple[str, str, bool]]:
    return [
        (str(name), str(dtype), str(nullable).upper() == "YES")
        for name, dtype, nullable in con.execute(
            """
            select column_name, data_type, is_nullable
            from information_schema.columns
            where table_schema='main' and table_name=?
            order by ordinal_position
            """,
            [table],
        ).fetchall()
    ]


def table_names(con: duckdb.DuckDBPyConnection, selected: list[str] | None) -> list[str]:
    names = [row[0] for row in con.execute(
        "select table_name from information_schema.tables where table_schema='main' and table_type='BASE TABLE' order by table_name"
    ).fetchall()]
    if selected:
        missing = sorted(set(selected) - set(names))
        if missing:
            raise SystemExit(f"source tables not found: {', '.join(missing)}")
        return [name for name in names if name in set(selected)]
    return names


def ensure_catalog(pg: psycopg.Connection[Any], schema: str) -> None:
    with pg.cursor() as cur:
        cur.execute(sql.SQL("create schema if not exists {} ").format(qident(schema)))
        cur.execute(sql.SQL("""
            create table if not exists {}.migration_runs (
                run_id text primary key,
                source_path text not null,
                source_sha256 text not null,
                source_bytes bigint not null,
                started_at timestamptz not null,
                completed_at timestamptz,
                status text not null,
                table_count integer not null,
                notes text
            )
        """).format(qident(schema)))
        cur.execute(sql.SQL("""
            create table if not exists {}.table_runs (
                run_id text not null,
                table_name text not null,
                source_row_count bigint not null,
                target_row_count bigint,
                source_digest text,
                status text not null,
                completed_at timestamptz,
                primary key (run_id, table_name)
            )
        """).format(qident(schema)))


def load_table(
    source: duckdb.DuckDBPyConnection,
    pg: psycopg.Connection[Any],
    schema: str,
    table: str,
    run_id: str,
    batch_size: int,
) -> tuple[int, str]:
    cols = columns(source, table)
    if not cols:
        raise RuntimeError(f"no columns found for {table}")
    source_count = int(source.execute(f"select count(*) from main.{duck_ident(table)}").fetchone()[0])
    column_sql = sql.SQL(", ").join(
        sql.SQL("{} {}{}").format(qident(name), sql.SQL(pg_type(dtype)), sql.SQL("" if nullable else " not null"))
        for name, dtype, nullable in cols
    )
    names_sql = sql.SQL(", ").join(qident(name) for name, _, _ in cols)
    placeholders = sql.SQL(", ").join(placeholder(dtype) for _, dtype, _ in cols)
    insert_sql = sql.SQL("insert into {}.{} ({}) values ({})").format(
        qident(schema), qident(table), names_sql, placeholders
    )
    with pg.cursor() as cur:
        cur.execute(sql.SQL("drop table if exists {}.{} ").format(qident(schema), qident(table)))
        cur.execute(sql.SQL("create table {}.{} ({})").format(qident(schema), qident(table), column_sql))
        digest = hashlib.sha256()
        reader = source.execute(f"select * from main.{duck_ident(table)}")
        while True:
            rows = reader.fetchmany(batch_size)
            if not rows:
                break
            normalized = [normalize_row(row, cols) for row in rows]
            for row in normalized:
                digest.update(json.dumps(row, default=str, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
            cur.executemany(insert_sql, normalized)
        cur.execute(sql.SQL("select count(*) from {}.{}").format(qident(schema), qident(table)))
        target_count = int(cur.fetchone()[0])
        cur.execute(
            sql.SQL("insert into {}.table_runs (run_id, table_name, source_row_count, target_row_count, source_digest, status, completed_at) values (%s,%s,%s,%s,%s,%s,%s)").format(qident(schema)),
            (run_id, table, source_count, target_count, digest.hexdigest(), "COMPLETE", datetime.now(timezone.utc)),
        )
    return source_count, digest.hexdigest()


def main() -> int:
    args = parse_args()
    source_path = args.source.resolve()
    if not source_path.is_file():
        raise SystemExit(f"source snapshot not found: {source_path}")
    source = duckdb.connect(str(source_path), read_only=True)
    try:
        tables = table_names(source, args.tables)
        source_hash = source_sha256(source_path)
        print(json.dumps({"source": str(source_path), "sha256": source_hash, "bytes": source_path.stat().st_size, "tables": len(tables)}, ensure_ascii=False))
        for table in tables:
            count = source.execute(f"select count(*) from main.{duck_ident(table)}").fetchone()[0]
            print(f"PLAN {table} rows={count}")
        if args.plan:
            return 0
        dsn = args.dsn or os.environ.get("PG_DSN") or "host=127.0.0.1 port=5432 dbname=market_research user=postgres"
        run_id = datetime.now(timezone.utc).strftime("legacy-%Y%m%dT%H%M%SZ")
        with psycopg.connect(dsn) as pg:
            ensure_catalog(pg, args.schema)
            with pg.cursor() as cur:
                cur.execute(sql.SQL("insert into {}.migration_runs (run_id, source_path, source_sha256, source_bytes, started_at, status, table_count) values (%s,%s,%s,%s,%s,%s,%s)").format(qident(args.schema)), (run_id, str(source_path), source_hash, source_path.stat().st_size, datetime.now(timezone.utc), "RUNNING", len(tables)))
            pg.commit()
            for table in tables:
                if args.resume:
                    with pg.cursor() as cur:
                        cur.execute(sql.SQL("select status from {}.table_runs where run_id=%s and table_name=%s").format(qident(args.schema)), (run_id, table))
                        if cur.fetchone() == ("COMPLETE",):
                            continue
                count, digest = load_table(source, pg, args.schema, table, run_id, args.batch_size)
                pg.commit()
                print(f"COMPLETE {table} rows={count} digest={digest}")
            with pg.cursor() as cur:
                cur.execute(sql.SQL("update {}.migration_runs set completed_at=%s,status=%s where run_id=%s").format(qident(args.schema)), (datetime.now(timezone.utc), "COMPLETE", run_id))
            pg.commit()
            print(f"MIGRATION_COMPLETE run_id={run_id}")
    finally:
        source.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
