"""Drop only archived Jobs schemas after exact row and digest verification."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys

import psycopg
from psycopg import sql

SOURCES = (
    "v4_jobs_2169e77ca47db3a6", "v4_jobs_230b6cd3c07bbaa6",
    "v4_jobs_30c6aa4db42f4b99", "v4_jobs_35279bfceb7647a2",
    "v4_jobs_64d0f9c30983a3ac", "v4_jobs_ac4c8f2d3782a2cb",
    "v4_jobs_b9c86bd811b1857f", "v4_jobs_fa56e0f43a4cbc3b",
)
TABLES = (
    "scheduler_policy", "update_jobs", "scheduler_dispatch",
    "scheduler_attempts", "scheduler_rearm", "update_job_days",
    "update_events", "update_job_progress", "source_probe_state",
)


def canonical(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, default=str).encode("utf-8")


def digest_rows(rows: dict[str, tuple[object, object]]) -> str:
    digest = hashlib.sha256()
    for key in sorted(rows):
        source_pk, payload = rows[key]
        digest.update(canonical({"source_pk": source_pk, "payload": payload}))
        digest.update(b"\n")
    return digest.hexdigest()


def cleanup(dsn: str) -> dict:
    outcomes = []
    with psycopg.connect(dsn, connect_timeout=5) as pg:
        identity = pg.execute("""SELECT current_database(),inet_server_addr()::text,
            inet_server_port(),current_user""").fetchone()
        if identity[:3] != ("market_research", "127.0.0.1/32", 5432):
            raise RuntimeError("V4_LEGACY_JOBS_CLEANUP_DATABASE_IDENTITY_MISMATCH")
        pg.execute("SET LOCAL statement_timeout='120s'")
        pg.execute("SET LOCAL lock_timeout='5s'")
        for source in SOURCES:
            if not re.fullmatch(r"v4_jobs_[0-9a-f]{16}", source):
                raise RuntimeError("V4_LEGACY_JOBS_CLEANUP_SOURCE_INVALID")
            with pg.transaction():
                if not pg.execute("SELECT to_regnamespace(%s)", (source,)).fetchone()[0]:
                    outcomes.append({"source_schema": source, "status": "ALREADY_ABSENT"})
                    continue
                receipt = pg.execute("""SELECT table_row_counts,table_sha256,verification
                    FROM v4.jobs_legacy_migration_map_r1 WHERE source_schema=%s""", (source,)).fetchone()
                if not receipt or receipt[2].get("status") != "VERIFIED":
                    raise RuntimeError(f"V4_LEGACY_JOBS_ARCHIVE_RECEIPT_REQUIRED:{source}")
                actual_objects = pg.execute("""SELECT c.relname,c.relkind
                    FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
                    WHERE n.nspname=%s ORDER BY c.relname""", (source,)).fetchall()
                table_names = [name for name, kind in actual_objects if kind == "r"]
                if any(kind not in ("r", "i", "S") for _name, kind in actual_objects):
                    raise RuntimeError(f"V4_LEGACY_JOBS_UNEXPECTED_RELATION_KIND:{source}")
                if set(table_names) - set(TABLES) or set(table_names) != set(receipt[0]):
                    raise RuntimeError(f"V4_LEGACY_JOBS_UNEXPECTED_TABLE:{source}")
                for table in table_names:
                    pk_cols = [r[0] for r in pg.execute("""SELECT a.attname
                        FROM pg_index i JOIN pg_attribute a ON a.attrelid=i.indrelid
                          AND a.attnum=ANY(i.indkey)
                        WHERE i.indrelid=%s::regclass AND i.indisprimary
                        ORDER BY array_position(i.indkey,a.attnum)""",
                        (f"{source}.{table}",)).fetchall()]
                    if not pk_cols:
                        raise RuntimeError(f"V4_LEGACY_JOBS_PRIMARY_KEY_REQUIRED:{source}.{table}")
                    pk_expr = sql.SQL("jsonb_build_object({})").format(sql.SQL(",").join(
                        sql.SQL("{},to_jsonb(t.{})").format(sql.Literal(col), sql.Identifier(col))
                        for col in pk_cols))
                    source_rel = sql.SQL("{}.{}").format(sql.Identifier(source), sql.Identifier(table))
                    source_rows = pg.execute(sql.SQL("SELECT to_jsonb(t),{} FROM {} t").format(
                        pk_expr, source_rel)).fetchall()
                    source_map = {canonical(pk).decode(): (pk, payload)
                                  for payload, pk in source_rows}
                    if len(source_map) != len(source_rows):
                        raise RuntimeError(f"V4_LEGACY_JOBS_SOURCE_PK_COLLISION:{source}.{table}")
                    stored_rows = pg.execute("""SELECT payload,row_sha256
                        FROM v4.jobs_legacy_rows_r1 WHERE source_schema=%s AND source_table=%s""",
                        (source, table)).fetchall()
                    archive_map = {}
                    for source_pk, payload, row_sha in pg.execute("""SELECT source_pk,payload,row_sha256
                        FROM v4.jobs_legacy_rows_r1 WHERE source_schema=%s AND source_table=%s""",
                        (source, table)).fetchall():
                        key = canonical(source_pk).decode()
                        archive_map[key] = (source_pk, payload)
                        if hashlib.sha256(canonical(payload)).hexdigest() != row_sha.strip():
                            raise RuntimeError(f"V4_LEGACY_JOBS_ARCHIVE_DIGEST_FAILED:{source}.{table}")
                    expected_count = receipt[0][table]
                    if (len(source_map) != expected_count or len(archive_map) != expected_count
                            or source_map != archive_map
                            or digest_rows(source_map) != receipt[1].get(table)
                            or digest_rows(archive_map) != receipt[1].get(table) or any(
                            hashlib.sha256(canonical(payload)).hexdigest() != row_sha
                            for payload, row_sha in stored_rows)):
                        raise RuntimeError(f"V4_LEGACY_JOBS_ARCHIVE_DIGEST_FAILED:{source}.{table}")
                for table in table_names:
                    pg.execute(sql.SQL("DROP TABLE {}.{} RESTRICT").format(
                        sql.Identifier(source), sql.Identifier(table)))
                routines = pg.execute("""SELECT p.proname,pg_get_function_identity_arguments(p.oid),p.prokind
                    FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace
                    WHERE n.nspname=%s ORDER BY p.proname""", (source,)).fetchall()
                if routines != [("reject_job_history_mutation", "", "f")]:
                    raise RuntimeError(f"V4_LEGACY_JOBS_UNEXPECTED_ROUTINES:{source}")
                pg.execute(sql.SQL("DROP FUNCTION {}.reject_job_history_mutation() RESTRICT")
                           .format(sql.Identifier(source)))
                pg.execute(sql.SQL("DROP SCHEMA {} RESTRICT").format(sql.Identifier(source)))
                outcomes.append({"source_schema": source, "status": "DROP_RESTRICT_SUCCESS",
                                 "tables_archived": len(table_names),
                                 "table_row_counts": receipt[0]})
    return {"database": identity, "status": "CLEANED", "schemas": outcomes}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    if not args.apply:
        raise SystemExit("Refusing database writes without --apply")
    sys.path.insert(0, "src")
    from workbench_db.v4_native import configured_dsn
    print(json.dumps(cleanup(configured_dsn()), ensure_ascii=False, sort_keys=True, default=str))


if __name__ == "__main__":
    main()
