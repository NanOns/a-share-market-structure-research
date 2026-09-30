"""Clean detached regression and 022 acceptance in a destroyed disposable cluster."""
from copy import deepcopy
from datetime import datetime,timezone
from pathlib import Path
import json
import os
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'src'))
from scripts.run_v4_08_r2_regression import REQUIRED_FAMILIES
from scripts.run_v4_08_r3_isolated_verification import disposable_cluster,apply_migrations,verify_schema
from scripts.build_v4_08_r2_membership_evidence import atomic_json
from scripts.verify_v4_08_r5_1 import compact_scan
from scripts.promote_v4_09_accepted_head import validate,bind
from scripts.verify_v4_10_state_reducer import check_vectors
from scripts.freeze_v4_10_contract import fixture,with_prior
from src.v4.research_state import reduce_state,digest
from src.v4.research_state_persistence import persist

def git(*args):
    return subprocess.run(['git',*args],cwd=ROOT,capture_output=True,text=True,check=True).stdout.strip()

def schema_acceptance(pg):
    import psycopg
    migrations=apply_migrations(pg);checks=verify_schema(pg)
    a=reduce_state(fixture()); x=fixture('SECTOR');x['entity_id']='fixture-sector';b=reduce_state(x)
    rows=[a,b];first=persist(pg,rows,'V4_10_FIXTURE_T');retry=persist(pg,rows,'V4_10_FIXTURE_T')
    checks['022_exact_readback']=first['row_count']==2 and first==retry
    revised=[]
    for row in rows:
        x=fixture(row['entity_type']);x['entity_id']=row['entity_id'];x['session_index']=21;x['trade_date']='2026-09-29'
        revised.append(reduce_state(with_prior(x,row)))
    second=persist(pg,revised,'V4_10_FIXTURE_T_REVISION_2','V4_10_FIXTURE_T')
    checks['022_revision_append_old_payload_preserved']=persist(pg,rows,'V4_10_FIXTURE_T')==first and pg.execute('SELECT count(*) FROM v4.research_state_engineering_results').fetchone()[0]==4
    changed=deepcopy(rows);changed[0]['health']='IMPROVING'
    payload=dict(changed[0]);payload.pop('publication_id');changed[0]['publication_id']='V4_10:'+digest(payload)
    try:persist(pg,changed,'V4_10_FIXTURE_T')
    except ValueError as e:checks['022_same_publication_conflict_rejected']='APPEND_ONLY_STATE_PUBLICATION_CONFLICT' in str(e)
    else:checks['022_same_publication_conflict_rejected']=False
    try:persist(pg,rows,'V4_10_FIXTURE_T',revision_of='V4_10_FIXTURE_T_REVISION_2')
    except ValueError:checks['022_revision_identity_conflict_rejected']=True
    else:checks['022_revision_identity_conflict_rejected']=False
    def rejected(sql,params=(),phrase=None):
        try:
            with pg.transaction():pg.execute(sql,params)
        except psycopg.Error as e:return phrase is None or phrase in str(e)
        return False
    for table in ['research_state_engineering_publications','research_state_engineering_results']:
        checks['022_'+table+'_update_rejected']=rejected(f'UPDATE v4.{table} SET publication_id=publication_id')
        checks['022_'+table+'_delete_rejected']=rejected(f'DELETE FROM v4.{table}')
    # Direct SQL probes prove the trigger, independently of the persistence helper.
    checks['022_payload_column_mismatch_rejected']=rejected('''INSERT INTO v4.research_state_engineering_results
        SELECT publication_id,state_publication_id,entity_id||':evil',entity_type,episode_key,episode_id,parent_episode_id,
            trade_date,session_index,model_contract_id,parameter_set_id,maturity,health,validity,tracking,scenario,
            state_freshness,final_eligibility,prior_state_binding,input_publication_ids,matched_predicates,unknown_predicates,
            transition_reasons,payload,payload_digest FROM v4.research_state_engineering_results LIMIT 1''',phrase='RESEARCH_STATE_PAYLOAD_COLUMN_MISMATCH')
    checks['022_publication_parameter_mismatch_rejected']=rejected('''INSERT INTO v4.research_state_engineering_results
        SELECT publication_id,state_publication_id,entity_id||':evil',entity_type,episode_key,episode_id,parent_episode_id,
            trade_date,session_index,model_contract_id,'WRONG_PARAMETER',maturity,health,validity,tracking,scenario,
            state_freshness,final_eligibility,prior_state_binding,input_publication_ids,matched_predicates,unknown_predicates,
            transition_reasons,payload,payload_digest FROM v4.research_state_engineering_results LIMIT 1''',phrase='RESEARCH_STATE_PUBLICATION_BINDING_MISMATCH')
    prior=pg.execute("SELECT payload->'prior_state_binding',prior_state_binding,input_publication_ids FROM v4.research_state_engineering_results WHERE publication_id='V4_10_FIXTURE_T_REVISION_2'").fetchall()
    checks['022_explicit_prior_input_publication_bindings']=all(a==b and b['publication_id'] and len(c)>0 for a,b,c in prior)
    tables=lambda:{r[0] for r in pg.execute("SELECT tablename FROM pg_tables WHERE schemaname='v4'").fetchall()}
    funcs=lambda:{r[0] for r in pg.execute("SELECT oid::regprocedure::text FROM pg_proc WHERE pronamespace='v4'::regnamespace").fetchall()}
    before_tables=tables();before_funcs=funcs()
    with pg.transaction():
        pg.execute('SAVEPOINT rollback_022')
        pg.execute((ROOT/'src/workbench_db/migrations/v4_postgres/rollback/022_v4_10_research_state_interface.sql').read_text(encoding='utf8'))
        checks['022_rollback_only_new_objects']=before_tables-tables()=={'research_state_engineering_results','research_state_engineering_publications'} and before_funcs-funcs()=={'v4.guard_research_state_engineering_binding()'}
        pg.execute('ROLLBACK TO SAVEPOINT rollback_022')
    checks['022_rollback_restore_exact']=persist(pg,rows,'V4_10_FIXTURE_T')==first and persist(pg,revised,'V4_10_FIXTURE_T_REVISION_2','V4_10_FIXTURE_T')==second
    return dict(contract_id='V4_10_SCHEMA_MIGRATION_RECEIPT_V1',status='PASS' if all(checks.values()) else 'FAIL',checks=checks,
        migrations=migrations,readback=first,revision_readback=second,config_dot_env_read=False,configured_or_production_database_used=False,
        consumer_contract_id='V4_10_REDUCER_INTERFACE_V1',scope='DISPOSABLE_SYNTHETIC_ENGINEERING_ONLY')

def main():
    before=git('status','--porcelain=v1');head=git('rev-parse','HEAD');started=time.monotonic()
    if before or git('branch','--show-current') or (ROOT/'config/.env').exists():raise ValueError('CLEAN_DETACHED_WITHOUT_DOT_ENV_REQUIRED')
    promotion=validate();post,coverage=check_vectors()
    if promotion['status']!='PASS' or post['status']!='PASS':raise ValueError('PROMOTION_OR_INDEPENDENT_VECTORS_FAILED')
    with disposable_cluster(Path(r'E:\Postgres\bin')) as (dsn,temp):
        import psycopg
        with psycopg.connect(dsn) as pg:
            identity=pg.execute('SELECT current_database(),current_user,inet_server_addr()::text,inet_server_port(),version()').fetchone()
            schema=schema_acceptance(pg)
            schema.update(tested_commit=head,database_identity=dict(zip(['database','owner','server_address','server_port','version'],identity)))
            if schema['status']!='PASS':raise ValueError(schema['checks'])
        guard=temp/'guard';guard.mkdir()
        (guard/'sitecustomize.py').write_bytes(b"import sys,os\ndef forbid(event,args):\n if event=='open' and isinstance(args[0],(str,bytes,os.PathLike)) and os.fsdecode(args[0]).replace('\\\\','/').lower().endswith('/config/.env'): raise RuntimeError('CONFIG_DOT_ENV_READ_FORBIDDEN')\nsys.addaudithook(forbid)\n")
        env=os.environ.copy();env['WORKBENCH_PG_DSN']=dsn;env['PYTHONPATH']=str(guard)+os.pathsep+str(ROOT)+os.pathsep+env.get('PYTHONPATH','')
        for key in ['PGPASSWORD','PGSERVICE','PGSERVICEFILE']:env.pop(key,None)
        families=[*REQUIRED_FAMILIES,'tests/v4_09','tests/v4_10','tests/test_fixed_qfq_samples.py','tests/test_phase0_2a_gate.py',
            'tests/test_phase1_qa_sample_selector.py','tests/governance/test_no_symbol_specific_runtime_logic.py']
        junit=temp/'junit.xml'
        obsolete='tests/v4_09/test_stock_prewatch.py::test_production_and_v4_09_acceptance_stay_disabled'
        run=subprocess.run([sys.executable,'-m','pytest','-q',*families,'--deselect='+obsolete,f'--junitxml={junit}'],cwd=ROOT,env=env,
            capture_output=True,text=True,encoding='utf8',errors='replace',timeout=1200)
        suites=list(ET.parse(junit).getroot().iter('testsuite')) if junit.exists() else []
        summary={k:sum(int(s.attrib.get(k,0)) for s in suites) for k in ['tests','failures','errors','skipped']}
        summary['passed']=summary['tests']-summary['failures']-summary['errors']-summary['skipped']
        regression=dict(contract_id='V4_10_ISOLATED_REGRESSION_V1',status='PASS' if run.returncode==0 and suites else 'FAIL',
            tested_commit=head,summary=summary,required_families=families,stdout=run.stdout,stderr=run.stderr,
            config_dot_env_read=False,configured_or_production_database_used=False,dsn_source='PROCESS_ENVIRONMENT_DISPOSABLE_CLUSTER',
            historical_test_supersession=dict(deselected_exact_node=obsolete,reason='Candidate-only absence guard superseded by externally authorized V4-09 accepted-head promotion',
                original_test_bytes_preserved=True,replacement='tests/v4_10/test_promotion.py: exact external decision/commits/upstream/artifact, permission false and overclaim rejection'))
    from scripts.scan_no_symbol_specific_runtime_logic import run as scan
    governance=scan(ROOT);governance['tested_commit']=head;after=git('status','--porcelain=v1')
    schema['temporary_cluster_destroyed']=True
    clean=dict(contract_id='V4_10_CLEAN_CHECKOUT_RECEIPT_V1',status='PASS_CLEAN_DETACHED_CHECKOUT' if not after and
        schema['status']=='PASS' and regression['status']=='PASS' and governance['status']=='PASS' else 'FAIL',
        tested_commit=head,detached_head=True,git_status_before=before,git_status_after=after,config_dot_env_present=False,
        config_dot_env_read=False,temporary_cluster_destroyed=True,promotion_validation=promotion,independent_vectors=post['status'],
        elapsed_seconds=round(time.monotonic()-started,3),created_at_utc=datetime.now(timezone.utc).isoformat())
    for name,value in [('SCHEMA_MIGRATION_RECEIPT',schema),('ISOLATED_REGRESSION',regression),('CLEAN_CHECKOUT_RECEIPT',clean),
            ('NO_SYMBOL_SPECIFIC_SYSTEM_LOGIC_SCAN',compact_scan(governance))]:
        atomic_json(ROOT/f'reports/v4_10/V4_10_{name}.json',value)
    print(json.dumps(dict(status=clean['status'],tested_commit=head,regression=summary,no_symbol=governance['status'],schema_checks=schema['checks'])))
    return clean['status']=='FAIL'

if __name__=='__main__':sys.exit(main())
