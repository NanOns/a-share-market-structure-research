"""R2.1 isolated queue and readiness injections; no production DB/network."""
from datetime import datetime
import json
import subprocess,types
from pathlib import Path
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


def test_frozen_baseline_and_repair_use_identical_failure_source_restore_fixture(tmp_path,monkeypatch):
    baseline='851770b1932d95836ce76bb44fd292117958bf04'
    source=subprocess.check_output(['git','show',baseline+':src/workbench_analysis/operational_daily_jobs_v1.py'],cwd=Path(__file__).resolve().parents[1])
    old=types.ModuleType('workbench_analysis.r21_frozen_jobs')
    old.__package__='workbench_analysis';exec(compile(source,'frozen_baseline_jobs.py','exec'),old.__dict__)
    plan=lambda *a,**k:dict(status='TIME_ELIGIBLE',requested_through_date='2026-10-09',missing_sessions=['2026-10-08','2026-10-09'],eligible_sessions=['2026-10-08','2026-10-09'],last_good_trade_date='2026-09-30')
    monkeypatch.setattr(old,'gap_plan',plan);monkeypatch.setattr(jobs_module,'gap_plan',plan)
    results=[]
    for label,klass in [('FROZEN_BASELINE',old.DailyJobs),('REPAIRED',DailyJobs)]:
        state={'source':'unavailable'};calls=[]
        def execute(day,mode):
            calls.append(day)
            return dict(status='FAILED_TERMINAL' if state['source']=='unavailable' else 'PUBLISHED')
        q=klass(tmp_path/label,execute,lambda:datetime.fromisoformat('2026-10-09T22:10:00+08:00'))
        if hasattr(q,'source_revision'):monkeypatch.setattr(q,'source_revision',lambda _:state['source'])
        q.tick();q.tick();state['source']='restored';q.tick()
        results.append(dict(version=label,calls=list(calls)))
        assert calls==(['2026-10-08'] if label=='FROZEN_BASELINE' else ['2026-10-08','2026-10-08','2026-10-09'])
        q.close()
    print(json.dumps(dict(case='IDENTICAL_TERMINAL_FAILURE_SOURCE_RESTORE',baseline_sha=baseline,evidence_kind='ISOLATED_INJECTION',results=results)))


def test_actual_frozen_schema_upgrade_and_old_reader_preserve_history(tmp_path,monkeypatch):
    source=subprocess.check_output(['git','show','851770b1932d95836ce76bb44fd292117958bf04:src/workbench_analysis/operational_daily_jobs_v1.py'],cwd=Path(__file__).resolve().parents[1])
    old=types.ModuleType('workbench_analysis.r21_legacy_schema');old.__package__='workbench_analysis'
    exec(compile(source,'frozen_legacy_schema.py','exec'),old.__dict__)
    plan=lambda *a,**k:dict(status='TIME_ELIGIBLE',requested_through_date='2026-10-09',missing_sessions=['2026-10-09'],eligible_sessions=['2026-10-09'],last_good_trade_date='2026-10-08')
    monkeypatch.setattr(old,'gap_plan',plan);monkeypatch.setattr(jobs_module,'gap_plan',plan)
    clock=lambda:datetime.fromisoformat('2026-10-09T22:10:00+08:00')
    legacy=old.DailyJobs(tmp_path,lambda *a:dict(status='FAILED_TERMINAL'),clock);legacy.tick()
    with legacy.connect() as db:
        before={table:[tuple(r) for r in db.execute('SELECT * FROM '+table)] for table in ('update_jobs','update_job_days','update_events')}
        assert db.execute('PRAGMA journal_mode').fetchone()[0]=='wal'
    legacy.close();q=DailyJobs(tmp_path,lambda *a:dict(status='PUBLISHED'),clock)
    revision=['a'];monkeypatch.setattr(q,'source_revision',lambda _:revision[0]);q.tick();revision[0]='b';q.tick();q.close()
    downgrade=old.DailyJobs(tmp_path,clock=clock)
    with downgrade.connect() as db:
        for table,original in before.items():
            current=[tuple(r) for r in db.execute('SELECT * FROM '+table)]
            assert all(row in current for row in original)
        assert db.execute('SELECT COUNT(*) FROM scheduler_attempts').fetchone()[0]==2
    assert downgrade.job(before['update_jobs'][0][0])['status']=='FAILED_TERMINAL'
    downgrade.close()
    print(json.dumps(dict(case='ACTUAL_FROZEN_SCHEMA_UPGRADE_OLD_READER_ROLLBACK',evidence_kind='ISOLATED_INJECTION',original_history_preserved=True,scheduler_attempts_preserved=2)))


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


def test_failed_probe_health_clears_after_verified_recovery(tmp_path):
    now=[datetime.fromisoformat('2026-10-09T22:10:00+08:00')]
    def probe(day):
        if now[0].minute==10:raise OSError('FIXTURE_PROVIDER_OFFLINE')
        return dict(verified=True,revision='restored')
    q=DailyJobs(tmp_path,clock=lambda:now[0],source_probe=probe)
    q.source_revision('2026-10-09')
    now[0]=datetime.fromisoformat('2026-10-09T22:45:00+08:00')
    assert q.source_revision('2026-10-09')
    receipt=json.loads((tmp_path/'runtime/dynamic_daily/recovery_probes/2026-10-09.json').read_bytes())
    assert receipt['probe_state']=='VERIFIED'


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
    ('suspended_with_bar','WAIT_BAOSTOCK_DAILY'),('no_daily','WAIT_BAOSTOCK_DAILY'),
    ('wrong_factor_date','WAIT_BAOSTOCK_FACTOR'),('missing_zero_query_proof','WAIT_BAOSTOCK_FACTOR'),
    ('wrong_native_bar_date','WAIT_TDX')])
def test_real_gate_reads_frozen_bytes_before_deriving(tmp_path,mutation,expected):
    from hashlib import sha256
    from workbench_analysis.operational_daily_storage_v1 import atomic_json
    day='2026-10-09';observed=day+'T18:35:00+08:00'
    row=dict(code='SH.600000',date=day,tradestatus='1',open=10,high=11,low=9,close=10,volume=1)
    native=dict(row,source_security_key=row['code'],trade_date=day)
    if mutation=='wrong_daily_date':row['date']='2026-10-08'
    if mutation=='suspended_with_bar':row['tradestatus']='0'
    if mutation=='wrong_native_bar_date':native['trade_date']='2026-10-08'
    daily=[] if mutation=='no_daily' else [row]
    factors=[dict(dividOperateDate='2026-10-08')] if mutation=='wrong_factor_date' else []
    factor_metadata={} if mutation=='missing_zero_query_proof' else dict(error_code='0')
    def write(name,payload):
        path=tmp_path/name;atomic_json(tmp_path,path,payload)
        return dict(path=str(path),sha256=sha256(path.read_bytes()).hexdigest())
    artifact=dict(native_baostock=write('raw.json',dict(observed_at=observed,target_date=day,adjustment_factor_rows=factors,adjustment_factor_metadata=factor_metadata)),
        tdx=write('bars.json',dict(target_bars=[native])),observed_at=observed,
        effective_package=dict(provider_package_date=day),
        normalized=dict(daily=dict(rows=daily),adjustment_factor=dict(rows=factors)))
    result,ready=executor.verify_source_gate(tmp_path,day,artifact,dict(source_freeze={'sha256':'a'*64}),
        datetime.fromisoformat(day+'T19:00:00+08:00'))
    assert ready['status']==expected
    assert result['source_ready']==(expected=='SOURCE_READY')
    assert (tmp_path/result['source_readiness']['path']).is_file()
