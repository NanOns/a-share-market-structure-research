"""Read-only verification of the installed FOCUS-04 settlement schema."""
from __future__ import annotations

import hashlib

import psycopg

from scripts.apply_focus_outcomes_schema_v1 import DDL_PATH, VERSION
from scripts.apply_focus_pg_schema_v1 import _dsn


TABLES = ("focus_outcome_settlement_batches",
          "focus_outcome_settlement_tasks",
          "focus_episode_followup_events")


def verify() -> dict[str, object]:
    expected_checksum = hashlib.sha256(DDL_PATH.read_bytes()).hexdigest()
    with psycopg.connect(_dsn()) as pg:
        with pg.cursor() as cur:
            cur.execute("set transaction read only")
            cur.execute("select checksum,status from workbench_meta.schema_migrations "
                        "where version=%s", (VERSION,))
            ledger = cur.fetchone()
            cur.execute("select table_name from information_schema.tables "
                        "where table_schema='workbench' and table_name=any(%s)",
                        (list(TABLES),))
            tables = tuple(sorted(row[0] for row in cur.fetchall()))
            cur.execute("select count(*) from pg_constraint c "
                        "join pg_class t on t.oid=c.conrelid "
                        "join pg_namespace n on n.oid=t.relnamespace "
                        "where n.nspname='workbench' and t.relname=any(%s) "
                        "and c.contype in ('p','u','f','c')", (list(TABLES),))
            constraints = int(cur.fetchone()[0])
            cur.execute("select 'focus_outcome_settlement_batches',count(*) "
                        "from workbench.focus_outcome_settlement_batches union all "
                        "select 'focus_outcome_settlement_tasks',count(*) "
                        "from workbench.focus_outcome_settlement_tasks union all "
                        "select 'focus_episode_followup_events',count(*) "
                        "from workbench.focus_episode_followup_events")
            row_counts = dict(cur.fetchall())
    if ledger != (expected_checksum, "COMPLETE"):
        raise RuntimeError("FOCUS_OUTCOME_SCHEMA_LEDGER_MISMATCH")
    if tables != tuple(sorted(TABLES)) or constraints < 16:
        raise RuntimeError("FOCUS_OUTCOME_SCHEMA_SHAPE_MISMATCH")
    return {"version": VERSION, "checksum": expected_checksum,
            "tables": tables, "constraints": constraints,
            "row_counts": row_counts, "mode": "READ_ONLY_VERIFIED"}


if __name__ == "__main__":
    print(verify())
