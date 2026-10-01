from pathlib import Path
import os,pytest,psycopg
@pytest.fixture(scope='session')
def candidate_dsn():
    dsn=os.environ.get('V4_10_DISPOSABLE_TEST_DSN')
    if dsn:yield dsn;return
    from scripts.run_v4_08_r3_isolated_verification import disposable_cluster,apply_migrations
    with disposable_cluster(Path('E:/Postgres/bin')) as (dsn,temp):
        with psycopg.connect(dsn) as pg:apply_migrations(pg)
        yield dsn
@pytest.fixture
def pg(candidate_dsn):
    with psycopg.connect(candidate_dsn) as pg:
        pg.execute('BEGIN')
        yield pg
        pg.rollback()
