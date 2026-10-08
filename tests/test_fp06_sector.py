import json,sqlite3
from types import SimpleNamespace
from workbench_service.domain_views import sector_view
from test_fp02_research_snapshot import reader

def test_overlap_uses_frozen_denominator(tmp_path):
    path=tmp_path/'s.sqlite';db=sqlite3.connect(path);db.executescript('CREATE TABLE objects(domain,id,payload);CREATE TABLE members(sector,security);')
    db.executemany('INSERT INTO members VALUES(?,?)',[('THEME:A','1'),('THEME:A','2'),('THEME:A','3'),('THEME:B','2'),('THEME:B','3'),('THEME:B','4')]);db.commit();db.close()
    r=SimpleNamespace(path=path,manifest={'sources':{'membership':{'sha256':'a'*64}}},context={'trade_date':'2026-09-30'},envelope=lambda **x:x)
    result=sector_view(r,{'entity_id':'THEME:A'},'overlap',{})
    assert result['items'][0]['intersection_count']==2
    assert result['items'][0]['union_count']==4
    assert result['items'][0]['jaccard']==.5
    assert result['member_count']==3 and result['unique_share']==1/3

def test_numeric_sort_and_injection_contract(reader):
    rows=reader.query('stocks',{'sort':'-close'})['items']
    assert [r['fields']['close']['value'] for r in rows]==list(range(6,-1,-1))
    assert reader.query('stocks',{'eligibility':'TRUE'})['total']==0
