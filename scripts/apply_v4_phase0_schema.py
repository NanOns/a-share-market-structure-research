"""Apply the hash-checked, transactional V4 Phase 0 PostgreSQL foundation."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
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
    "046_v4_workspace_namespace_alias_r1.sql":"V4_PG_WORKSPACE_NAMESPACE_ALIAS_R1",
    "047_v4_workspace_namespace_alias_central_schema_r1.sql":"V4_PG_WORKSPACE_NAMESPACE_ALIAS_CENTRAL_SCHEMA_R1",
    "048_v4_single_schema_research_storage_r1.sql":"V4_SINGLE_SCHEMA_RESEARCH_STORAGE_R1",
    "049_v4_single_schema_research_immutability_r1.sql":"V4_SINGLE_SCHEMA_RESEARCH_IMMUTABILITY_R1",
    "050_v4_forward_r7_single_schema_r1.sql":"V4_FORWARD_R7_SINGLE_SCHEMA_R1",
    "054_v4_forward_r7_namespace_identity_r1.sql":"V4_FORWARD_R7_NAMESPACE_IDENTITY_R1",
    "051_v4_history_single_schema_r1.sql":"V4_HISTORY_SINGLE_SCHEMA_R1",
    "052_v4_read_index_single_schema_r1.sql":"V4_READ_INDEX_SINGLE_SCHEMA_R1",
    "053_v4_daily_jobs_single_schema_r1.sql":"V4_DAILY_JOBS_SINGLE_SCHEMA_R1",
    "055_v4_read_index_r2_digest_identity_r1.sql":"V4_READ_INDEX_R2_DIGEST_IDENTITY_R1",
    "056_v4_owner_single_schema_storage_r1.sql":"V4_OWNER_SINGLE_SCHEMA_STORAGE_R1",
    "057_v4_schema_migration_ledger_r1.sql":"V4_SCHEMA_MIGRATION_LEDGER_R1",
    "058_v4_legacy_job_history_r1.sql":"V4_LEGACY_JOB_HISTORY_R1",
    "059_v4_forward_workspace_namespaces_r1.sql":"V4_FORWARD_WORKSPACE_NAMESPACES_R1",
    "060_v4_forward_source_lookup_indexes_r1.sql":"V4_FORWARD_SOURCE_LOOKUP_INDEXES_R1",
    "061_v4_journal_registry_single_schema_r1.sql":"V4_JOURNAL_REGISTRY_SINGLE_SCHEMA_R1",
    "062_v4_forward_r7_namespace_ordinal_r1.sql":"V4_FORWARD_R7_NAMESPACE_ORDINAL_R1",
    "063_v4_workspace_alias_history_only_r1.sql":"V4_WORKSPACE_ALIAS_HISTORY_ONLY_R1",
    "064_v4_forward_schema_retirement_r1.sql":"V4_FORWARD_SCHEMA_RETIREMENT_R1",
    "065_v4_publication_owner_single_schema_guard_r1.sql":"V4_PUBLICATION_OWNER_SINGLE_SCHEMA_GUARD_R1",
    "066_v4_publication_owner_receipt_guard_r1.sql":"V4_PUBLICATION_OWNER_RECEIPT_GUARD_R1",
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
    if value: return value
    import sys
    sys.path.insert(0,str(ROOT/"src"))
    from workbench_db.v4_native import configured_dsn
    return configured_dsn()

def verified_legacy_ledger_transition(cur,version,recorded_checksum,recorded_contract):
    """Accept only the observed pre-consolidation 057 ledger hash when its exact target exists."""
    if (version!="V4_SCHEMA_MIGRATION_LEDGER_R1"
            or recorded_contract!=version
            or recorded_checksum.strip()!="509e66d6ee070c5d38b93fdce5f195c87aefc10f0ad64b983e2399b0088116ce"):
        return False
    if cur.execute("select to_regclass('v4.schema_migrations'),to_regnamespace('v4_meta')").fetchone()!=("v4.schema_migrations",None):
        return False
    columns=cur.execute("""select column_name,data_type,is_nullable,character_maximum_length
        from information_schema.columns where table_schema='v4' and table_name='schema_migrations'
        order by ordinal_position""").fetchall()
    expected=[("version","text","NO",None),("checksum_sha256","character","NO",64),
              ("applied_at","timestamp with time zone","NO",None),("contract_id","text","NO",None)]
    primary_key=cur.execute("""select pg_get_constraintdef(oid) from pg_constraint
        where conrelid='v4.schema_migrations'::regclass and contype='p'""").fetchone()
    return columns==expected and primary_key==("PRIMARY KEY (version)",)

def apply():
    applied=[]
    with psycopg.connect(dsn()) as pg:
        identity=pg.execute("""select current_database(),pg_get_userbyid(datdba),pg_encoding_to_char(encoding),datcollate,datctype,
            inet_server_addr()::text,inet_server_port(),current_setting('transaction_read_only')
            from pg_database where datname=current_database()""").fetchone()
        if identity != ("market_research","postgres","UTF8","Chinese (Simplified)_China.936","Chinese (Simplified)_China.936","127.0.0.1/32",5432,"off"):
            raise RuntimeError("DATABASE_IDENTITY_OR_WRITE_CONTEXT_MISMATCH")
        # The historical 001 migration created v4_meta.  Keep its source file
        # and checksum immutable, but route its ledger into the sole business
        # schema when this runner executes it.
        pg.execute("CREATE SCHEMA IF NOT EXISTS v4")
        pg.execute("""CREATE TABLE IF NOT EXISTS v4.schema_migrations (
            version text PRIMARY KEY, checksum_sha256 char(64) NOT NULL,
            applied_at timestamptz NOT NULL, contract_id text NOT NULL)""")
        if pg.execute("SELECT to_regclass('v4_meta.schema_migrations')").fetchone()[0]:
            pg.execute("""INSERT INTO v4.schema_migrations(version,checksum_sha256,applied_at,contract_id)
                SELECT version,checksum_sha256,applied_at,contract_id FROM v4_meta.schema_migrations
                ON CONFLICT(version) DO NOTHING""")
            mismatch=pg.execute("""SELECT count(*) FROM v4_meta.schema_migrations old
                LEFT JOIN v4.schema_migrations new USING(version)
                WHERE new.version IS NULL OR new.checksum_sha256<>old.checksum_sha256
                   OR new.contract_id<>old.contract_id""").fetchone()[0]
            if mismatch: raise RuntimeError("V4_SCHEMA_MIGRATION_LEDGER_COPY_CONFLICT")
        pg.commit()
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
                exists=cur.execute("select to_regclass('v4.schema_migrations')").fetchone()[0]
                if exists:
                    old=cur.execute("select checksum_sha256,contract_id from v4.schema_migrations where version=%s",(version,)).fetchone()
                    if old:
                        if old[0].strip()!=checksum:
                            if verified_legacy_ledger_transition(cur,version,old[0],old[1]):
                                applied.append({"version":version,"checksum_sha256":checksum,"status":"ALREADY_APPLIED_COMPATIBILITY_VERIFIED"})
                                continue
                            raise RuntimeError(f"V4_MIGRATION_CHECKSUM_CONFLICT:{version}")
                        applied.append({"version":version,"checksum_sha256":checksum,"status":"ALREADY_APPLIED"})
                        continue
                schema_targets={m.group(1).strip('"').casefold() for m in re.finditer(
                    r'(?im)^\s*CREATE\s+SCHEMA\s+(?:IF\s+NOT\s+EXISTS\s+)?("?[a-z_][a-z0-9_]*"?)',text)}
                if schema_targets-{'v4','v4_meta'}:
                    raise RuntimeError('V4_SINGLE_SCHEMA_MIGRATION_SCHEMA_CREATE_BLOCKED:'+','.join(sorted(schema_targets-{'v4'})))
                if 'v4_meta' in schema_targets or 'v4_meta.' in text:
                    text=re.sub(r'(?im)^\s*CREATE\s+SCHEMA\s+IF\s+NOT\s+EXISTS\s+v4_meta\s*;\s*','',text)
                    text=text.replace('v4_meta.schema_migrations','v4.schema_migrations')
                try:
                    cur.execute(text)
                except Exception as exc:
                    raise RuntimeError(f"V4_MIGRATION_EXECUTION_FAILED:{filename}") from exc
                cur.execute("insert into v4.schema_migrations(version,checksum_sha256,applied_at,contract_id) values (%s,%s,now(),%s) on conflict(version) do nothing",(version,checksum,version))
                applied.append({"version":version,"checksum_sha256":checksum,"status":"APPLIED"})
    with psycopg.connect(dsn()) as pg:
        table_count = pg.execute("select count(*) from information_schema.tables where table_schema='v4'").fetchone()[0]
        ledger_count = pg.execute("select count(*) from information_schema.tables where table_schema='v4' and table_name='schema_migrations'").fetchone()[0]
    return {"status":"APPLIED" if any(x['status']=='APPLIED' for x in applied) else "ALREADY_CURRENT","migrations":applied,"v4_table_count":table_count,"migration_ledger_table_count":ledger_count}

if __name__=="__main__":
    ap=argparse.ArgumentParser(); ap.add_argument("--apply",action="store_true"); args=ap.parse_args()
    if not args.apply: raise SystemExit("Refusing DB mutation without --apply")
    print(json.dumps(apply()))
