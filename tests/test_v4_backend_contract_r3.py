"""A confirmed counterexample is evidence, never a backend migration pass."""
from pathlib import Path
import sqlite3
import pytest
from workbench_analysis.operational_daily_jobs_v1 import DailyJobs

def test_current_daily_jobs_require_sqlite_before_postgres_only_guard(monkeypatch,tmp_path):
    attempted=[]
    def reject(path,*args,**kwargs):
        attempted.append(Path(path))
        raise ValueError('V4_POSTGRES_ONLY_COUNTEREXAMPLE_SQLITE_ATTEMPT')
    monkeypatch.setattr(sqlite3,'connect',reject)
    with pytest.raises(ValueError,match='V4_POSTGRES_ONLY_COUNTEREXAMPLE_SQLITE_ATTEMPT'):
        DailyJobs(tmp_path)
    assert attempted==[tmp_path/'runtime/dynamic_daily/jobs.sqlite3']
    assert not attempted[0].exists()
