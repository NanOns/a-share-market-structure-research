from workbench_service.operational_risk_v1 import build_stock_family,build_sector_family,build_market_family
from workbench_service.research_priority_r1 import build_priority
from workbench_service.focus_episode_state_r1 import classify_episode
from workbench_service.candidate_research_read_v2 import first_capture_readiness
from workbench_analysis.validation_cohort_read_contract_r3 import maturity_schedule
from workbench_analysis.v4_15_settlement import due_plan
from datetime import datetime
from zoneinfo import ZoneInfo


def cell(value,quality='KNOWN'):
    return {'value':value,'quality':quality}


def test_risk_families_keep_independent_denominators_and_unknowns():
    current=[{'entity_id':'a','fields':{'core_price_damage':cell(True)}},
             {'entity_id':'b','fields':{'core_price_damage':cell(None,'SOURCE_INCOMPLETE')}}]
    prior=[{'entity_id':'a','fields':{'core_price_damage':cell(False)}}]
    stock=build_stock_family(current,prior,{'current':'core-T','prior':'core-T-1'},'2026-10-13')
    assert (stock['numerator'],stock['denominator'],stock['counts']['DAMAGED'])==(1,2,1)
    assert stock['changes'][0]['change']=='WORSENED'
    sectors=[{'entity_id':'industry','fields':{'health':cell('WEAKENING')}}]
    ecology=build_sector_family(sectors,{'industry':{'health':{'current':'WEAKENING','prior':'NONE'}}},'sector-T','2026-10-13')
    assert (ecology['family'],ecology['denominator'],ecology['change_total'])==('SECTOR_ECOLOGY_RISK',1,1)
    market=build_market_family({'row':{'stress_level':'HIGH','stress_change':'INCREASING'}},'market-T','2026-10-13')
    assert market['family']=='MARKET_PRESSURE_RISK' and market['changes'][0]['change']=='WORSENED'


def test_priority_separates_rankable_from_unknown_and_uses_stable_tiebreak():
    sectors=[
        {'entity_id':'THEME:B','display_name':'B','fields':{
            'maturity':cell('DEVELOPING'),'health':cell('NONE'),'sector_rs5':cell(0.2),'sector_rs20':cell(0.3),'output_state':cell('ROTATION_ACCEPTED')}},
        {'entity_id':'THEME:A','display_name':'A','fields':{
            'maturity':cell('DEVELOPING'),'health':cell('NONE'),'sector_rs5':cell(0.2),'sector_rs20':cell(0.3),'output_state':cell('ROTATION_ACCEPTED')}},
        {'entity_id':'THEME:U','fields':{'maturity':cell('UNKNOWN','SOURCE_INCOMPLETE')}}]
    stocks=[{'entity_id':'stock-A','fields':{
        'core_price_damage':cell(False),'rps20':cell(10),'rps20_delta3':cell(0.1),'ret5':cell(0.02),
        'pos60':cell(0.5),'prior_low20':cell(10),'close':cell(12)}},
        {'entity_id':'stock-U','fields':{'core_price_damage':cell(None,'SOURCE_INCOMPLETE')}}]
    result=build_priority('2026-10-13','token',stocks,sectors,
        {'regime_publication_status':'FACT_AXES_OBSERVED_COMPOSITE_UNACCEPTED'},'core','sector','a'*64)
    assert [row['entity_id'] for row in result['sectors']['items']]==['THEME:A','THEME:B']
    assert result['sectors']['not_rankable_rows'][0]['unknown_inputs']==['maturity','health','sector_rs5','sector_rs20','rotation']
    assert result['stocks']['items'][0]['entity_id']=='stock-A'
    assert result['stocks']['not_rankable_rows'][0]['exclusion_reason'].startswith('MISSING_')
    assert result['market_permission']['status']=='FACT_ONLY_NO_FORMAL_PERMISSION'


def test_focus_episode_close_requires_matching_explicit_owner_event():
    episode={'entity_id':'SEC-A','episode_id':'EP-1','end_date':None}
    assert classify_episode(episode,[])['status']=='ACTIVE'
    assert classify_episode(episode,[{'entity_id':'SEC-A','episode_id':'EP-2','event':'EXITED'}])['status']=='ACTIVE'
    exited=classify_episode(episode,[{'entity_id':'SEC-A','episode_id':'EP-1','event':'EXITED','trade_date':'2026-10-13'}])
    assert exited['status']=='EXITED'
    invalidated=classify_episode(episode,[{'entity_id':'SEC-A','episode_id':'EP-1','event':'INVALIDATED','trade_date':'2026-10-13'}])
    assert invalidated['status']=='INVALIDATED'
    assert classify_episode(dict(episode,end_date='2026-10-13'),[])['status']=='UNKNOWN'


def test_first_capture_missed_cutoff_and_settlement_horizons_are_session_based():
    head={'accepted_trade_date':'2026-10-13','owners':{},'cohort_signal_producers':{},
          'cohort_capture_receipts':{},'cohort_write_grants':{}}
    sessions=['2026-10-13','2026-10-14','2026-10-15','2026-10-16','2026-10-19','2026-10-20']
    before=datetime.fromisoformat('2026-10-14T14:59:00+08:00')
    after=datetime.fromisoformat('2026-10-14T15:01:00+08:00')
    pending=first_capture_readiness(head,'2026-10-14',sessions,evaluated_at=before)
    missed=first_capture_readiness(head,'2026-10-14',sessions,evaluated_at=after)
    assert pending['status']=='PENDING_NEXT_SESSION'
    assert missed['status']=='SOURCE_NOT_CAPTURED'
    assert missed['capture_state']=='NOT_CAPTURED_AT_T0'
    assert missed['historical_backfill_permitted'] is False
    assert missed['settlement_status']=='NOT_DUE'
    assert maturity_schedule('2026-10-14',sessions,'2026-10-15')[1]['status']=='DUE_REQUIRES_SETTLEMENT_OWNER'
    assert due_plan(sessions,'2026-10-14','2026-10-15')[0]['outcome_status']=='DUE'
