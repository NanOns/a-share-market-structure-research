"""Safety and display bounds, including risk-only/empty trading sessions."""
import json,uuid
from types import SimpleNamespace
import pytest
from workbench_service.domain_views import home

@pytest.mark.parametrize('event,count', [('NEW_CONFIRMED',42),('INVALIDATED',35),('PERSISTENT',40),('NONE',0)])
def test_home_does_not_hide_risk_or_invent_changes(tmp_path,event,count):
    from workbench_db.v4_snapshot_pg_r2 import Builder,read
    db=Builder(tmp_path,uuid.uuid4().hex)
    db.executescript('CREATE TABLE objects(domain text,id text,name text,symbol text,state text,payload text,PRIMARY KEY(domain,id));CREATE TABLE members(sector text,security text,PRIMARY KEY(sector,security));CREATE TABLE aliases(alias text,id text,PRIMARY KEY(alias,id));CREATE TABLE metadata(key text PRIMARY KEY,value text);')
    for i in range(count):
        r=dict(entity_id=str(i),fields={'effective_event':{'value':event}})
        db.execute('INSERT INTO objects VALUES(?,?,?,?,?,?)',('events',str(i),'','','',json.dumps(r)))
    descriptor=db.seal(dict(release_id='home-synthetic-test-only',context=dict(accepted_trade_date='2026-09-30'),fixture_scope='NEVER_PRODUCTION'));db.commit();db.close()
    r=SimpleNamespace(connect=lambda:read(descriptor),context={'trade_date':'2026-09-30'},manifest={'counts':{},'gaps':[],'sources':{'events':{'sha256':'f'*64}}},envelope=lambda **k:k)
    result=home(r)
    assert len(result['changes'])<=30
    assert result['change_total']==(count if event in ('NEW_CONFIRMED','INVALIDATED') else 0)
    assert len(result['risks'])==(min(30,count) if event=='INVALIDATED' else 0)
    assert result['persistent_count']==(count if event=='PERSISTENT' else 0)
