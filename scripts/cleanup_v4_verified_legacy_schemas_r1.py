"""Drop only fully migrated, enumerated V4 legacy schemas with RESTRICT."""
from __future__ import annotations

import argparse
import json
import sys

import psycopg
from psycopg import sql


def _expected():
    history = ("v4_history_80ef60f40eca6e6d", "v4_history_64d0f9c30983a3ac", "v4_history_dbe184da961f97b8")
    read_index = (
        "v4_read_index_80ef60f40eca6e6d", "v4_read_index_r2_80ef60f40eca6e6d",
        "v4_00bd3ea17fe4cd57d84f9171aa8e725fbd9edab55a754087aac5b2f5",
        "v4_65f092e59fec0d987186ef0b5f1b9018f0d20adb5e79c4ff8576a63b",
        "v4_96901ca1753536bec2e2767de6f018ceb6308dbde3826d5d13331b9c",
        "v4_b00d132ba317e5f34b85565c29c92cae40b5438cad5a96c5ac0b9966",
        "v4_f05334ead7664a2b939a283bb3ac15ed1200ea2138fa93ccd8cbb58c",
        "v4_fae10bdca7c337472de4a49557bb1d314a98d49ea5d2052b2cc35907",
    )
    journal = ("v4_journal_registry_0ce03c8f18ae940a", "v4_journal_registry_dbe184da961f97b8")
    owners = (
        ("research_priority", "v4_010ec70a0aec548ac90822657ab528c146dac69d2dba00efb2f65d4d"),
        ("research_priority", "v4_1d03238596d40b243bbe20251652a31daabf07f175664007bdde0dee"),
        ("research_priority", "v4_912533e33e54174e4d3b636c08236964ca679e2dc71050508f001860"),
        ("operational_risk", "v4_1d314c5c198c87e14096534bc6ec5b592ce101da01d4f62eab2a2496"),
        ("operational_risk", "v4_cd017ab98f5b3a4cbdfeaab0a98babd96f9565aad5cf7a0c6a0bc1c6"),
        ("operational_risk", "v4_d42d3617395cd804459ee5940b31590c74a69817a94daea159bbef4a"),
        ("sector_lifecycle", "v4_f8a7432ae9ae29f4a9fe737e204e8a5d0598f365d42a23f1379a665c"),
    )
    return {
        **{s: ("history", {"history", "history_versions"}) for s in history},
        **{s: ("read_index", {"read_items", "read_responses", "read_versions"}) for s in read_index},
        **{s: ("journal", {"journal_heads"}) for s in journal},
        **{s: ("owner", {"owner_payloads", "owner_versions"}) for fam, s in owners if fam != "sector_lifecycle"},
        **{s: ("owner", {"owner_rows", "owner_versions"}) for fam, s in owners if fam == "sector_lifecycle"},
        "v4_jobs_80ef60f40eca6e6d": ("jobs", {
            "scheduler_attempts", "scheduler_dispatch", "scheduler_policy", "scheduler_rearm",
            "source_probe_state", "update_events", "update_job_days", "update_job_progress", "update_jobs",
        }),
    }


def _receipt_count(pg, family: str, schema: str) -> int:
    table = {
        "history": "history_migration_map_r1",
        "read_index": "read_index_migration_map_r1",
        "journal": "journal_registry_migration_map_r1",
        "owner": "owner_schema_migration_map_r1",
        "jobs": "jobs_migration_map_r1",
    }[family]
    if family == "jobs":
        return 1 if pg.execute("SELECT 1 FROM v4.jobs_migration_map_r1 WHERE source_schema=%s AND verification->>'status'='VERIFIED'", (schema,)).fetchone() else 0
    return pg.execute(sql.SQL("SELECT count(*) FROM v4.{} WHERE source_schema=%s AND verification->>'status'='VERIFIED'").format(sql.Identifier(table)), (schema,)).fetchone()[0]


def _drop_schema_contents_restrict(pg, schema: str, tables: set[str]) -> None:
    # PostgreSQL DROP SCHEMA RESTRICT rejects even a schema containing only its
    # own relations. Drop its exact inventoried objects one by one, in FK order.
    pending = set(tables)
    while pending:
        referenced_by = {r[0] for r in pg.execute("""SELECT parent.relname
            FROM pg_constraint c JOIN pg_class child ON child.oid=c.conrelid
            JOIN pg_namespace child_ns ON child_ns.oid=child.relnamespace
            JOIN pg_class parent ON parent.oid=c.confrelid
            JOIN pg_namespace parent_ns ON parent_ns.oid=parent.relnamespace
            WHERE c.contype='f' AND child_ns.nspname=%s AND parent_ns.nspname=%s""", (schema, schema)).fetchall()}
        leaves = sorted(pending - referenced_by)
        if not leaves:
            raise RuntimeError(f"V4_LEGACY_SCHEMA_FK_CYCLE:{schema}")
        for table in leaves:
            pg.execute(sql.SQL("DROP TABLE {}.{} RESTRICT").format(sql.Identifier(schema), sql.Identifier(table)))
            pending.remove(table)
    routines = pg.execute("""SELECT p.proname,pg_get_function_identity_arguments(p.oid),p.prokind
        FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace WHERE n.nspname=%s ORDER BY 1,2""", (schema,)).fetchall()
    if any(kind != "f" or args for _, args, kind in routines):
        raise RuntimeError(f"V4_LEGACY_SCHEMA_UNSUPPORTED_ROUTINE_SIGNATURE:{schema}")
    for name, _, _ in routines:
        pg.execute(sql.SQL("DROP FUNCTION {}.{}() RESTRICT").format(
            sql.Identifier(schema), sql.Identifier(name)))
    pg.execute(sql.SQL("DROP SCHEMA {} RESTRICT").format(sql.Identifier(schema)))


def cleanup(dsn: str, *, apply: bool) -> dict:
    expected = _expected()
    results = []
    with psycopg.connect(dsn, connect_timeout=5) as pg:
        pg.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ" + (", READ WRITE" if apply else ", READ ONLY"))
        identity = pg.execute("SELECT current_database(),inet_server_addr()::text,inet_server_port() FROM pg_stat_activity WHERE pid=pg_backend_pid()").fetchone()
        if identity != ("market_research", "127.0.0.1/32", 5432):
            raise RuntimeError("V4_LEGACY_SCHEMA_CLEANUP_DATABASE_IDENTITY_MISMATCH")
        pg.execute("SET LOCAL statement_timeout='180s'")
        pg.execute("SET LOCAL lock_timeout='5s'")
        present = {r[0] for r in pg.execute("SELECT nspname FROM pg_namespace WHERE nspname LIKE 'v4\\_%' ESCAPE '\\'").fetchall()}
        for schema in sorted(present & expected.keys()):
            family, expected_tables = expected[schema]
            with pg.transaction():
                pg.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s,0))", ("V4_VERIFIED_SCHEMA_CLEANUP_R1:" + schema,))
                tables = {r[0] for r in pg.execute("SELECT tablename FROM pg_tables WHERE schemaname=%s", (schema,)).fetchall()}
                if tables != expected_tables:
                    raise RuntimeError(f"V4_LEGACY_SCHEMA_TABLE_SET_MISMATCH:{schema}:{sorted(tables)}")
                receipts = _receipt_count(pg, family, schema)
                if receipts < 1:
                    raise RuntimeError(f"V4_LEGACY_SCHEMA_VERIFIED_RECEIPTS_MISSING:{schema}")
                if family in ("history", "read_index", "journal", "owner"):
                    version_table = "history_versions" if family == "history" else "read_versions" if family == "read_index" else "journal_heads" if family == "journal" else "owner_versions"
                    source_count = pg.execute(sql.SQL("SELECT count(*) FROM {}.{}").format(sql.Identifier(schema), sql.Identifier(version_table))).fetchone()[0]
                    if source_count != receipts:
                        raise RuntimeError(f"V4_LEGACY_SCHEMA_RECEIPT_CARDINALITY_MISMATCH:{schema}:{source_count}:{receipts}")
                if family == "jobs":
                    expected_counts = {
                        "scheduler_attempts": 3, "scheduler_dispatch": 3, "scheduler_policy": 1,
                        "scheduler_rearm": 0, "source_probe_state": 3, "update_events": 406,
                        "update_job_days": 5, "update_job_progress": 2, "update_jobs": 4,
                    }
                    source_counts = {table: pg.execute(sql.SQL("SELECT count(*) FROM {}.{}").format(sql.Identifier(schema), sql.Identifier(table))).fetchone()[0] for table in sorted(tables)}
                    if source_counts != expected_counts:
                        raise RuntimeError("V4_LEGACY_JOBS_SOURCE_COUNTS_CHANGED")
                if apply:
                    _drop_schema_contents_restrict(pg, schema, tables)
                results.append({"schema": schema, "family": family, "tables": sorted(tables),
                                "verified_receipts": receipts,
                                "source_counts": source_counts if family == "jobs" else None,
                                "status": "DROP_RESTRICT_SUCCESS" if apply else "ELIGIBLE"})
    return {"status": "CLEANUP_APPLIED" if apply else "VERIFY_ONLY", "database": identity, "results": results}


def main() -> None:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--apply", action="store_true")
    mode.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    sys.path.insert(0, "src")
    from workbench_db.v4_native import configured_dsn
    print(json.dumps(cleanup(configured_dsn(), apply=args.apply), ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
