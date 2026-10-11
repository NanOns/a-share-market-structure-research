import json
from pathlib import Path
import hashlib
import shutil
import psycopg
import pytest
from concurrent.futures import ThreadPoolExecutor
from workbench_db.v4_journal_pg_r1 import JournalConnection,open_read
from workbench_db.v4_job_migration_r1 import import_oracle
from workbench_analysis.operational_daily_jobs_pg_r1 import DailyJobs
from workbench_db.v4_native import connection

def test_native_journal_copy_on_write_failure_and_immutable_snapshot(tmp_path):
    path=tmp_path/'journal.pg.json'
    db=JournalConnection(path,tmp_path,'R4_TEST_JOURNAL')
    db.execute('BEGIN IMMEDIATE')
    db.execute('INSERT INTO days VALUES(?,?,?)',('2026-10-08','a'*64,'[]'))
    db.execute("INSERT OR REPLACE INTO metadata VALUES('head',?)",('HEAD_ONE',))
    db.commit();db.close();before=path.read_bytes()
    with open_read(path) as old:assert old.execute('SELECT count(*) FROM days').fetchone()[0]==1
    failed=JournalConnection(path,tmp_path,'R4_TEST_JOURNAL')
    failed.execute('INSERT INTO days VALUES(?,?,?)',('2026-10-09','b'*64,'[]'));failed.rollback();failed.close()
    assert path.read_bytes()==before
    again=JournalConnection(path,tmp_path,'R4_TEST_JOURNAL')
    again.execute('INSERT INTO days VALUES(?,?,?)',('2026-10-09','b'*64,'[]'))
    again.execute("INSERT OR REPLACE INTO metadata VALUES('head',?)",('HEAD_TWO',));again.commit();again.close()
    old_descriptor=json.loads(before)
    with connection(old_descriptor['schema'],read_only=True) as pg:assert pg.execute('SELECT count(*) FROM days').fetchone()[0]==1
    with open_read(path) as new:assert new.execute('SELECT count(*) FROM days').fetchone()[0]==2
    with pytest.raises(psycopg.Error,match='IMMUTABLE'):
        with connection(old_descriptor['schema']) as pg:pg.execute('DELETE FROM days')

def test_migration_idempotency_and_full_row_reconciliation(tmp_path):
    jobs=DailyJobs(tmp_path)
    oracle=dict(kind='jobs',source_sha='a'*64,after_sha='a'*64,data={
        'scheduler_policy':dict(columns=['id','enabled','revision','updated_at'],rows=[[1,0,7,'2026-10-09T01:00:00+00:00']]),
        'update_jobs':dict(columns=['job_id','trigger','mode','through_date','status','created_at','finished_at','idempotency_key','error'],rows=[['OLD','MANUAL','CATCH_UP','2026-10-09','PUBLISHED_FULL','2026-10-09T22:00:00+08:00','2026-10-09T22:01:00+08:00','key',None]]),
        'update_job_days':dict(columns=['job_id','trade_date','state','attempt_count','next_retry_at','source_checks'],rows=[['OLD','2026-10-09','PUBLISHED',1,None,'{}']]),
        'update_events':dict(columns=['event_id','job_id','timestamp','stage','event_code','safe_detail'],rows=[[5,'OLD','2026-10-09T22:01:00+08:00','DAY_RECEIPT','PUBLISHED','{}']]),
    })
    result=import_oracle(jobs,oracle)
    assert result['counts']['update_events']==1
    assert not jobs.settings()['auto_enabled']
    assert jobs.job('OLD')['status']=='PUBLISHED_FULL'
    assert import_oracle(jobs,oracle)['status']=='ALREADY_IMPORTED'
    assert DailyJobs(tmp_path).job('OLD')['days'][0]['state']=='PUBLISHED'
    bad=json.loads(json.dumps(oracle));bad['data']['scheduler_policy']['rows'][0][1]=1
    with pytest.raises(ValueError,match='IDENTITY_CONFLICT'):import_oracle(jobs,bad)
    for table in ('scheduler_attempts','update_events'):
        with pytest.raises(psycopg.Error,match='IMMUTABLE_JOB'):
            with connection(jobs.schema) as pg:pg.execute('TRUNCATE '+table)


def test_journal_shared_lock_serializes_stale_head_and_export_failure(tmp_path,monkeypatch):
    path=tmp_path/'concurrent.pg.json'
    first=JournalConnection(path,tmp_path,'R4_TEST_JOURNAL')
    first.execute('INSERT INTO days VALUES(?,?,?)',('2026-10-08','a'*64,'[]'))
    first.execute("INSERT OR REPLACE INTO metadata VALUES('head',?)",('HEAD_ONE',))
    first.commit();first.close();original=path.read_bytes()
    frozen=tmp_path/'frozen.pg.json';shutil.copyfile(path,frozen)
    winner=JournalConnection(path,tmp_path,'R4_TEST_JOURNAL')
    winner.execute('INSERT INTO days VALUES(?,?,?)',('2026-10-09','b'*64,'[]'))
    winner.execute("INSERT OR REPLACE INTO metadata VALUES('head',?)",('HEAD_TWO',))
    def stale_writer():
        stale=JournalConnection(path,tmp_path,'R4_TEST_JOURNAL')
        try:
            current=stale.execute("SELECT value FROM metadata WHERE key='head'").fetchone()[0]
            # append(expected=HEAD_ONE) uses this exact comparison and rejects.
            assert current!='HEAD_ONE'
            assert current=='HEAD_TWO'
            stale.rollback()
            return current
        finally:stale.close()
    from workbench_db import v4_journal_pg_r1 as journal
    def export_failure(*args):raise OSError('INJECTED_DESCRIPTOR_EXPORT_FAILURE')
    monkeypatch.setattr(journal,'atomic_bytes',export_failure)
    with ThreadPoolExecutor(max_workers=1) as pool:
        future=pool.submit(stale_writer)
        with pytest.raises(OSError,match='EXPORT_FAILURE'):winner.commit()
        winner.close()
        assert future.result(timeout=10)=='HEAD_TWO'
    assert path.read_bytes()==original
    # Filesystem export is stale, but the committed PG registry is authoritative.
    with open_read(path) as current:
        assert current.execute("SELECT value FROM metadata WHERE key='head'").fetchone()[0]=='HEAD_TWO'
        assert current.execute('SELECT count(*) FROM days').fetchone()[0]==2
    with open_read(frozen) as historical:
        assert historical.execute("SELECT value FROM metadata WHERE key='head'").fetchone()[0]=='HEAD_ONE'
        assert historical.execute('SELECT count(*) FROM days').fetchone()[0]==1


def test_staged_journal_fork_uses_frozen_version_and_new_cas_namespace(tmp_path):
    original=tmp_path/'original.pg.json';stage=tmp_path/'staged.pg.json'
    db=JournalConnection(original,tmp_path,'R4_TEST_FORK')
    db.execute('INSERT INTO days VALUES(?,?,?)',('2026-10-08','a'*64,'[]'))
    db.execute("INSERT OR REPLACE INTO metadata VALUES('head',?)",('FROZEN_HEAD',));db.commit();db.close()
    shutil.copyfile(original,stage)
    fork=JournalConnection(stage,tmp_path,'R4_TEST_FORK')
    assert fork.execute("SELECT value FROM metadata WHERE key='head'").fetchone()[0]=='FROZEN_HEAD'
    fork.execute('INSERT INTO days VALUES(?,?,?)',('2026-10-09','b'*64,'[]'))
    fork.execute("INSERT OR REPLACE INTO metadata VALUES('head',?)",('STAGED_HEAD',));fork.commit();fork.close()
    with open_read(original) as prior:assert prior.execute('SELECT count(*) FROM days').fetchone()[0]==1
    with open_read(stage) as current:assert current.execute('SELECT count(*) FROM days').fetchone()[0]==2
