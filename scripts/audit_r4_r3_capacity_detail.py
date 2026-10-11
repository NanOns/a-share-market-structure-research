"""Two-T0 normal product workloads and safety-validation cost, engineering only."""
import gzip,hashlib,json,os,sys,threading,time,uuid
from pathlib import Path
from http.server import ThreadingHTTPServer
from urllib.request import Request,urlopen
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
OUT=ROOT/'docs/audits/r4_r3_integration_20261011'

def main():
    import psutil
    from tests import v4_native_isolation_plugin_r4 as guard
    from scripts.r4_readonly_source_guard import install
    install(['G:/codex work/大A交易','D:/new_tdx','G:/codex_tmp/test_temp/r4_batch2_default_product'])
    name='CAPACITY_DETAIL_'+uuid.uuid4().hex[:8]
    os.environ['R4_CONNECTION_LEDGER']=str(OUT/(name+'_INTENTS.jsonl'))
    config=SimpleNamespace();guard.pytest_configure(config);guard.ACTIVE=name
    from workbench_service.core_product_server_r1 import make_product_handler
    from workbench_analysis.operational_daily_jobs_pg_r1 import DailyJobs
    root=Path('G:/codex_tmp/r4_r3_ui_candidate');jobs=DailyJobs(root)
    source_paths=[ROOT/'src/workbench_service'/p for p in ('core_product_server_r1.py','core_product_bff_r1.py','product_http_transport_r2.py','operational_successor_bff_v1.py','r43_operational_bff.py','production_v4.py')]
    sources={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in source_paths}
    process=psutil.Process();rss=[process.memory_info().rss];stop=threading.Event()
    def sample():
        while not stop.wait(.1):rss.append(process.memory_info().rss)
    monitor=threading.Thread(target=sample,daemon=True);monitor.start();rows=[]
    def get(base,path):
        start=time.perf_counter()
        print(json.dumps(dict(phase='HTTP_REQUEST_BEGIN',path=path,elapsed_monotonic=start)),flush=True)
        with urlopen(Request(base+path,headers={'Accept-Encoding':'gzip'}),timeout=180) as response:
            raw=response.read();data=gzip.decompress(raw) if response.headers.get('Content-Encoding')=='gzip' else raw
        return dict(seconds=time.perf_counter()-start,bytes=len(raw),decoded_bytes=len(data),sha256=hashlib.sha256(data).hexdigest()),json.loads(data)
    try:
        for day in ('2026-09-29','2026-10-09'):
            server=ThreadingHTTPServer(('127.0.0.1',0),make_product_handler(root,jobs));thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
            base=f'http://127.0.0.1:{server.server_port}'
            try:
                cold,ctx=get(base,'/api/v4/context?trade_date='+day)
                path='/api/v4/home?trade_date='+day+'&context_token='+ctx['context_token']
                first,_=get(base,path);hot,_=get(base,path)
                if first['sha256']!=hot['sha256']:raise ValueError('COLD_HOT_FULL_PAYLOAD_DIFFERENCE')
                concurrent=[]
                for n in (1,4,8):
                    begin=time.perf_counter()
                    with ThreadPoolExecutor(max_workers=n) as pool:results=list(pool.map(lambda _:get(base,path)[0],range(2*n)))
                    ordered=sorted(r['seconds'] for r in results)
                    if any(r['sha256']!=first['sha256'] for r in results):raise ValueError('CONCURRENT_FULL_PAYLOAD_DIFFERENCE')
                    concurrent.append(dict(workers=n,requests=len(results),p95_seconds=ordered[min(len(ordered)-1,int(.95*len(ordered)))],throughput=len(results)/(time.perf_counter()-begin)))
                rows.append(dict(T0=day,token=ctx['context_token'],fresh_handler_context=cold,first_home=first,hot_home=hot,concurrency=concurrent))
                (OUT/(name+'_PARTIAL.json')).write_text(json.dumps(dict(status='INTERMEDIATE_NOT_FINAL',rows=rows,source_sha256=sources,rss_peak_bytes=max(rss)),indent=2),encoding='utf8')
            finally:server.shutdown();server.server_close();thread.join(2)
        # Reuse the exact production content verifier, with all row/hash checks.
        from workbench_service.production_v4 import ProductionV4ResearchReader
        from workbench_service.joint_release import AUTHORITY
        # The workload root serves operational owners; its old 09-30 snapshot
        # pointer is not their database. Measure the actual published R2 snapshot
        # separately, with its own explicit engineering authority and root.
        snapshot_root=Path('G:/codex_tmp/r4_r3_pg_publication_v2')
        authority=json.loads((snapshot_root/AUTHORITY).read_bytes())
        begin=time.perf_counter();reader=ProductionV4ResearchReader(snapshot_root,snapshot_authority=authority['snapshot'])
        from workbench_db.v4_snapshot_pg_r2 import read
        with read(reader.pg_descriptor):pass
        verification=dict(seconds=time.perf_counter()-begin,root=str(snapshot_root),release_id=reader.manifest['release_id'],database=reader.manifest['database'],scope='Separately published 09-30 native R2 snapshot: complete constructor and read verification; distinct from two-T0 operational-owner workload')
        if sources!={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in source_paths}:raise ValueError('SOURCE_CHANGED_DURING_RUN')
        result=dict(contract_id='R4_R3_TWO_T0_CAPACITY_DETAILS',rows=rows,snapshot_verification=verification,rss_initial_bytes=rss[0],rss_peak_bytes=max(rss),source_sha256=sources,capacity_acceptance='OPEN_NO_APPROVED_THRESHOLD',status='SCOPED_CONTENT_ORACLE_PASS',limits=['Fresh handler is measured; OS/PG cache is not purged and is not claimed cold','Concurrent shared-host engineering workload; no capacity threshold approved'])
        (OUT/(name+'_RESULT.json')).write_text(json.dumps(result,indent=2),encoding='utf8');print(json.dumps(dict(evidence=name,status=result['status'],rss_peak=max(rss))))
    except BaseException as exc:
        (OUT/(name+'_FAILURE.json')).write_text(json.dumps(dict(status='ENGINEERING_FAIL',error_type=type(exc).__name__,error=str(exc),completed_rows=rows,source_sha256=sources,rss_peak_bytes=max(rss),capacity_acceptance='OPEN'),indent=2),encoding='utf8')
        raise
    finally:
        stop.set();monitor.join(2);jobs.close();guard.pytest_sessionfinish(None,0);guard.pytest_unconfigure(config)

if __name__=='__main__':main()
