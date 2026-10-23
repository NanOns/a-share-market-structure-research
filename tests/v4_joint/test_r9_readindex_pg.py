"""真实候选 ReadIndex 的分页、日期、token 与坏摘要读回。"""
import json
import os
from pathlib import Path

import pytest

pytestmark=pytest.mark.skipif(os.environ.get('R9_READINDEX_E2E')!='1',reason='需已准备的候选 ReadIndex 与开发 PG')


def test_real_candidate_index_isolated_pages_dates_and_digests():
    from workbench_db.forward_r7_store import _configured_forward_dsn
    from workbench_db.v4_read_index_r2 import load,ReadIndex
    from workbench_analysis.operational_successor_v1 import OperationalSuccessorReaderV1
    from workbench_service.core_product_bff_r1 import CoreProductBFFR1
    os.environ['V4_NATIVE_PG_DSN']=_configured_forward_dsn(Path(__file__).resolve().parents[2])
    records=json.loads(Path(os.environ['R9_READINDEX_INPUT']).read_bytes())
    tokens=[r['candidate_context_token'] for r in records]
    for record in records:
        root=Path(record['scope']['source_workspace']);day=record['T0'];token=record['candidate_context_token']
        index=load(root,token,day)
        assert index is not None
        page=index.page('stocks',{'limit':'30','offset':'0','sort':'id'})
        following=index.page('stocks',{'limit':'30','offset':'30','sort':'id'})
        assert page['total']==record['counts']['stocks']['total']
        assert not {r['entity_id'] for r in page['items']}&{r['entity_id'] for r in following['items']}
        detail=index.detail('stocks',page['items'][0]['entity_id'])
        assert detail['trade_date']==day
        assert index.response('/api/v4/context')['context_token']==token
        with pytest.raises(ValueError,match='CONTEXT_MISMATCH'):ReadIndex(root,index.binding,tokens[1-tokens.index(token)],day)
        with pytest.raises(ValueError,match='SCHEMA_MISMATCH|DIGEST_MISMATCH'):
            broken=ReadIndex(root,dict(index.binding,digest='0'*64),token,day)
            broken.response('/api/v4/context')
        candidate=json.loads((root/record['candidate_binding']['path']).read_bytes())
        bff=CoreProductBFFR1(OperationalSuccessorReaderV1(root,candidate),None)
        status,response=bff.get('/api/v4/stocks',{'context_token':token,'as_of':day,'limit':'3'})
        assert status==200 and response['context_token']==token and response['data_trade_date']==day
        other=next(r['T0'] for r in records if r['T0']!=day)
        with pytest.raises(ValueError,match='AS_OF_TRADE_DATE_MISMATCH'):
            bff.get('/api/v4/stocks',{'context_token':token,'trade_date':day,'as_of':other})
        if other<day:
            historical=load(root,token,other)
            item=historical.page('stocks',{'limit':'1'})['items'][0]
            assert historical.detail('stocks',item['entity_id'])['trade_date']==other
            status,body=bff.get('/api/v4/stocks',{'context_token':token,'as_of':other,'limit':'2'})
            assert status==200 and body['data_trade_date']==other and body['snapshot_context_trade_date']==day
            assert body['dated_owner_bindings']==candidate['owners'][other]
            status,home=bff.get('/api/v4/home',{'context_token':token,'as_of':other})
            assert status==200 and home['data_trade_date']==other
            assert home['market']['candidate_trend_review']['as_of']==other
