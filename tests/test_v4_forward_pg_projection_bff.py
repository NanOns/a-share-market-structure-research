from types import SimpleNamespace

import pytest


def test_forward_fep_page_uses_only_published_pg_projection(tmp_path, monkeypatch):
    import workbench_db.forward_r7_store as store_module
    import workbench_service.core_product_bff_r1 as bff_module

    class Store:
        def __init__(self, root):
            assert root == tmp_path
        def read_counts(self):
            return {'status':'READY','historical':{'count':4}}
        def read_fep_projections(self):
            return {'status':'READY','total':1,'items':[{
                'stage':'E2','model_id':'model-1','scope':'HISTORICAL_ENGINEERING_DESCRIPTIVE_ONLY',
                'diagnostic_only':False,'sample_count':12,'asof':'2026-10-16',
                'source_hashes':{'catalog':'a'*64},
            }]}

    monkeypatch.setattr(store_module,'ForwardR7Store',Store)
    monkeypatch.setattr(bff_module,'read_r7_fep',lambda *_args,**_kwargs:pytest.fail('local FEP evidence was read'),raising=False)
    bff=object.__new__(bff_module.CoreProductBFFR1)
    bff.api=SimpleNamespace(root=tmp_path)
    bff.envelope=lambda day,**payload:dict(trade_date=day,**payload)

    code,payload=bff._forward_r7_read('/api/v4/forward/fep',{},'2026-10-16')
    assert code==200
    assert payload['data']['pg_projection_status']=='READY'
    assert payload['data']['historical_baselines'][0]['model_id']=='model-1'
    assert payload['source']['relation']=='forward_facts'


def test_forward_fep_page_degrades_without_falling_back_to_reports(tmp_path, monkeypatch):
    import workbench_db.forward_r7_store as store_module
    import workbench_service.core_product_bff_r1 as bff_module

    class Store:
        def __init__(self, root):pass
        def read_counts(self):raise RuntimeError('reader unavailable')

    monkeypatch.setattr(store_module,'ForwardR7Store',Store)
    monkeypatch.setattr(bff_module,'read_r7_fep',lambda *_args,**_kwargs:pytest.fail('local FEP evidence was read'),raising=False)
    bff=object.__new__(bff_module.CoreProductBFFR1)
    bff.api=SimpleNamespace(root=tmp_path)
    bff.envelope=lambda day,**payload:dict(trade_date=day,**payload)

    code,payload=bff._forward_r7_read('/api/v4/forward/fep',{},'2026-10-16')
    assert code==200
    assert payload['status']=='DATA_MISSING'
    assert payload['data']['historical_baselines']==[]
    assert payload['data']['missing_inputs']==['PG_PUBLISHED_FEP_RESEARCH_PROJECTION']
