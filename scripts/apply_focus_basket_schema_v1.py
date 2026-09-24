"""Install the additive immutable Focus entry-basket schema.

Default mode rehearses and rolls back. --apply commits the DDL and ledger.
"""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

import psycopg

from scripts.apply_focus_pg_schema_v1 import _dsn


ROOT = Path(__file__).resolve().parents[1]
DDL_PATH = ROOT / "src/workbench_db/focus_basket_schema_v1.sql"
VERSION = "FOCUS_EPISODE_BASKET_V1"


def install(*, apply: bool) -> dict[str, object]:
    ddl = DDL_PATH.read_text("utf-8")
    checksum = hashlib.sha256(ddl.encode("utf-8")).hexdigest()
    with psycopg.connect(_dsn()) as pg:
        try:
            with pg.cursor() as cur:
                cur.execute("select pg_advisory_xact_lock(hashtext(%s))", (VERSION,))
                cur.execute("select to_regclass('workbench.focus_episodes'),"
                            "to_regclass('workbench.focus_runs')")
                if any(value is None for value in cur.fetchone()):
                    raise RuntimeError("FOCUS_BASE_SCHEMA_REQUIRED")
                cur.execute("select checksum,status from workbench_meta.schema_migrations "
                            "where version=%s", (VERSION,))
                old = cur.fetchone()
                if old and old != (checksum, "COMPLETE"):
                    raise RuntimeError("FOCUS_BASKET_LEDGER_CONFLICT")
                cur.execute(ddl)
                cur.execute("select count(*) from pg_constraint "
                            "where conrelid='workbench.focus_episode_baskets'::regclass "
                            "and contype in ('p','u','f','c')")
                constraints = int(cur.fetchone()[0])
                if constraints != 10:
                    raise RuntimeError(f"FOCUS_BASKET_CONSTRAINT_COUNT:{constraints}")
                if apply and not old:
                    cur.execute("insert into workbench_meta.schema_migrations "
                                "(version,checksum,applied_at,status) "
                                "values (%s,%s,now(),'COMPLETE')", (VERSION, checksum))
            if apply:
                pg.commit()
            else:
                pg.rollback()
        except Exception:
            pg.rollback()
            raise
    return {"version": VERSION, "checksum": checksum,
            "mode": "APPLIED" if apply else "ROLLBACK_REHEARSAL",
            "constraints": constraints}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    print(install(apply=args.apply))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
