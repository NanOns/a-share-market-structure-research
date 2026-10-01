"""Independent 024 compatibility, role, append/revision and exact rollback receipts."""
from pathlib import Path
import json
import subprocess
from scripts.run_v4_10_r1_1_isolated_verification import seed_historical_022,schema_snapshot
from scripts.run_v4_08_r3_isolated_verification import verify_schema
from scripts.apply_v4_phase0_schema import VERSIONS
from scripts.promote_v4_09_accepted_head import bind
from scripts.verify_v4_10_r1_2 import check_vectors
from scripts.v4_10_r1_2_fixtures import *
from scripts.build_v4_10_r1_2_vectors import sector_unknown_bundle
ROOT=Path(__file__).resolve().parents[1]

def authority_snapshot(pg):
    return dict(schema=schema_snapshot(pg),roles=pg.execute("SELECT rolname,rolcanlogin,rolsuper,rolinherit FROM pg_roles ORDER BY rolname").fetchall(),
        grants=pg.execute("SELECT grantee,table_name,privilege_type,is_grantable FROM information_schema.role_table_grants WHERE table_schema='v4' ORDER BY grantee,table_name,privilege_type").fetchall())

def schema_acceptance(pg):
    import psycopg
    receipts=[];old022=None
    for path in sorted((ROOT/'src/workbench_db/migrations/v4_postgres').glob('*.sql')):
        if path.name.startswith('024_'):break
        pg.execute(path.read_text(encoding='utf8'))
        version=VERSIONS.get(path.name,'V4_STAGE_'+path.stem.upper());b=bind(path.relative_to(ROOT).as_posix())
        pg.execute('INSERT INTO v4_meta.schema_migrations VALUES (%s,%s,now(),%s)',(version,b['sha256'],version));receipts.append(b)
        if path.name.startswith('022_'):old022,_=seed_historical_022(pg)
    checks=verify_schema(pg)
    x,ms=accepted_bundle(19);publish_setup(pg,ms);historical=reduce_state(x,ledger=PostgresEngineeringLedger(pg))
    code=subprocess.run(['git','show','6049973cd78e51cdeb2ba33461f20ce96b13c8d6:src/v4/research_state_persistence.py'],cwd=ROOT,capture_output=True,check=True).stdout
    module={'__file__':str(ROOT/'src/v4/research_state_persistence.py'),'__name__':'src.v4.audited_r1_1_persistence','__package__':'src.v4'}
    exec(compile(code,module['__file__'],'exec'),module);module['persist'](pg,[historical],'R1_1_HISTORICAL_VALID_ROW')
    before=authority_snapshot(pg);old_rows=pg.execute('SELECT publication_id,payload,payload_digest FROM v4.research_state_engineering_results ORDER BY publication_id').fetchall()
    migration=ROOT/'src/workbench_db/migrations/v4_postgres/024_v4_10_research_state_authority_hardening.sql'
    rollback=ROOT/'src/workbench_db/migrations/v4_postgres/rollback/024_v4_10_research_state_authority_hardening.sql'
    pg.execute('SET CONSTRAINTS ALL IMMEDIATE');pg.execute('SET CONSTRAINTS ALL DEFERRED')
    pg.execute(migration.read_text(encoding='utf8'));receipts.append(bind(migration.relative_to(ROOT).as_posix()))
    read_old=lambda:pg.execute("SELECT publication_id,payload,payload_digest FROM v4.research_state_engineering_results WHERE publication_id IN ('AUDITED_R1_COMPATIBILITY','R1_1_HISTORICAL_VALID_ROW') ORDER BY publication_id").fetchall()
    checks['024_old_022_023_rows_byte_identity_readable']=read_old()==old_rows
    with pg.transaction():
        pg.execute('SAVEPOINT rollback_before_new_rows');pg.execute(rollback.read_text(encoding='utf8'))
        checks['024_rollback_before_new_rows_exact_023_schema_roles_grants']=authority_snapshot(pg)==before
        checks['024_rollback_before_new_rows_old_payloads']=read_old()==old_rows
        pg.execute('ROLLBACK TO SAVEPOINT rollback_before_new_rows')
    definitions=json.loads((ROOT/'config/v4_10_input_provenance_r1_2.json').read_text())['fields']
    keys=['producer_contract_id','producer_parameter_set_id','implemented','required','time_role','accepted_entity_types','not_applicable_entity_types']
    actual=pg.execute('SELECT field,'+','.join(keys)+' FROM v4.research_state_field_policy_r1_2 ORDER BY field COLLATE "C"').fetchall()
    checks['024_policy_exact_contract']=actual==[(field,*(d[k] for k in keys)) for field,d in sorted(definitions.items())]
    result,coverage=check_vectors(pg);checks['024_independent_vectors_and_permissions']=result['status']=='PASS'
    x,ms=accepted_bundle();sector,sms=sector_unknown_bundle();publish_setup(pg,ms+sms)
    with publisher_scope(pg):
        first=publish_state(pg,[x,sector],'R1_2_READBACK');retry=publish_state(pg,[x,sector],'R1_2_READBACK')
    checks['024_controlled_exact_readback_retry']=first==retry and first['row_count']==2
    rows=pg.execute("SELECT payload FROM v4.research_state_engineering_results WHERE publication_id='R1_2_READBACK' AND entity_type='STOCK'").fetchone()[0]
    nextx,ms=accepted_bundle(21,rows);nextx['prior_state_binding']['engineering_publication_id']='R1_2_READBACK';publish_setup(pg,ms)
    with publisher_scope(pg):second=publish_state(pg,[nextx],'R1_2_READBACK_REVISION_2','R1_2_READBACK')
    checks['024_revision_preserves_prior_and_old_payloads']=second['revision_of']=='R1_2_READBACK' and read_old()==old_rows
    try:
        with publisher_scope(pg):publish_state(pg,[nextx],'R1_2_READBACK')
    except ValueError as e:checks['024_same_publication_conflict_rejected']='APPEND_ONLY_STATE_PUBLICATION_CONFLICT' in str(e)
    else:checks['024_same_publication_conflict_rejected']=False
    for table in ['research_state_engineering_publications','research_state_engineering_results','research_state_input_manifests','research_state_boundary_prior_publications','research_state_field_policy_r1_2']:
        column='source_publication_id' if table=='research_state_boundary_prior_publications' else 'field' if table=='research_state_field_policy_r1_2' else 'publication_id'
        for operation in ['UPDATE','DELETE']:
            statement=f'UPDATE v4.{table} SET {column}={column}' if operation=='UPDATE' else f'DELETE FROM v4.{table}'
            try:
                with pg.transaction():pg.execute(statement)
            except psycopg.Error:checks['024_'+table+'_'+operation+'_rejected']=True
            else:checks['024_'+table+'_'+operation+'_rejected']=False
    with pg.transaction():
        pg.execute('SAVEPOINT protected_issuer_write')
        for table in ['research_state_input_manifests','research_state_boundary_prior_publications']:
            try:
                with pg.transaction():
                    pg.execute('SET LOCAL ROLE v4_10_reducer_publisher_r1_2');pg.execute(f'INSERT INTO v4.{table} SELECT * FROM v4.{table} LIMIT 1')
            except psycopg.Error as e:checks['024_publisher_cannot_register_'+table]='permission denied' in str(e)
            else:checks['024_publisher_cannot_register_'+table]=False
        pg.execute('ROLLBACK TO SAVEPOINT protected_issuer_write')
    pg.execute('SET CONSTRAINTS ALL IMMEDIATE');pg.execute('SET CONSTRAINTS ALL DEFERRED');after=authority_snapshot(pg)
    with pg.transaction():
        pg.execute('SAVEPOINT rollback_after_new_rows');pg.execute(rollback.read_text(encoding='utf8'))
        checks['024_rollback_after_new_rows_exact_023_schema_roles_grants']=authority_snapshot(pg)==before
        checks['024_rollback_retains_old_payloads']=read_old()==old_rows
        pg.execute('ROLLBACK TO SAVEPOINT rollback_after_new_rows')
    checks['024_restore_exact_new_schema_and_roles']=authority_snapshot(pg)==after
    for name in ['022_v4_10_research_state_interface.sql','023_v4_10_research_state_lineage_hardening.sql']:
        historical_bytes=subprocess.run(['git','show','db6319856468c6788c9dd656da3992e569a64572:src/workbench_db/migrations/v4_postgres/'+name],cwd=ROOT,capture_output=True,check=True).stdout
        checks[name+'_byte_identical']=(ROOT/'src/workbench_db/migrations/v4_postgres'/name).read_bytes()==historical_bytes
    return dict(contract_id='V4_10_R1_2_SCHEMA_MIGRATION_RECEIPT',status='PASS' if all(checks.values()) else 'FAIL',checks=checks,migrations=receipts,
        direct_sql_probes=result['sql_probes'],readback=first,revision_readback=second,old_rows_readable=True,
        trust_boundary='DB owner imports immutable old authority; controlled producer role alone inserts states after reduce/validation; ordinary application reads only',
        configured_or_production_database_used=False,config_dot_env_read=False),result,coverage
