import json
import pytest
from test_next_stage_c_episode_genesis import genesis
from sector.episode_genesis_candidate_v2 import create, observe
from workbench_analysis.v4_14_replay_io import publish


@pytest.mark.parametrize('age,status,next_index', [(0,'PENDING',1),(1,'UNKNOWN',3),(3,'UNKNOWN',5),(5,'UNKNOWN',None)])
def test_pending_and_due_missing(genesis, age, status, next_index):
    root,docs,refs,kwargs,days=genesis
    ep=create(root,**kwargs)
    result=observe(root,episode_binding=ep,trade_date=days[age],calendar_binding=refs['calendar'])
    assert result['followup_status']==status
    assert result['followup_complete']=='UNKNOWN'
    assert result['next_due_date']==(days[next_index] if next_index is not None else None)
    assert len(result['unknown_due_reasons'])==sum(h<=age for h in (1,3,5))


@pytest.mark.parametrize('event', ['SUSPENDED','DELISTED','OLD_EVENT_WITHOUT_OWNER','LATE_SOURCE'])
def test_events_do_not_replace_due_owner(genesis,event):
    root,docs,refs,kwargs,days=genesis
    ep=create(root,**kwargs)
    result=observe(root,episode_binding=ep,facts={'event':{'value':event,'max_source_date':days[1]}},trade_date=days[1],calendar_binding=refs['calendar'])
    assert result['followup_status']=='UNKNOWN' and result['followup']['1']['status']=='UNKNOWN'


def test_late_valid_settlement_and_calendar_gap(genesis):
    root,docs,refs,kwargs,days=genesis
    ep=create(root,**kwargs); item=json.loads((root/ep['path']).read_bytes())
    settlements={}
    for h in (1,3,5):
        raw=publish(root,f'inputs/raw-{h}.json',dict(trade_date=days[h],value=.01))
        settlements[str(h)]=publish(root,f'inputs/settled-{h}.json',dict(first_available=kwargs['cutoff'],trade_date=days[h],member_ids=item['member_ids'],episode_id=item['episode_id'],source_binding=raw))
    complete=observe(root,episode_binding=ep,trade_date=days[5],calendar_binding=refs['calendar'],settlement=settlements)
    assert complete['followup_complete']=='TRUE' and complete['followup_status']=='COMPLETE'
    docs['calendar']['session_dates']=days[:2]
    cb=publish(root,'inputs/short-calendar.json',docs['calendar'])
    capture=publish(root,'inputs/short-calendar-capture.json',dict(docs['capture'],capture_id='SHORT_CALENDAR'))
    price=publish(root,'inputs/short-calendar-price.json',dict(docs['price'],source_capture=capture))
    short=create(root,**dict(kwargs,calendar_binding=cb,capture_binding=capture,price_binding=price))
    gap=observe(root,episode_binding=short,trade_date=days[0],calendar_binding=cb)
    assert gap['followup_status']=='UNKNOWN'
    assert {r['horizon'] for r in gap['unknown_due_reasons']}=={'3','5'}
    none=observe(root,trade_date=days[0],calendar_binding=cb)
    assert none['followup_complete'] is None and none['followup_status']=='NO_PRIOR_EPISODE'
