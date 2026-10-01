"""Actual registration/chain proofs plus independent rejection and dispatch probes."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import pytest
from workbench_analysis.source_authority_producers_r4 import (
    HEAD_PATH,REGISTRY_PATH,AUDIT_PATH,require_external_audit,require_accepted_producer,
    require_formal_source,OwnerAcceptanceError)
from workbench_analysis.source_authority_governance_r4 import evaluate_consumer_gate
from workbench_analysis.dm01_chain_contract_r3 import validate_parent
from workbench_analysis.dm01_incremental_component_builders_r3 import load,digest,ComponentBuildError,resolve_target_session
ROOT=Path(__file__).resolve().parents[2]
P='reports/audits/DM01_A01_R3_'

def read(p):return json.loads((ROOT/p).read_text(encoding='utf8'))
def fields():return [r for r in read('config/source_authority_governance_r4.json')['field_rules'] if r['field_id'] in ('TRADING_STATUS','ISST')]

def test_four_actual_authorities_bind_real_audit():
    registry=read(REGISTRY_PATH);head=read(HEAD_PATH)
    assert len(registry['owners'])==4
    assert head['registry']['path']==REGISTRY_PATH
    assert hashlib.sha256((ROOT/REGISTRY_PATH).read_bytes()).hexdigest()==head['registry']['sha256']
    for entry in registry['owners']:
        owner=load(entry['producer_contract'])
        assert owner['external_authority']==entry['external_authority']==registry['external_authority']
        require_external_audit(ROOT,owner['external_authority'])
        assert owner['AS_RECORDED'] is False and owner['first_available_at_target_proven'] is False

@pytest.mark.parametrize('target',['2026-09-28','2026-09-29','2026-09-30'])
@pytest.mark.parametrize('field',['TRADING_STATUS','ISST'])
def test_real_three_date_field_instance_readback(target,field):
    if target=='2026-09-29':binding=read(P+'20260929_SOURCE_CAPTURE_R1.json')['instances'][field]
    else:binding=read('reports/audits/A10_A12_R3_SOURCE_INSTANCE_MANIFEST_R1.json')['instances'][target][field]
    gate=evaluate_consumer_gate(next(r for r in fields() if r['field_id']==field),project_root=ROOT,
        consumer_contract_id='DM01_FINAL_ALL_NINE',target_trade_date=target,availability='AVAILABLE',required=True,
        source_instance_binding=binding)
    assert gate['formal_authority_authorized'] and gate['status']=='PASS_CORE_SCOPE'

@pytest.mark.parametrize('rule',fields())
def test_producer_acceptance_does_not_fill_missing_instance(rule):
    with pytest.raises(OwnerAcceptanceError,match='SOURCE_INSTANCE_MISSING_FOR_TARGET_DATE'):
        require_formal_source(ROOT,rule,consumer_contract_id='DM01_FINAL_ALL_NINE',target_trade_date='2026-09-29')

def test_task_card_or_replaced_audit_cannot_accept():
    authority=read(REGISTRY_PATH)['external_authority']
    for path in ['docs/evidence/source_authority/V4_A10_A12_R3_ACCEPTANCE_FORMALIZATION_AND_DM01_A01_R3_ENTRY_TASK_20261001.md',
                 'docs/evidence/source_authority/V4_A10_A12_R3_PRODUCER_SOURCE_INSTANCE_SCOPE_REPAIR_TASK_20261001.md']:
        bad=deepcopy(authority);data=(ROOT/path).read_bytes()
        bad['document']=dict(path=path,sha256=hashlib.sha256(data).hexdigest(),bytes=len(data))
        with pytest.raises(OwnerAcceptanceError,match='INVALID_EXTERNAL_AUTHORITY_BINDING'):require_external_audit(ROOT,bad)
    bad=deepcopy(authority);bad['document']['sha256']='0'*64
    with pytest.raises(OwnerAcceptanceError):require_external_audit(ROOT,bad)

def test_R2_cannot_be_selected_as_active_trust_root(tmp_path):
    head=read(HEAD_PATH);head['registry']=read('data/v4/V4_SOURCE_AUTHORITY_GOVERNANCE_HEAD_R2.json')['registry']
    p=tmp_path/HEAD_PATH;p.parent.mkdir(parents=True);p.write_text(json.dumps(head),encoding='utf8')
    with pytest.raises(OwnerAcceptanceError,match='REGISTRY_NOT_IN_GLOBAL_AUTHORITY_HEAD'):
        require_accepted_producer(tmp_path,fields()[0],consumer_contract_id='DM01_FINAL_ALL_NINE')

@pytest.mark.parametrize('mode',['AS_RECORDED_PIT_FACT','FIRST_AVAILABLE_AT_TARGET'])
def test_reconstructed_producer_never_accepts_other_knowledge_mode(mode):
    with pytest.raises(OwnerAcceptanceError,match='HISTORICAL_MODE_OUT_OF_SCOPE'):
        require_accepted_producer(ROOT,fields()[0],consumer_contract_id='DM01_FINAL_ALL_NINE',historical_mode=mode)

@pytest.mark.parametrize('consumer',['RAW_DAILY','ADJUSTED_DAILY','UNDECLARED_CONSUMER'])
def test_field_authority_cannot_escalate_to_OHLC_or_QFQ(consumer):
    with pytest.raises(OwnerAcceptanceError,match='CONSUMER_OUT_OF_SCOPE'):
        require_accepted_producer(ROOT,fields()[0],consumer_contract_id=consumer)

def test_actual_phase_A_pre_capture_missing_day_vector_retained():
    receipt=read('reports/audits/A10_A12_R3_REAL_DATE_GLOBAL_GATE_R2.json')
    assert receipt['validator_scope']=='ACTUAL_REPOSITORY_R4_R3_HEAD' and not receipt['fixture_used']
    missing=[v for v in receipt['vectors'] if v['target']=='2026-09-29']
    assert len(missing)==2 and all(v['owner_acceptance_reason']=='SOURCE_INSTANCE_MISSING_FOR_TARGET_DATE' for v in missing)
    assert all(v['source_revision'] for v in receipt['historical'])

def test_calendar_resolver_cannot_skip_middle_session():
    contract=read('config/dm01_incremental_builders_contract_r3.json');ctx=load(contract['execution_context'])
    dates=ctx['sessions']
    with pytest.raises(ComponentBuildError,match='BLOCKED_MISSING_INTERMEDIATE_SESSION'):
        resolve_target_session(ctx['parent']['head']['accepted_trade_date'],ctx['calendar'],ctx['observed_at'],dates[-1])

def test_actual_all_nine_chain_and_source_dates_exact():
    receipt=read(P+'CONTINUOUS_CHAIN_POSTCHECK_R1.json')
    assert receipt['status']=='PASS' and receipt['sessions']==['2026-09-28','2026-09-29','2026-09-30']
    parent=receipt['accepted_anchor']['sha256']
    for target,binding in zip(receipt['sessions'],receipt['candidates']):
        marker=load(binding)
        assert marker['target_trade_date']==target and marker['parent_data_head_digest']==parent
        assert len(marker['components'])==9 and marker['external_acceptance']=='PENDING'
        assert load(marker['cross_postcheck_binding'])['status']=='PASS'
        for cap,r in marker['components'].items():
            payload=load(dict(path=r['artifact_path'],sha256=r['artifact_sha256']))
            assert digest(payload['rows'])==r['logical_digest']
            assert payload['trade_date']==target and r['target_trade_date']==target
        for instance in marker['source_instance_digests'].values():
            assert load(instance)['provider_date']==target
        parent=binding['sha256']

def test_unmarked_partial_parent_rejected():
    contract=read('config/dm01_incremental_builders_contract_r3.json');ctx=load(contract['execution_context'])
    bad=deepcopy(ctx['parent']);bad['kind']='PARTIAL_COMPONENTS'
    with pytest.raises(ComponentBuildError,match='PARENT_KIND_NOT_AUTHORIZED'):validate_parent(bad,contract)

def test_actual_dispatcher_stops_on_first_incomplete_day(monkeypatch):
    from scripts import run_dm01_a01_r3_chain as runner
    calls=[];outputs=[]
    def fail(**args):
        calls.append(args['source_freeze']['trade_date'])
        return dict(status='BLOCKED',reason='LATE_COMPONENT_FAILED',completed_components=list(range(7)),data_head_moved=False)
    monkeypatch.setattr(runner,'build_candidate',fail)
    monkeypatch.setattr(runner,'report',lambda name,value:outputs.append((name,value)))
    with pytest.raises(ValueError,match='INCOMPLETE_DAY_STOPS_CHAIN'):runner.execute()
    assert calls==['2026-09-28'] and outputs[-1][1]['subsequent_sessions_stopped'] is True

def test_atomic_failure_determinism_and_heads_preserved():
    atomic=read(P+'ATOMIC_FAILURE_PROBES_R1.json');det=read(P+'DETERMINISM_R1.json')
    assert atomic['status']=='PASS' and not atomic['partial_candidates_visible']
    for binding in atomic['failure_bindings']:
        assert not (ROOT/binding['path']).parent.joinpath('PROMOTION_CANDIDATE.json').exists()
    assert det['status']=='PASS' and det['old_candidates_immutable']
    for binding in read(P+'STAGE_ENTRY_R1.json')['protected_bindings']:
        from workbench_analysis.dm01_accepted_chain_v1 import resolve_frozen_binding, HEAD_PATH, ANCHOR_SHA
        path=resolve_frozen_binding(ROOT,binding) if binding['path']==HEAD_PATH else ROOT/binding['path']
        actual=hashlib.sha256(path.read_bytes()).hexdigest()
        assert actual in (binding['sha256'],binding.get('git_sha256'))
    anchor=resolve_frozen_binding(ROOT,dict(path=HEAD_PATH,sha256=ANCHOR_SHA))
    assert json.loads(anchor.read_bytes())['accepted_trade_date']=='2026-09-24'
