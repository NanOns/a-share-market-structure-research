"""Preserve small, enumerated Forward facts in fixed v4 rows with exact receipts."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys

import psycopg
from psycopg import sql
from psycopg.types.json import Jsonb

SOURCES=(
    "v4_forward_0b17987ca8eff537",
    "v4_forward_b58dca4685f32a81",
    "v4_forward_d358403c87339ff1",
    "v4_forward_fb8bc0a3ad27ca76",
    "v4_forward_925162ea70c87743",
)


def _digest_row(hasher,row):
    raw=json.dumps(row,ensure_ascii=False,separators=(",",":"),allow_nan=False,default=str).encode()
    hasher.update(len(raw).to_bytes(8,"big"));hasher.update(raw)


def migrate(dsn):
    results=[]
    with psycopg.connect(dsn,connect_timeout=5) as pg:
        identity=pg.execute("SELECT current_database(),inet_server_addr()::text,inet_server_port() FROM pg_stat_activity WHERE pid=pg_backend_pid()").fetchone()
        if identity!=("market_research","127.0.0.1/32",5432):raise RuntimeError("V4_FORWARD_REMAINDER_DATABASE_IDENTITY_MISMATCH")
        pg.execute("SET LOCAL statement_timeout='120s'");pg.execute("SET LOCAL lock_timeout='5s'")
        for source in SOURCES:
            namespace="LEGACY:"+source
            with pg.transaction():
                pg.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s,0))",("V4_FORWARD_REMAINDER_R1:"+source,))
                source_hash=hashlib.sha256();target_hash=hashlib.sha256();rows=0
                query=sql.SQL("SELECT kind,fact_key,payload,payload_sha256,source_sha256,ordinal FROM {}.forward_facts ORDER BY ordinal").format(sql.Identifier(source))
                with pg.cursor(name="v4_forward_remainder_source") as cur:
                    cur.itersize=1;cur.execute(query)
                    while batch:=cur.fetchmany(1):
                        kind,key,payload,payload_sha,source_sha,ordinal=batch[0]
                        payload_sha=payload_sha.strip()
                        if hashlib.sha256(payload.encode("utf-8")).hexdigest()!=payload_sha:
                            raise RuntimeError("V4_FORWARD_REMAINDER_SOURCE_DIGEST_MISMATCH:"+source+":"+kind+":"+key)
                        row=(kind,key,payload,payload_sha,source_sha,ordinal);_digest_row(source_hash,row)
                        target=pg.execute("SELECT payload,payload_sha256,source_sha256 FROM v4.forward_facts WHERE workspace_namespace=%s AND kind=%s AND fact_key=%s",(namespace,kind,key)).fetchone()
                        if target is None:
                            pg.execute("INSERT INTO v4.forward_facts(workspace_namespace,kind,fact_key,payload,payload_sha256,source_sha256) VALUES(%s,%s,%s,%s,%s,%s)",(namespace,kind,key,payload,payload_sha,source_sha))
                            target=(payload,payload_sha,source_sha)
                        if target!=(payload,payload_sha,source_sha):raise RuntimeError("V4_FORWARD_REMAINDER_TARGET_IDENTITY_CONFLICT:"+source+":"+kind+":"+key)
                        _digest_row(target_hash,(kind,key,target[0],target[1].strip(),target[2],ordinal))
                        proof=Jsonb(dict(status="VERIFIED",source_ordinal=ordinal,source_payload_sha256=payload_sha,target_payload_sha256=target[1].strip(),exact_payload_identity=True))
                        mapped=pg.execute("SELECT workspace_namespace,payload_sha256,target_sha256,verification FROM v4.forward_schema_migration_map_r1 WHERE source_schema=%s AND kind=%s AND fact_key=%s",(source,kind,key)).fetchone()
                        expected=(namespace,payload_sha,payload_sha)
                        if mapped and (mapped[0],mapped[1].strip(),mapped[2].strip())!=expected:raise RuntimeError("V4_FORWARD_REMAINDER_RECEIPT_CONFLICT")
                        if not mapped:
                            pg.execute("INSERT INTO v4.forward_schema_migration_map_r1(source_schema,workspace_namespace,kind,fact_key,payload_sha256,source_sha256,target_sha256,verification) VALUES(%s,%s,%s,%s,%s,%s,%s,%s)",(source,namespace,kind,key,payload_sha,source_sha,payload_sha,proof))
                        elif mapped[3].get("status")!="VERIFIED":raise RuntimeError("V4_FORWARD_REMAINDER_RECEIPT_UNVERIFIED")
                        rows+=1
                source_digest,target_digest=source_hash.hexdigest(),target_hash.hexdigest()
                if source_digest!=target_digest:raise RuntimeError("V4_FORWARD_REMAINDER_FULL_DIGEST_MISMATCH:"+source)
                map_count=pg.execute("SELECT count(*) FROM v4.forward_schema_migration_map_r1 WHERE source_schema=%s AND workspace_namespace=%s AND verification->>'status'='VERIFIED'",(source,namespace)).fetchone()[0]
                if map_count!=rows:raise RuntimeError("V4_FORWARD_REMAINDER_RECEIPT_CARDINALITY_MISMATCH:"+source)
                receipt=dict(contract_id="V4_FORWARD_PG_FACT_STORE_R1",workspace_namespace=namespace,originals=[],original_files_unchanged=True,
                    legacy_source_schema=source,legacy_source_rows=rows,source_digest=source_digest,target_digest=target_digest)
                old=pg.execute("SELECT receipt FROM v4.forward_migration_r1 WHERE workspace_namespace=%s",(namespace,)).fetchone()
                if old and old[0]!=receipt:raise RuntimeError("V4_FORWARD_REMAINDER_NAMESPACE_RECEIPT_CONFLICT")
                if not old:pg.execute("INSERT INTO v4.forward_migration_r1(workspace_namespace,receipt) VALUES(%s,%s)",(namespace,Jsonb(receipt)))
                results.append(dict(source_schema=source,namespace=namespace,rows=rows,source_digest=source_digest,target_digest=target_digest,status="VERIFIED"))
    return dict(status="MIGRATED_AND_VERIFIED",database=identity,target_schema="v4",results=results)


def main():
    parser=argparse.ArgumentParser();parser.add_argument("--apply",action="store_true");args=parser.parse_args()
    if not args.apply:raise SystemExit("Refusing database writes without --apply")
    sys.path.insert(0,"src")
    from workbench_db.v4_native import configured_dsn
    print(json.dumps(migrate(configured_dsn()),ensure_ascii=False,sort_keys=True))


if __name__=="__main__":main()
