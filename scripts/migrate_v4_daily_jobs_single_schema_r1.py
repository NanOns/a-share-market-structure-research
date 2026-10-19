"""Migrate the current-workspace scheduler history from its exact inventoried source."""
from __future__ import annotations

import argparse
import json
import sys

import psycopg
from psycopg import sql

SOURCE = "v4_jobs_80ef60f40eca6e6d"
NAMESPACE = "MAIN_DEV_WORKSPACE_R1"
TABLES = (
    ("scheduler_policy", "jobs_scheduler_policy_r1", "UPSERT"),
    ("update_jobs", "jobs_update_jobs_r1", "COPY"),
    ("scheduler_dispatch", "jobs_scheduler_dispatch_r1", "COPY"),
    ("scheduler_attempts", "jobs_scheduler_attempts_r1", "COPY"),
    ("scheduler_rearm", "jobs_scheduler_rearm_r1", "COPY"),
    ("update_job_days", "jobs_update_job_days_r1", "COPY"),
    ("update_events", "jobs_update_events_r1", "COPY"),
    ("update_job_progress", "jobs_update_job_progress_r1", "COPY"),
    ("source_probe_state", "jobs_source_probe_state_r1", "COPY"),
)


def migrate(dsn):
    with psycopg.connect(dsn,connect_timeout=5) as pg:
        identity=pg.execute("SELECT current_database(),inet_server_addr()::text,inet_server_port() FROM pg_stat_activity WHERE pid=pg_backend_pid()").fetchone()
        if identity[0]!="market_research" or identity[1] not in ("127.0.0.1","127.0.0.1/32") or identity[2]!=5432:
            raise RuntimeError("V4_DAILY_JOBS_DATABASE_IDENTITY_MISMATCH")
        if not pg.execute("SELECT to_regclass('v4.jobs_migration_map_r1')").fetchone()[0]:
            raise RuntimeError("V4_DAILY_JOBS_MIGRATION_053_REQUIRED")
        for source,_target,_mode in TABLES:
            source_table=source
            if not pg.execute("SELECT to_regclass(%s)",(f"{SOURCE}.{source_table}",)).fetchone()[0]:
                raise RuntimeError("V4_DAILY_JOBS_EXACT_SOURCE_TABLE_MISSING:"+source_table)
        pg.execute("SET LOCAL statement_timeout='120s'");pg.execute("SET LOCAL lock_timeout='5s'")
        with pg.transaction():
            pg.execute("SELECT pg_advisory_xact_lock(hashtext(%s))",("V4_DAILY_JOBS_SINGLE_SCHEMA_R1:"+SOURCE,))
            prior=pg.execute("SELECT table_counts,verification FROM v4.jobs_migration_map_r1 WHERE source_schema=%s",(SOURCE,)).fetchone()
            counts={}
            if prior is None:
                for source,target,mode in TABLES:
                    source_rel=sql.SQL("{}.{}").format(sql.Identifier(SOURCE),sql.Identifier(source))
                    target_rel=sql.SQL("v4.{}").format(sql.Identifier(target))
                    if mode=="UPSERT":
                        pg.execute(sql.SQL("INSERT INTO {} SELECT * FROM {} ON CONFLICT(id) DO UPDATE SET enabled=EXCLUDED.enabled,revision=EXCLUDED.revision,updated_at=EXCLUDED.updated_at").format(target_rel,source_rel))
                    else:
                        pg.execute(sql.SQL("INSERT INTO {} SELECT * FROM {}").format(target_rel,source_rel))
            for source,target,_mode in TABLES:
                source_rel=sql.SQL("{}.{}").format(sql.Identifier(SOURCE),sql.Identifier(source))
                target_rel=sql.SQL("v4.{}").format(sql.Identifier(target))
                source_count=pg.execute(sql.SQL("SELECT count(*) FROM {}").format(source_rel)).fetchone()[0]
                target_count=pg.execute(sql.SQL("SELECT count(*) FROM {}").format(target_rel)).fetchone()[0]
                if source_count!=target_count:
                    raise RuntimeError("V4_DAILY_JOBS_ROW_COUNT_MISMATCH:"+source)
                source_only=pg.execute(sql.SQL("SELECT count(*) FROM (SELECT * FROM {} EXCEPT ALL SELECT * FROM {}) d").format(source_rel,target_rel)).fetchone()[0]
                target_only=pg.execute(sql.SQL("SELECT count(*) FROM (SELECT * FROM {} EXCEPT ALL SELECT * FROM {}) d").format(target_rel,source_rel)).fetchone()[0]
                if source_only or target_only:
                    raise RuntimeError("V4_DAILY_JOBS_SOURCE_TARGET_PARITY_FAILED:"+source)
                counts[target]=source_count
            proof=dict(status="VERIFIED",source_schema=SOURCE,target_schema="v4",target_namespace=NAMESPACE,
                       source_target_row_parity=True,table_count=len(TABLES))
            if prior:
                if prior[0]!=counts or prior[1].get('status')!="VERIFIED":
                    raise RuntimeError("V4_DAILY_JOBS_EXISTING_MIGRATION_MAP_CONFLICT")
            else:
                pg.execute("INSERT INTO v4.jobs_migration_map_r1(source_schema,target_namespace,table_counts,verification) VALUES(%s,%s,%s,%s)",
                    (SOURCE,NAMESPACE,json.dumps(counts,separators=(",",":")),json.dumps(proof,separators=(",",":"))))
            row=pg.execute("SELECT target_namespace,table_counts,verification FROM v4.jobs_migration_map_r1 WHERE source_schema=%s",(SOURCE,)).fetchone()
            if not row or row[0]!=NAMESPACE or row[1]!=counts or row[2].get('status')!="VERIFIED":
                raise RuntimeError("V4_DAILY_JOBS_MIGRATION_MAP_READBACK_MISMATCH")
            return dict(status="MIGRATED_AND_VERIFIED",database=identity,source_schema=SOURCE,target_schema="v4",namespace=NAMESPACE,table_counts=counts)


def main():
    parser=argparse.ArgumentParser();parser.add_argument("--apply",action="store_true");args=parser.parse_args()
    if not args.apply:raise SystemExit("Refusing database writes without --apply")
    sys.path.insert(0,"src")
    from workbench_db.v4_native import configured_dsn
    print(json.dumps(migrate(configured_dsn()),ensure_ascii=False,sort_keys=True,default=str))


if __name__=="__main__":main()
