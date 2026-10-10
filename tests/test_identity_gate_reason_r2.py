"""Independent set/numeric oracle against actual verify_source_gate, not mocks."""
from datetime import datetime, timezone
import json
from pathlib import Path
import pytest
from test_cross_day_capture_repair_v1 import chain
from workbench_analysis import operational_daily_executor_v1 as executor
from workbench_analysis.source_readiness_v2 import source_readiness
from workbench_analysis.v4_14_replay_io import publish
from workbench_analysis.operational_daily_storage_v1 import atomic_json


@pytest.mark.parametrize('mode',['same','new','delist','rename','suspended','tdx_conflict','package_missing','member_version'])
def test_actual_provider_identity_classification(chain,monkeypatch,mode):
    exercise_provider_identity_classification(chain,monkeypatch,mode)


def exercise_provider_identity_classification(chain,monkeypatch,mode):
    root,day,_,_,_=chain
    head_path=root/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json'
    old=json.loads(head_path.read_bytes())
    prior=['SH.600001','SZ.000002']
    identity=publish(root,'inputs/full-prior-identity.json',dict(rows=[dict(
        source_security_key=key,security_id=key,board_scope='SH_MAIN' if key.startswith('SH') else 'SZ_MAIN',
        list_date='2000-01-01',delist_date=None) for key in prior]))
    life=publish(root,'inputs/full-prior-life.json',dict(identity=identity))
    old['owners'][old['accepted_trade_date']]['lifecycle']=life
    if mode=='member_version':old['membership_snapshot']=publish(root,'inputs/new-member-version.json',dict(version='changed',members=['OLD','NEW']))
    atomic_json(root,head_path,old);head_before=head_path.read_bytes()
    actual=prior+(['SZ.000003'] if mode=='new' else [])
    if mode=='delist':actual=['SH.600001']
    if mode=='rename':actual=['SH.600001','SZ.000004']
    now=datetime.now(timezone.utc).isoformat()
    daily=[dict(code=key,date=day,tradestatus='0' if mode=='suspended' and key=='SZ.000002' else '1',
        open='1',high='2',low='1',close='2',volume='10') for key in actual]
    native=[dict(source_security_key=row['code'],trade_date=day,open=1,high=2,low=1,close=2,volume=10)
        for row in daily if row['tradestatus']=='1']
    if mode=='tdx_conflict':native[0]['close']=99
    if mode=='package_missing':native=native[:-1]
    raw=publish(root,'inputs/original-provider.json',dict(target_date=day,observed_at=now,requested_at=now,
        daily_rows=daily,adjustment_factor_rows=[],adjustment_factor_metadata=dict(error_code='0')))
    tdx=publish(root,'inputs/original-target-bars.json',dict(target_bars=native))
    artifact=dict(native_baostock=raw,normalized=dict(daily=dict(rows=daily),adjustment_factor=dict(rows=[])),
        effective_package=dict(provider_package_date=day,observed_at=now),tdx=tdx,observed_at=now)
    frozen=publish(root,'inputs/source-freeze.json',artifact)
    originals={binding['path']:(root/binding['path']).read_bytes() for binding in (raw,tdx,frozen)}
    gbbq=root/'inputs/raw-gbbq';gbbq.write_bytes(b'SYNTHETIC_GBBQ_ORIGINAL')
    monkeypatch.setattr(executor,'Path',lambda path:gbbq if str(path)=='D:/new_tdx/T0002/hq_cache/gbbq' else Path(path))
    cutoff=datetime.fromisoformat(day+'T23:59:00+08:00')
    result,ready=executor.verify_source_gate(root,day,artifact,dict(source_freeze=frozen),now=cutoff)
    expected_provider=mode not in ('tdx_conflict','package_missing')
    expected_same=set(actual)==set(prior)
    assert ready['native_provider_facts']['status']==('NATIVE_PROVIDERS_RECONCILED' if expected_provider else 'NATIVE_PROVIDER_RECONCILIATION_FAILED')
    if expected_provider and not expected_same:
        assert ready['status']=='WAIT_DATED_IDENTITY_AUTHORITY' and not ready['source_ready']
        assert ready['sources']['baostock_daily']['status']=='VERIFIED'
    elif expected_provider:assert ready['source_ready']
    else:assert not ready['source_ready'] and ready['status']=='WAIT_BAOSTOCK_DAILY'
    # DailyJobs re-evaluates the exact saved evidence, retaining the identity gate.
    saved=json.loads((root/result['source_readiness']['path']).read_bytes())
    assert source_readiness(day,cutoff,saved['sources'])['status']==ready['status']
    assert ready['old_head_identity_preflight']['added_observed_codes']==sorted(set(actual)-set(prior))
    assert ready['old_head_identity_preflight']['missing_previous_codes']==sorted(set(prior)-set(actual))
    assert all((root/path).read_bytes()==raw for path,raw in originals.items())
    assert head_path.read_bytes()==head_before
    return dict(mode=mode, readiness=ready, bindings=result,
                independent_provider_expected=expected_provider,
                independent_scope_expected=expected_same, originals_unchanged=True,
                previous_head_unchanged=True)
