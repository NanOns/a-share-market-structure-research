"""Real supported scheduler imports and worker/HTTP integration, isolated PG only."""
from datetime import datetime
import json
from pathlib import Path
import threading
from http.server import ThreadingHTTPServer
from urllib.request import urlopen
import pytest

SOURCE = Path('G:/codex_tmp/test_temp/r4_batch2_default_product')

def test_historical_public_import_is_native_pg(tmp_path):
    from workbench_analysis.operational_daily_jobs_v1 import DailyJobs
    from workbench_analysis.operational_daily_jobs_pg_r1 import DailyJobs as Native
    jobs = DailyJobs(tmp_path)
    assert type(jobs) is Native
    assert jobs.settings()['auto_enabled']
    assert not list(tmp_path.rglob('*.sqlite*'))

def test_public_import_without_dsn_fails_closed(tmp_path, monkeypatch):
    from workbench_analysis.operational_daily_jobs_v1 import DailyJobs
    monkeypatch.delenv('V4_NATIVE_PG_DSN')
    with pytest.raises(RuntimeError, match='NO_FALLBACK'):
        DailyJobs(tmp_path)
    assert not list(tmp_path.rglob('*'))

def test_historical_subclass_cannot_reopen_sqlite(tmp_path):
    from workbench_analysis.operational_daily_jobs_v1 import DailyJobs
    class CustomJobs(DailyJobs):
        pass
    jobs=CustomJobs(tmp_path)
    assert jobs.settings(False)['auto_enabled'] is False
    with jobs.worker_lock():
        assert jobs.schema == 'v4'
    assert not list(tmp_path.rglob('*.sqlite*'))

@pytest.mark.parametrize('desktop', [False, True])
def test_real_worker_real_executor_accepted_noop_and_http(tmp_path, desktop):
    # Durable restart fixture, not fabricated FIRST_OBSERVED or new publication.
    from workbench_analysis.operational_daily_executor_v1 import execute_sources
    from workbench_analysis.operational_daily_jobs_v1 import DailyJobs
    from workbench_desktop.jobs import ManagedDailyJobs
    from workbench_service.core_product_server_r1 import make_product_handler
    if not (SOURCE/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json').exists():
        pytest.fail('FROZEN_DEFAULT_PRODUCT_SOURCE_REQUIRED')
    head=(SOURCE/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json').read_bytes()
    day=json.loads(head)['accepted_trade_date']
    complete=threading.Event()
    receipts=[]
    def real_executor(target, mode):
        result=execute_sources(SOURCE,target,mode)
        receipts.append(result)
        complete.set()
        return result
    jobs=(ManagedDailyJobs if desktop else DailyJobs)(tmp_path, real_executor)
    jobs.settings(False)
    with jobs.connect() as db:
        db.execute('INSERT INTO update_jobs VALUES(?,?,?,?,?,?,?,?,?)',
                   ('restart-noop','MANUAL','CATCH_UP',day,'QUEUED',datetime.now().astimezone().isoformat(),None,'restart-noop',None))
        db.execute('INSERT INTO update_job_days(job_id,trade_date,state) VALUES(?,?,?)',('restart-noop',day,'QUEUED'))
    server=ThreadingHTTPServer(('127.0.0.1',0),make_product_handler(SOURCE,jobs))
    http=threading.Thread(target=server.serve_forever);http.start()
    try:
        jobs.start()
        with pytest.raises(ValueError,match='WORKER_ALREADY_RUNNING'):
            jobs.start()
        assert complete.wait(10), jobs.worker_error
        jobs.close(timeout=10)
        assert receipts==[dict(status='PUBLISHED',reason='NOOP_ALREADY_CURRENT',accepted_trade_date=day,recovered_after_cas=True)]
        assert jobs.job('restart-noop')['status']=='PUBLISHED_FULL'
        with urlopen(f'http://127.0.0.1:{server.server_port}/api/v4/operations/daily-update/settings') as response:
            assert json.loads(response.read())['auto_enabled'] is False
        assert head==(SOURCE/'data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json').read_bytes()
        assert not list(tmp_path.rglob('*.sqlite*'))
    finally:
        jobs.close(timeout=10)
        server.shutdown();http.join();server.server_close()

def test_worker_close_reports_unsafe_boundary(tmp_path):
    from workbench_analysis.operational_daily_jobs_v1 import DailyJobs
    jobs=DailyJobs(tmp_path);entered=threading.Event();release=threading.Event()
    def slow_tick():
        entered.set();release.wait(10)
    jobs.tick=slow_tick
    jobs.start()
    try:
        assert entered.wait(5)
        with pytest.raises(TimeoutError,match='WAITING_SAFE_BOUNDARY'):
            jobs.close(timeout=0.01)
    finally:
        release.set();jobs.close(timeout=5)
