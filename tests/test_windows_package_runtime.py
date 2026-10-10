"""Actual lifecycle/SQLite, simulated executor; no numeric-release assertion."""
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import threading
import time
from urllib.request import urlopen
import pytest
from workbench_desktop.storage import WorkspaceLease
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
    with WorkspaceLease(tmp_path):
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
        assert db.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'


def factory(root, executor=None):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200); self.end_headers(); self.wfile.write(b'READBACK_ALIVE')
        def log_message(self, *_):
            pass
    worker = jobs(root, executor)
    worker.settings(False)
    return ThreadingHTTPServer(('127.0.0.1', 0), Handler), worker


def test_restart_recreates_objects_and_keeps_settings(tmp_path, plan):
    controller = EngineController(tmp_path, factory=lambda: factory(tmp_path))
    with WorkspaceLease(tmp_path):
        controller.perform('start')
        old_server, old_jobs = controller.server, controller.jobs
        controller.perform('restart')
        assert controller.server is not old_server and controller.jobs is not old_jobs
        assert not old_jobs.thread.is_alive()
        assert not controller.settings()['auto_enabled']
        controller.perform('stop')
        assert controller.state == 'STOPPED' and controller.server is None
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
