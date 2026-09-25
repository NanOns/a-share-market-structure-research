"""Apply the hash-checked, transactional V4 Phase 0 PostgreSQL foundation."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import psycopg

ROOT=Path(__file__).resolve().parents[1]
MIGRATIONS=ROOT/"src/workbench_db/migrations/v4_postgres"
VERSIONS={
    "001_v4_phase0_foundation.sql":"V4_PHASE0_FOUNDATION_V1",
    "002_namespace_integrity.sql":"V4_PHASE0_NAMESPACE_INTEGRITY_V1",
}

def dsn():
    value=os.environ.get("WORKBENCH_PG_DSN")
    if not value:
        for raw in (ROOT/"config/.env").read_text("utf-8-sig").splitlines():
            key,sep,val=raw.partition("=")
            if sep and key.strip()=="WORKBENCH_PG_DSN": value=val.strip().strip('"').strip("'"); break
    if not value: raise RuntimeError("WORKBENCH_PG_DSN_REQUIRED")
    return value

def apply():
    applied=[]
    with psycopg.connect(dsn()) as pg:
        for path in sorted(MIGRATIONS.glob("*.sql")):
            version=VERSIONS.get(path.name)
            if not version: raise RuntimeError(f"UNREGISTERED_V4_MIGRATION:{path.name}")
            text=path.read_text("utf-8"); checksum=hashlib.sha256(text.encode()).hexdigest()
            with pg.transaction():
                cur=pg.cursor()
                cur.execute("select current_database(), pg_get_userbyid(datdba), pg_encoding_to_char(encoding), datcollate, datctype from pg_database where datname=current_database()")
                identity=cur.fetchone()
                if identity != ("market_research","postgres","UTF8","Chinese (Simplified)_China.936","Chinese (Simplified)_China.936"):
                    raise RuntimeError("DATABASE_IDENTITY_MISMATCH")
                exists=cur.execute("select to_regclass('v4_meta.schema_migrations')").fetchone()[0]
                if exists:
                    old=cur.execute("select checksum_sha256 from v4_meta.schema_migrations where version=%s",(version,)).fetchone()
                    if old:
                        if old[0].strip()!=checksum: raise RuntimeError(f"V4_MIGRATION_CHECKSUM_CONFLICT:{version}")
                        applied.append({"version":version,"checksum_sha256":checksum,"status":"ALREADY_APPLIED"})
                        continue
                cur.execute(text)
                cur.execute("insert into v4_meta.schema_migrations(version,checksum_sha256,applied_at,contract_id) values (%s,%s,now(),%s) on conflict(version) do nothing",(version,checksum,version))
                applied.append({"version":version,"checksum_sha256":checksum,"status":"APPLIED"})
    return {"status":"APPLIED" if any(x['status']=='APPLIED' for x in applied) else "ALREADY_CURRENT","migrations":applied,"v4_table_count":13,"migration_ledger_table_count":1}

if __name__=="__main__":
    ap=argparse.ArgumentParser(); ap.add_argument("--apply",action="store_true"); args=ap.parse_args()
    if not args.apply: raise SystemExit("Refusing DB mutation without --apply")
    print(json.dumps(apply()))
