"""Read-only browser probe of the disposable default catalogue."""
import json,os,sys,threading
from pathlib import Path
from types import SimpleNamespace
from http.server import ThreadingHTTPServer
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]


def main():
    from scripts.audit_r4_default_product_http import CANDIDATE,write,sha
    from scripts.audit_r4_default_product_http import SOURCE
    from tests import v4_native_isolation_plugin_r4 as guard
    from scripts.r4_readonly_source_guard import install
    from workbench_service.core_product_server_r1 import make_product_handler
    from workbench_analysis.operational_daily_jobs_pg_r1 import DailyJobs
    install(['G:/codex work/大A交易','D:/new_tdx'])
    out=ROOT/'docs/audits/r4_external_repair_r2_20261011'
    joint=json.loads((CANDIDATE/'config/v4_joint_release_authority_v1.json').read_bytes())
    for binding in joint['ui_assets'].values():
        path=SOURCE/binding['path'];destination=CANDIDATE/binding['path']
        if sha(path)!=binding['sha256']:raise ValueError('FROZEN_UI_SOURCE_CHANGED')
        destination.parent.mkdir(parents=True,exist_ok=True);tmp=destination.with_suffix('.tmp');tmp.write_bytes(path.read_bytes());os.replace(tmp,destination)
    authority=CANDIDATE/'config/core_product_read_authority_r1.json';before=authority.read_bytes()
    dates={p.parent.name:dict(path=p.relative_to(CANDIDATE).as_posix(),sha256=sha(p),bytes=p.stat().st_size) for p in (CANDIDATE/'data/v4/r4_r2_dated_catalog').glob('*/MANIFEST.json')}
    if len(dates)!=5:raise ValueError('FIVE_DATE_CATALOG_REQUIRED')
    write(authority,dict(contract_id='CORE_PRODUCT_READ_AUTHORITY_R2',dates=dates))
    os.environ['R4_PG_DATA_DIRECTORY']='G:/codex_tmp/full_system_r4_fbd23a6b/pg_data'
    os.environ['R4_CONNECTION_LEDGER']=str(out/'DEFAULT_BROWSER_CONNECTIONS.jsonl')
    config=SimpleNamespace();guard.pytest_configure(config);guard.ACTIVE='DEFAULT_BROWSER_READONLY_R2'
    jobs=DailyJobs(CANDIDATE);base=make_product_handler(CANDIDATE,jobs);lock=threading.Lock()
    class Handler(base):
        def do_GET(self):
            with lock:
                try:return super().do_GET()
                finally:guard.pytest_sessionfinish(None,0)
        def send(self,status,body,content_type='application/json; charset=utf-8'):
            if content_type.startswith('text/html'):
                raw=body.decode('utf8') if isinstance(body,bytes) else str(body)
                raw=raw.replace('<body>','<body><aside role="status">隔离工程预览 · 未接受生产 · 仅允许读取</aside>',1)
                body=raw.encode('utf8')
            return super().send(status,body,content_type)
        def do_POST(self):return self.send(405,dict(code='ISOLATED_PREVIEW_READ_ONLY'))
        do_PUT=do_POST;do_PATCH=do_POST;do_DELETE=do_POST
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
    write(out/'DEFAULT_BROWSER_SERVER.json',dict(url=f'http://127.0.0.1:{server.server_port}/v4/research/home',pid=os.getpid(),production=False,constructor_history_injection=False))
    print(json.dumps(dict(port=server.server_port)),flush=True)
    try:server.serve_forever()
    finally:
        server.server_close();jobs.close();tmp=authority.with_suffix('.tmp');tmp.write_bytes(before);os.replace(tmp,authority)
        guard.pytest_sessionfinish(None,0);guard.pytest_unconfigure(config)


if __name__=='__main__':main()
