"""Read-only actual current owners -> isolated PG index -> numeric/query parity.

Production is SELECT-only. Performance is an isolated reader benchmark, not
production deployment nor an actual daily derivation acceptance result.
"""
import concurrent.futures
import gzip
import hashlib
import json
import math
import os
from pathlib import Path
import statistics
import sys
import time
import threading
import subprocess
import urllib.request
from types import SimpleNamespace
from http.server import ThreadingHTTPServer,BaseHTTPRequestHandler

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
SOURCE=Path('G:/codex work/v4-production-20261012')
FIXTURE=Path('G:/codex_tmp/hotfix_api_real_20261013/index_fixture')
OUT=ROOT/'docs/audits/v4_runtime_repair_20261013'

def write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    raw=json.dumps(value,ensure_ascii=False,indent=2).encode()
    temporary=path.with_suffix(path.suffix+'.tmp');temporary.write_bytes(raw);os.replace(temporary,path)

def main():
    for k in ('TMP','TEMP','TMPDIR'):os.environ[k]='G:/codex_tmp'
    from scripts.v4_closeout_prepare_formal_pg_roles import load_credentials,ROLES
    from workbench_analysis.operational_successor_v1 import OperationalSuccessorReaderV1
    from workbench_service.core_product_bff_r1 import CoreProductBFFR1
    from workbench_db.v4_read_index_r1 import prepare,ReadIndex,summary
    from workbench_db.v4_native import configured_dsn
    import psycopg
    cache=FIXTURE/'REAL_PROJECTIONS.json.gz'
    head=(SOURCE/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json').read_bytes()
    token=hashlib.sha256(head).hexdigest();candidate=json.loads(head);day=candidate['accepted_trade_date']
    FIXTURE.mkdir(parents=True,exist_ok=True)
    if cache.exists():
        with gzip.open(cache,'rt',encoding='utf-8') as f:material=json.load(f)
        if material['head_token']!=token:raise ValueError('REAL_REFERENCE_HEAD_CHANGED')
    else:
        creds=load_credentials(SOURCE/'config/native_pg_roles.dpapi')
        os.environ['V4_NATIVE_PG_DSN']=creds[ROLES[0]]
        os.environ['V4_NATIVE_PG_READER_DSN']=creds[ROLES[0]]
        bff=CoreProductBFFR1(OperationalSuccessorReaderV1(SOURCE,candidate),None)
        bff.building_read_index=True
        start=time.perf_counter()
        collections={d:bff.project(d,day) for d in ('stocks','sectors','focus')}
        query=dict(trade_date=day,context_token=token)
        responses={p:bff.get(p,query)[1] for p in ('/api/v4/context','/api/v4/home')}
        focus=bff.get('/api/v4/focus',dict(query,limit='1'))[1]
        responses['/api/v4/focus-meta']={k:v for k,v in focus.items() if k not in ('context','context_token','production_accepted','items','total','offset','limit','has_next','status','domain','gap')}
        memberships={}
        for sector in bff.source('sector',day):
            for sid in set(sector['member_ids']):memberships.setdefault(sid,[]).append(sector['sector_id'])
        material=dict(head_token=token,T0=day,collections=collections,responses=responses,
                      memberships=memberships,source_projection_seconds=time.perf_counter()-start)
        with gzip.open(cache,'wt',encoding='utf-8') as f:json.dump(material,f,ensure_ascii=False)
        print('REAL_REFERENCE_FROZEN',flush=True)
    assert (SOURCE/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json').read_bytes()==head
    os.environ.pop('V4_NATIVE_PG_READER_DSN',None)
    os.environ['V4_NATIVE_PG_DSN']='host=127.0.0.1 port=55791 user=r4_isolated_admin dbname=postgres'
    with psycopg.connect(configured_dsn()) as pg:
        pg.execute('SET TRANSACTION READ ONLY')
        identity=pg.execute("SELECT system_identifier::text,current_setting('data_directory') FROM pg_control_system()").fetchone()
    if identity[0]!='7695278778933357404' or Path(identity[1]).resolve()!=Path('G:/codex_tmp/full_system_r4_fbd23a6b/pg_data').resolve():raise ValueError('ISOLATED_PG_REQUIRED')
    start=time.perf_counter()
    index_root=FIXTURE/'compact_lists_r1'
    binding=prepare(index_root,token,day,material['collections'],material['responses'],material['memberships'])
    reader=ReadIndex(index_root,binding,token,day)
    build_seconds=time.perf_counter()-start
    # Old in-memory page is an independent filtering/sort reference. Its exact
    # collection is frozen from formal PG through the old full projector once.
    class Oracle(CoreProductBFFR1):
        def project(self,domain,date):return material['collections'][domain]
        def envelope(self,date,**payload):return payload
        def identity_records(self):return [],None
    oracle=object.__new__(Oracle);oracle.building_read_index=True
    checks=[]
    for domain in ('stocks','sectors','focus'):
        sample=material['collections'][domain][0]
        queries=[{},dict(sort='name'),dict(sort='-close'),dict(sort='-rps20,id'),
                 dict(sort='state,-close'),dict(q=sample['symbol']),dict(q=sample['display_name']),
                 dict(offset=30,limit=30),dict(offset=len(material['collections'][domain]),limit=30),
                 dict(state='UNKNOWN'),dict(type='INDUSTRY'),dict(health='HEALTHY')]
        for q in queries:
            actual=reader.page(domain,q);expected=oracle.page(domain,day,q)
            if (actual['total'],actual['offset'],actual['has_next'],actual['items'])!=(expected['total'],expected['offset'],expected['has_next'],[summary(r,domain) for r in expected['items']]):raise ValueError('REAL_SQL_PAGE_PARITY:'+domain+':'+str(q))
            checks.append(dict(domain=domain,query=q,total=actual['total'],returned=len(actual['items'])))
    assert reader.response('/api/v4/home')==material['responses']['/api/v4/home']
    def sample_request(domain):
        began=time.perf_counter()
        payload=reader.response('/api/v4/'+domain) if domain in ('context','home') else reader.page(domain,{})
        raw=json.dumps(payload,ensure_ascii=False).encode()
        return time.perf_counter()-began,len(raw)
    performance={}
    for domain in ('context','stocks','sectors','focus','home'):
        values=[sample_request(domain) for _ in range(20)]
        durations=sorted(v[0] for v in values)
        performance[domain]=dict(samples=20,median_seconds=statistics.median(durations),p95_seconds=durations[math.ceil(.95*len(durations))-1],max_seconds=max(durations),bytes=values[-1][1])
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
        results=list(pool.map(sample_request,['context','stocks','sectors','focus','home']*4))
    # Real SQL and HTTP, isolated Head-loader fixture. No new source authority
    # is granted to the production Head by this engineering transport test.
    from workbench_db.v4_read_index_r1 import AUTHORITY,CONTRACT
    from workbench_service import core_product_server_r1 as server_module
    write(index_root/AUTHORITY,dict(contract_id=CONTRACT,versions={token:{day:binding}}))
    write(index_root/'registry.json',{})
    write(index_root/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json',{'engineering_fixture':True})
    write(index_root/'data/v4/V4_DATA_ACCEPTED_HEAD.json',{'identity':{}})
    api=SimpleNamespace(root=index_root,token=token,cache={},snapshot={},candidate=dict(
        registry={'path':'registry.json','sha256':hashlib.sha256((index_root/'registry.json').read_bytes()).hexdigest()},
        published_sessions=candidate['published_sessions'],accepted_trade_date=day))
    original=server_module.accepted_api;original_daily=server_module.make_daily_handler
    server_module.accepted_api=lambda root:api
    server_module.make_daily_handler=lambda *args:BaseHTTPRequestHandler
    server=ThreadingHTTPServer(('127.0.0.1',0),server_module.make_product_handler(index_root,None))
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
    def http_request(domain):
        began=time.perf_counter()
        req=urllib.request.Request('http://127.0.0.1:'+str(server.server_port)+'/api/v4/'+domain+'?context_token='+token,headers={'Accept-Encoding':'gzip'})
        with opener.open(req,timeout=10) as response:
            raw=response.read();encoding=response.headers.get('Content-Encoding')
        decoded=json.loads(gzip.decompress(raw) if encoding=='gzip' else raw)
        assert decoded['context_token']==token and decoded['context']['trade_date']==day
        return time.perf_counter()-began,len(raw)
    http={};worker=None
    try:
        for mode in ('IDLE','SEPARATE_CPU_PROCESS'):
            if mode!='IDLE':
                worker=subprocess.Popen([sys.executable,'-B','-c','while True: sum(i*i for i in range(1000000))'],
                    env=dict(os.environ,TMP='G:/codex_tmp',TEMP='G:/codex_tmp',TMPDIR='G:/codex_tmp'),
                    stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,
                    creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            observed={}
            for domain in ('context','stocks','sectors','focus','home'):
                measurements=[http_request(domain) for _ in range(20)]
                times=sorted(v[0] for v in measurements)
                observed[domain]=dict(samples=20,median_seconds=statistics.median(times),p95_seconds=times[18],max_seconds=max(times),gzip_bytes=measurements[-1][1])
            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
                parallel_measurements=list(pool.map(http_request,['context','stocks','sectors','focus','home']*4))
            observed['concurrent_5']=dict(samples=len(parallel_measurements),max_seconds=max(v[0] for v in parallel_measurements))
            http[mode]=observed
    finally:
        if worker is not None:worker.terminate();worker.wait(timeout=10)
        server.shutdown();server.server_close();thread.join();server_module.accepted_api=original;server_module.make_daily_handler=original_daily
    receipt=dict(contract_id='V4_READ_INDEX_REAL_PG_PARITY_R1',acceptance='PASS_ISOLATED_FULL_CURRENT_READ_MODEL',
        source_T0=day,source_head_token=token,source_counts={k:len(v) for k,v in material['collections'].items()},
        source_projection_seconds=material['source_projection_seconds'],isolated_index_build_seconds=build_seconds,
        reference_sha256=hashlib.sha256(cache.read_bytes()).hexdigest(),query_checks=checks,
        numeric_null_quality_and_summary_parity=True,home_full_response_parity=True,
        idle_read_and_encode=performance,concurrent_5=dict(samples=len(results),max_seconds=max(v[0] for v in results)),
        production_head_unchanged=(SOURCE/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json').read_bytes()==head,
        production_SOURCE_select_only=True,isolated_http=http,production_http_benchmark=False,actual_deriving_http_benchmark=False,
        EXE_packaged=False,isolated_database_identity=identity[0])
    write(OUT/'READ_INDEX_REAL_PARITY.json',receipt)
    print(json.dumps({k:v for k,v in receipt.items() if k not in ('query_checks','reference_sha256')},ensure_ascii=False),flush=True)

if __name__=='__main__':main()
