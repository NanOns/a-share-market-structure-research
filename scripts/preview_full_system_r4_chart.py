"""Read-only isolated product preview; original source root is never published."""
import os,sys,json,threading
from pathlib import Path
from http.server import ThreadingHTTPServer
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from workbench_service.core_product_server_r1 import make_product_handler
from workbench_analysis.operational_daily_jobs_pg_r1 import DailyJobs
from tests import v4_native_isolation_plugin_r4 as guard

def main():
    from scripts.r4_readonly_source_guard import install
    source_guard=install(['G:/codex work/大A交易','D:/new_tdx'])
    candidate=Path('G:/codex_tmp/full_system_r4_fbd23a6b/chart_http_candidate')
    authority=candidate/'ISOLATED_HISTORY_AUTHORITY.json'
    os.environ['R4_PG_DATA_DIRECTORY']='G:/codex_tmp/full_system_r4_fbd23a6b/pg_data'
    os.environ['R4_CONNECTION_LEDGER']=str(ROOT/'docs/audits/full_system_r4_pg_only_20261011_fbd23a6b/R4_03_BROWSER_CONNECTIONS.jsonl')
    config=SimpleNamespace();guard.pytest_configure(config);guard.ACTIVE='ISOLATED_BROWSER_PRODUCT'
    jobs=DailyJobs(candidate/'browser_jobs')
    base=make_product_handler(Path('G:/codex work/大A交易'),jobs,isolated_history_authority=authority)
    receipt_lock=threading.RLock()
    class ReadOnlyHandler(base):
        def do_GET(self):
            with receipt_lock:
                try:return super().do_GET()
                finally:
                    guard.pytest_sessionfinish(None,0)
                    p=ROOT/'docs/audits/full_system_r4_pg_only_20261011_fbd23a6b/R4_BROWSER_SOURCE_GUARD.json'
                    temp=p.with_suffix('.tmp');temp.write_text(json.dumps(source_guard,indent=2),encoding='utf8');os.replace(temp,p)
        def send(self,status,body,content_type='application/json; charset=utf-8'):
            if content_type.startswith('text/html'):
                raw=body.decode('utf8') if isinstance(body,bytes) else str(body)
                raw=raw.replace('真实生产快照','隔离工程快照')
                raw=raw.replace('<body>','<body><aside role="status">隔离工程预览 · 未接受生产 · 仅允许读取</aside>',1)
                body=raw.encode('utf8')
            return super().send(status,body,content_type)
        def do_POST(self):self.send(403,dict(code='ISOLATED_PREVIEW_READ_ONLY'))
        do_PUT=do_POST
        do_PATCH=do_POST
        do_DELETE=do_POST
    server=ThreadingHTTPServer(('127.0.0.1',55891),ReadOnlyHandler)
    print(json.dumps(dict(url='http://127.0.0.1:55891/v4/research/stocks',production=False,authority=str(authority))),flush=True)
    try:server.serve_forever()
    finally:server.server_close();jobs.close();guard.pytest_sessionfinish(None,0);guard.pytest_unconfigure(config)

if __name__=='__main__':main()
