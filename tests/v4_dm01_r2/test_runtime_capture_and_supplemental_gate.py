import copy,hashlib,json
from pathlib import Path
import pytest
from workbench_analysis.baostock_dm01_capability_v2 import classify_capture_response,require_capability,digest
from workbench_analysis.baostock_dm01_sdk_schema_v2 import normalize_response
from workbench_analysis.baostock_daily_update_source import DAILY_METHOD,FACTOR_METHOD,DAILY_REQUIRED_FIELDS,FACTOR_REQUIRED_FIELDS
from workbench_analysis.dm01_source_boundary_r2 import source_freeze_complete_v2,require_external_a12_owner_for_final_candidate
ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'reports/dm01/a01_r2/20261001T033251758661Z/normalized_schema_v2_1'
def read(path):return json.loads(path.read_text(encoding='utf8'))
CAP=read(BASE/'runtime_capability_v2.json');CAPTURE=read(BASE/'TARGET_DATE_CAPTURE_normalized_receipt.json')
SDK=CAPTURE['sdk'];SCHEMA=read(ROOT/'config/baostock_dm01_sdk_schema_adapter_v2.json')
SOURCE=read(ROOT/'config/dm01_source_boundary_r2.json')

def test_smoke_and_target_nested_response_files_are_distinct_and_exact():
    smoke=read(ROOT/CAP['smoke_binding']['path'])
    for method in [DAILY_METHOD,FACTOR_METHOD]:
        a=smoke['responses'][method];b=CAPTURE['responses'][method]
        assert a['response_binding']['path']!=b['response_binding']['path']
        for r in [a,b]:
            path=ROOT/r['response_binding']['path']
            assert hashlib.sha256(path.read_bytes()).hexdigest()==r['response_binding']['sha256']
            assert digest(read(path)['rows'])==r['response_sha256']
        assert a['provider_date']=='2026-09-30' and b['provider_date']=='2026-09-28'

def test_runtime_smoke_date_a_supports_older_target_date_b():
    assert CAP['smoke_date']=='2026-09-30' and CAPTURE['target_trade_date']=='2026-09-28'
    assert require_capability(CAP,SDK,'2026-09-28')==CAPTURE['runtime_capability_id']

@pytest.mark.parametrize('method,required',[(DAILY_METHOD,DAILY_REQUIRED_FIELDS),(FACTOR_METHOD,FACTOR_REQUIRED_FIELDS)])
def test_real_target_capture_keeps_later_observation_and_exact_provider_date(method,required):
    response=CAPTURE['responses'][method]
    assert classify_capture_response(response,target='2026-09-28',required_fields=required)=='AVAILABLE'
    assert response['observed_at'].startswith('2026-10-01') and response['received_at'].startswith('2026-10-01')
    assert response['request_count']>0 and response['provider_date']=='2026-09-28'
    assert CAPTURE['origin']=='DELAYED_HISTORICAL_RETRIEVAL' and CAPTURE['first_availability_at_target_proven'] is False

@pytest.mark.parametrize('mode,expected',[('empty','PROVIDER_TARGET_DATE_EMPTY'),('failure','HISTORICAL_CATCHUP_QUERY_FAILED'),('schema','PROVIDER_SCHEMA_MISMATCH'),('date','PROVIDER_SCHEMA_MISMATCH')])
def test_actual_response_taxonomy(mode,expected):
    r=copy.deepcopy(CAPTURE['responses'][DAILY_METHOD])
    if mode=='empty':r['row_count']=0
    if mode=='failure':r['error_code']='1'
    if mode=='schema':r['fields']=[]
    if mode=='date':r['provider_date']='2026-09-30'
    assert classify_capture_response(r,target='2026-09-28',required_fields=DAILY_REQUIRED_FIELDS)==expected

@pytest.mark.parametrize('field,value',[('request_count',0),('observed_at','2026-09-27T00:00:00+00:00'),('received_at','2026-09-28T00:00:00'),('received_at','2026-10-01T00:00:00+00:00')])
def test_unqueried_or_backdated_capture_rejected(field,value):
    r=copy.deepcopy(CAPTURE['responses'][DAILY_METHOD]);r[field]=value
    with pytest.raises(ValueError):classify_capture_response(r,target='2026-09-28',required_fields=DAILY_REQUIRED_FIELDS)

def test_receipt_order_compares_instants_across_timezones():
    r=copy.deepcopy(CAPTURE['responses'][DAILY_METHOD]);r.update(observed_at='2026-10-01T03:00:00+00:00',received_at='2026-10-01T11:01:00+08:00')
    assert classify_capture_response(r,target='2026-09-28',required_fields=DAILY_REQUIRED_FIELDS)=='AVAILABLE'
    r['received_at']='2026-10-01T10:59:00+08:00'
    with pytest.raises(ValueError,match='BEFORE_OBSERVED'):classify_capture_response(r,target='2026-09-28',required_fields=DAILY_REQUIRED_FIELDS)

def test_only_declared_hash_pinned_factor_header_can_be_normalized():
    rawref=CAPTURE['responses'][FACTOR_METHOD]['raw_response_binding'];raw=read(ROOT/rawref['path'])
    rows,meta=normalize_response(raw['rows'],raw['provider_metadata'],target='2026-09-28',sdk=SDK,contract=SCHEMA,method=FACTOR_METHOD)
    assert len(rows)==16 and all('adjustFactor' in r and 'adjustFacto' not in r for r in rows)
    assert all('adjustFacto' in r for r in raw['rows'])
    wrong=copy.deepcopy(raw['provider_metadata']);wrong['fields'][-1]='arbitraryUnknown'
    with pytest.raises(ValueError):normalize_response(raw['rows'],wrong,target='2026-09-28',sdk=SDK,contract=SCHEMA,method=FACTOR_METHOD)
    with pytest.raises(ValueError):normalize_response(raw['rows'],raw['provider_metadata'],target='2026-09-28',sdk={**SDK,'installed_python_sources_sha256':'0'*64},contract=SCHEMA,method=FACTOR_METHOD)

def test_empty_factor_request_echo_does_not_prove_fact_date():
    raw=read(ROOT/CAPTURE['responses'][FACTOR_METHOD]['raw_response_binding']['path'])
    _,meta=normalize_response([],raw['provider_metadata'],target='2026-09-28',sdk=SDK,contract=SCHEMA,method=FACTOR_METHOD)
    assert meta['provider_date'] is None and meta['provider_date_basis']=='EMPTY_RESPONSE_TARGET_FACT_DATE_UNPROVEN'

@pytest.mark.parametrize('missing_factor',[True,False])
def test_supplemental_absence_preserves_required_core_preflight(tmp_path,missing_factor):
    path=tmp_path/'synthetic_accepted_source.json';path.write_bytes(b'fixture-only')
    binding=dict(path=path.name,sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    required={family:binding for family in SOURCE['required_source_families']}
    supplemental={} if missing_factor else {SOURCE['supplemental_source_families'][0]:binding}
    result=source_freeze_complete_v2(tmp_path,SOURCE,required,supplemental)
    assert result['core_source_gate']=='PASS' and result['canonical_adjustment_authority']=='GBBQ'
    assert result['supplemental'][SOURCE['supplemental_source_families'][1]]=='SUPPLEMENTAL_SOURCE_UNAVAILABLE'
    assert result['supplemental_can_overwrite_core'] is False

def test_missing_required_bytes_are_distinct_from_missing_provider(tmp_path):
    absent=dict(path='missing',sha256='0'*64);required={family:absent for family in SOURCE['required_source_families']}
    result=source_freeze_complete_v2(tmp_path,SOURCE,required,{})
    assert result['core_source_gate']=='BLOCKED' and set(result['required'].values())=={'CORE_REQUIRED_SOURCE_UNAVAILABLE'}

def test_final_candidate_cannot_self_accept_a12_engineering_contract():
    path=ROOT/'config/v4_02_status_st_authority_r1.json';binding=dict(path=path.relative_to(ROOT).as_posix(),sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    with pytest.raises(ValueError,match='A12_EXTERNAL_OWNER_ACCEPTANCE_REQUIRED'):
        require_external_a12_owner_for_final_candidate(ROOT,binding,read(ROOT/'data/v4/V4_STAGE_ACCEPTED_HEAD.json'))

def test_provider_revision_identity_changes_without_moving_data_head():
    fields={m:r['response_sha256'] for m,r in CAPTURE['responses'].items()};schema=CAPTURE['schema_adapter']['sha256']
    material=dict(target='2026-09-28',responses=fields,schema=schema)
    assert 'BS-CAPTURE-V2:'+digest(material)==CAPTURE['source_revision_id']
    revised=copy.deepcopy(material);revised['responses'][DAILY_METHOD]='f'*64
    assert digest(revised)!=digest(material)
    governed=read(ROOT/'config/source_authority_governance_r1.json')
    headbinding=next(b for b in governed['protected_bindings'] if b['path']=='data/v4/V4_DATA_ACCEPTED_HEAD.json')
    from workbench_analysis.dm01_accepted_chain_v1 import resolve_frozen_binding
    assert hashlib.sha256(resolve_frozen_binding(ROOT,headbinding).read_bytes()).hexdigest()==headbinding['sha256']
