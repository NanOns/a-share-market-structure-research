"""Install the additive FOCUS-05 statistics materialization schema."""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

import psycopg

from scripts.apply_focus_pg_schema_v1 import _dsn

ROOT = Path(__file__).resolve().parents[1]
DDL_PATH = ROOT / "src/workbench_db/focus_statistics_schema_v1.sql"
VERSION = "FOCUS_STATISTICS_MATERIALIZATION_V1"
TABLES = ("focus_statistics_batches", "focus_statistics_rows", "focus_statistics_heads")


def install(*, apply: bool) -> dict[str, object]:
    ddl = DDL_PATH.read_text("utf-8")
    checksum = hashlib.sha256(ddl.encode("utf-8")).hexdigest()
    with psycopg.connect(_dsn()) as pg:
        try:
            with pg.cursor() as cur:
                cur.execute("select pg_advisory_xact_lock(hashtext(%s))", (VERSION,))
                cur.execute("select to_regclass('workbench.focus_episode_outcomes'),"
                            "to_regclass('workbench.focus_outcome_heads'),"
                            "to_regclass('workbench_meta.schema_migrations')")
                if any(value is None for value in cur.fetchone()):
                    raise RuntimeError("FOCUS_OUTCOME_SCHEMA_REQUIRED")
                cur.execute("select checksum,status from workbench_meta.schema_migrations where version=%s",
                            (VERSION,))
                old = cur.fetchone()
                if old and old != (checksum, "COMPLETE"):
                    raise RuntimeError("FOCUS_STATISTICS_SCHEMA_LEDGER_CONFLICT")
                cur.execute(ddl)
                cur.execute("select table_name from information_schema.tables "
                            "where table_schema='workbench' and table_name=any(%s)", (list(TABLES),))
                tables = tuple(sorted(row[0] for row in cur.fetchall()))
                if tables != tuple(sorted(TABLES)):
                    raise RuntimeError("FOCUS_STATISTICS_SCHEMA_TABLES_MISSING")
                cur.execute("select count(*) from pg_constraint c join pg_class t on t.oid=c.conrelid "
                            "join pg_namespace n on n.oid=t.relnamespace where n.nspname='workbench' "
                            "and t.relname=any(%s) and c.contype in ('p','u','f','c')", (list(TABLES),))
                constraints = int(cur.fetchone()[0])
                if constraints < 15:
                    raise RuntimeError("FOCUS_STATISTICS_SCHEMA_CONSTRAINTS_MISSING")
                if apply and not old:
                    cur.execute("insert into workbench_meta.schema_migrations "
                                "(version,checksum,applied_at,status) values (%s,%s,now(),'COMPLETE')",
                                (VERSION, checksum))
            if apply:
                pg.commit()
            else:
                pg.rollback()
        except Exception:
            pg.rollback()
            raise
    return {"version": VERSION, "checksum": checksum,
            "mode": "APPLIED" if apply else "ROLLBACK_REHEARSAL",
            "tables": tables, "constraints": constraints}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    print(install(apply=parser.parse_args().apply))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
