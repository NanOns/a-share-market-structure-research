"""Normal restart product adapter; retains daily-operation gates and frozen readers."""
from pathlib import Path
from urllib.parse import urlparse,parse_qs
from http.server import ThreadingHTTPServer
import hashlib,json,threading
import psycopg
from .operational_daily_server_v1 import make_daily_handler, PREFIX
from .core_product_bff_r1 import CoreProductBFFR1, product_manifest_bindings
from workbench_analysis.operational_successor_v1 import accepted_api

def make_product_handler(root,jobs,*,isolated_history_authority=None):
    root=Path(root);base=make_daily_handler(root,jobs);lock=threading.RLock();cache={}
    class Handler(base):
        def send(self,status,body,content_type='application/json; charset=utf-8'):
            from .product_http_transport_r2 import encode
            raw,encoding=encode(body,content_type,self.headers.get('Accept-Encoding',''))
            return self.send_encoded(status,raw,encoding,content_type)
        def send_encoded(self,status,raw,encoding,content_type='application/json; charset=utf-8'):
            self.send_response(status)
            self.send_header('Content-Type',content_type)
            self.send_header('Content-Length',str(len(raw)))
            self.send_header('Cache-Control','no-store')
            self.send_header('Vary','Accept-Encoding')
            if encoding:self.send_header('Content-Encoding',encoding)
            self.end_headers();self.wfile.write(raw)
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
                        focus_authority=root/'config/core_product_focus_read_authority_r2.json'
                        owner_authority=root/'config/v4_operational_owner_pg_closeout_r1.json'
                        isolated_bytes=Path(isolated_history_authority).read_bytes() if isolated_history_authority is not None else b''
                        signature=hashlib.sha256(head.read_bytes()+(authority.read_bytes() if authority.exists() else b'')+(focus_authority.read_bytes() if focus_authority.exists() else b'')+(owner_authority.read_bytes() if owner_authority.exists() else b'')+isolated_bytes).hexdigest()
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
                            if owner_authority.exists():collect(json.loads(owner_authority.read_bytes()))
                            identity_head=root/'data/v4/V4_DATA_ACCEPTED_HEAD.json'
                            paths.add(identity_head);collect(json.loads(identity_head.read_bytes())['identity'])
                            collect(json.loads((root/api.candidate['registry']['path']).read_bytes()))
                            if authority.exists():
                                a=json.loads(authority.read_bytes());collect(a)
                                for binding in product_manifest_bindings(a):
                                    collect(json.loads((root/binding['path']).read_bytes()))
                            if focus_authority.exists():
                                a=json.loads(focus_authority.read_bytes());collect(a);collect(json.loads((root/a['manifest']['path']).read_bytes()))
                            cache.clear();cache.update(signature=signature,bff=CoreProductBFFR1(api,jobs,isolated_history_authority=isolated_history_authority),sources={p:(p.stat().st_size,p.stat().st_mtime_ns) for p in paths})
                        # A home response is derived entirely from this signed
                        # immutable Head and its verified source closure. Every
                        # request still passes the signature/change gate above.
                        # Cache bounded encoded variants, never mutable API state.
                        response_key=(signature,path,tuple(sorted((k,v[0]) for k,v in params.items())),self.headers.get('Accept-Encoding',''))
                        responses=cache.setdefault('home_encoded',{})
                        encoded=responses.get(response_key) if path=='/api/v4/home' else None
                        if encoded is not None:
                            # A disconnected/missing native database must not
                            # turn this optimization into an offline fallback.
                            from workbench_db.v4_native import configured_dsn
                            with psycopg.connect(configured_dsn(),connect_timeout=5) as pg:
                                pg.execute('SET TRANSACTION READ ONLY')
                                from workbench_db.v4_forward_pg_r1 import ForwardFactStore
                                if ForwardFactStore._database_identity(pg)!=cache['home_database_identity']:
                                    raise RuntimeError('PG_HOME_DATABASE_IDENTITY_MISMATCH')
                        if encoded is None:
                            code,data=cache['bff'].get(path,{k:v[0] for k,v in params.items()})
                            if path=='/api/v4/home' and code==200:
                                from workbench_db.v4_native import configured_dsn
                                from workbench_db.v4_forward_pg_r1 import ForwardFactStore
                                with psycopg.connect(configured_dsn(),connect_timeout=5) as pg:
                                    pg.execute('SET TRANSACTION READ ONLY')
                                    identity=ForwardFactStore._database_identity(pg)
                                prior_identity=cache.get('home_database_identity')
                                if prior_identity is not None and identity!=prior_identity:
                                    raise RuntimeError('PG_HOME_DATABASE_IDENTITY_MISMATCH')
                                cache['home_database_identity']=identity
                                from .product_http_transport_r2 import encode
                                raw,encoding=encode(data,'application/json; charset=utf-8',self.headers.get('Accept-Encoding',''))
                                encoded=(code,raw,encoding)
                                if len(responses)>=16:responses.pop(next(iter(responses)))
                                responses[response_key]=encoded
                    if encoded is not None:return self.send_encoded(*encoded)
                    return self.send(code,data)
                except (psycopg.Error,RuntimeError):
                    return self.send(503,dict(code='V4_PG_UNAVAILABLE',reason='PG_REQUIRED_NO_FALLBACK'))
                except (ValueError,KeyError,OSError) as exc:
                    return self.send(409 if str(exc)=='CONTEXT_TOKEN_MISMATCH' else 503 if 'SHA' in str(exc) or 'HASH' in str(exc) else 400,dict(code='PRODUCT_READ_FAILED',reason=str(exc)))
            return super().do_GET()
    return Handler

def serve_v4(root,host='127.0.0.1',port=28765):
    if host not in ('127.0.0.1','localhost'):raise ValueError('LOCAL_ONLY_PRODUCT_READER')
    from workbench_analysis.operational_daily_jobs_pg_r1 import DailyJobs
    from workbench_analysis.operational_daily_executor_v1 import execute_sources,probe_source_revision
    from workbench_analysis.operational_successor_release_v1 import recover
    recover(root)
    jobs=DailyJobs(root,executor=lambda day,mode:execute_sources(root,day,mode,cancelled=jobs.publication_cancelled,readback_url=f'http://127.0.0.1:{port}',progress=jobs.checkpoint),source_probe=probe_source_revision)
    server=ThreadingHTTPServer((host,port),make_product_handler(root,jobs));jobs.start()
    try:server.serve_forever()
    finally:jobs.close();server.server_close()
