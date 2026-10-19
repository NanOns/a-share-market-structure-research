"""Migrate each exact legacy journal registry pointer to fixed v4 heads."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys

import psycopg
from psycopg import sql
from psycopg.types.json import Jsonb

SOURCES=("v4_journal_registry_0ce03c8f18ae940a","v4_journal_registry_dbe184da961f97b8")


def canonical(value):
    return json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(",",":"),allow_nan=False).encode("utf-8")


def digest(value):return hashlib.sha256(value).hexdigest()


def migrate(dsn):
    sys.path.insert(0,"src")
    from workbench_db.v4_research_release_pg_r1 import load_release
    results=[]
    with psycopg.connect(dsn,connect_timeout=5) as pg:
        identity=pg.execute("SELECT current_database(),inet_server_addr()::text,inet_server_port() FROM pg_stat_activity WHERE pid=pg_backend_pid()").fetchone()
        if identity[0]!="market_research" or identity[1] not in ("127.0.0.1","127.0.0.1/32") or identity[2]!=5432:
            raise RuntimeError("V4_JOURNAL_REGISTRY_DATABASE_IDENTITY_MISMATCH")
        pg.execute("SET LOCAL statement_timeout='120s'")
        pg.execute("SET LOCAL lock_timeout='5s'")
        for source in SOURCES:
            relation=sql.SQL("{}.journal_heads").format(sql.Identifier(source))
            rows=pg.execute(sql.SQL("SELECT key,contract,descriptor::text FROM {} ORDER BY key COLLATE \"C\"").format(relation)).fetchall()
            migrated=[]
            for registry_key,contract,old_text in rows:
                old=json.loads(old_text)
                release_id=old.get("release_id")
                if (not isinstance(old.get("schema"),str)
                        or not old.get("schema").startswith("v4_research_")
                        or old.get("registry_key")!=registry_key
                        or old.get("journal_contract")!=contract
                        or old.get("contract_id")!="V4_PG_RESEARCH_SNAPSHOT_R2"
                        or not isinstance(release_id,str)):
                    raise RuntimeError("V4_JOURNAL_REGISTRY_SOURCE_DESCRIPTOR_INVALID:"+source)
                release=pg.execute("SELECT source_schema,contract_id,legacy_digest,original_descriptor,original_descriptor_sha256,sealed,storage_kind FROM v4.research_releases WHERE release_id=%s",(release_id,)).fetchone()
                if not release or release[0]!=old.get("schema") or release[1]!="V4_PG_RESEARCH_SNAPSHOT_R2" or not release[5] or release[6]!="journal":
                    raise RuntimeError("V4_JOURNAL_REGISTRY_RELEASE_NOT_MIGRATED:"+release_id)
                legacy_descriptor=bytes(release[3])
                if digest(legacy_descriptor)!=str(release[4]).strip():
                    raise RuntimeError("V4_JOURNAL_REGISTRY_LEGACY_DESCRIPTOR_SHA_MISMATCH:"+release_id)
                frozen=json.loads(legacy_descriptor.decode("utf-8"))
                if (frozen.get("schema"),frozen.get("release_id"),frozen.get("logical_digest"))!=(old.get("schema"),release_id,old.get("logical_digest")):
                    raise RuntimeError("V4_JOURNAL_REGISTRY_FROZEN_DESCRIPTOR_MISMATCH:"+release_id)
                canonical_descriptor,_,kind=load_release(pg,release_id,verify_content=True)
                if kind!="journal" or canonical_descriptor.get("registry_key")!=registry_key or canonical_descriptor.get("registry_schema")!="v4":
                    raise RuntimeError("V4_JOURNAL_REGISTRY_CANONICAL_DESCRIPTOR_INVALID:"+release_id)
                old_sha=str(release[4]).strip();new_raw=canonical(canonical_descriptor);new_sha=digest(new_raw)
                proof=dict(status="VERIFIED",source_schema=source,registry_key=registry_key,
                    legacy_release_id=release_id,legacy_descriptor_sha256=old_sha,
                    canonical_release_id=release_id,canonical_descriptor_sha256=new_sha,
                    research_release_original_descriptor_sha256=str(release[4]).strip(),
                    content_manifest=canonical_descriptor["content_manifest"])
                with pg.transaction():
                    prior=pg.execute("SELECT canonical_release_id,legacy_descriptor_sha256,canonical_descriptor_sha256,canonical_descriptor,verification FROM v4.journal_registry_migration_map_r1 WHERE source_schema=%s AND registry_key=%s",(source,registry_key)).fetchone()
                    expected=(release_id,old_sha,new_sha,canonical_descriptor,proof)
                    if prior and prior!=expected:
                        raise RuntimeError("V4_JOURNAL_REGISTRY_MIGRATION_RECEIPT_CONFLICT:"+registry_key)
                    current=pg.execute("SELECT contract,descriptor FROM v4.journal_heads WHERE key=%s",(registry_key,)).fetchone()
                    target=(contract,canonical_descriptor)
                    if current and current!=target:
                        raise RuntimeError("V4_JOURNAL_REGISTRY_TARGET_CONFLICT:"+registry_key)
                    if not current:
                        pg.execute("INSERT INTO v4.journal_heads(key,contract,descriptor) VALUES(%s,%s,%s)",(registry_key,contract,Jsonb(canonical_descriptor)))
                    if not prior:
                        pg.execute("INSERT INTO v4.journal_registry_migration_map_r1(source_schema,registry_key,journal_contract,legacy_release_id,legacy_descriptor_sha256,canonical_release_id,canonical_descriptor_sha256,canonical_descriptor,verification) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                            (source,registry_key,contract,release_id,old_sha,release_id,new_sha,Jsonb(canonical_descriptor),Jsonb(proof)))
                migrated.append(dict(source_schema=source,registry_key=registry_key,release_id=release_id,
                    old_descriptor_sha256=old_sha,canonical_descriptor_sha256=new_sha,status="VERIFIED"))
            results.append(dict(source_schema=source,registry_rows=len(rows),migrated_rows=len(migrated),results=migrated))
    return dict(status="MIGRATED_AND_VERIFIED",database=identity,target_schema="v4",results=results)


def main():
    parser=argparse.ArgumentParser();parser.add_argument("--apply",action="store_true");args=parser.parse_args()
    if not args.apply:raise SystemExit("Refusing database writes without --apply")
    sys.path.insert(0,"src")
    from workbench_db.v4_native import configured_dsn
    print(json.dumps(migrate(configured_dsn()),ensure_ascii=False,sort_keys=True))


if __name__=="__main__":main()
