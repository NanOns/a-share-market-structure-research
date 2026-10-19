"""Migrate the two active non-ingress generic Forward workspaces by exact rows."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys

import psycopg
from psycopg import sql
from psycopg.types.json import Jsonb

SOURCES = ("v4_forward_812843566da3f180", "v4_forward_eb17ba1165c8c2a5")


def digest_row(hasher, row):
    raw=json.dumps(row,sort_keys=True,separators=(",",":"),ensure_ascii=False,default=str).encode()
    hasher.update(len(raw).to_bytes(8,"big"));hasher.update(raw)


def migrate(dsn):
    result=[]
    with psycopg.connect(dsn,connect_timeout=5) as pg:
        identity=pg.execute("SELECT current_database(),inet_server_addr()::text,inet_server_port(),current_user").fetchone()
        if identity[:3]!=("market_research","127.0.0.1/32",5432):
            raise RuntimeError("V4_FORWARD_ACTIVE_ALIAS_DATABASE_IDENTITY_MISMATCH")
        pg.execute("SET LOCAL statement_timeout='120s'")
        pg.execute("SET LOCAL lock_timeout='5s'")
        for source in SOURCES:
            alias_rows=pg.execute("""SELECT logical_workspace_id FROM v4.workspace_namespace_alias_history_r1
                WHERE physical_schema=%s AND purpose='forward' AND status='ACTIVE'""",(source,)).fetchall()
            if len(alias_rows)!=1:raise RuntimeError("V4_FORWARD_ACTIVE_ALIAS_NOT_UNIQUE:"+source)
            namespace=alias_rows[0][0]+":forward"
            rel=sql.SQL("{}.forward_facts").format(sql.Identifier(source))
            with pg.transaction():
                pg.execute("SELECT pg_advisory_xact_lock(hashtext(%s))",("V4_FORWARD_ACTIVE_ALIAS_R1:"+source,))
                source_hash=hashlib.sha256();target_hash=hashlib.sha256();count=0
                query=sql.SQL("SELECT kind,fact_key,payload,payload_sha256,source_sha256,ordinal FROM {} ORDER BY ordinal").format(rel)
                with pg.cursor(name="v4_forward_active_alias_source") as cur:
                    cur.itersize=1;cur.execute(query)
                    while rows:=cur.fetchmany(1):
                        kind,key,payload,payload_sha,source_sha,ordinal=rows[0]
                        if hashlib.sha256(payload.encode("utf-8")).hexdigest()!=payload_sha:
                            raise RuntimeError("V4_FORWARD_ACTIVE_SOURCE_PAYLOAD_DIGEST_MISMATCH:"+source)
                        source_row=(kind,key,payload,payload_sha.strip(),source_sha)
                        digest_row(source_hash,source_row)
                        target=pg.execute("""SELECT payload,payload_sha256,source_sha256 FROM v4.forward_facts
                            WHERE workspace_namespace=%s AND kind=%s AND fact_key=%s""",
                            (namespace,kind,key)).fetchone()
                        if target is None:
                            pg.execute("""INSERT INTO v4.forward_facts(workspace_namespace,kind,fact_key,payload,payload_sha256,source_sha256)
                                VALUES(%s,%s,%s,%s,%s,%s)""",
                                (namespace,kind,key,payload,payload_sha.strip(),source_sha))
                            target=pg.execute("""SELECT payload,payload_sha256,source_sha256 FROM v4.forward_facts
                                WHERE workspace_namespace=%s AND kind=%s AND fact_key=%s""",
                                (namespace,kind,key)).fetchone()
                        if target!=(payload,payload_sha.strip(),source_sha):
                            raise RuntimeError("V4_FORWARD_ACTIVE_TARGET_CONFLICT:"+source+":"+kind+":"+key)
                        target_row=(kind,key,target[0],target[1],target[2])
                        digest_row(target_hash,target_row)
                        proof=Jsonb(dict(status="VERIFIED",exact_source_payload_sha256=payload_sha.strip(),
                            target_payload_sha256=payload_sha.strip(),source_ordinal=ordinal))
                        mapped=pg.execute("""SELECT workspace_namespace,payload_sha256,target_sha256,verification
                            FROM v4.forward_schema_migration_map_r1 WHERE source_schema=%s AND kind=%s AND fact_key=%s""",
                            (source,kind,key)).fetchone()
                        if mapped is None:
                            pg.execute("""INSERT INTO v4.forward_schema_migration_map_r1
                                (source_schema,workspace_namespace,kind,fact_key,payload_sha256,source_sha256,target_sha256,verification)
                                VALUES(%s,%s,%s,%s,%s,%s,%s,%s)""",
                                (source,namespace,kind,key,payload_sha.strip(),source_sha,payload_sha.strip(),proof))
                            mapped=pg.execute("""SELECT workspace_namespace,payload_sha256,target_sha256,verification
                                FROM v4.forward_schema_migration_map_r1 WHERE source_schema=%s AND kind=%s AND fact_key=%s""",
                                (source,kind,key)).fetchone()
                        if not mapped or mapped[0]!=namespace or mapped[1].strip()!=payload_sha.strip() or mapped[2].strip()!=payload_sha.strip() or mapped[3].get('status')!='VERIFIED':
                            raise RuntimeError("V4_FORWARD_ACTIVE_MIGRATION_RECEIPT_CONFLICT:"+source)
                        count+=1
                sd,td=source_hash.hexdigest(),target_hash.hexdigest()
                if sd!=td:raise RuntimeError("V4_FORWARD_ACTIVE_FULL_DIGEST_MISMATCH:"+source)
                expected=pg.execute(sql.SQL("SELECT count(*) FROM {}").format(rel)).fetchone()[0]
                actual=pg.execute("SELECT count(*) FROM v4.forward_schema_migration_map_r1 WHERE source_schema=%s",(source,)).fetchone()[0]
                if expected!=count or actual!=count:raise RuntimeError("V4_FORWARD_ACTIVE_ROW_PARITY_FAILED:"+source)
                source_bytes=pg.execute("SELECT pg_total_relation_size(%s::regclass)",(source+'.forward_facts',)).fetchone()[0]
                receipt=dict(status="VERIFIED",source_schema=source,source_table="forward_facts",
                    workspace_namespace=namespace,row_count=count,source_digest=sd,target_digest=td,
                    source_bytes=source_bytes,identity_contract="workspace_namespace+kind+fact_key")
                old_receipt=pg.execute("SELECT receipt FROM v4.forward_migration_r1 WHERE workspace_namespace=%s",(namespace,)).fetchone()
                if old_receipt and old_receipt[0]!=receipt:raise RuntimeError("V4_FORWARD_ACTIVE_MIGRATION_RECEIPT_CONFLICT:"+source)
                if not old_receipt:pg.execute("INSERT INTO v4.forward_migration_r1(workspace_namespace,receipt) VALUES(%s,%s)",(namespace,Jsonb(receipt)))
                result.append(dict(receipt))
    return dict(status="MIGRATED_AND_VERIFIED",database=identity,target_schema="v4",sources=result)


def main():
    parser=argparse.ArgumentParser();parser.add_argument("--apply",action="store_true");args=parser.parse_args()
    if not args.apply:raise SystemExit("Refusing database writes without --apply")
    sys.path.insert(0,"src")
    from workbench_db.v4_native import configured_dsn
    print(json.dumps(migrate(configured_dsn()),ensure_ascii=False,sort_keys=True,default=str))


if __name__=="__main__":main()
