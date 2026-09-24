"""Independent read-only verifier of installed basket schema and ledger."""
from __future__ import annotations

import hashlib

import psycopg

from scripts.apply_focus_basket_schema_v1 import DDL_PATH, VERSION
from scripts.apply_focus_pg_schema_v1 import _dsn


def main() -> int:
    checksum = hashlib.sha256(DDL_PATH.read_bytes()).hexdigest()
    with psycopg.connect(_dsn()) as pg:
        with pg.transaction():
            pg.execute("set transaction read only")
            with pg.cursor() as cur:
                cur.execute("select checksum,status from workbench_meta.schema_migrations "
                            "where version=%s", (VERSION,))
                ledger = cur.fetchone()
                cur.execute("select count(*) from pg_constraint "
                            "where conrelid='workbench.focus_episode_baskets'::regclass "
                            "and contype in ('p','u','f','c')")
                constraints = int(cur.fetchone()[0])
                cur.execute("select count(*) from pg_indexes where schemaname='workbench' "
                            "and tablename='focus_episode_baskets'")
                indexes = int(cur.fetchone()[0])
                cur.execute("select count(*) from workbench.focus_episode_baskets")
                rows = int(cur.fetchone()[0])
    if ledger != (checksum, "COMPLETE") or constraints != 10 or indexes != 2:
        raise RuntimeError("FOCUS_BASKET_SCHEMA_VERIFICATION_FAILED")
    print({"version": VERSION, "checksum": checksum,
           "constraints": constraints, "indexes": indexes, "business_rows": rows})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
