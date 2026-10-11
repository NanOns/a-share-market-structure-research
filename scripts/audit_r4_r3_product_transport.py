"""Actual default HTTP lossless transport oracle with bounded concurrency."""
import gzip,hashlib,json,os,sys,threading,time
from pathlib import Path
from http.server import ThreadingHTTPServer
from urllib.request import Request,urlopen
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
OUT=ROOT/'docs/audits/r4_r3_integration_20261011'
SOURCE_PATHS=('src/workbench_service/core_product_server_r1.py','src/workbench_service/product_http_transport_r2.py','src/workbench_service/core_product_bff_r1.py')
def main():
    from tests import v4_native_isolation_plugin_r4 as guard
    from scripts.r4_readonly_source_guard import install
    install(['G:/codex work/大A交易','D:/new_tdx','G:/codex_tmp/test_temp/r4_batch2_default_product'])
    prefix=os.environ.get('R4_TRANSPORT_PREFIX','TRANSPORT_ACTUAL')
    sources={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCE_PATHS}
    os.environ['R4_CONNECTION_LEDGER']=str(OUT/(prefix+'_CONNECTIONS.jsonl'))
    config=SimpleNamespace();guard.pytest_configure(config);guard.ACTIVE='DEFAULT_HTTP_TRANSPORT_R3'
    from workbench_service.core_product_server_r1 import make_product_handler
    from workbench_analysis.operational_daily_jobs_pg_r1 import DailyJobs
    candidate=Path('G:/codex_tmp/r4_r3_ui_candidate');jobs=DailyJobs(candidate)
    server=ThreadingHTTPServer(('127.0.0.1',0),make_product_handler(candidate,jobs));thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    base=f'http://127.0.0.1:{server.server_port}'
    def get(path,encoding):
        begin=time.perf_counter()
        with urlopen(Request(base+path,headers={'Accept-Encoding':encoding}),timeout=120) as response:
            raw=response.read();codec=response.headers.get('Content-Encoding');data=gzip.decompress(raw) if codec=='gzip' else raw
            return dict(code=response.status,codec=codec,bytes=len(raw),decoded_sha256=hashlib.sha256(data).hexdigest(),decoded_bytes=len(data),seconds=time.perf_counter()-begin,vary=response.headers.get('Vary')),json.loads(data)
    rows=[]
    try:
        _,context=get('/api/v4/context?trade_date=2026-10-09','identity');token=context['context_token']
        for route in ('home','stocks','sectors','focus','events','forward'):
            path=f'/api/v4/{route}?trade_date=2026-10-09&context_token={token}&limit=20'
            plain,_=get(path,'identity');compressed,_=get(path,'gzip')
            if plain['decoded_sha256']!=compressed['decoded_sha256']:raise ValueError('LOSSLESS_HTTP_ORACLE_DIFF')
            rows.append(dict(route=route,identity=plain,gzip=compressed,equal=True))
        workloads=[]
        for workers in (1,4,8):
            start=time.perf_counter()
            path=f'/api/v4/home?trade_date=2026-10-09&context_token={token}'
            with ThreadPoolExecutor(max_workers=workers) as pool:results=list(pool.map(lambda _:get(path,'gzip')[0],range(workers*2)))
            times=sorted(x['seconds'] for x in results)
            workloads.append(dict(workers=workers,requests=len(results),p95_seconds=times[min(len(times)-1,int(.95*len(times)))],throughput=len(results)/(time.perf_counter()-start),hashes=sorted(set(x['decoded_sha256'] for x in results))))
        if sources!={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCE_PATHS}:raise ValueError('EXECUTED_SOURCE_CHANGED_DURING_RUN')
        result=dict(contract_id='V4_R3_DEFAULT_HTTP_TRANSPORT_ORACLE_R1',source_bindings=sources,rows=rows,concurrency=workloads,status='SCOPED_LOSSLESS_PASS',capacity_acceptance='OPEN_NO_APPROVED_THRESHOLD',limits=['Single frozen T0 workload; retained snapshot lock and all safety checks; compression does not fix cold computation cost'])
        if prefix!='TRANSPORT_ACTUAL':
            before=json.loads((OUT/'TRANSPORT_ACTUAL_ORACLE.json').read_bytes())
            expected={r['route']:r['identity']['decoded_sha256'] for r in before['rows']}
            result['before_after_full_payload_equal']=all(r['identity']['decoded_sha256']==expected[r['route']] for r in rows)
            if not result['before_after_full_payload_equal']:raise ValueError('HOME_OPTIMIZATION_FULL_PAYLOAD_ORACLE_DIFF')
        path=OUT/(prefix+'_ORACLE.json');tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8');os.replace(tmp,path)
        print(json.dumps(dict(routes=len(rows),workloads=workloads)))
    finally:
        server.shutdown();server.server_close();jobs.close();thread.join(2);guard.pytest_sessionfinish(None,0);guard.pytest_unconfigure(config)
if __name__=='__main__':main()
