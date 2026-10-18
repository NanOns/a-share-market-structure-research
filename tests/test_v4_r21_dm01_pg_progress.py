from contextlib import contextmanager

from workbench_analysis import operational_daily_jobs_pg_r1 as daily_pg


class Cursor:
    def __init__(self, row):
        self.row = row

    def fetchone(self):
        return self.row


class ReadConnection:
    def __init__(self, progress, accepted):
        self.progress = progress
        self.accepted = accepted
        self.statements = []

    def execute(self, sql, params=()):
        self.statements.append((sql, params))
        if "FROM jobs_update_jobs_r1 j LEFT JOIN jobs_update_job_progress_r1" in sql:
            return Cursor(self.progress)
        if "MAX(d.trade_date)" in sql:
            return Cursor(self.accepted)
        raise AssertionError("unexpected progress SQL")


def test_dm01_daily_progress_uses_pg_published_receipts_without_head_file(monkeypatch, tmp_path):
    pg = ReadConnection(
        {"job_id": "job-1", "stage_state": "FAILED_TERMINAL", "processed": 10, "total": 10},
        {"last_published_trade_date": "2026-10-16"},
    )

    @contextmanager
    def read_connection(schema, *, dsn, read_only, row_factory):
        assert schema == "v4"
        assert dsn == "reader-dsn-placeholder"
        assert read_only is True
        yield pg

    monkeypatch.setattr(daily_pg, "connection", read_connection)
    monkeypatch.setattr(daily_pg, "configured_reader_dsn", lambda: "reader-dsn-placeholder")
    jobs = object.__new__(daily_pg.DailyJobs)
    jobs.schema = "v4"
    jobs.dsn = "reader-dsn-placeholder"
    jobs.root = tmp_path
    jobs.worker_error = None

    result = jobs.progress()
    assert result["last_published_trade_date"] == "2026-10-16"
    assert result["stage_state"] == "FAILED_TERMINAL"
    assert len(pg.statements) == 2
    assert "MAX(d.trade_date)" in pg.statements[1][0]
    assert not (tmp_path / "data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json").exists()


def test_dm01_published_receipt_poll_has_partial_index():
    assert "update_job_days_published_trade_date" in daily_pg.DDL
    assert "WHERE state='PUBLISHED'" in daily_pg.DDL
    assert "ADD COLUMN IF NOT EXISTS heartbeat_at timestamptz" in daily_pg.DDL


def test_dm01_status_catalog_preflight_is_select_only_and_covers_heartbeat():
    import re
    from pathlib import Path

    sql = (Path(__file__).resolve().parents[1] / "docs/upgrade/R21R4_DM01_PG_STATUS_PREFLIGHT_READONLY_20261017.sql").read_text(encoding="utf-8")
    statements = re.sub(r"--[^\n]*", "", sql)
    statements = [part.strip().upper() for part in statements.split(";") if part.strip()]
    assert statements[0] == "BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY"
    assert statements[-1] == "COMMIT"
    assert all(statement.startswith(("SELECT ", "WITH ")) for statement in statements[1:-1])
    assert "'V4' AS JOBS_SCHEMA" in sql.upper()
    assert "('JOBS_UPDATE_JOB_PROGRESS_R1','HEARTBEAT_AT')" in sql.upper()
    assert "JOBS_UPDATE_JOB_DAYS_PUBLISHED_TRADE_DATE_R1" in sql.upper()


def test_dm01_pg_progress_upsert_persists_real_heartbeat(monkeypatch, tmp_path):
    class RecordingConnection:
        def __init__(self):
            self.statements = []

        def execute(self, query, params=()):
            self.statements.append((query, params))

    pg = RecordingConnection()

    @contextmanager
    def write_connection(schema, *, dsn, row_factory):
        assert schema == "v4"
        yield pg

    monkeypatch.setattr(daily_pg, "connection", write_connection)
    jobs = object.__new__(daily_pg.DailyJobs)
    jobs.schema = "v4"
    jobs.dsn = "writer-dsn-placeholder"
    jobs.active_job_id = "job-1"
    jobs.lock_key = 42

    jobs.record_progress("2026-10-16", "SOURCE_CHECKING", {"processed": 2, "total": 5, "unit": "rows"})

    query, params = pg.statements[1]
    assert "heartbeat_at" in query.split("ON CONFLICT", 1)[0]
    assert "heartbeat_at=EXCLUDED.heartbeat_at" in query
    assert params == ("job-1", "2026-10-16", "SOURCE_CHECKING", 2, 5, "rows", "SOURCE_CHECKING", None)


def test_dm01_gap_plan_uses_pg_accepted_head_and_calendar_without_file_head(monkeypatch, tmp_path):
    from datetime import datetime
    from zoneinfo import ZoneInfo

    calendar = {
        "contract_id": "V4_OFFICIAL_MARKET_CALENDAR_V1", "status": "ACCEPTED",
        "agreement": True, "exchanges": ["SSE", "SZSE"],
        "coverage_start": "2026-10-15", "coverage_end": "2026-10-16",
        "accepted_trade_date": "2026-10-15", "session_dates": ["2026-10-15", "2026-10-16"],
        "binding": {"market_calendar_id": "calendar-r1", "calendar_digest": "a" * 64},
    }

    class Reader:
        def calendar(self):
            return calendar

    monkeypatch.setenv("V4_MARKET_CALENDAR_SOURCE", "PG")
    monkeypatch.setattr("workbench_db.v4_market_calendar_reader_r1.from_environment", lambda: Reader())
    jobs = object.__new__(daily_pg.DailyJobs)
    jobs.root = tmp_path
    jobs.clock = lambda: datetime.fromisoformat("2026-10-16T19:00:00+08:00").astimezone(ZoneInfo("Asia/Shanghai"))

    plan = jobs._gap_plan("2026-10-16")
    assert plan["last_good_trade_date"] == "2026-10-15"
    assert plan["last_good_head_source"] == "PG_ACCEPTED_PUBLICATION_HEAD"
    assert plan["eligible_sessions"] == ["2026-10-16"]
    assert not (tmp_path / "data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json").exists()


def test_daily_executor_noop_uses_pg_accepted_head_without_file_fallback(monkeypatch, tmp_path):
    from workbench_analysis import operational_daily_executor_v1 as executor

    class Reader:
        def calendar(self):
            return {"status": "ACCEPTED", "source": "PG_ACCEPTED_PUBLICATION_HEAD",
                    "accepted_trade_date": "2026-10-16"}

    monkeypatch.setenv("V4_MARKET_CALENDAR_SOURCE", "PG")
    monkeypatch.setattr("workbench_db.v4_market_calendar_reader_r1.from_environment", lambda: Reader())
    result = executor.execute_sources(tmp_path, "2026-10-16", "CATCH_UP")
    assert result["reason"] == "NOOP_ALREADY_CURRENT"
    assert result["accepted_trade_date"] == "2026-10-16"
    assert not (tmp_path / "data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json").exists()


def test_daily_executor_defaults_to_pg_accepted_head_without_file_fallback(monkeypatch,tmp_path):
    from workbench_analysis import operational_daily_executor_v1 as executor
    class Reader:
        def calendar(self):
            return {"status":"ACCEPTED","source":"PG_ACCEPTED_PUBLICATION_HEAD",
                    "accepted_trade_date":"2026-10-16"}
    monkeypatch.delenv("V4_MARKET_CALENDAR_SOURCE",raising=False)
    monkeypatch.setattr("workbench_db.v4_market_calendar_reader_r1.from_environment",lambda:Reader())
    result=executor.execute_sources(tmp_path,"2026-10-16","CATCH_UP")
    assert result["reason"]=="NOOP_ALREADY_CURRENT"
    assert result["accepted_trade_date"]=="2026-10-16"
    assert not (tmp_path/"data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json").exists()


def test_daily_executor_pg_head_failure_does_not_fall_back_to_file(monkeypatch, tmp_path):
    from workbench_analysis import operational_daily_executor_v1 as executor
    import pytest

    monkeypatch.setenv("V4_MARKET_CALENDAR_SOURCE", "PG")
    monkeypatch.setattr(
        "workbench_db.v4_market_calendar_reader_r1.from_environment",
        lambda: (_ for _ in ()).throw(ValueError("PG_READ_FAILED")),
    )
    with pytest.raises(ValueError, match="PG_READ_FAILED"):
        executor.execute_sources(tmp_path, "2026-10-16", "CATCH_UP")
    assert not (tmp_path / "data/v4/V4_OPERATIONAL_RESEARCH_HEAD.json").exists()


def test_dm01_daily_progress_reports_no_published_receipt_as_none(monkeypatch, tmp_path):
    pg = ReadConnection(None, {"last_published_trade_date": None})

    @contextmanager
    def read_connection(schema, *, dsn, read_only, row_factory):
        assert dsn == "reader-dsn-placeholder"
        assert read_only is True
        yield pg

    monkeypatch.setattr(daily_pg, "connection", read_connection)
    monkeypatch.setattr(daily_pg, "configured_reader_dsn", lambda: "reader-dsn-placeholder")
    jobs = object.__new__(daily_pg.DailyJobs)
    jobs.schema = "v4"
    jobs.dsn = "reader-dsn-placeholder"
    jobs.root = tmp_path
    jobs.worker_error = None

    result = jobs.progress()
    assert result["stage_state"] == "IDLE"
    assert result["last_published_trade_date"] is None


def test_dm01_progress_does_not_fall_back_to_writer_dsn(monkeypatch, tmp_path):
    import pytest

    def forbidden_connection(*args, **kwargs):
        raise AssertionError("reader configuration must fail before opening a connection")

    monkeypatch.setattr(daily_pg, "connection", forbidden_connection)
    monkeypatch.setattr(
        daily_pg,
        "configured_reader_dsn",
        lambda: (_ for _ in ()).throw(RuntimeError("V4_NATIVE_PG_READER_DSN_REQUIRED_NO_WRITER_FALLBACK")),
    )
    jobs = object.__new__(daily_pg.DailyJobs)
    jobs.schema = "v4"
    jobs.dsn = "writer-dsn-placeholder"
    jobs.root = tmp_path
    jobs.worker_error = None

    with pytest.raises(RuntimeError, match="V4_NATIVE_PG_READER_DSN_REQUIRED_NO_WRITER_FALLBACK"):
        jobs.progress()


def test_dm01_job_and_settings_reads_use_reader_dsn_and_readonly_transaction(monkeypatch, tmp_path):
    class RowsCursor:
        def __init__(self, one=None, rows=()):
            self.one=one;self.rows=rows
        def fetchone(self):return self.one
        def __iter__(self):return iter(self.rows)

    class ReadDb:
        def execute(self,sql,params=()):
            if sql=='SELECT * FROM jobs_update_jobs_r1 WHERE job_id=?':
                return RowsCursor(one={'job_id':'job-1','status':'QUEUED','through_date':'2026-10-16'})
            if sql=='SELECT * FROM jobs_update_job_days_r1 WHERE job_id=? ORDER BY trade_date':
                return RowsCursor(rows=[])
            if sql=='SELECT * FROM jobs_scheduler_policy_r1 WHERE id=1':
                return RowsCursor(one={'enabled':1,'revision':2,'updated_at':'2026-10-16T10:00:00+08:00'})
            raise AssertionError('unexpected read SQL: '+sql)

    db=ReadDb();opened=[]
    @contextmanager
    def connection(schema,*,dsn,read_only,row_factory):
        opened.append((schema,dsn,read_only))
        yield db

    monkeypatch.setattr(daily_pg,'connection',connection)
    monkeypatch.setattr(daily_pg,'configured_reader_dsn',lambda:'reader-only-dsn')
    jobs=object.__new__(daily_pg.DailyJobs)
    jobs.schema='v4';jobs.root=tmp_path;jobs.thread=None;jobs.policy_binding=None
    jobs._load_approved_policy=lambda: (
        {'contract_id':'READ_ONLY_OPERATIONAL_DAILY_RELEASE_POLICY_V1_1','version':'1.1.0',
         'historical_PIT_permission':False,'automated_trading_permission':False,
         'algorithm_upgrade_permission':False,'publication_ready':False},
        {'contract_id':'READ_ONLY_OPERATIONAL_DAILY_RELEASE_POLICY_V1_1','version':'1.1.0'},
    )

    assert jobs.job('job-1')['status']=='QUEUED'
    settings=jobs.settings()
    assert settings['auto_enabled'] is True and settings['revision']==2
    assert opened==[('v4','reader-only-dsn',True)]*2


def test_dm01_readonly_status_client_needs_no_writer_and_cannot_start_work(monkeypatch, tmp_path):
    import pytest
    pg=ReadConnection(None,None)
    @contextmanager
    def connection(schema,*,dsn,read_only,row_factory):
        assert schema=='v4' and dsn=='reader-only-dsn' and read_only is True
        yield pg
    monkeypatch.setattr(daily_pg,'connection',connection)
    monkeypatch.setattr(daily_pg,'configured_reader_dsn',lambda:'reader-only-dsn')
    monkeypatch.setattr(daily_pg,'configured_dsn',lambda:(_ for _ in ()).throw(AssertionError('writer DSN resolved')))
    reader=daily_pg.DailyJobsReadOnly(tmp_path)
    assert reader.progress()['stage_state']=='IDLE'
    with pytest.raises(RuntimeError,match='V4_PG_DAILY_JOBS_READ_ONLY'):
        reader.start()
    with pytest.raises(RuntimeError,match='V4_PG_DAILY_JOBS_READ_ONLY'):
        with reader.connect():
            pass
    with pytest.raises(RuntimeError,match='V4_PG_DAILY_JOBS_READ_ONLY'):
        reader.set_settings(False)
