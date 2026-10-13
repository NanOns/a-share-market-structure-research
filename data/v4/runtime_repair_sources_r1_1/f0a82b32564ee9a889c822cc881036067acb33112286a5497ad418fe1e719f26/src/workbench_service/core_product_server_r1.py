"""Normal restart product adapter; retains daily-operation gates and frozen readers."""
from pathlib import Path
from urllib.parse import urlparse,parse_qs
from http.server import ThreadingHTTPServer
import hashlib,json,threading,time,logging
from copy import copy
import psycopg
from .operational_daily_server_v1 import make_daily_handler, PREFIX
from .core_product_bff_r1 import CoreProductBFFR1, product_manifest_bindings
from workbench_analysis.operational_successor_v1 import accepted_api

def make_product_handler(root,jobs,*,isolated_history_authority=None):
    root=Path(root);base=make_daily_handler(root,jobs);lock=threading.RLock();published={}
    logger=logging.getLogger("v4.http.timing")
    flights={}
    def build(signature):
        authority=root/'config/core_product_read_authority_r1.json'
        focus_authority=root/'config/core_product_focus_read_authority_r2.json'
        owner_authority=root/'config/v4_operational_owner_pg_closeout_r1.json'
        api=accepted_api(root);paths=set()
        def collect(x):
            if isinstance(x,dict):
                if x.get('path') and x.get('sha256'):paths.add(root/x['path'])
                for v in x.values():collect(v)
            elif isinstance(x,list):
                for v in x:collect(v)
        collect(api.candidate);collect(api.snapshot)
        if api.candidate.get('native_membership_reference'):
            collect(json.loads((root/api.candidate['native_membership_reference']['path']).read_bytes()))
        from .native_product_catalog_v3 import KEY,load as load_catalog
        if KEY in api.candidate:
            catalog=load_catalog(root,api.candidate);collect(catalog)
            for binding in catalog['dates'].values():
                collect(json.loads((root/binding['path']).read_bytes()))
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
        cache=dict(signature=signature,bff=CoreProductBFFR1(api,jobs,isolated_history_authority=isolated_history_authority),sources={p:(p.stat().st_size,p.stat().st_mtime_ns) for p in paths})
        native=getattr(api,'pg_owner_authority',None)
        if native is not None:
            collect(native)
            cache['sources'].update({p:(p.stat().st_size,p.stat().st_mtime_ns) for p in paths})
            identities=[json.loads((root/binding['path']).read_bytes())['database_identity']
                        for owners in native['owners'].values() for entry in owners.values()
                        for binding in [entry['descriptor'] if getattr(api,'embedded_pg_owner_authority',False) else entry]]
            if not identities or any(value!=identities[0] for value in identities):
                raise RuntimeError('PG_OPERATIONAL_OWNER_DATABASE_IDENTITY_MISMATCH')
            cache['operational_database_identity']=identities[0]
        api=cache['bff'].api
        if api.candidate.get('exact_daily_adjustment_contract') and 'joint' not in cache:
            from .native_current_snapshot_v3 import current
            cache['joint']=current(root,api.candidate)
            collect(cache['joint'])
            if cache['joint']:
                policy=json.loads((root/api.candidate['release_policy']['path']).read_bytes())
                collect(policy)
                joint=json.loads((root/'config/v4_current_native_joint_authority_v3.json').read_bytes())
                collect(joint)
            cache['sources'].update({p:(p.stat().st_size,p.stat().st_mtime_ns) for p in paths})
        return cache

    def bind():
        nonlocal published
        # Expensive file/PG validation and construction run outside the pointer lock.
        signed=[root/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json',
                root/'config/core_product_read_authority_r1.json',
                root/'config/core_product_focus_read_authority_r2.json',
                root/'config/v4_operational_owner_pg_closeout_r1.json',
                root/'config/v4_read_index_authority_r1.json',
                root/'config/v4_current_native_joint_authority_v3.json']
        if isolated_history_authority is not None:signed.append(Path(isolated_history_authority))
        def signature():
            return hashlib.sha256(b''.join(p.read_bytes() if p.exists() else b'' for p in signed)).hexdigest()
        while True:
            token=signature();prior=published
            changed=any(not p.exists() or (p.stat().st_size,p.stat().st_mtime_ns)!=stat
                        for p,stat in prior.get('sources',{}).items())
            if token==prior.get('signature') and not changed:return prior
            with lock:
                flight=flights.get(token)
                leader=flight is None
                if leader:flight=threading.Event();flights[token]=flight
            if not leader:
                if not flight.wait(30):raise RuntimeError('PRODUCT_BIND_TIMEOUT')
                continue
            try:
                fresh=build(token)
                # Never install a generation assembled across a publication or source change.
                stable=signature()==token and all(p.exists() and
                    (p.stat().st_size,p.stat().st_mtime_ns)==stat for p,stat in fresh['sources'].items())
                if stable:
                    with lock:published=fresh
                    return fresh
            finally:
                with lock:flights.pop(token,None);flight.set()

    class Handler(base):
        PREFLIGHT_PRODUCT_CONTEXT=True
        def send(self,status,body,content_type='application/json; charset=utf-8'):
            from .product_http_transport_r2 import encode
            began=time.perf_counter()
            raw,encoding=encode(body,content_type,self.headers.get('Accept-Encoding',''))
            logger.info('path=%s encode_ms=%.3f bytes=%d',urlparse(self.path).path,(time.perf_counter()-began)*1000,len(raw))
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
                    started=time.perf_counter()
                    cache=bind();signature=cache['signature']
                    bound_at=time.perf_counter()
                    # Projected BFF and transport caches still depend on
                    # live native authority, including context-only reads.
                    if 'operational_database_identity' in cache:
                        from workbench_db.v4_native import configured_reader_dsn
                        from workbench_db.v4_forward_pg_r1 import ForwardFactStore
                        with psycopg.connect(configured_reader_dsn(),connect_timeout=5) as pg:
                            pg.execute('SET TRANSACTION READ ONLY')
                            if ForwardFactStore._database_identity(pg)!=cache['operational_database_identity']:
                                raise RuntimeError('PG_OPERATIONAL_OWNER_DATABASE_IDENTITY_MISMATCH')
                    # A home response is derived entirely from this signed
                    # immutable Head and its verified source closure. Every
                    # request still passes the signature/change gate above.
                    # Cache bounded encoded variants, never mutable API state.
                    # Each request owns its date snapshot/cache container. Immutable
                    # cached values may be shared; dated readers never share mutable state.
                    bff=copy(cache['bff']);api=copy(bff.api);api.cache=dict(getattr(api,"cache",{}));bff.api=api
                    if path!='/api/v4/context' and hasattr(api,'token') and params.get('context_token',[''])[0]!=api.token:
                        raise ValueError('CONTEXT_TOKEN_MISMATCH')
                    current_joint=cache.get('joint')
                    joint_token=hashlib.sha256(json.dumps(current_joint,sort_keys=True).encode()).hexdigest() if current_joint else None
                    response_key=(signature,joint_token,path,tuple(sorted((k,v[0]) for k,v in params.items())),self.headers.get('Accept-Encoding',''))
                    responses=cache.setdefault('home_encoded',{})
                    indexed=(root/'config/v4_read_index_authority_r1.json').is_file()
                    with lock:encoded=responses.get(response_key) if path=='/api/v4/home' and not indexed else None
                    if encoded is not None:
                        # A disconnected/missing native database must not
                        # turn this optimization into an offline fallback.
                        from workbench_db.v4_native import configured_reader_dsn
                        with psycopg.connect(configured_reader_dsn(),connect_timeout=5) as pg:
                            pg.execute('SET TRANSACTION READ ONLY')
                            from workbench_db.v4_forward_pg_r1 import ForwardFactStore
                            if ForwardFactStore._database_identity(pg)!=cache['home_database_identity']:
                                raise RuntimeError('PG_HOME_DATABASE_IDENTITY_MISMATCH')
                    if encoded is None:
                        code,data=bff.get(path,{k:v[0] for k,v in params.items()})
                        if current_joint is not None and code==200:
                            data['current_native_joint']=dict(contract_id=current_joint['contract_id'],T0=current_joint['T0'],business_token=current_joint['business_token'],snapshot=current_joint['snapshot'],full_product_release=current_joint['full_product_release'])
                        if path=='/api/v4/home' and code==200:
                            from workbench_db.v4_native import configured_reader_dsn
                            from workbench_db.v4_forward_pg_r1 import ForwardFactStore
                            with psycopg.connect(configured_reader_dsn(),connect_timeout=5) as pg:
                                pg.execute('SET TRANSACTION READ ONLY')
                                identity=ForwardFactStore._database_identity(pg)
                            prior_identity=cache.get('home_database_identity')
                            if prior_identity is not None and identity!=prior_identity:
                                raise RuntimeError('PG_HOME_DATABASE_IDENTITY_MISMATCH')
                            cache['home_database_identity']=identity
                            from .product_http_transport_r2 import encode
                            raw,encoding=encode(data,'application/json; charset=utf-8',self.headers.get('Accept-Encoding',''))
                            encoded=(code,raw,encoding)
                            if not indexed:
                                with lock:
                                    if len(responses)>=16:responses.pop(next(iter(responses)))
                                    responses[response_key]=encoded
                    logger.info('path=%s bind_ms=%.3f read_ms=%.3f',path,(bound_at-started)*1000,(time.perf_counter()-bound_at)*1000)
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
