import importlib.util,json
from pathlib import Path
import pytest
from workbench_analysis.r43_release_control import verify_record,verify_user_authorization,CONTRACT,DOMAINS,USER_CONTRACT
from workbench_analysis.r43_operational_publication import digest
from workbench_analysis.scoped_successor_r421 import atomic,canonical,sha
ROOT=Path(__file__).resolve().parents[1]
def test_missing_identity_rejected_even_if_status_matches(tmp_path):
    candidate={};record=dict(status='EXTERNALLY_ACCEPTED_R43_OPERATIONAL',candidate_digest=digest(candidate),historical_PIT_permission=False,review_contract=CONTRACT)
    with pytest.raises(ValueError,match='INDEPENDENT_REVIEWER'):verify_record(tmp_path,candidate,record)
def test_wrong_digest_rejected(tmp_path):
    with pytest.raises(ValueError,match='SCOPE_MISMATCH'):verify_record(tmp_path,{},dict(status='EXTERNALLY_ACCEPTED_R43_OPERATIONAL',candidate_digest='0'*64,historical_PIT_permission=False))
def test_simulation_never_grants_project_permission():
    r=dict(status='EXTERNALLY_ACCEPTED_R43_OPERATIONAL',candidate_digest=digest({}),historical_PIT_permission=False,review_contract=CONTRACT,simulation_only=True)
    with pytest.raises(ValueError,match='SIMULATION_AUTHORITY_FORBIDDEN'):verify_record(ROOT,{},r)
def release_module():
    spec=importlib.util.spec_from_file_location('r43_cli',ROOT/'scripts/promote_r43_operational_v1.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
def test_rollback_preserves_exact_predecessor_bytes_and_refuses_newer(tmp_path):
    module=release_module();head=tmp_path/'head.json';before=b'{ "old": true }\n';atomic(head,b'new');published=sha(head)
    module.rollback_exact(head,before,published);assert head.read_bytes()==before
    atomic(head,b'newer')
    with pytest.raises(ValueError,match='NEWER_HEAD'):module.rollback_exact(head,before,published)
    assert head.read_bytes()==b'newer' and not head.with_suffix('.lock').exists()
def test_rollback_first_publication_restores_absence(tmp_path):
    module=release_module();head=tmp_path/'head.json';atomic(head,b'first');module.rollback_exact(head,None,sha(head));assert not head.exists()
def test_user_authority_requires_exact_request_and_cannot_claim_external(tmp_path):
    from workbench_analysis.r43_operational_sources import ref
    proof=tmp_path/'request.md';atomic(proof,b'Actual human request fixture; not a production authorization')
    r=dict(status='USER_AUTHORIZED_OPERATIONAL_CUTOVER',contract_id=USER_CONTRACT,candidate_digest=digest({}),historical_PIT_permission=False,independent_external_acceptance=False,request_origin='DIRECT_HUMAN_USER_MESSAGE',request_text='不需要等待什么批准生产准入 ,我现在要求你  进行生产数据切换',request_evidence=ref(tmp_path,proof),domain_disposition={k:('VALIDATION_ONGOING' if k=='rotation' else 'USER_AUTHORIZED') for k in DOMAINS})
    verify_user_authorization(tmp_path,{},r)
    with pytest.raises(ValueError,match='CANNOT_CLAIM_EXTERNAL'):verify_user_authorization(tmp_path,{},dict(r,independent_external_acceptance=True))
    with pytest.raises(ValueError,match='ACTUAL_USER_REQUEST'):verify_user_authorization(tmp_path,{},dict(r,request_origin='ATTACHED_DOCUMENT'))
    atomic(proof,b'mutated')
    with pytest.raises(ValueError,match='SOURCE_DIGEST_MISMATCH'):verify_user_authorization(tmp_path,{},r)
