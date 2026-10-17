import pytest
from workbench_analysis.operational_new_listing_r1 import validate_basic
from workbench_analysis.security_entity_identity import stable_security_id

def basic(**kwargs):
    return dict(code='sz.301999',ipoDate='2026-10-13',outDate='',type='1',status='1',code_name='Example',**kwargs)

def test_current_day_ipo_stable_id_and_date_boundary():
    row=validate_basic('SZ.301999','2026-10-13',[basic()],set())
    assert row['security_id']==stable_security_id('SZ','SZ.301999','2026-10-13')
    from workbench_analysis.r43_operational_sources import date_valid_identity
    assert not date_valid_identity(row,'2026-10-12')
    assert date_valid_identity(row,'2026-10-13')
    assert row['board_scope']=='CHINEXT' and row['AS_RECORDED'] is False

@pytest.mark.parametrize('field,value',[('ipoDate','2026-10-12'),('ipoDate','2026-10-14'),('code','sz.301998'),('type','2'),('status','0'),('outDate','2026-10-13')])
def test_bad_lifecycle_or_code_stays_blocked(field,value):
    row=basic();row[field]=value
    with pytest.raises(ValueError):validate_basic('SZ.301999','2026-10-13',[row],set())

def test_duplicate_and_colliding_identity_stays_blocked():
    with pytest.raises(ValueError):validate_basic('SZ.301999','2026-10-13',[basic(),basic()],set())
    with pytest.raises(ValueError):validate_basic('SZ.301999','2026-10-13',[basic()],{stable_security_id('SZ','SZ.301999','2026-10-13')})


from workbench_analysis.operational_new_listing_r1 import observed_identity, classify_codes

def test_older_listing_admitted_as_independent_observed_code():
    metadata=basic();metadata['ipoDate']='2020-01-01'
    row=observed_identity('SZ.301999','2026-10-13',[metadata],set())
    assert row['code_status']=='NEW_CODE_UNLINKED'
    assert row['list_date']==row['first_seen_date']=='2026-10-13'
    assert row['confirmed_ipo_date']=='2020-01-01'
    assert row['security_id']==stable_security_id('SZ','SZ.301999','2026-10-13')
    assert row['alias_status']=='UNVERIFIED'

def test_metadata_missing_does_not_invent_ipo_or_change_stable_id():
    row=observed_identity('SZ.301999','2026-10-13',[],set())
    enhanced=observed_identity('SZ.301999','2026-10-13',[basic()],set())
    assert row['confirmed_ipo_date'] is None and row['metadata_status']=='METADATA_PENDING'
    assert row['security_id']==enhanced['security_id']
    assert enhanced['code_status']=='CONFIRMED_IPO'

@pytest.mark.parametrize('code',['BJ.830001','SZ.399001','SH.000001','SZ.3019999','sz.301999'])
def test_unsupported_code_cannot_gain_identity(code):
    with pytest.raises(ValueError):observed_identity(code,'2026-10-13',[],set())

def pair(code='SZ.301999'):
    daily=dict(code=code,date='2026-10-13',tradestatus='1',open='10',high='11',low='9',close='10.5',volume='100')
    native=dict(source_security_key=code,trade_date='2026-10-13',open=10,high=11,low=9,close=10.5,volume=100)
    return daily,native

def test_simulated_code_change_retains_missing_entity_and_no_alias():
    daily,native=pair()
    changes=classify_codes({'SZ.301998'},[daily],[native],'2026-10-13')
    assert changes['new_codes']==['SZ.301999'] and changes['absent_codes']==['SZ.301998']
    assert changes['identity_coverage']=='COMPLETE' and changes['absence_is_delisting_evidence'] is False

def test_conflict_is_explicit_single_object_quarantine():
    good,good_native=pair('SZ.301998');bad,bad_native=pair();bad_native['close']=11
    changes=classify_codes({'SZ.301998'},[good,bad],[good_native,bad_native],'2026-10-13')
    assert changes['valid_codes']==['SZ.301998'] and changes['new_codes']==[]
    assert changes['identity_coverage']=='PARTIAL_READY'
    assert changes['invalid_codes']==[dict(code='SZ.301999',reasons=['NATIVE_VALUE_MISMATCH:close'],usable_bar=False)]

@pytest.mark.parametrize('change',['duplicate','nan','wrong_day','one_source'])
def test_invalid_facts_never_admit_new_code(change):
    daily,native=pair();ds=[daily];ns=[native]
    if change=='duplicate':ds.append(dict(daily))
    elif change=='nan':daily['close']='NaN'
    elif change=='wrong_day':native['trade_date']='2026-10-14'
    else:ns=[]
    changes=classify_codes(set(),ds,ns,'2026-10-13')
    assert not changes['new_codes'] and changes['invalid_codes']

def test_absent_code_has_no_fabricated_suspension_bar():
    changes=classify_codes({'SZ.301998'},[],[],'2026-10-13')
    assert changes['absent_codes']==['SZ.301998'] and changes['valid_codes']==[]
    assert changes['absence_is_delisting_evidence'] is False


def test_suspended_new_code_requires_verified_security_metadata():
    with pytest.raises(ValueError):observed_identity('SZ.301999','2026-10-13',[],set(),'0')
    assert observed_identity('SZ.301999','2026-10-13',[basic()],set(),'0')['observation_status']=='SUSPENDED'

def test_absent_only_adapter_retains_identity_and_previous_bytes(tmp_path):
    import json
    from pathlib import Path
    from workbench_analysis.operational_new_listing_r1 import admitted_identity,CONTRACT
    from workbench_analysis.r43_owner_replay import ref,checked,load
    policy=Path(__file__).resolve().parents[1]/'config/v4_operational_new_listing_r1.json'
    (tmp_path/'config').mkdir();(tmp_path/'config/v4_operational_new_listing_r1.json').write_bytes(policy.read_bytes())
    previous=dict(rows=[observed_identity('SZ.301998','2026-10-12',[],set())])
    p=tmp_path/'identity.json';p.write_text(json.dumps(previous));before=p.read_bytes()
    gate=dict(dependency_bindings=dict(identity=ref(tmp_path,p),unknown_codes=[],missing_codes=['SZ.301998']),native_provider_facts=dict(status='NATIVE_PROVIDERS_RECONCILED'))
    freeze=dict(normalized=dict(daily=dict(rows=[])),native_baostock=dict(path='raw.json',sha256='a'*64),tdx=dict(path='native.json',sha256='b'*64))
    result=load(checked(tmp_path,admitted_identity(tmp_path,'2026-10-13',gate,freeze)))
    assert result['rows']==previous['rows'] and p.read_bytes()==before
    assert result['code_observations']==[dict(code='SZ.301998',status='NOT_OBSERVED',absence_is_delisting_evidence=False)]
    assert result['contract_id']==CONTRACT

def test_cached_older_metadata_admitted_without_network_and_repeat_id(tmp_path):
    import json
    from pathlib import Path
    from workbench_analysis.operational_new_listing_r1 import admitted_identity
    from workbench_analysis.r43_owner_replay import ref,checked,load
    policy=Path(__file__).resolve().parents[1]/'config/v4_operational_new_listing_r1.json'
    (tmp_path/'config').mkdir();(tmp_path/'config/v4_operational_new_listing_r1.json').write_bytes(policy.read_bytes())
    p=tmp_path/'identity.json';p.write_text(json.dumps(dict(rows=[])))
    folder=tmp_path/'data/v4/dynamic_daily_sources/new_listing_r1/2026-10-13';folder.mkdir(parents=True)
    metadata=basic();metadata['ipoDate']='2020-01-01'
    (folder/'SZ.301999.json').write_text(json.dumps(dict(target_session='2026-10-13',code='SZ.301999',rows=[metadata],received_at='2026-10-13T11:00:00+00:00')))
    gate=dict(dependency_bindings=dict(identity=ref(tmp_path,p),unknown_codes=['SZ.301999'],missing_codes=[]),native_provider_facts=dict(status='NATIVE_PROVIDERS_RECONCILED'))
    daily,_=pair();freeze=dict(normalized=dict(daily=dict(rows=[daily])),native_baostock=dict(path='raw.json',sha256='a'*64),tdx=dict(path='native.json',sha256='b'*64))
    a=admitted_identity(tmp_path,'2026-10-13',gate,freeze);b=admitted_identity(tmp_path,'2026-10-13',gate,freeze)
    assert a==b
    result=load(checked(tmp_path,a));assert len(result['rows'])==1
    assert result['rows'][0]['code_status']=='NEW_CODE_UNLINKED'


@pytest.mark.parametrize('field,value',[('high','8'),('low','12'),('close','0'),('volume','-1')])
def test_two_sources_agreeing_on_invalid_bar_still_quarantined(field,value):
    daily,native=pair();daily[field]=value;native[field]=value
    result=classify_codes(set(),[daily],[native],'2026-10-13')
    assert result['valid_codes']==[]
    assert 'SELF_CONTRADICTORY_OHLCV' in result['invalid_codes'][0]['reasons']


def test_missing_metadata_runtime_manifest_does_not_block_real_observation(tmp_path):
    import json
    from pathlib import Path
    from workbench_analysis.operational_new_listing_r1 import admitted_identity
    from workbench_analysis.r43_owner_replay import ref,checked,load
    policy=Path(__file__).resolve().parents[1]/'config/v4_operational_new_listing_r1.json'
    (tmp_path/'config').mkdir();(tmp_path/'config/v4_operational_new_listing_r1.json').write_bytes(policy.read_bytes())
    p=tmp_path/'identity.json';p.write_text(json.dumps(dict(rows=[])))
    gate=dict(dependency_bindings=dict(identity=ref(tmp_path,p),unknown_codes=['SZ.301999'],missing_codes=[]),native_provider_facts=dict(status='NATIVE_PROVIDERS_RECONCILED'))
    daily,_=pair();freeze=dict(normalized=dict(daily=dict(rows=[daily])),native_baostock=dict(path='raw.json',sha256='a'*64),tdx=dict(path='native.json',sha256='b'*64))
    result=load(checked(tmp_path,admitted_identity(tmp_path,'2026-10-13',gate,freeze)))
    assert result['rows'][0]['metadata_status']=='METADATA_PENDING'
    assert result['metadata_errors']==[dict(code='SZ.301999',error_type='KeyError')]


def partial_fixture(tmp_path):
    import json
    from workbench_analysis.r43_owner_replay import ref
    good,good_native=pair('SZ.301998');bad,bad_native=pair();bad_native['close']=11
    native=tmp_path/'native.json';native.write_text(json.dumps(dict(source_sha256='c'*64,target_bars=[good_native,bad_native])))
    artifact=dict(target_session='2026-10-13',tdx=dict(ref(tmp_path,native),bytes=native.stat().st_size),normalized=dict(daily=dict(rows=[good,bad])),native_baostock=dict(path='raw.json',sha256='b'*64))
    freeze=tmp_path/'original_freeze.json';freeze.write_text(json.dumps(artifact))
    result=dict(source_freeze=ref(tmp_path,freeze))
    changes=classify_codes({'SZ.301998'},[good,bad],[good_native,bad_native],'2026-10-13')
    return artifact,result,changes,native,freeze

def test_partial_freeze_is_explicit_immutable_and_has_effective_denominator(tmp_path):
    from workbench_analysis.operational_new_listing_r1 import filtered_freeze
    from workbench_analysis.r43_owner_replay import checked,load
    artifact,result,changes,native,freeze=partial_fixture(tmp_path)
    before=(native.read_bytes(),freeze.read_bytes())
    view,receipt=filtered_freeze(tmp_path,'2026-10-13',artifact,result,changes)
    quality=view['source_quality']
    assert quality['status']=='PARTIAL_READY' and quality['full_identity_coverage'] is False
    assert quality['effective_universe_count']==1 and quality['valid_codes']==['SZ.301998']
    assert [r['code'] for r in view['normalized']['daily']['rows']]==['SZ.301998']
    assert [r['source_security_key'] for r in load(__import__('pathlib').Path(view['tdx']['path']))['target_bars']]==['SZ.301998']
    assert before==(native.read_bytes(),freeze.read_bytes())
    assert load(checked(tmp_path,receipt['source_freeze']))==view
    assert filtered_freeze(tmp_path,'2026-10-13',artifact,result,changes)[1]['source_freeze']==receipt['source_freeze']

def test_partial_gate_rechecks_remaining_sources_and_keeps_factor_failure(tmp_path):
    from workbench_analysis.operational_new_listing_r1 import gate_adapter
    artifact,result,changes,_,_=partial_fixture(tmp_path)
    calls=[]
    def original(root,day,view,receipt,now):
        calls.append(view)
        return receipt,dict(status='WAIT_BAOSTOCK_FACTOR',source_ready=False,reason='EMPTY_FACTOR_PROOF_REQUIRED',dependency_bindings=dict(code_changes=changes if not view.get('source_quality') else {}))
    receipt,gate=gate_adapter(original,tmp_path,'2026-10-13',artifact,result)
    assert len(calls)==2 and gate['source_ready'] is False
    assert gate['status']=='WAIT_BAOSTOCK_FACTOR' and gate['source_quality']['invalid_codes']

def test_partial_gate_keeps_valid_source_ready_with_explicit_quality(tmp_path):
    from workbench_analysis.operational_new_listing_r1 import gate_adapter
    artifact,result,changes,_,_=partial_fixture(tmp_path)
    def original(root,day,view,receipt,now):
        return receipt,dict(status='SOURCE_READY' if view.get('source_quality') else 'WAIT_BAOSTOCK_DAILY',source_ready=bool(view.get('source_quality')),dependency_bindings=dict(code_changes=changes if not view.get('source_quality') else {}))
    receipt,gate=gate_adapter(original,tmp_path,'2026-10-13',artifact,result)
    assert gate['source_ready'] is True and gate['identity_coverage']=='PARTIAL_READY'
    assert receipt['source_quality']['effective_universe_count']==1


def test_supported_chinext_302_prefix_matches_existing_stock_code_contract():
    row=observed_identity('SZ.302132','2026-10-13',[],set())
    assert row['board_scope']=='CHINEXT'

def test_index_cannot_pass_two_source_new_code_admission():
    daily,native=pair('SZ.399001')
    result=classify_codes(set(),[daily],[native],'2026-10-13')
    assert result['valid_codes']==[] and result['invalid_codes'][0]['reasons']==['UNSUPPORTED_A_SHARE']


def test_new_listing_request_budget_uses_configured_baostock_cache_when_no_legacy_ledger(tmp_path,monkeypatch):
    from workbench_analysis.operational_new_listing_r1 import request_ledger_path
    configured=tmp_path/'configured-cache'
    monkeypatch.setattr('common.paths.resolve_baostock_cache_root',lambda root:configured)
    assert request_ledger_path(tmp_path)==configured/'request_ledger.json'


def test_new_listing_request_budget_preserves_existing_ledger_without_copying(tmp_path,monkeypatch):
    from workbench_analysis.operational_new_listing_r1 import request_ledger_path
    configured=tmp_path/'configured-cache'
    monkeypatch.setattr('common.paths.resolve_baostock_cache_root',lambda root:configured)
    legacy=tmp_path/'reports/v4_baostock/request_ledger.json'
    legacy.parent.mkdir(parents=True);legacy.write_text('{"by_shanghai_date":{}}',encoding='utf-8')
    assert request_ledger_path(tmp_path)==legacy
    assert legacy.read_text(encoding='utf-8')=='{"by_shanghai_date":{}}'
    assert not (configured/'request_ledger.json').exists()


def test_new_listing_request_budget_refuses_two_ledgers(tmp_path,monkeypatch):
    from workbench_analysis.operational_new_listing_r1 import request_ledger_path
    import pytest
    configured=tmp_path/'configured-cache'
    monkeypatch.setattr('common.paths.resolve_baostock_cache_root',lambda root:configured)
    legacy=tmp_path/'reports/v4_baostock/request_ledger.json'
    legacy.parent.mkdir(parents=True);legacy.write_text('{}',encoding='utf-8')
    configured.mkdir();(configured/'request_ledger.json').write_text('{}',encoding='utf-8')
    with pytest.raises(ValueError,match='BAOSTOCK_REQUEST_LEDGER_MIGRATION_CONFLICT'):
        request_ledger_path(tmp_path)
