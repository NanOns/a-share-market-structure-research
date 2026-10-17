"""Retained original counterexample node now guards the native successor."""
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
    # The authorized PG-only successor has removed the original SQLite
    # counterexample. Retain the node and its rejected-legacy-call probe,
    # and require missing native authority to fail before legacy fallback.
    monkeypatch.delenv('V4_NATIVE_PG_DSN',raising=False)
    monkeypatch.delenv('WORKBENCH_PG_DSN',raising=False)
    with pytest.raises(RuntimeError,match='WORKBENCH_PG_DSN_REQUIRED'):
        DailyJobs(tmp_path)
    assert attempted==[]
    assert not (tmp_path/'runtime/dynamic_daily/jobs.sqlite3').exists()
