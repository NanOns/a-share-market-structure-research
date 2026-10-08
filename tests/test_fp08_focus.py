from focus_tracker.v4_successor import project

def row(day,pre='TRUE',confirmed='FALSE'):
    return dict(entity_id='A',trade_date=day,raw_qualification={'PREWATCH':pre,'CONFIRMED':confirmed},publication_id=day)

def test_lifecycle_reentry_unknown_and_idempotency():
    days={'2026-09-24':[row('2026-09-24')],'2026-09-28':[row('2026-09-28','UNKNOWN','UNKNOWN')],'2026-09-29':[row('2026-09-29','FALSE')],'2026-09-30':[row('2026-09-30')]}
    result=project(days)
    assert [e['event'] for e in result['events']]==['NEW','DATA_UNAVAILABLE','EXITED','REENTERED']
    assert result==project(days)
    assert result['episodes'][1]['parent_episode_id']==result['episodes'][0]['episode_id']
    assert len({e['idempotency_key'] for e in result['events']})==4

def test_upgrade_and_no_fabricated_new_day():
    result=project({'2026-09-29':[row('2026-09-29')],'2026-09-30':[row('2026-09-30','FALSE','TRUE')]})
    assert [e['event'] for e in result['events']]==['NEW','UPGRADED']
    assert result['episodes'][0]['T0']=='2026-09-29'
