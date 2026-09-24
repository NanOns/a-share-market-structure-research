"""Read-only verification of the installed FOCUS target audit schema."""
from __future__ import annotations

import hashlib

import psycopg

from scripts.apply_focus_pg_schema_v1 import _dsn
from scripts.apply_focus_target_audit_schema_v1 import DDL_PATH, VERSION


def verify() -> dict[str, object]:
    checksum = hashlib.sha256(DDL_PATH.read_bytes()).hexdigest()
    with psycopg.connect(_dsn()) as pg:
        with pg.cursor() as cur:
            cur.execute("set transaction read only")
            cur.execute("select checksum,status from workbench_meta.schema_migrations "
                        "where version=%s", (VERSION,))
            ledger = cur.fetchone()
            cur.execute("select to_regclass('workbench.focus_target_data_audits')")
            table = cur.fetchone()[0]
            cur.execute("select count(*) from pg_constraint where "
                        "conrelid='workbench.focus_target_data_audits'::regclass "
                        "and contype in ('p','u','f','c')")
            constraints = int(cur.fetchone()[0])
            cur.execute("select count(*) from workbench.focus_target_data_audits")
            rows = int(cur.fetchone()[0])
    if ledger != (checksum, "COMPLETE") or table is None or constraints < 9:
        raise RuntimeError("FOCUS_TARGET_AUDIT_SCHEMA_SHAPE_MISMATCH")
    return {"version": VERSION, "checksum": checksum,
            "table": str(table), "constraints": constraints,
            "row_count": rows, "mode": "READ_ONLY_VERIFIED"}


if __name__ == "__main__":
    print(verify())
