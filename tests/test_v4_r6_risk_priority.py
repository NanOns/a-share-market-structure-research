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
    day='2026-10-13';proof={'input_digest':'a'*64,'producer_sha256':'b'*64,
        'parameter_sha256':'c'*64,'source_bindings':{'2026-10-13':{'sector':{'sha256':'d'*64}}}}
    def dated(value):return {'value':value,'quality':'KNOWN','as_of':day,'source':proof}
    def metric(value):return {'value':value,'quality':'OBSERVED','as_of':day}
    sectors=[
        {'entity_id':'THEME:B','display_name':'B','fields':{
            'maturity':dated('DEVELOPING'),'health':dated('NONE'),'sector_rs5':metric(0.2),'sector_rs20':metric(0.3),'output_state':dated('ROTATION_ACCEPTED')}},
        {'entity_id':'THEME:A','display_name':'A','fields':{
            'maturity':dated('DEVELOPING'),'health':dated('NONE'),'sector_rs5':metric(0.2),'sector_rs20':metric(0.3),'output_state':dated('ROTATION_ACCEPTED')}},
        {'entity_id':'THEME:U','fields':{'maturity':cell('UNKNOWN','SOURCE_INCOMPLETE')}}]
    stocks=[{'entity_id':'stock-A','fields':{
        'core_price_damage':cell(False),'rps20':cell(10),'rps20_delta3':cell(0.1),'ret5':cell(0.02),
        'pos60':cell(0.5),'prior_low20':{**cell(10),'adjustment_basis':'TDX_NATIVE_AFFINE_QFQ_T0_COORDINATE'},'close':{**cell(12),'adjustment_basis':'TDX_NATIVE_AFFINE_QFQ_T0_COORDINATE'}}},
        {'entity_id':'stock-U','fields':{'core_price_damage':cell(None,'SOURCE_INCOMPLETE')}}]
    result=build_priority('2026-10-13','token',stocks,sectors,
        {'regime_publication_status':'FACT_AXES_OBSERVED_COMPOSITE_UNACCEPTED'},'core','sector','a'*64)
    assert [row['entity_id'] for row in result['sectors']['items']]==['THEME:A','THEME:B']
    assert result['sectors']['not_rankable_rows'][0]['unknown_inputs']==['maturity','health','sector_rs5','sector_rs20','rotation']
    assert result['stocks']['items'][0]['entity_id']=='stock-A'
    assert result['stocks']['not_rankable_rows'][0]['exclusion_reason']=='MISSING_INPUT'
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


def test_r7_market_stress_cache_is_source_versioned_and_separate(monkeypatch):
    from workbench_service.core_product_bff_r1 import CoreProductBFFR1
    from workbench_analysis import r6_candidate_market_stress as stress

    class API:
        token='same-token'
        root='G:/codex_tmp/isolated-candidate'
        candidate={'owner_version':'A'}
        cache={}

    api=API();api.cache={}
    bff=object.__new__(CoreProductBFFR1);bff.api=api
    monkeypatch.setattr(stress,'candidate_market_stress_identity',lambda root,candidate:candidate['owner_version'])
    monkeypatch.setattr(stress,'build_candidate_market_stress',lambda root,candidate:{'T0':'2026-10-14','market_stress':candidate['owner_version']})
    first,first_diagnostics=bff._candidate_market_stress()
    assert first['market_stress']=='A' and first_diagnostics['cache_hit'] is False
    assert 'cache' not in first
    repeated,repeated_diagnostics=bff._candidate_market_stress()
    assert repeated['market_stress']=='A' and repeated_diagnostics['cache_hit'] is True
    api.candidate={'owner_version':'B'}
    replaced,replaced_diagnostics=bff._candidate_market_stress()
    assert replaced['market_stress']=='B' and replaced_diagnostics['cache_hit'] is False
    assert 'cache' not in replaced
    assert len(api.cache)==2


def test_r7_frozen_invalidation_contract_vectors_preserve_unknown():
    import json
    from pathlib import Path
    from workbench_analysis.r7_frozen_invalidation_v2 import evaluate_frozen_invalidation,load_contract

    contract,contract_sha=load_contract()
    assert contract['contract_id']=='FROZEN_INVALIDATION_CONTRACT_R2' and len(contract['vector_set'])>=12
    assert len(contract_sha)==64
    for vector in contract['vector_set']:
        result=evaluate_frozen_invalidation(
            prior_episode=vector.get('prior_episode'),
            current_close=vector.get('current_close'),
            frozen_invalidation_level=vector.get('frozen_invalidation_level'),
            current_price_basis_id=vector.get('current_price_basis_id','QFQ-1'),
            frozen_price_basis_id=vector.get('frozen_price_basis_id','QFQ-1'),
            current_bar_status=vector.get('current_bar_status','ACTUAL'),
            current_source_sha256=vector.get('current_source_sha256','a'*64),
            trade_date=vector.get('trade_date','2026-10-14'),
            source_trade_date=vector.get('source_trade_date','2026-10-14'))
        assert result['value']==vector['expected'],vector['id']
        assert result['status']==('IMPLEMENTED' if vector['expected'] in ('TRUE','FALSE') else
                                  'NOT_APPLICABLE' if vector['expected']=='NOT_APPLICABLE' else 'UNKNOWN'),vector['id']
