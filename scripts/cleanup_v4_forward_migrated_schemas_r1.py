"""Verify and retire only exact Forward source schemas already mapped to v4."""
from __future__ import annotations

import argparse
import json
import sys

import psycopg
from psycopg import sql

MAPPED = (
    "v4_forward_9c3fd7df8af41138",
    "v4_forward_d49f600857001503",
    "v4_forward_f17219af1df44bb8",
)
R7_EXCLUDED_SOURCE = "v4_forward_f17219af1df44bb8"


def cleanup(dsn: str, *, apply: bool) -> dict:
    results=[]
    with psycopg.connect(dsn,connect_timeout=5) as pg:
        pg.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ"+(", READ WRITE" if apply else ", READ ONLY"))
        identity=pg.execute("SELECT current_database(),inet_server_addr()::text,inet_server_port() FROM pg_stat_activity WHERE pid=pg_backend_pid()").fetchone()
        if identity != ("market_research","127.0.0.1/32",5432):
            raise RuntimeError("V4_FORWARD_CLEANUP_DATABASE_IDENTITY_MISMATCH")
        pg.execute("SET LOCAL statement_timeout='180s'");pg.execute("SET LOCAL lock_timeout='5s'")
        for source in MAPPED:
            with pg.transaction():
                pg.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s,0))",("V4_FORWARD_SCHEMA_CLEANUP_R1:"+source,))
                tables={r[0] for r in pg.execute("SELECT tablename FROM pg_tables WHERE schemaname=%s",(source,)).fetchall()}
                if tables!={"forward_facts","forward_migration"}:
                    raise RuntimeError("V4_FORWARD_SOURCE_TABLE_SET_MISMATCH:"+source)
                facts=pg.execute(sql.SQL("SELECT count(*) FROM {}.forward_facts").format(sql.Identifier(source))).fetchone()[0]
                mapped=pg.execute("SELECT count(*),count(*) FILTER(WHERE verification->>'status'='VERIFIED') FROM v4.forward_schema_migration_map_r1 WHERE source_schema=%s",(source,)).fetchone()
                r7_count=pg.execute(sql.SQL("SELECT count(*) FROM {}.forward_facts WHERE kind LIKE 'r7\\_%' ESCAPE '\\'").format(sql.Identifier(source))).fetchone()[0] if source == R7_EXCLUDED_SOURCE else 0
                target_mismatch=pg.execute(sql.SQL("""SELECT count(*) FROM {}.forward_facts s
                    LEFT JOIN v4.forward_schema_migration_map_r1 m ON m.source_schema=%s AND m.kind=s.kind AND m.fact_key=s.fact_key
                    LEFT JOIN v4.forward_facts t ON t.workspace_namespace=m.workspace_namespace AND t.kind=s.kind AND t.fact_key=s.fact_key
                    WHERE (m.fact_key IS NULL OR m.verification->>'status'<>'VERIFIED'
                       OR m.payload_sha256<>s.payload_sha256 OR m.source_sha256 IS DISTINCT FROM s.source_sha256
                       OR m.target_sha256<>s.payload_sha256 OR m.verification->>'source_ordinal'<>s.ordinal::text
                       OR t.fact_key IS NULL OR t.payload_sha256<>s.payload_sha256
                       OR t.source_sha256 IS DISTINCT FROM s.source_sha256)
                      AND s.kind NOT LIKE 'r7\\_%%' ESCAPE '\\'""").format(sql.Identifier(source)),(source,)).fetchone()[0]
                if (not facts or mapped[0] != facts-r7_count or mapped[1] != mapped[0] or target_mismatch):
                    raise RuntimeError(f"V4_FORWARD_SOURCE_NOT_FULLY_MIGRATED:{source}:{facts}:{mapped}:r7={r7_count}:{target_mismatch}")
                if r7_count:
                    r7_receipt=pg.execute("SELECT row_count,source_digest,target_digest FROM v4.forward_r7_migration_r1 WHERE source_schema=%s",(source,)).fetchone()
                    r7_mismatch=pg.execute(sql.SQL("""SELECT count(*) FROM {}.forward_facts s
                        LEFT JOIN v4.forward_r7_facts_r1 t ON t.origin_namespace='R7_ACTIVE' AND t.kind=s.kind AND t.fact_key=s.fact_key
                        WHERE s.kind LIKE 'r7\\_%' ESCAPE '\\'
                          AND (t.fact_key IS NULL OR t.payload<>s.payload OR t.payload_sha256<>s.payload_sha256
                               OR t.source_sha256 IS DISTINCT FROM s.source_sha256 OR t.ordinal<>s.ordinal)""").format(sql.Identifier(source))).fetchone()[0]
                    if not r7_receipt or r7_receipt[0] != r7_count or r7_receipt[1] != r7_receipt[2] or r7_mismatch:
                        raise RuntimeError(f"V4_FORWARD_R7_SOURCE_NOT_FULLY_MIGRATED:{source}:{r7_count}:{r7_receipt}:{r7_mismatch}")
                namespace_row=pg.execute("SELECT workspace_namespace FROM v4.forward_schema_migration_map_r1 WHERE source_schema=%s LIMIT 1",(source,)).fetchone()
                namespace=namespace_row[0] if namespace_row else "R7_ACTIVE"
                family="FORWARD_WORKSPACE_FACTS"
                migration=pg.execute(sql.SQL("SELECT receipt FROM {}.forward_migration WHERE singleton=1").format(sql.Identifier(source))).fetchone()
                if not migration or migration[0].get("contract_id")!="V4_FORWARD_PG_FACT_STORE_R1":
                    raise RuntimeError("V4_FORWARD_SOURCE_MIGRATION_DESCRIPTOR_MISSING:"+source)
                if apply:
                    pg.execute(sql.SQL("DROP TABLE {}.forward_facts RESTRICT").format(sql.Identifier(source)))
                    pg.execute(sql.SQL("DROP TABLE {}.forward_migration RESTRICT").format(sql.Identifier(source)))
                    routines=pg.execute("""SELECT p.proname,pg_get_function_identity_arguments(p.oid),p.prokind FROM pg_proc p
                        JOIN pg_namespace n ON n.oid=p.pronamespace WHERE n.nspname=%s ORDER BY 1""",(source,)).fetchall()
                    if routines!=[("reject_forward_fact_mutation","","f")]:
                        raise RuntimeError("V4_FORWARD_SOURCE_ROUTINE_SET_MISMATCH:"+source)
                    pg.execute(sql.SQL("DROP FUNCTION {}.reject_forward_fact_mutation() RESTRICT").format(sql.Identifier(source)))
                    pg.execute(sql.SQL("DROP SCHEMA {} RESTRICT").format(sql.Identifier(source)))
                results.append(dict(source_schema=source,family=family,workspace_namespace=namespace,
                    source_rows=facts,verified_receipt_rows=mapped[1]+r7_count,
                    source_digest="per-row-payload-sha256-parity",
                    target_digest="per-row-payload-sha256-parity",
                    status="DROP_RESTRICT_SUCCESS" if apply else "ELIGIBLE"))
    return dict(status="CLEANUP_APPLIED" if apply else "VERIFY_ONLY",database=identity,results=results)


def main():
    parser=argparse.ArgumentParser();mode=parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--apply",action="store_true");mode.add_argument("--verify-only",action="store_true")
    args=parser.parse_args();sys.path.insert(0,"src")
    from workbench_db.v4_native import configured_dsn
    print(json.dumps(cleanup(configured_dsn(),apply=args.apply),ensure_ascii=False,sort_keys=True))


if __name__=="__main__":main()
