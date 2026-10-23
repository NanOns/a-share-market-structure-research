"""SourceIngress V2：显式来源、真实原始包数值与时间边界。"""
import hashlib
import json
import struct
import zipfile

import pytest

from scripts.r8_batch04_ingest_tdx_source import _load_days


def _binding(path):
    return dict(path=str(path),sha256=hashlib.sha256(path.read_bytes()).hexdigest(),bytes=path.stat().st_size)


def _write(path,value):
    path.write_text(json.dumps(value),encoding='utf8');return _binding(path)


def _fixture(root):
    package=root/'native.zip';member='sh/lday/sh600001.day'
    blob=struct.pack('<IIIIIfII',20260303,1000,1100,900,1050,1000.0,100,0)
    with zipfile.ZipFile(package,'w') as archive:archive.writestr(member,blob)
    pack=_binding(package)
    receipt=_write(root/'capture.json',dict(contract_id='TDX_OFFICIAL_DAILY_PACKAGE_SOURCE_V1',
        status='TDX_PACKAGE_READY',download=pack,update_date='2026-03-04',tdx_root_write_count=0,
        observed_at='2026-03-04T08:00:00+00:00',downloaded_at='2026-03-04T08:00:20+00:00'))
    document=dict(target_session='2026-03-03',status='TARGET_BARS_EXTRACTED',provider_package_date='2026-03-04',
        source_sha256=pack['sha256'],row_count=1,tdx_root_write_count=0,reconstruction_from_later_snapshot=True,
        source_available_at='2026-03-04T08:00:20+00:00',target_bars=[dict(source_security_key='SH.600001',
            source_entry=member,entry_sha256=hashlib.sha256(blob).hexdigest(),trade_date='2026-03-03',
            open=10,high=11,low=9,close=10.5,amount=1000,volume=100)])
    artifact=_write(root/'bars.json',document)
    manifest=dict(contract_id='V4_TDX_SOURCE_INGRESS_INPUT_V2',package=pack,capture_receipt=receipt,
                  dates={'2026-03-03':artifact})
    path=root/'input.json';_write(path,manifest)
    return path,manifest,document


def test_dynamic_session_and_exact_native_values(tmp_path):
    path,_,_=_fixture(tmp_path)
    rows=_load_days(tmp_path,('2026-03-03',),path)
    assert len(rows)==1 and rows[0]['day']=='2026-03-03'


@pytest.mark.parametrize('kind',['price','amount','timestamp','wrong_day','duplicate','future_package'])
def test_self_consistent_manifest_cannot_fake_native_values_or_clocks(tmp_path,kind):
    path,manifest,document=_fixture(tmp_path)
    if kind=='price':document['target_bars'][0]['close']=10.6
    if kind=='amount':document['target_bars'][0]['amount']=1001
    if kind=='timestamp':document['source_available_at']='2026-03-04T08:00:00+00:00'
    if kind=='wrong_day':document['target_bars'][0]['trade_date']='2026-03-02'
    if kind=='duplicate':document['target_bars']*=2;document['row_count']=2
    if kind=='future_package':document['provider_package_date']='2026-03-02'
    manifest['dates']['2026-03-03']=_write(tmp_path/'bars.json',document)
    _write(path,manifest)
    with pytest.raises(ValueError):_load_days(tmp_path,('2026-03-03',),path)


def test_no_implicit_historical_date_list(tmp_path):
    path,_,_=_fixture(tmp_path)
    with pytest.raises(ValueError,match='TARGET_BINDING_MISSING'):
        _load_days(tmp_path,('2026-03-05',),path)


def test_asof_and_data_date_conflict_is_rejected():
    from workbench_db.v4_read_index_r2 import validate_query
    days=['2026-03-03','2026-03-04'];token='a'*64
    assert validate_query({'as_of':days[0],'context_token':token},token,days,days[-1],'/api/v4/stocks')==days[0]
    with pytest.raises(ValueError,match='AS_OF_TRADE_DATE_MISMATCH'):
        validate_query({'trade_date':days[0],'as_of':days[1],'context_token':token},token,days,days[-1],'/api/v4/stocks')
