"""Tests use only an explicitly disposable R1.1 DSN or their own destroyed cluster."""
from pathlib import Path
import os
import pytest
import psycopg

@pytest.fixture(scope='session')
def v410_disposable_dsn():
    if os.environ.get('V4_10_DISPOSABLE_TEST_DSN'):
        yield os.environ['V4_10_DISPOSABLE_TEST_DSN']
        return
    from scripts.run_v4_08_r3_isolated_verification import disposable_cluster,apply_migrations
    with disposable_cluster(Path(r'E:\Postgres\bin')) as (dsn,temp):
        with psycopg.connect(dsn) as pg:apply_migrations(pg)
        yield dsn

@pytest.fixture
def pg(v410_disposable_dsn):
    with psycopg.connect(v410_disposable_dsn) as connection:
        connection.execute('SAVEPOINT v410_test_scope')
        yield connection
        connection.execute('ROLLBACK TO SAVEPOINT v410_test_scope')
