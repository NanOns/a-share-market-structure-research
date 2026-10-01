from copy import deepcopy
import ast,json
from pathlib import Path
import pytest
from src.v4.confirmation import *
from scripts.v4_11_candidate_inputs_r1 import projection,positive_values,seal
from scripts.v4_11_engineering_vectors_r1 import *
from src.v4.confirmation_d2_bridge import engineering_d2_publication,verify_d2_publication
from src.v4.confirmation_events import state_events,freeze_prior_session

@pytest.fixture(scope='module')
def positive():return projection(positive_values())

@pytest.mark.parametrize('stage',['NONE','SEED','PREWATCH'])
def test_stage_to_confirmed(stage):
    old,new,frozen,events=event_vector(stage)
    assert events[0]['primary_event']==EXPECTED[stage+'_TO_CONFIRMED']
    assert new['rows'][0]['maturity']=='CONFIRMED'

def test_persistent():assert event_vector('CONFIRMED')[3][0]['primary_event']==EXPECTED['PERSISTENT_CONFIRMED']

def test_same_day_r1_r2_r3():
    old,new,frozen,events=event_vector('PREWATCH');prior_digest=frozen['head_digest'];parent=None;publications=[]
    for delta in (0,1,2):
        p=engineering_d2_publication([state_input('CONFIRMED',prior=old['rows'][0],delta=delta)])
        e=state_events(p,frozen,revision_of=parent)
        assert e[0]['primary_event']==EXPECTED['SAME_DAY_R1_R2_R3_NEW_CONFIRMED']
        assert e[0]['prior_session_state_head_digest']==prior_digest
        publications.append(p['publication_id']);parent=p['publication_id']
    assert len(set(publications))==3
    with pytest.raises(ConfirmationError,match='SAME_DAY_REVISION_PARENT'):
        freeze_prior_session(target_date='2026-09-30',prior_date='2026-09-30',calendar_publication_id=new['rows'][0]['calendar_publication_id'],rows=new['rows'],source_binding=new,scope='SYNTHETIC_ENGINEERING_ONLY',calendar_manifest=new['inputs'][0]['synthetic_calendar_manifest'])

def test_reconfirmed():
    before=engineering_d2_publication([state_input('CONFIRMED',session=20)])
    weak=engineering_d2_publication([state_input('NONE',session=21,prior=before['rows'][0])])
    assert weak['rows'][0]['maturity']=='CONFIRMED' and weak['rows'][0]['final_eligibility']=='FALSE'
    assert event_vector(prior=weak)[3][0]['primary_event']==EXPECTED['RECONFIRMED']

def test_reconfirmed_after_exit_keeps_confirmed_episode_history():
    p=engineering_d2_publication([state_input('CONFIRMED',session=19)])
    q=engineering_d2_publication([state_input('NONE',session=20,prior=p['rows'][0])])
    old=engineering_d2_publication([state_input('NONE',session=21,prior=q['rows'][0])])
    assert old['rows'][0]['maturity']=='NONE'
    x=state_input('CONFIRMED',prior=old['rows'][0]);new=engineering_d2_publication([x])
    frozen=freeze_prior_session(target_date='2026-09-30',prior_date='2026-09-29',calendar_publication_id=x['calendar_publication_id'],rows=old['rows'],source_binding=old,
        scope='SYNTHETIC_ENGINEERING_ONLY',calendar_manifest=x['synthetic_calendar_manifest'],episode_history=[p,q])
    e=state_events(new,frozen)[0]
    assert e['primary_event']=='RECONFIRMED' and e['parent_episode_id']==p['rows'][0]['episode_id']

def test_forged_frozen_calendar_rejected():
    old,new,frozen,events=event_vector('NONE');x=deepcopy(frozen)
    x['prior_trade_date']='2026-09-28';x['calendar_manifest']['sessions']=[s for s in x['calendar_manifest']['sessions'] if s['trade_date']!='2026-09-29']
    x['head_digest']=digest({k:v for k,v in x.items() if k!='head_digest'})
    with pytest.raises(ConfirmationError,match='PRIOR_CALENDAR_BINDING_INVALID'):state_events(new,x)

def test_d2_parent_must_equal_event_prior():
    old,new,frozen,events=event_vector('NONE')
    other=engineering_d2_publication([state_input('CONFIRMED',prior=None)])
    with pytest.raises(ConfirmationError,match='D2_PARENT_DIFFERS_FROM_FROZEN_PRIOR_SESSION'):state_events(other,frozen)

@pytest.mark.parametrize('prior_scenario,current_scenario,expected',[
 ('TREND_CONTINUE','LAUNCH_CONFIRM','SCENARIO_UPGRADED'),('LAUNCH_CONFIRM','TREND_CONTINUE','SCENARIO_CHANGED')])
def test_scenario_events(prior_scenario,current_scenario,expected):
    assert event_vector('CONFIRMED',prior_scenario=prior_scenario,current_scenario=current_scenario)[3][0]['primary_event']==expected

def test_weakening():assert event_vector('CONFIRMED',delta=-4)[3][0]['primary_event']==EXPECTED['CONFIRMATION_WEAKENED']
def test_hard_invalidation():
    old,new,frozen,events=event_vector('CONFIRMED',damage=True)
    assert new['rows'][0]['raw_qualification']['CONFIRMED']=='TRUE'
    assert new['rows'][0]['validity']=='INVALIDATED' and events[0]['primary_event']==EXPECTED['HARD_INVALIDATION_WINS']

def test_required_fact_unknown(positive):
    x=deepcopy(positive);x['rows'][0]['facts']['normal_universe']['quality']='CONFLICTING'
    row=detect_confirmation(seal(x))['rows'][0]
    assert row['confirmation_status']==EXPECTED['REQUIRED_FACT_UNKNOWN'] and not row['matched_scenarios']
    assert row['raw_predicates']['STRONG_PULLBACK']['NORMAL_UNIVERSE'] is None

def test_amount_disabled_and_multiscenario_dedup(positive):
    output=detect_confirmation(positive);r=output['rows'][0]
    assert len(output['rows'])==1 and r['matched_scenarios']==['STRONG_PULLBACK']
    assert r['diagnostic_legacy_matches']==['LAUNCH_CONFIRM','STRONG_PULLBACK','RECOVERY_TURN']
    assert all(e['status']==EXPECTED['AMOUNT_A_DISABLED'] for e in r['scenario_evidence'] if e['scenario'] in AMOUNT_BRANCHES)
    assert not {'maturity','validity','tracking'}&set(r)
    d2=engineering_d2_publication([from_confirmation(r)])
    assert d2['rows'][0]['maturity']=='CONFIRMED'
    with pytest.raises(ConfirmationError):state_events(r,{})

@pytest.mark.parametrize('field,value,message',[
 ('producer_contract_id','wrong','PRODUCER_MISMATCH'),('parameter_set_id','wrong','PARAMETER_MISMATCH'),
 ('source_publication_ids',['wrong'],'PUBLICATION_MISMATCH')])
def test_identity_rejected(positive,field,value,message):
    x=deepcopy(positive);x[field]=value
    with pytest.raises(ConfirmationError,match=message):detect_confirmation(seal(x))

@pytest.mark.parametrize('mutation,message',[
 ('future','FUTURE_TIMESTAMP_REJECTED'),('feedback','SAME_DAY_FEEDBACK_REJECTED'),('role','FACT_TIME_ROLE_MISMATCH'),
 ('unit','INPUT_UNIT_MISMATCH'),('prior','PRIOR_WINDOW_MUST_END_BEFORE_TARGET'),('hash','EXACT_INPUT_BINDING_INVALID'),('head','UNACCEPTED_DATA_HEAD')])
def test_provenance_rejected(positive,mutation,message):
    x=deepcopy(positive);f=x['rows'][0]['facts']['actual_bar']
    if mutation=='future':f['system_available_at']='2099-01-01T00:00:00+00:00'
    if mutation=='feedback':f['time_role']='FINAL_STATE'
    if mutation=='role':f['time_role']='PRIOR_SESSION_WINDOW'
    if mutation=='unit':f['unit']='percent'
    if mutation=='prior':x['rows'][0]['facts']['amr20_mean_prior']['trade_date']='2026-09-30'
    if mutation=='hash':x['source_bindings'][0]['sha256']='a'*64;x['source_publication_ids'][0]='a'*64
    if mutation=='head':x['accepted_data_head']['sha256']='a'*64
    with pytest.raises(ConfirmationError,match=message):detect_confirmation(seal(x))

def test_full_market_and_false_acceptance():
    x=projection(real=True);out=detect_confirmation(x)
    assert len(out['rows'])==len(x['rows'])==5224
    assert all(r['confirmation_status']=='UNKNOWN' for r in out['rows'])
    assert sum(not r['facts']['actual_bar']['value'] for r in x['rows'])==11
    x['rows'][0]['facts']['normal_universe'].update(value=True,quality='KNOWN',acceptance='EXTERNALLY_ACCEPTED')
    with pytest.raises(ConfirmationError,match='SOURCE_FIELD_NOT_ACCEPTED_FOR_TARGET'):detect_confirmation(seal(x))

def test_d2_output_cannot_be_manufactured():
    old,new,frozen,events=event_vector('NONE')
    x=deepcopy(new);x['rows'][0]['maturity']='NONE'
    with pytest.raises(ConfirmationError,match='D2_REDUCER_READBACK_MISMATCH'):state_events(x,frozen)
    altered=deepcopy(frozen);altered['prior_trade_date']='2026-09-28';altered['head_digest']=digest({k:v for k,v in altered.items() if k!='head_digest'})
    with pytest.raises(ConfirmationError,match='EXACT_PREVIOUS_CALENDAR_SESSION_REQUIRED'):state_events(new,altered)

def test_first_observed_and_none():
    empty=engineering_d2_publication([])
    assert event_vector(prior=empty)[3][0]['primary_event']=='FIRST_OBSERVED'
    assert event_vector('NONE','NONE')[3][0]['primary_event']=='NONE'

def test_raw_source_oracle_each_scenario():
    # Exact frozen source AST is executed independently, bypassing candidate producer.
    c,m,p,a,scanner=package();namespace={};exec(compile(exact(m['legacy_source']).read_text(encoding='utf8'),m['legacy_source']['path'],'exec'),namespace)
    oracle=namespace['scan_today_research'];base=positive_values()
    probes=[('launch','clv',.60,.5999),('pullback','pullback_episode_confirmed',True,False),('recovery_turn','clv',.55,.5499),('trend_continue','rps20',.70,.6999)]
    for branch,field,boundary,negative in probes:
        x=dict(base);x[field]=boundary
        expected={'positive':True,'negative':False,'boundary':True,'UNKNOWN':None}
        for label,value in [('positive',base[field]),('negative',negative),('boundary',boundary),('UNKNOWN',None)]:
            x[field]=value
            assert oracle(x)[branch]['eligible'] is expected[label]
            assert scanner(x)==oracle(x)

def test_no_symbol():
    from scripts.scan_no_symbol_specific_runtime_logic import run
    assert run(ROOT)['status']==EXPECTED['NO_SYMBOL']

def test_expected_inventory_complete():
    assert set(EXPECTED)==set(bound(package()[0]['entry_contract'])['golden_vectors']['coverage_required'])

def test_future_publication_cutoff_rejected(positive):
    x=deepcopy(positive);x['cutoff_timestamp']='2099-01-01T00:00:00+00:00'
    with pytest.raises(ConfirmationError,match='FUTURE_TIMESTAMP_REJECTED'):detect_confirmation(seal(x))
