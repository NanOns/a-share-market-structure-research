"""Two fixed synthetic groups. Success grants no production rights."""
import gzip
import json
from datetime import datetime
import pytest
from test_full_state_first_observed_v1 import inputs, DAY, NOW
from workbench_analysis.v4_14_replay_io import publish, ref
from workbench_analysis.state_publisher_bridge_v1 import bridge
from workbench_analysis.cohort_capture_readiness_r1 import prepare_capture


def fixture(root, fault=None):
    original = inputs(root)
    state=json.loads((root/original['state_binding']['path']).read_bytes())
    members=json.loads((root/original['membership_binding']['path']).read_bytes())
    model=json.loads((root/original['model_binding']['path']).read_bytes())
    state.update(evidence_class='OBSERVED_SOURCE_CANDIDATE', production=False,
                 production_write_authorized=False, adapter_gap='INDEPENDENT_ADMISSION_REQUIRED', synthetic=True)
    for row in state['scenario_outputs']: row['eligible_at_T0']=False
    if fault=='historical':state['evidence_class']='RECONSTRUCTED_RESEARCH_ONLY'
    if fault=='focus':state['scope']='FOCUS_TOP_K'
    if fault=='future':state['T0']='2026-10-13'
    (root/'publisher.gz').write_bytes(gzip.compress(json.dumps(state).encode(),mtime=0))
    publisher=ref(root,'publisher.gz')
    members.update(AS_RECORDED=True,PIT_ELIGIBLE=True,publisher_membership=state['membership'])
    if fault=='fake_member':members['AS_RECORDED']=False
    if fault=='changed_member':members['security_ids']=['SH.600001']
    members=publish(root,'bridge_members.json',members)
    model.update(T0=DAY,publisher_model=state['model'])
    if fault=='missing_clock':model.pop('first_available')
    model=publish(root,'bridge_model.json',model)
    clk=dict(T0=DAY,first_available=DAY+'T15:20:00+08:00',frozen_at=DAY+'T15:30:00+08:00',synthetic=True)
    events=[dict(security_id=r['security_id'],scenario=r['scenario'],episode_id=r['episode_id'],event_type=r['event_type']) for r in state['scenario_outputs']]
    benchmarks=[dict(security_id=r['security_id'],scenario=r['scenario'],benchmark=r['benchmark']) for r in state['scenario_outputs']]
    if fault=='event':events[0]['event_type']=None
    if fault=='benchmark':benchmarks[0]['benchmark']={}
    if fault=='revision':events[0]['episode_id']='CHANGED'
    events=publish(root,'bridge_events.json',dict(clk,rows=events))
    benchmarks=publish(root,'bridge_benchmarks.json',dict(clk,rows=benchmarks))
    bindings=dict(publisher=publisher,membership=members,model=model,events=events,benchmark=benchmarks)
    review=dict(clk,contract_id='STATE_SOURCE_INDEPENDENT_REVIEW_V1', sources=bindings,
        decision='SOURCE_FIELDS_REVIEWED',reviewer_role='INDEPENDENT_SOURCE_REVIEWER',
        state_lineage_id='SYNTHETIC_L2',frozen_signal_version='V1',capture_deadline=DAY+'T18:00:00+08:00')
    if fault=='late':review['first_available']=DAY+'T17:00:00+08:00'
    if fault=='owner_sha':review['sources']=dict(bindings,events=dict(events,sha256='0'*64))
    review=publish(root,'bridge_review.json',review)
    return dict(root=root,publisher_binding=publisher,membership_binding=members,model_binding=model,
        events_binding=events,benchmark_binding=benchmarks,admission_binding=review,
        candidate_directory='docs/evidence/synthetic_bridge',clock=lambda:datetime.fromisoformat(NOW))


def test_fixed_positive_group(tmp_path):
    args=fixture(tmp_path)
    result=bridge(**args)
    assert result['status']=='ENG_PRODUCER_READY' and not result['production_write_authorized']
    extracted=result['first_observed']['extraction']
    assert (extracted['eligible_count'],extracted['ineligible_count'])==(2,2)
    head=publish(tmp_path,'preflight.json',dict(owners={DAY:{'validation_cohort':extracted['owner_binding']}},cohort_capture_receipts={DAY:extracted['capture_receipt_binding']}))
    with pytest.raises(ValueError,match='WRITE_GRANT_REQUIRED'):
        prepare_capture(tmp_path,accepted_head=head,owner_binding=extracted['owner_binding'],trade_date=DAY,revision='r1',cutoff=NOW)
    assert result['source_owner_admitted'] is False
    grant=publish(tmp_path,'independent_synthetic_grant.json',dict(contract_id='COHORT_FIRST_CAPTURE_WRITE_GRANT_R1',capability='PREPARE_FIRST_CAPTURE',authorized=True,revoked=False,owner=extracted['owner_binding'],source_receipt=extracted['capture_receipt_binding'],trade_date=DAY,revision='r1',valid_from=DAY+'T15:00:00+08:00',valid_until=DAY+'T18:00:00+08:00',synthetic=True))
    granted=publish(tmp_path,'independent_synthetic_head.json',dict(owners={DAY:{'validation_cohort':extracted['owner_binding']}},cohort_capture_receipts={DAY:extracted['capture_receipt_binding']},cohort_write_grants={DAY:grant}))
    prepared=prepare_capture(tmp_path,accepted_head=granted,owner_binding=extracted['owner_binding'],trade_date=DAY,revision='r1',cutoff=NOW)
    assert prepared['eligible_count']==2 and prepared['production_write_authorized'] is False


@pytest.mark.parametrize('fault',['historical','late','fake_member','event','benchmark','focus','future','owner_sha','changed_member','missing_clock'])
def test_fixed_negative_group(tmp_path,fault):
    args=fixture(tmp_path,fault)
    if fault in ('historical','missing_clock'):
        result=bridge(**args)
        assert result['status']=='SOURCE_GAPS'
    else:
        with pytest.raises(ValueError):bridge(**args)


def test_same_revision_order_or_content_change_is_no_clobber(tmp_path):
    args=fixture(tmp_path);bridge(**args)
    source=json.loads(gzip.decompress((tmp_path/'publisher.gz').read_bytes()))
    source['scenario_outputs'].reverse()
    (tmp_path/'publisher.gz').write_bytes(gzip.compress(json.dumps(source).encode(),mtime=0))
    with pytest.raises(ValueError):bridge(**args)


def real_build_positive(root):
    # Historical target values are reused solely as clearly marked synthetic
    # test originals; injectable clocks never assert real first observation.
    from test_pre_next_t0_publisher import publisher_inputs
    from workbench_analysis.full_market_state_publisher_v1 import build
    root,row,candidate=publisher_inputs.__wrapped__(root)
    day='2026-10-09';stamp=day+'T18:35:00+08:00'
    row.update(AS_RECORDED=True,PIT_ELIGIBLE=True,synthetic=True)
    head=candidate([row],suffix='real_build_synthetic')
    h=json.loads((root/head['path']).read_bytes())
    sources=dict(facts=h['owners'][day]['prewatch'],lifecycle=h['owners'][day]['lifecycle'],membership=h['membership_snapshot'])
    obs=publish(root,'actual_build_observation.json',dict(T0=day,synthetic=True,sources=sources,cutoff=stamp,receipts=[dict(source=k,requested_at=day+'T18:20:00+08:00',received_at=day+'T18:25:00+08:00',first_available=day+'T18:30:00+08:00') for k in sources]))
    publisher=build(root,candidate_binding=head,trade_date=day,revision='SYNTHETIC_BUILD_R1',observation_binding=obs,clock=lambda:datetime.fromisoformat(stamp))
    source=json.loads(gzip.decompress((root/publisher['path']).read_bytes()))
    assert len(source['scenario_outputs'])==4
    original_model=json.loads((root/source['model']['path']).read_bytes())
    clocks=dict(T0=day,synthetic=True,first_available=day+'T18:30:00+08:00',frozen_at=stamp)
    members=publish(root,'actual_build_members.json',dict(clocks,membership_basis='AS_RECORDED',AS_RECORDED=True,PIT_ELIGIBLE=True,membership_version='SYNTHETIC_M',publisher_membership=source['membership'],security_ids=[row['security_id']]))
    model=publish(root,'actual_build_model.json',dict(original_model,**clocks,publisher_model=source['model']))
    events=publish(root,'actual_build_events.json',dict(clocks,rows=[dict(security_id=x['security_id'],scenario=x['scenario'],episode_id='SYNTHETIC_'+x['scenario'],event_type='SYNTHETIC_'+x['scenario']) for x in source['scenario_outputs']]))
    benchmark=publish(root,'actual_build_benchmark.json',dict(clocks,rows=[dict(security_id=x['security_id'],scenario=x['scenario'],benchmark={'id':'SYNTHETIC_BENCHMARK'}) for x in source['scenario_outputs']]))
    bindings=dict(publisher=publisher,membership=members,model=model,events=events,benchmark=benchmark)
    review=publish(root,'actual_build_review.json',dict(clocks,contract_id='STATE_SOURCE_INDEPENDENT_REVIEW_V1',sources=bindings,decision='SOURCE_FIELDS_REVIEWED',reviewer_role='INDEPENDENT_SOURCE_REVIEWER',state_lineage_id='SYNTHETIC_BUILD_LINEAGE',frozen_signal_version='SYNTHETIC_BUILD_V1',capture_deadline=day+'T19:00:00+08:00'))
    now=day+'T18:40:00+08:00'
    result=bridge(root,publisher_binding=publisher,membership_binding=members,model_binding=model,events_binding=events,benchmark_binding=benchmark,admission_binding=review,candidate_directory='docs/evidence/synthetic_build_bridge',clock=lambda:datetime.fromisoformat(now))
    extracted=result['first_observed']['extraction']
    assert extracted['eligible_count']+extracted['ineligible_count']==4
    grant=publish(root,'actual_build_grant.json',dict(contract_id='COHORT_FIRST_CAPTURE_WRITE_GRANT_R1',capability='PREPARE_FIRST_CAPTURE',authorized=True,revoked=False,owner=extracted['owner_binding'],source_receipt=extracted['capture_receipt_binding'],trade_date=day,revision='SYNTHETIC_BUILD_R1',valid_from=stamp,valid_until=day+'T19:00:00+08:00',synthetic=True))
    accepted=publish(root,'actual_build_synthetic_granted_head.json',dict(owners={day:{'validation_cohort':extracted['owner_binding']}},cohort_capture_receipts={day:extracted['capture_receipt_binding']},cohort_write_grants={day:grant}))
    prepared=prepare_capture(root,accepted_head=accepted,owner_binding=extracted['owner_binding'],trade_date=day,revision='SYNTHETIC_BUILD_R1',cutoff=now)
    assert not prepared['production_write_authorized']
    return dict(result=result,prepared=prepared,publisher=publisher,synthetic=True,grants_no_real_source_authority=True)


def test_fixed_positive_group_real_build_all_four_scenarios(tmp_path):
    real_build_positive(tmp_path)
