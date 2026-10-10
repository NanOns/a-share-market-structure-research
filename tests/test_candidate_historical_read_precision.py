"""Two distinct synthetic accepted releases; archives alone never grant access."""
import json
from copy import deepcopy
import pytest
from workbench_analysis.v4_14_replay_io import publish
from workbench_service.candidate_research_read_v2 import read_candidates
from test_producer_continuation_r2 import display_fixture


@pytest.fixture
def two_heads(display_fixture):
    root,day,old,hb,doc,index=display_fixture
    publish(root,f"data/v4/predecessors/{hb['sha256']}.json",old)
    new=deepcopy(old)
    new.update(accepted_trade_date='2026-10-12',dates=[day,'2026-10-12'],predecessor=hb)
    new['membership_snapshot']=publish(root,'inputs/new_members.json',{'new':'members'})
    new['owners']['2026-10-12']={'prewatch':new['membership_snapshot']}
    from workbench_analysis.operational_daily_storage_v1 import atomic_json
    from workbench_analysis.r43_owner_replay import ref
    atomic_json(root,root/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json',new)
    nb=ref(root,root/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json')
    state=dict(T0=day,production=False,source=old['owners'][day]['prewatch'],membership=old['membership_snapshot'],
        model=old['membership_snapshot'],config=old['membership_snapshot'],implementation=old['membership_snapshot'],
        universe_count=1,signal_count=4,research_eligible_count=1,evidence_class='RECONSTRUCTED_RESEARCH_ONLY')
    index['sessions'][day]['full_state']=publish(root,'inputs/full_state.json',state)
    (root/'data/v4/producer_candidate_index_v2.json').write_text(json.dumps(index))
    return root,day,old,hb,new,nb,index


def test_cross_head_sector_and_cohort_use_original_frozen_sources(two_heads):
    root,day,old,hb,new,nb,index=two_heads
    sector=read_candidates(root,head=new,token=nb['sha256'],day=day,sector_id='INDUSTRY:T0706')
    cohort=read_candidates(root,head=new,token=nb['sha256'],day=day)
    assert sector['candidate_status']=='AVAILABLE'
    assert cohort['candidate_status']=='RESEARCH_CANDIDATE_FROZEN'
    assert cohort['research_eligible_count']==1 and cohort['observed_count'] is None
    assert cohort['evidence_class']=='RECONSTRUCTED_RESEARCH_ONLY'
    assert sector['source']==index['sessions'][day]['sector']
    assert (root/hb['path']).read_bytes()==(root/f"data/v4/predecessors/{hb['sha256']}.json").read_bytes()


@pytest.mark.parametrize('case',['UNACCEPTED_HEAD','MUTATED_ARCHIVE','FUTURE_DATE','OLD_TOKEN','WRONG_SESSION'])
def test_historical_identity_negative_cases(two_heads,case):
    root,day,old,hb,new,nb,index=two_heads
    token=nb['sha256']
    if case=='UNACCEPTED_HEAD':
        fake=deepcopy(old);fake['invented']=True
        index['sessions'][day]['head']=publish(root,'inputs/unaccepted.json',fake)
    elif case=='MUTATED_ARCHIVE':
        (root/f"data/v4/predecessors/{hb['sha256']}.json").write_bytes(b'{}')
    elif case=='FUTURE_DATE':day='2026-10-13'
    elif case=='OLD_TOKEN':token=hb['sha256']
    else:
        day='2026-10-08';index['sessions'][day]=index['sessions']['2026-10-09']
    (root/'data/v4/producer_candidate_index_v2.json').write_text(json.dumps(index))
    result=read_candidates(root,head=new,token=token,day=day,sector_id='INDUSTRY:T0706')
    assert result['candidate_status']=='UNAVAILABLE' and result['reason']==case


def test_missing_historical_source_is_explicit(two_heads):
    root,_,_,_,new,nb,_=two_heads
    result=read_candidates(root,head=new,token=nb['sha256'],day='2026-10-07')
    assert result['reason']=='HISTORICAL_CANDIDATE_SOURCE_NOT_CAPTURED'
