"""Explicit engineering-only shadow publication and real loopback HTTP readback."""
import argparse,json,os,sys,threading,time,hashlib,statistics
from pathlib import Path
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from urllib.parse import urlparse,parse_qs,urlencode
from urllib.request import urlopen
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]

def binding(root,path):
    path=Path(path).resolve();raw=path.read_bytes()
    if not path.is_relative_to(root):raise ValueError('SOURCE_BINDING_OUTSIDE_FORMAL_ROOT')
    return dict(path=path.relative_to(root).as_posix(),sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))

def handler(root,shadow):
    from workbench_analysis.operational_successor_v1 import OperationalSuccessorReaderV1,validate,digest
    from workbench_service.core_product_bff_r1 import CoreProductBFFR1
    from copy import copy
    lock=threading.Lock();generations={};inflight={}
    head=shadow/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json'
    def generation():
        raw=head.read_bytes();signature=hashlib.sha256(raw).hexdigest()
        with lock:
            cached=generations.get(signature)
            if cached is not None:return cached
            event=inflight.get(signature);builder=event is None
            if builder:event=threading.Event();inflight[signature]=event
        if not builder:
            if not event.wait(120):raise TimeoutError('ENGINEERING_READER_BUILD_TIMEOUT')
            with lock:
                cached=generations.get(signature)
            if cached is None:raise ValueError('ENGINEERING_READER_BUILD_FAILED')
            return cached
        try:
            candidate=json.loads(raw)
            api=OperationalSuccessorReaderV1(root,candidate)
            bff=CoreProductBFFR1(api,NoLegacy())
            cached=(candidate,bff)
            with lock:
                if len(generations)>=2:generations.pop(next(iter(generations)))
                generations[signature]=cached
            return cached
        finally:
            with lock:inflight.pop(signature,None);event.set()
    class NoLegacy:
        def __getattr__(self,name):raise ValueError('ENGINEERING_LEGACY_READ_FORBIDDEN')
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def send(self,code,data):
            raw=json.dumps(data,ensure_ascii=False).encode();self.send_response(code);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
        def do_POST(self):self.send(405,dict(code='ENGINEERING_READ_ONLY'))
        do_PUT=do_DELETE=do_POST
        def do_GET(self):
            try:
                parsed=urlparse(self.path);query=parse_qs(parsed.query)
                if any(len(v)!=1 for v in query.values()):raise ValueError('DUPLICATE_PARAMETER')
                # One immutable candidate per request; no live mutable API cache.
                candidate,shared=generation()
                bff=copy(shared);api=copy(shared.api)
                api.cache=dict(shared.api.cache);api.snapshot=dict(shared.api.snapshot)
                bff.api=api
                if parsed.path=='/api/v4/operations/daily-update/progress':
                    return self.send(200,dict(contract_id='V4_ENGINEERING_SHADOW_PROGRESS_R11',stage_state='ENGINEERING_SHADOW_ONLY',target_trade_date=candidate['accepted_trade_date'],context_token=api.token,production_job_mutated=False))
                code,data=bff.get(parsed.path,{k:v[0] for k,v in query.items()})
                data['production_accepted']=False;data['engineering_scope']='SHADOW_POINTER_FORMAL_SOURCES_READ_ONLY'
                self.send(code,data)
            except Exception as exc:self.send(503,dict(code='ENGINEERING_SHADOW_READ_FAILED',reason=str(exc)[:300]))
    return Handler

def readback(base,candidate,samples,*,wrong_token=False):
    from workbench_analysis.operational_successor_v1 import digest
    token=digest(candidate);day=candidate['accepted_trade_date'];results=[]
    paths=['/api/v4/context','/api/v4/stocks','/api/v4/sectors','/api/v4/focus','/api/v4/home','/api/v4/market','/api/v4/stocks/SZ.301660/chart']
    for path in paths:
        query=dict(context_token=token,trade_date=day,limit=30)
        timings=[];sizes=[]
        for _ in range(samples):
            started=time.perf_counter()
            with urlopen(base+path+'?'+urlencode(query),timeout=30) as response:raw=response.read()
            data=json.loads(raw);timings.append(time.perf_counter()-started);sizes.append(len(raw))
            if data.get('context_token')!=token or data.get('context',{}).get('trade_date')!=day:raise ValueError('HTTP_SAME_TOKEN_READBACK_FAILED:'+path)
        timings.sort();results.append(dict(path=path,status='PASS',median_seconds=statistics.median(timings),p95_seconds=timings[min(len(timings)-1,int(.95*len(timings)))],max_seconds=max(timings),bytes=max(sizes)))
    return dict(status='PASS',accepted_trade_date=day,context_token='deliberately_wrong' if wrong_token else token,checks=results)

def main():
    p=argparse.ArgumentParser();p.add_argument('--candidate',required=True);p.add_argument('--g123',required=True);p.add_argument('--shadow-root',required=True);p.add_argument('--roles',required=True);p.add_argument('--rootformal',required=True);p.add_argument('--samples',type=int,default=20);p.add_argument('--mode',choices=['failure','success','measure'],required=True);a=p.parse_args()
    os.environ.update(TMP='G:/codex_tmp',TEMP='G:/codex_tmp',TMPDIR='G:/codex_tmp',R4_NATIVE_ISOLATION='1',PYTHONDONTWRITEBYTECODE='1')
    root=Path(a.rootformal).resolve();shadow=Path(a.shadow_root).resolve()
    if not shadow.is_relative_to(Path('G:/codex_tmp').resolve()) or not 1<=a.samples<=30:raise ValueError('ENGINEERING_SHADOW_SCOPE_REQUIRED')
    from scripts.v4_closeout_prepare_formal_pg_roles import load_credentials,ROLES
    secrets=load_credentials(a.roles);os.environ['V4_NATIVE_PG_DSN']=secrets[ROLES[1]];os.environ['V4_NATIVE_PG_READER_DSN']=secrets[ROLES[0]]
    from workbench_analysis.operational_successor_release_v1 import engineering_shadow_promote
    from workbench_analysis.operational_daily_storage_v1 import atomic_json
    candidate=json.loads(Path(a.candidate).read_bytes());g123=binding(root,a.g123)
    head=shadow/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json'
    if not head.exists():
        from workbench_service.v4_daily_refresh import atomic_bytes
        atomic_bytes(head,(root/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json').read_bytes())
    protected={p:p.read_bytes() for p in [root/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json',root/'config/v4_current_native_joint_authority_v3.json']}
    server=ThreadingHTTPServer(('127.0.0.1',0),handler(root,shadow));thread=threading.Thread(target=server.serve_forever);thread.start();base=f'http://127.0.0.1:{server.server_port}'
    before=head.read_bytes()
    try:
        if a.mode=='measure':result=readback(base,json.loads(before),a.samples)
        else:
            try:result=engineering_shadow_promote(root,candidate,hashlib.sha256(before).hexdigest(),lambda c:readback(base,c,a.samples,wrong_token=a.mode=='failure'),shadow_root=shadow,evidence_binding=g123)
            except ValueError as exc:
                if a.mode!='failure' or str(exc)!='HTTP_SAME_TOKEN_READBACK_FAILED':raise
                if head.read_bytes()!=before:raise ValueError('SHADOW_ROLLBACK_FAILED')
                result=dict(status='ENGINEERING_SHADOW_FAILURE_ROLLBACK_PASS',error=str(exc))
        if any(p.read_bytes()!=raw for p,raw in protected.items()):raise ValueError('FORMAL_POINTER_CHANGED')
        atomic_json(shadow,shadow/(a.mode+'_RESULT.json'),dict(result,formal_pointers_unchanged=True,production_acceptance=False))
        print(json.dumps(dict(status=result['status'],port=server.server_port,formal_pointers_unchanged=True)))
    finally:server.shutdown();thread.join();server.server_close()
if __name__=='__main__':main()
