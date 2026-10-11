"""Versioned UI preview in a new disposable root; accepted UI bytes untouched."""
import hashlib,json,os,shutil,sys
from pathlib import Path
from http.server import ThreadingHTTPServer
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'src')]
OUT=ROOT/'docs/audits/r4_r3_integration_20261011'
SOURCE=Path('G:/codex_tmp/test_temp/r4_batch2_default_product')
CANDIDATE=Path('G:/codex_tmp/r4_r3_ui_candidate')
def write(p,x):
    p.parent.mkdir(parents=True,exist_ok=True);tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding='utf8');os.replace(tmp,p)
def main():
    if CANDIDATE.exists():raise ValueError('NEW_PREVIEW_ROOT_REQUIRED')
    for p in SOURCE.rglob('*'):
        target=CANDIDATE/p.relative_to(SOURCE)
        if p.is_dir():target.mkdir(parents=True,exist_ok=True)
        else:
            target.parent.mkdir(parents=True,exist_ok=True)
            if p.stat().st_size>1024*1024:os.link(p,target)
            else:shutil.copyfile(p,target)
    # New namespace and authority, never overwrite the accepted UI release.
    joint_path=CANDIDATE/'config/v4_joint_release_authority_v1.json'
    joint=json.loads(joint_path.read_bytes())
    assets={}
    for name in joint['ui_assets']:
        source=ROOT/'src/workbench_service/static'/('research' if name in ('index.html','style.css') else 'core-product-r1')/name
        raw=source.read_bytes();digest=hashlib.sha256(raw).hexdigest()
        p=CANDIDATE/'data/v4/ui_r3_candidate'/digest/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
        assets[name]=dict(path=p.relative_to(CANDIDATE).as_posix(),sha256=digest,bytes=len(raw))
        if name.endswith('.js'):
            target=CANDIDATE/'src/workbench_service/static/core-product-r1'/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)
    joint['ui_assets']=assets;write(joint_path,joint)
    from workbench_db.v4_native import connection,workspace_schema
    from workbench_db.v4_history_pg_r1 import DDL
    from psycopg import sql
    target_schema=workspace_schema(CANDIDATE,'history')
    from workbench_db.v4_native import create_schema,configured_dsn
    import psycopg
    with psycopg.connect(configured_dsn()) as pg:create_schema(pg,target_schema)
    for path in (CANDIDATE/'data/v4/r4_r2_dated_catalog').glob('*/MANIFEST.json'):
        manifest=json.loads(path.read_bytes());binding=manifest['history_index']
        with connection(target_schema) as pg:
            pg.execute(DDL)
            if not pg.execute('SELECT 1 FROM history_versions WHERE version=%s',(binding['version'],)).fetchone():
                pg.execute(sql.SQL('INSERT INTO history SELECT * FROM {}.history WHERE version=%s').format(sql.Identifier(binding['schema'])),(binding['version'],))
                pg.execute(sql.SQL('INSERT INTO history_versions SELECT * FROM {}.history_versions WHERE version=%s').format(sql.Identifier(binding['schema'])),(binding['version'],))
        manifest['history_index']=dict(binding,schema=target_schema);write(path,manifest)
    dates={p.parent.name:dict(path=p.relative_to(CANDIDATE).as_posix(),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),bytes=p.stat().st_size) for p in (CANDIDATE/'data/v4/r4_r2_dated_catalog').glob('*/MANIFEST.json')}
    if len(dates)!=5:raise ValueError('FIVE_DATES_REQUIRED')
    write(CANDIDATE/'config/core_product_read_authority_r1.json',dict(contract_id='CORE_PRODUCT_READ_AUTHORITY_R2',dates=dates))
    from scripts.r4_readonly_source_guard import install
    install([str(SOURCE),'G:/codex work/大A交易','D:/new_tdx'])
    from tests import v4_native_isolation_plugin_r4 as guard
    config=SimpleNamespace();guard.pytest_configure(config);guard.ACTIVE='R3_UI_DEFAULT_HTTP'
    from workbench_analysis.operational_daily_jobs_pg_r1 import DailyJobs
    from workbench_service.core_product_server_r1 import make_product_handler
    jobs=DailyJobs(CANDIDATE);base=make_product_handler(CANDIDATE,jobs)
    class ReadOnly(base):
        def do_POST(self):return self.send(405,dict(code='ISOLATED_READ_ONLY'))
        do_PUT=do_POST;do_DELETE=do_POST;do_PATCH=do_POST
        def do_GET(self):
            try:return super().do_GET()
            finally:guard.pytest_sessionfinish(None,0)
    server=ThreadingHTTPServer(('127.0.0.1',0),ReadOnly)
    write(OUT/'UI_SERVER.json',dict(url=f'http://127.0.0.1:{server.server_port}/v4/research/home',pid=os.getpid(),production=False,assets=assets,root=str(CANDIDATE)))
    print(json.dumps(dict(port=server.server_port)),flush=True)
    try:server.serve_forever()
    finally:server.server_close();jobs.close();guard.pytest_unconfigure(config)
if __name__=='__main__':main()
