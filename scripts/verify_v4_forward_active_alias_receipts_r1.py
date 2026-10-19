"""Verify and seal exact-row Forward migration receipts without replaying payloads."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys

import psycopg
from psycopg.types.json import Jsonb

SOURCES=("v4_forward_812843566da3f180","v4_forward_eb17ba1165c8c2a5")


def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False,default=str).encode("utf-8")


def digest_rows(rows):
    return hashlib.sha256(canonical(rows)).hexdigest()


def verify(dsn):
    result=[]
    with psycopg.connect(dsn,connect_timeout=5) as pg:
        identity=pg.execute("SELECT current_database(),inet_server_addr()::text,inet_server_port() FROM pg_stat_activity WHERE pid=pg_backend_pid()").fetchone()
        if identity[:3]!=("market_research","127.0.0.1/32",5432):
            raise RuntimeError("V4_FORWARD_ACTIVE_RECEIPT_DATABASE_IDENTITY_MISMATCH")
        with pg.transaction():
            for source in SOURCES:
                aliases=pg.execute("SELECT logical_workspace_id FROM v4.workspace_namespace_aliases_r1 WHERE physical_schema=%s AND purpose='forward' AND status='ACTIVE'",(source,)).fetchall()
                if len(aliases)!=1:raise RuntimeError("V4_FORWARD_ACTIVE_RECEIPT_ALIAS_NOT_UNIQUE:"+source)
                namespace=aliases[0][0]+":forward"
                mappings=pg.execute("""SELECT kind,fact_key,payload_sha256,source_sha256,target_sha256,verification
                    FROM v4.forward_schema_migration_map_r1 WHERE source_schema=%s""",(source,)).fetchall()
                source_rows=[]
                for kind,key,payload_sha,source_sha,target_sha,proof in mappings:
                    if (proof.get("status")!="VERIFIED" or payload_sha.strip()!=target_sha.strip()
                            or proof.get("exact_source_payload_sha256")!=payload_sha.strip()
                            or proof.get("target_payload_sha256")!=target_sha.strip()):
                        raise RuntimeError("V4_FORWARD_ACTIVE_RECEIPT_ROW_PROOF_INVALID:"+source)
                    source_rows.append((proof.get("source_ordinal"),kind,key,payload_sha.strip(),source_sha.strip() if source_sha else None))
                source_rows.sort(key=lambda row:row[0])
                targets=pg.execute("""SELECT ordinal,kind,fact_key,payload_sha256,source_sha256
                    FROM v4.forward_facts WHERE workspace_namespace=%s""",(namespace,)).fetchall()
                target_rows=sorted(((ordinal,kind,key,payload_sha.strip(),source_sha.strip() if source_sha else None)
                                    for ordinal,kind,key,payload_sha,source_sha in targets),key=lambda row:row[0])
                canonical_source=[row[1:] for row in source_rows]
                canonical_target=[row[1:] for row in target_rows]
                if not mappings or canonical_source!=canonical_target:
                    raise RuntimeError("V4_FORWARD_ACTIVE_RECEIPT_FULL_ROW_IDENTITY_MISMATCH:"+source)
                source_digest=digest_rows(canonical_source);target_digest=digest_rows(canonical_target)
                size=pg.execute("SELECT pg_total_relation_size(%s::regclass)",(source+".forward_facts",)).fetchone()[0]
                receipt=dict(status="VERIFIED",source_schema=source,source_table="forward_facts",
                    workspace_namespace=namespace,row_count=len(canonical_source),source_digest=source_digest,
                    target_digest=target_digest,source_bytes=size,
                    digest_contract="V4_FORWARD_MIGRATED_ROW_HASH_SET_R1")
                previous=pg.execute("SELECT receipt FROM v4.forward_migration_r1 WHERE workspace_namespace=%s",(namespace,)).fetchone()
                if previous and previous[0]!=receipt:raise RuntimeError("V4_FORWARD_ACTIVE_RECEIPT_CONFLICT:"+source)
                if not previous:pg.execute("INSERT INTO v4.forward_migration_r1(workspace_namespace,receipt) VALUES(%s,%s)",(namespace,Jsonb(receipt)))
                result.append(receipt)
    return dict(status="VERIFIED",database=identity,target_schema="v4",results=result)


def main():
    parser=argparse.ArgumentParser();parser.add_argument("--apply",action="store_true");args=parser.parse_args()
    if not args.apply:raise SystemExit("Refusing database writes without --apply")
    sys.path.insert(0,"src")
    from workbench_db.v4_native import configured_dsn
    print(json.dumps(verify(configured_dsn()),ensure_ascii=False,sort_keys=True,default=str))


if __name__=="__main__":main()
