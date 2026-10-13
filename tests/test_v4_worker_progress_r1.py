import io
import threading
from pathlib import Path
from contextlib import contextmanager
import pytest
from workbench_desktop.jobs import ProcessDailyJobs
from workbench_analysis.operational_daily_jobs_pg_r1 import DailyJobs


def facade():
    jobs=object.__new__(ProcessDailyJobs)
    jobs.root=Path('G:/codex_tmp/test_temp/worker')
    jobs.readback_url='http://127.0.0.1:28899'
    jobs.admission=threading.RLock();jobs.stop=threading.Event()
    jobs.thread=None
    return jobs


def test_child_command_has_no_tray_or_http_start():
    cmd=facade().command()
    assert '--daily-worker' in cmd and '--readback-url' in cmd
    assert '--task' not in cmd


def test_quiesce_does_not_terminate_publication():
    jobs=facade()
    class Child:
        stdin=io.StringIO()
        def poll(self):return None
    jobs.process=Child()
    jobs.quiesce()
    assert jobs.stop.is_set()
    assert jobs.process.stdin.getvalue()=='QUIESCE\n'
    with pytest.raises(ValueError,match='MAINTENANCE_QUIESCING'):jobs.enqueue()


def test_progress_validates_real_counts():
    jobs=object.__new__(DailyJobs);jobs.active_job_id='job'
    with pytest.raises(ValueError,match='INVALID_PROGRESS_TOTAL'):
        jobs.record_progress('2026-10-13','CORE',dict(processed=4,total=3))
    with pytest.raises(ValueError,match='INVALID_PROGRESS_COUNT'):
        jobs.record_progress('2026-10-13','CORE',dict(processed=True,total=3))


def test_progress_upsert_preserves_stage_start_for_same_stage():
    jobs=object.__new__(DailyJobs);jobs.active_job_id='job';calls=[]
    class DB:
        def execute(self,sql,params):calls.append((sql,params))
    @contextmanager
    def connect():yield DB()
    jobs.connect=connect
    jobs.record_progress('2026-10-13','CORE',dict(processed=100,total=200,unit='securities'))
    sql,params=calls[0]
    assert 'ON CONFLICT(job_id)' in sql
    assert 'THEN update_job_progress.stage_started_at' in sql
    assert params[3:6]==(100,200,'securities')


def test_real_child_safe_control_and_g_temp(monkeypatch):
    import sys
    jobs=facade();jobs.worker_error=None
    code="import os,sys; assert os.environ['TMP']=='G:/codex_tmp'; line=sys.stdin.readline(); assert line.strip()=='QUIESCE'"
    monkeypatch.setattr(jobs,'command',lambda:[sys.executable,'-c',code])
    jobs.start()
    assert jobs.process.pid is not None
    jobs.close(timeout=5)
    assert jobs.process.returncode==0 and not jobs.thread.is_alive()


def test_security_counts_batch_after_completed_work():
    from workbench_analysis.r43_owner_replay import progress_items
    updates=[]
    iterator=progress_items(list(range(450)),updates.append,coordinate_endpoint='2026-10-13',clock=lambda:0)
    assert list(iterator)==list(range(450))
    assert [r['processed'] for r in updates]==[0,200,400,450]
    assert all(r['total']==450 and r['coordinate_endpoint']=='2026-10-13' for r in updates)


def test_security_counts_flush_on_elapsed_time():
    from workbench_analysis.r43_owner_replay import progress_items
    updates=[];ticks=iter([0,1,2,3])
    assert list(progress_items([1,2,3],updates.append,clock=lambda:next(ticks)))==[1,2,3]
    assert [r['processed'] for r in updates]==[0,2,3]
