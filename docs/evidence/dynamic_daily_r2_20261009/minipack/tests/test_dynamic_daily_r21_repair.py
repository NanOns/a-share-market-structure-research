"""R2.1 isolated queue and readiness injections; no production DB/network."""
from datetime import datetime
import json
import pytest
from workbench_analysis.operational_daily_jobs_v1 import DailyJobs
from workbench_analysis.source_readiness_v2 import source_readiness
import workbench_analysis.operational_daily_jobs_v1 as jobs_module
import workbench_analysis.operational_daily_executor_v1 as executor


@pytest.fixture
def queue(tmp_path,monkeypatch):
    monkeypatch.setattr(jobs_module,'gap_plan',lambda *a,**k:dict(status='TIME_ELIGIBLE',
        requested_through_date='2026-10-09',missing_sessions=['2026-10-08','2026-10-09'],
        eligible_sessions=['2026-10-08','2026-10-09'],last_good_trade_date='2026-09-30'))
    rev=['a'];calls=[];outcome=['FAILED_TERMINAL']
    q=DailyJobs(tmp_path,lambda d,m:(calls.append(d) or dict(status=outcome[0])),
        lambda:datetime.fromisoformat('2026-10-09T22:10:00+08:00'))
    monkeypatch.setattr(q,'source_revision',lambda _:rev[0])
    return q,rev,calls,outcome


def test_terminal_changed_source_creates_successor_preserves_history(queue):
    q,rev,calls,outcome=queue;q.tick()
    with q.connect() as db:old=db.execute('SELECT job_id FROM scheduler_dispatch').fetchone()[0]
    q.tick();assert calls==['2026-10-08']
    rev[0]='b';outcome[0]='PUBLISHED';q.tick()
    with q.connect() as db:
        rows=db.execute('SELECT * FROM scheduler_attempts ORDER BY attempt_ordinal').fetchall()
    assert len(rows)==2 and rows[1]['old_job_id']==old
    assert q.job(old)['status']=='FAILED_TERMINAL'
    assert calls==['2026-10-08','2026-10-08','2026-10-09']


def test_user_cancel_pause_rearm(queue):
    q,rev,calls,outcome=queue
    job=q.enqueue(trigger='SCHEDULER');q.cancel(job);rev[0]='b';q.tick();assert not calls
    q.rearm('2026-10-09','operator-1');q.settings(False);q.tick();assert not calls
    q.settings(True);q.tick();assert calls==['2026-10-08']


def test_system_interruption_recovers(queue):
    q,rev,calls,outcome=queue;q.tick()
    with q.connect() as db:db.execute("UPDATE update_jobs SET status='INTERRUPTED'")
    outcome[0]='PUBLISHED';q.tick();assert len(calls)==3


def test_attempt_budget_stops_until_explicit_rearm(queue):
    q,rev,calls,outcome=queue
    for n in range(12):rev[0]=str(n);q.tick()
    assert len(calls)==8
    q.rearm('2026-10-09','authorized');q.tick();assert len(calls)==9


def test_migration_preserves_legacy_dispatch(queue):
    q,rev,calls,outcome=queue;old=q.enqueue(trigger='SCHEDULER')
    with q.connect() as db:
        db.execute("UPDATE update_jobs SET status='FAILED_TERMINAL'")
        db.execute('INSERT INTO scheduler_dispatch VALUES(?,?)',('2026-10-09',old))
    q.tick();assert not calls
    rev[0]='new';q.tick();assert calls==['2026-10-08']
    assert q.job(old)['status']=='FAILED_TERMINAL'


def test_manual_retry_scheduler_collision_one_executor(queue):
    q,rev,calls,outcome=queue;q.tick()
    with q.connect() as db:old=db.execute('SELECT job_id FROM scheduler_dispatch').fetchone()[0]
    manual=q.retry(old);rev[0]='b';outcome[0]='PUBLISHED';q.tick()
    assert q.job(old)['status']=='FAILED_TERMINAL' and q.job(manual)['status']=='PUBLISHED_FULL'
    assert calls==['2026-10-08','2026-10-08','2026-10-09']
    with q.connect() as db:
        adopted=db.execute('SELECT * FROM scheduler_attempts WHERE job_id=?',(manual,)).fetchone()
    assert adopted['old_job_id']==old and adopted['attempt_ordinal']==2


def test_bounded_recovery_probe_has_persistent_cooldown(queue,monkeypatch):
    q,rev,calls,outcome=queue;probes=[]
    monkeypatch.setattr(q,'source_revision',jobs_module.DailyJobs.source_revision.__get__(q))
    q.source_probe=lambda d:(probes.append(d) or dict(verified=True,revision='fixture-proof',source_ready=False))
    q.tick();q.tick();assert probes==['2026-10-09']
    assert len(calls)==1


def proofs():
    common=dict(status='VERIFIED',target_session='2026-10-09',source_sha256='a'*64,
        observed_at='2026-10-09T18:35:00+08:00',provider_date='2026-10-09',row_count=1)
    return dict(tdx=dict(common,bars_date_coverage=['2026-10-09']),
        baostock_daily=dict(common,identity_reconciliation_passed=True),baostock_factor=dict(common))


@pytest.mark.parametrize('name',['tdx','baostock_daily','baostock_factor'])
def test_missing_source_fails_closed(name):
    p=proofs();p.pop(name)
    assert not source_readiness('2026-10-09',datetime.fromisoformat('2026-10-09T19:00+08:00'),p)['source_ready']


def test_zero_factor_requires_readable_digest_and_revision_changes():
    p=proofs();now=datetime.fromisoformat('2026-10-09T19:00+08:00')
    p['baostock_factor'].update(row_count=0,provider_date=None,verified_no_change=True)
    assert not source_readiness('2026-10-09',now,p)['source_ready']
    p['baostock_factor'].update(proof_target_session='2026-10-09',no_change_proof_sha256='b'*64)
    first=source_readiness('2026-10-09',now,p);assert first['source_ready']
    p['tdx']['source_sha256']='c'*64
    assert first['source_revision_id']!=source_readiness('2026-10-09',now,p)['source_revision_id']


def test_executor_1834_blocks_before_any_capture(tmp_path,monkeypatch):
    class Clock(datetime):
        @classmethod
        def now(cls,tz=None):return datetime.fromisoformat('2026-10-09T18:34+08:00')
    monkeypatch.setattr(executor,'datetime',Clock)
    monkeypatch.setattr(executor,'capture_latest_tdx_package',lambda **k:pytest.fail('CAPTURE_BEFORE_TIME_GATE'))
    result=executor.execute_sources(tmp_path,'2026-10-09','CATCH_UP',capture_only=True)
    assert not result['source_ready']


@pytest.mark.parametrize('mutation,expected',[
    ('good','SOURCE_READY'),('wrong_daily_date','WAIT_BAOSTOCK_DAILY'),
    ('suspended_with_bar','WAIT_BAOSTOCK_DAILY'),('no_daily','WAIT_BAOSTOCK_DAILY')])
def test_real_gate_reads_frozen_bytes_before_deriving(tmp_path,mutation,expected):
    from hashlib import sha256
    from workbench_analysis.operational_daily_storage_v1 import atomic_json
    day='2026-10-09';observed=day+'T18:35:00+08:00'
    row=dict(code='SH.600000',date=day,tradestatus='1',open=10,high=11,low=9,close=10,volume=1)
    native=dict(row,source_security_key=row['code'])
    if mutation=='wrong_daily_date':row['date']='2026-10-08'
    if mutation=='suspended_with_bar':row['tradestatus']='0'
    daily=[] if mutation=='no_daily' else [row]
    def write(name,payload):
        path=tmp_path/name;atomic_json(tmp_path,path,payload)
        return dict(path=str(path),sha256=sha256(path.read_bytes()).hexdigest())
    artifact=dict(native_baostock=write('raw.json',dict(observed_at=observed)),
        tdx=write('bars.json',dict(target_bars=[native])),observed_at=observed,
        effective_package=dict(provider_package_date=day),
        normalized=dict(daily=dict(rows=daily),adjustment_factor=dict(rows=[])))
    result,ready=executor.verify_source_gate(tmp_path,day,artifact,dict(source_freeze={'sha256':'a'*64}),
        datetime.fromisoformat(day+'T19:00:00+08:00'))
    assert ready['status']==expected
    assert result['source_ready']==(expected=='SOURCE_READY')
    assert (tmp_path/result['source_readiness']['path']).is_file()
