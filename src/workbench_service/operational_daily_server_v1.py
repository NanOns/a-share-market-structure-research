"""Daily-operation service wrapper; frozen V2 control adapter remains valid."""
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse,parse_qs
from collections import deque
import json,threading,time
from .v4_control_server_v2 import make_v4_handler
from workbench_analysis.operational_daily_jobs_v1 import DailyJobs
from workbench_analysis.operational_daily_executor_v1 import execute_sources

PREFIX='/api/v4/operations/daily-update'


def make_daily_handler(root,jobs):
    root=Path(root);base=make_v4_handler(root);writes={};mutex=threading.Lock()
    class Handler(base):
        def do_GET(self):
            parsed=urlparse(self.path);path=parsed.path
            if path=='/v4/research/data-update':
                return self.send(200,(root/'src/workbench_service/static/daily-update/index.html').read_bytes(),'text/html; charset=utf-8')
            if path=='/v4/daily-update.js':
                return self.send(200,(root/'src/workbench_service/static/daily-update/app.js').read_bytes(),'application/javascript; charset=utf-8')
            if path=='/v4/assets/app.js':
                from workbench_analysis.r43_operational_sources import checked
                adapter=json.loads((root/'config/v4_control_adapter_v2.json').read_bytes())
                raw=checked(root,adapter['ui_assets']['app.js']).read_bytes()
                enhancement=(root/'src/workbench_service/static/daily-update/entry.js').read_bytes()
                return self.send(200,raw+b'\n'+enhancement,'application/javascript; charset=utf-8')
            if path.startswith(PREFIX):
                try:
                    tail=path.removeprefix(PREFIX).strip('/').split('/')
                    if tail==['status']:return self.send(200,jobs.status())
                    if tail==['settings']:return self.send(200,jobs.settings())
                    if len(tail)==2 and tail[0]=='jobs':return self.send(200,jobs.job(tail[1]))
                    if len(tail)==3 and tail[0]=='jobs' and tail[2]=='events':
                        return self.send(200,dict(events=jobs.events(tail[1],int(parse_qs(parsed.query).get('after',['0'])[0]))))
                    return self.send(404,dict(code='DAILY_ROUTE_NOT_FOUND'))
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
                    return self.send(200,jobs.settings(body['auto_enabled']))
                if self.command=='POST' and tail in (['jobs'],['probe']):
                    if set(body)-{'mode','through_date'}:raise ValueError('JOB_FIELD_NOT_ALLOWED')
                    key=self.headers.get('Idempotency-Key','')
                    if not 1<=len(key)<=128:raise ValueError('IDEMPOTENCY_KEY_REQUIRED')
                    job=jobs.enqueue(body.get('through_date'),mode='PROBE' if tail==['probe'] else body.get('mode','CATCH_UP'),key=key)
                    return self.send(202,dict(job_id=job))
                if self.command=='POST' and len(tail)==3 and tail[0]=='jobs' and tail[2]=='retry':
                    return self.send(202,dict(job_id=jobs.retry(tail[1])))
                return self.send(404,dict(code='DAILY_ROUTE_NOT_FOUND'))
            except (ValueError,TypeError,KeyError) as exc:
                return self.send(400,dict(code='INVALID_DAILY_REQUEST',reason=str(exc)[:100]))
        def do_POST(self):return self.operation()
        def do_PUT(self):return self.operation()
    return Handler


def serve_v4(root,host='127.0.0.1',port=28765):
    if host not in {'127.0.0.1','localhost'}:raise ValueError('LAN_DAILY_OPERATIONS_REQUIRE_AUTHENTICATED_ADAPTER')
    jobs=DailyJobs(root,executor=lambda day,mode:execute_sources(root,day,mode))
    server=ThreadingHTTPServer((host,port),make_daily_handler(root,jobs))
    jobs.start()
    try:server.serve_forever()
    finally:jobs.close();server.server_close()
