import struct
from workbench_analysis.market_source_acquisition import corrected_candidate, read_day_bytes, official_sessions, is_stock_code
from pathlib import Path


def test_calendar_holiday_and_exact_predecessors():
    assert not is_stock_code('sz.399001') and is_stock_code('sz.300010')
    assert not is_stock_code('bj.899050') and not is_stock_code('bj.899601')
    assert is_stock_code('bj.920001') and is_stock_code('bj.830001')
    dates = official_sessions(Path(__file__).resolve().parents[1])
    assert dates[dates.index('2026-10-08')-1]=='2026-09-30'
    assert dates[dates.index('2026-09-30')-3]=='2026-09-24'
    assert not any(f'2026-10-{i:02}' in dates for i in range(1,8))


def test_day_target_not_stale_tail_or_wrong_unit():
    raw=struct.pack('<IIIIIfII',20260910,123,130,120,125,2000.,100,0)
    bars, last=read_day_bytes(raw,['2026-10-08'])
    assert bars=={} and last==20260910
    bars,_=read_day_bytes(raw,['2026-09-10'])
    assert bars['2026-09-10']['open']==1.23 and bars['2026-09-10']['volume']==100


def test_candidate_gates_and_coordinate_never_mix():
    row=dict(code='sh.600000',date='2026-10-08',tradestatus='1',open='10',high='11',low='9',close='10',volume='100',amount='1000')
    gates=dict(identity_verified=True,session_verified=True,overlap_verified=True,tolerance_accepted=True,coordinate_verified=False)
    out=corrected_candidate(None,row,**gates)
    assert out['status']=='BAOSTOCK_FALLBACK_CORRECTED' and not out['ATR_allowed'] and not out['production_admission']
    assert corrected_candidate({'close':9},row,**gates)['status']=='TDX_PRESERVED'
    assert corrected_candidate(None,row|dict(tradestatus='0'),**gates)['status']=='REJECTED_WITH_EVIDENCE'
    assert corrected_candidate(None,row|dict(high='nan'),**gates)['status']=='REJECTED_WITH_EVIDENCE'
    assert corrected_candidate(None,row,**(gates|dict(identity_verified=False)))['status']=='REJECTED_WITH_EVIDENCE'


def test_official_failure_does_not_skip_bao_and_errors_are_not_empty(tmp_path,monkeypatch):
    import json
    import workbench_analysis.market_source_acquisition as m
    (tmp_path/'config').mkdir()
    for name,value in [('v4_market_source_fallback_policy_v1.json',dict(contract_id=m.CONTRACT,production_admission=False)),
                       ('dm01_go_forward_runtime_contract_r4.json',dict(read_only_tdx_roots=[]))]:
        (tmp_path/'config'/name).write_text(json.dumps(value))
    monkeypatch.setattr(m,'official_sessions',lambda root:['2026-10-08'])
    monkeypatch.setattr(m.time,'sleep',lambda _:None)
    def fail(**kwargs):raise OSError('realistic transport failure')
    monkeypatch.setattr(m,'capture_tdx_official_daily_package',fail)
    class SDK:
        def __getattr__(self,name):return lambda **kwargs:None
    class Client:
        sdk=SDK();login_result={'error_code':'0'};logout_result={'error_code':'0'};runtime_endpoint={};last_query_result={}
        def __init__(self,*a,**k):pass
        def __enter__(self):return self
        def __exit__(self,*a):pass
        _safe_message=staticmethod(str)
        def query_rows(self,operation,method,**params):
            if method=='query_daily_history_k_AStock':raise TimeoutError('bounded timeout')
            return [],{'error_code':'0','page_count':1}
    monkeypatch.setattr(m,'BaoStockClient',Client)
    result=m.acquire(tmp_path,['2026-10-08'],tmp_path/'evidence')
    assert len(result['official']['2026-10-08'])==2
    failures=[q for q in result['queries'] if q['method']=='query_daily_history_k_AStock']
    assert len(failures)==2 and all(q['status']=='PROVIDER_CALL_ERROR' for q in failures)
    assert any(q['status']=='PROVIDER_EMPTY_CONFIRMED' for q in result['queries'])
    first_empty=next(q for q in result['queries'] if q.get('path'))
    frozen=Path(first_empty['path']).read_bytes()
    resumed=m.acquire(tmp_path,['2026-10-08'],tmp_path/'evidence')
    assert Path(first_empty['path']).read_bytes()==frozen
    versions={q['path'] for q in resumed['queries'] if q['method']==first_empty['method'] and q.get('path')}
    assert len(versions)==2
