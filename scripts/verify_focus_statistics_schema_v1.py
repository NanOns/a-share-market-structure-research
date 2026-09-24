"""Read-only verification of the installed Focus statistics schema."""
from __future__ import annotations

import hashlib

import psycopg

from scripts.apply_focus_pg_schema_v1 import _dsn
from scripts.apply_focus_statistics_schema_v1 import DDL_PATH, TABLES, VERSION


def verify() -> dict[str, object]:
    checksum = hashlib.sha256(DDL_PATH.read_bytes()).hexdigest()
    with psycopg.connect(_dsn()) as pg:
        with pg.cursor() as cur:
            cur.execute("select checksum,status from workbench_meta.schema_migrations where version=%s",
                        (VERSION,))
            ledger = cur.fetchone()
            if ledger != (checksum, "COMPLETE"):
                raise RuntimeError("FOCUS_STATISTICS_SCHEMA_LEDGER_MISMATCH")
            cur.execute("select table_name from information_schema.tables "
                        "where table_schema='workbench' and table_name=any(%s)", (list(TABLES),))
            tables = tuple(sorted(row[0] for row in cur.fetchall()))
            if tables != tuple(sorted(TABLES)):
                raise RuntimeError("FOCUS_STATISTICS_SCHEMA_TABLES_MISSING")
            cur.execute("select count(*) from pg_constraint c join pg_class t on t.oid=c.conrelid "
                        "join pg_namespace n on n.oid=t.relnamespace where n.nspname='workbench' "
                        "and t.relname=any(%s) and c.contype in ('p','u','f','c')", (list(TABLES),))
            constraints = int(cur.fetchone()[0])
            cur.execute("select (select count(*) from workbench.focus_statistics_batches),"
                        "(select count(*) from workbench.focus_statistics_rows),"
                        "(select count(*) from workbench.focus_statistics_heads)")
            rows = cur.fetchone()
    return {"version": VERSION, "checksum": checksum, "tables": tables,
            "constraints": constraints,
            "row_counts": dict(zip(("batches", "groups", "heads"), rows)),
            "mode": "READ_ONLY_VERIFIED"}


if __name__ == "__main__":
    print(verify())
