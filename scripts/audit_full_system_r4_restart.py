"""Restart only the attested G cluster; actual native HTTP fail-closed probe."""
import json,os,subprocess,sys,threading
from pathlib import Path
from types import SimpleNamespace
from http.server import ThreadingHTTPServer
from urllib.request import urlopen
from urllib.error import HTTPError
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from scripts.audit_full_system_r4_scope import write

def main():
    import psycopg
    from tests import v4_native_isolation_plugin_r4 as guard
    from workbench_analysis.operational_daily_jobs_pg_r1 import DailyJobs
    from workbench_desktop.engine import EngineController
    from workbench_service.operational_daily_server_v1 import make_daily_handler,PREFIX
    data=Path('G:/codex_tmp/full_system_r4_fbd23a6b/pg_data').resolve()
    with psycopg.connect(os.environ['V4_NATIVE_PG_DSN']) as pg:
        if Path(pg.execute('SHOW data_directory').fetchone()[0]).resolve()!=data:raise ValueError('ISOLATED_RESTART_DIRECTORY_MISMATCH')
        if pg.execute('SHOW port').fetchone()[0]!='55791':raise ValueError('ISOLATED_RESTART_PORT_MISMATCH')
        system=pg.execute('SELECT system_identifier FROM pg_control_system()').fetchone()[0]
    os.environ['R4_PG_DATA_DIRECTORY']=str(data);os.environ['R4_CONNECTION_LEDGER']=str(ROOT/'docs/audits/full_system_r4_pg_only_20261011_fbd23a6b/R4_02_PHYSICAL_RESTART_CONNECTIONS.jsonl')
    config=SimpleNamespace();guard.pytest_configure(config);guard.ACTIVE='ATTESTED_PG_PHYSICAL_RESTART_HTTP'
    candidate=Path('G:/codex_tmp/full_system_r4_fbd23a6b/restart_candidate');jobs=DailyJobs(candidate);jobs.settings(False)
    with jobs.connect() as db:
        db.execute('INSERT INTO update_jobs VALUES(?,?,?,?,?,?,?,?,?) ON CONFLICT(job_id) DO NOTHING',('R4_RESTART_SENTINEL','ENGINEERING_FIXTURE','PROBE','2026-10-09','QUEUED','2026-10-11T00:00:00+00:00',None,'R4_RESTART_SENTINEL',None))
    engine=EngineController(candidate,port=0)
    # Source root is read-only throughout; queue writes belong to candidate only.
    source_root=Path('G:/codex work/大A交易').resolve()
    server=ThreadingHTTPServer(('127.0.0.1',0),make_daily_handler(source_root,jobs));thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    def get():
        url=f'http://127.0.0.1:{server.server_port}'+PREFIX+'/settings'
        try:
            with urlopen(url,timeout=10) as response:return dict(code=response.status,payload=json.loads(response.read()))
        except HTTPError as error:return dict(code=error.code,payload=json.loads(error.read()))
    ctl='E:/Postgres/bin/pg_ctl.exe';stopped=False;result={};code=1
    def control(arguments):
        # Windows daemon descendants must not inherit an undrained PIPE.
        with Path('G:/codex_tmp/full_system_r4_fbd23a6b/restart_control.log').open('ab') as log:
            subprocess.run([ctl,*arguments],check=True,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,timeout=60)
    try:
        before=get();assert before['code']==200 and not before['payload']['auto_enabled']
        control(['-D',str(data),'-m','fast','-w','stop']);stopped=True
        offline=get();desktop=engine.status()
        assert offline['code']==503 and offline['payload']['code']=='V4_PG_UNAVAILABLE' and offline['payload']['fallback'] is False
        assert desktop['auto_daily_enabled'] is None and desktop['scheduler_settings_state']=='PG_UNAVAILABLE_OR_NOT_INITIALIZED'
        control(['-D',str(data),'-l','G:/codex_tmp/full_system_r4_fbd23a6b/pg.log','-o','-p 55791 -h 127.0.0.1','-w','start']);stopped=False
        after=get();again=DailyJobs(candidate)
        assert after['code']==200 and not after['payload']['auto_enabled'] and again.job('R4_RESTART_SENTINEL')['status']=='QUEUED'
        with psycopg.connect(os.environ['V4_NATIVE_PG_DSN']) as pg:assert pg.execute('SELECT system_identifier FROM pg_control_system()').fetchone()[0]==system
        result=dict(before_http=before,offline_http=offline,offline_desktop=desktop,after_http=after,system_identifier=str(system),data_directory=str(data),port=55791,persistent_job=again.job('R4_RESTART_SENTINEL'),sqlite_files=list(map(str,candidate.rglob('*.sqlite*'))))
        assert not result['sqlite_files'];code=0
    finally:
        if stopped:control(['-D',str(data),'-l','G:/codex_tmp/full_system_r4_fbd23a6b/pg.log','-o','-p 55791 -h 127.0.0.1','-w','start'])
        server.shutdown();server.server_close();thread.join(timeout=5);jobs.close()
        guard.pytest_sessionfinish(None,code);guard.pytest_unconfigure(config)
        write('R4_02_PHYSICAL_RESTART_RESULT.json',dict(**result,current_status='SCOPED_PHYSICAL_RESTART_HTTP_FAIL_CLOSED_PASS' if code==0 else 'SCOPED_RESTART_FAIL',negative_vectors=['Real PG shutdown -> HTTP503 with fallback=false','Desktop reports unknown auto state while PG is unavailable'],limitations=['Only isolated G PG was restarted; production PG/PID and Windows package untouched','Real executor crash/lease/checkpoint and accepted-T0 no-repeat gates remain separate'],next_conditions=['Executor process death/recovery and immutable checkpoint tests']))
    print(json.dumps(dict(status='PASS' if code==0 else 'FAIL',restart_port=55791)))
if __name__=='__main__':main()
