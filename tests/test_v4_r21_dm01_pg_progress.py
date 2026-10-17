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
        if "FROM update_jobs j LEFT JOIN update_job_progress" in sql:
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
        assert schema == "v4_jobs_test"
        assert read_only is True
        yield pg

    monkeypatch.setattr(daily_pg, "connection", read_connection)
    jobs = object.__new__(daily_pg.DailyJobs)
    jobs.schema = "v4_jobs_test"
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


def test_dm01_daily_progress_reports_no_published_receipt_as_none(monkeypatch, tmp_path):
    pg = ReadConnection(None, {"last_published_trade_date": None})

    @contextmanager
    def read_connection(schema, *, dsn, read_only, row_factory):
        yield pg

    monkeypatch.setattr(daily_pg, "connection", read_connection)
    jobs = object.__new__(daily_pg.DailyJobs)
    jobs.schema = "v4_jobs_test"
    jobs.dsn = "reader-dsn-placeholder"
    jobs.root = tmp_path
    jobs.worker_error = None

    result = jobs.progress()
    assert result["stage_state"] == "IDLE"
    assert result["last_published_trade_date"] is None
