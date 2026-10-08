"""Independent real-source oracle and transaction readback for FP02-04."""
import gzip
import json
import sqlite3
import statistics
import sys
import time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'));sys.path.insert(0,str(ROOT))
from scripts.fp01_evidence import write,ref
from workbench_service.production_v4 import ProductionV4ResearchReader,build_snapshot,rollback_snapshot,POINTER
from workbench_service.current_v4_context import digest,SourceInvalid
from workbench_service.research_bff import ResearchBFF
OUT=ROOT/'docs/evidence/fp02_20261008'

def main():
    reader=ProductionV4ResearchReader(ROOT);receipt={};bff=ResearchBFF(ROOT)
    for domain,expected in [('stocks',5213),('sectors',378)]:
        ids=[];tokens=set();times=[]
        for offset in range(0,expected,200):
            start=time.perf_counter();p=reader.query(domain,dict(limit='200',offset=str(offset)),summary=True);times.append(time.perf_counter()-start)
            assert p['total']==expected and p['has_next']==(offset+200<expected)
            ids.extend(row['entity_id'] for row in p['items']);tokens.add(p['context_token'])
        assert len(ids)==len(set(ids))==expected and len(tokens)==1
        receipt[domain]=dict(rows=len(ids),unique=len(set(ids)),page_p50_ms=round(statistics.median(times)*1000,2),page_max_ms=round(max(times)*1000,2),same_context=True)
    # Compare original accepted output values directly, without using builder projection functions.
    advanced=reader.manifest['sources']['advanced'];checks=[]
    with gzip.open(ROOT/advanced['path'],'rt',encoding='utf8') as f:
        for line in f:
            original=json.loads(line);page=reader.query('stocks',entity=original['security_id'])
            if not page['items']:continue
            projected=page['items'][0]
            for field in ['primary_industry','supporting_concepts','active_anchor_id','retest_count','basic_breakout_state']:
                assert projected['fields'][field]['value']==original['fields'][field]['value']
                assert projected['fields'][field]['quality']==original['fields'][field]['quality']
            checks.append(original['security_id'])
            if len(checks)==12:break
    receipt['real_profile_oracle']=dict(samples=checks,fields_per_sample=5,source=advanced,result='PASS')
    with sqlite3.connect(reader.path) as db:
        plans=db.execute('EXPLAIN QUERY PLAN SELECT id FROM objects WHERE domain=? AND name>=? AND name<? ORDER BY name,id LIMIT 30',('stocks','浦','浦\uffff')).fetchall()
        assert any('INDEX' in p[-1] for p in plans)
    receipt['query_plan']=plans
    assert reader.query('stocks',{'q':'600000'})['total']==1
    assert reader.query('stocks',{'q':'浦发银行'})['total']==1
    receipt['search']=dict(code='600000',chinese_name='浦发银行',result='PASS')
    for key in ['context_token','trade_date','release_id','model_namespace']:
        assert bff.get('/api/v4/stocks',{key:'stale'})[0]==409
    receipt['context_conflicts']='PASS_4_DIMENSIONS'
    routes=json.loads((ROOT/'config/v4_research_bff_contract_v1.json').read_bytes())['routes'];coverage=[]
    stock=reader.query('stocks',{'limit':'1'})['items'][0]['entity_id'];sector=reader.query('sectors',{'limit':'1'})['items'][0]['entity_id']
    for route in routes:
        path=route['path'].replace('{id}',stock if '/stocks/' in route['path'] else sector)
        code,p=bff.get(path,{})
        expected=501 if route['status'].endswith('501') else 200
        assert code==expected,(path,code,p)
        assert p['context_token']==reader.token
        coverage.append(dict(route=route['path'],http=code,status=p['status']))
    receipt['route_coverage']=coverage
    raw=(ROOT/POINTER).read_bytes();token=reader.token
    try:build_snapshot(ROOT,expected_pointer=digest(raw),fail_readback=True)
    except SourceInvalid as e:assert str(e)=='INJECTED_READBACK_FAILURE'
    else:raise AssertionError('Injected failure did not fail')
    assert (ROOT/POINTER).read_bytes()==raw
    receipt['failed_publication']='PASS_EXACT_POINTER_PRESERVED'
    new=build_snapshot(ROOT,expected_pointer=digest(raw));assert ProductionV4ResearchReader(ROOT).token!=token
    rollback_snapshot(ROOT,digest((ROOT/POINTER).read_bytes()))
    assert ProductionV4ResearchReader(ROOT).token==token and (ROOT/POINTER).read_bytes()==raw
    receipt['rollback']='PASS_EXACT_PRIOR_TOKEN_AND_POINTER'
    write(OUT/'REAL_READBACK_AND_ROLLBACK.json',receipt)
    write(OUT/'SNAPSHOT_DICTIONARY.json',reader.manifest)
    print(json.dumps({k:v for k,v in receipt.items() if k not in ['real_profile_oracle','route_coverage']},ensure_ascii=False))
if __name__=='__main__':main()
