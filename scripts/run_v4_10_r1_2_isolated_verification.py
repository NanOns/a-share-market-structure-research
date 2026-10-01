"""R1.1 clean detached regression, old-022 readback and independent 023 acceptance."""
from copy import deepcopy
from datetime import datetime,timezone
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'src'))
from scripts.run_v4_08_r2_regression import REQUIRED_FAMILIES
from scripts.run_v4_08_r3_isolated_verification import disposable_cluster,verify_schema
from scripts.apply_v4_phase0_schema import VERSIONS
from scripts.build_v4_08_r2_membership_evidence import atomic_json
from scripts.verify_v4_08_r5_1 import compact_scan
from scripts.promote_v4_09_accepted_head import validate,bind
from scripts.verify_v4_10_r1_2 import check_vectors,write_evidence
from scripts.v4_10_r1_1_fixtures import (accepted_bundle,publish_setup,synthetic_input,adapt_r1_input)
from src.v4.research_state import reduce_state,digest
from src.v4.state_identity import state_id
from src.v4.state_provenance import PostgresEngineeringLedger
from src.v4.research_state_persistence import persist

BASELINE='db6319856468c6788c9dd656da3992e569a64572'
OLD_IMPLEMENTATION='e3b29a434c57a94cc5fe68edc3de647862da4ec4'

def git(*args):return subprocess.run(['git',*args],cwd=ROOT,capture_output=True,text=True,check=True).stdout.strip()

def schema_snapshot(pg):
    return dict(tables=pg.execute("SELECT tablename FROM pg_tables WHERE schemaname='v4' ORDER BY tablename").fetchall(),
        columns=pg.execute("SELECT table_name,column_name,data_type,is_nullable,column_default FROM information_schema.columns WHERE table_schema='v4' ORDER BY table_name,ordinal_position").fetchall(),
        functions=pg.execute("SELECT oid::regprocedure::text,pg_get_functiondef(oid) FROM pg_proc WHERE pronamespace='v4'::regnamespace ORDER BY oid::regprocedure::text").fetchall(),
        triggers=pg.execute("SELECT c.relname,t.tgname,pg_get_triggerdef(t.oid) FROM pg_trigger t JOIN pg_class c ON c.oid=t.tgrelid WHERE c.relnamespace='v4'::regnamespace AND NOT t.tgisinternal ORDER BY c.relname,t.tgname").fetchall())

def seed_historical_022(pg):
    """Execute the exact audited R1 reducer for historical row compatibility, before 023."""
    from scripts.freeze_v4_10_contract import fixture
    from psycopg.types.json import Jsonb
    code=subprocess.run(['git','show',OLD_IMPLEMENTATION+':src/v4/research_state.py'],cwd=ROOT,capture_output=True,check=True).stdout
    module={'__file__':str(ROOT/'src/v4/research_state.py'),'__name__':'v4_10_audited_r1_compatibility'}
    exec(compile(code,str(ROOT/'src/v4/research_state.py'),'exec'),module)
    row=module['reduce_state'](fixture());checksum=module['digest']([row])
    pg.execute('''INSERT INTO v4.research_state_engineering_publications(publication_id,model_contract_id,consumer_contract_id,parameter_set_id,publication_digest,row_count,acceptance_scope)
        VALUES ('AUDITED_R1_COMPATIBILITY','RESEARCH_STATE_V1','V4_10_REDUCER_INTERFACE_V1','V4_10_STATE_REDUCER_PARAMETER_SET_V1',%s,1,'ENGINEERING_INTERFACE_ONLY')''',(checksum,))
    pg.execute('''INSERT INTO v4.research_state_engineering_results
        (publication_id,state_publication_id,entity_id,entity_type,episode_key,episode_id,parent_episode_id,trade_date,session_index,model_contract_id,parameter_set_id,maturity,health,validity,tracking,scenario,state_freshness,final_eligibility,prior_state_binding,input_publication_ids,matched_predicates,unknown_predicates,transition_reasons,payload,payload_digest)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)''',
        ('AUDITED_R1_COMPATIBILITY',row['publication_id'],row['entity_id'],row['entity_type'],row['episode_id'] or 'NO_EPISODE')+
        tuple(row[k] for k in ['episode_id','parent_episode_id','trade_date','session_index','model_contract_id','parameter_set_id','maturity','health','validity','tracking','scenario','state_freshness','final_eligibility'])+
        tuple(Jsonb(row[k]) for k in ['prior_state_binding','input_publication_ids','matched_predicates','unknown_predicates','transition_reasons'])+
        (Jsonb(row),module['digest'](row)))
    return row,checksum

from scripts.schema_v4_10_r1_2 import schema_acceptance

def main():
    before=git('status','--porcelain=v1');head=git('rev-parse','HEAD');started=time.monotonic()
    if before or git('branch','--show-current') or (ROOT/'config/.env').exists():raise ValueError('CLEAN_DETACHED_WITHOUT_DOT_ENV_REQUIRED')
    promotion=validate()
    if promotion['status']!='PASS':raise ValueError('V4_09_KEEP_ACCEPTED_REQUIRED')
    with disposable_cluster(Path(r'E:\Postgres\bin')) as (dsn,temp):
        import psycopg
        with psycopg.connect(dsn) as pg:
            identity=pg.execute('SELECT current_database(),current_user,inet_server_addr()::text,inet_server_port(),version()').fetchone()
            schema,post,coverage=schema_acceptance(pg);schema.update(tested_commit=head,database_identity=dict(zip(['database','owner','server_address','server_port','version'],identity)))
            if schema['status']!='PASS':raise ValueError(schema['checks'])
        guard=temp/'guard';guard.mkdir()
        (guard/'sitecustomize.py').write_bytes(b"import sys,os\ndef forbid(event,args):\n if event=='open' and isinstance(args[0],(str,bytes,os.PathLike)) and os.fsdecode(args[0]).replace('\\\\','/').lower().endswith('/config/.env'): raise RuntimeError('CONFIG_DOT_ENV_READ_FORBIDDEN')\nsys.addaudithook(forbid)\n")
        env=os.environ.copy();env['WORKBENCH_PG_DSN']=dsn;env['V4_10_DISPOSABLE_TEST_DSN']=dsn
        env['PYTHONPATH']=str(guard)+os.pathsep+str(ROOT)+os.pathsep+env.get('PYTHONPATH','')
        for key in ['PGPASSWORD','PGSERVICE','PGSERVICEFILE']:env.pop(key,None)
        families=[*REQUIRED_FAMILIES,'tests/v4_09','tests/v4_10','tests/test_fixed_qfq_samples.py','tests/test_phase0_2a_gate.py',
            'tests/test_phase1_qa_sample_selector.py','tests/governance/test_no_symbol_specific_runtime_logic.py']
        obsolete='tests/v4_09/test_stock_prewatch.py::test_production_and_v4_09_acceptance_stay_disabled';junit=temp/'junit.xml'
        run=subprocess.run([sys.executable,'-m','pytest','-q',*families,'--deselect='+obsolete,f'--junitxml={junit}'],cwd=ROOT,env=env,
            capture_output=True,text=True,encoding='utf8',errors='replace',timeout=1200)
        suites=list(ET.parse(junit).getroot().iter('testsuite')) if junit.exists() else []
        summary={k:sum(int(s.attrib.get(k,0)) for s in suites) for k in ['tests','failures','errors','skipped']}
        summary['passed']=summary['tests']-summary['failures']-summary['errors']-summary['skipped']
        regression=dict(contract_id='V4_10_R1_2_ISOLATED_REGRESSION',status='PASS' if run.returncode==0 and suites else 'FAIL',tested_commit=head,
            summary=summary,required_families=families,stdout=run.stdout,stderr=run.stderr,config_dot_env_read=False,
            configured_or_production_database_used=False,dsn_source='PROCESS_ENVIRONMENT_DISPOSABLE_CLUSTER',deselected_exact_nodes=[obsolete],
            historical_supersession='ONLY the existing authorized R1 candidate-absence guard; no new deselect')
    from scripts.scan_no_symbol_specific_runtime_logic import run as scan
    governance=scan(ROOT);governance['tested_commit']=head;after=git('status','--porcelain=v1');schema['temporary_cluster_destroyed']=True
    clean=dict(contract_id='V4_10_R1_2_CLEAN_CHECKOUT_RECEIPT',status='PASS_CLEAN_DETACHED_CHECKOUT' if not after and schema['status']=='PASS' and
        post['status']=='PASS' and regression['status']=='PASS' and governance['status']=='PASS' else 'FAIL',tested_commit=head,detached_head=True,
        git_status_before=before,git_status_after=after,config_dot_env_present=False,config_dot_env_read=False,temporary_cluster_destroyed=True,
        v4_09_keep_accepted=promotion,elapsed_seconds=round(time.monotonic()-started,3),created_at_utc=datetime.now(timezone.utc).isoformat())
    write_evidence(post,coverage)
    for name,value in [('SCHEMA_MIGRATION_RECEIPT',schema),('ISOLATED_REGRESSION',regression),('CLEAN_CHECKOUT_RECEIPT',clean),
        ('NO_SYMBOL_SPECIFIC_SYSTEM_LOGIC_SCAN',compact_scan(governance))]:atomic_json(ROOT/f'reports/v4_10/V4_10_R1_2_{name}.json',value)
    print(json.dumps(dict(status=clean['status'],tested_commit=head,vector_count=post['vector_count'],regression=summary,no_symbol=governance['status'],schema_checks=schema['checks'])))
    return clean['status']=='FAIL'

if __name__=='__main__':sys.exit(main())
