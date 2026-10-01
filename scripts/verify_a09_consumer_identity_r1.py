"""Independent migration, legacy-byte, SQL rejection, and exact rollback oracle."""
import ast,copy,hashlib,json,subprocess,sys
from pathlib import Path
import psycopg
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from scripts.build_v4_08_r2_membership_evidence import atomic_json
from scripts.enter_source_authority_remediation_r2 import bind
from scripts.run_v4_08_r3_isolated_verification import disposable_cluster,apply_migrations
from src.v4.stock_prewatch import load_accepted,build,CONSUMER_CONTRACT,digest
from src.v4.stock_prewatch_persistence import persist
MIGRATION='src/workbench_db/migrations/v4_postgres/025_v4_09_consumer_identity_hardening.sql'
ROLLBACK='src/workbench_db/migrations/v4_postgres/rollback/025_v4_09_consumer_identity_hardening.sql'

def legacy_writer():
    head=json.loads((ROOT/'data/v4/V4_09_ACCEPTED_HEAD.json').read_text(encoding='utf8'))
    entry=json.loads((ROOT/'reports/audits/A09_STAGE_ENTRY_R1.json').read_text(encoding='utf8'))
    source=subprocess.check_output(['git','show',entry['baseline_commit']+':src/v4/stock_prewatch_persistence.py'],cwd=ROOT)
    assert hashlib.sha256(source).hexdigest()==head['evidence_bindings']['src/v4/stock_prewatch_persistence.py']['sha256']
    scope={'__package__':'src.v4'};exec(compile(source,'accepted_legacy_stock_prewatch_persistence.py','exec'),scope)
    return scope['persist']

def schema(pg):
    queries=["""SELECT c.relname,a.attname,format_type(a.atttypid,a.atttypmod),a.attnotnull,pg_get_expr(d.adbin,d.adrelid) FROM pg_attribute a JOIN pg_class c ON c.oid=a.attrelid JOIN pg_namespace n ON n.oid=c.relnamespace LEFT JOIN pg_attrdef d ON d.adrelid=a.attrelid AND d.adnum=a.attnum WHERE n.nspname='v4' AND c.relname IN ('stock_prewatch_publications','stock_prewatch_results') AND a.attnum>0 AND NOT a.attisdropped ORDER BY c.relname,a.attnum""",
    """SELECT c.relname,x.conname,pg_get_constraintdef(x.oid) FROM pg_constraint x JOIN pg_class c ON c.oid=x.conrelid JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='v4' AND c.relname IN ('stock_prewatch_publications','stock_prewatch_results') ORDER BY 1,2""",
    """SELECT c.relname,t.tgname,pg_get_triggerdef(t.oid) FROM pg_trigger t JOIN pg_class c ON c.oid=t.tgrelid JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='v4' AND c.relname IN ('stock_prewatch_publications','stock_prewatch_results') AND NOT t.tgisinternal ORDER BY 1,2""",
    """SELECT p.proname,pg_get_functiondef(p.oid) FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace WHERE n.nspname='v4' AND p.proname LIKE '%stock_prewatch%' ORDER BY 1""",
    """SELECT indexname,indexdef FROM pg_indexes WHERE schemaname='v4' AND tablename IN ('stock_prewatch_publications','stock_prewatch_results') ORDER BY 1""",
    """SELECT version,checksum_sha256 FROM v4_meta.schema_migrations ORDER BY version"""]
    return [pg.execute(q).fetchall() for q in queries]

def rejected(pg,operation):
    try:
        with pg.transaction():operation()
    except (ValueError,psycopg.Error):return True
    return False

def oracle(pg,records,old_writer):
    # Roll the additive schema back inside a savepoint so genuine pre-025 rows exist.
    with pg.transaction():
        pg.execute('SAVEPOINT a09_scope')
        pg.execute((ROOT/ROLLBACK).read_text(encoding='utf8'))
        old_writer(pg,records);before_schema=schema(pg)
        original=pg.execute('SELECT publication_id,security_id,payload,payload_digest FROM v4.stock_prewatch_results ORDER BY publication_id,security_id').fetchall()
        publication_before=pg.execute('SELECT * FROM v4.stock_prewatch_publications ORDER BY publication_id').fetchall()
        pg.execute((ROOT/MIGRATION).read_text(encoding='utf8'))
        pg.execute("INSERT INTO v4_meta.schema_migrations VALUES ('V4_STAGE_025_V4_09_CONSUMER_IDENTITY_HARDENING',%s,now(),'A09_INDEPENDENT_ORACLE')",(bind(MIGRATION)['sha256'],))
        loaded=pg.execute('SELECT publication_id,security_id,payload,payload_digest FROM v4.stock_prewatch_results ORDER BY publication_id,security_id').fetchall()
        assert loaded==original
        assert pg.execute('SELECT DISTINCT consumer_contract_id FROM v4.stock_prewatch_publications').fetchall()==[(CONSUMER_CONTRACT,)]
        assert persist(pg,records)['consumer_contract_id']==CONSUMER_CONTRACT
        checks={'legacy_payloads_and_digests_unchanged':True,'legacy_retry_idempotent':True}
        checks['same_publication_other_consumer_rejected']=rejected(pg,lambda:persist(pg,records,consumer_contract_id='A09_FIXTURE_CONSUMER_B_V1'))
        checks['publication_consumer_update_rejected']=rejected(pg,lambda:pg.execute("UPDATE v4.stock_prewatch_publications SET consumer_contract_id='OTHER' WHERE publication_id=%s",(records[0]['publication_id'],)))
        checks['result_consumer_update_rejected']=rejected(pg,lambda:pg.execute("UPDATE v4.stock_prewatch_results SET consumer_contract_id='OTHER' WHERE publication_id=%s",(records[0]['publication_id'],)))
        mixed=copy.deepcopy(records);mixed[0]['consumer_contract_id']='OTHER'
        checks['mixed_row_consumer_rejected']=rejected(pg,lambda:persist(pg,mixed))
        changed=copy.deepcopy(records);changed[0]['input_digest']='f'*64
        checks['same_publication_changed_payload_rejected']=rejected(pg,lambda:persist(pg,changed))
        other=copy.deepcopy(records[:2]);consumer='A09_FIXTURE_CONSUMER_B_V1'
        for row in other:row.update(publication_id='A09_FIXTURE_OTHER_CONSUMER:'+digest(records),consumer_contract_id=consumer)
        before_b=pg.execute('SELECT count(*) FROM v4.stock_prewatch_publications').fetchone()[0]
        pg.execute('SAVEPOINT a09_b_consumer')
        result=persist(pg,other,consumer_contract_id=consumer)
        assert result['consumer_contract_id']==consumer
        assert pg.execute('SELECT DISTINCT consumer_contract_id FROM v4.stock_prewatch_results WHERE publication_id=%s',(other[0]['publication_id'],)).fetchall()==[(consumer,)]
        checks['distinct_consumer_publication_and_exact_payload_readback']=True
        checks['rollback_rejects_loss_of_nonlegacy_consumer']=rejected(pg,lambda:pg.execute((ROOT/ROLLBACK).read_text(encoding='utf8')))
        checks['db_foreign_key_rejects_cross_consumer_result']=rejected(pg,lambda:pg.execute("INSERT INTO v4.stock_prewatch_results SELECT publication_id,security_id||'_wrong',trade_date,model_contract_id,parameter_set_id,raw_qualification,emergence_axis,structure_quality_axis,risk_axis,priority_bucket,quality,reasons,input_digest,payload||jsonb_build_object('security_id',security_id||'_wrong'),payload_digest,'OTHER' FROM v4.stock_prewatch_results WHERE publication_id=%s LIMIT 1",(other[0]['publication_id'],)))
        checks['db_payload_consumer_mismatch_rejected']=rejected(pg,lambda:pg.execute("INSERT INTO v4.stock_prewatch_results SELECT publication_id,security_id||'_wrong',trade_date,model_contract_id,parameter_set_id,raw_qualification,emergence_axis,structure_quality_axis,risk_axis,priority_bucket,quality,reasons,input_digest,payload||jsonb_build_object('security_id',security_id||'_wrong','consumer_contract_id','OTHER'),payload_digest,consumer_contract_id FROM v4.stock_prewatch_results WHERE publication_id=%s LIMIT 1",(other[0]['publication_id'],)))
        pg.execute('ROLLBACK TO SAVEPOINT a09_b_consumer')
        assert pg.execute('SELECT count(*) FROM v4.stock_prewatch_publications').fetchone()[0]==before_b
        pg.execute((ROOT/ROLLBACK).read_text(encoding='utf8'))
        checks['exact_schema_migration_ledger_rollback']=schema(pg)==before_schema
        checks['exact_legacy_payload_rollback']=pg.execute('SELECT publication_id,security_id,payload,payload_digest FROM v4.stock_prewatch_results ORDER BY publication_id,security_id').fetchall()==original
        checks['exact_legacy_publication_rollback']=pg.execute('SELECT * FROM v4.stock_prewatch_publications ORDER BY publication_id').fetchall()==publication_before
        assert all(checks.values()),checks
        pg.execute('ROLLBACK TO SAVEPOINT a09_scope')
    return dict(status='PASS_INDEPENDENT_SQL_CONSUMER_AND_EXACT_ROLLBACK',checks=checks,legacy_row_count=len(records),legacy_payload_digest=digest(records))

def main():
    entry=json.loads((ROOT/'reports/audits/A09_STAGE_ENTRY_R1.json').read_text(encoding='utf8'));assert entry['next_unused_v4_migration']==25
    assert all(bind(b['path'])['sha256']==b['sha256'] for b in entry['migrations_before']+entry['protected_bindings'])
    context,cores,factors,seeds,package=load_accepted(ROOT);records=build(cores,factors,seeds,context,package)
    with disposable_cluster(Path(r'E:\Postgres\bin')) as (dsn,temp):
        with psycopg.connect(dsn) as pg:
            migrations=apply_migrations(pg);result=oracle(pg,records,legacy_writer())
    result.update(migration=bind(MIGRATION),rollback=bind(ROLLBACK),migrations=migrations,configured_database_used=False,disposable_database_cleaned_up=True,accepted_heads_unchanged=True,external_acceptance=None)
    atomic_json(ROOT/'reports/audits/A09_SCHEMA_LEGACY_READBACK_AND_ROLLBACK_R1.json',result)
    atomic_json(ROOT/'reports/audits/A09_ENGINEERING_GATES_R1.json',dict(status='PENDING_CLEAN_DETACHED',work_package='WP-A09-V4-09-N02',allowed_candidate_status='V4_09_N02_CONSUMER_IDENTITY_CANDIDATE_READY_FOR_EXTERNAL_REAUDIT',gates={**{k:'PASS_ENGINEERING' for k in result['checks']},'clean':'PENDING_CLEAN_DETACHED','external':'PENDING_INDEPENDENT_EXTERNAL_AUDIT'},evidence=bind('reports/audits/A09_SCHEMA_LEGACY_READBACK_AND_ROLLBACK_R1.json'),next_stage='Independent external A09 consumer identity audit; accepted heads unchanged'))
    print(json.dumps(dict(status=result['status'],rows=len(records),checks=len(result['checks']))))

if __name__=='__main__':main()
