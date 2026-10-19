"""Migrate the inventoried R1 and R2 projections into fixed v4 relations."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys

import psycopg
from psycopg import sql

SOURCES = (
    ("R1", "v4_read_index_80ef60f40eca6e6d", "token", "token", "read_versions_r1", "read_items_r1", "read_responses_r1"),
    ("R2", "v4_read_index_r2_80ef60f40eca6e6d", "token", "context_id", "read_versions_r2", "read_items_r2", "read_responses_r2"),
    ("R2", "v4_00bd3ea17fe4cd57d84f9171aa8e725fbd9edab55a754087aac5b2f5", "token", "context_id", "read_versions_r2", "read_items_r2", "read_responses_r2"),
    ("R2", "v4_65f092e59fec0d987186ef0b5f1b9018f0d20adb5e79c4ff8576a63b", "token", "context_id", "read_versions_r2", "read_items_r2", "read_responses_r2"),
    ("R2", "v4_96901ca1753536bec2e2767de6f018ceb6308dbde3826d5d13331b9c", "token", "context_id", "read_versions_r2", "read_items_r2", "read_responses_r2"),
    ("R2", "v4_b00d132ba317e5f34b85565c29c92cae40b5438cad5a96c5ac0b9966", "token", "context_id", "read_versions_r2", "read_items_r2", "read_responses_r2"),
    ("R2", "v4_f05334ead7664a2b939a283bb3ac15ed1200ea2138fa93ccd8cbb58c", "token", "context_id", "read_versions_r2", "read_items_r2", "read_responses_r2"),
    ("R2", "v4_fae10bdca7c337472de4a49557bb1d314a98d49ea5d2052b2cc35907", "token", "context_id", "read_versions_r2", "read_items_r2", "read_responses_r2"),
)


def _counts(pg, schema, source_context_column, target_context_column, items_table, context_id, day, digest=None):
    source = pg.execute(sql.SQL("SELECT domain,count(*) FROM {}.read_items WHERE {}=%s AND day=%s GROUP BY domain ORDER BY domain").format(sql.Identifier(schema),sql.Identifier(source_context_column)),(context_id,day)).fetchall()
    if target_context_column=="context_id":
        target=pg.execute("SELECT domain,count(*) FROM v4.read_items_r2 WHERE context_id=%s AND day=%s AND digest=%s GROUP BY domain ORDER BY domain",(context_id,day,digest)).fetchall()
    else:
        target = pg.execute(sql.SQL("SELECT domain,count(*) FROM v4.{} WHERE {}=%s AND day=%s GROUP BY domain ORDER BY domain").format(sql.Identifier(items_table),sql.Identifier(target_context_column)),(context_id,day)).fetchall()
    return dict(source),dict(target)


def _install_guards(pg, family):
    definitions={
        "R1": ("read_versions_r1", "read_items_r1", "read_responses_r1", "read_index_r1_immutable", "read_index_r1_no_truncate",
            """BEGIN
              IF TG_TABLE_NAME='read_versions_r1' THEN
                IF TG_OP='UPDATE' AND NOT OLD.sealed AND NEW.sealed AND
                   (OLD.token,OLD.day,OLD.digest,OLD.contract)=(NEW.token,NEW.day,NEW.digest,NEW.contract) THEN RETURN NEW; END IF;
                IF TG_OP='INSERT' THEN RETURN NEW; END IF;
                RAISE EXCEPTION 'READ_INDEX_IMMUTABLE';
              END IF;
              IF TG_OP<>'INSERT' OR EXISTS(SELECT 1 FROM v4.read_versions_r1 WHERE token=NEW.token AND day=NEW.day AND sealed) THEN
                RAISE EXCEPTION 'READ_INDEX_IMMUTABLE';
              END IF;
              RETURN NEW;
            END"""),
        "R2": ("read_versions_r2", "read_items_r2", "read_responses_r2", "read_index_r2_immutable", "read_index_r2_no_truncate",
            """BEGIN
              IF TG_TABLE_NAME='read_versions_r2' THEN
                IF TG_OP='UPDATE' AND NOT OLD.sealed AND NEW.sealed AND
                   (OLD.context_id,OLD.day,OLD.digest,OLD.contract)=(NEW.context_id,NEW.day,NEW.digest,NEW.contract) THEN RETURN NEW; END IF;
                IF TG_OP='INSERT' THEN RETURN NEW; END IF;
                RAISE EXCEPTION 'READ_INDEX_IMMUTABLE';
              END IF;
              IF TG_OP<>'INSERT' OR EXISTS(SELECT 1 FROM v4.read_versions_r2 WHERE context_id=NEW.context_id AND day=NEW.day AND digest=NEW.digest AND sealed) THEN
                RAISE EXCEPTION 'READ_INDEX_IMMUTABLE';
              END IF;
              RETURN NEW;
            END"""),
    }
    if family not in definitions:
        raise RuntimeError("V4_READ_INDEX_FAMILY_NOT_REGISTERED")
    versions,items,responses,fn,truncate_fn,body=definitions[family]
    pg.execute(sql.SQL("CREATE OR REPLACE FUNCTION v4.{}() RETURNS trigger LANGUAGE plpgsql AS {}").format(
        sql.Identifier(fn),sql.Literal(body)))
    pg.execute(sql.SQL("CREATE OR REPLACE FUNCTION v4.{}() RETURNS trigger LANGUAGE plpgsql AS {}").format(
        sql.Identifier(truncate_fn),sql.Literal("BEGIN RAISE EXCEPTION 'READ_INDEX_IMMUTABLE'; END")))
    for table in (versions,items,responses):
        immutable_trigger=f"read_index_{family.lower()}_immutable_guard"
        truncate_trigger=f"read_index_{family.lower()}_truncate_guard"
        pg.execute(sql.SQL("DROP TRIGGER IF EXISTS {} ON v4.{}").format(sql.Identifier(immutable_trigger),sql.Identifier(table)))
        pg.execute(sql.SQL("CREATE TRIGGER {} BEFORE INSERT OR UPDATE OR DELETE ON v4.{} FOR EACH ROW EXECUTE FUNCTION v4.{}()").format(
            sql.Identifier(immutable_trigger),sql.Identifier(table),sql.Identifier(fn)))
        pg.execute(sql.SQL("DROP TRIGGER IF EXISTS {} ON v4.{}").format(sql.Identifier(truncate_trigger),sql.Identifier(table)))
        pg.execute(sql.SQL("CREATE TRIGGER {} BEFORE TRUNCATE ON v4.{} FOR EACH STATEMENT EXECUTE FUNCTION v4.{}()").format(
            sql.Identifier(truncate_trigger),sql.Identifier(table),sql.Identifier(truncate_fn)))


def migrate(dsn):
    results=[]
    with psycopg.connect(dsn,connect_timeout=5) as pg:
        identity=pg.execute("SELECT current_database(),inet_server_addr()::text,inet_server_port() FROM pg_stat_activity WHERE pid=pg_backend_pid()").fetchone()
        if identity[0]!="market_research" or identity[1] not in ("127.0.0.1","127.0.0.1/32") or identity[2]!=5432:
            raise RuntimeError("V4_READ_INDEX_DATABASE_IDENTITY_MISMATCH")
        pg.execute("SET LOCAL statement_timeout='120s'");pg.execute("SET LOCAL lock_timeout='5s'")
        for family,schema,source_context_column,target_context_column,versions_table,items_table,responses_table in SOURCES:
            for table in ('read_versions','read_items','read_responses'):
                if not pg.execute("SELECT to_regclass(%s)",(f"{schema}.{table}",)).fetchone()[0]:
                    raise RuntimeError("V4_READ_INDEX_EXACT_SOURCE_RELATION_MISSING:"+schema+":"+table)
            with pg.transaction():
                pg.execute("SELECT pg_advisory_xact_lock(hashtext(%s))",("V4_READ_INDEX_SINGLE_SCHEMA_R1:"+schema,))
                source_versions=sql.SQL("SELECT {},day,digest,contract,sealed FROM {}.read_versions ORDER BY {},day COLLATE \"C\"").format(sql.Identifier(source_context_column),sql.Identifier(schema),sql.Identifier(source_context_column))
                versions=pg.execute(source_versions).fetchall()
                item_rows=response_rows=0
                for context_id,day,digest,contract,sealed in versions:
                    if sealed is not True:
                        raise RuntimeError("V4_READ_INDEX_SOURCE_VERSION_UNSEALED")
                    if family=="R2":
                        target_version=pg.execute("SELECT digest,contract,sealed FROM v4.read_versions_r2 WHERE context_id=%s AND day=%s AND digest=%s",(context_id,day,digest)).fetchone()
                    else:
                        target_version=pg.execute("SELECT digest,contract,sealed FROM v4.read_versions_r1 WHERE token=%s AND day=%s",(context_id,day)).fetchone()
                    if target_version and target_version!=(digest,contract,True):
                        raise RuntimeError("V4_READ_INDEX_TARGET_VERSION_IDENTITY_CONFLICT")
                    if target_version is None:
                        if family=="R2":
                            pg.execute("INSERT INTO v4.read_versions_r2(context_id,day,digest,contract,sealed) VALUES(%s,%s,%s,%s,false)",(context_id,day,digest,contract))
                            pg.execute(sql.SQL("INSERT INTO v4.read_items_r2(context_id,day,digest,domain,entity_id,symbol,display_name,aliases,search_parts,sector_ids,values_json,summary,detail,detail_sha256) SELECT {},day,%s,domain,entity_id,symbol,display_name,aliases,search_parts,sector_ids,values_json,summary,detail,detail_sha256 FROM {}.read_items WHERE {}=%s AND day=%s").format(sql.Identifier(source_context_column),sql.Identifier(schema),sql.Identifier(source_context_column)),(digest,context_id,day))
                            pg.execute(sql.SQL("INSERT INTO v4.read_responses_r2(context_id,day,digest,path,payload,payload_sha256) SELECT {},day,%s,path,payload,payload_sha256 FROM {}.read_responses WHERE {}=%s AND day=%s").format(sql.Identifier(source_context_column),sql.Identifier(schema),sql.Identifier(source_context_column)),(digest,context_id,day))
                            pg.execute("UPDATE v4.read_versions_r2 SET sealed=true WHERE context_id=%s AND day=%s AND digest=%s",(context_id,day,digest))
                        else:
                            pg.execute(sql.SQL("INSERT INTO v4.{} SELECT * FROM {}.read_versions WHERE {}=%s AND day=%s").format(sql.Identifier(versions_table),sql.Identifier(schema),sql.Identifier(source_context_column)),(context_id,day))
                            pg.execute(sql.SQL("INSERT INTO v4.{} SELECT {},day,domain,entity_id,symbol,display_name,aliases,search_parts,sector_ids,values_json,summary,detail,detail_sha256 FROM {}.read_items WHERE {}=%s AND day=%s").format(sql.Identifier(items_table),sql.Identifier(source_context_column),sql.Identifier(schema),sql.Identifier(source_context_column)),(context_id,day))
                            pg.execute(sql.SQL("INSERT INTO v4.{} SELECT {},day,path,payload,payload_sha256 FROM {}.read_responses WHERE {}=%s AND day=%s").format(sql.Identifier(responses_table),sql.Identifier(source_context_column),sql.Identifier(schema),sql.Identifier(source_context_column)),(context_id,day))
                    source_counts,target_counts=_counts(pg,schema,source_context_column,target_context_column,items_table,context_id,day,digest)
                    if source_counts!=target_counts:
                        raise RuntimeError("V4_READ_INDEX_DOMAIN_COUNT_MISMATCH")
                    source_responses=pg.execute(sql.SQL("SELECT count(*) FROM {}.read_responses WHERE {}=%s AND day=%s").format(sql.Identifier(schema),sql.Identifier(source_context_column)),(context_id,day)).fetchone()[0]
                    if family=="R2":
                        target_responses=pg.execute("SELECT count(*) FROM v4.read_responses_r2 WHERE context_id=%s AND day=%s AND digest=%s",(context_id,day,digest)).fetchone()[0]
                    else:
                        target_responses=pg.execute(sql.SQL("SELECT count(*) FROM v4.{} WHERE {}=%s AND day=%s").format(sql.Identifier(responses_table),sql.Identifier(target_context_column)),(context_id,day)).fetchone()[0]
                    if source_responses!=target_responses:
                        raise RuntimeError("V4_READ_INDEX_RESPONSE_COUNT_MISMATCH")
                    if family=="R2":
                        parity=pg.execute(sql.SQL("""SELECT count(*) FROM {}.read_items s FULL JOIN v4.read_items_r2 t
                            ON t.context_id=s.{} AND t.day=s.day AND t.digest=%s AND t.domain=s.domain AND t.entity_id=s.entity_id
                            WHERE (s.{}=%s OR (t.context_id=%s AND t.digest=%s)) AND (s.{} IS NULL OR t.context_id IS NULL OR
                              (s.domain,s.entity_id,s.symbol,s.display_name,s.aliases,s.search_parts,s.sector_ids,s.values_json,s.summary,s.detail,s.detail_sha256)
                              IS DISTINCT FROM (t.domain,t.entity_id,t.symbol,t.display_name,t.aliases,t.search_parts,t.sector_ids,t.values_json,t.summary,t.detail,t.detail_sha256))""").format(sql.Identifier(schema),sql.Identifier(source_context_column),sql.Identifier(source_context_column),sql.Identifier(source_context_column)),(digest,context_id,context_id,digest)).fetchone()[0]
                    else:
                        parity=pg.execute(sql.SQL("""SELECT count(*) FROM {}.read_items s FULL JOIN v4.{} t
                            ON t.{}=s.{} AND t.day=s.day AND t.domain=s.domain AND t.entity_id=s.entity_id
                            WHERE (s.{}=%s OR t.{}=%s) AND (s.{} IS NULL OR t.{} IS NULL OR
                              (s.domain,s.entity_id,s.symbol,s.display_name,s.aliases,s.search_parts,s.sector_ids,s.values_json,s.summary,s.detail,s.detail_sha256)
                              IS DISTINCT FROM (t.domain,t.entity_id,t.symbol,t.display_name,t.aliases,t.search_parts,t.sector_ids,t.values_json,t.summary,t.detail,t.detail_sha256))""").format(
                            sql.Identifier(schema),sql.Identifier(items_table),sql.Identifier(target_context_column),sql.Identifier(source_context_column),
                            sql.Identifier(source_context_column),sql.Identifier(target_context_column),sql.Identifier(source_context_column),sql.Identifier(target_context_column)),
                            (context_id,context_id)).fetchone()[0]
                    if parity:
                        raise RuntimeError(f"V4_READ_INDEX_SOURCE_TARGET_ITEM_PARITY_FAILED:{schema}:{context_id}:{day}:{digest}:{parity}")
                    if family=="R2":
                        response_parity=pg.execute(sql.SQL("""SELECT count(*) FROM {}.read_responses s FULL JOIN v4.read_responses_r2 t
                            ON t.context_id=s.{} AND t.day=s.day AND t.digest=%s AND t.path=s.path
                            WHERE (s.{}=%s OR (t.context_id=%s AND t.digest=%s)) AND (s.{} IS NULL OR t.context_id IS NULL OR
                              (s.path,s.payload,s.payload_sha256) IS DISTINCT FROM (t.path,t.payload,t.payload_sha256))""").format(sql.Identifier(schema),sql.Identifier(source_context_column),sql.Identifier(source_context_column),sql.Identifier(source_context_column)),(digest,context_id,context_id,digest)).fetchone()[0]
                    else:
                        response_parity=pg.execute(sql.SQL("""SELECT count(*) FROM {}.read_responses s FULL JOIN v4.{} t
                            ON t.{}=s.{} AND t.day=s.day AND t.path=s.path
                            WHERE (s.{}=%s OR t.{}=%s) AND (s.{} IS NULL OR t.{} IS NULL OR
                              (s.path,s.payload,s.payload_sha256) IS DISTINCT FROM (t.path,t.payload,t.payload_sha256))""").format(
                            sql.Identifier(schema),sql.Identifier(responses_table),sql.Identifier(target_context_column),sql.Identifier(source_context_column),
                            sql.Identifier(source_context_column),sql.Identifier(target_context_column),sql.Identifier(source_context_column),sql.Identifier(target_context_column)),
                            (context_id,context_id)).fetchone()[0]
                    if response_parity:
                        raise RuntimeError("V4_READ_INDEX_SOURCE_TARGET_RESPONSE_PARITY_FAILED")
                    domain_counts={key:value for key,value in source_counts.items()}
                    proof=dict(status="VERIFIED",source_items=sum(source_counts.values()),target_items=sum(target_counts.values()),
                               source_responses=source_responses,target_responses=target_responses,item_row_parity=True,response_row_parity=True)
                    pg.execute("""INSERT INTO v4.read_index_migration_map_r1
                        (generation,source_schema,context_id,day,digest,contract,domain_counts,response_count,verification)
                        VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb) ON CONFLICT DO NOTHING""",
                        (family,schema,context_id,day,digest,contract,json.dumps(domain_counts,separators=(",",":")),source_responses,json.dumps(proof,separators=(",",":"))))
                    mapped=pg.execute("SELECT digest,contract,domain_counts,response_count,verification FROM v4.read_index_migration_map_r1 WHERE generation=%s AND source_schema=%s AND context_id=%s AND day=%s",(family,schema,context_id,day)).fetchone()
                    if not mapped or mapped[:4]!=(digest,contract,domain_counts,source_responses) or mapped[4].get('status')!='VERIFIED':
                        raise RuntimeError("V4_READ_INDEX_MIGRATION_MAP_READBACK_MISMATCH")
                    item_rows+=sum(source_counts.values());response_rows+=source_responses
                _install_guards(pg,family)
                results.append(dict(generation=family,source_schema=schema,versions=len(versions),items=item_rows,responses=response_rows,status="VERIFIED"))
    return dict(status="MIGRATED_AND_VERIFIED",database=identity,target_schema="v4",results=results)


def main():
    parser=argparse.ArgumentParser();parser.add_argument("--apply",action="store_true");args=parser.parse_args()
    if not args.apply:raise SystemExit("Refusing database writes without --apply")
    sys.path.insert(0,"src")
    from workbench_db.v4_native import configured_dsn
    print(json.dumps(migrate(configured_dsn()),ensure_ascii=False,sort_keys=True,default=str))


if __name__=="__main__":main()
