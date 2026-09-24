"""Independent read-only check of the installed Focus PostgreSQL schema."""
from __future__ import annotations

import hashlib

import psycopg

from apply_focus_pg_schema_v1 import DDL_PATH, VERSION, _dsn


def main() -> int:
    checksum = hashlib.sha256(DDL_PATH.read_bytes()).hexdigest()
    with psycopg.connect(_dsn()) as pg:
        with pg.cursor() as cur:
            cur.execute("select checksum,status from workbench_meta.schema_migrations where version=%s", (VERSION,))
            ledger = cur.fetchone()
            cur.execute("""select count(*) from information_schema.tables
                           where table_schema='workbench' and table_name like 'focus_%%'""")
            tables = int(cur.fetchone()[0])
            cur.execute("""select count(*) from pg_constraint c
                           join pg_class t on t.oid=c.conrelid
                           join pg_namespace n on n.oid=t.relnamespace
                           where n.nspname='workbench' and t.relname like 'focus_%%'
                             and c.contype in ('p','u','f','c')""")
            constraints = int(cur.fetchone()[0])
            cur.execute("""select count(*) from pg_indexes
                           where schemaname='workbench' and tablename like 'focus_%%'""")
            indexes = int(cur.fetchone()[0])
            cur.execute("select count(*) from workbench.focus_runs")
            runs = int(cur.fetchone()[0])
            cur.execute("select count(*) from workbench.focus_trade_date_heads")
            heads = int(cur.fetchone()[0])
    # Additive Focus migrations may add tables/constraints while V1 stays intact.
    if ledger != (checksum, "COMPLETE") or tables < 14 or constraints < 68 or indexes < 18:
        raise RuntimeError("FOCUS_SCHEMA_INDEPENDENT_VERIFICATION_FAILED")
    print({"version": VERSION, "checksum": checksum, "tables": tables,
           "constraints": constraints, "indexes": indexes,
           "runs": runs, "heads": heads})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
