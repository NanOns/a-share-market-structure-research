"""Real shared-gate call at the last derivation boundary; isolated source bytes."""
from datetime import datetime
from pathlib import Path
from hashlib import sha256
import pytest
from workbench_analysis import operational_daily_executor_v1 as executor
from workbench_analysis import operational_daily_ready_owner_v2 as adapter
from workbench_analysis import operational_successor_release_v1 as publication
from workbench_analysis.operational_daily_storage_v1 import atomic_json

@pytest.mark.parametrize('factor_proof,expected',[('missing','WAIT_BAOSTOCK_FACTOR'),('valid','QA_FAILURE')])
def test_missing_source_never_builds_and_ready_then_qa_failure_never_publishes(tmp_path,monkeypatch,factor_proof,expected):
    day='2026-10-09';observed=day+'T18:35:00+08:00'
    class Clock(datetime):
        @classmethod
        def now(cls,tz=None):return datetime.fromisoformat(day+'T19:00:00+08:00')
    monkeypatch.setattr(executor,'datetime',Clock)
    def write(name,value):
        p=tmp_path/name;atomic_json(tmp_path,p,value)
        return dict(path=name,sha256=sha256(p.read_bytes()).hexdigest())
    native=dict(source_security_key='SH.600000',trade_date=day,open=10,high=11,low=9,close=10,volume=1)
    daily=dict(code='SH.600000',date=day,tradestatus='1',open=10,high=11,low=9,close=10,volume=1)
    artifact=dict(native_baostock=write('raw.json',dict(target_date=day,observed_at=observed,adjustment_factor_rows=[],adjustment_factor_metadata=dict(error_code='0') if factor_proof=='valid' else {})),
        tdx=write('bars.json',dict(target_bars=[native])),observed_at=observed,effective_package=dict(provider_package_date=day),
        normalized=dict(daily=dict(rows=[daily]),adjustment_factor=dict(rows=[])))
    result=dict(source_freeze=write('freeze.json',artifact));calls=[]
    def build(*args,**kwargs):
        calls.append('BUILD');raise ValueError('ISOLATED_DOWNSTREAM_QA_FAILURE')
    monkeypatch.setattr(adapter,'build',build)
    monkeypatch.setattr(publication,'promote',lambda *a,**k:pytest.fail('CAS_AFTER_MISSING_SOURCE_OR_FAILED_QA'))
    stages=[]
    if expected=='QA_FAILURE':
        with pytest.raises(ValueError,match='DOWNSTREAM_QA_FAILURE'):
            executor.derive_ready_sources(tmp_path,day,result,progress=lambda d,s,r:stages.append(s))
        assert calls==['BUILD'] and stages==['DERIVING']
    else:
        receipt=executor.derive_ready_sources(tmp_path,day,result,progress=lambda d,s,r:stages.append(s))
        assert receipt['status']==expected and not receipt['source_ready']
        assert not calls and not stages


@pytest.mark.parametrize('mutation',['prelisting','delisted','unknown_identity','halt_valid','later_package_old_day'])
def test_accepted_pool_lifecycle_and_later_observation_fail_closed(tmp_path,monkeypatch,mutation):
    day='2026-10-08' if mutation=='later_package_old_day' else '2026-10-09'
    observed='2026-10-09T18:35:00+08:00'
    def write(name,value):
        p=tmp_path/name;atomic_json(tmp_path,p,value)
        return dict(path=name,sha256=sha256(p.read_bytes()).hexdigest())
    identities=[dict(security_id='SID1',source_security_key='SH.600000',board_scope='SH_MAIN',list_date='2000-01-01',delist_date=None)]
    if mutation=='prelisting':identities[0]['list_date']='2026-10-12'
    if mutation=='delisted':identities[0]['delist_date']=day
    if mutation=='unknown_identity':identities=[]
    native=dict(source_security_key='SH.600000',trade_date=day,open=10,high=11,low=9,close=10,volume=1)
    daily=dict(code='SH.600000',date=day,tradestatus='1',open=10,high=11,low=9,close=10,volume=1)
    native_rows=[native];daily_rows=[daily]
    if mutation=='halt_valid':
        identities.append(dict(identities[0],security_id='SID2',source_security_key='SH.600001'))
        daily_rows.append(dict(daily,code='SH.600001',tradestatus='0'))
    identity=write('identity.json',dict(rows=identities))
    life=write('lifecycle.json',dict(identity=identity));membership=write('membership.json',dict(evidence_kind='ISOLATED_INJECTION'))
    write('data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json',dict(accepted_trade_date='2026-10-08',owners={'2026-10-08':dict(lifecycle=life)},membership_snapshot=membership))
    action_file=tmp_path/'isolated_gbbq';action_file.write_bytes(b'ISOLATED_ACTION_DIGEST_ONLY')
    real_path=Path
    monkeypatch.setattr(executor,'Path',lambda value:action_file if str(value)=='D:/new_tdx/T0002/hq_cache/gbbq' else real_path(value))
    artifact=dict(native_baostock=write('raw.json',dict(target_date=day,observed_at=observed,adjustment_factor_rows=[],adjustment_factor_metadata=dict(error_code='0'))),
        tdx=write('bars.json',dict(target_bars=native_rows)),observed_at=observed,effective_package=dict(provider_package_date='2026-10-09',observed_at=observed),
        normalized=dict(daily=dict(rows=daily_rows),adjustment_factor=dict(rows=[])))
    result,ready=executor.verify_source_gate(tmp_path,day,artifact,dict(source_freeze=write('freeze.json',artifact)),datetime.fromisoformat('2026-10-09T19:00:00+08:00'))
    assert ready['source_ready']==(mutation in {'halt_valid','later_package_old_day'})
    assert ready['sources']['tdx']['provider_observed_at']==observed
    assert ready['PIT_ELIGIBLE'] is False and ready['AS_RECORDED'] is False
    if mutation=='halt_valid':
        assert ready['dependency_bindings']['accepted_pool_count']==2
        assert len(native_rows)==1,'SUSPENSION_MUST_NOT_CREATE_A_BAR'


def test_changed_source_bytes_cannot_reuse_previously_ready_gate(tmp_path,monkeypatch):
    day='2026-10-09';observed=day+'T18:35:00+08:00'
    def write(name,value):
        p=tmp_path/name;atomic_json(tmp_path,p,value)
        return dict(path=name,sha256=sha256(p.read_bytes()).hexdigest())
    native=dict(source_security_key='SH.600000',trade_date=day,open=10,high=11,low=9,close=10,volume=1)
    daily=dict(code='SH.600000',date=day,tradestatus='1',open=10,high=11,low=9,close=10,volume=1)
    artifact=dict(native_baostock=write('raw.json',dict(target_date=day,observed_at=observed,adjustment_factor_rows=[],adjustment_factor_metadata=dict(error_code='0'))),tdx=write('bars.json',dict(target_bars=[native])),observed_at=observed,effective_package=dict(provider_package_date=day),normalized=dict(daily=dict(rows=[daily]),adjustment_factor=dict(rows=[])))
    result,ready=executor.verify_source_gate(tmp_path,day,artifact,dict(source_freeze=write('freeze.json',artifact)),datetime.fromisoformat(day+'T19:00:00+08:00'))
    assert ready['source_ready']
    (tmp_path/'raw.json').write_text('{}',encoding='utf8')
    monkeypatch.setattr(adapter,'build',lambda *a,**k:pytest.fail('DERIVE_AFTER_SOURCE_DIGEST_CHANGE'))
    with pytest.raises(ValueError,match='NATIVE_RESPONSE_DIGEST_MISMATCH'):
        executor.derive_ready_sources(tmp_path,day,result)
