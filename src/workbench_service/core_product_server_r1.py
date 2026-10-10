"""Normal restart product adapter; retains daily-operation gates and frozen readers."""
from pathlib import Path
from urllib.parse import urlparse,parse_qs
from http.server import ThreadingHTTPServer
import hashlib,json,threading
from .operational_daily_server_v1 import make_daily_handler, PREFIX
from .core_product_bff_r1 import CoreProductBFFR1
from workbench_analysis.operational_successor_v1 import accepted_api

def make_product_handler(root,jobs):
    root=Path(root);base=make_daily_handler(root,jobs);lock=threading.RLock();cache={}
    class Handler(base):
        def do_GET(self):
            parsed=urlparse(self.path);path=parsed.path
            if path.startswith('/v4/assets/'):
                name=path.rsplit('/',1)[-1]
                if name in ('app.js','api.js','components.js','stock.js','replay.js','labels.js'):
                    asset=root/'src/workbench_service/static/core-product-r1'/name
                    return self.send(200,asset.read_bytes(),'application/javascript; charset=utf-8')
            if path.startswith('/api/v4/') and not path.startswith((PREFIX,'/api/v4/original-0930/','/api/v4/shadow/')):
                try:
                    params=parse_qs(parsed.query,keep_blank_values=True)
                    if any(len(v)!=1 for v in params.values()):raise ValueError('DUPLICATE_PARAMETER')
                    with lock:
                        head=root/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json'
                        authority=root/'config/core_product_read_authority_r1.json'
                        signature=hashlib.sha256(head.read_bytes()+(authority.read_bytes() if authority.exists() else b'')).hexdigest()
                        changed=any(not p.exists() or (p.stat().st_size,p.stat().st_mtime_ns)!=stat for p,stat in cache.get('sources',{}).items())
                        if signature!=cache.get('signature') or changed:
                            api=accepted_api(root);paths=set()
                            def collect(x):
                                if isinstance(x,dict):
                                    if x.get('path') and x.get('sha256'):paths.add(root/x['path'])
                                    for v in x.values():collect(v)
                                elif isinstance(x,list):
                                    for v in x:collect(v)
                            collect(api.candidate);collect(api.snapshot)
                            collect(json.loads((root/api.candidate['registry']['path']).read_bytes()))
                            if authority.exists():
                                a=json.loads(authority.read_bytes());collect(a);collect(json.loads((root/a['manifest']['path']).read_bytes()))
                            cache.clear();cache.update(signature=signature,bff=CoreProductBFFR1(api,None),sources={p:(p.stat().st_size,p.stat().st_mtime_ns) for p in paths})
                        code,data=cache['bff'].get(path,{k:v[0] for k,v in params.items()})
                    return self.send(code,data)
                except (ValueError,KeyError,OSError) as exc:
                    return self.send(409 if str(exc)=='CONTEXT_TOKEN_MISMATCH' else 503 if 'SHA' in str(exc) or 'HASH' in str(exc) else 400,dict(code='PRODUCT_READ_FAILED',reason=str(exc)))
            return super().do_GET()
    return Handler

def serve_v4(root,host='127.0.0.1',port=28765):
    if host not in ('127.0.0.1','localhost'):raise ValueError('LOCAL_ONLY_PRODUCT_READER')
    from workbench_analysis.operational_daily_jobs_v1 import DailyJobs
    from workbench_analysis.operational_daily_executor_v1 import execute_sources,probe_source_revision
    from workbench_analysis.operational_successor_release_v1 import recover
    recover(root)
    jobs=DailyJobs(root,executor=lambda day,mode:execute_sources(root,day,mode,cancelled=jobs.publication_cancelled,readback_url=f'http://127.0.0.1:{port}',progress=jobs.checkpoint),source_probe=probe_source_revision)
    server=ThreadingHTTPServer((host,port),make_product_handler(root,jobs));jobs.start()
    try:server.serve_forever()
    finally:jobs.close();server.server_close()
