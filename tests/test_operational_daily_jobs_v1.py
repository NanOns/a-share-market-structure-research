from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import json,threading,urllib.request,urllib.error
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import pytest
from workbench_analysis.operational_daily_jobs_v1 import DailyJobs
import workbench_analysis.operational_daily_jobs_v1 as module
import workbench_service.operational_daily_server_v1 as http


@pytest.fixture
def plan(monkeypatch):
    def fake(root,now,through=None):
        return dict(status='TIME_ELIGIBLE',requested_through_date=through or '2026-10-09',
          eligible_target='2026-10-09',eligible_sessions=['2026-10-08','2026-10-09'],
          missing_sessions=['2026-10-08','2026-10-09'],scheduled_sessions=[],
          last_good_trade_date='2026-09-30')
    monkeypatch.setattr(module,'gap_plan',fake)


def test_persistent_default_pause_restart(tmp_path,plan):
    clock=lambda:datetime.fromisoformat('2026-10-09T22:10+08:00')
    jobs=DailyJobs(tmp_path,clock=clock)
    assert jobs.settings()['auto_enabled'] and not jobs.settings()['service_alive']
    jobs.settings(False);again=DailyJobs(tmp_path,clock=clock)
    assert not again.settings()['auto_enabled']
    assert len(again.events(again.enqueue(key='manual')))==1


def test_cancel_after_success_keeps_publication_and_stops_next_day(tmp_path,plan):
    calls=[]
    def executor(day,mode):
        calls.append(day);jobs.cancel(job)
        return dict(status='PUBLISHED',evidence_kind='SIMULATED_EXECUTOR_ONLY')
    jobs=DailyJobs(tmp_path,executor,lambda:datetime.fromisoformat('2026-10-09T22:10+08:00'))
    jobs.settings(False);job=jobs.enqueue();jobs.tick();jobs.tick()
    assert calls==['2026-10-08']
    assert jobs.job(job)['status']=='CANCELLED'
    assert jobs.job(job)['days'][0]['state']=='PUBLISHED'


@pytest.mark.parametrize('count',[1,2,5,10,20])
def test_gap_order_restart_and_no_republish(tmp_path,monkeypatch,count):
    # Simulated sources/executor; the durable queue and restart are real.
    from test_operational_daily_calendar_v2 import calendar
    dates=calendar()['session_dates'][1:count+1]
    monkeypatch.setattr(module,'gap_plan',lambda *a,**k:dict(status='TIME_ELIGIBLE',requested_through_date=dates[-1],
        missing_sessions=dates,eligible_sessions=dates,last_good_trade_date='2026-09-01'))
    calls=[];failed=[True]
    def executor(day,mode):
        calls.append(day)
        return dict(status='QA_BLOCKED' if day==dates[-1] and failed[0] else 'PUBLISHED',
                    evidence_kind='SIMULATED_SOURCE_AND_OWNER_ONLY')
    clock=lambda:datetime.fromisoformat('2026-12-01T22:10+08:00')
    jobs=DailyJobs(tmp_path,executor,clock);jobs.settings(False);job=jobs.enqueue();jobs.tick()
    assert calls==dates and jobs.job(job)['status']=='QA_BLOCKED'
    failed[0]=False;restart=DailyJobs(tmp_path,executor,clock);restart.retry(job);restart.tick()
    assert calls==dates+[dates[-1]] and restart.job(job)['status']=='PUBLISHED_FULL'


def test_concurrent_idempotency_and_days(tmp_path,plan):
    jobs=DailyJobs(tmp_path)
    with ThreadPoolExecutor(max_workers=4) as pool:
        ids=list(pool.map(lambda _:jobs.enqueue(key='same-key'),range(4)))
    assert len(set(ids))==1
    assert [d['trade_date'] for d in jobs.job(ids[0])['days']]==['2026-10-08','2026-10-09']


def test_sequential_failure_retains_success_and_retry_only_failed(tmp_path,plan):
    calls=[];fail=[True]
    def executor(day,mode):
        calls.append(day)
        return dict(status='QA_BLOCKED' if day=='2026-10-09' and fail[0] else 'PUBLISHED',
                    evidence_kind='SIMULATED_EXECUTOR_ONLY')
    jobs=DailyJobs(tmp_path,executor,lambda:datetime.fromisoformat('2026-10-09T22:10+08:00'))
    job=jobs.enqueue();jobs.tick();jobs.tick()
    assert calls==['2026-10-08','2026-10-09']
    assert jobs.job(job)['days'][0]['state']=='PUBLISHED'
    fail[0]=False;jobs.retry(job);jobs.tick()
    assert calls==['2026-10-08','2026-10-09','2026-10-09']
    assert jobs.job(job)['status']=='PUBLISHED_FULL'


def test_source_wait_then_resume(tmp_path,plan):
    now=[datetime.fromisoformat('2026-10-09T18:35+08:00')];calls=[]
    def executor(day,mode):
        calls.append(day)
        return dict(status='WAIT_BAOSTOCK_FACTOR' if len(calls)==1 else 'PROBED')
    jobs=DailyJobs(tmp_path,executor,lambda:now[0]);job=jobs.enqueue(mode='PROBE')
    # Catch-up mode exercises the real retry clock (probe bypasses time gates).
    with jobs.connect() as db:db.execute("UPDATE update_jobs SET mode='CATCH_UP' WHERE job_id=?",(job,))
    jobs.tick();jobs.tick();assert len(calls)==1
    assert jobs.job(job)['days'][0]['next_retry_at']=='2026-10-09T19:05:00+08:00'
    now[0]=datetime.fromisoformat('2026-10-09T19:05+08:00');jobs.tick()
    assert len(calls)==3


def test_restart_recovers_running_checkpoint(tmp_path,plan):
    jobs=DailyJobs(tmp_path);job=jobs.enqueue()
    with jobs.connect() as db:
        db.execute("UPDATE update_jobs SET status='RUNNING' WHERE job_id=?",(job,))
    calls=[]
    restart=DailyJobs(tmp_path,lambda day,mode:(calls.append(day) or dict(status='QA_BLOCKED')),
                      lambda:datetime.fromisoformat('2026-10-09T22:10+08:00'))
    restart.tick();assert calls==['2026-10-08']
    assert restart.job(job)['status']=='QA_BLOCKED'


def test_probe_never_claims_publication(tmp_path,plan):
    jobs=DailyJobs(tmp_path,lambda day,mode:dict(status='PROBED'),lambda:datetime.fromisoformat('2026-10-09T16:00+08:00'))
    job=jobs.enqueue(mode='PROBE');jobs.settings(False);jobs.tick()
    assert jobs.job(job)['status']=='PROBE_COMPLETE'


def test_waiting_daily_job_does_not_block_probe(tmp_path,plan):
    jobs=DailyJobs(tmp_path,lambda day,mode:dict(status='PROBED'),
                   lambda:datetime.fromisoformat('2026-10-09T16:00+08:00'))
    jobs.settings(False)
    catchup=jobs.enqueue(mode='CATCH_UP');probe=jobs.enqueue(mode='PROBE')
    with jobs.connect() as db:
        db.execute('UPDATE update_job_days SET next_retry_at=? WHERE job_id=?',('2026-10-09T18:35:00+08:00',catchup))
    jobs.tick()
    assert jobs.job(probe)['status']=='PROBE_COMPLETE'
    assert jobs.job(catchup)['status']=='QUEUED'


def test_http_capability_and_durable_202(tmp_path,plan,monkeypatch):
    class Base(BaseHTTPRequestHandler):
        def send(self,code,payload,content_type='application/json'):
            raw=json.dumps(payload).encode();self.send_response(code);self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
        def log_message(self,*a):pass
    monkeypatch.setattr(http,'make_v4_handler',lambda root:Base)
    jobs=DailyJobs(tmp_path);server=ThreadingHTTPServer(('127.0.0.1',0),http.make_daily_handler(tmp_path,jobs))
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    url=f'http://127.0.0.1:{server.server_port}'+http.PREFIX+'/jobs'
    try:
        request=urllib.request.Request(url,data=b'{}',headers={'Idempotency-Key':'test'})
        with pytest.raises(urllib.error.HTTPError) as failure:urllib.request.urlopen(request)
        assert failure.value.code==403
        request.add_header('X-V4-Operation','daily-update')
        request.add_header('Origin','https://hostile.invalid')
        with pytest.raises(urllib.error.HTTPError) as failure:urllib.request.urlopen(request)
        assert failure.value.code==403
        request.remove_header('Origin')
        with urllib.request.urlopen(request) as response:
            assert response.status==202;job=json.load(response)['job_id']
        assert DailyJobs(tmp_path).job(job)['status']=='QUEUED'
    finally:server.shutdown();server.server_close();thread.join()
