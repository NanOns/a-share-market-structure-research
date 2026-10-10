"""Real executor/ready-adapter call layers with synthetic kernel IO only."""
import json
import pytest
from test_cross_day_capture_repair_v1 import chain
from workbench_analysis import operational_daily_executor_v1 as executor
from workbench_analysis import operational_daily_ready_owner_v2 as adapter
from workbench_analysis import operational_daily_owner_v1 as owner
from workbench_analysis import operational_successor_release_v1 as release
from workbench_analysis import producer_bootstrap_v1 as bootstrap
from workbench_analysis.r43_owner_replay import ref
from workbench_analysis.v4_14_replay_io import publish
from workbench_analysis.operational_daily_storage_v1 import atomic_json
from scripts import audit_dynamic_daily_period_numbers_v1 as oracle


def test_capture_precedes_old_pool_gate_even_when_universe_not_ready(chain, monkeypatch):
    root, day, freeze, _, _ = chain
    calls = []
    def gate(root, day, artifact, result):
        assert result['first_capture_source_candidate']['candidate']
        calls.append('GATE')
        return result, dict(source_ready=False, status='WAIT_BAOSTOCK_DAILY', reason='NEW_IDENTITY_NEEDS_ADMISSION')
    monkeypatch.setattr(executor, 'verify_source_gate', gate)
    monkeypatch.setattr(adapter, 'build', lambda *a, **k: pytest.fail('OWNER_AFTER_FAILED_GATE'))
    result = executor.derive_ready_sources(root, day, dict(source_freeze=freeze))
    assert result['status']=='WAIT_BAOSTOCK_DAILY' and calls==['GATE']
    capture=result['first_capture_source_candidate']['candidate']
    assert json.loads((root/capture['path']).read_bytes())['capture_status']=='SOURCE_BYTES_CAPTURED'


@pytest.mark.parametrize('capture_failure', [False, True])
def test_executor_real_adapter_build_seal_and_strict_review_no_real_cas(chain,monkeypatch,capture_failure):
    root,day,freeze,new_head,_=chain
    head_binding=new_head()
    candidate=json.loads((root/head_binding['path']).read_bytes())
    old=(root/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json').read_bytes()
    candidate['predecessor']={'sha256':ref(root,root/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json')['sha256']}
    candidate_path=root/'inputs/sealed.json'
    atomic_json(root,candidate_path,candidate)
    gbbq=root/'inputs/gbbq';gbbq.write_bytes(b'SYNTHETIC_ONLY')
    dependencies={k:head_binding for k in ('parent_head','lifecycle','identity','membership_snapshot')}
    dependencies['gbbq']=dict(ref(root,gbbq),path=str(gbbq))
    readiness=publish(root,'inputs/ready.json',dict(source_ready=True,source_freeze=freeze,dependency_bindings=dependencies))
    folder=root/'kernel_fixture';(folder/'sources').mkdir(parents=True)
    (folder/'sources/gbbq').write_bytes(gbbq.read_bytes())
    receipt=publish(root,'inputs/day_receipt.json',dict(synthetic_only=True))
    candidate['day_receipt']=receipt
    atomic_json(root,candidate_path,candidate)
    context=dict(folder=folder,dates=[day],mappings={},snapshot=candidate['membership_snapshot'],seed_registry={},
                 freeze=freeze)
    calls=[]
    monkeypatch.setattr(executor,'verify_source_gate',lambda root,day,artifact,result:
        (dict(result,source_readiness=readiness),dict(source_ready=True)))
    def prepare(*a,**k):
        calls.append('OWNER_PREPARE')
        return context
    monkeypatch.setattr(owner,'prepare',prepare)
    monkeypatch.setattr(owner,'replay',lambda *a,**k:calls.append('KERNEL_REPLAY_FIXTURE'))
    monkeypatch.setattr(owner,'seal',lambda *a,**k:(candidate,ref(root,candidate_path)))
    def audit(*a,**k):
        atomic_json(root,folder/'PERIOD_NUMERIC_ORACLE.json',dict(synthetic_only=True))
        return dict(acceptance='PASS')
    monkeypatch.setattr(oracle,'audit',audit)
    monkeypatch.setattr(release,'promote',lambda *a,**k:pytest.fail('NO_REAL_CAS_ALLOWED'))
    # Sector numerical kernels are outside this focused capture-layer test.
    monkeypatch.setattr(bootstrap,'produce_daily_state',lambda *a,**k:head_binding)
    monkeypatch.setattr(bootstrap,'produce_daily_sector',lambda *a,**k:head_binding)
    if capture_failure:
        monkeypatch.setattr(bootstrap,'capture_daily_sources',lambda *a,**k:(_ for _ in ()).throw(OSError('SIDECAR_FAULT')))
    result=executor.derive_ready_sources(root,day,dict(source_freeze=freeze))
    assert calls==['OWNER_PREPARE','KERNEL_REPLAY_FIXTURE']
    assert result['status']=='QA_BLOCKED' and result['reason']=='LIVE_SERVICE_READBACK_ENDPOINT_REQUIRED'
    assert (root/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json').read_bytes()==old
    review=result['producer_review_candidates']['candidate']
    if capture_failure:
        assert review['strict_source']['reason']=='INITIAL_CAPTURE_FAILED'
    else:
        doc=json.loads((root/review['strict_source']['candidate']['path']).read_bytes())
        assert doc['scope_reconciliation']['status']=='SAME_DAY_SCOPE_RECONCILED'
    assert result['cohort_capture_readiness']['observed_count'] is None


def test_nested_native_transport_request_clock_is_preserved(chain):
    root,day,freeze,_,_=chain
    document=json.loads((root/freeze['path']).read_bytes())
    native=json.loads((root/document['native_baostock']['path']).read_bytes())
    requested=native.pop('requested_at')
    native['source_transport_v2']={'daily':{'requested_at':requested,'received_at':native['observed_at']}}
    document['native_baostock']=publish(root,'inputs/native_nested.json',native)
    freeze=publish(root,'inputs/freeze_nested.json',document)
    capture=bootstrap.capture_daily_sources(root,day,freeze)
    sources=json.loads((root/capture['path']).read_bytes())['sources']
    assert all(s['requested_at']==requested for s in sources if s['name'] in ('daily_freeze','native_baostock'))


def test_daily_authoritative_state_entry_freezes_without_grant(tmp_path,monkeypatch):
    from datetime import datetime
    from test_full_state_first_observed_v1 import inputs,DAY,NOW
    from workbench_analysis import full_state_first_observed_v1 as producer
    args=inputs(tmp_path)
    class Clock(datetime):
        @classmethod
        def now(cls,tz=None):return datetime.fromisoformat(NOW)
    monkeypatch.setattr(producer,'datetime',Clock)
    binding=publish(tmp_path,'inputs/day.json',dict(accepted_trade_date=DAY,
        first_observed_state_sources={DAY:dict(state=args['state_binding'],
            membership=args['membership_binding'],model=args['model_binding'])}))
    result=bootstrap.produce_first_observed_state(tmp_path,DAY,binding)
    assert result['status']=='ENGINEERING_CANDIDATE_CAPTURED'
    assert result['extraction']['eligible_count']==2 and result['extraction']['ineligible_count']==2
    assert result['formal_status']=='BLOCKED' and result['source_owner_admitted'] is False
    assert result['production_write_authorized'] is False and result['observed_count'] is None


def test_daily_state_missing_or_malformed_does_not_infer_research_eligibility(tmp_path):
    day='2026-10-12'
    missing=publish(tmp_path,'inputs/missing.json',dict(accepted_trade_date=day))
    result=bootstrap.produce_first_observed_state(tmp_path,day,missing)
    assert result['status']=='SOURCE_INCOMPLETE' and result['observed_count'] is None
    malformed=publish(tmp_path,'inputs/malformed.json',dict(accepted_trade_date=day,
        first_observed_state_sources={day:dict(state=missing)}))
    result=bootstrap.optional_step(bootstrap.produce_first_observed_state,tmp_path,day,malformed)
    assert result['main_flow_blocked'] is False and 'VERSIONED_INPUTS_REQUIRED' in result['reason']
