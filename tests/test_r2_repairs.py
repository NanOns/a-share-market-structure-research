import json,sqlite3
from types import SimpleNamespace
from workbench_service.domain_views import home
from workbench_service.focus_views import focus_view
from workbench_service.stock_views import timeline

def test_sixteenth_sector_does_not_hide_change(tmp_path):
    p=tmp_path/'x.sqlite';db=sqlite3.connect(p)
    db.executescript('CREATE TABLE objects(domain,id,payload);CREATE TABLE members(sector,security);')
    for i in range(16):
        sid=f'THEME:{i:02}';eid=f'S{i:02}'
        for domain,identity in [('sectors',sid),('events',eid)]:
            db.execute('INSERT INTO objects VALUES(?,?,?)',(domain,identity,json.dumps(dict(entity_id=identity,fields={'effective_event':{'value':'NEW_CONFIRMED'}}))))
        db.execute('INSERT INTO members VALUES(?,?)',(sid,eid))
    db.commit();db.close()
    r=SimpleNamespace(path=p,context={'trade_date':'2026-09-30'},manifest={'counts':{},'gaps':[],'sources':{'events':{}}},envelope=lambda **k:k)
    d=home(r)
    assert len(d['sector_changes'])==15 and d['sector_change_total']==16
    assert [x['entity_id'] for x in d['changes']]==['S15']

def test_focus_paths_have_distinct_data_and_outcomes_fail_closed():
    ep=dict(episode_id='E',entity_id='S',T0='2026-09-30',anchors=[dict(kind='FIRST_FOCUS',anchor_id='A',trade_date='2026-09-30')],observations=[dict(trade_date='2026-09-30',event='NEW',source_publication='P')])
    r=SimpleNamespace(manifest={'domain_features':{'focus':{'episodes':[ep],'events':[dict(entity_id='S',episode_id='E',trade_date='2026-09-30',event='NEW',idempotency_key='K')]}}},envelope=lambda **k:k)
    assert focus_view(r,'S','episodes',{})['items']==[ep]
    assert focus_view(r,'S','anchors',{})['items'][0]['anchor_id']=='A'
    assert 'observations' not in focus_view(r,'S','observations',{})['items'][0]
    assert focus_view(r,'S','timeline',{})['items'][0]['idempotency_key']=='K'
    assert focus_view(r,'S','outcomes',{})['status']=='SOURCE_INCOMPLETE'
    assert focus_view(r,'S','outcomes',{})['items']==[]

def test_stock_timeline_keeps_owner_source_and_names_missing_fields():
    r=SimpleNamespace(envelope=lambda **k:k)
    cell=dict(value=[{'event':'BREAKOUT','date':'2026-09-30'}],quality='KNOWN',source_digest='x')
    d=timeline(r,dict(fields={'structure_events':cell}),{})
    assert d['items'][0]['source']==cell
    assert d['owner_specific_debt'][0]['field']=='anchor_view_asof_t'
    assert d['status']=='SOURCE_INCOMPLETE'
