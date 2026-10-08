import gzip,json
from types import SimpleNamespace
import pytest
from focus_tracker.v4_native_core_adapter import AcceptedPaths,CAPABILITY
from workbench_service.current_v4_context import SourceInvalid,digest

def test_native_facts_require_observation_date_and_matching_price_coordinate():
    paths=AcceptedPaths.__new__(AcceptedPaths)
    paths.native={'2026-09-30':({'trade_date':'2026-09-30'},{'A':dict(close=10,ma20=9,ret5=.1,severe_extension=False)})}
    ready=dict(quality='READY',close='10')
    assert paths.native_facts('A','2026-09-29',ready)['facts']=={}
    actual=paths.native_facts('A','2026-09-30',ready)
    assert actual['facts']==dict(ma20=9,r5=.1,source_extended=False)
    with pytest.raises(SourceInvalid,match='COORDINATE_END_MISMATCH'):
        paths.native_facts('A','2026-09-30',dict(quality='READY',close='11'))
    assert paths.native_facts('A','2026-09-30',dict(quality='DATA_UNAVAILABLE'))['facts']=={}

def test_native_loader_rejects_future_row_and_parameter_revision(tmp_path,monkeypatch):
    monkeypatch.setattr('focus_tracker.v4_native_core_adapter.PricePaths.__init__',lambda *a:None)
    def binding(name,row):
        path=tmp_path/name;path.write_bytes(gzip.compress((json.dumps(row)+'\n').encode()));return dict(path=name,sha256=digest(path.read_bytes()))
    owner=dict(contract_id=CAPABILITY,trade_date='2026-09-30',price_basis='TDX_NATIVE_AFFINE_QFQ_TARGET_COORDINATE',factors=binding('f.gz',dict(security_id='A',trade_date='2026-10-09',fields={})),profiles=binding('p.gz',{}))
    with pytest.raises(SourceInvalid,match='DATE_MIX'):AcceptedPaths(tmp_path,dict(native_core={'2026-09-30':owner}))
    owner['factors']=binding('f.gz',dict(security_id='A',trade_date='2026-09-30',fields={key:dict(value=10,parameter_set_id='unregistered',window_end_trade_date='2026-09-30') for key in ('ma20','ret5','close')}))
    with pytest.raises(SourceInvalid,match='PARAMETER'):AcceptedPaths(tmp_path,dict(native_core={'2026-09-30':owner}))
