"""Restore the empty Focus schema from its versioned DDL in a rollback sandbox.

This checks DDL recoverability, table/constraint topology and current ledger.
It does not replace the PostgreSQL cluster's ordinary backup/restore process.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import psycopg

from apply_focus_pg_schema_v1 import DDL_PATH, VERSION, _dsn


SCRATCH = "focus_restore_probe"


def main() -> int:
    ddl = DDL_PATH.read_text("utf-8")
    checksum = hashlib.sha256(ddl.encode("utf-8")).hexdigest()
    scratch_ddl = ddl.replace("workbench.focus_", f"{SCRATCH}.focus_")
    if scratch_ddl == ddl:
        raise RuntimeError("FOCUS_SCHEMA_PREFIX_NOT_FOUND")
    with psycopg.connect(_dsn()) as pg:
        try:
            with pg.cursor() as cur:
                cur.execute("select pg_advisory_xact_lock(hashtext(%s))", ("FOCUS_RESTORE_DRILL",))
                cur.execute("select 1 from information_schema.schemata where schema_name=%s", (SCRATCH,))
                if cur.fetchone():
                    raise RuntimeError("FOCUS_RESTORE_SCRATCH_ALREADY_EXISTS")
                cur.execute(f"create schema {SCRATCH}")
                cur.execute(scratch_ddl)
                cur.execute("""select count(*) from information_schema.tables
                               where table_schema=%s and table_name like 'focus_%%'""", (SCRATCH,))
                restored_tables = int(cur.fetchone()[0])
                cur.execute("""select count(*) from pg_constraint c
                               join pg_class t on t.oid=c.conrelid
                               join pg_namespace n on n.oid=t.relnamespace
                               where n.nspname=%s and t.relname like 'focus_%%'
                                 and c.contype in ('p','u','f','c')""", (SCRATCH,))
                restored_constraints = int(cur.fetchone()[0])
                cur.execute("select checksum,status from workbench_meta.schema_migrations where version=%s", (VERSION,))
                ledger = cur.fetchone()
                if (restored_tables, restored_constraints) != (14, 68):
                    raise RuntimeError("FOCUS_RESTORE_TOPOLOGY_MISMATCH")
                if ledger and (ledger[0], ledger[1]) != (checksum, "COMPLETE"):
                    raise RuntimeError("FOCUS_RESTORE_LEDGER_MISMATCH")
            # The scratch schema and all its restored objects vanish together.
            pg.rollback()
        except Exception:
            pg.rollback()
            raise
    print({"version": VERSION, "checksum": checksum,
           "restored_tables": restored_tables,
           "restored_constraints": restored_constraints,
           "mode": "ROLLBACK_RESTORE_DRILL"})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
