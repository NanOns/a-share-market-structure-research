from datetime import datetime
import os
import pytest
import psycopg
from workbench_analysis.operational_daily_jobs_pg_r1 import DailyJobs
from workbench_analysis import operational_daily_jobs_v1 as state
from workbench_desktop.jobs import ManagedDailyJobs

@pytest.fixture
def jobs(tmp_path,monkeypatch):
    with psycopg.connect(os.environ['V4_NATIVE_PG_DSN']) as db:
        assert str(db.execute('SELECT system_identifier FROM pg_control_system()').fetchone()[0])=='7695278778933357404'
    monkeypatch.delenv('V4_NATIVE_PG_READER_DSN',raising=False)
    monkeypatch.setattr(state,'gap_plan',lambda *a,**k:dict(status='TIME_ELIGIBLE',requested_through_date='2026-10-13',eligible_target='2026-10-13',eligible_sessions=['2026-10-13'],missing_sessions=['2026-10-13'],scheduled_sessions=[],last_good_trade_date='2026-10-12'))
    clock=lambda:datetime.fromisoformat('2026-10-13T22:10+08:00')
    result=DailyJobs(tmp_path,clock=clock);result.settings(False)
    return result


def test_pg_progress_checkpoint_and_terminal_error(jobs):
    job=jobs.enqueue();jobs.active_job_id=job
    jobs.checkpoint('2026-10-13','CORE',dict(processed=100,total=5225,unit='securities'))
    first=jobs.progress()
    jobs.checkpoint('2026-10-13','CORE',dict(processed=200,total=5225,unit='securities'))
    latest=jobs.progress()
    assert latest['processed']==200 and latest['stage_started_at']==first['stage_started_at']
    assert latest['eta_seconds'] is None
    with jobs.connect() as db:
        db.execute("UPDATE update_jobs SET status='FAILED_TERMINAL',error='PG_PUBLISH_FAILED' WHERE job_id=?",(job,))
    assert jobs.progress()['error_code']=='PG_PUBLISH_FAILED'
    assert jobs.progress()['head_unchanged'] is True


def test_pg_maintenance_recovery_cannot_steal_writer(jobs):
    with jobs.worker_lock():
        with pytest.raises(RuntimeError,match='ALREADY_OWNED'):
            ManagedDailyJobs(jobs.root,clock=jobs.clock)
    other=ManagedDailyJobs(jobs.root,clock=jobs.clock)
    assert other.settings()['auto_enabled'] is False


def test_pg_paused_cancelled_not_rearmed_on_restart(jobs):
    job=jobs.enqueue();jobs.cancel(job)
    other=ManagedDailyJobs(jobs.root,clock=jobs.clock)
    other.original_executor=lambda *a:pytest.fail('cancelled or paused scheduler executed')
    other.tick()
    assert other.job(job)['status']=='CANCELLED'
    assert other.settings()['auto_enabled'] is False


def test_pg_worker_lock_release_on_crash(jobs):
    import subprocess,sys
    code="import psycopg,sys; db=psycopg.connect(sys.argv[1],autocommit=True); assert db.execute('SELECT pg_try_advisory_lock(%s)',(int(sys.argv[2]),)).fetchone()[0]; print('READY',flush=True); sys.stdin.readline(); sys.exit(3)"
    # Hold a lock in another process, reject a competing writer, then crash.
    child=subprocess.Popen([sys.executable,'-c',code,jobs.dsn,str(jobs.lock_key^1)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    try:
        assert child.stdout.readline().strip()=='READY'
        with pytest.raises(RuntimeError,match='ALREADY_OWNED'):
            with jobs.worker_lock():pass
    finally:
        child.communicate('CRASH\n',timeout=5)
    assert child.returncode==3
    with jobs.worker_lock():pass


def running(jobs):
    job=jobs.enqueue();jobs.active_job_id=job
    with jobs.connect() as db:
        db.execute("UPDATE update_jobs SET status='RUNNING' WHERE job_id=?",(job,))
    return job


def test_pg_cancel_before_boundary_prevents_publishing_checkpoint(jobs):
    job=running(jobs);jobs.cancel(job)
    jobs.checkpoint('2026-10-13','PUBLISHING',{})
    assert jobs.job(job)['status']=='CANCEL_REQUESTED'
    assert jobs.job(job)['days'][0]['state']!='PUBLISHING'
    assert jobs.publication_cancelled()


def test_pg_cancel_after_boundary_rejected_without_changing_job(jobs):
    job=running(jobs);jobs.checkpoint('2026-10-13','PUBLISHING',{})
    with pytest.raises(ValueError,match='PUBLICATION_SAFE_BOUNDARY'):jobs.cancel(job)
    assert jobs.job(job)['status']=='PUBLISHING'
    assert jobs.publication_cancelled() is False


def test_pg_concurrent_cancel_boundary_has_one_unambiguous_winner(jobs):
    from concurrent.futures import ThreadPoolExecutor
    import threading
    job=running(jobs);barrier=threading.Barrier(2)
    def cancel():
        barrier.wait()
        try:jobs.cancel(job);return 'CANCEL_ACCEPTED'
        except ValueError as exc:return str(exc)
    def publish():barrier.wait();jobs.checkpoint('2026-10-13','PUBLISHING',{})
    with ThreadPoolExecutor(max_workers=2) as pool:
        cancelled=pool.submit(cancel);published=pool.submit(publish)
        outcome=cancelled.result();published.result()
    status=jobs.job(job)['status']
    assert (status,outcome) in {('PUBLISHING','PUBLICATION_SAFE_BOUNDARY'),('CANCEL_REQUESTED','CANCEL_ACCEPTED')}


def test_pg_progress_actual_mode_survives_later_checkpoints(jobs):
    job=running(jobs)
    jobs.checkpoint('2026-10-13','CORE',dict(mode='APPEND_DAY',processed=1,total=2))
    jobs.checkpoint('2026-10-13','QA',{})
    result=jobs.progress()
    assert result['mode']=='APPEND_DAY' and result['job_mode']=='CATCH_UP'


@pytest.mark.parametrize('terminal',['FAILED_TERMINAL','CANCELLED','INTERRUPTED','QA_BLOCKED'])
def test_pg_terminal_elapsed_stops_and_finished_time_is_idempotent(jobs,terminal):
    job=running(jobs)
    with jobs.connect() as db:
        db.execute('UPDATE update_jobs SET status=? WHERE job_id=?',(terminal,job))
    jobs.record_progress('2026-10-13',terminal,{})
    first=jobs.progress()
    assert first['finished_at'] is not None
    jobs.record_progress('2026-10-13',terminal,{})
    second=jobs.progress()
    assert second['finished_at']==first['finished_at']
    assert second['elapsed_seconds']==first['elapsed_seconds']
