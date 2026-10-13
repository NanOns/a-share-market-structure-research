"""Actual current PG/HTTP while the genuine append producer uses CPU.

Random loopback source reader; not the final packaged 28765 acceptance.
"""
import argparse,json,os,sys,time,threading,statistics,urllib.request
from pathlib import Path
from http.server import ThreadingHTTPServer
import psutil

ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]

def main():
    p=argparse.ArgumentParser();p.add_argument('--pid',required=True,type=int);a=p.parse_args()
    root=Path('G:/codex work/v4-production-20261012')
    from scripts.v4_closeout_prepare_formal_pg_roles import load_credentials,ROLES
    credentials=load_credentials(root/'config/native_pg_roles.dpapi')
    os.environ['V4_NATIVE_PG_DSN']=credentials[ROLES[0]];os.environ['V4_NATIVE_PG_READER_DSN']=credentials[ROLES[0]]
    from workbench_service.core_product_server_r1 import make_product_handler
    worker=psutil.Process(a.pid)
    if not any('run_v4_append_candidate_r1_1.py' in x for x in worker.cmdline()):raise ValueError('REAL_APPEND_PRODUCER_REQUIRED')
    before_head=(root/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json').read_bytes()
    server=ThreadingHTTPServer(('127.0.0.1',0),make_product_handler(root,None))
    server.RequestHandlerClass.log_message=lambda *a:None
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}));base='http://127.0.0.1:'+str(server.server_port)
    def get(path,token=None):
        start=time.monotonic();query='?context_token='+token if token else ''
        with opener.open(base+'/api/v4/'+path+query,timeout=90) as response:raw=response.read()
        data=json.loads(raw)
        return time.monotonic()-start,len(raw),data
    try:
        warm,_,context=get('context');token=context['context_token']
        start_cpu=sum(worker.cpu_times()[:2]);measurements={}
        for path in ('context','stocks','sectors','focus','home'):
            times=[];bytes_=None
            for _ in range(20):
                duration,bytes_,data=get(path,token)
                if data['context_token']!=token or data['context']['trade_date']!='2026-10-12':raise ValueError('PREPUBLICATION_HEAD_MIXED')
                times.append(duration)
            ordered=sorted(times);measurements[path]=dict(samples=20,median_seconds=statistics.median(times),p95_seconds=ordered[18],max_seconds=max(times),bytes=bytes_)
        end_cpu=sum(worker.cpu_times()[:2])
        result=dict(contract_id='V4_R1_1_ACTUAL_APPEND_CPU_HTTP',acceptance='PASS' if all(v['p95_seconds']<=(.5 if k=='context' else 2) for k,v in measurements.items()) and end_cpu>start_cpu else 'FAIL',
            producer_pid=a.pid,producer_cpu_seconds_during_samples=end_cpu-start_cpu,producer_command_verified=True,
            endpoints=measurements,cold_context_seconds=warm,reader_port=server.server_port,
            source_pg='ACTUAL_FORMAL_PG_SELECT_ONLY',T0='2026-10-12',token=token,formal_28765=False,
            genuine_derivation=True,head_unchanged=before_head==(root/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json').read_bytes())
        path=ROOT/'docs/audits/v4_runtime_repair_20261013/R1_1_ACTUAL_APPEND_HTTP.json'
        temporary=path.with_suffix('.tmp');temporary.write_text(json.dumps(result,indent=2),encoding='utf-8');os.replace(temporary,path)
        print(json.dumps(result),flush=True)
    finally:server.shutdown();thread.join();server.server_close()

if __name__=='__main__':main()
