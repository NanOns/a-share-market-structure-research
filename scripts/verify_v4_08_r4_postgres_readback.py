"""Insert the candidate into a disposable PostgreSQL 18 DB and verify formal view."""
from __future__ import annotations
from collections import Counter
import json
from pathlib import Path
import sys
import psycopg
from psycopg.types.json import Jsonb
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from build_v4_08_r2_membership_evidence import atomic_json
from materialize_v4_08_r4_pit_candidate import FACTS,REVISION,SNAPSHOT,read,rows_from_gzip
from run_v4_08_r3_isolated_verification import disposable_cluster,apply_migrations,verify_schema

def main():
    independent=read('reports/v4_08/V4_08_R4_PIT_INDEPENDENT_POSTCHECK.json')
    if independent['status']!='PASS':raise ValueError('INDEPENDENT_PIT_VERIFICATION_REQUIRED')
    revision=read(REVISION);snapshot=read(SNAPSHOT);facts=rows_from_gzip(FACTS)
    checks={};result=None
    with disposable_cluster(Path(r'E:\Postgres\bin')) as (dsn,temp):
        with psycopg.connect(dsn) as pg:
            migrations=apply_migrations(pg)
            schema_checks=verify_schema(pg)
            if not all(schema_checks.values()):raise ValueError('MIGRATION_001_019_SCHEMA_GATE_FAILED')
            pg.execute('''INSERT INTO v4.sector_membership_source_revisions
            (source_revision_id,source_contract_id,source_digest,source_file_digests,observed_at,ingested_at,system_available_at,provider_available_at,membership_asof_date,membership_basis,supersedes_revision_id,source_bytes_digest,temporal_evidence_digest,temporal_evidence,provider_available_at_basis,membership_asof_basis,revision_quality)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)''',
            (revision['source_revision_id'],revision['source_contract_id'],revision['source_digest'],Jsonb(revision['source_file_digests']),revision['observed_at'],revision['ingested_at'],revision['system_available_at'],revision['provider_available_at'],revision['membership_asof_date'],revision['membership_basis'],revision['supersedes_revision_id'],revision['source_bytes_digest'],revision['temporal_evidence_digest'],Jsonb(revision['temporal_evidence']),revision['provider_available_at_basis'],revision['membership_asof_basis'],revision['revision_quality']))
            pg.execute('''INSERT INTO v4.sector_membership_snapshots
            (snapshot_id,target_trade_date,cutoff,sector_type_registry_digest,source_revision_id,source_digest,source_file_digests,membership_basis,membership_quality,pit_observed,historical_backtest_safe,row_count,supersedes_snapshot_id,snapshot_lineage_role)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)''',
            (snapshot['snapshot_id'],snapshot['target_trade_date'],snapshot['cutoff'],snapshot['sector_type_registry_digest'],snapshot['source_revision_id'],snapshot['source_digest'],Jsonb(snapshot['source_file_digests']),snapshot['membership_basis'],snapshot['membership_quality'],snapshot['pit_observed'],snapshot['historical_backtest_safe'],snapshot['row_count'],snapshot['supersedes_snapshot_id'],snapshot['snapshot_lineage_role']))
            insert='''INSERT INTO v4.sector_membership_facts
            (membership_fact_id,snapshot_id,source_revision_id,sector_id,sector_code,sector_name,sector_type,source_sector_type,source_security_key,security_id,identity_status,target_trade_date,membership_asof_date,cutoff,membership_basis,membership_quality,pit_observed,historical_backtest_safe,supersedes_revision_id)
            VALUES (%(membership_fact_id)s,%(snapshot_id)s,%(source_revision_id)s,%(sector_id)s,%(sector_code)s,%(sector_name)s,%(sector_type)s,%(source_sector_type)s,%(source_security_key)s,%(security_id)s,%(identity_status)s,%(target_trade_date)s,%(membership_asof_date)s,%(cutoff)s,%(membership_basis)s,%(membership_quality)s,%(pit_observed)s,%(historical_backtest_safe)s,%(supersedes_revision_id)s)'''
            with pg.cursor() as cursor:cursor.executemany(insert,facts)
            checks['all_formal_candidate_facts_inserted']=pg.execute('SELECT count(*) FROM v4.sector_membership_facts WHERE snapshot_id=%s',(snapshot['snapshot_id'],)).fetchone()[0]==snapshot['row_count']
            readback=pg.execute('''SELECT f.sector_type,count(*),count(DISTINCT f.sector_id),count(DISTINCT f.security_id),
                bool_and(f.membership_basis='PIT_OBSERVED' AND f.membership_quality='PIT_OBSERVED_ACCEPTED'
                AND f.target_trade_date=DATE '2026-09-30' AND f.membership_asof_date=f.target_trade_date
                AND f.identity_status='MAPPED' AND f.security_id IS NOT NULL
                AND f.pit_observed AND f.historical_backtest_safe
                AND r.revision_quality='PIT_OBSERVED_ACCEPTED'
                AND r.membership_basis='PIT_OBSERVED' AND s.membership_basis='PIT_OBSERVED'
                AND r.provider_available_at<=s.cutoff AND r.system_available_at<=s.cutoff
                AND (r.temporal_evidence->>'revision_chain_valid')::boolean)
                FROM v4.formal_sector_membership f JOIN v4.sector_membership_snapshots s USING(snapshot_id)
                JOIN v4.sector_membership_source_revisions r ON r.source_revision_id=f.source_revision_id
                WHERE f.snapshot_id=%s GROUP BY f.sector_type ORDER BY f.sector_type''',(snapshot['snapshot_id'],)).fetchall()
            result=[{'sector_type':x[0],'row_count':x[1],'unique_sectors':x[2],'unique_members':x[3],'all_contract_predicates_true':x[4]} for x in readback]
            checks['formal_view_readback_counts_and_quality_match_artifact']=sum(x['row_count'] for x in result)==snapshot['row_count'] and {x['sector_type']:x['row_count'] for x in result}==Counter(x['sector_type'] for x in facts)
            checks['every_formal_readback_row_satisfies_identity_temporal_and_chain_contract']=all(x['all_contract_predicates_true'] for x in result)
            checks['formal_view_has_no_STYLE_UNKNOWN_or_DERIVED_PARENT']=pg.execute("SELECT count(*) FROM v4.formal_sector_membership WHERE snapshot_id=%s AND sector_type NOT IN ('INDUSTRY','THEME')",(snapshot['snapshot_id'],)).fetchone()[0]==0
            checks['no_mixed_basis_in_database_snapshot']=pg.execute("SELECT count(*) FROM v4.sector_membership_facts WHERE snapshot_id=%s AND membership_basis<>'PIT_OBSERVED'",(snapshot['snapshot_id'],)).fetchone()[0]==0
            checks['positive_candidate_is_visible_only_by_exact_snapshot']=pg.execute('SELECT count(*) FROM v4.formal_sector_membership WHERE snapshot_id=%s',(snapshot['snapshot_id'],)).fetchone()[0]==snapshot['row_count']
            # A forged STYLE fact is transaction-local negative proof; the formal view must not expose it.
            poison=dict(facts[0]);poison.update(membership_fact_id='f'*64,sector_id='STYLE:R4_NEGATIVE_VECTOR',sector_code='R4_NEGATIVE_VECTOR',sector_name='synthetic negative vector',sector_type='STYLE',source_sector_type='style',source_security_key=poison['source_security_key'])
            pg.execute('SAVEPOINT style_negative_vector')
            pg.execute(insert,poison)
            checks['negative_STYLE_fact_is_excluded_by_formal_view']=pg.execute("SELECT count(*) FROM v4.formal_sector_membership WHERE snapshot_id=%s AND sector_type='STYLE'",(snapshot['snapshot_id'],)).fetchone()[0]==0
            pg.execute('ROLLBACK TO SAVEPOINT style_negative_vector')
            checks['negative_vector_rolled_back']=pg.execute('SELECT count(*) FROM v4.sector_membership_facts WHERE membership_fact_id=%s',('f'*64,)).fetchone()[0]==0
            identity=pg.execute("SELECT current_database(),current_user,inet_server_addr()::text,inet_server_port(),version(),datcollate,datctype FROM pg_database WHERE datname=current_database()").fetchone()
            result={'status':'PASS' if all(checks.values()) else 'FAIL','database_identity':dict(zip(['database','owner','server_address','server_port','version','datcollate','datctype'],identity)),'migrations':migrations,'checks':checks,'formal_view_counts':result,'config_dot_env_read':False,'configured_or_production_database_used':False,'dsn_source':'PROCESS_ENVIRONMENT_DISPOSABLE_CLUSTER','temporary_cluster_destroyed':True,'credentials_persisted':False,'tested_snapshot_id':snapshot['snapshot_id']}
    atomic_json(ROOT/'reports/v4_08/V4_08_R4_PIT_FORMAL_VIEW_READBACK.json',result)
    print(json.dumps({'status':result['status'],'checks':result['checks'],'formal_view_counts':result['formal_view_counts'],'database_identity':result['database_identity']}))
    return 0 if result['status']=='PASS' else 1

if __name__=='__main__':raise SystemExit(main())
