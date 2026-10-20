from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import threading
import pytest
from workbench_analysis.operational_daily_jobs_pg_r1 import DailyJobs
from workbench_analysis import operational_daily_jobs_v1 as state_machine

@pytest.fixture
def plan(monkeypatch):
    monkeypatch.setattr(state_machine,'gap_plan',lambda *a,**k: dict(status='TIME_ELIGIBLE',requested_through_date='2026-10-09',eligible_target='2026-10-09',eligible_sessions=['2026-10-08','2026-10-09'],missing_sessions=['2026-10-08','2026-10-09'],scheduled_sessions=[],last_good_trade_date='2026-09-30'))

def make(root,executor=None):
    return DailyJobs(root,executor,lambda:datetime.fromisoformat('2026-10-09T22:10+08:00'))

def test_pg_persistence_pause_idempotency_restart(tmp_path,plan):
    jobs=make(tmp_path);jobs.settings(False)
    with ThreadPoolExecutor(max_workers=4) as pool: ids=list(pool.map(lambda _:jobs.enqueue(key='one'),range(8)))
    assert len(set(ids))==1
    restart=make(tmp_path)
    assert not restart.settings()['auto_enabled']
    assert restart.job(ids[0])['status']=='QUEUED'
    assert len(restart.events(ids[0]))==1
    assert not list(tmp_path.rglob('*.sqlite*'))

def test_pg_cancel_preserves_published_and_restart(tmp_path,plan):
    calls=[]
    def execute(day,mode): calls.append(day);jobs.cancel(job);return dict(status='PUBLISHED')
    jobs=make(tmp_path,execute);jobs.settings(False);job=jobs.enqueue()
    jobs.tick();jobs.tick()
    assert calls==['2026-10-08']
    assert jobs.job(job)['status']=='CANCELLED'
    assert jobs.job(job)['days'][0]['state']=='PUBLISHED'
    make(tmp_path,execute).tick()
    assert calls==['2026-10-08']

def test_pg_worker_competition_and_recovery(tmp_path,plan):
    jobs=make(tmp_path);other=make(tmp_path)
    with jobs.worker_lock():
        with pytest.raises(RuntimeError,match='ALREADY_OWNED'):
            with other.worker_lock(): pass
    with other.worker_lock(): pass

def test_pg_retry_does_not_republish_completed_day(tmp_path,plan):
    calls=[];fail=[True]
    def execute(day,mode):
        calls.append(day)
        return dict(status='QA_BLOCKED' if day=='2026-10-09' and fail[0] else 'PUBLISHED')
    jobs=make(tmp_path,execute);jobs.settings(False);job=jobs.enqueue();jobs.tick()
    assert jobs.job(job)['status']=='QA_BLOCKED'
    fail[0]=False;again=make(tmp_path,execute);again.retry(job);again.tick()
    assert calls==['2026-10-08','2026-10-09','2026-10-09']
    assert again.job(job)['status']=='PUBLISHED_FULL'

def test_pg_disconnect_fails_closed_without_file(tmp_path,monkeypatch):
    monkeypatch.setenv('V4_NATIVE_PG_DSN','host=127.0.0.1 port=1 user=r4_isolated_admin dbname=postgres')
    from tests.v4_native_isolation_plugin_r4 import V4DatabaseGuardViolation
    with pytest.raises(V4DatabaseGuardViolation): make(tmp_path)
    assert not list(tmp_path.rglob('*'))

def test_guard_cannot_satisfy_business_exception():
    import sqlite3
    from tests.v4_native_isolation_plugin_r4 import V4DatabaseGuardViolation
    with pytest.raises(V4DatabaseGuardViolation):
        with pytest.raises(Exception): sqlite3.connect(':memory:')

def test_desktop_uses_pg_store(tmp_path,plan):
    from workbench_desktop.jobs import ManagedDailyJobs
    jobs=ManagedDailyJobs(tmp_path,clock=lambda:datetime.fromisoformat('2026-10-09T22:10+08:00'))
    jobs.settings(False);job=jobs.enqueue();jobs.cancel(job)
    assert jobs.job(job)['status']=='CANCELLED'
    assert jobs.schema == 'v4'
