import json
from workbench_db.v4_snapshot_pg_r2 import Builder
from workbench_service.production_v4 import ProductionV4ResearchReader,reference,REQUIRED_METADATA
from workbench_service.current_v4_context import canonical
from workbench_service.v4_daily_refresh import atomic_bytes
from workbench_service.domain_views import sector_view
from test_fp02_research_snapshot import reader

def test_overlap_uses_frozen_denominator(tmp_path):
    path=tmp_path/'s.pg.json';db=Builder(tmp_path,'fp06-overlap-engineering')
    db.executescript('CREATE TABLE objects(domain text,id text,name text,symbol text,state text,payload text,PRIMARY KEY(domain,id));CREATE TABLE aliases(alias text,id text,PRIMARY KEY(alias,id));CREATE TABLE members(sector text,security text,PRIMARY KEY(sector,security));CREATE TABLE metadata(key text PRIMARY KEY,value text);')
    for pair in [('THEME:A','1'),('THEME:A','2'),('THEME:A','3'),('THEME:B','2'),('THEME:B','3'),('THEME:B','4')]:db.execute('INSERT INTO members VALUES(?,?)',pair)
    descriptor=db.seal({'release_id':'fp06-overlap-engineering','context':{'accepted_trade_date':'2026-09-30'}},source_binding={'kind':'SYNTHETIC_ENGINEERING_ONLY','sha256':'a'*64});db.commit();db.close();atomic_bytes(path,canonical(descriptor))
    metadata={k:'unit-test-only' for k in REQUIRED_METADATA};metadata.update(trading_date='2026-09-30',evidence_origin='REAL_ACCEPTED_SOURCE')
    manifest=dict(database=reference(tmp_path,path),context=dict(accepted_trade_date='2026-09-30',data_updated_at='2026-10-01T00:00:00Z'),release_id='fp06-overlap-engineering',source_contract_digest='a'*64,sources={'membership':{'sha256':'a'*64}},quality='QUALITY_DEGRADED',gaps=[],counts={},metadata=metadata)
    atomic_bytes(tmp_path/'manifest.json',canonical(manifest));atomic_bytes(tmp_path/'config/v4_research_snapshot_authority_v1.json',canonical({'manifest':reference(tmp_path,tmp_path/'manifest.json')}))
    r=ProductionV4ResearchReader(tmp_path)
    result=sector_view(r,{'entity_id':'THEME:A'},'overlap',{})
    assert result['items'][0]['intersection_count']==2
    assert result['items'][0]['union_count']==4
    assert result['items'][0]['jaccard']==.5
    assert result['member_count']==3 and result['unique_share']==1/3

def test_numeric_sort_and_injection_contract(reader):
    rows=reader.query('stocks',{'sort':'-close'})['items']
    assert [r['fields']['close']['value'] for r in rows]==list(range(6,-1,-1))
    assert reader.query('stocks',{'eligibility':'TRUE'})['total']==0
