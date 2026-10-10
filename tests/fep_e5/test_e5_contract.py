"""E5-01..30 negatives, real PostgreSQL transactions and engineering-only API."""
from copy import deepcopy
from pathlib import Path
import json,os,threading,urllib.request
from http.server import ThreadingHTTPServer
import pytest
import psycopg
from workbench_analysis.fep_e1.feature_owner import verify_file
from workbench_analysis.fep_e5 import contracts as c,projection as p,fixtures as f
from workbench_analysis.fep_e5.ledger import Ledger
from workbench_service.expectancy_service import ExpectancyReadAPI,handler_factory

AT='2026-01-02T00:00:00+00:00';CUTOFF='2026-01-01T23:59:00+00:00';DEADLINE='2026-01-02T01:00:00+00:00'
def model():return dict(model_id='E5_TEST_MODEL',model_set_id='E5_TEST_SET',scope_id='FEP_STOCK_ENTRY_CORE',observation_scope='FIRST_PREWATCH',
    target_id='ABS_RETURN_N:T1',horizon='T1',feature_contract_id='CORE_TEST',namespace='FEP_E5_UNIT',model_family='CONDITIONAL_STATISTICS_BASELINE',
    activation_effective_at=CUTOFF,champion=False,evidence_class='ACCEPTED_BASELINE_ENGINEERING',artifact_digest='EXACT_TEST_ARTIFACT')
def slot():return dict(namespace='FEP_E5_UNIT',scope_id='FEP_STOCK_ENTRY_CORE',observation_scope='FIRST_PREWATCH',entity_id='TEST_ENTITY',
    observation_id='TEST_OBSERVATION',signal_key='FIRST_PREWATCH:TEST_EP',trade_date='2024-01-01',target_id='ABS_RETURN_N:T1',horizon='T1',
    feature_contract_id='CORE_TEST',model_family_scope='CONDITIONAL_STATISTICS_BASELINE',model_selection_cutoff=CUTOFF,prediction_deadline=DEADLINE)
def input_row():
    snap=dict(observation_id='TEST_OBSERVATION',publication_identity='EXACT_TEST_PUBLICATION',max_feature_source_trade_date='2024-01-01',features={'x':1.})
    return dict(observation_id='TEST_OBSERVATION',entity_id='TEST_ENTITY',trade_date='2024-01-01',snapshot_id='TEST_SNAPSHOT',snapshot_digest=c.logical(snap),
        snapshot=snap,input_mode='EXACT_IMMUTABLE_SNAPSHOT',source_available_at=CUTOFF)
def output():return dict(inference_model_id=model()['model_id'],inference_model_set_id=model()['model_set_id'],inference_snapshot_digest=input_row()['snapshot_digest'],inference_source_digest=model()['artifact_digest'],
    projection_state='READY',axes=dict(return_expectancy=.01,relative_expectancy=None,risk_expectancy=None,structure_expectancy=None),
    quality_state='OBSERVED',support_state='SUPPORTED',OOD_state=dict(JOINT_OOD='UNSET',global_OOD_OK=False,hard_reasons=[]),coherence_state='DIAGNOSTIC_ONLY',
    threshold_state='NOT_FROZEN',prediction_evidence='HISTORICAL_SIMULATION',FIRST_OBSERVED=False,REAL_OOS=False,PROMOTION_EVIDENCE=False)
def rejects(call,match=None):
    with pytest.raises(ValueError,match=match):call()
@pytest.fixture
def db():
    dsn=os.environ.get('FEP_E5_TEST_DSN','host=127.0.0.1 port=55488 user=fep_e1_admin dbname=fep_e1_fresh')
    with psycopg.connect(dsn,autocommit=True) as pg:
        ledger=Ledger(pg,historical_fixture=True);ledger.install()
        with pg.transaction(force_rollback=True):yield ledger
def activated(db):
    m=model();db.register_model(m);s=db.plan(slot());db.bind(s['slot_id'],m['model_id']);g=db.grant(m['model_id']);db.cas(g['grant_id'],'UNIT_ALLOW',0,'ALLOW',AT)
    return m,s,g

def test_e5_01_entry_daily_rejected():
    s=slot();s['observation_scope']='DAILY_LANDMARK';rejects(lambda:c.compatible(s,model()),'MISMATCH')
def test_e5_02_t1_t5_rejected():
    s=slot();s['horizon']='T5';rejects(lambda:c.compatible(s,model()),'MISMATCH')
def test_e5_03_abs_market_excess_rejected():
    s=slot();s['target_id']='MARKET_EXCESS_N:T1';rejects(lambda:c.compatible(s,model()),'MISMATCH')
def test_e5_04_core_supplemental_rejected():
    s=slot();s['feature_contract_id']='SUPPLEMENTAL';rejects(lambda:c.compatible(s,model()),'MISMATCH')
def test_e5_05_current_head_rebuild_rejected():
    row=input_row();row['input_mode']='LATEST_HEAD';rejects(lambda:c.snapshot_input(row),'CURRENT_HEAD')
def test_e5_06_seen_outer_promotion_rejected():
    value=output();value['PROMOTION_EVIDENCE']=True;rejects(lambda:c.evidence(value),'PROMOTION')
@pytest.mark.parametrize('family',['TREE_CHALLENGER'])
def test_e5_07_e4_champion_rejected(db,family):
    value=model();value.update(champion=True,model_family=family);rejects(lambda:db.register_model(value),'CHAMPION')
def test_e5_08_e2_champion_rejected(db):
    value=model();value['champion']=True;rejects(lambda:db.register_model(value),'CHAMPION')
def test_e5_09_display_without_champion_rejected():rejects(lambda:c.permission_request(model(),'MODEL_DISPLAY'),'CLOSED')
def test_e5_10_priority_without_daily_rejected():rejects(lambda:c.permission_request(model(),'PRIORITY_USE'),'CLOSED')
def test_e5_11_old_entry_as_today_rejected():
    pool,preds,day,risk=f.fixture();preds[pool[0]['entity_id']]['observation_scope']='FIRST_PREWATCH'
    rejects(lambda:c.daily_projection(pool,preds,day,f.priority_protocol(),synthetic_only=True),'ENTRY_DAILY')
def test_e5_12_v1_rank_mutation_rejected():
    pool,preds,day,risk=f.fixture();shadow=c.daily_projection(pool,preds,day,f.priority_protocol(),synthetic_only=True)
    shadow['rows'][0]['v1_rank']=999;rejects(lambda:c.verify_shadow(pool,shadow,risk),'PRIORITY_V1')
def test_e5_13_eligibility_mutation_rejected():
    pool,preds,day,risk=f.fixture();shadow=c.daily_projection(pool,preds,day,f.priority_protocol(),synthetic_only=True,risk_events=risk)
    shadow['rows'][0]['eligible']=False;rejects(lambda:c.verify_shadow(pool,shadow,risk),'ELIGIBILITY')
def test_e5_14_positive_hides_risk_rejected():
    pool,preds,day,risk=f.fixture();shadow=c.daily_projection(pool,preds,day,f.priority_protocol(),synthetic_only=True,risk_events=risk)
    shadow['rows'][-1]['risk']=[];rejects(lambda:c.verify_shadow(pool,shadow,risk),'RISK_EVENT')
def test_e5_15_ood_denominator_drop_rejected():
    pool,preds,day,risk=f.fixture();shadow=c.daily_projection(pool,preds,day,f.priority_protocol(),synthetic_only=True,risk_events=risk)
    shadow['rows']=[r for r in shadow['rows'] if r['projection_state']!='REJECTED_OOD'];rejects(lambda:c.verify_shadow(pool,shadow,risk),'DENOMINATOR')
def test_e5_16_no_model_slot_retained(db):
    s=db.plan(slot());p.missing(db,s,'NO_ACTIVE_MODEL',AT)
    with pytest.raises(psycopg.Error,match='APPEND_ONLY'):
        with db.pg.transaction():db.pg.execute('delete from fep_e5_engineering.prediction_slots where id=%s',(s['slot_id'],))
    assert db.get('prediction_slots',s['slot_id']) is not None and any(r['status']=='NO_ACTIVE_MODEL' for r in db.rows('slot_receipts'))
def test_e5_17_binding_not_replaced_by_better_result(db):
    m,s,g=activated(db);prediction=p.accept(db,s['slot_id'],input_row(),output(),AT,AT)
    other=dict(m,model_id='OTHER_BETTER_MODEL',model_set_id='OTHER_BETTER_SET');db.register_model(other)
    rejects(lambda:db.bind(s['slot_id'],other['model_id']),'IDEMPOTENCY')
    assert db.get('slot_model_bindings',s['slot_id'])['model_id']==m['model_id']
def test_e5_18_post_result_priority_tuple_rejected():
    pool,preds,day,risk=f.fixture();protocol=f.priority_protocol();protocol['fep_tuple']=['opaque_total_score']
    rejects(lambda:c.daily_projection(pool,preds,day,protocol,synthetic_only=True),'PRIORITY_TUPLE')
def test_e5_19_post_result_disposition_rejected():
    frozen={'E5_EFFECTIVENESS_EVALUATION':'CLOSED_ENGINEERING_ONLY','rule':'ENGINEERING_ONLY'};changed=dict(frozen,rule='PASS_INCREMENT')
    rejects(lambda:c.protocol_guard(changed,frozen),'PROTOCOL')
def test_e5_20_core_feedback_write_rejected():rejects(lambda:c.write_target('Core_Profile_State_Cohort'),'WRITE_FORBIDDEN')
def test_e5_21_exact_permission_not_cross_target_horizon(db):
    m,s,g=activated(db);key=c.permission_key(m,'SHADOW_INFERENCE');key['horizon']='T5';assert not db.allowed(m['model_id'],key,AT)
def test_e5_22_fixture_real_oos_rejected():
    pool,preds,day,risk=f.fixture();preds[pool[0]['entity_id']]['REAL_OOS']=True
    rejects(lambda:c.daily_projection(pool,preds,day,f.priority_protocol(),synthetic_only=True),'REAL_EVIDENCE')
def test_e5_23_reconstructed_first_observed_rejected():
    value=output();value['FIRST_OBSERVED']=True;rejects(lambda:c.evidence(value),'REAL_EVIDENCE')
def test_e5_24_rollback_cannot_delete_history(db):
    m,s,g=activated(db);record=p.accept(db,s['slot_id'],input_row(),output(),AT,AT)
    rejects(lambda:db.rollback(m['model_id'],'UNIT_ROLLBACK',AT,delete_history=True),'DELETE')
    db.rollback(m['model_id'],'UNIT_ROLLBACK',AT)
    assert db.get('predictions',record['prediction_id']) is not None
    assert not db.allowed(m['model_id'],c.permission_key(m,'SHADOW_INFERENCE'),AT)
def test_e5_25_failed_transaction_no_partial_activation(db):
    m=model();db.register_model(m);g=db.grant(m['model_id']);before=db.inventory()
    rejects(lambda:db.cas(g['grant_id'],'UNIT_FAILED_ACTIVATE',0,'ALLOW',AT,fail_after_receipt=True),'HEAD_UPDATE_FAILURE')
    assert db.inventory()==before and not db.allowed(m['model_id'],c.permission_key(m,'SHADOW_INFERENCE'),AT)
def test_e5_26_joint_unset_cannot_be_pass(db):
    m,s,g=activated(db);value=output();value['OOD_state']['global_OOD_OK']=True
    rejects(lambda:p.accept(db,s['slot_id'],input_row(),value,AT,AT),'JOINT_OOD')
def test_e5_27_real_daily_api_inactive(db):
    api=ExpectancyReadAPI(db,AT);assert api.priority()['v2_active'] is False
    pool,preds,day,risk=f.fixture();rejects(lambda:c.daily_projection(pool,preds,day,f.priority_protocol(),tie_break_enabled=True),'REAL_DAILY')
def test_e5_28_v1_source_parameter_digest_rejected(tmp_path):
    import hashlib
    path=tmp_path/'priority.json';path.write_bytes(b'new');ref=dict(path=path.name,bytes=3,sha256=hashlib.sha256(b'old').hexdigest())
    rejects(lambda:verify_file(tmp_path,ref),'EXACT_BYTES')
def test_e5_29_new_training_blocked():rejects(lambda:c.resources({'new_model_training':1}),'TRAINING')
def test_e5_30_label_recompute_blocked():rejects(lambda:c.resources({'new_label_resolution':1}),'LABEL')

def test_actual_append_only_predictions_and_corrected_view(db):
    m,s,g=activated(db);first=p.accept(db,s['slot_id'],input_row(),output(),AT,AT)
    revised=output();revised['prediction_evidence']='CORRECTED_RECONSTRUCTION'
    second=p.accept(db,s['slot_id'],input_row(),revised,AT,AT,revision=2,supersedes=first['prediction_id'])
    assert first['prediction_id']!=second['prediction_id'] and p.first_accepted(db,s['slot_id'])==first
    with pytest.raises(psycopg.Error,match='APPEND_ONLY'):
        with db.pg.transaction():db.pg.execute('update fep_e5_engineering.predictions set payload=payload where id=%s',(first['prediction_id'],))

def test_atomic_prediction_receipt_failure(db):
    m,s,g=activated(db);before=db.inventory()
    rejects(lambda:p.accept(db,s['slot_id'],input_row(),output(),AT,AT,fail_before_receipt=True),'ACCEPTANCE_FAILURE')
    assert db.inventory()==before

def test_prediction_persisted_then_priority_fails_independently(db):
    m,s,g=activated(db);record=p.accept(db,s['slot_id'],input_row(),output(),AT,AT)
    with pytest.raises(ValueError):
        with db.pg.transaction():db.put('priority_projection','FAILED_SHADOW',dict(status='UNACCEPTED'));raise ValueError('priority fails')
    assert db.get('priority_projection','FAILED_SHADOW') is None and db.get('predictions',record['prediction_id'])==record

def test_idempotence_semantic_clock_metadata(db):
    m,s,g=activated(db);first=p.accept(db,s['slot_id'],input_row(),output(),AT,AT);before=db.inventory()
    again=p.accept(db,s['slot_id'],input_row(),output(),AT,AT)
    assert again==first and db.inventory()==before
    later='2026-01-02T00:01:00+00:00'
    with pytest.raises(ValueError,match='FROZEN_PREDICTION_MUTATION'):
        p.accept(db,s['slot_id'],input_row(),output(),later,later)
    assert db.inventory()==before and db.get('predictions',first['prediction_id'])==first
    assert c.logical({'value':1,'created_at':'a','run_id':'one'})==c.logical({'value':1,'created_at':'b','run_id':'two'})

def test_priority_fixture_full_pool_and_risk_preserved():
    pool,preds,day,risk=f.fixture();before=deepcopy(pool)
    shadow=c.daily_projection(pool,preds,day,f.priority_protocol(),synthetic_only=True,tie_break_enabled=True,risk_events=risk)
    c.verify_shadow(pool,shadow,risk);assert pool==before and len(shadow['rows'])==7 and shadow['eligible_candidates']==6 and shadow['covered_candidates']==3
    assert shadow['rows'][0]['v2_shadow_rank']==3 and shadow['rows'][2]['v2_shadow_rank']==1
    assert shadow['rows'][-1]['risk']==['INVALIDATED','RISK_CHANGE','HIGH_EXTENSION']

def test_actual_http_bootstrap_context_and_api_permission(db):
    m,s,g=activated(db);record=p.accept(db,s['slot_id'],input_row(),output(),AT,AT);api=ExpectancyReadAPI(db,AT)
    server=ThreadingHTTPServer(('127.0.0.1',0),handler_factory(api));thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    try:
        with urllib.request.urlopen(f'http://127.0.0.1:{server.server_port}/api/v4/expectancy/context?slot_id='+s['slot_id'],timeout=5) as response:body=json.load(response)
        token=body['context'];normal=api.projection(s['slot_id'],token);diagnostic=api.projection(s['slot_id'],token,diagnostic=True)
        assert normal['axes'] is None and diagnostic['axes']['return_expectancy']==.01 and diagnostic['permission']=='SHADOW_INFERENCE_ONLY'
        assert not any(diagnostic['permissions'][k] for k in ('descriptive_display','model_display','priority_use'))
        assert api.projection(s['slot_id'],dict(token,model_set_id='different'))['status']=='CONTEXT_MISMATCH'
        assert 'NOT_APPLICABLE' in api.projection(s['slot_id'],token,diagnostic=True,mode='TODAY_RADAR')['status']
    finally:server.shutdown();server.server_close();thread.join(timeout=3)

@pytest.mark.parametrize('day_field',['trade_date','snapshot_trade_date','slot_trade_date','accepted_trade_date'])
def test_same_day_guard_each_clock(day_field):
    pool,preds,day,risk=f.fixture();preds[pool[0]['entity_id']][day_field]='2026-10-05'
    rejects(lambda:c.daily_projection(pool,preds,day,f.priority_protocol(),synthetic_only=True),'STALE')
def test_none_is_unknown_not_neutral():assert c.classify({'return_expectancy':None},dict(quality=True),dict(statistic='return_expectancy',positive=0,negative=0,risk_limit=1))=='UNKNOWN'
def test_unset_future_oos_closed():rejects(lambda:c.future_evaluation(dict(status='NOT_ACTIVE',evaluation_open=False,dimensions={'K':'UNSET'})),'UNSET')
def test_late_activation_and_deadline(db):
    value=model();value['activation_effective_at']=AT;rejects(lambda:c.compatible(slot(),value),'LATE')
    m,s,g=activated(db);rejects(lambda:p.accept(db,s['slot_id'],input_row(),output(),'2026-01-02T02:00:00+00:00','2026-01-02T02:00:00+00:00'),'DEADLINE')
def test_future_feature_snapshot_rejected(db):
    m,s,g=activated(db);row=input_row();row['snapshot']['max_feature_source_trade_date']='2024-01-02';row['snapshot_digest']=c.logical(row['snapshot'])
    rejects(lambda:p.accept(db,s['slot_id'],row,output(),AT,AT),'FUTURE_FEATURE')
def test_cas_idempotent_and_conflict(db):
    m,s,g=activated(db);first=db.get('deployment_receipts','UNIT_ALLOW')
    assert db.cas(g['grant_id'],'UNIT_ALLOW',0,'ALLOW',AT)==first
    rejects(lambda:db.cas(g['grant_id'],'UNIT_ALLOW',0,'REVOKE',AT),'CAS_REQUEST')
def test_all_fact_tables_have_db_guards(db):
    guards={r[0] for r in db.pg.execute("select c.relname from pg_trigger t join pg_class c on c.oid=t.tgrelid join pg_namespace n on n.oid=c.relnamespace where n.nspname='fep_e5_engineering' and t.tgenabled='O'")}
    assert guards==set(db.inventory())

@pytest.mark.parametrize('field,value',[('model_id','INJECTED'),('inference_model_id','OTHER'),('inference_source_digest','OTHER'),('inference_snapshot_digest','OTHER')])
def test_prediction_output_identity_cannot_override(db,field,value):
    m,s,g=activated(db);wrong=output();wrong[field]=value
    rejects(lambda:p.accept(db,s['slot_id'],input_row(),wrong,AT,AT),'BINDING|OVERRIDE')
