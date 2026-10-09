import pytest
from workbench_service.operational_gap_bff_v2 import OperationalGapBFFV2
from test_r43_operational_bff import API


def test_chart_gap_retains_date_and_scope_after_supported_controls():
    bff=OperationalGapBFFV2(API(),None)
    code,payload=bff.get('/api/v4/stocks/SEC-1/chart',{'period':'W','price_basis':'RAW','context_token':'exact-token'})
    assert code==200 and payload['status']=='SOURCE_INCOMPLETE'
    assert payload['context']['accepted_trade_date']=='2026-10-08'
    assert payload['gap']['task_stage']=='FP07'
    assert 'CHART_OWNER' in payload['gap']['missing_owner']
    assert payload['mixed_date_fallback'] is False
    with pytest.raises(ValueError,match='CONTEXT_TOKEN_MISMATCH'):
        bff.get('/api/v4/stocks/SEC-1/chart',{'period':'D','context_token':'wrong'})
    with pytest.raises(ValueError,match='INVALID_CHART_QUERY'):
        bff.get('/api/v4/stocks/SEC-1/chart',{'period':'minute'})


def test_focus_projection_keeps_episode_membership_and_excludes_future_observation(monkeypatch):
    from workbench_service.r43_operational_bff import OperationalResearchBFF
    api=API();api.candidate=dict(api.candidate,owners={'2026-10-08':{'forward':{'sha256':'fixture-only','contract_id':'FOCUS_TEST'}}})
    bff=OperationalGapBFFV2(api,None)
    monkeypatch.setattr(OperationalResearchBFF,'project',lambda self,domain,day:[dict(entity_id='SEC-1',fields={})])
    bff.source=lambda domain,day:dict(episodes=[dict(entity_id='SEC-1',episode_id='fixture-episode',T0='2026-09-28',start_date='2026-09-28',end_date=None,membership='EARLY',
        observations=[dict(trade_date='2026-10-08',event='PERSISTENT',membership='UNKNOWN',validity='UNKNOWN'),dict(trade_date='2026-10-09',event='EXITED')])])
    fields=bff.project('focus','2026-10-08')[0]['fields']
    assert fields['event']['value']=='PERSISTENT'
    assert fields['event']['observation_trade_date']=='2026-10-08'
    assert fields['membership']['value']=='EARLY'
    assert fields['end_date']['quality']=='KNOWN' and fields['end_date']['value'] is None
    assert fields['validity']['reason']=='OWNER_REPORTED_UNKNOWN_VALIDITY'
