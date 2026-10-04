"""R4R1 counterfactuals: synthetic inputs exercise semantics, never real evidence."""
from copy import deepcopy
import json
from pathlib import Path
import pytest
from workbench_analysis import dm01_runtime_r4 as r
from workbench_analysis import dm01_lineage_r4r1 as l
from tests.v4_dm01_r4.test_runtime import env as prior_env,build,promotion_fixture
from tests.v4_dm01.a01_fixture_inputs import save,rehash,replace_input

@pytest.fixture
def env(tmp_path):
    e=prior_env.__wrapped__(tmp_path)
    e['parent']['head'].update(knowledge_lineage='RECONSTRUCTED_CORRECTED',AS_RECORDED=False,first_available_at_target_proven=False)
    e['parent']['binding']=save(tmp_path,'fixture_v2_head.json',e['parent']['head'])
    e['parent']['binding']['path']=str(tmp_path/'fixture_v2_head.json')
    e['freeze']['parent_data_head_digest']=e['parent']['binding']['sha256'];rehash(e['freeze'])
    return e


def test_R4R1_01_parent_and_target_composition(env):
    observed=l.observation(env['freeze'],env['root'])
    observed.update(target_session_observation_proven=True,evidence_class='PIT_OBSERVED')
    # Pure projection counterfactual; no candidate or source acceptance is published.
    c=dict(parent=env['parent'],cap='PERIOD_RAW',freeze=dict(env['freeze'],engineering_simulation=False),target=env['freeze']['trade_date'])
    inherited=dict(trade_date='2026-09-24',as_of_date='2026-09-24',knowledge_lineage='RECONSTRUCTED_CORRECTED',AS_RECORDED=False)
    rows=[deepcopy(inherited),dict(trade_date='2026-09-28',as_of_date='2026-09-28',source_digest='parent-plus-target')]
    comp=l.annotate_rows(c,rows,observed)
    assert rows[0]==inherited
    assert rows[1]['knowledge_lineage']==l.MIXED and rows[1]['AS_RECORDED'] is False
    assert rows[1]['target_session_observation_proven'] is True
    assert comp['parent_head_lineage']=='RECONSTRUCTED_CORRECTED'
    assert comp['as_recorded_scope']=='TARGET_SESSION_OBSERVATION_ONLY'


def test_R4R1_02_false_forward_marker_cannot_promote(env,monkeypatch):
    marker=promotion_fixture(env,monkeypatch);marker['real_forward_evidence']=False
    binding=r.atomic(env['root'],env['root']/'false_forward.json',marker)
    before=(env['root']/r.HEAD).read_bytes()
    with pytest.raises(ValueError,match='REAL_FORWARD_EVIDENCE_REQUIRED'):
        r.promote(binding,expected_parent_sha=r.sha(env['root']/r.HEAD),root=env['root'])
    assert (env['root']/r.HEAD).read_bytes()==before


@pytest.mark.parametrize('vector,provider',[('R4R1-03','2026-09-28T08:00:00+00:00'),('R4R1-04',None)])
def test_no_first_availability_without_proof(env,vector,provider):
    for e in env['freeze']['availability_evidence'].values():e['source_provider_available_at']=provider
    rehash(env['freeze'])
    assert all(v['first_available_at_target_proven'] is False for v in l.first_availability(env['freeze'],env['root']).values())
    result=build(env);candidate=r.read(env['root'],result['candidate'])
    assert candidate['first_available_at_target_proven'] is False
    assert all(v['first_available_at_target_proven'] is False for v in candidate['components'].values())


def test_R4R1_05_simulation_cannot_claim_real_forward(env):
    result=build(env);candidate=r.read(env['root'],result['candidate']);candidate['real_forward_evidence']=True
    with pytest.raises(ValueError,match='SIMULATION_REAL_FORWARD_FORBIDDEN'):
        l.require_real_forward(candidate,env['freeze'],env['parent'],env['calendar'],env['root'])


def test_R4R1_06_before_close_rejected(env):
    env['freeze']['observed_at']='2026-09-28T06:59:00+00:00'
    for e in env['freeze']['availability_evidence'].values():
        e.update(captured_at='2026-09-28T06:00:00+00:00',received_at='2026-09-28T06:01:00+00:00',system_available_at='2026-09-28T06:01:00+00:00')
    rehash(env['freeze'])
    with pytest.raises(ValueError,match='BEFORE_ELIGIBLE_CLOSE'):l.observation(env['freeze'],env['root'])
    env['freeze']['observed_at']='2026-09-28T09:00:00+00:00';rehash(env['freeze'])
    with pytest.raises(ValueError,match='NATIVE_TARGET_OBSERVATION_BEFORE_ELIGIBLE_CLOSE'):l.observation(env['freeze'],env['root'])


def test_R4R1_07_synthetic_explicit_proof_remains_engineering(env):
    evidence=env['freeze']['availability_evidence']['BAOSTOCK_DAILY_UPDATE'];native=r.read(env['root'],evidence['binding'])
    native.update(source_provider_available_at='2026-09-28T08:00:00+00:00',query_operations=[dict(response_sha256=r.digest(native['daily_rows']))])
    proof=save(env['root'],'synthetic_first_availability.json',dict(contract_id='SOURCE_FIRST_AVAILABILITY_PROOF_V1',
        source_family='BAOSTOCK_DAILY_UPDATE',trade_date='2026-09-28',first_available_at=native['source_provider_available_at'],
        assertion='PROVIDER_FIRST_AVAILABILITY',source_content_digest=native['query_operations'][0]['response_sha256'],engineering_simulation=True))
    native['first_availability_proof']=proof;new=save(env['root'],'bao_proof_native.json',native)
    evidence.update(binding=new,first_availability_proof=proof,source_provider_available_at=native['source_provider_available_at']);rehash(env['freeze'])
    v=l.first_availability(env['freeze'],env['root'])['BAOSTOCK_DAILY_UPDATE']
    assert v['engineering_proof_checks_passed'] is True and v['first_available_at_target_proven'] is False
    result=build(env);candidate=r.read(env['root'],result['candidate'])
    assert candidate['real_forward_evidence'] is False
    observed=r.read(env['root'],candidate['target_session_observation_receipt'])
    assert observed['engineering_observation_checks_passed'] is True and observed['target_session_observation_proven'] is False


def test_R4R1_08_promoted_whole_head_keeps_mixed_lineage(env,monkeypatch):
    marker=promotion_fixture(env,monkeypatch);binding=r.atomic(env['root'],env['root']/'admitted_CAS_fixture.json',marker)
    result=r.promote(binding,expected_parent_sha=r.sha(env['root']/r.HEAD),root=env['root'])
    head=r.read(env['root'],result['data_head'])
    assert head['knowledge_lineage']==l.MIXED and head['AS_RECORDED'] is False
    assert head['first_available_at_target_proven'] is False
    assert head['target_session_source_manifest']==marker['source_manifest']
    assert result['r25_grant'] is False and result['real_shadow_observations_increment']==0


def test_R4R1_09_whole_head_overclaim_rejected(env):
    marker=r.read(env['root'],build(env)['candidate']);head=l.head_lineage(env['parent']['head'],marker,marker['target_session_observation_receipt'])
    head['AS_RECORDED']=True
    with pytest.raises(ValueError,match='WHOLE_HEAD_LINEAGE_OVERCLAIM'):l.validate_head_lineage(head,env['parent']['head'])
    marker.update(real_forward_evidence=True,engineering_simulation=False,knowledge_lineage=l.MIXED,AS_RECORDED=True)
    with pytest.raises(ValueError,match='WHOLE_CANDIDATE_LINEAGE_OVERCLAIM'):
        l.require_real_forward(marker,dict(env['freeze'],engineering_simulation=False),env['parent'],env['calendar'],env['root'])


def test_R4R1_10_whole_head_only_not_R25_authority(env):
    b=save(env['root'],'whole_head_only.json',dict(contract_id='V4_DATA_ACCEPTED_HEAD_V2',knowledge_lineage='PIT_OBSERVED'))
    with pytest.raises(ValueError,match='EXACT_TARGET_SESSION_BINDING_REQUIRED'):l.validate_r25_binding(env['root'],b)


def test_R4R1_11_exact_engineering_target_bridge_no_grant(env):
    result=build(env);candidate=r.read(env['root'],result['candidate']);parent=env['parent']['binding']
    child=dict(env['parent']['head'],**l.head_lineage(env['parent']['head'],candidate,candidate['target_session_observation_receipt']))
    child.update(final_candidate=result['candidate'],parent_archive=parent,parent_head_sha256=parent['sha256'])
    childref=save(env['root'],'bridge_child_fixture.json',child)
    bridge=dict(contract_id='DM01_R25_TARGET_SESSION_PIT_BINDING_R4R1_V1',parent_data_head=parent,child_data_head=childref,
        candidate=result['candidate'],target_trade_date=candidate['target_trade_date'],target_session_source_manifest=candidate['source_manifest'],
        target_session_all_nine_receipts=candidate['components'],target_session_observation_receipt=candidate['target_session_observation_receipt'])
    b=save(env['root'],'bridge.json',bridge);value=l.validate_r25_binding(env['root'],b,engineering=True)
    assert value==dict(status='PASS_ENGINEERING_CONTRACT_PATH',r25_grant=False,real_forward_evidence=False)
    bridge['target_trade_date']='2026-09-29';b=save(env['root'],'wrong_bridge.json',bridge)
    with pytest.raises(ValueError,match='TARGET_BINDING_MISMATCH'):l.validate_r25_binding(env['root'],b,engineering=True)


def test_R4R1_12_unknown_identity_rows_are_retained(env):
    env['identity']['records']=[];binding=save(env['root'],'unknown_identity.json',dict(records=[],fixture_scope='ENGINEERING_INPUT_ONLY'))
    env['identity'].update(binding=binding,publication_id=binding['sha256']);env['freeze']['identity_publication_id']=binding['sha256'];rehash(env['freeze'])
    life=save(env['root'],'unknown_lifecycle.json',dict(contract_id='CURRENT_LIFECYCLE_SNAPSHOT_V1',trade_date='2026-09-28',active_security_ids=[],fixture_scope='ENGINEERING_INPUT_ONLY'))
    env['freeze']['source_families']['IDENTITY_LIFECYCLE']=dict(life,source_revision=life['sha256'])
    phase=r.read(env['root'],env['freeze']['inputs']['SPECIAL_PRICE_PHASE']);phase.update(active_security_ids=[],lifecycle_snapshot=life)
    replace_input(env,'SPECIAL_PRICE_PHASE',phase)
    result=build(env);candidate=r.read(env['root'],result['candidate'])
    for cap in ['IDENTITY_UNIVERSE','RAW_DAILY','TRADING_STATUS','ISST']:
        payload=json.loads(Path(candidate['components'][cap]['artifact_path']).read_bytes())
        assert payload['rows'] and any(v.get('security_id') is None for v in payload['rows'])
        assert candidate['components'][cap]['target_identity_unknown_count']>0
    assert candidate['components']['IDENTITY_UNIVERSE']['status']=='DEGRADED_PASS'
