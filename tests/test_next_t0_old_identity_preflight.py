"""Real readiness gate with synthetic bytes; production Heads stay unchanged."""
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
import pytest
from test_cross_day_capture_repair_v1 import chain
from workbench_analysis import operational_daily_executor_v1 as executor
from workbench_analysis.operational_daily_storage_v1 import atomic_json
from workbench_analysis.r43_owner_replay import ref
from workbench_analysis.v4_14_replay_io import publish


@pytest.mark.parametrize('added', [False, True])
def test_real_gate_preserves_bytes_and_explains_old_scope(chain, monkeypatch, added):
    root, day, freeze, new_head, _ = chain
    head_path=root/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json'
    old=json.loads(head_path.read_bytes())
    identity=publish(root,'inputs/prior_identity.json',dict(rows=[dict(
        security_id='OLD',source_security_key='SH.600001',board_scope='SH_MAIN',list_date='2000-01-01',delist_date=None)]))
    life=publish(root,'inputs/prior_lifecycle.json',dict(identity=identity,active_security_ids=['OLD']))
    old['owners'][old['accepted_trade_date']]['lifecycle']=life
    atomic_json(root,head_path,old)
    before=head_path.read_bytes()
    now=datetime.now(timezone.utc).isoformat()
    codes=['SH.600001']+(['SZ.000002'] if added else [])
    daily=[dict(code=c,date=day,tradestatus='1',open='1',high='1',low='1',close='1',volume='1') for c in codes]
    native=publish(root,'inputs/raw_gate.json',dict(target_date=day,observed_at=now,requested_at=now,
        daily_rows=daily,adjustment_factor_rows=[],adjustment_factor_metadata=dict(error_code='0')))
    bars=publish(root,'inputs/bars_gate.json',dict(target_bars=[dict(
        source_security_key=c,trade_date=day,open=1,high=1,low=1,close=1,volume=1) for c in codes]))
    artifact=dict(native_baostock=native,normalized=dict(daily=dict(rows=daily),adjustment_factor=dict(rows=[])),
        effective_package=dict(provider_package_date=day,observed_at=now),tdx=bars,observed_at=now)
    binding=publish(root,'inputs/freeze_gate.json',artifact)
    original=(root/native['path']).read_bytes()
    gbbq=root/'inputs/gbbq';gbbq.write_bytes(b'SYNTHETIC_ONLY')
    monkeypatch.setattr(executor,'Path',lambda p: gbbq if str(p)=='D:/new_tdx/T0002/hq_cache/gbbq' else Path(p))
    # Only the isolated readiness clock advances past the date gate, never system time.
    clock=datetime.fromisoformat(day+'T23:59:00+08:00')
    result, ready=executor.verify_source_gate(root,day,artifact,dict(source_freeze=binding),now=clock)
    report=ready['old_head_identity_preflight']
    assert report['native_tdx_baostock_reconciliation_passed']
    assert report['source_bytes_preserved'] and not report['identity_authority_candidate']['eligible_as_authority']
    assert report['added_observed_codes']==(['SZ.000002'] if added else [])
    assert ready['source_ready'] is (not added)
    if added:
        assert ready['status']=='WAIT_BAOSTOCK_DAILY'
        assert report['diagnosis']=='PREVIOUS_HEAD_IDENTITY_SCOPE_MISMATCH'
        assert report['provider_availability']=='NATIVE_BYTES_CAPTURED_RECONCILED'
    assert head_path.read_bytes()==before
    assert (root/native['path']).read_bytes()==original
    stored=json.loads((root/result['source_readiness']['path']).read_bytes())
    assert stored['old_head_identity_preflight']==report


def test_partial_tdx_bytes_survive_baostock_not_ready(chain, monkeypatch):
    from scripts import accept_dynamic_daily_baostock_v2 as runtime
    root,day,_,_,_=chain
    before=(root/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json').read_bytes()
    package_path=root/'inputs/partial_package.zip'
    package_path.write_bytes(b'SYNTHETIC_TDX_PACKAGE_ALREADY_FROZEN')
    package=dict(download=ref(root,package_path),provider_package_date=day,
                 observed_at=datetime.now(timezone.utc).isoformat())
    target=publish(root,'inputs/partial_target.json',dict(synthetic_only=True))
    bars=dict(status='TARGET_BARS_EXTRACTED',artifact=target,row_count=1)
    monkeypatch.setattr(executor,'source_readiness',lambda *a:dict(time_eligible=True))
    monkeypatch.setattr(executor,'capture_latest_tdx_package',lambda **k:package)
    monkeypatch.setattr(executor,'extract_target_session_bars',lambda *a,**k:bars)
    def unavailable(*a,**k):raise OSError('SYNTHETIC_RUNTIME_UNAVAILABLE')
    monkeypatch.setattr(executor,'load_runtime_acceptance_manifest',unavailable)
    monkeypatch.setattr(runtime,'accept_runtime',lambda *a:dict(status='WAIT_BAOSTOCK_DAILY'))
    result=executor.execute_sources(root,day,'EXECUTE')
    assert result['status']=='WAIT_BAOSTOCK_DAILY'
    assert ref(root,package_path)==package['download']
    assert ref(root,root/target['path'])==target
    assert (root/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json').read_bytes()==before
