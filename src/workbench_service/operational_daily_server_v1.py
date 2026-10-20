"""Daily-operation service wrapper; frozen V2 control adapter remains valid."""
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse,parse_qs
from collections import deque
import json,os,threading,time
import psycopg
from .v4_server import make_v4_handler
from workbench_analysis.operational_daily_jobs_pg_r1 import DailyJobs
from workbench_analysis.operational_daily_executor_v1 import execute_sources

PREFIX='/api/v4/operations/daily-update'


def _local_successor_source_paths(root,candidate):
    """Extract bounded local source paths for diagnostics, never cache authority."""
    root=Path(root).resolve();paths=set()
    def visit(value):
        if isinstance(value,dict):
            if value.get('path') and value.get('sha256') and not value.get('pg_descriptor'):
                path=(root/value['path']).resolve()
                if path.is_relative_to(root):paths.add(path)
            for child in value.values():visit(child)
        elif isinstance(value,list):
            for child in value:visit(child)
    visit(candidate)
    return paths


def successor_control(api,legacy):
    from .operational_control_status import control_status
    current=api.context();current['authorization_mode']='DIRECT_HUMAN_USER'
    # The PG current endpoint returns a projection payload with ``context``;
    # the frozen control adapter expects the legacy reader envelope. Normalize
    # both shapes at this boundary so status never silently falls back to an
    # empty context or a file-backed reader.
    legacy_context=legacy.get('context',legacy) if isinstance(legacy,dict) else {}
    legacy_payload={
        'context':legacy_context,
        'context_token':legacy_context.get('context_token',legacy_context.get('publication_id','')),
        'production_permission':legacy.get('production_permission',{}) if isinstance(legacy,dict) else {},
    }
    control=control_status(legacy_payload,current,api.context_digest)
    control['data_updated_at']=api.candidate['observed_at']
    return dict(control,context=current)


def make_daily_handler(root,jobs,*,static_root=None,status_reader=None):
    root=Path(root);static=Path(static_root) if static_root is not None else root/'src/workbench_service/static'
    from workbench_db.v4_native import workspace_schema
    from .v4_server import pg_candidate_adapter_from_environment
    pg_adapter=pg_candidate_adapter_from_environment(workspace_root=root)
    base=make_v4_handler(root,pg_adapter,allow_pg_candidate=True,
        pg_candidate_release_id=os.environ.get('V4_PG_RESEARCH_CANDIDATE_RELEASE_ID'),static_root=static);writes={};mutex=threading.Lock()
    if status_reader is None:
        from workbench_analysis.operational_daily_jobs_pg_r1 import DailyJobsReadOnly
        status_reader=DailyJobsReadOnly(root)
    successor_cache={};successor_lock=threading.RLock()
    def successor_reader():
        from workbench_analysis.operational_successor_v1 import accepted_api
        # Re-resolve the exact PG Owner/registry facts on every request. Their
        # archival source paths are lineage only and are never stat'ed to
        # validate or invalidate the live API cache.
        api=accepted_api(root)
        if api.context_digest!=successor_cache.get('signature'):
            successor_cache.clear()
            successor_cache.update(signature=api.context_digest,api=api)
        from copy import copy
        return copy(successor_cache['api'])
    class Handler(base):
        def do_GET(self):
            parsed=urlparse(self.path);path=parsed.path
            if (path.startswith('/api/v4/') and not path.startswith(PREFIX) and not path.startswith('/api/v4/original-0930/')) or path=='/api/operations/status':
                from workbench_analysis.operational_successor_v1 import accepted_api
                try:
                    with successor_lock:
                        api=successor_reader()
                        params=parse_qs(parsed.query,keep_blank_values=True)
                        if any(len(v)!=1 for v in params.values()):raise ValueError('DUPLICATE_PARAMETER')
                        if path=='/api/operations/status':
                            request_context=params.get('context_token',[api.context_digest])[0]
                            if request_context!=api.context_digest:raise ValueError('CONTEXT_TOKEN_MISMATCH')
                            legacy=pg_adapter.read_current_endpoint('/api/v4/current/summary')
                            from .operational_control_status import CONTRACT as CONTROL_CONTRACT
                            return self.send(200,dict(successor_control(api,legacy),service_state='READY',service_mode='V4_DEFAULT_WORKBENCH',
                                service_control_contract=CONTROL_CONTRACT,product_version='V4',default_ui='V4',
                                daily_update=status_reader.status()))
                        from .operational_successor_bff_v1 import OperationalSuccessorBFFV1
                        from .research_bff import ResearchBFF
                        code,payload=OperationalSuccessorBFFV1(api,ResearchBFF(root)).get(path,{k:v[0] for k,v in params.items()})
                    return self.send(code,payload)
                except (ValueError,KeyError,OSError) as exc:
                    return self.send(409 if str(exc)=='CONTEXT_TOKEN_MISMATCH' else 503,dict(code='SUCCESSOR_READ_FAILED',reason=str(exc)[:180]))
            if path=='/v4/research/data-update':
                return self.send(200,(static/'daily-update/index.html').read_bytes(),'text/html; charset=utf-8')
            if path=='/v4/daily-update.js':
                return self.send(200,(static/'daily-update/app.js').read_bytes(),'application/javascript; charset=utf-8')
            if path=='/v4/assets/app.js':
                from workbench_analysis.operational_successor_v1 import accepted_api
                from workbench_db.v4_operational_registry_pg_r1 import read_registry
                try:
                    api=accepted_api(root)
                    registry=read_registry(root,api.candidate)
                    binding=next(b for b in registry['bindings']
                                 if b.get('path')=='src/workbench_service/static/r43-compat/app.js')
                    from workbench_analysis.r43_operational_sources import checked
                    raw=checked(root,binding).read_bytes()
                except (ValueError,KeyError,OSError,StopIteration) as error:
                    return self.send(503,dict(code='OPERATIONAL_UI_ASSET_UNAVAILABLE',
                        reason=str(error)[:160],fallback=False))
                enhancement=(static/'daily-update/entry.js').read_bytes()
                return self.send(200,raw+b'\n'+enhancement,'application/javascript; charset=utf-8')
            if path in ('/v4/assets/api.js','/v4/assets/components.js'):
                from workbench_analysis.operational_successor_v1 import CONTRACT
                from workbench_analysis.r43_owner_replay import checked_pg as checked
                from workbench_db.v4_operational_registry_pg_v1 import read_registry
                head=accepted_api(root).candidate
                if head.get('contract_id')==CONTRACT:
                    registry=read_registry(root,head)
                    relative='src/workbench_service/static/r43-compat/'+path.rsplit('/',1)[1]
                    binding=next(b for b in registry['bindings'] if b['path']==relative)
                    return self.send(200,checked(root,binding).read_bytes(),'application/javascript; charset=utf-8')
            if path==PREFIX+'/releases':
                from workbench_db.v4_operational_live_head_pg_r1 import read_current
                current=read_current(root)
                return self.send(200,dict(current=dict(sha256=current['head_sha256'],generation=current['generation'],
                    database_identity=current['database_identity']),predecessors=[]))
            if path.startswith(PREFIX):
                try:
                    tail=path.removeprefix(PREFIX).strip('/').split('/')
                    if tail==['progress']:return self.send(200,status_reader.progress())
                    if tail==['status']:return self.send(200,status_reader.status())
                    if tail==['settings']:return self.send(200,status_reader.settings())
                    if len(tail)==2 and tail[0]=='jobs':return self.send(200,status_reader.job(tail[1]))
                    if len(tail)==3 and tail[0]=='jobs' and tail[2]=='events':
                        return self.send(200,dict(events=status_reader.events(tail[1],int(parse_qs(parsed.query).get('after',['0'])[0]))))
                    return self.send(404,dict(code='DAILY_ROUTE_NOT_FOUND'))
                except (psycopg.Error,RuntimeError):return self.send(503,dict(code='V4_PG_UNAVAILABLE',fallback=False))
                except ValueError as exc:return self.send(400,dict(code=str(exc)))
            return super().do_GET()

        def operation(self):
            path=urlparse(self.path).path
            if not path.startswith(PREFIX):return self.send(404,dict(code='DAILY_ROUTE_NOT_FOUND'))
            origin=self.headers.get('Origin')
            hosts={f'http://127.0.0.1:{self.server.server_port}',f'http://localhost:{self.server.server_port}'}
            if (self.client_address[0] not in {'127.0.0.1','::1'} or
                self.headers.get('X-V4-Operation')!='daily-update' or (origin and origin not in hosts)):
                return self.send(403,dict(code='LOCAL_ORIGIN_CAPABILITY_REQUIRED'))
            with mutex:
                q=writes.setdefault(self.client_address[0],deque());now=time.monotonic()
                while q and now-q[0]>60:q.popleft()
                if len(q)>=30:return self.send(429,dict(code='WRITE_RATE_LIMIT'))
                q.append(now)
            try:
                count=int(self.headers.get('Content-Length','0'))
                if not 0<count<=4096:return self.send(413,dict(code='BODY_SIZE_LIMIT'))
                body=json.loads(self.rfile.read(count))
                if not isinstance(body,dict):raise ValueError('OBJECT_BODY_REQUIRED')
                tail=path.removeprefix(PREFIX).strip('/').split('/')
                if self.command=='PUT' and tail==['settings']:
                    if set(body)!={'auto_enabled'}:raise ValueError('SETTINGS_FIELD_NOT_ALLOWED')
                    jobs.set_settings(body['auto_enabled'])
                    return self.send(200,status_reader.settings())
                if self.command=='POST' and tail in (['jobs'],['probe']):
                    if set(body)-{'mode','through_date'}:raise ValueError('JOB_FIELD_NOT_ALLOWED')
                    key=self.headers.get('Idempotency-Key','')
                    if not 1<=len(key)<=128:raise ValueError('IDEMPOTENCY_KEY_REQUIRED')
                    job=jobs.enqueue(body.get('through_date'),mode='PROBE' if tail==['probe'] else body.get('mode','CATCH_UP'),key=key)
                    return self.send(202,dict(job_id=job))
                if self.command=='POST' and len(tail)==3 and tail[0]=='jobs' and tail[2]=='retry':
                    return self.send(202,dict(job_id=jobs.retry(tail[1])))
                if self.command=='POST' and len(tail)==3 and tail[0]=='jobs' and tail[2]=='cancel':
                    return self.send(202,dict(job_id=jobs.cancel(tail[1])))
                return self.send(404,dict(code='DAILY_ROUTE_NOT_FOUND'))
            except (psycopg.Error,RuntimeError):return self.send(503,dict(code='V4_PG_UNAVAILABLE',fallback=False))
            except (ValueError,TypeError,KeyError) as exc:
                return self.send(400,dict(code='INVALID_DAILY_REQUEST',reason=str(exc)[:100]))
        def do_POST(self):return self.operation()
        def do_PUT(self):return self.operation()
    return Handler


def serve_v4(root,host='127.0.0.1',port=28765):
    if host not in {'127.0.0.1','localhost'}:raise ValueError('LAN_DAILY_OPERATIONS_REQUIRE_AUTHENTICATED_ADAPTER')
    from workbench_analysis.operational_successor_release_v1 import recover
    recover(root)
    from workbench_analysis.operational_daily_executor_v1 import probe_source_revision
    jobs=DailyJobs(root,executor=lambda day,mode:execute_sources(root,day,mode,cancelled=jobs.publication_cancelled,readback_url=f'http://127.0.0.1:{port}',progress=jobs.checkpoint),source_probe=probe_source_revision)
    server=ThreadingHTTPServer((host,port),make_daily_handler(root,jobs))
    jobs.start()
    try:server.serve_forever()
    finally:jobs.close();server.server_close()
