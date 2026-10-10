"""Real functions, synthetic originals. No production admission or Head write."""
from datetime import datetime, timezone, timedelta
import hashlib
import hmac
import json
import pytest
from workbench_analysis.dated_identity_candidate_v1 import build, admission_candidate
from workbench_analysis.trusted_source_review_v1 import IsolatedReviewAuthority
from workbench_analysis.v4_14_replay_io import publish, ref, canonical


@pytest.fixture
def identity_fixture(tmp_path):
    now=datetime.now(timezone.utc);day=now.astimezone(timezone(timedelta(hours=8))).date().isoformat()
    prior=(datetime.fromisoformat(day)-timedelta(days=1)).date().isoformat()
    clk=(now-timedelta(seconds=2)).isoformat()
    base=dict(T0=day,revision='r1',requested_at=clk,received_at=clk,first_available=clk,
        evidence_class='SYNTHETIC_ISOLATED_TEST_ONLY')
    parent=publish(tmp_path,'docs/evidence/fixture/head.json',dict(accepted_trade_date=prior,
        identity_codes=['SH.600001'],evidence_class='SYNTHETIC_ISOLATED_TEST_ONLY'))
    original=publish(tmp_path,'inputs/official_identity_facts.json',dict(records=[dict(
        source_security_key='SH.600001',security_id='OLD',list_date='2000-01-01',delist_date=None,
        effective_from='2000-01-01',event_basis='OFFICIAL_DATED_IDENTITY',name='old')]))
    fact=json.loads((tmp_path/original['path']).read_bytes())['records'][0]
    bar=dict(source_security_key='SH.600001',trade_date=day,tradestatus='1',open=1,high=2,low=1,close=2,volume=10)
    member=publish(tmp_path,'inputs/members.json',dict(base,membership_basis='AS_RECORDED',
        membership_version='M1',member_ids=['OLD']))
    raw=publish(tmp_path,'inputs/gbbq_raw.json',dict(synthetic_raw_bytes='original'))
    docs=dict(roster=dict(base,rows=[bar],membership=member),tdx=dict(base,rows=[bar]),
        gbbq=dict(base,raw_binding=raw),identity_events=dict(base,records=[dict(fact,source_binding=original)]),
        membership=json.loads((tmp_path/member['path']).read_bytes()))
    sources={key:publish(tmp_path,'inputs/'+key+'.json',doc) if key!='membership' else member for key,doc in docs.items()}
    return tmp_path,now,day,docs,sources,parent


def rebuild(fixture,changed=None):
    root,now,day,docs,sources,parent=fixture
    if changed:
        sources=dict(sources)
        for key,doc in changed.items():sources[key]=publish(root,'inputs/changed-'+key+'.json',doc)
    return build(root,sources=sources,parent_head=parent,candidate_directory='docs/evidence/candidates',
        cutoff=now.isoformat(),clock=lambda:now)


def add_identity(fixture,*,removed=False,rename=False):
    root,now,day,docs,sources,parent=fixture
    event=dict(source_security_key='SZ.000002',security_id='OLD' if rename else 'NEW',list_date=day,
        effective_from=day,event_basis='OFFICIAL_DATED_IDENTITY',name='new',delist_date=None)
    old=docs['identity_events']['records'][0].copy();old.pop('source_binding')
    if rename:
        old['code_change']=dict(**{'from':'SH.600001','to':'SZ.000002'},effective_date=day)
        event['code_change']=old['code_change']
    if removed:old['delist_date']=day
    original=publish(root,'inputs/changed-official-facts.json',dict(records=[old,event]))
    events=dict(docs['identity_events'],records=[dict(r,source_binding=original) for r in (old,event)])
    bar=dict(docs['roster']['rows'][0],source_security_key='SZ.000002')
    bars=([docs['roster']['rows'][0]] if not (removed or rename) else [])+[bar]
    return dict(roster=dict(docs['roster'],rows=bars),tdx=dict(docs['tdx'],rows=bars),identity_events=events)


@pytest.mark.parametrize('mode',['same','new','delist','rename','suspended'])
def test_actual_candidate_functions_cross_day_identity(identity_fixture,mode):
    root,now,day,docs,sources,parent=identity_fixture
    changed=None
    if mode in ('new','delist','rename'):changed=add_identity(identity_fixture,removed=mode=='delist',rename=mode=='rename')
    if mode=='suspended':changed=dict(roster=dict(docs['roster'],rows=[dict(docs['roster']['rows'][0],tradestatus='0')]),tdx=dict(docs['tdx'],rows=[]))
    binding=rebuild(identity_fixture,changed)
    candidate=json.loads((root/binding['path']).read_bytes())
    assert candidate['status']=='IDENTITY_AUTHORITY_CANDIDATE_COMPLETE'
    assert candidate['provider_fact']=='NATIVE_PROVIDERS_RECONCILED'
    assert candidate['identity_authority_admitted'] is False
    assert admission_candidate(root,candidate_binding=binding)['status']=='NOT_ADMITTED'
    if mode=='rename':assert candidate['rows'][0]['code_boundary_proven']
    if mode=='delist':assert candidate['rows'][0]['delisting_proven']
    if mode=='suspended':assert candidate['rows'][0]['suspended']
    assert rebuild(identity_fixture,changed)==binding


@pytest.mark.parametrize('mode',['unknown_new','tdx_conflict','package_missing','missing_member_clock','absent_not_delisted'])
def test_identity_gaps_preserve_originals(identity_fixture,mode):
    root,now,day,docs,sources,parent=identity_fixture
    before={k:(root/v['path']).read_bytes() for k,v in sources.items()}
    if mode=='unknown_new':
        changed=add_identity(identity_fixture)
        changed['identity_events']=docs['identity_events']
    elif mode=='tdx_conflict':changed=dict(tdx=dict(docs['tdx'],rows=[dict(docs['tdx']['rows'][0],close=99)]))
    elif mode=='package_missing':changed=dict(tdx=dict(docs['tdx'],rows=[]))
    elif mode=='absent_not_delisted':
        changed=add_identity(identity_fixture)
        changed['roster']['rows']=changed['roster']['rows'][1:]
        changed['tdx']['rows']=changed['tdx']['rows'][1:]
    else:
        member=dict(docs['membership'],first_available=None)
        mb=publish(root,'inputs/member-without-clock.json',member)
        changed=dict(membership=member,roster=dict(docs['roster'],membership=mb))
        # The helper's exact changed member path must match the capture pointer.
        changed['roster']['membership']=publish(root,'inputs/changed-membership.json',member)
    binding=rebuild(identity_fixture,changed)
    candidate=json.loads((root/binding['path']).read_bytes())
    assert candidate['status']=='SOURCE_GAPS' and candidate['source_gaps']
    assert candidate['identity_authority_admitted'] is False
    assert all((root/sources[k]['path']).read_bytes()==raw for k,raw in before.items())
    if mode=='missing_member_clock':assert candidate['first_available'] is None


def test_changed_member_revision_wrong_day_backfill_and_wrong_sha(identity_fixture):
    root,now,day,docs,sources,parent=identity_fixture
    with pytest.raises(ValueError,match='MEMBER_REVISION'):
        rebuild(identity_fixture,dict(membership=dict(docs['membership'],revision='r2')))
    with pytest.raises(ValueError,match='SOURCE_REVISION'):
        rebuild(identity_fixture,dict(tdx=dict(docs['tdx'],T0='2026-09-24')))
    for cutoff in ('2026-09-24T18:35:00+08:00','2999-01-01T18:35:00+08:00'):
        with pytest.raises(ValueError,match='NO_BACKFILL'):
            build(root,sources=sources,parent_head=parent,candidate_directory='docs/evidence/c',cutoff=cutoff,clock=lambda:now)
    with pytest.raises(ValueError,match='REF_MISMATCH'):
        build(root,sources=dict(sources,roster=dict(sources['roster'],sha256='0'*64)),parent_head=parent,
            candidate_directory='docs/evidence/c',cutoff=now.isoformat(),clock=lambda:now)


def signed_review(fixture,binding):
    root,now,day,docs,sources,parent=fixture
    claim=dict(issuer='SYNTHETIC_EXTERNAL_TEST_SIGNER',capability='DATED_IDENTITY_SOURCE_REVIEW',
        audience='ISOLATED_SOURCE_ADMISSION_TEST_ONLY',review_id='TEST-1',revocation_epoch=1,revoked=False,
        valid_from=(now-timedelta(seconds=5)).isoformat(),valid_until=(now+timedelta(seconds=60)).isoformat(),
        trade_date=day,revision='r1',candidate=binding,parent_head=parent,sources=sources,
        scope='MAIN_DD_DATED_IDENTITY_CANDIDATE',evidence_class='SYNTHETIC_ISOLATED_TEST_ONLY')
    secret=b'EXPLICIT_SYNTHETIC_TEST_TRANSPORT_NOT_A_PRODUCTION_KEY'
    signature=hmac.new(secret,canonical(claim),hashlib.sha256).hexdigest()
    review=publish(root,'inputs/signed-review.json',dict(claims=claim,signature=signature))
    authority=IsolatedReviewAuthority(secret=secret,issuer=claim['issuer'],capabilities=[claim['capability']])
    return authority,review,claim


def test_independent_isolated_cas_retry_and_rollback(identity_fixture):
    root,now,day,docs,sources,parent=identity_fixture
    binding=rebuild(identity_fixture);authority,review,claim=signed_review(identity_fixture,binding)
    original=(root/parent['path']).read_bytes()
    def fail_readback(owner):return dict(head_sha256='0'*64)
    kwargs=dict(candidate_binding=binding,review_binding=review,head_path=parent['path'],cutoff=now.isoformat())
    with pytest.raises(ValueError,match='READBACK_FAILED'):authority.publish_identity(root,**kwargs,readback=fail_readback)
    assert (root/parent['path']).read_bytes()==original
    result=authority.publish_identity(root,**kwargs,readback=lambda _:dict(head_sha256=ref(root,parent['path'])['sha256']))
    assert result['status']=='ISOLATED_IDENTITY_OWNER_PUBLISHED' and result['production_write_authorized'] is False
    assert authority.publish_identity(root,**kwargs,readback=lambda _: {})['status']=='ISOLATED_IDENTITY_OWNER_ALREADY_PUBLISHED'


def test_wrong_cas_and_plain_caller_review_cannot_publish(identity_fixture):
    root,now,day,docs,sources,parent=identity_fixture
    binding=rebuild(identity_fixture);authority,review,claim=signed_review(identity_fixture,binding)
    fake=publish(root,'inputs/local-caller-review.json',dict(reviewer_role='INDEPENDENT_SOURCE_REVIEWER',decision='SOURCE_FIELDS_REVIEWED',authorized=True))
    assert admission_candidate(root,candidate_binding=binding,review_binding=fake)['status']=='NOT_ADMITTED'
    kwargs=dict(candidate_binding=binding,head_path=parent['path'],cutoff=now.isoformat(),readback=lambda _:{})
    with pytest.raises(ValueError):authority.publish_identity(root,**kwargs,review_binding=fake)
    (root/parent['path']).write_bytes(b'{"changed_head":true}')
    with pytest.raises(ValueError,match='CAS_STALE'):authority.publish_identity(root,**kwargs,review_binding=review)
    with pytest.raises(ValueError,match='NO_PRODUCTION_HEAD'):
        authority.publish_identity(root,**dict(kwargs,head_path='data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json'),review_binding=review)


def test_retry_preserves_first_freeze_at_later_actual_clock(identity_fixture):
    root,now,day,docs,sources,parent=identity_fixture
    binding=rebuild(identity_fixture)
    before=(root/binding['path']).read_bytes()
    retry=build(root,sources=sources,parent_head=parent,candidate_directory='docs/evidence/candidates',
                cutoff=now.isoformat(),clock=lambda:now+timedelta(seconds=1))
    assert retry==binding and (root/binding['path']).read_bytes()==before
