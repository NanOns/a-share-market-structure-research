"""Isolated controlled-clock source cache tests; no real provider calls."""
from datetime import datetime
import pytest
import workbench_analysis.operational_daily_executor_v1 as module
from daily_contract_pg_fixture import install as install_daily_contract_pg_fixture
from daily_contract_pg_fixture import install_calendar as install_daily_calendar_pg_fixture


def test_daily_runtime_contract_rejects_file_authority_mode(monkeypatch):
    monkeypatch.setenv('V4_DAILY_CONTRACT_SOURCE','FILE')
    with pytest.raises(ValueError,match='DAILY_RUNTIME_CONTRACT_PG_ONLY'):
        module._daily_runtime_contract('V4_DAILY_TDX_READONLY_SOURCE_R1','1.1.0')


def test_daily_runtime_contract_reads_approved_registry_with_identity(monkeypatch):
    from contextlib import contextmanager
    import workbench_analysis.contract_registry_pg_v1 as registry
    from workbench_db import v4_publication_reader

    monkeypatch.delenv('V4_DAILY_CONTRACT_SOURCE',raising=False)
    monkeypatch.setenv('V4_PG_MODEL_NAMESPACE_ID','daily_ns')
    identity={'database':'market_research','database_oid':42,'host':'127.0.0.1','port':5432}
    monkeypatch.setenv('V4_PG_EXPECTED_DATABASE_IDENTITY_JSON',__import__('json').dumps(identity))
    calls=[]
    @contextmanager
    def connection():
        yield object()
    def load(pg,contract_id,version,namespace,**kwargs):
        calls.append((contract_id,version,namespace,kwargs))
        return type('Registered',(),{'parsed_json':{
            'contract_id':contract_id,'contract_version':version,
            'source_mode':'READ_ONLY_INPUT','gbbq_relative_path':'T0002/hq_cache/gbbq'}})()
    monkeypatch.setattr(v4_publication_reader,'readonly_connection',connection)
    monkeypatch.setattr(registry,'load_current_approved_contract',load)

    result=module._daily_runtime_contract('V4_DAILY_TDX_READONLY_SOURCE_R1','1.1.0')

    assert result['gbbq_relative_path']=='T0002/hq_cache/gbbq'
    assert calls==[('V4_DAILY_TDX_READONLY_SOURCE_R1','1.1.0','daily_ns',
                    {'expected_database_identity':identity})]


def test_accepted_trade_date_rejects_file_head_authority(tmp_path,monkeypatch):
    (tmp_path/'data/v4').mkdir(parents=True)
    (tmp_path/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json').write_text(
        '{"accepted_trade_date":"2026-10-16"}',encoding='utf-8')
    monkeypatch.setenv('V4_MARKET_CALENDAR_SOURCE','FILE')
    with pytest.raises(ValueError,match='MARKET_CALENDAR_PG_ONLY'):
        module._accepted_trade_date(tmp_path)


def test_baostock_runtime_acceptance_rejects_file_authority_mode(monkeypatch):
    monkeypatch.setenv('V4_BAOSTOCK_RUNTIME_ACCEPTANCE_SOURCE','FILE')
    with pytest.raises(ValueError,match='BAOSTOCK_RUNTIME_ACCEPTANCE_PG_ONLY'):
        module._runtime_acceptance_source_mode()


@pytest.mark.parametrize('downloaded,expected',['2026-10-09T17:45:00+08:00,2'.split(','),
                                              '2026-10-09T18:36:00+08:00,1'.split(',')])
def test_missing_target_refreshes_pre_gate_capture_once(tmp_path,monkeypatch,downloaded,expected):
    install_daily_contract_pg_fixture(monkeypatch,module)
    monkeypatch.setenv('V4_DAILY_CONTRACT_SOURCE','PG')
    monkeypatch.setenv('V4_BAOSTOCK_RUNTIME_ACCEPTANCE_SOURCE','PG')
    monkeypatch.setenv('TDX_ROOT',str(tmp_path/'readonly-tdx-root'))
    monkeypatch.setenv('TDX_SNAPSHOT_ROOT',str(tmp_path/'snapshots'))
    class Clock(datetime):
        @classmethod
        def now(cls,tz=None):return datetime.fromisoformat('2026-10-09T18:40:00+08:00').astimezone(tz)
    calls=[]
    def capture(**kwargs):
        calls.append(kwargs.get('force_refresh',False))
        return dict(download={'path':'fixture'},provider_package_date='2026-10-09',
                    downloaded_at=downloaded,observed_at=downloaded)
    monkeypatch.setattr(module,'datetime',Clock)
    monkeypatch.setattr(module,'capture_latest_tdx_package',capture)
    monkeypatch.setattr(module,'extract_target_session_bars',lambda *a,**k:dict(status='WAIT_TDX_TARGET_BARS'))
    def runtime(*a,**k):raise RuntimeError('STOP_BEFORE_ANY_SDK_CALL')
    monkeypatch.setattr(module,'_load_pg_runtime_acceptance',runtime)
    with pytest.raises(RuntimeError,match='STOP_BEFORE_ANY_SDK_CALL'):
        module.execute_sources(tmp_path,'2026-10-09','CATCH_UP',capture_only=True)
    assert len(calls)==int(expected)
    assert calls==([False,True] if int(expected)==2 else [False])


def test_execute_sources_uses_pg_acceptance_and_freezes_its_binding(tmp_path,monkeypatch):
    import json
    from datetime import datetime,timezone,timedelta
    root=tmp_path
    install_daily_contract_pg_fixture(monkeypatch,module)
    day=datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=8))).date().isoformat()
    prior=(datetime.fromisoformat(day)-timedelta(days=1)).date().isoformat()
    head=root/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json';head.parent.mkdir(parents=True,exist_ok=True)
    head.write_text(json.dumps({'accepted_trade_date':prior}))
    schema=root/'config/baostock_dm01_sdk_schema_adapter_v2.json';schema.parent.mkdir(parents=True,exist_ok=True)
    schema.write_text('{}')
    for key in ('V4_BAOSTOCK_RUNTIME_ACCEPTANCE_SOURCE','V4_DAILY_CONTRACT_SOURCE'):
        monkeypatch.delenv(key,raising=False)
    install_daily_calendar_pg_fixture(monkeypatch,prior)
    monkeypatch.setenv('TDX_ROOT',str(root/'read-only-tdx'))
    monkeypatch.setenv('TDX_SNAPSHOT_ROOT',str(root/'data/v4/snapshots'))
    monkeypatch.setattr(module,'source_readiness',lambda *_a,**_k:{'time_eligible':True})
    now=datetime.now(timezone.utc).isoformat()
    package={'download':{'sha256':'d'*64},'provider_package_date':day,'observed_at':now}
    bars={'status':'TARGET_BARS_EXTRACTED','artifact':{'path':'inputs/tdx.json','sha256':'e'*64},
          'source_available_at':now,'row_count':1}
    monkeypatch.setattr(module,'capture_latest_tdx_package',lambda **_k:package)
    monkeypatch.setattr(module,'extract_target_session_bars',lambda *_a,**_k:bars)
    raw={'target_date':day,'observed_at':now,'daily_rows':[{'code':'sh.600000'}],
         'daily_metadata':{'error_code':'0'},'adjustment_factor_rows':[],
         'adjustment_factor_metadata':{'error_code':'0'}}
    raw_path=root/'data/v4/runtime_pg_ingress_cache/baostock'/day.replace('-','')/'native_response.json'
    raw_path.parent.mkdir(parents=True,exist_ok=True);raw_path.write_text(json.dumps(raw))
    manifest={'live_smoke':{'target_date':day,
        'daily':{'response_sha256':'a'*64},'adjustment_factor':{'response_sha256':'b'*64}}}
    receipt={'observed_at':now}
    manifest_path=root/'data/v4/runtime_pg_ingress_cache/baostock'/day.replace('-','')/'accepted_runtime_manifest.json'
    manifest_path.write_text(json.dumps(manifest))
    pg_binding={'path':raw_path.relative_to(root).as_posix(),'sha256':module.tdx.sha256_file(raw_path),
        'bytes':raw_path.stat().st_size,'source':'PG_FACT_DERIVED_CACHE','pg_payload_sha256':'c'*64}
    bundle={'database_identity':{'database':'market_research','database_oid':42,'host':'127.0.0.1','port':5432},
            'schema':'v4_fixture','payload_sha256':'c'*64}
    monkeypatch.setattr(module,'_load_pg_runtime_acceptance',lambda *_a,**_k:dict(
        manifest=manifest,receipt=receipt,raw=raw,raw_path=raw_path,manifest_path=manifest_path,
        manifest_sha256=module.tdx.sha256_file(manifest_path),native_response_binding=pg_binding,bundle=bundle))
    monkeypatch.setattr(module,'_canonical_rows_digest',lambda rows:'a'*64 if rows else 'b'*64)
    monkeypatch.setattr(module,'normalize_response',lambda rows,meta,**_k:(rows,meta))
    monkeypatch.setattr(module,'package_metadata',lambda:{'package':'baostock','version':'test'})
    from workbench_analysis import tdx_local_daily_fallback_v1 as fallback
    monkeypatch.setattr(fallback,'fallback',lambda p,b,*_a,**_k:(p,b,None))
    monkeypatch.setattr(module,'verify_source_gate',lambda *args,**_k:(args[3],
        {'source_ready':False,'status':'WAIT_SYNTHETIC_GATE','reason':'controlled test boundary'}))
    from workbench_analysis import producer_bootstrap_v1 as bootstrap
    monkeypatch.setattr(bootstrap,'capture_daily_sources',lambda *_a,**_k:{'candidate':None})
    monkeypatch.setattr(module,'_pg_source_ingest_plan_diagnostic',lambda *_a,**_k:None)

    result=module.execute_sources(root,day,'CATCH_UP')
    frozen=json.loads((root/result['source_freeze']['path']).read_bytes())
    assert result['status']=='WAIT_SYNTHETIC_GATE'
    assert frozen['runtime_acceptance_pg']['database_identity']==bundle['database_identity']
    assert frozen['runtime_acceptance_pg']['payload_sha256']=='c'*64
    assert frozen['runtime_acceptance_pg']['native_response']==pg_binding
