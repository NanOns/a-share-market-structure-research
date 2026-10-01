import os
import pytest
import psycopg
from scripts.verify_a09_consumer_identity_r1 import oracle,legacy_writer
from tests.v4_09.test_stock_prewatch import fixture_context,PACKAGE
from src.v4.stock_prewatch import build

def test_real_postgres_legacy_rows_consumers_collisions_and_exact_rollback():
    dsn=os.environ.get('V4_10_DISPOSABLE_TEST_DSN')
    if not dsn:pytest.skip('Explicit disposable database DSN required')
    context,cores,factors,seeds=fixture_context(count=3)
    records=build(cores,factors,seeds,context,PACKAGE)
    with psycopg.connect(dsn) as pg:
        result=oracle(pg,records,legacy_writer())
        assert all(result['checks'].values()) and result['legacy_row_count']==3
