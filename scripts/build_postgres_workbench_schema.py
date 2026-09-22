"""Build the first formal PostgreSQL schema from the verified legacy copy.

The ``legacy`` schema is immutable migration evidence.  This script creates
the independently versioned ``workbench`` schema, copies data inside
PostgreSQL, then restores source constraints in dependency-safe phases.
"""
from __future__ import annotations

import argparse
import os
from datetime import datetime, timezone
from typing import Any

import duckdb
import psycopg
from psycopg import sql


def qi(value: str) -> sql.Identifier:
    return sql.Identifier(value)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--source", default="runtime/postgres_migration/20260922/market_research.source.duckdb")
    p.add_argument("--dsn", default=None)
    p.add_argument("--schema", default="workbench")
    p.add_argument("--meta-schema", default="workbench_meta")
    p.add_argument("--apply", action="store_true", help="perform the schema build")
    return p.parse_args()


def table_names(source: duckdb.DuckDBPyConnection) -> list[str]:
    return [r[0] for r in source.execute("select table_name from information_schema.tables where table_schema='main' and table_type='BASE TABLE' order by table_name").fetchall()]


def constraint_rows(source: duckdb.DuckDBPyConnection) -> list[dict[str, Any]]:
    rows = source.execute(
        """
        select table_name, constraint_type, constraint_text, constraint_name,
               constraint_column_names, referenced_table, referenced_column_names
        from duckdb_constraints()
        where schema_name='main'
        order by table_name, constraint_index
        """
    ).fetchall()
    keys = ["table_name", "constraint_type", "constraint_text", "constraint_name", "columns", "referenced_table", "referenced_columns"]
    return [dict(zip(keys, row)) for row in rows]


def ensure_meta(pg: psycopg.Connection[Any], meta: str) -> None:
    with pg.cursor() as cur:
        cur.execute(sql.SQL("create schema if not exists {} ").format(qi(meta)))
        cur.execute(sql.SQL("""
            create table if not exists {}.schema_migrations (
                version text primary key,
                checksum text not null,
                applied_at timestamptz not null,
                status text not null
            )
        """).format(qi(meta)))
        cur.execute(sql.SQL("""
            create table if not exists {}.migration_table_catalog (
                run_id text not null,
                table_name text not null,
                source_schema text not null,
                target_schema text not null,
                migration_class text not null,
                source_row_count bigint not null,
                target_row_count bigint,
                source_pk text,
                constraint_count integer not null default 0,
                status text not null,
                completed_at timestamptz,
                primary key (run_id, table_name)
            )
        """).format(qi(meta)))
        cur.execute(sql.SQL("""
            create table if not exists {}.migration_table_attempts (
                run_id text not null,
                table_name text not null,
                phase text not null,
                status text not null,
                detail text,
                recorded_at timestamptz not null
            )
        """).format(qi(meta)))
        cur.execute(sql.SQL("""
            create table if not exists {}.migration_reference_checks (
                run_id text not null,
                object_name text not null,
                object_type text not null,
                status text not null,
                detail text,
                recorded_at timestamptz not null
            )
        """).format(qi(meta)))


def text_columns(source: duckdb.DuckDBPyConnection, table: str) -> list[str]:
    return [r[0] for r in source.execute("select column_name from information_schema.columns where table_schema='main' and table_name=? and is_nullable='NO' order by ordinal_position", [table]).fetchall()]


def source_count(source: duckdb.DuckDBPyConnection, table: str) -> int:
    return int(source.execute('select count(*) from main."' + table.replace('"', '""') + '"').fetchone()[0])


def main() -> int:
    args = parse_args()
    if not args.apply:
        raise SystemExit("Refusing to change PostgreSQL without --apply")
    source = duckdb.connect(args.source, read_only=True)
    tables = table_names(source)
    constraints = constraint_rows(source)
    by_table: dict[str, list[dict[str, Any]]] = {t: [] for t in tables}
    for row in constraints:
        by_table[row["table_name"]].append(row)
    dsn = args.dsn or os.environ.get("PG_DSN") or "host=127.0.0.1 port=5432 dbname=market_research user=postgres"
    run_id = datetime.now(timezone.utc).strftime("pgschema-%Y%m%dT%H%M%SZ")
    now = datetime.now(timezone.utc)
    try:
        with psycopg.connect(dsn) as pg:
            ensure_meta(pg, args.meta_schema)
            with pg.cursor() as cur:
                cur.execute(sql.SQL("create schema if not exists {} ").format(qi(args.schema)))
                cur.execute(sql.SQL("insert into {}.schema_migrations (version, checksum, applied_at, status) values (%s,%s,%s,%s) on conflict (version) do nothing").format(qi(args.meta_schema)), ("PG_SCHEMA_V1", "source-constraints-v1", now, "RUNNING"))
            pg.commit()

            # Phase 1: create tables and copy from the verified legacy schema.
            for table in tables:
                with pg.cursor() as cur:
                    cur.execute(sql.SQL("create table if not exists {}.{} (like {}.{} including defaults)").format(qi(args.schema), qi(table), qi("legacy"), qi(table)))
                    cur.execute(sql.SQL("truncate table {}.{} ").format(qi(args.schema), qi(table)))
                    cur.execute(sql.SQL("insert into {}.{} select * from {}.{}").format(qi(args.schema), qi(table), qi("legacy"), qi(table)))
                    count = int(cur.execute(sql.SQL("select count(*) from {}.{}").format(qi(args.schema), qi(table))).fetchone()[0])
                    pks = [r["constraint_text"] for r in by_table[table] if r["constraint_type"] == "PRIMARY KEY"]
                    cur.execute(sql.SQL("insert into {}.migration_table_catalog (run_id,table_name,source_schema,target_schema,migration_class,source_row_count,target_row_count,source_pk,constraint_count,status,completed_at) values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)").format(qi(args.meta_schema)), (run_id, table, "main", args.schema, "COPY_WITH_CAST", source_count(source, table), count, pks[0] if pks else None, len(by_table[table]), "DATA_COPIED", now))
                pg.commit()
                print(f"DATA_COPIED {table} rows={count}")

            # Phase 2: non-null, primary-key and unique constraints.
            for table in tables:
                for column in text_columns(source, table):
                    with pg.cursor() as cur:
                        cur.execute(sql.SQL("alter table {}.{} alter column {} set not null").format(qi(args.schema), qi(table), qi(column)))
                    pg.commit()
                for row in by_table[table]:
                    if row["constraint_type"] not in ("PRIMARY KEY", "UNIQUE"):
                        continue
                    kind = "primary key" if row["constraint_type"] == "PRIMARY KEY" else "unique"
                    cols = sql.SQL(", ").join(qi(str(c)) for c in row["columns"])
                    statement = sql.SQL("alter table {}.{} add constraint {} {} ({})").format(qi(args.schema), qi(table), qi(row["constraint_name"]), sql.SQL(kind), cols)
                    try:
                        with pg.cursor() as cur:
                            cur.execute(statement)
                            cur.execute(sql.SQL("insert into {}.migration_table_attempts values (%s,%s,%s,%s,%s,%s)").format(qi(args.meta_schema)), (run_id, table, "KEYS", "APPLIED", row["constraint_name"], datetime.now(timezone.utc)))
                        pg.commit()
                    except Exception as exc:
                        pg.rollback()
                        with pg.cursor() as cur:
                            cur.execute(sql.SQL("insert into {}.migration_table_attempts values (%s,%s,%s,%s,%s,%s)").format(qi(args.meta_schema)), (run_id, table, "KEYS", "FAILED", f"{row['constraint_name']}: {exc}", datetime.now(timezone.utc)))
                        pg.commit()
                        raise

            # Phase 3: checks and foreign keys after all tables and keys exist.
            for table in tables:
                for row in by_table[table]:
                    if row["constraint_type"] not in ("CHECK", "FOREIGN KEY"):
                        continue
                    if row["constraint_type"] == "CHECK":
                        definition = str(row["constraint_text"])[len("CHECK"):].strip()
                        definition = definition.replace("CAST('t' AS BOOLEAN)", "TRUE").replace("CAST('f' AS BOOLEAN)", "FALSE")
                        statement = sql.SQL("alter table {}.{} add constraint {} check {}").format(qi(args.schema), qi(table), qi(row["constraint_name"]), sql.SQL(definition))
                    else:
                        cols = sql.SQL(", ").join(qi(str(c)) for c in row["columns"])
                        refcols = sql.SQL(", ").join(qi(str(c)) for c in row["referenced_columns"])
                        statement = sql.SQL("alter table {}.{} add constraint {} foreign key ({}) references {}.{} ({})").format(qi(args.schema), qi(table), qi(row["constraint_name"]), cols, qi(args.schema), qi(str(row["referenced_table"])), refcols)
                    try:
                        with pg.cursor() as cur:
                            cur.execute(statement)
                            cur.execute(sql.SQL("insert into {}.migration_reference_checks values (%s,%s,%s,%s,%s,%s)").format(qi(args.meta_schema)), (run_id, row["constraint_name"], row["constraint_type"], "APPLIED", table, datetime.now(timezone.utc)))
                        pg.commit()
                    except Exception as exc:
                        pg.rollback()
                        with pg.cursor() as cur:
                            cur.execute(sql.SQL("insert into {}.migration_reference_checks values (%s,%s,%s,%s,%s,%s)").format(qi(args.meta_schema)), (run_id, row["constraint_name"], row["constraint_type"], "FAILED", f"{table}: {exc}", datetime.now(timezone.utc)))
                        pg.commit()
                        raise

            with pg.cursor() as cur:
                cur.execute(sql.SQL("update {}.schema_migrations set status='COMPLETE', applied_at=%s where version='PG_SCHEMA_V1'").format(qi(args.meta_schema)), (datetime.now(timezone.utc),))
            pg.commit()
            print(f"PG_SCHEMA_COMPLETE run_id={run_id} tables={len(tables)} constraints={len(constraints)}")
    finally:
        source.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
