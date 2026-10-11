"""Five dates/cross-industry HTTP through default R2 catalogue, no injection."""
import json
import os
from pathlib import Path
import shutil
import sys
import threading
import time
from types import SimpleNamespace
from http.server import ThreadingHTTPServer
from urllib.request import urlopen
from urllib.error import HTTPError
from urllib.parse import urlencode, quote
from concurrent.futures import ThreadPoolExecutor

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from scripts.audit_r4_default_product_http import CANDIDATE,SOURCE,freeze,sha,write
OUT=ROOT/'docs/audits/r4_external_repair_r2_20261011'


def main():
    freeze(reuse=True)
    from tests import v4_native_isolation_plugin_r4 as guard
    from workbench_db.v4_native import connection,workspace_schema
    from workbench_db.v4_history_pg_r1 import DDL
    from workbench_analysis.operational_successor_v1 import accepted_api
    from workbench_analysis.operational_daily_jobs_pg_r1 import DailyJobs
    from workbench_service.core_product_server_r1 import make_product_handler
    from psycopg import sql
    prior=json.loads((ROOT/'docs/audits/full_system_r4_pg_only_20261011_fbd23a6b/R4_03_FIVE_DATE_HISTORY_RESULT.json').read_bytes())
    authority_path=CANDIDATE/'config/core_product_read_authority_r1.json'
    before=authority_path.read_bytes();singleton=json.loads(before)
    base=json.loads((CANDIDATE/singleton['manifest']['path']).read_bytes())
    target=workspace_schema(CANDIDATE,'history')
    os.environ['R4_CONNECTION_LEDGER']=str(OUT/'DEFAULT_FIVE_DATES_CONNECTIONS.jsonl')
    os.environ['R4_PG_DATA_DIRECTORY']='G:/codex_tmp/full_system_r4_fbd23a6b/pg_data'
    config=SimpleNamespace();guard.pytest_configure(config);guard.ACTIVE='DEFAULT_FIVE_DATE_PRODUCT_HTTP_R2'
    server=jobs=thread=None;code=1;results=[];routes=[];catalog={}
    try:
        with connection(target) as pg:
            pg.execute(DDL)
            for item in prior['results']:
                b=item['pg_binding'];version=b['version']
                expected=(b['head_token'],b['T0'],b['source_digest'],b['logical_digest'],b['symbol_count'],b['bar_count'])
                actual=pg.execute(sql.SQL('SELECT head_token,t0::text,source_digest,logical_digest,symbol_count,bar_count FROM {}.history_versions WHERE version=%s').format(sql.Identifier(b['schema'])),(version,)).fetchone()
                if actual!=expected:raise ValueError('FROZEN_HISTORY_VERSION_MISMATCH')
                if not pg.execute('SELECT 1 FROM history_versions WHERE version=%s',(version,)).fetchone():
                    pg.execute(sql.SQL('INSERT INTO history SELECT * FROM {}.history WHERE version=%s').format(sql.Identifier(b['schema'])),(version,))
                    pg.execute(sql.SQL('INSERT INTO history_versions SELECT * FROM {}.history_versions WHERE version=%s').format(sql.Identifier(b['schema'])),(version,))
        for item in prior['results']:
            day=item['T0'];b=item['pg_binding'];source=item['source_binding']
            dest=CANDIDATE/source['path']
            if not dest.exists():
                dest.parent.mkdir(parents=True,exist_ok=True);temporary=dest.with_suffix('.tmp');shutil.copyfile(SOURCE/source['path'],temporary);os.replace(temporary,dest)
            if sha(dest)!=source['sha256']:raise ValueError('FROZEN_HISTORY_SOURCE_MISMATCH')
            manifest=dict(base,T0=day,history_index=dict(b,schema=target),source_bindings=dict(history=source))
            if day!=base['T0']:
                manifest.update(contract_id='CORE_PRODUCT_DATED_HISTORY_ONLY_PACK_R1',capabilities=['CHART_HISTORY'],market_facts=None)
            path=CANDIDATE/('data/v4/r4_r2_dated_catalog/'+day+'/MANIFEST.json')
            write(path,manifest);catalog[day]=dict(path=path.relative_to(CANDIDATE).as_posix(),sha256=sha(path),bytes=path.stat().st_size)
        write(authority_path,dict(contract_id='CORE_PRODUCT_READ_AUTHORITY_R2',dates=catalog))
        api=accepted_api(CANDIDATE);jobs=DailyJobs(CANDIDATE)
        server=ThreadingHTTPServer(('127.0.0.1',0),make_product_handler(CANDIDATE,jobs))
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        def get(path,q):
            start=time.monotonic()
            try:
                with urlopen(f'http://127.0.0.1:{server.server_port}'+path+'?'+urlencode(q),timeout=120) as response:
                    raw=response.read();return response.status,json.loads(raw),len(raw),time.monotonic()-start
            except HTTPError as exc:return exc.code,json.loads(exc.read()),0,time.monotonic()-start
        selected=[];industries=set()
        _,stocks,_,_=get('/api/v4/stocks',dict(context_token=api.token,trade_date=base['T0'],limit=200))
        for row in stocks['items']:
            sector=row['fields'].get('primary_industry',{}).get('value')
            if sector is not None and sector not in industries:
                selected.append(dict(id=row['entity_id'],symbol=row['symbol'],industry=sector));industries.add(sector)
            if len(selected)==5:break
        if len(selected)!=5:raise ValueError('CROSS_INDUSTRY_SAMPLE_UNAVAILABLE')
        for day in catalog:
            for route in ('home','stocks','sectors','focus','events','forward'):
                status,data,size,seconds=get('/api/v4/'+route,dict(context_token=api.token,trade_date=day,limit=20))
                if status!=200:raise ValueError('PRODUCT_ROUTE_FAILED:'+str((day,route,status,data)))
                routes.append(dict(T0=day,route=route,code=status,status=data.get('status'),bytes=size,seconds=seconds))
            for stock in selected:
                for period in ('D','W','M'):
                    for basis in ('RAW','QFQ'):
                        for offset,limit in ((0,20),(20,20),(0,120)):
                            q=dict(context_token=api.token,trade_date=day,period=period,price_basis=basis,offset=offset,limit=limit)
                            path='/api/v4/stocks/'+quote(stock['id'],safe='')+'/chart'
                            status,data,size,seconds=get(path,q)
                            missing=period!='D' and ('period_raw' if basis=='RAW' else 'period_adjusted') not in api.candidate['owners'][day]
                            if status!=200 or data.get('production_accepted') is not False:raise ValueError('DEFAULT_CHART_FAILED:'+str((status,data)))
                            if missing:
                                if data.get('status')!='SOURCE_INCOMPLETE':raise ValueError('MISSING_PERIOD_OWNER_HIDDEN')
                            elif data.get('status')!='READY' or data['series_index']['engine']!='postgresql' or any(x['trade_date']>day for x in data['items']):raise ValueError('DEFAULT_CHART_DATA_INVALID')
                            results.append(dict(security_id=stock['id'],query={k:v for k,v in q.items() if k!='context_token'},code=status,status=data['status'],items=data['items'],total=data['total'],bytes=size,seconds=seconds))
        negative=[];day=base['T0'];stock=selected[0];path='/api/v4/stocks/'+stock['id']+'/chart'
        for change,expected in [({'context_token':'wrong'},409),({'period':'Y'},400),({'limit':201},400),({'offset':-1},400),({'trade_date':'2026-10-12'},400)]:
            status,data,_,_=get(path,dict(context_token=api.token,trade_date=day,**{})|change)
            if status!=expected:raise ValueError('DEFAULT_NEGATIVE_MISMATCH:'+str((change,status,data)))
            negative.append(dict(change=change,code=status,body=data))
        measurements=[]
        for workers in (1,4,8):
            q=dict(context_token=api.token,trade_date=day,period='D',price_basis='QFQ',limit=120)
            with ThreadPoolExecutor(max_workers=workers) as pool:responses=list(pool.map(lambda _:get(path,q),range(workers*2)))
            if any(r[0]!=200 or r[1]['context']['context_token']!=api.token for r in responses):raise ValueError('CONCURRENT_CONTEXT_MISMATCH')
            times=sorted(r[3] for r in responses);measurements.append(dict(concurrency=workers,requests=len(times),p95_seconds=times[min(len(times)-1,int(.95*len(times)))],capacity_acceptance='OPEN_NO_APPROVED_THRESHOLD'))
        code=0
        write(OUT/'DEFAULT_FIVE_DATES_RESULT.json',dict(contract_id='R4_DEFAULT_FIVE_DATE_HTTP_R2',current_status='SCOPED_DEFAULT_CATALOG_HTTP_PASS',denominator=dict(dates=5,stocks=5,industries=5,charts=len(results),product_routes=len(routes)),samples=selected,results=results,product_routes=routes,negative_vectors=negative,concurrency=measurements,constructor_history_injection=False,production_changed=False,limitations=['Period-owner gaps preserved','Cross-industry sample only, not whole stock universe','No capacity threshold/production admission','Earlier-date catalogue only confers CHART_HISTORY; market facts remain unbound']))
        print(json.dumps(dict(charts=len(results),routes=len(routes),states={s:sum(x['status']==s for x in results) for s in ('READY','SOURCE_INCOMPLETE')},negative=len(negative),port=server.server_port)),flush=True)
    finally:
        temporary=authority_path.with_suffix('.tmp');temporary.write_bytes(before);os.replace(temporary,authority_path)
        if server:server.shutdown();server.server_close()
        if thread:thread.join(2)
        if jobs:jobs.close()
        guard.pytest_sessionfinish(None,code);guard.pytest_unconfigure(config)


if __name__=='__main__':main()
