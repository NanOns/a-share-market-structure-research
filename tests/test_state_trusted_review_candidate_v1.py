import pytest
from workbench_analysis.state_trusted_review_candidate_v1 import review_candidate
from workbench_analysis.v4_14_replay_io import publish
from test_dated_identity_candidate_v1 import identity_fixture, rebuild, signed_review
import hashlib
import hmac
from workbench_analysis.v4_14_replay_io import canonical
from workbench_analysis.trusted_source_review_v1 import IsolatedReviewAuthority


@pytest.mark.parametrize('claim', [
    {'reviewer_role':'INDEPENDENT_REVIEWER','decision':'ACCEPT'},
    {'Writer_Grant':True,'STATE_SOURCE_ADMITTED':True},
    {'first_available':'2999-01-01T00:00:00Z'},
    {'revision':'OTHER_REVISION'},
    {'membership_date':'2026-10-09'},
    {'episode':None},
    {'universe':'FOCUS_TOP_K'},
    {'benchmark':'CALLER_DEFINED'},
    {'accepted_head':{'sha256':'0'*64}},
])
def test_workspace_claim_cannot_install_trusted_service(tmp_path,claim):
    binding=publish(tmp_path,'inputs/review.json',claim)
    result=review_candidate(tmp_path,review_binding=binding,**claim)
    assert result['status']=='NOT_ADMITTED'
    assert result['candidate_status']=='UNTRUSTED_REVIEW_CANDIDATE'
    assert not result['formal_cohort_enabled'] and not result['bridge_executed']
    assert not result['production_write_authorized'] and not result['STATE_SOURCE_ADMITTED']


@pytest.mark.parametrize('field,value', [
    ('issuer','OTHER'),('scope','FORMAL_COHORT'),('valid_until','2000-01-01T00:00:00Z'),
    ('revoked',True),('revocation_epoch',0),('revision','OTHER'),
    ('parent_head',{'path':'other','sha256':'0'*64}),('audience','PRODUCTION'),
])
def test_signed_transport_checks_independent_pin_and_exact_claims(identity_fixture,field,value):
    root,now,day,docs,sources,parent=identity_fixture
    candidate=rebuild(identity_fixture);authority,binding,claim=signed_review(identity_fixture,candidate)
    expected={k:claim[k] for k in ('scope','capability','revision','trade_date','parent_head','candidate','sources')}
    assert authority.verify(root,review_binding=binding,expected=expected,cutoff=now.isoformat())['status']=='ISOLATED_REVIEW_VERIFIED'
    altered=dict(claim,**{field:value})
    signature=hmac.new(b'EXPLICIT_SYNTHETIC_TEST_TRANSPORT_NOT_A_PRODUCTION_KEY',canonical(altered),hashlib.sha256).hexdigest()
    wrong=publish(root,'inputs/altered-review.json',dict(claims=altered,signature=signature))
    result=authority.verify(root,review_binding=wrong,expected=expected,cutoff=now.isoformat())
    assert result['status']=='NOT_ADMITTED' and not result['STATE_SOURCE_ADMITTED']


def test_revocation_and_issuer_signature_not_document_controlled(identity_fixture):
    root,now,day,docs,sources,parent=identity_fixture
    candidate=rebuild(identity_fixture);authority,binding,claim=signed_review(identity_fixture,candidate)
    expected={k:claim[k] for k in ('scope','capability','revision','trade_date','parent_head','candidate','sources')}
    revoked=IsolatedReviewAuthority(secret=b'EXPLICIT_SYNTHETIC_TEST_TRANSPORT_NOT_A_PRODUCTION_KEY',issuer=claim['issuer'],capabilities=[claim['capability']],revoked=['TEST-1'])
    assert revoked.verify(root,review_binding=binding,expected=expected,cutoff=now.isoformat())['status']=='NOT_ADMITTED'
    forged=publish(root,'inputs/forged-signature.json',dict(claims=claim,signature='0'*64))
    assert authority.verify(root,review_binding=forged,expected=expected,cutoff=now.isoformat())['status']=='NOT_ADMITTED'
