import json
from types import SimpleNamespace
import psycopg
import pytest
from workbench_db.v4_read_index_r1 import prepare,ReadIndex,AUTHORITY,CONTRACT
from workbench_db.v4_native import connection
from workbench_service.core_product_bff_r1 import CoreProductBFFR1

TOKEN='a'*64
DAY='2026-10-13'

def row(sid,value,name='股票',state='OBSERVE'):
    return dict(entity_id=sid,security_id=sid,symbol='SZ.'+sid,display_name=name,
                trade_date=DAY,search_aliases=[sid],source={'path':'large','sha256':'z'*64},
                fields=dict(close=dict(value=value,quality='KNOWN',unit='CNY',source={'path':'large'}),
                            scenario=dict(value=state,quality='KNOWN')))

@pytest.fixture
def index(tmp_path):
    rows=[row('000001',2,'甲'),row('000002',10,'乙'),row('000003',None,'丙')]
    context=dict(context={'trade_date':DAY},context_token=TOKEN,status='READY')
    binding=prepare(tmp_path,TOKEN,DAY,{'stocks':rows}, {'/api/v4/context':context,'/api/v4/home':context}, {'000001':['S1']})
    return ReadIndex(tmp_path,binding,TOKEN,DAY),rows,context

def test_sql_numeric_null_last_search_stable_page_and_filter(index):
    reader,_,_=index
    data=reader.page('stocks',{'sort':'-close','limit':1})
    assert data['total']==3 and data['items'][0]['entity_id']=='000002' and data['has_next']
    assert reader.page('stocks',{'sort':'-close','offset':2})['items'][0]['entity_id']=='000003'
    assert reader.page('stocks',{'sort':'close'})['items'][0]['entity_id']=='000001'
    assert reader.page('stocks',{'q':'SZ.000002'})['total']==1
    assert reader.page('stocks',{'q':'甲'})['total']==1
    assert reader.page('stocks',{'q':'%'})['total']==0
    assert reader.page('stocks',{'state':'MISSING'})['total']==0
    assert reader.page('stocks',{},sector='S1')['total']==1
    last=reader.page('stocks',{'offset':3})
    assert last['total']==3 and last['items']==[] and not last['has_next']
    assert reader.page('stocks',{'sort':'state,-close'})['items'][-1]['entity_id']=='000003'

def test_detail_evidence_retained_summary_bounded(index):
    reader,rows,context=index
    assert reader.detail('stocks','000001')==rows[0]
    assert reader.response('/api/v4/context')==context
    page=reader.page('stocks',{})
    assert 'source' not in page['items'][0] and 'source' not in page['items'][0]['fields']['close']
    assert page['items'][0]['fields']['close']['value']==2

def test_immutable_and_head_day_guards(index):
    reader,rows,_=index
    with pytest.raises(ValueError,match='CONFLICT'):
        prepare(reader.root,TOKEN,DAY,{'stocks':[row('000001',99)]},{},{})
    with pytest.raises(psycopg.Error,match='IMMUTABLE'):
        with connection(reader.binding['schema']) as pg:pg.execute('UPDATE read_items SET summary=%s',('{}',))
    with pytest.raises(ValueError,match='CONTEXT'):
        ReadIndex(reader.root,reader.binding,'b'*64,DAY)
    with pytest.raises(ValueError,match='CONTEXT'):
        ReadIndex(reader.root,reader.binding,TOKEN,'2026-10-12')
    for q in ({'sort':'unsafe;DROP'},{'limit':201},{'offset':-1},{'q':'x'*81}):
        with pytest.raises(ValueError):reader.page('stocks',q)

def test_indexed_bff_never_projects_or_decodes_owner(index):
    reader,_,context=index
    authority=reader.root/AUTHORITY;authority.parent.mkdir(parents=True,exist_ok=True)
    authority.write_text(json.dumps(dict(contract_id=CONTRACT,versions={TOKEN:{DAY:reader.binding}})))
    api=SimpleNamespace(root=reader.root,token=TOKEN,candidate={'published_sessions':[DAY],'accepted_trade_date':DAY})
    class BFF(CoreProductBFFR1):
        def project(self,*a):raise AssertionError('FULL_PROJECT_FORBIDDEN')
        def source(self,*a):raise AssertionError('FULL_OWNER_FORBIDDEN')
    bff=BFF(api,None)
    assert bff.get('/api/v4/context',{})==(200,context)
    code,data=bff.get('/api/v4/stocks',{'context_token':TOKEN,'sort':'-close','limit':'1'})
    assert code==200 and data['total']==3 and len(data['items'])==1
    with pytest.raises(ValueError,match='TOKEN'):bff.get('/api/v4/stocks',{'context_token':'bad'})
    with pytest.raises(ValueError,match='DATE'):bff.get('/api/v4/context',{'trade_date':'2026-10-12'})
