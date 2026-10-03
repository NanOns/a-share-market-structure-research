"""Contract-only checks and intrinsic negative gates; no replay implementation."""
from copy import deepcopy
from pathlib import Path
import json
import pytest
from jsonschema.exceptions import ValidationError
from scripts import validate_r17r1_refreeze as v
def test_full_contract_freeze_ready_for_external_audit_only():
    r=v.validate();assert r['V4_14_CONTRACT_COMPLETENESS']=='PASS_READY_FOR_EXTERNAL_AUDIT'
    assert r['V4_14_RUNTIME']=='NOT_IMPLEMENTED' and r['ALGORITHM_STATE_REPLAY_PASS']=='NOT_GRANTED' and r['runtime_executed'] is False
@pytest.mark.parametrize('dimension',v.REQUIRED)
def test_every_dimension_has_independent_positive_and_negative(dimension):
    b=v.load();rows={r['id']:r for r in b[v.NAMES[4]]['vectors']}
    assert rows[dimension+'_positive']['expected']['required_behavior']==v.LITERAL_BEHAVIOR[dimension]
    assert rows[dimension+'_negative']['expected']['verdict']=='REJECT_CONTRACT_VIOLATION'
def intrinsic_bundle(monkeypatch):
    b=deepcopy(v.load());original=v.exact
    def resolved(ref):
        name=Path(ref['path']).stem.removeprefix('v4_14_')
        if ref['path'].startswith('config/v4_14_') and name in b:
            # Isolate semantic gates from the separately tested exact-byte gate.
            return json.dumps(b[name],ensure_ascii=False).encode()
        return original(ref)
    monkeypatch.setattr(v,'exact',resolved);return b
@pytest.mark.parametrize('mutation',[
 'missing_dimension','missing_pair','wrong_expected','wrong_source_hash','missing_time_role','missing_history','unknown_false','runtime_true','replay_granted','production_true','missing_non_edge','feedback_edge','alias_feedback_edge','same_day_prior','different_previous_manifest','memory_prior','missing_process_exit','missing_readback_receipt','historical_current_membership','historical_missing_availability','real_implies_historical','old_revision_mutable','duplicate_episode','revision_in_logical_key','field_wrong_owner','duplicate_field','missing_source_binding','evidence_class_collapsed','contract_version_wrong'])
def test_intrinsic_negative_contract_gates(monkeypatch,mutation):
    b=intrinsic_bundle(monkeypatch);gate=b[v.NAMES[0]];cases=b[v.NAMES[1]];dag=b[v.NAMES[2]];q=b[v.NAMES[3]];book=b[v.NAMES[4]]
    if mutation=='missing_dimension':gate['required_dimensions'].pop()
    elif mutation=='missing_pair':book['vectors']=[r for r in book['vectors'] if r['id']!='expiry_positive']
    elif mutation=='wrong_expected':next(r for r in book['vectors'] if r['id']=='hysteresis_positive')['expected']['required_behavior']['downgrade_count']=2
    elif mutation=='wrong_source_hash':gate['source_bindings'][0]['sha256']='0'*64
    elif mutation=='missing_time_role':gate['time_role']=''
    elif mutation=='missing_history':gate['required_history']=''
    elif mutation=='unknown_false':q['failure_policy']['unknown_to_false']=True
    elif mutation=='runtime_true':gate['runtime_implemented']=True
    elif mutation=='replay_granted':gate['ALGORITHM_STATE_REPLAY_PASS']='PASS'
    elif mutation=='production_true':gate['production']=True
    elif mutation=='missing_non_edge':dag['forbidden_edges'].remove(['D3','A','T'])
    elif mutation in ['feedback_edge','alias_feedback_edge']:dag['replay_required_edges'].append(dict(producer='D3' if mutation=='feedback_edge' else 'PROFILE',consumer='A',field='bad',time_role='T'))
    elif mutation=='same_day_prior':dag['cross_day']['same_day_revisions']['no_r1_to_r2_prior']=False
    elif mutation=='different_previous_manifest':dag['cross_day']['same_day_revisions']['same_exact_previous_manifest']=False
    elif mutation=='memory_prior':dag['cross_day']['memory_prior_is_proof']=True
    elif mutation=='missing_process_exit':dag['cross_day']['required_sequence'].remove('PRODUCER_PROCESS_EXIT')
    elif mutation=='missing_readback_receipt':dag['cross_day']['must_record'].remove('readback_sha256')
    elif mutation=='historical_current_membership':q['evidence_classes']['HISTORICAL_PIT_EFFECTIVENESS']['current_membership_backfill_allowed']=True
    elif mutation=='historical_missing_availability':q['evidence_classes']['HISTORICAL_PIT_EFFECTIVENESS']['required'].remove('availability_cutoff')
    elif mutation=='real_implies_historical':q['evidence_classes']['REAL_ACCEPTED_SOURCE_CAPABILITY_SCOPED']['historical_effectiveness_implied']=True
    elif mutation=='old_revision_mutable':gate['identity_rules']['old_revisions']='OVERWRITE'
    elif mutation=='duplicate_episode':gate['identity_rules']['episode_continuation']='NEW_ID_EVERY_DAY'
    elif mutation=='revision_in_logical_key':gate['identity_rules']['event_logical_key'].append('revision')
    elif mutation=='field_wrong_owner':gate['field_registry'][0]['source_binding']['sha256']='0'*64
    elif mutation=='duplicate_field':gate['field_registry'].append(deepcopy(gate['field_registry'][0]))
    elif mutation=='missing_source_binding':gate.pop('source_bindings')
    elif mutation=='evidence_class_collapsed':q['evidence_classes'].pop('ENGINEERING_SYNTHETIC')
    elif mutation=='contract_version_wrong':gate['version']='2.0.0'
    with pytest.raises((AssertionError,KeyError,ValueError,ValidationError)):v.validate_bundle(b)
def test_source_byte_gate_rejects_self_consistent_wrong_reference():
    ref=deepcopy(v.load()[v.NAMES[0]]['source_bindings'][0]);ref['sha256']='0'*64
    with pytest.raises(AssertionError):v.exact(ref)
def test_no_future_replay_runtime_or_accepted_head():
    assert not (v.ROOT/'data/v4/V4_14_ACCEPTED_HEAD.json').exists()
    if (v.ROOT/'src/workbench_analysis/v4_14_replay_runtime.py').exists():
        assert 'AUTHORIZED_NEXT_SCOPED_ENGINEERING' in (v.ROOT/'docs/evidence/r18/V4_R17R1_INDEPENDENT_EXTERNAL_AUDIT_R1_20261003.md').read_text(encoding='utf8')
