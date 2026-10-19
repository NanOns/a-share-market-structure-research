"""Move small historical Jobs schema rows into fixed v4 archive tables."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys

import psycopg
from psycopg import sql
from psycopg.types.json import Jsonb

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


def digest_rows(rows: dict[str, dict]) -> str:
    h = hashlib.sha256()
    for key in sorted(rows):
        h.update(canonical({"source_pk": rows[key][0], "payload": rows[key][1]}))
        h.update(b"\n")
    return h.hexdigest()


def migrate(dsn: str) -> dict:
    summaries = []
    with psycopg.connect(dsn, connect_timeout=5) as pg:
        identity = pg.execute("""SELECT current_database(),inet_server_addr()::text,
            inet_server_port(),current_user""").fetchone()
        if identity[:3] != ("market_research", "127.0.0.1/32", 5432):
            raise RuntimeError("V4_LEGACY_JOBS_DATABASE_IDENTITY_MISMATCH")
        pg.execute("SET LOCAL statement_timeout='120s'")
        pg.execute("SET LOCAL lock_timeout='5s'")
        for source in SOURCES:
            if not re.fullmatch(r"v4_jobs_[0-9a-f]{16}", source):
                raise RuntimeError("V4_LEGACY_JOBS_SOURCE_NAME_INVALID")
            with pg.transaction():
                pg.execute("SELECT pg_advisory_xact_lock(hashtext(%s))",
                           ("V4_LEGACY_JOB_ARCHIVE_R1:" + source,))
                counts = {}
                digests = {}
                for table in TABLES:
                    if not pg.execute("SELECT to_regclass(%s)", (f"{source}.{table}",)).fetchone()[0]:
                        continue
                    pk_cols = [r[0] for r in pg.execute("""SELECT a.attname
                        FROM pg_index i JOIN pg_attribute a ON a.attrelid=i.indrelid
                          AND a.attnum=ANY(i.indkey)
                        WHERE i.indrelid=%s::regclass AND i.indisprimary
                        ORDER BY array_position(i.indkey,a.attnum)""", (f"{source}.{table}",)).fetchall()]
                    if not pk_cols:
                        raise RuntimeError(f"V4_LEGACY_JOBS_PRIMARY_KEY_REQUIRED:{source}.{table}")
                    pk_expr = sql.SQL("jsonb_build_object({})").format(sql.SQL(",").join(
                        sql.SQL("{},to_jsonb(t.{})").format(sql.Literal(col), sql.Identifier(col))
                        for col in pk_cols))
                    source_rel = sql.SQL("{}.{}").format(sql.Identifier(source), sql.Identifier(table))
                    source_rows = pg.execute(sql.SQL("SELECT to_jsonb(t),{} FROM {} t").format(pk_expr, source_rel)).fetchall()
                    source_map = {canonical(pk).decode(): (pk, payload) for payload, pk in source_rows}
                    if len(source_map) != len(source_rows):
                        raise RuntimeError(f"V4_LEGACY_JOBS_SOURCE_PK_COLLISION:{source}.{table}")
                    for pk, payload in source_map.values():
                        row_sha = hashlib.sha256(canonical(payload)).hexdigest()
                        pg.execute("""INSERT INTO v4.jobs_legacy_rows_r1
                            (source_schema,source_table,source_pk,payload,row_sha256)
                            VALUES(%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING""",
                            (source, table, Jsonb(pk), Jsonb(payload), row_sha))
                    target_rows = pg.execute("""SELECT source_pk,payload,row_sha256
                        FROM v4.jobs_legacy_rows_r1 WHERE source_schema=%s AND source_table=%s""",
                        (source, table)).fetchall()
                    target_map = {canonical(pk).decode(): (pk, payload) for pk, payload, _sha in target_rows}
                    if source_map != target_map or len(source_map) != len(target_map):
                        raise RuntimeError(f"V4_LEGACY_JOBS_PARITY_FAILED:{source}.{table}")
                    for _pk, payload, row_sha in target_rows:
                        if hashlib.sha256(canonical(payload)).hexdigest() != row_sha:
                            raise RuntimeError(f"V4_LEGACY_JOBS_ROW_DIGEST_FAILED:{source}.{table}")
                    counts[table] = len(source_map)
                    digests[table] = digest_rows(source_map)
                proof = {"status": "VERIFIED", "source_schema": source,
                         "target_relation": "v4.jobs_legacy_rows_r1",
                         "table_row_parity": True, "primary_keys_preserved": True,
                         "payload_digests_verified": True}
                prior = pg.execute("""SELECT table_row_counts,table_sha256,verification
                    FROM v4.jobs_legacy_migration_map_r1 WHERE source_schema=%s""", (source,)).fetchone()
                if prior is None:
                    pg.execute("""INSERT INTO v4.jobs_legacy_migration_map_r1
                        (source_schema,table_row_counts,table_sha256,verification)
                        VALUES(%s,%s,%s,%s)""",
                        (source, Jsonb(counts), Jsonb(digests), Jsonb(proof)))
                elif prior[0] != counts or prior[1] != digests or prior[2] != proof:
                    raise RuntimeError(f"V4_LEGACY_JOBS_MIGRATION_MAP_CONFLICT:{source}")
                summaries.append({"source_schema": source, "row_counts": counts,
                                  "table_sha256": digests, "status": "VERIFIED"})
    return {"status": "MIGRATED_AND_VERIFIED", "database": identity,
            "target_schema": "v4", "sources": summaries}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    if not args.apply:
        raise SystemExit("Refusing database writes without --apply")
    sys.path.insert(0, "src")
    from workbench_db.v4_native import configured_dsn
    print(json.dumps(migrate(configured_dsn()), ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
