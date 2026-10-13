"""Publication-context negative controls; no numerical producer execution."""
from copy import deepcopy
import pytest
from workbench_service.native_current_snapshot_v3 import CONTRACT, validate_document
from workbench_analysis.operational_successor_v1 import digest
from workbench_service.native_current_snapshot_v3 import JOINT_CONTRACT,validate_joint_document,current


def sample():
    candidate=dict(accepted_trade_date='2026-10-12',published_sessions=['2026-10-09','2026-10-12'],owners={'2026-10-12':{'core':{'path':'core.json','sha256':'a'*64}}},native_pg_owner_authority={'path':'pg.json','sha256':'b'*64})
    document=dict(contract_id=CONTRACT,business_token=digest(candidate),T0='2026-10-12',published_sessions=candidate['published_sessions'],owners=candidate['owners'],native_content={'native_pg_owner_authority':candidate['native_pg_owner_authority']},PIT_ELIGIBLE=False,AS_RECORDED=False,historical_PIT_permission=False,trading=False,probability_claims=False)
    return candidate,deepcopy(document)


def test_matching_snapshot_has_one_business_context():
    candidate,document=sample()
    assert validate_document(document,candidate)['business_token']==digest(candidate)


@pytest.mark.parametrize('mutation,reason',[
    ({'T0':'2026-09-30'},'DATE_MISMATCH'),
    ({'business_token':'c'*64},'TOKEN_MISMATCH'),
    ({'published_sessions':['2026-10-12']},'SESSION_DENOMINATOR_MISMATCH'),
    ({'owners':{}},'OWNER_BINDING_MISMATCH'),
    ({'native_content':{}},'NATIVE_CONTENT_MISMATCH'),
    ({'PIT_ELIGIBLE':True},'SCOPE_ESCALATION'),
    ({'AS_RECORDED':True},'SCOPE_ESCALATION'),
    ({'trading':True},'SCOPE_ESCALATION'),
])
def test_no_individually_valid_but_mixed_authorities(mutation,reason):
    candidate,document=sample();document.update(mutation)
    with pytest.raises(ValueError,match=reason):validate_document(document,candidate)


def test_new_owner_bytes_invalidate_old_snapshot_token():
    candidate,document=sample();candidate=deepcopy(candidate)
    candidate['owners']['2026-10-12']['core']['sha256']='d'*64
    with pytest.raises(ValueError,match='TOKEN_MISMATCH'):validate_document(document,candidate)


@pytest.mark.parametrize('mutation,reason',[
    ({'T0':'2026-09-30'},'BUSINESS_CONTEXT_MISMATCH'),
    ({'business_token':'f'*64},'BUSINESS_CONTEXT_MISMATCH'),
    ({'operational_candidate':{'path':'another_head.json'}},'HEAD_SNAPSHOT_MISMATCH'),
    ({'ui_assets':{}},'UI_BINDINGS_REQUIRED'),
    ({'PIT_ELIGIBLE':True},'SCOPE_ESCALATION'),
    ({'trading':True},'SCOPE_ESCALATION'),
])
def test_current_joint_rejects_individually_readable_wrong_scope(mutation,reason):
    candidate,snapshot=sample();snapshot['candidate']={'path':'candidate.json','sha256':'1'*64}
    joint=dict(contract_id=JOINT_CONTRACT,T0=snapshot['T0'],business_token=snapshot['business_token'],operational_candidate=snapshot['candidate'],ui_assets={'app.js':{'path':'app.js','sha256':'2'*64}},PIT_ELIGIBLE=False,AS_RECORDED=False,trading=False,probability_claims=False)
    joint.update(mutation)
    with pytest.raises(ValueError,match=reason):validate_joint_document(joint,snapshot,candidate)


def test_historical_joint_cannot_satisfy_current_publication(tmp_path):
    import json
    (tmp_path/'config').mkdir()
    (tmp_path/'config/v4_joint_release_authority_v1.json').write_text(json.dumps({'trade_date':'2026-09-30','full_product_release':True}))
    candidate,_=sample()
    with pytest.raises(ValueError,match='NO_HISTORICAL_FALLBACK'):current(tmp_path,candidate)
