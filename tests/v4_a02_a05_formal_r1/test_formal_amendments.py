from pathlib import Path
from copy import deepcopy
import json
import shutil
import pytest
ROOT=Path(__file__).resolve().parents[2]
from v4.rps_pit_history_a02_v1 import binding,immutable_json
from v4.a02_a05_external_acceptance_r1 import validate_authority,read_accepted_rps,accepted_legacy_observations,AUDIT_PATH,A05_RECORD,RPS_HEAD

def test_exact_actual_external_authority_pinned():
    ref=binding(ROOT,ROOT/AUDIT_PATH)
    assert validate_authority(ROOT,ref,'PASS_RECONSTRUCTED_INPUT_PRODUCER_SCOPE')==ROOT/AUDIT_PATH
    wrong={**ref,'path':'docs/evidence/next_round_r2/V4_A02_ACCEPTANCE_FORMALIZATION_AND_DOWNSTREAM_AMENDMENT_TASK_R1_20261001.md'}
    with pytest.raises(ValueError,match='AUTHORITY_PIN'):validate_authority(ROOT,wrong,'PASS_RECONSTRUCTED_INPUT_PRODUCER_SCOPE')
    wrong={**ref,'sha256':'0'*64}
    with pytest.raises(ValueError,match='AUTHORITY_PIN'):validate_authority(ROOT,wrong,'PASS_RECONSTRUCTED_INPUT_PRODUCER_SCOPE')

def test_accepted_scores_are_only_scoped_producer_acceptance():
    actual=read_accepted_rps(ROOT,'2026-09-30')
    assert actual['head']['AS_RECORDED'] is False and actual['head']['downstream_amendments_accepted'] is False
    assert len(actual['publication']['rows'])==5224
    assert actual['prior_publications'][1]['trade_date']=='2026-09-29'
    assert actual['prior_publications'][3]['trade_date']=='2026-09-24'
    with pytest.raises(ValueError,match='DATE_NOT_ACCEPTED'):read_accepted_rps(ROOT,'2026-09-25')

def test_formal_reader_does_not_recalculate_rps(monkeypatch):
    import v4.rps_pit_history_a02_v1 as producer
    monkeypatch.setattr(producer,'scores',lambda *a,**kw: (_ for _ in ()).throw(AssertionError('RUNTIME_RPS_RECALCULATION')))
    assert read_accepted_rps(ROOT,'2026-09-28')['deltas'][3][0]['fields']['rps5_delta3']['current_trade_date']=='2026-09-28'

def test_A05_current_snapshot_observation_scope_is_exact():
    observations=accepted_legacy_observations(ROOT,target='2026-09-24')
    assert len(observations)==6188 and all(x['quality']=='ACCEPTED' and x['accepted_source_scope']=='CURRENT_SNAPSHOT_ONLY' for x in observations.values())
    with pytest.raises(ValueError,match='TARGET_NOT_ACCEPTED'):accepted_legacy_observations(ROOT,target='2026-09-30')

def test_A02_counterfeit_record_publications_rejected_before_loading(tmp_path):
    paths=[AUDIT_PATH,RPS_HEAD]
    head=json.loads((ROOT/RPS_HEAD).read_bytes());record_path=head['acceptance_record']['path']
    for p in paths+[record_path]:
        dest=tmp_path/p;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/p,dest)
    record=json.loads((tmp_path/record_path).read_bytes());record['producer_evidence']['sha256']='0'*64
    (tmp_path/record_path).write_text(json.dumps(record),encoding='utf8')
    head['acceptance_record']=binding(tmp_path,tmp_path/record_path)
    (tmp_path/RPS_HEAD).write_text(json.dumps(head),encoding='utf8')
    with pytest.raises(ValueError,match='EVIDENCE_PIN'):read_accepted_rps(tmp_path,'2026-09-28')

def test_B2_rejects_historical_scope_or_stale_current_snapshot():
    from sector.a05_b2_scoped_amendment_r1 import evaluate_current_snapshot
    with pytest.raises(ValueError,match='SCOPE_REQUIRED'):
        evaluate_current_snapshot({}, {},source_sha256='',source_parameter_sha256='',parameter_set_sha256='',exact_snapshot_scope=dict(accepted_time_role='HISTORICAL_PIT',target='2026-09-24',accepted_snapshot_trade_date='2026-09-24'))
    with pytest.raises(ValueError,match='SCOPE_REQUIRED'):
        evaluate_current_snapshot({}, {},source_sha256='',source_parameter_sha256='',parameter_set_sha256='',exact_snapshot_scope=dict(accepted_time_role='CURRENT_SNAPSHOT_ONLY',target='2026-09-30',accepted_snapshot_trade_date='2026-09-24'))

def test_A02_full_independent_replay_and_prior_big_diff():
    from scripts.verify_a02_a05_formal_amendment_readback_r1 import verify_a02
    result=verify_a02()
    assert result['mismatches']==0 and result['changed_rows']==dict(V4_05=5222,V4_07=5222,V4_09=2811)

def test_A05_full_real_snapshot_independent_AST_readback():
    from scripts.verify_a02_a05_formal_amendment_readback_r1 import verify_a05
    result=verify_a05()
    assert result['real_B2_rows']==541 and result['independent_AST_mismatches']==0
    assert result['new_snapshot_states']==dict(FALSE=535,TRUE=2,UNKNOWN=4)
    assert result['same_date_9_30_adoption']=='REJECTED'

def test_old_head_and_rotation_context_immutable():
    result=json.loads((ROOT/'reports/audits/next_round_r2/V4_08_ACCEPTED_HEAD_B2_CAPABILITY_AMENDMENT_CANDIDATE_R3.json').read_bytes())
    ref=result['old_accepted_head'];assert binding(ROOT,ROOT/ref['path'])==ref
    proof=json.loads((ROOT/result['rotation_context_readback']['path']).read_bytes())
    assert proof['rotation_business_changed']==proof['context_business_changed']==0
    for ref in proof['accepted_artifacts'].values():assert binding(ROOT,ROOT/ref['path'])['sha256']==ref['sha256']
    assert result['old_head_replaced'] is False and result['production'] is False
