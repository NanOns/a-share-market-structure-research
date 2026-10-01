from copy import deepcopy
import json
from pathlib import Path
import pytest
from workbench_analysis.dm01_incremental_component_builders import (
    BUILDERS,BUILD_ORDER,ComponentBuildError,ROOT,digest,resolve_target_session,sha)
from workbench_analysis.dm01_candidate_orchestrator_r1 import build_candidate
from workbench_analysis.dm01_independent_postcheck_r1 import check_cross_components
from .a01_fixture_inputs import make_inputs,replace_input,rehash,save,TARGET,SID

HEADS=[ROOT/'data/v4'/p for p in ('V4_DATA_ACCEPTED_HEAD.json','V4_STAGE_ACCEPTED_HEAD.json','V4_DEV_BASELINE_HEAD.json')]

def run(env):
    return build_candidate(parent_data_head=env['parent'],source_freeze=env['freeze'],calendar_binding=env['calendar'],
        identity_binding=env['identity'],staging_root=env['staging'],head_paths=HEADS)

def components(env):
    r={}
    for cap in BUILD_ORDER:r[cap]=BUILDERS[cap](TARGET,env['parent'],env['freeze'],env['calendar'],env['identity'],env['staging'])
    return r

def test_nine_actual_adapters_independent_candidate_and_idempotence(tmp_path):
    env=make_inputs(tmp_path);before={str(p):sha(p) for p in HEADS};first=run(env)
    assert first['status']=='DM01_A01_INCREMENTAL_BUILDERS_CANDIDATE_READY_FOR_EXTERNAL_REAUDIT',first
    second=run(env);assert second['status']=='NOOP_IDENTICAL_CANDIDATE'
    assert second['candidate_sha256']==first['candidate_sha256']
    assert all(sha(Path(p))==v for p,v in before.items())
    assert first['postcheck']['adapter_used_as_oracle'] is False
    assert len(first['components'])==9

@pytest.mark.parametrize('case', ['wrong_parent','wrong_target','skip_session','raw_duplicate','raw_identity_mismatch',
    'raw_source_digest','calendar_mismatch','identity_publication','period_parent','period_parent_date','price_source','malformed_special',
    'special_lifecycle','freeze_tamper','missing_family'])
def test_atomic_fail_closed_negative_inputs(tmp_path,case):
    env=make_inputs(tmp_path)
    f=env['freeze']
    if case=='wrong_parent':f['parent_data_head_digest']='wrong';rehash(f)
    elif case=='wrong_target':f['trade_date']='2026-09-29';rehash(f)
    elif case=='skip_session':f['trade_date']='2026-09-30';rehash(f)
    elif case in ('raw_duplicate','raw_identity_mismatch','raw_source_digest'):
        delta=json.loads(Path(f['inputs']['TDX_PACKAGE_DELTA']['path']).read_text(encoding='utf8'))
        if case=='raw_duplicate':delta['target_bars'].append(deepcopy(delta['target_bars'][0]))
        elif case=='raw_identity_mismatch':delta['target_bars'][0]['security_id']='SZ.000002'
        else:delta['current_snapshot_id']='sha256-'+'b'*64
        replace_input(env,'TDX_PACKAGE_DELTA',delta)
    elif case=='calendar_mismatch':env['calendar']['session_dates'].append('2026-10-08')
    elif case=='identity_publication':env['identity']['publication_id']='wrong'
    elif case in ('period_parent','period_parent_date'):
        p=env['parent'];ref=p['components']['PERIOD_RAW'];v=json.loads(Path(ref['path']).read_text(encoding='utf8'))
        if case=='period_parent':p['components']['PERIOD_RAW']=dict(ref,sha256='bad')
        else:
            v['rows'][0]['as_of_date']='2026-09-23';new=save(tmp_path,'bad_parent_period.json',v);p['components']['PERIOD_RAW']=new
            p['component_manifest_binding']=save(tmp_path,'parent_components_changed.json',dict(parent_data_head_digest=p['binding']['sha256'],components=p['components']))
    elif case=='price_source':replace_input(env,'PRICE_RULES',dict(rules=[]))
    elif case in ('malformed_special','special_lifecycle'):
        value=json.loads(Path(f['inputs']['SPECIAL_PRICE_PHASE']['path']).read_text(encoding='utf8'))
        if case=='malformed_special':value['event_store']=dict(path=str(tmp_path/'missing-events'),sha256='bad')
        else:value['lifecycle_snapshot']['sha256']='bad'
        replace_input(env,'SPECIAL_PRICE_PHASE',value)
    elif case=='freeze_tamper':f['identity_publication_id']='tamper'
    elif case=='missing_family':del f['source_families']['GBBQ'];rehash(f)
    before={str(p):sha(p) for p in HEADS};result=run(env)
    assert result['status']=='BLOCKED',result
    assert all(sha(Path(p))==v for p,v in before.items())
    assert not list(env['staging'].rglob('PROMOTION_CANDIDATE.json'))

@pytest.mark.parametrize('provider_status,isst,present,expected',[('0','0',True,'ACTUAL_TRADED'),('0','1',False,'SUSPENDED'),
    ('1','0',False,'DATA_GAP'),('', '',False,'UNKNOWN'),('1','',True,'ACTUAL_TRADED')])
def test_status_ST_conflict_and_missing_semantics(tmp_path,provider_status,isst,present,expected):
    env=make_inputs(tmp_path);f=env['freeze'];bao=json.loads(Path(f['inputs']['BAOSTOCK_DAILY_UPDATE']['path']).read_text(encoding='utf8'))
    bao['daily_rows'][0].update(tradestatus=provider_status,isST=isst);replace_input(env,'BAOSTOCK_DAILY_UPDATE',bao)
    for cap in ('IDENTITY_UNIVERSE','RAW_DAILY'):
        BUILDERS[cap](TARGET,env['parent'],f,env['calendar'],env['identity'],env['staging'])
    if not present:
        from workbench_analysis.dm01_extracted_domain_r1 import classify_dated_status
        facts={(bao['daily_rows'][0]['code'],TARGET):(provider_status,isst)} if provider_status in ('0','1') and isst in ('0','1') else {}
        row,conflicts=classify_dated_status(dict(security_id=SID,source_security_key='SH.600001',trade_date=TARGET,source_bar_present=False),facts)
        row['status_conflict']=bool(conflicts)
    else:
        r=BUILDERS['TRADING_STATUS'](TARGET,env['parent'],f,env['calendar'],env['identity'],env['staging'])
        row=json.loads(Path(r['artifact_path']).read_text(encoding='utf8'))['rows'][0]
    assert row['status']==expected
    assert row['status_conflict']==(provider_status=='0' and present and isst in ('0','1'))
    r=BUILDERS['ISST'](TARGET,env['parent'],f,env['calendar'],env['identity'],env['staging'])
    st=json.loads(Path(r['artifact_path']).read_text(encoding='utf8'))['rows'][0]
    assert st['is_st']==(isst if isst in ('0','1') and provider_status in ('0','1') else None)

def test_unsupported_adjustment_per_security_fail_closed(tmp_path):
    env=make_inputs(tmp_path);v=json.loads(Path(env['freeze']['inputs']['GBBQ_DISPOSITIONS']['path']).read_text(encoding='utf8'))
    v['rows'][0]['blocking_categories']=[11];replace_input(env,'GBBQ_DISPOSITIONS',v)
    receipts=components(env);adjusted=json.loads(Path(receipts['ADJUSTED_DAILY']['artifact_path']).read_text(encoding='utf8'))['rows'][0]
    assert adjusted['adjustment_readiness']=='UNKNOWN'
    assert all(adjusted[p] is None for p in ('open','high','low','close'))
    assert receipts['ADJUSTED_DAILY']['status']=='DEGRADED_PASS'

def test_independent_postcheck_rejects_raw_adjusted_or_period_or_price_tamper(tmp_path):
    env=make_inputs(tmp_path);receipts=components(env)
    for cap,field,value in [('ADJUSTED_DAILY','close','99.00'),('PERIOD_RAW','volume',999999),('PRICE_LIMIT','limit_up_price','999.00'),
                            ('SPECIAL_PHASE','special_price_phase','RELISTING_FIRST_DAY')]:
        original=Path(receipts[cap]['artifact_path']).read_bytes();v=json.loads(original);v['rows'][-1][field]=value
        path=Path(receipts[cap]['artifact_path']);path.write_text(json.dumps(v),encoding='utf8')
        changed=deepcopy(receipts);changed[cap].update(artifact_sha256=sha(path),logical_digest=digest(v['rows']))
        assert check_cross_components(changed,env['freeze'],env['parent'],env['calendar'],env['identity'])['status']=='FAIL'
        path.write_bytes(original)

def test_source_revision_is_new_candidate_not_overwrite(tmp_path):
    env=make_inputs(tmp_path);first=run(env);assert first['status'].endswith('EXTERNAL_REAUDIT'),first
    bao=json.loads(Path(env['freeze']['inputs']['BAOSTOCK_DAILY_UPDATE']['path']).read_text(encoding='utf8'))
    bao['source_revision_note']='new audited capture revision';replace_input(env,'BAOSTOCK_DAILY_UPDATE',bao)
    second=run(env);assert second['status'].endswith('EXTERNAL_REAUDIT'),second
    assert second['candidate_path']!=first['candidate_path']
    assert sha(first['candidate_path'])==first['candidate_sha256']

def test_calendar_next_completed_and_missing_intermediate():
    cal=dict(session_dates=['2026-09-24','2026-09-28','2026-09-29','2026-09-30'])
    assert resolve_target_session('2026-09-24',cal,'2026-10-01T09:00:00+08:00')=='2026-09-28'
    with pytest.raises(ComponentBuildError,match='MISSING_INTERMEDIATE'):
        resolve_target_session('2026-09-24',cal,'2026-10-01T09:00:00+08:00','2026-09-30')
    with pytest.raises(ComponentBuildError,match='WAIT_MARKET_CLOSE'):
        resolve_target_session('2026-09-24',cal,'2026-09-28T14:59:00+08:00')

def test_configured_TDX_root_remains_completely_untouched_on_failure(tmp_path):
    env=make_inputs(tmp_path);root=tmp_path/'tdx-read-only';root.mkdir();sentinel=root/'input.dat';sentinel.write_bytes(b'unchanged')
    env['staging']=root/'candidates';before=list(root.rglob('*'));result=run(env)
    assert result['status']=='BLOCKED'
    assert list(root.rglob('*'))==before and sentinel.read_bytes()==b'unchanged'

def test_same_day_parent_is_frozen_and_candidate_digest_tamper_rejected(tmp_path):
    env=make_inputs(tmp_path);first=run(env);assert first['status'].endswith('EXTERNAL_REAUDIT')
    marker=Path(first['candidate_path']);v=json.loads(marker.read_text(encoding='utf8'));v['postcheck_digest']='forged';marker.write_text(json.dumps(v),encoding='utf8')
    result=run(env);assert result['status']=='BLOCKED' and result['reason']=='CANDIDATE_DIGEST_MISMATCH'
    assert result['protected_heads_unchanged']

def test_partial_components_invisible_until_final_marker(tmp_path):
    env=make_inputs(tmp_path)
    result=BUILDERS['IDENTITY_UNIVERSE'](TARGET,env['parent'],env['freeze'],env['calendar'],env['identity'],env['staging'])
    assert result['candidate_only'] and not list(env['staging'].rglob('PROMOTION_CANDIDATE.json'))
    assert not (ROOT/'data/v4/artifact_store/dm01_a01').exists()

def test_week_month_boundary_and_holiday_close_parent_periods(tmp_path):
    from .a01_fixture_inputs import advance_engineering_inputs_to_month_boundary
    env=make_inputs(tmp_path);advance_engineering_inputs_to_month_boundary(env)
    first=run(env);assert first['status'].endswith('EXTERNAL_REAUDIT'),first
    for cap in ('PERIOD_RAW','PERIOD_ADJUSTED'):
        rows=json.loads(Path(first['components'][cap]['artifact_path']).read_text(encoding='utf8'))['rows']
        old=[r for r in rows if r.get('as_of_date')=='2026-09-30']
        assert len(old)==2 and all(r['period_view']=='CLOSED_ONLY' for r in old)
        current=[r for r in rows if r.get('as_of_date')=='2026-10-08']
        from decimal import Decimal
        assert len(current)==2 and all(r['actual_count']==1 and r['volume']==1000 and Decimal(r['open'])==Decimal('10.1') for r in current)

def test_closed_parent_period_exactly_preserved(tmp_path):
    env=make_inputs(tmp_path);p=env['parent']
    for cap in ('PERIOD_RAW','PERIOD_ADJUSTED'):
        value=json.loads(Path(p['components'][cap]['path']).read_text(encoding='utf8'))
        closed=deepcopy(value['rows'][0]);closed.update(period_key='2026-W38',period_end_date='2026-09-18',period_view='CLOSED_ONLY',as_of_date='2026-09-18')
        value['rows'].append(closed);p['components'][cap]=save(tmp_path,cap+'_with_closed.json',value)
    p['component_manifest_binding']=save(tmp_path,'parent_closed_components.json',dict(parent_data_head_digest=p['binding']['sha256'],components=p['components']))
    result=run(env);assert result['status'].endswith('EXTERNAL_REAUDIT'),result
    assert result['postcheck']['component_checks']['PERIOD_RAW']['status']=='PASS'

def test_parent_roster_absence_remains_identity_unknown_not_delisting(tmp_path):
    from workbench_analysis.daily_source_manifests import build_current_lifecycle_snapshot
    env=make_inputs(tmp_path);records=env['identity']['records'];second=deepcopy(records[0]);second.update(source_security_key='SZ.000002',symbol='SZ.000002',security_id='DM01-ENGINEERING-INPUT-B',board='SZ_MAIN',board_scope='SZ_MAIN')
    records.append(second);ref=save(tmp_path,'two_identities.json',dict(records=records));env['identity'].update(binding=ref,publication_id=ref['sha256'])
    prior=json.loads(Path(env['parent']['components']['IDENTITY_UNIVERSE']['path']).read_text(encoding='utf8'))
    prior['rows'].append(dict(security_id=second['security_id'],source_security_key=second['source_security_key'],trade_date='2026-09-24'))
    p=env['parent'];p['components']['IDENTITY_UNIVERSE']=save(tmp_path,'prior_roster_with_absent.json',prior)
    p['component_manifest_binding']=save(tmp_path,'parent_absent_components.json',dict(parent_data_head_digest=p['binding']['sha256'],components=p['components']))
    f=env['freeze'];f['identity_publication_id']=ref['sha256'];rehash(f)
    r=BUILDERS['IDENTITY_UNIVERSE'](TARGET,p,f,env['calendar'],env['identity'],env['staging'])
    rows=json.loads(Path(r['artifact_path']).read_text(encoding='utf8'))['rows'];absent=next(r for r in rows if r['security_id']==second['security_id'])
    assert absent['unknown_reason']=='ROSTER_ABSENCE_IS_NOT_DELISTING' and absent['absence_is_delisting_evidence'] is False

def test_suspended_member_generates_no_synthetic_daily_and_null_no_actual_period(tmp_path):
    env=make_inputs(tmp_path);p=env['parent'];f=env['freeze'];records=env['identity']['records']
    second=deepcopy(records[0]);second.update(source_security_key='SZ.000002',symbol='SZ.000002',security_id='DM01-ENGINEERING-INPUT-B',board='SZ_MAIN',board_scope='SZ_MAIN')
    records.append(second);ref=save(tmp_path,'suspended_identity.json',dict(records=records));env['identity'].update(binding=ref,publication_id=ref['sha256'])
    prior=json.loads(Path(p['components']['IDENTITY_UNIVERSE']['path']).read_text(encoding='utf8'));prior['rows'].append(dict(security_id=second['security_id'],source_security_key=second['source_security_key'],trade_date='2026-09-24'))
    p['components']['IDENTITY_UNIVERSE']=save(tmp_path,'prior_suspended_identity.json',prior)
    p['component_manifest_binding']=save(tmp_path,'parent_suspended_components.json',dict(parent_data_head_digest=p['binding']['sha256'],components=p['components']))
    bao=json.loads(Path(f['inputs']['BAOSTOCK_DAILY_UPDATE']['path']).read_text(encoding='utf8'));bao['daily_rows'].append(dict(date=TARGET,code='sz.000002',tradestatus='0',isST='0'));replace_input(env,'BAOSTOCK_DAILY_UPDATE',bao)
    phase=json.loads(Path(f['inputs']['SPECIAL_PRICE_PHASE']['path']).read_text(encoding='utf8'));phase['active_security_ids'].append(second['security_id'])
    life=json.loads(Path(f['source_families']['IDENTITY_LIFECYCLE']['path']).read_text(encoding='utf8'));life['active_security_ids'].append(second['security_id'])
    life_ref=save(tmp_path,'suspended_lifecycle.json',life);phase['lifecycle_snapshot']=life_ref
    f['source_families']['IDENTITY_LIFECYCLE'].update(life_ref,source_revision=life_ref['sha256'])
    replace_input(env,'SPECIAL_PRICE_PHASE',phase)
    f['identity_publication_id']=ref['sha256'];rehash(f);result=run(env)
    assert result['status'].endswith('EXTERNAL_REAUDIT'),result
    raw=json.loads(Path(result['components']['RAW_DAILY']['artifact_path']).read_text(encoding='utf8'))['rows'];assert len(raw)==1
    rows=json.loads(Path(result['components']['PERIOD_RAW']['artifact_path']).read_text(encoding='utf8'))['rows']
    suspended=[r for r in rows if r['security_id']==second['security_id']]
    assert len(suspended)==2 and all(r['period_status']=='NO_ACTUAL_BARS' and r['suspended_count']==1 and r['open'] is None for r in suspended)

def test_new_listing_target_period_and_IPO_price_runtime(tmp_path):
    env=make_inputs(tmp_path);records=env['identity']['records'];records[0]['list_date']=TARGET
    ref=save(tmp_path,'listing_target_identity.json',dict(records=records));env['identity'].update(binding=ref,publication_id=ref['sha256'])
    env['freeze']['identity_publication_id']=ref['sha256'];rehash(env['freeze'])
    result=run(env);assert result['status'].endswith('EXTERNAL_REAUDIT'),result
    price=json.loads(Path(result['components']['PRICE_LIMIT']['artifact_path']).read_text(encoding='utf8'))['rows'][0]
    assert price['limit_status']=='NO_LIMIT' and price['special_price_phase']=='IPO_FIRST_5_TRADING_DAYS'
