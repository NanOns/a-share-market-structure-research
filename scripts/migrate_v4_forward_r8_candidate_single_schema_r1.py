"""Migrate the exact isolated R8 candidate Forward facts into fixed v4 rows."""
from __future__ import annotations

import argparse
from datetime import date
import hashlib
import json
import sys

import psycopg
from psycopg import sql

SOURCE="v4_r8_forward_64d0f9c30983a3ac"
NAMESPACE="R8_CANDIDATE_64D0F9C30983A3AC"


def canonical(value):
    return json.dumps(value,ensure_ascii=False,separators=(",",":"),allow_nan=False).encode("utf-8")


def digest_row(hasher,row):
    raw=canonical(row);hasher.update(len(raw).to_bytes(8,"big"));hasher.update(raw)


def business_identity(payload):
    try:value=json.loads(payload)
    except (TypeError,json.JSONDecodeError):return None,None,None
    if not isinstance(value,dict):return None,None,None
    owner=value.get("owner_id")
    run_id=value.get("run_id") or value.get("source_run_id")
    t0=value.get("trade_date") or value.get("T0")
    try:t0=date.fromisoformat(t0) if isinstance(t0,str) and len(t0)==10 else None
    except ValueError:t0=None
    return owner,run_id,t0


def migrate(dsn):
    with psycopg.connect(dsn,connect_timeout=5) as pg:
        identity=pg.execute("SELECT current_database(),inet_server_addr()::text,inet_server_port() FROM pg_stat_activity WHERE pid=pg_backend_pid()").fetchone()
        if identity[0]!="market_research" or identity[1] not in ("127.0.0.1","127.0.0.1/32") or identity[2]!=5432:
            raise RuntimeError("V4_FORWARD_R8_DATABASE_IDENTITY_MISMATCH")
        pg.execute("SET LOCAL statement_timeout='180s'");pg.execute("SET LOCAL lock_timeout='5s'")
        if not pg.execute("SELECT to_regclass('v4.forward_r7_facts_r1')").fetchone()[0]:
            raise RuntimeError("V4_FORWARD_R8_FIXED_TARGET_MISSING")
        source_table=sql.SQL("{}.forward_facts").format(sql.Identifier(SOURCE))
        prior=pg.execute("SELECT row_count,source_digest,target_digest,origin_namespace FROM v4.forward_r7_migration_r1 WHERE source_schema=%s",(SOURCE,)).fetchone()
        with pg.transaction():
            pg.execute("SELECT pg_advisory_xact_lock(hashtext(%s))",("V4_FORWARD_R8_CANDIDATE_R1:"+SOURCE,))
            source_hash=hashlib.sha256();count=0
            with pg.cursor(name="forward_r8_candidate_source") as cur:
                cur.itersize=1
                cur.execute(sql.SQL("SELECT kind,fact_key,payload,payload_sha256,source_sha256,ordinal FROM {} ORDER BY ordinal").format(source_table))
                while batch:=cur.fetchmany(1):
                    kind,key,payload,payload_sha,source_sha,ordinal=batch[0]
                    payload_sha=payload_sha.strip()
                    if hashlib.sha256(payload.encode("utf-8")).hexdigest()!=payload_sha:
                        raise RuntimeError("V4_FORWARD_R8_SOURCE_PAYLOAD_DIGEST_MISMATCH")
                    row_identity=(kind,key,payload,payload_sha,source_sha,ordinal)
                    digest_row(source_hash,row_identity)
                    owner,run_id,t0=business_identity(payload)
                    target=pg.execute("""SELECT owner_id,run_id,t0,kind,fact_key,payload,payload_sha256,source_sha256,ordinal
                        FROM v4.forward_r7_facts_r1 WHERE origin_namespace=%s AND kind=%s AND fact_key=%s""",
                        (NAMESPACE,kind,key)).fetchone()
                    expected=(owner,run_id,t0,kind,key,payload,payload_sha,source_sha,ordinal)
                    if target is None:
                        pg.execute("""INSERT INTO v4.forward_r7_facts_r1
                            (origin_namespace,owner_id,run_id,t0,kind,fact_key,payload,payload_sha256,source_sha256,ordinal)
                            OVERRIDING SYSTEM VALUE VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                            (NAMESPACE,*expected))
                        target=pg.execute("""SELECT owner_id,run_id,t0,kind,fact_key,payload,payload_sha256,source_sha256,ordinal
                            FROM v4.forward_r7_facts_r1 WHERE origin_namespace=%s AND kind=%s AND fact_key=%s""",
                            (NAMESPACE,kind,key)).fetchone()
                    if target!=expected:raise RuntimeError("V4_FORWARD_R8_TARGET_FACT_IDENTITY_CONFLICT:"+kind+":"+key)
                    count+=1
            source_digest=source_hash.hexdigest()
            target_hash=hashlib.sha256();target_count=0
            with pg.cursor(name="forward_r8_candidate_target") as cur:
                cur.itersize=8
                cur.execute("""SELECT kind,fact_key,payload,payload_sha256,source_sha256,ordinal
                    FROM v4.forward_r7_facts_r1 WHERE origin_namespace=%s ORDER BY ordinal""",(NAMESPACE,))
                for row in cur:
                    kind,key,payload,payload_sha,source_sha,ordinal=row
                    digest_row(target_hash,(kind,key,payload,payload_sha.strip(),source_sha,ordinal));target_count+=1
            target_digest=target_hash.hexdigest()
            expected_count=pg.execute(sql.SQL("SELECT count(*) FROM {}").format(source_table)).fetchone()[0]
            if target_count!=count or count!=expected_count or target_digest!=source_digest:
                raise RuntimeError("V4_FORWARD_R8_FULL_SOURCE_TARGET_DIGEST_MISMATCH")
            if prior and prior!=(count,source_digest,target_digest,NAMESPACE):
                raise RuntimeError("V4_FORWARD_R8_MIGRATION_RECEIPT_CONFLICT")
            if not prior:
                pg.execute("""INSERT INTO v4.forward_r7_migration_r1
                    (source_schema,source_table,origin_namespace,row_count,source_digest,target_digest)
                    VALUES(%s,'forward_facts',%s,%s,%s,%s)""",(SOURCE,NAMESPACE,count,source_digest,target_digest))
            pg.execute("SELECT setval(pg_get_serial_sequence('v4.forward_r7_facts_r1','ordinal'),GREATEST((SELECT coalesce(max(ordinal),1) FROM v4.forward_r7_facts_r1),1),true)")
        size=pg.execute("SELECT pg_total_relation_size(%s::regclass)",(SOURCE+".forward_facts",)).fetchone()[0]
        return dict(status="MIGRATED_AND_VERIFIED",database=identity,source_schema=SOURCE,target_schema="v4",
            relation="forward_r7_facts_r1",origin_namespace=NAMESPACE,rows=count,source_bytes=size,
            source_digest=source_digest,target_digest=target_digest)


def main():
    parser=argparse.ArgumentParser();parser.add_argument("--apply",action="store_true");args=parser.parse_args()
    if not args.apply:raise SystemExit("Refusing database writes without --apply")
    sys.path.insert(0,"src")
    from workbench_db.v4_native import configured_dsn
    print(json.dumps(migrate(configured_dsn()),ensure_ascii=False,sort_keys=True))


if __name__=="__main__":main()
