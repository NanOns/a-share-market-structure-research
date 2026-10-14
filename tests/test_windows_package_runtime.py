"""Actual PostgreSQL lifecycle, simulated executor; no numeric-release assertion."""
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import threading
import time
from urllib.request import urlopen
import pytest
from workbench_desktop.storage import WorkspaceLease,verified_existing_owner,atomic
from workbench_desktop.engine import EngineController
from workbench_desktop.jobs import ManagedDailyJobs
import workbench_analysis.operational_daily_jobs_v1 as daily


@pytest.fixture
def plan(monkeypatch):
    monkeypatch.setattr(daily, 'gap_plan', lambda *a, **k: dict(
        status='TIME_ELIGIBLE', requested_through_date='2026-10-09',
        missing_sessions=['2026-10-09'], eligible_sessions=['2026-10-09'],
        last_good_trade_date='2026-10-08'))


def jobs(root, executor=None):
    return ManagedDailyJobs(root, executor, clock=lambda: datetime.fromisoformat('2026-10-09T22:10+08:00'))


def test_workspace_lock_survives_stopped_engine(tmp_path):
    with WorkspaceLease(tmp_path) as lease:
        controller=EngineController(tmp_path)
        assert controller.instance_id==lease.identity['instance_id']
        controller.transition('STOPPED')
        assert verified_existing_owner(tmp_path)['verified_status']['engine_state']=='STOPPED'
        stale=controller.status();stale['instance_id']='stale';atomic(tmp_path/'runtime/desktop/status.json',stale)
        assert verified_existing_owner(tmp_path)['verified_status']['engine_state']=='INITIALIZING'
        with pytest.raises(ValueError, match='ALREADY_OWNED'):
            WorkspaceLease(tmp_path).acquire()
    with WorkspaceLease(tmp_path):
        pass


def test_maintenance_resume_preserves_user_cancel_and_pause(tmp_path, plan):
    worker = jobs(tmp_path)
    worker.settings(False)
    cancelled = worker.enqueue(key='cancelled')
    worker.cancel(cancelled)
    interrupted = worker.enqueue(key='interrupted')
    worker.original_executor = lambda *_: (worker.quiesce() or dict(status='CANCELLED'))
    worker.tick()
    assert worker.job(interrupted)['status'] == 'INTERRUPTED'
    assert worker.job(interrupted)['error'] == 'MAINTENANCE_INTERRUPTED'
    with pytest.raises(ValueError, match='QUIESCING'):
        worker.enqueue()
    with pytest.raises(ValueError, match='QUIESCING'):
        worker.retry(interrupted)
    restarted = jobs(tmp_path, lambda *_: dict(status='PUBLISHED'))
    assert restarted.job(cancelled)['status'] == 'CANCELLED'
    assert restarted.job(interrupted)['status'] == 'QUEUED'
    assert not restarted.settings()['auto_enabled']
    restarted.tick()
    assert restarted.job(interrupted)['status'] == 'PUBLISHED_FULL'
    with restarted.connect() as db:
        # Inspect the persisted native store after recovery, including foreign
        # key consistency and the user's paused policy. SQLite PRAGMA cannot
        # establish integrity for this PostgreSQL-only runtime.
        persisted = db.execute('SELECT job_id,status FROM update_jobs ORDER BY job_id').fetchall()
        assert {row['job_id']: row['status'] for row in persisted} == {
            cancelled: 'CANCELLED', interrupted: 'PUBLISHED_FULL'}
        assert db.execute('SELECT enabled FROM scheduler_policy WHERE id=1').fetchone()[0] == 0
        assert db.execute('SELECT count(*) FROM update_job_days d LEFT JOIN update_jobs j ON d.job_id=j.job_id WHERE j.job_id IS NULL').fetchone()[0] == 0
        # Policy events have a nullable job_id by contract; every event that
        # names a job must refer to an existing job.
        assert db.execute('SELECT count(*) FROM update_events e LEFT JOIN update_jobs j ON e.job_id=j.job_id WHERE e.job_id IS NOT NULL AND j.job_id IS NULL').fetchone()[0] == 0


def factory(root, executor=None):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200); self.end_headers(); self.wfile.write(b'READBACK_ALIVE')
        def log_message(self, *_):
            pass
    worker = jobs(root, executor)
    worker.settings(False)
    return ThreadingHTTPServer(('127.0.0.1', 0), Handler), worker

@pytest.mark.parametrize("worker_kind", ["managed", "process"])
def test_product_stays_starting_until_real_context_readback(tmp_path,plan,monkeypatch,worker_kind):
    """Real isolated PG and HTTP; controlled child body for the process facade."""
    import os
    import traceback
    entered=threading.Event();release=threading.Event();errors=[];trace=[]
    started=time.perf_counter()
    def mark(stage, **detail):
        trace.append(dict(stage=stage,elapsed_seconds=time.perf_counter()-started,**detail))
    class Handler(BaseHTTPRequestHandler):
        PREFLIGHT_PRODUCT_CONTEXT=True
        def do_GET(self):
            assert self.path=='/api/v4/context'
            mark('HTTP_CONTEXT_ENTERED')
            entered.set();release.wait(5)
            raw=json.dumps({'context_token':'engineering-token','context':{'trade_date':'2026-10-09'}}).encode()
            self.send_response(200);self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
            mark('HTTP_CONTEXT_SENT')
        def log_message(self,*args):pass
    def create():
        mark('FACTORY_ENTERED')
        mark('PG_INITIALIZATION_STARTED')
        if worker_kind=='managed':
            worker=jobs(tmp_path)
        else:
            import sys
            from workbench_desktop.jobs import ProcessDailyJobs
            worker=ProcessDailyJobs(tmp_path,readback_url='http://127.0.0.1:0')
            # Exercise the real facade/monitor/control with a bounded child.
            # Full source capture/derivation belongs to the later APPEND gate.
            marker=tmp_path/'child_pg_readback.json'
            child="""import json,os,sys
from pathlib import Path
import psycopg
from psycopg import sql
assert os.environ['TMP']=='G:/codex_tmp'
with psycopg.connect(os.environ['V4_NATIVE_PG_DSN']) as pg:
    pg.execute('SET TRANSACTION READ ONLY')
    enabled=pg.execute(sql.SQL('SELECT enabled FROM {}.scheduler_policy WHERE id=1').format(sql.Identifier(sys.argv[1]))).fetchone()[0]
    assert enabled==0
Path(sys.argv[2]).write_text(json.dumps(dict(paused=True,pid=os.getpid())),encoding='utf-8')
assert sys.stdin.readline().strip()=='QUIESCE'
"""
            monkeypatch.setattr(worker,'command',lambda:[sys.executable,'-c',child,worker.schema,str(marker)])
        mark('PG_INITIALIZATION_FINISHED')
        worker.settings(False)
        mark('PG_PAUSE_PERSISTED')
        server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        mark('HTTP_SOCKET_BOUND')
        return server,worker
    controller=EngineController(tmp_path,factory=create)
    def start():
        mark('START_THREAD_ENTERED')
        try:
            controller.perform('start')
            mark('START_COMPLETED')
        except Exception:
            errors.append(traceback.format_exc())
            mark('START_FAILED')
    with WorkspaceLease(tmp_path):
        thread=threading.Thread(target=start);thread.start()
        try:
            assert entered.wait(5), json.dumps(dict(errors=errors,trace=trace),ensure_ascii=False)
            assert controller.state=='STARTING'
            release.set();thread.join(5)
            assert not thread.is_alive() and not errors, json.dumps(dict(errors=errors,trace=trace))
            assert controller.state=='RUNNING'
            assert controller.last_snapshot['context_token']=='engineering-token'
            if worker_kind=='process':
                marker=tmp_path/'child_pg_readback.json'
                deadline=time.monotonic()+5
                while not marker.exists() and time.monotonic()<deadline: time.sleep(.01)
                assert marker.exists(), 'CHILD_PG_READBACK_NOT_REACHED'
                assert json.loads(marker.read_text(encoding='utf-8'))['paused'] is True
                assert controller.jobs.process.pid != __import__('os').getpid()
                assert controller.jobs.thread.is_alive()
                mark('CHILD_REAL_PG_READBACK_CONFIRMED')
        finally:
            release.set();thread.join(5);controller.perform('stop')
            mark('STOP_COMPLETED')
            evidence=dict(contract_id='F_PG_01_MANAGED_START_DIAGNOSTIC_R1',
                worker_kind=worker_kind,pg_dsn_configured=bool(os.environ.get('V4_NATIVE_PG_DSN')),
                workspace=str(tmp_path),http_preflight_entered=entered.is_set(),errors=errors,trace=trace)
            if os.environ.get('F_PG_01_EVIDENCE_PATH'):
                path=__import__('pathlib').Path(os.environ['F_PG_01_EVIDENCE_PATH'])
                temporary=path.with_suffix('.tmp')
                temporary.write_text(json.dumps(evidence,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
                temporary.replace(path)


def test_rejected_context_releases_resources_and_never_reports_running(tmp_path,plan):
    from urllib.error import HTTPError
    class Handler(BaseHTTPRequestHandler):
        PREFLIGHT_PRODUCT_CONTEXT=True
        def do_GET(self):
            self.send_response(409);self.send_header('Content-Length','0');self.end_headers()
        def log_message(self,*args):pass
    allocated=[]
    def create():
        worker=jobs(tmp_path);worker.settings(False)
        server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        allocated.append((server,worker));return server,worker
    controller=EngineController(tmp_path,factory=create)
    with WorkspaceLease(tmp_path):
        with pytest.raises(HTTPError):controller.perform('start')
        assert controller.state=='FAILED'
        assert controller.server is controller.jobs is controller.http_thread is None
        server,worker=allocated[0]
        assert server.socket.fileno()==-1
        assert not worker.thread or not worker.thread.is_alive()
        states=[json.loads(path.read_bytes())['engine_state'] for path in (tmp_path/'runtime/desktop/events').glob('*.json')]
        assert 'RUNNING' not in states
        controller.perform('stop');assert controller.state=='STOPPED'


def test_restart_recreates_objects_and_keeps_settings(tmp_path, plan):
    controller = EngineController(tmp_path, factory=lambda: factory(tmp_path))
    with WorkspaceLease(tmp_path):
        controller.perform('start')
        old_server, old_jobs = controller.server, controller.jobs
        controller.perform('restart')
        assert controller.server is not old_server and controller.jobs is not old_jobs
        assert not old_jobs.thread.is_alive()
        assert not controller.settings()['auto_enabled']
        assert controller.status()['auto_daily_enabled'] is False
        controller.perform('stop')
        assert controller.state == 'STOPPED' and controller.server is None
        controller.settings(True)
        assert controller.status()['auto_daily_enabled'] is True
        controller.settings(False)
        assert controller.status()['auto_daily_enabled'] is False
        with pytest.raises(ValueError, match='ALREADY_OWNED'):
            WorkspaceLease(tmp_path).acquire()


def test_http_remains_alive_while_active_executor_finishes(tmp_path, plan):
    entered, release = threading.Event(), threading.Event()
    def executor(*_):
        entered.set()
        assert release.wait(8)
        assert urlopen(f'http://127.0.0.1:{controller.port}', timeout=2).read() == b'READBACK_ALIVE'
        return dict(status='PUBLISHED', evidence_kind='SIMULATED_EXECUTOR')
    def create():
        server, worker = factory(tmp_path, executor)
        worker.enqueue()
        return server, worker
    controller = EngineController(tmp_path, factory=create)
    with WorkspaceLease(tmp_path):
        controller.perform('start')
        assert entered.wait(5)
        old_jobs = controller.jobs
        stop = threading.Thread(target=lambda: controller.perform('stop'))
        stop.start()
        deadline = time.monotonic()+3
        while controller.state != 'WAITING_SAFE_BOUNDARY' and time.monotonic()<deadline:
            time.sleep(.01)
        assert controller.state == 'WAITING_SAFE_BOUNDARY'
        with pytest.raises(ValueError, match='IN_PROGRESS'):
            controller.perform('restart')
        assert urlopen(f'http://127.0.0.1:{controller.port}', timeout=2).read() == b'READBACK_ALIVE'
        release.set(); stop.join(6)
        assert not stop.is_alive() and controller.state == 'STOPPED'
        with old_jobs.connect() as db:
            assert db.execute('SELECT state FROM update_job_days').fetchone()[0] == 'PUBLISHED'


def test_start_failure_does_not_report_stopped_resources_as_running(tmp_path):
    controller = EngineController(tmp_path, factory=lambda: (_ for _ in ()).throw(ValueError('TEST_START_FAILURE')))
    with pytest.raises(ValueError, match='TEST_START_FAILURE'):
        controller.perform('start')
    assert controller.state == 'FAILED' and controller.server is None
    controller.perform('stop')
    assert controller.state == 'STOPPED'


def test_cancel_pending_restart_keeps_live_objects(tmp_path, plan):
    entered, release = threading.Event(), threading.Event()
    def executor(*_):
        entered.set(); release.wait(8)
        return dict(status='PUBLISHED')
    def create():
        server, worker = factory(tmp_path, executor)
        worker.enqueue()
        return server, worker
    controller = EngineController(tmp_path, factory=create)
    controller.perform('start')
    try:
        assert entered.wait(4)
        old_server = controller.server
        thread = threading.Thread(target=lambda: controller.perform('restart'))
        thread.start()
        deadline = time.monotonic()+3
        while controller.state != 'WAITING_SAFE_BOUNDARY' and time.monotonic()<deadline:
            time.sleep(.01)
        controller.cancel_maintenance(); thread.join(3)
        assert not thread.is_alive() and controller.state=='RUNNING' and controller.server is old_server
    finally:
        release.set(); controller.perform('stop')


def test_source_task_only_with_workspace_owner(tmp_path, monkeypatch):
    from workbench_desktop.source_adapter import tdx_capture, executor
    with pytest.raises(ValueError, match='LEASE_REQUIRED'):
        tdx_capture(tmp_path)
    with WorkspaceLease(tmp_path):
        execute = executor(tmp_path)
        latest = execute.__globals__['capture_latest_tdx_package']
        refresh = latest.__globals__['_refresh_existing_downloader']
        proxy = refresh.__globals__['subprocess']
        with pytest.raises(ValueError, match='NOT_WHITELISTED'):
            proxy.run(['arbitrary.exe'],cwd=tmp_path)
        calls=[]
        import workbench_desktop.source_adapter as adapter
        monkeypatch.setattr(adapter,'tdx_capture',lambda root:calls.append(root))
        refresh()
        assert calls==[tmp_path]


def test_production_port_reserved_before_recovery(tmp_path,monkeypatch):
    from workbench_desktop import engine
    from workbench_service import core_product_server_r1 as service
    from workbench_analysis import operational_successor_release_v1 as release
    calls=[]
    for name in ['data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json','data/v4/V4_DATA_ACCEPTED_HEAD.json','config/v4_production_runtime_authority_v1.json']:
        path=tmp_path/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text('{}')
    monkeypatch.setattr(release,'recover',lambda root:calls.append('recover'))
    job_root=tmp_path/'isolated_jobs';job_root.mkdir()
    monkeypatch.setattr(engine,'ManagedDailyJobs',lambda *a,**k:jobs(job_root))
    class Handler(BaseHTTPRequestHandler):
        pass
    monkeypatch.setattr(service,'make_product_handler',lambda *a:Handler)
    with WorkspaceLease(tmp_path):
        controller=EngineController(tmp_path,port=0)
        server,worker=controller.production_factory()
        try:
            assert server.server_port>0 and calls==['recover']
            calls.clear()
            conflict=EngineController(tmp_path,port=server.server_port)
            with pytest.raises(OSError):conflict.production_factory()
            assert calls==[]
        finally:
            server.server_close();worker.close()


def test_native_source_view_preserves_rows_unknowns_and_raw_bytes(tmp_path):
    from workbench_desktop.source_view import project
    from workbench_analysis.tdx_official_daily_source import sha256_file
    raw=tmp_path/'raw.json'
    rows=[dict(source_security_key='SH.600000',close=123.456),dict(source_security_key='SZ.000001',close=11.22),
          dict(source_security_key='BJ.920001',close=1),dict(source_security_key='UNKNOWN.123456',close=8)]
    document=dict(contract_id='TDX_LATEST_PACKAGE_TARGET_SESSION_V2',status='TARGET_BARS_EXTRACTED',
        target_session='2026-10-09',source_available_at='2026-10-09T19:00+08:00',target_bars=rows,row_count=4)
    raw.write_text(json.dumps(document),encoding='utf-8');before=raw.read_bytes()
    extraction=dict(document,artifact=dict(path=str(raw),sha256=sha256_file(raw)))
    with WorkspaceLease(tmp_path):
        result=project(tmp_path,extraction)
        assert result['target_bars']==[rows[0],rows[1],rows[3]]
        assert result['excluded_source_security_keys']==['BJ.920001']
        assert result['source_available_at']==document['source_available_at']
        assert raw.read_bytes()==before
        assert project(tmp_path,extraction)['artifact']==result['artifact']
        raw.write_text('{}')
        with pytest.raises(ValueError,match='RAW_SHA_MISMATCH'):project(tmp_path,extraction)


def test_known_legacy_writer_blocks_workspace_before_any_lock_or_db(tmp_path):
    import os,subprocess,sys
    from workbench_desktop.storage import legacy_workspace_writers
    if os.name!='nt':pytest.skip('Windows process-image contract')
    script=tmp_path/'scripts/start_product_attested_r4.py'
    script.parent.mkdir();script.write_text('import time; time.sleep(30)\n',encoding='utf-8')
    child=subprocess.Popen([sys.executable,str(script)],cwd=tmp_path,
        env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',TMP='G:/codex_tmp',TEMP='G:/codex_tmp',TMPDIR='G:/codex_tmp'))
    try:
        deadline=time.monotonic()+3
        while child.pid not in legacy_workspace_writers(tmp_path) and time.monotonic()<deadline:time.sleep(.05)
        assert child.pid in legacy_workspace_writers(tmp_path)
        with pytest.raises(ValueError,match='LEGACY_V4_WORKSPACE_WRITER_MUST_EXIT'):
            WorkspaceLease(tmp_path).acquire()
        assert not (tmp_path/'runtime/desktop/app.lock').exists()
        assert not (tmp_path/'runtime/dynamic_daily/jobs.sqlite3').exists()
    finally:
        child.terminate();child.wait(timeout=5)
