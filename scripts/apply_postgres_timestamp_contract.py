"""Register timestamp semantics and safely promote explicit *_utc columns."""
from __future__ import annotations

import argparse
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import duckdb
import psycopg
from psycopg import sql


ROOT = Path(__file__).resolve().parents[1]


def qi(value: str) -> sql.Identifier:
    return sql.Identifier(value)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--source", default="runtime/postgres_migration/20260922/market_research.source.duckdb")
    p.add_argument("--dsn", default=None)
    p.add_argument("--apply", action="store_true")
    args = p.parse_args()
    if not args.apply:
        raise SystemExit("Refusing to change PostgreSQL without --apply")
    source = duckdb.connect(args.source, read_only=True)
    rows = source.execute("select table_name,column_name from information_schema.columns where table_schema='main' and data_type='TIMESTAMP' order by table_name,column_name").fetchall()
    dsn = args.dsn or os.environ.get("PG_DSN") or "host=127.0.0.1 port=5432 dbname=market_research user=postgres"
    now = datetime.now(timezone.utc)
    try:
        with psycopg.connect(dsn) as pg:
            with pg.cursor() as cur:
                cur.execute("""
                    create table if not exists workbench_meta.timestamp_semantics_catalog (
                        table_name text not null,
                        column_name text not null,
                        source_type text not null,
                        writer_semantics text not null,
                        semantic_timezone text,
                        target_type text not null,
                        transform_rule text not null,
                        status text not null,
                        reviewed_at timestamptz not null,
                        primary key (table_name,column_name)
                    )
                """)
            for table, column in rows:
                explicit_utc = str(column).lower().endswith("_utc")
                if explicit_utc:
                    with pg.cursor() as cur:
                        cur.execute(sql.SQL("alter table workbench.{} alter column {} type timestamptz using {} at time zone 'UTC'").format(qi(table), qi(column), qi(column)))
                    target_type = "timestamptz"
                    semantics = "UTC_INSTANT"
                    rule = "source TIMESTAMP interpreted as UTC wall value; promote with AT TIME ZONE UTC"
                    status = "APPLIED"
                else:
                    target_type = "timestamp without time zone"
                    semantics = "UNCONFIRMED_LOCAL_OR_UTC"
                    rule = "retain wall-clock type until writer and source contract review"
                    status = "PENDING_REVIEW"
                with pg.cursor() as cur:
                    cur.execute("""
                        insert into workbench_meta.timestamp_semantics_catalog
                        (table_name,column_name,source_type,writer_semantics,semantic_timezone,target_type,transform_rule,status,reviewed_at)
                        values (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                        on conflict (table_name,column_name) do update set target_type=excluded.target_type,semantic_timezone=excluded.semantic_timezone,transform_rule=excluded.transform_rule,status=excluded.status,reviewed_at=excluded.reviewed_at
                    """, (table, column, "DuckDB TIMESTAMP", semantics, "UTC" if explicit_utc else None, target_type, rule, status, now))
                pg.commit()
            print(f"TIMESTAMP_CONTRACT_COMPLETE total={len(rows)} applied_utc={sum(str(c).lower().endswith('_utc') for _,c in rows)} pending_review={sum(not str(c).lower().endswith('_utc') for _,c in rows)}")
    finally:
        source.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
