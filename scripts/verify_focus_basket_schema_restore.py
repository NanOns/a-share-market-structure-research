"""Rollback-only scratch-schema restore drill for the additive basket DDL."""
from __future__ import annotations

import hashlib

import psycopg

from scripts.apply_focus_basket_schema_v1 import DDL_PATH, VERSION
from scripts.apply_focus_pg_schema_v1 import _dsn


SCRATCH = "focus_basket_restore_probe"


def main() -> int:
    ddl = DDL_PATH.read_text("utf-8")
    checksum = hashlib.sha256(ddl.encode("utf-8")).hexdigest()
    scratch_ddl = ddl.replace("workbench.focus_episode_baskets",
                              f"{SCRATCH}.focus_episode_baskets")
    with psycopg.connect(_dsn()) as pg:
        try:
            with pg.cursor() as cur:
                cur.execute("select pg_advisory_xact_lock(hashtext(%s))", (VERSION + "_RESTORE",))
                cur.execute("select 1 from information_schema.schemata where schema_name=%s", (SCRATCH,))
                if cur.fetchone():
                    raise RuntimeError("BASKET_RESTORE_SCRATCH_EXISTS")
                cur.execute(f"create schema {SCRATCH}")
                cur.execute(scratch_ddl)
                cur.execute("select count(*) from pg_constraint "
                            "where conrelid=%s::regclass and contype in ('p','u','f','c')",
                            (f"{SCRATCH}.focus_episode_baskets",))
                constraints = int(cur.fetchone()[0])
                if constraints != 10:
                    raise RuntimeError("BASKET_RESTORE_TOPOLOGY_MISMATCH")
                cur.execute("select checksum,status from workbench_meta.schema_migrations "
                            "where version=%s", (VERSION,))
                ledger = cur.fetchone()
                if ledger and ledger != (checksum, "COMPLETE"):
                    raise RuntimeError("BASKET_RESTORE_LEDGER_MISMATCH")
            pg.rollback()
        except Exception:
            pg.rollback()
            raise
    print({"version": VERSION, "checksum": checksum,
           "restored_constraints": constraints, "mode": "ROLLBACK_RESTORE_DRILL"})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
