from pathlib import Path
import json
import pytest
from workbench_service.r43_operational_bff import OperationalResearchBFF

class API:
    token='exact-token'
    candidate={'dates':['2026-09-30','2026-10-08'],'membership_observed_at':'2026-10-09T09:44:00+08:00'}
    def context(self):return {'accepted_trade_date':'2026-10-08','membership_observed_at':self.candidate['membership_observed_at'],'AS_RECORDED':False,'PIT_ELIGIBLE':False}

def test_existing_context_envelope_and_no_cross_date_fallback():
    bff=OperationalResearchBFF(API(),None)
    code,data=bff.get('/api/v4/forward/statistics',{'context_token':'exact-token'})
    assert code==200 and data['status']=='SOURCE_INCOMPLETE'
    assert data['reason']=='NO_OPERATIONAL_COMPATIBILITY_OWNER_FOR_ROUTE'
    assert data['mixed_date_fallback'] is False and data['legacy_trade_date']=='2026-09-30'
    assert data['context']['accepted_trade_date']=='2026-10-08' and data['context_token']=='exact-token'
    assert data['context']['PIT_ELIGIBLE'] is False

@pytest.mark.parametrize('query,reason',[
 ({'context_token':'stale'},'CONTEXT_TOKEN_MISMATCH'),
 ({'context_token':'exact-token','trade_date':'2026-10-09'},'TARGET_DATE_NOT_GRANTED'),
 ({'context_token':'exact-token','limit':'0'},'INVALID_QUERY_BOUND'),
 ({'context_token':'exact-token','unknown':'1'},'UNKNOWN_PARAMETER')])
def test_compatibility_query_contract(query,reason):
    with pytest.raises(ValueError,match=reason):OperationalResearchBFF(API(),None).get('/api/v4/forward/statistics',query)

def test_search_pagination_and_detail_use_existing_fields_envelope():
    bff=OperationalResearchBFF(API(),None)
    bff.project=lambda domain,day:[{'entity_id':'SEC-1','symbol':'SH.600001','display_name':'样本甲','fields':{'close':{'value':10},'scenario':{'value':'NONE'}}},{'entity_id':'SEC-2','symbol':'SH.600002','display_name':'样本乙','fields':{'close':{'value':11},'scenario':{'value':'UNKNOWN'}}}]
    code,data=bff.get('/api/v4/stocks',{'context_token':'exact-token','q':'600002','sort':'-close','limit':'1'})
    assert code==200 and data['total']==1 and data['items'][0]['entity_id']=='SEC-2'
    code,data=bff.get('/api/v4/stocks/SEC-1',{'context_token':'exact-token'})
    assert data['item']['fields']['close']['value']==10



def test_owner_state_quality_is_preserved_in_compatibility_cell():
    from workbench_service.r43_operational_bff import owner_cell
    ref={'sha256':'exact-owner','contract_id':'REAL_STATE_OWNER'}
    known=owner_cell({'value':'NORMAL','unknown_reason':None},ref,'trend_state','2026-10-08')
    unknown=owner_cell({'value':'UNKNOWN','unknown_reason':'NO_PRIOR_OWNER'},ref,'trend_state','2026-10-08')
    assert known['quality']=='KNOWN' and known['source_digest']=='exact-owner'
    assert unknown['quality']=='UNKNOWN' and unknown['reason']=='NO_PRIOR_OWNER'
    nested=owner_cell({'quality':'UNKNOWN','reason':'NO_TDX_NON_TARGET_MEMBER'},ref,'relative_sector_state','2026-10-08')
    assert nested['quality']=='UNKNOWN' and nested['reason']=='NO_TDX_NON_TARGET_MEMBER'
