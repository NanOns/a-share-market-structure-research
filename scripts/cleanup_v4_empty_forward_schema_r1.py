"""Retire the one confirmed empty Forward alias while preserving its receipt."""
from __future__ import annotations

import argparse
import json
import sys

import psycopg
from psycopg import sql
from psycopg.types.json import Jsonb

SOURCE="v4_forward_ca206ffd216e90b4"


def cleanup(dsn,*,apply):
    with psycopg.connect(dsn,connect_timeout=5) as pg:
        pg.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ"+(", READ WRITE" if apply else ", READ ONLY"))
        identity=pg.execute("SELECT current_database(),inet_server_addr()::text,inet_server_port() FROM pg_stat_activity WHERE pid=pg_backend_pid()").fetchone()
        if identity!=("market_research","127.0.0.1/32",5432):raise RuntimeError("V4_FORWARD_EMPTY_RETIREMENT_DATABASE_MISMATCH")
        pg.execute("SET LOCAL statement_timeout='60s'");pg.execute("SET LOCAL lock_timeout='5s'")
        with pg.transaction():
            pg.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s,0))",("V4_FORWARD_EMPTY_RETIREMENT_R1:"+SOURCE,))
            tables={r[0] for r in pg.execute("SELECT tablename FROM pg_tables WHERE schemaname=%s",(SOURCE,)).fetchall()}
            if tables!={"forward_facts","forward_migration"}:raise RuntimeError("V4_FORWARD_EMPTY_TABLE_SET_MISMATCH")
            source_rows=pg.execute(sql.SQL("SELECT count(*) FROM {}.forward_facts").format(sql.Identifier(SOURCE))).fetchone()[0]
            if source_rows!=0:raise RuntimeError("V4_FORWARD_SOURCE_NOT_EMPTY")
            map_rows=pg.execute("SELECT count(*) FROM v4.forward_schema_migration_map_r1 WHERE source_schema=%s",(SOURCE,)).fetchone()[0]
            if map_rows:raise RuntimeError("V4_FORWARD_EMPTY_SOURCE_HAS_UNEXPECTED_FACT_MAP")
            migration=pg.execute(sql.SQL("SELECT receipt FROM {}.forward_migration WHERE singleton=1").format(sql.Identifier(SOURCE))).fetchone()
            if not migration or migration[0].get("contract_id")!="V4_FORWARD_PG_FACT_STORE_R1":raise RuntimeError("V4_FORWARD_EMPTY_MIGRATION_RECEIPT_MISSING")
            alias_rows=pg.execute("""SELECT logical_workspace_id,purpose,physical_schema,source_root_identity_sha256,
                contract_id,status,registered_at,migration_state,archived_at FROM v4.workspace_namespace_alias_history_r1
                WHERE physical_schema=%s AND purpose='forward'""",(SOURCE,)).fetchall()
            if len(alias_rows)!=1 or alias_rows[0][7]!="MIGRATION_HISTORY_ONLY":raise RuntimeError("V4_FORWARD_EMPTY_ALIAS_HISTORY_NOT_UNIQUE")
            owner=pg.execute("SELECT pg_get_userbyid(nspowner) FROM pg_namespace WHERE nspname=%s",(SOURCE,)).fetchone()[0]
            relation_sizes={r[0]:r[1] for r in pg.execute("""SELECT c.relname,pg_total_relation_size(c.oid)::bigint
                FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname=%s AND c.relkind='r' ORDER BY 1""",(SOURCE,)).fetchall()}
            alias_payload=[[v.isoformat() if hasattr(v, "isoformat") else v for v in r] for r in alias_rows]
            proof=dict(status="VERIFIED_EMPTY_SOURCE",database=identity,target_schema="v4",source_fact_rows=0,
                target_fact_rows=0,source_to_target_fact_map_rows=0,drop_mode="RESTRICT",active_alias_lookup_removed=True)
            existing=pg.execute("SELECT source_owner,source_relation_bytes,source_fact_rows,target_fact_rows,workspace_alias_history,forward_migration_receipt,verification FROM v4.forward_legacy_schema_retirements_r1 WHERE source_schema=%s",(SOURCE,)).fetchone()
            expected=(owner,relation_sizes,0,0,alias_payload,migration[0],proof)
            if existing and existing!=expected:raise RuntimeError("V4_FORWARD_EMPTY_RETIREMENT_RECEIPT_CONFLICT")
            if apply and not existing:
                pg.execute("""INSERT INTO v4.forward_legacy_schema_retirements_r1
                  (source_schema,source_owner,source_relation_bytes,source_fact_rows,target_fact_rows,
                   workspace_alias_history,forward_migration_receipt,verification)
                  VALUES(%s,%s,%s,%s,%s,%s,%s,%s)""",
                  (SOURCE,owner,Jsonb(relation_sizes),0,0,Jsonb(alias_payload),Jsonb(migration[0]),Jsonb(proof)))
            if apply:
                pg.execute(sql.SQL("DROP TABLE {}.forward_facts RESTRICT").format(sql.Identifier(SOURCE)))
                pg.execute(sql.SQL("DROP TABLE {}.forward_migration RESTRICT").format(sql.Identifier(SOURCE)))
                routines=pg.execute("""SELECT p.proname,pg_get_function_identity_arguments(p.oid),p.prokind FROM pg_proc p
                    JOIN pg_namespace n ON n.oid=p.pronamespace WHERE n.nspname=%s ORDER BY 1""",(SOURCE,)).fetchall()
                if routines!={ ("reject_forward_fact_mutation","","f") }:
                    if routines != [("reject_forward_fact_mutation","","f")]:raise RuntimeError("V4_FORWARD_EMPTY_ROUTINE_SET_MISMATCH")
                pg.execute(sql.SQL("DROP FUNCTION {}.reject_forward_fact_mutation() RESTRICT").format(sql.Identifier(SOURCE)))
                pg.execute(sql.SQL("DROP SCHEMA {} RESTRICT").format(sql.Identifier(SOURCE)))
            return dict(status="DROP_RESTRICT_SUCCESS" if apply else "VERIFIED_EMPTY_ELIGIBLE",database=identity,
                source_schema=SOURCE,source_rows=0,alias_history_rows=len(alias_rows),owner=owner,
                relation_sizes=relation_sizes,proof=proof)


def main():
    p=argparse.ArgumentParser();m=p.add_mutually_exclusive_group(required=True);m.add_argument("--apply",action="store_true");m.add_argument("--verify-only",action="store_true");a=p.parse_args()
    sys.path.insert(0,"src")
    from workbench_db.v4_native import configured_dsn
    print(json.dumps(cleanup(configured_dsn(),apply=a.apply),ensure_ascii=False,sort_keys=True))


if __name__=="__main__":main()
