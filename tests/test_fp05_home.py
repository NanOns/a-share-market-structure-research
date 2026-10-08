"""Safety and display bounds, including risk-only/empty trading sessions."""
import sqlite3,json
from types import SimpleNamespace
import pytest
from workbench_service.domain_views import home

@pytest.mark.parametrize('event,count', [('NEW_CONFIRMED',42),('INVALIDATED',35),('PERSISTENT',40),('NONE',0)])
def test_home_does_not_hide_risk_or_invent_changes(tmp_path,event,count):
    path=tmp_path/'sample.sqlite';db=sqlite3.connect(path)
    db.executescript('CREATE TABLE objects(domain,id,payload);CREATE TABLE members(sector,security);')
    for i in range(count):
        r=dict(entity_id=str(i),fields={'effective_event':{'value':event}})
        db.execute('INSERT INTO objects VALUES(?,?,?)',('events',str(i),json.dumps(r)))
    db.commit();db.close()
    r=SimpleNamespace(path=path,context={'trade_date':'2026-09-30'},manifest={'counts':{},'gaps':[],'sources':{'events':{'sha256':'f'*64}}},envelope=lambda **k:k)
    result=home(r)
    assert len(result['changes'])<=30
    assert result['change_total']==(count if event in ('NEW_CONFIRMED','INVALIDATED') else 0)
    assert len(result['risks'])==(min(30,count) if event=='INVALIDATED' else 0)
    assert result['persistent_count']==(count if event=='PERSISTENT' else 0)
