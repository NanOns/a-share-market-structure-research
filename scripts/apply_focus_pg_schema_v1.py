"""Install FOCUS_PG_SCHEMA_V1 after the accepted PostgreSQL migration.

Default is a rollback-only DDL rehearsal. Pass --apply to commit. Neither mode
prints credentials or reads TDX inputs.
"""
from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path

import psycopg


ROOT = Path(__file__).resolve().parents[1]
DDL_PATH = ROOT / "src/workbench_db/focus_schema_v1.sql"
VERSION = "FOCUS_PG_SCHEMA_V1"


def _dsn() -> str:
    value = os.environ.get("WORKBENCH_PG_DSN")
    local = ROOT / "config/.env"
    if not value and local.is_file():
        for line in local.read_text("utf-8").splitlines():
            key, sep, val = line.partition("=")
            if sep and key.strip() == "WORKBENCH_PG_DSN":
                value = val.strip().strip('"').strip("'")
                break
    if not value:
        raise RuntimeError("WORKBENCH_PG_DSN_REQUIRED")
    return value


def install(*, apply: bool) -> dict[str, object]:
    ddl = DDL_PATH.read_text("utf-8")
    checksum = hashlib.sha256(ddl.encode("utf-8")).hexdigest()
    with psycopg.connect(_dsn()) as pg:
        try:
            with pg.cursor() as cur:
                cur.execute("select pg_advisory_xact_lock(hashtext(%s))", (VERSION,))
                cur.execute("select 1 from information_schema.schemata where schema_name='workbench'")
                if not cur.fetchone():
                    raise RuntimeError("WORKBENCH_SCHEMA_MISSING")
                cur.execute("select checksum,status from workbench_meta.schema_migrations where version=%s", (VERSION,))
                old = cur.fetchone()
                if old and (old[0] != checksum or old[1] != "COMPLETE"):
                    raise RuntimeError("FOCUS_SCHEMA_LEDGER_CONFLICT")
                cur.execute(ddl)
                cur.execute("""select count(*) from information_schema.tables
                               where table_schema='workbench' and table_name like 'focus_%'""")
                count = int(cur.fetchone()[0])
                if count != 14:
                    raise RuntimeError(f"FOCUS_SCHEMA_TABLE_COUNT_MISMATCH:{count}")
                cur.execute("""select count(*) from pg_constraint c
                               join pg_class t on t.oid=c.conrelid
                               join pg_namespace n on n.oid=t.relnamespace
                               where n.nspname='workbench' and t.relname like 'focus_%'
                                 and c.contype in ('p','u','f','c')""")
                constraints = int(cur.fetchone()[0])
                if constraints < 45:
                    raise RuntimeError(f"FOCUS_SCHEMA_CONSTRAINT_COUNT_LOW:{constraints}")
                if apply and not old:
                    cur.execute("""insert into workbench_meta.schema_migrations
                                   (version,checksum,applied_at,status)
                                   values (%s,%s,now(),'COMPLETE')""", (VERSION, checksum))
            if apply:
                pg.commit()
            else:
                pg.rollback()
        except Exception:
            pg.rollback()
            raise
    return {"version": VERSION, "checksum": checksum,
            "mode": "APPLIED" if apply else "ROLLBACK_REHEARSAL",
            "focus_tables": count, "constraints": constraints}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    print(install(apply=args.apply))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
