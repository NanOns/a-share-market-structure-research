"""Negative source/admission fixtures and independent arithmetic oracles."""
import gzip
import json
from copy import deepcopy
from datetime import datetime,timezone,timedelta
import pytest
from workbench_analysis.v4_14_replay_io import publish
from workbench_analysis.r43_owner_replay import ref
from workbench_analysis.strict_source_candidate_v2 import freeze_for_review,validate_cutoff
from workbench_analysis.source_capture_candidate_v1 import capture,instant
from workbench_service.candidate_research_read_v2 import read_candidates
from sector.research_rank_source_v2 import extract_strength


def test_rank_uses_normal_median_not_rps_or_absolute_return():
    core=[dict(security_id=str(i),trade_date='2026-10-09',fields={
        f'ret{n}':dict(value=i/100,quality_state='OBSERVED') for n in (5,20)}) for i in range(101)]
    states=[dict(security_id=str(i),trade_date='2026-10-09',target_values=dict(normal_universe=i<100)) for i in range(101)]
    result=extract_strength(core,states,'2026-10-09')
    assert result[0]['rs5']==pytest.approx(-.495)
    assert result[99]['rs20']==pytest.approx(.495)
    assert result[100]['rs5'] is None
    core[0]['fields']['ret20']['value']=None
    result=extract_strength(core,states,'2026-10-09')
    assert all(r['rs20'] is None for r in result) # 99 is below original minimum 100.
    assert result[99]['rs5']==pytest.approx(.495)


@pytest.mark.parametrize('change', ['duplicate','date','future'])
def test_rank_rejects_wrong_source_window(change):
    core=[dict(security_id='S',trade_date='2026-10-09',fields={
        f'ret{n}':dict(value=.1,quality_state='OBSERVED',window_end_trade_date='2026-10-09') for n in (5,20)})]
    if change=='duplicate':core*=2
    if change=='date':core[0]['trade_date']='2026-10-08'
    if change=='future':core[0]['fields']['ret5']['window_end_trade_date']='2026-10-12'
    with pytest.raises(ValueError):extract_strength(core,[],'2026-10-09')


@pytest.mark.parametrize('key',['max_source_date','window_end_trade_date','window_start_trade_date','window_end'])
def test_nested_future_windows_fail_closed(key):
    with pytest.raises(ValueError,match='FUTURE_STATE_WINDOW_INPUT'):
        validate_cutoff({'fields':{'ret5':{key:'2026-10-12'}}},'2026-10-09')


@pytest.fixture
def source_fixture(tmp_path):
    day=datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=8))).date().isoformat()
    common=publish(tmp_path,'inputs/common.json',{})
    calendar=publish(tmp_path,'inputs/calendar.json',dict(session_dates=[day]))
    life=publish(tmp_path,'inputs/life.json',dict(active_security_ids=['S']))
    snapshot=publish(tmp_path,'inputs/members.json',dict(sources=[]))
    def rows(name,data):
        p=tmp_path/f'inputs/{name}.gz';p.write_bytes(gzip.compress(('\n'.join(json.dumps(r) for r in data)).encode()))
        return ref(tmp_path,p)
    core=rows('core',[dict(security_id='S',trade_date=day,fields=dict(ret5=dict(window_end_trade_date=day)),PIT_ELIGIBLE=False)])
    prewatch=rows('state',[dict(security_id='S',trade_date=day,target_values={},normal_evidence={},PIT_ELIGIBLE=False,
        confirmation=dict(scenario_evidence=[dict(scenario='LAUNCH_CONFIRM',status='FALSE')]))])
    raw=rows('raw',[dict(security_id='S',trade_date=day)])
    head=dict(accepted_trade_date=day,owners={day:dict(raw=raw,core=core,prewatch=prewatch,lifecycle=life)},membership_snapshot=snapshot)
    hb=publish(tmp_path,'inputs/head.json',head)
    for path in ('src/workbench_analysis/r43_focus_replay.py','config/research_attention_v3.yaml',
                 'src/workbench_analysis/strict_source_candidate_v2.py','src/workbench_analysis/full_state_signal_candidate_v1.py'):
        p=tmp_path/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_text('test fixture')
    original=tmp_path/'inputs/original';original.write_bytes(b'observed now')
    now=datetime.now(timezone.utc).isoformat()
    cb=capture(tmp_path,trade_date=day,sessions=[day],calendar_binding=calendar,
        sources=[dict(name='original',path=str(original),trade_date=day,requested_at=now,received_at=now,timestamp_basis='LOCAL_READ')],
        security_ids=['S'],sector_ids=['B'],model_binding=common,config_binding=common)
    return tmp_path,day,hb,cb


def test_live_capture_has_real_clock_without_grant_and_keeps_strict_gap(source_fixture):
    root,day,hb,cb=source_fixture
    capture_doc=json.loads((root/cb['path']).read_bytes())
    assert instant(capture_doc['captured_at'])>=instant(capture_doc['sources'][0]['received_at'])
    binding=freeze_for_review(root,capture_binding=cb,candidate_binding=hb,trade_date=day)
    doc=json.loads((root/binding['path']).read_bytes())
    assert doc['review_readiness']=='SOURCE_GAPS'
    assert 'STRICT_STATE_WINDOWS_AND_MEMBERSHIP_NOT_ADMITTED' in doc['source_gaps']
    assert not doc['formal_consumer_enabled'] and not doc['PIT_ELIGIBLE']
    assert doc['observed_count'] is None and not any(r['eligible_at_T0'] for r in doc['signals'])
    assert freeze_for_review(root,capture_binding=cb,candidate_binding=hb,trade_date=day)==binding


def test_historical_capture_cannot_be_promoted_by_clock_change(source_fixture):
    root,day,hb,cb=source_fixture
    doc=json.loads((root/cb['path']).read_bytes());doc['evidence_class']='RECONSTRUCTED_RESEARCH_ONLY'
    altered=publish(root,'inputs/historical.json',doc)
    with pytest.raises(ValueError,match='NO_HISTORICAL_FIRST_CAPTURE_BACKFILL'):
        freeze_for_review(root,capture_binding=altered,candidate_binding=hb,trade_date=day)


@pytest.fixture
def display_fixture(tmp_path):
    day='2026-10-09';b=publish(tmp_path,'inputs/source.json',{})
    owner={k:b for k in ('lifecycle','core','sector','prewatch')}
    head=dict(owners={day:owner},membership_snapshot=b)
    hb=publish(tmp_path,'inputs/head.json',head)
    doc=dict(T0=day,production=False,sources=deepcopy(owner),membership=b,model=b,dependencies=[b],
        evidence_class='RECONSTRUCTED_RESEARCH_ONLY',rows=[dict(sector_id='INDUSTRY:T0706',T0=day,
        production=False,formal_consumer_enabled=False,inputs={},CONFIRMED='TRUE')])
    sb=publish(tmp_path,'inputs/sector.json',doc)
    index=dict(contract_id='PRODUCER_CANDIDATE_INDEX_V2',sessions={day:dict(head=hb,sector=sb,production=False)})
    p=tmp_path/'data/v4/producer_candidate_index_v2.json';p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(index))
    return tmp_path,day,head,hb,doc,index


def test_candidate_is_head_bound_and_never_formal(display_fixture):
    root,day,head,hb,_,_=display_fixture
    r=read_candidates(root,head=head,token=hb['sha256'],day=day,sector_id='INDUSTRY:T0706')
    assert r['candidate_status']=='AVAILABLE' and r['item']['CONFIRMED']=='TRUE'
    assert r['observed_count'] is None and not r['formal_consumer_enabled']
    r=read_candidates(root,head=head,token='different',day=day,sector_id='INDUSTRY:T0706')
    assert r['candidate_status']=='UNAVAILABLE' and r['reason']=='CANDIDATE_HEAD_MISMATCH'


@pytest.mark.parametrize('change',['date','duplicate','member','owner','missing_owner','formal','tamper'])
def test_bad_candidate_is_local_unavailable(display_fixture,change):
    root,day,head,hb,doc,index=display_fixture
    if change=='date':doc['T0']='2026-10-08'
    if change=='duplicate':doc['rows']*=2
    if change=='member':doc['membership']=publish(root,'inputs/wrong.json',dict(wrong=True))
    if change=='owner':doc['sources']['core']=publish(root,'inputs/wrong.json',dict(wrong=True))
    if change=='missing_owner':del doc['sources']['core']
    if change=='formal':doc['rows'][0]['formal_consumer_enabled']=True
    sb=publish(root,'inputs/altered.json',doc)
    if change=='tamper':(root/sb['path']).write_bytes(b'{}')
    index['sessions'][day]['sector']=sb
    (root/'data/v4/producer_candidate_index_v2.json').write_text(json.dumps(index))
    r=read_candidates(root,head=head,token=hb['sha256'],day=day,sector_id='INDUSTRY:T0706')
    assert r['candidate_status']=='UNAVAILABLE' and r['formal_consumer_enabled'] is False
