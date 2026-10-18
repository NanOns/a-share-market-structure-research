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
    "021_v4_09_stock_prewatch.sql":"V4_09_STOCK_PREWATCH_V1",
    "010_source_manifest_contract_r1.sql":"V4_PG_CONSUMED_SOURCE_MANIFEST_R1",
    "001_v4_phase0_foundation.sql":"V4_PHASE0_FOUNDATION_V1",
    "002_namespace_integrity.sql":"V4_PHASE0_NAMESPACE_INTEGRITY_V1",
    "003_phase0_contract_alignment.sql":"V4_PHASE0_CONTRACT_ALIGNMENT_R2",
    "004_publication_head_revision_identity.sql":"V4_PUBLICATION_HEAD_REVISION_IDENTITY_R2",
    "005_market_session_publication_chain.sql":"V4_MARKET_SESSION_PUBLICATION_CHAIN_R2",
    "006_fact_source_guard_table_specific_fields.sql":"V4_FACT_SOURCE_GUARD_TABLE_SPECIFIC_FIELDS_R2",
    "007_state_and_namespace_publication_identity.sql":"V4_STATE_AND_NAMESPACE_PUBLICATION_IDENTITY_R2",
    "008_prior_session_state_freeze_integrity.sql":"V4_PRIOR_SESSION_STATE_FREEZE_INTEGRITY_R3",
    "009_publication_head_guard_sql_alias_fix.sql":"V4_PUBLICATION_HEAD_GUARD_SQL_ALIAS_FIX_R3",
    "010_security_lifecycle_history_r5.sql":"V4_SECURITY_LIFECYCLE_HISTORY_R5_V1",
    "011_security_membership_interval_r6_2.sql":"V4_SECURITY_MEMBERSHIP_INTERVAL_R6_2_V1",
    "012_provider_lifecycle_fact_r6_2.sql":"V4_PROVIDER_LIFECYCLE_FACT_R6_2_V1",
    "013_v4_06_stock_profile_enrichments.sql":"V4_06_STOCK_PROFILE_ENRICHMENTS_V1",
    "034_source_package_revision_authority_r2.sql":"V4_SOURCE_PACKAGE_REVISION_AUTHORITY_R2",
    "035_source_manifest_contract_r2.sql":"V4_SOURCE_MANIFEST_CONTRACT_R2",
    "036_source_package_fact_provenance_r6.sql":"V4_SOURCE_PACKAGE_FACT_PROVENANCE_R6",
    "037_daily_core_result_binding_r6.sql":"V4_DAILY_CORE_RESULT_BINDING_R6",
    "038_publication_module_results_r4.sql":"V4_PUBLICATION_MODULE_RESULTS_R4",
    "039_tdx_package_row_count_authority_r1.sql":"V4_TDX_PACKAGE_ROW_COUNT_AUTHORITY_R1",
    "040_source_manifest_r3_fact_proof.sql":"V4_SOURCE_MANIFEST_R3_FACT_PROOF",
    "041_r3_effective_date_gate.sql":"V4_R3_EFFECTIVE_DATE_GATE_R1",
    "042_market_universe_persistence_r1.sql":"V4_MARKET_UNIVERSE_PERSISTENCE_R1",
    "044_operational_research_live_head_r1.sql":"V4_OPERATIONAL_RESEARCH_LIVE_HEAD_R1",
    "045_dm01_data_accepted_head_pg_r1.sql":"V4_DM01_DATA_ACCEPTED_HEAD_PG_R1",
}

def dsn():
    value=os.environ.get("V4_NATIVE_PG_DSN")
    if not value:
        env_path=ROOT/"config/.env"
        if env_path.is_file():
            lines=env_path.read_text("utf-8-sig").splitlines()
        else:
            lines=[]
        for raw in lines:
            key,sep,val=raw.partition("=")
            if sep and key.strip()=="V4_NATIVE_PG_DSN": value=val.strip().strip('"').strip("'"); break
    if not value: raise RuntimeError("V4_NATIVE_PG_DSN_REQUIRED")
    return value

def apply():
    applied=[]
    with psycopg.connect(dsn()) as pg:
        # Apply only the explicit, contract-registered foundation set. The
        # directory also contains feature migrations owned by other runners;
        # globbing every SQL file made this entrypoint fail on those unrelated
        # migrations and obscured the 034-038 publication chain.
        for filename,version in sorted(VERSIONS.items()):
            path=MIGRATIONS/filename
            if not path.is_file(): raise RuntimeError(f"REGISTERED_V4_MIGRATION_MISSING:{filename}")
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
    with psycopg.connect(dsn()) as pg:
        table_count = pg.execute("select count(*) from information_schema.tables where table_schema='v4'").fetchone()[0]
        ledger_count = pg.execute("select count(*) from information_schema.tables where table_schema='v4_meta'").fetchone()[0]
    return {"status":"APPLIED" if any(x['status']=='APPLIED' for x in applied) else "ALREADY_CURRENT","migrations":applied,"v4_table_count":table_count,"migration_ledger_table_count":ledger_count}

if __name__=="__main__":
    ap=argparse.ArgumentParser(); ap.add_argument("--apply",action="store_true"); args=ap.parse_args()
    if not args.apply: raise SystemExit("Refusing DB mutation without --apply")
    print(json.dumps(apply()))
