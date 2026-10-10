from copy import deepcopy
import pytest
from workbench_analysis.fep_e5.admission import evaluate, inspect_isolated_candidate, current_gate
from pathlib import Path

AT='2026-10-09T12:00:00+00:00'
def fixture():
    request=dict(scope_id='S',target_id='T',horizon='T1',feature_contract_id='F',model_set_id='M',model_revision=1,capability='MODEL_DISPLAY')
    grant=dict(request,grant_id='G',formal_approval=True,active=True,valid_from='2026-10-09T00:00:00+00:00',expires_at='2026-10-10T00:00:00+00:00')
    model=dict(request,production_role='ACCEPTED_PRODUCTION',champion=True)
    head=dict(action='ALLOW',grant_id='G',activation_id='A',version=1)
    return request,dict(grant=grant,model=model,head=head,cas_receipt=deepcopy(head),external_approval_id='ISOLATED_APPROVAL',source=dict(input_mode='AS_RECORDED',digest='D',first_available_at='2026-10-09T00:00:00+00:00'),mature_count=1,prediction_owner='ISOLATED_OWNER',frozen_digest='D',original_frozen_digest='D')

CASES=[('forged_grant','cas_receipt','grant_id','FORGED','CAS_RECEIPT_MISMATCH'),('wrong_model_set','grant','model_set_id','OTHER','GRANT_BINDING_MISMATCH'),('wrong_revision','model','model_revision',2,'REGISTRY_BINDING_MISMATCH'),('expired','grant','expires_at','2026-10-08T00:00:00+00:00','GRANT_TIME_INVALID'),('revoked','grant','revoked',True,'GRANT_INACTIVE'),('non_as_recorded','source','input_mode','RECONSTRUCTED_CORRECTED','INPUT_ASOF_NOT_VERIFIED'),('future_source','source','first_available_at','2026-10-12T00:00:00+00:00','INPUT_ASOF_NOT_VERIFIED'),('no_mature',None,'mature_count',0,'SAMPLE_NOT_MATURE'),('missing_owner',None,'prediction_owner',None,'PREDICTION_OWNER_MISSING'),('shadow_escalation','grant','capability','SHADOW_INFERENCE','GRANT_BINDING_MISMATCH'),('same_id_frozen_mutation',None,'frozen_digest','CHANGED','FEP_FROZEN_PREDICTION_MUTATION'),('no_external_approval',None,'external_approval_id',None,'EXTERNAL_APPROVAL_MISSING'),('revoke_head','head','action','REVOKE','HEAD_NOT_ALLOWED')]
@pytest.mark.parametrize('name,parent,key,value,error',CASES)
def test_isolated_negative_matrix(name,parent,key,value,error):
    request,bundle=fixture();(bundle[parent] if parent else bundle)[key]=value
    result=inspect_isolated_candidate(bundle,request,at=AT)
    assert result['status']=='NOT_ELIGIBLE'
    assert any(e.startswith(error) for e in result['errors'])
    assert result['production_authorized'] is False

def test_complete_isolated_fixture_never_authorizes_production():
    request,bundle=fixture();result=inspect_isolated_candidate(bundle,request,at=AT)
    assert result['status']=='GATE_ELIGIBLE_CANDIDATE'
    assert result['errors']==[] and not result['production_authorized']

def test_legacy_all_true_counterexample_is_closed_and_fields_consistent():
    request,bundle=fixture()
    result=evaluate(bundle['model'],accepted=True,grant=bundle['grant'],request=request,input_asof=True,mature=True,scoring=True)
    assert result['gate_candidate_status']=='GATE_ELIGIBLE_CANDIDATE'
    assert not result['production_authorized'] and result['status']!='READY'
    assert all(f['value'] is None and f['status']=='SOURCE_INCOMPLETE' for f in result['fields'].values())

def test_actual_current_missing_authority_is_closed():
    result=current_gate(Path(__file__).resolve().parents[2])
    assert result['authority']['formal_owner'] is None
    assert not result['production_authorized'] and not result['prediction_generated']
